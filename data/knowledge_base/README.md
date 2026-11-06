# Steam Review Knowledge Base

Open [index.html](index.html) to browse the collection and its recommendation distribution. Open [processing_logic.html](processing_logic.html) to compare processing results for 50 selected reviews.

## Collection

- 20 games, 500 reviews per game, 10,000 collected reviews.
- 6,121 recommended (61.21%) and 3,879 not recommended (38.79%).
- Primary requests use `language=english`, `filter=all`, `review_type=all`, `purchase_type=all`, and off-topic activity filtering.
- Additional recent-order pages supplement 5 games; each sampling run is recorded in `collection_manifest.json`.
- Per-game collection windows are recorded in `collection_manifest.json`.
- Each review keeps its source text, Steam recommendation, game information, timestamps, and source URL.

## Full collection processing

| Result | Count |
|---|---:|
| Collected source reviews | 10,000 |
| Retained documents | 9,781 |
| Archived records | 219 |
| Records awaiting a language check | 0 |
| Retrieval chunks | 12,822 |
| Source words | 851,272 |
| Retained text words | 823,461 |
| Retained word types (lowercase) | 22,827 |


The full retrieval dataset is [processed/chunks.jsonl](processed/chunks.jsonl). Complete retained documents are in [processed/filtered_reviews.jsonl](processed/filtered_reviews.jsonl), and counts and processing rules are in [processed/processing_report.json](processed/processing_report.json). Source preservation, partitioning, offsets, and coverage checks are in [processed/validation_report.json](processed/validation_report.json).

## Processing examples: 50 reviews

| Result | Count |
|---|---:|
| Selected source reviews | 50 |
| Reviews with formatting changes | 17 |
| Retained example reviews | 47 |
| Archived example records | 3 |
| Examples awaiting a language check | 0 |
| Example chunks | 110 |

The retained examples contain 30 recommended and 17 not recommended reviews. [processing_sample_50/processed/processing_report.json](processing_sample_50/processed/processing_report.json) records the results for these 50 examples.

## Files

| File or folder | Contents |
|---|---|
| `index.html` | Collection overview, distribution bars, and game links |
| `processing_logic.html` | Original text, cleaned text, English selection, and chunks for 50 examples |
| `all_reviews.json` | All 10,000 source reviews in one normalized dataset |
| Each game folder | `reviews.json`, `raw_responses.json`, and a searchable `reviews.html` |
| `collection_manifest.json`, `games.json` | Collection settings and game catalog |
| `analysis_summary.json` | Source corpus statistics and aspect keyword coverage |
| `processed/` | Full collection: cleaned documents, retained documents, archived records, check candidates, chunks, and processing report |
| `processing_sample_50/` | The 50 selected source reviews, selection manifest, and processing results |
| `processing_sample_50/processed/` | Cleaned example documents, retained documents, archived records, check candidates, chunks, and processing report |
| `DATA_FORMAT.md` | Actual document and chunk fields |
| `PROCESSING.md` | Cleaning, language selection, duplicate handling, and chunking rules |
| `SAMPLE_QUERIES.md`, `sample_queries.jsonl` | 10 starter retrieval queries |

## Data flow

```text
raw_responses.json → reviews.json → all_reviews.json
    ↓
processed/clean_reviews.jsonl
    ↓
processed/filtered_reviews.jsonl / excluded_reviews.jsonl
    ↓
processed/chunks.jsonl

processing_sample_50/sample_reviews.json (50 selected reviews)
    ↓
processing_sample_50/processed/clean_reviews.jsonl
    ↓
filtered_reviews.jsonl / excluded_reviews.jsonl
    ↓
chunks.jsonl
```

The 50-review processing example provides `processing_sample_50/processed/chunks.jsonl` for testing. Generation can use retrieved chunk text and its source metadata. `filtered_reviews.jsonl` stores each complete retained example document.

## Aspects and evaluation

Current data suggests Story, Gameplay, Graphics / Visuals, Controls, Performance, Audio / Music, Bugs / Stability, and Online / Multiplayer as candidate aspects. Value / Monetization and Updates / Development Support can also be discussed with the group. A review can mention several aspects with different sentiments.

`steam_recommended` stores the overall Steam recommendation. Aspect-sentiment evaluation uses separate manual labels, aiming for coverage across aspects and positive/negative cases. The starter queries support early retrieval smoke tests; the Retrieval and Generation groups can adapt the queries to their evaluation design.


