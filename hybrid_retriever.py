from dense_retriever import DenseRetriever
from sparse_retriever import SparseRetriever


class HybridRetriever:
    """Send the query to BM25 and dense retrieval and return both ranked lists unfused."""

    def __init__(self, sparse_dir='sparse_index', dense_dir='dense_index'):
        self.sparse = SparseRetriever(sparse_dir)
        self.dense = DenseRetriever(dense_dir)

    def retrieve(self, query, top_k=20, filters=None):
        return {
            'sparse': self.sparse.retrieve(query, top_k=top_k, filters=filters),
            'dense': self.dense.retrieve(query, top_k=top_k, filters=filters),
        }
