"""Security review port for an independently configured model."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from ollive.domain.security import SecurityReview, SecurityStage


class SecurityGatePort(ABC):
    """Review untrusted runtime data without generating user-facing content."""

    @abstractmethod
    def review(
        self,
        *,
        stage: SecurityStage,
        payload: dict[str, Any],
        item_ids: list[str] | None = None,
    ) -> SecurityReview:
        """Return one constrained, fail-closed security verdict."""
        ...
