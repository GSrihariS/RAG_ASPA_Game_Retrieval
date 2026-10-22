import json
from collections import defaultdict
from pathlib import Path

import bm25s
import numpy as np
import Stemmer

from filters import parse_game_filter


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
        rows = defaultdict(list)
        for i, chunk in enumerate(self.chunks):
            rows[chunk['metadata']['game_name'].casefold()].append(i)
        self.game_rows = {game: np.array(indices) for game, indices in rows.items()}

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

    def retrieve(self, query, top_k=10, filters=None):
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Query must be a nonempty string')
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError('top_k must be a positive integer')

        games = parse_game_filter(filters)
        if games is None:
            eligible = None
        else:
            # Restrict candidates before ranking, so all results match the game.
            found = [self.game_rows[game] for game in games if game in self.game_rows]
            if not found:
                return []
            eligible = np.sort(np.concatenate(found))

        tokens = self._tokenize(query)
        if not tokens:
            return []
        scores = self.model.get_scores(tokens)

        candidates = np.flatnonzero(scores > 0) if eligible is None else eligible[scores[eligible] > 0]
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
