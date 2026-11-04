/* Optional save compatibility for the unique sai.
 * Older builds reject the whole profile when any weapon type is missing from
 * their registry (they do not drop just that item). A clone written to storage
 * keeps the same object as a katana plus an optional marker; the live player
 * and the supporting build keep wt sewer_sai. Profile version is unchanged.
 */
import { SAI_WEAPON } from './sewer-register.js';

export const SAI_HOLD = 'sewer_sai';
const LEGACY_WT = 'katana';

export function encodeSaiForLegacy(node, seen = new Set()) {
  if (!node || typeof node !== 'object' || seen.has(node)) return node;
  seen.add(node);
  if (!Array.isArray(node) && node.wt === SAI_WEAPON) {
    node.wt = LEGACY_WT;
    node.hold = SAI_HOLD;
  }
  for (const value of Object.values(node)) encodeSaiForLegacy(value, seen);
  return node;
}

export function restoreSaiFromLegacy(node, seen = new Set()) {
  if (!node || typeof node !== 'object' || seen.has(node)) return node;
  seen.add(node);
  if (!Array.isArray(node) && node.hold === SAI_HOLD && node.wt === LEGACY_WT) {
    node.wt = SAI_WEAPON;
    delete node.hold;
  }
  for (const value of Object.values(node)) restoreSaiFromLegacy(value, seen);
  return node;
}

export function legacySaiCandidate(candidate) {
  if (!candidate || typeof candidate !== 'object') return candidate;
  let copy;
  try { copy = JSON.parse(JSON.stringify(candidate)); }
  catch { return candidate; }
  return encodeSaiForLegacy(copy);
}

export function installSaiSave(game) {
  if (!game || typeof game.saveStore !== 'function') return false;
  if (!game._saiSaveInstalled) {
    const originalStore = game.saveStore;
    game.saveStore = function (...args) {
      return wrapStore(originalStore.apply(this, args));
    };
    game._saiSaveInstalled = true;
  }
  try { game.saveStore(); } catch { /* store may be unavailable until play */ }
  return true;
}

function wrapStore(store) {
  if (!store || store._saiSaveWrapped) return store;
  const write = store.write;
  const load = store.load;
  if (typeof write === 'function') {
    store.write = function (candidate, ...args) {
      return write.call(this, legacySaiCandidate(candidate), ...args);
    };
  }
  if (typeof load === 'function') {
    store.load = function (...args) {
      const result = load.apply(this, args);
      if (result?.candidate?.p) restoreSaiFromLegacy(result.candidate.p);
      return result;
    };
  }
  store._saiSaveWrapped = true;
  return store;
}
