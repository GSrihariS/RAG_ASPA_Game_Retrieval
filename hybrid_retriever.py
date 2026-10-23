from dense_retriever import DenseRetriever
from fusion import RRF_K, reciprocal_rank_fusion
from sparse_retriever import SparseRetriever


class HybridRetriever:
    """Send the query to BM25 and dense retrieval; return both ranked lists, or one list fused by RRF."""

    def __init__(self, sparse_dir='sparse_index', dense_dir='dense_index'):
        self.sparse = SparseRetriever(sparse_dir)
        self.dense = DenseRetriever(dense_dir)

    def retrieve(self, query, top_k=20, filters=None):
        return {
            'sparse': self.sparse.retrieve(query, top_k=top_k, filters=filters),
            'dense': self.dense.retrieve(query, top_k=top_k, filters=filters),
        }

    def retrieve_fused(self, query, top_k=10, candidates=20, filters=None, rrf_k=RRF_K):
        """Fuse the top `candidates` of each method with reciprocal rank fusion and keep the best `top_k`."""
        results = self.retrieve(query, top_k=candidates, filters=filters)
        return reciprocal_rank_fusion(results, k=rrf_k, top_k=top_k)
