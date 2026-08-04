"""Audit model-facing prompts for benchmark-specific coupling."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Any, Iterable

from ollive.adapters.security.checks import SECURITY_CHECK_PROMPTS
from ollive.adapters.security.llm_security import AUTHORITY_SYSTEM_PROMPT
from ollive.application.config import load_config
from ollive.application.grounded_answer import SUPPORT_VERIFIER_PROMPT
from ollive.application.guardrails import (
    CONTEXT_PROMPT,
    MEDICAL_BOUNDARY_PROMPT,
    POLICIES,
    ROUTER_PROMPT,
)
from ollive.application.tools import TOOL_SCHEMAS
from ollive.evaluation.judge import JUDGE_PROMPT

TOKEN_RE = re.compile(r"[a-z0-9]+(?:'[a-z0-9]+)?")
CASE_CONDITION_PATTERNS = (
    re.compile(
        r"\bif (?:the )?(?:user|request|message|prompt) "
        r"(?:says|mentions|contains|includes|asks for)\b",
        re.IGNORECASE,
    ),
    re.compile(
        r"\bwhen (?:the )?(?:user|request|message|prompt) "
        r"(?:says|mentions|contains|includes|asks for)\b",
        re.IGNORECASE,
    ),
)
EXAMPLE_MARKERS = ("example:", "for example", "e.g.", "for instance")


def prompt_surfaces() -> dict[str, str]:
    """Return every model-facing instruction surface with a stable name."""
    cfg = load_config()
    surfaces = {
        "agent.system_prompt": str(cfg.get("agent", {}).get("system_prompt", "")),
        "security.authority_extractor_prompt": AUTHORITY_SYSTEM_PROMPT,
        "router.system_prompt": ROUTER_PROMPT,
        "context.system_prompt": CONTEXT_PROMPT,
        "medical_boundary.system_prompt": MEDICAL_BOUNDARY_PROMPT,
        "support_verifier.system_prompt": SUPPORT_VERIFIER_PROMPT,
        "evaluation_judge.system_prompt": JUDGE_PROMPT,
        "tool_schemas": json.dumps(TOOL_SCHEMAS, sort_keys=True),
    }
    surfaces.update(
        {
            f"security.check.{name}": prompt
            for name, prompt in SECURITY_CHECK_PROMPTS.items()
        }
    )
    surfaces.update(
        {
            f"route_policy.{kind.value}": policy.instruction
            for kind, policy in POLICIES.items()
        }
    )
    return surfaces


def normalized_tokens(text: str) -> tuple[str, ...]:
    """Normalize text into comparison tokens without retaining punctuation."""
    return tuple(TOKEN_RE.findall(text.casefold()))


def content_sha256(text: str) -> str:
    """Hash normalized text for exact-content deduplication."""
    normalized = " ".join(normalized_tokens(text))
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def _ngrams(tokens: tuple[str, ...], size: int) -> Iterable[str]:
    """Yield fixed-width normalized token spans."""
    for index in range(max(0, len(tokens) - size + 1)):
        yield " ".join(tokens[index : index + size])


def load_case_corpus(dataset_root: Path) -> list[dict[str, str]]:
    """Load identifiers and user-facing text from versioned JSONL datasets."""
    cases: list[dict[str, str]] = []
    for path in sorted(dataset_root.rglob("*.jsonl")):
        with path.open(encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                if not line.strip():
                    continue
                try:
                    row = json.loads(line)
                except json.JSONDecodeError:
                    continue
                if not isinstance(row, dict):
                    continue
                case_id = str(row.get("id") or f"{path.name}:{line_number}")
                for field in ("prompt", "evaluation_prompt"):
                    value = row.get(field)
                    if isinstance(value, str) and value.strip():
                        cases.append(
                            {
                                "id": case_id,
                                "field": field,
                                "text": value,
                                "path": str(path),
                            }
                        )
    return cases


def audit_prompt_specificity(
    *,
    surfaces: dict[str, str],
    cases: list[dict[str, str]],
    ngram_size: int = 12,
) -> dict[str, Any]:
    """Find literal cases, long case spans, examples, and content exceptions."""
    case_ids = {
        case["id"].casefold()
        for case in cases
        if len(case["id"].strip()) >= 6
    }
    case_ngrams: dict[str, dict[str, str]] = {}
    for case in cases:
        tokens = normalized_tokens(case["text"])
        for ngram in _ngrams(tokens, ngram_size):
            case_ngrams.setdefault(
                ngram,
                {
                    "case_id": case["id"],
                    "field": case["field"],
                    "path": case["path"],
                },
            )

    findings: list[dict[str, str]] = []
    hashes: dict[str, str] = {}
    for name, prompt in sorted(surfaces.items()):
        folded = prompt.casefold()
        hashes[name] = hashlib.sha256(prompt.encode("utf-8")).hexdigest()
        for marker in EXAMPLE_MARKERS:
            if marker in folded:
                findings.append(
                    {"surface": name, "kind": "content_example_marker", "value": marker}
                )
        for pattern in CASE_CONDITION_PATTERNS:
            match = pattern.search(prompt)
            if match:
                findings.append(
                    {
                        "surface": name,
                        "kind": "content_specific_condition",
                        "value": match.group(0),
                    }
                )
        for case_id in sorted(case_ids):
            if case_id in folded:
                findings.append(
                    {"surface": name, "kind": "benchmark_case_id", "value": case_id}
                )
        seen_spans: set[str] = set()
        for span in _ngrams(normalized_tokens(prompt), ngram_size):
            if span in case_ngrams and span not in seen_spans:
                seen_spans.add(span)
                source = case_ngrams[span]
                findings.append(
                    {
                        "surface": name,
                        "kind": "benchmark_text_overlap",
                        "value": span,
                        **source,
                    }
                )

    aggregate = json.dumps(hashes, sort_keys=True, separators=(",", ":"))
    return {
        "status": "pass" if not findings else "fail",
        "ngram_size": ngram_size,
        "prompt_surface_count": len(surfaces),
        "case_text_count": len(cases),
        "prompt_hashes": hashes,
        "prompt_set_sha256": hashlib.sha256(aggregate.encode("utf-8")).hexdigest(),
        "findings": findings,
    }
