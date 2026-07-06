from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

MemoryType = Literal[
    "meal",
    "workout",
    "goal",
    "daily_summary",
    "user_preference",
    "body_weight_log",
    "nutrition_insight",
    "agent_note",
]


class MemoryCreate(BaseModel):
    user_id: int = Field(..., ge=1)
    memory_type: MemoryType
    content: str = Field(..., min_length=1, max_length=5000)
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_table: str | None = Field(default=None, max_length=100)
    source_id: int | str | None = None


class MemorySearchRequest(BaseModel):
    user_id: int = Field(..., ge=1)
    query: str = Field(..., min_length=1, max_length=2000)
    limit: int = Field(default=5, ge=1, le=20)
    memory_type: MemoryType | None = None


class MemoryResponse(BaseModel):
    memory_id: str
    user_id: int
    memory_type: MemoryType
    content: str
    metadata: dict[str, Any] = Field(default_factory=dict)
    source_table: str | None = None
    source_id: int | str | None = None
    created_at: datetime
    score: float | None = None


class MemorySearchResponse(BaseModel):
    results: list[MemoryResponse] = Field(default_factory=list)
