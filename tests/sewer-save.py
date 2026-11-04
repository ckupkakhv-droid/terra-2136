"""Legacy sai save: storage keeps a katana marker, the live profile keeps sewer_sai."""
import os, shutil
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome'),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), timeout=90000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game.sewers && game._saiSaveInstalled')
    seeded = page.evaluate('''() => {
      const weapon = game.makeWeapon('katana', 0, 4, null);
      weapon.wt = 'sewer_sai';
      weapon.nm = '«Последний из клана»';
      const before = game.p.inv.bandage || 0;
      game.p.weapons.push(weapon);
      game.p.trace = 1;
      const saved = game.save();
      const raw = localStorage.getItem('terra_save');
      const stored = JSON.parse(raw).p.weapons.find(w => w.nm === weapon.nm);
      return {saved: saved?.status || null, ok: !!saved?.ok, live: weapon.wt, hold: weapon.hold || null,
        storedWt: stored?.wt || null, storedHold: stored?.hold || null, bandage: before,
        storedBandage: JSON.parse(raw).p.inv.bandage, trace: JSON.parse(raw).p.trace};
    }''')
    assert seeded['ok'] and seeded['live'] == 'sewer_sai' and seeded['hold'] is None, seeded
    assert seeded['storedWt'] == 'katana' and seeded['storedHold'] == 'sewer_sai', seeded
    assert seeded['storedBandage'] == seeded['bandage'] and seeded['trace'] == 1, seeded
    page.reload()
    page.locator('#mContinue').click()
    page.wait_for_function('game.state==="play" && game.p.weapons.some(w=>w.wt==="sewer_sai")')
    restored = page.evaluate('''() => {
      const weapon = game.p.weapons.find(w => w.nm === '«Последний из клана»');
      return {wt: weapon.wt, hold: weapon.hold || null, trace: game.p.trace, bandage: game.p.inv.bandage};
    }''')
    assert restored == {'wt': 'sewer_sai', 'hold': None, 'trace': 1, 'bandage': seeded['bandage']}, restored
    assert not errors, errors
    print('PASS: sai save is katana+hold on disk, sewer_sai after reload; trace and bandage kept; JS errors 0')
    browser.close()
