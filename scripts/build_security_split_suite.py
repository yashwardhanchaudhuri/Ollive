#!/usr/bin/env python3
"""Build the original group-separated security train/dev/test corpus."""

from __future__ import annotations

import json

from ollive.evaluation.security_corpus import build_split, parse_args


def main() -> None:
    """Build the configured split and print a compact artifact summary."""
    args = parse_args()
    manifest = build_split(args)
    print(
        json.dumps(
            {
                "total_records": manifest["selection"]["total_records"],
                "artifacts": manifest["artifacts"],
                "manifest": str(args.manifest),
                "case_text_printed": False,
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()
