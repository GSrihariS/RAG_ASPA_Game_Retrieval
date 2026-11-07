"""Compare context improvements on the original frozen split; select using DEV.

The previously inspected test set is a reused holdout, not a new blind test.
Known live errors are diagnostic regression cases, never training examples.
"""
import hashlib
import json

from paths import ANNOTATIONS_PATH
from generation.aspect_analysis import MODEL_DIR, RESULTS_DIR, AspectAnalyzer
from generation.evaluate_aspect import load_records, score_model, split_records

OUT = RESULTS_DIR / 'aspect_optimization'
CONFIGS = {
    'augmented_local_per_aspect_bge': {'mode': 'direct', 'context_mode': 'local_per_aspect', 'feature_mode': 'bge', 'detection_mode': 'local_augmented'},
    'augmented_local_shared_bge': {'mode': 'direct', 'context_mode': 'local_shared', 'feature_mode': 'bge', 'detection_mode': 'local_augmented'},
    'augmented_local_shared_hybrid': {'mode': 'direct', 'context_mode': 'local_shared', 'feature_mode': 'hybrid', 'detection_mode': 'local_augmented'},
}


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding='utf-8')


def graphic_negative(metric):
    return metric['per_aspect']['graphics_visuals']['end_to_end']['graphics_visuals:Negative']['f1-score']


def objective(metric):
    return 0.7 * metric['end_to_end']['micro']['f1'] + 0.3 * graphic_negative(metric)


