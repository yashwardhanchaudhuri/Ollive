# Prompt guardrail design

| Field | Value |
|---|---|
| Objective | Explain which failures the guardrails address and where enforcement lives |
| Audience | Prompt authors, application developers, and evaluators |
| Status | Best measured concise five-guard profile restored; fused and expanded variants rejected |

## At a glance

Ollive does not depend on one long safety prompt. At ingress, a focused Security
LM call extracts content mode, authority target, requested effect, execution intent,
and an exact supporting span. The same original envelope then passes through separate
direct-injection, delimiter/role-confusion, Persona/DAN permission, harmful-capability,
and individualized-medical guards in that order. Each specialist receives one concise
risk definition and its nearest allowed boundary, leaving other classes to their own
guards. The sequence stops at the first owned block. An allowed review uses the lowest
per-check trust score. Context, evidence, combined evidence, and output retain their
own smaller ordered sequences.

Before those prompts run, deterministic session-frequency, current-message, and
accumulated-context budgets constrain repeated probing and many-shot loading.

Prompts influence classification and generation. Code enforces verdict schemas,
trust boundaries, tool order, search limits, query fidelity, retries, marker
provenance, claim-to-source verification, and final withholding.

## Threat model

The runtime design addresses direct and indirect prompt injection, multi-turn
context poisoning, role and authority impersonation, encoded instructions, tool
result poisoning, fake citations, search drift, harmful physiological or
psychological guidance, unsafe disclosure, best-of-N probing, and malformed model
or provider output.

A classifier is not a proof of safety. Novel obfuscation, shared model failure
modes, compromised trusted sources, and false-positive blocking remain in scope for
adversarial evaluation.

## Production invariants

The production prompts are intentionally independent of evaluation case wording.

1. **Bound traffic before semantic review.** Admit at most 12 requests per 60 seconds,
   20,000 characters in one message, and 48,000 characters across bounded context.
   This handles rapid and oversized many-shot loading without claiming semantic detection.
2. **Gate external data before the answer model.** Current input, selected
   context, individual KB and web items, combined evidence, and proposed output each
   require a valid security decision. Empty prior context and oversized input are
   decided by fixed application rules without a model call.
3. **Make authority policy application-owned.** The Security LM extracts typed
   authority semantics. Code blocks privileged override, disclosure, impersonation,
   persistence, and unauthorized action at the guard that owns the attack class; an
   earlier model verdict cannot consume a later guard's class. Model-authored
   authority labels cannot directly grant approval. Intent classes are reusable
   semantic guidance, not benchmark phrases or keyword blocklists.
4. **Route by requested domain, not permission.** Adversarial framing affects the
   response boundary, not the subject classification.
5. **Ground every wellness route.** The application forces one KB lookup and at
   least one web search; only a remaining material gap may trigger searches two and
   three.
6. **Treat user and evidence content as data.** Application-authored envelopes assign
   immutable source and authority metadata. Tags, delimiters, serialized role names,
   embedded instructions, supplied markers, and raw provider envelopes cannot alter
   that provenance.
7. **Verify claim-level entailment.** Every atomic claim is paired with its selected
   approved passage in an isolated forced-schema check before rendering.
8. **Fail closed at application boundaries.** Missing or malformed security and
   routing verdicts, unknown tools, unusable provenance, invalid citations, and a
   rejected final output are withheld.

A dedicated context classifier emits one strict boolean stating whether prior
dialogue supplies a missing substantive subject. The router separately emits the
domain, response depth, and explicit web intent. Neither model controls the
mandatory KB-plus-web minimum or the three-search maximum.

## Why these choices exist

