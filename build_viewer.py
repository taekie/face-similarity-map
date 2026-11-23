"""Assemble an offline single-file HTML with local map and model results."""
import json
import shutil
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


def build_viewer(data, out):
    data = dict(data)
    data['similarities'] = (1 - np.load(out / 'cosine-distances.npy')).tolist()
    replacements = {
        '__D3_BUNDLE__': (ROOT / 'd3.v7.min.js').read_text(),
        '__WORLD_BUNDLE__': (ROOT / 'world-view.js').read_text(),
        '__WORLD_DATA__': (ROOT / 'data/world-compact.geojson').read_text(),
        '__GEOGRAPHY_DATA__': (ROOT / 'data/geography.json').read_text(),
        '__ANALYSIS_DATA__': json.dumps(data, ensure_ascii=False),
    }
    text = (ROOT / 'viewer.html').read_text()
    for token, content in replacements.items():
        text = text.replace(token, content)
    (out / 'index.html').write_text(text)
    for asset in (ROOT / 'assets').iterdir():
        shutil.copy2(asset, out / asset.name)


if __name__ == '__main__':
    out = ROOT / 'output'
    build_viewer(json.loads((out / 'analysis.json').read_text()), out)
