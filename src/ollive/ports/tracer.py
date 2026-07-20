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
    ) -> AbstractContextManager[Any]: ...

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
    ) -> None: ...

    @abstractmethod
    def log_span(
        self,
        *,
        name: str,
        input: Any = None,
        output: Any = None,
        metadata: dict[str, Any] | None = None,
    ) -> None: ...

    @abstractmethod
    def flush(self) -> None: ...
