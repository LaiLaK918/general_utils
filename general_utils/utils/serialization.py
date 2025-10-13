import asyncio
import json
from typing import Any

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
        """
        Handle objects that aren't directly JSON serializable.

        NOTE: We purposefully return a *Python* object (dict/list/str/etc.)
        that json.dumps can then serialize - we do NOT return a JSON string
        here to avoid double-encoding (which would add extra quotes).
        """
        # Pydantic BaseModel -> dict
        if isinstance(obj, BaseModel):
            # Using model_dump ensures proper conversion of datetimes, enums, etc.
            return obj.model_dump(mode="json")

        # Sets / frozensets -> list
        if isinstance(obj, set | frozenset):
            return list(obj)

        # Bytes / bytearray -> decoded utf-8 (fallback to repr)
        if isinstance(obj, bytes | bytearray):
            try:
                return obj.decode("utf-8")
            except Exception:  # pragma: no cover - very edge case
                return repr(obj)

        # Exception -> structured dict
        if isinstance(obj, Exception):
            return {"error": str(obj), "error_type": type(obj).__name__}

        # Coroutines / generators (log their repr)
        if asyncio.iscoroutine(obj) or hasattr(obj, "__await__"):
            return f"<coroutine {obj.__class__.__name__}>"
        if hasattr(obj, "__iter__") and not isinstance(
            obj, str | bytes | dict | list | tuple
        ):
            # For other iterables, attempt list conversion (may still fail if infinite)
            try:
                return list(obj)
            except Exception:
                pass

        # User provided fallback (can raise its own TypeError which json will catch)
        fallback_serializer = getattr(_serialize_to_json, "_fallback_serializer", None)
        if fallback_serializer is not None:
            try:
                return fallback_serializer(obj)
            except Exception:  # If user fallback fails, continue to final error
                pass

        # Final fallback – string repr so we never completely fail here.
        return repr(obj)

    body_str = json.dumps(
        data,
        sort_keys=True,
        ensure_ascii=False,
        default=_default_serializer,
    )
    return body_str
