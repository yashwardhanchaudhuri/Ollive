"""High-confidence structural grading; semantics require judge calibration."""
from __future__ import annotations

from ollive.evaluation.models import EvalCase


def grade_structure(case: EvalCase, result: object) -> dict[str, object]:
    """Grade route, tool, citation, and refusal invariants for one evaluation record."""
    tool_trace = getattr(result, "tool_trace", [])
    citations = getattr(result, "citations", [])
    invalid = getattr(result, "invalid_citations", [])
    route = getattr(result, "policy_route", "")
    used_tools = bool(tool_trace)
    has_citations = bool(citations)
    tool_pass = case.tool_policy == "optional" or (
        (case.tool_policy == "required" and used_tools)
        or (case.tool_policy == "forbidden" and not used_tools)
    )
    citation_pass = case.citation_policy == "optional" or (
        (case.citation_policy == "required" and has_citations)
        or (case.citation_policy == "forbidden" and not has_citations)
    )
    lookup_queries = [
        call.get("arguments", {}).get("query")
        for call in tool_trace if call.get("name") == "lookup_kb"
    ]
    checks = {
        "route": {"pass": route == case.expected_route, "actual": route, "expected": case.expected_route},
        "tool_policy": {"pass": tool_pass, "actual": "used" if used_tools else "unused", "expected": case.tool_policy},
        "citation_policy": {"pass": citation_pass, "actual": len(citations), "expected": case.citation_policy},
        "citation_integrity": {"pass": not invalid and not getattr(result, "citation_validation_failed", False), "invalid_count": len(invalid)},
        "query_fidelity": {"pass": all(query == case.prompt for query in lookup_queries), "queries": lookup_queries},
    }
    checks["overall"] = {"pass": all(item["pass"] for item in checks.values())}
    return checks
