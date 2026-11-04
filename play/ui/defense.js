/* [defense] Оборона лагеря, этап 1: турели с магазином, подносчики, порох/гвозди/газ.
 * Подключается к бандлу через window.TERRA_DEFENSE_CTX/HOOK (scripts/apply-defense-hook.py).
 * Сейв: турели остаются записями p.base с t:"turretB"; новые необязательные поля
 * dk (вид), lvl, mag, dprio. Блок p.camp.defense {v:1, porters:[]}. Без полей — значения по умолчанию.
 * Блок с v>1 (более новая версия) не читается и не переписывается: модуль замирает.
 */
(() => {
  'use strict';
  const ASSET = new URL('../assets/defense/', document.currentScript?.src || location.href).href;
  const TIER_LIMIT = [4, 7, 10, 14, 18];          // Стоянка · Лагерь · Форпост · Посёлок · Город
  const TICK = 0.25;                               // как у родной обороны
  const POOL = { low: 48, med: 96, high: 160 };    // снаряды обороны в отдельном пуле
  const FLAME_PARTS = { low: 2, med: 4, high: 6 }; // частиц огнемёта за тик на турель
  const FAR = 70;                                  // дальше — модель скрыта, турель стреляет без эффектов
  const SUPPLY_R = 90;                             // подносчики обслуживают турели в 90 м от склада
  const BACKPACK_R = 30;                           // пустая турель берёт из рюкзака героя рядом (как раньше)
  const TYPES = {
    pkm: {
      key: 'turretB', name: 'Спарка ПКМ', short: 'ПКМ', model: 'turret-pkm.glb', ammo: 'a545', lvlReq: 3,
      cost: null, // родная стоимость turretB
      range: [13, 15, 17], cd: [0.6, 0.5, 0.42], dmg: [18, 21, 25], mag: [60, 90, 120], carry: 60,
      proj: 'tracer', speed: 70, scale: 0.68, muzzle: [0, 1.75, 1.95],
      up: [null, { scrap: 10, chem: 4 }, { scrap: 18, chem: 8, cloth: 2 }],
      about: 'Пулемётная спарка. Ровный урон по одиночным целям, 5.45 со склада.'
    },
    nail: {
      key: 'dNail', name: 'Гвоздомёт', short: 'Гвозди', model: 'turret-nail.glb', ammo: 'nails', lvlReq: 3,
      cost: { scrap: 16, wood: 8 },
      range: [10, 11, 12], cd: [0.35, 0.3, 0.26], dmg: [9, 11, 13], mag: [40, 60, 80], carry: 40, slow: 0.7,
      proj: 'nail', speed: 38, scale: 0.7, muzzle: [0, 1.35, 2.0],
      up: [null, { scrap: 8, wood: 6 }, { scrap: 14, wood: 8, chem: 2 }],
      about: 'Пневматика на гвоздях: дешёвый боеприпас, замедляет цель.'
    },
    flame: {
      key: 'dFlame', name: 'Огнемёт «Пропан»', short: 'Газ', model: 'turret-flame.glb', ammo: 'gas', lvlReq: 5,
      cost: { scrap: 18, chem: 10 },
      range: [6, 6.5, 7], cd: [0.25, 0.25, 0.25], dmg: [8, 10, 12], mag: [6, 8, 10], carry: 3, burn: 1 / 16, cone: 0.62,
      proj: 'flame', scale: 0.62, muzzle: [0, 1.15, 1.0],
      up: [null, { scrap: 10, chem: 6 }, { scrap: 16, chem: 10, cell: 1 }],
      about: 'Конус огня по группе. 1 баллон газа — 4 секунды огня.'
    }
  };
  const BY_KEY = Object.fromEntries(Object.entries(TYPES).map(([dk, t]) => [t.key, dk]));
  const ITEMS = {
    powder: { name: 'Порох', icon: '⚫', cat: 'res' },
    nails: { name: 'Гвозди', icon: '📌', cat: 'ammo' },
    gas: { name: 'Газ (баллон)', icon: '🧯', cat: 'ammo' }
  };
  const RECIPES = [
    { id: 'powder', out: { powder: 3 }, need: { chem: 1, wood: 1 }, name: 'Порох ×3' },
    { id: 'a545p', out: { a545: 30 }, need: { scrap: 2, powder: 2 }, name: '5.45 ×30 (на порохе)' },
    { id: 'nails', out: { nails: 30 }, need: { scrap: 2 }, name: 'Гвозди ×30' },
    { id: 'gas', out: { gas: 2 }, need: { chem: 2, scrap: 1 }, name: 'Газ ×2 баллона' }
  ];

  let ctx = null, game = null, booted = false;
  const S = { player: null, views: new Map(), tmpl: {}, inst: {}, crate: null, pool: null, trips: new Map(), acc: 0, supplyAcc: 0,
    lastEmit: 0, dirty: true, stats: { shots: 0, refills: 0, delivered: 0 }, hiddenViews: new Set() };

  const num = (v, d) => (Number.isFinite(v) ? v : d);
  const clampLvl = (v) => Math.max(1, Math.min(3, num(v, 1) | 0));
  const dkOf = (o) => (TYPES[o?.dk] ? o.dk : 'pkm');
  const isTurret = (o) => o && o.t === 'turretB';
  const turrets = () => (game?.p?.base || []).filter(isTurret);
  const idOf = (o) => (game.defenseId ? game.defenseId(o) : o.x + ',' + o.z + ',1');
  const tierOf = () => Math.max(1, Math.min(5, num(game?.p?.camp?.tier, 1) | 0));
  const limit = () => TIER_LIMIT[tierOf() - 1];
  const isTech = () => game?.p?.classProfile?.classId === 'technician';
  const qkey = () => (POOL[game?.qk] ? game.qk : 'med');
  const magMax = (o) => Math.round(TYPES[dkOf(o)].mag[clampLvl(o.lvl) - 1] * (isTech() ? 1.25 : 1));
  const magOf = (o) => Math.max(0, num(o.mag, 0));
  const dmgOf = (o) => TYPES[dkOf(o)].dmg[clampLvl(o.lvl) - 1] * (isTech() ? 1.1 : 1);
  // Башни не сканируются заново на каждую турель: список обновляется вместе с базой.
  function cacheTowers() {
    const B = ctx.B.defense;
    const list = [];
    const base = game.p?.base || [];
    for (let i = 0; i < base.length; i++) if (ctx.Li[base[i].t]?.tower) list.push(base[i]);
    S.towers = list;
    S.towerRad = B?.towerRadius || 0;
    S.towerBonusV = B?.towerBonus || 0;
  }
  const towerBonus = (o) => {
    if (!S.towers) cacheTowers();
    const rad = S.towerRad;
    if (!rad) return 0;
    for (let i = 0; i < S.towers.length; i++) {
      const h = S.towers[i];
      if (Math.hypot(h.x - o.x, h.z - o.z) < rad) return S.towerBonusV;
    }
    return 0;
  };
  const rangeOf = (o) => TYPES[dkOf(o)].range[clampLvl(o.lvl) - 1] + towerBonus(o);
  const campRes = () => (game.p.camp && (game.p.camp.res = game.p.camp.res || {}));
  const depot = () => {
    const w = Object.values(game.p.camp?.buildings || {}).find((b) => b?.type === 'warehouse' && b.lvl > 0 && b.hp > 0 && b.placement);
    if (w) return { x: w.placement.x, z: w.placement.z, warehouse: true };
    const h = game.homePos?.();
    return h ? { x: h.x, z: h.z, warehouse: false } : null;
  };
  // сейв с блоком camp.defense новее v1: модуль замирает и ничего не пишет ни в блок, ни в турели,
  // поэтому сохранение из этой сборки не портит данные более новой (проверка без правки валидатора бандла)
  const isFuture = () => Number(game?.p?.camp?.defense?.v) > 1;
  const dstate = () => {
    const c = game.p.camp;
    if (!c) return { v: 1, porters: [] };
    if (!c.defense || typeof c.defense !== 'object') c.defense = { v: 1, porters: [] };
    if (isFuture()) return { v: c.defense.v, porters: [] }; // блок из более новой версии не трогаем
    if (!Array.isArray(c.defense.porters)) c.defense.porters = [];
    c.defense.v = 1;
    return c.defense;
  };
  const settler = (id) => game.p.camp?.settlers?.[id];
  const available = (s) => s && (ctx.Q ? ctx.Q(s) : !s.dead && !s.captive && !s.mission);
  const ammoName = (k) => ctx.Yt[k]?.name || k;

  function emit(reason, extra) {
    S.lastEmit = performance.now();
    try { window.dispatchEvent(new CustomEvent('terra:defense-change', { detail: { reason, ...extra } })); } catch {}
  }

  /* ---------- данные ---------- */
  function installData() {
    const { Li, Yt, uu, B } = ctx;
    for (const [k, v] of Object.entries(ITEMS)) if (!Yt[k]) Yt[k] = v;
    if (Array.isArray(uu)) for (const r of RECIPES) if (!uu.some((x) => x.id === r.id)) uu.push(r);
    const base = Li.turretB;
    if (!base) return false;
    if (!base.baseCost) base.baseCost = { ...base.cost };
    base.n = TYPES.pkm.name;
    base.dk = 'pkm';
    base.turret = 0; // родной тик больше не стреляет: огонь и магазин ведёт этот модуль
    for (const [dk, t] of Object.entries(TYPES)) {
      if (t.key === 'turretB') continue;
      if (!Li[t.key]) Li[t.key] = { ...base, n: t.name, cost: t.cost, lvl: t.lvlReq, as: 'turretB', dk };
    }
    if (B.defense?.hp && !B.defense.hp.turretB) B.defense.hp.turretB = 120;
    // снос: родной код возвращает долю B.refund от A.refundOf(запись) || A.cost
    base.refundOf = (o) => paidCost(o);
    return true;
  }
  // всё, что вложено в турель: цена её вида + улучшения до текущего уровня
  function paidCost(o) {
    const t = TYPES[dkOf(o)] || TYPES.pkm, out = {};
    const add = (c) => { for (const [k, v] of Object.entries(c || {})) out[k] = (out[k] || 0) + v; };
    add(t.cost || ctx.Li.turretB.baseCost);
    for (let i = 1; i < clampLvl(o?.lvl); i++) add(t.up[i]);
    return out;
  }

  /* ---------- модели ---------- */
  function loadModels() {
    if (S.loading) return;
    S.loading = true;
    const loader = new ctx.G();
    ctx.M && loader.setMeshoptDecoder(ctx.M);
    const load = (file) => new Promise((res) => loader.load(ASSET + file, (g) => res(g.scene), undefined, () => res(null)));
    // материалы как у построек лагеря (Lambert): дешевле на телефоне и без пересвета от окружения
    const matte = (sc) => {
      if (!sc || !ctx.L) return sc;
      const cache = new Map();
      sc.traverse((m) => {
        if (!m.isMesh) return;
        const src = m.material;
        if (!cache.has(src)) cache.set(src, new ctx.L({ color: src.color, map: src.map || null }));
        m.material = cache.get(src);
      });
      return sc;
    };
    Promise.all([...Object.entries(TYPES).map(([dk, t]) => load(t.model).then((sc) => { S.tmpl[dk] = matte(sc); })),
      load('ammo-crate.glb').then((sc) => { S.crate = sc; })]).then(() => { S.dirty = true; if (game) game.baseDirty = true; });
  }
  /* Турели рисуются InstancedMesh-ами: по одному на (вид, деталь, материал). 18 турелей трёх видов —
   * не больше 18 вызовов отрисовки вместо ~6 на каждую турель. */
  function buildInst(dk, cap) {
    const old = S.inst[dk];
    if (old) for (const pt of old.parts) { pt.im.removeFromParent(); pt.im.dispose?.(); }
    const src = S.tmpl[dk];
    if (!src) return null;
    src.updateMatrixWorld(true);
    const parts = [];
    src.traverse((m) => {
      if (!m.isMesh) return;
      let gun = false;
      for (let a = m; a; a = a.parent) if (a.name === 'gun') gun = true;
      const im = new ctx.I(m.geometry, m.material, cap);
      // Тень стволов на среднем и низком (телефон) не отбрасываем: в карту теней не кладём
      // ~2 тыс. треугольников на турель. На высоком качестве — как раньше, все части.
      im.count = 0; im.frustumCulled = false; im.castShadow = false; im.receiveShadow = true; im.name = 'defense-' + dk;
      game.scene.add(im);
      parts.push({ im, local: m.matrixWorld.clone(), gun });
    });
    return (S.inst[dk] = { parts, cap, n: 0 });
  }
  const M1 = () => S.m1 || (S.m1 = new ctx.D());
  const M2 = () => S.m2 || (S.m2 = new ctx.D());
  function applyCastShadows() {
    const high = game.qk === 'high';
    if (S.shadowHigh === high) return;
    S.shadowHigh = high;
    for (const I of Object.values(S.inst)) for (const pt of I.parts) pt.im.castShadow = high;
  }
  function writeInst(v, gunsOnly) {
    const I = S.inst[v.dk];
    if (!I || v.slot == null) return;
    const t = TYPES[v.dk], sc = t.scale * (1 + 0.06 * (v.lvl - 1));
    const lift = I.parts[0]?.im.matrixWorld.elements[13] - (I.parts[0]?.im.position.y || 0) || 0;
    const y = (ctx.Y ? ctx.Y(v.o.x, v.o.z) : 0) - lift;
    const a = M1(), b = M2();
    for (const pt of I.parts) {
      // Основание и «mid» не крутятся за целью: их матрица пишется при сборке и при смене высоты земли.
      if (gunsOnly && !pt.gun) continue;
      const yaw = pt.gun ? v.gunYaw : v.baseYaw;
      a.makeRotationY(yaw);
      if (pt.gun && v.kick > 0) { b.makeTranslation(0, 0, -0.18 * v.kick); a.multiply(b); }
      b.makeScale(sc, sc, sc); a.premultiply(b);
      // порядок: T · S · R · (kick) · local
      a.elements[12] = v.o.x; a.elements[13] = y; a.elements[14] = v.o.z;
      a.multiply(pt.local);
      pt.im.setMatrixAt(v.slot, a);
      pt.im.instanceMatrix.needsUpdate = true;
    }
  }
  function dropView() {}
  function syncViews() {
    const list = turrets(), byDk = {};
    for (const o of list) (byDk[dkOf(o)] = byDk[dkOf(o)] || []).push(o);
    const next = new Map();
    for (const dk of Object.keys(TYPES)) {
      const arr = byDk[dk] || [];
      let I = S.inst[dk];
      if (S.tmpl[dk] && (!I || I.cap < arr.length)) I = buildInst(dk, Math.max(TIER_LIMIT[4], arr.length + 4));
      if (!I) continue;
      arr.forEach((o, slot) => {
        const id = idOf(o), prev = S.views.get(id);
        const baseYaw = ((o.r || 0) * Math.PI) / 2;
        const v = { o, dk, lvl: clampLvl(o.lvl), slot, baseYaw, yaw: prev?.yaw ?? baseYaw, gunYaw: prev?.gunYaw ?? baseYaw, kick: 0 };
        next.set(id, v);
        writeInst(v);
      });
      I.n = arr.length;
      for (const pt of I.parts) pt.im.count = arr.length;
    }
    S.views = next;
    S.dirty = false;
    S.shadowHigh = undefined;
    applyCastShadows();
  }
  function patchGeo() {
    if (game._defenseGeo) return;
    const orig = game.geoOf;
    game._defenseGeo = orig;
    game.geoOf = function (e, t, i, n) {
      // турель рисует GLB-модель модуля; в общем меше остаётся только полоса прочности
      if (e === 'turretB' && S.tmpl[dkOf(t)] && !S.future) return;
      return orig.call(this, ctx.Li[e]?.as || e, t, i, n);
    };
  }
  function patchPlace() {
    if (game._defensePlace) return;
    const orig = game.validPlace;
    game._defensePlace = orig;
    game.validPlace = function (e, x, z) {
      const L = ctx.Li[e];
      if (L && (e === 'turretB' || L.as === 'turretB') && !this.build?.demo) {
        const used = (this.p?.base || []).filter(isTurret).length, max = TIER_LIMIT[Math.max(1, Math.min(5, num(this.p?.camp?.tier, 1) | 0)) - 1];
        if (used >= max) return 'Лимит турелей ' + used + '/' + max + ' · поднимите уровень лагеря';
      }
      return orig.call(this, e, x, z);
    };
  }

  /* ---------- пул снарядов обороны ---------- */
  function makePool() {
    const n = POOL[qkey()];
    const Box = game.ghostM?.geometry?.constructor, Basic = game.ghostMat?.constructor;
    if (!Box || !Basic || !ctx.I) return null;
    const mesh = new ctx.I(new Box(1, 1, 1), new Basic({ color: 0xffd27a, toneMapped: false }), n);
    mesh.count = 0; mesh.frustumCulled = false; mesh.name = 'defenseProjectiles';
    const col = new ctx.C();
    for (let i = 0; i < n; i++) mesh.setColorAt(i, col.set(0xffd27a));
    game.scene.add(mesh);
    return { mesh, n, list: [], m: new ctx.D(), v: new ctx.V(), up: new ctx.V(0, 1, 0), col };
  }
  function fireProjectile(kind, from, target, dmg, slow) {
    const P = S.pool;
    if (!P) { game.hurtEnemy(target, dmg, { wt: 'turret' }); return; }
    if (P.list.length >= P.n) P.list.shift();
    const dx = target.x - from.x, dz = target.z - from.z, dy = 1.1 - from.y, d = Math.hypot(dx, dy, dz) || 1;
    const sp = kind === 'nail' ? TYPES.nail.speed : TYPES.pkm.speed;
    P.list.push({ kind, x: from.x, y: from.y, z: from.z, vx: (dx / d) * sp, vy: (dy / d) * sp, vz: (dz / d) * sp, t: d / sp, target, dmg, slow });
  }
  function updatePool(dt) {
    const P = S.pool;
    if (!P) return;
    const { mesh, m, list } = P;
    // y снарядов хранится относительно земли; пул стоит в начале координат, поэтому
    // переводим в абсолютную высоту и вычитаем подъём, который сцена дала самому пулу
    const lift = mesh.matrixWorld.elements[13] - mesh.position.y;
    let w = 0;
    for (let i = 0; i < list.length; i++) {
      const b = list[i];
      b.t -= dt;
      if (b.t <= 0) {
        const e = b.target;
        if (e && !e.dead) {
          game.hurtEnemy(e, b.dmg, { wt: 'turret' });
          if (b.slow) e.slow = [b.slow, 0.6];
        }
        continue;
      }
      b.x += b.vx * dt; b.y += b.vy * dt; b.z += b.vz * dt;
      list[w++] = b;
    }
    list.length = w;
    const kinds = P.kinds || (P.kinds = []);
    for (let i = 0; i < w; i++) {
      const b = list[i], len = b.kind === 'nail' ? 0.35 : 1.1, th = b.kind === 'nail' ? 0.05 : 0.04;
      const yaw = Math.atan2(b.vx, b.vz);
      m.makeRotationY(yaw);
      m.scale(P.v.set(th, th, len));
      m.setPosition(b.x, b.y + (ctx.Y ? ctx.Y(b.x, b.z) : 0) - lift, b.z);
      mesh.setMatrixAt(i, m);
      if (kinds[i] !== b.kind) {
        kinds[i] = b.kind;
        mesh.setColorAt(i, P.col.set(b.kind === 'nail' ? 0xb8b8b0 : 0xffd27a));
        P.colorDirty = true;
      }
    }
    mesh.count = w;
    mesh.instanceMatrix.needsUpdate = w > 0;
    if (P.colorDirty && mesh.instanceColor) { mesh.instanceColor.needsUpdate = true; P.colorDirty = false; }
  }

  /* ---------- цели: одна сетка на тик, тот же «ближайший», что nearestEnemy ---------- */
  const CELL = 4;
  function rebuildEnemyGrid() {
    const enemies = game.enemies || [];
    const g = new Map();
    for (let i = 0; i < enemies.length; i++) {
      const e = enemies[i];
      if (!e || e.dead || !Number.isFinite(e.x) || !Number.isFinite(e.z)) continue;
      const k = Math.floor(e.x / CELL) + ',' + Math.floor(e.z / CELL);
      let b = g.get(k);
      if (!b) g.set(k, (b = []));
      b.push(e, i);
    }
    S.grid = g;
  }
  function gridNearest(x, z, R) {
    const g = S.grid;
    if (!g) return game.nearestEnemy(x, z, R);
    let best = null, bestD = R, bestI = 1e9;
    const reach = Math.ceil(R / CELL);
    const c0 = Math.floor(x / CELL), c1 = Math.floor(z / CELL);
    for (let ix = c0 - reach; ix <= c0 + reach; ix++) {
      for (let iz = c1 - reach; iz <= c1 + reach; iz++) {
        const b = g.get(ix + ',' + iz);
        if (!b) continue;
        for (let n = 0; n < b.length; n += 2) {
          const e = b[n];
          if (e.dead) continue;
          const a = Math.hypot(e.x - x, e.z - z);
          const idx = b[n + 1];
          if (a < bestD || (best && a === bestD && idx < bestI)) { bestD = a; best = e; bestI = idx; }
        }
      }
    }
    return best;
  }
  function pickEnemy(x, z, R) {
    const e = gridNearest(x, z, R);
    S.searches = (S.searches || 0) + 1;
    if (window.TERRA_PERF_AUDIT) {
      const exact = game.nearestEnemy(x, z, R);
      if (exact !== e) S.mismatch = (S.mismatch || 0) + 1;
    }
    return e;
  }
  // Прямая пустая по клеткам мира — тот же ответ, что segHit === -1, без шага 0.35 м.
  function losBlocked(x, z, ex, ez) {
    const w = game.world;
    if (!w?.segHit) return false;
    const h = 2.7;
    if (typeof w.query === 'function') {
      const any = w.query(Math.min(x, ex), Math.min(z, ez), Math.max(x, ex), Math.max(z, ez), (s) => s.h >= h);
      if (!any) { S.losFast = (S.losFast || 0) + 1; return false; }
    }
    S.losFull = (S.losFull || 0) + 1;
    return w.segHit(x, z, ex, ez, h) >= 0;
  }
  function eachEnemyIn(x, z, R, fn) {
    const g = S.grid;
    if (!g) {
      for (const en of game.enemies || []) {
        if (!en || en.dead) continue;
        const dx = en.x - x, dz = en.z - z, d = Math.hypot(dx, dz);
        if (d <= R && d >= 0.01) fn(en, dx, dz, d);
      }
      return;
    }
    const reach = Math.ceil(R / CELL);
    const c0 = Math.floor(x / CELL), c1 = Math.floor(z / CELL);
    for (let ix = c0 - reach; ix <= c0 + reach; ix++) {
      for (let iz = c1 - reach; iz <= c1 + reach; iz++) {
        const b = g.get(ix + ',' + iz);
        if (!b) continue;
        for (let n = 0; n < b.length; n += 2) {
          const en = b[n];
          if (en.dead) continue;
          const dx = en.x - x, dz = en.z - z, d = Math.hypot(dx, dz);
          if (d <= R && d >= 0.01) fn(en, dx, dz, d);
        }
      }
    }
  }

  /* ---------- стрельба ---------- */
  function takeAmmo(o, need) {
    // 1) магазин; 2) пустой магазин и герой рядом — из рюкзака (поведение до обновления)
    const t = TYPES[dkOf(o)];
    if (magOf(o) >= need - 1e-6) { o.mag = +(magOf(o) - need).toFixed(4); return true; }
    const p = game.p;
    if (Math.hypot(p.x - o.x, p.z - o.z) <= BACKPACK_R && (p.inv[t.ammo] || 0) >= 1) {
      p.inv[t.ammo] -= 1;
      o.mag = +(magOf(o) + (t.proj === 'flame' ? 1 : 1) - need).toFixed(4);
      return true;
    }
    return false;
  }
  const RT = new WeakMap(); // кулдаун и состояние — только в памяти, в сейв не попадают
  const rt = (o) => { let r = RT.get(o); if (!r) RT.set(o, (r = { cd: 0 })); return r; };
  function tickTurret(o, v) {
    const dk = dkOf(o), t = TYPES[dk], lv = clampLvl(o.lvl), r = rt(o);
    r.cd -= TICK;
    if (r.cd > 0) return;
    if (o.hp != null && o.hp <= 0) return;
    const R = rangeOf(o);
    const e = pickEnemy(o.x, o.z, R);
    if (!e) return;
    if (losBlocked(o.x, o.z, e.x, e.z)) return;
    const need = t.proj === 'flame' ? t.burn : 1;
    if (!takeAmmo(o, need)) return;
    r.cd = t.cd[lv - 1];
    S.stats.shots++;
    const near = Math.hypot(game.p.x - o.x, game.p.z - o.z) < FAR;
    const yaw = Math.atan2(e.x - o.x, e.z - o.z);
    if (v) { v.yaw = yaw; v.kick = 1; v.fresh = true; }
    const s = t.scale, c = Math.cos(yaw), sn = Math.sin(yaw);
    const mz = t.muzzle[2] * s, from = { x: o.x + sn * mz, y: t.muzzle[1] * s, z: o.z + c * mz };
    if (t.proj === 'flame') {
      const dmg = dmgOf(o);
      eachEnemyIn(o.x, o.z, R, (en, dx, dz, d) => {
        const a = Math.acos(Math.max(-1, Math.min(1, (dx * sn + dz * c) / d)));
        if (a <= t.cone) game.hurtEnemy(en, dmg, { wt: 'turret', dot: true });
      });
      if (near && game.pA) {
        const k = FLAME_PARTS[qkey()];
        for (let i = 0; i < k; i++) {
          const sp = 9 + Math.random() * 6, j = (Math.random() - 0.5) * t.cone * 1.2;
          game.pA.spawn(from.x, from.y, from.z, Math.sin(yaw + j) * sp, 0.6 + Math.random(), Math.cos(yaw + j) * sp, 0.45, 0.55, 1, 0.45 + Math.random() * 0.3, 0.12, 0);
        }
      }
    } else {
      fireProjectile(t.proj, from, e, dmgOf(o), t.slow);
      if (near && game.pA) game.pA.spawn(from.x, from.y, from.z, 0, 0.5, 0, 0.12, 0.35, 1, 0.8, 0.4, 0);
    }
    if (near) try { game.sfx?.modShot?.(dk === 'pkm' ? 'camp' : 'turret', from); } catch {}
  }
  function animateViews(dt) {
    const hide = !!game.world?.inDungeon;
    if (hide !== S.hidden) {
      S.hidden = hide;
      for (const I of Object.values(S.inst)) for (const pt of I.parts) pt.im.visible = !hide;
    }
    if (hide) return;
    const p = game.p;
    for (const v of S.views.values()) {
      if (Math.hypot(p.x - v.o.x, p.z - v.o.z) > FAR) { v.groundY = null; continue; }
      const y = ctx.Y ? ctx.Y(v.o.x, v.o.z) : 0;
      const yMoved = v.groundY == null || Math.abs(v.groundY - y) > 0.01;
      if (yMoved) v.groundY = y;
      const d = ((v.yaw - v.gunYaw + Math.PI * 3) % (Math.PI * 2)) - Math.PI;
      const spin = Math.abs(d) >= 1e-3 || v.kick > 0 || v.fresh;
      if (!spin && !yMoved) continue;
      if (spin) {
        v.gunYaw += d * Math.min(1, dt * 10);
        v.kick = Math.max(0, v.kick - dt * 8);
        v.fresh = false;
      }
      writeInst(v, !yMoved);
    }
  }

  /* ---------- подносчики ---------- */
  function porterIds() { return dstate().porters.filter((id) => settler(id)); }
  function needFor(o) { return magMax(o) - magOf(o); }
  function planTrips() {
    const dp = depot();
    if (!dp) return;
    const res = campRes();
    const busy = new Set([...S.trips.values()].map((t) => t.turret));
    const list = turrets().filter((o) => !busy.has(idOf(o)) && Math.hypot(o.x - dp.x, o.z - dp.z) <= SUPPLY_R && needFor(o) >= Math.max(1, magMax(o) * 0.35) && (res[TYPES[dkOf(o)].ammo] || 0) >= 1)
      .sort((a, b) => num(b.dprio, 0) - num(a.dprio, 0) || magOf(a) / magMax(a) - magOf(b) / magMax(b));
    for (const id of porterIds()) {
      if (S.trips.has(id) || !list.length) continue;
      const s = settler(id);
      if (!available(s)) continue;
      const o = list.shift();
      const sk = num(s.skills?.haul, 0), speed = (ctx.B.camp?.movement?.speed || 3.2) * (1 + sk * 0.06);
      const t = TYPES[dkOf(o)];
      S.trips.set(id, { id, turret: idOf(o), o, from: dp, to: { x: o.x, z: o.z }, phase: 'go', k: 0, speed, carry: Math.round(t.carry * (1 + sk * 0.1)), ammo: t.ammo, view: null });
      emit('porter-start', { settlerId: id, turretId: idOf(o) });
    }
  }
  function porterView(trip) {
    if (trip.view !== null || !game.npcMesh) return trip.view;
    const s = settler(trip.id);
    let v = null;
    try { v = game.npcMesh({ name: s.name, prof: s.prof, model: ctx.R ? ctx.R(s.prof) : 's_scout', tint: s.tint }); } catch { v = null; }
    if (v && S.crate) { const c = S.crate.clone(true); c.scale.setScalar(0.42); c.position.set(0, 1.05, 0.38); v.root.add(c); v._crate = c; }
    if (v) try { ctx.K?.play?.(v, 'walk', 0.15); } catch {}
    trip.view = v || false;
    return trip.view;
  }
  function endTrip(trip) {
    const v = trip.view;
    if (v) { v.root.removeFromParent(); try { v.src?.release?.(v); } catch {} }
    const nv = game.npcV?.[trip.id];
    if (nv?.root) nv.root.visible = true;
    S.trips.delete(trip.id);
  }
  function updateTrips(dt) {
    for (const trip of [...S.trips.values()]) {
      const s = settler(trip.id);
      const o = turrets().find((x) => idOf(x) === trip.turret);
      if (!available(s) || !o || !dstate().porters.includes(trip.id)) { endTrip(trip); emit('porter-cancel', { settlerId: trip.id }); continue; }
      const a = trip.phase === 'go' ? trip.from : trip.to, b = trip.phase === 'go' ? trip.to : trip.from;
      const len = Math.max(0.5, Math.hypot(b.x - a.x, b.z - a.z));
      trip.k = Math.min(1, trip.k + (trip.speed * dt) / len);
      const x = a.x + (b.x - a.x) * trip.k, z = a.z + (b.z - a.z) * trip.k;
      const near = Math.hypot(game.p.x - x, game.p.z - z) < 60 && !game.world.inDungeon;
      const v = near ? porterView(trip) : trip.view;
      if (v) {
        v.root.visible = near;
        v.root.position.set(x, 0, z);
        v.root.rotation.y = Math.atan2(b.x - a.x, b.z - a.z);
        if (v._crate) v._crate.visible = trip.phase === 'go';
        try { v.mixer?.update(dt); } catch {}
        const nv = game.npcV?.[trip.id];
        if (nv?.root && nv !== v) { nv.root.visible = false; }
      }
      if (trip.k < 1) continue;
      if (trip.phase === 'go') {
        // патроны списываются со склада в момент доставки: при сохранении в пути ничего не теряется
        const res = campRes(), have = Math.floor(res[trip.ammo] || 0);
        const put = Math.min(have, trip.carry, Math.ceil(needFor(o)));
        if (put > 0) {
          res[trip.ammo] -= put; // склад и магазин меняются одним шагом: любая запись видит либо оба, либо ни одного
          o.mag = Math.min(magMax(o), magOf(o) + put);
          S.stats.refills++; S.stats.delivered += put;
          emit('refill', { turretId: trip.turret, settlerId: trip.id, amount: put, ammo: trip.ammo });
        }
        trip.phase = 'back'; trip.k = 0;
      } else { endTrip(trip); emit('porter-done', { settlerId: trip.id }); }
    }
  }

  /* ---------- главный тик ---------- */
  function onSession() {
    if (game.p === S.player) return;
    S.views.clear();
    for (const I of Object.values(S.inst)) for (const pt of I.parts) pt.im.count = 0;
    for (const t of [...S.trips.values()]) endTrip(t);
    S.player = game.p; S.dirty = true; S.lastError = null;
    emit('session');
  }
  function setFuture(on) {
    S.future = on;
    S.player = null; S.dirty = true; game.baseDirty = true;
    for (const I of Object.values(S.inst)) for (const pt of I.parts) pt.im.count = 0;
    for (const t of [...S.trips.values()]) endTrip(t);
    if (S.pool) { S.pool.list.length = 0; S.pool.mesh.count = 0; }
    if (on) { console.warn('[defense] сейв из более новой версии обороны (camp.defense.v=' + game.p.camp.defense.v + '): модуль отключён'); game.ui?.toast?.('Оборона: сейв из более новой версии — турели отключены, данные не меняются', '#ffb84a'); }
    emit('future');
  }
  function update(dt) {
    if (!ctx || !game.p || !game.scene) return;
    if (isFuture() !== !!S.future) setFuture(isFuture());
    if (S.future) return;
    const t0 = performance.now();
    const mark = !!window.TERRA_PERF;
    if (mark) performance.mark('terra-defense-start');
    try { step(dt); } finally {
      const ms = performance.now() - t0;
      S.lastMs = ms;
      S.ms = S.ms == null ? ms : S.ms * 0.95 + ms * 0.05;
      S.msMax = Math.max(S.msMax || 0, ms);
      if (mark) {
        performance.mark('terra-defense-end');
        performance.measure('terra-defense', 'terra-defense-start', 'terra-defense-end');
        performance.clearMarks('terra-defense-start');
        performance.clearMarks('terra-defense-end');
        performance.clearMeasures('terra-defense');
      }
    }
  }
  function step(dt) {
    onSession();
    if (!S.pool) S.pool = makePool();
    if (S.dirty || S.baseRef !== game.p.base || S.baseCount !== game.p.base?.length) {
      S.baseRef = game.p.base; S.baseCount = game.p.base?.length;
      S.turretList = turrets();
      cacheTowers();
      syncViews();
      emit('base');
    }
    applyCastShadows();
    const live = game.state === 'play' && !game.world?.inDungeon && !game._coopGuest && game.net?.role !== 'guest';
    if (live) {
      S.acc += dt;
      let n = 0;
      while (S.acc >= TICK && n++ < 4) {
        S.acc -= TICK;
        rebuildEnemyGrid();
        const list = S.turretList || turrets();
        for (let i = 0; i < list.length; i++) tickTurret(list[i], S.views.get(idOf(list[i])));
      }
      S.supplyAcc += dt;
      if (S.supplyAcc >= 1) { S.supplyAcc = 0; planTrips(); }
      updateTrips(dt);
    }
    updatePool(dt);
    animateViews(dt);
    if (performance.now() - S.lastEmit > 1000 && turrets().length) emit('tick');
  }

  /* ---------- API для [ui] ---------- */
  const STATE_LABEL = { building: 'Строится', online: 'В строю', lowAmmo: 'Мало патронов', empty: 'Пустой магазин', damaged: 'Повреждена', broken: 'Сломана', upgrading: 'Улучшается', unpowered: 'Нет питания', offline: 'Выключена' };
  function stateOf(o) {
    const maxHp = ctx.B.defense?.hp?.turretB || 120, hp = num(o.hp, maxHp);
    if (hp <= 0) return 'broken';
    if (magOf(o) <= 0) return 'empty';
    if (magOf(o) < magMax(o) * 0.25) return 'lowAmmo';
    if (hp < maxHp * 0.5) return 'damaged';
    return 'online';
  }
  function cardOf(o) {
    const dk = dkOf(o), t = TYPES[dk], lv = clampLvl(o.lvl), maxHp = ctx.B.defense?.hp?.turretB || 120;
    const assigned = [...S.trips.values()].filter((x) => x.turret === idOf(o)).map((x) => {
      const s = settler(x.id);
      const len = Math.hypot(x.to.x - x.from.x, x.to.z - x.from.z);
      return { id: x.id, name: s?.name || x.id, prof: s?.prof || null, task: x.phase === 'go' ? 'Несёт ' + ammoName(x.ammo) : 'Возвращается на склад', eta: x.phase === 'go' ? Math.ceil(((1 - x.k) * len) / x.speed) : 0 };
    });
    const st = stateOf(o), mm = magMax(o);
    const next = st === 'empty' || st === 'lowAmmo' ? (porterIds().length ? 'Подносчик принесёт ' + ammoName(t.ammo) + ' со склада' : 'Назначьте подносчика или зарядите из рюкзака') : lv < 3 ? 'Улучшить до ' + (lv + 1) + ' ур.' : 'Готова';
    return { id: idOf(o), dk, name: t.name, lvl: lv, branch: null, post: null, x: o.x, z: o.z, hp: num(o.hp, maxHp), maxHp, wear: num(o.wear, 0), mag: Math.floor(magOf(o) * (t.proj === 'flame' ? 4 : 1)) / (t.proj === 'flame' ? 4 : 1), magMax: mm, ammoItem: t.ammo, ammoName: ammoName(t.ammo), range: +rangeOf(o).toFixed(1), dmg: +dmgOf(o).toFixed(1), state: st, stateLabel: STATE_LABEL[st], priority: num(o.dprio, 0), assignedSettlers: assigned, nextAction: next, upgradeCost: lv < 3 ? t.up[lv] : null };
  }
  function find(id) { return turrets().find((o) => idOf(o) === id); }
  const ok = (x = {}) => (emit(x.reason || 'action', x), { ok: true, ...x });
  const no = (reason) => ({ ok: false, reason });
  /* Защищённая запись приказа: снимок затронутого состояния → изменение → синхронный game.save().
   * game.save() (savePlayerCandidate) возвращает {ok, status, reason}; приказ считается выполненным
   * только при status === 'committed'. Иначе — полный откат снимка (рюкзак, склад, запись турели,
   * блок camp.defense), {ok:false, reason:'save-failed'} и событие с reason 'save-failed'.
   * Побочные эффекты (визуал, отмена ходки) выполняются только после подтверждённой записи.
   * status 'committed-unpublished' значит: запись на диске есть, но игра остановила дальнейшие записи —
   * в памяти оставляем изменение (оно совпадает с диском), но отвечаем ok:false 'save-unconfirmed'. */
  const restore = (obj, copy) => { if (!obj || !copy) return; for (const k of Object.keys(obj)) if (!(k in copy)) delete obj[k]; Object.assign(obj, JSON.parse(JSON.stringify(copy))); };
  function tx(kind, { turret = null, mutate, after = null }) {
    const p = game.p, camp = p.camp, o = turret;
    const snap = {
      inv: JSON.parse(JSON.stringify(p.inv || {})),
      res: camp?.res ? JSON.parse(JSON.stringify(camp.res)) : null,
      def: camp?.defense ? JSON.parse(JSON.stringify(camp.defense)) : undefined,
      o: o ? JSON.parse(JSON.stringify(o)) : null
    };
    const extra = mutate();
    let r;
    try { r = game.save?.(); } catch (e) { r = { ok: false, status: 'error', reason: String(e?.message || e) }; }
    if (r?.ok && r.status === 'committed') {
      S.lastError = null;
      after?.();
      S.dirty = true; game.baseDirty = true;
      return ok({ reason: kind, ...extra });
    }
    if (r?.status === 'committed-unpublished') {
      after?.();
      S.dirty = true; game.baseDirty = true;
      S.lastError = { kind, reason: 'save-unconfirmed', status: r.status, save: r.reason };
      emit('save-failed', { ok: false, kind, status: r.status, saveReason: r.reason });
      return { ok: false, reason: 'save-unconfirmed', status: r.status, saveReason: r.reason };
    }
    restore(p.inv, snap.inv);
    if (camp?.res && snap.res) restore(camp.res, snap.res);
    if (camp) { if (snap.def === undefined) delete camp.defense; else if (camp.defense) restore(camp.defense, snap.def); else camp.defense = snap.def; }
    if (o) restore(o, snap.o);
    S.dirty = true; game.baseDirty = true;
    S.lastError = { kind, reason: 'save-failed', status: r?.status || 'none', save: r?.reason || 'no-result' };
    emit('save-failed', { ok: false, kind, status: r?.status, saveReason: r?.reason });
    return { ok: false, reason: 'save-failed', status: r?.status, saveReason: r?.reason };
  }
  const api = {
    version: 1,
    get ready() { return !!ctx && !!game?.p; },
    getState() {
      if (!ctx || !game?.p) return { ready: false, limit: { used: 0, max: TIER_LIMIT[0] }, summary: null, turrets: [], porters: [], catalog: [] };
      if (isFuture()) return { ready: false, future: true, limit: { used: turrets().length, max: limit() }, summary: null, turrets: [], porters: [], catalog: [] };
      const list = turrets().map(cardOf), res = campRes() || {};
      return {
        ready: true,
        limit: { used: list.length, max: limit(), tiers: TIER_LIMIT.slice() },
        summary: { total: list.length, online: list.filter((x) => x.state === 'online').length, needAmmo: list.filter((x) => x.state === 'empty' || x.state === 'lowAmmo').length, porters: porterIds().length, trips: S.trips.size, technician: isTech(), stock: { a545: res.a545 || 0, nails: res.nails || 0, gas: res.gas || 0, powder: res.powder || 0 } },
        turrets: list,
        porters: porterIds().map((id) => { const s = settler(id), tr = S.trips.get(id); return { id, name: s?.name || id, prof: s?.prof || null, available: available(s), task: tr ? (tr.phase === 'go' ? 'Несёт к турели' : 'Возвращается') : 'Ждёт заказ', turretId: tr?.turret || null }; }),
        catalog: Object.entries(TYPES).map(([dk, t]) => ({ dk, key: t.key, name: t.name, about: t.about, ammoItem: t.ammo, ammoName: ammoName(t.ammo), cost: t.cost || ctx.Li.turretB?.cost, lvlReq: t.lvlReq, magMax: t.mag, range: t.range, dmg: t.dmg }))
      };
    },
    build(dk) {
      const t = TYPES[dk];
      if (!t || !game?.p) return no('unknown-turret');
      if (turrets().length >= limit()) return no('limit');
      game.toggleBuild?.(true);
      if (game.build) { game.build.sel = t.key; game.build.demo = false; game.renderBuildBar?.(); }
      return ok({ reason: 'build-mode', dk });
    },
    upgrade(id) {
      const o = find(id); if (!o) return no('not-found');
      const lv = clampLvl(o.lvl); if (lv >= 3) return no('max-level');
      const cost = TYPES[dkOf(o)].up[lv], inv = game.p.inv;
      if (!Object.entries(cost).every(([k, n]) => (inv[k] || 0) >= n)) return no('resources');
      return tx('upgrade', { turret: o, mutate: () => {
        for (const [k, n] of Object.entries(cost)) inv[k] -= n;
        o.dk = dkOf(o); o.lvl = lv + 1;
        return { id, lvl: o.lvl };
      } });
    },
    repair(id) {
      const o = find(id); if (!o) return no('not-found');
      const maxHp = ctx.B.defense?.hp?.turretB || 120;
      if (num(o.hp, maxHp) >= maxHp) return no('full');
      if ((game.p.inv.scrap || 0) < 2) return no('resources');
      return tx('repair', { turret: o, mutate: () => { game.p.inv.scrap -= 2; o.hp = maxHp; return { id }; } });
    },
    reload(id) {
      const o = find(id); if (!o) return no('not-found');
      const t = TYPES[dkOf(o)], inv = game.p.inv, put = Math.min(Math.floor(inv[t.ammo] || 0), Math.ceil(needFor(o)));
      if (put <= 0) return no(needFor(o) < 1 ? 'full' : 'no-ammo');
      return tx('reload', { turret: o, mutate: () => { inv[t.ammo] -= put; o.dk = dkOf(o); o.mag = Math.min(magMax(o), magOf(o) + put); return { id, amount: put }; } });
    },
    assign(settlerId, on = true) {
      const s = settler(settlerId); if (!s) return no('not-found');
      const has = (game.p.camp?.defense?.porters || []).includes(settlerId);
      if (!!on === has) return ok({ reason: 'assign', settlerId, porter: !!on, unchanged: true });
      return tx('assign', {
        mutate: () => { const d = dstate(); d.porters = on ? [...d.porters, settlerId] : d.porters.filter((x) => x !== settlerId); return { settlerId, porter: !!on }; },
        after: () => { if (!on) { const tr = S.trips.get(settlerId); tr && endTrip(tr); } }
      });
    },
    setPriority(id, prio) {
      const o = find(id); if (!o) return no('not-found');
      const v = Math.max(0, Math.min(3, prio | 0));
      if (num(o.dprio, 0) === v) return ok({ reason: 'priority', id, priority: v, unchanged: true });
      return tx('priority', { turret: o, mutate: () => { o.dprio = v; return { id, priority: v }; } });
    },
    deposit(item, n) {
      if (!['a545', 'nails', 'gas', 'powder'].includes(item)) return no('item');
      const inv = game.p.inv, put = Math.min(Math.floor(inv[item] || 0), Math.max(0, n | 0) || Infinity);
      if (!(put > 0)) return no('no-items');
      const res = campRes(); if (!res) return no('no-camp');
      return tx('deposit', { mutate: () => { inv[item] -= put; res[item] = (res[item] || 0) + put; return { item, amount: put }; } });
    },
    _debug: () => ({ ms: +(S.ms || 0).toFixed(3), msMax: +(S.msMax || 0).toFixed(2), lastMs: S.lastMs == null ? null : +S.lastMs.toFixed(3), trips: S.trips.size, pool: S.pool?.list.length || 0, poolMax: S.pool?.n || 0, views: S.views.size, searches: S.searches || 0, losFast: S.losFast || 0, losFull: S.losFull || 0, mismatch: S.mismatch || 0, stats: { ...S.stats } })
  };
  window.terraDefense = api;

  /* ---------- раздел «Оборона» в лагере (window.terraCampUI из PR #14) ---------- */
  const el = (tag, cls, text) => { const e = document.createElement(tag); if (cls) e.className = cls; if (text != null) e.textContent = text; return e; };
  const TONE = { online: 'ok', lowAmmo: 'warn', empty: 'bad', damaged: 'warn', broken: 'bad' };
  function act(label, fn, info = false) {
    const b = el('button', info ? 'campInfoButton' : 'campPrimaryAction', label);
    b.type = 'button';
    b.addEventListener('click', () => {
      const r = fn();
      if (r && (r.reason === 'save-failed' || r.reason === 'save-unconfirmed')) game.ui?.toast?.(saveErrorText(r), '#ff6a5a');
      else if (r && r.ok === false) game.ui?.toast?.('Нельзя: ' + (REASON[r.reason] || r.reason), '#ffba66');
      renderDefense(lastContainer);
    });
    return b;
  }
  const REASON = { resources: 'не хватает ресурсов в рюкзаке', 'no-ammo': 'нет боеприпасов в рюкзаке', full: 'уже полно', 'max-level': 'максимальный уровень', limit: 'лимит турелей', 'no-items': 'в рюкзаке нет', 'not-found': 'турель не найдена' };
  const SAVE_REASON = { 'storage-write': 'в браузере закончилось место', 'backup-failed': 'не записалась резервная копия, игра остановила записи до перезагрузки', 'backup-unverified': 'не проверилась резервная копия', 'write-unverified': 'запись не подтвердилась', 'changed-externally': 'сохранение изменили в другой вкладке', guest: 'в кооперативе сохраняет хозяин', dungeon: 'в подземелье запись недоступна' };
  function saveErrorText(e) {
    const why = SAVE_REASON[e.saveReason || e.save] || e.saveReason || e.save || e.status || 'неизвестная причина';
    return e.reason === 'save-unconfirmed'
      ? 'Приказ записан, но игра не подтвердила сохранение (' + why + '). Перезагрузите игру.'
      : 'Приказ не выполнен: игра не смогла записать сохранение (' + why + '). Ресурсы и турели не изменились.';
  }
  const costText = (c) => Object.entries(c || {}).map(([k, n]) => ammoName(k) + ' ' + n).join(', ');
  let lastContainer = null;
  function styleOnce() {
    if (document.getElementById('terraDefenseStyle')) return;
    const st = el('style');
    st.id = 'terraDefenseStyle';
    st.textContent = '#campPanel .defenseStat{display:grid;gap:2px;padding:8px;border:1px solid var(--camp-line,#6a5640);border-radius:8px;background:#151a18;min-width:0}'
      + '#campPanel .defenseStat b{font-size:16px;color:var(--camp-ink,#f1dfbd)}#campPanel .defenseStat span{font-size:11px;color:var(--panel-muted,#c2b29b);overflow-wrap:anywhere}'
      + '#campPanel .defenseBody{display:grid;gap:6px;min-width:0}#campPanel .defenseBody .campItemCard__title{display:flex;flex-wrap:wrap;gap:6px;align-items:center}'
      + '#campPanel .defenseSaveError{display:block;padding:10px 12px;border:1px solid #c0503f;background:#2a1513;color:#ffd7cf;font-size:13px}'
      + '#campPanel .defenseWide{grid-column:1/-1}#campPanel .defenseWide .campItemCard__actions{grid-column:1/-1;display:flex;flex-wrap:wrap;justify-content:flex-start}';
    document.head.append(st);
  }
  function iconNode() {
    const d = el('div', 'campItemCard__icon');
    const g = document.querySelector('#campTabs [data-camp-tab="defense"] svg');
    if (g) d.append(g.cloneNode(true));
    return d;
  }
  function stat(value, label) { const d = el('div', 'defenseStat'); d.append(el('b', null, String(value)), el('span', null, label)); return d; }
  function renderDefense(container) {
    if (!container || !container.isConnected) return;
    lastContainer = container;
    styleOnce();
    const st = api.getState();
    if (st.future) {
      const s = container.querySelector('.campSection__summary') || container, l = container.querySelector('.campSection__list') || container;
      s.textContent = ''; l.textContent = '';
      l.append(el('div', 'campItemCard__meta', 'Сохранение сделано более новой версией обороны. Турели отключены, чтобы не испортить данные — обновите игру.'));
      return;
    }
    const summary = container.querySelector('.campSection__summary') || container;
    const list = container.querySelector('.campSection__list') || container;
    summary.textContent = ''; list.textContent = '';
    container.dataset.defenseTurrets = '1';
    if (!st.ready) return;
    const s = st.summary.stock;
    if (S.lastError) {
      const e = el('div', 'campItemCard defenseWide defenseSaveError', saveErrorText(S.lastError));
      e.setAttribute('role', 'alert');
      list.append(e);
    }
    summary.append(stat(st.limit.used + '/' + st.limit.max, 'турелей (лимит по уровню лагеря)'), stat(st.summary.porters, 'подносчиков'),
      stat(st.summary.needAmmo, 'ждут боеприпасы'), stat(s.a545 + ' · ' + s.nails + ' · ' + s.gas, 'склад: 5.45 · гвозди · газ'));
    for (const t of st.turrets) {
      const card = el('article', 'campItemCard');
      card.dataset.tone = TONE[t.state] || 'idle';
      card.dataset.defenseId = t.id;
      const body = el('div', 'defenseBody');
      const title = el('div', 'campItemCard__title');
      title.append(el('span', null, t.name + ' · ' + t.lvl + ' ур.'));
      const badge = el('span', 'campStatusBadge', t.stateLabel); badge.dataset.tone = TONE[t.state] || 'idle'; title.append(badge);
      const meter = el('div', 'campMeter'); meter.dataset.kind = 'ammo'; meter.dataset.level = t.state === 'empty' ? 'bad' : t.state === 'lowAmmo' ? 'warn' : 'ok';
      meter.style.setProperty('--value', String(t.magMax ? Math.min(1, t.mag / t.magMax) : 0));
      meter.setAttribute('role', 'meter'); meter.setAttribute('aria-label', 'Магазин ' + t.mag + ' из ' + t.magMax);
      meter.append(el('i'), el('span', null, t.mag + '/' + t.magMax));
      const who = t.assignedSettlers.map((a) => a.name + ': ' + a.task + (a.eta ? ' (~' + a.eta + ' с)' : '')).join('; ');
      const meta = el('div', 'campItemCard__meta');
      meta.append(el('span', null, t.ammoName + ' · прочность ' + Math.ceil(t.hp) + '/' + t.maxHp), el('span', null, who || t.nextAction));
      if (t.upgradeCost) meta.append(el('span', null, 'Улучшение: ' + costText(t.upgradeCost)));
      body.append(title, meter, meta);
      const a = el('div', 'campItemCard__actions');
      const r = act('Зарядить', () => api.reload(t.id)); r.setAttribute('aria-label', 'Зарядить из рюкзака: ' + t.name); a.append(r);
      if (t.upgradeCost) { const u = act('Улучшить', () => api.upgrade(t.id)); u.setAttribute('aria-label', 'Улучшить ' + t.name + ': ' + costText(t.upgradeCost)); a.append(u); }
      const info = act('i', () => {
        const box = el('div');
        const c = st.catalog.find((x) => x.dk === t.dk);
        for (const line of [c?.about, 'Урон ' + t.dmg + ' · дальность ' + t.range + ' м', 'Боеприпас: ' + t.ammoName + ' · магазин по уровням ' + (c?.magMax || []).join('/'), 'Подносчики берут его со склада лагеря; пустая турель рядом с героем берёт из рюкзака.'])
          if (line) box.append(el('p', null, line));
        window.terraCampUI?.openInfo?.(t.name, box);
        return { ok: true };
      }, true);
      info.setAttribute('aria-label', 'Подробности: ' + t.name);
      a.append(info);
      card.append(iconNode(), body, a);
      list.append(card);
    }
    const pc = el('article', 'campItemCard defenseWide');
    const pb = el('div', 'defenseBody');
    pb.append(el('div', 'campItemCard__title', 'Подносчики'), el('div', 'campItemCard__meta', 'Носят 5.45, гвозди и газ со склада лагеря к турелям, магазин которых опустел больше чем на треть.'));
    pc.append(iconNode(), pb);
    const pa = el('div', 'campItemCard__actions');
    for (const sv of Object.values(game.p.camp?.settlers || {})) {
      if (sv.dead) continue;
      const on = st.porters.some((x) => x.id === sv.id);
      const b = act((on ? '✓ ' : '+ ') + sv.name, () => api.assign(sv.id, !on));
      b.setAttribute('aria-pressed', String(on)); b.dataset.porter = sv.id;
      pa.append(b);
    }
    if (!pa.children.length) pb.append(el('div', 'campItemCard__meta', 'В лагере пока нет жителей.'));
    pc.append(pa);
    list.append(pc);
    const bc = el('article', 'campItemCard defenseWide');
    const bb = el('div', 'defenseBody');
    bb.append(el('div', 'campItemCard__title', 'Снабжение и стройка'), el('div', 'campItemCard__meta', 'Порох — в патроны 5.45 (рецепт «5.45 ×30 на порохе»), гвозди — Гвоздомёту, газ — Огнемёту. Сдайте их на склад, чтобы подносчики могли носить.'));
    bc.append(iconNode(), bb);
    const ba = el('div', 'campItemCard__actions');
    for (const k of ['a545', 'nails', 'gas', 'powder']) if ((game.p.inv[k] || 0) >= 1) ba.append(act('На склад: ' + ammoName(k) + ' ×' + Math.floor(game.p.inv[k]), () => api.deposit(k)));
    if (st.limit.used < st.limit.max) for (const c of st.catalog) ba.append(act('Построить: ' + c.name, () => { const r = api.build(c.dk); if (r.ok) document.querySelector('#campPanel .panelFoot [data-close]')?.click(); return r; }));
    bc.append(ba);
    list.append(bc);
  }
  function updateBadge() {
    const ui = window.terraCampUI;
    if (!ui?.setBadge || !api.ready) return;
    const n = api.getState().summary?.needAmmo || 0;
    if (n !== S.badge) { S.badge = n; ui.setBadge('defense', n, 'warn'); }
  }
  // родная вкладка с полосками прочности подписывает любую turretB как «Турель»:
  // после отрисовки меняем подпись на вид турели (карточки идут в порядке game.defenseList()).
  function relabelNative() {
    const panel = document.getElementById('campPanel');
    if (!panel || panel.classList.contains('hidden') || !game?.defenseList) return;
    const list = game.defenseList();
    if (!list.some((d) => d.type === 'turretB')) return;
    for (const grid of panel.querySelectorAll('.defGrid')) {
      const cards = [...grid.children];
      if (cards.length !== list.length) continue;
      const heads = cards.map((c) => c.firstChild?.nodeType === 3 ? c.firstChild : null);
      const ok = list.every((d, i) => heads[i] && (d.type !== 'turretB' || heads[i].nodeValue === 'Турель' || cards[i].dataset.dk));
      if (!ok) continue;
      const turrets = new Map(game.p.base.filter(isTurret).map((o) => [game.defenseId(o), o]));
      list.forEach((d, i) => {
        const o = d.type === 'turretB' && turrets.get(d.id);
        if (!o) return;
        const t = TYPES[dkOf(o)] || TYPES.pkm, name = t.name + (clampLvl(o.lvl) > 1 ? ' · ур. ' + clampLvl(o.lvl) : '');
        if (heads[i].nodeValue !== name) heads[i].nodeValue = name;
        cards[i].dataset.dk = dkOf(o);
      });
    }
  }
  function watchNative() {
    const panel = document.getElementById('campPanel');
    if (!panel) return setTimeout(watchNative, 500);
    let q = 0;
    new MutationObserver(() => { if (!q) { q = 1; queueMicrotask(() => { q = 0; relabelNative(); }); } })
      .observe(panel, { childList: true, subtree: true });
  }
  function watchPanel() {
    watchNative();
    let tries = 0;
    const attach = () => {
      const ui = window.terraCampUI;
      if (ui?.registerSection) {
        ui.registerSection({ id: 'defense', native: true, label: 'Оборона', order: 1, render: (container) => renderDefense(container) });
        let t = 0;
        window.addEventListener('terra:defense-change', () => {
          const now = performance.now();
          if (now - t < 1000) return;
          t = now;
          updateBadge();
          const panel = document.getElementById('campPanel');
          if (lastContainer?.isConnected && panel && !panel.classList.contains('hidden') && ui.tab === 'defense') renderDefense(lastContainer);
        });
        return;
      }
      if (++tries < 40) setTimeout(attach, 250);
      else console.warn('[defense] terraCampUI не найден: раздел турелей в лагере не показан');
    };
    attach();
  }

  /* ---------- подключение ---------- */
  function boot(g) {
    game = g || game || window.game;
    ctx = window.TERRA_DEFENSE_CTX;
    if (!ctx || !game) return;
    if (!booted) {
      if (!installData()) return;
      booted = true;
      loadModels();
      const mu = game.moduleUpdate;
      game.moduleUpdate = function (dt) {
        const r = mu.apply(this, arguments);
        try { update(dt); } catch (e) { if (!S.err) { S.err = 1; console.warn('[defense]', e); } }
        return r;
      };
      watchPanel();
    }
    patchGeo();
    patchPlace();
    S.dirty = true;
    game.baseDirty = true;
  }
  for (const k of ['build', 'upgrade', 'repair', 'reload', 'assign', 'setPriority', 'deposit']) {
    const f = api[k];
    api[k] = function () { return isFuture() ? no('future') : f.apply(this, arguments); };
  }
  window.TERRA_DEFENSE_HOOK = boot;
  if (window.TERRA_DEFENSE_CTX) boot(window.game);
})();
