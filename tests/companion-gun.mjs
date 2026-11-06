import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';

const html = fs.readFileSync(new URL('../play/index.html', import.meta.url), 'utf8');
const cut = (start, end) => {
  const a = html.indexOf(start);
  const b = html.indexOf(end, a + start.length);
  assert.ok(a >= 0 && b > a, start + ' → ' + end);
  return html.slice(a, b);
};
const native = cut('function ic(e){', 'function H6(e)');
assert.match(native, /function _6\(e,t\)/);
assert.match(native, /function wm\(e,t,i=!1\)/);
assert.match(native, /_6\(e,t\)/);
assert.doesNotMatch(native, /s\.uid!==t/);

const ai = [{mul: 1}, {mul: 1.1, strict: true, lvl: 8}];
const context = {
  Math, Number,
  Tt: {
    stick: {name: 'Палка', cls: 'melee', dmg: 9},
    shotgun: {name: 'Двустволка', cls: 'gun', dmg: 12, mag: 2, ammo: 'a12'},
    rifle: {name: 'Автомат', cls: 'gun', dmg: 15, mag: 30, ammo: 'a545'},
  },
  ai,
  B: {bag: 24},
  xi: (item, level) => !ai[item?.g]?.strict || Number.isFinite(level) && level >= ai[item.g].lvl,
  Cd: (player, pos) => Math.hypot((player.x || 0) - pos.x, (player.z || 0) - pos.z),
  companion: null,
};
context.Ti = () => context.companion;
vm.createContext(context);
vm.runInContext(native, context);

const gun = (uid, wt, extra = {}) => ({uid, wt, nm: extra.nm || wt, mag: extra.mag ?? 1, g: extra.g ?? 0, r: 0, e: 0, ...extra});
function rig(distance = 1) {
  const resident = {id: 'qa', pos: {x: 0, z: 0}, gear: {weapon: null, armor: null}};
  const state = {v: 1, mode: 'follow', settlerId: 'qa'};
  const player = {x: distance, z: 0, level: 4, eq: [], weapons: [], armor: [{uid: 50, at: 'vest'}], camp: {fieldCompanion: state, settlers: {qa: resident}}};
  context.companion = {state, resident};
  return {player, resident, state};
}
const pile = (player, resident) => JSON.stringify([...(player.weapons || []), resident.gear.weapon].filter(Boolean).map(item => JSON.stringify(item)).sort());
const keys = object => Object.keys(object).sort().join(',');

test('вызов без uid переносит первый подходящий ствол и оставляет остальные', () => {
  const {player, resident, state} = rig();
  const melee = gun(1, 'stick');
  const locked = gun(2, 'rifle', {locked: true});
  const first = gun(3, 'rifle', {nm: 'Автомат'});
  const second = gun(4, 'shotgun', {nm: 'Двустволка'});
  player.weapons = [melee, locked, first, second];
  const before = pile(player, resident);
  const moved = context.wm(player);
  assert.equal(moved.ok, true);
  assert.equal(moved.publishWeapons, true);
  assert.equal(state.v, 3);
  assert.equal(resident.gear.weapon, first);
  assert.deepEqual(player.weapons.map(item => item.uid), [1, 2, 4]);
  assert.equal(player.weapons[2], second);
  assert.equal(pile(player, resident), before);
  assert.equal(resident.gear.armor, null);
  assert.equal(player.armor.length, 1);
  assert.equal(keys(state), 'mode,settlerId,v');
});

test('выбранный uid переносит именно этот ствол', () => {
  const {player, resident} = rig();
  const first = gun(3, 'rifle');
  const second = gun(4, 'shotgun');
  player.weapons = [first, second];
  const before = pile(player, resident);
  const moved = context.wm(player, 4, false);
  assert.equal(moved.ok, true);
  assert.equal(resident.gear.weapon, second);
  assert.equal(player.weapons.length, 1);
  assert.equal(player.weapons[0], first);
  assert.equal(player.weapons.filter(item => item.uid === 4).length, 0);
  assert.equal(pile(player, resident), before);
});

