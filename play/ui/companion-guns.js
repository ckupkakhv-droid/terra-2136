/* Список стволов в штатной карточке .campCompanion.
   Кнопки и команда остаются у карточки: giveGun / takeGun через commandCompanion.
   Этот модуль только читает уже поставленные кнопки и не шлёт второй приказ. */
(() => {
  'use strict';
  function rows(root = document) {
    const scope = root?.querySelectorAll ? root : document;
    return [...scope.querySelectorAll('.campCompanion [data-weapon-uid]')].map(button => ({
      uid: Number(button.getAttribute('data-weapon-uid')),
      action: button.getAttribute('data-companion-action') || '',
      disabled: !!button.disabled,
    }));
  }
  window.terraCompanionGuns = Object.freeze({
    selector: '.campCompanion',
    give: 'giveGun',
    take: 'takeGun',
    rows,
  });
})();
