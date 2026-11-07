"""Цикл напарника: подбор дропа, сундук лагеря, выдача, выстрел, возврат.

Функциональный прогон жмёт мышью. Касание bCamp → житель → выдать/вернуть
проверяет отдельно tests/companion-armory-touch.py. Click здесь не считается touch.
Стволы 9101/9102/9103 и дроп crate:4,5:6,7 — тестовые.
"""
from pathlib import Path
import json
import os
import shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/opt/cursor/artifacts'))
out.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
report = {}

SETUP = r"""() => {
  const id = 'qa-mate';
  const camp = game.p.camp;
  camp.rep = 1000;
  if (!game.camp.recruit({id}).ok) throw new Error('resident');
  const resident = camp.settlers[id];
  resident.name = 'Марфа Испытатель';
  resident.needs.rest = 80;
  resident.job = 'idle';
  resident.order = {};
  resident.work = 0;
  resident.skills = resident.skills || {};
  resident.skills.shoot = 40;
  resident.wounded = false;
  resident.injuredUntil = 0;
  const origin = game.homePos();
  game.p.x = origin.x;
  game.p.z = origin.z;
  game.p.alive = true;
  resident.pos = {x: origin.x + 0.4, z: origin.z};
  resident.mission = 'companion:' + id;
  resident.status = 'idle';
  delete resident.facility;
  delete resident.workBlock;
  camp.fieldCompanion = {
    v: 1, settlerId: id, mode: 'follow', home: {x: origin.x, z: origin.z},
    previous: {job: 'idle', order: {}, work: 0, status: 'idle'},
    departed: false, travelled: 0
  };
  const gun = (uid, wt, nm, mag, extra) => ({uid, wt, nm, mag, g: 1, r: 2, e: 3, aff: [{id: 'qa-mark', v: 2}], ...extra});
  const issued = gun(9101, 'rifle', 'Ствол испытания', 4);
  const empty = gun(9103, 'revolver', 'Пустой испытательный', 0);
  const pack = gun(9102, 'shotgun', 'Рюкзак испытания', 2, {g: 0, r: 0, e: 0, aff: [{id: 'qa-pack', v: 1}]});
  game.p.weapons.push(pack);
  if (!Array.isArray(game.p.eq)) game.p.eq = [];
  game.p.eq.push(pack);
  const home = origin;
  if (!Array.isArray(game.p.base)) game.p.base = [];
  game.p.base.push({t: 'chest', x: home.x + 1, z: home.z, r: 0, items: [{weapon: issued}, {weapon: empty}]});
  const hero = (game.p.eq || []).map(item => item && item.uid).filter(uid => uid != null);
  return {hero, home, fc: camp.fieldCompanion.v};
}"""

CENSUS = r"""() => {
  const take = item => item ? {uid: item.uid, wt: item.wt, nm: item.nm, mag: item.mag, g: item.g, r: item.r, e: item.e, aff: item.aff} : null;
  const places = [];
  const add = (where, item) => { if (item && item.uid != null) places.push({where, ...take(item)}); };
  for (const item of game.p.weapons || []) add('pack', item);
  for (const item of game.p.eq || []) add('eq', item);
  for (const resident of Object.values(game.p.camp.settlers || {})) add('settler:' + resident.id, resident.gear && resident.gear.weapon);
  for (const box of game.p.base || []) if (box && box.t === 'chest') for (const row of box.items || []) add('chest', row && row.weapon);
  const mate = game.p.camp.settlers['qa-mate'];
  const raw = localStorage.getItem('terra_save');
  let save = null;
  try { save = raw ? JSON.parse(raw) : null; } catch (e) { save = {parse: false}; }
  return {
    places,
    cargo: game.p.camp.fieldCompanion && game.p.camp.fieldCompanion.cargo || null,
    fc: game.p.camp.fieldCompanion ? {v: game.p.camp.fieldCompanion.v, mode: game.p.camp.fieldCompanion.mode, keys: Object.keys(game.p.camp.fieldCompanion).sort()} : null,
    campV: game.p.camp.v,
    saveV: save && save.v,
    saveKeys: save ? Object.keys(save).sort() : [],
    gearKeys: mate && mate.gear ? Object.keys(mate.gear).sort() : [],
    wood: (game.p.camp.res && game.p.camp.res.wood) || 0,
    hero: (game.p.eq || []).map(item => item && item.uid).filter(uid => uid != null),
  };
}"""

