"""Dataset loading and strict shape validation."""
from __future__ import annotations

import json
from pathlib import Path

from ollive.evaluation.models import EvalCase

VALID_AXES = {"hallucination", "bias_harm", "content_safety"}
VALID_ROUTES = {"conversation", "wellness", "medical", "out_of_scope"}
VALID_POLICIES = {"required", "forbidden", "optional"}
VALID_SEVERITIES = {"low", "medium", "high", "critical"}


def load_cases(path: Path) -> list[EvalCase]:
    cases: list[EvalCase] = []
    seen: set[str] = set()
    with path.open("r", encoding="utf-8") as handle:
        for line_number, raw in enumerate(handle, 1):
            if not raw.strip():
                continue
            case = EvalCase.from_dict(json.loads(raw))
            if case.id in seen:
                raise ValueError(f"Duplicate case id at line {line_number}: {case.id}")
            if case.axis not in VALID_AXES:
                raise ValueError(f"Invalid axis for {case.id}: {case.axis}")
            if case.expected_route not in VALID_ROUTES:
                raise ValueError(f"Invalid route for {case.id}: {case.expected_route}")
            if case.tool_policy not in VALID_POLICIES or case.citation_policy not in VALID_POLICIES:
                raise ValueError(f"Invalid policy for {case.id}")
            if case.severity not in VALID_SEVERITIES:
                raise ValueError(f"Invalid severity for {case.id}: {case.severity}")
            if not case.expected_behavior or not case.forbidden_behavior:
                raise ValueError(f"Missing behavioral rubric for {case.id}")
            seen.add(case.id)
            cases.append(case)
    if not cases:
        raise ValueError(f"No evaluation cases found in {path}")
    return cases


def dataset_summary(cases: list[EvalCase]) -> dict[str, int]:
    summary = {"total": len(cases)}
    for case in cases:
        summary[case.axis] = summary.get(case.axis, 0) + 1
    return summary
