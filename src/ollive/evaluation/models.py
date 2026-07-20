"""Typed evaluation records."""
from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    id: str
    axis: str
    subtype: str
    severity: str
    prompt: str
    expected_route: str
    tool_policy: str
    citation_policy: str
    expected_behavior: str
    forbidden_behavior: str
    pair_id: str | None = None
    identity: str | None = None
    tags: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, value: dict[str, Any]) -> "EvalCase":
        return cls(**value)


@dataclass
class EvalRecord:
    run_id: str
    case: dict[str, Any]
    backend: str
    model: str
    repetition: int
    response: str = ""
    route: str = ""
    citations: list[dict[str, Any]] = field(default_factory=list)
    invalid_citations: list[dict[str, Any]] = field(default_factory=list)
    citation_validation_failed: bool = False
    tool_trace: list[dict[str, Any]] = field(default_factory=list)
    usage: dict[str, Any] = field(default_factory=dict)
    structural_grades: dict[str, Any] = field(default_factory=dict)
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
