"""Add the optional chunk-local height profile to the existing esbuild bundle.

The readable profile/geometry implementation lives in play/ui/metro-descent.js.
This small adapter is kept reproducible because the original bundle sources
are not present. It deliberately fails if a future build changes either anchor.
"""
from pathlib import Path

target = Path(__file__).resolve().parents[1] / 'play/index.html'
source = target.read_text()
anchor = 'function Ot(e,t){let i=Math.floor(e/Qt),n=Math.floor(t/Qt),s=xf.get(i+","+n);'
hook = 'if(typeof s?.metroHeight==="function"){let r=s.metroHeight(e,t);if(Number.isFinite(r))return r}'
bridge = 'window.TERRA_SEWER_BRIDGE={Chunk:Ie,'
api = ('metroHeightVersion:1,metroProfileAt:(e,t)=>xf.get(Math.floor(e/Qt)+","+'
       'Math.floor(t/Qt))?.metroHeight?.profileAt?.(e,t)??null,'
       'dungeonPromptInfo:dH,dungeonPromptLabel:fH,')
for needle, replacement in [(anchor, anchor + hook), (bridge, bridge + api)]:
    if replacement in source:
        continue
    if source.count(needle) != 1:
        raise SystemExit('Metro height adapter: bundle anchor changed')
    source = source.replace(needle, replacement, 1)
# Preserve every native lease/depth guard; extend only entry proximity to the
# actual shaft belonging to that same original entry and loaded height cache.
reach = ('function metroEntryReach(g,e){if(!g?.p||g.world?.inDungeon||e?.kind!=="metro"||e.sewer)return false;'
         'let p=xf.get(Math.floor(g.p.x/Qt)+","+Math.floor(g.p.z/Qt))?.metroHeight?.profileAt?.(g.p.x,g.p.z);'
         'return !!p&&e.x===p.x&&e.z===p.z+1.5}')
if reach not in source:
    if 'function metroEntryReach(' in source:
        raise SystemExit('Metro entry proximity adapter changed')
    source = source.replace(anchor, reach + anchor, 1)
guards = [
    ('c.view?.isOpen()&&Math.hypot(e.p.x-t.x,e.p.z-t.z)<2.6',
     'c.view?.isOpen()&&(Math.hypot(e.p.x-t.x,e.p.z-t.z)<2.6||metroEntryReach(e,t))'),
    ('this.p.alive&&!this.world.inDungeon&&Math.hypot(this.p.x-e.x,this.p.z-e.z)<2.6&&this.useEntrance(e)',
     'this.p.alive&&!this.world.inDungeon&&(Math.hypot(this.p.x-e.x,this.p.z-e.z)<2.6||metroEntryReach(this,e))&&this.useEntrance(e)'),
]
for needle,replacement in guards:
    if replacement in source:
        continue
    if source.count(needle)!=1:
        raise SystemExit('Metro entry proximity guard changed')
    source=source.replace(needle,replacement,1)
target.write_text(source)
print('Metro height adapter ready')
