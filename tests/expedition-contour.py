"""Один прогон контура: меню, HUD и обложка лагеря на нескольких окнах."""
from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright, expect

OUT = Path(os.environ.get('TERRA_QA_OUTPUT', 'docs/ui/expedition-contour'))
OUT.mkdir(parents=True, exist_ok=True)
CHROMIUM = os.environ.get('TERRA_CHROMIUM') or '/usr/local/bin/google-chrome'
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
VIEWPORTS = [(1440, 900), (390, 844), (844, 390), (320, 568), (360, 640)]
BACKUP = {
    'mExportCrystalCopies': 'ЭКСПОРТ РЕЗЕРВНОЙ КОПИИ',
    'mRestoreCrystalCopy': 'ВОССТАНОВИТЬ КОПИЮ',
    'mImportSave': 'ИМПОРТ СЕЙВА (JSON)',
    'mExportSave': 'СКАЧАТЬ ЗАПИСАННЫЙ СЕЙВ (JSON)',
}

def box(page, selector):
    return page.locator(selector).first.evaluate('''(el) => {
      const r = el.getBoundingClientRect();
      const s = getComputedStyle(el);
      return {w: r.width, h: r.height, l: r.left, t: r.top, r: r.right, b: r.bottom,
        size: parseFloat(s.fontSize), text: (el.innerText || el.textContent || '').replace(/\\s+/g, ' ').trim()};
    }''')

def overlaps(a, b):
    if a['w'] < 1 or b['w'] < 1 or a['h'] < 1 or b['h'] < 1:
        return False
    return a['l'] < b['r'] - 1 and a['r'] > b['l'] + 1 and a['t'] < b['b'] - 1 and a['b'] > b['t'] + 1

