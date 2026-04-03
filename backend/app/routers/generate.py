"""
generate.py  (Router / View 層)
-------------------------------
定義所有與「生成伴奏」相關的 HTTP 路由。

Router 層只負責：
  - 宣告路徑、HTTP 方法、參數解析
  - 套用 Rate Limit 裝飾器
  - 把驗證後的資料交給 Controller
  - 把 Controller 回傳的 bytes 包裝成 HTTP Response
"""

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import Response, JSONResponse
import base64

from app.controllers import generate_controller
from app.core.config import Settings, get_settings
from app.core.limiter import limiter
from app.models.schemas import GenerateFromJsonRequest, HealthResponse

router = APIRouter(prefix="/api", tags=["generate"])


@router.get("/health", response_model=HealthResponse, summary="健康檢查")
async def health_check(settings: Settings = Depends(get_settings)):
    return HealthResponse(status="ok", version="1.0.0")


@router.post(
    "/generate-from-json",
    summary="從 JSON 旋律生成伴奏",
    response_class=Response,
    responses={
        200: {"content": {"audio/midi": {}}, "description": "MIDI 二進位資料"},
        400: {"description": "請求格式錯誤或不支援的模式"},
        422: {"description": "旋律資料驗證失敗"},
        429: {"description": "請求過於頻繁，請稍後再試"},
        500: {"description": "伺服器內部錯誤"},
    },
)
@limiter.limit("5/minute")
async def generate_from_json(
    request: Request,  # slowapi 需要此參數
    req: GenerateFromJsonRequest,
    settings: Settings = Depends(get_settings),
):
    """
    接收前端 Pad / VexFlow 編輯器的 JSON 旋律資料，呼叫 AI 模型生成伴奏。

    Request Body:
      - `melody`: 音符事件列表 `[{pitch, step, duration, accidental}]`
      - `mode`: 推理模式 (`"ar"` 或 `"nar"`，預設 `"ar"`)
      - `bpm`: 每分鐘拍數（預設 120）

    Response:
      - 二進位 MIDI 檔案（Content-Type: audio/midi）
    """
    midi_bytes = await generate_controller.generate_from_json(req)
    return Response(
        content=midi_bytes,
        media_type="audio/midi",
        headers={"Content-Disposition": "attachment; filename=accompaniment.mid"},
    )


@router.post(
    "/generate-from-midi",
    summary="從上傳 MIDI 生成伴奏",
    response_class=Response,
    responses={
        200: {"content": {"audio/midi": {}}, "description": "MIDI 二進位資料"},
        400: {"description": "請求格式錯誤"},
        422: {"description": "MIDI 解析失敗"},
        429: {"description": "請求過於頻繁，請稍後再試"},
        500: {"description": "伺服器內部錯誤"},
    },
)
@limiter.limit("5/minute")
async def generate_from_midi(
    request: Request,  # slowapi 需要此參數
    midiFile: UploadFile = File(..., description="上傳的 MIDI 檔案"),
    targetTrackIndex: int = Form(..., description="使用者選擇的旋律音軌索引"),
    mode: str = Form(
        default="oneStage",
        description="推理模式：'oneStage' | 'twoStage-std' | 'twoStage-bar' | 'twoStage-nar'",
    ),
    complexity: float = Form(default=0.5, description="伴奏複雜度 0.0~1.0"),
    creativity: float = Form(default=1.0, description="創意程度 0.1~2.0"),
    settings: Settings = Depends(get_settings),
):
    """
    接收上傳的 MIDI 檔案與使用者選定的音軌索引，呼叫 AI 模型生成伴奏。

    Form Data:
      - `midiFile`: MIDI 檔案（.mid / .midi）
      - `targetTrackIndex`: 整數，選定的旋律音軌索引
      - `mode`: 推理模式（預設 `"ar"`）

    Response:
      - 二進位 MIDI 檔案（Content-Type: audio/midi）
    """
    midi_bytes, chords_list = await generate_controller.generate_from_midi(
        file=midiFile,
        target_track_index=targetTrackIndex,
        mode=mode,
        complexity=complexity,
        creativity=creativity,
    )
    
    encoded_midi = base64.b64encode(midi_bytes).decode('utf-8')
    
    return JSONResponse(
        content={
            "midi_b64": encoded_midi,
            "chords": chords_list
        }
    )
