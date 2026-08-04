#!/usr/bin/env python3
"""Generate a reader-facing report from one evaluation run."""

from __future__ import annotations

import argparse
from pathlib import Path

from ollive.evaluation.report import generate


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse result, destination, and optional calibration paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--calibration", type=Path)
    return parser.parse_args(argv)


def main() -> None:
    """Generate and print the report path."""
    args = parse_args()
    print(generate(args.results, args.output_dir, args.calibration))


if __name__ == "__main__":
    main()
