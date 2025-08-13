<div align="center">

# general-utils

Composable Python utilities for everyday backend work: Argon2 password helpers, Redis + FastAPI response caching, YAML‑backed dynamic Pydantic settings, structured logging (Loguru), environment variable access, and execution time (sync & async) decorators.

</div>

## ✨ Features

- Authentication helpers: Simple Argon2 password hashing & verification (`general_utils.auth.hash_password`, `verify_credential`).
- Response caching decorator for FastAPI with Redis (GET + POST/PUT hashing of bodies) and easy cache clearing.
- YAML configuration system built on top of Pydantic Settings: auto template generation, hot reload when files change, layered sources.
- Structured logging via Loguru with configurable verbosity and rotating file output helpers.
- Execution timing decorators for sync & async functions with automatic call‑site resolution.
- Safe environment variable accessor that validates presence & non‑empty values.
- Lightweight, no framework lock‑in—import only what you need.

## 🧩 Install

Requires Python 3.12+.

```bash
pip install git+https://github.com/LaiLaK918/general-utils.git
```

Or using uv:

```bash
uv add git+https://github.com/LaiLaK918/general-utils.git
```

## 🗂 Package Overview

| Module                                | Purpose                                                |
| ------------------------------------- | ------------------------------------------------------ |
| `general_utils.auth`                  | Argon2 password hashing & verification                 |
| `general_utils.caching.redis_fastapi` | Redis response cache decorator for FastAPI             |
| `general_utils.config`                | YAML + Pydantic dynamic settings & template generation |
| `general_utils.utils.log_common`      | Loguru logger factory & logging helpers                |
| `general_utils.utils.timing`          | Execution time decorators (sync & async)               |
| `general_utils.utils.env`             | Strict environment variable retrieval                  |

## 🔐 Auth Helpers

```python
from general_utils.auth import hash_password, verify_credential

hashed = hash_password("SuperSecret123!")
assert verify_credential("SuperSecret123!", hashed) is True
```

## ⚡ FastAPI Redis Response Cache

Cache GET responses (path+query) and POST/PUT/PATCH responses (path + hashed body or model field).

```python
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from pydantic import BaseModel
from general_utils.caching.redis_fastapi import RedisCache

cache = RedisCache(redis_url="redis://localhost:6379", prefix="myapp", default_expire=30)

@asynccontextmanager
async def lifespan(app: FastAPI):
	await cache.init()
	yield
	await cache.close()

app = FastAPI(lifespan=lifespan)

@app.get("/time")
@cache.cache_response(expire_seconds=10)
async def get_time(request: Request):
	from datetime import datetime
	return {"time": datetime.utcnow().isoformat()}

class InputData(BaseModel):
	value: int

@app.post("/compute")
@cache.cache_response(expire_seconds=60, model_param="data")
async def compute_result(request: Request, data: InputData):
	return {"result": data.value * 2}

@app.delete("/clear-cache")
async def clear_all(pattern: str = "*"):
	deleted = await cache.clear_all_cache(pattern)
	return {"deleted": deleted}
```

Notes:

- The code currently uses `redis.from_url` with `await`; ensure you use a recent `redis` library (async interface). If you encounter issues, switch to `from redis import asyncio as redis` and adjust the import.
- Keys for POST/PUT/PATCH incorporate a SHA256 of the request body (or chosen Pydantic model param) for uniqueness.

## 🛠 Configuration System

Define strongly‑typed settings classes that can auto‑generate YAML templates and hot‑reload when files change.

```python
from general_utils.config.config import Configs

# Access settings (auto loaded / auto reloaded when yaml files change)
port = Configs.basic_config.api_server["port"]

# Generate template files (writes YAML skeletons if absent)
Configs.create_all_templates()

# Turn off auto reload if desired
Configs.set_auto_reload(False)
```

Each settings class inherits `BaseFileSettings` and declares `model_config = SettingsConfigDict(yaml_file=Path(...))` so the values can be overridden in YAML without code changes.

## 🧾 Logging

```python
from general_utils.utils.log_common import build_logger

logger = build_logger("api")  # Creates logs/api.log (rotating via Loguru)
logger.info("<green>Server started</green>")
```

Verbosity can be toggled with `Configs.basic_config.log_verbose`.

## ⏱ Timing Decorators

```python
from general_utils.utils.timing import measure_execution_time, measure_execution_time_async

@measure_execution_time
after = []
def compute():
	for _ in range(100_000):
		after.append(1)

import asyncio

@measure_execution_time_async
async def compute_async():
	await asyncio.sleep(0.2)

compute()
asyncio.run(compute_async())
```

Logs include module path, file location, line number, and elapsed time.

## 🌱 Environment Variables

```python
from general_utils.utils.env import get_env

api_key = get_env("API_KEY")  # Raises if unset or empty
```

## 🧪 Linting

This project uses Ruff (configured in `pyproject.toml`). Run checks:

```bash
ruff check
```

Auto‑fix (where possible):

```bash
ruff check --fix
```

## 📦 Dependencies (core)

- argon2-cffi – password hashing
- loguru – structured colorful logging
- memoization – lightweight caching decorator used internally
- pydantic / pydantic-settings – settings & validation
- ruamel-yaml – preserving comments & formatting for templates
- redis – caching backend (async used in decorator)
- fastapi – (optional) for the response caching decorator

## 🚀 Roadmap Ideas

- Async Redis import refinement (`redis.asyncio`) wrapper
- Optional instrumentation exporters (OpenTelemetry)
- Additional cache backends (in‑memory / memcached)

## 🤝 Contributing

1. Fork & create a feature branch.
2. Install dependencies & enable Ruff.
3. Add / update tests or examples if changing behavior.
4. Submit a PR with a concise description.

## 📄 License

MIT © Hoang

## 🔎 At a Glance (Short Description)

Composable Python utilities: Argon2 auth helpers, Redis+FastAPI response caching, YAML‑backed dynamic Pydantic settings, structured logging, env access, and execution time decorators.

---

If this saves you time, a star ⭐ is appreciated.
