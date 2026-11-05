"""Publish the ready hero before native pose updates, with an optional hook.

The original bundle sources are unavailable; keep this narrow edit reproducible
and fail if a future build changes its anchors. Readable guards live in art/.
"""
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'play/index.html'
html=path.read_text(encoding='utf-8')
tag='<script src="art/actor-readiness.js?v=1"></script>'
anchor='<script src="art/leaf-canopies.js?v=2"></script>'
if tag not in html:
    if html.count(anchor)!=1:raise SystemExit('Actor readiness: script anchor changed')
    html=html.replace(anchor,anchor+'\n'+tag,1)
before='heroPose(t){let i=this.p'
after='heroPose(t){window.TERRA_ART?.readyHero?.(this);let i=this.p'
if after not in html:
    if html.count(before)!=1:raise SystemExit('Actor readiness: native pose anchor changed')
    html=html.replace(before,after,1)
# Early publication has no reason to revisit unrelated enemy instances. The
# default refresh path, including its final loader cleanup, stays unchanged.
edits=[
    ('refreshModelMode(){let t=this.modelsOn=!0;',
     'refreshModelMode(heroOnly=!1){let t=this.modelsOn=!0;'),
    ('this.heroInst&&(this.heroInst.root.visible=!!(t&&this.glb.hero));for(let i of this.enemies)',
     'this.heroInst&&(this.heroInst.root.visible=!!(t&&this.glb.hero));if(heroOnly===!0)return;for(let i of this.enemies)'),
]
for before,after in edits:
    if after in html:continue
    if html.count(before)!=1:raise SystemExit('Actor readiness: native refresh anchor changed')
    html=html.replace(before,after,1)
path.write_text(html,encoding='utf-8')
print('Native hero readiness hook ready')
