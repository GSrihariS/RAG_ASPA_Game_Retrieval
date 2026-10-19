import argparse
import sys
from sparse_retriever import SparseRetriever


def main():
    parser = argparse.ArgumentParser(description='Search Steam reviews with BM25 sparse retrieval')
    parser.add_argument('query', help='Natural-language search query')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--appid', type=int, nargs='+', help='Restrict results to these Steam app IDs')
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

    retriever = SparseRetriever()
    filters = {'appid': args.appid} if args.appid else None
    results = retriever.retrieve(args.query, top_k=args.top_k, filters=filters)
    for rank, result in enumerate(results, start=1):
        print(f"\n{rank}. {result['chunk_id']} | {result['metadata']['game_name']} | score={result['score']:.4f}")
        print(result['text'])


if __name__ == '__main__':
    main()
