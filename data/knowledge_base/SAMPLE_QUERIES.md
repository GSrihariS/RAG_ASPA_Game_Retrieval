# Sample Retrieval Queries

These 10 starter queries ask about player opinions on game aspects, comparisons between games, and patterns across the collection. The machine-readable version is `sample_queries.jsonl`.

The opinion queries leave sentiment open, so the retrieved evidence can guide the summary.

| ID | Query | Test purpose |
|---|---|---|
| `sq001` | What do players think about the story and characters in Clair Obscur: Expedition 33? | Story and characters |
| `sq002` | How do players describe performance and optimization in Monster Hunter Wilds? | Performance and optimization |
| `sq003` | What do players say about stability and reliability in Cyberpunk 2077? | Stability and reliability |
| `sq004` | What do players think about cooperative multiplayer in Left 4 Dead 2? | Online / Multiplayer |
| `sq005` | How do players describe the controls, movement, and difficulty in Hollow Knight: Silksong? | Controls and Gameplay |
| `sq006` | What do players think about the music and sound design in Hades II? | Audio / Music |
| `sq007` | What do players think about the story, characters, and controls in Red Dead Redemption 2? | Story and Controls |
| `sq008` | How do players describe difficulty and controls in Hollow Knight compared with Hollow Knight: Silksong? | Cross-game comparison |
| `sq009` | What do players say about performance and optimization across the games in this collection? | Cross-game overview |
| `sq010` | What do Clair Obscur: Expedition 33 players say about native VR support and motion-controller tracking? | Unsupported-topic test |

## Suggested first test

Run the queries against BM25, dense retrieval, and the initial hybrid method. Inspect the top 5 results for `sq001`-`sq007` and `sq010`, and the top 10 for `sq008`-`sq009`.

For a quick manual check, assign each returned chunk one of these relevance grades:

- `2`: directly answers or provides strong evidence for the query.
- `1`: relates to the requested game or aspect and provides partial evidence.
- `0`: irrelevant.

Record the query ID, retrieval method, rank, chunk ID, score, relevance grade, and a short note. These judgments can form a small retrieval evaluation file. Aspect-sentiment labels belong to the separate sentiment evaluation dataset.

## Query fields

| Field | Meaning |
|---|---|
| `query_id` | Stable query identifier |
| `query_text` | Question sent to the retriever |
| `query_type` | Single game/aspect, multiple aspects, cross-game comparison, cross-game overview, or unsupported topic |
| `target_appids` / `target_games` | Game scope; an empty array covers the collection |
| `expected_aspects` | Aspects the query addresses, using the candidate categories |
| `expected_sentiment` | `any` for opinion queries; `null` for the unsupported-topic test |
| `expected_answerable_in_current_sample` | Expected availability of evidence in the collected 10,000-review collection |
| `suggested_top_k` | Number of returned chunks suggested for inspection |
| `relevance_judgments_status` | Currently `unjudged` for all queries |
