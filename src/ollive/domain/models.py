"""Core domain models — no infrastructure dependencies."""

from __future__ import annotations

from enum import Enum
from typing import Any, Literal

from pydantic import BaseModel, Field


class Role(str, Enum):
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class Citation(BaseModel):
    """Validated evidence reference from the local KB or an allowed web source."""

    doc_type: str
    line: int
    descriptor: str
    end_line: int | None = None
    title: str | None = None
    text: str = ""
    source_type: Literal["knowledge_base", "web"] = "knowledge_base"
    url: str | None = None
    domain: str | None = None

    @property
    def marker(self) -> str:
        line_part = f"L{self.line}"
        if self.end_line and self.end_line != self.line:
            line_part = f"L{self.line}-{self.end_line}"
        return f"[{self.doc_type}:{line_part}:{self.descriptor}]"


class Chunk(BaseModel):
    chunk_id: str
    doc_id: str
    doc_type: str
    title: str
    start_line: int
    end_line: int
    descriptor: str
    text: str

    def to_citation(self) -> Citation:
        return Citation(
            doc_type=self.doc_type,
            line=self.start_line,
            end_line=self.end_line,
            descriptor=self.descriptor,
            title=self.title,
            text=self.text,
        )


class Message(BaseModel):
    role: Role
    content: str = ""
    name: str | None = None
    tool_call_id: str | None = None
    tool_calls: list[dict[str, Any]] | None = None


class ToolCallRequest(BaseModel):
    id: str
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)


class ToolResult(BaseModel):
    tool_call_id: str
    name: str
    content: str
    citations: list[Citation] = Field(default_factory=list)


class UsageStats(BaseModel):
    prompt_tokens: int = 0
    completion_tokens: int = 0
    total_tokens: int = 0
    latency_ms: float = 0.0
    model: str = ""
    backend: str = ""

    def add(self, other: "UsageStats") -> "UsageStats":
        return UsageStats(
            prompt_tokens=self.prompt_tokens + other.prompt_tokens,
            completion_tokens=self.completion_tokens + other.completion_tokens,
            total_tokens=self.total_tokens + other.total_tokens,
            latency_ms=self.latency_ms + other.latency_ms,
            model=other.model or self.model,
            backend=other.backend or self.backend,
        )


class LLMResponse(BaseModel):
    content: str = ""
    tool_calls: list[ToolCallRequest] = Field(default_factory=list)
    usage: UsageStats = Field(default_factory=UsageStats)
    raw: dict[str, Any] = Field(default_factory=dict)


class AgentTurnResult(BaseModel):
    assistant_message: str
    citations: list[Citation] = Field(default_factory=list)
    invalid_citations: list[Citation] = Field(default_factory=list)
    citation_validation_failed: bool = False
    tool_trace: list[dict[str, Any]] = Field(default_factory=list)
    usage: UsageStats = Field(default_factory=UsageStats)
    backend: str = ""
    model: str = ""
    policy_route: str = ""
