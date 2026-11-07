"""Generate English ABSA report, comparison figure and handoff/presentation notes."""
import csv
import json
import os
import tempfile
from pathlib import Path

os.environ.setdefault('MPLCONFIGDIR', str(Path(tempfile.gettempdir()) / 'nlp-aspect-matplotlib'))
ROOT = Path(__file__).resolve().parent


def main():
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from generation.aspect_analysis import MODEL_DIR, RESULTS_DIR, AspectAnalyzer
    from paths import ANNOTATIONS_PATH
    from generation.evaluate_aspect import load_records, split_records

    out = RESULTS_DIR / 'aspect_optimization'
    metrics = json.loads((out / 'metrics.json').read_text())
    selected = metrics['selected']
    old = metrics['test']['previous_deployment']
    new = metrics['test'][selected]
    context = metrics['test']['local_context_hybrid']
    model = AspectAnalyzer.load()
    baseline = AspectAnalyzer.load(MODEL_DIR / 'aspect_model_previous.joblib')
    test = split_records(load_records(ANNOTATIONS_PATH))['test']
    old_predictions = baseline.predict([r['text'] for r in test])
    new_predictions = model.predict([r['text'] for r in test])
    negative_audit = []
    for r, before, after in zip(test, old_predictions, new_predictions):
        if r['human_annotation']['graphics_visuals']['sentiment'] == 'Negative':
            negative_audit.append({'chunk_id':r['chunk_id'], 'gold':'Negative',
                'before_sentiment':before['graphics_visuals']['sentiment'],
                'after_sentiment':after['graphics_visuals']['sentiment'],
                'before_mentioned':before['graphics_visuals']['mentioned'],
                'after_mentioned':after['graphics_visuals']['mentioned']})
    (out / 'graphics_negative_audit.json').write_text(json.dumps(negative_audit,indent=2))
    wrong_old = sum(x['before_sentiment']=='Positive' for x in negative_audit)
    wrong_new = sum(x['after_sentiment']=='Positive' for x in negative_audit)
    gfx_old = old['per_aspect']['graphics_visuals']['sentiment_gold_aspect']['Negative']
    gfx_new = new['per_aspect']['graphics_visuals']['sentiment_gold_aspect']['Negative']
    pair_old = old['per_aspect']['graphics_visuals']['end_to_end']['graphics_visuals:Negative']
    pair_new = new['per_aspect']['graphics_visuals']['end_to_end']['graphics_visuals:Negative']

    comparison = []
    for name, score in [('Previous deployment',old),('Local-context hybrid',context),('Optimized deployment',new)]:
        comparison.append({'model':name,'aspect_f1':score['aspect_detection']['1']['f1-score'],
            'sentiment_macro_f1':score['sentiment_gold_aspect']['macro avg']['f1-score'],
            'end_to_end_micro_f1':score['end_to_end']['micro']['f1'],
            'graphics_negative_recall':score['per_aspect']['graphics_visuals']['sentiment_gold_aspect']['Negative']['recall'],
            'graphics_negative_f1':score['per_aspect']['graphics_visuals']['sentiment_gold_aspect']['Negative']['f1-score']})
    with (out / 'comparison.csv').open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=list(comparison[0]),lineterminator='\n');w.writeheader();w.writerows(comparison)
    image_dir=ROOT/'docs/images';image_dir.mkdir(parents=True,exist_ok=True)
    fig,axes=plt.subplots(1,3,figsize=(12,4.6),layout='constrained')
    names=['Previous','Optimized']
    measures=[('End-to-end Micro-F1',old['end_to_end']['micro']['f1'],new['end_to_end']['micro']['f1']),
              ('Graphics/Negative Recall',gfx_old['recall'],gfx_new['recall']),
              ('Sentiment Macro-F1',old['sentiment_gold_aspect']['macro avg']['f1-score'],new['sentiment_gold_aspect']['macro avg']['f1-score'])]
    for ax,(title,before,after) in zip(axes,measures):
        bars=ax.bar(names,[before,after],color=['#8a9098','#286b8e'],width=.55)
        ax.set_ylim(0,1.08);ax.set_title(title,fontsize=11);ax.set_ylabel('Score (0–1)');ax.set_xlabel('Model')
        ax.bar_label(bars,fmt='%.4f',padding=4);ax.spines[['top','right']].set_visible(False)
    fig.suptitle('ABSA optimization: reused 200-review holdout',fontsize=14)
    fig.text(.5,-.025,'Source: data/generation_results/absa/aspect_optimization/metrics.json · seed 42 · Graphics/Negative n=14 · exploratory comparison',ha='center',fontsize=8)
    fig.savefig(image_dir/'optimization_comparison.png',dpi=180,bbox_inches='tight');plt.close(fig)

    trained_spans=model.training_info.get('exact_train_evidence_contexts',0)
    example_dir = RESULTS_DIR / 'aspect_live_runs/monster_hunter_graphics_performance'
    with (example_dir / 'displayed_aspects.csv').open(newline='', encoding='utf-8') as f:
        live_aspects = {row['Aspect']: row for row in csv.DictReader(f)}
    live_gfx = live_aspects['graphics_visuals']
    live_perf = live_aspects['performance']
    live_figure = ('\n![Optimized live Graphics evidence and disclosed cue override](images/optimized_live_page.jpg)\n'
                   if (image_dir/'optimized_live_page.jpg').exists() else '')
    report=f'''# 4.1 Aspect-Based Sentiment Analysis

The aspect-based sentiment analysis (ABSA) component takes the retrieved Steam review passages and returns aspect mentions, sentiment distributions, and source passage IDs. It covers story, graphics and visuals, gameplay, controls, performance, audio, bugs and stability, and online multiplayer. Each opinion receives a Positive, Negative, or Neutral label. A review counts once per aspect. When different passages from the same review carry opposite labels, the system records a Mixed conflict separately from the three-class percentages.

## Method

The baseline applies word and character TF-IDF to the full review passage. Separate classifiers detect aspects and use subjectivity to inform sentiment classification. This can produce the wrong aspect label when a review praises one feature and criticizes another. For example, two retrieved Monster Hunter Wilds reviews criticized graphics, yet the baseline labeled those opinions Positive.

The optimized model selects sentences or contrast clauses around aspect terms and uses the full passage when it finds no term. The eight aspect detectors combine full-passage TF-IDF with an aspect-term indicator and a frozen, 384-dimensional BGE embedding of the selected context. A shared class-balanced logistic classifier combines local TF-IDF with BGE embeddings to predict sentiment. During training, {trained_spans:,} aspect contexts use exact evidence excerpts from training annotations. At inference, the model selects its own context. [BGE model card](https://huggingface.co/BAAI/bge-small-en-v1.5)

A narrow rule handles explicit evaluations followed by an aspect list, such as “the only negative thing is the graphics and performance.” The rule skips negated statements and records the original classifier label whenever it overrides a prediction. The rule was added after inspection of the live errors and retained because it preserved the development objective.

## Evaluation

The data contain 1,000 annotated reviews from 20 games, with one passage per review. We use the original 600/200/200 training, development, and test split, stratified by game and grouped to keep duplicate material together. Mixed and Unclear labels count as aspect mentions and are excluded from three-class sentiment and end-to-end scoring. The test split contains 520 eligible opinions, including 14 negative Graphics opinions and 15 Neutral opinions. Model selection uses a development objective that weights overall end-to-end Micro-F1 at 0.7 and Graphics/Negative end-to-end F1 at 0.3, subject to a maximum overall development F1 drop of 0.01 from the baseline. We reuse the previously inspected test split for this exploratory comparison.

The optimized model improves aspect detection F1 from **{old['aspect_detection']['1']['f1-score']:.4f}** to **{new['aspect_detection']['1']['f1-score']:.4f}** and end-to-end Micro-F1 from **{old['end_to_end']['micro']['f1']:.4f}** to **{new['end_to_end']['micro']['f1']:.4f}**. End-to-end micro-precision rises from {old['end_to_end']['micro']['precision']:.4f} to {new['end_to_end']['micro']['precision']:.4f}, and micro-recall rises from {old['end_to_end']['micro']['recall']:.4f} to {new['end_to_end']['micro']['recall']:.4f}. With gold Graphics mentions supplied, negative recall rises from **{gfx_old['recall']:.4f}** to **{gfx_new['recall']:.4f}** and negative opinions classified as positive fall from **{wrong_old}/14** to **{wrong_new}/14**. End-to-end Graphics/Negative F1 rises from **{pair_old['f1-score']:.4f}** to **{pair_new['f1-score']:.4f}**.

The local-context hybrid without exact evidence supervision reaches end-to-end Micro-F1 **{context['end_to_end']['micro']['f1']:.4f}** and sentiment Macro-F1 **{context['sentiment_gold_aspect']['macro avg']['f1-score']:.4f}**. The selected model improves end-to-end performance but lowers sentiment Macro-F1 from **{old['sentiment_gold_aspect']['macro avg']['f1-score']:.4f}** to **{new['sentiment_gold_aspect']['macro avg']['f1-score']:.4f}** relative to the baseline. Neutral F1 falls from **{old['sentiment_gold_aspect']['Neutral']['f1-score']:.4f}** to **{new['sentiment_gold_aspect']['Neutral']['f1-score']:.4f}**, and Graphics/Negative precision falls from **{gfx_old['precision']:.4f}** to **{gfx_new['precision']:.4f}**. These trade-offs and the small negative sample limit the conclusions we can draw about generalization. [Evaluation results](../../../data/generation_results/absa/aspect_optimization/summary.txt)

![ABSA results on the reused test split](images/optimization_comparison.png)

## Integration example

For “Are the graphics of Monster Hunter Wilds worth the performance cost?”, the app runs hybrid retrieval and reranking, then applies ABSA to the five highest-ranked passages. In the integration run, Graphics was mentioned in **{live_gfx['Reviews mentioning aspect']}** retrieved reviews and labeled **{live_gfx['Negative']} Negative**. Performance was mentioned in **{live_perf['Reviews mentioning aspect']}** reviews and labeled **{live_perf['Negative']} Negative** and **{live_perf['Positive']} Positive**. These percentages describe the retrieved reviews for this query.

With the retrieved passages fixed, both previously identified graphics errors change from Positive to Negative. The local-context classifier corrects one, and the explicit evaluation rule corrects the other. These examples were inspected during development and serve as regression checks. The app displays counts, exact source excerpts, and the rule override when applicable. The JSON output preserves the passage IDs and excerpt offsets for downstream use. [Live verification](../../../data/generation_results/absa/aspect_live_runs/monster_hunter_graphics_performance/validation.json) · [Exported predictions](../../../data/generation_results/absa/aspect_live_runs/monster_hunter_graphics_performance/aspect_results.json)
{live_figure}
'''
    (ROOT/'docs/aspect_report.md').write_text(report.rstrip()+'\n',encoding='utf-8')
    overview = (ROOT/'docs/generation_overview.md').read_text(encoding='utf-8')
    overview_body = overview.partition('\n')[2].strip()
    absa_section = '\n'.join('#' + line if line.startswith('#') else line
                             for line in report.strip().splitlines())
    summary_path = ROOT/'rag_summary/experiments/final/report.md'
    summary_report = summary_path.read_text(encoding='utf-8')
    summary_section = '\n'.join('### ' + line.lstrip('# ') if line.startswith('#') else line
                                for line in summary_report.strip().splitlines())
    combined_report = (
        '# 4 Generation\n\n' + overview_body + '\n\n' + absa_section + '\n\n'
        '## 4.2 Evidence-Grounded RAG Summarization\n\n'
        'See the [summarization method and experiment setup](../rag_summary/README.md) and '
        '[per-method scores](../rag_summary/experiments/final/summary.csv).\n\n'
        + summary_section + '\n'
    )
    (ROOT/'docs/generation_report.md').write_text(combined_report, encoding='utf-8')
    summary='\n'.join(f"{r['model']}: aspect F1={r['aspect_f1']:.4f}; sentiment Macro-F1={r['sentiment_macro_f1']:.4f}; end-to-end F1={r['end_to_end_micro_f1']:.4f}; Graphics/Negative recall={r['graphics_negative_recall']:.4f}" for r in comparison)
    (out/'summary.txt').write_text(summary+'\n',encoding='utf-8')
    handoff=f'''# ABSA Team Handoff

The ABSA contribution lives in `code/generation/`. Models, evaluation outputs and real retrieval examples are under `data/generation_results/absa/`.

The [combined Generation report](docs/generation_report.md) places the Overview before Section 4.1 and the summarization results in Section 4.2. Use the [standalone Section 4.1](docs/aspect_report.md) when inserting ABSA into the team paper. The [English presentation guide](docs/PRESENTATION_GUIDE.md) contains the speaking notes and live demonstration.

Run `streamlit run app.py` from `code/`. Choose the Monster Hunter Wilds graphics and performance query, then switch between **Previous baseline** and **Optimized**. The end-to-end Micro-F1 comparison is {old['end_to_end']['micro']['f1']:.4f} to {new['end_to_end']['micro']['f1']:.4f} on the reused test split. The report explains the weaker Neutral result and the explicit cue override.

For integration, call `generation.aspect_analysis.AspectAnalyzer.load().analyze(hits, query=query)` and include the returned payload under `aspect_analysis`. Preserve `chunk_id` and `metadata.document_id` for citations and review deduplication.
'''
    (ROOT/'TEAM_HANDOFF.md').write_text(handoff,encoding='utf-8')
    presentation=f'''# English Presentation Guide — ABSA Member

Target length: about 3 minutes, plus a 1-minute live demonstration. You present only your ABSA contribution.

## Slide 1 — My responsibility (30 seconds)

Show: Retrieval reviews → ABSA → aspect distributions + evidence IDs → shared UI / RAG teammate.

Say: “My contribution is the aspect-based sentiment analysis branch. It identifies eight aspects in retrieved game reviews, predicts Positive, Negative or Neutral, and returns distributions with source IDs. I consume the Retrieval output; the separate summarization module turns evidence into a natural-language answer.”

## Slide 2 — Method and the error we addressed (45 seconds)

Show two short source excerpts: “graphics are unnecessarily demanding … make the game look bad” and “the only negative thing … is the performance and the graphics”.

Say: “The original model used whole-chunk TF-IDF features, so praise of gameplay could influence graphics sentiment. The optimized system selects aspect-local clauses, combines TF-IDF with frozen BGE embeddings, and learns from exact evidence spans in training annotations. Detection also receives local semantic features. A narrow explicit-evaluation rule handles clear aspect lists; I show when it overrides the classifier.”

## Slide 3 — Comparison and trade-offs (45 seconds)

Show docs/images/optimization_comparison.png. Quote the metric names, not just numbers.

Say: “We preserve the 600/200/200 split. End-to-end Micro-F1 improves from {old['end_to_end']['micro']['f1']:.4f} to {new['end_to_end']['micro']['f1']:.4f}. Graphics-negative recall improves from {gfx_old['recall']:.4f} to {gfx_new['recall']:.4f}. However, sentiment Macro-F1 changes from {old['sentiment_gold_aspect']['macro avg']['f1-score']:.4f} to {new['sentiment_gold_aspect']['macro avg']['f1-score']:.4f}, and Neutral recognition is weaker. These are exploratory results on a reused holdout, not a new blind test or a significance claim.”

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
'''
    (ROOT/'docs/PRESENTATION_GUIDE.md').write_text(presentation,encoding='utf-8')
    (ROOT/'requirements-report.txt').write_text('matplotlib==3.10.7\n',encoding='utf-8')
    print(summary)
    print('English report, figure, TEAM_HANDOFF.md and PRESENTATION_GUIDE.md generated.')


if __name__ == '__main__':
    main()
