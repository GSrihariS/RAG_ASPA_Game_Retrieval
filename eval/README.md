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

The evaluation takes about 40 minutes with the reranker on a GPU (RTX 3070 Ti Laptop; the reranker
scores ~120k query-chunk pairs). It needs a CUDA build of torch; `--device cpu` works but takes many hours.
Rankings are saved per query to `results/checkpoint.jsonl`, so if the run stops, the same command
resumes from there; the checkpoint is deleted once the results are written.
Options: `--candidates 300 --rerank-candidates 300 --rrf-k 60 --device cuda --batch-size 32 --k 5 10 20
--relevant-grade 1`.

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

Binary metrics (P, Recall, RR, R-Prec, bpref) count grade ≥1 as relevant; nDCG uses the grades.
Queries have 8–50 relevant chunks (single-game, median 28) and 58–538 (cross-game).
In total 4,310 grade-2 and 666 grade-1 judgments, covering 991 of the 1000 chunks.

## Protocol

The whole pipeline runs on the full 12,813-chunk index, and chunks without an annotation are dropped
only from each final ranking before scoring (condensed lists, Sakai & Kando 2008,
[doi:10.1007/s10791-008-9059-7](https://doi.org/10.1007/s10791-008-9059-7)). Fusion and reranking
therefore see the real BM25 / dense ranks, unannotated chunks included. The configurations follow the
app and `query_hybrid.py`:

- `bm25`, `dense` (bge-small-en-v1.5): full rankings, condensed
- `hybrid_rrf`: top-300 of each, reciprocal rank fusion (k = 60), condensed
- `hybrid_rerank`: RRF top-300 reranked by bge-reranker-v2-m3 on the original query, condensed
- `+qe`: hierarchical query expansion (`query_expansion.expand_query`) for BM25 and dense
- `+filter`: `game_name` filter on the target games (cross-game queries are never filtered)

**Evaluation depth.** The app fuses the top 20 of each retriever and reranks the top 30. Only ~8% of
the index is annotated, so that top 30 keeps a median of 3 annotated chunks (all 100 queries below
10), too few for @10. The evaluation therefore uses depth 300 / 300, which keeps 11–118 annotated
chunks per hybrid ranking (median 28–62 depending on the run). The reranker scores each (query, chunk) pair independently,
so the order of the annotated chunks does not depend on the unannotated chunks around them; the
depth only decides which annotated chunks reach the reranker. The scores describe how the pipeline
orders the judged chunks, not the exact top 10 a user sees in the app.

**Short lists.** The report lists, per run, how many annotated chunks each condensed ranking keeps.
Missing ranks count as nonrelevant (as in trec_eval). Every ranking has ≥10 annotated chunks except
`bm25+filter` on q33 (5: BM25 returns only chunks with a nonzero score). Below 20 are 23 queries for
`hybrid_rerank` and 19 for `hybrid_rerank+filter`, so their @20 values are slightly understated.

**bpref** (Buckley & Voorhees 2004) uses only judged chunks, so it is the same on the full and the
condensed ranking. It is binary and, like R-Prec and Recall, depends on how deep a ranking goes
(see Observations).

## Results

Mean over 100 queries (full tables, per-type and per-query breakdowns in
[results/report.md](results/report.md)):

| run | P@10 | Recall@20 | MRR@20 | nDCG@5 | nDCG@10 | R-Prec | bpref |
|---|---|---|---|---|---|---|---|
| bm25 | 0.440 | 0.197 | 0.767 | 0.526 | 0.460 | 0.270 | 0.226 |
| dense | 0.522 | 0.253 | 0.853 | 0.633 | 0.546 | 0.339 | 0.293 |
| hybrid_rrf | 0.519 | 0.245 | 0.829 | 0.618 | 0.537 | 0.299 | 0.252 |
| hybrid_rerank | 0.555 | 0.242 | 0.891 | 0.668 | **0.586** | 0.268 | 0.234 |
| hybrid_rerank+qe | 0.519 | 0.218 | 0.884 | 0.644 | 0.554 | 0.244 | 0.214 |
| bm25+filter | 0.692 | 0.433 | 0.824 | 0.669 | 0.662 | 0.541 | 0.504 |
| dense+filter | 0.736 | 0.459 | 0.877 | 0.719 | 0.712 | 0.662 | 0.689 |
| bm25+qe+filter | 0.766 | 0.480 | 0.879 | 0.729 | 0.728 | 0.646 | 0.629 |
| hybrid_rrf+filter | 0.724 | 0.455 | 0.852 | 0.716 | 0.696 | 0.573 | 0.546 |
| hybrid_rerank+filter | 0.790 | 0.466 | 0.934 | 0.788 | **0.769** | 0.525 | 0.504 |
| hybrid_rerank+qe+filter | 0.797 | 0.483 | 0.934 | 0.787 | **0.772** | 0.563 | 0.546 |

nDCG@10 by query type:

| run | single_aspect | aspect_sentiment | multi_aspect | cross_game |
|---|---|---|---|---|
| hybrid_rerank | 0.529 | 0.515 | 0.671 | 0.880 |
| hybrid_rerank+filter | 0.759 | 0.698 | 0.877 | 0.880 |
| hybrid_rerank+qe+filter | 0.767 | 0.696 | 0.878 | 0.879 |

### Observations

Significance: paired Wilcoxon signed-rank test on per-query nDCG@10 (100 queries).

- The full pipeline (RRF + rerank) is the best configuration at the top of the ranking:
  nDCG@10 0.586 without a filter and 0.769 with the game filter (0.772 with query expansion, not a
  significant difference, p = 0.28); MRR@20 0.93 with the filter. With the filter it beats dense
  (+0.058, p < 0.0001, better on 61 queries, worse on 27) and RRF alone (+0.073, p < 0.0001); without
  the filter the gain over dense is +0.041 (p = 0.003).
- RRF without reranking is no better than dense alone (0.537 vs 0.546, p = 0.70; with the filter
  0.696 vs 0.712, p = 0.035): fusing with the weaker BM25 list does not help, and the reranker is what
  makes the hybrid worthwhile.
- The game filter is the largest single gain (+0.183 nDCG@10 for hybrid_rerank, better on 78 queries,
  worse on 1). Without it only ~65% of the top-10 chunks of single-game queries come from the target
  game (hybrid_rerank: 307 of the 880 top-10 chunks of the 88 single-game queries are from another game).
- Query expansion helps BM25 only when results are restricted to the right game
  (bm25+filter 0.662 → 0.728, p < 0.0001; RRF+filter 0.696 → 0.733, p < 0.0001). Without the filter it
  hurts (BM25 0.460 → 0.336, hybrid_rerank 0.586 → 0.554, both p < 0.001): the added aspect words
  outweigh the game name, and only 36% of BM25's top-10 is from the target game. With the filter and
  the reranker it makes no difference (+0.002, p = 0.28).
- With the filter, the remaining errors are mostly chunks of the right game that do not mention the
  target aspect at all (hybrid_rerank+filter: 179 of the 210 nonrelevant top-10 chunks); the opposite
  sentiment accounts for 31. Generic "great game" reviews that mention many aspects outrank chunks
  about the specific aspect.
- Sentiment queries score lowest (0.70 with filter), negative ones more so (0.65 vs 0.75 for positive):
  their targets are narrow cells, e.g. complaints about one aspect of a mostly praised game.
- By aspect (single-game, single-aspect queries, hybrid_rerank+filter), performance (0.51) and
  controls (0.58) are the hardest, gameplay (0.85) the easiest. Weakest queries: q63 (Resident Evil
  Resistance stability; 8 relevant), q32 (Monster Hunter Wilds controls, negative), q51 / q96 (Warzone
  performance), q76 (Left 4 Dead 2 performance, positive), q65 (Spacebase DF-9 controls).
- Compare configurations on the top-heavy metrics (nDCG@k, P@10, MRR). Recall, R-Prec and bpref also
  count relevant chunks that a ranking never reaches, so they favour `bm25` / `dense` (all annotated
  chunks ranked) over the hybrid runs, which stop at the evaluation depth (median 28–62 annotated
  chunks). This is why bpref puts dense+filter (0.689) above hybrid_rerank+filter (0.504), the
  opposite of nDCG@10. Recall@k is small in general because queries have many relevant chunks
  (median 28).
- Cross-game queries have so many relevant chunks that the top 10 is almost always relevant, so they
  separate configurations less than single-game queries.
