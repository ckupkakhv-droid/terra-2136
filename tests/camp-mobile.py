"""Геометрия мобильного каркаса лагеря (play/ui/camp-mobile.*).

Сервер из корня репозитория на :8080 (или TERRA_TEST_URL), Python Playwright и Chromium/Chrome.
Чистый профиль, жители создаются штатным API; личные сохранения не используются.
Проверяет: цели касания ≥ 48 px, вкладки без обрезки и наложений, нижнюю панель в портрете и рельс
в альбоме, safe-area-переменные (--sl/--sr/--st/--sb), вкладку «Оборона», API window.terraCampUI,
неизменность camp state при навигации и возврат в игру.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-mobile-qa'))
out.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
VIEWS = [('portrait', 390, 844), ('landscape', 844, 390), ('narrow', 360, 740), ('small-landscape', 667, 375), ('desktop', 1280, 800)]
TABS = ['overview', 'settlers', 'build', 'expansion', 'defense', 'more']

GEOMETRY = """() => {
  const vw = innerWidth, vh = innerHeight, panel = document.getElementById('campPanel');
  const css = n => parseFloat(getComputedStyle(document.documentElement).getPropertyValue(n)) || 0;
  const safe = {l: css('--sl'), r: css('--sr'), t: css('--st'), b: css('--sb')};
  const visible = e => { const r = e.getBoundingClientRect(); const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && !e.closest('[hidden]') && !e.closest('details:not([open]) > :not(summary)'); };
  const small = [];
  for (const e of panel.querySelectorAll('button, summary, select, input, a[href], [role=button]')) {
    if (!visible(e)) continue;
    const r = e.getBoundingClientRect();
    if (r.width < 47.5 || r.height < 47.5) small.push(`${(e.getAttribute('aria-label') || e.textContent || e.tagName).trim().slice(0, 40)} ${Math.round(r.width)}×${Math.round(r.height)}`);
  }
  const nav = document.getElementById('campTabs'), nr = nav.getBoundingClientRect();
  const tabs = [...nav.querySelectorAll('button')].filter(visible).map(b => { const r = b.getBoundingClientRect();
    return {id: b.dataset.campTab || b.className, x: r.left, y: r.top, r: r.right, b: r.bottom, w: r.width, h: r.height, on: b.classList.contains('on'),
      clipped: r.left < nr.left - 0.5 || r.right > nr.right + 0.5 || r.top < nr.top - 0.5 || r.bottom > nr.bottom + 0.5}; });
  let overlap = [];
  for (let i = 0; i < tabs.length; i++) for (let j = i + 1; j < tabs.length; j++) {
    const a = tabs[i], c = tabs[j];
    if (Math.min(a.r, c.r) - Math.max(a.x, c.x) > 0.5 && Math.min(a.b, c.b) - Math.max(a.y, c.y) > 0.5) overlap.push(a.id + '/' + c.id);
  }
  const body = document.getElementById('campBody');
  const br = body.getBoundingClientRect();
  const navOverBody = Math.min(nr.right, br.right) - Math.max(nr.left, br.left) > 0.5 && Math.min(nr.bottom, br.bottom) - Math.max(nr.top, br.top) > 0.5;
  const x = panel.querySelector('.win > h2 .x').getBoundingClientRect();
  const foot = panel.querySelector('.panelFoot');
  return {vw, vh, safe, small, tabs, overlap, navOverBody, navScroll: [nav.scrollWidth, nav.clientWidth, nav.scrollHeight, nav.clientHeight],
    bodyOverflow: body.scrollWidth > body.clientWidth + 1, close: [x.left, x.top, x.right, x.bottom],
    footVisible: !!foot && foot.getClientRects().length > 0 && getComputedStyle(foot).display !== 'none'};
}"""

def check(page, name, label, mode):
    g = page.evaluate(GEOMETRY)
    assert not g['small'], f'{name}/{label}: цели < 48 px: {g["small"]}'
    assert not g['overlap'], f'{name}/{label}: вкладки накладываются: {g["overlap"]}'
    assert not g['navOverBody'], f'{name}/{label}: панель вкладок перекрывает содержимое'
    assert not [t for t in g['tabs'] if t['clipped']], f'{name}/{label}: вкладка обрезана: {g["tabs"]}'
    assert not g['bodyOverflow'], f'{name}/{label}: горизонтальное переполнение'
    ids = [t['id'] for t in g['tabs']]
    for tab in TABS: assert tab in ids, f'{name}/{label}: нет вкладки {tab}: {ids}'
    s, vw, vh = g['safe'], g['vw'], g['vh']
    inside = lambda l, t, r, b: l >= s['l'] - 0.5 and t >= s['t'] - 0.5 and r <= vw - s['r'] + 0.5 and b <= vh - s['b'] + 0.5
    assert inside(*g['close']), f'{name}/{label}: ✕ вне safe-area {g["close"]} {s}'
    for t in g['tabs']: assert inside(t['x'], t['y'], t['r'], t['b']), f'{name}/{label}: {t["id"]} вне safe-area {s}'
    if mode == 'portrait':
        assert 'campMobilePlay' in ids and not g['footVisible'], f'{name}: «В игру» должна быть в панели вкладок'
        assert min(t['y'] for t in g['tabs']) >= vh * 0.8, f'{name}: вкладки не внизу экрана'
        assert len({round(t['y']) for t in g['tabs']}) == 1, f'{name}: вкладки в несколько рядов'
        assert g['navScroll'][0] <= g['navScroll'][1] + 1, f'{name}: панель вкладок прокручивается'
    elif mode == 'landscape':
        assert 'campMobilePlay' in ids and not g['footVisible'], f'{name}: «В игру» должна быть в рельсе'
        assert max(t['r'] for t in g['tabs']) - min(t['x'] for t in g['tabs']) <= 90 and min(t['x'] for t in g['tabs']) <= g['vw'] * 0.1, f'{name}: рельс не слева или шире 90 px'
        assert g['navScroll'][2] <= g['navScroll'][3] + 1, f'{name}: рельс прокручивается'
    else:
        assert 'campMobilePlay' not in ids and g['footVisible'], 'desktop: подвал «В игру» должен остаться'
    return g

with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    for name, width, height in VIEWS:
        touch = name != 'desktop'
        mode = 'desktop' if not touch else ('portrait' if height > width else 'landscape')
        context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=touch, has_touch=touch)
        page = context.new_page()
        page.set_default_timeout(60000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(URL, wait_until='load', timeout=90000)
        tap = (lambda loc: loc.tap()) if touch else (lambda loc: loc.click())
        tap(page.locator('#mNew'))
        tap(page.locator('#skip'))
        expect(page.locator('#hud')).to_be_visible()
        tap(page.locator('#bCamp'))
        page.wait_for_function('() => !!window.terraCampUI')
        page.evaluate("""() => { game.p.camp.rep = 1000;
          for (const id of ['qa-m1', 'qa-m2']) if (!game.camp.recruit({id}).ok) throw Error('Fixture recruitment failed'); }""")
        tap(page.locator('#campTabs [data-camp-tab="overview"]'))
        before = page.evaluate('JSON.stringify(game.p.camp)')
        for tab in TABS:
            tap(page.locator(f'#campTabs [data-camp-tab="{tab}"]'))
            page.wait_for_timeout(150)
            assert page.evaluate('game.ui.campPanel.tab') == tab, tab
            expect(page.locator(f'#campTabs [data-camp-tab="{tab}"]')).to_have_class('on')
            assert page.locator('#campTabs button.on').count() == 1, f'{name}/{tab}: несколько активных вкладок'
            page.locator('#campBody').evaluate('e => e.scrollTop = e.scrollHeight')
            check(page, name, tab, mode)
            if tab in ('settlers', 'defense'):
                page.locator('#campBody').evaluate('e => e.scrollTop = 0')
                page.screenshot(path=str(out / f'{name}-{tab}.png'))
            if tab == 'more':
                expect(page.locator('#campBody .campDestination[data-camp-tab="defense"]')).to_be_hidden()
            if tab == 'defense':
                expect(page.locator('#campBody .campSectionBack')).to_be_hidden()
        # Карточка жителя и раздел из «Ещё».
        tap(page.locator('#campTabs [data-camp-tab="settlers"]'))
        tap(page.locator('[data-resident="qa-m1"]'))
        check(page, name, 'resident', mode)
        tap(page.locator('#campTabs [data-camp-tab="more"]'))
        tap(page.locator('#campBody [data-camp-tab="contracts"]'))
        expect(page.locator('#campTabs [data-camp-tab="more"]')).to_have_class('on')
        check(page, name, 'contracts', mode)
        # Safe-area: вырез слева/справа и полоска жестов снизу.
        # Типичные значения iPhone: портрет — вырез сверху и полоска снизу, альбом — вырез сбоку.
        inset = {'portrait': ['10px', '10px', '47px', '34px'], 'landscape': ['47px', '47px', '8px', '21px'], 'desktop': ['24px', '24px', '24px', '24px']}[mode]
        page.evaluate("""(v) => { const s = document.documentElement.style;
          ['--sl', '--sr', '--st', '--sb'].forEach((n, i) => s.setProperty(n, v[i])); }""", inset)
        page.wait_for_timeout(100)
        check(page, name, 'safe-area', mode)
        if touch: page.screenshot(path=str(out / f'{name}-safe-area.png'))
        page.evaluate("() => { const s = document.documentElement.style; for (const n of ['--sl','--sr','--st','--sb']) s.removeProperty(n); }")
        # Точки встраивания для [defense] и других разделов.
        events = page.evaluate("""() => new Promise(resolve => {
          const seen = []; const panel = document.getElementById('campPanel');
          panel.addEventListener('terra:camp-tab', e => seen.push(e.detail.tab));
          const ok = terraCampUI.registerSection({id: 'qa-section', label: 'Тест', order: 5,
            render(container) { container.querySelector('.campSection__list').innerHTML =
              '<article class="campItemCard" data-tone="bad"><div class="campItemCard__icon"></div><div class="campItemCard__meta">' +
              '<b class="campItemCard__title">Турель</b><span class="campMeter" data-kind="hp" data-level="bad" style="--value:.2"><span></span><i></i><em>20%</em></span>' +
              '<span class="campStatusBadge" data-tone="bad">нужен ремонт</span></div>' +
              '<div class="campItemCard__actions"><button class="campInfoButton campButton">i</button><button class="campPrimaryAction campButton">Починить</button></div></article>'; } });
          terraCampUI.setBadge('defense', 2, 'bad');
          resolve({ok, sections: terraCampUI.sections(), seen});
        })""")
        assert events['ok'] and 'defense' in events['sections'] and 'qa-section' in events['sections'], events
        expect(page.locator('#campTabs [data-camp-tab="defense"] .campTabBadge')).to_have_text('2')
        in_tabs = page.locator('#campTabs [data-camp-tab="qa-section"]').count() == 1
        if not in_tabs:  # нет места во вкладках — раздел доступен карточкой в «Ещё»
            tap(page.locator('#campTabs [data-camp-tab="more"]'))
        tap(page.locator('#campTabs [data-camp-tab="qa-section"]' if in_tabs else '#campBody [data-camp-mobile="card"][data-camp-tab="qa-section"]'))
        expect(page.locator('#campBody .campSection[data-camp-section="qa-section"] .campItemCard')).to_be_visible()
        assert page.evaluate('terraCampUI.tab') == 'qa-section'
        g = check(page, name, 'custom-section', mode)
        active = [t['id'] for t in g['tabs'] if t['on']]
        assert active == ['qa-section' if in_tabs else 'more'], f'{name}: активная вкладка {active}'
        if touch: page.screenshot(path=str(out / f'{name}-custom-section.png'))
        page.evaluate("() => terraCampUI.openInfo('Турель', 'Прочность 20 %. Нужен лом.')")
        expect(page.locator('.campInfoSheet')).to_be_visible()
        check(page, name, 'info-sheet', mode)
        page.keyboard.press('Escape')
        expect(page.locator('.campInfoSheet')).to_have_count(0)
        expect(page.locator('#campPanel')).to_be_visible()
        tap(page.locator('#campTabs [data-camp-tab="overview"]'))
        expect(page.locator('#campBody .campSection[data-camp-section="qa-section"]')).to_have_count(0)
        assert page.evaluate('terraCampUI.tab') == 'overview'
        assert page.evaluate('JSON.stringify(game.p.camp)') == before, 'Навигация изменила camp state'
        # Возврат в игру тем же штатным путём.
        if touch: tap(page.locator('#campTabs .campMobilePlay'))
        else: page.locator('#campPanel .panelFoot [data-close]').click()
        expect(page.locator('#campPanel')).not_to_be_visible()
        assert page.evaluate('game.state') == 'play'
        assert not errors, errors
        print(f'PASS {name} {width}×{height}: цели ≥48, вкладки без обрезки/наложений, safe-area, «Оборона», terraCampUI, возврат в игру')
        context.close()
    browser.close()
    print('PASS: camp-mobile, 5 viewports; JavaScript errors: 0')
