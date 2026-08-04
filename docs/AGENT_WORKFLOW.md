# Agent workflow

| Field | Value |
|---|---|
| Objective | Explain how one user message crosses runtime security, routing, evidence, grounding, and output boundaries |
| Audience | Developers, reviewers, and evaluators |
| Status | Best measured concise five-guard profile restored; fused and expanded variants rejected |
| Supporting code | `application/pipeline/`, `application/security.py`, `adapters/security/llm_security.py` |

## At a glance

Ollive uses one answer-model workflow and a separate Security LM. Before either
model runs, application code enforces a per-session request window plus current-
message and accumulated-context size budgets. The Security LM never answers the
user and has no retrieval or web tools. At ingress, one constrained call extracts
authority semantics. The original envelope then passes through direct injection,
delimiter/role confusion, Persona/DAN permission escalation, harmful action, and
individualized medical guards in that fixed order. Each specialist receives one
concise risk definition and its nearest allowed boundary, returns one decision and
trust score, and stops the sequence on an owned block. Application code withholds
blocked input from the answer model.

![Ollive runtime workflow](agent_workflow.svg)

The runtime invariant is simple: no external user, memory, KB, or web content reaches
the main answer pipeline without a valid security decision. Missing, malformed, or
unavailable model verdicts fail closed.

## Code-level pipeline

`WellnessAgent` is now only a session facade. It supplies an immutable dialogue
snapshot to `RuntimePipeline`, then stores the finalized user/assistant pair. The
pipeline owns the only legal execution order:

    Request/context admission budget
      → IngressStage
      → RoutingStage
      → MedicalStage, NonGroundedStage, or GroundedStage
          → EvidenceStage for every KB/web call
      → OutputStage

`TurnState` carries typed data between stages. `EvidenceStage` is the only pipeline
module permitted to execute external tools; it sends raw results to
`SecurityBroker`, reconstructs safe tool messages from approved citations, and only
then appends them to answer-model context.

## Trust boundaries

| Data | Treatment before the answer model |
|---|---|
| Current user message | Session frequency/message/context budgets → authority extraction → direct injection → delimiter/role confusion → Persona/DAN → harm → medical |
| Selected conversation context | Source-separated envelopes, composed-authority extraction, then boundary → harm checks |
| KB passages | Instruction-injection check, then harmful-content check per result |
| Web results | Domain/relevance filter, then instruction-injection and harmful-content checks |
| Combined KB and web evidence | Cross-fragment boundary check, then cross-fragment harm check |
| Proposed response | Grounding checks, then integrity → harm → medical output checks |
| System policy and application schemas | Trusted, application-owned control data |

Authority extraction is typed independently from `allow` or `block`. Code blocks an
executed privileged override, disclosure, impersonation, persistence request, or
unauthorized action only when the extraction cites an exact received span. If the
extractor copies that span incorrectly, its opinion cannot block; the ordered focused
checks still run on the original envelope. Evidence checks additionally return
`allow` or `exclude` for every supplied item. The application combines exclusions
across completed checks and rebuilds tool messages from approved citation objects,
so raw provider payloads never enter the answer-model message list.

## Runtime sequence

### 1. Input and context gates

The session admits at most 12 requests per 60 seconds, 20,000 characters in one
message, and 48,000 characters across the bounded current context. A limit block
occurs before either model call and is not stored in dialogue memory. This constrains
rapid repeated attempts and single- or multi-turn many-shot loading; it does not
semantically classify the remaining shorter attacks.

The application assigns the current message untrusted provenance outside its text,
normalizes invisible Unicode formatting without removing punctuation, and sends that
inspection envelope to the authority extractor. The same envelope then enters the
direct-injection guard, delimiter/role-confusion guard, Persona/DAN permission guard,
harm guard, and medical guard. An anchored authority finding is assigned to its
owning guard, so code enforcement and trace output preserve the same class order.
The first owned block ends the sequence; an allow records the lowest completed check
score. Input above `security.max_input_chars` is blocked before any model call.
Bounded dialogue uses its separate composed-context authority and boundary/harm
review only when prior dialogue exists. With no prior dialogue the application
records `no_prior_context`.
Blocked messages are not written into agent memory.

The context-dependency classifier then decides whether retrieval uses the current message
alone or the immediately preceding user turn plus the current message. Grounded answer
generation may receive up to the three most recent approved user turns. Historical tool
payloads never enter conversation memory.

### 2. Policy routing

The main model selects one constrained route:

| Route | Evidence tools | Response behavior |
|---|---:|---|
| Conversation | No | Brief conversational response |
| Wellness clarification | No | Two to four material questions |
| Medical | No | Application-owned standard or urgent boundary |
| Out of scope | No | Brief refusal or wellness redirection |
| Wellness | Required | Mandatory KB and web evidence pipeline |

Every proposed response, including non-grounded responses, passes the final Security LM
alignment gate before rendering.

### 3. Mandatory grounded evidence

Every wellness route performs these steps in application-enforced order:

1. `lookup_kb` using the application-selected query.
2. Security LM review of every returned KB citation.
3. At least one `search_web` call.
4. Tavily trusted-domain and relevance filtering.
5. Security LM review of every accepted web citation.
6. Security LM review of the combined approved KB and web set.

The first web search is mandatory even when the KB appears sufficient. If the answer model
submits an evidence limitation while attempts remain, the application forces another
search. The second and third searches must target the remaining material gap. A hard
application limit prevents a fourth search. After the third attempt, unresolved scope must
remain an explicit evidence limitation.

