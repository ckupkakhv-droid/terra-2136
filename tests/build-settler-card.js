/**
 * Строки карточки стройки только форматируют уже посчитанные звание и проект.
 * Формулы опыта, fv и остатка здесь не воспроизводятся и не должны меняться в бандле.
 * Запуск: node tests/build-settler-card.js
 */
'use strict';

const fs = require('fs');
const path = require('path');
const assert = require('assert');

const html = fs.readFileSync(path.join(__dirname, '../play/index.html'), 'utf8');

function extract(name) {
  const start = html.indexOf('function ' + name + '(');
  assert.notStrictEqual(start, -1, name);
  let i = html.indexOf('{', start);
  let depth = 0;
  for (; i < html.length; i++) {
    const ch = html[i];
    if (ch === '{') depth++;
    else if (ch === '}') {
      depth--;
      if (depth === 0) return html.slice(start, i + 1);
    }
  }
  throw new Error('unclosed ' + name);
}

const buildProjectGoalLines = new Function('return ' + extract('buildProjectGoalLines'))();
const buildCrewLines = new Function('return ' + extract('buildCrewLines'))();

assert.deepStrictEqual(buildProjectGoalLines(null), []);
assert.deepStrictEqual(buildProjectGoalLines({from: 0, to: 1, remaining: 44.2}), [
  'Улучшение: ур. 0 → 1',
  'Осталось 45 ед. работы'
]);
assert.deepStrictEqual(buildCrewLines({
  title: 'Новичок', level: 1, xp: 0.25, need: 60, next: 'Следопыт',
  buildEffect: 'Стройка: +0% к скорости работы. Материалы и XP без бонуса.'
}, {name: 'Марфа'}), [
  'Марфа · Новичок · ур. 1',
  'До звания «Следопыт»: 0 / 60 опыта',
  'Стройка: +0% к скорости работы. Материалы и XP без бонуса.'
]);
assert.deepStrictEqual(buildCrewLines({
  title: 'Мастер вылазок', level: 6, xp: 12.9, need: 360, next: null, buildEffect: null
}, {name: 'Илья'}), [
  'Илья · Мастер вылазок · ур. 6',
  'Высшее звание · уровень продолжает расти'
]);
const longName = 'Архивариус Серафима Длинноименованная';
assert.ok(buildCrewLines({
  title: 'Новичок', level: 1, xp: 3, need: 60, next: 'Следопыт',
  buildEffect: 'Стройка: +0% к скорости работы. Материалы и XP без бонуса.'
}, {name: longName})[0].startsWith(longName));

for (const name of ['buildProjectGoalLines', 'buildCrewLines', 'buildCrewNote']) {
  const source = extract(name);
  assert.ok(!source.includes('xpPerSecond'), name);
  assert.ok(!source.includes('skillBonus'), name);
  assert.ok(!source.includes('fv('), name);
  assert.ok(!source.includes('rankXP'), name);
  assert.ok(!/campBar|campMeter/.test(source), name);
}

assert.strictEqual(html.includes('function buildCrewNote'), true);
assert.strictEqual(html.includes('if(!n||!n.assigned)return null'), true);
assert.strictEqual(html.includes('let crewNote=buildCrewNote(e,f,p,m);crewNote&&g.append(crewNote);'), true);

assert.ok(html.includes('function x9(e,t,i,n,s){let r=B.camp.work;for(t.xp+=r.xpPerSecond*n;t.xp>=r.xpLevel*t.lvl;)t.xp-=r.xpLevel*t.lvl,t.lvl++,t.skills[i]+=r.skillPerLevel,Se(e,s,"settlerLevelUp",{id:t.id,lvl:t.lvl})}'));
assert.ok(html.includes('function fv(e){return["builder","engineer"].includes(e?.prof)&&Number.isSafeInteger(e.lvl)&&e.lvl>0?Math.min(Yu.length-1,e.lvl-1)*.04:0}'));
assert.ok(html.includes('m.project.remaining=Math.max(0,m.project.remaining-h*(1+fv(t)))'));
assert.ok(html.includes('buildingUpgraded",{id:c.target,lvl:m.lvl}),u({target:c.target}),d())):(f=!1,d())'));
assert.ok(html.includes('fieldCompanion={v:1'));
assert.ok(html.includes('function v$(e=B.camp.seed){let t={v:1,seed:e'));

console.log('build-settler-card: ok');
