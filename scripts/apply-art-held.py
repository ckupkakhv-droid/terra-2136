"""[art] PR №2: подключить арт-слой оружия и инструментов в руках героя (play/art/held.js + play/assets/art/held.glb).

Точки в play/index.html (проверяется точная базовая версия main после PR #13):
  1) <script src="art/held.js"></script> сразу после art/landmarks.js;
  2) хук hookHeld рядом с хуком ориентиров (GLTFLoader/MeshoptDecoder для загрузки; Xg/$g — только для витрины ?artpreview=weapons);
  3) оружие героя: после c=Xg(r) в кэше wGeoCache — TERRA_ART.held(c,"w_"+r);
  4) инструмент героя: после $g(o) в ixPost — TERRA_ART.held(d,"t_"+o).
Вызовы Xg/$g для жителей и строителей лагеря не меняются.
"""
from pathlib import Path
import hashlib, sys

root = Path(__file__).resolve().parents[1]
path = root / 'play/index.html'
raw = path.read_bytes()
BASE = '39463103ffc3c49e92a68d503e3795cbcf13de5f51e8523f2985e4f62fba054c'  # main 23484d1 (PR #13)
digest = hashlib.sha256(raw).hexdigest()
if digest != BASE and '--rebased' not in sys.argv:
    raise SystemExit(f'Unsupported HTML baseline {digest[:12]}; review upstream changes, then rerun with --rebased.')
s = raw.decode()
assert 'TERRA_ART.held' not in s and 'art/held.js' not in s, 'already applied'

def rep(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

rep('<script src="art/landmarks.js"></script>', '<script src="art/landmarks.js"></script>\n<script src="art/held.js"></script>')
rep('get MD(){return vp}})}catch(e){console.warn("TERRA_ART",e)}',
    'get MD(){return vp}})}catch(e){console.warn("TERRA_ART",e)}'
    'try{window.TERRA_ART&&TERRA_ART.hookHeld&&TERRA_ART.hookHeld({get Xg(){return Xg},get Tg(){return $g},get GL(){return _h},get MD(){return vp}})}catch(e){}')
rep('c||(c=Xg(r),Tt[r].cls==="gun"', 'c||(c=Xg(r),window.TERRA_ART&&TERRA_ART.held&&TERRA_ART.held(c,"w_"+r),Tt[r].cls==="gun"')
rep('d||(d=i.geo["t_"+o]=$g(o)),', 'd||(d=i.geo["t_"+o]=$g(o),window.TERRA_ART&&TERRA_ART.held&&TERRA_ART.held(d,"t_"+o)),')

grow = len(s.encode()) - len(raw)
assert 0 < grow < 1024, f'HTML grew by {grow} bytes'
path.write_text(s)
print(f'patched play/index.html (+{grow} bytes)')
