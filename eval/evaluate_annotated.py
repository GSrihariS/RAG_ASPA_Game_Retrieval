"""Evaluate retrieval on the human-annotated chunk set with the query benchmark.

Run from the project root:  python eval/evaluate_annotated.py

Only annotated chunks have labels, so every ranking is condensed (Sakai & Kando, 2008): the
whole pipeline (retrieval, fusion, reranking) runs on the full index, and chunks without an
annotation are dropped only from its final output, before scoring. Fusion and reranking use an
evaluation depth (300 / 300 by default) deeper than the app's 20 / 30, so that enough annotated
chunks remain after condensing (only ~8% of the index is annotated).

Relevance grades for a query with target games G (empty = any game), target aspects A
and target sentiment S:
  S = any
    2  chunk is from G and an aspect in A is mentioned with an opinion (Opinionated, not Neutral/Unclear)
    1  ... mentioned, but Objective or Neutral/Unclear
  S = Positive / Negative
    2  chunk is from G and an aspect in A has sentiment S and is Opinionated
    1  ... sentiment S but not Opinionated, or Mixed / Neutral / Unclear
  0  otherwise (wrong game, aspect not mentioned, or opposite sentiment)

Configurations, each with and without hierarchical query expansion (+qe) and a game_name
filter on the target games (+filter; queries without target games are never filtered):
  bm25           BM25 ranking
  dense          dense ranking
  hybrid_rrf     top-N of BM25 and of dense fused by reciprocal rank fusion
  hybrid_rerank  top-M of hybrid_rrf reranked by bge-reranker-v2-m3 on the original query
"""
import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from evaluate import evaluate  # noqa: E402
from fusion import RRF_K, reciprocal_rank_fusion  # noqa: E402
from hybrid_retriever import HybridRetriever  # noqa: E402
from query_expansion import expand_query  # noqa: E402
from reranker import Reranker  # noqa: E402

CONFIGS = ('bm25', 'dense', 'hybrid_rrf', 'hybrid_rerank')
VARIANTS = ('', '+qe', '+filter', '+qe+filter')
QUERY_TYPES = ('single_aspect', 'aspect_sentiment', 'multi_aspect', 'cross_game')
MIN_RELEVANT, MIN_HIGHLY_RELEVANT = 5, 3


def load_annotations(path):
    with path.open(encoding='utf-8') as f:
        records = json.load(f)['records']
    return {r['chunk_id']: r for r in records if r['status'] == 'Confirmed'}


def grade(record, query):
    if query['target_games'] and record['game_name'] not in query['target_games']:
        return 0
    target = query['target_sentiment']
    best = 0
    for aspect in query['target_aspects']:
        label = record['human_annotation'][aspect]
        sentiment = label['sentiment']
        if sentiment == 'Not mentioned':
            continue
        opinionated = label['subjectivity'] == 'Opinionated'
        if target == 'any':
            g = 2 if opinionated and sentiment not in ('Neutral', 'Unclear') else 1
        elif sentiment == target:
            g = 2 if opinionated else 1
        elif sentiment in ('Mixed', 'Neutral', 'Unclear'):
            g = 1
        else:
            g = 0
        best = max(best, g)
    return best


def r_precision(qrels, results, relevant_grade):
    values = []
    for query_id, labels in qrels.items():
        relevant = {c for c, g in labels.items() if g >= relevant_grade}
        top = results.get(query_id, [])[:len(relevant)]
        values.append(sum(c in relevant for c in top) / len(relevant))
    return sum(values) / len(values)


def bpref(qrels, results, relevant_grade):
    """Buckley & Voorhees (2004): only judged chunks count, nonrelevant ones above each relevant hit."""
    values = []
    for query_id, labels in qrels.items():
        relevant = {c for c, g in labels.items() if g >= relevant_grade}
        nonrelevant = len(labels) - len(relevant)
        denom = min(len(relevant), nonrelevant)
        above, total = 0, 0.0
        for c in results.get(query_id, []):
            if c in relevant:
                total += 1 - min(above, len(relevant)) / denom if denom else 1
            elif c in labels:
                above += 1
        values.append(total / len(relevant))
    return sum(values) / len(values)


