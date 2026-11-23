"""Assemble an offline single-file HTML with local map and model results."""
import json
import shutil
from pathlib import Path
import numpy as np

ROOT = Path(__file__).resolve().parent


def build_viewer(data, out):
    data = dict(data)
    names = json.loads((ROOT / 'data/cluster-names.json').read_text())
    by_members = {tuple(sorted(group['members'])): group['name'] for group in names['groups']}
    data['cluster_info'] = {}
    for k, assignment in data['clusters'].items():
        info = []
        for cluster in range(int(k)):
            members = [r['label'] for r, group in zip(data['records'], assignment) if group == cluster]
            key = tuple(sorted(members))
            if key not in by_members:
                raise ValueError(f'Missing geographic name for k={k}: {members}')
            info.append({'name': by_members[key], 'members': members})
        if len({group['name'] for group in info}) != int(k):
            raise ValueError(f'Duplicate geographic names for k={k}')
        data['cluster_info'][k] = info
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
