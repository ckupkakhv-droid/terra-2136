"""Touch-browser check for work availability and native section navigation.

Run with the game served locally, Python Playwright and Chromium/Chrome.
Creates a disposable profile and native recruited resident; uses no personal save.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-jobs-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), wait_until='load', timeout=90000)
    page.locator('#mNew').tap()
    page.locator('#skip').tap()
    expect(page.locator('#hud')).to_be_visible()
    page.locator('#bCamp').tap()
    page.evaluate("""() => {
      game.p.camp.rep = 1000;
      if (!game.camp.recruit({id:'qa-jobs'}).ok) throw Error('Recruitment failed');
      game.p.camp.settlers['qa-jobs'].name = 'Павел Испытатель';
    }""")
    before = page.evaluate('JSON.stringify(game.p.camp)')

    def open_resident():
        page.locator('#campTabs [data-camp-tab="settlers"]').tap()
        expect(page.locator('#residentSearchInput')).to_be_visible()
        page.locator('#residentSearchInput').fill('Павел')
        page.locator('[data-resident="qa-jobs"]').tap()
        expect(page.locator('.residentJobOption')).to_have_count(13)

    open_resident()
    # Disabled native controls stay disabled, with their exact reason exposed.
    disabled = page.locator('.campJobs [data-resident-job]:disabled')
    assert disabled.count() > 0
    for button in disabled.all():
        reason_id = button.get_attribute('aria-describedby')
        assert reason_id
        expect(page.locator('#' + reason_id)).to_have_text(button.get_attribute('title'))
    expect(page.locator('[data-resident-job="idle"]')).to_be_enabled()
    expect(page.locator('[data-resident-job="idle"] + .residentJobReason')).to_be_hidden()

    # Reasons are visible on touch, without hover; both orientations remain usable.
    for name, width, height in [('portrait',390,844),('landscape',844,390)]:
        page.set_viewport_size({'width':width,'height':height})
        page.locator('[data-resident-job="build"]').scroll_into_view_if_needed()
        assert page.locator('#campBody').evaluate('(e) => e.scrollWidth <= e.clientWidth + 1'), name
        link = page.locator('[data-resident-job="build"]').locator('..').locator('.residentJobLink')
        link.scroll_into_view_if_needed()
        expect(link).to_be_in_viewport()
        assert link.bounding_box()['height'] >= 44
        back = page.locator('[data-camp-back="list"]')
        expect(back).to_be_in_viewport()
        assert back.bounding_box()['y'] >= page.locator('#campBody').bounding_box()['y'] - 1
        page.screenshot(path=str(out / (name + '.png')))

    page.set_viewport_size({'width':390,'height':844})
    for job, target in [('build','build'), ('repair','build'), ('haul','warehouses'), ('operate','power')]:
        button = page.locator('[data-resident-job="' + job + '"]')
        expect(button).to_be_disabled()
        button.locator('..').locator('.residentJobLink').tap()
        assert page.evaluate('game.ui.campPanel.tab') == target
        assert page.evaluate('game.state') == 'modal'
        open_resident()
    assert page.evaluate('JSON.stringify(game.p.camp)') == before, 'Navigation mutated camp state'

    # A native order still runs normally: explicit rest then existing guarded auto.
    page.locator('[data-resident-job="idle"]').tap()
    expect(page.locator('.campResidents')).to_contain_text('Назначение принято')
    assert page.evaluate("!!game.p.camp.settlers['qa-jobs'].order.stick")
    page.locator('[data-camp-back="list"]').tap()
    expect(page.locator('#residentSearchInput')).to_have_value('Павел')
    page.locator('[data-resident-order="qa-jobs"]').tap()
    expect(page.locator('.campResidents')).to_contain_text('Приказ сохранён')
    assert not page.evaluate("!!game.p.camp.settlers['qa-jobs'].order.stick")
    assert not errors, errors
    print('PASS: native disabled reasons and accessibility, four destination links, touch portrait/landscape, read-only navigation, native rest and guarded auto; JavaScript errors: 0')
    browser.close()
