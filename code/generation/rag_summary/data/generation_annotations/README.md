# Final Generation Evaluation Data

## Sources

The source reviews, aspect annotations, and queries come from the group repository [RAG_ASPA_Game_Retrieval](https://github.com/GSrihariS/RAG_ASPA_Game_Retrieval/tree/34e8675a6af11e6871119d2de264a2487ba9b7b5), pinned to commit `34e8675a6af11e6871119d2de264a2487ba9b7b5`.

- `data/steam_annotations_confirmed.json`: 1,000 manually reviewed passages with sentiment, subjectivity, and supporting-quote annotations across eight aspects.
- `eval/queries.jsonl`: 100 queries with target games, aspects, and sentiments.
- `eval/results/runs.json`: saved retrieval results. This experiment uses up to ten evidence passages per query from the condensed annotated rankings.
- `chunks.jsonl`: source retrieval passages and their provenance metadata.

This directory includes all 1,000 annotated passages required for generation evaluation. Hashes of the source and final local files are recorded in `manifest.json`. The source audit for the fixed queries is available in `../../experiments/steam_generation_eval.audit.json`.

## Files

| File | Contents |
|---|---|
| `passages.jsonl` | 1,000 source texts, provenance IDs, and original human annotations for all eight aspects |
| `facts.jsonl` | 2,898 mentioned review–aspect facts, their sentiments, and supporting-quote offsets |
| `query_annotations.jsonl` | Final required, optional, and excluded fact sets and coverage groups for 100 queries |
| `human_review.json` | 40 individual user decisions, including candidate facts, source texts, questions, and choices |
| `statistics.json` | Dataset counts and final reference-set statistics |
| `manifest.json` | Source version, file hashes, and reference-construction method |

## Human Review

The reference version is `human_review_v1`. The 40 decisions across 16 queries are divided into:

- **A: Core information.** 22 facts included in the required reference sets.
- **B: Optional background.** Seven facts that are not required for coverage. When selected, they are removed from the denominator used to calculate selection precision.
- **C: Excluded information.** 11 facts excluded from the required sets. Selecting them counts as an incorrect selection.

The original aspect annotations remain unchanged. Explicit substatements approved by the user may occur within passages whose overall aspect sentiment is labeled `Mixed`; grouping uses the sentiment of the approved substatement. Other entries retain the original game, aspect, and sentiment matching rules.

The final references contain 591 required query–fact pairs, 238 game–aspect–sentiment coverage units, and 27 applicable positive/negative contrast groups across 24 queries. Query `q76` has no required facts. The minimum-requirements assessment permitted as background is listed separately in its optional set.

## Generation Input and Scoring

For every visible review passage, the runner provides all eight aspect slots. Each candidate contains only `fact_id`, `chunk_id`, and `aspect`. The existence of a slot does not indicate that the aspect is mentioned. Human annotations and reference sets are not sent to the model.

Generated claims include `fact_ids`. The program combines the selected IDs from the final retained claims, then computes all metrics through `evaluate_fact_selection.py`. Incorrect or unknown IDs remain in the output and count toward scoring penalties.

A coverage unit is covered when at least one of its supporting facts is selected. A positive/negative contrast group requires at least one selected positive fact and one selected negative fact. A `Mixed` label does not automatically count as covering both sides.

Condition retention and sentence-level semantic support were not annotated in this review and are not scored in this experiment.
