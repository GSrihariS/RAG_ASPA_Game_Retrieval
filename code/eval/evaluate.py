"""Evaluate any ranked retriever against graded query-document relevance judgments.

Input formats:
  qrels.json:   {"query_id": {"chunk_id": 0|1|2, ...}, ...}
  results.json: {"query_id": ["chunk_id", ...], ...}

Unjudged documents are treated as nonrelevant for Precision and MRR and
assigned zero gain for nDCG. Recall is against *known* relevant judgments,
not necessarily all relevant documents in the corpus.
"""
import argparse
import json
import math
from pathlib import Path


def dcg(grades):
    return sum((2**grade - 1) / math.log2(rank + 1)
               for rank, grade in enumerate(grades, start=1))


def evaluate(qrels, results, k_values=(5, 10), relevant_grade=2):
    if not isinstance(qrels, dict) or not qrels:
        raise ValueError('qrels must be a nonempty JSON object')
    if not isinstance(results, dict):
        raise ValueError('results must be a JSON object')

    per_query = {}
    for query_id, labels in qrels.items():
        if not isinstance(labels, dict):
            raise ValueError(f'{query_id}: labels must be a dictionary')
        if any(type(g) is not int or g not in (0, 1, 2) for g in labels.values()):
            raise ValueError(f'{query_id}: relevance grades must be 0, 1, or 2')
        ranked = results.get(query_id, [])
        if not isinstance(ranked, list) or any(not isinstance(x, str) for x in ranked):
            raise ValueError(f'{query_id}: results must be a list of chunk IDs')
        if len(ranked) != len(set(ranked)):
            raise ValueError(f'{query_id}: duplicate retrieved chunk IDs')

        relevant = {doc_id for doc_id, grade in labels.items() if grade >= relevant_grade}
        scores = {}
        for k in k_values:
            top = ranked[:k]
            hits = sum(doc_id in relevant for doc_id in top)
            scores[f'P@{k}'] = hits / k
            scores[f'Recall@{k}'] = hits / len(relevant) if relevant else 0.0
            first = next((i for i, doc_id in enumerate(top, 1) if doc_id in relevant), None)
            scores[f'RR@{k}'] = 1.0 / first if first else 0.0
            actual = [labels.get(doc_id, 0) for doc_id in top]
            ideal = sorted(labels.values(), reverse=True)[:k]
            ideal_dcg = dcg(ideal)
            scores[f'nDCG@{k}'] = dcg(actual) / ideal_dcg if ideal_dcg else 0.0
        per_query[query_id] = scores

    keys = [f'{metric}@{k}' for k in k_values
            for metric in ('P', 'Recall', 'RR', 'nDCG')]
    mean = {key: sum(row[key] for row in per_query.values()) / len(per_query)
            for key in keys}
    return per_query, mean


def main():
    parser = argparse.ArgumentParser(description='Evaluate ranked retrieval results using qrels')
    parser.add_argument('--qrels', type=Path, required=True, help='JSON mapping query IDs to chunk relevance grades')
    parser.add_argument('--results', type=Path, required=True, help='JSON mapping query IDs to ranked chunk IDs')
    parser.add_argument('--k', type=int, nargs='+', default=[5, 10], help='Ranking cutoffs (default: 5 10)')
    parser.add_argument('--relevant-grade', type=int, choices=[1, 2], default=2,
                        help='Minimum grade considered relevant for binary metrics (default: 2)')
    parser.add_argument('--save', type=Path, help='Optional path to save metrics as JSON')
    args = parser.parse_args()
    if any(k <= 0 for k in args.k):
        parser.error('All k values must be positive')

    with args.qrels.open(encoding='utf-8') as f:
        qrels = json.load(f)
    with args.results.open(encoding='utf-8') as f:
        results = json.load(f)

    per_query, mean = evaluate(qrels, results, sorted(set(args.k)), args.relevant_grade)
    print(f'Evaluated {len(per_query)} queries | Relevant grade >= {args.relevant_grade}')
    for metric, value in mean.items():
        print(f'{metric:<12} {value:.4f}')
    print('Note: Recall uses known judged relevant chunks; incomplete qrels yield pooled/approximate recall.')
    print('Unjudged retrieved chunks count as irrelevant; use pooled judgments for fair comparisons.')

    if args.save:
        args.save.parent.mkdir(parents=True, exist_ok=True)
        with args.save.open('w', encoding='utf-8') as f:
            json.dump({'mean': mean, 'per_query': per_query}, f, indent=2)
        print(f'Saved metrics to {args.save}')


if __name__ == '__main__':
    main()
