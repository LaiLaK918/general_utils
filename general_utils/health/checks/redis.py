import aioredis  # type: ignore

from ...schemas.health import HealthStatus
from ..base import HealthCheckBase


class RedisHealth(HealthCheckBase):
    name = "redis"

    def __init__(self, url: str):  # noqa: D107
        self.url = url
        self._redis = None

    async def check(self):
        """Check Redis connectivity."""
        try:
            if not self._redis:
                self._redis = aioredis.from_url(self.url)
            pong = await self._redis.ping()
            return HealthStatus.OK, pong
        except Exception as e:
            return HealthStatus.ERROR, str(e)
