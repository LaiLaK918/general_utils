from minio import Minio

from ...schemas.health import HealthStatus
from ..base import HealthCheckBase


class MinioHealth(HealthCheckBase):
    name = "minio"

    def __init__(self, client: Minio):  # noqa: D107
        self.client = client

    async def check(self):
        """Check MinIO connectivity."""
        try:
            if self.client.list_buckets():
                return HealthStatus.OK, "accessible"
            return HealthStatus.DEGRADED, "empty bucket list"
        except Exception as e:
            return HealthStatus.ERROR, str(e)