| Choice | Failure reduced | Trade-off |
|---|---|---|
| Independent Security LM at every trust boundary | Direct and indirect injection entering the answer model | Several small classifier calls and possible false positives |
| Focused authority extraction plus code mapping | Broad allow/block prompt confusion and delimiter impersonation | One additional constrained ingress call |
| Ordered single-purpose checks with paired benign boundaries | One broad verdict confusing unrelated risks | More model calls on allowed traffic; the first block stops later calls |
| Lowest per-check safe-passage trust score | One confident check hiding a weak one | Self-reported telemetry requires calibration and cannot grant permission |
| Exact extracted evidence span | Hallucinated authority classification | An unanchored first opinion cannot block; focused checks still run |
| Sliding request window plus message/context caps | Rapid probing, oversized single-prompt many-shot, and accumulated multi-turn loading | Session-local limits need upstream identity-aware enforcement in distributed deployment |
| Unicode canonical inspection without punctuation stripping | Invisible formatting while retaining attack structure | Canonical text may differ from display text and is hash-linked to the original |
| Application-owned verdict enforcement | Classifier-generated or smuggled content | Rejected data cannot be repaired in place |
| Classify context separately from policy | Stale-topic inheritance from overloaded routing | One additional small model call only when prior dialogue exists |
| Route before answering | Treating every turn like factual wellness advice | Extra model call and possible misrouting |
| Force KB plus web search number one | Unsupported wellness guidance and unnoticed KB gaps | Added tool and gate latency on every grounded turn |
| Cap web search at three | Best-of-N probing and unbounded evidence loops | Some gaps remain explicit limitations |
| Preserve the application-bound KB query | Search drift and hidden facets | Contextual follow-ups only add the immediately preceding user turn |
| Rebuild evidence from approved typed objects | Raw tool-envelope prompt injection | Some provider metadata is intentionally discarded |
| Dynamic citation enum | Fabricated or stale markers | More schema pressure on small models |
| Claim entailment verifier | Semantically mismatched citations | Added model call and calibration requirement |
| Final full-lineage gate | Harm emerging only in the composed response | Another classifier call before rendering |

## Anti-overfitting protocol

- `core.v1.jsonl` and `prompt_regression.v1.jsonl` are development sets.
- Production prompts must not contain dataset prompts, case IDs, answer labels, or
  case-derived substitutions copied from those sets.
- An automated test rejects illustrative phrases and query-specific anchors in all
  model-facing prompts, including every focused Security LM prompt.
- New evaluation manifests store hashes of the answer, router, authority, and each
  focused security prompt plus Security LM identity and web-search bounds.
- Generalization claims require a separately authored sealed holdout that prompt
  authors cannot inspect before the prompt version is frozen.
- The holdout should cover new syntax, multi-turn placement, indirect injection,
  evidence conflicts, encoding transformations, and attack composition.
- Report repeated generations and confidence intervals. One favorable run is
  directional evidence, not a release claim.
- Human review remains required for critical safety behavior, identity fairness,
  medical boundaries, and claim-to-source entailment.


## Protection by attack family

### Direct Prompt Injection

`DirectInjectionGuard` runs before routing or tools. It looks for an attempted
override of assistant policy, hidden instructions, tool rules, or persistent
memory. Authority extraction must identify the target, intended effect, execution
request, and an exact evidence span. Application code blocks the request before any
downstream work; malformed or unanchored security output fails closed.

### Many-Shot Jailbreaking

Application limits cap one message at 20,000 characters, bounded conversation
context at 48,000 characters, and a session at 12 requests per 60 seconds. Repeated
examples remain untrusted regardless of their number or position. Shorter attempts
still pass through every relevant semantic guard, while oversized or rapidly
repeated loads stop before model execution.

### Delimiter Break Attack

The broker normalizes Unicode with NFKC, removes invisible formatting, and wraps
messages in application-owned provenance boundaries. User-written `SYSTEM` labels,
JSON fields, XML tags, Markdown fences, YAML/front matter, fake chat headers and end
markers, nested or mismatched boundaries, and Unicode separators remain untrusted
data. The guard names these nine structural families but contains no evaluation
prompts. It judges their shared effect: whether a wrapper tries to make an inner
imperative executable or more authoritative. Structured wellness data and explicit
quotation, analysis, translation, and transformation remain allowed.

### DAN-Style Persona

`PersonaGuard` separates harmless role-play and quoted analysis from personas that
claim elevated permission. It blocks persona requests that suspend policy,
impersonate a privileged role, disclose protected context, or authorize prohibited
actions. Application code enforces the typed decision, so declaring that rules no
longer apply cannot grant authority.
## Observed results and variation

