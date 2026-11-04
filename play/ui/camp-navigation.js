/* Progressive UI enhancement. All orders remain in the game's existing handlers. */
(() => {
  function start() {
    const panel = document.getElementById('campPanel');
    if (!panel) return;
    const body = panel.querySelector('#campBody');
    const tabs = panel.querySelector('#campTabs');
    let query = '';
    let currentRows = null;
    const jobOptions = new WeakMap();
    let reasonSequence = 0;
    const normalize = value => value.toLocaleLowerCase('ru').replaceAll('ё', 'е').trim();

    function enhanceResidents() {
      const rows = body.querySelector('.residentRows');
      if (rows === currentRows) return;
      currentRows = rows;
      if (!rows) return;
      const toolbar = document.createElement('div');
      toolbar.className = 'residentSearch';
      const label = document.createElement('label');
      label.htmlFor = 'residentSearchInput';
      label.textContent = 'Найти жителя';
      const input = document.createElement('input');
      input.id = label.htmlFor;
      input.type = 'search';
      input.placeholder = 'Имя или профессия';
      input.autocomplete = 'off';
      input.value = query;
      const clear = document.createElement('button');
      clear.type = 'button';
      clear.className = 'campButton';
      clear.textContent = 'Сбросить';
      const status = document.createElement('small');
      status.className = 'residentSearchStatus';
      status.id = 'residentSearchStatus';
      status.setAttribute('role', 'status');
      input.setAttribute('aria-describedby', status.id);
      function filter() {
        query = input.value;
        const needle = normalize(query);
        const cards = [...rows.querySelectorAll('.residentRow')];
        let visible = 0;
        for (const card of cards) {
          const summary = card.querySelector('.residentSummary');
          const matches = normalize(summary?.textContent || summary?.getAttribute('aria-label') || '').includes(needle);
          card.classList.toggle('campSearchHidden', !matches);
          if (matches) visible++;
        }
        clear.disabled = !query;
        status.textContent = cards.length ? (visible ? `В текущем списке: ${visible} из ${cards.length}` : 'Совпадений нет. Измените поиск или фильтр занятости.') : 'В текущем списке жителей нет.';
      }
      input.addEventListener('input', filter);
      clear.addEventListener('click', () => { input.value = ''; filter(); input.focus(); });
      toolbar.append(label, input, clear, status);
      rows.before(toolbar);
      filter();
    }
    const destinations = {
      build: ['build', 'Открыть очередь работ'],
      repair: ['build', 'Открыть очередь работ'],
      haul: ['warehouses', 'Открыть склады и доставку'],
      operate: ['power', 'Открыть энергоснабжение'],
    };
    function explainJobs() {
      for (const button of body.querySelectorAll('.campJobs [data-resident-job]')) {
        let option = jobOptions.get(button);
        if (!option) {
          const wrapper = document.createElement('div');
          wrapper.className = 'residentJobOption';
          button.before(wrapper);
          wrapper.append(button);
          const reason = document.createElement('small');
          reason.className = 'campReason residentJobReason';
          reason.id = `resident-job-reason-${++reasonSequence}`;
          wrapper.append(reason);
          option = {reason, signature: null, originalDescription: button.getAttribute('aria-describedby') || ''};
          const destination = destinations[button.dataset.residentJob];
          if (destination) {
            const link = document.createElement('button');
            link.type = 'button';
            link.className = 'campButton residentJobLink';
            link.textContent = destination[1];
            link.dataset.campDestination = destination[0];
            link.addEventListener('click', () => {
              const game = window.game;
              if (!link.isConnected || !button.disabled || panel.classList.contains('hidden') || game?.state !== 'modal') return;
              game.ui.campPanel.select(destination[0]);
            });
            wrapper.append(link);
            option.link = link;
          }
          jobOptions.set(button, option);
        }
        const signature = `${button.disabled}:${button.title}`;
        if (signature === option.signature) continue;
        option.signature = signature;
        option.reason.textContent = button.disabled ? button.title || 'Сейчас недоступно' : '';
        option.reason.hidden = !button.disabled;
        if (option.link) option.link.hidden = !button.disabled;
        const description = [option.originalDescription, button.disabled ? option.reason.id : ''].filter(Boolean).join(' ');
        if (description) button.setAttribute('aria-describedby', description);
        else button.removeAttribute('aria-describedby');
      }
    }
    let watchedJobs = null;
    const jobObserver = new MutationObserver(explainJobs);
    function enhanceContent() {
      enhanceResidents();
      const jobs = body.querySelector('.campJobs');
      if (jobs === watchedJobs) return;
      jobObserver.disconnect();
      watchedJobs = jobs;
      if (jobs) {
        explainJobs();
        jobObserver.observe(jobs, {subtree: true, attributes: true, attributeFilter: ['disabled', 'title']});
      }
    }
    new MutationObserver(enhanceContent).observe(body, {childList: true, subtree: true});
    enhanceContent();

    // Move focus only; Enter/Space use the native buttons and their existing handlers.
    tabs.addEventListener('keydown', event => {
      if (!['ArrowLeft', 'ArrowRight', 'ArrowUp', 'ArrowDown', 'Home', 'End'].includes(event.key)) return;
      const buttons = [...tabs.querySelectorAll('button:not(:disabled)')];
      const index = buttons.indexOf(event.target);
      if (index < 0) return;
      event.preventDefault();
      const next = event.key === 'Home' ? 0 : event.key === 'End' ? buttons.length - 1 : (index + (['ArrowLeft', 'ArrowUp'].includes(event.key) ? -1 : 1) + buttons.length) % buttons.length;
      buttons[next].focus();
      buttons[next].scrollIntoView({block: 'nearest', inline: 'nearest'});
    });
    for (const [id, text] of Object.entries({bCamp: 'Лагерь и жители', bMap: 'Карта · M', bPause: 'Пауза · Esc'})) {
      const button = document.getElementById(id);
      if (button) { button.setAttribute('aria-label', text); button.title = text; }
    }
    enhanceFieldHud();
  }

  function enhanceFieldHud() {
    const hud = document.getElementById('hud');
    const objective = document.getElementById('obj');
    const title = document.getElementById('objT');
    const hint = document.getElementById('objH');
    if (!hud || !objective || !title || !hint) return;
    const toggle = document.createElement('button');
    toggle.type = 'button';
    toggle.id = 'objectiveToggle';
    toggle.setAttribute('aria-controls', 'objectiveDetails');
    toggle.setAttribute('aria-labelledby', 'objT objectiveActionLabel');
    const action = document.createElement('span');
    action.id = 'objectiveActionLabel';
    action.className = 'hudScreenReaderText';
    const chevron = document.createElement('span');
    chevron.className = 'objectiveChevron';
    chevron.textContent = '⌄';
    chevron.setAttribute('aria-hidden', 'true');
    const shortTitle = document.createElement('span');
    shortTitle.className = 'objectiveShortTitle';
    shortTitle.textContent = 'Цель';
    shortTitle.setAttribute('aria-hidden', 'true');
    objective.prepend(toggle);
    toggle.append(title, shortTitle, action, chevron);
    const details = document.createElement('section');
    details.id = 'objectiveDetails';
    const detailTitle = document.createElement('strong');
    detailTitle.id = 'objectiveDetailTitle';
    details.setAttribute('aria-labelledby', detailTitle.id);
    details.append(detailTitle, hint);
    objective.append(details);
    const syncTitle = () => {
      if (detailTitle.textContent !== title.textContent) detailTitle.textContent = title.textContent;
    };
    const titleObserver = new MutationObserver(syncTitle);
    let expanded;
    function expand(open) {
      if (expanded === open) return;
      expanded = open;
      objective.classList.toggle('objectiveExpanded', open);
      hud.classList.toggle('objectiveDetailsOpen', open);
      toggle.setAttribute('aria-expanded', String(open));
      action.textContent = open ? 'Скрыть подробности цели' : 'Показать подробности цели';
      details.hidden = !open;
      titleObserver.disconnect();
      if (open) {
        syncTitle();
        titleObserver.observe(title, {childList: true, characterData: true, subtree: true});
      }
    }
    expand(false);
    // The touch controller listens on window: reading/scrolling the hint must not steer it.
    objective.addEventListener('pointerdown', event => event.stopPropagation());
    toggle.addEventListener('click', event => {
      event.stopPropagation();
      if (window.game?.state === 'play') expand(toggle.getAttribute('aria-expanded') !== 'true');
    });
    toggle.addEventListener('keydown', event => {
      if (['Enter', ' '].includes(event.key)) event.stopPropagation();
      if (event.key === 'Escape') {
        event.preventDefault();
        event.stopPropagation();
        expand(false);
      }
    });
    document.addEventListener('pointerdown', event => {
      if (!objective.contains(event.target)) expand(false);
    }, true);
    new MutationObserver(() => {
      if (hud.classList.contains('hidden')) expand(false);
    }).observe(hud, {attributes: true, attributeFilter: ['class']});

    // Native HUD buttons use pointerdown. Keyboard/assistive click needs the same action.
    const actions = {bMap: game => game.ui.openMap(), bPause: game => game.ui.pause()};
    for (const [id, caption] of Object.entries({bCamp: 'Лагерь', bMap: 'Карта', bPause: 'Пауза'})) {
      const button = document.getElementById(id);
      if (!button) continue;
      const label = document.createElement('span');
      label.className = 'hudButtonCaption';
      label.textContent = caption;
      label.setAttribute('aria-hidden', 'true');
      button.append(label);
      button.addEventListener('keydown', event => {
        if (['Enter', ' '].includes(event.key)) event.stopPropagation();
      });
      if (actions[id]) button.addEventListener('click', event => {
        if (event.detail === 0 && window.game?.state === 'play') actions[id](window.game);
      });
    }
    const skills = document.getElementById('lvlW');
    if (skills) {
      skills.tabIndex = 0;
      skills.addEventListener('keydown', event => {
        if (!['Enter', ' '].includes(event.key)) return;
        event.preventDefault();
        event.stopPropagation();
        if (window.game?.state === 'play') window.game.ui.openInv('skills');
      });
    }
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, {once: true});
})();

// Мобильный каркас лагеря: play/ui/camp-mobile.* (HUD и логика выше не меняются).
{ const s = document.createElement('script'); s.src = new URL('camp-mobile.js', document.currentScript?.src || new URL('ui/', location.href)).href; document.head.append(s);
  const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = new URL('camp-mobile.css', document.currentScript?.src || new URL('ui/', location.href)).href; document.head.append(l); }

// «Штабной стол»: личное дело жителя и чертежи построек — play/ui/camp-dossier.* (только оформление).
{ const base = document.currentScript?.src || new URL('ui/', location.href);
  const s = document.createElement('script'); s.src = new URL('camp-dossier.js', base).href; document.head.append(s);
  const l = document.createElement('link'); l.rel = 'stylesheet'; l.href = new URL('camp-dossier.css', base).href; document.head.append(l); }
