"""Keep the native hero visible after a failed own model; refine only its rig."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'play/index.html'
s=p.read_text(encoding='utf-8')
pairs=[
 ('<script src="art/actor-readiness.js?v=1"></script>','<script src="art/actor-readiness.js?v=1"></script><script src="art/actor-fallbacks.js?v=1"></script>'),
 ('let o=s[r].b.geometry(),a=new pi(o,i9,n);','let o=window.TERRA_ART?.fallbackActorGeometry?.(i,r,s[r].b)||s[r].b.geometry(),a=new pi(o,i9,n);'),
 ('this.heroRig.setVisible(!1),t&&this.glb.hero&&!this.heroInst','this.heroRig.setVisible(!(t&&this.glb.hero)),t&&this.glb.hero&&!this.heroInst'),
]
done=[b in s for a,b in pairs]
if any(done) and not all(done):raise SystemExit('Partial hero fallback patch')
for before,after in pairs:
 if after in s:
  if s.count(after)!=1:raise SystemExit('Ambiguous hero fallback anchor')
 else:
  if s.count(before)!=1:raise SystemExit('Native hero fallback anchor changed')
  s=s.replace(before,after,1)
p.write_text(s,encoding='utf-8')
print('Hero fallback suit connected; missing own model keeps the rig visible')
