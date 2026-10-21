import argparse
import sys

from hybrid_retriever import HybridRetriever
from reranker import Reranker

SOURCE_TAGS = {('sparse',): 'S', ('dense',): 'D', ('sparse', 'dense'): 'S+D'}


def print_hits(hits):
    for rank, hit in enumerate(hits, start=1):
        print(f"\n{rank}. {hit['chunk_id']} | {hit['metadata']['game_name']} | score={hit['score']:.4f}")
        print(hit['text'])


def main():
    parser = argparse.ArgumentParser(description='Search Steam reviews with BM25 + dense retrieval and bge reranking')
    parser.add_argument('query', help='Natural-language search query')
    parser.add_argument('--top-k', type=int, default=5, help='Results kept after reranking')
    parser.add_argument('--candidates', type=int, default=20, help='Results retrieved by each method')
    parser.add_argument('--game', nargs='+', help='Filter reviews by exact game name(s) (case-insensitive)')
    parser.add_argument('--no-rerank', action='store_true',
                        help='Print the sparse and dense results separately without reranking')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    retriever = HybridRetriever()
    filters = {'game_name': args.game} if args.game else None
    results = retriever.retrieve(args.query, top_k=args.candidates, filters=filters)

    if args.no_rerank:
        for method, hits in results.items():
            print(f'\n===== {method} ({len(hits)} results) =====')
            print_hits(hits)
        return

    reranked = Reranker().rerank(args.query, results, top_k=args.top_k)
    for rank, hit in enumerate(reranked, start=1):
        source = SOURCE_TAGS.get(tuple(hit['retrieved_by']), '+'.join(hit['retrieved_by']))
        ranks = ' '.join(f"{m}#{hit[f'{m}_rank']}" for m in hit['retrieved_by'])
        print(f"\n{rank}. {hit['chunk_id']} | {hit['metadata']['game_name']} | "
              f"rerank={hit['score']:.4f} | {source} ({ranks})")
        print(hit['text'])


if __name__ == '__main__':
    main()
