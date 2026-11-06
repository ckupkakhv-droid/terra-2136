"""Открыть прежнюю чистую фабрику значка оружия для листа рецепта.

У штатного крафта spear/club показывают значок ящика по ключу _weapon.
Новый каталог читает настоящий вид из recipe.out._weapon и использует fs.
Тело фабрики, рецепты и операции не меняются. Повторный запуск безопасен.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'play/index.html'
source = path.read_text()
anchor = 'window.TERRA_CAMP_ALBUM_DATA=Object.freeze({progression:WL,expansion:Z1,portrait:s=>uF(vM(s))});'
bridge = 'window.TERRA_FIELD_KIT_DATA=Object.freeze({weaponIcon:fs});'
if source.count(bridge + anchor) == 1:
    print('Field kit icon bridge already applied')
elif source.count(anchor) == 1 and bridge not in source:
    path.write_text(source.replace(anchor, bridge + anchor, 1))
    print('Applied read-only native weapon icon bridge')
else:
    raise SystemExit('Unexpected source; no patch written')
