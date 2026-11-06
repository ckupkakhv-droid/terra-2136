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
const native = cut('function ic(e){', 'function VD(e,t)') + '\n' + cut('function YD(e,t){', 'var Y9');
assert.match(native, /function wm\(e,t,i=!1\)/);
assert.match(native, /function YD\(e,t\)/);
assert.doesNotMatch(native, /function Vtt\(/);

const context = {
  Math, Number, Set, WeakMap,
  Y9: new WeakMap(),
  Tt: {
    stick: {name:'Палка', cls:'melee', dmg:9, rate:.42},
    shotgun: {name:'Двустволка', cls:'gun', dmg:12, rate:.55, mag:2, ammo:'a12', speed:55, col:'#ffb070'},
    rifle: {name:'Автомат', cls:'gun', dmg:15, rate:.095, mag:30, ammo:'a545', speed:80, col:'#fff0a0'},
    plain: {name:'Без темпа', cls:'gun', dmg:5, mag:4, speed:60, col:'#fff'},
  },
  ai: [{mul:1}],
  se: [{mul:1}],
  B: {bag:24, camp:{guards:{range:16, cooldown:.9, maxAccuracy:.98, accuracy:.7, skillAccuracy:.015, skillDamage:.08}}},
  xi: () => true,
  Xi: () => () => 0,
  Vs: () => 1,
  Ko: () => 1,
  GD: () => 'companion',
  Cd: (a, b) => Math.hypot((a.x || 0) - (b.x || 0), (a.z || 0) - (b.z || 0)),
  companion: null,
};
context.Ti = () => context.companion;
vm.createContext(context);
vm.runInContext(native, context);

const gun = (uid, wt, nm, mag) => ({uid, wt, nm, mag, g:0, r:0, e:0});
function rig(mode = 'follow', v = 3) {
  const resident = {id:'qa', pos:{x:0, z:0}, wounded:false, injuredUntil:0, skills:{shoot:5}, gear:{weapon:null, armor:{note:'vest'}}};
  const state = {v, mode};
  const store = {canWriteProtected(){ return true; }, sessionToken:'tok', generation:1, blocked:false};
  const player = {alive:true, x:1, z:0, level:20, eq:[], weapons:[], inv:{a12:10, a545:10}, camp:{sim:{tick:5}, seed:'seed'}};
  const game = {
    state:'play', t:10, p:player, world:{inDungeon:false, segHit(){ return -1; }},
    dungeonTransition:false, _coopGuest:false, net:null,
    saveStore:() => store, _crystalLiveStore:store, _crystalLiveGeneration:1,
    save:() => ({status:'committed'}),
    enemies:[], bullets:[], sfx:{}, beam(){},
  };
  context.companion = {state, resident};
  context.Y9 = new WeakMap();
  return {game, player, resident, state};
}
const pile = (player, resident) => JSON.stringify([...(player.weapons || []), resident.gear.weapon].filter(Boolean).map(item => JSON.stringify(item)).sort());

test('отказ дальше 3 м не трогает стопку и не создаёт копию', () => {
  const {player, resident} = rig();
  const item = gun(7, 'shotgun', 'Двустволка', 2);
  player.weapons = [item];
  player.x = 6;
  const before = pile(player, resident);
  const refused = context.wm(player, 7, false);
  assert.equal(refused.ok, false);
  assert.match(refused.reason, /3 м/);
  assert.equal(player.weapons.length, 1);
  assert.equal(player.weapons[0], item);
  assert.equal(resident.gear.weapon, null);
  assert.equal(pile(player, resident), before);
});

test('возврат ближе 3 м переносит тот же ствол без второй копии', () => {
  const {player, resident, state} = rig();
  const carried = gun(7, 'shotgun', 'Двустволка', 2);
  const other = gun(8, 'rifle', 'Автомат', 10);
  resident.gear.weapon = carried;
  player.weapons = [other];
  player.x = 1;
  const before = pile(player, resident);
  const moved = context.wm(player, 7, true);
  assert.equal(moved.ok, true);
  assert.equal(state.v, 3);
  assert.equal(resident.gear.weapon, null);
  assert.equal(player.weapons.at(-1), carried);
  assert.equal(player.weapons.filter(item => item.uid === 7).length, 1);
  assert.equal(pile(player, resident), before);
});

test('чужой uid не списывает первый свободный ствол', () => {
  const {player, resident} = rig();
  const first = gun(1, 'rifle', 'Автомат', 10);
  const second = gun(2, 'shotgun', 'Двустволка', 2);
  player.weapons = [first, second];
  player.x = 1;
  const refused = context.wm(player, 2, false);
  assert.equal(refused.ok, false);
  assert.deepEqual(player.weapons.map(item => item.uid), [1, 2]);
  assert.equal(resident.gear.weapon, null);
  assert.equal(player.weapons[0], first);
  assert.equal(player.weapons[1], second);
});

test('ожидание и следование без годной цели не тратят патроны и не перезаряжают', () => {
  for (const mode of ['wait', 'follow']) {
    const {game, player, resident} = rig(mode, 3);
    resident.gear.weapon = gun(7, 'shotgun', 'Двустволка', 2);
    game.enemies = mode === 'wait' ? [{dead:false, pineBlocked:false, aggro:true, x:2, z:0}] : [];
    context.YD(game, .3);
    assert.equal(resident.gear.weapon.mag, 2, mode);
    assert.equal(game.bullets.length, 0, mode);
    assert.equal(player.inv.a12, 10, mode);
    if (mode === 'follow') assert.equal(context.Y9.get(game).wait, .2);
    if (mode === 'wait') assert.equal(context.Y9.get(game).wait, 0);
  }
});

test('выстрел только у gun в режиме follow: один снаряд, кулдаун ствола, без дозарядки', () => {
  const calm = rig('follow', 3);
  calm.resident.gear.weapon = gun(7, 'shotgun', 'Двустволка', 2);
  calm.game.enemies = [{dead:false, pineBlocked:false, aggro:false, x:2, z:0}];
  context.YD(calm.game, .3);
  assert.equal(calm.game.bullets.length, 0);
  assert.equal(calm.resident.gear.weapon.mag, 2);

  const melee = rig('follow', 3);
  melee.resident.gear.weapon = gun(4, 'stick', 'Сухая', 0);
  melee.game.enemies = [{dead:false, pineBlocked:false, aggro:true, x:2, z:0}];
  context.YD(melee.game, .3);
  assert.equal(melee.game.bullets.length, 0);
  assert.equal(melee.player.inv.a12, 10);

  const off = rig('follow', 1);
  off.resident.gear.weapon = gun(7, 'shotgun', 'Двустволка', 2);
  off.game.enemies = [{dead:false, pineBlocked:false, aggro:true, x:2, z:0}];
  context.YD(off.game, .3);
  assert.equal(off.game.bullets.length, 0);
  assert.equal(off.resident.gear.weapon.mag, 2);

  const shot = rig('follow', 3);
  shot.resident.gear.weapon = gun(7, 'shotgun', 'Двустволка', 2);
  shot.game.enemies = [{dead:false, pineBlocked:false, aggro:true, x:2, z:0}];
  context.YD(shot.game, .3);
  assert.equal(shot.game.bullets.length, 1);
  assert.equal(shot.resident.gear.weapon.mag, 1);
  assert.equal(shot.player.inv.a12, 10);
  assert.equal(shot.game.bullets[0].wt, 'guard');
  assert.ok(shot.game.bullets[0].dmg > 0);
  assert.equal(context.Y9.get(shot.game).wait, .55);
  context.YD(shot.game, .05);
  assert.equal(shot.resident.gear.weapon.mag, 1);
  assert.equal(shot.game.bullets.length, 1);

  const fallback = rig('follow', 3);
  fallback.resident.gear.weapon = gun(11, 'plain', 'Без темпа', 4);
  fallback.game.enemies = [{dead:false, pineBlocked:false, aggro:true, x:2, z:0}];
  context.YD(fallback.game, .3);
  assert.equal(fallback.game.bullets.length, 1);
  assert.equal(context.Y9.get(fallback.game).wait, .9);
  assert.equal(fallback.resident.gear.armor.note, 'vest');
});

test('текст защиты описывает условия и не обещает отдельный бой', () => {
  const armed = rig('follow', 3);
  armed.resident.gear.weapon = gun(7, 'shotgun', 'Двустволка', 2);
  assert.match(context.jD({}), /Защита героя · Двустволка/);
  const waiting = rig('wait', 3);
  waiting.resident.gear.weapon = gun(7, 'shotgun', 'Двустволка', 1);
  assert.match(context.jD({}), /не стреляет/);
  const bare = rig('follow', 3);
  bare.resident.gear.weapon = null;
  assert.match(context.jD({}), /личное огнестрельное оружие/);
  assert.match(context.jD({}), /Ближний бой пока не поддерживается/);
  const cold = rig('follow', 1);
  cold.resident.gear.weapon = gun(7, 'shotgun', 'Двустволка', 0);
  assert.match(context.jD({}), /Защита выключена/);
  for (const sample of ['follow', 'wait']) {
    const view = rig(sample, 3);
    view.resident.gear.weapon = sample === 'follow' ? gun(7, 'shotgun', 'Двустволка', 2) : null;
    assert.doesNotMatch(context.jD({}), /сражаться|газ блокир/i);
  }
});

test('пилот не объявляет новую команду брони или боя', () => {
  const ui = fs.readFileSync(new URL('../play/ui/companion-card.js', import.meta.url), 'utf8');
  assert.doesNotMatch(ui, /сражаться/);
  assert.doesNotMatch(ui, /setAttribute\(\s*['"]data-companion-action/);
  assert.doesNotMatch(ui, /gear\.armor\s*=/);
  assert.match(ui, /За мной/);
  assert.match(ui, /giveGun/);
  assert.match(ui, /takeGun/);
});
