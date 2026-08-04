#!/usr/bin/env python3
"""Combine compatible evaluation JSONL files without altering records."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Any

from ollive.evaluation.artifacts import load_jsonl, write_jsonl


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse compatible input runs and their combined destination."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    """Validate compatible case order and combine evaluation run records."""
    args = parse_args()
    rows: list[dict[str, Any]] = []
    dataset_signatures: set[tuple[str, ...]] = set()
    for path in args.inputs:
        current = load_jsonl(path)
        signature = tuple(row["case"]["id"] for row in current)
        dataset_signatures.add(signature)
        rows.extend(current)
    if len(dataset_signatures) != 1:
        raise SystemExit("Input runs do not contain identical ordered case IDs")

    written = write_jsonl(args.output, rows)
    print(f"Wrote {written} records from {len(args.inputs)} runs to {args.output}")


if __name__ == "__main__":
    main()
