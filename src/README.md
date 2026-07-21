# Python source root

## At a glance

This is the packaging boundary for importable code. The `src` layout prevents
accidental imports from the repository root and mirrors an installed package.

| Entry | Responsibility |
|---|---|
| `ollive/` | Contains the complete application package. |
| `README.md` | Explains the packaging boundary. |

`pyproject.toml` discovers packages here. Runtime data, scripts, tests, and
reports stay outside because they are not application modules.
