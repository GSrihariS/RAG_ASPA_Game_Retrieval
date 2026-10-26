import json
import time
from collections import Counter
from datetime import datetime
from pathlib import Path

import streamlit as st

from fusion import RRF_K, merge, reciprocal_rank_fusion
from hybrid_retriever import HybridRetriever
from query_expansion import expand_query
from query_hybrid import describe_source
from reranker import Reranker

QUERIES_PATH = Path('eval/queries.jsonl')
MODES = ['Hybrid + Rerank', 'Hybrid (RRF)', 'BM25', 'Dense']
EXPANSION_MODES = {'Hierarchical': 'hierarchical', 'Broad': 'broad', 'Off': None}

st.set_page_config(page_title='Steam Review Search', page_icon='🎮', layout='wide')


@st.cache_resource(show_spinner='Loading BM25 and dense indexes...')
def load_retriever():
    return HybridRetriever()


@st.cache_resource(show_spinner='Loading reranker model...')
def load_reranker():
    reranker = Reranker()
    _ = reranker.model  # load the checkpoint now so it is not counted in the rerank timing
    return reranker


@st.cache_data
def load_sample_queries():
    if not QUERIES_PATH.exists():
        return []
    with QUERIES_PATH.open('r', encoding='utf-8') as file:
        return [json.loads(line) for line in file if line.strip()]


def game_names(retriever):
    return sorted({chunk['metadata']['game_name'] for chunk in retriever.sparse.chunks})


@st.cache_data(max_entries=64, show_spinner=False)
def search(query, mode, games, top_k, candidates, rerank_candidates, rrf_k, sparse_query, dense_query):
    """Run one query and return (hits, per-stage timings in ms). Cached so reruns keep the measured timings.

    `sparse_query` / `dense_query` are the (possibly expanded) retriever inputs; the reranker scores the original query.
    """
    retriever = load_retriever()
    filters = {'game_name': list(games)} if games else None
    timings = {}
    results = {}

    if mode in ('BM25', 'Hybrid (RRF)', 'Hybrid + Rerank'):
        start = time.perf_counter()
        results['sparse'] = retriever.sparse.retrieve(sparse_query, top_k=candidates, filters=filters)
        timings['BM25'] = (time.perf_counter() - start) * 1000
    if mode in ('Dense', 'Hybrid (RRF)', 'Hybrid + Rerank'):
        start = time.perf_counter()
        results['dense'] = retriever.dense.retrieve(dense_query, top_k=candidates, filters=filters)
        timings['Dense'] = (time.perf_counter() - start) * 1000

    if mode in ('BM25', 'Dense'):
        method = next(iter(results))
        hits = merge(results)[:top_k]
        for hit in hits:
            hit['score'] = hit[f'{method}_score']
    else:
        start = time.perf_counter()
        fused = reciprocal_rank_fusion(results, k=rrf_k, top_k=rerank_candidates)
        timings['RRF'] = (time.perf_counter() - start) * 1000
        if mode == 'Hybrid (RRF)':
            hits = fused[:top_k]
        else:
            reranker = load_reranker()
            start = time.perf_counter()
            hits = reranker.rerank(query, fused, top_k=top_k)
            timings['Rerank'] = (time.perf_counter() - start) * 1000

    timings['Total'] = sum(timings.values())
    return hits, timings


def use_sample(sample):
    st.session_state.query = sample['query_text']
    st.session_state.games = sample.get('target_games', [])


def score_line(hit, mode):
    parts = []
    if 'score' in hit and mode == 'Hybrid + Rerank':
        parts.append(f"rerank **{hit['score']:.4f}**")
    if 'rrf_score' in hit:
        parts.append(f"rrf {hit['rrf_score']:.4f} (#{hit['rrf_rank']})")
    if 'sparse_score' in hit:
        parts.append(f"bm25 {hit['sparse_score']:.2f}")
    if 'dense_score' in hit:
        parts.append(f"cosine {hit['dense_score']:.3f}")
    return ' · '.join(parts)


def render_stats(hits):
    recommended = sum(1 for hit in hits if hit['metadata'].get('steam_recommended'))
    share = recommended / len(hits)
    playtimes = [hit['metadata'].get('playtime_at_review_minutes') or 0 for hit in hits]

    col1, col2, col3 = st.columns(3)
    col1.metric('Recommended 👍', f'{share:.0%} ({recommended}/{len(hits)})')
    col2.metric('Not recommended 👎', f'{1 - share:.0%} ({len(hits) - recommended}/{len(hits)})')
    col3.metric('Avg playtime at review', f'{sum(playtimes) / len(playtimes) / 60:.1f} h')
    st.progress(share, text='Share of retrieved reviews that recommend the game (Steam metadata)')

    counts = Counter(hit['metadata']['game_name'] for hit in hits)
    if len(counts) > 1:
        st.caption('Hits per game')
        st.bar_chart(dict(counts.most_common()), horizontal=True)


def render_expansion(expansion, expansion_mode, mode):
    if expansion is None:
        st.caption('Query expansion: off')
        return
    if not expansion.aspects:
        st.caption('Query expansion: no aspect detected, query used as is')
        return
    with st.expander(f"Query expansion ({expansion_mode.lower()}): {', '.join(expansion.aspects)}"):
        if EXPANSION_MODES[expansion_mode] == 'hierarchical':
            for aspect, topics in expansion.subtopics:
                st.markdown(f"- **{aspect}**: {', '.join(topics) if topics else '(broad fallback)'}")
        if mode != 'Dense':
            st.markdown('**BM25 query**')
            st.code(expansion.sparse, language=None, wrap_lines=True)
        if mode != 'BM25':
            st.markdown('**Dense query**')
            st.code(expansion.dense, language=None, wrap_lines=True)
        if mode == 'Hybrid + Rerank':
            st.caption('The reranker scores candidates against the original query.')


