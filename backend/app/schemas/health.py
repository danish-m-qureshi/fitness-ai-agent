from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field

ServiceHealthStatus = Literal["ok", "degraded", "unavailable", "disabled"]


class ServiceHealthResponse(BaseModel):
    service: str
    status: ServiceHealthStatus
    checked_at_utc: datetime
    details: dict[str, Any] = Field(default_factory=dict)


class HealthAggregateResponse(BaseModel):
    status: ServiceHealthStatus
    checked_at_utc: datetime
    services: dict[str, ServiceHealthResponse]
