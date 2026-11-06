/* Экспедиционный контур. Команды, цифры и сохранения не меняются:
   только группировка уже существующих кнопок меню, подписи и возврат фокуса. */
(() => {
  'use strict';
  const BACKUP_IDS = ['mExportCrystalCopies', 'mRestoreCrystalCopy', 'mImportSave', 'mExportSave'];

  function start() {
    document.getElementById('hud')?.classList.add('contourHud');
    document.getElementById('menu')?.classList.add('contourMenu');
    labelVitals();
    labelPulse();
    groupBackups();
    markPrimary();
    const menu = document.querySelector('#menu .mbtns');
    if (menu) new MutationObserver(() => { groupBackups(); markPrimary(); }).observe(menu, {childList: true, attributes: true, subtree: true, attributeFilter: ['class', 'hidden', 'disabled']});
    watchCamp();
    watchWarnings();
    const pulseHost = document.getElementById('mmW') || document.getElementById('tr');
    if (pulseHost) new MutationObserver(labelPulse).observe(pulseHost, {childList: true, subtree: true});
  }

  function labelVitals() {
    const hp = document.querySelector('#tl .bar.hp');
    const sta = document.querySelector('#tl .bar.st');
    const xp = document.querySelector('#tl .bar.xp');
    const rad = document.getElementById('radB');
    if (hp && !hp.getAttribute('aria-label')) hp.setAttribute('aria-label', 'Здоровье');
    if (sta && !sta.getAttribute('aria-label')) sta.setAttribute('aria-label', 'Выносливость');
    if (xp && !xp.getAttribute('aria-label')) xp.setAttribute('aria-label', 'Опыт');
    if (rad && !rad.getAttribute('aria-label')) rad.setAttribute('aria-label', 'Радиация');
    const food = document.getElementById('food');
    const water = document.getElementById('water');
    const sync = () => {
      if (food) food.setAttribute('aria-label', 'Еда ' + food.textContent.replace(/\s+/g, ' ').trim());
      if (water) water.setAttribute('aria-label', 'Вода ' + water.textContent.replace(/\s+/g, ' ').trim());
    };
    sync();
    for (const node of [food, water]) {
      if (node) new MutationObserver(sync).observe(node, {childList: true, characterData: true, subtree: true});
    }
  }

  function labelPulse() {
    const pulse = document.getElementById('evPulse');
    if (pulse && !pulse.getAttribute('aria-label')) pulse.setAttribute('aria-label', 'Пульс зоны');
  }

  let grouping = false;
  function groupBackups() {
    if (grouping) return;
    const box = document.querySelector('#menu .mbtns');
    if (!box) return;
    const ready = BACKUP_IDS.every(id => document.getElementById(id));
    if (!ready && !document.getElementById('menuFieldTools')) return;
    grouping = true;
    try {
      let details = document.getElementById('menuFieldTools');
      if (!details) {
        details = document.createElement('details');
        details.id = 'menuFieldTools';
        details.className = 'menuFieldTools';
        const summary = document.createElement('summary');
        summary.textContent = 'Резерв и запись';
        details.append(summary);
        box.append(details);
      }
      const capacity = document.getElementById('crystalBackupCapacity');
      if (capacity && capacity.parentElement !== details) details.append(capacity);
      for (const id of BACKUP_IDS) {
        const button = document.getElementById(id);
        if (!button) continue;
        const next = button.nextElementSibling;
        if (button.parentElement !== details) details.append(button);
        if (next && next.tagName === 'P' && !next.id && next.parentElement !== details) details.append(next);
      }
      const file = document.querySelector('#menu input[type="file"]');
      if (file && file.parentElement !== details) details.append(file);
      const cancel = [...document.querySelectorAll('#menu button')].find(button => button.textContent.trim() === 'Отмена' && !button.id);
      const confirm = cancel?.parentElement;
      if (confirm && confirm !== details && confirm.parentElement !== details) details.append(confirm);
    } finally {
      grouping = false;
    }
  }

  function visible(button) {
    return !!button && !button.hidden && !button.classList.contains('hidden') && !button.disabled;
  }

  function markPrimary() {
    const resume = document.getElementById('mContinue');
    const fresh = document.getElementById('mNew');
    const primary = visible(resume) ? resume : fresh;
    for (const button of [resume, fresh]) button?.classList.toggle('expeditionPrimary', button === primary);
  }

  function showSupplyReason() {
    const button = document.querySelector('#campPanel [data-supply-assign]');
    if (!button) return;
    const title = (button.title || '').trim();
    const own = button.textContent.replace(/\s+/g, ' ').trim();
    const extra = button.disabled && title && !own.includes(title) ? title : '';
    let note = document.getElementById('contourSupplyReason');
    if (!extra) {
      note?.remove();
      if (button.getAttribute('aria-describedby') === 'contourSupplyReason') button.removeAttribute('aria-describedby');
      return;
    }
    const host = button.closest('.campSupply') || button.parentElement;
    if (!note) {
      note = document.createElement('small');
      note.className = 'contourReason';
      note.id = 'contourSupplyReason';
    }
    if (note.parentElement !== host) host.append(note);
    if (note.textContent !== extra) note.textContent = extra;
    button.setAttribute('aria-describedby', note.id);
  }

  function tunePause() {
    const button = document.querySelector('#campPanel .fbPauseInfo');
    if (!button || button.dataset.contourPause) return;
    button.dataset.contourPause = '1';
    button.textContent = 'Пауза';
  }

  const WARNING_BLOCKS = '#bCamp,#bMap,#bPause,#objectiveToggle,#tBag,#weap,#lvlW,#evPulse,#tInteract,#tBuild,#tSprint,#tDodge,#tSwap,#tThrow,#tReload,#tCycle,#obj,#tl,#zone,#mmW';

  function shown(el) {
    if (!el) return false;
    const style = getComputedStyle(el);
    if (style.display === 'none' || style.visibility === 'hidden') return false;
    const rect = el.getBoundingClientRect();
    return rect.width > 1 && rect.height > 1;
  }

  function rectOf(el) {
    const rect = el.getBoundingClientRect();
    return {left: rect.left, top: rect.top, right: rect.right, bottom: rect.bottom};
  }

  function intersects(a, b) {
    return a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1;
  }

  function clearLane(el) {
    el.style.left = '';
    el.style.top = '';
    el.style.width = '';
    el.style.maxWidth = '';
    el.style.transform = '';
  }

  let settling = false;
  function settleWarnings() {
    if (settling) return;
    const hud = document.getElementById('evHud');
    const radio = document.getElementById('radio');
    if (!hud || !radio) return;
    const live = hud.classList.contains('on') || shown(radio);
    if (!live) {
      clearLane(hud);
      clearLane(radio);
      return;
    }
    settling = true;
    try {
      const blocks = [...document.querySelectorAll(WARNING_BLOCKS)].filter(shown).map(rectOf);
      const margin = 8;
      const rights = blocks.filter(box => box.left > innerWidth * 0.55).map(box => box.left);
      const rightLimit = Math.min(innerWidth - margin, ...(rights.length ? rights : [innerWidth - margin]));
      const left = margin;
      const width = Math.max(168, Math.min(340, rightLimit - left));
      const head = Math.max(
        document.getElementById('tl')?.getBoundingClientRect().bottom || 0,
        document.getElementById('obj')?.getBoundingClientRect().bottom || 0,
        document.getElementById('mmW')?.getBoundingClientRect().bottom || 0
      );
      const taken = [];
      const park = (el, minTop) => {
        if (el === hud && !hud.classList.contains('on')) return minTop;
        if (el === radio && !shown(radio)) return minTop;
        el.style.left = left + 'px';
        el.style.transform = 'none';
        el.style.width = width + 'px';
        el.style.maxWidth = width + 'px';
        const height = el.getBoundingClientRect().height;
        let top = Math.max(minTop, head + margin);
        for (let step = 0; step < 50; step++) {
          const spot = {left, top, right: left + width, bottom: top + height};
          const busy = blocks.concat(taken).some(box => intersects(spot, box));
          if (!busy && spot.bottom < innerHeight - margin) {
            el.style.top = top + 'px';
            taken.push(spot);
            return spot.bottom + 6;
          }
          top += 8;
        }
        el.style.top = top + 'px';
        taken.push({left, top, right: left + width, bottom: top + height});
        return top + height + 6;
      };
      let cursor = head + margin;
      if (hud.classList.contains('on')) cursor = park(hud, cursor);
      if (shown(radio)) park(radio, cursor);
    } finally {
      settling = false;
    }
  }

  function watchWarnings() {
    const arm = () => {
      const hud = document.getElementById('evHud');
      const radio = document.getElementById('radio');
      if (!hud || !radio || hud.dataset.contourLane) return !!hud && false;
      hud.dataset.contourLane = '1';
      const observer = new MutationObserver(() => settleWarnings());
      observer.observe(hud, {attributes: true, attributeFilter: ['class']});
      observer.observe(radio, {attributes: true, attributeFilter: ['style', 'class']});
      window.addEventListener('resize', settleWarnings);
      settleWarnings();
      return true;
    };
    if (arm()) return;
    const observer = new MutationObserver(() => { if (arm()) observer.disconnect(); });
    observer.observe(document.body, {childList: true, subtree: true});
  }

  function watchCamp() {
    const arm = () => {
      const panel = document.getElementById('campPanel');
      if (!panel || panel.dataset.contourWatch) return !!panel && false;
      panel.dataset.contourWatch = '1';
      let opener = null;
      document.getElementById('bCamp')?.addEventListener('pointerdown', () => { opener = document.getElementById('bCamp'); }, true);
      document.getElementById('bCamp')?.addEventListener('keydown', event => {
        if (event.key === 'Enter' || event.key === ' ') opener = document.getElementById('bCamp');
      }, true);
      const restore = () => {
        if (!panel.classList.contains('hidden')) return;
        const active = document.activeElement;
        if (!active || active === document.body || panel.contains(active)) (opener || document.getElementById('bCamp'))?.focus();
      };
      new MutationObserver(restore).observe(panel, {attributes: true, attributeFilter: ['class']});
      const body = document.getElementById('campBody');
      if (body) new MutationObserver(() => { tunePause(); showSupplyReason(); }).observe(body, {childList: true, subtree: true});
      tunePause();
      showSupplyReason();
      return true;
    };
    if (arm()) return;
    const observer = new MutationObserver(() => { if (arm()) observer.disconnect(); });
    observer.observe(document.body, {childList: true, subtree: true});
  }

  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, {once: true});
})();
