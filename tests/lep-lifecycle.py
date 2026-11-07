"""Жизненный цикл опоры: выгрузка района и десять возвратов.

Не замер кадров и не повтор smoke. Один запуск Chromium, временный профиль.

  python3 -m http.server 8080
  python3 tests/lep-lifecycle.py

Правило удержания в world.update: при inDungeon выход сразу; иначе район
без флага dg снимается, когда |cx-игрок| или |cz-игрок| больше radius+1.
unload зовёт discardChunk, тот снимает меши, вызывает geometry.dispose
и удаляет запись, только если в карте всё ещё этот же объект.
Число районов при радиусе 1 остаётся 9: окно уехало, старый объект исчез.
"""
import json
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
OUT = Path(os.environ.get('TERRA_LEP_OUT', '/tmp/lep-lifecycle'))
CHROME = os.environ.get('TERRA_CHROMIUM') or shutil.which('google-chrome') or shutil.which('chromium')
ROAD = {'cx': -3, 'cz': -3, 'x': -132.8, 'z': -120.0}
FAR = {'x': 5000.0, 'z': 5000.0}

OUT.mkdir(parents=True, exist_ok=True)

BOOT = """() => new Promise((resolve) => {
  const t = setInterval(() => {
    if (window.game && game.state === 'play' && game.p && game.world && game.ren && window.TERRA_LEP && TERRA_LEP.ready) {
      clearInterval(t); resolve(true);
    }
  }, 100);
})"""

RUN = r"""
(cfg) => {
  const world = game.world;
  const road = cfg.road, far = cfg.far;
  const key = road.cx + ',' + road.cz;
  const discarded = [];
  const unloads = [];
  const discard = world.discardChunk.bind(world);
  const unload = world.unload.bind(world);
  world.discardChunk = function (ch) {
    discarded.push({cx: ch.cx, cz: ch.cz, dg: !!ch.dg, life: ch._life || null});
    return discard(ch);
  };
  world.unload = function (ch) {
    const ok = unload(ch);
    unloads.push({cx: ch.cx, cz: ch.cz, dg: !!ch.dg, ok: ok === true});
    return ok;
  };
  function place(x, z) {
    game.p.x = x; game.p.z = z;
    game.world.update(x, z, true);
    game.cameraUpdate(1);
  }
  place(road.x, road.z);
  const first = world.chunks.get(key);
  if (!first) return {ok: false, reason: 'road chunk missing before unload', radius: world.radius, inDungeon: !!world.inDungeon};
  first._life = 'road-0';
  const px = Math.floor(far.x / 48), pz = Math.floor(far.z / 48);
  const rule = {
    radius: world.radius,
    keep: world.radius + 1,
    inDungeon: !!world.inDungeon,
    dg: !!first.dg,
    farChunk: {cx: px, cz: pz},
    chebyshev: Math.max(Math.abs(first.cx - px), Math.abs(first.cz - pz)),
    wouldUnload: !world.inDungeon && !first.dg && Math.max(Math.abs(first.cx - px), Math.abs(first.cz - pz)) > world.radius + 1
  };
  const beforeIds = [...world.chunks.keys()];
  place(far.x, far.z);
  const gone = !world.chunks.has(key);
  const stillSame = [...world.chunks.values()].some(ch => ch._life === 'road-0');
  const roadDiscards = discarded.filter(d => d.cx === road.cx && d.cz === road.cz);
  const roadUnloads = unloads.filter(d => d.cx === road.cx && d.cz === road.cz);
  if (!(gone && !stillSame && roadDiscards.length === 1 && roadUnloads.some(d => d.ok))) {
    return {ok: false, reason: 'real unload did not remove the road chunk object', rule, gone, stillSame, roadDiscards, roadUnloads, chunkCount: world.chunks.size, beforeIds};
  }
  function programs() {
    const list = game.ren.info.programs || [];
    return [...list].map(p => ({id: p.id, name: p.name || '', cacheKey: String(p.cacheKey || '')}));
  }
  function geometries() { return game.ren.info.memory.geometries; }
  function batches() {
    let n = 0;
    game.scene.traverse(o => { if (o.name === 'lep-batch') n++; });
    return n;
  }
  function height() {
    const ox = game.p.x, oz = game.p.z;
    game.p.x = road.x; game.p.z = road.z;
    game.cameraUpdate(1);
    const h = game.p.y;
    game.p.x = ox; game.p.z = oz;
    return h;
  }
  function anchors(h) {
    const ry = Math.PI / 2, cs = Math.cos(ry), sn = Math.sin(ry);
    const local = [[-4.2, 10.8, 0], [4.2, 10.8, 0], [3, 13.2, 0]];
    const ch = world.chunks.get(key);
    const meshes = (ch && ch.meshes || []).filter(m => m.userData && m.userData.det && m.geometry && m.geometry.attributes.position);
    return local.map(p => {
      const ax = road.x + cs * p[0] + sn * p[2];
      const ay = h + p[1];
      const az = road.z - sn * p[0] + cs * p[2];
      let n = 0, sx = 0, sy = 0, sz = 0;
      for (const m of meshes) {
        const pos = m.geometry.attributes.position;
        for (let i = 0; i < pos.count; i++) {
          const x = pos.getX(i), y = pos.getY(i), z = pos.getZ(i);
          const dx = x - ax, dy = y - ay, dz = z - az;
          if (dx * dx + dy * dy + dz * dz > 0.04 * 0.04) continue;
          n++; sx += x; sy += y; sz += z;
        }
      }
      const c = n ? {x: sx / n, y: sy / n, z: sz / n} : null;
      const delta = c ? Math.hypot(c.x - ax, c.y - ay, c.z - az) : null;
      return {expect: {x: ax, y: ay, z: az}, verts: n, centroid: c, delta};
    });
  }
  function markAndCol() {
    const ch = world.chunks.get(key);
    const mark = ch && (ch.map || []).find(m => m && m.c === '#6a7076');
    const col = ch && (ch.cols || []).find(c => c && Math.abs((c.x1 - c.x0) - 3) < 0.05 && Math.abs((c.z1 - c.z0) - 3) < 0.05 && Math.abs(c.h - 2) < 0.05 && c.x0 <= road.x && c.x1 >= road.x && c.z0 <= road.z && c.z1 >= road.z);
    return {
      mark: mark ? {x0: mark.x0, z0: mark.z0, x1: mark.x1, z1: mark.z1, c: mark.c} : null,
      col: col ? {x0: col.x0, z0: col.z0, x1: col.x1, z1: col.z1, h: col.h} : null
    };
  }
  const cycles = [];
  for (let i = 1; i <= 10; i++) {
    place(road.x, road.z);
    const h = height();
    const batchesBeforeFlush = batches();
    try { TERRA_LEP.flush(); } catch (e) { /* счётчик ниже */ }
    if (game.renderT) game.renderT();
    const anc = anchors(h);
    const mc = markAndCol();
    const life = world.chunks.get(key);
    cycles.push({
      i, h,
      chunkLife: life ? (life._life || null) : null,
      present: !!life,
      batchesBeforeFlush,
      anchors: anc,
      anchorDeltaMax: Math.max(...anc.map(a => a.delta == null ? Infinity : a.delta)),
      mark: mc.mark, col: mc.col,
      lepBatches: batches(),
      geometries: geometries(),
      programs: programs()
    });
    if (life) life._life = 'road-' + i;
    if (i < 10) place(far.x, far.z);
  }
  const base = cycles[0];
  const progIds = (row) => row.programs.map(p => p.id + ':' + p.cacheKey).sort();
  const baseIds = progIds(base);
  const compare = cycles.map(row => {
    const ids = progIds(row);
    return {
      i: row.i,
      geometries: row.geometries,
      geometryDelta: row.geometries - base.geometries,
      programCount: row.programs.length,
      newProgramIds: ids.filter(id => !baseIds.includes(id)),
      droppedProgramIds: baseIds.filter(id => !ids.includes(id)),
      anchorDeltaMax: row.anchorDeltaMax,
      anchorVsFirst: row.anchors.map((a, k) => {
        const b = base.anchors[k].centroid, c = a.centroid;
        return (b && c) ? Math.hypot(c.x - b.x, c.y - b.y, c.z - b.z) : null;
      })
    };
  });
  let fallback = null;
  try {
    const cx = 27, cz = 15, x = cx * 48 + 11.2, z = cz * 48 + 24;
    const errBefore = TERRA_LEP.stats.errors.slice();
    const restore = TERRA_LEP.debugDrop('lod0');
    place(x, z);
    game.p.x = x; game.p.z = z; game.cameraUpdate(1);
    const hh = game.p.y;
    const ch = world.chunkAt(x, z);
    const cs = Math.cos(Math.PI / 2), sn = Math.sin(Math.PI / 2);
    const foot = {x: x + sn * 1.4, y: hh, z: z - sn * 1.4};
    let chunkN = 0, batchN = 0, owners = [];
    for (const m of (ch && ch.meshes || [])) {
      const pos = m.geometry && m.geometry.attributes && m.geometry.attributes.position;
      if (!pos) continue;
      let n = 0;
      for (let i = 0; i < pos.count; i++) {
        const dx = pos.getX(i) - foot.x, dy = pos.getY(i) - foot.y, dz = pos.getZ(i) - foot.z;
        if (dx * dx + dy * dy + dz * dz <= 0.22 * 0.22) n++;
      }
      if (n) { chunkN += n; owners.push({name: m.name || '', det: !!(m.userData && m.userData.det), n}); }
    }
    const batch = game.scene.getObjectByName('lep-batch');
    const bp = batch && batch.geometry && batch.geometry.attributes.position;
    if (bp) for (let i = 0; i < bp.count; i++) {
      const dx = bp.getX(i) - foot.x, dy = bp.getY(i) - foot.y, dz = bp.getZ(i) - foot.z;
      if (dx * dx + dy * dy + dz * dz <= 0.22 * 0.22) batchN++;
    }
    const errors = TERRA_LEP.stats.errors.slice();
    restore();
    fallback = {chunkN, batchN, owners, errors, errBefore, repeated: errors.filter(e => e === 'lep:lod-missing:lod0').length};
  } catch (e) {
    fallback = {error: String(e)};
  }
  return {
    ok: true,
    rule, gone, stillSame,
    roadDiscards, roadUnloads,
    discardCount: discarded.length,
    chunkCountFar: null,
    cycles: cycles.map(row => ({
      i: row.i, h: row.h, present: row.present,
      batchesBeforeFlush: row.batchesBeforeFlush,
      anchorDeltaMax: row.anchorDeltaMax,
      anchors: row.anchors,
      mark: row.mark, col: row.col,
      lepBatches: row.lepBatches,
      geometries: row.geometries,
      programs: row.programs
    })),
    compare, fallback
  };
}
"""


def main():
    if not CHROME:
        raise SystemExit('Chromium не найден')
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=CHROME,
            args=['--ignore-gpu-blocklist', '--enable-webgl', '--use-gl=angle', '--enable-unsafe-swiftshader'],
        )
        ctx = browser.new_context(viewport={'width': 1280, 'height': 800}, device_scale_factor=1)
        ctx.add_init_script(
            "localStorage.setItem('terra_set', JSON.stringify({q:'med', vol:0, vm:0, vs:0, va:0, post:false, dpr:1, shake:false}));"
        )
        page = ctx.new_page()
        page.set_default_timeout(180000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(URL, wait_until='load')
        page.locator('#mNew').click()
        try:
            page.locator('#skip').click(timeout=15000)
        except Exception:
            pass
        page.wait_for_function(BOOT)
        result = page.evaluate(RUN, {'road': ROAD, 'far': FAR})
        browser.close()
    result['pageErrors'] = errors
    path = OUT / 'lifecycle.json'
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding='utf-8')
    print('wrote', path)
    if not result.get('ok'):
        print(json.dumps({k: result.get(k) for k in ('reason', 'rule', 'gone', 'stillSame', 'roadDiscards', 'roadUnloads')}, ensure_ascii=False, indent=2))
        raise SystemExit(1)
    assert not errors, errors[:3]
    cmp = result['compare']
    for row in result['cycles']:
        assert row['present'] and row['lepBatches'] == 1, row['i']
        assert row['mark'] and row['mark']['c'] == '#6a7076', row['mark']
        assert row['col'] and abs(row['col']['h'] - 2) < 0.05, row['col']
        assert row['anchorDeltaMax'] <= 0.001, row['anchors']
    for row in cmp:
        assert all(d is not None and d <= 0.001 for d in row['anchorVsFirst']), row
    growth = [row['geometryDelta'] for row in cmp]
    new_progs = [row['newProgramIds'] for row in cmp if row['newProgramIds']]
    fb = result['fallback']
    assert fb and not fb.get('error'), fb
    assert fb['chunkN'] == 36 and fb['batchN'] == 0, fb
    assert sorted(o['n'] for o in fb['owners']) == [18, 18], fb
    assert fb['errors'].count('lep:lod-missing:lod0') == 1, fb['errors']
    print('UNLOAD', json.dumps(result['rule'], ensure_ascii=False), 'discards', result['roadDiscards'])
    print('cycles', [(c['i'], c['geometries'], c['lepBatches'], round(c['anchorDeltaMax'], 6)) for c in result['cycles']])
    print('geometryDelta', growth)
    print('newPrograms', new_progs)
    print('fallback foot', fb['chunkN'], fb['owners'])


if __name__ == '__main__':
    main()
