"""Validate a narrow, auditable evaluation-cue safeguard using DEV noninferiority.

Designed after inspecting known live failures. It is NOT blind test evidence.
Run after optimize_aspect.py and refine_aspect_evidence.py.
"""
from copy import deepcopy
import json

from paths import ANNOTATIONS_PATH
from generation.aspect_analysis import MODEL_DIR, RESULTS_DIR, AspectAnalyzer
from generation.evaluate_aspect import load_records, split_records, score_model
from generation.optimize_aspect import objective, write_json



def main():
    out = RESULTS_DIR / 'aspect_optimization'
    metrics = json.loads((out / 'metrics.json').read_text())
    parts = split_records(load_records(ANNOTATIONS_PATH))
    base = AspectAnalyzer.load()
    if getattr(base, 'explicit_cues', False):
        base = AspectAnalyzer.load(MODEL_DIR / 'aspect_model_without_cues.joblib')
    base.save(MODEL_DIR / 'aspect_model_without_cues.joblib')
    guarded = deepcopy(base)
    guarded.explicit_cues = True
    base_dev = score_model(base, parts['dev'])
    guarded_dev = score_model(guarded, parts['dev'])
    use = (objective(guarded_dev) >= objective(base_dev) - 1e-12
           and guarded_dev['end_to_end']['micro']['f1'] >= base_dev['end_to_end']['micro']['f1'] - 1e-12)
    write_json(out / 'cue_guard_selection.json', {
        'rule_design': 'Engineered after known live failure analysis; not independent test evidence',
        'selection': 'Enable only when DEV objective and end-to-end F1 do not decrease',
        'selected': use, 'base_dev': base_dev, 'guarded_dev': guarded_dev,
    })
    if use:
        name = base.training_info['configuration'].removesuffix('_with_explicit_cues') + '_with_explicit_cues'
        guarded.training_info['configuration'] = name
        guarded.training_info['explicit_cue_policy'] = 'Narrow evaluation-cue/aspect-list rule; scores remain raw classifier outputs'
        metrics['development'][name] = guarded_dev
        metrics['test'][name] = score_model(guarded, parts['test'])
        metrics['selected'] = name
        model = guarded
    else:
        model = base
    model.save()
    write_json(out / 'metrics.json', metrics)
    write_json(out / 'selection.json', {'selected': metrics['selected'], 'protocol': metrics['protocol'], 'cue_guard_enabled': use})
    for path in (RESULTS_DIR / 'aspect_live_runs').glob('*/search_results.json'):
        write_json(out / 'regression' / path.parent.name / 'after.json', model.analyze(json.loads(path.read_text())))
    print('Selected:', metrics['selected'], 'explicit cue guard:', use)


if __name__ == '__main__':
    main()
