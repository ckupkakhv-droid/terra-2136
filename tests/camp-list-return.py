"""Native resident list -> dossier -> task targets -> list, with search retained.

Uses a disposable profile and native recruitment API. Does not issue any orders.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-list-qa'))
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
    page.evaluate('''()=>{
      game.p.camp.rep=1000;
      for(const [id,name] of [['qa-return-1','Анна Соснова'],['qa-return-2','Борис Соснов'],['qa-return-3','Иван Громов']]){
        if(!game.camp.recruit({id}).ok)throw Error('Recruitment fixture failed');
        game.p.camp.settlers[id].name=name;
      }
    }''')
    before = page.evaluate('JSON.stringify(game.p.camp)')
    for name, width, height in [('portrait', 390, 844), ('landscape', 844, 390), ('desktop', 1280, 800)]:
        page.set_viewport_size({'width': width, 'height': height})
        page.locator('#campTabs [data-camp-tab="settlers"]').click()
        search = page.locator('#residentSearchInput')
        search.fill('соснов')
        page.locator('[data-worker-filter="free"]').click()
        expect(page.locator('.residentRow:visible')).to_have_count(2)
        page.locator('[data-resident="qa-return-1"]').click()
        expect(page.locator('.campResidents.dossier')).to_be_visible()
        expect(page.locator('.dossierDial')).to_contain_text('1 из 2')
        page.locator('.dossierStep[data-step="1"]').click()
        expect(page.locator('[data-resident-biography="qa-return-2"]')).to_be_attached()
        expect(page.locator('.dossierDial')).to_contain_text('2 из 2')
        page.locator('.dossierStep[data-step="-1"]').click()
        expect(page.locator('[data-resident-biography="qa-return-1"]')).to_be_attached()
        # Craft opens the native recipe selector, without assigning a job.
        page.locator('[data-resident-job="craft"]').click()
        expect(page.locator('.campTargets')).to_be_visible()
        expect(page.locator('.campResidents.dossier')).to_have_count(0)
        expect(page.locator('#campBody')).not_to_have_class('body scroll deskDossier')
        page.locator('[data-camp-back="resident"]').click()
        expect(page.locator('.campResidents.dossier')).to_be_visible()
        page.locator('[data-camp-back="list"]').click()
        expect(page.locator('.campResidents.dossier')).to_have_count(0)
        expect(search).to_have_value('соснов')
        expect(page.locator('[data-worker-filter="free"]')).to_have_attribute('aria-pressed', 'true')
        expect(page.locator('.residentRow:visible')).to_have_count(2)
        expect(page.locator('[data-resident="qa-return-3"]')).not_to_be_visible()
        expect(page.locator('[data-resident="qa-return-1"]')).to_be_focused()
        # This native recruitment fold was hidden by the stale dossier class.
        hiring = page.locator('.campResidents > .campFold')
        expect(hiring.locator('summary')).to_be_visible()
        hiring.locator('summary').tap()
        expect(hiring).to_have_attribute('open', '')
        expect(hiring.locator('.campGrid')).to_be_visible()
        assert page.locator('#campBody').evaluate('e=>e.scrollWidth<=e.clientWidth+1'), name
        page.screenshot(path=str(out / f'{name}-hiring.png'))
        page.locator('.residentSearch button').click()
        expect(page.locator('.residentRow:visible')).to_have_count(3)
        assert page.evaluate('JSON.stringify(game.p.camp)') == before, 'Browsing changed camp state'
        print(f'PASS {name}: filtered paging, task targets, back, visible hiring, focus and unchanged camp state', flush=True)
    assert not errors, errors
    print('PASS camp list return; JS0')
    browser.close()
