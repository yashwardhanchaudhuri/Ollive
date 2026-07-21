"""Load YAML config + environment secrets."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_CONFIG = ROOT / "config" / "backends.yaml"


def project_root() -> Path:
    """Return the repository root used to resolve configuration and data."""
    return ROOT


def load_config(path: Path | None = None) -> dict[str, Any]:
    """Load YAML configuration and resolve its environment-backed secrets."""
    load_dotenv(ROOT / ".env", override=False)
    cfg_path = path or DEFAULT_CONFIG
    with cfg_path.open("r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)


    # Resolve env-backed URLs/keys into backend dicts for convenience
    for name, backend in cfg.get("backends", {}).items():
        for key in ("base_url_env", "api_key_env"):
            env_name = backend.get(key)
            if env_name:
                resolved_key = key.replace("_env", "")
                backend[resolved_key] = os.getenv(env_name, backend.get(resolved_key, ""))

    search = cfg.get("tools", {}).get("search_web", {})
    if search.get("api_key_env"):
        search["api_key"] = os.getenv(search["api_key_env"], "")

    return cfg


def resolve_path(relative: str) -> Path:
    """Resolve a configured repository-relative path to an absolute path."""
    path = Path(relative)
    if path.is_absolute():
        return path
    return ROOT / path
