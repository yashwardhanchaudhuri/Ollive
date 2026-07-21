"""Short-term conversational memory: last N turns."""

from __future__ import annotations

from ollive.domain.models import Message, Role


class ShortTermMemory:
    def __init__(self, max_turns: int = 8) -> None:
        """Initialize ShortTermMemory with its runtime collaborators."""
        self.max_turns = max_turns
        self._messages: list[Message] = []

    def add(self, message: Message) -> None:
        """Append one message and enforce the configured turn bound."""
        self._messages.append(message)
        self._trim()

    def extend(self, messages: list[Message]) -> None:
        """Append messages and enforce the configured turn bound."""
        self._messages.extend(messages)
        self._trim()

    def as_list(self) -> list[Message]:
        """Return a copy so callers cannot mutate memory accidentally."""
        return list(self._messages)

    def clear(self) -> None:
        """Remove all persisted dialogue from the current session."""
        self._messages.clear()

    def restore(self, messages: list[Message]) -> None:
        """Replace dialogue from a checkpoint and reapply the bound."""
        self._messages = list(messages)
        self._trim()

    def _trim(self) -> None:
        """Keep only the newest configured number of user-led turns."""
        # Count user messages so trimming starts on a complete user-led turn.
        user_idxs = [i for i, m in enumerate(self._messages) if m.role == Role.USER]
        if len(user_idxs) <= self.max_turns:
            return
        cut = user_idxs[-self.max_turns]
        self._messages = self._messages[cut:]
