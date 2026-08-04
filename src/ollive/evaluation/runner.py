"""Execute an evaluation dataset against one or more configured backends."""
from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import subprocess
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ollive.evaluation.artifacts import atomic_text_writer, write_json
from ollive.evaluation.dataset import load_cases
from ollive.evaluation.grader import grade_structure
from ollive.evaluation.models import EvalRecord

ROOT = Path(__file__).resolve().parents[3]


def revision() -> str:
    """Return the source revision recorded in run manifests."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "HEAD"], cwd=ROOT, text=True, stderr=subprocess.DEVNULL
        ).strip()
    except (OSError, subprocess.SubprocessError):
        return "unknown"


def run(
    dataset: Path,
    output: Path,
    backends: list[str],
    repetitions: int,
    limit: int | None,
    offset: int = 0,
) -> None:
    """Execute the configured workflow and return collected records."""
    from ollive.adapters.security.checks import SECURITY_CHECK_PROMPTS
    from ollive.adapters.security.llm_security import SECURITY_SYSTEM_PROMPT
    from ollive.application.config import load_config
    from ollive.application.factory import build_agent
    from ollive.application.guardrails import ROUTER_PROMPT

    cases = load_cases(dataset)
    if offset < 0:
        raise ValueError("offset must be non-negative")
    cases = cases[offset:]
    if limit is not None:
        cases = cases[:limit]
    cfg = load_config()
    run_id = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ") + "-" + uuid.uuid4().hex[:8]
    # Build provenance up front, then publish it only after the matching result
    # file completes so a failed rerun cannot pair a new manifest with old output.
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "dataset": str(dataset),
        "dataset_offset": offset,
        "dataset_cases": len(cases),
        "backends": backends,
        "repetitions": repetitions,
        "git_revision": revision(),
        "python": platform.python_version(),
        "prompt_sha256": hashlib.sha256(
            cfg.get("agent", {}).get("system_prompt", "").encode("utf-8")
        ).hexdigest(),
        "router_prompt_sha256": hashlib.sha256(ROUTER_PROMPT.encode("utf-8")).hexdigest(),
        "security_prompt_sha256": hashlib.sha256(
            SECURITY_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "security_check_prompt_sha256": {
            name: hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            for name, prompt in sorted(SECURITY_CHECK_PROMPTS.items())
        },
        "security": {
            "provider": cfg.get("security", {}).get("provider"),
            "model": cfg.get("security", {}).get("model"),
        },
        "pipeline": {
            "max_tool_rounds": cfg.get("pipeline", {}).get("max_tool_rounds"),
            "min_web_searches": cfg.get("pipeline", {}).get("min_web_searches"),
            "max_web_searches": cfg.get("pipeline", {}).get("max_web_searches"),
        },
        "config": {
            name: {
                "provider": cfg["backends"][name]["provider"],
                "model": cfg["backends"][name]["model"],
                "temperature": cfg["backends"][name].get("temperature"),
                "max_tokens": cfg["backends"][name].get("max_tokens"),
            }
            for name in backends
        },
    }
    manifest_path = output.with_suffix(".manifest.json")

    total = len(cases) * len(backends) * repetitions
    completed = 0
    with atomic_text_writer(output) as handle:
        for backend in backends:
            agent = build_agent(backend, session_id=f"eval-{run_id}-{backend}", cfg=cfg)
            for repetition in range(1, repetitions + 1):
                for case in cases:
                    completed += 1
                    print(f"[{completed}/{total}] {backend} r{repetition} {case.id}", flush=True)
                    started = time.perf_counter()
                    try:
                        # Clear dialogue, citations, and usage so one case cannot
                        # influence the next while immutable resources are reused.
                        agent.reset()
                        result = agent.chat(case.prompt)
                        record = EvalRecord(
                            run_id=run_id,
                            case=asdict(case),
                            backend=result.backend,
                            model=result.model,
                            repetition=repetition,
                            response=result.assistant_message,
                            route=result.policy_route,
                            citations=[value.model_dump() for value in result.citations],
                            invalid_citations=[value.model_dump() for value in result.invalid_citations],
                            citation_validation_failed=result.citation_validation_failed,
                            security_validation_failed=result.security_validation_failed,
                            security_trace=result.security_trace,
                            tool_trace=result.tool_trace,
                            usage=result.usage.model_dump(),
                            structural_grades=grade_structure(case, result),
                        )
                    except Exception as exc:
                        # Keep failures as records; dropping them would shrink the
                        # denominator and reward an unstable backend.
                        record = EvalRecord(
                            run_id=run_id,
                            case=asdict(case),
                            backend=backend,
                            model=cfg["backends"][backend]["model"],
                            repetition=repetition,
                            usage={"latency_ms": (time.perf_counter() - started) * 1000},
                            error=f"{type(exc).__name__}: {exc}",
                        )
                    handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    write_json(manifest_path, manifest)
    print(f"Results: {output}")
    print(f"Manifest: {manifest_path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line options for the evaluation runner."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=ROOT / "evaluation/datasets/core.v1.jsonl")
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--backends", nargs="+", default=["oss", "frontier"])
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    return parser.parse_args(argv)


if __name__ == "__main__":
    args = parse_args()
    run(
        args.dataset,
        args.output,
        args.backends,
        args.repetitions,
        args.limit,
        args.offset,
    )
