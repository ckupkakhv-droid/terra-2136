/* Рюкзак: внешний вид и жесты поверх штатных кнопок.
   Надевание идёт через game.equipWeapon / game.wearArmor — те же вызовы, что у кнопок слота.
   Файл не читает и не пишет сохранение. ?backpack=0 выключает слой. */
(() => {
  'use strict';
  if (new URLSearchParams(location.search).get('backpack') === '0') return;

  const ARMOR = {
    jacket: 'body', padded: 'body', vest: 'body', plate: 'body', exo: 'body',
    ushanka: 'head', helmet: 'head', gasmask: 'head', sphere: 'head', exohelm: 'head',
    pants: 'legs', knees: 'legs', cargo: 'legs', greaves: 'legs', exolegs: 'legs',
    mitts: 'hands', tactgloves: 'hands', knuckles: 'hands', exogloves: 'hands',
    valenki: 'feet', kirzachi: 'feet', berets: 'feet', exoboots: 'feet',
    raincoat: 'back', ozk: 'back', ghillie: 'back', exocloak: 'back',
    dogtag: 'acc', compass: 'acc', rosary: 'acc', psiamulet: 'acc',
  };
  const MODULES = { drone: 1, turret: 1 };
  const SCALES = {
    'Здоровье': 250,
    'Выносливость': 150,
    'Броня': 80,
    'Снижение урона': 100,
    'Урон за удар / выстрел': 80,
    'Атак в секунду': 4,
    'Шанс крита': 100,
  };
  const ICONS = {
    'Здоровье': 'M12 20s-7-4.4-7-9a4 4 0 0 1 7-2 4 4 0 0 1 7 2c0 4.6-7 9-7 9z',
    'Выносливость': 'M13 2 4 14h7l-1 8 9-12h-7z',
    'Броня': 'M12 3 19 6v6c0 4.2-2.8 6.8-7 9-4.2-2.2-7-4.8-7-9V6z',
    'Снижение урона': 'M12 3 19 6v6c0 4.2-2.8 6.8-7 9-4.2-2.2-7-4.8-7-9V6z',
    'Урон за удар / выстрел': 'M5 19 19 5M14 5h5v5M5 10V5h5',
    'Атак в секунду': 'M4 13h6l2-7 3 12 2-5h3',
    'Шанс крита': 'M12 3l2.2 5.6L20 11l-5.8 2.4L12 19l-2.2-5.6L4 11l5.8-2.4z',
  };

  const DOUBLE_TAP_MS = 380;
  const statMem = new Map();
  let tip;
  let tipTimer = 0;
  let pending = null;
  let dragPayload = '';
  let mo;
  let scheduled = 0;

  const game = () => window.game || null;
  const reduced = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
  const fine = () => matchMedia('(hover: hover) and (pointer: fine)').matches;

  function svgIcon(path) {
    const svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
    svg.setAttribute('viewBox', '0 0 24 24');
    svg.setAttribute('class', 'bp-ico');
    svg.setAttribute('aria-hidden', 'true');
    const p = document.createElementNS(svg.namespaceURI, 'path');
    p.setAttribute('d', path);
    p.setAttribute('fill', 'none');
    p.setAttribute('stroke', 'currentColor');
    p.setAttribute('stroke-width', '1.7');
    p.setAttribute('stroke-linejoin', 'round');
    p.setAttribute('stroke-linecap', 'round');
    svg.append(p);
    return svg;
  }

  function numOf(text) {
    const t = String(text).replace(/\s/g, '').replace('%', '').replace(',', '.');
    if (!t || t === '—' || t === '-') return null;
    const n = Number(t);
    return Number.isFinite(n) ? n : null;
  }

  function fmt(n, digits) {
    if (!Number.isFinite(n)) return '—';
    return n.toLocaleString('ru-RU', { maximumFractionDigits: digits });
  }

  function weaponOf(uid) {
    const list = game()?.p?.weapons;
    if (!Array.isArray(list)) return null;
    return list.find(item => item && item.uid === uid) || null;
  }
  function armorOf(uid) {
    const list = game()?.p?.armor;
    if (!Array.isArray(list)) return null;
    return list.find(item => item && item.uid === uid) || null;
  }

  function ensureTip() {
    if (tip) return tip;
    tip = document.createElement('div');
    tip.id = 'bpTip';
    tip.hidden = true;
    tip.setAttribute('role', 'tooltip');
    document.body.append(tip);
    return tip;
  }
  function hideTip() {
    clearTimeout(tipTimer);
    if (tip) tip.hidden = true;
  }
  function placeTip(x, y) {
    const node = ensureTip();
    node.hidden = false;
    const w = node.offsetWidth;
    const h = node.offsetHeight;
    let left = x + 14;
    let top = y + 18;
    if (left + w > innerWidth - 8) left = x - w - 14;
    if (top + h > innerHeight - 8) top = y - h - 12;
    node.style.left = Math.max(8, left) + 'px';
    node.style.top = Math.max(8, top) + 'px';
  }
  function line(label, now, was, digits) {
    const row = document.createElement('div');
    const name = document.createElement('span');
    name.textContent = label + ' ';
    row.append(name);
    if (!Number.isFinite(now)) {
      row.append(document.createTextNode('—'));
      return row;
    }
    const value = document.createElement('span');
    if (!Number.isFinite(was)) {
      value.textContent = fmt(now, digits);
    } else {
      const d = now - was;
      if (Math.abs(d) < (digits ? 0.05 : 0.5)) {
        value.className = 'same';
        value.textContent = fmt(now, digits) + ' · так же';
      } else {
        value.className = d > 0 ? 'up' : 'down';
        value.textContent = fmt(now, digits) + ' ' + (d > 0 ? '+' : '−') + fmt(Math.abs(d), digits);
      }
    }
    row.append(value);
    return row;
  }
  function fillTip(tile) {
    const g = game();
    const node = ensureTip();
    node.replaceChildren();
    const title = document.createElement('b');
    title.textContent = tile.querySelector('.nm')?.textContent || 'Предмет';
    node.append(title);
    if (!g) return;
    const ui = g.ui;
    if (tile.dataset.w) {
      const item = weaponOf(Number(tile.dataset.w));
      const st = item && g.wstat ? g.wstat(item) : null;
      if (!item || !st) return;
      const mod = !!MODULES[item.wt];
      const slot = Number.isInteger(ui?.equipmentWeaponSlot) ? ui.equipmentWeaponSlot : (g.p.slot || 0);
      const cur = mod ? g.p.mods?.[item.wt] : g.p.eq?.[slot];
      const note = document.createElement('small');
      note.textContent = cur && cur.uid !== item.uid && g.wname ? 'Сейчас: ' + g.wname(cur) : (cur ? 'Уже надето' : 'Слот свободен');
      node.append(note);
      const other = cur && cur.uid !== item.uid && g.wstat ? g.wstat(cur) : null;
      node.append(line('Урон', Math.round(st.dmg), other ? Math.round(other.dmg) : null, 0));
      const speed = st.rate > 0 ? 1 / st.rate : null;
      const ospeed = other && other.rate > 0 ? 1 / other.rate : null;
      node.append(line('Скорость', speed, other ? ospeed : null, 1));
      node.append(line('Крит', Math.round((st.crit || 0) * 100), other ? Math.round((other.crit || 0) * 100) : null, 0));
      return;
    }
    if (tile.dataset.armor) {
      const item = armorOf(Number(tile.dataset.armor));
      if (!item || typeof g.armorVal !== 'function') return;
      const slot = ARMOR[item.at];
      const cur = slot && g.wornArmor ? g.wornArmor(slot) : null;
      const note = document.createElement('small');
      const curName = cur && tile.ownerDocument.querySelector(`[data-equipment-armor="${slot}"] .equipmentSlotName`);
      note.textContent = cur && cur.uid !== item.uid ? 'Сейчас: ' + (curName ? curName.textContent : 'надето') : (cur ? 'Уже надето' : 'Слот свободен');
      node.append(note);
      const now = g.armorVal(item);
      const was = cur && cur.uid !== item.uid ? g.armorVal(cur) : null;
      node.append(line('Броня', Math.round(now), was == null ? null : Math.round(was), 0));
    }
  }
  function showTip(tile, x, y, sticky) {
    fillTip(tile);
    placeTip(x, y);
    clearTimeout(tipTimer);
    if (sticky) tipTimer = setTimeout(hideTip, 2200);
  }

  function paintCompare(root) {
    root.querySelectorAll('.invCompare').forEach(block => {
      if (block.dataset.bp) return;
      block.dataset.bp = '1';
      const html = block.innerHTML;
      block.innerHTML = html.replace(/(\d+(?:[.,]\d+)?)\s*→\s*(\d+(?:[.,]\d+)?)/g, (all, a, b) => {
        const from = Number(String(a).replace(',', '.'));
        const to = Number(String(b).replace(',', '.'));
        if (!Number.isFinite(from) || !Number.isFinite(to) || from === to) return all;
        const cls = to > from ? 'up' : 'down';
        return `<span class="bp-delta ${cls}">${all}</span>`;
      });
    });
  }

  function paintSlots(root) {
    root.querySelectorAll('.equipmentSlot, .equipmentWeapon').forEach(btn => {
      const name = btn.querySelector('.equipmentSlotName') || btn.querySelector('span:last-child');
      const empty = name && name.textContent.trim() === 'Пусто';
      btn.classList.toggle('is-empty', !!empty);
      if (empty && name && !name.classList.contains('bp-clip')) name.classList.add('bp-clip');
    });
  }

  function paintMeter(root) {
    const cap = root.querySelector('.bag-cap');
    if (!cap || cap.querySelector('.bp-meter')) return;
    const match = cap.textContent.match(/(\d+)\s*\/\s*(\d+)/);
    if (!match) return;
    const used = Number(match[1]);
    const max = Number(match[2]);
    const bar = document.createElement('span');
    bar.className = 'bp-meter';
    bar.style.setProperty('--p', String(max ? Math.min(100, used / max * 100) : 0));
    bar.setAttribute('role', 'meter');
    bar.setAttribute('aria-valuemin', '0');
    bar.setAttribute('aria-valuemax', String(max));
    bar.setAttribute('aria-valuenow', String(used));
    bar.setAttribute('aria-label', `Место в рюкзаке ${used} из ${max}`);
    const fill = document.createElement('i');
    bar.append(fill);
    cap.append(bar);
  }

  function paintStats(root) {
    root.querySelectorAll('.equipmentStat').forEach(stat => {
      const label = stat.querySelector('dt')?.textContent?.trim() || '';
      const value = stat.querySelector('dd');
      if (!value || stat.querySelector('.bp-bar')) return;
      const path = ICONS[label];
      if (path) stat.prepend(svgIcon(path));
      const bar = document.createElement('span');
      bar.className = 'bp-bar';
      const fill = document.createElement('i');
      bar.append(fill);
      stat.append(bar);
      const next = numOf(value.textContent);
      const scale = SCALES[label] || (next == null ? 1 : Math.max(next, 1));
      const ratio = next == null ? 0 : Math.max(0, Math.min(1, next / scale));
      bar.style.setProperty('--v', String(ratio));
      const prev = statMem.get(label);
      statMem.set(label, next);
      if (prev == null || next == null || prev === next || reduced()) return;
      stat.classList.add(next > prev ? 'bp-up' : 'bp-down');
      const digits = Math.abs(next - Math.round(next)) > 0.001 || Math.abs(prev - Math.round(prev)) > 0.001 ? 1 : 0;
      const suffix = /%/.test(value.textContent) ? '%' : '';
      const t0 = performance.now();
      const step = now => {
        const k = Math.min(1, (now - t0) / 280);
        const eased = 1 - (1 - k) * (1 - k);
        value.textContent = fmt(prev + (next - prev) * eased, digits) + suffix;
        if (k < 1) requestAnimationFrame(step);
        else setTimeout(() => stat.classList.remove('bp-up', 'bp-down'), 700);
      };
      requestAnimationFrame(step);
    });
  }

  function paintCards(root) {
    if (!fine()) return;
    root.querySelectorAll('.tile[data-w], .tile[data-armor]').forEach(tile => {
      tile.draggable = true;
    });
  }

  function markFits() {
    const g = game();
    const ui = g?.ui;
    const root = document.getElementById('invBody');
    if (!root || !ui || ui.tab !== 'eq') return;
    root.querySelectorAll('.bp-fit').forEach(el => el.classList.remove('bp-fit'));
    if (ui.gearView === 'armor' && ui.aSel != null) {
      const item = armorOf(ui.aSel);
      const slot = item && ARMOR[item.at];
      if (slot) root.querySelector(`[data-equipment-armor="${slot}"]`)?.classList.add('bp-fit');
      return;
    }
    if (ui.sel == null) return;
    const item = weaponOf(ui.sel);
    if (!item) return;
    if (MODULES[item.wt]) root.querySelector(`[data-equipment-module="${item.wt}"]`)?.classList.add('bp-fit');
    else root.querySelectorAll('[data-equipment-weapon]').forEach(el => el.classList.add('bp-fit'));
  }

  function clearDrops() {
    dragPayload = '';
    document.querySelectorAll('#inv .bp-drop, #inv .bp-hot, #inv .bp-drag').forEach(el => {
      el.classList.remove('bp-drop', 'bp-hot', 'bp-drag');
    });
  }
  function markDrops(payload) {
    clearDrops();
    dragPayload = payload;
    const root = document.getElementById('inv');
    if (!root) return;
    const [kind, id] = payload.split(':');
    if (kind === 'w') {
      const item = weaponOf(Number(id));
      if (!item) return;
      const sel = MODULES[item.wt]
        ? `[data-equipment-module="${item.wt}"]`
        : '[data-equipment-weapon]';
      root.querySelectorAll(sel).forEach(el => el.classList.add('bp-drop'));
    } else if (kind === 'a') {
      const item = armorOf(Number(id));
      const slot = item && ARMOR[item.at];
      const el = slot && root.querySelector(`[data-equipment-armor="${slot}"]`);
      if (el) el.classList.add('bp-drop');
    }
  }

  function quickEquip(tile, slotEl) {
    const g = game();
    const ui = g?.ui;
    if (!g || !ui) return false;
    try {
      if (tile?.dataset.w || (dragPayload.startsWith('w:') && slotEl)) {
        const uid = Number(tile?.dataset.w || dragPayload.slice(2));
        const item = weaponOf(uid);
        if (!item) return false;
        let slot = Number.isInteger(ui.equipmentWeaponSlot) ? ui.equipmentWeaponSlot : (Number.isInteger(g.p.slot) ? g.p.slot : 0);
        if (slotEl?.dataset.equipmentWeapon != null) slot = Number(slotEl.dataset.equipmentWeapon);
        if (MODULES[item.wt] && slotEl?.dataset.equipmentModule && slotEl.dataset.equipmentModule !== item.wt) return false;
        const ok = !!g.equipWeapon(uid, MODULES[item.wt] ? 0 : slot);
        if (ok) ui.renderInv();
        return ok;
      }
      if (tile?.dataset.armor || dragPayload.startsWith('a:')) {
        const uid = Number(tile?.dataset.armor || dragPayload.slice(2));
        const item = armorOf(uid);
        const slot = item && ARMOR[item.at];
        if (slotEl?.dataset.equipmentArmor && slot && slotEl.dataset.equipmentArmor !== slot) return false;
        const ok = !!g.wearArmor(uid);
        if (ok) ui.renderInv();
        return ok;
      }
    } catch (err) {
      return false;
    }
    return false;
  }

function pumpPreview(preview) {
  clearTimeout(preview._bpPump);
  preview._bpPump = 0;
  if (!preview.host || reduced() || !preview.game?.glb?.hero) return;
  if (typeof preview.visible === 'function' && !preview.visible()) return;
  preview.request?.();
  preview._bpPump = setTimeout(() => pumpPreview(preview), 80);
}

function hookPreview() {
  const preview = game()?.ui?.equipmentPreview;
  if (!preview || typeof preview.draw !== 'function') return;
  if (preview._bp) {
    if (preview.host && !preview._bpPump) pumpPreview(preview);
    return;
  }
  preview._bp = true;
  const orig = preview.draw;
  const origUnmount = preview.unmount?.bind(preview);
    preview.draw = function draw() {
      const now = performance.now();
      if (this.inst?.mixer && !this.source?.isHeroFallback && !reduced()) {
        const dt = Math.min(0.05, (now - (this._bpT || now)) / 1000);
        this._bpT = now;
        try { this.inst.mixer.update(dt || 0.016); } catch (err) { /* клип недоступен — остаётся кадр */ }
      }
      const userYaw = this.yaw || 0;
      // Кадр считает штатный draw: полные границы позы модели, аспект окна.
      // Размер хоста не подменяем — иначе собьём этот расчёт.
      if (this.game?.glb?.hero && !reduced() && !this._bpDrag) this.yaw = userYaw + Math.sin(now / 900) * 0.045;
      if (this.scene && this._bpLit !== this.scene) {
        this._bpLit = this.scene;
        this.scene.traverse(obj => {
          if (obj.isHemisphereLight) obj.intensity = Math.max(obj.intensity || 0, 2.6);
        });
      }
      try { orig.call(this); }
      finally {
        this.yaw = userYaw;
        // A newly ready GLB resumes its idle animation; the static suit waits
        // for input, resize or the loader notification without a timer.
        if (!this._bpPump && this.host && this.game?.glb?.hero && !reduced()) pumpPreview(this);
      }
    };
    preview.unmount = function unmount() {
      clearTimeout(this._bpPump);
      this._bpPump = 0;
      this._bpLit = null;
      this._bpT = 0;
      this._bpDrag = false;
      if (origUnmount) origUnmount();
    };
    pumpPreview(preview);
  }

  function decorate() {
    const inv = document.getElementById('inv');
    const root = document.getElementById('invBody');
    if (!inv || !root || inv.classList.contains('hidden')) return;
    if (!inv.classList.contains('bp')) inv.classList.add('bp');
    paintSlots(root);
    paintMeter(root);
    paintStats(root);
    paintCards(root);
    paintCompare(root);
    markFits();
    hookPreview();
  }
  function schedule() {
    if (scheduled) return;
    scheduled = requestAnimationFrame(() => {
      scheduled = 0;
      decorate();
    });
  }

  function replay(tile) {
    const ev = new MouseEvent('click', { bubbles: true, cancelable: true });
    ev._bpReplay = true;
    tile.dispatchEvent(ev);
  }

  function bind(inv) {
    inv.addEventListener('click', event => {
      if (event.target.closest('.tabs button')) {
        const body = document.getElementById('invBody');
        if (!body || reduced()) return;
        body.classList.remove('bp-swap');
        void body.offsetWidth;
        body.classList.add('bp-swap');
      }
    });

    const body = document.getElementById('invBody');
    body.addEventListener('click', event => {
      const tile = event.target.closest('.tile[data-w], .tile[data-armor]');
      if (!tile) return;
      if (event._bpReplay) return;
      event.stopPropagation();
      event.preventDefault();
      const key = tile.dataset.w ? 'w' + tile.dataset.w : 'a' + tile.dataset.armor;
      const now = performance.now();
      if (pending && pending.key === key && now - pending.t < DOUBLE_TAP_MS) {
        clearTimeout(pending.timer);
        pending = null;
        if (!quickEquip(tile)) replay(tile);
        return;
      }
      if (pending) clearTimeout(pending.timer);
      pending = {
        key,
        t: now,
        timer: setTimeout(() => {
          pending = null;
          if (tile.isConnected) replay(tile);
        }, DOUBLE_TAP_MS),
      };
    }, true);

    body.addEventListener('pointerover', event => {
      if (event.pointerType === 'touch') return;
      const tile = event.target.closest('.tile[data-w], .tile[data-armor]');
      if (!tile) return;
      showTip(tile, event.clientX, event.clientY, false);
    });
    body.addEventListener('pointermove', event => {
      if (tip?.hidden || event.pointerType === 'touch') return;
      if (!event.target.closest('.tile[data-w], .tile[data-armor]')) return;
      placeTip(event.clientX, event.clientY);
    });
    body.addEventListener('pointerout', event => {
      const tile = event.target.closest('.tile[data-w], .tile[data-armor]');
      if (!tile || tile.contains(event.relatedTarget)) return;
      hideTip();
    });
    body.addEventListener('pointerup', event => {
      if (event.pointerType === 'mouse') return;
      const tile = event.target.closest('.tile[data-w], .tile[data-armor]');
      if (!tile) return;
      const rect = tile.getBoundingClientRect();
      showTip(tile, rect.left + rect.width / 2, rect.top, true);
    });
    body.addEventListener('scroll', hideTip, { passive: true });

    let drag = null;
    inv.addEventListener('pointerdown', event => {
      const stage = event.target.closest('[data-equipment-preview]');
      if (!stage || event.target.closest('button')) return;
      const preview = game()?.ui?.equipmentPreview;
      if (!preview) return;
      drag = { id: event.pointerId, x: event.clientX, yaw: preview.yaw || 0 };
      preview._bpDrag = true;
      try { stage.setPointerCapture?.(event.pointerId); } catch (err) { /* синтетический указатель */ }
    });
    inv.addEventListener('pointermove', event => {
      if (!drag || event.pointerId !== drag.id) return;
      const preview = game()?.ui?.equipmentPreview;
      if (!preview) return;
      preview.yaw = drag.yaw + (event.clientX - drag.x) * 0.012;
      preview.request?.();
    });
    const endDrag = event => {
      if (!drag || (event && event.pointerId !== drag.id)) return;
      const preview = game()?.ui?.equipmentPreview;
      if (preview) preview._bpDrag = false;
      drag = null;
    };
    inv.addEventListener('pointerup', endDrag);
    inv.addEventListener('pointercancel', endDrag);

    body.addEventListener('dragstart', event => {
      const tile = event.target.closest('.tile[data-w], .tile[data-armor]');
      if (!tile || !fine()) {
        event.preventDefault();
        return;
      }
      if (pending) {
        clearTimeout(pending.timer);
        pending = null;
      }
      const payload = tile.dataset.w ? 'w:' + tile.dataset.w : 'a:' + tile.dataset.armor;
      event.dataTransfer.setData('text/plain', payload);
      event.dataTransfer.effectAllowed = 'copy';
      tile.classList.add('bp-drag');
      markDrops(payload);
    });
    inv.addEventListener('dragover', event => {
      const slot = event.target.closest('.bp-drop');
      if (!slot) return;
      event.preventDefault();
      event.dataTransfer.dropEffect = 'copy';
      slot.classList.add('bp-hot');
    });
    inv.addEventListener('dragleave', event => {
      event.target.closest?.('.bp-hot')?.classList.remove('bp-hot');
    });
    inv.addEventListener('drop', event => {
      const slot = event.target.closest('.bp-drop');
      if (!slot) return;
      event.preventDefault();
      event.stopPropagation();
      const payload = event.dataTransfer.getData('text/plain') || dragPayload;
      dragPayload = payload;
      quickEquip(null, slot);
      clearDrops();
    });
    inv.addEventListener('dragend', clearDrops);

    mo = new MutationObserver(schedule);
    mo.observe(body, { childList: true });
    mo.observe(inv, { attributes: true, attributeFilter: ['class'] });
  }

  function bindTabs(inv) {
    const tabs = inv.querySelector('.tabs'), panel = document.getElementById('invBody');
    if (!tabs || !panel) return;
    const names = {eq: ['Экипировка', 'Снаряж.'], items: ['Вещи', 'Вещи'], craft: ['Крафт', 'Крафт'],
      skills: ['Навыки', 'Навыки'], settle: ['Поселение', 'Посел.'], log: ['Журнал', 'Журнал']};
    const decorated = new WeakSet();
    const vertical = matchMedia('(orientation: landscape) and (max-height: 520px)');
    const buttons = () => [...tabs.querySelectorAll('button[data-tab]')];
    const enabled = () => buttons().filter(b => !b.disabled);
    let queued = false, reveal = true, lastSelected = null;
    function tabStop(target) { for (const b of buttons()) b.tabIndex = b === target ? 0 : -1; }
    function sync() {
      queued = false;
      const all = buttons();
      if (!all.length) return;
      tabs.setAttribute('role', 'tablist');
      tabs.setAttribute('aria-label', 'Разделы рюкзака');
      tabs.setAttribute('aria-orientation', vertical.matches ? 'vertical' : 'horizontal');
      for (const b of all) {
        if (!decorated.has(b)) {
          decorated.add(b);
          const name = names[b.dataset.tab] || [b.textContent.trim(), b.textContent.trim()];
          if (!b.id) b.id = 'inventory-tab-' + b.dataset.tab;
          b.setAttribute('role', 'tab');
          b.setAttribute('aria-controls', panel.id);
          if (!b.hasAttribute('aria-label')) b.setAttribute('aria-label', name[0]);
          if (!b.title) b.title = name[0];
          const short = document.createElement('span');
          short.className = 'bpNavShort';short.textContent = name[1];short.setAttribute('aria-hidden', 'true');b.append(short);
        }
      }
      const selected = all.find(b => b.classList.contains('on')) || all[0];
      for (const b of all) b.setAttribute('aria-selected', String(b === selected));
      panel.setAttribute('role', 'tabpanel');panel.setAttribute('aria-labelledby', selected.id);
      const focus = all.includes(document.activeElement) && !document.activeElement.disabled ? document.activeElement : null;
      tabStop(focus || (selected.disabled ? enabled()[0] : selected));
      if (reveal || selected !== lastSelected) {
        reveal = false;lastSelected = selected;
        const target = focus || selected;
        queueMicrotask(() => { if (target.isConnected && !inv.classList.contains('hidden')) target.scrollIntoView({block:'nearest', inline:'nearest'}); });
      }
    }
    function queue() { if (!queued) { queued = true;queueMicrotask(sync); } }
    tabs.addEventListener('keydown', event => {
      if (inv.classList.contains('hidden') || window.game?.state !== 'modal' || event.altKey || event.ctrlKey || event.metaKey) return;
      const all = enabled(), index = all.indexOf(event.target);
      if (index < 0) return;
      if (event.key === 'Enter' || event.key === ' ') { event.stopPropagation();return; }
      const previous = vertical.matches ? 'ArrowUp' : 'ArrowLeft';
      const next = vertical.matches ? 'ArrowDown' : 'ArrowRight';
      if (![previous, next, 'Home', 'End'].includes(event.key)) return;
      event.preventDefault();event.stopPropagation();
      const at = event.key === 'Home' ? 0 : event.key === 'End' ? all.length - 1 : (index + (event.key === previous ? -1 : 1) + all.length) % all.length;
      tabStop(all[at]);all[at].focus({preventScroll: true});all[at].scrollIntoView({block: 'nearest', inline: 'nearest'});
    });
    tabs.addEventListener('focusin', event => { if (enabled().includes(event.target)) tabStop(event.target); });
    tabs.addEventListener('focusout', event => { if (!tabs.contains(event.relatedTarget)) queue(); });
    new MutationObserver(queue).observe(tabs, {childList: true, subtree: true, attributes: true, attributeFilter: ['class', 'disabled']});
    new MutationObserver(() => { reveal = true;queue(); }).observe(inv, {attributes: true, attributeFilter: ['class']});
    const resize = () => { if (!inv.classList.contains('hidden')) { reveal = true;queue(); } };
    vertical.addEventListener('change', resize);window.addEventListener('resize', resize, {passive:true});sync();
  }

  function boot() {
    const inv = document.getElementById('inv');
    if (!inv) return;
    bind(inv);
    bindTabs(inv);
    schedule();
  }
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
