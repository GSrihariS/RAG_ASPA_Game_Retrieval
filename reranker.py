from sentence_transformers import CrossEncoder

from fusion import merge

MODEL_NAME = 'BAAI/bge-reranker-v2-m3'


class Reranker:
    def __init__(self, model_name=MODEL_NAME, max_length=512, batch_size=16, device=None):
        self.model_name = model_name
        self.max_length = max_length
        self.batch_size = batch_size
        self.device = device
        self._model = None

    @property
    def model(self):
        # Load lazily: the checkpoint is ~2.2 GB and only needed once reranking starts.
        if self._model is None:
            self._model = CrossEncoder(self.model_name, max_length=self.max_length, device=self.device)
        return self._model

    merge = staticmethod(merge)

    def rerank(self, query, results, top_k=5):
        if not isinstance(query, str) or not query.strip():
            raise ValueError('Query must be a nonempty string')
        if not isinstance(top_k, int) or top_k < 1:
            raise ValueError('top_k must be a positive integer')

        candidates = self.merge(results)
        if not candidates:
            return []
        scores = self.model.predict([(query, c['text']) for c in candidates],
                                    batch_size=self.batch_size, show_progress_bar=False)
        for candidate, score in zip(candidates, scores):
            candidate['score'] = float(score)
            candidate['retrieval_method'] = 'hybrid_rerank'
        candidates.sort(key=lambda c: -c['score'])
        return candidates[:top_k]
