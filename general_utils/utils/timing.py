import inspect
import os
import time
from functools import lru_cache, wraps

from .log_common import build_logger


@lru_cache(maxsize=1)
def get_timing_logger():
    """Cache default timing logger to avoid recreating handlers."""
    return build_logger("timing")


def _find_caller_info():
    """Find first non-internal frame (skip this file, site-packages, asyncio)."""
    frame = inspect.currentframe()
    while frame:
        info = inspect.getframeinfo(frame)
        fname = info.filename
        if (
            "timing_utils" not in fname
            and "site-packages" not in fname
            and "/asyncio/" not in fname
            and not fname.startswith("<")
        ):
            rel_path = os.path.relpath(fname, start=os.getcwd())
            return rel_path, info.lineno
        frame = frame.f_back
    return "unknown", -1


def _log_time(f, start_time, logger, level: str = "info"):
    """Log elapsed time with actual call site of decorated function."""
    elapsed = time.time() - start_time

    # --- NEW: find frame where the decorated function was called ---
    frame = inspect.currentframe()
    # đi ngược 2 bước: current (_log_time) -> wrapper -> caller
    frame = (
        frame.f_back.f_back if frame and frame.f_back and frame.f_back.f_back else None
    )

    path, lineno = "unknown", -1
    while frame:
        info = inspect.getframeinfo(frame)
        fname = info.filename
        if (
            "site-packages" not in fname
            and "timing_utils" not in fname
            and "asyncio" not in fname
            and not fname.startswith("<")
        ):
            path = os.path.relpath(fname, start=os.getcwd())
            lineno = info.lineno
            break
        frame = frame.f_back

    module = inspect.getmodule(f)
    modname = module.__name__ if module else "unknown"
    qualname = getattr(f, "__qualname__", f.__name__)

    msg = (
        f"\033[92m[⏱ {elapsed:7.3f}s]\033[0m "
        f"{modname}.{qualname} "
        f"(\033[96m{path}:{lineno}\033[0m)"
    )
    getattr(logger, level, logger.info)(msg)


def measure_time(func=None, *, logger=None, is_async=False, level: str = "info"):
    """
    Decorator to measure execution time for sync or async functions.

    Args:
        func: function to wrap (can be omitted for parameterized decorator)
        logger: optional custom logger (default: cached timing logger)
        is_async: True if function is async
        level: log level, e.g., "info", "debug"

    Usage:
        @measure_time
        def foo(): ...

        @measure_time(is_async=True)
        async def bar(): ...

        @measure_time(logger=my_logger, level="debug")
        def custom(): ...

    """

    def decorator(f):
        nonlocal logger
        logger = logger or get_timing_logger()

        if is_async:

            @wraps(f)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                result = await f(*args, **kwargs)
                _log_time(f, start, logger, level)
                return result

            return async_wrapper
        else:

            @wraps(f)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                result = f(*args, **kwargs)
                _log_time(f, start, logger, level)
                return result

            return sync_wrapper

    return decorator if func is None else decorator(func)


# Syntactic sugar for readability
def measure_time_async(func=None, **kwargs):
    """Decorator to measure execution time for async functions."""
    return measure_time(func, is_async=True, **kwargs)
