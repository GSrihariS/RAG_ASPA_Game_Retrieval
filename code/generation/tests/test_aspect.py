"""Contract, leakage, aggregation and evaluation checks; no model downloads."""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
from paths import ANNOTATIONS_PATH
from generation.aspect_analysis import (ASPECTS, DEFAULT_MODEL, RESULTS_DIR, AspectAnalyzer,
                             aggregate_predictions, normalize_hits, source_excerpt, aspect_context, explicit_aspect_cue)
from generation.evaluate_aspect import load_records, score_model, split_records


class AspectContractTests(unittest.TestCase):
    def test_explicit_evaluation_cue_is_bound_to_listed_aspects(self):
        text = 'The only negative thing is the graphics and performance.'
        self.assertEqual(explicit_aspect_cue(text, 'graphics_visuals')['sentiment'], 'Negative')
        self.assertEqual(explicit_aspect_cue(text, 'performance')['sentiment'], 'Negative')
        self.assertIsNone(explicit_aspect_cue(text, 'audio'))
        self.assertIsNone(explicit_aspect_cue('There is no negative thing that I can name.', 'graphics_visuals'))
        self.assertIsNone(explicit_aspect_cue('The negative thing is not the graphics.', 'graphics_visuals'))
        self.assertIsNone(explicit_aspect_cue('The negative thing is audio, graphics are wonderful.', 'graphics_visuals'))
        self.assertEqual(explicit_aspect_cue('The positive aspects are the music and story.', 'audio')['sentiment'], 'Positive')

    def test_aspect_context_separates_contrasting_aspects(self):
        text = 'The gameplay is excellent, but the graphics look awful. The music is lovely.'
        graphics = aspect_context(text, 'graphics_visuals')
        self.assertEqual(graphics['text'], 'but the graphics look awful.')
        self.assertNotIn('excellent', graphics['text'])
        self.assertIn('excellent', aspect_context(text, 'gameplay')['text'])
        for span in graphics['spans']:
            self.assertEqual(text[span['start']:span['end']], span['text'])

    def test_context_keeps_negated_continuation_and_implicit_fallback(self):
        text = 'The graphics are detailed but not impressive.'
        self.assertIn('not impressive', aspect_context(text, 'graphics_visuals')['text'])
        implicit = 'It looks like a blurry mess.'
        context = aspect_context(implicit, 'graphics_visuals')
        self.assertEqual(context['text'], implicit)
        self.assertEqual(context['selection_method'], 'full_passage_fallback')

    def test_normalization_and_duplicate_validation(self):
        hit = {'chunk_id': 'steam:1:2:chunk:001', 'text': 'Great story.', 'metadata': {}}
        self.assertEqual(len(normalize_hits({'results': [hit, hit]})), 1)
        self.assertEqual(normalize_hits([hit])[0]['document_id'], 'steam:1:2')
        with self.assertRaises(ValueError):
            normalize_hits([hit, {**hit, 'text': 'Different story.'}])
        with self.assertRaises(ValueError):
            normalize_hits([{'text': 'No ID'}])

    def test_exact_excerpt_and_fallback(self):
        text = 'Combat is fun!\n The soundtrack is superb. Last sentence.'
        excerpt = source_excerpt(text, 'audio')
        self.assertEqual(excerpt['text'], 'The soundtrack is superb.')
        self.assertEqual(text[excerpt['start']:excerpt['end']], excerpt['text'])
        fallback = source_excerpt(text, 'performance')
        self.assertEqual(fallback['text'], text)
        self.assertFalse(fallback['verified_entailment'])

    def test_review_counts_mixed_and_ratios(self):
        model = AspectAnalyzer()
        hits = normalize_hits([
            {'chunk_id': f'steam:1:{rid}:chunk:{i}', 'text': 'story', 'metadata': {}}
            for rid, i in [('r1', '1'), ('r1', '2'), ('r2', '1'), ('r3', '1'), ('r3', '2')]])
        evidence = [{**hit, 'aspect': 'story', 'sentiment': label} for hit, label in
                    zip(hits, ['Positive', 'Negative', 'Neutral', 'Positive', 'Positive'])]
        result = aggregate_predictions(hits, evidence, 'q', model)
        story = result['aspects'][0]
        self.assertEqual(result['input_review_count'], 3)
        self.assertEqual(story['mixed_review_count'], 1)
        self.assertEqual(story['classified_review_count'], 2)
        self.assertEqual([s['ratio'] for s in story['sentiments']], [0.5, 0, 0.5])
        self.assertIsNone(result['aspects'][1]['sentiments'][0]['ratio'])

    def test_split_has_no_review_or_text_leakage(self):
        records = load_records(ANNOTATIONS_PATH)
        parts = split_records(records)
        self.assertEqual([len(parts[k]) for k in ('train', 'dev', 'test')], [600, 200, 200])
        for field in ('document_id', 'text'):
            seen = set()
            for part in parts.values():
                ids = {r[field] if field == 'document_id' else ' '.join(r[field].casefold().split()) for r in part}
                self.assertFalse(seen & ids)
                seen.update(ids)
        self.assertTrue(all(len({r['game_name'] for r in part}) == 20 for part in parts.values()))

    def test_end_to_end_metric_penalizes_false_and_missed_mentions(self):
        gold = {a: {'sentiment': 'Not mentioned', 'subjectivity': '', 'evidence': ''} for a in ASPECTS}
        gold['story'] = {'sentiment': 'Positive', 'subjectivity': 'Opinionated', 'evidence': 'good story'}
        record = {'chunk_id': 'c', 'text': 'good story', 'human_annotation': gold}
        row = {a: {'mentioned': a == 'story', 'sentiment': 'Positive', 'subjectivity': 'Opinionated'} for a in ASPECTS}

        class Fixed:
            def predict(self, texts):
                return [row]

        self.assertEqual(score_model(Fixed(), [record])['end_to_end']['micro']['f1'], 1)
        row['audio']['mentioned'] = True
        scores = score_model(Fixed(), [record])['end_to_end']['micro']
        self.assertEqual(scores['precision'], 0.5)
        self.assertEqual(scores['recall'], 1)
        row['story']['mentioned'] = False
        self.assertEqual(score_model(Fixed(), [record])['end_to_end']['micro']['f1'], 0)

    def test_two_stage_routes_objective_to_neutral(self):
        def head(classes, probabilities, prediction):
            classifier = Mock()
            classifier.classes_ = np.array(classes)
            classifier.predict_proba.return_value = np.array([probabilities])
            classifier.predict.return_value = np.array([prediction])
            return classifier

        model = AspectAnalyzer(mode='two_stage')
        model.vectorizer = Mock()
        model.vectorizer.transform.return_value = np.ones((1, 2))
        model.heads = {'story': {
            'presence': head([0, 1], [0.1, 0.9], 1),
            'sentiment': head(['Positive', 'Negative', 'Neutral'], [0.8, 0.1, 0.1], 'Positive'),
            'opinion_sentiment': head(['Positive', 'Negative', 'Neutral'], [0.8, 0.1, 0.1], 'Positive'),
            'subjectivity': head(['Objective', 'Opinionated'], [0.9, 0.1], 'Objective'),
        }}
        result = model.predict(['There are three chapters.'])[0]['story']
        self.assertEqual(result['sentiment'], 'Neutral')
        self.assertEqual(result['sentiment_scores']['Neutral'], 1)
        model.mode = 'direct'
        self.assertEqual(model.predict(['There are three chapters.'])[0]['story']['sentiment'], 'Positive')

    @unittest.skipUnless(DEFAULT_MODEL.exists(), 'Train checkpoint first')
    def test_checkpoint_and_cli_roundtrip(self):
        model = AspectAnalyzer.load()
        data = json.loads((RESULTS_DIR / 'aspect_results/example_retrieval.json').read_text())
        expected = model.analyze(data)
        self.assertEqual(expected['query'], data['query'])
        with tempfile.TemporaryDirectory() as directory:
            saved = Path(directory) / 'model.joblib'
            model.save(saved)
            self.assertEqual(AspectAnalyzer.load(saved).analyze(data), expected)
            output = Path(directory) / 'output.json'
            subprocess.run([sys.executable, '-m', 'generation.aspect_analysis', '--input',
                            str(RESULTS_DIR / 'aspect_results/example_retrieval.json'),
                            '--model', str(saved), '--output', str(output)], check=True, capture_output=True)
            self.assertEqual(json.loads(output.read_text()), expected)
        for evidence in expected['evidence']:
            e = evidence['excerpt']
            self.assertEqual(e['text'], evidence['text'][e['start']:e['end']])
        empty = model.analyze([])
        self.assertEqual(empty['input_review_count'], 0)
        self.assertEqual(empty['evidence'], [])


if __name__ == '__main__':
    unittest.main()
