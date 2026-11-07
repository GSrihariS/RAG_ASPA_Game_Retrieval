# English Presentation Guide — ABSA Member

Target length: about 3 minutes, plus a 1-minute live demonstration. You present only your ABSA contribution.

## Slide 1 — My responsibility (30 seconds)

Show: Retrieval reviews → ABSA → aspect distributions + evidence IDs → shared UI / RAG teammate.

Say: “My contribution is the aspect-based sentiment analysis branch. It identifies eight aspects in retrieved game reviews, predicts Positive, Negative or Neutral, and returns distributions with source IDs. I consume the Retrieval output; the separate summarization module turns evidence into a natural-language answer.”

## Slide 2 — Method and the error we addressed (45 seconds)

Show two short source excerpts: “graphics are unnecessarily demanding … make the game look bad” and “the only negative thing … is the performance and the graphics”.

Say: “The original model used whole-chunk TF-IDF features, so praise of gameplay could influence graphics sentiment. The optimized system selects aspect-local clauses, combines TF-IDF with frozen BGE embeddings, and learns from exact evidence spans in training annotations. Detection also receives local semantic features. A narrow explicit-evaluation rule handles clear aspect lists; I show when it overrides the classifier.”

## Slide 3 — Comparison and trade-offs (45 seconds)

Show docs/images/optimization_comparison.png. Quote the metric names, not just numbers.

Say: “We preserve the 600/200/200 split. End-to-end Micro-F1 improves from 0.6719 to 0.7748. Graphics-negative recall improves from 0.7143 to 0.9286. However, sentiment Macro-F1 changes from 0.6094 to 0.5905, and Neutral recognition is weaker. These are exploratory results on a reused holdout, not a new blind test or a significance claim.”

## Slide 4 — Real integration and limitations (45 seconds)

Say: “The module runs after actual BM25, dense retrieval and reranking. It keeps review IDs, exact excerpts and offsets, and avoids counting multiple chunks from the same review more than once. Both known graphics failures are corrected, but they are regression cases used during development. Predictions and citations still require inspection; source traceability does not prove semantic entailment.”

## Live demo — exact sequence (about 1 minute)

1. Open the app and expand Sample queries.
2. Choose “Are the graphics of Monster Hunter Wilds worth the performance cost?” The sample button sets the exact game filter.
3. Keep Hybrid + Rerank, Hierarchical expansion and top-k=5.
4. Under Aspect model, select Previous baseline. Expand graphics_visuals and show the two Positive errors.
5. Switch to Optimized. Show the Negative labels for the same reviews; explain the explicit-cue override caption for the first known case.
6. Show the evidence ID, original excerpt and Steam source link. Download aspect_results.json.
7. If time permits, run “How is the soundtrack in Hollow Knight?” as a positive control.

## What to hand in / show

Share the GitHub branch, your report section and figure. During the presentation show the method diagram, the measured comparison with its Neutral trade-off, and the before/after real-page example. You do not need to implement the other member's RAG summarizer or its metrics.

## Questions you should be able to answer

- Why local context? It reduces sentiment interference between different aspects, although the selector is imperfect.
- Was BGE fine-tuned? No. Its embeddings are frozen; logistic classifier heads are trained on the supplied train split.
- Did you use test evidence for training? No. Evidence supervision uses exact TRAIN quotations only. Inference uses automatic contexts.
- Is the explicit rule learned? No. It is a disclosed narrow linguistic safeguard, with negation/target-list tests and a development non-degradation check.
- Is 2/2 a benchmark? No. It is a diagnostic regression result on already inspected cases.
- Does the optimized model improve everything? No. Overall triplet F1 and graphics-negative recall improve; Neutral and sentiment Macro-F1 weaken.
