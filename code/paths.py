"""Locations of everything under data/.

Paths are absolute, so scripts find the data no matter which directory they run from.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / 'data'

KNOWLEDGE_BASE_DIR = DATA_DIR / 'knowledge_base'
CHUNKS_PATH = KNOWLEDGE_BASE_DIR / 'processed' / 'chunks.jsonl'

SPARSE_INDEX_DIR = DATA_DIR / 'indexes' / 'sparse'
DENSE_INDEX_DIR = DATA_DIR / 'indexes' / 'dense'

EVALUATION_DATASET_DIR = DATA_DIR / 'evaluation_dataset'
ANNOTATIONS_PATH = EVALUATION_DATASET_DIR / 'steam_annotations_confirmed.json'
QUERIES_PATH = EVALUATION_DATASET_DIR / 'queries.jsonl'

RETRIEVAL_RESULTS_DIR = DATA_DIR / 'retrieval_results'
GENERATION_RESULTS_DIR = DATA_DIR / 'generation_results'
