"""Подносчик и стена: глухой отрезок не списывает склад, открытый путь довозит.

Живой бандл, Playwright и Chromium. Новая игра, без личного сейва.
Стена — обычные записи base t:wall, их видит и segHit, и segmentNav.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
OUT = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-porter-obstacle'))
OUT.mkdir(parents=True, exist_ok=True)
CHROME = os.environ.get('TERRA_CHROMIUM') or '/usr/local/bin/google-chrome'

BOOT = r"""
() => {
  const h = game.homePos();
  game.p.level = 6;
  game.p.camp.rep = 1000;
  const rec = game.camp.recruit({ id: 'qa-porter', name: 'Марк Поднос', prof: 'hauler' });
  if (!rec.ok) throw Error('recruit ' + JSON.stringify(rec));
  const s = game.p.camp.settlers['qa-porter'];
  s.job = 'idle';
  s.order = Object.assign({}, s.order, { stick: false });
  game.p.camp.res.a545 = 200;
  game.world.radius = 3;
  for (const dz of [-1, 0, 1]) for (const dx of [-1, 0, 1]) game.world.update(h.x + dx * 40, h.z + dz * 40, true);
  const depot = { x: h.x, z: h.z };
  const nav = game.workerSceneContext().segmentNav;
  const pad = 2.1;
  const span = (a, b) => {
    const dx = b.x - a.x, dz = b.z - a.z, len = Math.hypot(dx, dz);
    return { start: { x: a.x + dx / len * pad, z: a.z + dz / len * pad }, end: { x: b.x - dx / len * pad, z: b.z - dz / len * pad } };
  };
  const clear = [];
  for (let i = 0; i < 16; i++) {
    const ang = i * Math.PI / 8;
    const dir = { x: Math.cos(ang), z: Math.sin(ang) };
    const far = { x: h.x + dir.x * 18, z: h.z + dir.z * 18 };
    const seg = span(depot, far);
    if (game.world.segHit(seg.start.x, seg.start.z, seg.end.x, seg.end.z, 1.1) < 0 && nav.check(seg.start, seg.end).ok) clear.push({ i, dir, far });
  }
  if (clear.length < 2) return { ok: false, reason: 'no clear rays', clear: clear.length };
  const blockedRay = clear[0];
  const openRay = clear.find(r => { const d = Math.min(Math.abs(r.i - blockedRay.i), 16 - Math.abs(r.i - blockedRay.i)); return d >= 4; }) || clear[clear.length - 1];
  const blocked = blockedRay.far;
  const open = openRay.far;
  const mid = { x: h.x + blockedRay.dir.x * 10, z: h.z + blockedRay.dir.z * 10 };
  const px = -blockedRay.dir.z, pz = blockedRay.dir.x;
  const alongX = Math.abs(px) >= Math.abs(pz);
  const walls = [];
  for (let k = -7; k <= 7; k += 1.5) walls.push({ t: 'wall', x: mid.x + px * k, z: mid.z + pz * k, r: alongX ? 0 : 1 });
  game.p.base = game.p.base.filter(o => o.t !== 'wall' && o.t !== 'turretB');
  game.p.base.push(...walls);
  game.p.base.push({ t: 'turretB', dk: 'pkm', x: blocked.x, z: blocked.z, r: 0, mag: 0, dprio: 3 });
  game.p.base.push({ t: 'turretB', dk: 'pkm', x: open.x, z: open.z, r: 0, mag: 0, dprio: 0 });
  game.baseDirty = true;
  game.rebuildBase();
  const boxes = [];
  game.world.query(mid.x - 14, mid.z - 14, mid.x + 14, mid.z + 14, (box) => {
    const thin = box.x1 - box.x0 < 0.6 || box.z1 - box.z0 < 0.6;
    if (box.h >= 2.5 && thin && Math.hypot((box.x0 + box.x1) / 2 - mid.x, (box.z0 + box.z1) / 2 - mid.z) < 12)
      boxes.push({ x0: box.x0, x1: box.x1, z0: box.z0, z1: box.z1 });
    return false;
  });
  const bseg = span(depot, blocked), oseg = span(depot, open);
  window.__lay = { depot, blocked, open, mid, boxes };
  const model = window.TERRA_DEFENSE_CTX.R('hauler');
  const probe = game.glb?.[model] ? game.npcMesh({ name: 'probe', prof: 'hauler', model }) : null;
  if (probe?.root) { probe.root.removeFromParent(); try { probe.src.release(probe); } catch {} }
  return {
    ok: true,
    mesh: !!probe?.root,
    boxes: boxes.length,
    blockedAt: blocked, openAt: open,
    blocked: { seg: game.world.segHit(bseg.start.x, bseg.start.z, bseg.end.x, bseg.end.z, 1.1), nav: nav.check(bseg.start, bseg.end) },
    open: { seg: game.world.segHit(oseg.start.x, oseg.start.z, oseg.end.x, oseg.end.z, 1.1), nav: nav.check(oseg.start, oseg.end) },
    speed: window.TERRA_DEFENSE_CTX.B.camp.movement.speed,
    save: game.save()
  };
}
"""


def main():
    report = {}
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=CHROME, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage', '--no-sandbox'])
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        page.set_default_timeout(90000)
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.add_init_script("localStorage.setItem('terra_set', JSON.stringify({q:'low', post:false, dpr:1}))")
        page.goto(URL, wait_until='load', timeout=120000)
        page.locator('#mNew').click()
        page.locator('#skip').click()
        page.wait_for_function('game.state==="play" && terraDefense.ready && game.p && game.p.camp')
        page.wait_for_timeout(500)
        boot = page.evaluate(BOOT)
        report['boot'] = boot
        assert boot['save']['ok'] is True, boot['save']
        assert boot['mesh'] is True, 'модель подносчика не собралась'
        assert boot['boxes'] >= 8, boot
        assert boot['blocked']['nav']['ok'] is False and boot['blocked']['nav']['reason'] == 'obstacle', boot['blocked']
        assert boot['blocked']['seg'] >= 0, boot['blocked']
        assert boot['open']['nav']['ok'] is True and boot['open']['seg'] < 0, boot['open']
        page.evaluate(r"""() => {
          const orig = game.moduleUpdate.bind(game);
          window.__sim = 0;
          window.__events = [];
          window.addEventListener('terra:defense-change', (e) => window.__events.push(e.detail));
          game.loop = () => {};
          game.moduleUpdate = function (dt) { window.__sim += dt; return orig(dt); };
          const h = game.homePos();
          game.p.x = h.x; game.p.z = h.z + 3;
          const assigned = terraDefense.assign('qa-porter', true);
          if (!assigned.ok) throw Error(JSON.stringify(assigned));
        }""")

        def pump(seconds, dt=0.05):
            return page.evaluate("""({seconds, dt}) => {
              const lay = window.__lay;
              const inside = (x, z) => lay.boxes.some(b => x > b.x0 && x < b.x1 && z > b.z0 && z < b.z1);
              let prev = null, crossed = 0, seen = 0;
              const n = Math.round(seconds / dt);
              for (let i = 0; i < n; i++) {
                game.moduleUpdate(dt);
                if (i % 2) continue;
                let body = null;
                for (const o of game.scene.children) {
                  if (!o.position || o.visible === false || !(o.children?.length >= 3)) continue;
                  if (Math.hypot(o.position.x - game.p.x, o.position.z - game.p.z) < 0.4) continue;
                  const nearPath = Math.hypot(o.position.x - lay.depot.x, o.position.z - lay.depot.z) < 22
                    || Math.hypot(o.position.x - lay.open.x, o.position.z - lay.open.z) < 4;
                  if (nearPath) body = { x: o.position.x, z: o.position.z };
                }
                if (!body) continue;
                seen++;
                if (prev) {
                  const steps = Math.max(1, Math.ceil(Math.hypot(body.x - prev.x, body.z - prev.z) / 0.1));
                  for (let s = 0; s <= steps; s++) {
                    const t = s / steps, x = prev.x + (body.x - prev.x) * t, z = prev.z + (body.z - prev.z) * t;
                    if (inside(x, z)) crossed++;
                  }
                } else if (inside(body.x, body.z)) crossed++;
                prev = body;
              }
              const st = terraDefense.getState();
              const debug = {
                player: { x: +game.p.x.toFixed(1), z: +game.p.z.toFixed(1) },
                kids: game.scene.children.filter(o => (o.children?.length || 0) > 2).slice(0, 10).map(o => ({ n: o.children.length, x: +o.position.x.toFixed(1), z: +o.position.z.toFixed(1), vis: o.visible !== false }))
              };
              return {
                sim: +window.__sim.toFixed(2), seen, crossed, debug,
                warehouse: game.p.camp.res.a545,
                turrets: st.turrets.map(t => ({ mag: t.mag, state: t.state, prio: t.priority, x: +t.x.toFixed(1), z: +t.z.toFixed(1) })),
                task: st.porters[0]?.task || null,
                trips: st.summary.trips
              };
            }""", {'seconds': seconds, 'dt': dt})

        both = pump(8)
        report['both'] = both
        def at(turrets, spot):
            return next(t for t in turrets if abs(t['x'] - spot['x']) < 1.5 and abs(t['z'] - spot['z']) < 1.5)
        assert at(both['turrets'], boot['blockedAt'])['mag'] == 0, both
        assert at(both['turrets'], boot['openAt'])['mag'] == 60, both
        assert both['warehouse'] == 140, both
        assert both['crossed'] == 0, both
        assert both['seen'] > 0, both
        page.evaluate(r"""() => {
          const lay = window.__lay;
          game.cam.position.set(lay.mid.x, 14, lay.mid.z + 12);
          game.cam.lookAt(lay.mid.x, 1, lay.mid.z);
          game.ren.render(game.scene, game.cam);
        }""")
        page.screenshot(path=str(OUT / 'wall-not-crossed.png'))

        # Полный магазин открытой турели: восточная по-прежнему за стеной, списывать нечего.
        page.evaluate(r"""() => {
          const lay = window.__lay;
          const open = game.p.base.find(o => o.t === 'turretB' && Math.hypot(o.x - lay.open.x, o.z - lay.open.z) < 1);
          open.mag = 60;
          game.p.camp.res.a545 = 100;
          window.__sim = 0;
        }""")
        full = pump(3)
        report['full'] = full
        assert full['warehouse'] == 100, full
        assert at(full['turrets'], boot['openAt'])['mag'] == 60 and at(full['turrets'], boot['blockedAt'])['mag'] == 0, full
        assert full['trips'] == 0, full

        # Стена встаёт на уже открытом пути: начатый ход отменяется, склад цел.
        page.evaluate(r"""() => {
          for (const o of game.p.base) if (o.t === 'turretB') o.mag = 0;
          game.p.camp.res.a545 = 180;
          window.__sim = 0;
        }""")
        pump(1.2)
        mid = page.evaluate("""() => ({ warehouse: game.p.camp.res.a545, trips: terraDefense.getState().summary.trips, mag: terraDefense.getState().turrets.map(t => t.mag) })""")
        assert mid['trips'] == 1 and mid['warehouse'] == 180 and mid['mag'] == [0, 0], mid
        page.evaluate(r"""() => {
          const lay = window.__lay;
          const dx = lay.open.x - lay.depot.x, dz = lay.open.z - lay.depot.z, len = Math.hypot(dx, dz);
          const mx = lay.depot.x + dx / len * 10, mz = lay.depot.z + dz / len * 10;
          const px = -dz / len, pz = dx / len, alongX = Math.abs(px) >= Math.abs(pz);
          window.__seal = { x: mx, z: mz };
          for (let k = -6; k <= 6; k += 1.5) game.p.base.push({ t: 'wall', x: mx + px * k, z: mz + pz * k, r: alongX ? 0 : 1 });
          game.baseDirty = true; game.rebuildBase();
          window.__events.length = 0;
        }""")
        sealed = pump(2)
        report['sealed'] = {'mid': mid, 'after': sealed, 'events': page.evaluate('window.__events.slice(-6)')}
        assert sealed['warehouse'] == 180, sealed
        assert sealed['trips'] == 0, sealed
        assert any(e.get('reason') == 'obstacle' for e in report['sealed']['events']), report['sealed']['events']

        # Снос турели в пути. Поперечную стену убираем, северная турель снова доступна.
        page.evaluate(r"""() => {
          const seal = window.__seal;
          game.p.base = game.p.base.filter(o => !(o.t === 'wall' && Math.hypot(o.x - seal.x, o.z - seal.z) < 8));
          for (const o of game.p.base) if (o.t === 'turretB') o.mag = 0;
          game.p.camp.res.a545 = 160;
          game.baseDirty = true; game.rebuildBase();
          window.__sim = 0;
        }""")
        pump(1.2)
        page.evaluate("""() => { const lay = window.__lay; game.p.base = game.p.base.filter(o => !(o.t === 'turretB' && Math.hypot(o.x - lay.open.x, o.z - lay.open.z) < 1)); game.baseDirty = true; game.rebuildBase(); }""")
        gone = pump(1.2)
        report['dismantle'] = gone
        assert gone['warehouse'] == 160, gone
        assert all(t['mag'] == 0 for t in gone['turrets']), gone

        # Отмена назначения.
        page.evaluate(r"""() => {
          const lay = window.__lay;
          game.p.base.push({ t: 'turretB', dk: 'pkm', x: lay.open.x, z: lay.open.z, r: 0, mag: 0, dprio: 0 });
          game.p.camp.res.a545 = 150;
          game.baseDirty = true; game.rebuildBase();
          window.__sim = 0;
        }""")
        pump(1.2)
        cancel = page.evaluate("terraDefense.assign('qa-porter', false)")
        after_cancel = pump(1)
        report['cancel'] = {'api': cancel, 'after': after_cancel}
        assert cancel['ok'] is True and cancel['porter'] is False, cancel
        assert after_cancel['warehouse'] == 150, after_cancel
        assert after_cancel['task'] is None, after_cancel

        # Ранение и смена роли не снимают ход: это не баг пути. Доставка по открытому лучу доходит.
        page.evaluate(r"""() => {
          const s = game.p.camp.settlers['qa-porter'];
          s.order = Object.assign({}, s.order, { stick: true, job: 'haul' });
          const a = terraDefense.assign('qa-porter', true);
          if (!a.ok) throw Error(JSON.stringify(a));
          game.p.camp.res.a545 = 130;
          const lay = window.__lay;
          for (const o of game.p.base) if (o.t === 'turretB' && Math.hypot(o.x - lay.open.x, o.z - lay.open.z) < 1) o.mag = 0;
          window.__sim = 0;
        }""")
        pump(1.0)
        page.evaluate("""() => { const s = game.p.camp.settlers['qa-porter']; s.wounded = true; s.injuredUntil = (game.p.camp.sim?.tick || 0) + 5000; s.job = 'guard'; s.prof = 'guard'; }""")
        injured = pump(7)
        report['injury'] = injured
        assert injured['warehouse'] == 70, injured
        assert any(t['mag'] == 60 for t in injured['turrets']), injured
        assert page.evaluate("game.p.camp.settlers['qa-porter'].order.stick === true")

        # Смерть обрывает ход без списания.
        page.evaluate(r"""() => {
          const s = game.p.camp.settlers['qa-porter'];
          s.dead = false; s.wounded = false; s.injuredUntil = 0; s.job = 'idle'; s.prof = 'hauler';
          for (const o of game.p.base) if (o.t === 'turretB') o.mag = 0;
          game.p.camp.res.a545 = 90;
          window.__sim = 0;
        }""")
        pump(1.0)
        page.evaluate("""() => { game.p.camp.settlers['qa-porter'].dead = true; }""")
        dead = pump(2)
        report['dead'] = dead
        assert dead['warehouse'] == 90, dead
        assert dead['trips'] == 0, dead
        assert all(t['mag'] == 0 for t in dead['turrets']), dead

        # Сейв в пути: патроны ещё на складе, схема defense прежняя, после загрузки одна доставка.
        page.evaluate(r"""() => {
          const s = game.p.camp.settlers['qa-porter'];
          s.dead = false; s.wounded = false; s.job = 'idle'; s.prof = 'hauler';
          for (const o of game.p.base) if (o.t === 'turretB') o.mag = 0;
          game.p.camp.res.a545 = 80;
          window.__sim = 0;
        }""")
        pump(1.0)
        saved = page.evaluate(r"""() => {
          const r = game.save();
          const data = JSON.parse(localStorage.getItem('terra_save'));
          const turret = data.p.base.filter(o => o.t === 'turretB');
          return {
            save: r,
            a545: data.p.camp.res.a545,
            mags: turret.map(o => o.mag),
            defenseKeys: Object.keys(data.p.camp.defense).sort(),
            turretKeys: Object.keys(turret[0]).sort(),
            version: data.v
          };
        }""")
        report['saved'] = saved
        assert saved['save']['ok'] is True, saved
        assert saved['a545'] == 80 and saved['mags'] == [0, 0], saved
        assert saved['defenseKeys'] == ['porters', 'v'], saved
        assert 'trip' not in saved['defenseKeys']
        page.reload(timeout=120000)
        page.locator('#mContinue').click()
        page.wait_for_function('game.state==="play" && terraDefense.ready && game.p.camp.res.a545 === 80')
        page.evaluate(r"""() => {
          const orig = game.moduleUpdate.bind(game);
          game.loop = () => {};
          window.__sim = 0;
          game.moduleUpdate = function (dt) { window.__sim += dt; return orig(dt); };
          const h = game.homePos();
          const turrets = game.p.base.filter(o => o.t === 'turretB');
          window.__lay = { boxes: [], depot: { x: h.x, z: h.z }, open: turrets.find(o => (o.dprio | 0) === 0) || turrets[0], blocked: turrets.find(o => (o.dprio | 0) === 3) || turrets[0], mid: h };
          game.world.radius = 3;
          for (const dz of [-1, 0, 1]) for (const dx of [-1, 0, 1]) game.world.update(h.x + dx * 40, h.z + dz * 40, true);
        }""")
        continued = pump(8)
        report['continued'] = continued
        assert continued['warehouse'] == 20, continued
        assert sum(t['mag'] for t in continued['turrets']) == 60, continued
        cold = page.evaluate('game.p.camp.res.a545')
        page.evaluate('game.save()')
        page.reload(timeout=120000)
        page.locator('#mContinue').click()
        page.wait_for_function('game.state==="play" && game.p && game.p.camp')
        assert page.evaluate('game.p.camp.res.a545') == cold

        # Житель с работой и меткой подносчика: кнопки досье не наезжают.
        page.evaluate(r"""() => {
          const s = game.p.camp.settlers['qa-porter'];
          s.dead = false; s.job = 'haul';
          s.order = Object.assign({}, s.order, { job: 'haul', stick: true });
          game.ui.campPanel.open();
          game.ui.campPanel.select('settlers');
        }""")
        page.wait_for_timeout(300)
        page.locator('[data-resident="qa-porter"]').click()
        page.wait_for_timeout(200)
        overlap = page.evaluate(r"""() => {
          const nodes = [...document.querySelectorAll('#campBody button, #campBody .residentJobOption')];
          const rects = nodes.map(el => { const r = el.getBoundingClientRect(); return { t: (el.innerText || '').trim().slice(0, 40), x: r.x, y: r.y, w: r.width, h: r.height }; }).filter(r => r.w > 4 && r.h > 4 && r.t);
          const hits = [];
          for (let i = 0; i < rects.length; i++) for (let j = i + 1; j < rects.length; j++) {
            const a = rects[i], b = rects[j];
            if (a.t === b.t) continue;
            const ix = Math.min(a.x + a.w, b.x + b.w) - Math.max(a.x, b.x);
            const iy = Math.min(a.y + a.h, b.y + b.h) - Math.max(a.y, b.y);
            if (ix > 10 && iy > 10) hits.push([a.t, b.t]);
          }
          return { hits, porter: game.p.camp.defense.porters.includes('qa-porter'), job: game.p.camp.settlers['qa-porter'].job };
        }""")
        page.screenshot(path=str(OUT / 'resident-with-job.png'))
        report['ui'] = overlap
        assert overlap['hits'] == [] and overlap['porter'] is True and overlap['job'] == 'haul', overlap
        assert not errors, errors
        (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
        print('PASS porter obstacle: blocked mag 0, open delivered, no wall crossing, seal/dismantle/cancel/death keep stock, injury still delivers, save schema unchanged, UI clear')
        browser.close()


if __name__ == '__main__':
    main()
