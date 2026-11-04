import { RAPHAEL_BOSS, SAI_WEAPON, SEWER_KEY, registerSewerContent } from './sewer-register.js';

const installed = new WeakMap();

function rewardGrade(level, grades) {
  if (Array.isArray(grades) && grades.length) {
    // S80 remains subject to its native strict level rule; this reward caps at S.
    let result = 0;
    for (let i = 0; i < Math.min(grades.length, 6); i++) {
      if (Number.isFinite(grades[i]?.lvl) && level >= grades[i].lvl) result = i;
    }
    return result;
  }
  // Conservative fallback below native D/C/B level thresholds (4/8/13).
  return Math.max(0, Math.min(3, Math.floor(level / 5)));
}

export function installSewerReward(game, bridge = globalThis.TERRA_SEWER_BRIDGE) {
  if (installed.has(game)) return installed.get(game);
  if (!registerSewerContent(bridge) || typeof game.rollLoot !== 'function') return null;
  const originalLoot = game.rollLoot;

  game.rollLoot = function(key, ...args) {
    if (key !== RAPHAEL_BOSS) return originalLoot.call(this, key, ...args);
    // JH calls rollLoot on a detached game view. Generating on the live player
    // would mutate its UID before storage commit; never fall back to that path.
    if (this === game || this.p === game.p || this._coopGuest || this.net?.role ||
        !this.world?.inDungeon || !this.dg?.sewer || this.dg.key !== SEWER_KEY) return [];
    const level = Number.isFinite(this.p.level) ? this.p.level : 1;
    const weapon = this.makeWeapon('katana', rewardGrade(level, bridge.grades), 4, null);
    weapon.wt = SAI_WEAPON;
    weapon.nm = '«Последний из клана»';
    weapon.aff = [
      {id: 'bleed', v: .14},
      {id: 'crit', v: .08},
      {id: 'speed', v: .08},
      {id: 'leech', v: .03},
    ];
    return [{weapon}];
  };

  const api = Object.freeze({
    boss: RAPHAEL_BOSS,
    weapon: SAI_WEAPON,
    canSpawn() {
      return game.state === 'play' && game.p?.alive === true &&
        !!game.world?.inDungeon && game.dg?.sewer === true &&
        game.dg.key === SEWER_KEY && !game.dungeonTransition &&
        !game._coopGuest && !game.net?.role && !game.defeated?.[game.dg.key] &&
        !game.enemies?.some(enemy => enemy.boss === RAPHAEL_BOSS && !enemy.dead);
    },
  });
  installed.set(game, api);
  return api;
}
