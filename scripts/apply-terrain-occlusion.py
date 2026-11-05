"""Include the native 1.6 m contact-shadow radius in its spatial lookup.

The original module sources are unavailable. This adapter changes only the
four bounds of the temporary terrain AO index, with strict native anchors.
"""
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'play/index.html'
html=path.read_text(encoding='utf-8')
radius='K<1.6&&(bt=Math.min(bt,.45+.55*$s(0,1.6,K)))'
if html.count(radius)!=1:raise SystemExit('Native contact-shadow radius changed')
before='for(let A=Math.floor((v.x0-n)/4);A<=Math.floor((v.x1-n)/4);A++)for(let w=Math.floor((v.z0-s)/4);w<=Math.floor((v.z1-s)/4);w++)'
after='for(let A=Math.floor((v.x0-n-1.6)/4);A<=Math.floor((v.x1-n+1.6)/4);A++)for(let w=Math.floor((v.z0-s-1.6)/4);w<=Math.floor((v.z1-s+1.6)/4);w++)'
if after not in html:
    if html.count(before)!=1:raise SystemExit('Terrain AO index anchor changed')
    html=html.replace(before,after,1)
if html.count(after)!=1:raise SystemExit('Terrain AO patch is ambiguous')
path.write_text(html,encoding='utf-8')
print('Terrain contact-shadow lookup includes the native radius')
