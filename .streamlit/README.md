# Streamlit configuration

## At a glance

This folder controls framework-level presentation defaults. It sits outside the
Python UI so Streamlit can load it before `streamlit_app.py` runs.

| File | Responsibility |
|---|---|
| `config.toml` | Sets the application theme and server-facing Streamlit options. |

Component layout and behavior belong in `src/ollive/ui/`; CSS belongs in that
package's `styles.css`. Do not put secrets here—Ollive reads runtime credentials
from the repository-root `.env`.
