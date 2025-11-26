import asyncio
import functools
from typing import Any, Callable, Dict, List, Optional

from langfuse import SpanLevel, get_client, propagate_attributes
from langfuse._internal.trace_context import TraceContext


def langfuse_trace(
    *,
    # start_as_current_span parameters
    trace_context: Optional[TraceContext] = None,
    name: Optional[str] = None,
    input: Any = None,
    output: Any = None,
    metadata: Any = None,
    version: Optional[str] = None,
    level: Optional[SpanLevel] = None,
    status_message: Optional[str] = None,
    end_on_exit: Optional[bool] = None,

    # propagate_attributes parameters
    user_id: Optional[str] = None,
    session_id: Optional[str] = None,
    pa_metadata: Optional[Dict[str, str]] = None,
    pa_version: Optional[str] = None,
    tags: Optional[List[str]] = None,
    as_baggage: bool = False,
):
    """
    Decorator to wrap a function call inside a Langfuse span,
    with optional propagate_attributes() context.

    If `name` is not provided, the wrapped function's name is used.
    """

    def decorator(func: Callable):
        span_name = name or func.__name__
        lf_client = get_client()

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            with lf_client.start_as_current_span(
                name=span_name,
                trace_context=trace_context,
                input=input,
                output=output,
                metadata=metadata,
                version=version,
                level=level,
                status_message=status_message,
                end_on_exit=end_on_exit,
            ) as span:

                with propagate_attributes(
                    user_id=user_id,
                    session_id=session_id,
                    metadata=pa_metadata,
                    version=pa_version,
                    tags=tags,
                    as_baggage=as_baggage
                ):
                    result = func(*args, **kwargs)

                    # If output not manually set, we set it here
                    try:
                        span.update_trace(output=result)
                    except Exception:
                        pass

                    return result

        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            with lf_client.start_as_current_span(
                name=span_name,
                trace_context=trace_context,
                input=input,
                output=output,
                metadata=metadata,
                version=version,
                level=level,
                status_message=status_message,
                end_on_exit=end_on_exit,
            ) as span:

                with propagate_attributes(
                    user_id=user_id,
                    session_id=session_id,
                    metadata=pa_metadata,
                    version=pa_version,
                    tags=tags,
                    as_baggage=as_baggage
                ):
                    result = await func(*args, **kwargs)

                    # update output
                    try:
                        span.update_trace(output=result)
                    except Exception:
                        pass

                    return result

        # Choose correct wrapper based on sync/async
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator
