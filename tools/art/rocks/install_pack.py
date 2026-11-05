"""Install the two verified native rocks, retaining every unrelated entry.

python3 tools/art/rocks/install_pack.py /tmp/terra-rocks/entries.json
"""
import base64
import gzip
import hashlib
import json
from pathlib import Path
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from assets_boot import configure_boot

layout=json.loads((Path(__file__).parent/'native-layout.json').read_text())
entries=json.loads(Path(sys.argv[1]).read_text())
if set(entries)!=set(layout):raise ValueError('Expected the pinned rock pair')
path=ROOT/'play/assets/pack/TERRA_PROPS.json.gz'
before=json.loads(gzip.decompress(path.read_bytes()));raw=zlib.decompress(base64.b64decode(before['bin'][2:]))
packed=bytearray();index={}
for name,old in before['idx'].items():
    if name in entries:
        entry=entries[name];data=base64.b64decode(entry['bin'],validate=True);expected=entry['layout']
        if len(data)!=expected['t']*24 or not 0<expected['t']<=layout[name]['layout']['t']:raise ValueError('Invalid budget: '+name)
        if any(expected[k]!=old[k] for k in ['s','w','h','d']):raise ValueError('Native layout changed: '+name)
        if entry['result']['boundaryEdges'] or entry['result']['nonManifoldEdges']:raise ValueError('Open rock: '+name)
    else:data=raw[old['o']:old['o']+old['t']*24]
    index[name]={**old,'o':len(packed),'t':len(data)//24};packed.extend(data)
value={'bin':'z:'+base64.b64encode(zlib.compress(packed,9)).decode(),'idx':index}
path.write_bytes(gzip.compress(json.dumps(value,separators=(',',':')).encode(),compresslevel=9,mtime=0))
manifest_path=ROOT/'play/assets/pack/manifest.json';manifest=json.loads(manifest_path.read_text())
group=next(g for g in manifest['groups'] if g['name']=='TERRA_PROPS')
group.update(bytes=path.stat().st_size,sha256=hashlib.sha256(path.read_bytes()).hexdigest())
manifest_path.write_text(json.dumps(manifest,separators=(',',':')),encoding='utf-8')
html=ROOT/'play/index.html'
html.write_text(configure_boot(html.read_text(encoding='utf-8'),manifest_path.read_bytes(),(ROOT/'play/assets/boot.js').read_bytes()),encoding='utf-8')
print('Installed',len(entries),'closed rocks;',path.stat().st_size,'compressed bytes')
