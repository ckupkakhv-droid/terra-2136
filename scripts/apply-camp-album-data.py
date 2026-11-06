"""Открыть два существующих чистых запроса интерфейса, не меняя механику.

WL — штатная дорожная карта требований; Z1 — текущий шаг расширения.
Запросы только читают переданное состояние; uF(vM) строит прежний портрет.
Экспорт нужен рисунку альбома,
чтобы не дублировать формулы ценности, требования и поиск следующей цели.
Применяется строго к опубликованной 0.4.38, повторный запуск безопасен.
"""
from pathlib import Path
path=Path(__file__).resolve().parents[1]/'play/index.html'
s=path.read_text()
before='try{window.game=new hr}'
after='window.TERRA_CAMP_ALBUM_DATA=Object.freeze({progression:WL,expansion:Z1,portrait:s=>uF(vM(s))});'+before
if s.count(after)==1:print('Camp album data bridge already applied')
elif s.count(before)==1:path.write_text(s.replace(before,after,1));print('Applied read-only native camp album queries')
else:raise SystemExit('Unexpected source; no patch written')
