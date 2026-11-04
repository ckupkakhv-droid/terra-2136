"""Дымовая проверка вынесенного архива: загрузка, мир, лагерь, звук, сейв.

Сервер: python3 -m http.server 8080 из корня репозитория.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-assets-qa'))
out.mkdir(parents=True, exist_ok=True)
url = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
if not chromium:
    raise SystemExit('Нет Chromium/Chrome')

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=chromium,
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--no-sandbox'],
    )
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' and 'favicon' not in message.location.get('url', '') else None)
    page.goto(url, wait_until='load', timeout=120000)
    page.wait_for_function('window.game && document.getElementById("terraBoot") === null', timeout=120000)
    page.screenshot(path=str(out / 'menu.png'))
    state = page.evaluate('''() => ({
      audio: Object.keys(window.TERRA_AUDIO || {}).length,
      hero: typeof (window.TERRA_ASSETS || {}).hero,
      tex: !!window.TERRA_TEX,
      kit: !!window.TERRA_KIT,
      enemies: !!window.TERRA_EVENT_ENEMIES?.assets?.c_siren_event,
      parasite: window.TERRA_CREATURE_PARASITE?.sha256?.slice(0, 12) || '',
      credits: typeof window.TERRA_CREDITS === 'string' && window.TERRA_CREDITS.length > 100,
    })''')
    assert state['audio'] > 300, state
    assert state['hero'] == 'string' and state['tex'] and state['kit'] and state['enemies'] and state['credits'], state
    assert state['parasite'].startswith('cd7fa336b1b7'), state
    dupes = page.evaluate('''() => {
      const names = performance.getEntriesByType('resource').map(e => e.name);
      const packs = names.filter(n => n.includes('/assets/pack/'));
      const counts = {};
      for (const n of packs) counts[n] = (counts[n] || 0) + 1;
      return Object.entries(counts).filter(([, c]) => c > 1);
    }''')
    assert not dupes, dupes
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game.state === "play" && game.glb && game.glb.hero')
    # A short effect may decode before long music/ambience. Wait for the actual
    # assertion, rather than treating the first buffer plus 600 ms as readiness.
    page.wait_for_function('game.sfx && game.sfx.buf && Object.keys(game.sfx.buf).some(k => k[0] === "m" || k[0] === "a")', timeout=30000)
    page.wait_for_timeout(600)
    page.screenshot(path=str(out / 'world.png'))
    audible = page.evaluate('Object.keys(game.sfx.buf).filter(k => k[0] === "m" || k[0] === "a").length')
    assert audible > 0, audible
    page.locator('#bCamp').click()
    page.wait_for_selector('#campPanel, #campBody, .campSection', timeout=15000)
    page.screenshot(path=str(out / 'camp.png'))
    page.keyboard.press('Escape')
    page.wait_for_function('game.state === "play"')
    saved = page.evaluate('(() => { const r = game.save(); return !!(r && r.ok !== false); })()')
    assert saved, 'save failed'
    raw = page.evaluate("localStorage.getItem('terra_save')")
    assert raw and '"p"' in raw
    page.reload(wait_until='load', timeout=120000)
    page.locator('#mContinue').click()
    page.wait_for_function('game.state === "play" && game.p && game.p.hp > 0')
    page.screenshot(path=str(out / 'continue.png'))
    # Канализация и лаборатория остаются отдельными файлами и открываются по относительному пути.
    sewer = page.evaluate('''async () => {
      const lab = await fetch('assets/sewer/lab/lab_kit.glb');
      const mutant = await fetch('assets/sewer/mutant.glb');
      return {lab: lab.status, labBytes: Number(lab.headers.get('content-length')), mutant: mutant.status};
    }''')
    assert sewer['lab'] == 200 and sewer['labBytes'] > 1000 and sewer['mutant'] == 200, sewer
    assert not errors, errors
    print('PASS assets pack', state, 'sfx', audible, 'sewer', sewer)
    browser.close()
