# Downstream task and generation

Pending (Generation group).

## Connecting to the UI

`code/app.py` has a placeholder titled "Sentiment analysis / generated answer". Provide one function
it can call there, for example:

```python
from generation.answer import answer

result = answer(query, hits)
```

`hits` is the ranked list the app already has. Each hit is a dict with:

| Key | Content |
|---|---|
| `chunk_id` | Chunk ID, for citing evidence |
| `text` | Chunk text |
| `metadata` | Includes `game_name`, `document_id`, `source` and `title` |

Hits also carry rank and score fields that depend on the retrieval mode, such as `retrieved_by`,
`sparse_rank` and `rrf_score`; see `retrieval/fusion.py` and `retrieval/reranker.py`.

## Using retrieval directly

Run from `code/` so the imports resolve, for example `python -m generation.evaluate`:

```python
from retrieval.hybrid_retriever import HybridRetriever
from retrieval.reranker import Reranker
```

## Conventions

- Write results to `data/generation_results/` using `GENERATION_RESULTS_DIR` from `paths.py`: generated
  answers or classification results, precision/recall/F1, faithfulness, answer relevance and context
  relevance, and the Q5 ablation study.
- Add your dependencies to `code/requirements.txt` with pinned versions.
- Read API keys from environment variables. `.env` is ignored by git and left out of the packages.
- Describe how to run your scripts here, and replace the TODO in the root `README.md`.
