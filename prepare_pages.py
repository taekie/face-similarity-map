"""Build the viewer and stage only the public web assets for GitHub Pages."""
import json
import shutil
from pathlib import Path

from build_viewer import build_viewer

ROOT = Path(__file__).resolve().parent
OUT = ROOT / 'output'
DOCS = ROOT / 'docs'

if __name__ == '__main__':
    build_viewer(json.loads((OUT / 'analysis.json').read_text()), OUT)
    DOCS.mkdir(exist_ok=True)
    for name in ['index.html', 'favicon.svg', 'favicon-32.png', 'favicon.ico', 'apple-touch-icon.png']:
        shutil.copy2(OUT / name, DOCS / name)
    shutil.copy2(ROOT / 'D3-LICENSE', DOCS / 'D3-LICENSE')
    (DOCS / '.nojekyll').touch()
    print(f'Prepared GitHub Pages assets in {DOCS}')
