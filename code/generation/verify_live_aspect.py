"""Run the REAL full Streamlit app, retrieve fresh top-5 hits and verify ABSA.

No Retrieval mocks, saved ranks or annotation-based filtering are used. Requires
the full requirements.txt and the original BGE embedding/reranker checkpoints.
Run from code/: python -m generation.verify_live_aspect
This is an integration demonstration, not a new held-out accuracy benchmark.
"""
from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import os
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

from paths import CHUNKS_PATH, GENERATION_RESULTS_DIR, ROOT

RESULTS_DIR = GENERATION_RESULTS_DIR / 'absa'
os.environ.setdefault('OMP_NUM_THREADS', '1')
os.environ.setdefault('OPENBLAS_NUM_THREADS', '1')
os.environ.setdefault('TOKENIZERS_PARALLELISM', 'false')
if (ROOT / '.cache/huggingface').exists():
    os.environ.setdefault('HF_HOME', str(ROOT / '.cache/huggingface'))
from streamlit.testing.v1 import AppTest
from generation.aspect_analysis import DEFAULT_MODEL

CASES = {
    'hollow_knight_audio': {
        'query': 'How is the soundtrack in Hollow Knight?', 'games': ['Hollow Knight'],
    },
    'monster_hunter_graphics_performance': {
        'query': 'Are the graphics of Monster Hunter Wilds worth the performance cost?',
        'games': ['Monster Hunter Wilds'],
    },
}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding='utf-8')


