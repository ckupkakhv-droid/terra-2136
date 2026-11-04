"""Подключить оформление рюкзака из play/ui.

Основа — play/index.html из fix/visual-bugs-nov4: кадр куклы там уже
считается по позе (скиннинг, 3–97 перцентиль) и аспекту окна. Этот патч
только добавляет две ссылки и формулу камеры не трогает.
Повторный запуск на уже пропатченном файле ничего не меняет.
"""
from pathlib import Path
import hashlib

root = Path(__file__).resolve().parents[1]
path = root / 'play/index.html'
raw = path.read_bytes()
text = raw.decode('utf-8')
if 'ui/backpack.css' in text or 'ui/backpack.js' in text:
    if text.count('href="ui/backpack.css"') != 1 or text.count('src="ui/backpack.js"') != 1:
        raise SystemExit('Метки рюкзака есть, но не по одному разу.')
    raise SystemExit(0)
expected = '13041e3ea9bfdd636ac6958c883a2781bd0a155082cdc46d562fc1314c4dcb86'
if hashlib.sha256(raw).hexdigest() != expected:
    raise SystemExit('Другая основа HTML. Сверьте правки, прежде чем накладывать патч.')
anchor = (
    '<script src="art/visual-fixes.js"></script>\n'
    '<link rel="stylesheet" href="ui/visual-fixes.css">\n'
    '<script defer src="ui/visual-fixes.js"></script>'
)
insert = (
    anchor + '\n'
    '<link rel="stylesheet" href="ui/backpack.css">\n'
    '<script defer src="ui/backpack.js"></script>'
)
if text.count(anchor) != 1:
    raise SystemExit(f'Якорь visual-fixes встретился {text.count(anchor)} раз, нужен один.')
text = text.replace(anchor, insert, 1)
if text.count('href="ui/backpack.css"') != 1 or text.count('src="ui/backpack.js"') != 1:
    raise SystemExit('Метки рюкзака не встали одним куском.')
if 'setFromObject(r)' not in text or 'applyBoneTransform' not in text:
    raise SystemExit('В основе нет кадра по позе. Патч камеры не дублируем и не затираем.')
path.write_text(text)
print(f'Рюкзак подключён, {len(text.encode()) - len(raw):+d} байт. Кадр куклы не менялся.')
