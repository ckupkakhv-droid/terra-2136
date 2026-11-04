/* Повторяемый замер обороны: лагерь, 0/6/18 турелей, полный ночной рейд camp.raids (60).
 * Подключается из tests/turret-perf.py и из консоли телефона (удалённая отладка).
 * Сессию после замера не сохранять: скрипт двигает сюжет, рейд и здоровье только в памяти.
 */
(function () {
  'use strict';
  if (window.terraTurretPerf && window.terraTurretPerf._v === 1) return;

  const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
  const RAID_N = 60;

  function stats(values) {
    const s = values.filter((v) => Number.isFinite(v)).sort((a, b) => a - b);
    if (!s.length) return null;
    const sum = s.reduce((a, b) => a + b, 0);
    const at = (p) => s[Math.min(s.length - 1, Math.max(0, Math.ceil(p * s.length) - 1))];
    return { n: s.length, mean: sum / s.length, min: s[0], p50: at(0.5), p95: at(0.95), max: s[s.length - 1] };
  }

  function glInfo() {
    const game = window.game;
    const gl = game?.ren?.getContext?.();
    const ext = gl && gl.getExtension('WEBGL_debug_renderer_info');
    return {
      vendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : null,
      renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null,
      pixelRatio: game?.ren?.getPixelRatio?.() ?? null,
      buffer: gl ? [gl.drawingBufferWidth, gl.drawingBufferHeight] : null,
      qk: game?.qk ?? null,
      touch: 'ontouchstart' in window || matchMedia('(pointer:coarse)').matches,
      devicePixelRatio: window.devicePixelRatio,
      viewport: [window.innerWidth, window.innerHeight],
      state: game?.state ?? null,
      dayT: game?.dayT ?? null
    };
  }

  function installProbes() {
    const game = window.game;
    if (!game || game.__terraPerfProbed) return;
    game.__terraPerfProbed = true;
    window.TERRA_PERF = 1;
    game.__perfFrames = [];
    game.__perfOn = false;
    game.__perfHold = false;
    const loop = game.loop.bind(game);
    const mu = game.moduleUpdate.bind(game);
    game.moduleUpdate = function (dt) {
      const a = performance.now();
      performance.mark('terra-module-start');
      const r = mu(dt);
      performance.mark('terra-module-end');
      performance.measure('terra-module', 'terra-module-start', 'terra-module-end');
      game.__perfModuleMs = performance.now() - a;
      performance.clearMarks('terra-module-start');
      performance.clearMarks('terra-module-end');
      performance.clearMeasures('terra-module');
      return r;
    };
    game.loop = function (t) {
      if (game.__perfHold) holdWorld();
      const prev = game.last;
      performance.mark('terra-frame-start');
      const wall0 = performance.now();
      loop(t);
      const wall1 = performance.now();
      const rendered = game.last === t && game.last !== prev;
      if (rendered && game.__perfOn) {
        performance.mark('terra-frame-end');
        performance.measure('terra-frame', 'terra-frame-start', 'terra-frame-end');
        const info = game.ren?.info?.render || { calls: 0, triangles: 0 };
        const dbg = window.terraDefense?._debug?.() || {};
        game.__perfFrames.push({
          t,
          frameMs: game.__perfPrevT != null ? t - game.__perfPrevT : null,
          jsMs: wall1 - wall0,
          moduleMs: game.__perfModuleMs || 0,
          defenseMs: Number.isFinite(dbg.lastMs) ? dbg.lastMs : null,
          calls: info.calls,
          triangles: info.triangles,
          enemies: game.enemies?.length || 0,
          pool: dbg.pool || 0
        });
        game.__perfPrevT = t;
        performance.clearMarks('terra-frame-end');
        performance.clearMeasures('terra-frame');
      }
      performance.clearMarks('terra-frame-start');
    };
  }

  function holdWorld() {
    const game = window.game;
    const pin = game.__perfPin;
    if (!pin || !game.p) return;
    game.dayT = 22;
    game.p.x = pin.x;
    game.p.z = pin.z;
    game.p.hp = game.p.maxHp;
    const list = game.enemies || [];
    for (let i = 0; i < list.length; i++) {
      const e = list[i];
      if (e && e.__perf) { e.hp = 1e9; e.dead = false; }
    }
  }

  function clearEnemies() {
    const game = window.game;
    let guard = 0;
    while (game.enemies?.length && guard++ < 400) game.removeEnemy(game.enemies.length - 1);
  }

  async function waitFor(fn, ms, label) {
    const t0 = performance.now();
    let last;
    while (performance.now() - t0 < ms) {
      last = fn();
      if (last === true) return;
      await sleep(50);
    }
    throw new Error((label || 'timeout') + ': ' + JSON.stringify(last));
  }

  function place(count) {
    const game = window.game;
    const h = game.homePos();
    if (!h) throw new Error('нет homePos');
    game.story = Math.max(7, game.story | 0);
    game.p.peaceful = false;
    game.p.camp.peaceful = false;
    game.p.maxHp = Math.max(game.p.maxHp || 0, 1e6);
    game.p.hp = game.p.maxHp;
    const settlers = game.p.camp.settlers || (game.p.camp.settlers = {});
    if (!settlers['perf-bench'] && game.camp?.recruit) {
      try { game.camp.recruit({ id: 'perf-bench' }); } catch (e) { /* лагерь может отказать — рейд ниже всё равно активен */ }
    }
    const base = game.p.base;
    if (!Array.isArray(base)) throw new Error('нет p.base');
    for (let i = base.length - 1; i >= 0; i--) if (base[i] && base[i].t === 'turretB') base.splice(i, 1);
    const kinds = ['pkm', 'nail', 'flame'];
    for (let i = 0; i < count; i++) {
      const a = (i / Math.max(count, 1)) * Math.PI * 2;
      base.push({
        t: 'turretB', dk: kinds[i % 3], lvl: 1, mag: 800, hp: 120, r: 0,
        x: Math.round((h.x + Math.cos(a) * 5.2) * 100) / 100,
        z: Math.round((h.z + Math.sin(a) * 5.2) * 100) / 100
      });
    }
    game.baseDirty = true;
    clearEnemies();
    const units = [];
    for (let b = 0; b < RAID_N; b++) {
      const a = (b / RAID_N) * Math.PI * 2 + 0.17;
      const dist = b % 3 === 0 ? 8 : b % 3 === 1 ? 11 : 14;
      units.push({
        id: 'raid:perf:' + b,
        kind: b % 10 === 0 ? 'mutant' : b % 5 === 0 ? 'runner' : 'zombie',
        wave: 0, at: 0,
        x: h.x + Math.cos(a) * dist,
        z: h.z + Math.sin(a) * dist,
        hp: null, dead: false
      });
    }
    const raids = game.p.camp.raids || (game.p.camp.raids = { clock: 0, sequence: 0, next: null, active: null, last: null });
    raids.next = null;
    raids.active = {
      id: 9001, day: game.p.days || 1, interval: 180, size: RAID_N, strength: 80,
      target: { id: 'camp', x: h.x, z: h.z }, units, elapsed: 1, breach: 0
    };
    game.__perfPin = { x: h.x, z: h.z };
    game.__perfHold = true;
    game.p.x = h.x;
    game.p.z = h.z;
    game.dayT = 22;
    if (typeof game.updateRaidEnemies === 'function') game.updateRaidEnemies();
    const tagged = () => (game.enemies || []).filter((e) => e && e.raidId === 9001).length;
    if (tagged() < RAID_N) {
      for (let b = 0; b < units.length; b++) {
        const u = units[b];
        const exists = (game.enemies || []).some((e) => e && e.raidUnit === u.id);
        if (exists) continue;
        const e = game.spawnEnemy(u.kind === 'runner' ? 'zombie' : u.kind, u.x, u.z, { force: 1, aggro: 1, lvl: game.p.camp.tier || 1 });
        if (!e) continue;
        e.raidId = 9001;
        e.raidUnit = u.id;
        if (u.kind === 'runner' && e.def?.spd) e.spd = e.def.spd * 1.7;
      }
    }
    for (const e of game.enemies || []) {
      if (!e) continue;
      e.hp = 1e9;
      e.__perf = 1;
    }
    return h;
  }

  function setTrace(on) {
    const game = window.game;
    const ren = game.ren;
    if (!ren.__perfOrig) {
      ren.__perfOrig = ren.render.bind(ren);
      ren.render = function (scene, camera) {
        const t0 = ren.info.render.triangles;
        const c0 = ren.info.render.calls;
        const r = ren.__perfOrig(scene, camera);
        if (ren.__perfTrace) {
          ren.__perfPasses.push({
            tri: ren.info.render.triangles - t0,
            calls: ren.info.render.calls - c0,
            children: scene?.children?.length || 0
          });
        }
        return r;
      };
    }
    ren.__perfTrace = !!on;
    ren.__perfPasses = [];
  }

  async function sample(seconds, trace) {
    const game = window.game;
    game.__perfFrames = [];
    game.__perfPrevT = null;
    game.__perfOn = true;
    setTrace(!!trace);
    const shots0 = window.terraDefense?._debug?.().stats?.shots || 0;
    const t0 = performance.now();
    const budget = seconds * 1000;
    // На SwiftShader кадр может длиться секунду, а сим — не больше 50 мс.
    // Ждём хотя бы 6 обработанных кадров, иначе тик турели (0.25 с) не наступает.
    while (performance.now() - t0 < budget || (game.__perfFrames.length < 6 && performance.now() - t0 < budget * 3)) await sleep(100);
    game.__perfOn = false;
    const passes = trace ? (game.ren.__perfPasses || []).slice() : null;
    setTrace(false);
    const frames = game.__perfFrames.splice(0);
    const shots1 = window.terraDefense?._debug?.().stats?.shots || 0;
    const dbg = window.terraDefense?._debug?.() || {};
    const enemies = frames.map((f) => f.enemies);
    return {
      frames: frames.length,
      frameMs: stats(frames.map((f) => f.frameMs)),
      jsMs: stats(frames.map((f) => f.jsMs)),
      moduleMs: stats(frames.map((f) => f.moduleMs)),
      defenseMs: stats(frames.map((f) => f.defenseMs)),
      calls: stats(frames.map((f) => f.calls)),
      triangles: stats(frames.map((f) => f.triangles)),
      pool: stats(frames.map((f) => f.pool)),
      enemies: stats(enemies),
      enemyLast: game.enemies?.length || 0,
      raidAlive: (game.enemies || []).filter((e) => e && !e.dead && e.raidId === 9001).length,
      shots: shots1 - shots0,
      defenseEmaMs: dbg.ms ?? null,
      defenseMsMax: dbg.msMax ?? null,
      views: dbg.views ?? null,
      gl: glInfo(),
      passes: passes && passes.slice(0, 24)
    };
  }

  async function arm(count) {
    installProbes();
    place(count);
    await waitFor(() => {
      const d = window.terraDefense?._debug?.();
      if (!d) return { noDefense: true };
      if ((d.views || 0) !== count) return { views: d.views, want: count };
      const raid = (window.game.enemies || []).filter((e) => e && e.raidId === 9001).length;
      if (raid < RAID_N - 5) return { raid };
      return true;
    }, 20000, 'турели или рейд не встали');
  }

  async function run(opts) {
    opts = opts || {};
    const counts = opts.turrets || [0, 6, 18];
    const seconds = opts.seconds || 4;
    const warmup = opts.warmup ?? 1.5;
    const label = opts.label || '';
    if (!window.game || game.state !== 'play' || !game.p) throw new Error('нужна уже начатая игра (state=play)');
    installProbes();
    if (opts.pixelRatio) {
      game.ren.setPixelRatio(opts.pixelRatio);
      game.resize();
    }
    const out = [];
    for (const n of counts) {
      await arm(n);
      game.__perfOn = false;
      await sleep(warmup * 1000);
      const row = await sample(seconds, !!opts.trace);
      row.turrets = n;
      row.label = label;
      row.raidSize = game.p?.camp?.raids?.active?.size ?? null;
      row.okShots = n === 0 ? row.shots === 0 : row.shots > 0;
      out.push(row);
    }
    return { label, gl: glInfo(), rows: out };
  }

  window.terraTurretPerf = { _v: 1, run, arm, sample, glInfo, installProbes, RAID_N };
})();
