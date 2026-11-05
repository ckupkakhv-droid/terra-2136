"""Install district paint blending and consistent slope weights at grid borders."""
from pathlib import Path

p=Path(__file__).resolve().parents[1]/'play/index.html'
s=p.read_text()
anchor='if(Y>.06){let U=Qn(k*.2,E*.2,5,2)>.5;'
hook='window.TERRA_ART?.blendTerrainBase?.(l,k,E,g,u,dT,Qn,Wr);'
edits=[
 ('<script src="art/salvage-props.js"></script>',
  '<script src="art/salvage-props.js"></script>\n<script src="art/terrain-blend.js"></script>'),
 (anchor,hook+anchor),
 ('let V=0,Y=1-1/P,Z=e.hv[w];','let V=0,Y=1-1/Q,Z=e.hv[w];'),
]
for old,new in edits:
 if new in s:continue
 if s.count(old)!=1:raise SystemExit('Terrain paint adapter: native anchor changed')
 s=s.replace(old,new,1)
p.write_text(s)
print('Terrain paint adapter ready')
