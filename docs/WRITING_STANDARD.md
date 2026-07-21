# Documentation writing standard

| Field | Value |
|---|---|
| Objective | Make every Ollive document easy to scan, understand, verify, and act on |
| Audience | Contributors writing project, operational, evaluation, or design documentation |
| Status | Active writing standard |
| Scope | Reader-facing Markdown; runtime knowledge documents follow additional corpus rules |

## The reader should understand the point first

Every document opens by answering three questions:

1. What does this document explain?
2. Why does that matter?
3. What should the reader understand or be able to do afterward?

Detail follows this orientation. A document should never require the reader to
infer its purpose from a list of components.

## Use progressive disclosure

Ollive documents follow this reading sequence:

1. **At a glance** — the conclusion or operating model.
2. **Why this design exists** — the problem and trade-off.
3. **How it works** — the mechanism in plain language.
4. **Evidence or expected result** — what supports the explanation.
5. **Variations** — what changes across models, environments, prompts, or runs.
6. **Insights** — what the evidence means.
7. **Scope and limitations** — what must not be inferred.
8. **Next action** — how to reproduce, operate, or extend it.

A short operational document can combine sections, but it should preserve this
order.

## Explain choices, not inventories

A component list is useful only when it explains responsibility or consequence.

Weak:

> The application has an agent, router, tools, memory, and tracer.

Better:

> Ollive separates routing from answering so medical boundaries are chosen before
> any retrieval or advice is generated. Tools, memory, and tracing then operate
> inside that selected boundary.

Tables should compare decisions, map responsibilities, or expose variation. They
should not repeat prose in a denser format.

## Define jargon where it first appears

Use plain language first, followed by the technical name when it helps:

- “local vector search using FAISS,” not “FAISS RAG” without explanation;
- “a model call that selects the turn policy,” then “semantic router”;
- “the passage must support the claim,” then “entailment”;
- “reject the output when validation fails,” then “fail closed.”

Do not assume readers know RAG, tool calling, manifests, calibration, semantic
grading, or counterfactual evaluation.

## Separate observation from interpretation

Use these labels consistently:

| Label | Meaning |
|---|---|
| Observed | Directly measured in code, a run, a test, or an artifact |
| Inferred | A reasoned interpretation of observed evidence |
| Expected | Intended behavior not established by the cited run |
| Not measured | No current evidence supports a conclusion |
| Out of scope | Deliberately excluded from the document or system |

Metrics without interpretation are an information dump. Interpretation without
an evidence link is speculation.

## Evidence obligations

- Architecture claims link to code, configuration, or tests.
- Operational claims include a verification command and expected outcome.
- Evaluation results link to raw records, manifests, and summaries.
- External factual claims use authoritative sources.
- Historical results remain labeled with their model, dataset, prompt, and date.
- Missing evidence is stated directly rather than filled with confident prose.

## Templates by document class

### Design document

Objective → problem → decision → workflow → alternatives → evidence → insights →
limitations → change guidance.

### Operational guide

Objective → supported setup → decision path → commands → checkpoints → variants →
troubleshooting → security boundary.

### Evaluation report

Question → evidence status → method → dataset → results → variation → failures →
insights → limitations → release interpretation → artifacts.

### Navigation document

Purpose → recommended reading order → artifact map → common tasks → scope.

## Review checklist

Before merging a Markdown change, confirm:

- The objective is visible in the first screen.
- The opening summarizes the higher-level picture.
- Design choices include reasons and trade-offs.
- Jargon is defined or replaced.
- Tables reveal a relationship rather than store prose.
- Results identify the supporting artifact.
- Variation and regressions are discussed, not hidden by an average.
- Insights are separated from raw results.
- Limitations state what is not measured.
- Links and commands are valid.
- Generated artifacts are regenerated from their documented source and renderer; curated submission reports identify their source Markdown and style file.
