import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer


class DenseRetriever:
    def __init__(self, index_dir='dense_index'):
        index_dir = Path(index_dir)
        with (index_dir / 'config.json').open('r', encoding='utf-8') as file:
            config = json.load(file)
        with (index_dir / 'chunks.json').open('r', encoding='utf-8') as file:
            self.chunks = json.load(file)
        self.index = faiss.read_index(str(index_dir / 'faiss.index'))
        if self.index.ntotal != len(self.chunks):
            raise ValueError('FAISS index and chunk records are out of sync')
        if self.index.d != config['dimension']:
            raise ValueError('FAISS index dimension does not match config')
        self.model = SentenceTransformer(config['model_name'])

    def retrieve(self, query, top_k=10, filters=None, use_prefix=True):
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Query must be a nonempty string')
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError('top_k must be a positive integer')

        if filters is not None:
            if not isinstance(filters, dict) or set(filters) != {'game_name'}:
                raise ValueError('Only filters={"game_name": "..."} is supported')
            if not isinstance(filters['game_name'], str) or not filters['game_name'].strip():
                raise ValueError('game_name must be a nonempty string')

        prefix = 'Represent this sentence for searching relevant passages: ' if use_prefix else ''
        query_embedding = self.model.encode(
            [prefix + query], normalize_embeddings=True, convert_to_numpy=True
        )
        query_embedding = np.asarray(query_embedding, dtype=np.float32)
        if filters is None:
            scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))
            ranked = zip(scores[0], indices[0])
        else:
            # Restrict candidates before ranking, so all results match the game.
            game = filters['game_name'].strip().casefold()
            eligible = [i for i, chunk in enumerate(self.chunks)
                        if chunk.get('metadata', {}).get('game_name', '').casefold() == game]
            if not eligible:
                return []
            vectors = np.stack([self.index.reconstruct(i) for i in eligible])
            similarities = vectors @ query_embedding[0]
            best = np.argsort(-similarities, kind='stable')[:top_k]
            ranked = ((similarities[j], eligible[j]) for j in best)

        results = []
        for score, idx in ranked:
            if idx < 0:
                continue
            chunk = self.chunks[int(idx)]
            metadata = chunk['metadata'].copy()
            metadata['source'] = chunk['source']
            metadata['title'] = chunk['title']

            results.append({
                'chunk_id': chunk['id'],
                'text': chunk['text'],
                'score': float(score),
                'retrieval_method': 'dense',
                'metadata': metadata,
            })
        return results
