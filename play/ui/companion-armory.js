/* Склад стволов — уже построенный сундук в 24 м от лагеря (t:"chest", items[{weapon}]).
   Выдача и сдача переносят тот же объект. Новых полей сейва нет.
   Дальний бой разведчика здесь не появляется: его симуляции в игре нет. */
(() => {
  'use strict';
  const GUNS = new Set(['revolver', 'shotgun', 'rifle', 'railgun']);
  const REACH = 24;

  const gameOf = () => window.game || null;
  const dist = (a, b) => Number.isFinite(a?.x) && Number.isFinite(a?.z) && Number.isFinite(b?.x) && Number.isFinite(b?.z)
    ? Math.hypot(a.x - b.x, a.z - b.z) : Infinity;
  const isGun = item => !!item && GUNS.has(item.wt) && Number.isSafeInteger(item.uid) && item.uid > 0;
  const homeOf = game => game.homePos?.() || null;

  function chests(player, home) {
    return (player?.base || []).filter(row => row && row.t === 'chest' && dist(row, home) <= REACH);
  }

  function owners(player, uid) {
    const found = [];
    for (const item of player?.weapons || []) if (item?.uid === uid) found.push('pack');
    for (const item of player?.eq || []) if (item?.uid === uid) found.push('eq');
    for (const item of Object.values(player?.mods || {})) if (item?.uid === uid) found.push('mod');
    for (const resident of Object.values(player?.camp?.settlers || {})) {
      if (resident?.gear?.weapon?.uid === uid) found.push('settler');
    }
    for (const box of player?.base || []) {
      for (const row of box?.items || []) if (row?.weapon?.uid === uid) found.push('chest');
    }
    return found;
  }

  function usable(player, item) {
    if (!isGun(item) || item.lock || item.fav) return false;
    if (item.g === 6 && !(Number.isFinite(player.level) && player.level >= 50)) return false;
    const who = owners(player, item.uid);
    return who.length === 1 && who[0] === 'chest';
  }

  function stockGuns(player, home, uid) {
    const rows = [];
    for (const box of chests(player, home)) {
      for (const row of box.items || []) {
        if (!usable(player, row?.weapon)) continue;
        if (uid != null && row.weapon.uid !== uid) continue;
        rows.push({box, row});
      }
    }
    rows.sort((a, b) => (b.row.weapon.mag > 0) - (a.row.weapon.mag > 0) || a.row.weapon.uid - b.row.weapon.uid);
    return rows;
  }

  function roleNeeds(camp, resident) {
    if (!resident || resident.dead || resident.captive) return '';
    const state = camp?.fieldCompanion;
    if (state?.settlerId === resident.id && ['follow', 'wait'].includes(state.mode)) return 'companion';
    if (resident.job === 'scout') return 'scout';
    if ((resident.job === 'guard' || resident.job === 'patrol') && resident.order?.postId) return 'guard';
    return '';
  }

  function keepsWeapon(camp, resident) {
    const state = camp?.fieldCompanion;
    if (resident && state?.settlerId === resident.id && ['follow', 'wait', 'return'].includes(state.mode)) return true;
    return !!roleNeeds(camp, resident);
  }

  function idleReason(camp, resident) {
    if (!resident || resident.dead || resident.captive) return 'Житель недоступен';
    if (resident.job === 'guard' || resident.job === 'patrol') return 'Охране ствол нужен на посту. Поста нет.';
    return 'Склад выдаёт ствол охране на посту, разведке и напарнику в вылазке.';
  }

  function writable(game) {
    const store = game.saveStore?.();
    if (game.world?.inDungeon || game.dungeonTransition) return 'Сундук лагеря недоступен под землёй';
    if (!store?.canWriteProtected?.() || game._crystalLiveStore !== store || game._crystalLiveGeneration !== store.generation) {
      return 'Запись лагеря сейчас закрыта';
    }
    return '';
  }

  function commit(game, mutator) {
    const blocked = writable(game);
    if (blocked) return {ok: false, reason: blocked};
    let reason = '';
    let copy = null;
    let extra = null;
    const result = game.savePlayerCandidate(player => {
      const out = mutator(player);
      if (!out?.ok) {
        reason = out?.reason || 'Не вышло';
        throw new Error(reason);
      }
      copy = player;
      extra = out;
    });
    if (result?.status !== 'committed' || !copy) return {ok: false, reason: reason || result?.reason || 'Запись не прошла'};
    game.p.base = copy.base;
    game.p.camp = copy.camp;
    if (game.p.st && copy.camp) {
      game.p.st.npc = copy.camp.settlers;
      game.p.st.fac = copy.camp.buildings;
      game.p.st.rep = copy.camp.rep;
    }
    game.markCrystalLive?.();
    return extra;
  }

  function issue(id, uid) {
    const game = gameOf();
    const home = homeOf(game);
    const resident = game?.p?.camp?.settlers?.[id];
    if (!game?.p || !home) return {ok: false, reason: 'Лагерь ещё не готов'};
    const state = game.p.camp?.fieldCompanion;
    if (state?.settlerId === id && state.mode === 'return') return {ok: false, reason: 'Напарник возвращается: новый ствол не выдаю'};
    if (!roleNeeds(game.p.camp, resident)) return {ok: false, reason: idleReason(game.p.camp, resident)};
    if (resident.gear?.weapon) return {ok: false, reason: 'У жителя уже есть оружие'};
    if (dist(resident.pos, home) > REACH) return {ok: false, reason: 'Подойдите с жителем к лагерю: сундук выдаёт ствол только в 24 м'};
    const wanted = uid == null ? null : Number(uid);
    return commit(game, player => {
      const person = player.camp?.settlers?.[id];
      const role = roleNeeds(player.camp, person);
      if (!role) return {ok: false, reason: 'Потребность уже изменилась'};
      if (person.gear?.weapon) return {ok: false, reason: 'У жителя уже есть оружие'};
      if (dist(person.pos, home) > REACH) return {ok: false, reason: 'Житель уже не у лагеря'};
      if (!chests(player, home).length) return {ok: false, reason: 'Нет сундука в 24 м от лагеря'};
      const rows = stockGuns(player, home, wanted);
      if (!rows.length) return {ok: false, reason: wanted == null ? 'В сундуке нет свободного ствола' : 'Этого ствола нет в сундуке'};
      const {box, row} = rows[0];
      const item = row.weapon;
      const before = owners(player, item.uid);
      if (before.length !== 1 || before[0] !== 'chest') return {ok: false, reason: 'Ствол числится не только в сундуке'};
      box.items.splice(box.items.indexOf(row), 1);
      person.gear = person.gear || {weapon: null, armor: null};
      person.gear.weapon = item;
      const after = owners(player, item.uid);
      if (after.length !== 1 || after[0] !== 'settler') return {ok: false, reason: 'Перенос не сошёлся'};
      const state = player.camp.fieldCompanion;
      if (role === 'companion' && state?.settlerId === id && [1, 2, 3].includes(state.v)) state.v = 3;
      return {ok: true, uid: item.uid, role, mag: item.mag};
    });
  }

  function recall(id) {
    const game = gameOf();
    const home = homeOf(game);
    const resident = game?.p?.camp?.settlers?.[id];
    const item = resident?.gear?.weapon;
    if (!game?.p || !home) return {ok: false, reason: 'Лагерь ещё не готов'};
    if (!isGun(item)) return {ok: false, reason: 'У жителя нет ствола со склада'};
    if (dist(resident.pos, home) > REACH) return {ok: false, reason: 'Сдать ствол можно у лагеря, в 24 м'};
    return commit(game, player => {
      const person = player.camp?.settlers?.[id];
      const carried = person?.gear?.weapon;
      if (!isGun(carried)) return {ok: false, reason: 'У жителя нет ствола со склада'};
      if (dist(person.pos, home) > REACH) return {ok: false, reason: 'Житель уже не у лагеря'};
      const who = owners(player, carried.uid);
      if (who.includes('eq') || who.includes('pack') || who.includes('mod')) return {ok: false, reason: 'Это оружие героя, его не забираю'};
      if (who.includes('chest') || who.filter(kind => kind === 'settler').length !== 1) return {ok: false, reason: 'Владелец ствола уже не один'};
      const box = chests(player, home)[0];
      if (!box) return {ok: false, reason: 'Нет сундука в 24 м от лагеря'};
      (box.items || (box.items = [])).push({weapon: carried});
      person.gear.weapon = null;
      const after = owners(player, carried.uid);
      if (after.length !== 1 || after[0] !== 'chest') return {ok: false, reason: 'Возврат не сошёлся'};
      return {ok: true, uid: carried.uid, mag: carried.mag};
    });
  }

  function settle(id) {
    const game = gameOf();
    const resident = game?.p?.camp?.settlers?.[id];
    if (!resident?.gear?.weapon || keepsWeapon(game.p.camp, resident)) return {ok: false, reason: 'Ствол ещё нужен'};
    return recall(id);
  }

  let hooked = false;
  function install() {
    const game = gameOf();
    const camp = game?.camp;
    if (!camp || hooked) return !!camp;
    const command = camp.commandCompanion?.bind(camp);
    const assign = camp.assignResidentTask?.bind(camp);
    if (!command || !assign) return false;
    camp.commandCompanion = function (cmd, ctx) {
      const id = game.p?.camp?.fieldCompanion?.settlerId || '';
      const result = command(cmd, ctx);
      if (result?.ok && cmd?.action === 'finish' && id) {
        const resident = game.p?.camp?.settlers?.[id];
        if (resident?.gear?.weapon && !keepsWeapon(game.p.camp, resident)) {
          const back = recall(id);
          if (back?.ok) result.stock = {uid: back.uid, where: 'chest'};
        }
      }
      return result;
    };
    camp.assignResidentTask = function (cmd, ctx) {
      const id = cmd?.residentId || '';
      const result = assign(cmd, ctx);
      if (result?.ok && id) {
        const resident = game.p?.camp?.settlers?.[id];
        if (resident?.gear?.weapon && !keepsWeapon(game.p.camp, resident)) recall(id);
      }
      return result;
    };
    hooked = true;
    return true;
  }

  function line(resident) {
    const game = gameOf();
    const home = homeOf(game);
    if (!game?.p || !resident || !home) return null;
    const held = isGun(resident.gear?.weapon) ? resident.gear.weapon : null;
    const role = roleNeeds(game.p.camp, resident);
    if (!held && !role) return null;
    const guns = stockGuns(game.p, home);
    const near = dist(resident.pos, home) <= REACH;
    const box = chests(game.p, home).length;
    const root = document.createElement('div');
    root.className = 'ccArmory';
    root.dataset.armoryResident = resident.id;
    const note = document.createElement('p');
    const name = held ? (held.nm || held.wt) + ' · uid ' + held.uid + ' · магазин ' + (held.mag ?? 0) : 'В сундуке свободных стволов: ' + guns.length;
    note.textContent = name;
    const why = document.createElement('small');
    why.textContent = role === 'scout'
      ? 'Дальнего боя разведки нет. Ствол только при себе.'
      : role === 'companion'
        ? 'В вылазке стреляет этот ствол, вслед за героем.'
        : role === 'guard'
          ? 'Охране на посту, из сундука лагеря.'
          : 'Слот свободен для сдачи в сундук.';
    const button = document.createElement('button');
    button.type = 'button';
    button.dataset.armoryAction = held ? 'recall' : 'issue';
    button.textContent = held ? 'Сдать в сундук' : 'Выдать из сундука';
    if (!held) {
      button.disabled = !near || !box || !guns.length;
      if (!box) why.textContent = 'Нет сундука в 24 м от лагеря.';
      else if (!guns.length) why.textContent = 'В сундуке нет свободного ствола. Новый не создаётся.';
      else if (!near) why.textContent = 'Житель далеко от лагеря.';
    } else if (!near || !box) {
      button.disabled = true;
      why.textContent = !box ? 'Нет сундука в 24 м от лагеря.' : 'Сдать ствол можно у лагеря, в 24 м.';
    }
    button.addEventListener('click', async event => {
      event.preventDefault();
      event.stopPropagation();
      if (button.dataset.armoryBusy === '1') return;
      button.dataset.armoryBusy = '1';
      try {
        if (typeof globalThis.terraSaveOwnership === 'function') {
          const gate = await globalThis.terraSaveOwnership(game);
          if (!gate?.ok) {
            game.ui?.toast?.(gate?.reason || 'Запись лагеря сейчас закрыта');
            return;
          }
        }
        const out = button.dataset.armoryAction === 'recall' ? recall(resident.id) : issue(resident.id);
        game.ui?.toast?.(out.reason || (out.ok ? 'Ствол переложен' : 'Не вышло'));
        game.ui?.campPanel?.refresh?.();
      } finally {
        button.dataset.armoryBusy = '0';
      }
    });
    root.append(note, why, button);
    root.dataset.armorySig = [resident.id, name, why.textContent, button.textContent, button.disabled ? '0' : '1'].join('\n');
    return root;
  }

  function place(host, block) {
    const prev = host.querySelector(':scope > .ccArmory');
    const next = block?.dataset.armorySig || '';
    if ((prev?.dataset.armorySig || '') === next) return;
    prev?.remove();
    if (block) host.append(block);
  }

  function mountCard(card, resident) {
    const layout = card?.querySelector(':scope > .ccLayout');
    if (!layout || !resident) return;
    const state = gameOf()?.p?.camp?.fieldCompanion;
    place(layout, state?.settlerId === resident.id ? line(resident) : null);
  }

  function mountDossier(root, resident) {
    const host = root?.querySelector(':scope > .fbAssignment');
    if (!host || !resident) return;
    const companion = gameOf()?.p?.camp?.fieldCompanion?.settlerId === resident.id;
    place(host, companion ? null : line(resident));
  }

  function start(tries = 0) {
    if (!install() && tries < 80) setTimeout(() => start(tries + 1), 50);
  }
  window.terraArmory = Object.freeze({
    issue, recall, settle, mountCard, mountDossier,
    roleNeeds: id => roleNeeds(gameOf()?.p?.camp, gameOf()?.p?.camp?.settlers?.[id]),
    keepsWeapon: id => keepsWeapon(gameOf()?.p?.camp, gameOf()?.p?.camp?.settlers?.[id]),
    owners: uid => owners(gameOf()?.p, Number(uid)),
  });
  if (document.readyState === 'complete') start();
  else window.addEventListener('load', () => start(), {once: true});
})();