test('чужой, запертый, избранный, надетый и закрытый рангом uid не списывает другой ствол', () => {
  const {player, resident} = rig();
  const first = gun(3, 'rifle');
  const locked = gun(5, 'shotgun', {locked: true});
  const favorite = gun(6, 'shotgun', {fav: true});
  const worn = gun(7, 'shotgun');
  const ranked = gun(8, 'shotgun', {g: 1});
  const melee = gun(9, 'stick');
  player.eq = [worn];
  player.weapons = [first, locked, favorite, worn, ranked, melee];
  const before = pile(player, resident);
  for (const uid of [2, 5, 6, 7, 8, 9, 1.5, 0]) {
    const refused = context.wm(player, uid, false);
    assert.equal(refused.ok, false, String(uid));
    assert.match(refused.reason, /свободн/);
  }
  assert.deepEqual(player.weapons.map(item => item.uid), [3, 5, 6, 7, 8, 9]);
  assert.equal(resident.gear.weapon, null);
  assert.equal(pile(player, resident), before);
});

test('дальше 3 м отказ не меняет стопку, ровно 3 м переносит выбранный ствол', () => {
  const far = rig(3.01);
  const item = gun(4, 'shotgun');
  far.player.weapons = [gun(3, 'rifle'), item];
  const before = pile(far.player, far.resident);
  const refused = context.wm(far.player, 4, false);
  assert.equal(refused.ok, false);
  assert.match(refused.reason, /3 м/);
  assert.equal(pile(far.player, far.resident), before);
  assert.equal(far.resident.gear.weapon, null);

  const near = rig(3);
  const chosen = gun(4, 'shotgun');
  near.player.weapons = [gun(3, 'rifle'), chosen];
  const moved = context.wm(near.player, 4);
  assert.equal(moved.ok, true);
  assert.equal(near.resident.gear.weapon, chosen);
});

test('возврат ближе 3 м переносит тот же ствол без второй копии', () => {
  const {player, resident, state} = rig();
  const carried = gun(7, 'shotgun', {nm: 'Двустволка'});
  const other = gun(8, 'rifle');
  resident.gear.weapon = carried;
  player.weapons = [other];
  const before = pile(player, resident);
  const moved = context.wm(player, 7, true);
  assert.equal(moved.ok, true);
  assert.equal(state.v, 3);
  assert.equal(resident.gear.weapon, null);
  assert.equal(player.weapons.at(-1), carried);
  assert.equal(player.weapons.filter(item => item.uid === 7).length, 1);
  assert.equal(pile(player, resident), before);
  assert.equal(keys(carried), 'e,g,mag,nm,r,uid,wt');
});

test('возврат без uid забирает ствол слота, чужой uid и полный рюкзак ничего не стирают', () => {
  const {player, resident} = rig();
  const carried = gun(7, 'shotgun');
  resident.gear.weapon = carried;
  player.weapons = [gun(8, 'rifle')];
  const wrong = context.wm(player, 8, true);
  assert.equal(wrong.ok, false);
  assert.equal(resident.gear.weapon, carried);
  assert.equal(player.weapons.length, 1);

  const bare = context.wm(player, undefined, true);
  assert.equal(bare.ok, true);
  assert.equal(resident.gear.weapon, null);
  assert.equal(player.weapons.at(-1), carried);

  resident.gear.weapon = carried;
  player.weapons = Array.from({length: 24}, (_, index) => gun(100 + index, 'rifle'));
  const full = context.wm(player, 7, true);
  assert.equal(full.ok, false);
  assert.equal(resident.gear.weapon, carried);
  assert.equal(player.weapons.length, 24);
  assert.equal(player.weapons.filter(item => item.uid === 7).length, 0);
});

test('занятый слот не принимает второй ствол', () => {
  const {player, resident} = rig();
  const carried = gun(7, 'shotgun');
  const extra = gun(4, 'rifle');
  resident.gear.weapon = carried;
  player.weapons = [extra];
  const refused = context.wm(player, 4, false);
  assert.equal(refused.ok, false);
  assert.equal(resident.gear.weapon, carried);
  assert.equal(player.weapons[0], extra);
  assert.equal(player.weapons.length, 1);
});
