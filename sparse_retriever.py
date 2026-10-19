import json
from pathlib import Path

import bm25s
import numpy as np
import Stemmer


class SparseRetriever:
    def __init__(self, index_dir='sparse_index'):
        index_dir = Path(index_dir)
        with (index_dir / 'config.json').open('r', encoding='utf-8') as file:
            self.config = json.load(file)
        with (index_dir / 'chunks.json').open('r', encoding='utf-8') as file:
            self.chunks = json.load(file)
        self.model = bm25s.BM25.load(str(index_dir / 'bm25'))
        if self.model.scores['num_docs'] != len(self.chunks):
            raise ValueError('BM25 index and chunk records are out of sync')
        self.stemmer = Stemmer.Stemmer(self.config['stemmer'])
        self.appids = np.array([chunk['metadata']['appid'] for chunk in self.chunks])

    def _tokenize(self, query):
        tokens = bm25s.tokenize(
            query,
            lower=self.config['lower'],
            stopwords=self.config['stopwords'],
            stemmer=self.stemmer,
            return_ids=False,
            show_progress=False,
        )[0]
        return [token for token in tokens if token in self.model.vocab_dict]

    def _filter_mask(self, filters):
        if not filters:
            return None
        unknown = set(filters) - {'appid'}
        if unknown:
            raise ValueError(f'Unsupported filter keys: {sorted(unknown)}')
        appids = filters['appid']
        if isinstance(appids, int):
            appids = [appids]
        return np.isin(self.appids, list(appids))

    def retrieve(self, query, top_k=10, filters=None):
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Query must be a nonempty string')
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError('top_k must be a positive integer')

        mask = self._filter_mask(filters)
        tokens = self._tokenize(query)
        if not tokens:
            return []
        scores = self.model.get_scores(tokens)
        if mask is not None:
            scores = np.where(mask, scores, 0.0)

        candidates = np.flatnonzero(scores > 0)
        order = candidates[np.argsort(-scores[candidates], kind='stable')][:top_k]

        results = []
        for idx in order:
            chunk = self.chunks[int(idx)]
            metadata = chunk['metadata'].copy()
            metadata['document_id'] = chunk['document_id']
            metadata['source'] = chunk['source']
            metadata['title'] = chunk['title']

            results.append({
                'chunk_id': chunk['id'],
                'text': chunk['text'],
                'score': float(scores[idx]),
                'retrieval_method': 'bm25',
                'metadata': metadata,
            })
        return results
