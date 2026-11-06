# Knowledge-base construction

Pending (Data group). The data itself is already in `data/knowledge_base/`, but the scripts that
produced it are not in the repository yet.

## What belongs here

- The scripts that collect the Steam reviews, and clean, filter and chunk them.
- The script that computes inter-annotator agreement. The assignment requires at least 80% over at
  least 1,000 records.

## What belongs in `data/`

- The labels of **each annotator**, in `data/evaluation_dataset/`. The current
  `steam_annotations_confirmed.json` holds one merged label per chunk, so agreement cannot be computed
  from it.

## Conventions

- Run from `code/` and take locations from `paths.py`, for example
  `from paths import KNOWLEDGE_BASE_DIR, CHUNKS_PATH`.
- Keep the chunk fields (`id`, `document_id`, `source`, `title`, `text`, `metadata`): the retrieval code
  and the indexes depend on them.
- If you regenerate `chunks.jsonl`, rebuild the indexes and tell the retrieval group, because the
  evaluation results depend on them.
- Add your dependencies to `code/requirements.txt` with pinned versions.
- Describe how to run your scripts here, and replace the TODO in the root `README.md`.
