"""Ground only rendered live-hero parts; leave native pose/weapon matrices local."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'play/index.html'
s=p.read_text(encoding='utf-8')
pairs=[
 ('<script src="art/actor-fallbacks.js?v=2"></script>','<script src="art/actor-fallbacks.js?v=2"></script><script src="art/actor-grounding.js?v=1"></script>'),
 ('for(let n of this.parts)n.im.count=i,n.im.instanceMatrix.needsUpdate=!0,n.im.instanceColor&&(n.im.instanceColor.needsUpdate=!0)}setVisible(t)', 'for(let n of this.parts)n.im.count=i,n.im.instanceMatrix.needsUpdate=!0,n.im.instanceColor&&(n.im.instanceColor.needsUpdate=!0);window.TERRA_ART?.groundHeroRig?.(this,t)}setVisible(t)'),
]
done=[b in s for a,b in pairs]
if any(done) and not all(done):raise SystemExit('Partial hero terrain grounding patch')
for before,after in pairs:
 if after in s:
  if s.count(after)!=1:raise SystemExit('Ambiguous hero terrain grounding anchor')
 else:
  if s.count(before)!=1:raise SystemExit('Native hero terrain grounding anchor changed')
  s=s.replace(before,after,1)
p.write_text(s,encoding='utf-8')
print('Live hero instance matrices grounded; native root and hand matrices retained')
