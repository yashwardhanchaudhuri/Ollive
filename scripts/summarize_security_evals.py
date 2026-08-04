#!/usr/bin/env python3
"""Summarize Security LM ingress performance with worst-case repetition metrics."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ollive.evaluation.artifacts import write_text
from ollive.evaluation.security_summary import load_records, summarize


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse input and optional JSON output paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True, nargs="+")
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main() -> None:
    """Summarize all supplied records and optionally publish JSON output."""
    args = parse_args()
    records = [
        record
        for path in args.results
        for record in load_records(path)
    ]
    summary = summarize(records)
    rendered = json.dumps(summary, indent=2) + "\n"
    if args.output:
        write_text(args.output, rendered)
    print(rendered, end="")


if __name__ == "__main__":
    main()
