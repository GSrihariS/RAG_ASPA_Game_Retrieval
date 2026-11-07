"""Train ABSA models and run a fixed, review-grouped 60/20/20 benchmark.

Run from the repository root: python evaluate_aspect.py
The test split never selects C, feature configuration, or deployment model.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import platform
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
import sklearn
from sklearn.metrics import classification_report, confusion_matrix, precision_recall_fscore_support
from sklearn.model_selection import train_test_split

from paths import ANNOTATIONS_PATH, QUERIES_PATH, RETRIEVAL_RESULTS_DIR
from generation.aspect_analysis import RESULTS_DIR, ASPECTS, SENTIMENTS, AspectAnalyzer, DEFAULT_MODEL

CONFIGS = {
    'majority': {'mode': 'majority', 'use_char': False},
    'direct_word_char': {'mode': 'direct', 'use_char': True},
    'two_stage_word_char': {'mode': 'two_stage', 'use_char': True},
    'direct_word_only': {'mode': 'direct', 'use_char': False},
}


def load_records(path):
    data = json.loads(Path(path).read_text(encoding='utf-8'))
    records = [r for r in data['records'] if r.get('status') == 'Confirmed']
    if not records or len({r['chunk_id'] for r in records}) != len(records):
        raise ValueError('Expected confirmed records with unique chunk IDs')
    for record in records:
        if not record.get('document_id') or not record.get('game_name') or not record.get('text', '').strip():
            raise ValueError('Missing document ID, game name, or text')
        for aspect in ASPECTS:
            if record['human_annotation'][aspect]['sentiment'] not in (*SENTIMENTS, 'Mixed', 'Unclear', 'Not mentioned'):
                raise ValueError(f'Unknown sentiment: {record["chunk_id"]} / {aspect}')
    return records


def split_records(records, seed=42):
    """Keep reviews and exact normalized duplicate text in the same partition.

    Stratify by game for the supplied dataset. A duplicate spanning several games
    gets a composite stratum; fail explicitly if there are too few such groups.
    """
    parent = {r['document_id']: r['document_id'] for r in records}

    def find(key):
        while key != parent[key]:
            parent[key] = parent[parent[key]]
            key = parent[key]
        return key

    text_docs = {}
    for record in records:
        text_key = ' '.join(record['text'].casefold().split())
        doc = record['document_id']
        if text_key in text_docs:
            parent[find(doc)] = find(text_docs[text_key])
        text_docs[text_key] = doc
    groups = defaultdict(list)
    for r in records:
        groups[find(r['document_id'])].append(r)
    keys = sorted(groups)
    strata = {k: '|'.join(sorted({r['game_name'] for r in groups[k]})) for k in keys}
    train, remaining = train_test_split(keys, test_size=0.4, random_state=seed,
                                       stratify=[strata[k] for k in keys])
    dev, test = train_test_split(remaining, test_size=0.5, random_state=seed,
                                stratify=[strata[k] for k in remaining])
    return {name: [r for k in sorted(part) for r in groups[k]]
            for name, part in [('train', train), ('dev', dev), ('test', test)]}


def report(y_true, y_pred, labels):
    return classification_report(y_true, y_pred, labels=labels, output_dict=True, zero_division=0)


def score_model(model, records):
    predictions = model.predict([r['text'] for r in records])
    presence_gold, presence_pred = [], []
    sentiment_gold, sentiment_pred = [], []
    subject_gold, subject_pred = [], []
    triplet_gold, triplet_pred = [], []
    per_aspect = {}
    excluded = Counter()
    errors = []
    triplet_labels = [f'{aspect}:{s}' for aspect in ASPECTS for s in SENTIMENTS]
    for aspect in ASPECTS:
        ag, ap, sg, sp, tg, tp = [], [], [], [], [], []
        for r, row in zip(records, predictions):
            gold = r['human_annotation'][aspect]
            pred = row[aspect]
            ag.append(int(gold['sentiment'] != 'Not mentioned'))
            ap.append(int(pred['mentioned']))
            if gold['sentiment'] != 'Not mentioned' and gold['subjectivity'] in ('Objective', 'Opinionated'):
                subject_gold.append(gold['subjectivity'])
                subject_pred.append(pred['subjectivity'])
            if gold['sentiment'] in ('Mixed', 'Unclear'):
                excluded[gold['sentiment']] += 1
                continue
            gold_pair = f"{aspect}:{gold['sentiment']}" if ag[-1] else '__none__'
            pred_pair = f"{aspect}:{pred['sentiment']}" if pred['mentioned'] else '__none__'
            tg.append(gold_pair)
            tp.append(pred_pair)
            if gold['sentiment'] in SENTIMENTS:
                sg.append(gold['sentiment'])
                sp.append(pred['sentiment'])
            if gold_pair != pred_pair and len(errors) < 60:
                errors.append({'chunk_id': r['chunk_id'], 'aspect': aspect,
                               'gold': gold['sentiment'],
                               'predicted': pred['sentiment'] if pred['mentioned'] else 'Not mentioned',
                               'text': r['text'], 'gold_evidence': gold.get('evidence', '')})
        presence_gold.extend(ag)
        presence_pred.extend(ap)
        sentiment_gold.extend(sg)
        sentiment_pred.extend(sp)
        triplet_gold.extend(tg)
        triplet_pred.extend(tp)
        per_aspect[aspect] = {
            'presence': report(ag, ap, [0, 1]),
            'sentiment_gold_aspect': report(sg, sp, list(SENTIMENTS)),
            'end_to_end': report(tg, tp, [f'{aspect}:{s}' for s in SENTIMENTS]),
        }
    p, r, f, _ = precision_recall_fscore_support(triplet_gold, triplet_pred, labels=triplet_labels,
                                                average='micro', zero_division=0)
    return {
        'n_chunks': len(records), 'excluded_sentiment_pairs': dict(excluded),
        'aspect_detection': report(presence_gold, presence_pred, [0, 1]),
        'sentiment_gold_aspect': report(sentiment_gold, sentiment_pred, list(SENTIMENTS)),
        'sentiment_confusion_matrix': {
            'labels': list(SENTIMENTS), 'rows': 'gold', 'columns': 'predicted',
            'values': confusion_matrix(sentiment_gold, sentiment_pred, labels=list(SENTIMENTS)).tolist(),
        },
        'subjectivity_gold_aspect': report(subject_gold, subject_pred, ['Objective', 'Opinionated']),
        'end_to_end': {
            'micro': {'precision': float(p), 'recall': float(r), 'f1': float(f)},
            'per_triplet_class': report(triplet_gold, triplet_pred, triplet_labels),
        },
        'per_aspect': per_aspect, 'error_examples': errors,
    }


def _write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def format_summary(metrics):
    lines = [
        'ABSA benchmark: repository Confirmed labels; seed 42 by default',
        f"Protocol: {metrics['protocol']['split_sizes']}; seed={metrics['protocol']['seed']}",
        'Deployment selected using DEV end-to-end micro-F1: ' + metrics['protocol']['deployment_config'],
        'P/R/F1 below are on TEST. Sentiment uses gold supported aspect mentions.',
        'Mixed/Unclear are excluded from sentiment and triplet scoring, not mapped to Neutral.',
    ]
    for name, score in metrics['test'].items():
        lines.append('\n' + name)
        for label, values in [
            ('Aspect presence', score['aspect_detection']['1']),
            ('Sentiment macro', score['sentiment_gold_aspect']['macro avg']),
        ]:
            lines.append(f"  {label}: P={values['precision']:.4f} R={values['recall']:.4f} F1={values['f1-score']:.4f}")
        v = score['end_to_end']['micro']
        lines.append(f"  End-to-end triplet micro: P={v['precision']:.4f} R={v['recall']:.4f} F1={v['f1']:.4f}")
    lines.append(f"\nControlled ablation: fixed C={metrics['controlled_ablation']['fixed_C']}")
    for name, score in metrics['controlled_ablation']['test'].items():
        lines.append(f"  {name}: triplet micro-F1={score['end_to_end']['micro']['f1']:.4f}; "
                     f"sentiment macro-F1={score['sentiment_gold_aspect']['macro avg']['f1-score']:.4f}")
    return '\n'.join(lines) + '\n'


def legacy_main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--annotations', type=Path, default=ANNOTATIONS_PATH)
    parser.add_argument('--out-dir', type=Path, default=RESULTS_DIR / 'aspect_results')
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL)
    parser.add_argument('--seed', type=int, default=42)
    parser.add_argument('--c-values', type=float, nargs='+', default=[0.5, 2.0])
    args = parser.parse_args()
    if any(c <= 0 for c in args.c_values):
        parser.error('C values must be positive')
    records = load_records(args.annotations)
    splits = split_records(records, args.seed)
    train, dev, test = (splits[k] for k in ('train', 'dev', 'test'))
    manifest = {
        'seed': args.seed, 'grouping': 'document_id plus exact normalized duplicate text',
        'stratification': 'game_name; within-game generalization, not unseen games',
        'annotation_sha256': hashlib.sha256(args.annotations.read_bytes()).hexdigest(),
        'splits': {k: {'chunk_ids': [r['chunk_id'] for r in part],
                       'document_ids': sorted({r['document_id'] for r in part}),
                       'games': dict(Counter(r['game_name'] for r in part))}
                   for k, part in splits.items()},
    }
    _write_json(args.out_dir / 'split_manifest.json', manifest)
    selected_models, dev_metrics, tuning = {}, {}, {}
    for name, config in CONFIGS.items():
        tuning[name] = []
        best_score = -1
        for c in ([args.c_values[0]] if name == 'majority' else args.c_values):
            model = AspectAnalyzer(**config, c=c).fit(train)
            metrics = score_model(model, dev)
            score = metrics['end_to_end']['micro']['f1']
            tuning[name].append({'C': c, 'dev_end_to_end_micro_f1': score})
            print(f'{name} C={c}: dev triplet micro-F1={score:.4f}', flush=True)
            if score > best_score:
                best_score = score
                selected_models[name], dev_metrics[name] = model, metrics
    # This decision is made entirely before looking at any test results.
    deployment_name = max(selected_models, key=lambda name: dev_metrics[name]['end_to_end']['micro']['f1'])
    selected = selected_models[deployment_name]
    selected.training_info = {
        'configuration': deployment_name, 'seed': args.seed,
        'train_chunks': len(train), 'dev_chunks': len(dev), 'test_chunks': len(test),
        'trained_on': 'train only; no train+dev refit',
        'selection_metric': 'dev end-to-end triplet micro-F1',
        'annotation_sha256': manifest['annotation_sha256'],
    }
    selected.save(args.model)
    test_metrics = {name: score_model(model, test) for name, model in selected_models.items()}
    # A separate controlled ablation holds C fixed. Independently tuned models
    # above compare deployable systems, but cannot isolate the two-stage effect.
    fixed_c = max(args.c_values)
    controlled = {}
    for name in ('direct_word_char', 'two_stage_word_char', 'direct_word_only'):
        model = selected_models[name]
        if model.c != fixed_c:
            model = AspectAnalyzer(**CONFIGS[name], c=fixed_c).fit(train)
        controlled[name] = score_model(model, test)
    metrics = {
        'protocol': {
            'selection': 'C and deployment configuration selected by dev end-to-end micro-F1 only',
            'sentiment_policy': 'Positive/Negative/Neutral only; Mixed/Unclear excluded, never Neutral',
            'aspect_detection_policy': 'All 8 aspects on all test chunks, including Mixed/Unclear mentions',
            'gold_aspect_sentiment': 'Classify gold supported mentions regardless of predicted presence',
            'end_to_end_policy': 'Correct aspect AND sentiment; false mentions add FP, missed mentions add FN',
            'deployment_config': deployment_name, 'seed': args.seed,
            'split_sizes': {k: len(v) for k, v in splits.items()},
            'versions': {'python': platform.python_version(), 'sklearn': sklearn.__version__, 'numpy': np.__version__},
            'limitations': [
                'Same games occur in all partitions; no unseen-game generalization claim.',
                'Single seed and small neutral support; no statistical significance claim.',
                'Whole-chunk text can mix aspect opinions; excerpts are unverified source spans.',
                'No benchmark for Mixed/Unclear sentiment, or for excerpt entailment accuracy.',
            ],
        },
        'tuning': tuning, 'dev': dev_metrics, 'test': test_metrics,
        'controlled_ablation': {'fixed_C': fixed_c, 'test': controlled},
    }
    _write_json(args.out_dir / 'metrics.json', metrics)
    (args.out_dir / 'summary.txt').write_text(format_summary(metrics), encoding='utf-8')
    # A reproducible DEMO, not freshly executed retrieval: choose 5 TEST chunks
    # in the order from an existing condensed, annotated retrieval run.
    runs_path = RETRIEVAL_RESULTS_DIR / 'eval/runs.json'
    queries_path = QUERIES_PATH
    test_by_id = {r['chunk_id']: r for r in test}
    example = None
    if runs_path.exists() and queries_path.exists():
        runs = json.loads(runs_path.read_text(encoding='utf-8'))
        config_name = 'hybrid_rerank+qe+filter'
        for line in queries_path.read_text(encoding='utf-8').splitlines():
            q = json.loads(line)
            ids = [cid for cid in runs.get(config_name, {}).get(q['query_id'], []) if cid in test_by_id][:5]
            if len(ids) == 5:
                example = {'query': q['query_text'], 'results': [
                    {'chunk_id': cid, 'document_id': test_by_id[cid]['document_id'],
                     'text': test_by_id[cid]['text'], 'metadata': {'game_name': test_by_id[cid]['game_name']}}
                    for cid in ids],
                    'provenance': {'kind': 'saved_condensed_run_test_subset', 'run': config_name,
                                   'query_id': q['query_id'], 'fresh_retrieval': False}}
                break
    if example is None:
        example = {'query': 'Demo: opinions in held-out reviews', 'results': test[:5],
                   'provenance': {'kind': 'held_out_demo', 'fresh_retrieval': False}}
    _write_json(args.out_dir / 'example_retrieval.json', example)
    result = selected.analyze(example)
    result['input_provenance'] = example['provenance']
    _write_json(RESULTS_DIR / 'aspect_results.json', result)
    print(f'Saved model: {args.model}; chosen on DEV: {deployment_name}', flush=True)
    for name, metric in test_metrics.items():
        presence = metric['aspect_detection']['1']['f1-score']
        sent = metric['sentiment_gold_aspect']['macro avg']['f1-score']
        end = metric['end_to_end']['micro']['f1']
        print(f'{name}: TEST aspect F1={presence:.4f}; sentiment macro-F1={sent:.4f}; triplet micro-F1={end:.4f}')


def main():
    """Reproduce optimized ABSA; retain original baseline evaluator on request."""
    import sys
    if '--legacy-baselines' in sys.argv:
        sys.argv.remove('--legacy-baselines')
        return legacy_main()
    if len(sys.argv) > 1:
        raise SystemExit('Use no arguments for the fixed optimized experiment, or --legacy-baselines for original options.')
    from generation.optimize_aspect import main as optimize
    from generation.refine_aspect_evidence import main as refine
    from generation.validate_aspect_guard import main as guard
    optimize()
    refine()
    guard()


if __name__ == '__main__':
    main()
