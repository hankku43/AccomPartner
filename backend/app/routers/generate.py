"""
generate.py  (Router / View 層)
-------------------------------
定義所有與「生成伴奏」相關的 HTTP 路由。

Router 層只負責：
  - 宣告路徑、HTTP 方法、參數解析
  - 套用 Rate Limit 裝飾器
  - 把驗證後的資料交給 Controller
  - 把 Controller 回傳的 bytes 包裝成 HTTP Response

佇列機制：
  - /api/generate-from-json     → 提交到佇列，立即回傳 job_id
  - /api/generate-from-midi     → 提交到佇列，立即回傳 job_id
  - /api/queue/status/{job_id}  → 輪詢 job 狀態
  - /api/queue/vip-check        → 查詢插隊冷卻狀態
  - /api/queue/cancel/{job_id}  → 取消排隊中的工作（QUEUED 才能取消）
  - /api/queue/result/{job_id}  → 取得完成後的結果（MIDI bytes 或 JSON）
"""

import io
import base64

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response, JSONResponse

from app.controllers import generate_controller
from app.core.config import Settings, get_settings
from app.core.limiter import limiter
from app.core.job_queue import get_queue_manager, JobStatus
from app.models.schemas import GenerateFromJsonRequest, HealthResponse

router = APIRouter(prefix="/api", tags=["generate"])

# MIDI 上傳大小上限（防止 DoS 攻擊耗盡伺服器記憶體）
MIDI_MAX_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB


@router.get("/health", response_model=HealthResponse, summary="健康檢查")
async def health_check(settings: Settings = Depends(get_settings)):
    return HealthResponse(status="ok", version="1.0.0")


# ── 佇列狀態查詢 ─────────────────────────────────────────────────────────────

@router.get("/queue/status/{job_id}", summary="查詢工作佇列狀態")
async def get_job_status(job_id: str):
    """
    輪詢 job 狀態。前端每 2 秒呼叫一次。

    Response:
      - status: queued | running | done | error
      - position: 目前在佇列的位置（1-based，0 代表正在執行）
      - queue_length: 目前佇列未完成工作總數
      - progress: 0.0 ~ 1.0
      - stage_label: 目前階段描述字串
      - estimated_wait_seconds: 粗估等待秒數
      - elapsed_seconds: 已執行秒數
      - error: 若失敗，錯誤訊息
    """
    qm = get_queue_manager()
    job = qm.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} 不存在")
    return JSONResponse(content=job.to_dict())


@router.get("/queue/vip-check", summary="查詢插隊密碼冷卻狀態")
async def vip_check(request: Request):
    """
    查詢目前 IP 是否可以使用插隊密碼。
    Response:
      - eligible: true/false
      - cooldown_remaining_seconds: 剩餘冷卻秒數
    """
    qm = get_queue_manager()
    client_ip = request.client.host
    result = await qm.check_vip_eligibility(client_ip)
    return JSONResponse(content=result)


@router.delete("/queue/cancel/{job_id}", summary="取消排隊中的工作")
async def cancel_job(job_id: str):
    """
    取消一個尚未執行的 job（QUEUED 狀態）。
    已在執行或已完成的 job 無法取消，回傳 cancelled=False。
    """
    qm = get_queue_manager()
    result = await qm.cancel(job_id)
    if not result["cancelled"] and result.get("reason") == "job not found":
        raise HTTPException(status_code=404, detail=f"Job {job_id} 不存在")
    return JSONResponse(content=result)


@router.get("/queue/result/{job_id}", summary="取得完成的工作結果")
async def get_job_result(job_id: str):
    """
    取得完成的工作結果。
    - 若 job 尚未完成，回傳 202 Accepted。
    - 若 job 完成，回傳 JSON { midi_b64, chords } 或原始 MIDI bytes。
    """
    qm = get_queue_manager()
    job = qm.get_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail=f"Job {job_id} 不存在")

    if job.status == JobStatus.ERROR:
        raise HTTPException(status_code=500, detail=job.error or "推理失敗")

    if job.status != JobStatus.DONE:
        return JSONResponse(status_code=202, content={"detail": "Job 尚未完成", "status": job.status})

    # 從 result 取出
    result = job.result
    if result is None:
        raise HTTPException(status_code=500, detail="Job 完成但沒有結果")

    # result 可能是 bytes（generate-from-json）或 (bytes, list)（generate-from-midi）
    if isinstance(result, tuple):
        midi_bytes, chords_list = result
        encoded_midi = base64.b64encode(midi_bytes).decode("utf-8")
        return JSONResponse(content={"midi_b64": encoded_midi, "chords": chords_list})
    else:
        return Response(
            content=result,
            media_type="audio/midi",
            headers={"Content-Disposition": "attachment; filename=accompaniment.mid"},
        )


