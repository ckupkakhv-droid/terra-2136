/* Мобильный каркас лагеря: вкладки под большой палец, «В игру» в панели, вкладка «Оборона»
   и точки встраивания window.terraCampUI. Только оформление и навигация: приказы, экономика
   и сохранения остаются в штатных обработчиках игры. HUD в поле живёт в camp-navigation.*. */
(() => {
  'use strict';
  // Иконки из набора игры (game-icons.net, CC BY 3.0 — см. README → «Авторы и лицензии»).
  const ICONS = {
    play: 'M106.854 106.002a26.003 26.003 0 0 0-25.64 29.326c16 124 16 117.344 0 241.344a26.003 26.003 0 0 0 35.776 27.332l298-124a26.003 26.003 0 0 0 0-48.008l-298-124a26.003 26.003 0 0 0-10.136-1.994z',
    turret: 'M130.72 61C106 61.11 106 62.875 106 91H76l-15 30v60l15 30h30c0 30 0 30 30 30h120c30 0 30 0 30-30h15l15-30h180v-60H316l-15-30h-15c0-30 0-30-30-30H136c-1.875 0-3.633-.007-5.28 0zM166 271a15 15 0 0 0-15 15v45a15 15 0 0 0 15 15h60a15 15 0 0 0 15-15v-45a15 15 0 0 0-15-15h-60zm-15 105c-30 0-45 30-45 30-15 0-30 0-30 15l-60 15v15h360v-15l-60-15c0-15-15-15-30-15 0 0-15-30-45-30h-90z',
    close: 'M256 16C123.45 16 16 123.45 16 256s107.45 240 240 240 240-107.45 240-240S388.55 16 256 16zm0 60c99.41 0 180 80.59 180 180s-80.59 180-180 180S76 355.41 76 256 156.59 76 256 76zm-80.625 60c-.97-.005-2.006.112-3.063.313v-.032c-18.297 3.436-45.264 34.743-33.375 46.626l73.157 73.125-73.156 73.126c-14.63 14.625 29.275 58.534 43.906 43.906L256 299.906l73.156 73.156c14.63 14.628 58.537-29.28 43.906-43.906l-73.156-73.125 73.156-73.124c14.63-14.625-29.275-58.5-43.906-43.875L256 212.157l-73.156-73.125c-2.06-2.046-4.56-3.015-7.47-3.03z',
  };
  const svg = name => `<svg class="gi" viewBox="0 0 512 512" aria-hidden="true"><path d="${ICONS[name]}"/></svg>`;
  const MOBILE = '(orientation: portrait) and (max-width: 600px), (orientation: landscape) and (max-height: 500px)';
  const SHORT = {expansion: 'Уровень'};
  const sections = new Map();
  const badges = new Map();

  function start() {
    const panel = document.getElementById('campPanel');
    const tabs = panel?.querySelector('#campTabs');
    const body = panel?.querySelector('#campBody');
    if (!panel || !tabs || !body || window.terraCampUI) return;
    const media = window.matchMedia(MOBILE);
    const campPanel = () => window.game?.ui?.campPanel;
    let lastTab = null;
    let customTab = null;
    let decorating = false;

    function currentTab() { return customTab || campPanel()?.tab || null; }

    function makeTab(section) {
      const button = document.createElement('button');
      button.type = 'button';
      button.dataset.campTab = section.id;
      button.dataset.campMobile = 'section';
      button.innerHTML = section.icon || svg('turret');
      const label = document.createElement('span');
      label.textContent = section.label;
      button.append(label);
      button.title = section.label;
      button.setAttribute('aria-label', section.label);
      button.addEventListener('click', () => openSection(section.id));
      return button;
    }

    function openSection(id) {
      const section = sections.get(id);
      const native = campPanel();
      if (!section || !native || panel.classList.contains('hidden')) return;
      if (section.native) { customTab = null; native.select(id); return; }
      // Своё содержимое поверх штатного раздела; штатный refresh его снимет сам.
      customTab = id;
      for (const child of body.children) child.classList.add('campMobileHidden');
      renderSection(section);
      decorate();
      body.scrollTop = 0;
    }

    function renderSection(section) {
      if (typeof section.render !== 'function') return;
      let container = body.querySelector(`:scope > .campSection[data-camp-section="${section.id}"]`);
      if (!container) {
        container = document.createElement('section');
        container.className = 'campSection';
        container.dataset.campSection = section.id;
        container.setAttribute('aria-label', section.label);
        const summary = document.createElement('div');
        summary.className = 'campSection__summary';
        const list = document.createElement('div');
        list.className = 'campSection__list';
        container.append(summary, list);
        body.append(container);
      }
      try { section.render(container, window.game); }
      catch (error) { console.error('[Terra camp UI] section', section.id, error); }
    }

    function decorate() {
      if (decorating) return;
      decorating = true;
      try {
        if (customTab && !body.querySelector(`:scope > .campSection[data-camp-section="${customTab}"]`)) customTab = null;
        const tab = currentTab();
        const more = tabs.querySelector('[data-camp-tab="more"]');
        // Сколько вкладок помещается без прокрутки (по 48 px); лишние разделы уходят в «Ещё».
        const vertical = media.matches && window.matchMedia('(orientation: landscape)').matches;
        const room = media.matches ? Math.floor((vertical ? tabs.clientHeight : tabs.clientWidth) / 48) : Infinity;
        const nativeCount = tabs.querySelectorAll('button[data-camp-tab]:not([data-camp-mobile])').length + (media.matches ? 1 : 0);
        let free = room - nativeCount;
        const overflow = [];
        for (const section of [...sections.values()].sort((a, b) => a.order - b.order)) {
          let button = tabs.querySelector(`[data-camp-tab="${section.id}"][data-camp-mobile]`);
          if (free-- <= 0) { button?.remove(); overflow.push(section); continue; }
          if (!button) {
            button = makeTab(section);
            tabs.insertBefore(button, more || tabs.querySelector('.campMobilePlay'));
          }
        }
        const moreGrid = body.querySelector(':scope > .campMore');
        if (moreGrid) {
          for (const card of moreGrid.querySelectorAll('[data-camp-mobile="card"]'))
            if (!overflow.some(section => section.id === card.dataset.campTab)) card.remove();
          for (const section of overflow) {
            if (section.native || moreGrid.querySelector(`[data-camp-mobile="card"][data-camp-tab="${section.id}"]`)) continue;
            const card = document.createElement('button');
            card.type = 'button';
            card.className = 'campCard campDestination';
            card.dataset.campTab = section.id;
            card.dataset.campMobile = 'card';
            card.innerHTML = section.icon || svg('turret');
            const title = document.createElement('strong');
            title.textContent = section.label;
            card.append(title);
            card.setAttribute('aria-label', section.label);
            card.addEventListener('click', () => openSection(section.id));
            moreGrid.append(card);
          }
          // Штатный раздел, не поместившийся во вкладки, остаётся в «Ещё».
          for (const section of overflow) if (section.native)
            moreGrid.querySelector(`.campDestination[data-camp-tab="${section.id}"]:not([data-camp-mobile])`)?.classList.add('campMobileKeep');
        }
        for (const button of tabs.querySelectorAll('button[data-camp-tab]')) {
          const id = button.dataset.campTab;
          const on = id === tab || (id === 'more' && !!tab && ![...tabs.querySelectorAll('button[data-camp-tab]')].some(b => b.dataset.campTab === tab));
          button.classList.toggle('on', on);
          button.setAttribute('aria-pressed', String(on));
          if (SHORT[id]) button.dataset.short = SHORT[id];
          const badge = badges.get(id);
          let em = button.querySelector('.campTabBadge');
          if (badge && badge.count > 0) {
            if (!em) { em = document.createElement('em'); em.className = 'campTabBadge'; button.append(em); }
            em.textContent = badge.count > 99 ? '99+' : String(badge.count);
            em.dataset.tone = badge.tone || 'bad';
            button.setAttribute('aria-label', `${button.title} · ${badge.count}`);
          } else {
            em?.remove();
            if (button.title) button.setAttribute('aria-label', button.title);
          }
        }
        let play = tabs.querySelector('.campMobilePlay');
        if (!play) {
          play = document.createElement('button');
          play.type = 'button';
          play.className = 'campMobilePlay';
          play.innerHTML = svg('play') + '<span>В игру</span>';
          play.setAttribute('aria-label', 'Вернуться в игру');
          play.title = 'Вернуться в игру';
          // Тот же штатный путь, что у кнопки «В игру» в подвале.
          play.addEventListener('click', () => panel.querySelector('.panelFoot [data-close]')?.click());
        }
        if (tabs.lastElementChild !== play) tabs.append(play);
        play.hidden = play.disabled = !media.matches;
        panel.dataset.campMobileTab = tab || '';
        panel.classList.toggle('campMobile', media.matches);
        if (tab !== lastTab) {
          lastTab = tab;
          panel.dispatchEvent(new CustomEvent('terra:camp-tab', {detail: {tab}}));
        }
      } finally { decorating = false; }
    }

    let queued = false;
    function schedule() {
      if (queued) return;
      queued = true;
      queueMicrotask(() => {
        queued = false;
        decorate();
        if (!panel.classList.contains('hidden')) {
          const tab = currentTab();
          const section = sections.get(tab);
          if (section?.native && typeof section.render === 'function') renderSection(section);
          panel.dispatchEvent(new CustomEvent('terra:camp-refresh', {detail: {tab}}));
        }
      });
    }
    // Штатный refresh пересобирает вкладки и тело раздела; дополняем после него.
    new MutationObserver(records => { if (!decorating && records.some(r => [...r.addedNodes].some(n => !n.dataset?.campMobile && !n.classList?.contains('campMobilePlay')))) schedule(); })
      .observe(tabs, {childList: true});
    new MutationObserver(records => {
      if (decorating) return;
      if (customTab && !body.querySelector(`:scope > .campSection[data-camp-section="${customTab}"]`)) schedule();
      else if (records.some(r => [...r.addedNodes].some(n => n.classList?.contains('campMore')))) schedule();
    })
      .observe(body, {childList: true});
    media.addEventListener?.('change', decorate);

    let sheet = null;
    function openInfo(title, content) {
      closeInfo();
      sheet = document.createElement('section');
      sheet.className = 'campInfoSheet';
      sheet.setAttribute('role', 'dialog');
      sheet.setAttribute('aria-modal', 'true');
      const head = document.createElement('header');
      const h = document.createElement('strong');
      h.id = 'campInfoSheetTitle';
      h.textContent = String(title || 'Подробности');
      sheet.setAttribute('aria-labelledby', h.id);
      const close = document.createElement('button');
      close.type = 'button';
      close.className = 'campInfoClose';
      close.innerHTML = svg('close');
      close.setAttribute('aria-label', 'Закрыть подробности');
      close.addEventListener('click', closeInfo);
      head.append(h, close);
      const box = document.createElement('div');
      box.className = 'campInfoSheet__body';
      if (content instanceof Node) box.append(content);
      else box.textContent = String(content ?? '');
      sheet.append(head, box);
      sheet.addEventListener('keydown', event => {
        if (event.key === 'Escape') { event.preventDefault(); event.stopPropagation(); closeInfo(); }
      });
      panel.querySelector('.win')?.append(sheet);
      close.focus({preventScroll: true});
      return sheet;
    }
    function closeInfo() { sheet?.remove(); sheet = null; }
    new MutationObserver(() => { if (panel.classList.contains('hidden')) closeInfo(); })
      .observe(panel, {attributes: true, attributeFilter: ['class']});

    window.terraCampUI = Object.freeze({
      version: 1,
      /** Вкладка лагеря. native: true — штатный раздел игры (открывается game.ui.campPanel.select). */
      registerSection(options) {
        const id = String(options?.id || '');
        if (!/^[a-z][a-z0-9-]*$/.test(id) || ['overview', 'settlers', 'build', 'expansion', 'more'].includes(id)) return false;
        const old = sections.get(id) || {};
        sections.set(id, {
          id, native: !!(options.native ?? old.native), label: String(options.label || old.label || id),
          icon: options.icon || old.icon, order: Number.isFinite(options.order) ? options.order : (old.order ?? 10),
          render: options.render || old.render,
        });
        tabs.querySelector(`[data-camp-tab="${id}"][data-camp-mobile]`)?.remove();
        decorate();
        if (currentTab() === id && !panel.classList.contains('hidden')) schedule();
        return true;
      },
      setBadge(id, count, tone = 'bad') {
        const n = Math.max(0, Math.floor(Number(count) || 0));
        if (n) badges.set(String(id), {count: n, tone: ['ok', 'warn', 'bad', 'idle'].includes(tone) ? tone : 'bad'});
        else badges.delete(String(id));
        decorate();
      },
      openInfo, closeInfo,
      get tab() { return currentTab(); },
      sections: () => [...sections.keys()],
    });
    // Оборона: штатный раздел игры, просто выведен из «Ещё» в основную панель.
    window.terraCampUI.registerSection({id: 'defense', native: true, label: 'Оборона', icon: svg('turret'), order: 1});
    decorate();
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, {once: true});
})();
