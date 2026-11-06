"""Выбор ствола напарника на телефоне.

Один профиль Chromium 390×844. Кнопка карточки — штатный обработчик giveGun/takeGun.
Сервер из корня репозитория, TERRA_TEST_URL или http://127.0.0.1:8080/play/.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-companion-gun'))
out.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')

SETUP = r"""() => {
  const id = 'qa-gun';
  const camp = game.p.camp;
  camp.rep = 1000;
  if (!game.camp.recruit({id}).ok) throw new Error('resident');
  const resident = camp.settlers[id];
  resident.name = 'Павел Стволов';
  resident.needs.rest = 80;
  resident.job = 'idle';
  resident.order = {};
  resident.work = 0;
  const origin = game.homePos?.() || {x: game.p.x, z: game.p.z};
  game.p.x = origin.x;
  game.p.z = origin.z;
  resident.pos = {x: origin.x, z: origin.z};
  resident.mission = 'companion:' + id;
  resident.status = 'idle';
  delete resident.facility;
  delete resident.workBlock;
  camp.fieldCompanion = {v:1, settlerId:id, mode:'follow', home:{x:origin.x, z:origin.z}, previous:{job:'idle', order:{}, work:0, status:'idle'}, departed:false, travelled:0};
  const gun = (uid, wt, nm, extra = {}) => ({uid, wt, nm, mag: 1, g: 0, r: 0, e: 0, ...extra});
  game.p.weapons.push(
    gun(9001, 'rifle', 'Автомат испытателя'),
    gun(9002, 'shotgun', 'Двустволка испытателя'),
    gun(9003, 'revolver', 'Запертый револьвер', {locked: true}),
  );
  return {v: camp.fieldCompanion.v, weapons: game.p.weapons.map(item => item.uid)};
}"""

SNAP = r"""() => {
  const resident = game.p.camp.settlers['qa-gun'];
  const carried = resident.gear.weapon;
  const pack = game.p.weapons.map(item => item.uid);
  const pile = [...pack, carried?.uid].filter(uid => uid != null).sort((a, b) => a - b);
  return {
    pile, pack, carried: carried?.uid || null,
    armor: resident.gear.armor,
    campV: game.p.camp.v,
    fcKeys: Object.keys(game.p.camp.fieldCompanion).sort(),
    gearKeys: Object.keys(resident.gear).sort(),
    pKeys: Object.keys(game.p).sort(),
    campKeys: Object.keys(game.p.camp).sort(),
    weaponKeys: (carried ? [carried] : game.p.weapons).filter(item => item.uid === 9002 || item.uid === 9001).map(item => Object.keys(item).sort().join(',')),
  };
}"""

def reveal(page, selector):
    details = page.locator(selector)
    if details.count() and not details.first.evaluate('node => node.open'):
        details.first.locator(':scope > summary').tap()

def open_guns(page):
    reveal(page, '.fbCompanionFold')
    if page.locator('.campCompanion [data-weapon-uid="9002"]').count() == 0:
        reveal(page, '.fbOverviewDetails')
    expect(page.locator('.campCompanion .companionEquipment > summary').first).to_be_visible()
    reveal(page, '.campCompanion .companionEquipment')

with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=1)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: message.type == 'error' and errors.append(message.text))
    page.goto(URL, wait_until='load', timeout=90000)
    page.locator('#mNew').tap()
    page.locator('#skip').tap()
    expect(page.locator('#hud')).to_be_visible()
    prepared = page.evaluate(SETUP)
    assert prepared['v'] == 1, prepared

    page.locator('#bCamp').tap()
    page.wait_for_function('() => !!window.terraCompanionGuns && !!document.querySelector("[data-fieldbook-section=settlers]")')
    page.locator('[data-fieldbook-section="settlers"]').tap()
    page.locator('[data-resident="qa-gun"]').tap()
    open_guns(page)
    expect(page.locator('.campCompanion [data-weapon-uid="9002"]')).to_be_visible()
    before = page.evaluate(SNAP)
    page.wait_for_timeout(200)
    assert page.evaluate(SNAP) == before, 'Просмотр списка стволов изменил сейв'
    rows = page.evaluate('() => terraCompanionGuns.rows()')
    by_uid = {row['uid']: row for row in rows}
    assert by_uid[9001]['action'] == 'giveGun' and not by_uid[9001]['disabled']
    assert by_uid[9002]['action'] == 'giveGun' and not by_uid[9002]['disabled']
    assert 9003 not in by_uid
    assert page.locator('.campCompanion [data-companion-action="giveArmor"], .campCompanion [data-weapon-uid="9003"]').count() == 0

    geometry = page.evaluate(r"""() => {
      const body = document.getElementById('campBody');
      const small = [];
      for (const button of document.querySelectorAll('.campCompanion .companionEquipment button, .campCompanion .companionEquipment summary')) {
        const box = button.getBoundingClientRect();
        if (box.width < 44 || box.height < 44) small.push((button.getAttribute('data-weapon-uid') || button.textContent || '').trim().slice(0, 40) + ' ' + Math.round(box.width) + 'x' + Math.round(box.height));
      }
      return {small, overflow: body.scrollWidth > body.clientWidth + 1};
    }""")
    assert not geometry['small'], geometry
    assert not geometry['overflow'], geometry
    page.screenshot(path=str(out / 'guns-390.png'))

    chosen = page.locator('.campCompanion [data-weapon-uid="9002"]')
    chosen.scroll_into_view_if_needed()
    chosen.focus()
    page.keyboard.press('Enter')
    page.wait_for_function("() => game.p.camp.settlers['qa-gun'].gear.weapon?.uid === 9002")
    given = page.evaluate(SNAP)
    assert given['pile'] == before['pile']
    assert given['carried'] == 9002
    assert 9002 not in given['pack'] and 9001 in given['pack'] and 9003 in given['pack']
    assert given['pack'].count(9002) == 0
    assert given['armor'] is None
    assert given['campV'] == before['campV']
    assert given['fcKeys'] == before['fcKeys']
    assert given['gearKeys'] == before['gearKeys']
    assert given['pKeys'] == before['pKeys']
    added = set(given['campKeys']) - set(before['campKeys'])
    assert added <= {'warehouseDeliveries'}, added
    assert 'uid' not in given['fcKeys']
    assert 'uid' in given['weaponKeys'][0]
    open_guns(page)
    page.screenshot(path=str(out / 'returned-ready-390.png'))

    page.wait_for_timeout(450)
    open_guns(page)
    returned = page.locator('.campCompanion [data-companion-action="takeGun"]')
    expect(returned).to_be_visible()
    assert returned.get_attribute('data-weapon-uid') == '9002'
    returned.tap()
    page.wait_for_function("() => !game.p.camp.settlers['qa-gun'].gear.weapon && game.p.weapons.some(item => item.uid === 9002)")
    back = page.evaluate(SNAP)
    assert back['pile'] == before['pile']
    assert back['carried'] is None
    assert back['pack'].count(9002) == 1

    page.evaluate("() => { game.p.x += 10; game.ui.campPanel.refresh(); }")
    page.wait_for_timeout(100)
    open_guns(page)
    far = page.locator('.campCompanion [data-weapon-uid="9002"]')
    expect(far).to_be_disabled()
    assert '3' in (far.get_attribute('title') or '')
    stayed = page.evaluate(SNAP)
    assert stayed['pile'] == before['pile']
    assert stayed['carried'] is None
    assert not errors, errors
    print('PASS selected gun, return, distance, schema; JS0', flush=True)
    browser.close()