# ── 提交到佇列 ───────────────────────────────────────────────────────────────

@router.post(
    "/generate-from-json",
    summary="從 JSON 旋律提交到佇列生成伴奏",
    responses={
        200: {"description": "JSON { job_id: string }"},
        400: {"description": "請求格式錯誤或不支援的模式"},
        422: {"description": "旋律資料驗證失敗"},
        429: {"description": "請求過於頻繁，請稍後再試"},
    },
)
@limiter.limit("5/minute")
async def generate_from_json(
    request: Request,  # slowapi 需要此參數
    req: GenerateFromJsonRequest,
    settings: Settings = Depends(get_settings),
):
    """
    接收前端 JSON 旋律資料，提交到佇列，立即回傳 job_id。
    前端透過 /api/queue/status/{job_id} 輪詢進度。
    """
    qm = get_queue_manager()
    client_ip = request.client.host
    vip_password = request.headers.get("X-VIP-Password", "")

    async def coro_factory(update_progress=None):
        return await generate_controller.generate_from_json(req, update_progress=update_progress)

    job = await qm.submit(coro_factory, client_ip=client_ip, vip_password=vip_password)
    return JSONResponse(content={"job_id": job.job_id, **job.to_dict()})


@router.post(
    "/generate-from-midi",
    summary="從上傳 MIDI 提交到佇列生成伴奏",
    responses={
        200: {"description": "JSON { job_id: string }"},
        400: {"description": "請求格式錯誤"},
        413: {"description": "上傳的 MIDI 檔案超過大小限制（10MB）"},
        422: {"description": "MIDI 解析失敗"},
        429: {"description": "請求過於頻繁，請稍後再試"},
        500: {"description": "伺服器內部錯誤"},
    },
)
@limiter.limit("5/minute")
async def generate_from_midi(
    request: Request,  # slowapi 需要此參數
    midiFile: UploadFile = File(..., description="上傳的 MIDI 檔案（最大 10MB）"),
    targetTrackIndex: int = Form(..., description="使用者選擇的旋律音軌索引"),
    mode: str = Form(
        default="oneStage",
        description="推理模式：'oneStage' | 'twoStage-std' | 'twoStage-bar' | 'twoStage-nar' | 'threeStage'",
    ),
    complexity: float = Form(default=0.5, description="伴奏複雜度 0.0~1.0"),
    creativity: float = Form(default=1.0, description="創意程度 0.1~2.0"),
    settings: Settings = Depends(get_settings),
):
    """
    接收上傳 MIDI，提交到佇列，立即回傳 job_id。
    前端透過 /api/queue/status/{job_id} 輪詢進度。
    """
    # ── 檔案大小驗證 ────────────────────────────────────────────────────────
    midi_content = await midiFile.read()
    if len(midi_content) > MIDI_MAX_SIZE_BYTES:
        raise HTTPException(
            status_code=413,
            detail=f"MIDI 檔案大小超過限制（上限 {MIDI_MAX_SIZE_BYTES // (1024 * 1024)} MB）",
        )

    # 已讀取的 bytes 重新包裝成 UploadFile-like，供 coro_factory 閉包使用
    saved_content = midi_content
    saved_filename = midiFile.filename
    saved_track_index = targetTrackIndex
    saved_mode = mode
    saved_complexity = complexity
    saved_creativity = creativity

    qm = get_queue_manager()
    client_ip = request.client.host
    vip_password = request.headers.get("X-VIP-Password", "")

    async def coro_factory(update_progress=None):
        fake_file = UploadFile(filename=saved_filename, file=io.BytesIO(saved_content))
        return await generate_controller.generate_from_midi(
            file=fake_file,
            target_track_index=saved_track_index,
            mode=saved_mode,
            complexity=saved_complexity,
            creativity=saved_creativity,
            update_progress=update_progress,
        )

    job = await qm.submit(coro_factory, client_ip=client_ip, vip_password=vip_password)
    return JSONResponse(content={"job_id": job.job_id, **job.to_dict()})
