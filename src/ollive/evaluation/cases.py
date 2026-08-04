"""Shared constructors for deterministic evaluation datasets."""
from __future__ import annotations

from typing import Any


def build_case(
    case_id: str,
    axis: str,
    subtype: str,
    severity: str,
    prompt: str,
    expected_route: str,
    tool_policy: str,
    citation_policy: str,
    expected_behavior: str,
    forbidden_behavior: str,
    **extra: Any,
) -> dict[str, Any]:
    """Build a consistently shaped evaluation case."""
    value: dict[str, Any] = {
        "id": case_id,
        "axis": axis,
        "subtype": subtype,
        "severity": severity,
        "prompt": prompt,
        "expected_route": expected_route,
        "tool_policy": tool_policy,
        "citation_policy": citation_policy,
        "expected_behavior": expected_behavior,
        "forbidden_behavior": forbidden_behavior,
    }
    value.update(extra)
    return value
