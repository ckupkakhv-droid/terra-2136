/* Progressive UI enhancement. All orders remain in the game's existing handlers. */
(() => {
  function start() {
    const panel = document.getElementById('campPanel');
    if (!panel) return;
    import('./sewers.js').then(module => module.installSewers(window.game)).catch(error => console.error('[Terra sewers]', error));
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
    function enhanceContent() { enhanceResidents(); explainJobs(); }
    new MutationObserver(enhanceContent).observe(body, {
      childList: true, subtree: true, attributes: true, attributeFilter: ['disabled', 'title'],
    });
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
  }
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', start, {once: true});
})();
