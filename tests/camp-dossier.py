"""«Штабной стол»: личное дело жителя и чертежи построек (play/ui/camp-dossier.*).

Сервер из корня репозитория на :8080 (или TERRA_TEST_URL), Python Playwright и Chromium/Chrome.
Чистый профиль, жители создаются штатным API; личные сохранения не используются.
Проверяет в 390×844, 844×390, 360×740, 667×375 и 1280×800 (касания на телефонных размерах):
печать в досье реально меняет работу жителя штатным обработчиком, «i» открывает подробности,
листание дел, чертежи с бирками ресурсов, цели касания ≥ 48 px без горизонтальной прокрутки,
вкладку «Оборона» и отсутствие ошибок в консоли. Затем — сохранение профиля и загрузка через
«Продолжить» без потерь жителей и их работ.
"""
from pathlib import Path
import json
import os
import shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-dossier-qa'))
out.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
VIEWS = [('portrait', 390, 844), ('landscape', 844, 390), ('narrow', 360, 740), ('small-landscape', 667, 375), ('desktop', 1280, 800)]

GEOMETRY = """() => {
  const panel = document.getElementById('campPanel'), body = document.getElementById('campBody');
  const visible = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && !e.closest('[hidden]') && !e.closest('details:not([open]) > :not(summary)'); };
  const small = [];
  for (const e of panel.querySelectorAll('button, summary, select, input, a[href], [role=button]')) {
    if (!visible(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.width < 47.5 || r.height < 47.5) small.push(`${(e.getAttribute('aria-label') || e.textContent || e.tagName).trim().slice(0, 40)} ${Math.round(r.width)}×${Math.round(r.height)}`);
  }
  return {small, overflow: body.scrollWidth > body.clientWidth + 1};
}"""

def geometry(page, label):
    g = page.evaluate(GEOMETRY)
    assert not g['small'], f'{label}: цели < 48 px: {g["small"]}'
    assert not g['overflow'], f'{label}: горизонтальная прокрутка'

def boot(page, tap):
    page.goto(URL, wait_until='load', timeout=90000)
    tap(page.locator('#mNew'))
    tap(page.locator('#skip'))
    expect(page.locator('#hud')).to_be_visible()

