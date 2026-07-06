from typing import Any

from pydantic import BaseModel, Field


class DebugConfigResponse(BaseModel):
    environment: str
    debug: bool
    api_prefix: str
    api_key_enabled: bool
    database: dict[str, Any] = Field(default_factory=dict)
    qdrant: dict[str, Any] = Field(default_factory=dict)
    ollama: dict[str, Any] = Field(default_factory=dict)
    email: dict[str, Any] = Field(default_factory=dict)
    scheduler: dict[str, Any] = Field(default_factory=dict)


class DebugServicesResponse(BaseModel):
    services: dict[str, str]
