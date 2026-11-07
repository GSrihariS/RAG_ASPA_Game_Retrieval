"""Supervised aspect detection and sentiment analysis for retrieved Steam chunks.

Optimized configurations reuse the small BGE encoder; lexical baselines use TF-IDF.
Only load joblib files created by this project: pickle-based files execute code.
"""
from __future__ import annotations

import argparse
import json
import re
import os
import sys
from functools import lru_cache
from collections import defaultdict
from pathlib import Path

import joblib
import numpy as np
from sklearn.dummy import DummyClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import FeatureUnion
from sklearn.base import BaseEstimator, TransformerMixin

from paths import GENERATION_RESULTS_DIR, ROOT

RESULTS_DIR = GENERATION_RESULTS_DIR / 'absa'
MODEL_DIR = RESULTS_DIR / 'models'

# Existing checkpoints store the module name from the original flat layout.
if __name__ == 'generation.aspect_analysis':
    sys.modules.setdefault('aspect_analysis', sys.modules[__name__])

_EMBEDDING_CACHE = {}


@lru_cache(maxsize=1)
def _semantic_encoder():
    """Reuse the existing small BGE encoder; never pickle its Torch weights."""
    cache = ROOT / '.cache/huggingface'
    if cache.exists():
        os.environ.setdefault('HF_HOME', str(cache))
    from sentence_transformers import SentenceTransformer
    return SentenceTransformer('BAAI/bge-small-en-v1.5', device='cpu',
                               cache_folder=str(cache / 'hub') if cache.exists() else None)


class BgeFeatures(BaseEstimator, TransformerMixin):
    def __init__(self, weight=1.0):
        self.weight = weight

    def fit(self, texts, y=None):
        return self

    def transform(self, texts):
        from scipy.sparse import csr_matrix
        texts = list(texts)
        missing = list(dict.fromkeys(t for t in texts if t not in _EMBEDDING_CACHE))
        if missing:
            values = _semantic_encoder().encode(missing, batch_size=32, normalize_embeddings=True,
                                                convert_to_numpy=True, show_progress_bar=False)
            _EMBEDDING_CACHE.update(zip(missing, values))
        return csr_matrix(np.stack([_EMBEDDING_CACHE[t] for t in texts]) * self.weight)

ASPECTS = (
    'story', 'graphics_visuals', 'gameplay', 'controls', 'performance',
    'audio', 'bugs_stability', 'online_multiplayer',
)
SENTIMENTS = ('Positive', 'Negative', 'Neutral')
DEFAULT_MODEL = MODEL_DIR / 'aspect_model.joblib'
# Used ONLY to select readable source excerpts, never as sentiment/gold labels.
EVIDENCE_TERMS = {
    'story': r'\b(story|stories|narrativ\w*|plot|character\w*|writing|dialog\w*|ending\w*|lore)\b',
    'graphics_visuals': r'\b(graphic\w*|visual\w*|texture\w*|art|animation\w*|lighting|beautiful)\b',
    'gameplay': r'\b(gameplay|combat|mechanic\w*|quest\w*|mission\w*|fight\w*|gunplay|level\w*|difficulty)\b',
    'controls': r'\b(control\w*|keyboard|mouse|input\w*|button\w*|movement|camera|aim\w*)\b',
    'performance': r'\b(performance|fps|frame\w*|optimi\w*|stutter\w*|lag\w*|runs?|loading|gpu|cpu)\b',
    'audio': r'\b(audio|sound\w*|music|voice\w*|acting|ost)\b',
    'bugs_stability': r'\b(bug\w*|crash\w*|glitch\w*|stability|broken|freeze\w*|freezing|softlock\w*)\b',
    'online_multiplayer': r'\b(online|multiplayer|co-op|coop|server\w*|matchmak\w*|pvp|lobby|lobbies|cheater\w*)\b',
}
CONTEXT_TERMS = dict(EVIDENCE_TERMS)
# Context anchors describe aspects, rather than positive sentiment words.
CONTEXT_TERMS['graphics_visuals'] = (
    r'\b(graphics?|graphical|visuals?|visually|textures?|art|artwork|artstyle|'
    r'animations?|lighting|resolution|rendering|fidelity|scenery|aesthetics?)\b'
)


