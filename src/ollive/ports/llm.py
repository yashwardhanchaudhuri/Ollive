"""LLM port — OpenAI-compatible chat with optional tool calling."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ollive.domain.models import LLMResponse, Message


class LLMPort(ABC):
    @property
    @abstractmethod
    def model_name(self) -> str:
        """Return the adapter model identifier."""
        ...

    @property
    @abstractmethod
    def backend_name(self) -> str:
        """Return the adapter backend identifier."""
        ...

    @abstractmethod
    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
    ) -> LLMResponse:
        """Generate one model response with optional constrained tool calling."""
        ...
