"""Реальная навигация рюкзака: касание, клавиатура, фокус и неизменность сейва.

Одноразовый профиль Chromium. TERRA_TEST_URL задаёт игру или самостоятельный HTML.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/')
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-backpack-navigation'))
out.mkdir(parents=True, exist_ok=True)
tabs = ['eq', 'items', 'craft', 'skills', 'settle', 'log']

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 1382, 'height': 964}, has_touch=True)
    page.set_default_timeout(90000)
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.on('console', lambda m: errors.append(m.text[:1000]) if m.type == 'error' else None)
    page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
    page.goto(url, timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game.state==="play" && game.sewers && TERRA_KITS.ready && terraDefense.ready')
    page.evaluate('()=>{game.loop=()=>{};if(document.getElementById("inv").classList.contains("hidden"))game.ui.openInv("skills");else document.querySelector("#inv [data-tab=skills]").click()}')
    nav = page.locator('#inv [role="tablist"]')
    expect(nav).to_be_visible()

    def tab(name):
        return page.locator('#inv [data-tab="' + name + '"]')

    def settle():
        page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')

    def shot(name):
        page.evaluate('game.renderT()')
        page.screenshot(path=str(out / name), animations='disabled')

    def selected(name):
        expect(tab(name)).to_have_attribute('aria-selected', 'true')
        expect(page.locator('#inv [role="tab"][aria-selected="true"]')).to_have_count(1)
        expect(page.locator('#invBody')).to_have_attribute('aria-labelledby', 'inventory-tab-' + name)
        assert page.evaluate('game.ui.tab') == name

    def snapshot():
        return page.evaluate('JSON.stringify({p:game.p,save:localStorage.getItem("terra_save")})')

    def fit():
        return nav.evaluate('''root=>{
            const r=root.getBoundingClientRect();
            return {viewport:[innerWidth,innerHeight],client:[root.clientWidth,root.clientHeight],
                scroll:[root.scrollWidth,root.scrollHeight],orientation:root.getAttribute('aria-orientation'),
                buttons:[...root.querySelectorAll('[role=tab]')].map(b=>{
                    const a=b.getBoundingClientRect();
                    const label=[...b.querySelectorAll('span')].find(s=>getComputedStyle(s).display!=='none');
                    const l=label.getBoundingClientRect();
                    return {id:b.dataset.tab,width:a.width,height:a.height,label:label.textContent,
                        labelFits:l.left>=a.left-1&&l.right<=a.right+1,
                        visible:Math.max(0,Math.min(a.right,r.right)-Math.max(a.left,r.left))*
                            Math.max(0,Math.min(a.bottom,r.bottom)-Math.max(a.top,r.top))/(a.width*a.height)};
                })};
        }''')

    # Warm native one-time view setup before comparing navigation alone.
    for name in tabs:
        tab(name).tap()
        selected(name)
    tab('skills').tap()
    settle()
    before = snapshot()
    report = {'views': []}
    for w, h in [(320, 568), (390, 844), (844, 390), (1382, 964)]:
        page.set_viewport_size({'width': w, 'height': h})
        settle()
        info = fit()
        assert len(info['buttons']) == 6, info
        assert all(b['width'] >= 43.5 and b['height'] >= 43.5 and b['visible'] > .995 and b['labelFits'] for b in info['buttons']), info
        assert info['scroll'][0] <= info['client'][0] + 1, info
        for name in tabs:
            tab(name).tap()
            selected(name)
            assert snapshot() == before, ('Navigation changed player/save', w, name)
        tab('skills').tap()
        page.locator('#invBody').evaluate('e=>e.scrollTop=0')
        shot(f'{w}x{h}.png')
        report['views'].append(info)
    print('PASS all six tabs visible/44px targets/labels fit; actual touch switches all six in four sizes; entire player and raw save unchanged', flush=True)

    report['keyboard'] = []
    for w, h, previous, following, orientation in [
        (390, 844, 'ArrowLeft', 'ArrowRight', 'horizontal'),
        (844, 390, 'ArrowUp', 'ArrowDown', 'vertical')]:
        page.set_viewport_size({'width': w, 'height': h})
        settle()
        expect(nav).to_have_attribute('aria-orientation', orientation)
        tab('skills').tap()
        tab('skills').focus()
        page.keyboard.press(following)
        expect(tab('settle')).to_be_focused()
        selected('skills')
        page.keyboard.press('End')
        expect(tab('log')).to_be_focused()
        selected('skills')
        if w == 390:
            shot('keyboard-focus.png')
        page.keyboard.press('Enter')
        selected('log')
        page.keyboard.press(following)
        expect(tab('eq')).to_be_focused()
        selected('log')
        page.keyboard.press('Space')
        selected('eq')
        page.keyboard.press(previous)
        expect(tab('log')).to_be_focused()
        selected('eq')
        page.keyboard.press('Home')
        expect(tab('eq')).to_be_focused()
        expect(page.locator('#inv [role="tab"][tabindex="0"]')).to_have_count(1)
        assert snapshot() == before
        report['keyboard'].append({'viewport': [w, h], 'manualActivation': True, 'wrap': True, 'homeEnd': True})
    print('PASS horizontal/vertical arrows, wrap, Home/End focus only; Enter/Space native activation; one tab stop; no player/save changes', flush=True)

    # A short landscape viewport scrolls the rail; the final tab remains reachable.
    page.set_viewport_size({'width': 812, 'height': 320})
    settle()
    tab('eq').focus()
    page.keyboard.press('End')
    expect(tab('log')).to_be_focused()
    settle()
    short = fit()
    assert short['buttons'][-1]['visible'] > .995, short
    page.keyboard.press('Enter')
    selected('log')
    shot('812x320.png')
    page.locator('#inv .x[data-close="inv"]').tap()
    page.wait_for_function('game.state==="play"')
    page.evaluate('game.ui.openInv("log")')
    settle()
    assert fit()['buttons'][-1]['visible'] > .995
    selected('log')
    report['shortLandscape'] = short
    print('PASS 812x320 final tab revealed by End and after reopening; native close resumes play', flush=True)

    # The native async commit may finish after the user moves focus to navigation.
    page.set_viewport_size({'width': 1382, 'height': 964})
    tab('skills').tap()
    expect(page.locator('.classDossier')).to_be_visible()
    page.evaluate('''()=>{const original=game.commitClass;game.commitClass=function(...args){
        return new Promise(resolve=>{window.__resumeClass=()=>resolve(original.apply(this,args))})}}''')
    page.locator('[data-circuit-toggle="on"]').click()
    expect(page.locator('[data-circuit-toggle]')).to_be_disabled()
    tab('skills').focus()
    page.keyboard.press('ArrowRight')
    expect(tab('settle')).to_be_focused()
    page.evaluate('()=>{__resumeClass()}')
    expect(page.locator('[data-circuit-toggle="off"]')).to_be_enabled()
    expect(tab('settle')).to_be_focused()
    selected('skills')
    assert page.evaluate('game.p.classProfile.classId==="contourist" && JSON.parse(localStorage.getItem("terra_save")).p.classProfile.classId==="contourist"')
    page.keyboard.press('Enter')
    selected('settle')
    report['asyncClassFocus'] = {'focusRetained': True, 'nativeClassSaved': True, 'activationAfterCommit': True}
    assert not errors, errors
    report['errors'] = errors
    (out / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2))
    print('PASS real deferred class commit/save preserves navigation focus; Enter still selects destination; JS0', flush=True)
    browser.close()
