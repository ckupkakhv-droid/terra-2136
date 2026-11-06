"""Real camp sheets: focus, scrolling, dismissal and native refresh cleanup.

Run against a disposable browser profile; no existing saves are used.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-info-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/'), timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.locator('#bCamp').click()
    page.wait_for_function('!!window.terraCampUI')
    def switch(tab):
        if page.locator('#campTabs').get_attribute('hidden') is not None:
            page.locator('.fbSections').click()
        page.locator('#campTabs [data-camp-tab="'+tab+'"]').click()
    page.evaluate("game.p.camp.rep=1000;game.camp.recruit({id:'qa-info'})")
    before = page.evaluate('JSON.stringify(game.p.camp)')
    switch('settlers')
    page.locator('[data-resident="qa-info"]').click()
    source = page.locator('.dossier .deskInfo')
    source.focus()
    page.keyboard.press('Enter')
    sheet = page.locator('.campInfoSheet')
    close = sheet.locator('.campInfoClose')
    expect(sheet).to_have_class('campInfoSheet deskSheet')
    expect(close).to_be_focused()
    for key in ['Tab', 'Shift+Tab', 'Tab']:
        page.keyboard.press(key)
        expect(close).to_be_focused()
    # Even programmatic focus cannot move into the background's native close.
    page.evaluate('document.querySelector("#campPanel .x").focus()')
    expect(close).to_be_focused()
    for name, width, height in [('portrait', 390, 844), ('narrow', 320, 568),
                                ('landscape', 844, 390), ('desktop', 1280, 800)]:
        page.set_viewport_size({'width': width, 'height': height})
        # Read the end of the actual biography/skills sheet. Its close stays put.
        old = close.bounding_box()
        sheet.locator('.campInfoSheet__body').evaluate('e=>e.scrollTop=e.scrollHeight')
        now = close.bounding_box()
        assert abs(now['y'] - old['y']) < 1 and now['y'] >= 0, (name, old, now)
        assert now['height'] >= 48 and now['width'] >= 48, (name, now)
        assert page.evaluate('''()=>{
          const s=document.querySelector('.campInfoSheet'),b=s.getBoundingClientRect();
          return s.scrollWidth<=s.clientWidth+1 && b.left>=0 && b.right<=innerWidth+1 && b.bottom<=innerHeight+1;
        }'''), name
        page.screenshot(path=str(out / f'{name}.png'))
    scroll = page.locator('#campBody').evaluate('e=>e.scrollTop')
    page.keyboard.press('Escape')
    expect(sheet).to_have_count(0)
    expect(source).to_be_focused()
    assert page.locator('#campBody').evaluate('e=>e.scrollTop') == scroll
    assert page.evaluate('game.state') == 'modal'

    # A long sheet with an interactive tail still traps both directions. The
    # dimmed exposed area dismisses it, without changing tabs or camp orders.
    page.evaluate('''()=>{
      document.querySelector('.dossier .deskInfo').focus();
      const c=document.createElement('div');
      for(let i=0;i<30;i++){const p=document.createElement('p');p.textContent='Запись полевого журнала '+i;c.append(p)}
      const b=document.createElement('button');b.textContent='Конец записи';c.append(b);
      terraCampUI.openInfo('Длинная запись',c);
    }''')
    page.keyboard.press('Shift+Tab')
    expect(sheet.locator('.campInfoSheet__body button')).to_be_focused()
    assert page.evaluate('''()=>{
      const body=document.querySelector('.campInfoSheet__body').getBoundingClientRect();
      const target=document.activeElement.getBoundingClientRect();
      return target.top>=body.top-1 && target.bottom<=body.bottom+1;
    }'''), 'Keyboard focus is clipped inside the long sheet'
    page.keyboard.press('Tab')
    expect(close).to_be_focused()
    page.keyboard.press('Tab')
    expect(sheet.locator('.campInfoSheet__body button')).to_be_focused()
    page.keyboard.press('Shift+Tab')
    expect(close).to_be_focused()
    page.locator('.campInfoBackdrop').click(position={'x': 10, 'y': 10})
    expect(sheet).to_have_count(0)
    expect(source).to_be_focused()

    # Building sheets use the same close and restore path.
    switch('build')
    building = page.locator('.bp .deskInfo').first
    building.focus()
    page.keyboard.press('Enter')
    expect(sheet).to_be_visible()
    close.tap()
    expect(building).to_be_focused()
    expect(page.locator('.campInfoBackdrop')).to_have_count(0)

    # Refresh/reopen and forced panel closure must not leave inert navigation.
    building.click()
    page.evaluate('game.ui.campPanel.select("settlers")')
    expect(sheet).to_have_count(0)
    assert page.locator('#campTabs').evaluate('e=>!e.inert')
    page.locator('[data-resident="qa-info"]').click()
    source.click()
    assert page.evaluate('JSON.stringify(game.p.camp)') == before, 'Reading changed camp state'
    page.evaluate('game.ui.close("campPanel")')
    expect(sheet).to_have_count(0)
    expect(page.locator('.campInfoBackdrop')).to_have_count(0)
    assert page.evaluate('game.state') == 'play'
    page.locator('#bCamp').click()
    switch('overview')
    assert page.evaluate('game.ui.campPanel.tab') == 'overview'
    assert not errors, errors
    print('PASS camp info: 4 viewports, focus trap/return, sticky close, backdrop, buildings, native refresh and panel cleanup; JS0')
    browser.close()
