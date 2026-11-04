"""[defense] Одноразовая обвязка бандла для play/ui/defense.js (PR #16).

Уже применена в репозитории; повторный запуск ничего не меняет (каждая правка
проверяется по своему якорю, без привязки к sha256 всего файла). Четыре точечные правки:
1. подключение <script defer src="ui/defense.js">;
2. baseInit отдаёт модулю обороны каталог построек, конфиг, предметы, рецепты и
   нужные классы three.js (window.TERRA_DEFENSE_CTX) и вызывает window.TERRA_DEFENSE_HOOK;
3. новая постройка сохраняет `t: w.as || sel` и `dk: w.dk` — новые турели пишутся
   в сейв как обычная turretB с полем dk;
4. при сносе возврат считается от `A.refundOf(запись)`, если он есть (цена вида и уровня).

Проверки camp.defense.v>1 в валидаторе сейва (Vv) нет намеренно: Vv лежит на одной
строке бандла длиной ~200 КБ, которую правит и #15, — правка там дала бы конфликт слияния.
Блок из более новой версии обрабатывает сам ui/defense.js: модуль замирает и не пишет
ни в блок, ни в турели (см. isFuture).

Если после слияния чужих правок index.html придётся собрать заново: взять их версию
файла и запустить этот скрипт ещё раз — правки, которых нет, он допишет.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'play/index.html'
s = path.read_text()
EDITS = [
    # тег стоит перед camp-navigation.css, а не в конце <head>: туда же дописывают свои
    # теги #10 и #15, и соседние вставки дали бы конфликт слияния
    ('\n<link rel="stylesheet" href="ui/camp-navigation.css">\n',
     '\n<script defer src="ui/defense.js"></script>\n<link rel="stylesheet" href="ui/camp-navigation.css">\n'),
    ('baseInit(){let e=this.p;',
     'baseInit(){window.TERRA_DEFENSE_CTX={Li,B,Yt,uu,G:_h,M:vp,K:Ke,R:R2,I:pi,X:$t,D:Dt,V:H,C:Rt,L:Xe,N:nh,Y:Ot,Q:Qu},'
     'window.TERRA_DEFENSE_HOOK?.(this);let e=this.p;'),
    ('m={t:l.sel,x:l.gx,z:l.gz,r:l.rot}', 'm={t:w.as||l.sel,dk:w.dk,x:l.gx,z:l.gz,r:l.rot}'),
    ('for(let[w,k]of Object.entries(A.cost))', 'for(let[w,k]of Object.entries(A.refundOf?.(v)||A.cost))'),
]
changed = 0
for old, new in EDITS:
    if s.count(new) == 1:
        continue  # уже применено
    assert s.count(old) == 1, 'якорь не найден или неоднозначен: ' + old[:60]
    s = s.replace(old, new)
    changed += 1
if changed:
    path.write_text(s)
print('applied', changed, 'of', len(EDITS))
