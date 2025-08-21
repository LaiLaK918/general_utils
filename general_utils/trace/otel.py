import asyncio
from functools import wraps
from typing import Any, Callable, Dict, Optional

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

from ..utils.log_common import build_logger

logger = build_logger(__name__)


def _serialize_to_json(data) -> Dict[str, Any]:
    """
    Convert arbitrary input into a JSON-serializable dictionary.

    The function guarantees a dict return type. If the underlying converted
    representation is already a dict, it is returned (with keys coerced to str).
    Otherwise the converted value is wrapped under the key "value".

    This keeps a uniform shape for downstream consumers that expect a mapping.

    Args:
        data: Arbitrary data to convert.

    Returns:
        dict: JSON-serializable dictionary representation.

    """
    fallback_serializer = getattr(_serialize_to_json, "_fallback_serializer", None)

    def convert(obj: Any) -> Any:
        if obj is None or isinstance(obj, str | int | float | bool):
            return obj
        if isinstance(obj, BaseModel):
            return obj.model_dump(mode="json")
        if isinstance(obj, dict):
            return {str(k): convert(v) for k, v in obj.items()}
        if isinstance(obj, list | tuple | set | frozenset):
            return [convert(v) for v in obj]
        if isinstance(obj, bytes | bytearray):
            try:
                return obj.decode("utf-8")
            except Exception:  # pragma: no cover
                return repr(obj)
        if isinstance(obj, Exception):
            return {"error": str(obj), "error_type": type(obj).__name__}
        if asyncio.iscoroutine(obj) or hasattr(obj, "__await__"):
            return f"<coroutine {obj.__class__.__name__}>"
        if hasattr(obj, "__iter__"):
            try:
                return [convert(v) for v in obj]
            except Exception:  # pragma: no cover
                pass
        if fallback_serializer is not None:
            try:
                return convert(fallback_serializer(obj))
            except Exception:  # pragma: no cover
                pass
        return repr(obj)

    converted = convert(data)
    if isinstance(converted, dict):
        # Ensure all keys are strings (JSON requirement)
        return {str(k): v for k, v in converted.items()}
    return {"value": converted}


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
