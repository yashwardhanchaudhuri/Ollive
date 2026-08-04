#!/usr/bin/env python3
"""Score non-blocked public attacks with the published StrongREJECT evaluator."""
from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Any

from ollive.evaluation.artifacts import atomic_text_writer, load_jsonl


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse the run, evaluator, judge model, and output options."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--results", type=Path, nargs="+", required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument(
        "--evaluator",
        choices=("strongreject_rubric", "strongreject_finetuned", "harmbench"),
        default="strongreject_rubric",
    )
    parser.add_argument("--judge-model")
    return parser.parse_args(argv)


def main() -> None:
    """Assign zero to ingress blocks and judge every attack that reached downstream."""
    args = parse_args()
    try:
        from strong_reject.evaluate import evaluate
    except ImportError as exc:
        raise SystemExit(
            "Install pinned StrongREJECT in an isolated evaluation environment; "
            "see scripts/README.md"
        ) from exc

    with atomic_text_writer(args.output) as handle:
        records = (
            record
            for results_path in args.results
            for record in load_jsonl(results_path)
        )
        for record in records:
            case = record.get("case", {})
            if "attack" not in case.get("tags", []):
                continue
            blocked = record.get("route") == "security_blocked"
            result: dict[str, Any] = {
                "run_id": record.get("run_id"),
                "case_id": case.get("id"),
                "backend": record.get("backend"),
                "repetition": record.get("repetition"),
                "method": case.get("provenance", {}).get("method"),
                "evaluator": args.evaluator,
                "gate_blocked": blocked,
            }
            if blocked:
                result["score"] = 0.0
            elif record.get("error"):
                result["score"] = None
                result["error"] = record["error"]
            else:
                kwargs = {}
                if args.judge_model and args.evaluator == "strongreject_rubric":
                    kwargs["models"] = [args.judge_model]
                scored = evaluate(
                    case.get("evaluation_prompt") or case.get("prompt", ""),
                    record.get("response", ""),
                    [args.evaluator],
                    **kwargs,
                )[0]
                result.update(scored)
            handle.write(json.dumps(result, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
