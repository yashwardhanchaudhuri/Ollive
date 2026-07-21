"""Local Hugging Face Transformers LLM — no API keys."""

from __future__ import annotations

import json
import re
import time
from typing import Any

import torch
from transformers import AutoModelForCausalLM, AutoTokenizer

from ollive.domain.models import LLMResponse, Message, ToolCallRequest, UsageStats
from ollive.ports.llm import LLMPort


_TOOL_CALL_RE = re.compile(
    r"<tool_call>\s*(\{.*?\})\s*</tool_call>",
    re.DOTALL,
)
_LLAMA_TOOL_RE = re.compile(
    r'\{"name"\s*:\s*"([^"]+)"\s*,\s*"parameters"\s*:\s*(\{.*?\})\s*\}',
    re.DOTALL,
)


def _openai_tools_to_hf(tools: list[dict[str, Any]] | None) -> list[dict[str, Any]] | None:
    """Translate OpenAI tool schemas into Transformers chat-template format."""
    if not tools:
        return None
    converted = []
    for t in tools:
        if t.get("type") == "function" and "function" in t:
            fn = t["function"]
            converted.append(
                {
                    "type": "function",
                    "function": {
                        "name": fn["name"],
                        "description": fn.get("description", ""),
                        "parameters": fn.get("parameters", {}),
                    },
                }
            )
        else:
            converted.append(t)
    return converted


def _messages_to_hf(messages: list[Message]) -> list[dict[str, Any]]:
    """Translate domain messages into Transformers chat-template dictionaries."""
    out: list[dict[str, Any]] = []
    for m in messages:
        role = m.role.value
        if role == "tool":
            out.append(
                {
                    "role": "tool",
                    "content": m.content,
                    "name": m.name or "tool",
                    "tool_call_id": m.tool_call_id or "",
                }
            )
            continue
        item: dict[str, Any] = {"role": role, "content": m.content or ""}
        if m.tool_calls:
            # Represent prior assistant tool calls for multi-turn
            item["tool_calls"] = m.tool_calls
        out.append(item)
    return out


def _parse_tool_calls(text: str) -> tuple[str, list[ToolCallRequest]]:
    """Extract tool calls from common OSS chat formats."""
    tool_calls: list[ToolCallRequest] = []
    cleaned = text

    for i, match in enumerate(_TOOL_CALL_RE.finditer(text)):
        try:
            payload = json.loads(match.group(1))
            name = payload.get("name") or payload.get("function", {}).get("name")
            args = (
                payload.get("arguments")
                or payload.get("parameters")
                or payload.get("function", {}).get("arguments")
                or {}
            )
            if isinstance(args, str):
                args = json.loads(args)
            if name:
                tool_calls.append(
                    ToolCallRequest(id=f"call_local_{i}", name=name, arguments=args)
                )
        except json.JSONDecodeError:
            continue
        cleaned = cleaned.replace(match.group(0), "")

    if tool_calls:
        return cleaned.strip(), tool_calls

    # Llama-style bare JSON tool call lines
    for i, match in enumerate(_LLAMA_TOOL_RE.finditer(text)):
        try:
            args = json.loads(match.group(2))
        except json.JSONDecodeError:
            args = {}
        tool_calls.append(
            ToolCallRequest(
                id=f"call_local_{i}",
                name=match.group(1),
                arguments=args,
            )
        )
        cleaned = cleaned.replace(match.group(0), "")

    return cleaned.strip(), tool_calls


class LocalTransformersLLM(LLMPort):
    """In-process OSS model via transformers (GPU if available)."""

    def __init__(
        self,
        *,
        backend_name: str,
        model: str,
        temperature: float = 0.3,
        max_tokens: int = 1024,
        device: str | None = None,
        load_in_4bit: bool = False,
    ) -> None:
        """Initialize LocalTransformersLLM with its runtime collaborators."""
        self._backend_name = backend_name
        self._model_name = model
        self._temperature = temperature
        self._max_tokens = max_tokens
        self._tokenizer = AutoTokenizer.from_pretrained(model)
        dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
        kwargs: dict[str, Any] = {
            "torch_dtype": dtype,
            "device_map": device or ("auto" if torch.cuda.is_available() else None),
        }
        if load_in_4bit:
            kwargs["load_in_4bit"] = True
        self._model = AutoModelForCausalLM.from_pretrained(model, **kwargs)
        self._model.eval()

    @property
    def model_name(self) -> str:
        """Return the adapter model identifier."""
        return self._model_name

    @property
    def backend_name(self) -> str:
        """Return the adapter backend identifier."""
        return self._backend_name

    def chat(
        self,
        messages: list[Message],
        tools: list[dict[str, Any]] | None = None,
        tool_choice: str | dict[str, Any] | None = "auto",
    ) -> LLMResponse:
        """Generate one response through the in-process model backend."""
        hf_messages = _messages_to_hf(messages)
        hf_tools = _openai_tools_to_hf(tools)

        apply_kwargs: dict[str, Any] = {
            "tokenize": False,
            "add_generation_prompt": True,
        }
        # Llama / Qwen chat templates accept tools when provided
        if hf_tools and tool_choice is not None:
            apply_kwargs["tools"] = hf_tools

        try:
            prompt = self._tokenizer.apply_chat_template(hf_messages, **apply_kwargs)
        except TypeError:
            # Template may not accept tools — fall back to prompt injection
            if hf_tools:
                tool_blob = json.dumps(hf_tools, indent=2)
                hf_messages = list(hf_messages)
                hf_messages.insert(
                    1 if hf_messages and hf_messages[0]["role"] == "system" else 0,
                    {
                        "role": "system",
                        "content": (
                            "To call a tool, emit one <tool_call> element containing a JSON "
                            "object. Its name field must select an available tool and its "
                            "arguments field must satisfy that tool schema. Do not emit "
                            "placeholder values.\n"
                            f"Available tools:\n{tool_blob}"
                        ),
                    },
                )
            prompt = self._tokenizer.apply_chat_template(
                hf_messages, tokenize=False, add_generation_prompt=True
            )

        inputs = self._tokenizer(prompt, return_tensors="pt")
        inputs = {k: v.to(self._model.device) for k, v in inputs.items()}
        prompt_tokens = int(inputs["input_ids"].shape[-1])

        gen_kwargs: dict[str, Any] = {
            "max_new_tokens": self._max_tokens,
            "do_sample": self._temperature > 0,
            "temperature": max(self._temperature, 1e-5),
            "pad_token_id": self._tokenizer.eos_token_id,
        }

        t0 = time.perf_counter()
        with torch.inference_mode():
            output_ids = self._model.generate(**inputs, **gen_kwargs)
        latency_ms = (time.perf_counter() - t0) * 1000

        new_tokens = output_ids[0][prompt_tokens:]
        text = self._tokenizer.decode(new_tokens, skip_special_tokens=True)
        content, tool_calls = _parse_tool_calls(text)

        # Some templates put tool calls in special tokens — try parsing raw decode too
        if not tool_calls:
            raw = self._tokenizer.decode(new_tokens, skip_special_tokens=False)
            content2, tool_calls = _parse_tool_calls(raw)
            if tool_calls:
                content = content2

        usage = UsageStats(
            prompt_tokens=prompt_tokens,
            completion_tokens=int(new_tokens.shape[-1]),
            total_tokens=prompt_tokens + int(new_tokens.shape[-1]),
            latency_ms=latency_ms,
            model=self._model_name,
            backend=self._backend_name,
        )
        return LLMResponse(
            content=content if not tool_calls else (content or ""),
            tool_calls=tool_calls,
            usage=usage,
        )