def explicit_aspect_cue(text, aspect):
    """A conservative, auditable rule for explicit evaluation + aspect lists.

    Handles e.g. 'the only negative thing is the graphics and performance'.
    It abstains on negation and on tails containing a separate proposition.
    This is an engineered linguistic safeguard, not a learned model score.
    """
    pattern = re.compile(r'\b(negative|positive)\s+(?:things?|aspects?|parts?|points?)\b'
                         r'[^.!?\n]{0,100}?\b(?:is|are)\b([^.!?\n]+)', re.I)
    for match in pattern.finditer(text):
        prefix = text[max(0, match.start() - 35):match.start()]
        if re.search(r'\b(no|not|never|hardly)\b', prefix, re.I):
            continue
        target_list = match.group(2)
        found = {a for a, p in CONTEXT_TERMS.items() if re.search(p, target_list, re.I)}
        remainder = target_list
        for p in CONTEXT_TERMS.values():
            remainder = re.sub(p, ' ', remainder, flags=re.I)
        remainder = re.sub(r'\b(the|its|and|or)\b|[\s,&]', '', remainder, flags=re.I)
        if remainder or aspect not in found:
            continue
        return {'sentiment': match.group(1).capitalize(),
                'rule': 'explicit_evaluation_with_aspect_list',
                'source_text': match.group(), 'start': match.start(), 'end': match.end()}
    return None


def aspect_context(text, aspect):
    """Select exact, aspect-linked sentences/contrast clauses without gold spans.

    A clause without a new aspect inherits the preceding clause's aspects within
    the SAME sentence, preserving continuations such as 'but not impressive'.
    When no anchor is found, retain the whole passage for implicit mentions.
    """
    patterns = {a: re.compile(p, re.I) for a, p in CONTEXT_TERMS.items()}
    selected = []
    for sentence in re.finditer(r'[^.!?\n;]+(?:[.!?;]+|$)', text):
        boundaries = [sentence.start()]
        boundaries += [sentence.start() + m.start() for m in re.finditer(
            r'\b(?:but|however|whereas|while|although)\b', sentence.group(), re.I)
            if m.start() > 0]
        boundaries.append(sentence.end())
        previous = set()
        for start, end in zip(boundaries, boundaries[1:]):
            while start < end and text[start].isspace():
                start += 1
            while end > start and text[end - 1].isspace():
                end -= 1
            if start == end:
                continue
            found = {a for a, pattern in patterns.items() if pattern.search(text[start:end])}
            assigned = found or previous
            if aspect in assigned:
                selected.append({'text': text[start:end], 'start': start, 'end': end})
            if found:
                previous = found
    if not selected:
        return {'text': text, 'spans': [{'text': text, 'start': 0, 'end': len(text)}],
                'selection_method': 'full_passage_fallback'}
    return {'text': '\n'.join(s['text'] for s in selected), 'spans': selected,
            'selection_method': 'aspect_local_clauses'}


def _vectorizer(use_char, feature_mode='lexical'):
    if feature_mode == 'bge':
        return BgeFeatures()
    parts = [('word', TfidfVectorizer(ngram_range=(1, 2), min_df=2, max_features=18000,
                                    sublinear_tf=True, strip_accents='unicode'))]
    if use_char:
        parts.append(('char', TfidfVectorizer(analyzer='char_wb', ngram_range=(3, 5),
                                             min_df=3, max_features=18000, sublinear_tf=True)))
    if feature_mode == 'hybrid':
        parts.append(('semantic', BgeFeatures(weight=2.0)))
    return FeatureUnion(parts)


def read_json_input(path):
    """Read a JSON retrieval export/list, or the repository's chunk JSONL."""
    path = Path(path)
    if path.suffix == '.jsonl':
        return [json.loads(line) for line in path.read_text(encoding='utf-8').splitlines() if line.strip()]
    return json.loads(path.read_text(encoding='utf-8'))


