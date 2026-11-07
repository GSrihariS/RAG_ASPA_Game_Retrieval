# Aspect-Based Opinion RAG over Steam Game Reviews

AI6127 group project. A retrieval-augmented generation system that finds what players say about a
specific aspect of a game (story, performance, controls, ...) in 10,000 Steam reviews from 20 games,
and answers from that evidence.

## Layout

The repository has two top-level folders, one for each submission package.

```
code/                     source code (code.zip, together with this README)
  app.py                  Streamlit UI
  paths.py                locations of everything under data/
  requirements.txt
  data_pipeline/          knowledge-base construction: collection, cleaning, chunking, agreement
  retrieval/              BM25, dense, RRF fusion, reranking, query expansion, index builders
  generation/             downstream task: RAG summarization (rag_summary/), experiments and tests
  eval/                   retrieval evaluation and annotation-set tools
  scripts/                batch runs and submission packaging
  docs/UI.md              UI guide
data/                     all data and results (data.zip), described in data/README.md
  knowledge_base/         the Steam reviews and their chunks
  evaluation_dataset/     annotated chunks (eval.xls), agreement, retrieval queries and label statistics
  indexes/                prebuilt BM25 and FAISS indexes
  retrieval_results/      the 100-query retrieval evaluation and final pipeline results for 100 queries
  generation_results/     generated answers from the summarization experiment, and their metrics
```

| Assignment part | Code | Data and results |
|---|---|---|
| Knowledge base (20 points) | `code/data_pipeline/` | `data/knowledge_base/` |
| Retrieval (40 points) | `code/retrieval/`, `code/eval/`, `code/app.py` | `data/indexes/`, `data/evaluation_dataset/`, `data/retrieval_results/` |
| Downstream task and generation (40 points) | `code/generation/` | `data/evaluation_dataset/`, `data/generation_results/` |

## Setup

Tested with Python 3.13 on Windows 11.

1. Unpack `code.zip` and `data.zip` into the same folder, so that `code/` and `data/` sit side by side.
   In a git clone, unpack `data.zip` over the repository instead: git holds only part of `data/`.
2. For GPU acceleration, install the CUDA build of torch first. Without this step, `requirements.txt`
   installs the default build for your platform.

   ```bash
   pip install torch==2.10.0 --index-url https://download.pytorch.org/whl/cu128
   ```

3. Install the dependencies:

   ```bash
   cd code
   pip install -r requirements.txt
   ```

There is nothing to compile. The models download from Hugging Face on first use:
`BAAI/bge-small-en-v1.5` (about 130 MB) and `BAAI/bge-reranker-v2-m3` (about 2.2 GB).

## Run

Run every command from the `code/` folder.

**Search UI**, then open http://localhost:8501 (see [docs/UI.md](code/docs/UI.md)):

```bash
streamlit run app.py
```

**Command-line search:**

```bash
python -m retrieval.query_sparse "How is the soundtrack?" --game "Hollow Knight"
python -m retrieval.query_dense "How is the soundtrack?" --game "Hollow Knight"
python -m retrieval.query_hybrid "How is the soundtrack?" --game "Hollow Knight"
```

**Rebuild the indexes.** `data.zip` already contains them, so this is only needed if the chunks change:

```bash
python -m retrieval.build_sparse_index
python -m retrieval.build_dense_index
```

**Retrieval evaluation.** About 40 minutes with the reranker on an RTX 3070 Ti Laptop GPU; details and
results are in [eval/README.md](code/eval/README.md):

```bash
python eval/evaluate_annotated.py
```

**Annotation set tools:**

```bash
python eval/dataset_stats.py
python eval/export_eval_xls.py
```

## Knowledge-base construction

`data.zip` already contains the built knowledge base, so these steps are only needed to rebuild it. Run them
from `code/`; [code/data_pipeline/README.md](code/data_pipeline/README.md) has the details and output files.

```bash
python -m data_pipeline.collect_steam_reviews
python -m data_pipeline.process_steam_reviews
```

Collection calls the Steam API and writes to a new folder, `data/knowledge_base_all_365_500/`. Processing reads
`data/knowledge_base/all_reviews.json` and overwrites `data/knowledge_base/processed/`. If the chunks change,
rebuild the indexes as well.

**Annotation agreement.** This writes `data/evaluation_dataset/iaa_report.json`:

```bash
python -m data_pipeline.calculate_iaa
```

## Downstream task and generation

The app uses the same ranked reviews for two downstream tasks. **Aspect-based sentiment analysis (ABSA)** shows
aspect sentiment distributions with source excerpts and requires no generation API key. **Evidence-grounded RAG
summarization** answers the question with citations. Its experiment compares four methods (`baseline`, `improved`,
`verify_delete`, `verify_revise`) on 100 fixed questions. Run these commands from `code/`.

**Inspect aspect sentiment in the UI.** Start `streamlit run app.py`, run a search, and choose **Previous baseline**
or **Optimized** in the Aspect model selector. See the [ABSA instructions](code/generation/ABSA_README.md) and
[report Section 4.1](code/generation/docs/aspect_report.md) for the method, evaluation, and demonstration.

**Generate an answer in the UI.** This needs an API key for an OpenAI-compatible service. Set the key, start the
UI, search, then click **Generate summary**. On Windows PowerShell, use `$env:GENERATION_API_KEY = "your-key"`.

```bash
export GENERATION_API_KEY=your-key
streamlit run app.py
```

The service defaults to `https://api.deepseek.com` and the model to `deepseek-v4-pro`. To change them, set
`GENERATION_BASE_URL` and `GENERATION_MODEL`.

**Reproduce the final scores.** This rescores the saved answers and needs no API key. Use a new output folder:

```bash
python generation/rag_summary/recompute_results.py generation/rag_summary/experiments/final/generation_results.json --output ../data/generation_results/rag_summary/report_reproduction
```

The final scores are listed in [data/README.md](data/README.md). Python usage and the UI integration are in
[code/generation/README.md](code/generation/README.md); the method descriptions and the commands for rerunning
the experiment are in [rag_summary/README.md](code/generation/rag_summary/README.md).

