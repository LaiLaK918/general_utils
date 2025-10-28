from celery import Celery

from ...schemas.health import HealthStatus
from ..base import HealthCheckBase


class CeleryHealth(HealthCheckBase):
    name = "celery"

    def __init__(self, app: Celery):  # noqa: D107
        self.app = app

    async def check(self):
        """Check Celery connectivity."""
        try:
            res = self.app.control.ping(timeout=2)
            if res:
                return HealthStatus.OK, f"{len(res)} workers"
            return HealthStatus.DEGRADED, "no workers"
        except Exception as e:
            return HealthStatus.ERROR, str(e)
