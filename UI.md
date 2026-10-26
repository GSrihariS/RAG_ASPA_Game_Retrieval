# Search UI

A Streamlit app (`app.py`) for searching the Steam review knowledge base with BM25, dense retrieval, RRF fusion and cross-encoder reranking.

## Prerequisites

- Python dependencies:

  ```bash
  pip install -r requirements.txt
  ```

- The indexes `sparse_index/` and `dense_index/` in the project root. If they are missing, build them with:

  ```bash
  python build_sparse_index.py
  python build_dense_index.py
  ```

## Run

From the project root:

```bash
streamlit run app.py
```

Then open http://localhost:8501 in a browser.

The first start takes about 30–40 s while the indexes and embedding model load. The reranker (`BAAI/bge-reranker-v2-m3`, ~2.2 GB) is downloaded and loaded the first time you search in **Hybrid + Rerank** mode. After that, both stay cached while the server runs.

## Usage

- **Sidebar**: choose the retrieval mode (Hybrid + Rerank, Hybrid (RRF), BM25, Dense), filter by game, set top-k, and pick the query expansion mode (Hierarchical by default, Broad, or Off). More parameters (candidates per retriever, reranker candidates, RRF k) are under **Advanced**.
- **Query**: type a question or pick one under **Sample queries** (loaded from `eval/queries.jsonl`).
- **Results**: per-stage latency in ms, the detected aspects/subtopics with the expanded BM25 and dense queries (the reranker still scores the original query), the average playtime of the reviewers, and one card per review with scores, source ranks (`S` = BM25, `D` = dense), date, playtime and a link to the review on Steam.
- **Download results (JSON)** saves the query, parameters, timings and results.
