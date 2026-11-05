/* «Живой лагерь» (концепт В): метки над постройками, жителями и турелями,
   контекстное меню штатных приказов и чертёжный призрак в режиме стройки.
   Новых механик нет: приказы идут через game.camp / game.buildAction / terraDefense.
   Формат сохранения не читается и не пишется этим файлом.
   Подключение — из camp-navigation.js. ?livecamp=0 выключает модуль (замер кадра). */
(() => {
  'use strict';
  if (new URLSearchParams(location.search).get('livecamp') === '0') return;

  const NAMES = {
    generator: 'Генератор', sawmill: 'Лесопилка', pump: 'Насос', watch: 'Вышка',
    workshop: 'Мастерская', farm: 'Ферма', lab: 'Лаборатория', kitchen: 'Кухня',
    cistern: 'Цистерна', barracks: 'Казарма', campfire: 'Костёр', radio: 'Радиопост',
  };
  const REASON = {
    busy: 'Строительство уже идёт', max: 'Максимальный уровень', 'max-level': 'Максимальный уровень',
    tier: 'Нужен уровень лагеря', technology: 'Нужна технология', resources: 'Недостаточно ресурсов',
    unavailable: 'Сейчас недоступно', job: 'Такой работы нет', full: 'Уже полный',
    'no-ammo': 'Нет патронов', 'not-found': 'Не найдено', 'save-failed': 'Запись сохранения не прошла',
    'save-unconfirmed': 'Сохранение не подтверждено', limit: 'Лимит турелей', project: 'Нет стройки',
    paused: 'Стройка на паузе',
  };
  const BASE_KEEP = {
    door: 2.4, gate: 2.6, bed: 1.4, chest: 1.5, bench: 1.8, anvil: 1.6, chem: 1.8,
    fire: 1.6, light: 2.6, turretB: 2.3, watchtower: 4.2, checkpoint: 2.4, shockTrap: 1.2,
    dNail: 2.2, dFlame: 2.1,
  };
  const FAR = 38;
  const MAX = 12;
  const why = value => REASON[value] || (typeof value === 'string' && /[а-яё]/i.test(value) ? value : 'Сейчас нельзя');
  const game = () => window.game;
  const num = (v, d = 0) => (Number.isFinite(v) ? v : d);

  const layer = document.createElement('div');
  layer.id = 'campLiveLayer';
  const tags = new Map();
  let menu = null;
  let menuOwner = null;
  let back = null;
  let note = null;
  let aim = null;
  let place = null;
  let vec = null;
  let tmp = null;
  let anchors = [];
  let explicit = [];
  let lastCollect = 0;
  let lastScan = 0;
  let aiming = false;
  let pickDown = null;
  let selectedCell = null;
  const ghostHooks = new WeakSet();

  function session(g = game()) { return { game: g, player: g?.p, world: g?.world }; }
  function current(owner) {
    const g = game();
    return !!owner && owner.game === g && owner.player === g?.p && owner.world === g?.world &&
      !!g?.p?.alive && g.state === 'play' && !g.world?.inDungeon && !g.dungeonTransition;
  }
  function selectedCurrent() {
    const g = game();
    return selectedCell && current(selectedCell.owner) && g.build?.on &&
      g.build.sel === selectedCell.sel && g.build.rot === selectedCell.rot &&
      g.build.demo === selectedCell.demo;
  }
  function installGhostHook(g) {
    if (!g || ghostHooks.has(g) || typeof g.ghostPos !== 'function') return;
    const native = g.ghostPos;
    g.ghostPos = function (...args) {
      if (this === g && selectedCurrent()) return { ...selectedCell.point };
      selectedCell = null;
      return native.apply(this, args);
    };
    ghostHooks.add(g);
  }

  function vectors() {
    const g = game();
    const src = g?.ghostM?.position;
    if (!src?.clone) return false;
    if (!vec) { vec = src.clone(); tmp = src.clone(); }
    return true;
  }
  function ground(x, z) {
    const fn = window.TERRA_DEFENSE_CTX?.Y;
    const y = typeof fn === 'function' ? fn(x, z) : 0;
    return Number.isFinite(y) ? y : 0;
  }
  function visualOrigin() {
    const list = game()?.world?._campEmit;
    if (!Array.isArray(list)) return null;
    const fire = list.find(item => item && item.cookingFire && Number.isFinite(item.x) && Number.isFinite(item.z));
    if (!fire) return null;
    return { x: fire.x, y: num(fire.y, 0) - 0.45, z: fire.z - 0.4 };
  }
  function level(camp, id) { return (camp.buildings?.[id]?.lvl || 0) | 0; }
  function buildingState(camp, id) {
    const spec = window.TERRA_DEFENSE_CTX?.B?.camp?.buildings?.[id];
    const row = camp.buildings?.[id];
    const lvl = level(camp, id);
    const maxHp = (spec?.hp || row?.hp || 1) * Math.max(1, lvl);
    const hp = num(row?.hp, maxHp);
    const project = row?.project;
    const working = Object.values(camp.settlers || {}).some(s => s && !s.dead && (s.facility === id || s.order?.target === id) && (s.status === 'working' || s.job === 'operate'));
    let upgrade = null;
    if (spec && !project && lvl < (spec.max || 1)) {
      const next = lvl + 1;
      const tierOk = (camp.tier | 0) >= (spec.tier || 1) + (next - 1) * (window.TERRA_DEFENSE_CTX.B.camp.upgrade?.tierPerLevel || 1);
      const techOk = !spec.tech || !!camp.tech?.[spec.tech];
      const scale = window.TERRA_DEFENSE_CTX.B.camp.upgrade?.costScale || 1.75;
      const enough = tierOk && techOk && Object.entries(spec.baseCost || {}).every(([k, v]) => (camp.res?.[k] || 0) >= Math.ceil(v * scale ** (next - 1)));
      upgrade = enough;
    }
    if (project && !project.paused) return { text: 'строится', tone: 'warn' };
    if (project?.paused) return { text: 'пауза', tone: 'idle' };
    if (!lvl) return { text: 'не построено', tone: 'idle' };
    if (hp <= 0) return { text: 'разрушено', tone: 'bad' };
    if (hp < maxHp * 0.5) return { text: 'нужен ремонт', tone: 'bad' };
    if (working) return { text: 'работает', tone: 'ok' };
    if (upgrade) return { text: 'можно улучшить', tone: 'ok' };
    if (upgrade === false && lvl > 0 && lvl < (spec?.max || 99)) return { text: 'не хватает', tone: 'warn' };
    return { text: 'простой', tone: 'idle' };
  }
  function settlerState(s) {
    if (s.wounded || s.status === 'injured') return { text: 'ранен', tone: 'bad' };
    if (s.job === 'idle' || s.status === 'rest') return { text: 'отдых', tone: 'idle' };
    if (s.status === 'working') return { text: 'работает', tone: 'ok' };
    if (s.status === 'travel') return { text: 'в пути', tone: 'warn' };
    if (s.status === 'blocked') return { text: 'ждёт', tone: 'warn' };
    return { text: 'простой', tone: 'idle' };
  }
  function pushAnchor(list, item) {
    if (!item || !Number.isFinite(item.x) || !Number.isFinite(item.z)) return;
    const g = game();
    const dx = item.x - g.p.x, dz = item.z - g.p.z;
    item.d2 = dx * dx + dz * dz;
    if (item.d2 > FAR * FAR) return;
    item.y = Number.isFinite(item.y) ? item.y : ground(item.x, item.z) + (item.top || 2.4);
    item.key = item.kind + ':' + item.id;
    if (list.some(other => other.key === item.key)) return;
    list.push(item);
  }
  function facilitySpots(camp, origin) {
    const en = id => level(camp, id) > 0;
    const mm = id => en(id) || !!camp.buildings?.[id]?.project;
    const tech = camp.tech || {};
    const tier = camp.tier | 0 || 1;
    const medic = Object.values(camp.settlers || {}).some(s => s && !s.dead && (s.prof === 'medic' || s.prof === 'scientist'));
    const spots = [{ id: 'campfire', x: 0, z: 0.4, top: 1.7, decor: true }];
    if (en('kitchen') || en('farm')) spots.push({ id: en('kitchen') || camp.buildings?.kitchen?.project ? 'kitchen' : 'farm', x: -6.2, z: -5.4, top: 3.2 });
    if (tech.medicine || en('lab') || medic) spots.push({ id: 'lab', x: 6.3, z: -5.2, top: 3.1 });
    if (en('workshop')) spots.push({ id: 'workshop', x: 7.4, z: -0.6, top: 3.1 });
    if (tech.logistics || tier >= 2) spots.push({ id: 'radio', x: -7.1, z: -0.4, top: 2.6, decor: true });
    if (en('sawmill')) spots.push({ id: 'sawmill', x: -8.2, z: 3.6, top: 2.8 });
    if (mm('cistern')) spots.push({ id: 'cistern', x: 8.6, z: 6.4, top: 2.2 });
    if (mm('barracks')) spots.push({ id: 'barracks', x: -4.6, z: -8.6, top: 2.7 });
    if (en('pump')) spots.push({ id: 'pump', x: 9.2, z: -2.6, top: 2.1 });
    if (mm('watch')) spots.push({ id: 'watch', x: 0.2, z: -7.4, top: 4.4 });
    if (mm('generator')) spots.push({ id: 'generator', x: 10.4, z: 2, top: 2.9 });
    if (mm('farm') && !spots.some(s => s.id === 'farm')) spots.push({ id: 'farm', x: -1.6, z: 8.6, top: 3.5 });
    return spots.map(s => ({ ...s, x: origin.x + s.x, z: origin.z + s.z, y: origin.y + s.top }));
  }
  function readExplicit(obj, into) {
    if (!obj) return;
    const data = obj.userData?.campAnchor;
    const named = typeof obj.name === 'string' && obj.name.startsWith('campAnchor:') ? obj.name.slice(11) : '';
    const id = data?.id || named;
    const kind = data?.kind || (named ? 'building' : '');
    if (!id || !kind || !obj.getWorldPosition) return;
    obj.getWorldPosition(tmp);
    into.push({
      id: String(id), kind: kind === 'settler' || kind === 'defense' ? kind : 'building',
      x: tmp.x, y: tmp.y + num(data?.top, 0.4), z: tmp.z, explicit: true,
    });
  }
  function scanExplicit() {
    const g = game();
    const found = [];
    if (!vectors()) return found;
    const home = g.scene?.getObjectByName?.('camp-home');
    if (home) {
      readExplicit(home, found);
      for (const child of home.children || []) readExplicit(child, found);
    }
    for (const view of Object.values(g.npcV || {})) readExplicit(view?.root, found);
    return found;
  }
  function collect() {
    const g = game();
    const camp = g?.p?.camp;
    if (!g?.p || g.state !== 'play' || g.world?.inDungeon || !camp) return [];
    const now = performance.now();
    if (now - lastScan > 500) { lastScan = now; explicit = scanExplicit(); }
    const list = [];
    const seen = new Set();
    for (const item of explicit) {
      const state = item.kind === 'settler' ? settlerState(camp.settlers?.[item.id] || {}) : item.kind === 'defense' ? defenseState(item.id) : buildingState(camp, item.id);
      pushAnchor(list, { ...item, name: NAMES[item.id] || camp.settlers?.[item.id]?.name || item.id, ...stateLabel(state) });
      seen.add(item.kind + ':' + item.id);
    }
    const origin = visualOrigin();
    if (origin) {
      for (const spot of facilitySpots(camp, origin)) {
        if (seen.has('building:' + spot.id)) continue;
        const state = spot.decor ? { text: spot.id === 'campfire' ? 'горит' : 'на связи', tone: 'ok' } : buildingState(camp, spot.id);
        pushAnchor(list, { kind: 'building', id: spot.id, name: NAMES[spot.id] || spot.id, x: spot.x, y: spot.y, z: spot.z, decor: !!spot.decor, ...stateLabel(state) });
      }
    }
    const defense = window.terraDefense?.getState?.();
    const turrets = defense?.ready ? defense.turrets || [] : [];
    for (const turret of turrets) {
      if (seen.has('defense:' + turret.id)) continue;
      const tone = turret.state === 'online' ? 'ok' : turret.state === 'broken' || turret.state === 'empty' ? 'bad' : turret.state === 'offline' ? 'idle' : 'warn';
      pushAnchor(list, { kind: 'defense', id: turret.id, name: turret.name || 'Турель', x: turret.x, z: turret.z, top: 2.4, text: turret.stateLabel || turret.state || 'в строю', tone });
      seen.add('defense:' + turret.id);
    }
    const catalog = window.TERRA_DEFENSE_CTX?.Li || {};
    for (const block of g.p.base || []) {
      const top = BASE_KEEP[block.t];
      if (!top) continue;
      if ((block.t === 'turretB' || block.t === 'dNail' || block.t === 'dFlame') && turrets.some(t => Math.hypot(t.x - block.x, t.z - block.z) < 0.8)) continue;
      const id = block.t + '@' + block.x + ',' + block.z;
      if (seen.has('building:' + id)) continue;
      const broken = block.hp != null && block.hp <= 0;
      const hurt = block.hp != null && window.TERRA_DEFENSE_CTX?.B?.defense?.hp?.[block.t] && block.hp < window.TERRA_DEFENSE_CTX.B.defense.hp[block.t];
      pushAnchor(list, {
        kind: 'building', id, name: catalog[block.t]?.n || block.t, x: block.x, z: block.z, top,
        text: broken ? 'разрушено' : hurt ? 'нужен ремонт' : 'на месте', tone: broken || hurt ? 'bad' : 'idle',
        base: block,
      });
    }
    for (const settler of Object.values(camp.settlers || {})) {
      if (!settler || settler.dead || seen.has('settler:' + settler.id)) continue;
      const view = g.npcV?.[settler.id];
      let x, y, z;
      if (vectors() && view?.root?.getWorldPosition && view.root.visible !== false) {
        view.root.getWorldPosition(tmp);
        x = tmp.x; y = tmp.y + 2.05; z = tmp.z;
      } else if (Number.isFinite(settler.pos?.x)) {
        x = settler.pos.x; z = settler.pos.z; y = ground(x, z) + 2.05;
      } else continue;
      const state = settlerState(settler);
      pushAnchor(list, { kind: 'settler', id: settler.id, name: settler.name || 'Житель', x, y, z, text: state.text, tone: state.tone });
    }
    list.sort((a, b) => a.d2 - b.d2);
    return list.slice(0, MAX);
  }
  function stateLabel(state) { return { text: state.text, tone: state.tone }; }
  function defenseState(id) {
    const turret = window.terraDefense?.getState?.()?.turrets?.find(item => item.id === id);
    if (!turret) return { text: 'турель', tone: 'idle' };
    const tone = turret.state === 'online' ? 'ok' : turret.state === 'broken' || turret.state === 'empty' ? 'bad' : 'warn';
    return { text: turret.stateLabel || 'турель', tone };
  }
  function project(item) {
    const g = game();
    if (!g?.cam || !vec) return null;
    vec.set(item.x, item.y, item.z);
    vec.project(g.cam);
    if (vec.z < -1 || vec.z > 1) return null;
    const w = g.W || innerWidth, h = g.H || innerHeight;
    const x = (vec.x * 0.5 + 0.5) * w, y = (-vec.y * 0.5 + 0.5) * h;
    if (x < -40 || y < -40 || x > w + 40 || y > h + 40) return null;
    return { x, y };
  }
  function hudBlocks(x, y) {
    const w = innerWidth, h = innerHeight;
    const touch = document.body.classList.contains('touchUI') || document.body.classList.contains('building');
    if (touch && y > h - 120) return true;
    if (x > w - 150 && y < 168) return true;
    if (x < 210 && y < 118) return true;
    if (!touch && y > h - 96 && (x < 180 || x > w - 250)) return true;
    return false;
  }
  function fitTag(button, x, y) {
    const margin = 8;
    button.style.left = x + 'px';
    button.style.top = y + 'px';
    const rect = button.getBoundingClientRect();
    let dx = 0, dy = 0;
    if (rect.left < margin) dx = margin - rect.left;
    else if (rect.right > innerWidth - margin) dx = innerWidth - margin - rect.right;
    if (rect.top < margin) dy = margin - rect.top;
    else if (rect.bottom > innerHeight - margin) dy = innerHeight - margin - rect.bottom;
    if (dx || dy) {
      button.style.left = (x + dx) + 'px';
      button.style.top = (y + dy) + 'px';
    }
  }
  function tagFor(item) {
    let button = tags.get(item.key);
    if (!button) {
      button = document.createElement('button');
      button.type = 'button';
      button.className = 'campLiveTag';
      button.append(document.createElement('b'), document.createElement('i'));
      button.addEventListener('pointerdown', event => event.stopPropagation());
      button.addEventListener('click', () => openMenu(button._anchor));
      tags.set(item.key, button);
      layer.append(button);
    }
    return button;
  }
  function paint() {
    const g = game();
    const show = g?.state === 'play' && !g.world?.inDungeon && !g.build?.on && !document.querySelector('.modal:not(.hidden), .screen:not(.hidden)');
    const live = show ? anchors : [];
    const used = new Set();
    for (const item of live) {
      const pos = project(item);
      const button = tagFor(item);
      used.add(item.key);
      button._anchor = item;
      if (!pos || pos.x < 0 || pos.y < 0 || pos.x > innerWidth || pos.y > innerHeight || hudBlocks(pos.x, pos.y)) {
        button.hidden = true;
        continue;
      }
      button.hidden = false;
      button.dataset.tone = item.tone || 'idle';
      button.dataset.kind = item.kind;
      fitTag(button, pos.x, pos.y);
      const title = button.firstChild, status = title.nextSibling;
      if (title.textContent !== item.name) title.textContent = item.name;
      if (status.textContent !== item.text) status.textContent = item.text;
      const label = item.name + ', ' + item.text;
      if (button.getAttribute('aria-label') !== label) button.setAttribute('aria-label', label);
    }
    for (const [key, button] of tags) if (!used.has(key)) button.hidden = true;
    styleGhost();
    paintPlace();
  }
  function styleGhost() {
    const mat = game()?.ghostMat;
    if (!mat || mat._campLive) return;
    mat.wireframe = true;
    mat.depthWrite = false;
    mat.transparent = true;
    const set = mat.color.set.bind(mat.color);
    // Штатный кадр красит призрак сам. Подменяем оттенок на чертёжный: синий — можно, красный — нельзя.
    mat.color.set = function () {
      return set(game()?.build?.err ? 0xe25b4a : 0x7eb6ff);
    };
    mat._campLive = true;
  }
  function paintPlace() {
    const g = game();
    installGhostHook(g);
    if (selectedCell && !selectedCurrent()) selectedCell = null;
    const on = !!(g?.build?.on && g.state === 'play' && g.build.sel !== 'warehouse' && !document.body.classList.contains('settlementPlacing'));
    document.body.classList.toggle('campLiveBuilding', on);
    if (!place) return;
    place.hidden = !on;
    aim.hidden = !on;
    if (!on) { selectedCell = null; setAim(false); return; }
    const bad = !!g.build.err;
    const confirm = place.querySelector('[data-act="confirm"]');
    confirm.dataset.valid = bad ? '0' : '1';
    confirm.setAttribute('aria-label', bad ? 'Поставить нельзя: ' + g.build.err : 'Поставить постройку');
    const hint = place.querySelector('small');
    const text = g.build.err || 'Синий чертёж — место свободно';
    if (hint.textContent !== text) hint.textContent = text;
  }
  function setAim(on, x, y) {
    aiming = on;
    window.TERRA_CAMP_GHOST_AIM = on;
    const g = game();
    if (!g?.mouse) return;
    if (on) { g.mouse.x = x; g.mouse.y = y; g.mouse.has = true; g.mouse.down = false; }
    else if (g.touchSeen) g.mouse.has = false;
  }
  function openPanel(tab) {
    const g = game();
    const panel = g?.ui?.campPanel;
    if (!panel) return;
    if (g.state === 'play') panel.open();
    panel.select(tab);
  }
  function openTarget(tab, selector, activate = false) {
    const owner = session(), g = owner.game;
    const native = g?.ui?.campPanel, root = native?.root;
    if (!root) return;
    openPanel(tab);
    closeMenu();
    const ready = () => game() === g && g.p === owner.player && g.world === owner.world &&
      g.p?.alive && g.state === 'modal' && !g.world?.inDungeon && !g.dungeonTransition &&
      !root.classList.contains('hidden') &&
      native.tab === tab && (!window.terraCampUI || window.terraCampUI.tab === tab);
    // Let the native section and its progressive enhancements finish first.
    requestAnimationFrame(() => {
      if (!ready()) return;
      const node = root.querySelector(selector);
      if (!node || node.closest('[inert]')) return;
      if (activate && root.querySelector('#residentSearchInput')?.value) {
        root.querySelector('.residentSearch button')?.click();
      }
      // Clearing search also updates the dossier's filtered paging order.
      requestAnimationFrame(() => {
        if (!ready() || !node.isConnected || !root.contains(node) || node.disabled ||
            node.closest('[inert]') || !node.getClientRects().length) return;
        if (activate) node.click();
        else {
          if (!node.hasAttribute('tabindex')) node.tabIndex = -1;
          node.classList.add('campLiveTarget');
          node.focus({ preventScroll: true });
          node.scrollIntoView({ block: 'center', inline: 'nearest' });
        }
      });
    });
  }
  function tell(result) {
    if (result?.ok) { closeMenu(); return; }
    if (!note) return;
    note.hidden = false;
    note.textContent = why(result?.reason);
  }
  function actionsFor(item) {
    const g = game();
    if (!item || !g) return [];
    if (item.kind === 'settler') {
      const run = (job, detail) => () => tell(g.camp?.assign?.(item.id, job, detail));
      return [
        { label: 'Дело', run: () => openTarget('settlers', `[data-resident="${CSS.escape(item.id)}"]`, true) },
        { label: 'Отдых', run: run('idle') },
        { label: 'Дерево', run: run('gather:wood') },
        { label: 'Вода', run: run('gather:water') },
      ];
    }
    if (item.kind === 'defense') {
      const api = window.terraDefense;
      const order = (method) => () => { const result = api?.[method]?.(item.id); tell(result); if (result?.ok) closeMenu(); };
      return [
        { label: 'Карточка', run: () => openTarget('defense', `[data-defense-id="${CSS.escape(item.id)}"]`) },
        { label: 'Починить', run: order('repair') },
        { label: 'Зарядить', run: order('reload') },
        { label: 'Улучшить', run: order('upgrade') },
      ];
    }
    if (item.decor) return [{ label: 'Лагерь', run: () => { openPanel('overview'); closeMenu(); } }];
    if (item.base) {
      const list = [];
      const dist = Math.hypot(item.x - g.p.x, item.z - g.p.z);
      if (dist < 2.4 && typeof g.useBlock === 'function') list.push({ label: 'Открыть', run: () => { g.useBlock(item.base); closeMenu(); } });
      list.push({ label: 'Строить', run: () => { g.toggleBuild?.(true); if (g.build) g.build.sel = item.base.t; g.renderBuildBar?.(); closeMenu(); } });
      return list;
    }
    return [
      { label: 'Чертёж', run: () => openTarget('build', `.campCard[data-building="${CSS.escape(item.id)}"]`) },
      { label: 'Улучшить', run: () => tell(g.camp?.upgrade?.(item.id)) },
      { label: 'Жители', run: () => { openPanel('settlers'); closeMenu(); } },
    ];
  }
  function closeMenu() {
    menu?.remove(); back?.remove();
    menu = null; menuOwner = null; back = null; note = null;
  }
  function openMenu(item) {
    if (!item || !current(session())) return;
    closeMenu();
    const acts = actionsFor(item);
    if (!acts.length) return;
    const owner = menuOwner = session();
    back = document.createElement('button');
    back.id = 'campLiveBack';
    back.type = 'button';
    back.setAttribute('aria-label', 'Закрыть меню');
    back.addEventListener('pointerdown', event => event.stopPropagation());
    back.addEventListener('click', closeMenu);
    menu = document.createElement('div');
    menu.id = 'campLiveMenu';
    menu.setAttribute('role', 'menu');
    menu.setAttribute('aria-label', item.name);
    const buttons = [];
    const close = document.createElement('button');
    close.type = 'button';
    close.className = 'campLiveClose';
    close.textContent = '✕';
    close.setAttribute('aria-label', 'Закрыть');
    close.addEventListener('click', closeMenu);
    menu.append(close);
    buttons.push(close);
    for (const act of acts) {
      const button = document.createElement('button');
      button.type = 'button';
      button.setAttribute('role', 'menuitem');
      const span = document.createElement('span');
      span.textContent = act.label;
      button.append(span);
      button.setAttribute('aria-label', item.name + ': ' + act.label);
      button.addEventListener('pointerdown', event => event.stopPropagation());
      button.addEventListener('click', () => {
        if (owner !== menuOwner) return;
        if (!current(owner)) { closeMenu(); return; }
        act.run();
      });
      menu.append(button);
      buttons.push(button);
    }
    note = document.createElement('div');
    note.id = 'campLiveNote';
    note.hidden = true;
    menu.append(note);
    document.body.append(back, menu);
    layoutMenu(item, buttons);
    close.focus({ preventScroll: true });
  }
  function layoutMenu(item, buttons) {
    const pos = project(item) || { x: innerWidth / 2, y: innerHeight / 2 };
    const short = innerHeight < 520 || innerWidth < 420;
    if (short) {
      menu.classList.add('is-stack');
      const rect = menu.getBoundingClientRect();
      const left = Math.min(Math.max(12, pos.x - rect.width / 2), Math.max(12, innerWidth - rect.width - 12));
      const top = Math.min(Math.max(12, pos.y - rect.height - 8), Math.max(12, innerHeight - rect.height - 12));
      menu.style.left = left + 'px';
      menu.style.top = top + 'px';
      return;
    }
    const radius = 78;
    const size = radius * 2 + 72;
    const count = buttons.length;
    buttons.forEach((button, index) => {
      const angle = -Math.PI / 2 + index * (Math.PI * 2 / count);
      button.style.left = (size / 2 - 32 + Math.cos(angle) * radius) + 'px';
      button.style.top = (size / 2 - 32 + Math.sin(angle) * radius) + 'px';
    });
    const left = Math.max(8, Math.min(pos.x - size / 2, innerWidth - size - 8));
    const top = Math.max(8, Math.min(pos.y - size / 2, innerHeight - size - 120));
    menu.style.left = left + 'px';
    menu.style.top = top + 'px';
    menu.style.width = size + 'px';
    menu.style.height = size + 'px';
  }
  function ensurePlace() {
    aim = document.createElement('div');
    aim.id = 'campLiveAim';
    aim.hidden = true;
    aim.tabIndex = 0;
    aim.setAttribute('aria-label', 'Вести чертёж постройки');
    const hint = document.createElement('span');
    hint.textContent = 'Ведите чертёж';
    aim.append(hint);
    const point = event => setAim(true, event.clientX, event.clientY);
    aim.addEventListener('pointerdown', event => {
      if (event.button > 0) return;
      if (!current(session()) || !game()?.build?.on) return;
      selectedCell = null;
      event.preventDefault();
      event.stopPropagation();
      aim.setPointerCapture?.(event.pointerId);
      point(event);
    });
    aim.addEventListener('pointermove', event => { if (aiming) { event.preventDefault(); point(event); } });
    aim.addEventListener('pointerup', () => {
      const g = game();
      if (aiming && current(session()) && g?.build?.on) {
        const point = g.ghostPos?.();
        if (Number.isFinite(point?.x) && Number.isFinite(point?.z)) {
          selectedCell = { owner: session(g), sel: g.build.sel, rot: g.build.rot,
            demo: g.build.demo, point: { ...point } };
        }
      }
      setAim(false);
    });
    const cancelAim = () => { if (aiming) selectedCell = null; setAim(false); };
    aim.addEventListener('pointercancel', cancelAim);
    aim.addEventListener('lostpointercapture', cancelAim);
    place = document.createElement('div');
    place.id = 'campLivePlace';
    place.hidden = true;
    const confirm = document.createElement('button');
    confirm.type = 'button';
    confirm.dataset.act = 'confirm';
    confirm.textContent = 'Поставить';
    confirm.addEventListener('pointerdown', event => event.stopPropagation());
    confirm.addEventListener('click', () => {
      if (!current(session()) || !game()?.build?.on) return;
      // Refresh the native candidate from the pinned cell immediately before committing.
      const g = game();
      if (selectedCurrent()) {
        const point = g.ghostPos();
        g.build.gx = point.x; g.build.gz = point.z; g.build.gy = point.y;
      }
      g.buildAction?.();
      selectedCell = null;
    });
    const cancel = document.createElement('button');
    cancel.type = 'button';
    cancel.dataset.act = 'cancel';
    cancel.textContent = 'Отмена';
    cancel.setAttribute('aria-label', 'Отменить строительство');
    cancel.addEventListener('pointerdown', event => event.stopPropagation());
    cancel.addEventListener('click', () => { selectedCell = null; setAim(false); game()?.toggleBuild?.(false); });
    const status = document.createElement('small');
    status.setAttribute('role', 'status');
    place.append(confirm, cancel, status);
    document.body.append(aim, place);
  }
  function pick(x, y) {
    const g = game();
    if (!g?.ray || !g.cam || !anchors.length) return null;
    g.ray.setFromCamera({ x: (x / (g.W || innerWidth)) * 2 - 1, y: -((y / (g.H || innerHeight)) * 2 - 1) }, g.cam);
    const origin = g.ray.ray.origin, dir = g.ray.ray.direction;
    let best = null, bestT = 1e9;
    for (const item of anchors) {
      const vx = item.x - origin.x, vy = item.y - origin.y, vz = item.z - origin.z;
      const t = vx * dir.x + vy * dir.y + vz * dir.z;
      if (t < 0.4 || t > 42) continue;
      const dist = Math.hypot(item.x - (origin.x + dir.x * t), item.y - (origin.y + dir.y * t), item.z - (origin.z + dir.z * t));
      if (dist < 1.4 && t < bestT) { best = item; bestT = t; }
    }
    return best;
  }
  function onKey(event) {
    if (event.key === 'Escape' && menu) { event.preventDefault(); event.stopPropagation(); closeMenu(); }
  }
  function onPointerDown(event) {
    if (!current(session())) return;
    if (event.pointerType === 'touch' || event.button > 0 || menu || aim?.contains(event.target)) return;
    if (event.target.closest?.('#campLiveLayer, #campLivePlace, #hud, #touch, #buildBar, button, a')) return;
    const hit = pick(event.clientX, event.clientY);
    if (!hit) return;
    pickDown = { id: event.pointerId, x: event.clientX, y: event.clientY, hit, owner: session() };
    event.preventDefault();
    event.stopPropagation();
  }
  function onPointerUp(event) {
    if (!pickDown || pickDown.id !== event.pointerId) return;
    if (!current(pickDown.owner)) { pickDown = null; return; }
    const hit = pickDown.hit;
    const moved = Math.hypot(event.clientX - pickDown.x, event.clientY - pickDown.y);
    pickDown = null;
    if (moved < 10) openMenu(hit);
  }
  function tick(now) {
    const g = game();
    if (menu && !current(menuOwner)) closeMenu();
    if (selectedCell && !selectedCurrent()) selectedCell = null;
    if (!g?.p || g.state !== 'play' || document.hidden) { anchors = []; paint(); return; }
    if (now - lastCollect > 180) { lastCollect = now; anchors = collect(); }
    paint();
  }
  function frame(now) {
    requestAnimationFrame(frame);
    if (now - frame.last < 90) return;
    frame.last = now;
    try { tick(now); } catch (error) { console.error('[camp-live]', error); }
  }
  frame.last = 0;

  function start() {
    if (!document.body || window.terraCampLive) return;
    document.body.append(layer);
    ensurePlace();
    window.addEventListener('keydown', onKey, true);
    window.addEventListener('pointerdown', onPointerDown, true);
    window.addEventListener('pointerup', onPointerUp, true);
    window.addEventListener('blur', () => { selectedCell = null; pickDown = null; setAim(false); closeMenu(); });
    window.terraCampLive = Object.freeze({
      version: 1,
      anchors: () => anchors.map(item => ({ key: item.key, kind: item.kind, id: item.id, name: item.name, text: item.text, tone: item.tone, x: item.x, z: item.z })),
    });
    requestAnimationFrame(frame);
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, { once: true });
})();
