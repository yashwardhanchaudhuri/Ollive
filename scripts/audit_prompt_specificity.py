#!/usr/bin/env python3
"""Fail when model prompts contain benchmark cases or content exceptions."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ollive.evaluation.artifacts import write_text
from ollive.evaluation.prompt_audit import (
    audit_prompt_specificity,
    load_case_corpus,
    prompt_surfaces,
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse dataset, overlap-width, and output options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--datasets", type=Path, default=Path("evaluation/datasets"))
    parser.add_argument("--ngram-size", type=int, default=12)
    parser.add_argument("--output", type=Path)
    return parser.parse_args(argv)


def main() -> None:
    """Run the prompt audit, persist its report, and fail on any finding."""
    args = parse_args()
    report = audit_prompt_specificity(
        surfaces=prompt_surfaces(),
        cases=load_case_corpus(args.datasets),
        ngram_size=args.ngram_size,
    )
    rendered = json.dumps(report, indent=2)
    if args.output:
        write_text(args.output, rendered + "\n")
    print(rendered)
    if report["status"] != "pass":
        raise SystemExit(1)


if __name__ == "__main__":
    main()
