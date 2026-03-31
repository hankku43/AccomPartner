from pydantic_settings import BaseSettings
from functools import lru_cache
from typing import List


class Settings(BaseSettings):
    # 模型相關路徑
    model_dir: str = ""
    ar_script_path: str = ""
    nar_script_path: str = ""

    # API 設定
    rate_limit: int = 5
    default_bpm: int = 120

    # CORS
    allowed_origins: List[str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache()
def get_settings() -> Settings:
    return Settings()
