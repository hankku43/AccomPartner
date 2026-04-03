"""
generate_controller.py
----------------------
業務邏輯控制器（Controller 層）。

職責：
  1. 接收已驗證的請求資料（來自 Router 層）
  2. 協調 Service 層的呼叫順序
  3. 處理業務例外狀況並轉換為 HTTP 錯誤
  4. 回傳 MIDI bytes 給 Router
"""

import traceback
import logging

from fastapi import HTTPException, UploadFile

from app.models.schemas import GenerateFromJsonRequest
from app.services import midi_service
from app.services.model_router import get_service

logger = logging.getLogger(__name__)


async def generate_from_json(req: GenerateFromJsonRequest) -> bytes:
    """
    流程：
      1. 把 JSON 音符列表 → MIDI bytes（midi_service）
      2. 根據 mode 選擇推理服務（model_router）
      3. 呼叫推理服務，取得帶伴奏的 MIDI bytes
      4. 回傳給 Router

    Args:
        req: 驗證後的 GenerateFromJsonRequest

    Returns:
        MIDI 二進位資料 (bytes)
    """
    try:
        melody_midi = midi_service.notes_to_midi(req.melody, bpm=req.bpm)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"旋律轉換 MIDI 失敗：{e}")

    service_fn = get_service(req.mode)
    logger.info(
        "JSON 推理請求: mode=%s, complexity=%.2f, creativity=%.2f",
        req.mode,
        req.complexity,
        req.creativity,
    )

    try:
        result_midi, _ = await service_fn(
            melody_midi, complexity=req.complexity, creativity=req.creativity
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"模型推理失敗：{e}")

    return result_midi


async def generate_from_midi(
    file: UploadFile,
    target_track_index: int,
    mode: str,
    complexity: float = 0.5,
    creativity: float = 1.0,
) -> tuple[bytes, list[list[str]]]:
    """
    流程：
      1. 讀取上傳的 MIDI 檔案 bytes
      2. 提取指定音軌（midi_service）
      3. 根據 mode 選擇推理服務
      4. 呼叫推理服務
      5. 回傳

    Args:
        file:               上傳的 MIDI 檔案 (UploadFile)
        target_track_index: 使用者選擇的旋律音軌索引
        mode:               推理模式 ('oneStage' | 'twoStage-std' | 'twoStage-bar' | 'twoStage-nar')

    Returns:
        MIDI 二進位資料 (bytes)
    """
    raw_bytes = await file.read()
    if not raw_bytes:
        raise HTTPException(status_code=400, detail="上傳的 MIDI 檔案是空的")

    try:
        melody_midi = midi_service.extract_track_from_midi(
            raw_bytes, target_track_index
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"MIDI 解析失敗：{e}")

    service_fn = get_service(mode)
    logger.info(
        "MIDI 推理請求: mode=%s, complexity=%.2f, creativity=%.2f",
        mode,
        complexity,
        creativity,
    )

    try:
        result_midi, chords_list = await service_fn(
            melody_midi, complexity=complexity, creativity=creativity
        )
    except Exception as e:
        logger.error("模型推理失敗：%s\n%s", e, traceback.format_exc())
        raise HTTPException(status_code=500, detail=f"模型推理失敗：{e}")

    return result_midi, chords_list
