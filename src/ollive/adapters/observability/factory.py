"""Build tracer from config — local OSS by default, Langfuse optional."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from ollive.adapters.observability.local_tracer import LocalFileTracer
from ollive.ports.tracer import TracerPort


def build_tracer_from_config(
    obs_cfg: dict[str, Any] | None = None,
    *,
    project_root: Path | None = None,
) -> TracerPort:
    obs = obs_cfg or {}
    if not obs.get("enabled", True):
        from ollive.adapters.observability.langfuse_tracer import NoOpTracer

        return NoOpTracer()

    provider = str(obs.get("provider", "local")).lower()
    root = project_root or Path(__file__).resolve().parents[4]

    if provider == "langfuse":
        from ollive.adapters.observability.langfuse_tracer import build_tracer

        return build_tracer(enabled=True)

    # Default: local JSONL — fully OSS, zero keys
    trace_dir = obs.get("trace_dir", "data/traces")
    path = Path(trace_dir)
    if not path.is_absolute():
        path = root / path
    return LocalFileTracer(path)
