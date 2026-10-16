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

    def retrieve(self, query, top_k=10, filters=None, use_query_instruction=True):
        if filters is not None:
            raise NotImplementedError('Metadata filtering is not implemented yet')
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Query must be a nonempty string')
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError('top_k must be a positive integer')

        prefix = 'Represent this sentence for searching relevant passages: ' if use_query_instruction else ''
        query_embedding = self.model.encode(
            [prefix + query], normalize_embeddings=True, convert_to_numpy=True
        )
        query_embedding = np.asarray(query_embedding, dtype=np.float32)
        scores, indices = self.index.search(query_embedding, min(top_k, self.index.ntotal))

        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < 0:
                continue
            chunk = self.chunks[int(idx)]
            results.append({
                'chunk_id': chunk['id'],
                'text': chunk['text'],
                'score': float(score),
                'retrieval_method': 'dense',
                'metadata': {**chunk.get('metadata', {}),
                             **{key: value for key, value in chunk.items()
                                if key not in ('id', 'text', 'metadata')}},
            })
        return results
