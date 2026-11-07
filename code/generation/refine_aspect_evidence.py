"""Validate TRAIN-only evidence supervision; retain context model if it wins DEV."""
import json
import shutil

from paths import ANNOTATIONS_PATH
from generation.aspect_analysis import MODEL_DIR, RESULTS_DIR, AspectAnalyzer
from generation.evaluate_aspect import load_records, split_records, score_model
from generation.optimize_aspect import write_json, objective, graphic_negative

OUT = RESULTS_DIR / 'aspect_optimization'


def main():
    prior = json.loads((OUT / 'metrics.json').read_text())
    exploration = RESULTS_DIR / 'aspect_context_exploration'
    if not exploration.exists():
        shutil.copytree(OUT, exploration)
    context_path = MODEL_DIR / 'aspect_model_context.joblib'
    if not context_path.exists():
        shutil.copy2(MODEL_DIR / 'aspect_model.joblib', context_path)
    parts = split_records(load_records(ANNOTATIONS_PATH))
    models = {'previous_deployment': AspectAnalyzer.load(MODEL_DIR / 'aspect_model_previous.joblib'),
              'local_context_hybrid': AspectAnalyzer.load(context_path)}
    dev = {name: score_model(model, parts['dev']) for name, model in models.items()}
    protocol = dict(prior['protocol'])
    protocol.update({
        'development_iteration': 'Train-only exact evidence span supervision versus automatic train contexts',
        'evidence_policy': 'Only exact source substrings from TRAIN annotations; never DEV/TEST evidence at fit or inference',
        'candidate_C': [2, 8], 'selection': 'Same development objective and guardrail; include previous context deployment as control',
    })
    write_json(OUT / 'evidence_protocol.json', protocol)
    for c in [2, 8]:
        name = f'evidence_supervised_C{c}'
        print('TRAIN', name, flush=True)
        model = AspectAnalyzer(mode='direct', context_mode='local_shared', feature_mode='hybrid',
                               detection_mode='local_augmented', presence_c=2, c=c,
                               evidence_supervision=True).fit(parts['train'])
        score = score_model(model, parts['dev'])
        models[name], dev[name] = model, score
        print('DEV', name, 'objective=',objective(score), 'e2e=',score['end_to_end']['micro']['f1'],
              'gfxneg=',graphic_negative(score),flush=True)
    threshold = dev['previous_deployment']['end_to_end']['micro']['f1'] - .01
    eligible = [name for name, score in dev.items() if score['end_to_end']['micro']['f1'] >= threshold]
    name = max(eligible, key=lambda k: objective(dev[k]))
    model = models[name]
    training_counts = dict(model.training_info)
    model.training_info = dict(models['local_context_hybrid'].training_info)
    model.training_info.update({'configuration': name, 'evidence_supervision': model.evidence_supervision,
                                'trained_on': '600 training reviews only; exact TRAIN evidence supervision; no dev/test/live examples used for fitting',
                                'exact_train_evidence_contexts': training_counts.get('exact_train_evidence_contexts',0),
                                'selection_metric': protocol['development_objective'],
                                'train_evidence_policy': protocol['evidence_policy']})
    model.save(MODEL_DIR / 'aspect_model.joblib')
    write_json(OUT / 'selection.json', {'selected': name, 'eligible': eligible,
                                      'guardrail_threshold': threshold, 'protocol': protocol})
    print('FROZEN DEPLOYMENT', name, flush=True)
    test = {key: score_model(m, parts['test']) for key,m in models.items()}
    metrics = {'protocol': protocol, 'selected': name, 'development': dev, 'test': test,
               'context_phase_metrics': '../aspect_context_exploration/metrics.json'}
    write_json(OUT / 'metrics.json', metrics)
    for key,s in test.items():
        print('TEST',key,'e2e=',s['end_to_end']['micro']['f1'],
              'sentiment=',s['sentiment_gold_aspect']['macro avg']['f1-score'],
              'gfxNeg=',s['per_aspect']['graphics_visuals']['sentiment_gold_aspect']['Negative'],flush=True)
    for path in (RESULTS_DIR / 'aspect_live_runs').glob('*/search_results.json'):
        data = json.loads(path.read_text())
        write_json(OUT / 'regression' / path.parent.name / 'before.json', models['previous_deployment'].analyze(data))
        write_json(OUT / 'regression' / path.parent.name / 'after.json', model.analyze(data))


if __name__ == '__main__':
    main()
