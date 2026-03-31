from pydantic import BaseModel, Field
from typing import List


class NoteEvent(BaseModel):
    """代表一個旋律音符事件（以 8 分音符為 step 單位）"""

    pitch: int = Field(..., ge=0, le=127, description="MIDI 音高編號 (0-127，60=C4)")
    step: int = Field(..., ge=0, description="在 8 分音符網格中的起始位置 (0-based)")
    duration: int = Field(..., ge=1, description="佔幾個 8 分音符 slot")
    accidental: str = Field(default="", description="臨時記號：'' | '#' | 'b'")


class GenerateFromJsonRequest(BaseModel):
    """前端 /api/generate-from-json 的請求格式"""

    melody: List[NoteEvent] = Field(..., min_length=1, description="旋律音符列表")
    mode: str = Field(default="onestage", description="推理模式")
    bpm: int = Field(default=120, ge=40, le=300, description="每分鐘拍數")
    complexity: float = Field(default=0.5, ge=0.0, le=1.0, description="伴奏複雜度")
    creativity: float = Field(default=1.0, ge=0.1, le=2.0, description="創意程度")


class HealthResponse(BaseModel):
    """健康檢查回傳格式"""

    status: str
    version: str


class ErrorResponse(BaseModel):
    """錯誤回傳格式"""

    detail: str
