# Language-model adapters

## At a glance

These adapters translate Ollive messages and tool schemas into provider calls,
then normalize responses into domain models consumed by the agent loop.

| File | Responsibility |
|---|---|
| `openai_compatible.py` | Serves OpenAI and OpenAI-compatible APIs, including local vLLM. |
| `local_transformers.py` | Runs compatible Hugging Face models directly in-process. |
| `__init__.py` | Marks the model-adapter namespace. |
| `README.md` | Describes adapter selection and ownership. |

Safety routing and citation validation stay outside this layer, allowing local
and frontier models to share the same agent policy.
