from enum import Enum
from typing import Optional

from pydantic import BaseModel


class HealthStatus(str, Enum):
    OK = "ok"
    DEGRADED = "degraded"
    ERROR = "error"


class HealthCheckComponent(BaseModel):
    status: HealthStatus
    detail: str


class HealthCheckResult(BaseModel):
    status: HealthStatus
    timestamp: float
    components: dict[str, HealthCheckComponent]
    stale: Optional[bool] = False


class CachedHealthCheckResult(BaseModel):
    time: float
    data: HealthCheckResult
