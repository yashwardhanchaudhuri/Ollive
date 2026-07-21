# Streamlit user interface

## At a glance

The UI presents the agent without owning wellness policy. It manages browser
session state, backend switching, chat rendering, and citation drawers.

| File | Responsibility |
|---|---|
| `streamlit_app.py` | Application entry point; builds session agents, handles chat turns, and renders sources and usage. |
| `styles.css` | Holds visual layout and component styling outside Python. |
| `__init__.py` | Marks the UI namespace. |
| `README.md` | Explains presentation-layer ownership. |

Changing a backend starts a fresh model-owned chat. Routing, retrieval, and
grounding changes belong in `application/`, not in Streamlit callbacks.
