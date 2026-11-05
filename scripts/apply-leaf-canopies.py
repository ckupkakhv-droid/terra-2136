"""Install fine-leaf rendering and its shared native shadow material factory.

The original bundled sources are unavailable. Fail on changed anchors and keep
this tiny bridge reproducible; readable rendering lives in leaf-canopies.js.
"""
from pathlib import Path

p=Path(__file__).resolve().parents[1]/'play/index.html'
s=p.read_text();old='<script src="art/prop-materials.js"></script>';tag='<script src="art/leaf-canopies.js?v=2"></script>';new=old+'\n'+tag
legacy='<script src="art/leaf-canopies.js"></script>'
if legacy in s:
 if s.count(legacy)!=1:raise SystemExit('Leaf canopies: duplicate legacy script')
 s=s.replace(legacy,tag,1)
elif new not in s:
 if s.count(old)!=1:raise SystemExit('Leaf canopies: script anchor changed')
 s=s.replace(old,new,1)
old='TERRA_ART.hook({Ie,get ue(){return ue},'
new=('TERRA_ART.hook({Ie,makeLeafShadows:(wind,fell)=>[vr(new D0({depthPacking:bx}),'
     '{wind,fell}),vr(new Ny,{wind,fell})],get ue(){return ue},')
if new not in s:
 if s.count(old)!=1:raise SystemExit('Leaf canopies: native shadow bridge changed')
 s=s.replace(old,new,1)
# Falling trees construct a native mesh directly, bypassing ue.mesh. Attach
# exactly the same visible mask and shared shadows before the proxy is shown.
old='c.castShadow=!0,c.matrixAutoUpdate=!1,c.userData.noT=!0,this.scene.add(c);'
new='window.TERRA_ART?.applyLeafMesh?.(c),'+old
if new not in s:
 if s.count(old)!=1:raise SystemExit('Leaf canopies: native tree proxy changed')
 s=s.replace(old,new,1)
p.write_text(s)
print('Leaf canopy layer ready')
