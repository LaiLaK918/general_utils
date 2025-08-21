import asyncio
import json
from functools import wraps
from typing import Any, Callable, Optional

try:
    from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
    from opentelemetry.sdk.resources import SERVICE_NAME, Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.trace import get_tracer_provider, set_tracer_provider

    OTEL_AVAILABLE = True
except ImportError:
    OTEL_AVAILABLE = False


from pydantic import BaseModel


def _serialize_to_json(data) -> str:
    """
    Safely serialize data to JSON string, with optional fallback for custom types.

    Args:
        data: The data to serialize.
        fallback_serializer (Optional[Callable]): Function to handle non-serializable types.

    Returns:
        str: JSON string representation of the data.

    """

    def _default_serializer(obj: Any) -> Any:
        if isinstance(data, BaseModel):
            return data.model_dump_json()
        if fallback_serializer is not None:
            return fallback_serializer(obj)
        raise TypeError(f"Object of type {type(obj).__name__} is not JSON serializable")

    fallback_serializer = getattr(_serialize_to_json, "_fallback_serializer", None)

    try:
        body_str = json.dumps(
            data, sort_keys=True, ensure_ascii=False, default=_default_serializer
        )
    except TypeError as e:
        if fallback_serializer is not None:
            body_str = json.dumps(
                data,
                sort_keys=True,
                ensure_ascii=False,
                default=fallback_serializer,
            )
        else:
            raise e
    return body_str


def set_serialize_fallback(fallback_func: Callable[[Any], dict]) -> None:
    """
    Set a fallback serializer function for _serialize_to_json.

    Args:
        fallback_func (Callable): Function to handle non-serializable types.

    """
    _serialize_to_json._fallback_serializer = fallback_func


class OTLPExporterSingleton:
    """Singleton class for OTLP span exporter."""

    _instance: Optional["OTLPSpanExporter"] = None

    @classmethod
    def get_instance(
        cls, endpoint: str = "grpc://otel-collector:4137", insecure: bool = False
    ) -> "OTLPSpanExporter":
        """
        Get singleton instance of OTLP span exporter.

        Args:
            endpoint: OTLP endpoint URL
            insecure: Whether to use insecure connection

        Returns:
            OTLPSpanExporter: The singleton instance

        Raises:
            ImportError: If OpenTelemetry is not available
            ValueError: If endpoint format is invalid

        """
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry is not available. Install with: pip install general-utils[trace]"
            )

        if cls._instance is None:
            if "grpc://" not in endpoint:
                raise ValueError("OTLP endpoint must start with 'grpc://'")
            cls._instance = OTLPSpanExporter(endpoint=endpoint, insecure=insecure)
        return cls._instance


class SpanProcessor:
    """
    OpenTelemetry span processor for tracing.

    Args:
        service_name: Name of the service
        oltp_endpoint: OTLP endpoint URL
        oltp_insecure: Whether to use insecure connection
        serialize_fallback: Optional callable for custom serialization fallback

    """

    def __init__(
        self,
        service_name: str,
        oltp_endpoint: str = "grpc://otel-collector:4137",
        oltp_insecure: bool = False,
        serialize_fallback: Optional[Callable[[Any], dict]] = None,
    ):
        """
        Initialize span processor with OpenTelemetry configuration.

        Args:
            service_name: Name of the service
            oltp_endpoint: OTLP endpoint URL
            oltp_insecure: Whether to use insecure connection
            serialize_fallback: Optional callable for custom serialization fallback

        Raises:
            ImportError: If OpenTelemetry is not available
            ValueError: If endpoint format is invalid

        Example:
            To use a custom serialization fallback, define a function like this:

            def custom_fallback_serializer(obj: Any) -> dict:
                return {"error": "Unable to serialize", "type": type(obj).__name__}

            Then, pass it to the SpanProcessor:

            processor = SpanProcessor(
                service_name="my_service",
                serialize_fallback=custom_fallback_serializer
            )

        """
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry is not available. Install with: pip install general-utils[trace]"
            )

        self.service_name = service_name
        self.oltp_endpoint = oltp_endpoint
        self.oltp_insecure = oltp_insecure

        # Support custom serialization fallback from parameter
        if serialize_fallback:
            set_serialize_fallback(serialize_fallback)

        # Set up resource and tracer provider
        resource = Resource.create({SERVICE_NAME: self.service_name})
        set_tracer_provider(TracerProvider(resource=resource))

        # Get singleton exporter
        exporter = OTLPExporterSingleton.get_instance(
            endpoint=self.oltp_endpoint, insecure=self.oltp_insecure
        )

        # Add batch span processor
        span_processor = BatchSpanProcessor(exporter)
        get_tracer_provider().add_span_processor(span_processor)

    def log_trace(
        self,
        span_name: str,
        prefix: str = "langfuse.observation",
        log_input: bool = True,
        log_output: bool = True,
    ):
        """
        Decorator to trace a function with OpenTelemetry and log input/output.

        Args:
            span_name (str): The name of the span to create.
            prefix (str): Attribute prefix for input/output logging.
            log_input (bool): Whether to log function input arguments. Default True.
            log_output (bool): Whether to log function output/return value. Default True.

        Returns:
            Callable: The decorated function with tracing capabilities.

        Raises:
            ImportError: If OpenTelemetry is not available

        """
        if not OTEL_AVAILABLE:
            raise ImportError(
                "OpenTelemetry is not available. Install with: pip install general-utils[trace]"
            )

        def decorator(func):
            tracer = get_tracer_provider().get_tracer(self.service_name)

            if asyncio.iscoroutinefunction(func):

                @wraps(func)
                async def wrapper(*args, **kwargs):
                    with tracer.start_as_current_span(span_name) as span:
                        if log_input:
                            input_data = {"args": args, "kwargs": kwargs}
                            span.set_attribute(
                                f"{prefix}.input", _serialize_to_json(input_data)
                            )

                        try:
                            result = await func(*args, **kwargs)
                            if log_output:
                                span.set_attribute(
                                    f"{prefix}.output", _serialize_to_json(result)
                                )
                            return result
                        except Exception as e:
                            error_data = {
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                            if log_output:
                                span.set_attribute(
                                    f"{prefix}.output", _serialize_to_json(error_data)
                                )
                            raise

            else:

                @wraps(func)
                def wrapper(*args, **kwargs):
                    with tracer.start_as_current_span(span_name) as span:
                        if log_input:
                            input_data = {"args": args, "kwargs": kwargs}
                            span.set_attribute(
                                f"{prefix}.input", _serialize_to_json(input_data)
                            )

                        try:
                            result = func(*args, **kwargs)
                            if log_output:
                                span.set_attribute(
                                    f"{prefix}.output", _serialize_to_json(result)
                                )
                            return result
                        except Exception as e:
                            error_data = {
                                "error": str(e),
                                "error_type": type(e).__name__,
                            }
                            if log_output:
                                span.set_attribute(
                                    f"{prefix}.output", _serialize_to_json(error_data)
                                )
                            raise

            return wrapper

        return decorator
