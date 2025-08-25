"""OpenTelemetry tracing utilities."""

from .otel import OTLPExporterSingleton, SpanProcessor

__all__ = ["OTLPExporterSingleton", "SpanProcessor"]
