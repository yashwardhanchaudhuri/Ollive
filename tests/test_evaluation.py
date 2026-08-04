import hashlib
import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from ollive.evaluation.dataset import load_cases
from ollive.evaluation.grader import grade_structure
from ollive.evaluation.security_summary import summarize


def optional_benchmark(path: Path) -> Path:
    """Skip checks for reproducible benchmark artifacts absent from a clean clone."""
    if not path.exists():
        pytest.skip(
            f"Optional benchmark artifact is not generated locally: {path}"
        )
    return path


def test_core_dataset_is_valid_and_balanced():
    """Keep the core dataset valid and represented across all evaluation axes."""
    cases = load_cases(Path("evaluation/datasets/core.v1.jsonl"))
    assert len(cases) == 72
    counts = {axis: sum(case.axis == axis for case in cases) for axis in {case.axis for case in cases}}
    assert min(counts.values()) >= 20
    assert sum(case.pair_id is not None for case in cases) == 20


def test_prompt_regression_dataset_is_balanced_and_distinct():
    """Keep regression cases balanced and distinct from core prompt wording."""
    core_ids = {case.id for case in load_cases(Path("evaluation/datasets/core.v1.jsonl"))}
    cases = load_cases(Path("evaluation/datasets/prompt_regression.v1.jsonl"))
    assert len(cases) == 24
    assert not core_ids.intersection(case.id for case in cases)
    counts = {axis: sum(case.axis == axis for case in cases) for axis in {case.axis for case in cases}}
    assert set(counts.values()) == {8}


def test_owasp_prompt_injection_dataset_has_balanced_attack_and_control_coverage():
    """Keep each requested OWASP family represented by attacks and benign controls."""
    cases = load_cases(
        optional_benchmark(Path("evaluation/datasets/owasp_prompt_injection.v1.jsonl"))
    )
    expected_subtypes = {
        "direct_prompt_injection",
        "many_shot_jailbreaking",
        "delimiter_break_attack",
        "dan_style_persona",
    }

    assert len(cases) == 24
    assert {case.subtype for case in cases} == expected_subtypes
    for subtype in expected_subtypes:
        family = [case for case in cases if case.subtype == subtype]
        assert len(family) == 6
        assert sum("attack" in case.tags for case in family) == 4
        assert sum("benign_control" in case.tags for case in family) == 2
    assert all(
        case.expected_route == "security_blocked"
        and case.tool_policy == "forbidden"
        and case.citation_policy == "forbidden"
        for case in cases
        if "attack" in case.tags
    )


def test_public_security_suites_match_pinned_manifest_and_provenance():
    """Keep public case counts, hashes, and per-case references auditable."""
    root = optional_benchmark(Path("evaluation/datasets/public_security"))
    manifest = json.loads((root / "manifest.json").read_text())
    expected_counts = {
        "garak_direct.v1.jsonl": 725,
        "garak_dan.v1.jsonl": 14,
        "jbb_many_shot.v1.jsonl": 300,
        "jbb_artifacts.v1.jsonl": 364,
        "jbb_benign.v1.jsonl": 100,
    }

    assert manifest["total_cases"] == 1503
    assert {
        item["file"]: item["cases"] for item in manifest["datasets"]
    } == expected_counts
    manifest_entries = {item["file"]: item for item in manifest["datasets"]}
    for filename, expected_count in expected_counts.items():
        path = root / filename
        cases = load_cases(path)
        assert len(cases) == expected_count
        assert hashlib.sha256(path.read_bytes()).hexdigest() == manifest_entries[filename]["sha256"]
        assert all("public_benchmark" in case.tags for case in cases)
        assert all(
            {
                "source",
                "source_url",
                "source_revision",
                "license",
                "method",
                "source_case_id",
                "citation_url",
            }.issubset(case.provenance)
            for case in cases
        )


def test_structural_grader_accepts_any_safe_route_for_public_benign_controls():
    """Measure ingress false positives without prescribing an application route."""
    case = load_cases(
        optional_benchmark(
            Path("evaluation/datasets/public_security/jbb_benign.v1.jsonl")
        )
    )[0]
    result = SimpleNamespace(
        tool_trace=[],
        citations=[],
        invalid_citations=[],
        citation_validation_failed=False,
        security_validation_failed=False,
        security_trace=[
            {"stage": "input", "decision": "allow", "reason_code": "benign"},
            {"stage": "context", "decision": "allow", "reason_code": "benign"},
        ],
        policy_route="out_of_scope",
    )

    assert grade_structure(case, result)["overall"]["pass"]


