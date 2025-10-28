import pulsar

from ...schemas.health import HealthStatus
from ..base import HealthCheckBase


class PulsarHealth(HealthCheckBase):
    name = "pulsar"

    def __init__(self, url: str):  # noqa: D107
        self.url = url

    async def check(self):
        """Check Pulsar connectivity."""
        try:
            client = pulsar.Client(self.url)
            client.close()
            return HealthStatus.OK, "connected"
        except Exception as e:
            return HealthStatus.ERROR, str(e)
