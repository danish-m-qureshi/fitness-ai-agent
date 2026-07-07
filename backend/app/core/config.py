from functools import lru_cache
from typing import Any

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "Fitness AI Agent"
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = True
    docs_enabled: bool = True
    api_v1_prefix: str = "/api/v1"
    log_level: str = "INFO"
    database_url: str = (
        "postgresql+psycopg://fitness_user:fitness_password@db:5432/fitness_ai_agent"
    )
    llm_provider: str = "ollama"
    ollama_base_url: str = "http://host.docker.internal:11434"
    vision_model: str = "qwen3-vl:8b"
    ollama_timeout_seconds: float = 60.0
    qdrant_host: str = "qdrant"
    qdrant_port: int = 6333
    qdrant_collection_name: str = "fitness_memory"
    embedding_model_name: str = "nomic-embed-text"
    meal_image_upload_dir: str = "storage/uploads/meals"
    max_image_upload_bytes: int = 8 * 1024 * 1024
    whatsapp_provider: str = "mock"
    whatsapp_meta_access_token: str | None = None
    whatsapp_meta_phone_number_id: str | None = None
    whatsapp_meta_verify_token: str | None = None
    whatsapp_meta_api_base_url: str = "https://graph.facebook.com"
    whatsapp_meta_api_version: str = "v20.0"
    smtp_host: str | None = None
    smtp_port: int = 587
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_from_email: str | None = None
    smtp_use_tls: bool = True
    summary_email_enabled: bool = False
    summary_schedule_enabled: bool = False
    summary_schedule_hour: int = 20
    summary_schedule_minute: int = 0
    summary_schedule_timezone: str = "UTC"
    api_key_enabled: bool = False
    api_key: str | None = None
    redis_url: str | None = None

    @field_validator("debug", mode="before")
    @classmethod
    def normalize_debug(cls, value: Any) -> Any:
        if isinstance(value, str):
            normalized = value.strip().lower()
            if normalized in {"release", "prod", "production"}:
                return False
            if normalized in {"debug", "dev", "development"}:
                return True

        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )


@lru_cache
def get_settings() -> Settings:
    return Settings()
