# Agent workflow

| Field | Value |
|---|---|
| Objective | Explain how one user message becomes a bounded, grounded Ollive response |
| Audience | Developers, reviewers, and evaluators |
| Status | Describes the current production workflow |
| Supporting code | application/agent.py, application/guardrails.py, application/tools.py |

## At a glance

Ollive uses one orchestrating agent. It makes several constrained model calls,
but those calls are stages of one workflow rather than independent agents.

The central design choice is to select a safety and evidence boundary before
answering. A greeting should remain conversational, a vague personalized request
should ask for context, a factual wellness answer should retrieve evidence, and
a medical request should stop at the medical boundary.

```text
User message
    │
    ▼
Semantic policy route
    ├── conversation ───────────────► natural answer
    ├── wellness clarification ─────► ask for missing context
    ├── medical boundary ───────────► safe boundary response
    ├── out of scope ───────────────► brief redirection
    └── grounded wellness
            │
            ▼
       forced KB lookup
            │
            ▼
      evidence completeness
        ├── sufficient ─────────────► structured answer submission
        └── material gap ───────────► one authoritative web search
                                           │
                                           ▼
                                  structured answer submission
            │
            ▼
      shape + citation validation
            ├── valid ──────────────► render and remember
            └── invalid ────────────► bounded correction or withholding
```

## Why routing happens first

A single universal prompt tended to produce two opposite failures: it could cite
ordinary conversation unnecessarily, or answer medical and safety-sensitive
requests too freely. Ollive therefore asks the selected model to return a small,
strict routing object before it produces the response.

The router receives recent dialogue only to resolve follow-ups. Alongside the route and
grounding decision, it selects whether retrieval needs recent user context and whether
the user explicitly requested a detailed answer. It cannot choose arbitrary values, and
malformed output falls back to a no-tool, out-of-scope policy.

## Route behavior

| Route | Why it exists | Tools | Expected response |
|---|---|---:|---|
| Conversation | Preserve natural greetings and assistant questions | No | Brief, uncited conversation |
| Wellness clarification | Avoid generic plans when personal constraints are missing | No | Two to four useful questions |
| Wellness | Ground factual lifestyle guidance | Required | Retrieved, structured, cited answer |
| Medical | Prevent diagnosis, prescribing, dosing, and dangerous clinical guidance | No | Boundary or urgent-help response |
| Out of scope | Keep the assistant within its supported purpose | No | Brief refusal or redirection |

A wellness route can also disable tools for a purely non-factual boundary
response. This keeps refusal text from acquiring irrelevant citations.

## Grounded wellness execution

### 1. The application forces retrieval

On the first grounded round, the model can call only `lookup_kb`. The model may
select a document type from the live enum and a result count, but the application
controls the query.

For an independent request, the query is the current user message. For a dependent
follow-up such as “elaborate,” the application concatenates recent user-authored
messages with the current message. It performs no model-written query expansion, so the
original topic survives without introducing hidden facets.

### 2. Retrieval returns evidence objects

The local retriever embeds the query, searches paragraph vectors in FAISS, and
returns the most similar chunks. Each chunk includes its document type, title,
line positions, descriptor, text, and stable citation marker.

### 3. The agent checks evidence completeness

After local retrieval, the model must choose one of two constrained actions. It
submits an answer when the passages directly support the material parts of the
request, or calls `search_web` once when a material detail is missing. An empty
KB result forces the web path. This is a semantic decision rather than a keyword
or regular-expression rule.

If the model first submits an `evidence_limitation`, the application treats that
structured signal as partial completion and forces the single web-search round
before accepting a final answer.

Web search is restricted twice: Tavily receives `include_domains` from the
configured allowlist, and the adapter independently rejects off-domain URLs and
results below the configured relevance score. Tavily documents `include_domains`
in its [Search API reference](https://docs.tavily.com/documentation/api-reference/endpoint/search).
The model cannot add domains through tool arguments.

Each accepted result becomes evidence with a title, excerpt, original URL, and
application-generated citation marker. After web search, another search is not
offered; structured finalization is required.

### 4. Free-text finalization is disabled

`submit_grounded_answer` contains the exact KB and web markers returned during
the current turn. Standard turns permit at most three items; an explicit request for detail permits up to
five. An item is either a
supported claim tied to one returned marker or an evidence limitation with no
citation. If both evidence sources are empty, only a structured limitation can
pass validation.

### 5. The application validates before display

Validation checks shape, field bounds, marker provenance, limitation count, and
citation syntax. The application adds citation markers itself, so the model
cannot type a plausible-looking replacement into the prose.

This proves that a marker came from the current retrieval. It does not
independently prove that the source passage entails every word of the claim.

## Correction and fail-closed behavior

When structured output is malformed, the application returns the validation
error to the model and requests a corrected submission using the same evidence.
The entire loop is bounded by the configured maximum number of rounds.

If correction still fails, Ollive withholds the answer. This design prefers an
explicit quality failure over displaying unsupported wellness guidance.

## Conversation memory

Only final user and assistant messages persist. Tool payloads and model tool-call
envelopes remain in traces but are removed from conversational memory. The router sees
that bounded dialogue to resolve intent; grounded answer generation receives user turns
and current retrieval, but excludes prior assistant prose so stale claims cannot be
reused as evidence.

This avoids two common problems:

- stale passages appearing as evidence for a later question;
- token growth caused by carrying full retrieval payloads across turns.

If an exception interrupts a turn, memory rolls back to its previous state.

## Backend variation

The workflow is backend-independent.

| Backend | Model access | Important variation |
|---|---|---|
| OSS | Qwen 3.5 9B through local vLLM | Local service availability and tool-schema adherence |
| Frontier | OpenAI-compatible GPT endpoint | Remote latency, provider behavior, and no temperature field when unsupported |

Both backends receive the same route schemas, tool schemas, policies, memory, and
retrieval evidence. A fair comparison therefore changes the model backend while
freezing the surrounding workflow.

## What current evidence suggests

Observed evaluation results show that explicit routing and forced tool policies
substantially improve structural compliance. They also show that stricter
citation handling can increase withheld answers. The useful design lesson is not
that more restriction is always better: grounding must remain direct and
conversational, or safety improves while usefulness declines.

See the [consolidated evaluation report](../evaluation/REPORT.md) for the
measurements and limitations.

## Scope and limitations

- This is one agent with staged model calls, not a multi-agent deliberation system.
- Routing is model-based and can select a defensible route different from a test label.
- Marker validation proves provenance, not semantic entailment.
- The local KB limits what grounded answers can establish.
- The authoritative-domain allowlist reduces source risk but does not guarantee that
  every returned excerpt is correct, current, or sufficient for the generated claim.
- Web fallback requires `TAVILY_API_KEY`; without it, the agent can only return a
  structured evidence limitation when the KB is insufficient.
- Matched Qwen and frontier structural runs are complete; human semantic review and
  repeated sampling remain pending.

## Code map

| Responsibility | Source |
|---|---|
| Main loop and memory cleanup | `src/ollive/application/agent.py` |
| Semantic routes and policies | `src/ollive/application/guardrails.py` |
| Tool schemas and execution | `src/ollive/application/tools.py` |
| Grounded answer contract | `src/ollive/application/grounded_answer.py` |
| Retrieval and indexing | `src/ollive/adapters/rag/` |
| Backend adaptation | `src/ollive/adapters/llm/` |
| Citation parsing | `src/ollive/domain/citations.py` |
| Streamlit rendering | `src/ollive/ui/streamlit_app.py` |
