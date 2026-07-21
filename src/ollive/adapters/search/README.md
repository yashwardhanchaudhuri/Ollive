# External search adapters

## At a glance

Web search supplements the local KB when a material request remains unanswered.
Results are normalized for the tool router.

| File | Responsibility |
|---|---|
| `tavily_search.py` | Queries Tavily, enforces trusted domains and scores, and provides a disabled null implementation. |
| `__init__.py` | Marks the search-adapter namespace. |
| `README.md` | Explains the bounded-search role. |

Trusted domains come from `config/backends.yaml`; returned evidence must retain
its URL-backed citations.
