/* Targeted transaction test using the bundle's actual JH/Xc/UID/makeWeapon code.
 * Storage outcomes and non-reward subsystems are fixtures; browser reload,
 * schema/lease integration and combat presentation require browser coverage.
 */
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import vm from 'node:vm';
import { registerSewerContent, RAPHAEL_BOSS, SAI_WEAPON } from '../play/ui/sewer-register.js';
import { installSewerReward } from '../play/ui/sewer-reward.js';

const bundle = readFileSync(new URL('../play/index.html', import.meta.url), 'utf8');
function between(start, end) {
  const a = bundle.indexOf(start), b = bundle.indexOf(end, a);
  assert(a >= 0 && b > a, `Native anchor changed: ${start}`);
  return bundle.slice(a, b);
}

const bridge = {
  WeaponBuilder: class {},
  bosses: {moloh: {}},
  weapons: {katana: {cls: 'melee', dmg: 17}},
  grades: [1, 4, 8, 13, 19, 26, 50].map(lvl => ({lvl})),
};
assert(registerSewerContent(bridge));
assert(Object.hasOwn(bridge.weapons, SAI_WEAPON));
assert(!Object.keys(bridge.weapons).includes(SAI_WEAPON), 'Unique sai leaked into random weapon pool');

const context = vm.createContext({
  structuredClone, Math, Object, Number, Date, JSON,
  vi: bridge.bosses, Tt: bridge.weapons, Be: {}, Zo: [],
  Sl: structuredClone, xI: () => ({v: 1, seq: 0, entries: []}),
  B: {mastery: {damageDivisor: 1, kill: 1, killPerLevel: 0}},
  Bm: () => ({contractEvent() {}}),
  ji: (p, amount) => {p.xp += amount;}, K3: () => 1, hi: () => 0,
  Dl: () => ({chest: [], direct: []}), lu: () => 0, uo: () => false,
  ug: () => ({v: 1, indexByKey: {}, domains: {}}), dg() {}, Ot: () => 0,
  se: Array.from({length: 7}, () => ({fx: 0})), hu: [], SE: [],
  EE: {katana: ['a', 'b', 'c']}, mD: () => null,
});
vm.runInContext([
  between('function*ca(', 'var Zc='),
  between('function Xc(', 'var g2='),
  between('function Nk(', 'var Sl,ZH='),
].join('\n'), context);
const nativeMakeWeapon = vm.runInContext(
  `({${between('makeWeapon(e,t=0', ',randArmor(')}}).makeWeapon`, context,
);

function fixture(snapshot = null) {
  const p = snapshot?.p ?? {alive: true, level: 20, hp: 100, maxHp: 100,
    xp: 0, sp: 0, uid: 1, days: 1, x: 48056, z: 48056, inv: {},
    weapons: [], armor: [], eq: [], skills: {}, camp: {}};
  let raw = JSON.stringify(snapshot ?? {p, sd: {}, def: {}}), failNext = null;
  const store = {
    generation: 0, sessionToken: 'fixture', blocked: false,
    canWriteProtected() {return !this.blocked;},
    verifiedRaw: () => ({ok: true, raw}),
    write(candidate) {
      if (failNext) {
        const status = failNext; failNext = null;
        if (status === 'uncertain') this.blocked = 'write-unverified';
        return {ok: false, status, reason: status === 'uncertain' ? 'write-unverified' : 'storage-write'};
      }
      raw = JSON.stringify(candidate); this.generation++;
      return {ok: true, status: 'committed'};
    },
    halt(reason) {this.blocked = reason;},
  };
  let rolls = 0;
  const game = {
    p, state: 'play', storyData: snapshot?.sd ?? {}, defeated: snapshot?.def ?? {},
    world: {inDungeon: true, conts: []}, enemies: [],
    dg: {key: '12,-10', sewer: true, ch: {cx: 1000, cz: 1000}, from: {x: 12, z: -7}},
    saveStore: () => store,
    saveResult: result => result,
    buildSaveCandidate() {return {p: structuredClone(this.p), sd: this.storyData, def: this.defeated};},
    markCrystalLive() {this._crystalLiveStore = store; this._crystalLiveGeneration = store.generation;},
    makeWeapon(...args) {rolls++; return nativeMakeWeapon.apply(this, args);},
    rollLoot(key, extra) {return {receiver: this, key, extra};},
  };
  game.markCrystalLive();
  const api = installSewerReward(game, bridge);
  const enemy = () => ({boss: RAPHAEL_BOSS, base: 'mutant', lvl: 15, xp: 1000,
    x: 48056, z: 48056, hp: 1, dead: false});
  function victory(target) {
    return context.JH(game, target, {publish(candidate, save) {
      for (const key of ['uid', 'trophy', 'durableChests', 'g07WorldBosses', 'kills',
        'gunKills', 'xp', 'level', 'sp', 'hp', 'maxHp', 'mast', 'camp']) {
        if (Object.hasOwn(candidate, key)) game.p[key] = candidate[key];
      }
      game.storyData = save.sd; game.defeated = save.def;
    }});
  }
  return {game, api, enemy, victory, fail(status = 'failedKnownNotWritten') {failNext = status;},
    stored: () => JSON.parse(raw), rolls: () => rolls};
}

