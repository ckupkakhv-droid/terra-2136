import { showRecording } from './sewer-cinematic.js';
import { SEWER_KEY } from './sewer-register.js';

// The clue is derived from existing durable progress. The one-time toast stores
// optional player.trace and uses the normal save; no other profile fields change.
export function installMoscowSignal(game, onSignal = () => {}, isBusy = () => false) {
  const button = document.createElement('button');
  button.id = 'moscowSignalAction';
  button.type = 'button';
  button.textContent = 'Прочитать перехват';
  button.hidden = true;
  document.body.append(button);
  const eligible = () => !!game.p?.alive && !!game.defeated?.[SEWER_KEY] &&
    game.p.routeTransit?.stage === 2 && !game._coopGuest && !game.net?.role;
  function nearby() {
    if (!eligible() || isBusy() || game.state !== 'play' || game.world?.inDungeon || game.dungeonTransition) return null;
    const sites = window.TerraWorldSites;
    if (!sites?.placementForContainer || !sites?.noteFor) return null;
    return game.world.conts?.find(container =>
      Math.hypot(game.p.x - container.x, game.p.z - container.z) <= 2.3 &&
      game.world.segHit(game.p.x, game.p.z, container.x, container.z, 1.1) < 0 &&
      sites.placementForContainer(game, container)?.id === 'signal' && sites.noteFor(game, container)) || null;
  }
  button.addEventListener('pointerdown', event => event.stopPropagation());
  button.addEventListener('click', event => {
    event.stopPropagation();
    if (!nearby()) return;
    showRecording(game, '', {
      heading: 'РАДИОПОСТ НОЛЬ · МОСКОВСКИЙ ПЕРЕХВАТ',
      finishLabel: 'Вернуться',
      onFinish() {
        onSignal();
        button.hidden = !nearby();
        if (!button.hidden) button.focus({preventScroll:true});
        else {
          const canvas=document.getElementById('c');
          if (canvas && !canvas.hasAttribute('tabindex')) canvas.tabIndex=-1;
          canvas?.focus({preventScroll:true});
        }
      },
      frames: [
        ['РУЧНАЯ ЛЕНТА', 'На старой катушке повторяется тот же машинный позывной, что звучал под коллектором. Кто-то записал его поверх сигнала «Арес-7».'],
        ['КОНТУР', '«Московский контур: приём. Патрульные узлы активны. Дальнейшие команды — после проверки линии». На расшифровке помета: «Шаги и скрежет металла».'],
        ['СЛЕД ВЕДЁТ ДАЛЬШЕ', 'Координаты стёрты помехами. Сохраните частоту: она может связать радиопост, коллектор и действующие машины.'],
      ],
    });
  });
  return Object.freeze({ eligible, update() {
    // Optional player.trace survives load and respawn. Older builds ignore it.
    if (eligible() && game.state === 'play' && !game.world?.inDungeon &&
        !game.dungeonTransition && game.p.trace !== 1) {
      game.p.trace = 1;
      game.ui.toast('Новый след: Московский перехват в журнале подземной карты');
      try { game.save?.(); } catch { /* the flag stays on the player for the next successful save */ }
    }
    button.hidden = !nearby();
  } });
}
