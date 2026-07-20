"""Langfuse v4 tracer adapter with no-op fallback."""

from __future__ import annotations

import os
from contextlib import AbstractContextManager, contextmanager, nullcontext
from typing import Any, Iterator

from ollive.ports.tracer import TracerPort


class NoOpTracer(TracerPort):
    def start_trace(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> AbstractContextManager[Any]:
        return nullcontext()

    def log_generation(
        self,
        *,
        name: str,
        model: str,
        input_messages: list[dict[str, Any]],
        output: str,
        usage: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None

    def log_span(
        self,
        *,
        name: str,
        input: Any = None,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        return None

    def flush(self) -> None:
        return None


class LangfuseTracer(TracerPort):
    """Langfuse SDK v4 (observation-based) adapter."""

    def __init__(self) -> None:
        from langfuse import Langfuse

        self._client = Langfuse(
            public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
            secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
            host=os.getenv("LANGFUSE_HOST", "https://cloud.langfuse.com"),
        )
        self._current: Any = None

    @contextmanager
    def start_trace(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Iterator[Any]:
        meta = dict(metadata or {})
        if session_id:
            meta["session_id"] = session_id
        with self._client.start_as_current_observation(
            name=name,
            as_type="agent",
            metadata=meta,
        ) as span:
            prev = self._current
            self._current = span
            try:
                yield span
            finally:
                self._current = prev

    def log_generation(
        self,
        *,
        name: str,
        model: str,
        input_messages: list[dict[str, Any]],
        output: str,
        usage: dict[str, Any],
        metadata: dict[str, Any] | None = None,
    ) -> None:
        usage_details = {
            k: int(v)
            for k, v in {
                "input": usage.get("input") or usage.get("prompt_tokens"),
                "output": usage.get("output") or usage.get("completion_tokens"),
                "total": usage.get("total") or usage.get("total_tokens"),
            }.items()
            if v is not None
        }
        parent = self._current or self._client
        gen = parent.start_observation(
            name=name,
            as_type="generation",
            model=model,
            input=input_messages,
            output=output,
            metadata=metadata or {},
            usage_details=usage_details or None,
        )
        gen.end()

    def log_span(
        self,
        *,
        name: str,
        input: Any = None,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        parent = self._current or self._client
        as_type = "tool" if name.startswith("tool:") else "span"
        span = parent.start_observation(
            name=name,
            as_type=as_type,
            input=input,
            output=output,
            metadata=metadata or {},
        )
        span.end()

    def flush(self) -> None:
        self._client.flush()


def build_tracer(enabled: bool = True) -> TracerPort:
    if not enabled:
        return NoOpTracer()
    flag = os.getenv("LANGFUSE_ENABLED", "true").lower()
    if flag in {"0", "false", "no"}:
        return NoOpTracer()
    if not os.getenv("LANGFUSE_PUBLIC_KEY") or not os.getenv("LANGFUSE_SECRET_KEY"):
        return NoOpTracer()
    try:
        return LangfuseTracer()
    except Exception:
        return NoOpTracer()