Security rejection of a passage excludes it. The answer model receives a newly serialized
empty or reduced evidence result, never the rejected text. A combined-evidence block also
prevents newly retrieved web content from being added to the model context.

### 4. Structured grounding

Free-text completion is disabled after retrieval. The answer model must call
`submit_grounded_answer` with bounded atomic items. A supported claim selects one marker
from evidence approved during the current turn. Unsupported scope uses the no-citation
limitation sentinel.

Application validation then checks:

- strict JSON shape and item bounds;
- marker membership in the current approved evidence set;
- citation grammar and provenance;
- isolated claim-to-passage entailment.

Malformed output receives at most two corrections using the same approved evidence.
Verifier-approved claims may survive as a best-effort answer; unsupported claims are never
softened into uncited prose.

### 5. Final alignment gate

After grounding, the separate Security LM receives the current request, selected route,
approved evidence, safe tool trace, and proposed response as one bounded payload. It
checks integrity, harmful capability, and individualized medical risk in separate
ordered turns. It cannot rewrite the answer. Application code either renders the
already-grounded response or replaces it with an application-owned rejection.

## Fail-closed behavior

The following conditions never default to approval:

- request-frequency, current-message, or accumulated-context budget exceeded;
- Security LM timeout or adapter exception;
- missing, free-text, malformed, or incorrectly typed verdict;
- missing or reordered evidence item decisions;
- answer-model tool calls that were not offered;
- more than three web calls;
- malformed grounded-answer objects;
- stale or fabricated citation markers;
- unsupported claim/source pairs;
- final output rejection.

Security events are recorded separately from tool traces. The UI does not expose internal
risk flags or classifier reasoning.

## Model separation

`security.model` is mandatory. The Security LM runs in a separate adapter with constrained
prompts, forced schemas, and no answer or retrieval tools; it may share model weights
with the selected answer model. The composition root rejects disabled or missing
security configuration at startup.

This is logical adapter separation. Operators must still decide whether production requires
separate providers, credentials, processes, or hardware.

## Evaluation boundary

Deterministic tests cover request/context limits, malformed extraction and verdict
closure, semantic direct override, self-declared delimiter boundaries, quoted and
persona contrasts, exact-span anchoring, immutable context provenance, blocked-input
isolation, mandatory KB-plus-web execution, every runtime gate, and the three-search
cap. The frozen broader Qwen suite separately measured 44/79 direct injections,
36/78 delimiter breaks, 180/200 DAN/persona attacks, and 30/30 many-shot cases
constructed as ten each at 8, 32, and 64 shots. Deepset Prompt Injections supplied
direct and delimiter cases; disjoint hash-sorted JailbreakHub rows supplied persona
and many-shot cases. At the current 20,000-character cap, 27/30 archived many-shot
prompts exceed the input budget; this is retrospective size analysis, not a rerun.
On the 1,213-case Qwen regression, attack blocking rose from 64.9% to 74.8% and
fail-closed attack blocks fell from 65 to zero, but benign blocking rose from 11.3%
to 16.8%. Because the same cases informed the refactor and comparison, they are now
development evidence.
On the same consumed 357-case subset, the earlier grouped sequential GPT design
blocked 89/157 attacks and 68/200 benign controls. The concise class-specific sequence
blocked 117/157 attacks (74.5%) and 69/200 benign controls (34.5%): 53/79 direct
and 64/78 delimiter attacks. It completed with zero execution errors and used
1,655,506 tokens. Persona/DAN produced 40 of the 69 benign blocks. A later
expanded-variation rerun blocked only 100/157 attacks and 70/200 benign controls
while using 2,115,220 tokens, so that prompt version was rejected. The runtime now
uses the concise profile whose per-guard hashes match the 117/157 benchmark manifests
exactly.

## Scope and limitations

This implementation protects runtime traffic only. KB and web ingestion security is
future scope. The Security LM is a probabilistic classifier, not a formal sandbox:
it can miss novel attacks or reject harmless text, and its effectiveness depends on
model choice, calibration, provider independence, and adversarial testing. The
implemented limiter is local to one agent/browser session. Identity-aware global
limiting, authentication, audit review, and infrastructure isolation remain separate
deployment controls.

The current deterministic suite proves control-flow enforcement, not a 90% attack
blocking rate. That claim requires a frozen threat taxonomy, multi-turn and indirect
injection cases, repeated attempts, independent human labels, and measured false
positive and false negative rates.

## Code map

| Responsibility | Source |
|---|---|
| Security contracts | `src/ollive/domain/security.py` |
| Security capability port | `src/ollive/ports/security.py` |
| Ordered check definitions | `src/ollive/adapters/security/checks.py` |
| Constrained Security LM adapter | `src/ollive/adapters/security/llm_security.py` |
| Application enforcement broker | `src/ollive/application/security.py` |
| Stage ordering | `src/ollive/application/pipeline/runtime.py` |
| Tool isolation and search cap | `src/ollive/application/pipeline/evidence.py` |
| Grounded execution | `src/ollive/application/pipeline/grounded.py` |
| Request and context budgets | `src/ollive/application/request_limits.py` |
| Session facade | `src/ollive/application/agent.py` |
| Backend composition | `src/ollive/application/factory.py` |
| Tool validation and dispatch | `src/ollive/application/tools.py` |
| Grounded-answer contract | `src/ollive/application/grounded_answer.py` |
