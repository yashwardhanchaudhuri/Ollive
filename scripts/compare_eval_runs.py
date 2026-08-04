#!/usr/bin/env python3
"""Compare two compatible evaluation runs."""

from __future__ import annotations

import argparse
from pathlib import Path

from ollive.evaluation.compare import generate_comparison


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse baseline, candidate, and output paths."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--baseline", type=Path, required=True)
    parser.add_argument("--candidate", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    return parser.parse_args(argv)


def main() -> None:
    """Generate and print the comparison report path."""
    args = parse_args()
    print(generate_comparison(args.baseline, args.candidate, args.output_dir))


if __name__ == "__main__":
    main()