def normalize_hits(data):
    """Accept the app's {'query': ..., 'results': hits}, or a list of hits.

    Duplicate chunk IDs count once; conflicting copies raise rather than mask data
    corruption. review IDs are namespaced by appid when no document_id is supplied.
    """
    if isinstance(data, dict):
        data = data.get('results', data.get('hits'))
    if not isinstance(data, list):
        raise ValueError('Expected a list of hits or an object containing results/hits')
    seen = {}
    for hit in data:
        if not isinstance(hit, dict):
            raise ValueError('Each hit must be an object')
        cid = hit.get('chunk_id', hit.get('id'))
        text = hit.get('text')
        meta = hit.get('metadata') or {}
        if not isinstance(cid, str) or not cid.strip():
            raise ValueError('Every hit needs a nonempty chunk_id or id')
        if not isinstance(text, str) or not text.strip():
            raise ValueError(f'{cid}: text must be a nonempty string')
        if not isinstance(meta, dict):
            raise ValueError(f'{cid}: metadata must be an object')
        document_id = hit.get('document_id') or meta.get('document_id')
        if not document_id and ':chunk:' in cid:
            document_id = cid.rsplit(':chunk:', 1)[0]
        if not document_id and meta.get('review_id') is not None:
            document_id = f"review:{meta.get('appid', meta.get('game_name', 'unknown'))}:{meta['review_id']}"
        item = {
            'chunk_id': cid, 'document_id': str(document_id or cid), 'text': text,
            'game_name': meta.get('game_name', hit.get('game_name', '')),
            'source_url': meta.get('source_url', hit.get('source_url', '')),
        }
        if cid in seen and seen[cid] != item:
            raise ValueError(f'Conflicting copies of chunk_id {cid}')
        seen.setdefault(cid, item)
    return list(seen.values())


def source_excerpt(text, aspect):
    """Return an exact source span, not a verified explanation of the prediction.

    Prefer an aspect-keyword sentence. If no keyword exists, expose the whole
    passage so an implicit mention is not represented by an unrelated sentence.
    Offsets are Python character offsets relative to the retrieved chunk.
    """
    candidates = list(re.finditer(r'[^.!?\n]+(?:[.!?]+|$)', text))
    pattern = re.compile(EVIDENCE_TERMS[aspect], re.I)
    ranked = [(len(pattern.findall(m.group())), m) for m in candidates]
    best = max(ranked, key=lambda pair: pair[0], default=(0, None))
    if best[0]:
        start, end = best[1].span()
        while start < end and text[start].isspace():
            start += 1
        method = 'aspect_keyword_sentence'
    else:
        start, end, method = 0, len(text), 'full_passage_fallback'
    return {'text': text[start:end], 'start': start, 'end': end,
            'selection_method': method, 'verified_entailment': False}


def _fit_head(features, labels, c, majority=False):
    if not labels:
        raise ValueError('No training labels for a classifier head')
    if majority or len(set(labels)) < 2:
        head = DummyClassifier(strategy='most_frequent')
    else:
        head = LogisticRegression(C=c, class_weight='balanced', max_iter=1500,
                                  solver='liblinear', random_state=42)
        # One-vs-rest is explicit and remains supported across sklearn releases.
        from sklearn.multiclass import OneVsRestClassifier
        head = OneVsRestClassifier(head)
    return head.fit(features, labels)


def _probabilities(head, features, labels):
    raw = head.predict_proba(features)
    result = np.zeros((features.shape[0], len(labels)), dtype=float)
    for j, label in enumerate(head.classes_):
        if label in labels:
            result[:, labels.index(label)] = raw[:, j]
    return result