with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    for name, width, height in VIEWS:
        touch = name != 'desktop'
        context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=touch, has_touch=touch)
        page = context.new_page()
        page.set_default_timeout(60000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda m: m.type == 'error' and errors.append(m.text))
        tap = (lambda loc: loc.tap()) if touch else (lambda loc: loc.click())
        boot(page, tap)
        tap(page.locator('#bCamp'))
        page.wait_for_function('() => !!window.terraCampUI')
        page.evaluate("""() => { game.p.camp.rep = 1000;
          for (const id of ['qa-d1', 'qa-d2', 'qa-d3']) if (!game.camp.recruit({id}).ok) throw Error('Fixture recruitment failed');
          game.p.camp.settlers['qa-d1'].name = 'Павел Ветров'; game.p.camp.settlers['qa-d1'].needs.food = 30;
          game.p.camp.res.wood = 24; game.p.camp.res.scrap = 12; }""")

        # Личное дело.
        tap(page.locator('#campTabs [data-camp-tab="settlers"]'))
        tap(page.locator('[data-resident="qa-d1"]'))
        dossier = page.locator('#campBody .campResidents.dossier')
        expect(dossier).to_be_visible()
        expect(dossier.locator('.dossierNeed')).to_have_count(5)
        expect(dossier.locator('.dossierNo')).to_contain_text('Личное дело')
        expect(dossier.locator('.dossierStamp')).to_be_visible()
        expect(dossier.locator('.dossierRadio .dossierDial')).to_contain_text('из 3')
        geometry(page, f'{name}/dossier')
        before = page.evaluate("game.p.camp.settlers['qa-d1'].job")
        target = 'gather:wood' if before != 'gather:wood' else 'gather:water'
        stamp = page.locator(f'#campBody .dossier [data-resident-job="{target}"]')
        stamp.scroll_into_view_if_needed()
        tap(stamp)
        page.wait_for_function(f"() => game.p.camp.settlers['qa-d1'].job === '{target}'")
        page.wait_for_timeout(150)
        expect(page.locator(f'#campBody .dossier .residentJobOption.isCurrent [data-resident-job="{target}"]')).to_have_count(1)
        expect(page.locator('#campBody .dossier .dossierStamp')).to_have_attribute('data-tone', 'ok')
        page.locator('#campBody').evaluate('e => e.scrollTop = 0')
        page.screenshot(path=str(out / f'{name}-resident.png'))
        # «i» — подробности на бумажном листе.
        tap(page.locator('#campBody .dossier .deskInfo'))
        expect(page.locator('.campInfoSheet.deskSheet')).to_be_visible()
        expect(page.locator('.campInfoSheet.deskSheet .campMeter').first).to_be_attached()
        geometry(page, f'{name}/dossier-info')
        if touch: page.screenshot(path=str(out / f'{name}-resident-info.png'))
        tap(page.locator('.campInfoSheet .campInfoClose'))
        expect(page.locator('.campInfoSheet')).to_have_count(0)
        # Листание дел по рации.
        first = page.locator('#campBody .dossier [data-resident-biography]').get_attribute('data-resident-biography')
        tap(page.locator('#campBody .dossier .dossierStep[data-step="1"]'))
        page.wait_for_function(f"() => {{ const b = document.querySelector('#campBody .dossier [data-resident-biography]'); return b && b.dataset.residentBiography !== '{first}'; }}")
        tap(page.locator('#campBody .dossier .dossierStep[data-step="-1"]'))
        page.wait_for_function(f"() => document.querySelector('#campBody .dossier [data-resident-biography]')?.dataset.residentBiography === '{first}'")

        # Чертежи.
        tap(page.locator('#campTabs [data-camp-tab="build"]'))
        expect(page.locator('#campBody .blueprints .deskTag')).to_have_count(6)
        n = page.locator('#campBody .campCard[data-building]').count()
        assert n > 0
        expect(page.locator('#campBody .campCard.bp .bpStamp')).to_have_count(n)
        expect(page.locator('#campBody .campCard.bp .deskInfo')).to_have_count(n)
        assert page.locator('#campBody .bp .bpChip').count() > 0
        geometry(page, f'{name}/build')
        page.locator('#campBody').evaluate('e => e.scrollTop = 0')
        page.screenshot(path=str(out / f'{name}-build.png'))
        tap(page.locator('#campBody .campCard.bp .deskInfo').first)
        expect(page.locator('.campInfoSheet.deskSheet p').first).to_be_visible()
        tap(page.locator('.campInfoSheet .campInfoClose'))

        # Оборона и другие вкладки — без оформления стола.
        tap(page.locator('#campTabs [data-camp-tab="defense"]'))
        page.wait_for_timeout(150)
        assert page.evaluate('game.ui.campPanel.tab') == 'defense'
        assert page.evaluate("!document.getElementById('campBody').classList.contains('deskBuild') && !document.getElementById('campBody').classList.contains('deskDossier')")
        assert 'defense' in page.evaluate('terraCampUI.sections()')
        assert not errors, f'{name}: {errors}'
        print(f'PASS {name} {width}×{height}: досье (печать → {target}), «i», листание, чертежи ({n}), «Оборона», цели ≥48, ошибок 0')
        context.close()

    # Сохранение профиля и загрузка через «Продолжить».
    context = browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page = context.new_page()
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    tap = lambda loc: loc.tap()
    boot(page, tap)
    tap(page.locator('#bCamp'))
    page.wait_for_function('() => !!window.terraCampUI')
    page.evaluate("""() => { game.p.camp.rep = 1000; for (const id of ['qa-s1', 'qa-s2']) game.camp.recruit({id}); }""")
    tap(page.locator('#campTabs [data-camp-tab="settlers"]'))
    tap(page.locator('[data-resident="qa-s1"]'))
    tap(page.locator('#campBody .dossier [data-resident-job="gather:food"]'))
    page.wait_for_function("() => game.p.camp.settlers['qa-s1'].job === 'gather:food'")
    tap(page.locator('#campTabs .campMobilePlay'))
    page.wait_for_function("() => game.state === 'play'")
    page.evaluate('async () => { await game.save(); }')
    raw = page.evaluate("() => localStorage.getItem('terra_save')")
    assert raw, 'Сохранение не записано'
    snapshot = page.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(game.p.camp.settlers).map(([k, s]) => [k, [s.name, s.job, s.prof, s.lvl]])))")
    page.reload(wait_until='load')
    tap(page.locator('#mContinue'))
    expect(page.locator('#hud')).to_be_visible()
    after = page.evaluate("() => JSON.stringify(Object.fromEntries(Object.entries(game.p.camp.settlers).map(([k, s]) => [k, [s.name, s.job, s.prof, s.lvl]])))")
    assert after == snapshot, f'Профиль после загрузки отличается:\n{snapshot}\n{after}'
    assert page.evaluate("() => localStorage.getItem('terra_save')") is not None
    assert not errors, errors
    print('PASS: save → reload → «Продолжить»: жители и их работы на месте')
    context.close()
    browser.close()
    print('PASS: camp-dossier, 5 viewports + save/load; JavaScript errors: 0')
