"""[art] PR №1: подключить слой моделей ориентиров (play/art/landmarks.js + play/assets/art/landmarks.glb).

Вносит в play/index.html только две точки:
  1) <script src="art/landmarks.js"></script> в <head> (до бандла, после подключения UI лагеря);
  2) хук после `Object.assign(Ie.prototype,fT);`, который передаёт арт-слою ссылки на генератор чанка,
     батчи и уже встроенные GLTFLoader/MeshoptDecoder. Без арт-слоя хук ничего не делает.
Проверяется точная базовая версия main (после PR #8). Повторный запуск — ошибка, а не двойной патч.
"""
from pathlib import Path
import hashlib, sys

root = Path(__file__).resolve().parents[1]
path = root / 'play/index.html'
raw = path.read_bytes()
BASE = '858fe60ec39a73b663dc0c5a915da3597afa99aefeddc414c7b6b3aaf2046cc9'  # main 6f5aaf0 (PR #8 не менял HTML)
digest = hashlib.sha256(raw).hexdigest()
if digest != BASE and '--rebased' not in sys.argv:
    raise SystemExit(f'Unsupported HTML baseline {digest[:12]}; review upstream changes, then rerun with --rebased.')
s = raw.decode()
assert 'TERRA_ART' not in s, 'already applied'

tag_anchor = '<script defer src="ui/camp-navigation.js"></script>\n</head>'
assert s.count(tag_anchor) == 1
s = s.replace(tag_anchor, '<script defer src="ui/camp-navigation.js"></script>\n<script src="art/landmarks.js"></script>\n</head>')

hook_anchor = 'Object.assign(Ie.prototype,fT);'
assert s.count(hook_anchor) == 1
hook = ('try{window.TERRA_ART&&TERRA_ART.hook&&TERRA_ART.hook({Ie,get ue(){return ue},get Wr(){return Wr},get Ct(){return Ct},get L(){return L},'
        'get GL(){return _h},get MD(){return vp}})}catch(e){console.warn("TERRA_ART",e)}')
s = s.replace(hook_anchor, hook_anchor + hook)

grow = len(s.encode()) - len(raw)
assert 0 < grow < 1024, f'HTML grew by {grow} bytes'
path.write_text(s)
print(f'patched play/index.html (+{grow} bytes)')
