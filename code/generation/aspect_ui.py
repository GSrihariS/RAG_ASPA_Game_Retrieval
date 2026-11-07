"""Streamlit panel for aspect-based sentiment analysis."""
import json

import streamlit as st


@st.cache_resource(show_spinner='Loading aspect classifiers...')
def load_aspect_analyzer(checkpoint, checkpoint_version):
    from generation.aspect_analysis import AspectAnalyzer

    return AspectAnalyzer.load(checkpoint)


def render_aspect_analysis(hits, query):
    st.subheader('Aspect-based sentiment analysis')
    model_name = st.radio('Aspect model', ['Optimized', 'Previous baseline'], horizontal=True, key='aspect_model')
    try:
        from generation.aspect_analysis import MODEL_DIR

        filename = 'aspect_model_previous.joblib' if model_name == 'Previous baseline' else 'aspect_model.joblib'
        checkpoint = MODEL_DIR / filename
        version = (checkpoint.stat().st_mtime_ns, checkpoint.stat().st_size)
        result = load_aspect_analyzer(checkpoint, version).analyze(hits, query=query)
    except (ImportError, FileNotFoundError) as exc:
        st.info('Aspect analysis is unavailable. Install code/requirements.txt and run '
                'python -m generation.evaluate_aspect to prepare the local model.')
        with st.expander('Setup details'):
            st.code(str(exc), language=None)
        return None
    st.caption('Automatic predictions for the retrieved reviews. Check the source excerpts before using '
               'these counts in an answer. Each review counts once per aspect. '
               'Conflicting positive/negative chunks are listed as Mixed and excluded from percentages. '
               'Source excerpts have not been checked for entailment.')
    rows = []
    for aspect in result['aspects']:
        row = {'Aspect': aspect['aspect'], 'Reviews mentioning aspect': aspect['mentioned_review_count'],
               'Mixed reviews': aspect['mixed_review_count']}
        row.update({s['sentiment']: f"{s['ratio']:.1%}" if s['ratio'] is not None else '—'
                    for s in aspect['sentiments']})
        rows.append(row)
    st.dataframe(rows, hide_index=True, width='stretch')
    for aspect in result['aspects']:
        if not aspect['mentioned_review_count']:
            continue
        with st.expander(f"{aspect['aspect']}: source excerpts ({aspect['mentioned_review_count']} reviews)"):
            for item in result['evidence']:
                if item['aspect'] == aspect['aspect']:
                    st.markdown(f"**{item['sentiment']}** · `{item['chunk_id']}`")
                    st.write(item['excerpt']['text'])
                    if item.get('decision_cue'):
                        st.caption(f"Explicit evaluation cue: {item['sentiment']}. "
                                   f"The classifier originally predicted {item['classifier_sentiment']}.")
                    if item['excerpt']['selection_method'] == 'full_passage_fallback':
                        st.caption('Full passage shown: no aspect keyword was found. '
                                   'Check whether this aspect is actually discussed.')
                    if item.get('source_url'):
                        st.markdown(f"[View on Steam]({item['source_url']})")
    st.download_button('Download aspect results (JSON)', json.dumps(result, ensure_ascii=False, indent=2),
                       file_name='aspect_results.json', mime='application/json')
    return result
