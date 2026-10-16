import argparse
from dense_retriever import DenseRetriever


def main():
    parser = argparse.ArgumentParser(description='Search Steam reviews with dense retrieval')
    parser.add_argument('query', help='Natural-language search query')
    parser.add_argument('--top-k', type=int, default=5)
    args = parser.parse_args()

    retriever = DenseRetriever()
    results = retriever.retrieve(args.query, top_k=args.top_k, use_prefix=True)
    for rank, result in enumerate(results, start=1):
        print(f"\n{rank}. {result['chunk_id']} | score={result['score']:.4f}")
        print(result['text'])


if __name__ == '__main__':
    main()
