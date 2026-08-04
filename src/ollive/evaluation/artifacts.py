"""Reliable readers and atomic writers for generated evaluation artifacts."""

from __future__ import annotations

from contextlib import contextmanager
import json
import os
from pathlib import Path
import tempfile
from typing import Any, Iterable, Iterator, TextIO


@contextmanager
def atomic_output_path(path: Path) -> Iterator[Path]:
    """Yield a sibling temporary path and atomically publish it on success."""
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
    )
    os.close(descriptor)
    temporary = Path(temporary_name)
    try:
        yield temporary
        os.replace(temporary, path)
    except BaseException:
        temporary.unlink(missing_ok=True)
        raise


@contextmanager
def atomic_text_writer(path: Path) -> Iterator[TextIO]:
    """Yield a UTF-8 writer whose complete contents replace the destination."""
    with atomic_output_path(path) as temporary:
        with temporary.open("w", encoding="utf-8", newline="\n") as handle:
            yield handle
            handle.flush()
            os.fsync(handle.fileno())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load non-empty UTF-8 JSONL records from a path."""
    with path.open(encoding="utf-8") as handle:
        return [json.loads(line) for line in handle if line.strip()]


def write_jsonl(path: Path, rows: Iterable[dict[str, Any]]) -> int:
    """Atomically write JSONL records and return their count."""
    count = 0
    with atomic_text_writer(path) as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
            count += 1
    return count


def write_json(path: Path, value: Any) -> None:
    """Atomically write one indented JSON document with a trailing newline."""
    write_text(path, json.dumps(value, indent=2, ensure_ascii=False) + "\n")


def write_text(path: Path, value: str) -> None:
    """Atomically write UTF-8 text."""
    with atomic_text_writer(path) as handle:
        handle.write(value)


def file_sha256(path: Path) -> str:
    """Return the SHA-256 digest of a file without loading it into memory."""
    import hashlib

    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_english(text: str) -> bool:
    """Return whether the optional deterministic detector identifies English."""
    try:
        from langdetect import DetectorFactory, LangDetectException, detect
    except ImportError as exc:
        raise RuntimeError(
            "Security corpus builders require the evaluation extra: "
            "python -m pip install -e '.[evaluation]'"
        ) from exc

    DetectorFactory.seed = 0
    try:
        return detect(text) == "en"
    except LangDetectException:
        return False
