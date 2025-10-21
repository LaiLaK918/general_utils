import inspect
import json
import os
import time
from functools import lru_cache, wraps
from typing import Callable, Optional

from .log_common import build_logger


@lru_cache(maxsize=1)
def get_timing_logger():
    """Cache the default logger to avoid handler duplication."""
    return build_logger("timing")


def _find_call_site():
    """Find the frame of the actual function call (outside timing_v2)."""
    frame = inspect.currentframe()
    # move up: current (_find_call_site) → _log_time → wrapper → caller
    if frame:
        frame = frame.f_back.f_back.f_back
    while frame:
        info = inspect.getframeinfo(frame)
        fname = info.filename
        if (
            "timing_v2" not in fname
            and "site-packages" not in fname
            and "asyncio" not in fname
            and not fname.startswith("<")
        ):
            rel_path = os.path.relpath(fname, start=os.getcwd())
            return rel_path, info.lineno
        frame = frame.f_back
    return "unknown", -1


def _log_time(
    f,
    start: float,
    logger,
    level: str,
    tag: Optional[str],
    threshold_warning: Optional[float],
    elapsed: float,
    path: str,
    lineno: int,
):
    """Logs execution time with accurate call site info."""
    module = inspect.getmodule(f)
    modname = module.__name__ if module else "unknown"
    qualname = getattr(f, "__qualname__", f.__name__)

    emoji = "⚠️" if threshold_warning and elapsed > threshold_warning else "⏱"
    color = "\033[93m" if emoji == "⚠️" else "\033[92m"

    if tag:
        if isinstance(tag, list | tuple):
            tag_text = "[" + "|".join(map(str, tag)) + "] "
        else:
            tag_text = f"[{tag}] "
    else:
        tag_text = ""

    msg = (
        f"{color}[{emoji} {elapsed:7.3f}s]\033[0m "
        f"{tag_text}{modname}.{qualname} "
        f"(\033[96m{path}:{lineno}\033[0m)"
    )

    if threshold_warning and elapsed > threshold_warning:
        logger.warning(msg)
    else:
        getattr(logger, level, logger.info)(msg)


def measure_time(
    func=None,
    *,
    logger=None,
    is_async=False,
    level: str = "info",
    is_return_measured_time: bool = False,
    threshold_warning: Optional[float] = None,
    on_complete_callback: Optional[
        Callable[[Callable, tuple, dict, float], None]
    ] = None,
    record_to: Optional[str] = None,
    metric_collector: Optional[Callable[[str, float], None]] = None,
    tag: Optional[str] = None,
):
    """
    Advanced timing decorator with logging, metrics, callbacks, and warnings.

    Args:
        logger: Optional custom logger. Default = cached timing logger.
        is_async: Set True for async functions.
        level: Log level for normal timing logs.
        is_return_measured_time: If True, returns (result, elapsed_time).
        threshold_warning: Log warning if elapsed_time > threshold (seconds).
        on_complete_callback: Callback executed after completion: fn, args, kwargs, elapsed.
        record_to: Path to JSONL file for structured timing logs.
        metric_collector: Function to collect (func_name, elapsed_time) metrics.
        tag: Optional label for grouping logs (e.g., "db", "ml", "api").

    """

    def decorator(f):
        nonlocal logger
        logger = logger or get_timing_logger()

        def _record_metrics_and_logs(
            start, result, args, kwargs, elapsed, path, lineno
        ):
            # log to console/file
            _log_time(
                f, start, logger, level, tag, threshold_warning, elapsed, path, lineno
            )

            # optional: callback
            if on_complete_callback:
                try:
                    on_complete_callback(f, args, kwargs, elapsed)
                except Exception as e:
                    logger.warning(f"[timing_v2] Callback failed: {e}")

            # optional: metric collector
            if metric_collector:
                try:
                    metric_collector(f.__qualname__, elapsed)
                except Exception as e:
                    logger.warning(f"[timing_v2] Metric collector failed: {e}")

            # optional: structured record
            if record_to:
                try:
                    with open(record_to, "a", encoding="utf-8") as fp:
                        json.dump(
                            {
                                "function": f.__qualname__,
                                "elapsed": elapsed,
                                "tag": tag,
                                "path": path,
                                "lineno": lineno,
                                "timestamp": time.time(),
                            },
                            fp,
                            ensure_ascii=False,
                        )
                        fp.write("\n")
                except Exception as e:
                    logger.warning(f"[timing_v2] Failed to record log: {e}")

        if is_async:

            @wraps(f)
            async def async_wrapper(*args, **kwargs):
                start = time.time()
                result = await f(*args, **kwargs)
                elapsed = time.time() - start
                path, lineno = _find_call_site()
                _record_metrics_and_logs(
                    start, result, args, kwargs, elapsed, path, lineno
                )
                return (result, elapsed) if is_return_measured_time else result

            return async_wrapper

        else:

            @wraps(f)
            def sync_wrapper(*args, **kwargs):
                start = time.time()
                result = f(*args, **kwargs)
                elapsed = time.time() - start
                path, lineno = _find_call_site()
                _record_metrics_and_logs(
                    start, result, args, kwargs, elapsed, path, lineno
                )
                return (result, elapsed) if is_return_measured_time else result

            return sync_wrapper

    return decorator if func is None else decorator(func)
