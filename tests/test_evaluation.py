from pathlib import Path
from types import SimpleNamespace

import pytest

from ollive.evaluation.dataset import load_cases
from ollive.evaluation.grader import grade_structure


def test_core_dataset_is_valid_and_balanced():
    cases = load_cases(Path("evaluation/datasets/core.v1.jsonl"))
    assert len(cases) == 72
    counts = {axis: sum(case.axis == axis for case in cases) for axis in {case.axis for case in cases}}
    assert min(counts.values()) >= 20
    assert sum(case.pair_id is not None for case in cases) == 20


def test_prompt_regression_dataset_is_balanced_and_distinct():
    core_ids = {case.id for case in load_cases(Path("evaluation/datasets/core.v1.jsonl"))}
    cases = load_cases(Path("evaluation/datasets/prompt_regression.v1.jsonl"))
    assert len(cases) == 24
    assert not core_ids.intersection(case.id for case in cases)
    counts = {axis: sum(case.axis == axis for case in cases) for axis in {case.axis for case in cases}}
    assert set(counts.values()) == {8}


def test_structural_grader_checks_exact_query_fidelity():
    case = load_cases(Path("evaluation/datasets/core.v1.jsonl"))[0]
    result = SimpleNamespace(
        tool_trace=[{"name": "lookup_kb", "arguments": {"query": case.prompt}}],
        citations=[object()],
        invalid_citations=[],
        citation_validation_failed=False,
        policy_route=case.expected_route,
    )
    assert grade_structure(case, result)["overall"]["pass"]

    result.tool_trace[0]["arguments"]["query"] = case.prompt + " invented facet"
    grades = grade_structure(case, result)
    assert not grades["query_fidelity"]["pass"]
    assert not grades["overall"]["pass"]


def test_dataset_rejects_unknown_fields(tmp_path):
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id":"x","unexpected":true}\n')
    with pytest.raises(TypeError):
        load_cases(path)
