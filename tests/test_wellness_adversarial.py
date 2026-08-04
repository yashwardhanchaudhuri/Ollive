"""Tests for the human-authored custom wellness adversarial suite."""

from __future__ import annotations

import json
from collections import Counter

from ollive.evaluation.wellness_adversarial import (
    ATTACK_CLASSES,
    MECE_VARIATIONS,
    WELLNESS_REQUESTS,
    build_cases,
    build_dataset,
)


def test_mece_design_has_four_by_nine_unique_cells() -> None:
    """Every requested class owns nine mechanisms and all wellness domains."""
    class_slugs = {slug for slug, _name in ATTACK_CLASSES}
    assert set(MECE_VARIATIONS) == class_slugs
    for variations in MECE_VARIATIONS.values():
        assert len(variations) == 9
        assert len({item.slug for item in variations}) == 9
        assert len({item.name for item in variations}) == 9
        assert {item.domain for item in variations} == set(WELLNESS_REQUESTS)


def test_authored_cases_are_balanced_unique_and_not_model_generated() -> None:
    """The builder emits exactly three human-authored alternatives per MECE cell."""
    rows = build_cases()
    cells = Counter(
        (row["subtype"], row["provenance"]["attack_variation"]) for row in rows
    )
    assert len(rows) == 108
    assert len(cells) == 36
    assert set(cells.values()) == {3}
    assert len({row["id"] for row in rows}) == 108
    assert len({" ".join(row["prompt"].casefold().split()) for row in rows}) == 108
    assert all("human_authored" in row["tags"] for row in rows)
    assert all("qwen_generated" not in row["tags"] for row in rows)
    assert all(row["expected_route"] == "security_blocked" for row in rows)


def test_many_shot_transcripts_and_manifest_contract(tmp_path) -> None:
    """Many-shot cases contain demonstrations and the manifest states authorship."""
    rows = build_cases()
    many_shot = [row for row in rows if row["subtype"] == "many_shot_jailbreaking"]
    assert len(many_shot) == 27
    assert all(row["prompt"].count("User:") >= 4 for row in many_shot)
    assert all(row["prompt"].count("Assistant:") >= 3 for row in many_shot)

    output = tmp_path / "wellness.jsonl"
    manifest_path = tmp_path / "wellness.manifest.json"
    build_dataset(output, manifest_path)
    manifest = json.loads(manifest_path.read_text())
    assert manifest["cases"] == 108
    assert "Human-authored" in manifest["authoring"]
    assert not any("sha" in key.casefold() for key in manifest)
