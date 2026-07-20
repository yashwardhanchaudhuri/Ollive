"""Local OSS tracer — JSONL files, no API keys."""

from __future__ import annotations

import json
import time
import uuid
from contextlib import AbstractContextManager, contextmanager
from pathlib import Path
from typing import Any, Iterator

from ollive.ports.tracer import TracerPort


class LocalFileTracer(TracerPort):
    """Append-only JSONL traces under data/traces/."""

    def __init__(self, trace_dir: Path) -> None:
        self.trace_dir = trace_dir
        self.trace_dir.mkdir(parents=True, exist_ok=True)
        self._trace_id: str | None = None
        self._session_id: str | None = None
        self._events: list[dict[str, Any]] = []
        self._path: Path | None = None

    @contextmanager
    def start_trace(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> Iterator[str]:
        self._trace_id = str(uuid.uuid4())
        self._session_id = session_id
        self._events = []
        day = time.strftime("%Y%m%d")
        self._path = self.trace_dir / f"traces_{day}.jsonl"
        self._events.append(
            {
                "type": "trace_start",
                "trace_id": self._trace_id,
                "session_id": session_id,
                "name": name,
                "metadata": metadata or {},
                "ts": time.time(),
            }
        )
        try:
            yield self._trace_id
        finally:
            self._events.append(
                {
                    "type": "trace_end",
                    "trace_id": self._trace_id,
                    "ts": time.time(),
                }
            )
            self._flush_events()
            self._trace_id = None
            self._events = []

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
        self._events.append(
            {
                "type": "generation",
                "trace_id": self._trace_id,
                "session_id": self._session_id,
                "name": name,
                "model": model,
                "input": input_messages,
                "output": output,
                "usage": usage,
                "metadata": metadata or {},
                "ts": time.time(),
            }
        )

    def log_span(
        self,
        *,
        name: str,
        input: Any = None,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        self._events.append(
            {
                "type": "span",
                "trace_id": self._trace_id,
                "session_id": self._session_id,
                "name": name,
                "input": input,
                "output": output,
                "metadata": metadata or {},
                "ts": time.time(),
            }
        )

    def flush(self) -> None:
        self._flush_events()

    def _flush_events(self) -> None:
        if not self._path or not self._events:
            return
        with self._path.open("a", encoding="utf-8") as f:
            for event in self._events:
                f.write(json.dumps(event, ensure_ascii=False, default=str) + "\n")
        self._events = []
