from ollive.application.memory import ShortTermMemory
from ollive.domain.models import Message, Role


def test_memory_trims_to_last_n_user_turns():
    mem = ShortTermMemory(max_turns=2)
    for i in range(5):
        mem.add(Message(role=Role.USER, content=f"u{i}"))
        mem.add(Message(role=Role.ASSISTANT, content=f"a{i}"))
    texts = [m.content for m in mem.as_list()]
    assert texts[0] == "u3"
    assert "u0" not in texts
    assert "u4" in texts
