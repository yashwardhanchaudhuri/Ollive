"""Architectural regression tests for the segregated runtime pipeline."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ollive.application.pipeline import PipelineConfig


ROOT = Path(__file__).resolve().parents[1]
APPLICATION = ROOT / "src/ollive/application"


def _method_source(path: Path, class_name: str, method_name: str) -> str:
    """Return normalized source for one class method using the Python AST."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.ClassDef) and node.name == class_name:
            for child in node.body:
                if isinstance(child, ast.FunctionDef) and child.name == method_name:
                    return ast.unparse(child)
    raise AssertionError(f"missing {class_name}.{method_name}")


def test_pipeline_rejects_zero_web_search_mode():
    """Make one web search the non-configurable grounded-turn minimum."""
    with pytest.raises(ValueError, match="1 <= minimum"):
        PipelineConfig(
            system_prompt="test",
            min_web_searches=0,
            max_web_searches=3,
        )


def test_agent_remains_a_session_only_facade():
    """Keep policy, evidence, and security enforcement out of WellnessAgent."""
    path = APPLICATION / "agent.py"
    source = path.read_text(encoding="utf-8")
    assert len(source.splitlines()) < 150
    assert "RuntimePipeline" in source
    for forbidden in (
        "review_input(",
        "filter_evidence(",
        "lookup_kb",
        "search_web",
        "verify_claim_support(",
        "parse_citations(",
    ):
        assert forbidden not in source


def test_ingress_reviews_the_complete_bounded_history_snapshot():
    """Prevent later stages from seeing history omitted from aggregate review."""
    source = (APPLICATION / "pipeline/ingress.py").read_text(encoding="utf-8")
    assert "*state.history," in source
    assert "state.history[-" not in source


def test_runtime_pipeline_orders_ingress_before_routing_and_output():
    """Prevent the answer model from running before the ingress boundary."""
    source = _method_source(
        APPLICATION / "pipeline/runtime.py", "RuntimePipeline", "run"
    )
    assert source.index("self._ingress.run") < source.index("self._routing.run")
    assert source.index("self._routing.run") < source.index("self._grounded.run")
    assert source.rindex("self._output.run") > source.index("self._grounded.run")


def test_only_evidence_stage_executes_external_tools():
    """Keep raw tool execution and evidence approval in one owned boundary."""
    pipeline = APPLICATION / "pipeline"
    owners = []
    for path in pipeline.glob("*.py"):
        if "self._tools.execute" in path.read_text(encoding="utf-8"):
            owners.append(path.name)
    assert owners == ["evidence.py"]

    source = (pipeline / "evidence.py").read_text(encoding="utf-8")
    assert source.index("self._tools.execute") < source.index("filter_evidence")
    assert source.index("filter_evidence") < source.index("safe_tool_result")


def test_additional_searches_require_a_bound_named_gap():
    """Keep searches two and three behind structured sufficiency feedback."""
    source = (APPLICATION / "pipeline/grounded.py").read_text(encoding="utf-8")
    assert "_append_sufficiency_feedback" in source
    assert "_bind_remaining_gap_query" in source
    assert "not state.citations" not in source
