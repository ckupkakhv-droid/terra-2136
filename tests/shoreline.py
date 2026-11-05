"""Run on served game: TERRA_TEST_URL=http://127.0.0.1:8180/play/ python3 tests/shoreline.py.
Compares terrain/water/collision/RNG output with the v0.4.6 baseline, then renders
an actual riverbank at desktop and phone viewports. Uses a disposable profile.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

output = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-shoreline-qa'))
output.mkdir(parents=True, exist_ok=True)
with sync_playwright() as playwright:
    browser = playwright.chromium.launch(executable_path='/usr/bin/chromium', args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'
    ])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' and 'favicon' not in msg.text else None)
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/'), wait_until='domcontentloaded', timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game?.state === "play"')
    summary = page.evaluate('''async () => {
      const output=[], marks=new Set();
      for (const [x,z] of [[-5,-5],[-5,-4],[-4,-5],[0,0],[1,2],[4,-4],[-2,3]]) {
        const c=new TERRA_SEWER_BRIDGE.Chunk(x,z);c.prep();c.terrain();
        for (let i=1;i<c.w.a.length;i+=2) marks.add(c.w.a[i]);
        output.push({x,z,p:c.w.p,n:c.w.n,c:c.w.c,cols:c.cols,grid:Array.from(c.grid),river:c.riverHere,rng:[c.r(),c.r(),c.r()]});
      }
      const bytes=new TextEncoder().encode(JSON.stringify(output));
      const digest=Array.from(new Uint8Array(await crypto.subtle.digest('SHA-256',bytes)),b=>b.toString(16).padStart(2,'0')).join('');
      return {digest, marks:[...marks]};
    }''')
    assert summary['digest'] == '49be172e845d04a451fda73df6fbf4f2e15d16be0bc399027841f753d7bb1dfb', summary
    assert 2 in summary['marks'] and 3 in summary['marks'], summary
    page.evaluate('''() => {game.p.x=-212; game.p.z=-228; game.p.hp=game.p.maxHp=10000; game.camT=null;}''')
    page.wait_for_timeout(6000)
    page.screenshot(path=str(output / 'river-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(2000)
    page.screenshot(path=str(output / 'river-phone.png'))
    assert not errors, errors
    print('PASS: baseline terrain, water geometry, collisions and RNG; shoreline coverage and rendered river desktop/phone; JS/console 0')
    browser.close()