The retained matched run reports Qwen at 63 of 72 structural passes and GPT-5.4
mini at 51 of 72. Those records predate the separate Security LM and mandatory
web-search pipeline, so they are historical answer-workflow baselines, not evidence
of current attack-blocking performance.

The complete frozen suite covers 1,213 cases: 575 attacks and 638 benign controls.
Deepset Prompt Injections supplies 79 direct attacks, 78 fixed delimiter-wrapped
attacks, and 198 controls; hash-disjoint JailbreakHub data supplies 200 DAN/persona
attacks, 30 many-shot transcripts (ten each at 8, 32, and 64 shots), and 200 regular
prompt controls; XSTest supplies 188 unsafe contrasts and 240 safe controls.

With the selected prompt hash, Qwen 3.5 9B via vLLM (historical quantization unrecorded) blocked 415/575 attacks
(72.2%) and 83/638 controls (13.0%); GPT-5.4 mini blocked 490/575 attacks (85.2%)
and 103/638 controls (16.1%). Correct gate decisions were 970/1,213 (80.0%) and
1,025/1,213 (84.5%), respectively, with zero execution errors. Model verdicts
accounted for 403 Qwen and 478 GPT attack blocks; each backend also rejected 12
oversized inputs at the application boundary. At the current 20,000-character
session budget, 27/30 many-shot prompts are deterministically oversized, while the
remaining three still require semantic review.

After compact delimiter-family guidance was added, a 27-case focused rerun blocked
16/27 under explicitly configured FP8 and 22/27 under the historical/default BF16
launch, with no errors. These focused results do not replace the older full-suite totals.

The 357-case prompt-selection ablation compared five designs on the same 79 direct,
78 delimiter, and 200 benign cases. The selected concise class-owned profile blocked
117/157 attacks and 69/200 controls. It outperformed the grouped sequence (89/157,
68/200), while the fused semantic-canary design over-blocked controls (108/200) and
the expanded-variation design reduced attack blocking (100/157). These ablations
explain the selected prompt; the complete matched results above are the headline
evaluation.

A fused semantic-canary experiment on the same cases was rejected. It blocked
121/157 attacks (77.1%), but only 117 were valid semantic blocks; four were malformed
output fail-closed blocks. It blocked 108/200 benign controls (54.0%) and used
2,874,973 tokens. Trust-score ranking fell to 0.550.

After the semantic canary was removed, an expanded-variation prompt rerun blocked
100/157 attacks (63.7%): 43/79 direct and 57/78 delimiter attacks. It blocked
70/200 benign controls (35.0%), completed without execution or fail-closed errors,
used 2,115,220 tokens, and produced a trust-score ranking of 0.629. This was 17
fewer attack blocks, one more benign block, and 27.8% more tokens than the concise
profile. The expanded prompt was rejected. The active concise prompts now match
all per-guard hashes in the 117/157 benchmark manifests.

## Design insight

The strongest part of this design is not a classifier prompt by itself. It is the
narrow contract around every turn: the Security LM decides, application code
enforces, raw evidence is rebuilt from approved objects, and no model can raise the
search cap. That reduces blast radius even when a model behaves unexpectedly.

## Known architectural boundary

A Security LM can still mis-extract novel or obfuscated attacks, share failure modes
with the answer model, or over-block harmless requests. Typed extraction and focused
checks narrow each decision but do not make semantic perception deterministic. A
trust score is classifier telemetry, not an independently calibrated probability.
For an allowed sequence, application code records the lowest completed check score.
It never lets a score override a block, raise authority, or skip a required check.
Application code constrains verdict shape, tool order, search count, answer structure,
marker provenance, and claim-to-source verification. The security classifier and
entailment check both require adversarial calibration and human adjudication.

Session-local rate and size limiting remains defense in depth, not the primary semantic control. It reduces
high-volume probing and best-of-N attempts but does not make one allowed malicious
request safe. Other limits include incomplete KB coverage, trusted-source
compromise, development-set contamination, and same-family judge dependence.
Supporting historical measurements and failure registers are in the
[evaluation report](../evaluation/REPORT.md).
