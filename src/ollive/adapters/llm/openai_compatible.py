"""OpenAI-compatible LLM adapter (GPT + vLLM)."""

from __future__ import annotations

import json
import time
from typing import Any

from openai import OpenAI

from ollive.domain.models import LLMResponse, Message, Role, ToolCallRequest, UsageStats
from ollive.ports.llm import LLMPort


def messages_to_openai(messages: list[Message]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for m in messages:
        item: dict[str, Any] = {"role": m.role.value, "content": m.content}
        if m.name:
            item["name"] = m.name
        if m.tool_call_id:
            item["tool_call_id"] = m.tool_call_id
        if m.tool_calls:
            item["tool_calls"] = m.tool_calls
            if not m.content:
                item["content"] = None
        out.append(item)
    return out


class OpenAICompatibleLLM(LLMPort):
    def __init__(
        self,
        *,
        backend_name: str,
        model: str,
        api_key: str,
        base_url: str | None = None,
        temperature: float | None = None,
        max_tokens: int = 1024,
        instruct_mode: bool = False,
        provider: str = "openai",
    ) -> None:
        self._backend_name = backend_name
        self._model = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._instruct_mode = instruct_mode
        self._provider = provider
        kwargs: dict[str, Any] = {"api_key": api_key or "EMPTY"}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = OpenAI(**kwargs)

    @property
    def model_name(self) -> str:
        return self._model

    @property
    def backend_name(self) -> str:
        return self._backend_name

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
    ) -> LLMResponse:
        payload: dict[str, Any] = {
            "model": self._model,
            "messages": messages_to_openai(messages),
        }
        if self._temperature is not None:
            payload["temperature"] = self._temperature
        if self._provider == "openai":
            payload["max_completion_tokens"] = self._max_tokens
        else:
            payload["max_tokens"] = self._max_tokens
        if tools:
            payload["tools"] = tools
            if tool_choice is not None:
                payload["tool_choice"] = tool_choice

        # Qwen3.5 instruct / non-thinking mode
        if self._instruct_mode:
            payload["extra_body"] = {
                "chat_template_kwargs": {"enable_thinking": False},
            }

        t0 = time.perf_counter()
        resp = self._client.chat.completions.create(**payload)
        latency_ms = (time.perf_counter() - t0) * 1000

        choice = resp.choices[0].message
        tool_calls: list[ToolCallRequest] = []
        if choice.tool_calls:
            for tc in choice.tool_calls:
                try:
                    args = json.loads(tc.function.arguments or "{}")
                except json.JSONDecodeError:
                    args = {"_raw": tc.function.arguments}
                tool_calls.append(
                    ToolCallRequest(id=tc.id, name=tc.function.name, arguments=args)
                )

        usage_raw = resp.usage
        usage = UsageStats(
            prompt_tokens=getattr(usage_raw, "prompt_tokens", 0) or 0,
            completion_tokens=getattr(usage_raw, "completion_tokens", 0) or 0,
            total_tokens=getattr(usage_raw, "total_tokens", 0) or 0,
            latency_ms=latency_ms,
            model=self._model,
            backend=self._backend_name,
        )
        return LLMResponse(
            content=choice.content or "",
            tool_calls=tool_calls,
            usage=usage,
            raw=resp.model_dump() if hasattr(resp, "model_dump") else {},
        )
