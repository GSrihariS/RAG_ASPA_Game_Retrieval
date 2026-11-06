"""Export the confirmed annotations to data/evaluation_dataset/eval.xls, one row per chunk and aspect.

Run from code/:  python eval/export_eval_xls.py
"""
import argparse
import json
import sys
from pathlib import Path

import xlwt

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dataset_stats import ASPECTS  # noqa: E402
from paths import ANNOTATIONS_PATH, EVALUATION_DATASET_DIR  # noqa: E402

COLUMNS = ('sample_id', 'chunk_id', 'game_name', 'text', 'aspect', 'subjectivity', 'sentiment', 'evidence')


def main():
    parser = argparse.ArgumentParser(description='Export the annotation set to eval.xls')
    parser.add_argument('--annotations', type=Path, default=ANNOTATIONS_PATH)
    parser.add_argument('--out', type=Path, default=EVALUATION_DATASET_DIR / 'eval.xls')
    args = parser.parse_args()

    with args.annotations.open(encoding='utf-8') as f:
        records = [r for r in json.load(f)['records'] if r['status'] == 'Confirmed']

    book = xlwt.Workbook(encoding='utf-8')
    sheet = book.add_sheet('eval')
    for col, name in enumerate(COLUMNS):
        sheet.write(0, col, name)
    row = 0
    for record in records:
        for aspect in ASPECTS:
            label = record['human_annotation'][aspect]
            row += 1
            values = (record['sample_id'], record['chunk_id'], record['game_name'], record['text'],
                      aspect, label['subjectivity'], label['sentiment'], label['evidence'])
            for col, value in enumerate(values):
                sheet.write(row, col, value)
    args.out.parent.mkdir(parents=True, exist_ok=True)
    book.save(str(args.out))
    print(f'Wrote {row} rows from {len(records)} chunks to {args.out}')


if __name__ == '__main__':
    main()