def main():
    records = load_records(ANNOTATIONS_PATH)
    splits = split_records(records, 42)
    previous_manifest = json.loads((RESULTS_DIR / 'aspect_previous/split_manifest.json').read_text())
    for name, part in splits.items():
        assert [r['chunk_id'] for r in part] == previous_manifest['splits'][name]['chunk_ids']
    baseline = AspectAnalyzer.load(MODEL_DIR / 'aspect_model_previous.joblib')
    baseline_dev = score_model(baseline, splits['dev'])
    protocol = {
        'split': 'Original document-grouped, game-stratified 600/200/200; seed 42; unchanged IDs',
        'development_objective': '0.7 * end-to-end micro-F1 + 0.3 * Graphics/Negative end-to-end F1',
        'guardrail': 'Development end-to-end micro-F1 >= previous deployment minus 0.01',
        'c_values': [2.0, 8.0], 'presence_C': 2.0, 'training_data': '600 train reviews only',
        'development_iteration': 'Local semantic detection phase motivated by DEV false aspect predictions; same objective/guardrail. Earlier lexical/semantic exploration retained.',
        'test_status': 'Previously inspected holdout, reused for comparison; not a new blind benchmark',
        'known_live_cases': 'Diagnostic regression cases only; no labels/text added to training',
        'annotation_sha256': hashlib.sha256((ANNOTATIONS_PATH).read_bytes()).hexdigest(),
        'original_split_manifest': '../aspect_previous/split_manifest.json',
    }
    # Persist the selection rule before running or observing any new test results.
    write_json(OUT / 'protocol.json', protocol)
    models = {'previous_deployment': baseline}
    development = {'previous_deployment': baseline_dev}
    tuning = []
    for name, config in CONFIGS.items():
        for c in protocol['c_values']:
            key = f'{name}_C{c:g}'
            print('TRAIN', key, flush=True)
            model = AspectAnalyzer(**config, c=c, presence_c=2.0).fit(splits['train'])
            score = score_model(model, splits['dev'])
            models[key], development[key] = model, score
            entry = {'configuration': key, 'C': c, 'objective': objective(score),
                     'end_to_end_micro_f1': score['end_to_end']['micro']['f1'],
                     'graphics_negative_end_to_end_f1': graphic_negative(score)}
            tuning.append(entry)
            print('DEV', entry, flush=True)
            write_json(OUT / 'development_tuning.json', tuning)
    threshold = baseline_dev['end_to_end']['micro']['f1'] - 0.01
    eligible = [key for key, score in development.items() if score['end_to_end']['micro']['f1'] >= threshold]
    selected_name = max(eligible, key=lambda key: objective(development[key]))
    selected = models[selected_name]
    selected.training_info = {
        'configuration': selected_name, 'seed': 42, 'train_chunks': 600, 'dev_chunks': 200, 'test_chunks': 200,
        'trained_on': 'train only; no gold evidence spans or live regression texts used as training data',
        'selection_metric': protocol['development_objective'], 'selection_guardrail': protocol['guardrail'],
        'annotation_sha256': protocol['annotation_sha256'], 'test_status': protocol['test_status'],
    }
    selected.save(MODEL_DIR / 'aspect_model.joblib')
    selected.save(MODEL_DIR / 'aspect_model_context.joblib')
    write_json(OUT / 'selection.json', {'selected': selected_name, 'eligible': eligible,
                                      'guardrail_threshold': threshold, 'protocol': protocol})
    print('FROZEN DEPLOYMENT', selected_name, flush=True)
    # All choices above are fixed before this loop accesses test labels.
    test = {key: score_model(model, splits['test']) for key, model in models.items()}
    fixed_c = selected.c
    controlled = {}
    controlled_configs = {
        'whole_per_aspect_lexical': {'mode': 'direct', 'context_mode': 'whole', 'feature_mode': 'lexical'},
        'local_per_aspect_bge_global_detection': {'mode': 'direct', 'context_mode': 'local_per_aspect', 'feature_mode': 'bge'},
        **CONFIGS,
    }
    for name, config in controlled_configs.items():
        key = name.replace('_direct', '') + f'_C{fixed_c:g}'
        model = models.get(key)
        if model is None:
            model = AspectAnalyzer(**config, c=fixed_c, presence_c=2.0).fit(splits['train'])
        controlled[name] = score_model(model, splits['test'])
    result = {'protocol': protocol, 'selected': selected_name, 'development': development,
              'test': test, 'controlled_ablation': {'C': fixed_c, 'test': controlled}}
    write_json(OUT / 'metrics.json', result)
    lines = [f'Selected using development data only: {selected_name}',
             'Test below is the reused original holdout, not a new blind test.']
    for name, metric in test.items():
        gfx = metric['per_aspect']['graphics_visuals']['sentiment_gold_aspect']['Negative']
        lines.append(f"{name}: end-to-end micro-F1={metric['end_to_end']['micro']['f1']:.4f}; "
                     f"sentiment macro-F1={metric['sentiment_gold_aspect']['macro avg']['f1-score']:.4f}; "
                     f"Graphics/Negative P/R/F1={gfx['precision']:.4f}/{gfx['recall']:.4f}/{gfx['f1-score']:.4f}; "
                     f"Graphics/Negative end-to-end F1={graphic_negative(metric):.4f}")
    (OUT / 'summary.txt').write_text('\n'.join(lines) + '\n', encoding='utf-8')
    print('\n'.join(lines), flush=True)
    # Compare, but never train/select against, the existing fresh retrieval cases.
    regression = {}
    for path in (RESULTS_DIR / 'aspect_live_runs').glob('*/search_results.json'):
        data = json.loads(path.read_text())
        old = baseline.analyze(data)
        new = selected.analyze(data)
        write_json(OUT / 'regression' / path.parent.name / 'before.json', old)
        write_json(OUT / 'regression' / path.parent.name / 'after.json', new)
        regression[path.parent.name] = {
            'before': [{'chunk_id': e['chunk_id'], 'aspect': e['aspect'], 'sentiment': e['sentiment']} for e in old['evidence']],
            'after': [{'chunk_id': e['chunk_id'], 'aspect': e['aspect'], 'sentiment': e['sentiment']} for e in new['evidence']],
        }
    write_json(OUT / 'regression_predictions.json', regression)


if __name__ == '__main__':
    main()
