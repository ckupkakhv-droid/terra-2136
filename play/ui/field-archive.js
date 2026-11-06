/* Полевой архив: короткие записи о спусках, где игрок уже был.
 * Объявление на входе помнится только в этом заходе. Название, код и выход
 * после загрузки берутся из уже существующих dungeonContainers и tps.
 * Новых полей profile, camp и fieldCompanion нет.
 */
(() => {
  'use strict';
  const MAX = 5;
  // Южный коллектор: play/ui/sewers.js, вход 12,−10 и лестница первого сектора.
  const COLLECTOR = {key: '12,-10', name: 'Канализация · Южный коллектор', exit: 'Лестница на поверхность'};
  const METRO_EXIT = 'Выход в город';
  const memory = new WeakMap();
  const wrapped = new WeakSet();

  function clean(value) {
    return String(value || '').replace(/\s+/g, ' ').trim().slice(0, 180);
  }
  function sentence(value) {
    const text = clean(value);
    return /[.!?…]$/u.test(text) ? text : text + '.';
  }
  function listFor(player) {
    if (!player || typeof player !== 'object') return [];
    let list = memory.get(player);
    if (!list) memory.set(player, list = []);
    return list;
  }
  function samePlace(title, name) {
    return title.toLocaleLowerCase('ru') === name.toLocaleLowerCase('ru');
  }
  function announced(name) {
    const banner = document.getElementById('banner');
    const small = banner?.querySelector('small');
    const line = clean(small?.textContent || '');
    if (!banner || !line) return '';
    const title = clean(banner.textContent.replace(small.textContent, ''));
    return samePlace(title, name) ? line : '';
  }
  function remember(game) {
    const player = game?.p;
    const dungeon = game?.dg;
    if (!player || !dungeon || !game.world?.inDungeon) return;
    const key = dungeon.key;
    const name = clean(dungeon.name);
    if (!name || typeof key !== 'string' || !/^-?\d{1,6},-?\d{1,6}$/.test(key)) return;
    const list = listFor(player);
    let row = list.find(item => item.key === key);
    const threat = announced(name);
    const exit = (game.world.ents || []).find(item => item?.kind === 'exit' && item.name &&
      Math.hypot(player.x - item.x, player.z - item.z) < 14);
    const exitName = exit ? clean(exit.name) : '';
    if (!row) {
      if (list.length >= MAX || (!threat && !exitName)) return;
      row = {key, name, threat: '', exit: ''};
      list.push(row);
    }
    if (!row.threat && threat) row.threat = threat;
    if (!row.exit && exitName) row.exit = exitName;
    const button = document.getElementById('fieldArchiveOpen');
    const label = 'Полевой архив · ' + rows(player).length;
    if (button && button.textContent !== label) button.textContent = label;
  }
  function namedPlace(player, key) {
    if (key === COLLECTOR.key) return {name: COLLECTOR.name, exit: COLLECTOR.exit};
    const [x, z] = key.split(',').map(Number);
    let best = null;
    let gap = Infinity;
    for (const point of Object.values(player.tps || {})) {
      if (!point || point.type !== 'metro' || typeof point.name !== 'string') continue;
      const dx = Math.abs(point.x - x);
      const dz = Math.abs(point.z - z - 3.5);
      if (dx > 2 || dz > 1) continue;
      const score = dx + dz;
      if (score < gap) { gap = score; best = point; }
    }
    return best ? {name: clean(best.name), exit: METRO_EXIT} : null;
  }
  // Игра уже пишет код и тему в dungeonContainers на выходе. Строки баннера там нет.
  function remembered(player) {
    const domains = player?.dungeonContainers?.domains;
    if (!domains || typeof domains !== 'object') return [];
    const rows = [];
    for (const [key, domain] of Object.entries(domains)) {
      if (!domain || domain.theme !== 'metro' || !/^-?\d{1,6},-?\d{1,6}$/.test(key)) continue;
      const place = namedPlace(player, key);
      if (!place?.name) continue;
      rows.push({key, name: place.name, threat: '', exit: place.exit || ''});
      if (rows.length >= MAX) break;
    }
    return rows;
  }
  function rows(player) {
    const session = listFor(player);
    const seen = new Set(session.map(item => item.key));
    const all = session.slice();
    for (const row of remembered(player)) {
      if (seen.has(row.key) || all.length >= MAX) continue;
      all.push(row);
      seen.add(row.key);
    }
    return all;
  }
  function watch(game) {
    if (!game || wrapped.has(game) || typeof game.loop !== 'function') return;
    const loop = game.loop;
    game.loop = function (time) {
      try { remember(this); } catch (error) { console.error('[field-archive]', error); }
      return loop.call(this, time);
    };
    wrapped.add(game);
  }

  function sheet() {
    let root = document.getElementById('fieldArchive');
    if (root) return root;
    root = document.createElement('section');
    root.id = 'fieldArchive';
    root.className = 'modal hidden';
    root.setAttribute('role', 'dialog');
    root.setAttribute('aria-modal', 'true');
    root.setAttribute('aria-labelledby', 'fieldArchiveTitle');
    root.innerHTML = '<div class="win fieldArchiveSheet"><h2><span id="fieldArchiveTitle">Полевой архив</span><button type="button" class="x" id="fieldArchiveClose" aria-label="Закрыть полевой архив">×</button></h2><p class="fieldArchiveLimit">Название, код и выход игра помнит после загрузки. Строка объявления живёт только до неё: в сохранении для неё нет поля.</p><div id="fieldArchiveBody" tabindex="-1"></div></div>';
    document.body.append(root);
    root.querySelector('#fieldArchiveClose').addEventListener('click', event => { event.stopPropagation(); close(true); });
    root.addEventListener('pointerdown', event => event.stopPropagation());
    root.addEventListener('click', event => { if (event.target === root) close(true); });
    return root;
  }
  function render(root) {
    const body = root.querySelector('#fieldArchiveBody');
    const list = rows(window.game?.p);
    body.replaceChildren();
    if (!list.length) {
      const empty = document.createElement('p');
      empty.className = 'fieldArchiveEmpty';
      empty.textContent = 'В этом заходе спусков ещё нет. Запись появится после входа туда, где вы уже стояли у выхода.';
      body.append(empty);
      return;
    }
    for (const row of list) {
      const card = document.createElement('article');
      card.className = 'fieldArchiveCard';
      card.dataset.archiveKey = row.key;
      const title = document.createElement('h3');
      title.textContent = row.name;
      const code = document.createElement('p');
      code.textContent = 'Код спуска: ' + row.key + '.';
      card.append(title, code);
      if (row.threat) {
        const threat = document.createElement('p');
        threat.textContent = 'На спуске объявили: ' + sentence(row.threat);
        card.append(threat);
      }
      if (row.exit) {
        const exit = document.createElement('p');
        exit.textContent = 'Выход этой вылазки: ' + sentence(row.exit);
        card.append(exit);
      }
      body.append(card);
    }
    if (list.length >= MAX) {
      const full = document.createElement('p');
      full.className = 'fieldArchiveLimit';
      full.textContent = 'Дальше лист не берёт: пять записей за заход.';
      body.append(full);
    }
  }
  let returnFocus = null;
  let inert = [];
  function open() {
    const root = sheet();
    if (!root.classList.contains('hidden')) return;
    const game = window.game;
    if (!game || game.state !== 'modal' || document.getElementById('inv')?.classList.contains('hidden')) return;
    render(root);
    inert = ['inv', 'hud'].map(id => document.getElementById(id)).filter(Boolean).map(element => [element, element.inert]);
    for (const [element] of inert) element.inert = true;
    returnFocus = document.activeElement;
    root.classList.remove('hidden');
    root.querySelector('#fieldArchiveClose').focus();
  }
  function close(restore) {
    const root = document.getElementById('fieldArchive');
    if (!root || root.classList.contains('hidden')) return;
    root.classList.add('hidden');
    for (const [element, value] of inert) element.inert = value;
    inert = [];
    const button = document.getElementById('fieldArchiveOpen');
    if (restore && button) button.focus();
    else if (restore && returnFocus?.isConnected) returnFocus.focus();
    returnFocus = null;
  }
  function targets() {
    return [...sheet().querySelectorAll('button')].filter(element => element.getClientRects().length);
  }
  window.addEventListener('keydown', event => {
    const root = document.getElementById('fieldArchive');
    if (!root || root.classList.contains('hidden')) return;
    if (window.game?.state !== 'modal' || document.getElementById('inv')?.classList.contains('hidden')) { close(false); return; }
    if (event.key === 'Escape') { event.preventDefault(); event.stopImmediatePropagation(); close(true); return; }
    if (event.key !== 'Tab') return;
    const items = targets();
    if (!items.length) return;
    event.preventDefault();
    event.stopImmediatePropagation();
    const index = items.indexOf(document.activeElement);
    items[(index + (event.shiftKey ? -1 : 1) + items.length) % items.length].focus();
  }, true);

  function mount() {
    const body = document.getElementById('invBody');
    const tab = document.querySelector('#inv [data-tab="log"].on');
    if (!body || !tab || document.getElementById('inv')?.classList.contains('hidden')) return;
    let button = body.querySelector('#fieldArchiveOpen');
    const label = 'Полевой архив · ' + rows(window.game?.p).length;
    if (!button) {
      button = document.createElement('button');
      button.id = 'fieldArchiveOpen';
      button.type = 'button';
      button.className = 'fieldArchiveOpen';
      button.setAttribute('aria-haspopup', 'dialog');
      button.setAttribute('aria-controls', 'fieldArchive');
      button.addEventListener('pointerdown', event => event.stopPropagation());
      button.addEventListener('click', event => { event.preventDefault(); event.stopPropagation(); open(); });
      body.prepend(button);
    }
    if (button.textContent !== label) button.textContent = label;
  }
  function start() {
    watch(window.game);
    sheet();
    const body = document.getElementById('invBody');
    const inv = document.getElementById('inv');
    if (!body || !inv) return;
    let queued = false;
    const schedule = () => { if (!queued) { queued = true; queueMicrotask(() => { queued = false; mount(); }); } };
    new MutationObserver(schedule).observe(body, {childList: true});
    new MutationObserver(() => { if (inv.classList.contains('hidden')) close(false); else schedule(); }).observe(inv, {attributes: true, attributeFilter: ['class']});
    schedule();
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, {once: true});
})();
