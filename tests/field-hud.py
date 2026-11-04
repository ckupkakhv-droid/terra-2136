"""Real-game HUD checks with disposable desktop and touch browser profiles."""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-field-hud-qa'))
out.mkdir(parents=True, exist_ok=True)
chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
if not chromium:
    raise SystemExit('Set TERRA_CHROMIUM to Chromium/Chrome.')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    for mode in ['desktop', 'touch']:
        context = browser.new_context(viewport={'width':1280,'height':800}, has_touch=mode=='touch', is_mobile=mode=='touch')
        page = context.new_page()
        page.set_default_timeout(60000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), wait_until='load', timeout=90000)
        if mode == 'touch':
            page.locator('#mNew').tap()
            page.locator('#skip').tap()
        else:
            page.locator('#mNew').click()
            page.locator('#skip').click()
        expect(page.locator('#hud')).to_be_visible()
        if mode == 'touch':
            expect(page.locator('#tInteract')).to_be_visible()
        toggle = page.locator('#objectiveToggle')
        expect(toggle).to_have_attribute('aria-expanded', 'false')
        sizes = [('desktop',1280,800)] if mode=='desktop' else [('portrait',390,844),('landscape',844,390),('small',667,375),('compact',568,320)]
        for name, width, height in sizes:
            page.set_viewport_size({'width':width,'height':height})
            geometry = page.evaluate("""() => {
              const target = document.getElementById('obj').getBoundingClientRect();
              const nodes = document.querySelectorAll('#tl,#topBtns,#mmW,#touch button');
              const collisions = [...nodes].filter(el => {
                if (!el.getClientRects().length) return false;
                const r = el.getBoundingClientRect();
                return target.left < r.right && target.right > r.left && target.top < r.bottom && target.bottom > r.top;
              }).map(el => el.id);
              return {collisions,inside:target.left>=0&&target.right<=innerWidth,hit:document.getElementById('objectiveToggle').getBoundingClientRect().height};
            }""")
            assert not geometry['collisions'], (name, geometry)
            assert geometry['inside'] and geometry['hit'] >= 44, (name, geometry)
            for button in ['bCamp','bMap','bPause']:
                expect(page.locator('#'+button+' .hudButtonCaption')).to_be_visible()
            if mode=='touch': toggle.tap()
            else: toggle.press('Space')
            expect(toggle).to_have_attribute('aria-expanded', 'true')
            expect(page.locator('#objH')).to_be_visible()
            expect(page.locator('#objectiveDetailTitle')).to_have_text(page.locator('#objT').inner_text())
            assert page.locator('#objH').evaluate("""el => {
                const r = el.getBoundingClientRect();
                const hit = document.elementFromPoint(r.x+r.width/2, r.y+r.height/2);
                return hit === el || el.contains(hit);
            }"""), 'Hint is clipped or covered by another control'
            if mode=='touch': page.locator('#objH').tap()
            assert page.evaluate("game.state === 'play' && !game.stL.on && !game.stR.on && !game.mouse.down && !game.keys.has('Space')")
            page.screenshot(path=str(out / (name+'-expanded.png')))
            toggle.press('Escape')
            expect(toggle).to_have_attribute('aria-expanded', 'false')
            assert page.evaluate("game.state === 'play'")
            page.screenshot(path=str(out / (name+'.png')))
        # Live native goal nodes remain intact and readable after disclosure.
        expect(page.locator('#objT')).to_have_count(1)
        expect(page.locator('#objH')).to_have_count(1)
        # Keyboard used to miss pointerdown-only handlers; it must not trigger dodge.
        page.locator('#bMap').press('Enter')
        expect(page.locator('#wmap')).to_be_visible()
        page.keyboard.press('Escape')
        page.locator('#bPause').press('Space')
        expect(page.locator('#pResume')).to_be_visible()
        page.locator('#pResume').click()
        page.locator('#lvlW').press('Enter')
        expect(page.locator('#inv')).to_be_visible()
        assert page.evaluate("game.state === 'modal'")
        page.keyboard.press('Escape')
        assert not errors, errors
        print('PASS', mode, 'layout, captions, objective disclosure, touch input isolation, keyboard map/pause/skills; JavaScript errors: 0', flush=True)
        context.close()
    browser.close()
