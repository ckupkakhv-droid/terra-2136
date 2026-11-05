"""Feather local pad/pond normals into the common world stencil at cell edges.

Only the shading gradient and its existing slope paint use this transition.
Native heights, water geometry, placement and collision remain untouched.
"""
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'play/index.html'
html=path.read_text(encoding='utf-8')
head='terrain(){let e=this.T,t=x1,i=t+2,n=this.ox,s=this.oz,r=e.xs,o=this.s;'
copy=head+'let groundBase=window.TERRA_ART?.terrainEdgeNormalsEnabled===false||!(this.pads.length||this.ponds?.length)?null:e.hv.slice();'
normal='N=A===1?-(e.hv[v*i+A+2]-e.hv[v*i+M])/(r[A+2]-r[M]):C,W=v===1?-(e.hv[(v+2)*i+A]-e.hv[T*i+A])/(r[v+2]-r[T]):R,Q=Math.hypot(N,1,W);'
feather='N=A===1?-(e.hv[v*i+A+2]-e.hv[v*i+M])/(r[A+2]-r[M]):C,W=v===1?-(e.hv[(v+2)*i+A]-e.hv[T*i+A])/(r[v+2]-r[T]):R;if(groundBase){let groundBlend=$s(0,4,Math.min(k-n,n+Qt-k,E-s,s+Qt-E));if(groundBlend<1){let groundRight=A===1?A+2:S,groundDown=v===1?v+2:I,groundX=-(groundBase[v*i+groundRight]-groundBase[v*i+M])/(r[groundRight]-r[M]),groundZ=-(groundBase[groundDown*i+A]-groundBase[T*i+A])/(r[groundDown]-r[T]);N=groundX+(N-groundX)*groundBlend,W=groundZ+(W-groundZ)*groundBlend}}let Q=Math.hypot(N,1,W);'
if html.count(head)!=1:raise SystemExit('Native terrain head changed or duplicated')
# The head is a prefix of the copied version; count the complete variants.
if copy in html or feather in html:
    if html.count(copy)!=1 or html.count(feather)!=1 or normal in html:raise SystemExit('Partial or ambiguous terrain-normal patch')
else:
    if html.count(head)!=1 or html.count(normal)!=1:raise SystemExit('Native terrain-normal anchors changed')
    html=html.replace(head,copy,1).replace(normal,feather,1)
path.write_text(html,encoding='utf-8')
print('Terrain edge normals use a common stencil and a 4 m transition')
