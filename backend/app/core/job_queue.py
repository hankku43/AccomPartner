"""
job_queue.py  (Core)
--------------------
全域非同步工作佇列，負責：
  1. 接收推理請求，分配 job_id
  2. 維護一個有序的工作佇列（asyncio.Queue）
  3. 提供「插隊密碼」機制：密碼正確時工作排到下一位（佇列最前端）
     - 每個 IP 每分鐘僅能使用一次插隊
  4. 以 asyncio 背景 Worker 序列處理工作（一次只跑一個，避免 GPU OOM）
  5. 提供 get_job_status(job_id) 查詢進度
  6. 完成的 Job 在 JOB_TTL_SECONDS 後自動從記憶體清除
"""

from __future__ import annotations

import asyncio
import time
import uuid
import logging
import os
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Coroutine, Optional

logger = logging.getLogger(__name__)

# ── 插隊密碼（從環境變數讀取，避免硬編碼）────────────────────────────────────
VIP_PASSWORD = os.getenv("VIP_QUEUE_PASSWORD", "accompartner2025")
# 每個 IP 使用插隊密碼的冷卻時間（秒）
VIP_COOLDOWN_SECONDS = 60
# 完成的 Job 在記憶體中保留的時間（秒），讓前端有足夠時間取結果
JOB_TTL_SECONDS = 600  # 10 分鐘


