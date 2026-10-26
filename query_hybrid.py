import argparse
import sys

from fusion import RRF_K
from hybrid_retriever import HybridRetriever
from query_expansion import expand_query
from reranker import Reranker

SOURCE_TAGS = {('sparse',): 'S', ('dense',): 'D', ('sparse', 'dense'): 'S+D'}


def describe_source(hit):
    source = SOURCE_TAGS.get(tuple(hit['retrieved_by']), '+'.join(hit['retrieved_by']))
    ranks = ' '.join(f"{m}#{hit[f'{m}_rank']}" for m in hit['retrieved_by'])
    return f'{source} ({ranks})'


def main():
    parser = argparse.ArgumentParser(
        description='Search Steam reviews with BM25 + dense retrieval, RRF fusion and bge reranking')
    parser.add_argument('query', help='Natural-language search query')
    parser.add_argument('--top-k', type=int, default=5, help='Results kept after reranking')
    parser.add_argument('--candidates', type=int, default=20, help='Results retrieved by each method')
    parser.add_argument('--rerank-candidates', type=int, default=30,
                        help='Top RRF-fused results passed to the reranker')
    parser.add_argument('--rrf-k', type=float, default=RRF_K, help='RRF smoothing constant')
    parser.add_argument('--game', nargs='+', help='Filter reviews by exact game name(s) (case-insensitive)')
    parser.add_argument('--no-rerank', action='store_true',
                        help='Print the RRF-fused top-k without reranking')
    parser.add_argument('--no-expand', action='store_true',
                        help='Disable aspect-based expansion for both retrievers')
    args = parser.parse_args()
    if args.rerank_candidates < args.top_k:
        parser.error('--rerank-candidates must be at least --top-k')
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    retriever = HybridRetriever()
    filters = {'game_name': args.game} if args.game else None
    expansion = None if args.no_expand else expand_query(args.query)
    sparse_query = args.query if expansion is None else expansion.sparse
    dense_query = args.query if expansion is None else expansion.dense
    if expansion is None:
        print('Query expansion: disabled')
    else:
        print('Detected aspects:', ', '.join(expansion.aspects) or '(none)')
        print('BM25 query:', sparse_query)
        print('Dense query:', dense_query)
    fused = retriever.retrieve_fused(args.query, top_k=args.rerank_candidates, candidates=args.candidates,
                                     filters=filters, rrf_k=args.rrf_k,
                                     sparse_query=sparse_query, dense_query=dense_query)

    if args.no_rerank:
        for rank, hit in enumerate(fused[:args.top_k], start=1):
            print(f"\n{rank}. {hit['chunk_id']} | {hit['metadata']['game_name']} | "
                  f"rrf={hit['rrf_score']:.4f} | {describe_source(hit)}")
            print(hit['text'])
        return

    reranked = Reranker().rerank(args.query, fused, top_k=args.top_k)
    for rank, hit in enumerate(reranked, start=1):
        print(f"\n{rank}. {hit['chunk_id']} | {hit['metadata']['game_name']} | "
              f"rerank={hit['score']:.4f} | rrf#{hit['rrf_rank']} | {describe_source(hit)}")
        print(hit['text'])


if __name__ == '__main__':
    main()
