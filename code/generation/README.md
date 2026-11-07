# Downstream task and generation

This directory contains the downstream modules that consume the ranked Steam review passages returned by the retriever.

| Component | Location | Purpose |
|---|---|---|
| Aspect-based Sentiment Analysis | [ABSA module and setup](ABSA_README.md) | Predict aspect-level sentiment from the review evidence |
| Evidence-grounded RAG summarization | `generation/rag_summary/` | Answer the user question with review citations |

The two components can use the same retrieved passages. The summarizer reads the review text directly and does not require predicted sentiment labels from the classification component. Its implementation and experiment instructions are documented in `rag_summary/README.md`.

## Report materials

- [Combined Generation report](docs/generation_report.md)
- [Generation overview paragraph](docs/generation_overview.md)
- [Section 4.1: Aspect-Based Sentiment Analysis](docs/aspect_report.md)
- [Section 4.2 supporting results: Evidence-Grounded RAG Summarization](rag_summary/experiments/final/report.md)

## Connecting to the UI

`code/app.py` passes the same `query` and ranked `hits` to the ABSA panel and the evidence-grounded summary. The summarization function is:

```python
from generation.rag_summary.rag_generator import generate_summary

result = generate_summary(query, hits, approach="improved", max_claims=4)
```

Configure the API environment variables below before making this call. Run integration commands from **`code/`**, so imports from `generation`, `retrieval`, and `paths` resolve.

### Retrieval input

Pass the original question and the same final `hits` list displayed by the app. Each hit is a dictionary with:

| Key | Content and use |
|---|---|
| `chunk_id` | Required. Original passage ID, retained in citations |
| `text` | Required. Review evidence used to generate the answer |
| `metadata` | Optional dictionary containing source information |
| `metadata.game_name` | Game identity used when interpreting the passage |
| `metadata.source_url` | Original review URL retained in the output citations |

Additional metadata such as `document_id`, `source`, and `title` can remain in the hit. Rank and score fields such as `retrieved_by`, `sparse_rank`, `dense_rank`, `rrf_rank`, `rrf_score`, and `score` are not added to the model context. The ranked list order is preserved, duplicate passage IDs are removed, and the original user question is used rather than the expanded retrieval query.

No conversion is required between the app's final `hits` list and the summarizer. BM25-only, dense-only, fused, and reranked results use the same input contract.

### API configuration

Set the following environment variables in the shell or hosting environment before starting the app:

| Variable | Example or purpose |
|---|---|
| `GENERATION_API_KEY` | Your generation provider's API key |
| `GENERATION_BASE_URL` | `https://api.deepseek.com` |
| `GENERATION_MODEL` | `deepseek-v4-pro` |

The API must support OpenAI-compatible Chat Completions and JSON object output. The summarizer reads credentials from the environment. Keys are not included in generated result files. Official DeepSeek V4 thinking is disabled automatically by the default client configuration.

### Streamlit integration

Run `streamlit run app.py` from `code/` and search for reviews. The ABSA panel runs on the retrieved passages and includes its results in the search export. The adjacent summary panel calls `render_summary(query, hits)` only when you click **Generate summary**. It reuses the saved answer when the question and passages are unchanged and writes a successful answer to `data/generation_results/rag_summary/latest_answer.json`.

### Generation output

The returned dictionary contains:

| Field | Content |
|---|---|
| `summary` | Answer text with inline `[chunk_id]` citations |
| `claims` | Retained claims, supporting `chunk_ids`, and evidence quotes for B/C/D |
| `citations` | Unique cited passage IDs and available source URLs |
| `status` | `ok`, `abstained`, or `no_evidence` |
| `usage` | Available input/output token counts |
| `latency_seconds` | Generation workflow time |
| `stage_calls`, `claim_audit` | Generation and self-verification records |

The `improved` configuration requires verbatim evidence quotes and validates them against the supplied passages. The other available configurations are `baseline`, `verify_delete`, and `verify_revise`. The latter two use the generation model for internal self-checking. Live generation uses the original chunk IDs for citations and does not require the benchmark's `fact_candidates`.

## Using retrieval directly

Run from `code/`. The following example follows the group's query expansion, fusion, and reranking pipeline, then generates an answer from the final results:

```python
from generation.rag_summary.rag_generator import generate_summary
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.query_expansion import expand_query
from retrieval.reranker import Reranker

query = "How is the soundtrack in Hollow Knight?"
expansion = expand_query(query, mode="hierarchical")
fused = HybridRetriever().retrieve_fused(
    query,
    top_k=30,
    candidates=20,
    filters={"game_name": ["Hollow Knight"]},
    sparse_query=expansion.sparse,
    dense_query=expansion.dense,
)
hits = Reranker().rerank(query, fused, top_k=5)
result = generate_summary(query, hits, approach="improved", max_claims=4)
```

`HybridRetriever.retrieve()` returns separate sparse and dense lists. Use the final list from fusion or reranking as the generation input.

### Using the UI's JSON export

The search interface's **Download results (JSON)** button produces `search_results.json` containing `query` and `results`. The generator accepts this structure directly. Save the export to `data/retrieval_results/search_results.json`, set the API environment variables, and run from `code/`:

```bash
python -c "from paths import GENERATION_RESULTS_DIR; (GENERATION_RESULTS_DIR / 'rag_summary').mkdir(parents=True, exist_ok=True)"
python generation/rag_summary/rag_generator.py ../data/retrieval_results/search_results.json --approach improved --max-claims 4 --output ../data/generation_results/rag_summary/answer.json
```

Fields such as `mode`, `filters`, `params`, `expansion`, and `timings_ms` remain in the retrieval export and are not passed to the model as review evidence.

## Evaluation

The live integration above answers questions using the current retrieval results. The summarization experiment uses a separate fixed 100-question benchmark with saved contexts and human-reviewed reference sets. It measures fact-selection Precision/Recall/F1, coverage-unit recall, and polarity-contrast coverage using deterministic code. Final scoring does not call an evaluator model.

To reproduce the saved summarization results without API calls, run from `code/`:

```bash
python generation/rag_summary/recompute_results.py generation/rag_summary/experiments/final/generation_results.json --output ../data/generation_results/rag_summary/report_reproduction
```

Use a new output directory. Full experiment settings, benchmark data, results, and additional commands are described in `rag_summary/README.md`. New questions or changed retrieval contexts need corresponding reference annotations before benchmark selection metrics can be computed.

For the ABSA interface, execution commands, and evaluation, see [ABSA instructions](ABSA_README.md).

## Conventions

- Run group integration commands from `code/` and take shared data locations from `paths.py`.
- Write integrated generation outputs and task-specific evaluation results under `GENERATION_RESULTS_DIR`, using separate subdirectories for each component. The summarizer uses `data/generation_results/rag_summary/`.
- The summarizer's bundled benchmark data and archived results remain inside `rag_summary/` for reproduction; the integration examples write new outputs to the shared data directory.
- Add any new dependencies to `code/requirements.txt` with pinned versions. The summarization module itself uses only the Python standard library.
- Read API keys from environment variables. `.env` is ignored by git and excluded from submission packages; this summarizer does not load `.env` files automatically.
- Keep the internal implementation instructions in each component's own README. This README describes the handoff between retrieval, the shared app, and the downstream modules.
- Update the downstream-task entry in the root `README.md` when the modules are integrated.