const test = fixture(), boss = test.enemy();
const untouched = test.game.rollLoot('crate', 'forwarded');
assert.equal(untouched.receiver, test.game);
assert.equal(untouched.extra, 'forwarded');
assert.equal(test.game.rollLoot(RAPHAEL_BOSS).length, 0);
assert.equal(test.game.p.uid, 1, 'Live rollLoot mutated UID');
assert(test.api.canSpawn());
test.fail();
assert.equal(test.victory(boss).status, 'failedKnownNotWritten');
assert(!boss._durableCommitted);
assert(!test.game.defeated['12,-10']);
assert(!test.game.p.durableChests);
assert.equal(test.game.p.uid, 1);
assert.equal(test.rolls(), 1);
assert(boss._durableVictory.retryable);
const firstRoll = structuredClone(boss._durableVictory.items);
assert.equal(test.victory(boss).status, 'committed');
assert(boss._durableCommitted);
assert.equal(test.rolls(), 1, 'Retry rerolled unique reward');
assert.equal(test.game.defeated['12,-10'], 1);
assert(!test.api.canSpawn());
assert.equal(test.game.p.durableChests.entries.length, 1);
const chest = test.game.p.durableChests.entries[0];
assert.equal(chest.domain, 'dungeon');
assert.equal(chest.key, '12,-10');
assert.equal(chest.x, 56);
assert.equal(chest.z, 56);
assert.equal(chest.items[0].weapon.wt, SAI_WEAPON);
assert.equal(chest.items[0].weapon.g, 4);
assert.equal(chest.items[0].weapon.r, 4);
assert.deepEqual(chest.items, firstRoll);
assert.equal(test.victory(boss).reason, 'already-committed');
assert.equal(test.game.p.durableChests.entries.length, 1);
const reload = fixture(test.stored());
assert(!reload.api.canSpawn(), 'Reload allowed completed sewer boss to respawn');
assert.equal(reload.game.p.durableChests.entries.length, 1);
assert.equal(reload.game.p.durableChests.entries[0].items[0].weapon.uid, chest.items[0].weapon.uid);
assert.equal(reload.game.p.x, 12, 'Dungeon write persisted synthetic player coordinates');
assert.equal(reload.game.p.z, -7);
reload.game.defeated = {};
reload.game._coopGuest = true;
assert(!reload.api.canSpawn(), 'Guest can spawn protected unique encounter');

const stale = fixture(), changedBoss = stale.enemy();
stale.fail();
assert.equal(stale.victory(changedBoss).status, 'failedKnownNotWritten');
changedBoss.lvl++;
assert.equal(stale.victory(changedBoss).reason, 'stale-victory');
assert(!stale.game.defeated['12,-10']);
assert(!stale.game.p.durableChests);
assert.equal(stale.game.p.uid, 1);
assert(!changedBoss._durableVictory, 'Stale retry cache was retained');
assert.equal(stale.victory(changedBoss).status, 'committed');
assert.equal(stale.game.p.durableChests.entries.length, 1);

const uncertain = fixture(), unknownBoss = uncertain.enemy();
uncertain.fail('uncertain');
assert.equal(uncertain.victory(unknownBoss).status, 'uncertain');
assert(!unknownBoss._durableCommitted);
assert(!unknownBoss._durableVictory.retryable);
assert(!uncertain.game.defeated['12,-10']);
assert(!uncertain.game.p.durableChests);
assert.equal(uncertain.game.p.uid, 1);
assert.equal(uncertain.victory(unknownBoss).reason, 'write-unverified');
console.log('PASS: native JH/Xc failed-write retry, stale/uncertain rejection, one committed chest/UID, snapshot reload gate, reward-only registry, detached construction');
