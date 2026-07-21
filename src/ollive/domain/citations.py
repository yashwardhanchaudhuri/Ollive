"""Citation parsing and validation helpers."""

from __future__ import annotations

import re

from ollive.domain.models import Citation

# [diet:L9:portion-control-satiety] or [diet:L9-L10:portion-control-satiety]
CITATION_RE = re.compile(
    r"\[(?P<doc_type>[a-z0-9_]+):L(?P<start>\d+)(?:-L?(?P<end>\d+))?:(?P<descriptor>[a-z0-9\-]+)\]",
    re.IGNORECASE,
)


def slugify_descriptor(text: str, max_words: int = 5) -> str:
    """Create the bounded descriptor stored with an indexed paragraph."""
    words = re.findall(r"[a-zA-Z0-9]+", text.lower())
    if not words:
        return "chunk"
    return "-".join(words[:max_words])


def parse_citations(text: str) -> list[Citation]:
    """Extract syntactically valid internal markers from rendered answer text."""
    found: list[Citation] = []
    for match in CITATION_RE.finditer(text):
        start = int(match.group("start"))
        end_raw = match.group("end")
        end = int(end_raw) if end_raw else start
        found.append(
            Citation(
                doc_type=match.group("doc_type").lower(),
                line=start,
                end_line=end,
                descriptor=match.group("descriptor").lower(),
            )
        )
    return found


def validate_citations(
    claimed: list[Citation],
    allowed: list[Citation],
) -> tuple[list[Citation], list[Citation]]:
    """Return (valid, invalid) against tool-returned citations."""
    allowed_keys = {
        (c.doc_type.lower(), c.line, c.descriptor.lower()) for c in allowed
    }
    # Also allow end_line variants by start line + descriptor
    allowed_keys |= {
        (c.doc_type.lower(), c.line, c.descriptor.lower(), c.end_line or c.line)
        for c in allowed
    }
    valid: list[Citation] = []
    invalid: list[Citation] = []
    for c in claimed:
        key = (c.doc_type.lower(), c.line, c.descriptor.lower())
        if key in {(a.doc_type.lower(), a.line, a.descriptor.lower()) for a in allowed}:
            # Enrich with text from allowed set when possible
            for a in allowed:
                if (
                    a.doc_type.lower() == c.doc_type.lower()
                    and a.line == c.line
                    and a.descriptor.lower() == c.descriptor.lower()
                ):
                    valid.append(a)
                    break
            else:
                valid.append(c)
        else:
            invalid.append(c)
    return valid, invalid
