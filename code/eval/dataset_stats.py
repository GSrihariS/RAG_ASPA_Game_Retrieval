"""Summarize the confirmed annotation set and write the tables to data/evaluation_dataset/dataset_stats.md.

Run from code/:  python eval/dataset_stats.py
"""
import argparse
import json
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import ANNOTATIONS_PATH, EVALUATION_DATASET_DIR  # noqa: E402

ASPECTS = ('story', 'graphics_visuals', 'gameplay', 'controls',
           'performance', 'audio', 'bugs_stability', 'online_multiplayer')
SENTIMENTS = ('Positive', 'Negative', 'Mixed', 'Neutral', 'Unclear', 'Not mentioned')


def table(header, rows):
    lines = ['| ' + ' | '.join(header) + ' |', '|' + '---|' * len(header)]
    lines += ['| ' + ' | '.join(str(x) for x in row) + ' |' for row in rows]
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(description='Statistics of the confirmed annotation set')
    parser.add_argument('--annotations', type=Path,
                        default=ANNOTATIONS_PATH)
    parser.add_argument('--out', type=Path, default=EVALUATION_DATASET_DIR / 'dataset_stats.md')
    args = parser.parse_args()

    with args.annotations.open(encoding='utf-8') as f:
        data = json.load(f)
    records = [r for r in data['records'] if r['status'] == 'Confirmed']
    games = sorted({r['game_name'] for r in records})
    labels = [(r, a, r['human_annotation'][a]) for r in records for a in ASPECTS]

    sentiment = Counter((a, l['sentiment']) for _, a, l in labels)
    subjectivity = Counter((a, l['subjectivity']) for _, a, l in labels if l['sentiment'] != 'Not mentioned')
    per_chunk = Counter(sum(r['human_annotation'][a]['sentiment'] != 'Not mentioned' for a in ASPECTS)
                        for r in records)
    reviews = {r['document_id'] for r in records}
    lengths = sorted(len(r['text'].split()) for r in records)

    out = [
        '# Annotation set statistics',
        '',
        f"Source: `{args.annotations.name}` (dataset `{data['dataset_id']}`)",
        '',
        f'- Confirmed chunks: {len(records)} from {len(reviews)} reviews of {len(games)} games',
        f'- Chunk length (words): min {lengths[0]}, median {lengths[len(lengths) // 2]}, max {lengths[-1]}',
        f'- Aspects: {len(ASPECTS)} ({", ".join(ASPECTS)})',
        '',
        '## Chunks per game',
        '',
        table(['game', 'chunks'], [(g, sum(r['game_name'] == g for r in records)) for g in games]),
        '',
        '## Aspect x sentiment',
        '',
        table(['aspect', *SENTIMENTS, 'mentioned'],
              [(a, *(sentiment[a, s] for s in SENTIMENTS), len(records) - sentiment[a, 'Not mentioned'])
               for a in ASPECTS]),
        '',
        '## Subjectivity of aspect mentions',
        '',
        table(['aspect', 'Opinionated', 'Objective', '(blank)'],
              [(a, subjectivity[a, 'Opinionated'], subjectivity[a, 'Objective'], subjectivity[a, ''])
               for a in ASPECTS]),
        '',
        '## Aspects mentioned per chunk',
        '',
        table(['aspects', 'chunks'], sorted(per_chunk.items())),
        '',
        '## Positive / negative mentions per game and aspect',
        '',
        table(['game', *ASPECTS],
              [(g, *(f"{sum(r['game_name'] == g and l['sentiment'] == 'Positive' for r, b, l in labels if b == a)}"
                     f" / {sum(r['game_name'] == g and l['sentiment'] == 'Negative' for r, b, l in labels if b == a)}"
                     for a in ASPECTS)) for g in games]),
        '',
    ]
    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text('\n'.join(out), encoding='utf-8')
    print('\n'.join(out))


if __name__ == '__main__':
    main()
