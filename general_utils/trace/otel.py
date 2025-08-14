import asyncio
import json
from functools import wraps
from typing import Optional

from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.trace import get_tracer_provider, set_tracer_provider
from pydantic import BaseModel


def _serialize_to_json(data) -> str:
    """
    Safely serialize data to JSON string.

    Args:
        data: The data to serialize.

    Returns:
        str: JSON string representation of the data.
    """
    if isinstance(data, BaseModel):
        body_str = data.model_dump_json()
    else:
        body_str = json.dumps(data, sort_keys=True, ensure_ascii=False)
    return body_str


class OTLPExporterSingleton:
    _instance: Optional[OTLPSpanExporter] = None

    @classmethod
    def get_instance(cls, endpoint: str = "grpc://otel-collector:4137", insecure: bool = False) -> OTLPSpanExporter:
        if cls._instance is None:
            if 'grpc://' not in endpoint:
                raise ValueError("OTLP endpoint must start with 'grpc://'")
            cls._instance = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
        return cls._instance


class SpanProcessor:
    def __init__(self, service_name: str, oltp_endpoint: str = "grpc://otel-collector:4137", oltp_insecure: bool = False):
        self.service_name = service_name
        self.oltp_endpoint = oltp_endpoint
        self.oltp_insecure = oltp_insecure

        # Set up resource and tracer provider
        resource = Resource.create({SERVICE_NAME: self.service_name})
        set_tracer_provider(TracerProvider(resource=resource))

        # Get singleton exporter
        exporter = OTLPExporterSingleton.get_instance(
            endpoint=self.oltp_endpoint, insecure=self.oltp_insecure)

        # Add batch span processor
        span_processor = BatchSpanProcessor(exporter)
        get_tracer_provider().add_span_processor(span_processor)

    def log_trace(self, span_name: str, prefix: str = "langfuse.observation"):
        """
        Decorator to trace a function with OpenTelemetry and log input/output.

        Args:
            span_name (str): The name of the span to create.
            prefix (str): Attribute prefix for input/output logging.

        Returns:
            Callable: The decorated function with tracing capabilities.
        """

        def decorator(func):
            tracer = get_tracer_provider().get_tracer(self.service_name)

            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def wrapper(*args, **kwargs):
                    with tracer.start_as_current_span(span_name) as span:
                        # Log input data
                        input_data = {"args": args, "kwargs": kwargs}
                        span.set_attribute(f"{prefix}.input", _serialize_to_json(input_data))

                        try:
                            result = await func(*args, **kwargs)
                            span.set_attribute(f"{prefix}.output", _serialize_to_json(result))
                            return result
                        except Exception as e:
                            error_data = {"error": str(e), "error_type": type(e).__name__}
                            span.set_attribute(f"{prefix}.output", _serialize_to_json(error_data))
                            raise

            else:

                @wraps(func)
                def wrapper(*args, **kwargs):
                    with tracer.start_as_current_span(span_name) as span:
                        # Log input data
                        input_data = {"args": args, "kwargs": kwargs}
                        span.set_attribute(f"{prefix}.input", _serialize_to_json(input_data))

                        try:
                            result = func(*args, **kwargs)
                            span.set_attribute(f"{prefix}.output", _serialize_to_json(result))
                            return result
                        except Exception as e:
                            error_data = {"error": str(e), "error_type": type(e).__name__}
                            span.set_attribute(f"{prefix}.output", _serialize_to_json(error_data))
                            raise

            return wrapper

        return decorator

