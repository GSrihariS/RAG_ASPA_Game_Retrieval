"""Build the two submission packages in dist/: code.zip (README + code/) and data.zip (data/).

Unpacking both into one folder restores the layout the code expects.

Run from code/:  python scripts/package_submission.py
"""
import sys
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from paths import DATA_DIR, ROOT  # noqa: E402

EXCLUDED_DIRS = {'__pycache__', '.ipynb_checkpoints'}
EXCLUDED_FILES = {'.env', 'checkpoint.jsonl'}


def add_tree(archive, top):
    for path in sorted(top.rglob('*')):
        if path.is_file() and path.name not in EXCLUDED_FILES and not EXCLUDED_DIRS & set(path.parts):
            archive.write(path, path.relative_to(ROOT))


def main():
    dist = ROOT / 'dist'
    dist.mkdir(exist_ok=True)

    code_zip, data_zip = dist / 'code.zip', dist / 'data.zip'
    with zipfile.ZipFile(code_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
        archive.write(ROOT / 'README.md', 'README.md')
        add_tree(archive, ROOT / 'code')
    with zipfile.ZipFile(data_zip, 'w', zipfile.ZIP_DEFLATED) as archive:
        add_tree(archive, DATA_DIR)

    for path in (code_zip, data_zip):
        print(f'{path}: {path.stat().st_size / 1e6:.2f} MB')


if __name__ == '__main__':
    main()
