"""Audit shipped kiosk quantisation, three LODs and unchanged native KIT data."""
import base64
from collections import Counter
import copy
import gzip
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import subprocess
import zlib

ROOT=Path(__file__).resolve().parents[1]
ART=ROOT/'tools/art/kiosk'
BASE='5f64bb12451c08830c63c1fee03a8b9e9858cd9f'
FILE='play/assets/pack/TERRA_KIT.json.gz'


def module(name):
    spec=importlib.util.spec_from_file_location(name,ART/(name+'.py'))
    value=importlib.util.module_from_spec(spec);spec.loader.exec_module(value);return value


def raw(part):return zlib.decompress(base64.b64decode(part['bin'],validate=True))


def vectors(data,lod):
    p=[tuple(lod['mn'][a]+v*lod['sc'][a]/65535 for a,v in enumerate(q)) for q in struct.iter_unpack('<3H',data[lod['o'][0]:lod['o'][0]+lod['nv']*6])]
    n=[tuple(v/127 for v in q[:3]) for q in struct.iter_unpack('<4b',data[lod['o'][1]:lod['o'][1]+lod['nv']*4])]
    uv=list(struct.iter_unpack('<2H',data[lod['o'][2]:lod['o'][2]+lod['nv']*4]))
    indices=struct.unpack_from('<%sH'%lod['ni'],data,lod['o'][3])
    return p,n,uv,indices


def cross(a,b):return (a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0])


gen=module('generate');installer=module('install_pack')
layout=json.loads((ART/'native-layout.json').read_text())
palette=json.loads((ART/'palette.json').read_text())
generated={'layout':layout,'lods':[gen.build(i,palette,layout['bounds']) for i in range(3)]}
before=json.loads(gzip.decompress(subprocess.check_output(['git','show',BASE+':'+FILE],cwd=ROOT)))
after=json.loads(gzip.decompress((ROOT/FILE).read_bytes()))
expected,_=installer.install(copy.deepcopy(before),generated)
assert expected==after,'Shipped pack differs from authoring source'
repeat,_=installer.install(copy.deepcopy(after),generated)
assert repeat==after,'Pack installer is not idempotent'
for group in before:
    assert before[group].keys()==after[group].keys()
    assert before[group]['idx'].keys()==after[group]['idx'].keys()
    for key in before[group]:
        if key not in ('idx','bin'):assert before[group][key]==after[group][key],(group,key)
    old_data,new_data=raw(before[group]),raw(after[group])
    for name,old in before[group]['idx'].items():
        new=after[group]['idx'][name]
        if group=='decor' and name=='kiosk':continue
        assert {k:v for k,v in old.items() if k!='lods'}=={k:v for k,v in new.items() if k!='lods'}
        assert len(old['lods'])==len(new['lods'])
        for a,b in zip(old['lods'],new['lods']):
            assert {k:v for k,v in a.items() if k!='o'}=={k:v for k,v in b.items() if k!='o'}
            for (a0,a1),(b0,b1) in zip(installer.ranges(a),installer.ranges(b)):
                assert old_data[a0:a1]==new_data[b0:b1],(group,name)

old=before['decor']['idx']['kiosk'];new=after['decor']['idx']['kiosk']
assert {k:new[k] for k in ('w','h','d')}==layout['dimensions']=={k:old[k] for k in ('w','h','d')}
report=[]
for level,lod in enumerate(new['lods']):
    p,n,uv,indices=vectors(raw(after['decor']),lod)
    assert lod['ni']<old['lods'][level]['ni'],'LOD triangle budget regressed'
    assert all(math.isfinite(v) for values in (p,n,uv) for q in values for v in q)
    assert all(abs(sum(v*v for v in q)-1)<.025 for q in n),'Bad packed normal'
    assert min(indices)>=0 and max(indices)<len(p)
    min_dot=1
    for start in range(0,len(indices),3):
        a,b,c=[p[i] for i in indices[start:start+3]]
        normal=cross([b[i]-a[i] for i in range(3)],[c[i]-a[i] for i in range(3)])
        length=math.sqrt(sum(v*v for v in normal));assert length>1e-10,('Degenerate packed triangle',level,start)
        avg=[sum(n[k][a] for k in indices[start:start+3])/3 for a in range(3)]
        dot=sum(normal[a]*avg[a] for a in range(3))/length
        min_dot=min(min_dot,dot);assert dot>.97,('Backwards normal',level,start,dot)
        ta,tb,tc=[uv[i] for i in indices[start:start+3]]
        assert (tb[0]-ta[0])*(tc[1]-ta[1])-(tc[0]-ta[0])*(tb[1]-ta[1])!=0,('Collapsed normal-map UV',level,start)
    for axis in range(3):
        assert abs(min(q[axis] for q in p)-layout['bounds']['mn'][axis])<1e-7
        assert abs(max(q[axis] for q in p)-layout['bounds']['mn'][axis]-layout['bounds']['sc'][axis])<1e-7
    # Audit each solid separately: intentionally thin sign ink/window shards
    # and far sheet interiors have explicit closed=False authoring metadata.
    source=generated['lods'][level];closed=0
    for part in source['parts']:
        if not part['closed']:continue
        edges=Counter()
        for start in range(part['start'],part['end'],3):
            tri=[p[i] for i in indices[start:start+3]]
            for a,b in zip(tri,tri[1:]+tri[:1]):edges[tuple(sorted((a,b)))]+=1
        assert all(count==2 for count in edges.values()),('Open structural part',level,part['name'],Counter(edges.values()))
        closed+=1
    report.append({'lod':level,'vertices':lod['nv'],'triangles':lod['ni']//3,'beforeTriangles':old['lods'][level]['ni']//3,'closedSolids':closed,'minimumNormalDot':min_dot})
manifest=(ROOT/'play/assets/pack/manifest.json').read_bytes()
group=next(g for g in json.loads(manifest)['groups'] if g['name']=='TERRA_KIT')
packed=(ROOT/FILE).read_bytes()
assert group['bytes']==len(packed) and group['sha256']==hashlib.sha256(packed).hexdigest()
assert 'data-terra-manifest-sha256="'+hashlib.sha256(manifest).hexdigest()+'"' in (ROOT/'play/index.html').read_text()
print(json.dumps(report,indent=2))
print('PASS packed winding/nondegenerate geometry/normal-map UVs/closed structural parts/bounds/LOD budgets; all other KIT entries and atlases byte exact; deterministic and idempotent installer; boot pins')
