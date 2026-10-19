import json
from pathlib import Path

import bm25s
import Stemmer

SOURCE_PATH = Path('chunks.jsonl')
INDEX_DIR = Path('sparse_index')
K1 = 1.5
B = 0.75
METHOD = 'lucene'
STOPWORDS = 'en'
STEMMER = 'english'


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

    corpus_tokens = bm25s.tokenize(
        [chunk['text'] for chunk in chunks],
        lower=True,
        stopwords=STOPWORDS,
        stemmer=Stemmer.Stemmer(STEMMER),
    )
    model = bm25s.BM25(k1=K1, b=B, method=METHOD)
    model.index(corpus_tokens)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    model.save(str(INDEX_DIR / 'bm25'))
    with (INDEX_DIR / 'chunks.json').open('w', encoding='utf-8') as file:
        json.dump(chunks, file, ensure_ascii=False)
    with (INDEX_DIR / 'config.json').open('w', encoding='utf-8') as file:
        json.dump({'k1': K1, 'b': B, 'method': METHOD, 'stopwords': STOPWORDS,
                   'stemmer': STEMMER, 'lower': True, 'num_docs': len(chunks)}, file, indent=2)
    print(f'Indexed {len(chunks)} chunks in {INDEX_DIR}')


if __name__ == '__main__':
    main()
