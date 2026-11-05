"""Connect readable shared AO to the native paint and chunk lifecycle.

The module receives pre-water/cliff collider eligibility and native grid paint.
Existing save callbacks and rendering/physics geometry remain intact.
"""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'play/index.html'
s=p.read_text(encoding='utf-8')
pairs=[
 ('<script src="art/terrain-blend.js"></script>','<script src="art/terrain-blend.js"></script><script src="art/terrain-contact.js?v=1"></script>'),
 ('let y=(v,A)=>{let w=A*i+v;return[n+r[v],e.hv[w],s+r[A],w]};','window.TERRA_ART?.captureTerrainContact?.(this,e,f,a);let y=(v,A)=>{let w=A*i+v;return[n+r[v],e.hv[w],s+r[A],w]};'),
 ('return this.chunks.set(this.key(t,i),r),this.refreshLists(),r.lander&&','return this.chunks.set(this.key(t,i),r),window.TERRA_ART?.attachTerrainContact?.(this,r,s,n),this.refreshLists(),r.lander&&'),
 ('discardChunk(t){t.fencePart','discardChunk(t){window.TERRA_ART?.detachTerrainContact?.(this,t);t.fencePart'),
]
new=[b in s for a,b in pairs]
if any(new) and not all(new):raise SystemExit('Partial shared terrain contact patch')
for a,b in pairs:
 if b in s:
  if s.count(b)!=1:raise SystemExit('Ambiguous shared contact anchor')
 else:
  if s.count(a)!=1:raise SystemExit('Native shared contact anchor changed: '+a[:65])
  s=s.replace(a,b,1)
p.write_text(s,encoding='utf-8')
print('Shared terrain contact connected to paint / build / discard')
