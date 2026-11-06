"""Пилот карточки напарника: обзор, личное дело, ствол и броня без новой кнопки."""
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8091/play/')
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-companion-card'))
out.mkdir(parents=True, exist_ok=True)
KNOWN = {'recruit', 'follow', 'wait', 'return', 'map', 'giveGun', 'takeGun', 'arm', 'resupply', 'pickup', 'unload'}

with sync_playwright() as p:
    browser_path = os.environ.get('TERRA_CHROME') or next(path for path in ('/usr/bin/chromium', '/usr/bin/google-chrome') if os.path.exists(path))
    browser = p.chromium.launch(executable_path=browser_path, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 840, 'height': 390}, has_touch=True)
    page.set_default_timeout(90000)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    page.add_init_script("localStorage.setItem('terra_set', JSON.stringify({q:'med', post:false, dpr:1}))")
    page.goto(url, timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game.state==="play" && game.sewers && TERRA_KITS.ready && terraDefense.ready')
    page.evaluate('() => { game.loop = () => {}; }')
    page.evaluate('''() => {
      const h = game.homePos();
      game.p.x = h.x; game.p.z = h.z + 1.2; game.p.alive = true; game.p.level = 20; game.p.camp.rep = 1000;
      const hired = game.camp.recruit({id:'qa-companion', name:'Павел Ветров', prof:'gunsmith', pos:h});
      if (!hired.ok) throw new Error('recruit ' + JSON.stringify(hired));
      const s = game.p.camp.settlers['qa-companion'];
      s.pos = {x:h.x, z:h.z + 1};
      s.job = 'idle'; s.order = {}; s.work = 0; s.status = 'idle';
      s.lvl = 3; s.xp = 20;
      s.skills = {shoot:5, gather:1, build:1, craft:1, haul:1, scout:2, medic:1};
      s.mission = 'companion:qa-companion';
      s.wounded = false; s.injuredUntil = 0;
      s.gear = {weapon:{uid:7, wt:'shotgun', nm:'Двустволка', mag:2, g:0, r:0, e:0}, armor:{note:'vest'}};
      game.p.camp.fieldCompanion = {v:3, settlerId:'qa-companion', mode:'follow', home:{x:h.x, z:h.z}, departed:false, travelled:0, previous:{job:'idle', order:{}, work:0, status:'idle'}};
      game.p.weapons = [
        {uid:8, wt:'rifle', nm:'Автомат', mag:10, g:0, r:0, e:0, locked:false, fav:false},
        {uid:9, wt:'stick', nm:'Сухая', mag:0, g:0, r:0, e:0}
      ];
      game.ui.campPanel.open();
      game.ui.campPanel.select('overview');
    }''')
    card = page.locator('#campBody .fbHomeBoard > .campCompanion.ccPilot')
    expect(card).to_be_visible()
    page.wait_for_timeout(300)
    def snap():
        return page.evaluate('JSON.stringify({p:game.p, save:localStorage.getItem("terra_save")})')
    before = snap()
    assert page.locator('.fbOverviewDetails .campCompanion').count() == 0
    expect(card.locator('[data-companion-mode="follow"]')).to_have_text('За мной')
    expect(card.locator('.ccProf')).to_have_text('Оружейник')
    expect(card.locator('.ccShoot')).to_have_text('Стрельба 5')
    expect(card.locator('.ccMeter')).to_have_attribute('aria-valuemax', '180')
    expect(card.locator('.ccMeter')).to_have_attribute('aria-valuenow', '20')
    expect(card.locator('.companionFacts')).to_contain_text('Двустволка')
    expect(card.locator('.ccDefense')).to_contain_text('Защита героя')
    expect(card.locator('[data-companion-action="wait"]')).to_be_visible()
    expect(card.locator('[data-companion-action="return"]')).to_be_visible()
    expect(card.locator('[data-companion-action="follow"]')).to_have_count(0)
    expect(card.locator('[data-companion-action="takeGun"]')).to_have_count(1)
    summary = card.locator('.companionEquipment summary')
    def show(selector):
        page.evaluate('''(sel) => { const node = document.querySelector(sel); const body = document.getElementById('campBody'); const top = node.getBoundingClientRect().top - body.getBoundingClientRect().top + body.scrollTop; body.scrollTop = Math.max(0, top - 8); }''', selector)
    show('#campBody .fbHomeBoard > .ccPilot')
    page.screenshot(path=str(out / 'overview-face-840.png'), animations='disabled')
    card.screenshot(path=str(out / 'overview-card.png'), animations='disabled')
    summary.scroll_into_view_if_needed()
    summary.tap()
    expect(card.locator('.ccWeapon-carried')).to_contain_text('Двустволка')
    page.screenshot(path=str(out / 'overview-840.png'), animations='disabled')
    expect(card.locator('.ccWeaponList')).to_contain_text('Автомат')
    expect(card.locator('.ccWeaponList')).not_to_contain_text('Сухая')
    expect(summary).to_be_focused()
    summary.tap()
    expect(summary).to_be_focused()
    actions = page.evaluate('''() => [...document.querySelectorAll('#campBody .ccPilot [data-companion-action]')].map(b => b.dataset.companionAction)''')
    assert set(actions) <= KNOWN, actions
    labels = page.evaluate('''() => [...document.querySelectorAll('#campBody .ccPilot button')].map(b => b.textContent)''')
    assert not any('брон' in t.lower() or 'сража' in t.lower() for t in labels), labels
    assert 'газ блокир' not in card.inner_text().lower()
    sizes = page.evaluate('''() => [...document.querySelectorAll('#campBody .fbHomeBoard .ccPilot button, #campBody .fbHomeBoard .ccPilot summary')].filter(e => e.getClientRects().length).map(e => { const r = e.getBoundingClientRect(); return {t:e.textContent.slice(0,40), h:r.height, w:r.width}; })''')
    assert sizes and all(item['h'] >= 44 and item['w'] >= 44 for item in sizes), sizes
    assert snap() == before, 'Обзор изменил игрока или сейв'
    page.locator('[data-fieldbook-section="settlers"]').tap()
    page.locator('[data-resident="qa-companion"]').tap()
    dossier = page.locator('.campResidents.dossier .campCompanion.ccPilot')
    expect(dossier).to_be_visible()
    expect(page.locator('.fbCompanionFold')).to_have_count(0)
    expect(dossier.locator('[data-companion-mode="follow"]')).to_be_visible()
    expect(dossier.locator('.ccProf')).to_have_text('Оружейник')
    show('.campResidents.dossier > .ccPilot')
    page.screenshot(path=str(out / 'dossier-face-840.png'), animations='disabled')
    dossier.screenshot(path=str(out / 'dossier-card.png'), animations='disabled')
    dossier.locator('.companionEquipment summary').scroll_into_view_if_needed()
    dossier.locator('.companionEquipment summary').tap()
    expect(dossier.locator('[data-companion-action="takeGun"]')).to_be_visible()
    dossier_actions = page.evaluate('''() => [...document.querySelectorAll('.campResidents.dossier .ccPilot [data-companion-action]')].map(b => b.dataset.companionAction)''')
    assert set(dossier_actions) <= KNOWN, dossier_actions
    dossier_labels = page.evaluate('''() => [...document.querySelectorAll('.campResidents.dossier .ccPilot button')].map(b => b.textContent)''')
    assert not any('брон' in t.lower() or 'сража' in t.lower() for t in dossier_labels), dossier_labels
    page.screenshot(path=str(out / 'dossier-840.png'), animations='disabled')
    assert snap() == before, 'Личное дело изменило игрока или сейв'
    page.evaluate('''() => { game.p.x += 12; game.ui.campPanel.refresh?.(); }''')
    page.locator('[data-resident="qa-companion"]').tap()
    page.locator('.campResidents.dossier .companionEquipment summary').tap()
    far = page.locator('.campResidents.dossier .ccPilot [data-companion-action="takeGun"]')
    expect(far).to_be_visible()
    assert far.is_disabled()
    far.scroll_into_view_if_needed()
    far_box = far.bounding_box()
    assert far_box and far_box['height'] >= 44 and far_box['width'] >= 44, far_box
    expect(far).to_contain_text('Вернуть оружие')
    save_now = page.evaluate('localStorage.getItem("terra_save")')
    assert json.loads(before)['save'] == save_now
    page.screenshot(path=str(out / 'return-disabled-840.png'), animations='disabled')
    page.locator('.campResidents.dossier .ccPilot').screenshot(path=str(out / 'return-disabled-card.png'), animations='disabled')
    assert not errors, errors
    (out / 'report.json').write_text(json.dumps({'viewport':[840, 390], 'actions': actions, 'sizes': sizes, 'errors': errors}, ensure_ascii=False, indent=2))
    print('PASS companion card 840x390 overview/dossier/weapon list/no armor button/read-only save', flush=True)
    browser.close()
