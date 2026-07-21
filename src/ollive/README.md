# Ollive application package

## At a glance

Dependencies point inward: domain types sit at the center, ports define needed
capabilities, adapters implement them, application code coordinates behavior,
and the UI presents results.

| Entry | Responsibility |
|---|---|
| `__init__.py` | Marks the package and carries its package description. |
| `domain/` | Infrastructure-free models and citation rules. |
| `ports/` | Interfaces consumed by orchestration. |
| `adapters/` | Model, retrieval, search, and tracing implementations. |
| `application/` | Agent loop, policies, memory, grounding, and composition. |
| `evaluation/` | Reusable evaluation and reporting logic. |
| `ui/` | Streamlit presentation and interaction state. |
| `README.md` | Maps these package boundaries. |

Domain code must not import adapters or UI; that keeps behavior testable without
