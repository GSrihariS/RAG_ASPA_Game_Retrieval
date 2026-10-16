import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

SOURCE_PATH = Path('chunks.jsonl')
INDEX_DIR = Path('dense_index')
MODEL_NAME = 'BAAI/bge-small-en-v1.5'
BATCH_SIZE = 64


def main():
    chunks = []
    with SOURCE_PATH.open('r', encoding='utf-8') as file:
        for line in file:
            if line.strip():
                chunk = json.loads(line)
                if not isinstance(chunk.get('id'), str) or not chunk['id']:
                    raise ValueError('Every chunk must have a nonempty string id')
                if isinstance(chunk.get('text'), str) and chunk['text'].strip():
                    chunks.append(chunk)

    if not chunks:
        raise ValueError('No valid chunks to index')
    if len({chunk['id'] for chunk in chunks}) != len(chunks):
        raise ValueError('Duplicate chunk IDs found')

    model = SentenceTransformer(MODEL_NAME)
    embeddings = model.encode(
        [chunk['text'] for chunk in chunks],
        batch_size=BATCH_SIZE,
        convert_to_numpy=True,
        normalize_embeddings=True,
        show_progress_bar=True,
    )
    embeddings = np.asarray(embeddings, dtype=np.float32)
    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_DIR / 'faiss.index'))
    with (INDEX_DIR / 'chunks.json').open('w', encoding='utf-8') as file:
        json.dump(chunks, file, ensure_ascii=False)
    with (INDEX_DIR / 'config.json').open('w', encoding='utf-8') as file:
        json.dump({'model_name': MODEL_NAME, 'dimension': int(embeddings.shape[1]),
                   'normalized': True, 'metric': 'inner_product'}, file, indent=2)
    print(f'Indexed {index.ntotal} chunks in {INDEX_DIR}')


if __name__ == '__main__':
    main()
