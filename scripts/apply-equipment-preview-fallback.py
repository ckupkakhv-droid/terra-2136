"""Use an independently owned native suit while equipment awaits its hero GLB."""
from pathlib import Path
p=Path(__file__).resolve().parents[1]/'play/index.html'
s=p.read_text(encoding='utf-8')
pairs=[
 ('art/actor-fallbacks.js?v=1','art/actor-fallbacks.js?v=2'),
 ('<script defer src="ui/backpack.js"></script>','<script defer src="ui/backpack.js?v=2"></script>'),
 ('this.player=this.game.p,this.canvas=document.createElement("canvas")','this.player=this.game.p,this.modelUnwatch=window.TERRA_ART?.watchEquipmentModel?.(this.game,this),this.canvas=document.createElement("canvas")'),
 ('let t=this.game.glb?.hero;if(!t){this.timer','let t=this.game.glb?.hero||window.TERRA_ART?.equipmentFallbackSource?.(this.game,Pi);if(!t){this.timer'),
 ('},400));return}try{if(!this.inst){this.source=t', '},400));return}try{if(this.inst&&this.source!==t){this.source?.release(this.inst),this.inst=null}if(!this.inst){this.source=t'),
 ('this.frame=this.timer=0,this.observer?.disconnect()', 'this.frame=this.timer=0,this.modelUnwatch?.(),this.modelUnwatch=null,this.observer?.disconnect()'),
 ('this.glb[r]=new Ke(c,s[r]||1.8)}catch(o){console.warn("GLB",r,o)}', 'this.glb[r]=new Ke(c,s[r]||1.8),window.TERRA_ART?.equipmentModelReady?.(this,r)}catch(o){console.warn("GLB",r,o)}'),
]
done=[b in s for a,b in pairs]
if any(done) and not all(done):raise SystemExit('Partial equipment preview fallback patch')
for before,after in pairs:
 if after in s:
  if s.count(after)!=1:raise SystemExit('Ambiguous equipment preview fallback anchor')
 else:
  if s.count(before)!=1:raise SystemExit('Native equipment preview fallback anchor changed')
  s=s.replace(before,after,1)
p.write_text(s,encoding='utf-8')
print('Equipment suit preview connected; own ready model signals one replacement')
