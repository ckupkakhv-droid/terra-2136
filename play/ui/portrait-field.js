/* Портрет: цель, сводка, радио и событие — значки.
 * Текст берётся из уже нарисованных узлов. Новых полей сохранения нет.
 * Срочная плашка не прячется: имя и таймер остаются на значке.
 */
(() => {
  'use strict';
  const MQ = '(orientation: portrait) and (max-width: 520px)';
  const QUIET = ['obj', 'dropHud', 'zone', 'kills'];
  let kind = null;
  let opener = null;
  let seenRadio = '';
  let seenEvent = '';
  let readRadio = '';
  let readEvent = '';

  function glyph(name) {
    const mark = document.createElement('i');
    mark.className = 'fieldGlyph';
    mark.setAttribute('aria-hidden', 'true');
    const src = document.querySelector('[data-ic="' + name + '"]');
    if (src && src.innerHTML) mark.innerHTML = src.innerHTML;
    return mark;
  }

  function chip(id, icon, label) {
    const button = document.createElement('button');
    button.type = 'button';
    button.id = id;
    button.className = 'fieldChip';
    button.append(glyph(icon));
    const text = document.createElement('span');
    text.className = 'fieldChipText';
    const time = document.createElement('b');
    time.className = 'fieldTime';
    button.append(text, time);
    button.dataset.field = label;
    button.addEventListener('click', () => toggle(id));
    return button;
  }

  function mount() {
    if (document.getElementById('fieldDock')) return;
    const stack = document.getElementById('leftHudStack');
    if (!stack) return;
    const dock = document.createElement('div');
    dock.id = 'fieldDock';
    dock.append(
      chip('fieldGoal', 'info', 'Цель'),
      chip('fieldPouch', 'bag', 'Сводка'),
      chip('fieldRadio', 'radio', 'Радио'),
      chip('fieldAlert', 'moon', 'Событие')
    );
    stack.append(dock);
    const sheet = document.createElement('section');
    sheet.id = 'fieldSheet';
    sheet.className = 'hidden';
    sheet.setAttribute('role', 'dialog');
    sheet.setAttribute('aria-labelledby', 'fieldSheetTitle');
    sheet.innerHTML = '<div class="fieldPaper"><header><h2 id="fieldSheetTitle"></h2><button type="button" id="fieldSheetClose" aria-label="Закрыть лист">×</button></header><div id="fieldSheetBody"></div></div>';
    document.body.append(sheet);
    sheet.querySelector('#fieldSheetClose').addEventListener('click', () => close(true));
    sheet.addEventListener('keydown', trap);
  }

  function plain(id) {
    return (document.getElementById(id)?.textContent || '').replace(/\s+/g, ' ').trim();
  }

  function portrait() {
    return window.matchMedia(MQ).matches;
  }

  function playing() {
    const hud = document.getElementById('hud');
    return !!(hud && !hud.classList.contains('hidden') && portrait());
  }

  function radioLive() {
    const el = document.getElementById('radio');
    return !!(el && el.style.display === 'flex' && plain('radioT'));
  }

  function line(label, value) {
    const node = document.createElement('p');
    node.textContent = label + ': ' + value;
    return node;
  }

  function para(text) {
    const node = document.createElement('p');
    node.textContent = text;
    return node;
  }

  function paint(next) {
    const title = document.getElementById('fieldSheetTitle');
    const body = document.getElementById('fieldSheetBody');
    const focused = document.activeElement;
    if (focused && body.contains(focused) && next !== 'fieldAlert') return;
    body.replaceChildren();
    if (next === 'fieldGoal') {
      title.textContent = plain('objT') || 'Цель';
      const hint = plain('objH');
      const detail = plain('objD');
      if (hint) body.append(para(hint));
      if (detail && detail !== hint) body.append(para(detail));
    } else if (next === 'fieldPouch') {
      title.textContent = 'Сводка';
      for (const [id, label] of [['food', 'Еда'], ['water', 'Вода'], ['clock', 'Время'], ['zone', 'Место'], ['kills', 'Бой'], ['dropN_bag', 'Рюкзак'], ['dropN_scrap', 'Лом'], ['dropN_wood', 'Дерево'], ['dropN_chem', 'Химия'], ['dropN_cloth', 'Ткань']]) {
        const value = plain(id);
        if (value) body.append(line(label, value));
      }
    } else if (next === 'fieldRadio') {
      title.textContent = 'Радио';
      const message = plain('radioT') || 'Тишина.';
      body.append(para(message));
      readRadio = message;
      const chipNode = document.getElementById('fieldRadio');
      if (chipNode) chipNode.classList.remove('isFresh');
    } else if (next === 'fieldAlert') {
      const ev = document.getElementById('evHud');
      const name = (ev?.querySelector('.evh b')?.textContent || 'Событие').trim();
      const timer = (document.getElementById('evTm')?.textContent || '').trim();
      title.textContent = name;
      if (timer) {
        const stamp = document.createElement('p');
        stamp.className = 'fieldStamp';
        stamp.textContent = timer;
        body.append(stamp);
      }
      const seen = new Set([name, timer]);
      for (const node of ev?.querySelectorAll('.evw span, .evd span') || []) {
        const text = node.textContent.replace(/\s+/g, ' ').trim();
        if (!text || seen.has(text)) continue;
        seen.add(text);
        body.append(para(text));
      }
      readEvent = name;
      const chipNode = document.getElementById('fieldAlert');
      if (chipNode) chipNode.classList.remove('isFresh');
    }
  }

  function place() {
    const sheet = document.getElementById('fieldSheet');
    if (!sheet || sheet.classList.contains('hidden')) return;
    const dock = document.getElementById('fieldDock');
    const stick = document.getElementById('stickL');
    const top = (dock?.getBoundingClientRect().bottom || 96) + 8;
    const stickTop = stick && stick.getClientRects().length ? stick.getBoundingClientRect().top : innerHeight - 168;
    sheet.style.top = Math.round(top) + 'px';
    sheet.style.bottom = Math.round(Math.max(12, innerHeight - stickTop + 10)) + 'px';
  }

  function open(next) {
    mount();
    kind = next;
    opener = document.getElementById(next);
    paint(next);
    const sheet = document.getElementById('fieldSheet');
    sheet.classList.remove('hidden');
    place();
    sheet.querySelector('#fieldSheetClose').focus();
  }

  function close(restore) {
    const sheet = document.getElementById('fieldSheet');
    if (!sheet || sheet.classList.contains('hidden')) { kind = null; return; }
    sheet.classList.add('hidden');
    kind = null;
    if (restore && opener?.isConnected) opener.focus();
    opener = null;
  }

  function toggle(next) {
    if (kind === next) close(true);
    else open(next);
  }

  function quiet(on) {
    for (const id of QUIET.concat(['evHud', 'radio'])) {
      const el = document.getElementById(id);
      if (!el) continue;
      if (on) {
        el.setAttribute('aria-hidden', 'true');
        el.inert = true;
      } else if (el.getAttribute('aria-hidden') === 'true') {
        el.removeAttribute('aria-hidden');
        el.inert = false;
      }
    }
  }

  function refill() {
    for (const [id, name] of [['fieldGoal', 'info'], ['fieldPouch', 'bag'], ['fieldRadio', 'radio'], ['fieldAlert', 'moon']]) {
      const mark = document.querySelector('#' + id + ' .fieldGlyph');
      if (!mark || mark.innerHTML) continue;
      const src = document.querySelector('[data-ic="' + name + '"]');
      if (src && src.innerHTML) mark.innerHTML = src.innerHTML;
    }
  }

  function tick() {
    const hud = document.getElementById('hud');
    if (!hud) return;
    const on = playing();
    document.documentElement.classList.toggle('portraitMenu', portrait());
    hud.classList.toggle('portraitField', on);
    const toasts = document.getElementById('toasts');
    if (!on) {
      quiet(false);
      close(false);
      if (toasts) toasts.style.top = '';
      return;
    }
    mount();
    refill();
    quiet(true);
    const goal = document.getElementById('fieldGoal');
    const goalText = plain('objT');
    goal.hidden = !goalText;
    goal.querySelector('.fieldChipText').textContent = goalText;
    goal.setAttribute('aria-label', 'Цель. ' + (plain('obj') || goalText));
    const pouch = document.getElementById('fieldPouch');
    const bag = plain('dropN_bag');
    pouch.querySelector('.fieldChipText').textContent = bag;
    pouch.setAttribute('aria-label', 'Сводка. Рюкзак ' + bag);
    const radio = document.getElementById('fieldRadio');
    const message = plain('radioT');
    const showRadio = radioLive();
    radio.hidden = !showRadio;
    radio.querySelector('.fieldChipText').textContent = '';
    if (showRadio && message !== seenRadio) {
      seenRadio = message;
      if (message !== readRadio) radio.classList.add('isFresh');
    }
    if (!showRadio && kind === 'fieldRadio') close(false);
    radio.setAttribute('aria-label', (radio.classList.contains('isFresh') ? 'Новое радио. ' : 'Радио. ') + message);
    const alert = document.getElementById('fieldAlert');
    const ev = document.getElementById('evHud');
    const liveEvent = !!ev?.classList.contains('on');
    alert.hidden = !liveEvent;
    if (liveEvent) {
      const name = (ev.querySelector('.evh b')?.textContent || 'Событие').trim();
      const timer = (document.getElementById('evTm')?.textContent || '').trim();
      const clock = (timer.match(/\d+:\d+/) || [timer])[0];
      alert.querySelector('.fieldChipText').textContent = name;
      alert.querySelector('.fieldTime').textContent = clock;
      alert.classList.toggle('isUrgent', ev.classList.contains('night') || ev.classList.contains('rift') || ev.classList.contains('asc'));
      if (name !== seenEvent) {
        seenEvent = name;
        if (name !== readEvent) alert.classList.add('isFresh');
      }
      alert.setAttribute('aria-label', name + (timer ? ', ' + timer : '') + '. ' + plain('evHud'));
    } else if (kind === 'fieldAlert') close(false);
    const inv = document.getElementById('inv');
    if (inv && !inv.classList.contains('hidden')) close(false);
    if (kind === 'fieldAlert') {
      const stamp = document.querySelector('#fieldSheetBody .fieldStamp');
      const fresh = (document.getElementById('evTm')?.textContent || '').trim();
      if (stamp && fresh && stamp.textContent !== fresh) stamp.textContent = fresh;
    }
    if (toasts) {
      const below = document.getElementById('fieldDock')?.getBoundingClientRect().bottom || 96;
      toasts.style.top = Math.round(below + 8) + 'px';
    }
    place();
  }

  function trap(event) {
    if (event.key !== 'Tab') return;
    const sheet = document.getElementById('fieldSheet');
    const items = [...sheet.querySelectorAll('button')].filter(el => el.getClientRects().length);
    if (!items.length) return;
    const index = items.indexOf(document.activeElement);
    event.preventDefault();
    items[(index + (event.shiftKey ? -1 : 1) + items.length) % items.length].focus();
  }

  window.addEventListener('keydown', event => {
    const sheet = document.getElementById('fieldSheet');
    if (!sheet || sheet.classList.contains('hidden')) return;
    if (event.key !== 'Escape') return;
    event.preventDefault();
    event.stopImmediatePropagation();
    close(true);
  }, true);

  function start() {
    mount();
    tick();
    setInterval(tick, 250);
    window.addEventListener('resize', tick);
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, {once: true});
})();
