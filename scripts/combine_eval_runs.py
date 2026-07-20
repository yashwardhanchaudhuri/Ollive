#!/usr/bin/env python3
"""Combine compatible evaluation JSONL files without altering records."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--inputs", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()

    rows = []
    dataset_signatures = set()
    for path in args.inputs:
        current = [json.loads(line) for line in path.open(encoding="utf-8") if line.strip()]
        signature = tuple(row["case"]["id"] for row in current)
        dataset_signatures.add(signature)
        rows.extend(current)
    if len(dataset_signatures) != 1:
        raise SystemExit("Input runs do not contain identical ordered case IDs")

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", encoding="utf-8") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False) + "\n")
    print(f"Wrote {len(rows)} records from {len(args.inputs)} runs to {args.output}")


if __name__ == "__main__":
    main()
