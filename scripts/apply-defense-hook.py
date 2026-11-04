"""[defense] Минимальная обвязка бандла для play/ui/defense.js.

Делает три точечные замены в play/index.html и не увеличивает файл:
1. baseInit отдаёт модулю обороны каталог построек, конфиг, предметы,
   рецепты и нужные классы three.js (window.TERRA_DEFENSE_CTX + хук);
2. новая постройка сохраняет `t: w.as || sel` и `dk: w.dk`, поэтому
   новые турели пишутся в сейв как обычная turretB с полем dk;
3. проверка сейва отклоняет блок camp.defense из будущей версии (v>1).
Байты компенсируются удалением ведущих отступов в строках 4736-4950
(CSS обороны и GLSL-шейдеры внутри шаблонных строк; на работу не влияет).
"""
from pathlib import Path
import hashlib

root = Path(__file__).resolve().parents[1]
path = root / 'play/index.html'
raw = path.read_bytes()
BASE = '39463103ffc3c49e92a68d503e3795cbcf13de5f51e8523f2985e4f62fba054c'
if hashlib.sha256(raw).hexdigest() != BASE:
    raise SystemExit('Unsupported HTML baseline; review the upstream changes before applying.')
s = raw.decode()

def once(old, new):
    global s
    assert s.count(old) == 1, old
    s = s.replace(old, new)

once('baseInit(){let e=this.p;',
     'baseInit(){window.TERRA_DEFENSE_CTX={Li,B,Yt,uu,G:_h,M:vp,K:Ke,R:R2,I:pi,X:$t,D:Dt,V:H,C:Rt,L:Xe,N:nh,Y:Ot,Q:Qu},'
     'window.TERRA_DEFENSE_HOOK?.(this);let e=this.p;')
once('m={t:l.sel,x:l.gx,z:l.gz,r:l.rot}', 'm={t:w.as||l.sel,dk:w.dk,x:l.gx,z:l.gz,r:l.rot}')
once('if(e.p.camp?.power?.v>1)return{ok:!1,reason:"future"};',
     'if(e.p.camp?.power?.v>1)return{ok:!1,reason:"future"};if(e.p.camp?.defense?.v>1)return{ok:!1,reason:"future"};')
once('<script src="art/landmarks.js"></script>\n',
     '<script src="art/landmarks.js"></script>\n<script defer src="ui/defense.js"></script>\n')

lines = s.split('\n')
need = len(s.encode()) - len(raw)
for i in range(4735, 4950):  # 0-based: строки 4736..4950
    if need <= 0:
        break
    ln = lines[i]
    st = ln.lstrip(' \t')
    cut = len(ln) - len(st)
    if cut:
        lines[i] = st
        need -= cut
s = '\n'.join(lines)
assert len(s.encode()) <= len(raw), 'Keep the large HTML from growing'
path.write_text(s)
print('ok', len(raw), '->', len(s.encode()))
