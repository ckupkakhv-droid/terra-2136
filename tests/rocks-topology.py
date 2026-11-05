"""Audit the shipped int16 rocks, preserving 100 unrelated native prop entries."""
import base64
from collections import Counter
import gzip
import hashlib
import json
from pathlib import Path
import struct
import subprocess
import zlib

ROOT=Path(__file__).resolve().parents[1];ART=ROOT/'tools/art/rocks'
BASE='b378442bb6d0077806f31fb893eb49e1660f6965'
FILE='play/assets/pack/TERRA_PROPS.json.gz'

def decode(data):
    v=json.loads(gzip.decompress(data));return v['idx'],zlib.decompress(base64.b64decode(v['bin'][2:]))

def audit(data,entry):
    edges=Counter();points=[]
    for i in range(entry['t']):
        values=struct.unpack_from('<9h3b3B',data,entry['o']+i*24)
        tri=[tuple(values[j:j+3]) for j in [0,3,6]];normal=values[9:12]
        u=[tri[1][k]-tri[0][k] for k in range(3)];v=[tri[2][k]-tri[0][k] for k in range(3)]
        cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]]
        assert sum(a*b for a,b in zip(cross,normal))>0,('Invalid normal',i)
        for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted((a,b)))]+=1
        points.extend(tri)
    return edges,points

before,old=decode(subprocess.check_output(['git','show',BASE+':'+FILE],cwd=ROOT))
after,new=decode((ROOT/FILE).read_bytes());targets=json.loads((ART/'native-layout.json').read_text())
lock=json.loads((ART/'source-lock.json').read_text());assert len(lock['files'])==len(targets)==2
for source in lock['files']:
    raw=(ART/'sources'/source['file']).read_bytes()
    assert len(raw)==source['bytes'] and hashlib.sha256(raw).hexdigest()==source['sha256']
    assert hashlib.sha1(('blob '+str(len(raw))+'\0').encode()+raw).hexdigest()==source['blob']
    assert json.loads(raw)['asset']['version']=='2.0'
assert before.keys()==after.keys();report=[]
for name,entry in after.items():
    original=before[name];assert all(entry[k]==original[k] for k in ['s','w','h','d']),name
    data=new[entry['o']:entry['o']+entry['t']*24]
    if name not in targets:
        assert entry['t']==original['t'] and data==old[original['o']:original['o']+original['t']*24],name
        continue
    assert targets[name]['layout']==original
    assert 0<entry['t']<=original['t'],name
    edges,points=audit(new,entry);old_edges,_=audit(old,original)
    assert all(n==2 for n in edges.values()),(name,Counter(edges.values()))
    assert any(n==1 for n in old_edges.values()),'Published baseline should reproduce the open rock'
    step=entry['s']
    for axis,extent in [(0,entry['w']),(2,entry['d'])]:
        lo=min(p[axis] for p in points)*step;hi=max(p[axis] for p in points)*step
        assert abs(lo+extent/2)<=step and abs(hi-extent/2)<=step,(name,axis,lo,hi)
    assert abs(min(p[1] for p in points)*step)<=step
    assert abs(max(p[1] for p in points)*step-entry['h'])<=step
    report.append({'name':name,'before':original['t'],'after':entry['t'],
                   'boundaryEdgesBefore':sum(n==1 for n in old_edges.values()),'boundaryEdgesAfter':0})
manifest=json.loads((ROOT/'play/assets/pack/manifest.json').read_text())
group=next(g for g in manifest['groups'] if g['name']=='TERRA_PROPS');raw=(ROOT/FILE).read_bytes()
assert group['bytes']==len(raw) and group['sha256']==hashlib.sha256(raw).hexdigest()
manifest_sha=hashlib.sha256((ROOT/'play/assets/pack/manifest.json').read_bytes()).hexdigest()
assert f'data-terra-manifest-sha256="{manifest_sha}"' in (ROOT/'play/index.html').read_text()
print(json.dumps(report));print('PASS two closed quantised rocks, normals/bounds/precision/budgets/source hashes; 100 unrelated entries byte exact, boot pin verified')
