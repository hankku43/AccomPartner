"""
model_router.py
---------------
根據前端傳入的 mode 字串，分派到對應的推理服務模組。

支援模式：
    "onestage": oneStage_service.generate,
    "twostagestd": twoStage_service.generate_std,
    "twostagebar": twoStage_service.generate_bar,
    "twostagenar": twoStage_service.generate_nar,

後續新增模式只需在此處加入 mapping 即可，無需修改其他層。
"""

from typing import Callable, Awaitable
from fastapi import HTTPException

from app.services import oneStage_service, twoStage_service

# mode 字串 → 推理函數的對應表
_SERVICE_MAP: dict[str, Callable[[bytes], Awaitable[bytes]]] = {
    "onestage": oneStage_service.generate,
    "twostagestd": twoStage_service.generate_std,
    "twostagebar": twoStage_service.generate_bar,
    "twostagenar": twoStage_service.generate_nar,
}

SUPPORTED_MODES = list(_SERVICE_MAP.keys())


def get_service(mode: str) -> Callable[[bytes], Awaitable[bytes]]:
    """
    根據 mode 字串回傳對應的推理函數。

    Args:
        mode: 模式名稱（大小寫不敏感）

    Returns:
        async callable: (melody_midi_bytes: bytes) -> bytes

    Raises:
        HTTPException 400: 不支援的模式
    """
    normalized = mode.lower().strip().replace("-", "")
    service_fn = _SERVICE_MAP.get(normalized)

    if service_fn is None:
        raise HTTPException(
            status_code=400,
            detail=f"不支援的模式：'{mode}'。可用模式：{SUPPORTED_MODES}",
        )

    return service_fn
