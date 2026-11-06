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
