import { showRecording } from './sewer-cinematic.js';
import { SEWER_KEY } from './sewer-register.js';

// This clue is derived from existing durable progress; listening never writes a save.
export function installMoscowSignal(game, onSignal = () => {}, isBusy = () => false) {
  const button = document.createElement('button');
  button.id = 'moscowSignalAction';
  button.type = 'button';
  button.textContent = 'Прочитать перехват';
  button.hidden = true;
  document.body.append(button);
  let announcedPlayer = null;

  const eligible = () => !!game.p?.alive && !!game.defeated?.[SEWER_KEY] &&
    game.p.routeTransit?.stage === 2 && !game._coopGuest && !game.net?.role;
  function nearby() {
    if (!eligible() || isBusy() || game.state !== 'play' || game.world?.inDungeon || game.dungeonTransition) return null;
    const sites = window.TerraWorldSites;
    if (!sites?.placementForContainer || !sites?.noteFor) return null;
    return game.world.conts?.find(container =>
      Math.hypot(game.p.x - container.x, game.p.z - container.z) <= 2.3 &&
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
    if (eligible() && game.state === 'play' && !game.world?.inDungeon &&
        !game.dungeonTransition && announcedPlayer !== game.p) {
      announcedPlayer = game.p;
      game.ui.toast('Новый след: Московский перехват в журнале подземной карты');
    }
    button.hidden = !nearby();
  } });
}
