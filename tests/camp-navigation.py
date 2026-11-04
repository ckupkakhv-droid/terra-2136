"""Browser integration check. Run with server on :8080, Python Playwright and Chromium.
Uses a fresh browser context and recruits two test residents through the native API.
No personal save files are loaded. Screenshots go outside the checkout.
"""
from pathlib import Path
import os
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-navigation-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto('http://127.0.0.1:8080/play/', wait_until='load', timeout=90000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    expect(page.locator('#hud')).to_be_visible()
    expect(page.locator('#bCamp')).to_have_attribute('aria-label', 'Лагерь и жители')
    page.locator('#bCamp').click()
    page.evaluate("""() => {
      game.p.camp.rep = 1000;
      for (const id of ['qa-1','qa-2']) {
        if (!game.camp.recruit({id}).ok) throw Error('Fixture recruitment failed');
      }
      game.p.camp.settlers['qa-1'].name = 'Павел Оченьдлиннаяфамилияпоселенца';
    }""")
    before = page.evaluate('JSON.stringify(game.p.camp)')
    tabs = page.locator('#campTabs button')
    tabs.first.focus()
    page.keyboard.press('ArrowRight')
    expect(page.locator('[data-camp-tab="settlers"]')).to_be_focused()
    page.keyboard.press('Enter')
    search = page.locator('#residentSearchInput')
    expect(search).to_be_visible()
    search.fill('павел')
    expect(page.locator('.residentRow:visible')).to_have_count(1)
    page.locator('[data-worker-filter="free"]').click()
    expect(search).to_have_value('павел')
    expect(page.locator('.residentRow:visible')).to_have_count(1)
    page.locator('.residentRow:visible .residentSummary').click()
    page.locator('[data-camp-back]').click()
    expect(search).to_have_value('павел')
    search.fill('несуществующее имя')
    expect(page.locator('.residentRow:visible')).to_have_count(0)
    expect(page.locator('.residentSearchStatus')).to_contain_text('Совпадений нет')
    page.locator('.residentSearch button').click()
    expect(search).to_be_focused()
    expect(page.locator('.residentRow:visible')).to_have_count(2)
    search.fill('разведчик')
    expect(page.locator('.residentRow:visible')).to_have_count(1)
    page.locator('.residentSearch button').click()
    expect(page.locator('.residentRecommendation')).to_contain_text('Строительство и снабжение расходуют ресурсы')
    for name, width, height in [('desktop',1280,800),('portrait',390,844),('landscape',844,390)]:
        page.set_viewport_size({'width':width,'height':height})
        search.scroll_into_view_if_needed()
        assert page.locator('#campBody').evaluate('(e) => e.scrollWidth <= e.clientWidth + 1'), name
        assert search.bounding_box()['height'] >= 44
        page.screenshot(path=str(out / (name + '.png')))
    assert page.evaluate('JSON.stringify(game.p.camp)') == before, 'Browsing mutated camp state'
    page.locator('#campPanel .panelFoot button').click()
    expect(page.locator('#campPanel')).not_to_be_visible()
    assert page.evaluate('game.state') == 'play'
    assert not errors, errors
    print('PASS: search, profession, empty result, clear, filter/detail persistence, keyboard tabs, 3 viewports, read-only camp state, return to game; JavaScript errors: 0')
    browser.close()