def render_hit(rank, hit, mode):
    meta = hit['metadata']
    verdict = '👍 Recommended' if meta.get('steam_recommended') else '👎 Not recommended'
    created = meta.get('created_at_utc', '')[:10]
    playtime = (meta.get('playtime_at_review_minutes') or 0) / 60

    with st.container(border=True):
        st.markdown(f"**{rank}. {meta['game_name']}** &nbsp; {verdict} &nbsp; "
                    f"`{describe_source(hit)}`")
        st.caption(f"{score_line(hit, mode)} &nbsp;|&nbsp; 📅 {created} &nbsp;|&nbsp; ⏱ {playtime:.1f} h played"
                   f" &nbsp;|&nbsp; 👍 {meta.get('helpful_votes', 0)} helpful"
                   f" &nbsp;|&nbsp; chunk {meta.get('chunk_index')}/{meta.get('chunk_count')}")
        st.write(hit['text'])
        if meta.get('source_url'):
            st.markdown(f"[View on Steam]({meta['source_url']})")
        with st.expander('Metadata'):
            st.json({'chunk_id': hit['chunk_id'], **meta})


def main():
    retriever = load_retriever()
    games_all = game_names(retriever)

    with st.sidebar:
        st.header('Search settings')
        mode = st.radio('Retrieval mode', MODES, help='Hybrid modes fuse BM25 and dense results with RRF')
        games = st.multiselect('Filter by game', games_all, key='games',
                               help='Leave empty to search all games')
        top_k = st.slider('Results to show (top-k)', 1, 30, 5)
        expansion_mode = st.radio('Query expansion', list(EXPANSION_MODES), horizontal=True,
                                  help='Add aspect keywords to the BM25 and dense queries. Hierarchical only adds '
                                       'the matched subtopics; Broad adds the whole aspect vocabulary.')
        with st.expander('Advanced'):
            candidates = st.slider('Candidates per retriever', 5, 100, 20)
            rerank_candidates = st.slider('Fused candidates passed to reranker', 5, 100, 30,
                                          disabled=mode != 'Hybrid + Rerank')
            rrf_k = st.number_input('RRF k', min_value=0.0, value=float(RRF_K), step=10.0,
                                    disabled=mode not in ('Hybrid (RRF)', 'Hybrid + Rerank'))
        if mode == 'Hybrid + Rerank' and rerank_candidates < top_k:
            st.error('Reranker candidates must be at least top-k')
            st.stop()

    st.title('🎮 Steam Review Search')
    st.caption(f'Search {len(retriever.sparse.chunks):,} review passages from {len(games_all)} games '
               'with BM25, dense embeddings, RRF fusion and a cross-encoder reranker.')

    query = st.text_input('Ask about a game', key='query',
                          placeholder='e.g. What do players say about performance and optimization?')

    samples = load_sample_queries()
    if samples:
        with st.expander('Sample queries'):
            cols = st.columns(2)
            for i, sample in enumerate(samples):
                cols[i % 2].button(sample['query_text'], key=f"sample_{sample['query_id']}",
                                   on_click=use_sample, args=(sample,), width='stretch')

    if not query.strip():
        st.info('Enter a query or pick a sample query to start.')
        return

    query = query.strip()
    expansion = expand_query(query, mode=EXPANSION_MODES[expansion_mode]) if EXPANSION_MODES[expansion_mode] else None
    sparse_query = query if expansion is None else expansion.sparse
    dense_query = query if expansion is None else expansion.dense

    spinner = 'Retrieving and reranking...' if mode == 'Hybrid + Rerank' else 'Retrieving...'
    with st.spinner(spinner):
        hits, timings = search(query, mode, tuple(games), top_k, candidates, rerank_candidates, rrf_k,
                               sparse_query, dense_query)

    cols = st.columns(len(timings))
    for col, (stage, ms) in zip(cols, timings.items()):
        col.metric(f'{stage} (ms)', f'{ms:,.0f}')
    render_expansion(expansion, expansion_mode, mode)

    if not hits:
        st.warning('No matching reviews. Try other keywords or remove the game filter.')
        return

    st.subheader('Overview')
    render_stats(hits)
    with st.container(border=True):
        st.markdown('**Sentiment analysis / generated answer**')
        st.caption('Placeholder: the downstream generation and aspect-based sentiment module will be shown here.')

    st.subheader(f'Top {len(hits)} reviews')
    export = {
        'query': query,
        'mode': mode,
        'filters': {'game_name': list(games)} if games else None,
        'params': {'top_k': top_k, 'candidates': candidates,
                   'rerank_candidates': rerank_candidates, 'rrf_k': rrf_k},
        'expansion': None if expansion is None else {
            'mode': EXPANSION_MODES[expansion_mode],
            'aspects': list(expansion.aspects),
            'subtopics': {aspect: list(topics) for aspect, topics in expansion.subtopics},
            'sparse_query': expansion.sparse,
            'dense_query': expansion.dense,
        },
        'timings_ms': timings,
        'exported_at': datetime.now().isoformat(timespec='seconds'),
        'results': hits,
    }
    st.download_button('Download results (JSON)', json.dumps(export, ensure_ascii=False, indent=2),
                       file_name='search_results.json', mime='application/json')
    for rank, hit in enumerate(hits, start=1):
        render_hit(rank, hit, mode)


if __name__ == '__main__':
    main()