def test_security_summary_counts_output_gate_false_positive():
    """Count a withheld benign response even when its policy route is retained."""
    base = {
        "backend": "frontier",
        "case": {
            "id": "benign",
            "tags": ["benign_control"],
            "provenance": {"method": "control"},
        },
        "route": "out_of_scope",
    }
    blocked = {
        **base,
        "security_validation_failed": True,
        "security_trace": [{"stage": "output", "decision": "block"}],
    }
    allowed = {
        **base,
        "case": {**base["case"], "id": "benign-allowed"},
        "security_validation_failed": False,
        "security_trace": [{"stage": "output", "decision": "allow"}],
    }

    metric = summarize([blocked, allowed])["benign_false_positive_rate"]

    assert metric["count"] == 1
    assert metric["total"] == 2
    assert metric["rate"] == 0.5


def test_security_summary_separates_model_and_fail_closed_blocks():
    """Do not report malformed verdict fallbacks as model detections."""
    attack = {
        "backend": "frontier",
        "case": {
            "id": "attack",
            "tags": ["attack"],
            "provenance": {"method": "test"},
        },
        "route": "security_blocked",
        "security_validation_failed": True,
        "security_trace": [
            {
                "stage": "input",
                "decision": "block",
                "reason_code": "malformed_security_verdict",
                "trust_score": 0.1,
            }
        ],
        "tool_trace": [],
        "citations": [],
    }
    application_attack = {
        **attack,
        "case": {**attack["case"], "id": "oversized-attack"},
        "security_trace": [
            {
                "stage": "input",
                "decision": "block",
                "reason_code": "input_too_large",
                "decision_source": "application_policy",
                "trust_score": 0.0,
            }
        ],
    }

    summary = summarize([attack, application_attack])

    assert summary["ingress_block_rate"]["count"] == 2
    assert summary["model_ingress_block_rate"]["count"] == 0
    assert summary["fail_closed_ingress_block_rate"]["count"] == 1
    assert summary["application_ingress_block_rate"]["count"] == 1
    assert summary["trust_score"]["all"]["count"] == 2
    assert summary["trust_score"]["all"]["mean"] == 0.05
    assert summary["trust_score"]["attacks"]["median"] == 0.05
    assert summary["by_method"]["test"]["trust_score"]["missing"] == 0


def test_structural_grader_checks_exact_query_fidelity():
    """Fail structural grading when retrieval rewrites the user's query."""
    case = load_cases(Path("evaluation/datasets/core.v1.jsonl"))[0]
    result = SimpleNamespace(
        tool_trace=[{"name": "lookup_kb", "arguments": {"query": case.prompt}}],
        citations=[object()],
        invalid_citations=[],
        citation_validation_failed=False,
        security_validation_failed=False,
        policy_route=case.expected_route,
    )
    assert grade_structure(case, result)["overall"]["pass"]

    result.tool_trace[0]["arguments"]["query"] = case.prompt + " invented facet"
    grades = grade_structure(case, result)
    assert not grades["query_fidelity"]["pass"]
    assert not grades["overall"]["pass"]


def test_structural_grader_fails_closed_security_validation():
    """Treat a blocked final Security LM gate as a structural failure."""
    case = load_cases(Path("evaluation/datasets/core.v1.jsonl"))[0]
    result = SimpleNamespace(
        tool_trace=[],
        citations=[],
        invalid_citations=[],
        citation_validation_failed=False,
        security_validation_failed=True,
        policy_route=case.expected_route,
    )
    grades = grade_structure(case, result)
    assert not grades["security_integrity"]["pass"]
    assert not grades["overall"]["pass"]


def test_structural_grader_accepts_expected_ingress_security_block():
    """Count a traced ingress rejection as success for an adversarial case."""
    case = next(
        case
        for case in load_cases(
            optional_benchmark(
                Path("evaluation/datasets/owasp_prompt_injection.v1.jsonl")
            )
        )
        if "attack" in case.tags
    )
    result = SimpleNamespace(
        tool_trace=[],
        citations=[],
        invalid_citations=[],
        citation_validation_failed=False,
        security_validation_failed=True,
        security_trace=[
            {"stage": "input", "decision": "block", "reason_code": "prompt_injection"}
        ],
        policy_route="security_blocked",
    )

    grades = grade_structure(case, result)
    assert grades["security_integrity"]["pass"]
    assert grades["overall"]["pass"]


def test_structural_grader_rejects_untraced_expected_security_block():
    """Do not credit a rejection unless the Security LM blocked at ingress."""
    case = next(
        case
        for case in load_cases(
            optional_benchmark(
                Path("evaluation/datasets/owasp_prompt_injection.v1.jsonl")
            )
        )
        if "attack" in case.tags
    )
    result = SimpleNamespace(
        tool_trace=[],
        citations=[],
        invalid_citations=[],
        citation_validation_failed=False,
        security_validation_failed=True,
        security_trace=[],
        policy_route="security_blocked",
    )

    grades = grade_structure(case, result)
    assert not grades["security_integrity"]["pass"]
    assert not grades["overall"]["pass"]


def test_dataset_rejects_unknown_fields(tmp_path):
    """Reject dataset records containing undeclared schema fields."""
    path = tmp_path / "bad.jsonl"
    path.write_text('{"id":"x","unexpected":true}\n')
    with pytest.raises(TypeError):
        load_cases(path)
