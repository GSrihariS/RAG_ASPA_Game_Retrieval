# 4.1 Aspect-Based Sentiment Analysis

The aspect-based sentiment analysis (ABSA) component takes the retrieved Steam review passages and returns aspect mentions, sentiment distributions, and source passage IDs. It covers story, graphics and visuals, gameplay, controls, performance, audio, bugs and stability, and online multiplayer. Each opinion receives a Positive, Negative, or Neutral label. A review counts once per aspect. When different passages from the same review carry opposite labels, the system records a Mixed conflict separately from the three-class percentages.

## Method

The baseline applies word and character TF-IDF to the full review passage. Separate classifiers detect aspects and use subjectivity to inform sentiment classification. This can produce the wrong aspect label when a review praises one feature and criticizes another. For example, two retrieved Monster Hunter Wilds reviews criticized graphics, yet the baseline labeled those opinions Positive.

The optimized model selects sentences or contrast clauses around aspect terms and uses the full passage when it finds no term. The eight aspect detectors combine full-passage TF-IDF with an aspect-term indicator and a frozen, 384-dimensional BGE embedding of the selected context. A shared class-balanced logistic classifier combines local TF-IDF with BGE embeddings to predict sentiment. During training, 1,495 aspect contexts use exact evidence excerpts from training annotations. At inference, the model selects its own context. [BGE model card](https://huggingface.co/BAAI/bge-small-en-v1.5)

A narrow rule handles explicit evaluations followed by an aspect list, such as “the only negative thing is the graphics and performance.” The rule skips negated statements and records the original classifier label whenever it overrides a prediction. The rule was added after inspection of the live errors and retained because it preserved the development objective.

## Evaluation

The data contain 1,000 annotated reviews from 20 games, with one passage per review. We use the original 600/200/200 training, development, and test split, stratified by game and grouped to keep duplicate material together. Mixed and Unclear labels count as aspect mentions and are excluded from three-class sentiment and end-to-end scoring. The test split contains 520 eligible opinions, including 14 negative Graphics opinions and 15 Neutral opinions. Model selection uses a development objective that weights overall end-to-end Micro-F1 at 0.7 and Graphics/Negative end-to-end F1 at 0.3, subject to a maximum overall development F1 drop of 0.01 from the baseline. We reuse the previously inspected test split for this exploratory comparison.

The optimized model improves aspect detection F1 from **0.7989** to **0.8791** and end-to-end Micro-F1 from **0.6719** to **0.7748**. End-to-end micro-precision rises from 0.6889 to 0.7824, and micro-recall rises from 0.6558 to 0.7673. With gold Graphics mentions supplied, negative recall rises from **0.7143** to **0.9286** and negative opinions classified as positive fall from **4/14** to **1/14**. End-to-end Graphics/Negative F1 rises from **0.5600** to **0.7333**.

The local-context hybrid without exact evidence supervision reaches end-to-end Micro-F1 **0.7515** and sentiment Macro-F1 **0.6412**. The selected model improves end-to-end performance but lowers sentiment Macro-F1 from **0.6094** to **0.5905** relative to the baseline. Neutral F1 falls from **0.1667** to **0.0000**, and Graphics/Negative precision falls from **0.8333** to **0.7222**. These trade-offs and the small negative sample limit the conclusions we can draw about generalization. [Evaluation results](../../../data/generation_results/absa/aspect_optimization/summary.txt)

![ABSA results on the reused test split](images/optimization_comparison.png)

## Integration example

For “Are the graphics of Monster Hunter Wilds worth the performance cost?”, the app runs hybrid retrieval and reranking, then applies ABSA to the five highest-ranked passages. In the integration run, Graphics was mentioned in **4** retrieved reviews and labeled **100.0% Negative**. Performance was mentioned in **4** reviews and labeled **75.0% Negative** and **25.0% Positive**. These percentages describe the retrieved reviews for this query.

With the retrieved passages fixed, both previously identified graphics errors change from Positive to Negative. The local-context classifier corrects one, and the explicit evaluation rule corrects the other. These examples were inspected during development and serve as regression checks. The app displays counts, exact source excerpts, and the rule override when applicable. The JSON output preserves the passage IDs and excerpt offsets for downstream use. [Live verification](../../../data/generation_results/absa/aspect_live_runs/monster_hunter_graphics_performance/validation.json) · [Exported predictions](../../../data/generation_results/absa/aspect_live_runs/monster_hunter_graphics_performance/aspect_results.json)

![Optimized live Graphics evidence and disclosed cue override](images/optimized_live_page.jpg)
