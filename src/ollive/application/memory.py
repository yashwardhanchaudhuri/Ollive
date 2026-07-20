"""Short-term conversational memory: last N turns."""

from __future__ import annotations

from ollive.domain.models import Message, Role


class ShortTermMemory:
    def __init__(self, max_turns: int = 8) -> None:
        self.max_turns = max_turns
        self._messages: list[Message] = []

    def add(self, message: Message) -> None:
        self._messages.append(message)
        self._trim()

    def extend(self, messages: list[Message]) -> None:
        self._messages.extend(messages)
        self._trim()

    def as_list(self) -> list[Message]:
        return list(self._messages)

    def clear(self) -> None:
        self._messages.clear()

    def restore(self, messages: list[Message]) -> None:
        self._messages = list(messages)
        self._trim()

    def _trim(self) -> None:
        # Keep last N user/assistant turn-pairs roughly by counting user messages
        user_idxs = [i for i, m in enumerate(self._messages) if m.role == Role.USER]
        if len(user_idxs) <= self.max_turns:
            return
        cut = user_idxs[-self.max_turns]
        self._messages = self._messages[cut:]
