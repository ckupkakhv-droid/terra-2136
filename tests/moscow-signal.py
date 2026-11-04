"""Actual radio-site clue with a disposable profile and progress fixtures."""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

expect.set_options(timeout=30000)
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-moscow-signal-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium'),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), timeout=90000)
    page.locator('#mNew').tap(); page.locator('#skip').tap()
    page.wait_for_function('game.sewers && game.state === "play"')
    page.evaluate('game.p.x=23.5;game.p.z=124;game.camT=null')
    page.wait_for_function('TerraWorldSites.placements.some(p=>p.id==="signal")', timeout=90000)
    site = page.evaluate('''() => {
      const c=game.world.conts.find(c=>TerraWorldSites.placementForContainer(game,c)?.id==='signal');
      if (!c) throw Error('Radio site container is not loaded');
      for(let r=.6;r<2.2;r+=.2) for(let a=0;a<Math.PI*2;a+=Math.PI/12) {
        const x=c.x+Math.cos(a)*r,z=c.z+Math.sin(a)*r;
        if(!game.world.collide({x,z},.3) && game.world.segHit(x,z,c.x,c.z,1.1)<0) {
          game.p.x=x;game.p.z=z;game.camT=null;return {x:c.x,z:c.z};
        }
      }
      throw Error('No reachable radio site approach');
    }''')
    assert site
    expect(page.locator('#moscowSignalAction')).to_be_hidden()
    page.evaluate('''() => { window.signalToasts=[]; const toast=game.ui.toast;
      game.ui.toast=function(text,...args){if(text.includes('Московский перехват'))signalToasts.push(text);return toast.call(this,text,...args);}; }''')
    page.evaluate('game.defeated["12,-10"]=1')
    expect(page.locator('#moscowSignalAction')).to_be_hidden()
    page.evaluate('game.p.routeTransit={v:1,stage:2}')
    expect(page.locator('#moscowSignalAction')).to_be_visible()
    page.wait_for_function('signalToasts.length === 1')
    before = page.evaluate('''() => JSON.stringify({defeated:game.defeated,
      transit:game.p.routeTransit,inv:game.p.inv,weapons:game.p.weapons,chests:game.p.durableChests})''')
    page.locator('#moscowSignalAction').tap()
    expect(page.locator('#recordingTitle')).to_have_text('РУЧНАЯ ЛЕНТА')
    page.locator('#recordingNext').tap()
    expect(page.locator('#recordingText')).to_contain_text('Московский контур')
    page.screenshot(path=str(out/'signal-portrait.png'))
    page.locator('#recordingSkip').tap()
    expect(page.locator('#moscowSignalAction')).to_be_visible()
    assert page.evaluate('document.activeElement.id') == 'moscowSignalAction'
    page.locator('#moscowSignalAction').tap()
    expect(page.locator('#recordingTitle')).to_have_text('РУЧНАЯ ЛЕНТА')
    page.keyboard.press('Escape')
    expect(page.locator('#sewerRecording')).to_have_count(0)
    after = page.evaluate('''() => JSON.stringify({defeated:game.defeated,
      transit:game.p.routeTransit,inv:game.p.inv,weapons:game.p.weapons,chests:game.p.durableChests})''')
    assert before == after
    assert page.evaluate('signalToasts.length') == 1
    page.evaluate('game.ui.openMap()')
    page.locator('#sewerLayerButton').tap()
    expect(page.locator('#moscowRoute')).to_contain_text('Московский перехват')
    page.locator('#moscowRoute summary').tap()
    expect(page.locator('#moscowRoute')).to_contain_text('Радиопост Ноль')
    page.set_viewport_size({'width':844,'height':390})
    assert page.locator('#sewerMap .win').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
    page.screenshot(path=str(out/'journal-landscape.png'))
    assert not errors, errors
    print('PASS: actual reachable radio site, gated repeatable clue, modal control, unchanged progress and map journal; no JS errors')
    browser.close()
