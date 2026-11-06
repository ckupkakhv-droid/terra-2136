"""Splice only the kiosk LOD blocks; keep all unrelated KIT attributes exact."""
import base64
import copy
import gzip
import hashlib
import json
import math
from pathlib import Path
import struct
import sys
import zlib

ROOT=Path(__file__).resolve().parents[3]
sys.path.insert(0,str(ROOT/'scripts'))
from assets_boot import configure_boot


def align(n):return (n+3)//4*4


def encode(lod,bounds):
    """Weld identical complete quantized vertices, keeping every hard/UV seam."""
    p,n,uv,idx=lod['p'],lod['n'],lod['uv'],lod['i']
    assert len(p)==len(n) and len(p)//3*2==len(uv) and len(idx)%3==0
    if not all(math.isfinite(v) for values in (p,n,uv) for v in values):raise ValueError('Nonfinite kiosk attribute')
    if not all(type(i) is int and 0<=i<len(p)//3 for i in idx):raise ValueError('Invalid kiosk indices')
    vertices=[];seen={};remap=[]
    for v in range(len(p)//3):
        if any(not -1e-8<=(p[v*3+a]-bounds['mn'][a])/bounds['sc'][a]<=1+1e-8 for a in range(3)):raise ValueError('Kiosk exceeds native bounds')
        if abs(sum(x*x for x in n[v*3:v*3+3])-1)>1e-5:raise ValueError('Invalid kiosk normal')
        if any(not 0<=x<=1 for x in uv[v*2:v*2+2]):raise ValueError('Invalid kiosk UV')
        q=tuple(max(0,min(65535,round((p[v*3+a]-bounds['mn'][a])/bounds['sc'][a]*65535))) for a in range(3))
        norm=tuple(max(-127,min(127,round(n[v*3+a]*127))) for a in range(3))
        tex=tuple(max(0,min(65535,round(uv[v*2+a]*65535))) for a in range(2))
        key=q+norm+tex
        if key not in seen:seen[key]=len(vertices);vertices.append((q,norm,tex))
        remap.append(seen[key])
    indices=[remap[i] for i in idx];nv=len(vertices)
    if nv>65535:raise ValueError('Native KIT indices require Uint16')
    packet=bytearray();offsets=[]
    for kind in ['position','normal','uv','index']:
        while len(packet)%4:packet.append(0)
        offsets.append(len(packet))
        if kind=='position':
            for q,_,_ in vertices:packet.extend(struct.pack('<3H',*q))
        elif kind=='normal':
            for _,n,_ in vertices:packet.extend(struct.pack('<4b',*n,0))
        elif kind=='uv':
            for _,_,t in vertices:packet.extend(struct.pack('<2H',*t))
        else:packet.extend(struct.pack('<%sH'%len(indices),*indices))
    while len(packet)%4:packet.append(0)
    return bytes(packet),{'nv':nv,'ni':len(indices),'o':offsets,'mn':bounds['mn'],'sc':bounds['sc']}


def ranges(lod):return [(lod['o'][i],lod['o'][i]+lod['nv']*size) for i,size in enumerate([6,4,4])]+[(lod['o'][3],lod['o'][3]+lod['ni']*2)]


def install(source,entries):
    before=copy.deepcopy(source);part=source['decor'];old=part['idx']['kiosk'];layout=entries['layout']
    if {k:old[k] for k in ['w','h','d']}!=layout['dimensions']:raise ValueError('Native dimensions changed')
    for key,h in layout['textures'].items():
        if hashlib.sha256(part[key].encode()).hexdigest()!=h:raise ValueError('Atlas changed: '+key)
    raw=zlib.decompress(base64.b64decode(part['bin'],validate=True));splices=[]
    if len(old['lods'])!=3 or len(entries['lods'])!=3:raise ValueError('Expected three kiosk LODs')
    if [l['o'][0] for l in old['lods']]!=sorted(l['o'][0] for l in old['lods']):raise ValueError('Native LOD order changed')
    for asset in part['idx'].values():
        for lod in asset['lods']:
            if lod['ni']%3 or any(o%2 for o in lod['o']) or any(not 0<=a<=b<=len(raw) for a,b in ranges(lod)):raise ValueError('Invalid native KIT ranges')
    for level,lod in enumerate(old['lods']):
        start,end=lod['o'][0],align(lod['o'][3]+lod['ni']*2)
        if start%4 or not start<end<=len(raw):raise ValueError('Invalid kiosk splice range')
        packet,meta=encode(entries['lods'][level],layout['bounds']);splices.append((start,end,packet,meta))
    splices.sort(key=lambda a:a[0])
    if any(a[1]>b[0] for a,b in zip(splices,splices[1:])):raise ValueError('Overlapping kiosk LOD blocks')
    for name,asset in part['idx'].items():
        if name=='kiosk':continue
        for lod in asset['lods']:
            if any(a<end and b>start for a,b in ranges(lod) for start,end,_,_ in splices):raise ValueError('Shared kiosk data: '+name)
    data=bytearray();cursor=0;new_lods=[]
    for start,end,packet,meta in splices:
        data.extend(raw[cursor:start]);new_start=len(data);data.extend(packet);cursor=end
        new_lods.append({**meta,'o':[new_start+x for x in meta['o']]})
    data.extend(raw[cursor:])
    def relocate(offset):return offset+sum(len(packet)-(end-start) for start,end,packet,_ in splices if offset>=end)
    for name,asset in part['idx'].items():
        if name=='kiosk':asset['lods']=new_lods
        else:
            for lod in asset['lods']:lod['o']=[relocate(o) for o in lod['o']]
    part['bin']=base64.b64encode(zlib.compress(data,9)).decode()
    # Independent byte ranges ensure untouched normals, UVs and indices too.
    for name,old_asset in before['decor']['idx'].items():
        if name=='kiosk':continue
        for a,b in zip(old_asset['lods'],part['idx'][name]['lods']):
            if {k:v for k,v in a.items() if k!='o'}!={k:v for k,v in b.items() if k!='o'}:raise ValueError('Metadata changed: '+name)
            for (a0,a1),(b0,b1) in zip(ranges(a),ranges(b)):
                if raw[a0:a1]!=data[b0:b1]:raise ValueError('Unrelated attributes changed: '+name)
    for group in ['bld','posts']:
        if before[group]!=source[group]:raise ValueError('Unrelated KIT group changed')
    return source,{'oldBytes':len(raw),'newBytes':len(data),'triangles':[l['ni']//3 for l in new_lods],'vertices':[l['nv'] for l in new_lods]}


if __name__=='__main__':
    entries=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));path=ROOT/'play/assets/pack/TERRA_KIT.json.gz'
    value,report=install(json.loads(gzip.decompress(path.read_bytes())),entries)
    packed=gzip.compress(json.dumps(value,separators=(',',':')).encode(),compresslevel=9,mtime=0)
    manifest_path=ROOT/'play/assets/pack/manifest.json';manifest=json.loads(manifest_path.read_text(encoding='utf-8'))
    next(g for g in manifest['groups'] if g['name']=='TERRA_KIT').update(bytes=len(packed),sha256=hashlib.sha256(packed).hexdigest())
    manifest_bytes=json.dumps(manifest,separators=(',',':')).encode()
    html_path=ROOT/'play/index.html';html=configure_boot(html_path.read_text(encoding='utf-8'),manifest_bytes,(ROOT/'play/assets/boot.js').read_bytes())
    path.write_bytes(packed);manifest_path.write_bytes(manifest_bytes);html_path.write_text(html,encoding='utf-8')
    print(json.dumps({**report,'compressedBytes':len(packed),'sha256':hashlib.sha256(packed).hexdigest()},indent=2))
