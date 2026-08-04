# Capability ports

## At a glance

Ports state what the application needs while hiding how a vendor or library
provides it. They make the agent independently testable and adapters replaceable.

| File | Responsibility |
|---|---|
| `llm.py` | Defines chat completion with messages, tools, and normalized usage. |
| `security.py` | Defines the independent runtime security-review capability. |
| `retriever.py` | Defines evidence search and document-type discovery. |
| `web_search.py` | Defines bounded external search results. |
| `tracer.py` | Defines model, tool, and turn observability events. |
| `__init__.py` | Marks the port namespace. |
| `README.md` | Explains interface ownership. |

Application code imports these contracts; concrete implementations live under
