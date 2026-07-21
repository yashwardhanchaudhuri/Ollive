# Knowledge-base design

| Field | Value |
|---|---|
| Objective | Explain what Ollive's local evidence can support and how it becomes retrievable citations |
| Audience | Content reviewers, developers, and evaluators |
| Status | Describes the current nine-document corpus |
| Scope | General wellness content; not a clinical reference library |

## At a glance

Ollive grounds ordinary wellness guidance in nine Markdown documents. The corpus
is intentionally small and inspectable: each retrieved answer can point back to a
specific paragraph and line position.

That transparency comes with a strict limitation. Retrieval can only show that a
passage was returned; it cannot make the passage more authoritative or fill gaps
that the corpus does not cover.

## Topic map

| Document type | High-level purpose | Important gap |
|---|---|---|
| diet | Balanced eating and practical meal habits | No universal calorie or hydration targets |
| exercise | Exercise modes, consistency, and recovery | No morning-versus-evening comparison |
| wellness_retreats | Retreat selection and practical trade-offs | No measured success rates |
| meditation_reflection | General reflection and mindfulness practices | No treatment or cure evidence |
| reading_socializing | Reading, connection, and routine ideas | Numerical cognitive-risk claims are not established |
| daily_habits | Routines, sleep hygiene, and habit formation | No universal sleep-duration number |
| natural_organic_eating | Local and organic eating themes | Universal nutrient superiority is not established |
| natural_supplements | General supplement cautions | Dosing and interaction advice is outside scope |
| nature_general_welfare | Accessible engagement with nature | No guaranteed exposure duration or effect size |

The gaps matter because the agent is expected to state an evidence limitation
instead of converting related prose into an exact answer.

## Why the corpus uses paragraph chunks

Each non-heading paragraph becomes one retrieval unit. Paragraphs are large
enough to preserve meaning but small enough to cite precisely.

The indexer records:

- document type derived from the filename;
- document title;
- start and end line;
- a short descriptor derived from the paragraph;
- full paragraph text.

The embedding model converts each paragraph into a vector. FAISS then compares
the query vector with those paragraph vectors using normalized inner product.

## Why document types are a closed enum

The model sees the exact document types loaded by the index. It may select only
those values or omit the filter.

This prevents wasted calls to invented categories such as `sleep` when sleep
content actually lives under `daily_habits`. Startup also fails when configured
types and indexed types differ, making configuration drift visible.

## Query fidelity

The model does not author the local search query. The tool router replaces any
model-supplied query with the current user message.

This choice sacrifices aggressive query expansion, but it preserves user intent
and makes evaluation exact: every recorded KB query should equal the input
prompt.

## Citation construction

A citation marker combines document type, line position, and descriptor:

    [daily_habits:L11:sleep-hygiene-is-among-the]

The internal marker is stable enough to validate within a corpus version. The UI
shows the document title rather than the raw marker and opens the supporting
paragraph in a source drawer.

## Evidence quality boundary

The current corpus was supplied as project material. The repository does not
contain a source ledger proving every scientific or medical-sounding statement.
It should therefore be treated as a curated demonstration corpus, not as an
independently validated health reference.

A future evidence revision should:

1. Inventory every externally verifiable claim.
2. Attach authoritative sources in a versioned source manifest that maps claims to references.
3. Remove unsupported precision and universal language.
4. Review medical-boundary content with qualified experts.
5. Freeze a corpus hash.
6. Rebuild the index.
7. Rerun retrieval and grounding evaluations.

## Why corpus Markdown is not casually reformatted

Citation markers include line positions. Adding headings or moving paragraphs
changes those markers and makes archived results harder to interpret.

Documentation improvements therefore live in this methodology document until a
versioned corpus revision is approved. A corpus revision must preserve the old
snapshot or record its hash, rebuild the index, and regenerate evidence.

## What retrieval results mean

A high-ranked paragraph means it is semantically similar to the query under the
configured embedding model. It does not mean:

- the passage is clinically authoritative;
- the passage answers every detail in the question;
- the passage entails a generated claim;
- lower-ranked passages are false;
- the corpus is complete.

This distinction explains why Ollive validates citation provenance and still
needs semantic claim review.

## Operational workflow

1. Review or update the corpus.
2. Run `python scripts/build_index.py`.
3. Confirm configured and indexed document types match.
4. Run retrieval and citation tests.
5. Run the grounded evaluation cases.
6. Archive the corpus/configuration identity with any published result.

## Scope and next insight

The small corpus is valuable because failures are inspectable. It is inadequate
for broad medical or evidence-grade wellness coverage. Expansion should optimize
for provenance and coverage—not document count alone.
