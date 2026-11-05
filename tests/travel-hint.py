"""Travel onboarding in a live game on small portrait and landscape screens.

TERRA_TEST_URL defaults to http://127.0.0.1:8180/play/; use a disposable profile.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-travel-hint-qa'))
out.mkdir(parents=True, exist_ok=True)

with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'
    ])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text) if m.type == 'error' and 'favicon' not in m.text else None)
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/'), wait_until='domcontentloaded', timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game?.state === "play" && game.world.ents.some(e=>e.kind === "metro" && !e.sewer)', timeout=90000)
    entry = page.evaluate('game.world.ents.find(e=>e.kind === "metro" && !e.sewer)')
    page.evaluate('''e=>{game.p.x=e.x;game.p.z=e.z+2;game.p.hp=game.p.maxHp=10000;game.camT=null;game.enemies=[]}''', entry)
    page.wait_for_function('game.ui.tips.target("travel") !== null', timeout=90000)

    for width, height in [(320, 568), (360, 640), (390, 844), (844, 390), (640, 360)]:
        page.set_viewport_size({'width': width, 'height': height})
        # Preserve the native target selection and presentation while isolating
        # this hint from unrelated onboarding events in the disposable profile.
        page.evaluate('''()=>{const t=game.ui.tips;t.clear();t.player=game.p;
          for(const k of ['health','ammo','enemy','loot','build','anvil','craft','survivor','bag','night'])t.seen[k]=true;
          t.seen.travel=false;t.cooldown=0;t.tick();}''')
        page.wait_for_function('''()=>!document.getElementById('contextTips').classList.contains('hidden') &&
          document.getElementById('tipCard').dataset.tip === 'travel' ''', timeout=15000)
        result = page.evaluate('''()=>{const card=document.getElementById('tipCard'),r=card.getBoundingClientRect(),
          root=document.getElementById('contextTips').getBoundingClientRect(),ring=document.getElementById('tipRing'),
          map=document.getElementById('bMap').getBoundingClientRect();
          const visible=e=>{const s=getComputedStyle(e),b=e.getBoundingClientRect();return e.getClientRects().length && s.visibility!=='hidden' && s.display!=='none' && b.width>0 && b.height>0};
          const intersects=b=>r.left<b.right && r.right>b.left && r.top<b.bottom && r.bottom>b.top;
          const controls=[...document.querySelectorAll('#obj,#mm,#bCamp,#bMap,#bPause,#touch button')]
            .filter(visible).filter(e=>intersects(e.getBoundingClientRect())).map(e=>e.id);
          return {rect:{left:r.left,top:r.top,right:r.right,bottom:r.bottom,width:r.width,height:r.height},controls,
            targetError:Math.hypot(root.left+Number(ring.getAttribute('cx'))-(map.left+map.width/2),
                                   root.top+Number(ring.getAttribute('cy'))-(map.top+map.height/2)),
            label:card.getAttribute('aria-label')};}''')
        rect = result['rect']
        assert not result['controls'], (width, height, result)
        assert rect['left'] >= 0 and rect['right'] <= width and rect['top'] >= 0 and rect['bottom'] <= height, (width, height, result)
        assert rect['height'] >= 48 and result['targetError'] < 2 and 'закрыть подсказку' in result['label'], (width, height, result)
        page.screenshot(path=str(out / f'travel-{width}x{height}.png'))
        print('PASS layout', width, height, flush=True)

    # Dismiss with real touch and then use the map control; the hint must not
    # reopen in the same onboarding state or prevent the map from opening.
    card = page.locator('#tipCard').bounding_box()
    page.touchscreen.tap(card['x'] + card['width']/2, card['y'] + card['height']/2)
    page.wait_for_function("document.getElementById('contextTips').classList.contains('hidden')")
    assert page.evaluate('game.ui.tips.seen.travel === true')
    page.wait_for_timeout(500)
    assert page.locator('#contextTips').evaluate("e=>e.classList.contains('hidden')")
    map_button = page.locator('#bMap').bounding_box()
    page.touchscreen.tap(map_button['x'] + map_button['width']/2, map_button['y'] + map_button['height']/2)
    page.wait_for_function("!document.getElementById('wmap').classList.contains('hidden')")
    assert not errors, errors
    print('PASS touch dismissal, map access and JS/console 0', flush=True)
    browser.close()
