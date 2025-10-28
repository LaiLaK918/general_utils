import asyncpg  # type: ignore

from ...schemas.health import HealthStatus
from ..base import HealthCheckBase


class PostgresHealth(HealthCheckBase):
    name = "postgres"

    def __init__(self, dsn: str):  # noqa: D107
        self.dsn = dsn

    async def check(self):
        """Check PostgreSQL connectivity."""
        try:
            conn = await asyncpg.connect(self.dsn)
            await conn.execute("SELECT 1;")
            await conn.close()
            return HealthStatus.OK, "connected"
        except Exception as e:
            return HealthStatus.ERROR, str(e)