def md_table(header, rows):
    lines = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    lines += ['| ' + ' | '.join(row) + ' |' for row in rows]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Evaluate retrieval on the annotated chunk set')
    parser.add_argument('--annotations', type=Path,
                        default=Path('data/steam_annotations_confirmed.json'))
    parser.add_argument('--queries', type=Path, default=Path('eval/queries.jsonl'))
    parser.add_argument('--candidates', type=int, default=300,
                        help='Chunks taken from each of BM25 and dense for RRF (app: 20; deeper so that '
                             'enough annotated chunks remain after condensing)')
    parser.add_argument('--rerank-candidates', type=int, default=300,
                        help='Top RRF-fused chunks passed to the reranker (app: 30)')
    parser.add_argument('--device', default='cuda', help='Device for the reranker')
    parser.add_argument('--batch-size', type=int, default=32, help='Reranker batch size')
    parser.add_argument('--rrf-k', type=float, default=RRF_K)
    parser.add_argument('--k', type=int, nargs='+', default=[5, 10, 20])
    parser.add_argument('--relevant-grade', type=int, choices=[1, 2], default=1)
    parser.add_argument('--out-dir', type=Path, default=Path('eval/results'))
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if args.device.startswith('cuda'):
        import torch
        if not torch.cuda.is_available():
            sys.exit('CUDA is not available; install a CUDA build of torch or pass --device cpu')

    annotated = load_annotations(args.annotations)
    with args.queries.open(encoding='utf-8') as f:
        queries = [json.loads(line) for line in f if line.strip()]

    qrels = {q['query_id']: {c: grade(r, q) for c, r in annotated.items()} for q in queries}
    for q in queries:
        grades = qrels[q['query_id']].values()
        rel, high = sum(g >= 1 for g in grades), sum(g == 2 for g in grades)
        if rel < MIN_RELEVANT or high < MIN_HIGHLY_RELEVANT:
            sys.exit(f"{q['query_id']} has too few relevant annotated chunks ({rel} relevant, {high} at grade 2)")

    # Rankings are checkpointed per query, so a crashed run resumes where it stopped.
    args.out_dir.mkdir(parents=True, exist_ok=True)
    checkpoint = args.out_dir / 'checkpoint.jsonl'
    settings = [args.candidates, args.rerank_candidates, args.rrf_k, args.relevant_grade]
    done = {}
    if checkpoint.exists():
        with checkpoint.open(encoding='utf-8') as f:
            for line in f:
                if line.strip():
                    record = json.loads(line)
                    done[record['query_id']] = record
        print(f'Resuming: {len(done)} queries in {checkpoint}')

    reranker = Reranker(device=args.device, batch_size=args.batch_size)
    _ = reranker.model  # load the ~2.2 GB checkpoint before the indexes to keep peak memory low
    retriever = HybridRetriever()
    depth = len(retriever.sparse.chunks)
    runs, cand_recall = defaultdict(dict), defaultdict(list)

    with checkpoint.open('a', encoding='utf-8') as ckpt:
        for q in queries:
            query_id, text, games = q['query_id'], q['query_text'], q['target_games']
            relevant = {c for c, g in qrels[query_id].items() if g >= args.relevant_grade}
            record = done.get(query_id)
            if record is None or record['settings'] != settings + [text, games]:
                record = {'query_id': query_id, 'settings': settings + [text, games], 'runs': {}, 'cand_recall': {}}
                expansion = expand_query(text)
                for variant in VARIANTS:
                    filters = {'game_name': games} if '+filter' in variant and games else None
                    sparse_query = expansion.sparse if '+qe' in variant else text
                    dense_query = expansion.dense if '+qe' in variant else text
                    # Run the pipeline on the whole (filtered) index; condense only its final outputs.
                    hits = retriever.retrieve(text, top_k=depth, filters=filters,
                                              sparse_query=sparse_query, dense_query=dense_query)
                    fused = reciprocal_rank_fusion({m: hs[:args.candidates] for m, hs in hits.items()},
                                                   k=args.rrf_k)
                    reranked = reranker.rerank(text, fused[:args.rerank_candidates], top_k=args.rerank_candidates)
                    condense = lambda hs: [h['chunk_id'] for h in hs if h['chunk_id'] in annotated]  # noqa: E731

                    record['runs']['bm25' + variant] = condense(hits['sparse'])
                    record['runs']['dense' + variant] = condense(hits['dense'])
                    record['runs']['hybrid_rrf' + variant] = condense(fused)
                    record['runs']['hybrid_rerank' + variant] = condense(reranked)
                    pool = set(condense(fused[:args.rerank_candidates]))
                    record['cand_recall'][variant] = len(pool & relevant) / len(relevant)
                ckpt.write(json.dumps(record) + '\n')
                ckpt.flush()
                print(f"{query_id} relevant={len(relevant):<4} aspects={','.join(expansion.aspects) or '-'}",
                      flush=True)
            for name, ranked in record['runs'].items():
                runs[name][query_id] = ranked
            for variant, value in record['cand_recall'].items():
                cand_recall[variant].append(value)

    k_values = sorted(set(args.k))
    table = {}
    for name, results in runs.items():
        per_query, mean = evaluate(qrels, results, k_values, args.relevant_grade)
        mean['R-Prec'] = r_precision(qrels, results, args.relevant_grade)
        mean['bpref'] = bpref(qrels, results, args.relevant_grade)
        for query_id, labels in qrels.items():
            per_query[query_id]['R-Prec'] = r_precision({query_id: labels}, results, args.relevant_grade)
            per_query[query_id]['bpref'] = bpref({query_id: labels}, results, args.relevant_grade)
        table[name] = {'mean': mean, 'per_query': per_query}

    names = [c + v for v in VARIANTS for c in CONFIGS]
    kmax = max(k_values)
    metrics = ([f'P@{k}' for k in k_values] + [f'Recall@{k}' for k in k_values] + [f'RR@{kmax}']
               + [f'nDCG@{k}' for k in k_values] + ['R-Prec', 'bpref'])

    # Condensed lists can be shorter than k; missing ranks then count as nonrelevant (as in trec_eval).
    lengths = {n: {q: len(runs[n][q]) for q in qrels} for n in names}
    short = {n: {k: sorted(q for q, length in lengths[n].items() if length < k) for k in k_values} for n in names}
    for n in names:
        if short[n][kmax]:
            print(f"Warning: {n} has fewer than {kmax} annotated chunks for {', '.join(short[n][kmax])}")
    fmt = lambda x: f'{x:.4f}'  # noqa: E731
    report = [
        f'# Retrieval results: {len(queries)} queries, {len(annotated)} annotated chunks',
        '',
        f'Relevant grade >= {args.relevant_grade} for P / Recall / RR / R-Prec / bpref; nDCG uses grades 0-2. '
        f'Candidates per retriever {args.candidates}, reranker candidates {args.rerank_candidates}, '
        f'RRF k {args.rrf_k:g}. `+qe` = hierarchical query expansion, `+filter` = game_name filter on the '
        'target games (cross-game queries are never filtered).',
        '',
        '## Knowledge base and protocol',
        '',
        f'- The knowledge base is the full index: {depth} chunks from '
        f"{len({c['document_id'] for c in retriever.sparse.chunks})} reviews of "
        f"{len({c['metadata']['game_name'] for c in retriever.sparse.chunks})} games, not only the annotated set.",
        f'- The {len(annotated)} annotated chunks are a subset of it (same chunk IDs and text).',
        '- The whole pipeline runs on the full knowledge base: BM25 and dense rank every chunk, RRF fuses their '
        f'top {args.candidates} by real rank, and the reranker reorders the fused top {args.rerank_candidates}. '
        'Unannotated chunks are dropped only from each final ranking (condensed lists, Sakai & Kando 2008), '
        'and only annotated chunks are scored.',
        f'- The evaluation depth ({args.candidates} / {args.rerank_candidates}) is deeper than the app '
        '(20 / 30): only ~8% of the index is annotated, so the app-depth top 30 keeps a median of 3 annotated '
        'chunks, too few for @10. The reranker scores each chunk independently, so the order of the annotated '
        'chunks does not depend on the unannotated ones around them.',
        '- So the metrics measure how the annotated chunks are ordered relative to each other in a real, '
        'full-corpus ranking (BM25 statistics and the dense neighbourhood come from all chunks). Unannotated '
        'chunks in between are skipped, neither counted as hits nor as errors, so the scores are not the '
        'exact top-k a user sees in the app.',
        '- bpref (Buckley & Voorhees 2004) uses only judged chunks by definition, so it is the same on the full '
        'and the condensed ranking; it is binary and reported next to the graded nDCG.',
        '',
        '## Mean over all queries',
        '',
        md_table(['run', *metrics],
                 [[n, *(fmt(table[n]['mean'][m]) for m in metrics)] for n in names]),
        '',
        'Rerank candidate recall (relevant chunks in the RRF top-'
        f'{args.rerank_candidates}): '
        + ', '.join(f"{v or 'base'} {sum(r) / len(r):.4f}" for v, r in cand_recall.items()),
        '',
        '## Annotated chunks per condensed ranking',
        '',
        'Lists shorter than k count the missing ranks as nonrelevant.',
        '',
        md_table(['run', 'min', 'median', *(f'queries < {k}' for k in k_values)],
                 [[n, str(min(lengths[n].values())), str(sorted(lengths[n].values())[len(qrels) // 2]),
                   *(f"{len(short[n][k])}" + (f" ({', '.join(short[n][k])})" if 0 < len(short[n][k]) <= 5 else '')
                     for k in k_values)] for n in names]),
        '',
    ]
    types = [t for t in QUERY_TYPES if any(q['query_type'] == t for q in queries)]
    by_type = {t: [q['query_id'] for q in queries if q['query_type'] == t] for t in types}
    for metric in ('nDCG@10' if 10 in k_values else f'nDCG@{kmax}', 'R-Prec'):
        report += [f'## {metric} by query type', '',
                   md_table(['run', *(f'{t} ({len(by_type[t])})' for t in types), f'all ({len(queries)})'],
                            [[n, *(fmt(sum(table[n]['per_query'][i][metric] for i in by_type[t]) / len(by_type[t]))
                                   for t in types), fmt(table[n]['mean'][metric])] for n in names]),
                   '']
    primary = 'nDCG@10' if 10 in k_values else f'nDCG@{kmax}'
    shown = ['bm25', 'dense', 'hybrid_rrf', 'hybrid_rerank', 'hybrid_rerank+qe', 'hybrid_rerank+qe+filter']
    report += [f'## {primary} per query', '',
               md_table(['query', 'type', 'rel', *shown, 'query text'],
                        [[q['query_id'], q['query_type'],
                          str(sum(g >= args.relevant_grade for g in qrels[q['query_id']].values())),
                          *(fmt(table[n]['per_query'][q['query_id']][primary]) for n in shown), q['query_text']]
                         for q in queries]),
               '']
    print('\n' + '\n'.join(report))

    with (args.out_dir / 'qrels.json').open('w', encoding='utf-8') as f:
        json.dump({q: {c: g for c, g in labels.items() if g} for q, labels in qrels.items()}, f, indent=2)
    with (args.out_dir / 'runs.json').open('w', encoding='utf-8') as f:
        json.dump(runs, f, indent=2)
    with (args.out_dir / 'metrics.json').open('w', encoding='utf-8') as f:
        json.dump({'configs': table,
                   'rerank_candidate_recall': {v or 'base': sum(r) / len(r) for v, r in cand_recall.items()},
                   'judged_lengths': lengths},
                  f, indent=2)
    (args.out_dir / 'report.md').write_text('\n'.join(report), encoding='utf-8')
    checkpoint.unlink()
    print(f'\nSaved qrels, runs, metrics and report to {args.out_dir}')


if __name__ == '__main__':
    main()
