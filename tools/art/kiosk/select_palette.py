"""Optional UV material sampling; requires NumPy and Pillow. Shipped pixels stay unchanged."""
import base64
import gzip
import io
import json
from pathlib import Path
import sys
import numpy as np
from PIL import Image

def atlas_palette(part):
    def read(key):
        data=base64.b64decode(part[key].split(',',1)[-1]);return Image.open(io.BytesIO(data)).convert('RGB')
    images=[read(k) for k in ['c','n','r','e']]
    # Analysis samples the maps at common UV coordinates; shipped pixels stay
    # untouched. The native maps deliberately have different resolutions.
    color,normal,rough,emission=(np.asarray(i.resize(images[0].size,Image.Resampling.NEAREST),dtype=np.float32) for i in images)
    h,w=color.shape[:2]
    targets={'paint':[72,91,97],'paint_edge':[118,132,100],'trim':[113,122,123],'roof':[139,141,133],
             'rust':[112,61,33],'dark':[30,36,37],'ink':[188,190,176],'glass':[42,60,66]}
    flat=np.sum((normal-np.array([128,128,255]))**2,axis=2)
    allowed=(flat<1400)&(emission.max(axis=2)<5)&(rough[:,:,1]>85)
    allowed[:10]=False;allowed[-10:]=False;allowed[:,:10]=False;allowed[:,-10:]=False
    result={}
    for name,target in targets.items():
        score=np.sum((color-np.array(target))**2,axis=2)+flat*2.5
        score[~allowed]=1e12
        candidates=np.argpartition(score.ravel(),300)[:300]
        best=None
        for at in candidates:
            y,x=divmod(int(at),w);c=color[y-3:y+4,x-3:x+4];n=normal[y-3:y+4,x-3:x+4]
            value=float(score[y,x]+np.mean(np.var(c,axis=(0,1)))*5+np.mean(np.var(n,axis=(0,1)))*3)
            if best is None or (value,y,x)<(best[0],best[1],best[2]):best=(value,y,x)
        _,y,x=best
        # Nonzero UV area is required by the native tangent-frame derivatives.
        result[name]={'uv':[(x-1)/w,1-(y+2)/h,(x+2)/w,1-(y-1)/h],
                      'pixel':[x,y],'color':[round(float(v),2) for v in color[y,x]],
                      'normal':[round(float(v),2) for v in normal[y,x]],'roughness':float(rough[y,x,1])}
    # Reuse the cabinet's coherent, worn sheet-metal UV region. It carries
    # real grain and roughness, unlike a single-color sample. Atlas pixels and
    # every other asset's UVs remain unchanged.
    for name,uv in [('paint',[.008,.134,.040,.164]),('roof',[.008,.160,.040,.168])]:
        x0,x1=int(uv[0]*w),int(uv[2]*w);y0,y1=int((1-uv[3])*h),int((1-uv[1])*h)
        result[name]={'uv':uv,'source':'existing utility-cabinet sheet',
                      'color':color[y0:y1,x0:x1].mean(axis=(0,1)).round(2).tolist(),
                      'normal':normal[y0:y1,x0:x1].mean(axis=(0,1)).round(2).tolist(),
                      'roughness':float(rough[y0:y1,x0:x1,1].mean())}
    return result


if __name__=='__main__':
    root=Path(__file__).resolve().parents[3]
    part=json.loads(gzip.decompress((root/'play/assets/pack/TERRA_KIT.json.gz').read_bytes()))['decor']
    Path(sys.argv[1]).write_text(json.dumps(atlas_palette(part),indent=2)+'\n')
