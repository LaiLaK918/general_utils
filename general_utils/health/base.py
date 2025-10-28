from abc import ABC, abstractmethod
from typing import Any

from ..schemas.health import HealthStatus


class HealthCheckBase(ABC):
    """Base class for all health checkers."""

    name: str

    @abstractmethod
    async def check(self) -> tuple[HealthStatus, Any]:
        """Return (status, detail)."""
        ...
