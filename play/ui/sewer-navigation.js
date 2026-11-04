/* UI-only navigation for the collector. Story and contract target providers
 * are replaced only during a synchronous native arrow/minimap render, then
 * restored even if rendering throws. No quest or save state is changed.
 */
const installed = new WeakMap();

export function installSewerNavigation(game, {active, pumps, center, boss}) {
  if (installed.has(game)) return installed.get(game);
  const ui = game.ui;
  const nativeObjective = ui.objective;
  let showingCollector = false, collectorTitle = '';

  function objective() {
    if (!active() || !game.dg?.ch || !game.p) return null;
    const key = game.dg.key;
    if (game.defeated?.[key]) {
      const chest = game.p.durableChests?.entries?.find(entry =>
        entry.domain === 'dungeon' && entry.key === key && entry.kind === 'boss' && entry.items?.length);
      if (chest) return {
        title: 'Коллектор · заберите награду',
        hint: 'Откройте сундук охотника. Лестница на поверхность находится в первом секторе.',
        label: 'Награда',
        target: {x: game.dg.ch.cx * 48 + chest.x, z: game.dg.ch.cz * 48 + chest.z},
      };
      const start = center(0);
      return {
        title: 'Коллектор · вернитесь к лестнице',
        hint: 'Вылазка завершена. Лестница на поверхность находится в первом секторе.',
        label: 'Лестница',
        target: game.dg.ch.ents?.find(entry => entry.kind === 'exit') || {x: start.x, z: start.z - 4},
      };
    }
    const running = pumps();
    const pending = [1, 3].filter(index => !running.has(index)).map(index => {
      const room = center(index);
      return {index, x: room.x + 4, z: room.z};
    }).sort((a, b) => Math.hypot(game.p.x - a.x, game.p.z - a.z) - Math.hypot(game.p.x - b.x, game.p.z - b.z));
    if (pending.length) return {
      title: `Коллектор · насосы ${running.size}/2`,
      hint: 'Сухие дорожки обходят воду. Найдите и включите оба насоса.',
      label: `Насос ${pending[0].index === 1 ? 1 : 2}`,
      target: pending[0],
    };
    const hunter = boss();
    return {
      title: hunter ? 'Коллектор · последний из клана' : 'Коллектор · нижняя камера',
      hint: 'Охотник ждёт в нижней камере. Уклоняйтесь от красных колец и рывка.',
      label: hunter ? 'Рафаэль' : 'Нижняя камера',
      target: hunter || center(6),
    };
  }

  function sync() {
    const state = objective();
    if (!state) {
      if (showingCollector) {
        showingCollector = false;
        // A native camp tracker may already have reclaimed the objective.
        if (document.getElementById('objT')?.textContent === collectorTitle) nativeObjective.call(ui);
      }
      return;
    }
    showingCollector = true;
    collectorTitle = state.title;
    const distance = Math.round(Math.hypot(game.p.x - state.target.x, game.p.z - state.target.z));
    for (const [id, text] of [
      ['objT', state.title], ['objH', state.hint], ['objD', `${state.label} · ${distance} м`],
    ]) {
      const element = document.getElementById(id);
      if (element && element.textContent !== text) element.textContent = text;
    }
  }

  function renderLocally(render, context, args) {
    const state = objective();
    if (!state) return render.apply(context, args);
    const restores = [];
    function replace(owner, name, value) {
      const descriptor = Object.getOwnPropertyDescriptor(owner, name);
      restores.push(() => {
        if (descriptor) Object.defineProperty(owner, name, descriptor);
        else delete owner[name];
      });
      owner[name] = value;
    }
    try {
      replace(game, 'storyTarget', () => state.target);
      if (game.camp) replace(game.camp, 'contractTarget', () => null);
      return render.apply(context, args);
    } finally {
      for (const restore of restores.reverse()) restore();
    }
  }

  for (const name of ['arrow', 'minimap']) {
    const render = ui[name];
    ui[name] = function(...args) { return renderLocally(render, this, args); };
  }
  // Native hud writes distance/progress after arrow(), including contract text.
  // Replace it in the same render, avoiding a frame of surface guidance.
  const hud = ui.hud;
  ui.hud = function(...args) { const result = hud.apply(this, args); sync(); return result; };
  ui.objective = function(...args) { const result = nativeObjective.apply(this, args); sync(); return result; };
  const api = Object.freeze({sync});
  installed.set(game, api);
  return api;
}