class JobStatus(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    DONE = "done"
    ERROR = "error"


@dataclass
class Job:
    job_id: str
    coro_factory: Callable[[], Coroutine]  # 呼叫後回傳一個 coroutine
    status: JobStatus = JobStatus.QUEUED
    position: int = 0          # 佇列位置（0 = 正在跑 / 快輪到）
    progress: float = 0.0      # 0.0 ~ 1.0
    stage_label: str = ""      # 例如 "Stage 1/3: Chord Prediction"
    result: Optional[Any] = None
    error: Optional[str] = None
    vip_accepted: bool = False
    created_at: float = field(default_factory=time.time)
    started_at: Optional[float] = None
    finished_at: Optional[float] = None

    # 方便前端輪詢的 dict
    def to_dict(self) -> dict:
        wait_sec = None
        if self.status == JobStatus.QUEUED and self.position > 0:
            # 粗估：每個 job 平均 120 秒（three-stage 最慢）
            wait_sec = self.position * 120
        elapsed = None
        if self.started_at:
            end = self.finished_at or time.time()
            elapsed = round(end - self.started_at, 1)
        return {
            "job_id": self.job_id,
            "status": self.status.value,
            "position": self.position,
            "queue_length": _queue_manager.queue_length(),
            "progress": round(self.progress, 3),
            "stage_label": self.stage_label,
            "estimated_wait_seconds": wait_sec,
            "elapsed_seconds": elapsed,
            "error": self.error,
            "vip_accepted": self.vip_accepted,
        }


class QueueManager:
    """
    管理一個 FIFO 佇列 + 插隊邏輯 + 單 Worker。

    修正：
    - _jobs 中的完成 Job 在 JOB_TTL_SECONDS 後自動清除（防止記憶體洩漏）
    - _vip_cooldown 中的過期條目在 _check_vip 時順帶清除（防止記憶體洩漏）
    - _recalc_positions 改用 _is_running 旗標，不再線性掃 _jobs（效能優化）
    """

    def __init__(self):
        # 有序 list 當作優先佇列（比 asyncio.Queue 更容易插隊）
        self._pending: list[Job] = []
        self._jobs: dict[str, Job] = {}   # job_id → Job
        self._lock = asyncio.Lock()
        self._event = asyncio.Event()     # 喚醒 worker

        # 修正 3：用明確旗標取代線性掃描
        self._is_running: bool = False

        self._worker_task: Optional[asyncio.Task] = None

        # 插隊冷卻：IP → 上次使用時間戳
        self._vip_cooldown: dict[str, float] = {}

    # ── 公開 API ────────────────────────────────────────────────────────────

    async def submit(
        self,
        coro_factory: Callable[[], Coroutine],
        client_ip: str = "unknown",
        vip_password: str = "",
    ) -> Job:
        """
        提交一個工作到佇列。
        - vip_password 正確 → 插到現有 QUEUED 工作的最前面（緊接在 RUNNING 後）
        - vip_password 錯誤或未提供 → 正常排隊到尾巴
        回傳 Job 物件，前端可用 job.job_id 輪詢狀態。
        """
        job_id = str(uuid.uuid4())
        job = Job(job_id=job_id, coro_factory=coro_factory)
        self._jobs[job_id] = job

        is_vip = self._check_vip(client_ip, vip_password)
        job.vip_accepted = is_vip

        async with self._lock:
            if is_vip:
                # 插到佇列最前面（index 0）
                self._pending.insert(0, job)
                logger.info("[Queue] VIP jump: job=%s ip=%s", job_id, client_ip)
            else:
                self._pending.append(job)

            self._recalc_positions()

        self._event.set()
        return job

    async def check_vip_eligibility(self, client_ip: str) -> dict:
        """
        回傳該 IP 目前是否在插隊冷卻中。
        """
        now = time.time()
        last = self._vip_cooldown.get(client_ip, 0)
        remaining = max(0, VIP_COOLDOWN_SECONDS - (now - last))
        return {
            "eligible": remaining == 0,
            "cooldown_remaining_seconds": round(remaining),
        }

    async def cancel(self, job_id: str) -> dict:
        """
        取消一個排隊中的 job。
        - QUEUED：從 _pending 移除，狀態改 ERROR
        - RUNNING / DONE / ERROR：無法中途取消，回傳 cancelled=False
        """
        job = self._jobs.get(job_id)
        if not job:
            return {"cancelled": False, "reason": "job not found"}
        if job.status == JobStatus.RUNNING:
            return {"cancelled": False, "reason": "job already running"}
        if job.status in (JobStatus.DONE, JobStatus.ERROR):
            return {"cancelled": False, "reason": "job already finished"}

        async with self._lock:
            try:
                self._pending.remove(job)
            except ValueError:
                # 在檢查與加鎖之間剛好被 worker 取走
                return {"cancelled": False, "reason": "job already running"}
            job.status = JobStatus.ERROR
            job.error = "Cancelled by user"
            job.finished_at = time.time()
            self._recalc_positions()

        asyncio.create_task(self._schedule_cleanup(job_id))
        logger.info("[Queue] Job %s cancelled by user.", job_id)
        return {"cancelled": True}

    def get_job(self, job_id: str) -> Optional[Job]:
        return self._jobs.get(job_id)

    def queue_length(self) -> int:
        """含 RUNNING 在內的未完成工作數量"""
        return len(self._pending) + (1 if self._is_running else 0)

    # ── 背景 Worker ──────────────────────────────────────────────────────────

    def start_worker(self):
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker_loop())
            logger.info("[Queue] Worker started.")

    async def _worker_loop(self):
        while True:
            await self._event.wait()
            self._event.clear()

            while True:
                async with self._lock:
                    if not self._pending:
                        break
                    job = self._pending.pop(0)
                    job.status = JobStatus.RUNNING
                    job.position = 0   # 重要：開始執行後重置為 0
                    job.started_at = time.time()
                    # 修正 3：設定執行旗標
                    self._is_running = True
                    self._recalc_positions()

                logger.info("[Queue] Running job=%s", job.job_id)

                # 建立進度回報函式
                def _make_updater(j):
                    def update(progress: float, label: str = ""):
                        j.progress = max(0.0, min(1.0, progress))
                        j.stage_label = label
                    return update

                try:
                    result = await job.coro_factory(_make_updater(job))
                    job.result = result
                    job.status = JobStatus.DONE
                    job.progress = 1.0
                    job.stage_label = "Done ✓"
                except Exception as e:
                    logger.error("[Queue] Job %s failed: %s", job.job_id, e)
                    job.status = JobStatus.ERROR
                    job.error = str(e)
                finally:
                    job.finished_at = time.time()
                    # 修正 3：清除執行旗標
                    self._is_running = False
                    logger.info(
                        "[Queue] Job=%s finished in %.1fs status=%s",
                        job.job_id,
                        job.finished_at - job.started_at,
                        job.status,
                    )
                    # 修正 1：排程 TTL 清除，讓前端有時間取結果
                    asyncio.create_task(self._schedule_cleanup(job.job_id))

    async def _schedule_cleanup(self, job_id: str):
        """等待 JOB_TTL_SECONDS 後，從 _jobs 字典移除已完成的 Job，防止記憶體洩漏。"""
        await asyncio.sleep(JOB_TTL_SECONDS)
        removed = self._jobs.pop(job_id, None)
        if removed:
            logger.debug("[Queue] Job %s expired and removed from memory.", job_id)

    # ── 內部輔助 ─────────────────────────────────────────────────────────────

    def _check_vip(self, client_ip: str, password: str) -> bool:
        """驗證插隊密碼，並更新冷卻時間（只有通過才更新）。

        修正 2：同時清除過期的 IP 冷卻條目，防止字典無限成長。
        """
        now = time.time()

        # 修正 2：清除所有過期條目（比 VIP_COOLDOWN_SECONDS 更舊的）
        expired_ips = [
            ip for ip, ts in self._vip_cooldown.items()
            if now - ts >= VIP_COOLDOWN_SECONDS * 2  # 留 2 倍冷卻時間作緩衝
        ]
        for ip in expired_ips:
            del self._vip_cooldown[ip]
        if expired_ips:
            logger.debug("[Queue] Purged %d expired VIP cooldown entries.", len(expired_ips))

        if not password or password != VIP_PASSWORD:
            return False

        last = self._vip_cooldown.get(client_ip, 0)
        if now - last < VIP_COOLDOWN_SECONDS:
            logger.warning(
                "[Queue] VIP cooldown active for ip=%s, %.0fs remaining",
                client_ip, VIP_COOLDOWN_SECONDS - (now - last)
            )
            return False  # 冷卻中，忽略密碼
        self._vip_cooldown[client_ip] = now
        return True

    def _recalc_positions(self):
        """重算每個 pending job 的佇列位置（1-based，0 保留給 running）。

        修正 3：改用 _is_running 旗標，O(n) 只掃 _pending，不掃 _jobs。
        """
        offset = 1 if self._is_running else 0
        for i, j in enumerate(self._pending):
            j.position = i + offset


# ── 全域單例 ─────────────────────────────────────────────────────────────────
_queue_manager = QueueManager()


def get_queue_manager() -> QueueManager:
    return _queue_manager
