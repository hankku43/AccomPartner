from pydantic_settings import BaseSettings, SettingsConfigDict
from functools import lru_cache
from typing import List, Union
from pydantic import field_validator


class Settings(BaseSettings):
    # 模型相關路徑
    model_dir: str = ""

    # API 設定
    rate_limit: int = 10
    default_bpm: int = 120

    # CORS
    allowed_origins: Union[List[str], str] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def assemble_cors_origins(cls, v: Union[str, List[str]]) -> Union[List[str], str]:
        if isinstance(v, str) and not v.startswith("["):
            return [i.strip() for i in v.split(",")]
        return v

    # pydantic-settings v2 推薦寫法（取代棄用的 class Config）
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )


@lru_cache()
def get_settings() -> Settings:
    return Settings()
