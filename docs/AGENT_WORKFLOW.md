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

The central design choice is to select context, safety, and evidence boundaries before
answering. Non-substantive conversation remains natural, under-specified individualized
requests seek constraints, factual wellness content requires evidence, and medical
content stops at an application-owned boundary. The model cannot compose pharmaceutical
facts on that route.

```text
User message
    │
    ▼
Context-dependency classifier
    │
    ▼
Policy router
    ├── conversation / clarification / out of scope ──► bounded response
    ├── medical ──► urgency selector ──► application-owned response
    └── grounded wellness
            │
            ▼
      bounded query builder
            │
            ▼
       forced KB lookup
            │
            ├── material evidence gap or required web retrieval ──► one web search
            │
            ▼
      structured answer submission
            │
            ▼
      shape, bounds, and marker validation
            │
            ▼
      claim-to-source entailment validation
            ├── valid ──► render and remember
            └── invalid ──► bounded correction or withholding
```

## Why staged decisions happen first

A single universal prompt tended to produce two opposite failures: it could cite
ordinary conversation unnecessarily, or answer medical and safety-sensitive
requests too freely. Ollive therefore asks the selected model to return a small,
strict routing object before it produces the response.

A focused constrained call first decides whether prior dialogue supplies a missing
substantive subject. It receives bounded history and the current message as explicit untrusted
data and emits one boolean; no regex, keyword list, or retrieval score makes this decision.
The policy router then selects the domain route, response depth, and explicit web requirement.
Application policy makes every wellness route grounded.

## Route behavior

| Route | Why it exists | Tools | Expected response |
|---|---|---:|---|
| Conversation | Preserve natural greetings and assistant questions | No | Brief, uncited conversation |
| Wellness clarification | Avoid generic plans when personal constraints are missing | No | Two to four useful questions |
| Wellness | Ground factual lifestyle guidance | Required | Retrieved, structured, cited answer |
| Medical | Prevent substantive clinical or pharmaceutical generation | No | Application-owned boundary or urgent-help response |
| Out of scope | Keep the assistant within its supported purpose | No | Brief refusal or redirection |

## Grounded wellness execution

### 1. The application forces retrieval

On the first grounded round, the model can call only `lookup_kb`. The model may
select a document type from the live enum and a result count, but the application
controls the query.

For a self-contained request, the query is the current user message. When the context
classifier selects continuation, the application concatenates only the immediately preceding
user message with the current message. It performs no model-written query expansion, so the
original wording survives without introducing hidden facets or stale retrieved evidence.

### 2. Retrieval returns evidence objects

The local retriever embeds the query, searches paragraph vectors in FAISS, and
returns the most similar chunks. Each chunk includes its document type, title,
line positions, descriptor, text, and stable citation marker.

### 3. The agent checks evidence completeness

After local retrieval, the model submits an answer when the passages directly support the request, or calls `search_web` once when the router marks an explicit web request or a distinct factual part remains unsupported. A request for more detail alone does not justify web search. An empty
KB result forces the web path. This is a semantic decision rather than a keyword
or regular-expression rule.

If the model first submits an `evidence_limitation`, the application treats that
structured signal as partial completion and forces the single web-search round
before accepting a final answer.

Web search uses Tavily advanced extraction to obtain relevant prose rather than
bibliography-heavy snippets. It is restricted twice: Tavily receives `include_domains`
from the configured allowlist, and the adapter independently rejects off-domain URLs
and results below the configured relevance score. Tavily documents `include_domains`
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
citation syntax. It then sends only the atomic claim/source pairs to an isolated,
forced-schema entailment check. A claim passes only when its selected passage alone
supports every factual assertion; topic similarity and outside knowledge are rejected.
The application adds citation markers only after both boundaries pass.

## Correction and fail-closed behavior

When structured output is malformed or a selected passage does not entail its
claim, the application returns the precise validation error and the same evidence.
The initial draft receives at most two corrected submissions, while the complete
tool loop remains bounded by the configured maximum number of rounds.

If correction still fails but the verifier approved part of a valid structured
draft, Ollive returns an explicit exact-match limitation followed only by that supported,
cited subset. When no generated claim survives, it may show a short verbatim excerpt from
the highest-ranked retrieved source. Malformed output or absent evidence still fails
closed. Unsupported generated claims are never softened into the fallback.

## Conversation memory

Only final user and assistant messages persist. Tool payloads and model tool-call
envelopes remain in traces but are removed from conversational memory. The router sees
bounded dialogue to resolve intent. The dedicated context classifier binds the evidence
query to either the current request alone or the immediately preceding user turn plus
the current request; assistant prose never enters that query. For a grounded continuation,
answer generation receives up to the three most recent user turns for conversational
continuity. Regardless of that context, only passages returned during the current turn
can serve as evidence, so prior assistant claims and stale tool payloads cannot become sources.

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
- Entailment validation is model-based; it improves on marker provenance but still requires calibration and human review.
- The local KB limits what grounded answers can establish.
- The authoritative-domain allowlist reduces source risk but does not guarantee that
  every returned excerpt is correct, current, or sufficient for the generated claim.
- Web fallback requires `TAVILY_API_KEY`; without it, the agent can only return a
  structured evidence limitation when the KB is insufficient.
- Matched structural runs and qualitative human checks are complete; blinded case-level adjudication and repeated sampling are not reported.

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
