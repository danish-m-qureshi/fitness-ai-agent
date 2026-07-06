from datetime import datetime
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

GoalStatus = Literal["active", "completed", "paused", "cancelled"]


class GoalCreate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    title: str = Field(..., min_length=1, max_length=150)
    description: str | None = None
    target_value: float | None = None
    unit: str | None = Field(default=None, max_length=50)
    status: GoalStatus = "active"


class GoalUpdate(BaseModel):
    user_id: int | None = Field(default=None, ge=1)
    title: str = Field(default=None, min_length=1, max_length=150)
    description: str | None = None
    target_value: float | None = None
    unit: str | None = Field(default=None, max_length=50)
    status: GoalStatus = None


class GoalResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    title: str
    description: str | None
    target_value: float | None
    unit: str | None
    status: str
    created_at: datetime
    updated_at: datetime
