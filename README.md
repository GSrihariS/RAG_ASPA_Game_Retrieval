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
  generation/             downstream task and answer generation
  eval/                   retrieval evaluation and annotation-set tools
  scripts/                batch runs and submission packaging
  docs/UI.md              UI guide
data/                     all data and results (data.zip), described in data/README.md
  knowledge_base/         the Steam reviews and their chunks
  evaluation_dataset/     annotated chunks (eval.xls), retrieval queries and label statistics
  indexes/                prebuilt BM25 and FAISS indexes
  retrieval_results/      sample-query results and the 100-query retrieval evaluation
  generation_results/     generated answers or classification results, and their metrics
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

TODO (Data group): how to run the collection, cleaning, chunking and agreement scripts.
See [code/data_pipeline/README.md](code/data_pipeline/README.md).

## Downstream task and generation

TODO (Generation group): how to run generation, classification and their evaluation.
See [code/generation/README.md](code/generation/README.md).

## Packaging

This writes `code.zip` and `data.zip` to `dist/`:

```bash
python scripts/package_submission.py
```

## Notes for contributors

- Modules import each other from the `code/` root, for example `from retrieval.fusion import merge`.
  That is why modules with imports run as `python -m retrieval.query_hybrid` from `code/`.
- Take data locations from `paths.py` rather than writing relative paths.
- Do not add an `__init__.py` to `code/` itself: it would shadow the standard library's `code` module.
