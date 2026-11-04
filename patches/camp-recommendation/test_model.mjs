import test from 'node:test';
import assert from 'node:assert/strict';
import { recommendResident } from './recommendation.mjs';
const task = { key: 'water', label: 'Вода' };
const camp = (...people) => ({ settlers: Object.fromEntries(people.map(p => [p.id, p])) });
const person = (id, score, extra = {}) => ({ id, name: id, score, ...extra });
const api = { reason: (_, p) => p.reason || '', efficiency: (_, p, skill) => p[skill] ?? p.score };
test('highest effective productivity wins, not highest raw skill/profession', () => {
  const c = camp(person('expert', 0.7), person('healthy', 1.2));
  assert.equal(recommendResident(c, task, api).candidate.id, 'healthy');
});
test('never considers people rejected by the native availability validator', () => {
  const excluded = ['companion', 'courier', 'mission', 'resting', 'injured', 'busy', 'carrying'];
  const c = camp(...excluded.map(id => person(id, 999, { reason: id })), person('free', 1));
  const result = recommendResident(c, task, api);
  assert.equal(result.candidate.id, 'free');
  assert.deepEqual(result.blocked.map(p => p.reason), excluded);
});
test('selection does not mutate any camp data', () => {
  const c = camp(person('b', 2), person('a', 2));
  const before = structuredClone(c);
  assert.equal(recommendResident(c, task, api).candidate.id, 'a');
  assert.deepEqual(c, before);
});
test('ties stay stable after serialization/reordered residents', () => {
  assert.equal(recommendResident(camp(person('b', 1), person('a', 1)), task, api).candidate.id, 'a');
  assert.equal(recommendResident(camp(person('a', 1), person('b', 1)), task, api).candidate.id, 'a');
});
test('construction uses build efficiency and preserves target in the explicit request', () => {
  const c = camp(person('builder', 0, { build: 2, gather: 1 }), person('gatherer', 0, { build: 1, gather: 2 }));
  const build = { key: 'build', target: 'workshop' };
  assert.deepEqual(recommendResident(c, build, api).candidate.request, { residentId: 'builder', task: 'build', target: 'workshop' });
  assert.equal(recommendResident(c, task, api).candidate.id, 'gatherer');
});
test('no assignment when the selected task is blocked or unknown', () => {
  assert.equal(recommendResident(camp(person('a', 2)), { key: 'build', reason: 'Нет свободной стройки' }, api).candidate, null);
  assert.equal(recommendResident(camp(person('a', 2)), { key: 'auto' }, api).candidate, null);
});
test('invalid effectiveness and dead residents fail closed', () => {
  const result = recommendResident(camp(person('dead', 900, { dead: true }), person('bad', NaN), person('negative', -1)), task, api);
  assert.equal(result.candidate, null);
  assert.equal(result.blocked.length, 2);
});
test('selection request cannot silently switch when the camp later changes', () => {
  const c = camp(person('a', 2), person('b', 1));
  const selected = recommendResident(c, task, api);
  c.settlers.b.score = 99;
  assert.equal(selected.candidate.request.residentId, 'a');
});

test('legacy/incomplete resident data cannot break the recommendation panel', () => {
  const result = recommendResident(camp(person('legacy', 1), person('valid', 2)), task, {
    ...api, efficiency: (_, person) => { if (person.id === 'legacy') throw new TypeError('Missing needs'); return person.score; }
  });
  assert.equal(result.candidate.id, 'valid');
  assert.equal(result.blocked.length, 1);
});
