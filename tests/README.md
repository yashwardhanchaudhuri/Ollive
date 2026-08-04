# Test suite

## At a glance

Tests exercise behavior at architectural seams with deterministic substitutes,
so most safety and grounding regressions require no live model or network.

| File | Responsibility |
|---|---|
| `test_agent_grounding.py` | Covers tool loops, contextual follow-ups, partial evidence, web completion, failure closure, and memory rollback. |
| `test_citations.py` | Covers marker parsing/validation and bounded Tavily results. |
| `test_documentation.py` | Enforces reader orientation, link integrity, docstrings, and folder-guide coverage. |
| `test_evaluation.py` | Covers dataset shape, balance, strict loading, and structural grading. |
| `test_grounded_answer.py` | Covers answer-schema bounds, item shape, and citation-marker provenance. |
| `test_guardrails.py` | Covers semantic route enums, boundaries, and malformed-output closure. |
| `test_indexer.py` | Covers filename types, paragraph chunks, corpus indexing, and README exclusion. |
| `test_memory.py` | Covers bounded dialogue retention. |
| `test_request_limits.py` | Covers session request windows, message/context caps, reset behavior, and pre-model enforcement. |
| `test_pipeline_architecture.py` | Keeps the agent as a facade and tool execution inside the evidence stage. |
| `test_script_quality.py` | Covers atomic artifact publication and import-safe, path-clean script entry points. |
| `test_security.py` | Covers typed authority extraction, direct and delimiter attacks, benign contrasts, immutable provenance, fail-closed verdicts, mandatory evidence gates, and web-search caps. |
| `test_security_controls.py` | Covers deterministic persona-authority enforcement and output-canary leak blocking. |
| `test_wellness_adversarial.py` | Covers authored MECE balance, uniqueness, many-shot structure, manifest design, and non-model provenance. |
| `README.md` | Explains test responsibilities. |

Run `python -m pytest -q` from the repository root. Live service checks are
operational verification and do not replace these deterministic tests.
