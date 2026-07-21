# Curated wellness knowledge base

## At a glance

These nine documents are the local evidence Ollive may cite. The retrieval
adapter splits their prose into paragraph chunks and assigns a `doc_type` from
each filename.

| File | Evidence scope |
|---|---|
| `01_Diet.md` | General nutrition and balanced eating. |
| `02_Exercise.md` | Movement, training, recovery, and consistency. |
| `03_Wellness_Retreats.md` | Retreat purpose, selection, and expectations. |
| `04_Meditation_Reflection.md` | Mindfulness and reflective practices. |
| `05_Reading_Socializing.md` | Reading, relationships, and social wellbeing. |
| `06_Daily_Habits.md` | Routines, sleep hygiene, and everyday behavior. |
| `07_Natural_Organic_Eating.md` | Organic and minimally processed food choices. |
| `08_Natural_Supplements.md` | General supplement context and cautions. |
| `09_Nature_General_Welfare.md` | Nature exposure and broad wellbeing. |
| `wellness_docs_md.zip` | Original local archive of the supplied corpus; ignored by Git and never indexed. |
| `README.md` | Explains the corpus and is excluded from retrieval. |

Corpus edits require an index rebuild and grounding regression tests because
they can change retrieval results and citation line numbers.