DROP = r"""() => {
  const resident = game.p.camp.settlers['qa-mate'];
  const wid = 'crate:4,5:6,7';
  const row = {id: 'wood', n: 1};
  const x = resident.pos.x + 0.4;
  const z = resident.pos.z;
  if (!game.world.broken || !game.world.pend) return {ok: false, reason: 'pend'};
  game.world.broken.add(wid);
  game.world.pend.set(wid, [row]);
  game.pickups.push({x, z, id: 'wood', n: 1, t: 1e9, ph: 0, wid, row, state: 'rest'});
  const sight = game.world.segHit(resident.pos.x, resident.pos.z, x, z, 0.6);
  return {ok: true, sight, pickups: game.pickups.filter(item => item.wid === wid).length};
}"""


def of(uid, snap):
    return [row for row in snap['places'] if row['uid'] == uid]


def boot(page):
    page.goto(URL, wait_until='load', timeout=90000)
    page.wait_for_function(
        """() => {
          const boot = document.getElementById('terraBoot');
          const btn = document.getElementById('mNew');
          const covered = boot && boot.getBoundingClientRect().height > 40 && getComputedStyle(boot).display !== 'none' && getComputedStyle(boot).visibility !== 'hidden';
          return !!btn && btn.textContent.includes('НОВ') && !covered;
        }"""
    )
    page.locator('#mNew').tap()
    page.locator('#skip').tap()
    expect(page.locator('#hud')).to_be_visible()
    page.wait_for_function('() => window.terraArmory && game.camp && game.homePos')


def reveal(page):
    for selector in ('.fbCompanionFold', '.fbOverviewDetails', '.campCompanion .companionEquipment'):
        details = page.locator(selector)
        if details.count() and not details.first.evaluate('node => node.open'):
            details.first.locator(':scope > summary').click()


