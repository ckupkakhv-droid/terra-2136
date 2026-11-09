/* Карточка напарника: те же кнопки и те же приказы.
   Новых полей сейва, отдельного боевого режима и команды брони нет.
   Стволы списка — классы gun текущего каталога: revolver, shotgun, rifle, railgun. */
(() => {
  'use strict';
  const PROFESSIONS = {scientist:'Учёный',engineer:'Инженер',medic:'Медик',scout:'Разведчик',builder:'Строитель',gatherer:'Собиратель',hauler:'Грузчик',guard:'Боец',farmer:'Фермер',crafter:'Мастер',gunsmith:'Оружейник',trader:'Торговец'};
  const GUNS = new Set(['revolver','shotgun','rifle','railgun']);
  const MODE = {follow:'За мной',wait:'Ждёт',return:'В лагерь'};
  const MODE_ACTS = ['recruit','follow','wait','return'];
  const NEAR_ACTS = ['pickup','unload','map'];
  const GEAR_ACTS = ['giveGun','takeGun','arm','resupply'];
  const el = (tag, cls, text) => { const n = document.createElement(tag); if (cls) n.className = cls; if (text != null) n.textContent = text; return n; };
  let armed = null;

  function people() { return window.game?.p?.camp?.settlers || null; }
  function residentFor(card) {
    const roster = people();
    if (!roster) return null;
    const root = card.closest('.campResidents');
    if (root?.querySelector(':scope > .residentIdentityHead')) {
      const id = root.querySelector('[data-resident-biography]')?.getAttribute('data-resident-biography')
        || root.querySelector('[data-resident-order]')?.getAttribute('data-resident-order');
      if (id && roster[id]) return roster[id];
    }
    const id = window.game?.p?.camp?.fieldCompanion?.settlerId;
    return id && roster[id] || null;
  }
  function modeOf(resident) {
    const state = window.game?.p?.camp?.fieldCompanion;
    return resident && state?.settlerId === resident.id && MODE[state.mode] ? state.mode : '';
  }
  function signature(card) {
    const acts = [...card.querySelectorAll('[data-companion-action]')].map(button => [button.dataset.companionAction, button.textContent, button.disabled ? 1 : 0].join(':')).join(';');
    const state = window.game?.p?.camp?.fieldCompanion;
    const resident = state && people()?.[state.settlerId];
    const carried = resident?.gear?.weapon;
    const pack = (window.game?.p?.weapons || []).map(item => item && typeof item === 'object' ? [item.uid, item.wt, item.nm, item.mag].join(':') : '').join(',');
    return [acts, state?.v, state?.mode, resident?.lvl, resident?.xp, resident?.prof, carried?.uid, carried?.wt, carried?.nm, carried?.mag, pack].join('|');
  }
  function isDefense(text) { return /Защита|не стреляет|Нет патронов|Ближний бой/.test(text || ''); }
  function isXp(text) { return /опыта|Высшее звание/.test(text || ''); }
  function isStatus(text) { return /Следует|Ждёт|Возвращается|Путь не загружен|Проход закрыт|В лагере|поверхности/.test(text || ''); }
  function itemName(item) { return typeof item?.nm === 'string' && item.nm.trim() ? item.nm.trim() : ''; }
  function isGun(item) { return !!item && typeof item === 'object' && GUNS.has(item.wt) && Number.isSafeInteger(item.uid) && item.uid > 0; }

  function weaponList(resident, giveName) {
    const carried = resident?.gear?.weapon;
    const rows = [];
    if (isGun(carried) || (carried && typeof carried === 'object' && itemName(carried) && Number.isFinite(carried.mag) && GUNS.has(carried.wt))) {
      rows.push({name: itemName(carried) || carried.wt, mag: carried.mag, where: 'у жителя', role: 'carried'});
    }
    let marked = false;
    for (const item of window.game?.p?.weapons || []) {
      if (!isGun(item) || !itemName(item)) continue;
      const chosen = !marked && !!giveName && itemName(item) === giveName;
      if (chosen) marked = true;
      rows.push({name: itemName(item), mag: item.mag, where: chosen ? 'этим стволом передаёт команда' : 'в рюкзаке', role: chosen ? 'chosen' : 'pack'});
    }
    if (!rows.length) return null;
    const list = el('ul', 'ccWeaponList');
    list.setAttribute('aria-label', 'Стволы без отдельной команды на каждый');
    for (const row of rows) {
      const line = el('li', 'ccWeapon' + (row.role === 'carried' ? ' ccWeapon-carried' : row.role === 'chosen' ? ' ccWeapon-chosen' : ''));
      const mag = Number.isSafeInteger(row.mag) ? ' · магазин ' + row.mag : '';
      line.textContent = row.name + mag + ' · ' + row.where;
      list.append(line);
    }
    return list;
  }

  function meterFor(xpNode) {
    const match = /([\d\s]+)\s*\/\s*([\d\s]+)/.exec((xpNode?.textContent || '').replace(/\u00a0/g, ' '));
    if (!match) return null;
    const now = Number(match[1].replace(/\s/g, '')), max = Number(match[2].replace(/\s/g, ''));
    if (!Number.isFinite(now) || !Number.isFinite(max) || max <= 0) return null;
    const meter = el('span', 'ccMeter');
    meter.setAttribute('role', 'meter');
    meter.setAttribute('aria-valuemin', '0');
    meter.setAttribute('aria-valuemax', String(max));
    meter.setAttribute('aria-valuenow', String(Math.min(now, max)));
    meter.setAttribute('aria-valuetext', now + ' из ' + max);
    meter.setAttribute('aria-label', 'Опыт: ' + now + ' из ' + max);
    const bar = el('i');
    bar.style.width = Math.max(0, Math.min(100, now / max * 100)) + '%';
    meter.append(bar);
    return meter;
  }

  function place(card) {
    const fold = card.parentElement?.classList?.contains('fbCompanionFold') ? card.parentElement : null;
    if (fold) fold.replaceWith(card);
    const board = document.querySelector('#campBody .fbHomeBoard');
    if (board && card.closest('.fbOverviewDetails')) {
      const supply = board.querySelector(':scope > .campSupply');
      if (supply) supply.after(card); else board.prepend(card);
    }
  }

  function dress(card) {
    const icons = {wait:'pause', return:'camp', pickup:'hand', map:'map', follow:'person', recruit:'person'};
    const short = {wait:'Ждать', return:'В лагерь', pickup:'Подобрать', map:'На карте', follow:'За мной'};
    for (const button of card.querySelectorAll('[data-companion-action]')) {
      const key = button.dataset.companionAction;
      if (short[key] && button.dataset.ccWord !== short[key]) {
        if (!button.dataset.ccFull) button.dataset.ccFull = button.textContent.replace(/\s+/g, ' ').trim();
        button.textContent = short[key];
        button.setAttribute('aria-label', button.dataset.ccFull || short[key]);
        button.dataset.ccWord = short[key];
      }
      if (!button.querySelector('.ccActMark') && icons[key]) {
        const src = document.querySelector('[data-ic="' + icons[key] + '"] svg');
        if (src) {
          const mark = document.createElement('i');
          mark.className = 'ccActMark';
          mark.setAttribute('aria-hidden', 'true');
          mark.append(src.cloneNode(true));
          button.prepend(mark);
        }
      }
      const block = button.closest('.companionAction');
      const small = block?.querySelector(':scope > small');
      if (small && block && !block.querySelector('.ccHint')) {
        const hint = document.createElement('details');
        hint.className = 'ccHint';
        const sum = document.createElement('summary');
        sum.textContent = 'Зачем';
        hint.append(sum, small);
        block.append(hint);
      }
    }
  }

  function paintCard(card) {
    place(card);
    const sig = signature(card);
    if (card.dataset.ccSig === sig && card.querySelector(':scope > .ccLayout')) {
      dress(card);
      window.terraArmory?.mountCard(card, residentFor(card));
      return;
    }
    const restore = armed && !armed.isConnected ? armed.dataset?.companionAction || '' : '';
    if (restore) armed = null;
    const resident = residentFor(card);
    const mode = modeOf(resident);
    const drawer = card.querySelector('.companionEquipment');
    const wasOpen = !!drawer?.open;
    const blocks = [...card.querySelectorAll('.companionAction')];
    const modeRow = el('div', 'ccModes');
    const nearRow = el('div', 'ccNear');
    const gearRow = el('div', 'ccGear');
    const otherRow = el('div', 'ccNear');
    modeRow.setAttribute('role', 'group');
    modeRow.setAttribute('aria-label', 'Режим вылазки');
    for (const block of blocks) {
      const action = block.querySelector('[data-companion-action]')?.dataset.companionAction || '';
      (MODE_ACTS.includes(action) ? modeRow : NEAR_ACTS.includes(action) ? nearRow : GEAR_ACTS.includes(action) ? gearRow : otherRow).append(block);
    }
    const header = card.querySelector('.companionHeader');
    const rank = card.querySelector('.companionRank');
    const training = card.querySelector('.companionTraining');
    const facts = card.querySelector('.companionFacts');
    const ranks = [...card.querySelectorAll('details')].find(node => node !== drawer && /Звания/.test(node.querySelector('summary')?.textContent || ''));
    const smalls = [...card.querySelectorAll('small')].filter(node => !node.closest('.companionAction') && !ranks?.contains(node) && !facts?.contains(node));
    const defense = smalls.find(node => isDefense(node.textContent));
    const xp = smalls.find(node => node !== defense && isXp(node.textContent));
    const status = smalls.find(node => node !== defense && node !== xp && isStatus(node.textContent));
    const face = el('div', 'ccFace');
    if (resident && window.terraCampFieldbook?.portrait) {
      const photo = el('span', 'ccPhoto');
      window.terraCampFieldbook.portrait(photo, resident);
      face.append(photo);
    }
    const info = el('div', 'ccId');
    if (header) info.append(header);
    const prof = PROFESSIONS[resident?.prof] || (typeof resident?.prof === 'string' ? resident.prof : '');
    if (prof) info.append(el('b', 'ccProf', prof));
    if (rank) info.append(rank);
    if (Number.isFinite(resident?.skills?.shoot)) info.append(el('span', 'ccShoot', 'Стрельба ' + resident.skills.shoot));
    const meter = meterFor(xp);
    if (meter) info.append(meter);
    if (xp) info.append(xp);
    if (training) info.append(training);
    if (mode) {
      const now = el('p', 'ccNow', MODE[mode]);
      now.dataset.companionMode = mode;
      now.setAttribute('aria-current', 'true');
      if (status?.textContent) now.title = status.textContent;
      info.append(now);
    }
    if (facts) info.append(facts);
    if (defense) { defense.classList.add('ccDefense'); info.append(defense); }
    if (status) { status.classList.add('ccStatus'); info.append(status); }
    if (info.childNodes.length) face.append(info);

    if (drawer) {
      drawer.classList.add('ccDrawer');
      drawer.querySelector(':scope > .ccWeaponList')?.remove();
      const give = gearRow.querySelector('[data-companion-action="giveGun"]');
      const giveName = (give?.textContent || '').replace(/^Передать:\s*/, '').trim();
      const list = weaponList(resident, giveName);
      const summary = drawer.querySelector('summary');
      const transfer = gearRow.querySelector('[data-companion-action="takeGun"], [data-companion-action="giveGun"]');
      if (summary && transfer?.textContent) summary.textContent = transfer.textContent;
      if (list) summary ? summary.after(list) : drawer.prepend(list);
      if (gearRow.childNodes.length) drawer.append(gearRow);
    }
    const layout = card.querySelector(':scope > .ccLayout') || el('div', 'ccLayout');
    const ordered = [face, modeRow.childNodes.length ? modeRow : null, nearRow.childNodes.length ? nearRow : null, drawer, !drawer && gearRow.childNodes.length ? gearRow : null, otherRow.childNodes.length ? otherRow : null, ranks].filter(Boolean);
    layout.replaceChildren(...ordered);
    if (!layout.isConnected) card.append(layout);
    const extra = el('div', 'ccExtra');
    for (const node of [...card.children]) {
      if (node === layout || node.tagName === 'STYLE') continue;
      if (!node.childNodes.length && node.matches('div')) continue;
      extra.append(node);
    }
    if (extra.childNodes.length) layout.append(extra);
    dress(card);
    card.classList.add('ccPilot');
    card.dataset.ccPilot = '1';
    card.dataset.ccSig = signature(card);
    if (drawer) drawer.open = wasOpen;
    window.terraArmory?.mountCard(card, resident);
    place(card);
    if (restore) {
      const button = card.querySelector('[data-companion-action="' + CSS.escape(restore) + '"]');
      const panel = document.getElementById('campPanel');
      if (button && panel && !panel.classList.contains('hidden') && !document.querySelector('.campInfoSheet')) button.focus({preventScroll: true});
    }
  }

  function paint() {
    const body = document.getElementById('campBody');
    if (!body || document.getElementById('campPanel')?.classList.contains('hidden')) return;
    for (const card of body.querySelectorAll('.campCompanion')) paintCard(card);
  }

  function start(tries = 0) {
    const panel = document.getElementById('campPanel');
    const body = document.getElementById('campBody');
    if (!panel || !body) { if (tries < 80) setTimeout(() => start(tries + 1), 50); return; }
    panel.addEventListener('focusin', event => {
      const button = event.target?.closest?.('[data-companion-action]');
      if (button && panel.contains(button)) armed = button;
    });
    let queued = false;
    new MutationObserver(() => { if (!queued) { queued = true; queueMicrotask(() => { queued = false; paint(); }); } }).observe(body, {childList: true, subtree: true});
    panel.addEventListener('terra:camp-tab', paint);
    panel.addEventListener('terra:camp-refresh', paint);
    new MutationObserver(paint).observe(panel, {attributes: true, attributeFilter: ['class']});
    paint();
    window.terraCompanionCard = Object.freeze({paint, modeLabel: mode => MODE[mode] || ''});
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', () => start(), {once: true});
})();
