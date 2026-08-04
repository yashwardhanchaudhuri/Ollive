"""Regression checks for evaluation script hygiene and artifact publication."""
from __future__ import annotations

import ast
from pathlib import Path

import pytest

from ollive.evaluation.artifacts import (
    atomic_text_writer,
    load_jsonl,
    write_jsonl,
)


ROOT = Path(__file__).resolve().parents[1]


def test_atomic_writers_publish_complete_content(tmp_path: Path) -> None:
    """Successful writes replace their destination with complete content."""
    target = tmp_path / "nested" / "result.txt"
    with atomic_text_writer(target) as handle:
        handle.write("complete\n")
    assert target.read_text(encoding="utf-8") == "complete\n"

    jsonl = tmp_path / "records.jsonl"
    rows = [{"id": "one"}, {"id": "two", "text": "café"}]
    assert write_jsonl(jsonl, rows) == 2
    assert load_jsonl(jsonl) == rows


def test_atomic_writer_preserves_destination_on_failure(tmp_path: Path) -> None:
    """A failed generation leaves the last complete artifact untouched."""
    target = tmp_path / "result.txt"
    target.write_text("previous\n", encoding="utf-8")
    with pytest.raises(RuntimeError, match="generation failed"):
        with atomic_text_writer(target) as handle:
            handle.write("partial")
            raise RuntimeError("generation failed")
    assert target.read_text(encoding="utf-8") == "previous\n"
    assert not list(tmp_path.glob(".result.txt.*.tmp"))


def _is_main_guard(node: ast.stmt) -> bool:
    """Return whether a statement is the conventional module entry guard."""
    return (
        isinstance(node, ast.If)
        and "__name__" in ast.unparse(node.test)
        and "__main__" in ast.unparse(node.test)
    )


def test_scripts_are_import_safe_and_do_not_patch_sys_path() -> None:
    """Every script keeps argument parsing and execution behind a main guard."""
    for path in sorted((ROOT / "scripts").glob("*.py")):
        source = path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(path))
        assert any(_is_main_guard(node) for node in tree.body), path
        for statement in tree.body:
            if isinstance(statement, (ast.FunctionDef, ast.ClassDef)) or _is_main_guard(statement):
                continue
            calls = (node for node in ast.walk(statement) if isinstance(node, ast.Call))
            assert not any(
                (isinstance(call.func, ast.Name) and call.func.id == "parse_args")
                or (isinstance(call.func, ast.Attribute) and call.func.attr == "parse_args")
                for call in calls
            ), path
        assert "sys.path" not in source, path
