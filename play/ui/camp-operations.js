/* Field roster and perimeter. Reuse native controls, orders and disclosures. */
(() => {
  'use strict';
  const paths = {
    people: 'M12 29a8 8 0 1 0 0-16 8 8 0 0 0 0 16m-11 17v-5c0-11 22-11 22 0v5M43 29a8 8 0 1 0 0-16 8 8 0 0 0 0 16M32 46v-5c0-11 22-11 22 0v5',
    all: 'M15 22a6 6 0 1 0 0-12 6 6 0 0 0 0 12m24 0a6 6 0 1 0 0-12 6 6 0 0 0 0 12M3 43v-8c0-11 24-11 24 0v8m0 0v-8c0-11 24-11 24 0v8',
    free: 'm10 25 12 12 25-26M10 45h36',
    working: 'm12 38 27-27 7 7-27 27-7-7M8 12l10-4 7 7-4 10-8-2-5-11',
    waiting: 'M18 12v30m19-30v30M8 6h40v42H8z',
    water: 'M28 5C17 22 12 28 12 34a16 16 0 0 0 32 0c0-6-5-12-16-29m-8 29c0 5 3 8 8 8',
    wood: 'M8 27h40v18H8zM8 27l12-15h28v15m-28-15v15m19 4a5 5 0 1 0 0 10 5 5 0 0 0 0-10',
    build: 'm7 10 15 15m-6 6 15 15m-23-1 27-27 10 10-27 27zM31 7l5-5 18 18-5 5',
  };
  const svg = name => `<svg viewBox="0 0 56 56" aria-hidden="true"><path d="${paths[name] || paths.people}"/></svg>`;
  const el = (tag, cls, text) => { const n = document.createElement(tag); n.className = cls; if (text != null) n.textContent = text; return n; };
  const done = new WeakSet();
  let quickOpen = false;
  function start() {
    const panel = document.getElementById('campPanel'), body = panel?.querySelector('#campBody');
    if (!body) return;
    panel.classList.add('campOperations');
    function roster(root) {
      if (!root.querySelector('.residentRows')) return;
      root.classList.add('opsRoster');
      // Native filters may replace children while keeping the same root node.
      if (!root.querySelector(':scope > .opsRosterHead')) {
        const total = root.querySelector('[data-worker-filter="all"]')?.textContent.match(/\d+/)?.[0] || '0';
        const head = el('header', 'opsRosterHead');
        const title = el('div', '');title.append(el('small', 'opsSerial', 'ШТАБ / ЛИЧНЫЙ СОСТАВ'), el('h3', '', 'Картотека лагеря'));
        const count = el('div', 'opsPersonnel');count.innerHTML = svg('people');count.append(el('b', '', total));count.setAttribute('aria-label', 'Жителей: '+total);
        head.append(title, count);root.prepend(head);
        const empty = +total === 0;
        root.classList.toggle('opsRosterEmpty', empty);
        if (empty) {
          const scene = el('section', 'opsEmptyRoster');
          scene.innerHTML = '<svg class="opsSignal" viewBox="0 0 240 120" aria-hidden="true"><path d="M24 106H216M98 106l22-90 22 90m-36-34h28m-21-28h14M78 37a57 57 0 0 0 0 60m84-60a57 57 0 0 1 0 60M63 24a77 77 0 0 0 0 85m114-85a77 77 0 0 1 0 85"/><circle cx="120" cy="16" r="5"/><path d="M30 91V70h23v36m134 0V77h23v14"/></svg>';
          scene.append(el('small', 'opsSerial', 'ПОИСК ВЫЖИВШИХ'), el('h3', '', 'У костра пока никого'), el('p', '', 'Найдите выживших и приведите их в лагерь.'));
          root.append(scene);
          const find = root.querySelector(':scope > .campFold');
          if (find) { find.classList.add('opsRecruit');scene.append(find); }
        } else {
          const tasks=root.querySelector(':scope > .residentTasks'),hint=root.querySelector(':scope > .residentTaskHint'),rec=root.querySelector(':scope > .residentRecommendation');
          if (tasks) {
            const quick=el('details','opsQuickOrder');quick.open=quickOpen;
            const selected=tasks.querySelector('[aria-pressed="true"]')?.textContent || 'выбрать';
            quick.append(el('summary','','Быстрый приказ · '+selected),tasks);
            if (hint) quick.append(hint);if (rec) quick.append(rec);
            quick.addEventListener('toggle',()=>{if(quick.isConnected)quickOpen=quick.open;});head.after(quick);
          }
        }
      }
      for (const button of root.querySelectorAll('[data-worker-filter], [data-worker-task]')) {
        if (done.has(button)) continue;done.add(button);
        const original = button.textContent, count = original.match(/\d+$/)?.[0];
        const label = original.replace(/\s+\d+$/, '');
        button.innerHTML = svg(button.dataset.workerFilter || button.dataset.workerTask);
        button.append(el('span', '', label));if (count != null) button.append(el('b', '', count));
      }
      for (const rec of root.querySelectorAll('.residentRecommendation')) {
        if (done.has(rec)) continue;done.add(rec);
        const lines = [...rec.querySelectorAll(':scope > small')];
        if (lines.length) {
          const help = el('details', 'opsRules');help.append(el('summary', '', 'Правила назначения'), ...lines);rec.append(help);
        }
      }
      const search = root.querySelector('.residentSearch');
      if (search && !done.has(search)) {
        done.add(search);const clear = search.querySelector('button');
        if (clear) { clear.textContent = '×';clear.setAttribute('aria-label', 'Очистить поиск');clear.title = 'Очистить поиск'; }
      }
      for (const [index, row] of [...root.querySelectorAll('.residentRow')].entries()) {
        if (done.has(row)) continue;done.add(row);row.dataset.fileNumber = String(index+1).padStart(2,'0');
      }
    }
    function perimeter(root) {
      if (done.has(root)) return;done.add(root);root.classList.add('opsPerimeter');
      const cards = [...root.querySelectorAll(':scope > .defCard')];
      const threat = cards[0];if (threat) threat.classList.add('opsThreat');
      const armory = cards[1];
      if (armory) {
        const fold = el('details', 'opsArmory');fold.append(el('summary', '', 'Оружейная / патроны и выдача'));armory.before(fold);fold.append(armory);
      }
      const positions = root.querySelector(':scope > .defGrid');
      if (positions) {
        positions.classList.add('opsPositions');positions.setAttribute('aria-label', 'Посты охраны');
        [...positions.children].forEach((card, i) => {
          const number = el('small', 'opsPositionNo', 'ПОЗИЦИЯ '+String(i+1).padStart(2,'0'));card.prepend(number);
        });
      }
      // Native buttons and their closures survive moving into this tool strip.
      const tools = el('div', 'opsPerimeterTools');
      const buttons = [...root.querySelectorAll(':scope > button')];
      if (buttons.length) { buttons[0].before(tools);tools.append(...buttons); }
      const requirement = root.querySelector(':scope > small');if (requirement) {requirement.classList.add('opsRequirement');tools.append(requirement);}
      if (positions) {
        const fold=el('details','opsPosts');fold.append(el('summary','','Посты охраны / '+positions.children.length+' позиции'));
        tools.before(fold);fold.append(tools,positions);
      }
    }
    let queued = false;
    function refresh() {
      queued = false;if (panel.classList.contains('hidden')) return;
      body.querySelectorAll('.campResidents').forEach(roster);body.querySelectorAll('.campDefense').forEach(perimeter);
      for (const picker of body.querySelectorAll('.defPicker:empty')) if (!picker.dataset.empty) {
        picker.dataset.empty='1';picker.append(el('small','campReason','Нет доступных бойцов. Найдите жителей.'));
      }
    }
    const schedule = () => { if (!queued) { queued = true;queueMicrotask(refresh); } };
    new MutationObserver(schedule).observe(body,{childList:true,subtree:true});
    new MutationObserver(schedule).observe(panel,{attributes:true,attributeFilter:['class']});
    refresh();
  }
  if (document.readyState === 'complete') start();else window.addEventListener('load',start,{once:true});
})();
