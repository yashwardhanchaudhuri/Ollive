"""Run datasets through the ingress Security LM without the answer pipeline."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import platform
import time
import uuid
from dataclasses import asdict
from datetime import datetime, timezone
from pathlib import Path

from ollive.evaluation.artifacts import atomic_text_writer, write_json
from ollive.evaluation.dataset import load_cases
from ollive.evaluation.models import EvalRecord

def run(
    dataset: Path,
    output: Path,
    repetitions: int,
    limit: int | None,
    offset: int = 0,
    security_backend: str | None = None,
) -> None:
    """Execute only the application ingress boundary for every selected case."""
    from ollive.adapters.security.checks import SECURITY_CHECK_PROMPTS
    from ollive.adapters.security.llm_security import (
        AUTHORITY_SYSTEM_PROMPT,
        SECURITY_SYSTEM_PROMPT,
    )
    from ollive.application.config import load_config
    from ollive.application.factory import build_security_broker

    cases = load_cases(dataset)
    if offset < 0:
        raise ValueError("offset must be non-negative")
    cases = cases[offset:]
    if limit is not None:
        cases = cases[:limit]

    cfg = load_config()
    if security_backend is not None:
        available = cfg.get("backends", {})
        if security_backend not in available:
            raise ValueError(f"Unknown security backend: {security_backend}")
        cfg["security"] = {
            **cfg.get("security", {}),
            **available[security_backend],
            "enabled": True,
        }
    broker = build_security_broker(cfg)
    security_model = str(cfg["security"]["model"])
    run_id = (
        datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
        + "-"
        + uuid.uuid4().hex[:8]
    )
    manifest = {
        "run_id": run_id,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "runner": "security_ingress_only",
        "dataset": str(dataset),
        "dataset_sha256": hashlib.sha256(dataset.read_bytes()).hexdigest(),
        "dataset_offset": offset,
        "dataset_cases": len(cases),
        "repetitions": repetitions,
        "python": platform.python_version(),
        "security_model": security_model,
        "security_backend": security_backend or "security",
        "security_provider": cfg["security"]["provider"],
        "security_quantization": os.environ.get("OLLIVE_VLLM_QUANTIZATION"),
        "security_prompt_sha256": hashlib.sha256(
            SECURITY_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
        "security_check_prompt_sha256": {
            name: hashlib.sha256(prompt.encode("utf-8")).hexdigest()
            for name, prompt in sorted(SECURITY_CHECK_PROMPTS.items())
        },
        "authority_prompt_sha256": hashlib.sha256(
            AUTHORITY_SYSTEM_PROMPT.encode("utf-8")
        ).hexdigest(),
    }
    manifest_path = output.with_suffix(".manifest.json")

    total = len(cases) * repetitions
    completed = 0
    with atomic_text_writer(output) as handle:
        for repetition in range(1, repetitions + 1):
            for case in cases:
                completed += 1
                print(
                    f"[{completed}/{total}] ingress r{repetition} {case.id}",
                    flush=True,
                )
                started = time.perf_counter()
                try:
                    review = broker.review_input(case.prompt)
                    blocked = not review.allowed
                    record = EvalRecord(
                        run_id=run_id,
                        case=asdict(case),
                        backend="security",
                        model=security_model,
                        repetition=repetition,
                        route="security_blocked" if blocked else "ingress_allowed",
                        security_validation_failed=blocked,
                        security_trace=[broker.trace_payload(review)],
                        usage=review.usage.model_dump(),
                    )
                except Exception as exc:
                    record = EvalRecord(
                        run_id=run_id,
                        case=asdict(case),
                        backend="security",
                        model=security_model,
                        repetition=repetition,
                        usage={"latency_ms": (time.perf_counter() - started) * 1000},
                        error=f"{type(exc).__name__}: {exc}",
                    )
                handle.write(json.dumps(record.to_dict(), ensure_ascii=False) + "\n")
    write_json(manifest_path, manifest)
    print(f"Results: {output}")
    print(f"Manifest: {manifest_path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse ingress-only evaluation arguments."""
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--offset", type=int, default=0)
    parser.add_argument("--limit", type=int)
    parser.add_argument(
        "--security-backend",
        help="Use an existing configured backend as the Security LM for this run.",
    )
    return parser.parse_args(argv)
