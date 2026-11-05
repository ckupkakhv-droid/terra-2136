"""Check a real station prompt against touch HUD and enter it on a small screen."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-dungeon-prompt-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'
    ])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' and 'favicon' not in msg.text else None)
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/'), wait_until='domcontentloaded', timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game?.state === "play" && game.world.ents.some(e=>e.kind === "metro" && !e.sewer)', timeout=90000)
    entry = page.evaluate('game.world.ents.find(e=>e.kind === "metro" && !e.sewer)')
    page.evaluate('''e=>{game.p.x=e.x;game.p.z=e.z+2;game.p.hp=game.p.maxHp=10000;game.camT=null;game.enemies=[]}''', entry)
    page.wait_for_function('''()=>{const p=document.getElementById('prompt');return p.classList.contains('dungeon-entry') && getComputedStyle(p).display!=='none'}''', timeout=90000)
    for width, height in [(320, 568), (360, 640), (390, 844), (844, 390), (640, 360), (568, 320), (480, 320)]:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(350)
        result = page.evaluate('''()=>{const p=document.getElementById('prompt'),r=p.getBoundingClientRect();
          const visible=e=>{const s=getComputedStyle(e),b=e.getBoundingClientRect();return e.getClientRects().length && s.visibility!=='hidden' && s.display!=='none' && b.width>0 && b.height>0};
          const intersects=b=>Math.min(r.right,b.right)-Math.max(r.left,b.left)>1 && Math.min(r.bottom,b.bottom)-Math.max(r.top,b.top)>1;
          const controls=[...document.querySelectorAll('#obj,#mm,#bCamp,#bMap,#bPause,#weap,#tipCard,#touch button')].filter(visible).filter(e=>intersects(e.getBoundingClientRect())).map(e=>e.id);
          return {rect:{left:r.left,top:r.top,right:r.right,bottom:r.bottom},controls,
            action:p.querySelector('.dungeon-entry-action')?.textContent,details:[...p.querySelectorAll('.dungeon-entry-detail,.dungeon-entry-caution')].map(e=>({text:e.textContent,visible:visible(e)}))};}''')
        assert not result['controls'], (width, height, result)
        r = result['rect']
        assert r['left'] >= 0 and r['right'] <= width and r['top'] >= 0 and r['bottom'] <= height, (width, height, result)
        assert result['action'] and result['details'] and all(x['text'] and x['visible'] for x in result['details']), (width, height, result)
        page.screenshot(path=str(out / f'prompt-{width}x{height}.png'))
        print('PASS prompt', width, height, flush=True)
    page.set_viewport_size({'width': 640, 'height': 360})
    page.wait_for_timeout(300)
    button = page.locator('#tInteract').bounding_box()
    page.touchscreen.tap(button['x'] + button['width']/2, button['y'] + button['height']/2)
    page.wait_for_function('game.world.inDungeon && !game.dungeonTransition', timeout=90000)
    assert not errors, errors
    print('PASS touch entry and JS/console 0', flush=True)
    browser.close()
