/* Осмотр конкретного ствола в уже открытом рюкзаке.
   Карточка читает выбранный uid, wname и wstat. Надевание — прежние data-act.
   Файл не пишет сохранение. ?weaponcard=0 выключает слой. */
(() => {
  'use strict';
  if (new URLSearchParams(location.search).get('weaponcard') === '0') return;

  const NS = 'http://www.w3.org/2000/svg';
  const RARITY = ['Обычная', 'Редкая', 'Очень редкая', 'Особая', 'Уникальная', 'Легендарная', 'Реликтовая'];
  const GRADE = ['F', 'D', 'C', 'B', 'A', 'S', 'S80'];
  const KIND = {
    stick: 'melee', club: 'melee', machete: 'melee', katana: 'melee', greatsword: 'melee', spear: 'melee',
    revolver: 'gun', shotgun: 'gun', rifle: 'gun', railgun: 'gun',
    drone: 'module', turret: 'module',
  };
  const KIND_LABEL = { melee: 'ближний бой', gun: 'огнестрел', module: 'модуль' };
  const SCHEME = {
    stick: 'M8 30 L28 8',
    club: 'M8 30 L26 12 M26 12 h8 v8',
    machete: 'M6 30 L46 8 L50 12 L10 34 Z',
    katana: 'M8 32 Q30 18 54 6',
    greatsword: 'M8 32 L40 6 L48 12 L16 36 Z',
    spear: 'M6 32 L44 8 M44 8 L54 4 L46 14',
    revolver: 'M6 22 H30 M26 22 a5 5 0 1 0 .1 0 M34 20 H54',
    shotgun: 'M4 16 H60 M4 24 H60',
    rifle: 'M4 20 H60 M36 20 v8 h10 v-8 M8 20 v6 h12',
    railgun: 'M6 14 H58 M6 26 H58 M16 14 V26 M46 14 V26',
    drone: 'M32 4 L54 18 L32 32 L10 18 Z',
    turret: 'M8 24 H36 V16 H52 V24 M14 24 V32 H30 V24',
  };
  const AFFIX = {
    bleed: v => '🩸 ' + Math.round(v * 100) + '%/с',
    fire: v => '🔥 ' + Math.round(v * 100) + '%',
    shock: v => 'ϟ ' + Math.round(v * 100) + '%',
    slow: v => '❄ −' + Math.round(v * 100) + '%',
    crit: v => '◎ +' + Math.round(v * 100) + '%',
    leech: v => '♥ ' + Math.round(v * 100) + '%',
    chain: v => '⚡ ' + Math.round(v * 100) + '%',
    explode: v => '✹ ' + Math.round(v * 100) + '%',
    speed: v => '+' + Math.round(v * 100) + '% скорость',
    range: v => '+' + Math.round(v * 100) + '% дальность',
    dmg: v => '+' + Math.round(v * 100) + '% урон',
  };

  let open = false;
  let needFocus = false;
  let painting = false;

  const game = () => window.game || null;

  function weaponOf(uid) {
    const list = game()?.p?.weapons;
    if (!Array.isArray(list)) return null;
    return list.find(item => item && item.uid === uid) || null;
  }

  function el(tag, cls) {
    const node = document.createElement(tag);
    if (cls) node.className = cls;
    return node;
  }

  function scheme(kind) {
    const svg = document.createElementNS(NS, 'svg');
    svg.setAttribute('viewBox', '0 0 64 36');
    svg.setAttribute('aria-hidden', 'true');
    const path = document.createElementNS(NS, 'path');
    path.setAttribute('d', SCHEME[kind] || 'M4 8 H60 V28 H4 Z');
    path.setAttribute('fill', 'none');
    path.setAttribute('stroke', 'currentColor');
    path.setAttribute('stroke-width', '1.7');
    path.setAttribute('stroke-linejoin', 'round');
    path.setAttribute('stroke-linecap', 'round');
    svg.append(path);
    return svg;
  }

  function typeName(g, item) {
    const full = String(g.wname(item));
    const prefix = item.e ? '+' + item.e + ' ' : '';
    let rest = full.startsWith(prefix) ? full.slice(prefix.length) : full;
    const stamp = item.nm == null ? '' : String(item.nm);
    if (stamp && rest.endsWith(stamp)) rest = rest.slice(0, rest.length - stamp.length).trim();
    return rest || String(item.wt || '');
  }

  function place(g, item) {
    const eq = Array.isArray(g.p.eq) ? g.p.eq : [];
    const slot = eq.findIndex(w => w && w.uid === item.uid);
    if (slot >= 0) return 'слот ' + (slot + 1);
    const mod = g.p.mods && g.p.mods[item.wt];
    if (mod && mod.uid === item.uid) return 'модуль установлен';
    return 'в рюкзаке';
  }

  function affixLine(item) {
    if (!Array.isArray(item.aff) || !item.aff.length) return '';
    return item.aff.map(entry => {
      if (!entry || entry.id == null) return '';
      const fmt = AFFIX[entry.id];
      return fmt ? fmt(Number(entry.v) || 0) : entry.id + ' ' + entry.v;
    }).filter(Boolean).join(' · ');
  }

  function statRows(item, st, kind) {
    const rows = [
      ['Урон', 'dmg', Math.round(st.dmg) + (st.pellets > 1 ? ' ×' + st.pellets : '')],
      ['Скорость', 'speed', (st.rate > 0 ? (1 / st.rate).toFixed(1) : '—') + '/с'],
    ];
    if (kind === 'melee') {
      rows.push(['Дальность', 'reach', Number(st.reach).toFixed(1) + ' м']);
      rows.push(['Дуга', 'arc', Math.round(st.arc * 57) + '°']);
    } else if (kind === 'gun') {
      rows.push(['Магазин', 'mag', String(st.mag)]);
      rows.push(['Перезарядка', 'reload', Number(st.reload).toFixed(1) + ' с']);
    } else if (kind === 'module') {
      rows.push(['Радиус', 'range', Number(st.range).toFixed(0) + ' м']);
    }
    rows.push(['Крит', 'crit', Math.round((st.crit || 0) * 100) + '%']);
    if (Number.isFinite(st.ml)) rows.push(['Мастерство', 'ml', st.ml + '/10']);
    return rows;
  }

  function shell() {
    const card = el('section', 'wi-card');
    card.id = 'weaponInspect';
    card.setAttribute('role', 'region');
    card.setAttribute('aria-labelledby', 'weaponInspectTitle');
    const kicker = el('p', 'wi-kicker');
    kicker.textContent = 'Осмотр';
    const top = el('div', 'wi-top');
    const figure = el('figure', 'wi-scheme');
    figure.setAttribute('aria-label', 'Схема типа');
    const caption = el('figcaption');
    caption.textContent = 'схема';
    figure.append(caption);
    const id = el('div', 'wi-id');
    const title = el('h3');
    title.id = 'weaponInspectTitle';
    title.dataset.wi = 'name';
    const type = el('p');
    type.dataset.wi = 'type';
    const state = el('p');
    state.dataset.wi = 'state';
    const uid = el('p');
    uid.dataset.wi = 'uid';
    id.append(title, type, state, uid);
    const close = el('button', 'wi-close');
    close.type = 'button';
    close.textContent = 'Закрыть';
    close.setAttribute('aria-label', 'Закрыть осмотр');
    top.append(figure, id, close);
    const stats = el('dl', 'wi-stats');
    const aff = el('p', 'wi-aff');
    aff.dataset.wi = 'aff';
    const acts = el('div', 'wi-acts');
    card.append(kicker, top, stats, aff, acts);
    close.addEventListener('click', event => {
      event.preventDefault();
      event.stopPropagation();
      closeCard(true);
    });
    return card;
  }

  function fill(card, item) {
    const g = game();
    const st = g.wstat(item);
    const kind = KIND[item.wt] || '';
    const name = String(g.wname(item));
    const type = typeName(g, item);
    const rarity = RARITY[item.r] || ('редкость ' + item.r);
    const grade = GRADE[item.g] || String(item.g);
    const enchant = Number.isFinite(item.e) ? item.e : 0;
    const kindLabel = KIND_LABEL[kind] || String(item.wt || '');
    card.dataset.weaponUid = String(item.uid);
    card.dataset.weaponWt = String(item.wt || '');
    card.querySelector('[data-wi="name"]').textContent = name;
    card.querySelector('[data-wi="type"]').textContent = 'Тип: ' + type + (kindLabel ? ' · ' + kindLabel : '');
    const ammo = kind === 'gun' && Number.isFinite(item.mag) ? ' · патроны ' + item.mag : '';
    card.querySelector('[data-wi="state"]').textContent =
      'Состояние: ' + rarity + ' · ранг ' + grade + ' · заточка +' + enchant + ' · ' + place(g, item) +
      (item.lock ? ' · защита' : ' · без замка') + ammo;
    card.querySelector('[data-wi="uid"]').textContent = 'Учёт № ' + item.uid;
    const figure = card.querySelector('.wi-scheme');
    figure.querySelector('svg')?.remove();
    figure.prepend(scheme(item.wt));
    const stats = card.querySelector('.wi-stats');
    stats.replaceChildren();
    for (const [label, key, value] of statRows(item, st, kind)) {
      const row = el('div', 'wi-row');
      const dt = el('dt');
      dt.textContent = label;
      const dd = el('dd');
      dd.dataset.wi = key;
      dd.textContent = value;
      row.append(dt, dd);
      stats.append(row);
    }
    const aff = affixLine(item);
    const affNode = card.querySelector('[data-wi="aff"]');
    affNode.hidden = !aff;
    affNode.textContent = aff;
    const box = card.querySelector('.wi-acts');
    box.replaceChildren();
    const detail = card.parentElement;
    const buttons = detail ? [...detail.querySelectorAll('.invEquip button[data-act]')].filter(button => !button.closest('#weaponInspect')) : [];
    for (const button of buttons) {
      const copy = el('button', 'btn sm wi-act');
      copy.type = 'button';
      copy.dataset.act = button.dataset.act;
      copy.textContent = button.textContent;
      if (button.disabled) {
        copy.disabled = true;
        copy.classList.add('dis');
      }
      box.append(copy);
    }
  }

  function paint(item) {
    const host = document.querySelector('#invBody .invDetail');
    if (!host) return false;
    let card = document.getElementById('weaponInspect');
    let created = false;
    if (!card || card.parentElement !== host) {
      card?.remove();
      card = shell();
      host.prepend(card);
      created = true;
    }
    fill(card, item);
    return created;
  }

  function closeCard(restore) {
    open = false;
    needFocus = false;
    document.getElementById('weaponInspect')?.remove();
    if (restore) document.querySelector('#invBody [data-inv-back]')?.focus({ preventScroll: true });
  }

  function sync() {
    if (painting || !open) return;
    const g = game();
    const ui = g?.ui;
    const inv = document.getElementById('inv');
    if (!g || !ui || !inv || inv.classList.contains('hidden') || ui.invDetail !== 'weapon') {
      open = false;
      document.getElementById('weaponInspect')?.remove();
      return;
    }
    const item = weaponOf(ui.sel);
    if (!item || typeof g.wname !== 'function' || typeof g.wstat !== 'function') {
      open = false;
      document.getElementById('weaponInspect')?.remove();
      return;
    }
    painting = true;
    try {
      const created = paint(item);
      const active = document.activeElement;
      const inside = !!(active && inv.contains(active));
      // Штатный renderInv снимает фокус вместе с кнопкой слота. Возвращаем его в карточку,
      // чтобы Escape по-прежнему закрывал осмотр, а не терялся на body.
      if ((needFocus && created) || !inside) {
        needFocus = false;
        document.querySelector('#weaponInspect .wi-close')?.focus({ preventScroll: true });
      }
      const tip = document.getElementById('bpTip');
      if (tip) tip.hidden = true;
    } finally {
      painting = false;
    }
  }

  function boot() {
    const inv = document.getElementById('inv');
    const body = document.getElementById('invBody');
    if (!inv || !body) return;
    body.addEventListener('click', event => {
      if (event.target.closest('.wi-close')) return;
      const select = event.target.closest('.tile[data-w], [data-equipment-weapon], [data-equipment-module]');
      const step = event.target.closest('[data-inv-step]');
      const act = event.target.closest('#weaponInspect [data-act]');
      if (select) {
        open = true;
        needFocus = true;
        queueMicrotask(sync);
      } else if (open && (step || act)) {
        queueMicrotask(sync);
      }
    });
    inv.addEventListener('keydown', event => {
      if (event.key !== 'Escape' || !document.getElementById('weaponInspect')) return;
      event.preventDefault();
      event.stopPropagation();
      closeCard(true);
    }, true);
    new MutationObserver(() => { if (open) sync(); }).observe(body, { childList: true });
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
