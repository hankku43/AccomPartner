"""
main.py
-------
FastAPI 應用程式入口點。

負責：
  1. 建立 FastAPI 實例（含 metadata）
  2. 掛載 CORS 中介層
  3. 掛載 Rate Limiter（slowapi）
  4. 註冊所有路由器
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

import asyncio
from app.core.cleanup import start_cleanup_task
from app.core.config import get_settings
from app.core.limiter import limiter
from app.routers import generate

settings = get_settings()

app = FastAPI(
    title="AI 伴奏生成實驗室 API",
    description=(
        "接收旋律資料（JSON 或 MIDI 上傳），"
        "呼叫 AR / NAR 模型生成伴奏，回傳 MIDI 二進位流。"
    ),
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc",
)

# ── Rate Limiter ─────────────────────────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(
    RateLimitExceeded,
    _rate_limit_exceeded_handler,  # 自動回傳 429 JSON
)

# ── CORS ─────────────────────────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["Content-Type"],
)

# ── 路由器 ───────────────────────────────────────────────────────────────────
app.include_router(generate.router)

@app.on_event("startup")
async def startup_event():
    # 啟動非同步背景清理任務，確保長期運行時磁碟空間不被塞爆
    asyncio.create_task(start_cleanup_task())