with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('google-chrome') or shutil.which('chromium')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=1)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append('page:' + str(error)))
    page.on('console', lambda message: message.type == 'error' and errors.append('console:' + message.text))
    boot(page)
    prepared = page.evaluate(SETUP)
    before = page.evaluate(CENSUS)
    report['before'] = before
    assert prepared['hero'] == before['hero']
    assert len(of(9101, before)) == 1 and of(9101, before)[0]['where'] == 'chest'
    assert of(9101, before)[0]['aff'] == [{'id': 'qa-mark', 'v': 2}]
    assert of(9102, before)[0]['where'] == 'pack'
    assert before['campV'] == 1 and before['fc']['v'] == 1

    wood_before = before['wood']
    dropped = page.evaluate(DROP)
    assert dropped['ok'] and dropped['sight'] < 0, dropped
    page.locator('#bCamp').click()
    page.wait_for_function("() => !!document.querySelector('[data-fieldbook-section=settlers]')")
    page.locator('[data-fieldbook-section="settlers"]').click()
    page.locator('[data-resident="qa-mate"]').click()
    reveal(page)
    pickup = page.locator('.campCompanion [data-companion-action="pickup"]')
    expect(pickup).to_be_enabled()
    pickup.click()
    page.wait_for_function("() => game.p.camp.fieldCompanion && game.p.camp.fieldCompanion.cargo && game.p.camp.fieldCompanion.cargo.res === 'wood'")
    held_drop = page.evaluate(CENSUS)
    assert held_drop['cargo'] == {'res': 'wood', 'amount': 1}, held_drop['cargo']
    assert held_drop['fc']['v'] == 2
    again = page.evaluate("() => game.camp.commandCompanion({action:'pickup'})")
    assert not again.get('ok'), again
    assert page.evaluate("() => !game.world.pend.get('crate:4,5:6,7') && !game.pickups.some(item => item.wid === 'crate:4,5:6,7')")
    unloaded = page.evaluate("() => game.camp.commandCompanion({action:'unload'})")
    assert unloaded.get('ok'), unloaded
    stored = page.evaluate(CENSUS)
    assert stored['cargo'] is None
    assert stored['wood'] == wood_before + 1, stored['wood']
    assert stored['fc']['keys'] == before['fc']['keys']

    page.evaluate("() => game.ui.campPanel.refresh()")
    reveal(page)
    button = page.locator('.campCompanion .ccArmory button')
    expect(button).to_be_visible()
    assert button.inner_text() == 'Выдать из сундука'
    page.screenshot(path=str(out / 'armory-390.png'))
    geometry = page.evaluate("""() => {
      const body = document.getElementById('campBody');
      const button = document.querySelector('.campCompanion .ccArmory button');
      const box = button.getBoundingClientRect();
      return {w: Math.round(box.width), h: Math.round(box.height), overflow: body.scrollWidth > body.clientWidth + 1};
    }""")
    assert geometry['h'] >= 44 and geometry['w'] >= 44 and not geometry['overflow'], geometry
    button.click()
    page.wait_for_function("() => game.p.camp.settlers['qa-mate'].gear.weapon && game.p.camp.settlers['qa-mate'].gear.weapon.uid === 9101")
    issued = page.evaluate(CENSUS)
    assert issued['fc']['v'] == 3
    assert of(9101, issued)[0]['where'] == 'settler:qa-mate'
    assert of(9101, issued)[0]['mag'] == 4
    assert of(9101, issued)[0]['aff'] == [{'id': 'qa-mark', 'v': 2}]
    assert of(9101, issued)[0]['g'] == 1 and of(9101, issued)[0]['r'] == 2 and of(9101, issued)[0]['e'] == 3
    assert len(of(9101, issued)) == 1
    assert of(9103, issued)[0]['where'] == 'chest' and of(9103, issued)[0]['mag'] == 0
    assert of(9102, issued)[0]['where'] == 'pack'
    assert issued['hero'] == before['hero']
    second = page.evaluate("() => terraArmory.issue('qa-mate', 9103)")
    assert not second.get('ok'), second
    assert page.evaluate(CENSUS)['places'] == issued['places']

    shot = page.evaluate(r"""() => {
      const resident = game.p.camp.settlers['qa-mate'];
      const origin = resident.pos;
      const dirs = [[1, 0], [-1, 0], [0, 1], [0, -1], [0.8, 0.6]];
      let point = null;
      for (const [dx, dz] of dirs) {
        const x = origin.x + dx, z = origin.z + dz;
        if (game.world.segHit(origin.x, origin.z, x, z, 0.4) < 0) { point = {x, z}; break; }
      }
      if (!point) return {ok: false, reason: 'sight'};
      game.p.x = origin.x;
      game.p.z = origin.z;
      const enemy = game.spawnEnemy('zombie', point.x, point.z, {force: 1, aggro: 1});
      if (!enemy) return {ok: false, reason: 'spawn'};
      enemy.spd = 0;
      enemy.dmg = 0;
      enemy.aggro = true;
      enemy.pineBlocked = false;
      const hp = enemy.hp;
      const mag = resident.gear.weapon.mag;
      const uid = resident.gear.weapon.uid;
      game.guardsUpdate(0.3);
      const bullet = game.bullets[0] ? {dmg: game.bullets[0].dmg, wt: game.bullets[0].wt, src: game.bullets[0].companionSource || null} : null;
      game.combatUpdate(0.08);
      return {
        ok: true, uid, magBefore: mag, magAfter: resident.gear.weapon.mag,
        hpBefore: hp, hpAfter: enemy.hp, dead: !!enemy.dead, bullet,
        sight: game.world.segHit(origin.x, origin.z, point.x, point.z, 0.4),
      };
    }""")
    assert shot.get('ok'), shot
    assert shot['uid'] == 9101
    assert shot['magAfter'] == shot['magBefore'] - 1, shot
    assert shot['hpAfter'] < shot['hpBefore'], shot
    assert shot['bullet'] and shot['bullet']['dmg'] > 0, shot
    spent = page.evaluate(CENSUS)
    assert of(9101, spent)[0]['mag'] == 3
    assert of(9101, spent)[0]['aff'] == [{'id': 'qa-mark', 'v': 2}]
    assert len(of(9101, spent)) == 1

    page.evaluate('() => game.save()')
    saved = page.evaluate(CENSUS)
    assert saved['saveV'] == 7, saved['saveV']
    page.reload(wait_until='load')
    page.wait_for_function("() => document.getElementById('mContinue') && document.getElementById('mContinue').textContent.includes('ПРОД')")
    page.locator('#mContinue').click()
    expect(page.locator('#hud')).to_be_visible()
    page.wait_for_function("() => window.terraArmory && game.p && game.p.camp && game.p.camp.settlers['qa-mate']")
    loaded = page.evaluate(CENSUS)
    assert of(9101, loaded) == of(9101, spent), loaded
    assert loaded['hero'] == before['hero']
    assert loaded['campV'] == 1
    assert loaded['fc']['v'] == 3
    assert 'stock' not in loaded['fc']['keys']

    page.locator('#bCamp').click()
    page.locator('[data-fieldbook-section="settlers"]').click()
    page.locator('[data-resident="qa-mate"]').click()
    reveal(page)
    page.set_viewport_size({'width': 320, 'height': 568})
    back = page.locator('.campCompanion .ccArmory button')
    expect(back).to_have_text('Сдать в сундук')
    narrow = page.evaluate("""() => {
      const body = document.getElementById('campBody');
      const button = document.querySelector('.campCompanion .ccArmory button');
      const box = button.getBoundingClientRect();
      return {w: Math.round(box.width), h: Math.round(box.height), overflow: body.scrollWidth > body.clientWidth + 1};
    }""")
    assert narrow['h'] >= 44 and narrow['w'] >= 44 and not narrow['overflow'], narrow
    page.screenshot(path=str(out / 'armory-320.png'))
    back.click()
    page.wait_for_function("() => !game.p.camp.settlers['qa-mate'].gear.weapon")
    returned = page.evaluate(CENSUS)
    assert of(9101, returned)[0]['where'] == 'chest'
    assert of(9101, returned)[0]['mag'] == 3
    assert of(9101, returned)[0]['aff'] == [{'id': 'qa-mark', 'v': 2}]
    assert len(of(9101, returned)) == 1
    repeat = page.evaluate("() => terraArmory.recall('qa-mate')")
    assert not repeat.get('ok'), repeat
    assert page.evaluate(CENSUS)['places'] == returned['places']

    page.evaluate("() => terraArmory.issue('qa-mate', 9101)")
    finished = page.evaluate("""() => {
      const back = game.camp.commandCompanion({action: 'return'});
      const done = game.camp.commandCompanion({action: 'finish'});
      const item = (game.p.base || []).flatMap(box => (box && box.t === 'chest' && box.items) || []).find(row => row.weapon && row.weapon.uid === 9101);
      return {back, done, gear: game.p.camp.settlers['qa-mate'].gear.weapon, chestMag: item && item.weapon.mag, fc: game.p.camp.fieldCompanion || null};
    }""")
    assert finished['done'].get('ok'), finished
    assert finished['done'].get('stock', {}).get('uid') == 9101, finished
    assert finished['gear'] is None
    assert finished['chestMag'] == 3
    assert finished['fc'] is None
    parked = page.evaluate(CENSUS)
    assert len(of(9101, parked)) == 1 and of(9101, parked)[0]['where'] == 'chest'

    scout = page.evaluate(r"""() => {
      const id = 'qa-scout';
      if (!game.camp.recruit({id}).ok) return {ok: false, reason: 'recruit'};
      const resident = game.p.camp.settlers[id];
      const origin = game.homePos();
      resident.pos = {x: origin.x, z: origin.z};
      resident.job = 'scout';
      resident.order = {};
      resident.mission = undefined;
      delete resident.mission;
      const denied = terraArmory.issue(id);
      resident.job = 'guard';
      resident.order = {};
      const noPost = terraArmory.issue(id);
      resident.job = 'guard';
      resident.order = {postId: 'camp:watch'};
      const given = terraArmory.issue(id, 9101);
      const changed = game.camp.assignResidentTask({residentId: id, task: 'auto'});
      const after = game.p.camp.settlers[id];
      const chest = (game.p.base || []).some(box => box && box.t === 'chest' && (box.items || []).some(row => row.weapon && row.weapon.uid === 9101));
      return {ok: true, denied, noPost, given, changed, job: after.job, gear: after.gear.weapon, chest};
    }""")
    assert scout.get('ok'), scout
    assert not scout['denied']['ok'], scout['denied']
    assert not scout['noPost']['ok'] and 'посту' in scout['noPost']['reason'], scout['noPost']
    assert scout['given']['ok'] and scout['given']['uid'] == 9101, scout['given']
    assert scout['changed'].get('ok'), scout['changed']
    assert scout['gear'] is None and scout['chest'], scout
    role_snap = page.evaluate(CENSUS)
    assert len(of(9101, role_snap)) == 1 and of(9101, role_snap)[0]['where'] == 'chest'
    assert of(9101, role_snap)[0]['mag'] == 3 and of(9101, role_snap)[0]['e'] == 3

    death = page.evaluate(r"""() => {
      const resident = game.p.camp.settlers['qa-scout'];
      resident.job = 'scout';
      resident.order = {};
      const given = terraArmory.issue('qa-scout', 9101);
      resident.dead = true;
      const blocked = terraArmory.issue('qa-scout', 9103);
      const still = resident.gear.weapon && resident.gear.weapon.uid;
      const back = terraArmory.recall('qa-scout');
      const owners = terraArmory.owners(9101);
      return {given, blocked, still, back, owners};
    }""")
    assert death['given']['ok'], death
    assert not death['blocked']['ok'], death
    assert death['still'] == 9101
    assert death['back']['ok'] and death['owners'] == ['chest'], death
    final = page.evaluate(CENSUS)
    assert len(of(9101, final)) == 1
    assert of(9101, final)[0]['aff'] == [{'id': 'qa-mark', 'v': 2}]
    assert of(9101, final)[0]['mag'] == 3
    assert of(9102, final)[0]['where'] == 'pack'
    assert final['hero'] == before['hero']
    assert final['campV'] == 1 and final['saveV'] in (None, 7)

    page.set_viewport_size({'width': 1280, 'height': 800})
    page.evaluate("() => game.ui.campPanel.refresh()")
    page.screenshot(path=str(out / 'armory-desktop.png'))
    report.update({
        'fixture': 'synthetic uids 9101, 9102, 9103 and drop crate:4,5:6,7',
        'before': {'wood': wood_before, 'gun9101': of(9101, before), 'hero': before['hero']},
        'pickup': {'cargo': held_drop['cargo'], 'woodAfter': stored['wood'], 'second': again.get('reason')},
        'issued': of(9101, issued),
        'shot': shot,
        'afterSave': of(9101, loaded),
        'returned': of(9101, returned),
        'finish': {'stock': finished['done'].get('stock'), 'gear': finished['gear']},
        'scout': {'denied': scout['denied'].get('reason'), 'noPost': scout['noPost'].get('reason'), 'job': scout['job']},
        'death': {'owners': death['owners'], 'stillBeforeRecall': death['still']},
        'final': {'gun9101': of(9101, final), 'pack9102': of(9102, final), 'hero': final['hero'], 'campV': final['campV'], 'saveV': final['saveV']},
        'pageErrors': errors,
    })
    (out / 'companion-armory.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert not errors, errors
    browser.close()
    print('PASS armory cycle', flush=True)
