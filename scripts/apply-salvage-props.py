"""Install small-container art and its optional native breakable-geometry hook."""
from pathlib import Path

target=Path(__file__).resolve().parents[1]/'play/index.html'
s=target.read_text()
edits=[
 ('<script src="art/visual-fixes.js"></script>',
  '<script src="art/visual-fixes.js"></script>\n<script src="art/salvage-props.js"></script>'),
 ('function tnt(e){let t=new ue(()=>.5);t.hf=null,t.oy=0,t.sink=0;',
  'function tnt(e){let t=new ue(()=>.5);t.hf=null,t.oy=0,t.sink=0;'
  'if(window.TERRA_ART?.buildBreakable?.(e,t))return t.geometry();'),
]
for old,new in edits:
 if new in s:continue
 if s.count(old)!=1:raise SystemExit('Supply-container adapter: native anchor changed')
 s=s.replace(old,new,1)
target.write_text(s)
print('Supply-container adapter ready')
