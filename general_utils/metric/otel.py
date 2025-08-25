from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.instrumentation.system_metrics import SystemMetricsInstrumentor
from opentelemetry.metrics import set_meter_provider
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import SERVICE_NAME, Resource


def setup_metrics(service_name: str, otlp_endpoint: str = "grpc://otel-collector:4137", otlp_insecure: bool = False):
    """
    Set up OpenTelemetry metrics export to OTLP endpoint.

    This is separate from Prometheus metrics but allows sending
    the same metrics to the OpenTelemetry collector.
    """
    # Create a resource to identify our service
    resource = Resource.create({SERVICE_NAME: service_name})

    # Configure OpenTelemetry metrics exporter
    otlp_exporter = OTLPMetricExporter(
        endpoint=otlp_endpoint + "/v1/metrics", insecure=otlp_insecure
    )
    reader = PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=5000)
    meter_provider = MeterProvider(resource=resource, metric_readers=[reader])
    set_meter_provider(meter_provider)

    SystemMetricsInstrumentor().instrument()