class AspectAnalyzer:
    """Eight independent aspect heads, each with sentiment and subjectivity heads.

    Text features are fitted on TRAIN only. Optional evidence supervision uses
    exact TRAIN quotations; prediction never reads evaluation annotations.
    Review recommendations, query sentiment and test metadata are not features.
    """
    def __init__(self, mode='direct', use_char=True, c=2.0, context_mode='whole', feature_mode='lexical', presence_c=None, detection_mode='global', evidence_supervision=False, explicit_cues=False):
        if mode not in ('direct', 'two_stage', 'majority'):
            raise ValueError('mode must be direct, two_stage, or majority')
        self.mode, self.use_char, self.c = mode, use_char, c
        if context_mode not in ('whole', 'whole_shared', 'local_per_aspect', 'local_shared'):
            raise ValueError('Unknown context_mode')
        self.context_mode = context_mode
        if feature_mode not in ('lexical', 'bge', 'hybrid'):
            raise ValueError('Unknown feature_mode')
        self.feature_mode = feature_mode
        self.presence_c = c if presence_c is None else presence_c
        if detection_mode not in ('global', 'local_augmented'):
            raise ValueError('Unknown detection_mode')
        self.detection_mode = detection_mode
        self.evidence_supervision = evidence_supervision
        self.explicit_cues = explicit_cues
        self.training_info = {}

    def fit(self, records):
        if not records:
            raise ValueError('Training records cannot be empty')
        self.vectorizer = _vectorizer(self.use_char)
        features = self.vectorizer.fit_transform([r['text'] for r in records])
        self.heads = {}
        for aspect in ASPECTS:
            labels = [r['human_annotation'][aspect] for r in records]
            present = [int(l['sentiment'] != 'Not mentioned') for l in labels]
            valid = [i for i, l in enumerate(labels) if l['sentiment'] in SENTIMENTS]
            subject = [i for i, l in enumerate(labels)
                       if present[i] and l['subjectivity'] in ('Objective', 'Opinionated')]
            opinion = [i for i in valid if labels[i]['subjectivity'] == 'Opinionated']
            if not valid:
                raise ValueError(f'{aspect}: no supported three-class sentiment labels')
            self.heads[aspect] = {
                'presence': _fit_head(features, present, self.presence_c, self.mode == 'majority'),
                'sentiment': _fit_head(features[valid], [labels[i]['sentiment'] for i in valid],
                                       self.c, self.mode == 'majority'),
                'subjectivity': _fit_head(features[subject], [labels[i]['subjectivity'] for i in subject],
                                          self.c) if subject else None,
                'opinion_sentiment': _fit_head(features[opinion], [labels[i]['sentiment'] for i in opinion],
                                               self.c) if opinion else None,
            }
        self.training_info['train_chunks'] = len(records)
        if self.context_mode != 'whole':
            pairs = [(r, a) for a in ASPECTS for r in records]
            if self.context_mode.startswith('local'):
                self.context_vectorizer = _vectorizer(self.use_char, self.feature_mode)
                train_contexts = []
                supervised = 0
                for r, a in pairs:
                    evidence = r['human_annotation'][a].get('evidence', '').strip()
                    # Only TRAIN-time exact quotations are eligible supervision.
                    if self.evidence_supervision and evidence and evidence in r['text']:
                        train_contexts.append(evidence)
                        supervised += 1
                    else:
                        train_contexts.append(aspect_context(r['text'], a)['text'])
                self.training_info['exact_train_evidence_contexts'] = supervised
                local = self.context_vectorizer.fit_transform(train_contexts)
            else:
                self.context_vectorizer = (_vectorizer(self.use_char, self.feature_mode)
                                           if self.feature_mode != 'lexical' else self.vectorizer)
                if self.feature_mode != 'lexical':
                    self.context_vectorizer.fit([r['text'] for r in records])
                local = self.context_vectorizer.transform([r['text'] for r, a in pairs])

            def fit_context_heads(indices):
                valid = [i for i in indices if pairs[i][0]['human_annotation'][pairs[i][1]]['sentiment'] in SENTIMENTS]
                subject = [i for i in indices if pairs[i][0]['human_annotation'][pairs[i][1]]['sentiment'] != 'Not mentioned'
                           and pairs[i][0]['human_annotation'][pairs[i][1]]['subjectivity'] in ('Objective', 'Opinionated')]
                opinion = [i for i in valid if pairs[i][0]['human_annotation'][pairs[i][1]]['subjectivity'] == 'Opinionated']

                def labels(idx, field):
                    return [pairs[i][0]['human_annotation'][pairs[i][1]][field] for i in idx]

                return {
                    'sentiment': _fit_head(local[valid], labels(valid, 'sentiment'), self.c),
                    'subjectivity': _fit_head(local[subject], labels(subject, 'subjectivity'), self.c) if subject else None,
                    'opinion_sentiment': _fit_head(local[opinion], labels(opinion, 'sentiment'), self.c) if opinion else None,
                }

            if self.context_mode.endswith('shared'):
                self.context_heads = fit_context_heads(list(range(len(pairs))))
            else:
                self.context_heads = {a: fit_context_heads([i for i, (_, b) in enumerate(pairs) if b == a]) for a in ASPECTS}
        if self.detection_mode == 'local_augmented':
            for aspect in ASPECTS:
                contexts = [aspect_context(r['text'], aspect) for r in records]
                augmented = self._presence_features(features, contexts)
                present = [int(r['human_annotation'][aspect]['sentiment'] != 'Not mentioned') for r in records]
                self.heads[aspect]['presence'] = _fit_head(augmented, present, self.presence_c)
        return self

    @staticmethod
    def _presence_features(global_features, contexts):
        from scipy.sparse import hstack, csr_matrix
        semantic = BgeFeatures(weight=2.0).transform([c['text'] for c in contexts])
        anchor = csr_matrix([[int(c['selection_method'] != 'full_passage_fallback')] for c in contexts])
        return hstack([global_features, semantic, anchor], format='csr')

    def predict(self, texts):
        """Return presence + sentiment for ALL aspects (also used by evaluation)."""
        if not texts:
            return []
        features = self.vectorizer.transform(texts)
        rows = [{} for _ in texts]
        for aspect, heads in self.heads.items():
            sentiment_heads, sentiment_features = heads, features
            context_mode = getattr(self, 'context_mode', 'whole')
            contexts = None
            if context_mode != 'whole':
                sentiment_heads = self.context_heads if context_mode.endswith('shared') else self.context_heads[aspect]
                if context_mode.startswith('local'):
                    contexts = [aspect_context(t, aspect) for t in texts]
                    sentiment_features = self.context_vectorizer.transform([c['text'] for c in contexts])
                else:
                    sentiment_features = self.context_vectorizer.transform(texts)
            presence_features = features
            if getattr(self, 'detection_mode', 'global') == 'local_augmented':
                if contexts is None:
                    contexts = [aspect_context(t, aspect) for t in texts]
                presence_features = self._presence_features(features, contexts)
            mentioned = heads['presence'].predict(presence_features)
            presence = _probabilities(heads['presence'], presence_features, [0, 1])[:, 1]
            probabilities = _probabilities(sentiment_heads['sentiment'], sentiment_features, list(SENTIMENTS))
            subjective = (sentiment_heads['subjectivity'].predict(sentiment_features)
                          if sentiment_heads['subjectivity'] is not None else ['Opinionated'] * len(texts))
            if self.mode == 'two_stage':
                if sentiment_heads['opinion_sentiment'] is not None:
                    probabilities = _probabilities(sentiment_heads['opinion_sentiment'], sentiment_features, list(SENTIMENTS))
                for i, label in enumerate(subjective):
                    if label == 'Objective':
                        probabilities[i] = [0, 0, 1]
            for i in range(len(texts)):
                scores = {s: float(probabilities[i, j]) for j, s in enumerate(SENTIMENTS)}
                rows[i][aspect] = {
                    'mentioned': bool(mentioned[i]), 'presence_score': float(presence[i]),
                    'sentiment': max(scores, key=scores.get), 'sentiment_scores': scores,
                    'subjectivity': str(subjective[i]),
                }
                if contexts is not None:
                    rows[i][aspect]['classification_context'] = contexts[i]
                if getattr(self, 'explicit_cues', False):
                    cue = explicit_aspect_cue(texts[i], aspect)
                    if cue:
                        rows[i][aspect]['classifier_sentiment'] = rows[i][aspect]['sentiment']
                        rows[i][aspect]['sentiment'] = cue['sentiment']
                        rows[i][aspect]['mentioned'] = True
                        rows[i][aspect]['decision_cue'] = cue
        return rows

    def analyze(self, hits, query=''):
        if isinstance(hits, dict) and not query:
            query = hits.get('query', '')
        normalized = normalize_hits(hits)
        predictions = self.predict([h['text'] for h in normalized])
        evidence = []
        for hit, row in zip(normalized, predictions):
            for aspect, prediction in row.items():
                if prediction['mentioned']:
                    context = prediction.get('classification_context')
                    if context and context['selection_method'] != 'full_passage_fallback':
                        excerpt = {**context['spans'][0], 'selection_method': 'aspect_local_clause',
                                   'verified_entailment': False}
                    else:
                        excerpt = source_excerpt(hit['text'], aspect)
                    evidence.append({**hit, 'aspect': aspect, **prediction,
                                     'excerpt': excerpt})
        return aggregate_predictions(normalized, evidence, query, self)

    def save(self, path=DEFAULT_MODEL):
        path = Path(path)
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(self, path, compress=3)

    @classmethod
    def load(cls, path=DEFAULT_MODEL):
        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f'Model not found: {path}. Run python -m generation.evaluate_aspect first.')
        model = joblib.load(path)
        if not isinstance(model, cls):
            raise ValueError('Not an AspectAnalyzer checkpoint')
        return model


