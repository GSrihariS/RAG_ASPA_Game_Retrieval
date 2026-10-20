import argparse
from dense_retriever import DenseRetriever


def main():
    parser = argparse.ArgumentParser(description='Search Steam reviews with dense retrieval')
    parser.add_argument('query', help='Natural-language search query')
    parser.add_argument('--top-k', type=int, default=5)
    parser.add_argument('--no-prefix', action='store_true',
                        help='Disable BGE query prefix for baseline comparison')
    parser.add_argument('--game', help='Filter reviews by exact game name (case-insensitive)')
    args = parser.parse_args()

    retriever = DenseRetriever()
    results = retriever.retrieve(
        args.query, top_k=args.top_k,
        use_prefix=not args.no_prefix,
        filters={'game_name': args.game} if args.game else None,
    )
    for rank, result in enumerate(results, start=1):
        print(f"\n{rank}. {result['chunk_id']} | score={result['score']:.4f}")
        print(result['text'])


if __name__ == '__main__':
    main()
