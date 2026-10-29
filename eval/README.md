# Evaluation set

A 100-query retrieval benchmark built on the human-annotated chunk set
`data/steam_annotations_confirmed.json`.
The queries, scripts and results of the evaluation set live in this folder.

| file | content |
|---|---|
| `dataset_stats.py` → `dataset_stats.md` | statistics of the annotation set |
| `queries.jsonl` | the 100 queries (also the app's "Sample queries") |
| `evaluate_annotated.py` | builds qrels from the annotations, runs every retrieval configuration, scores it |
| `results/qrels.json` | graded judgments (nonzero grades only) |
| `results/runs.json` | ranked annotated chunk IDs per configuration and query |
| `results/metrics.json` | mean and per-query metrics, rerank candidate recall |
| `results/report.md` | all result tables |

## Run

From the project root:

```bash
python eval/dataset_stats.py
python eval/evaluate_annotated.py
```

The evaluation takes about 1 hour on CPU (the reranker scores ~12k query-chunk pairs).
Rankings are saved per query to `results/checkpoint.jsonl`, so if the run stops, the same command
resumes from there; the checkpoint is deleted once the results are written.
Options: `--candidates 20 --rerank-candidates 30 --rrf-k 60 --k 5 10 20 --relevant-grade 1`.

## Annotation set

1000 confirmed chunks, 50 from each of 20 games (one chunk per review). Each chunk is labelled on
8 aspects (story, graphics_visuals, gameplay, controls, performance, audio, bugs_stability,
online_multiplayer) with sentiment, subjectivity and an evidence span. Full tables in
[dataset_stats.md](dataset_stats.md).

| aspect | mentioned | positive | negative |
|---|---|---|---|
| gameplay | 775 | 376 | 237 |
| story | 402 | 239 | 99 |
| graphics_visuals | 381 | 268 | 84 |
| bugs_stability | 310 | 50 | 252 |
| online_multiplayer | 293 | 82 | 173 |
| audio | 266 | 204 | 54 |
| performance | 253 | 96 | 127 |
| controls | 218 | 68 | 130 |

Sentiment is strongly game-dependent (e.g. bugs: Spacebase DF-9 0 pos / 35 neg; audio: Hollow Knight
32 / 0; story: Wolfenstein: Youngblood 1 / 22) and some game-aspect cells are empty
(Warzone story, Hades II online), which shaped the query selection.

## Query design

Following common IR benchmark practice (TREC / BEIR style): stratified coverage of the label space,
several query types, varied wording, and graded relevance taken from the human labels rather than
from any retriever's output (so no pooling bias).

| type | n | sentiment | example |
|---|---|---|---|
| `single_aspect` | 40 | any | How is the soundtrack in Hollow Knight? |
| `aspect_sentiment` | 34 | 16 positive / 18 negative | Why do players complain about crashes and bugs in Spacebase DF-9? |
| `multi_aspect` | 14 | any | Are the graphics of Monster Hunter Wilds worth the performance cost? |
| `cross_game` | 12 | 7 positive / 5 negative | games with clunky, unresponsive controls (no game named) |

- 54 open-ended queries (any sentiment) and 46 that target a specific sentiment.
- Coverage: every game is targeted by 4–5 queries; every aspect by 9–22.
- A query is only kept if its cell has ≥5 relevant chunks and ≥3 at grade 2 (checked by the evaluator).
- Wording mixes full questions (85) and keyword style ("PAYDAY 3 heist gameplay"), average 10 words,
  plus paraphrases that avoid the aspect's usual words ("How well does Cyberpunk 2077 run on PC these
  days?", "Is there enough to do in Spacebase DF-9?") to test semantic rather than lexical matching.
  No text is copied from the chunks.
- Some queries ask for the minority opinion of a game (e.g. negative views of Hades II's story, of
  Redfall's visuals) so that sentiment, not only the aspect, decides relevance.

Fields: `query_id`, `query_text`, `query_type`, `target_games` (`[]` = any game), `target_aspects`,
`target_sentiment` (`any` / `Positive` / `Negative`).

### Relevance grades

| grade | `target_sentiment = any` | `target_sentiment = Positive / Negative` |
|---|---|---|
| 2 | target game, a target aspect mentioned with an opinion (Opinionated, not Neutral/Unclear) | target game, a target aspect with the target sentiment, Opinionated |
| 1 | target game, aspect mentioned but Objective or Neutral/Unclear | target sentiment but not Opinionated, or Mixed / Neutral / Unclear |
| 0 | otherwise | otherwise, including the opposite sentiment |

Binary metrics (P, Recall, RR, R-Prec) count grade ≥1 as relevant; nDCG uses the grades.
Queries have 8–50 relevant chunks (single-game, median 28) and 58–538 (cross-game).
In total 4,310 grade-2 and 666 grade-1 judgments, covering 991 of the 1000 chunks.

## Protocol

Retrievers search the full 12,813-chunk index; chunks without an annotation are then dropped
(condensed lists), so every scored result has a judgment. The configurations mirror the app and
`query_hybrid.py` defaults:

- `bm25`, `dense` (bge-small-en-v1.5): full condensed rankings
- `hybrid_rrf`: top-20 of each, reciprocal rank fusion (k = 60)
- `hybrid_rerank`: RRF top-30 reranked by bge-reranker-v2-m3 on the original query
- `+qe`: hierarchical query expansion (`query_expansion.expand_query`) for BM25 and dense
- `+filter`: `game_name` filter on the target games (cross-game queries are never filtered)

## Results

Mean over 100 queries (full tables, per-type and per-query breakdowns in
[results/report.md](results/report.md)):

| run | P@10 | Recall@20 | MRR@20 | nDCG@5 | nDCG@10 | R-Prec |
|---|---|---|---|---|---|---|
| bm25 | 0.440 | 0.197 | 0.767 | 0.526 | 0.460 | 0.270 |
| dense | 0.522 | 0.253 | 0.853 | 0.633 | 0.546 | 0.339 |
| hybrid_rrf | 0.518 | 0.241 | 0.828 | 0.604 | 0.533 | 0.270 |
| hybrid_rerank | 0.543 | 0.250 | 0.885 | 0.664 | **0.574** | 0.270 |
| hybrid_rerank+qe | 0.515 | 0.227 | 0.877 | 0.641 | 0.552 | 0.239 |
| bm25+filter | 0.692 | 0.433 | 0.824 | 0.669 | 0.662 | 0.541 |
| dense+filter | 0.736 | 0.459 | 0.877 | 0.719 | 0.712 | 0.662 |
| bm25+qe+filter | 0.766 | 0.480 | 0.879 | 0.729 | 0.728 | 0.646 |
| hybrid_rerank+filter | 0.792 | 0.484 | 0.934 | 0.785 | **0.769** | 0.522 |
| hybrid_rerank+qe+filter | 0.789 | 0.495 | 0.934 | 0.781 | 0.766 | 0.551 |

nDCG@10 by query type:

| run | single_aspect | aspect_sentiment | multi_aspect | cross_game |
|---|---|---|---|---|
| hybrid_rerank | 0.515 | 0.508 | 0.635 | 0.887 |
| hybrid_rerank+filter | 0.761 | 0.692 | 0.879 | 0.887 |
| hybrid_rerank+qe+filter | 0.764 | 0.693 | 0.882 | 0.847 |

### Observations

Significance: paired Wilcoxon signed-rank test on per-query nDCG@10 (100 queries).

- The full pipeline (RRF + rerank) is the best configuration at the top of the ranking:
  nDCG@10 0.574 without a filter and 0.769 with the game filter; MRR@20 0.93 with the filter.
  With the filter it beats dense (+0.057, p < 0.0001) and RRF alone (+0.069, p < 0.0001); without the
  filter the gain over dense is smaller (+0.029, p = 0.03).
- RRF without reranking is no better than dense alone (0.533 vs 0.546, p = 0.55): fusing with the
  weaker BM25 list does not help, and the reranker is what makes the hybrid worthwhile.
- The game filter is the largest single gain (+0.195 nDCG@10 for hybrid_rerank, better on 75 queries,
  worse on 2). Without it only 58–66% of the top-10 chunks of single-game queries come from the
  target game; wrong-game chunks are 315 of hybrid_rerank's 1000 top-10 chunks.
- Query expansion helps BM25 only when results are restricted to the right game
  (bm25+filter 0.662 → 0.728, p < 0.0001). Without the filter it hurts BM25 (0.460 → 0.336, p < 0.0001):
  the added aspect words outweigh the game name, and only 36% of the top-10 is from the target game.
  For the reranked pipeline it makes no difference (−0.003, p = 0.59).
- With the filter, the remaining errors are mostly chunks of the right game that do not mention the
  target aspect at all (hybrid_rerank+filter: 171 of the 208 nonrelevant top-10 chunks); the opposite
  sentiment accounts for 37. Generic "great game" reviews that mention many aspects outrank chunks
  about the specific aspect.
- Sentiment queries score lowest (0.69 with filter), negative ones more so (0.64 vs 0.75 for positive):
  their targets are narrow cells, e.g. complaints about one aspect of a mostly praised game.
- By aspect (single-game, single-aspect queries, hybrid_rerank+filter), performance (0.52) and
  controls (0.55) are the hardest, gameplay (0.85) the easiest. Weakest queries: q63 (Resident Evil
  Resistance stability; 8 relevant), q32 (Monster Hunter Wilds controls, negative), q51 / q96 (Warzone
  performance), q76 (Left 4 Dead 2 performance, positive), q65 (Spacebase DF-9 controls).
- Recall@k is small because queries have many relevant chunks (median 28); R-Prec is the better recall
  view. R-Prec of `hybrid_rrf` / `hybrid_rerank` is capped by their 40 / 30-chunk output lists, which
  is why it is low for cross-game queries (R up to 538).
- Cross-game queries have so many relevant chunks that the top 10 is almost always relevant, so they
  separate configurations less than single-game queries.
