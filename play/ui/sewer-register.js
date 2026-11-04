import { makeSaiGeometry } from './sewer-gear.js';
/* Run before window.load: native save validation must know saved sewer gear. */
export const SEWER_KEY = '12,-10';
export const RAPHAEL_BOSS = 'sewer_raphael';
export const RAPHAEL_MODEL = 'sewer_raphael_model';
export const SAI_WEAPON = 'sewer_sai';

export function registerSewerContent(bridge = globalThis.TERRA_SEWER_BRIDGE) {
  if (!bridge?.bosses || !bridge?.weapons?.katana || typeof bridge.WeaponBuilder !== 'function') return false;
  if (bridge.WeaponBuilder) bridge.makeSaiGeometry=()=>makeSaiGeometry(bridge);
  if (!Object.hasOwn(bridge.weapons, SAI_WEAPON)) {
    // Native random drops enumerate this registry. The sai is reward-only;
    // native validation and UID scans use Object.hasOwn and still recognize it.
    Object.defineProperty(bridge.weapons, SAI_WEAPON, {
      enumerable: false,
      configurable: true,
      writable: true,
      value: {
        ...bridge.weapons.katana,
        name: 'Парные саи',
        dmg: 15,
        rate: .28,
        reach: 2,
        arc: 1.9,
        kb: .9,
        col: '#d29276',
        combo: [1, 1.1, 1.5],
      },
    });
  }
  if (!Object.hasOwn(bridge.bosses, RAPHAEL_BOSS)) {
    bridge.bosses[RAPHAEL_BOSS] = {
      ...bridge.bosses.moloh,
      name: 'Рафаэль · последний из клана',
      base: 'mutant',
      model: RAPHAEL_MODEL,
      scale: .72,
      r: .85,
      h: 2.7,
      hp: 1800,
      spd: 3.8,
      dmg: 22,
      xp: 1000,
      tier: 4,
    };
  }
  return true;
}

export const sewerContentRegistered = registerSewerContent();
