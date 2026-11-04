/* Плашка подтверждения класса внутри вкладки «Навыки».
 * Кнопки переносятся как есть: data-tech-* / data-scout-* и делегирование бандла не меняются.
 * Текст миграции сейва не переписывается.
 */
(function () {
  'use strict';
  var busy = false;

  function plate(section) {
    var status = section.querySelector(':scope > [role="status"]');
    if (!status || status.classList.contains('classConfirm')) return;
    var cancel = status.querySelector('[data-tech-cancel], [data-scout-cancel]');
    var confirm = section.querySelector('[data-tech-toggle="confirm"], [data-scout-toggle="confirm"]');
    if (!cancel || !confirm) return;
    cancel.remove();
    var text = status.textContent.replace(/\s+/g, ' ').trim();
    status.textContent = '';
    status.classList.add('classConfirm');
    var p = document.createElement('p');
    p.className = 'classConfirmText';
    p.textContent = text;
    var actions = document.createElement('div');
    actions.className = 'classConfirmActions';
    confirm.classList.add('classConfirmYes');
    cancel.classList.add('classConfirmNo');
    actions.append(confirm, cancel);
    status.append(p, actions);
  }

  function scan() {
    if (busy) return;
    var root = document.getElementById('invBody');
    if (!root) return;
    var section = root.querySelector('.circuitClass');
    if (!section) return;
    busy = true;
    try { plate(section); } finally { busy = false; }
  }

  function boot() {
    var root = document.getElementById('invBody');
    if (!root) { setTimeout(boot, 300); return; }
    new MutationObserver(scan).observe(root, { childList: true, subtree: true });
    scan();
  }

  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', boot);
  else boot();
})();