def verify_export(export, dataframe):
    hits, result = export['results'], export['aspect_analysis']
    assert result is not None, 'Analysis was unavailable'
    assert len(hits) == export['params']['top_k'] == 5
    assert len({h['chunk_id'] for h in hits}) == 5
    assert result['input_chunk_count'] == 5
    assert result['input_review_count'] == len({h['metadata']['document_id'] for h in hits})
    assert all(h['metadata']['game_name'] in export['filters']['game_name'] for h in hits)
    assert all(h.get('retrieval_method') == 'hybrid_rerank' for h in hits)
    by_id = {h['chunk_id']: h for h in hits}
    for item in result['evidence']:
        hit = by_id[item['chunk_id']]
        excerpt = item['excerpt']
        assert item['document_id'] == hit['metadata']['document_id']
        assert excerpt['text'] == hit['text'][excerpt['start']:excerpt['end']]
        assert item['source_url'] == hit['metadata'].get('source_url', '')
    for aspect in result['aspects']:
        count = aspect['classified_review_count']
        assert count + aspect['mixed_review_count'] == aspect['mentioned_review_count']
        assert sum(s['count'] for s in aspect['sentiments']) == count
        if count:
            assert abs(sum(s['ratio'] for s in aspect['sentiments']) - 1) < 1e-10
        else:
            assert all(s['ratio'] is None for s in aspect['sentiments'])
        shown = dataframe[dataframe['Aspect'] == aspect['aspect']].iloc[0]
        assert int(shown['Reviews mentioning aspect']) == aspect['mentioned_review_count']
        assert int(shown['Mixed reviews']) == aspect['mixed_review_count']
        for s in aspect['sentiments']:
            expected = f"{s['ratio']:.1%}" if s['ratio'] is not None else '—'
            assert shown[s['sentiment']] == expected
            for cid in s['evidence_ids']:
                assert any(e['chunk_id'] == cid and e['aspect'] == aspect['aspect']
                           and e['sentiment'] == s['sentiment'] for e in result['evidence'])
    return {
        'fresh_real_retrieval': True, 'retrieval_mocks_used': False,
        'five_ranked_hits_and_game_filter': 'passed', 'unique_review_denominators': 'passed',
        'ratios_and_mixed_counts': 'passed', 'source_ids_urls_offsets': 'passed',
        'display_matches_export': 'passed',
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out-dir', type=Path, default=RESULTS_DIR / 'aspect_live_runs')
    parser.add_argument('--case', choices=[*CASES, 'all'], default='all')
    args = parser.parse_args()
    # AppTest executes app.py in-process with the real Streamlit widget lifecycle.
    app = AppTest.from_file(str(ROOT / 'code/app.py')).run(timeout=240)
    if app.exception:
        raise RuntimeError([e.message for e in app.exception])
    split = json.loads((RESULTS_DIR / 'aspect_results/split_manifest.json').read_text())
    split_docs = {key: set(part['document_ids']) for key, part in split['splits'].items()}
    cases = CASES if args.case == 'all' else {args.case: CASES[args.case]}
    manifest = {
        'executed_at': datetime.now(ZoneInfo('Asia/Singapore')).isoformat(timespec='seconds'),
        'pipeline': 'full app: BM25 + bge-small-en-v1.5 + RRF + bge-reranker-v2-m3 + ABSA',
        'versions': {name: importlib.metadata.version(name) for name in (
            'sentence-transformers', 'transformers', 'torch', 'faiss-cpu', 'bm25s',
            'PyStemmer', 'streamlit', 'scikit-learn', 'numpy', 'scipy', 'joblib')},
        'corpus_sha256': hashlib.sha256(CHUNKS_PATH.read_bytes()).hexdigest(),
        'aspect_model_sha256': hashlib.sha256(DEFAULT_MODEL.read_bytes()).hexdigest(),
        'runtime': {'OMP_NUM_THREADS': os.environ['OMP_NUM_THREADS'],
                    'OPENBLAS_NUM_THREADS': os.environ['OPENBLAS_NUM_THREADS']},
        'model_revisions': {},
        'not_an_accuracy_benchmark': True, 'cases': {},
    }
    from huggingface_hub import hf_hub_download
    for repo in ('BAAI/bge-small-en-v1.5', 'BAAI/bge-reranker-v2-m3'):
        config_file = hf_hub_download(repo, 'config.json', local_files_only=True)
        manifest['model_revisions'][repo] = Path(config_file).parent.name
    for key, case in cases.items():
        print('RUNNING', key, flush=True)
        app.text_input(key='query').set_value(case['query'])
        app.multiselect(key='games').set_value(case['games'])
        app.run(timeout=240)
        if app.exception:
            raise RuntimeError([e.message for e in app.exception])
        assert len(app.dataframe) == 1
        assert len(app.get('download_button')) == 2
        assert app.button(key='rag_summary_generate').label == 'Generate summary'
        export = app.session_state['last_search_export']
        checks = verify_export(export, app.dataframe[0].value)
        checks['absa_and_summary_controls_visible'] = 'passed'
        docs = {h['metadata']['document_id'] for h in export['results']}
        overlap = {name: sorted(docs & ids) for name, ids in split_docs.items()}
        overlap['unannotated'] = sorted(docs - set.union(*split_docs.values()))
        export['input_provenance'] = {
            'kind': 'fresh_full_index_retrieval', 'fresh_retrieval': True,
            'selection': 'unmodified final top-5; no annotation/split filter',
            'case': key, 'annotation_overlap_by_document': overlap,
        }
        export['aspect_analysis']['input_provenance'] = export['input_provenance']
        out = args.out_dir / key
        write_json(out / 'search_results.json', export)
        write_json(out / 'aspect_results.json', export['aspect_analysis'])
        write_json(out / 'validation.json', checks)
        if key == 'hollow_knight_audio' and args.out_dir == RESULTS_DIR / 'aspect_live_runs':
            # Primary deliverable now comes from real full-index retrieval.
            write_json(RESULTS_DIR / 'aspect_results.json', export['aspect_analysis'])
        app.dataframe[0].value.to_csv(out / 'displayed_aspects.csv', index=False)
        manifest['cases'][key] = {
            'query': case['query'], 'games': case['games'], 'checks': checks,
            'ranked_chunk_ids': [h['chunk_id'] for h in export['results']],
            'annotation_overlap_by_document': overlap, 'timings_ms': export['timings_ms'],
            'aspect_counts': {a['aspect']: {s['sentiment']: s['count'] for s in a['sentiments']}
                              for a in export['aspect_analysis']['aspects']},
        }
        write_json(args.out_dir / 'manifest.json', manifest)
        print('PASSED', key, 'chunks=', len(export['results']), 'reviews=', len(docs), flush=True)
    print('Fresh Retrieval -> ABSA -> full page verified:', args.out_dir, flush=True)


if __name__ == '__main__':
    main()
