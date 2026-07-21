"""Observability / tracing port."""

from __future__ import annotations

from abc import ABC, abstractmethod
from contextlib import AbstractContextManager
from typing import Any


class TracerPort(ABC):
    @abstractmethod
    def start_trace(
        self,
        name: str,
        metadata: dict[str, Any] | None = None,
        session_id: str | None = None,
    ) -> AbstractContextManager[Any]:
        """Open a trace scope for one agent turn."""
        ...

    @abstractmethod
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
        """Record one model generation and its usage metadata."""
        ...

    @abstractmethod
    def log_span(
        self,
        *,
        name: str,
        input: Any = None,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None:
        """Record one non-generation operation in the active trace."""
        ...

    @abstractmethod
    def flush(self) -> None:
        """Persist buffered trace events before returning the turn."""
        ...
