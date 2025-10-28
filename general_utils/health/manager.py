import asyncio
import time
from typing import Dict, List, Optional

import loguru

from ..schemas.health import HealthStatus
from ..utils.log_common import build_logger
from .base import HealthCheckBase


class HealthManager:
    """
    Asynchronous Health Manager with:
      - Dependency registration
      - Caching
      - Periodic background monitoring
      - Structured logging.

    Usage:
        ```python
        from fastapi import FastAPI
        import logging
        from core.health.manager import HealthManager
        from core.health.checks import postgres, redis

        logger = logging.getLogger("uvicorn")

        app = FastAPI()

        health = HealthManager(
            checks=[
                postgres.PostgresHealth("postgresql://user:pass@localhost/db"),
                redis.RedisHealth("redis://localhost:6379"),
            ],
            cache_ttl=20,
            interval=30,
            logger=logger,
        )

        @app.on_event("startup")
        async def startup():
            asyncio.create_task(health.start_background_monitor())

        @app.get("/health/live")
        async def live():
            return {"status": "alive"}

        @app.get("/health/ready")
        async def ready():
            return health.get_cached()
        ```
    """

    def __init__(
        self,
        checks: List[HealthCheckBase],
        cache_ttl: int = 15,
        interval: int = 30,
        logger: Optional[loguru.Logger] = None,
    ):
        """
        Initialize HealthManager.

        Args:
            checks (List[HealthCheckBase]): List of health check instances.
            cache_ttl (int): Time-to-live for cached results in seconds.
            interval (int): Interval between background checks in seconds.
            logger (Optional[loguru.Logger]): Logger instance for structured logging.

        """
        self.checks = checks
        self.cache_ttl = cache_ttl
        self.interval = interval
        self._cache: Dict[str, any] = {"time": 0, "data": {}}
        self._running = False
        self.logger = logger or build_logger("healthcheck")

    async def run_checks(self) -> Dict[str, any]:
        """Run all checks once and update cache."""
        results = {}
        tasks = [check.check() for check in self.checks]
        responses = await asyncio.gather(*tasks, return_exceptions=True)

        for checker, result in zip(self.checks, responses):
            if isinstance(result, Exception):
                results[checker.name] = {
                    "status": HealthStatus.ERROR,
                    "detail": str(result),
                }
                self.logger.error(f"[{checker.name}] failed: {result}")
            else:
                status, detail = result
                results[checker.name] = {"status": status, "detail": detail}

                if status == HealthStatus.ERROR:
                    self.logger.error(f"[{checker.name}] ❌ {detail}")
                elif status == HealthStatus.DEGRADED:
                    self.logger.warning(f"[{checker.name}] ⚠️ degraded: {detail}")
                else:
                    self.logger.debug(f"[{checker.name}] ✅ ok")

        overall = (
            HealthStatus.OK
            if all(v["status"] == HealthStatus.OK for v in results.values())
            else HealthStatus.DEGRADED
        )

        summary = {
            "status": overall,
            "timestamp": time.time(),
            "components": results,
        }
        self._cache = {"time": time.time(), "data": summary}
        return summary

    def get_cached(self) -> Dict[str, any]:
        """Return cached result if available."""
        if time.time() - self._cache["time"] > self.cache_ttl:
            # stale data marker
            self._cache["data"]["status"] = HealthStatus.DEGRADED
            self._cache["data"]["stale"] = True
        return self._cache["data"]

    async def start_background_monitor(self):
        """Run forever, periodically updating cache."""
        if self._running:
            self.logger.warning("Health monitor already running.")
            return
        self._running = True
        self.logger.info(
            f"🔄 Starting background health monitor (interval={self.interval}s)..."
        )

        while True:
            try:
                await self.run_checks()
            except Exception as e:
                self.logger.exception(f"Health monitor crashed: {e}")
            await asyncio.sleep(self.interval)
