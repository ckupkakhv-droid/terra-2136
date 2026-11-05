"""Install the prop-material repair and preserve atlas ids during native wreck rewinds."""
from pathlib import Path

p=Path(__file__).resolve().parents[1]/'play/index.html'
s=p.read_text()
edits=[
 ('<script src="art/terrain-blend.js"></script>',
  '<script src="art/terrain-blend.js"></script>\n<script src="art/prop-materials.js"></script>'),
 # A detailed wreck removes the just-appended packed body after inserting its
 # kit replacement. Rewind atlas ids along with the other vertex attributes.
 ('g.p.length=g.n.length=g.c.length=p,g.a.length=p/3*2,g.uv',
  'g.p.length=g.n.length=g.c.length=p,g.a.length=p/3*2,g.m&&(g.m.length=p/3),g.uv'),
]
for old,new in edits:
 if new in s:continue
 if s.count(old)!=1:raise SystemExit('Prop materials: bundle anchor changed')
 s=s.replace(old,new,1)
p.write_text(s)
print('Packed-prop material repair ready')