def aggregate_predictions(hits, evidence, query, model):
    """Count unique reviews within each aspect; conflicting chunk polarities stay Mixed.

    Mixed reviews are exposed separately and excluded from the three-class ratio
    denominator, never relabeled Neutral. Repeated/overlapping chunks do not add
    extra votes. The returned ratios describe this retrieved subset only.
    """
    review_count = len({h['document_id'] for h in hits})
    results = []
    for aspect in ASPECTS:
        grouped = defaultdict(list)
        for item in evidence:
            if item['aspect'] == aspect:
                grouped[item['document_id']].append(item)
        buckets = {s: [] for s in (*SENTIMENTS, 'Mixed')}
        for document_id, items in grouped.items():
            labels = {item['sentiment'] for item in items}
            if {'Positive', 'Negative'} <= labels:
                sentiment = 'Mixed'
            elif 'Positive' in labels:
                sentiment = 'Positive'
            elif 'Negative' in labels:
                sentiment = 'Negative'
            else:
                sentiment = 'Neutral'
            buckets[sentiment].append((document_id, items))
        denominator = sum(len(buckets[s]) for s in SENTIMENTS)
        sentiments = []
        for sentiment in SENTIMENTS:
            members = buckets[sentiment]
            sentiments.append({
                'sentiment': sentiment, 'count': len(members),
                'ratio': len(members) / denominator if denominator else None,
                'review_ids': [rid for rid, _ in members],
                'evidence_ids': sorted({item['chunk_id'] for _, items in members for item in items
                                        if item['sentiment'] == sentiment}),
            })
        mixed = buckets['Mixed']
        results.append({
            'aspect': aspect, 'mentioned_review_count': len(grouped),
            'mention_ratio': len(grouped) / review_count if review_count else None,
            'classified_review_count': denominator, 'sentiments': sentiments,
            'mixed_review_count': len(mixed), 'mixed_review_ids': [rid for rid, _ in mixed],
            'mixed_evidence_ids': sorted({item['chunk_id'] for _, items in mixed for item in items}),
        })
    return {
        'schema_version': '1.0', 'query': query,
        'model': {'mode': model.mode, 'use_char': model.use_char, 'C': model.c,
                  'context_mode': getattr(model, 'context_mode', 'whole'),
                  'feature_mode': getattr(model, 'feature_mode', 'lexical'),
                  'presence_C': getattr(model, 'presence_c', model.c),
                  'detection_mode': getattr(model, 'detection_mode', 'global'),
                  'evidence_supervision': getattr(model, 'evidence_supervision', False),
                  'explicit_cue_guard': getattr(model, 'explicit_cues', False),
                  'scores_calibrated': False, 'training': model.training_info},
        'input_chunk_count': len(hits), 'input_review_count': review_count,
        'aggregation_unit': 'unique document_id per aspect',
        'ratio_denominator': 'classified_review_count (excludes cross-chunk Mixed)',
        'scope': 'Predictions on retrieved reviews only; not all Steam reviews.',
        'evidence_policy': 'Exact source excerpts for inspection; entailment has not been verified.',
        'aspects': results, 'evidence': evidence,
    }


def analyze_aspects(hits, query='', model_path=DEFAULT_MODEL):
    """Uniform entry point for the Retrieval and RAG-summary teammates."""
    return AspectAnalyzer.load(model_path).analyze(hits, query=query)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input', type=Path, required=True, help='Retrieval JSON export or JSONL chunks')
    parser.add_argument('--output', type=Path, default=RESULTS_DIR / 'aspect_results.json')
    parser.add_argument('--model', type=Path, default=DEFAULT_MODEL)
    parser.add_argument('--query', default='')
    args = parser.parse_args()
    # Keep the checkpoint's class identity stable when this file is a script.
    from generation.aspect_analysis import analyze_aspects as run_analysis
    output = run_analysis(read_json_input(args.input), args.query, args.model)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(output, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"Wrote {args.output}: {output['input_review_count']} unique reviews")


if __name__ == '__main__':
    main()
