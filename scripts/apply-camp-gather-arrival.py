"""Привязать видимый сбор к прибытию на место и возврату в лагерь.

Старый таймер начислял ресурс даже за непроходимым препятствием и помечал
дорогу как работу. Используем существующие kv/Av, work и цикл .75 → лагерь;
новых полей сохранения нет. Применяется строго к опубликованной 0.4.37.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'play/index.html'
source = path.read_text()
changes = [
    ('let h=ya(e,t,a)*i;if(t.status="working",c.outpost)',
     'if(o==="gather"&&!t.facility&&!c.outpost&&Array.isArray(n.resourcePoints)&&Array.isArray(n.workerObstacles)){const m=kv(e,t,n);if(!Number.isFinite(t.pos?.x)||!Number.isFinite(t.pos?.z)||Math.hypot(t.pos.x-m.x,t.pos.z-m.z)>.4){t.status="travel";return}}let h=ya(e,t,a)*i;if(t.status="working",c.outpost)'),
    ('if(t.status!=="blocked"&&WI(t,B.camp.work.gatherPeriod)>=.75)return l("camp","travel");',
     'if(WI(t,B.camp.work.gatherPeriod)>=.75){let u=l("camp","travel");return u.carrying=!0,u}'),
    ('>r.teleport&&!["warehouse","segment"].includes(e.buildings[t.order?.target]?.type)',
     '>r.teleport&&!String(t.job).startsWith("gather:")&&!["warehouse","segment"].includes(e.buildings[t.order?.target]?.type)'),
    ('t.pos=nr(t.pos,s,r.speed*i,n.workerObstacles,Math.min(r.stop,.15))}',
     'const o=nr(t.pos,s,r.speed*i,n.workerObstacles,Math.min(r.stop,.15));if(String(t.job).startsWith("gather:")&&!t.facility&&!t.order?.outpost){if(Math.hypot(o.x-t.pos.x,o.z-t.pos.z)<1e-6&&Math.hypot(s.x-t.pos.x,s.z-t.pos.z)>.4)t.status="blocked",t.workBlock="obstacle";else delete t.workBlock}t.pos=o}'),
]
for before, after in changes:
    if source.count(after) == 1:
        continue
    if source.count(before) != 1:
        raise SystemExit('Unexpected gather source; no partial patch written')
    source = source.replace(before, after)
path.write_text(source)
print('Applied gather arrival gate and visible return cargo')
