"""Check shipped quantised trees, including topology after quantisation.

python3 tests/nature-topology.py [baseline git ref, default published 0.4.22]
"""
import base64
from collections import Counter
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import zlib

ROOT = Path(__file__).resolve().parents[1]
NATURE = ROOT / 'tools/art/nature'
BASE = sys.argv[1] if len(sys.argv) > 1 else '0d0cd953d5f37819e25d81beff66b590197bd2f5'
FILE = 'play/assets/pack/TERRA_PROPS.json.gz'


def decode(data):
    value = json.loads(gzip.decompress(data))
    return value['idx'], zlib.decompress(base64.b64decode(value['bin'][2:]))


before, old = decode(subprocess.check_output(['git', 'show', BASE + ':' + FILE], cwd=ROOT))
after, new = decode((ROOT / FILE).read_bytes())
targets = json.loads((NATURE / 'native-layout.json').read_text())
lock = json.loads((NATURE / 'source-lock.json').read_text())
# Separately replaced and audited against published 0.4.25 by rocks-topology.py.
rock_targets = {'qn_rock_medium_1', 'qn_rock_medium_3'}
assert len(targets) == 18 and len(lock['files']) == 15
assert all(entry['source'] in {source['file'] for source in lock['files']} for entry in targets.values())
for source in lock['files']:
    raw = (NATURE / 'sources' / source['file']).read_bytes()
    assert len(raw) == source['bytes'] and hashlib.sha256(raw).hexdigest() == source['sha256']
    assert hashlib.sha1(('blob ' + str(len(raw)) + '\0').encode() + raw).hexdigest() == source['blob']
    assert json.loads(raw)['asset']['version'] == '2.0'
assert before.keys() == after.keys()
report = []
for name, entry in after.items():
    original = before[name]
    assert all(entry[k] == original[k] for k in ['s', 'w', 'h', 'd']), name
    data = new[entry['o']:entry['o'] + entry['t'] * 24]
    if name not in targets:
        if name in rock_targets:
            continue
        assert data == old[original['o']:original['o'] + original['t'] * 24], name
        continue
    assert 0 < entry['t'] <= targets[name]['layout']['t'] == original['t'], name
    edges, bark = Counter(), []
    positions = []
    for i in range(entry['t']):
        xyz = struct.unpack_from('<9h', data, i * 24)
        normal = struct.unpack_from('<3b', data, i * 24 + 18)
        rgb = data[i * 24 + 21:i * 24 + 24]
        points = [tuple(xyz[k:k + 3]) for k in [0, 3, 6]]
        positions.extend(points)
        u = [points[1][k] - points[0][k] for k in range(3)]
        v = [points[2][k] - points[0][k] for k in range(3)]
        cross = [u[1]*v[2] - u[2]*v[1], u[2]*v[0] - u[0]*v[2], u[0]*v[1] - u[1]*v[0]]
        assert sum(x*y for x, y in zip(cross, normal)) > 0, (name, i, 'degenerate or inverted')
        if rgb[1] > rgb[0] * 1.06 and rgb[1] > rgb[2] * 1.1:
            continue
        bark.extend(points)
        for a, b in zip(points, points[1:] + points[:1]):
            edges[tuple(sorted((a, b)))] += 1
    assert bark and all(count == 2 for count in edges.values()), (name, Counter(edges.values()))
    step = entry['s']
    for axis, extent in [(0, entry['w']), (2, entry['d'])]:
        assert max(abs(p[axis]) * step for p in positions) <= extent * .5 + step, (name, axis)
    assert abs(min(p[1] for p in positions) * step) <= step, name
    assert max(p[1] for p in positions) * step <= entry['h'] + step, name
    assert max(math.hypot(p[0], p[2]) * step for p in positions) <= max(entry['w'], entry['d']) * .5, (name, 'native felling radius')
    low, high = min(p[1] for p in bark), max(p[1] for p in bark)
    base = set(p for p in bark if p[1] <= low + (high - low) * .01)
    pivot = [sum(p[k] for p in base) / len(base) * step for k in [0, 2]]
    assert max(map(abs, pivot)) < .01, (name, 'root pivot', pivot)
    report.append({'name': name, 'before': original['t'], 'after': entry['t'],
                   'openBarkEdges': 0, 'rootOffset': pivot})
print(json.dumps(report, ensure_ascii=False))
print('PASS 18 closed quantised trunks, normals, pivots, dimensions, budgets, source hashes; '
      '82 other prop entries byte-for-byte unchanged; two rocks audited separately')
