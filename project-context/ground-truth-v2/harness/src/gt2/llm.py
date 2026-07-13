# ---------------------------------------------------------------------------
# llm.py — cached structured LLM calls via LangChain init_chat_model.
# Contract: every call is cached on disk keyed sha256(model + schema name +
#   prompt), same resumability pattern as the product's e3_cache. Cache hits
#   cost $0 and make every stage re-runnable. Retries log loudly, never sleep
#   silently (telemetry-first doctrine). Temperature untouched (gpt-5 family
#   rejects non-default temperature).
# Deps: langchain, pydantic, config.
# ---------------------------------------------------------------------------
from __future__ import annotations

import hashlib
import json
import time
from pathlib import Path
from typing import Type, TypeVar

from pydantic import BaseModel

T = TypeVar("T", bound=BaseModel)

_models: dict[str, object] = {}
_models_lock = __import__("threading").Lock()


def _chat(model: str):
    # thread-safe: stages fan out over a ThreadPoolExecutor
    with _models_lock:
        if model not in _models:
            from langchain.chat_models import init_chat_model
            # default Anthropic max_tokens (1024) truncates large structured
            # outputs (e.g. a 60-URL ranking) -> ValidationError; raise the cap
            _models[model] = init_chat_model(model, max_tokens=16_000)
        return _models[model]


def _cache_key(model: str, schema: str, system: str, user: str) -> str:
    payload = json.dumps([model, schema, system, user], ensure_ascii=False)
    return hashlib.sha256(payload.encode()).hexdigest()


def invoke_structured(
    cache_dir: Path,
    model: str,
    schema: Type[T],
    system: str,
    user: str,
    max_attempts: int = 3,
) -> T:
    key = _cache_key(model, schema.__name__, system, user)
    cache_file = cache_dir / f"{key}.json"
    if cache_file.exists():
        return schema.model_validate_json(cache_file.read_text())

    bound = _chat(model).with_structured_output(schema)
    last_exc: Exception | None = None
    for attempt in range(1, max_attempts + 1):
        try:
            result = bound.invoke(
                [{"role": "system", "content": system},
                 {"role": "user", "content": user}]
            )
            if result is None:
                raise RuntimeError("structured output returned None")
            cache_file.write_text(result.model_dump_json())
            return result
        except Exception as exc:  # loud retry, telemetry-first
            last_exc = exc
            wait = 8 * attempt
            print(f"    ! {model} attempt {attempt}/{max_attempts} failed: "
                  f"{type(exc).__name__}: {str(exc)[:200]}"
                  + (f" — retrying in {wait}s" if attempt < max_attempts else ""))
            if attempt < max_attempts:
                time.sleep(wait)
    raise RuntimeError(f"{model} failed after {max_attempts} attempts") from last_exc
