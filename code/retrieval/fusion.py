RRF_K = 60


def merge(results):
    """Deduplicate retriever outputs by chunk ID, keeping each method's rank and score.

    `results` is HybridRetriever.retrieve output ({method: [hits]}), a single list of hits,
    or a list of already merged candidates (e.g. reciprocal_rank_fusion output), which is copied as is.
    """
    if isinstance(results, list):
        if results and 'retrieved_by' in results[0]:
            return [dict(candidate) for candidate in results]
        method = results[0]['retrieval_method'] if results else 'single'
        results = {method: results}
    merged = {}
    for method, hits in results.items():
        for rank, hit in enumerate(hits, start=1):
            entry = merged.get(hit['chunk_id'])
            if entry is None:
                entry = merged[hit['chunk_id']] = {
                    'chunk_id': hit['chunk_id'],
                    'text': hit['text'],
                    'metadata': hit['metadata'],
                    'retrieved_by': [],
                }
            entry['retrieved_by'].append(method)
            entry[f'{method}_rank'] = rank
            entry[f'{method}_score'] = hit['score']
    return list(merged.values())


def reciprocal_rank_fusion(results, k=RRF_K, top_k=None):
    """Fuse ranked lists ({method: [hits]}) by summing 1 / (k + rank) over the methods that returned each chunk.

    Only ranks are used, so BM25 and cosine scores need no normalization. Ties keep merge order
    (the first method's ranking first), so the output is deterministic.
    """
    if isinstance(k, bool) or not isinstance(k, (int, float)) or k < 0:
        raise ValueError('k must be a nonnegative number')
    if top_k is not None and (not isinstance(top_k, int) or top_k < 1):
        raise ValueError('top_k must be a positive integer or None')

    candidates = merge(results)
    for candidate in candidates:
        candidate['rrf_score'] = sum(1.0 / (k + candidate[f'{method}_rank'])
                                     for method in candidate['retrieved_by'])
        candidate['score'] = candidate['rrf_score']
        candidate['retrieval_method'] = 'hybrid_rrf'
    candidates.sort(key=lambda c: -c['rrf_score'])
    for rank, candidate in enumerate(candidates, start=1):
        candidate['rrf_rank'] = rank
    return candidates[:top_k]
