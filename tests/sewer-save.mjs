/* Legacy sai encoding: unknown wt rejects a whole old profile, so storage
 * keeps a katana-shaped copy plus an optional marker. Live objects stay sewer_sai. */
import assert from 'node:assert/strict';
import test from 'node:test';
import { encodeSaiForLegacy, restoreSaiFromLegacy, legacySaiCandidate } from '../play/ui/sewer-save.js';

test('storage clone becomes a katana with an optional marker', () => {
  const live = { p: { weapons: [{ uid: 4, wt: 'sewer_sai', nm: '«Последний из клана»', r: 4 }], inv: { bandage: 1 } } };
  const chest = { weapon: live.p.weapons[0] };
  live.p.durableChests = { entries: [{ items: [chest] }] };
  const stored = legacySaiCandidate(live);
  assert.equal(live.p.weapons[0].wt, 'sewer_sai');
  assert.equal(stored.p.weapons[0].wt, 'katana');
  assert.equal(stored.p.weapons[0].hold, 'sewer_sai');
  assert.equal(stored.p.weapons[0].nm, '«Последний из клана»');
  assert.equal(stored.p.durableChests.entries[0].items[0].weapon.wt, 'katana');
  assert.equal(stored.p.inv.bandage, 1);
  assert.notEqual(stored.p.weapons[0], live.p.weapons[0]);
});

test('loading the marker restores the sai without touching other gear', () => {
  const profile = { p: { weapons: [
    { uid: 1, wt: 'stick', nm: 'Палка' },
    { uid: 4, wt: 'katana', hold: 'sewer_sai', nm: '«Последний из клана»' },
  ], trace: 1 } };
  const eq = profile.p.weapons[1];
  profile.p.eq = [eq];
  restoreSaiFromLegacy(profile);
  assert.equal(profile.p.weapons[1].wt, 'sewer_sai');
  assert.equal(profile.p.eq[0].wt, 'sewer_sai');
  assert.equal('hold' in profile.p.weapons[1], false);
  assert.equal(profile.p.weapons[0].wt, 'stick');
  assert.equal(profile.p.trace, 1);
});

test('a plain katana is not rewritten', () => {
  const profile = { p: { weapons: [{ uid: 2, wt: 'katana', nm: 'Клинок' }] } };
  const stored = legacySaiCandidate(profile);
  restoreSaiFromLegacy(stored);
  assert.equal(stored.p.weapons[0].wt, 'katana');
  assert.equal(stored.p.weapons[0].hold, undefined);
});