def no_horizontal_overflow(page):
    return page.evaluate('() => document.documentElement.scrollWidth <= innerWidth + 1')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=CHROMIUM, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    context = browser.new_context(viewport={'width': 1440, 'height': 900}, has_touch=True, reduced_motion='reduce')
    page = context.new_page()
    page.set_default_timeout(90000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.add_init_script('''(() => {
      const orig = localStorage.setItem.bind(localStorage);
      const keys = [];
      localStorage.setItem = (key, value) => { keys.push(key); return orig(key, value); };
      window.__terraStorageKeys = keys;
    })();''')
    page.goto(URL, wait_until='load', timeout=120000)
    page.wait_for_selector('#menu.contourMenu', timeout=120000)
    page.wait_for_function('''() => document.getElementById("mExportSave")?.parentElement?.id === "menuFieldTools"''')
    assert page.locator('#menuFieldTools').evaluate('el => !el.open')
    assert page.locator('#mNew').evaluate('el => el.classList.contains("expeditionPrimary")')
    for bid, label in BACKUP.items():
        button = page.locator('#' + bid)
        expect(button).to_have_text(label)
        assert button.evaluate('el => el.parentElement.id === "menuFieldTools"')
        assert button.evaluate('el => typeof el.onclick === "function"')
    storage_before = page.evaluate('() => ({keys: Object.keys(localStorage), calls: window.__terraStorageKeys.slice()})')

    menu_report = []
    for width, height in VIEWPORTS:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(150)
        name = f'{width}x{height}'
        assert no_horizontal_overflow(page), name
        for selector in ['#mNew', '#mSettings', '#mHelp', '#menuFieldTools > summary']:
            hit = box(page, selector)
            assert hit['h'] >= 44 and hit['w'] >= 44, (name, selector, hit)
            assert hit['text'] and hit['size'] >= 13, (name, selector, hit)
        scroller = page.locator('#menu .mbtns')
        metrics = scroller.evaluate('''(el) => {
          el.scrollTop = el.scrollHeight;
          const nodes = [...el.querySelectorAll("button, summary")];
          const edge = el.getBoundingClientRect().bottom + 1;
          const clipped = nodes.filter(node => node.getBoundingClientRect().bottom > edge + el.clientHeight);
          return {top: el.scrollTop, max: el.scrollHeight - el.clientHeight, overflow: document.documentElement.scrollWidth > innerWidth + 1};
        }''')
        assert metrics['top'] + 2 >= metrics['max'] and not metrics['overflow'], (name, metrics)
        page.screenshot(path=str(OUT / f'after-menu-{name}.png'))
        menu_report.append(name)
    page.set_viewport_size({'width': 320, 'height': 568})
    page.locator('#menuFieldTools > summary').click()
    expect(page.locator('#menuFieldTools')).to_have_js_property('open', True)
    for bid in BACKUP:
        expect(page.locator('#' + bid)).to_be_visible()
    page.locator('#mExportSave').scroll_into_view_if_needed()
    reached = page.evaluate('''() => {
      const scroller = document.querySelector("#menu .mbtns");
      const button = document.getElementById("mExportSave");
      const area = scroller.getBoundingClientRect();
      const rect = button.getBoundingClientRect();
      return rect.height >= 44 && rect.top >= area.top - 1 && rect.bottom <= area.bottom + 1 && rect.right <= innerWidth + 1;
    }''')
    assert reached, 'backup command is outside the menu scroller'
    page.screenshot(path=str(OUT / 'after-menu-tools-320x568.png'))
    page.locator('#menuFieldTools > summary').click()
    assert page.evaluate('() => !document.getElementById("menuFieldTools").open && !localStorage.getItem("menuFieldTools")')

    page.set_viewport_size({'width': 1440, 'height': 900})
    page.locator('#mNew').click()
    page.locator('#skip').click()
    expect(page.locator('#hud.contourHud')).to_be_visible()
    page.wait_for_function('''() => document.getElementById("hpt").textContent.includes("/") && document.getElementById("zone").textContent.trim().length > 0''')
    save_before = page.evaluate('''() => {
      const raw = localStorage.getItem("terra_save");
      const walk = (value, path, depth, acc) => {
        if (!value || typeof value !== "object" || depth > 2) return;
        for (const key of Object.keys(value)) acc.push(path + key);
        if (depth < 2) for (const key of Object.keys(value)) walk(value[key], path + key + ".", depth + 1, acc);
      };
      const keys = [];
      if (raw) walk(JSON.parse(raw), "", 0, keys);
      return {raw: raw || "", keys};
    }''')
    hud_sample = page.evaluate('''() => ({
      hp: document.getElementById("hpt").textContent,
      food: document.getElementById("food").innerText,
      water: document.getElementById("water").innerText,
      clock: document.getElementById("clock").innerText,
      bag: document.getElementById("dropN_bag").textContent,
      obj: document.getElementById("objT").textContent,
      zone: document.getElementById("zone").innerText,
      weapon: document.getElementById("wName").innerText,
      ammo: document.getElementById("wAmmo").innerText,
      sta: document.querySelector(".bar.st").getAttribute("aria-label"),
      xp: document.querySelector(".bar.xp").getAttribute("aria-label"),
      pulse: document.getElementById("evPulse")?.getAttribute("aria-label") || ""
    })''')
    assert hud_sample['sta'] == 'Выносливость' and hud_sample['xp'] == 'Опыт'
    assert hud_sample['hp'] and hud_sample['food'] and hud_sample['water'] and hud_sample['bag'] and hud_sample['obj'] and hud_sample['zone']

    motion = page.evaluate('''() => ({
      logo: getComputedStyle(document.querySelector("#menu .logo")).transitionDuration,
      bar: getComputedStyle(document.querySelector("#tl .bar i")).transitionDuration,
      camp: getComputedStyle(document.querySelector("#campPanel") || document.body).transitionDuration
    })''')
    # Лагерь ещё скрыт, панель может не быть создана. Ноль проверяем на меню и полосе HUD.
    assert motion['logo'] == '0s' and motion['bar'] == '0s', motion

    hud_report = []
    for width, height in VIEWPORTS:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(200)
        name = f'{width}x{height}'
        assert no_horizontal_overflow(page), name
        for selector, minimum in [('#hpt', 14), ('#food', 14), ('#objT', 14), ('#dropHud', 12), ('#zone', 12), ('#wName', 14)]:
            sample = box(page, selector)
            assert sample['text'] and sample['size'] >= minimum, (name, selector, sample)
        for selector in ['#bCamp', '#bMap', '#bPause', '#objectiveToggle', '#lvlW']:
            hit = box(page, selector)
            assert hit['h'] >= 44 and hit['w'] >= 44, (name, selector, hit)
        pulse = page.locator('#evPulse')
        if pulse.count() and pulse.is_visible():
            hit = box(page, '#evPulse')
            assert hit['h'] >= 44 and hit['w'] >= 44, (name, hit)
        zone, buttons, minimap, objective = box(page, '#zone'), box(page, '#topBtns'), box(page, '#mmW'), box(page, '#obj')
        assert not overlaps(buttons, zone), (name, buttons, zone)
        assert not overlaps(buttons, minimap), (name, buttons, minimap)
        assert not overlaps(buttons, objective), (name, buttons, objective)
        touch_hits = page.evaluate('''() => {
          const zone = document.getElementById("zone").getBoundingClientRect();
          return [...document.querySelectorAll("#touch button, #actBar .ab")].filter(el => {
            const r = el.getBoundingClientRect();
            return r.width > 1 && zone.left < r.right - 1 && zone.right > r.left + 1 && zone.top < r.bottom - 1 && zone.bottom > r.top + 1;
          }).map(el => el.id || el.className);
        }''')
        assert not touch_hits, (name, touch_hits)
        page.screenshot(path=str(OUT / f'after-hud-{name}.png'))
        hud_report.append(name)

    page.set_viewport_size({'width': 1440, 'height': 900})
    page.locator('#bCamp').focus()
    page.keyboard.press('Enter')
    expect(page.locator('#campPanel')).to_be_visible()
    page.wait_for_selector('#campPanel .fbFolder')
    reason = page.evaluate('''() => {
      const button = document.querySelector("[data-supply-assign]");
      const note = document.getElementById("contourSupplyReason");
      return {disabled: !!button?.disabled, title: button?.title || "", note: note?.innerText || "", pause: document.querySelector(".fbPauseInfo")?.innerText || ""};
    }''')
    if reason['disabled'] and reason['title'] and reason['title'] not in page.locator('[data-supply-assign]').inner_text():
        assert reason['note'] == reason['title'], reason
    assert reason['pause'] == 'Пауза'
    shown = page.evaluate('''() => {
      const note = document.getElementById("contourSupplyReason");
      if (!note) return null;
      const r = note.getBoundingClientRect();
      const s = getComputedStyle(note);
      return {h: r.height, display: s.display, text: note.textContent};
    }''')
    assert shown and shown['display'] != 'none' and shown['h'] >= 12 and shown['text'] == reason['title'], shown
    for width, height in VIEWPORTS:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(200)
        name = f'{width}x{height}'
        assert no_horizontal_overflow(page), name
        for selector in ['#campPanel .fbPauseInfo', '#campPanel .panelFoot [data-close]', '#campPanel [data-supply-assign]']:
            hit = box(page, selector)
            assert hit['h'] >= 44 and hit['text'], (name, selector, hit)
        page.screenshot(path=str(OUT / f'after-camp-{name}.png'))

    page.locator('#campPanel .fbPauseInfo').focus()
    before_tab = page.evaluate('() => document.activeElement.className')
    page.keyboard.press('Tab')
    after_tab = page.evaluate('() => document.activeElement?.closest("#campPanel") ? document.activeElement.className : ""')
    assert after_tab and after_tab != before_tab
    page.locator('#campPanel .fbPauseInfo').focus()
    page.keyboard.press('Space')
    expect(page.locator('#campPanel .campInfoSheet')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#campPanel .campInfoSheet')).to_be_hidden()
    expect(page.locator('#campPanel')).to_be_visible()
    page.keyboard.press('Escape')
    expect(page.locator('#campPanel')).to_be_hidden()
    expect(page.locator('#bCamp')).to_be_focused()
    assert page.evaluate('() => window.game.state === "play"')

    save_after = page.evaluate('''() => {
      const raw = localStorage.getItem("terra_save");
      const walk = (value, path, depth, acc) => {
        if (!value || typeof value !== "object" || depth > 2) return;
        for (const key of Object.keys(value)) acc.push(path + key);
        if (depth < 2) for (const key of Object.keys(value)) walk(value[key], path + key + ".", depth + 1, acc);
      };
      const keys = [];
      if (raw) walk(JSON.parse(raw), "", 0, keys);
      return {keys, calls: window.__terraStorageKeys.filter(key => /contour|fieldTools/i.test(key))};
    }''')
    assert save_before['keys'] == save_after['keys'], sorted(set(save_after['keys']) - set(save_before['keys']))
    assert save_after['calls'] == []
    assert not errors, errors
    report = {
        'viewports': [f'{w}x{h}' for w, h in VIEWPORTS],
        'menu': menu_report,
        'hud': hud_sample,
        'motion': motion,
        'supply': reason,
        'saveKeysSame': True,
        'errors': errors,
    }
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS', json.dumps(hud_sample, ensure_ascii=False), reason)
    browser.close()
