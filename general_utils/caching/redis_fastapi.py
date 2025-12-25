import dataclasses
import functools
import hashlib
import json
import logging  # noqa: TID251
from datetime import date, datetime
from enum import Enum
from typing import Any, Callable, Optional

import redis.asyncio as redis
from fastapi import Request
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class RedisCache:
    def __init__(self, redis_url: str, prefix: str = "cache", default_expire: int = 60):
        """
        Initialize Redis cache.

        Args:
            redis_url (str): The Redis connection URL.
            prefix (str): The prefix for cache.
            default_expire (str): Cache expiration time.

        Example:
            ```
        from contextlib import asynccontextmanager

        from fastapi import FastAPI, Request
        from pydantic import BaseModel

        from general_utils.caching.redis_fastapi import RedisCache

        cache = RedisCache(
            redis_url="redis://localhost:6379", prefix="myapp", default_expire=30
        )


        @asynccontextmanager
        async def lifespan(app: FastAPI):
            await cache.init()
            yield
            await cache.close()


        app = FastAPI(lifespan=lifespan)


        # GET cache normal
        @app.get("/time")
        @cache.cache_response(expire_seconds=10)
        async def get_time(request: Request):
            from datetime import datetime

            return {"time": datetime.utcnow().isoformat()}


        # Model for POST
        class InputData(BaseModel):
            value: int


        # POST cache by model_param
        @app.post("/compute")
        @cache.cache_response(expire_seconds=60, model_param="data")
        async def compute_result(request: Request, data: InputData):
            return {"result": data.value * 2}


        # Clear cache API
        @app.delete("/clear-cache")
        async def clear_all(pattern: str = "*"):
            deleted = await cache.clear_all_cache(pattern)
            return {"deleted": deleted}
        ```

        """
        self.redis_url = redis_url
        self.prefix = prefix
        self.default_expire = default_expire
        self.redis = None

    async def init(self):
        """Initialize Redis connection."""
        try:
            self.redis = await redis.from_url(
                self.redis_url, encoding="utf-8", decode_responses=True
            )
        except Exception as e:
            logger.warning(f"Failed to initialize Redis connection: {e}")
            self.redis = None

    async def close(self):
        """Close Redis connection."""
        if self.redis:
            await self.redis.close()

    def _serialize_to_json(self, obj: Any) -> str:
        """
        Serialize object to JSON string, handling complex types.

        Supports:
            - Pydantic BaseModel
            - dataclasses
            - Enum
            - datetime/date
            - Standard JSON types
        """

        def default_serializer(o):
            # Pydantic BaseModel
            if isinstance(o, BaseModel):
                return o.model_dump()
            # dataclass
            if dataclasses.is_dataclass(o):
                return dataclasses.asdict(o)
            # Enum
            if isinstance(o, Enum):
                return o.value
            # datetime/date
            if isinstance(o, datetime | date):
                return o.isoformat()
            # Set
            if isinstance(o, set):
                return list(o)
            raise TypeError(
                f"Object of type {type(o).__name__} is not JSON serializable"
            )

        return json.dumps(
            obj, default=default_serializer, ensure_ascii=False, sort_keys=True
        )

    def _hash_body(self, body: Any) -> str:
        """Hash body to create a unique key for POST/PUT."""
        body_str = self._serialize_to_json(body)
        return hashlib.sha256(body_str.encode("utf-8")).hexdigest()

    def _build_key(
        self,
        request: Request | None,
        custom_key: Optional[str] = None,
        body: Any = None,
    ) -> str:
        # If POST/PUT/PATCH and has body → hash into key
        if (
            request
            and isinstance(request, Request)
            and request.method in {"POST", "PUT", "PATCH"}
            and body is not None
        ):
            body_hash = self._hash_body(body)
            return f"{self.prefix}:{request.url.path}:{body_hash}"

        if custom_key and not body:
            return f"{self.prefix}:{custom_key}"

        if custom_key and body:
            body_hash = self._hash_body(body)
            return f"{self.prefix}:{custom_key}:{body_hash}"

        # Default GET key by path + query
        return f"{self.prefix}:{request.url.path}?{request.url.query}"

    def cache_response(
        self,
        expire_seconds: Optional[int] = None,
        key: Optional[str] = None,
        model_param: Optional[str] = None,
    ):
        """
        Decorator cache for FastAPI.
        - expire_seconds: TTL of the cache
        - key: custom cache key
        - model_param: name of the function parameter containing model/body (e.g., 'data').
        """

        def decorator(func: Callable):
            @functools.wraps(func)
            async def wrapper(*args, **kwargs):
                request: Request = None
                body_data = None

                # Lấy Request object
                for arg in args:
                    if isinstance(arg, Request):
                        request = arg
                        break
                if (
                    not request
                    and "request" in kwargs
                    and isinstance(kwargs["request"], Request)
                ):
                    request = kwargs["request"]

                # Lấy model/body để hash key (nếu cần)
                if model_param and model_param in kwargs:
                    body_data = kwargs[model_param]

                cache_key = self._build_key(request, key, body=body_data)

                # Try to get from cache with error handling
                try:
                    if self.redis:
                        cached = await self.redis.get(cache_key)
                        if cached:
                            return json.loads(cached)
                except Exception as e:
                    logger.warning(f"Redis get error for key {cache_key}: {e}")
                    # Continue to execute the function if cache fails

                # Execute the original function
                result = await func(*args, **kwargs)

                # Try to set cache with error handling
                try:
                    if self.redis:
                        await self.redis.setex(
                            cache_key,
                            expire_seconds or self.default_expire,
                            self._serialize_to_json(result),
                        )
                except Exception as e:
                    logger.warning(f"Redis set error for key {cache_key}: {e}")
                    # Don't fail if caching fails, just log and continue

                return result

            return wrapper

        return decorator

    async def clear_cache(self, key: str) -> int:
        """Clear cache for a specific key."""
        if self.redis:
            return await self.redis.delete(f"{self.prefix}:{key}")
        return 0

    async def clear_all_cache(self, pattern: str = "*") -> int:
        """Clear all cache matching the pattern."""
        if self.redis:
            keys = await self.redis.keys(f"{self.prefix}:{pattern}")
            if keys:
                return await self.redis.delete(*keys)
        return 0
