"""Install verified tree entries in the existing native prop archive.

python3 tools/art/nature/install_pack.py /tmp/terra-nature/entries.json
All unrelated packed triangle bytes and metadata are retained.
"""
import base64
import gzip
import hashlib
import json
import sys
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
sys.path.insert(0, str(ROOT / 'scripts'))
from assets_boot import configure_boot

entries = json.loads(Path(sys.argv[1]).read_text())
layout = json.loads((Path(__file__).parent / 'native-layout.json').read_text())
if set(entries) != set(layout):
    raise ValueError('Expected the complete pinned tree set')
path = ROOT / 'play/assets/pack/TERRA_PROPS.json.gz'
previous = json.loads(gzip.decompress(path.read_bytes()))
raw = zlib.decompress(base64.b64decode(previous['bin'][2:]))
packed, index = bytearray(), {}
for name, old in previous['idx'].items():
    if name in entries:
        entry = entries[name]
        data = base64.b64decode(entry['bin'], validate=True)
        expected = entry['layout']
        if len(data) != expected['t'] * 24 or expected['t'] > layout[name]['layout']['t']:
            raise ValueError('Invalid triangle budget: ' + name)
        if any(old[k] != expected[k] for k in ['s', 'w', 'h', 'd']):
            raise ValueError('Native dimensions or precision changed: ' + name)
    else:
        data = raw[old['o']:old['o'] + old['t'] * 24]
    index[name] = {**old, 'o': len(packed), 't': len(data) // 24}
    packed.extend(data)
if not set(entries) <= set(index):
    raise ValueError('Native prop names changed')
value = {'bin': 'z:' + base64.b64encode(zlib.compress(packed, 9)).decode(), 'idx': index}
path.write_bytes(gzip.compress(json.dumps(value, separators=(',', ':')).encode(),
                               compresslevel=9, mtime=0))
manifest_path = ROOT / 'play/assets/pack/manifest.json'
manifest = json.loads(manifest_path.read_text())
group = next(g for g in manifest['groups'] if g['name'] == 'TERRA_PROPS')
group.update(bytes=path.stat().st_size, sha256=hashlib.sha256(path.read_bytes()).hexdigest())
manifest_path.write_text(json.dumps(manifest, separators=(',', ':')))
html = ROOT / 'play/index.html'
html.write_text(configure_boot(html.read_text(), manifest_path.read_bytes(),
                               (ROOT / 'play/assets/boot.js').read_bytes()))
print('Installed', len(entries), 'trees;', path.stat().st_size, 'compressed bytes')
