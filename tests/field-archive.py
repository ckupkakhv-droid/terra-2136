"""Полевой архив: запись только после живого спуска, без нового поля сейва."""
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

OUT = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-field-archive'))
ART = Path('/opt/cursor/artifacts')
OUT.mkdir(parents=True, exist_ok=True)
ART.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
FORBIDDEN = ('Кольцевая', 'Эпицентр', 'Гагаринская')

def paths(value, prefix, found):
    if isinstance(value, dict):
        for key, item in value.items():
            child = prefix + '.' + key
            found.add(child)
            paths(item, child, found)
    elif isinstance(value, list):
        for item in value:
            paths(item, prefix + '[]', found)

def save_shape(page):
    raw = page.evaluate('localStorage.getItem("terra_save")')
    data = json.loads(raw)
    found = set()
    paths(data, 'save', found)
    player = data.get('p') or {}
    return {
        'raw': raw,
        'paths': found,
        'top': sorted(data.keys()),
        'player': sorted(player.keys()) if isinstance(player, dict) else [],
        'campV': (player.get('camp') or {}).get('v') if isinstance(player, dict) else None,
        'fieldCompanion': player.get('fieldCompanion') if isinstance(player, dict) else None,
        'notes': player.get('notes') if isinstance(player, dict) else None,
        'tps': player.get('tps') if isinstance(player, dict) else None,
        'domains': (player.get('dungeonContainers') or {}).get('domains') if isinstance(player, dict) else None,
    }

def open_archive(page):
    page.evaluate('game.ui.openInv("log")')
    page.wait_for_selector('#fieldArchiveOpen')
    page.locator('#fieldArchiveOpen').click()
    page.wait_for_selector('#fieldArchive:not(.hidden)')

def archive_text(page):
    return page.locator('#fieldArchiveBody').inner_text()

def layout(page):
    return page.evaluate('''() => {
      const sheet = document.querySelector('.fieldArchiveSheet');
      const close = document.getElementById('fieldArchiveClose');
      const body = document.getElementById('fieldArchiveBody');
      const open = document.getElementById('fieldArchiveOpen');
      const foot = document.querySelector('#inv footer');
      const tabs = document.querySelector('#inv .tabs');
      const box = element => element ? element.getBoundingClientRect() : null;
      const overlap = (a, b) => !!(a && b && a.left < b.right - 1 && a.right > b.left + 1 && a.top < b.bottom - 1 && a.bottom > b.top + 1);
      const openBox = box(open), footBox = box(foot), tabBox = box(tabs), sheetBox = box(sheet), closeBox = box(close), bodyBox = box(body);
      return {
        sheetOverflow: !!(sheet && sheet.scrollWidth > sheet.clientWidth + 1),
        bodyOverflow: !!(body && body.scrollWidth > body.clientWidth + 1),
        cardOverflow: [...document.querySelectorAll('.fieldArchiveCard, .fieldArchiveEmpty, .fieldArchiveLimit')].filter(element => element.scrollWidth > element.clientWidth + 1).map(element => element.innerText.slice(0, 80)),
        closeInside: !!(closeBox && sheetBox && closeBox.top >= 0 && closeBox.bottom <= innerHeight + 1 && closeBox.left >= 0 && closeBox.right <= innerWidth + 1),
        closeSize: !!(closeBox && closeBox.width >= 43 && closeBox.height >= 43),
        closeOverCard: overlap(closeBox, bodyBox),
        openOverFoot: overlap(openBox, footBox),
        openOverTabs: overlap(openBox, tabBox),
        openSize: !!(openBox && openBox.height >= 43),
      };
    }''')

def descend(page, entry):
    started = page.evaluate('''(entry) => {
      const ent = game.world.ents.find(item => item.kind === entry.kind && item.x === entry.x && item.z === entry.z && item.name === entry.name);
      game.p.hp = game.p.maxHp = 10000;
      game.p.x = ent.x; game.p.z = ent.z + 0.4; game.camT = null;
      const ok = game.useEntrance(ent);
      return {ok, transition: !!game.dungeonTransition, state: game.state};
    }''', entry)
    assert started['ok'], started
    page.wait_for_function('game.dg && game.world.inDungeon && !game.dungeonTransition', timeout=90000)
    page.wait_for_timeout(400)
    inside = page.evaluate('''() => ({
      key: game.dg.key, name: game.dg.name, theme: game.dg.theme, sewer: !!game.dg.sewer,
      banner: document.querySelector("#banner small")?.textContent || "",
      exit: (game.world.ents || []).find(item => item.kind === "exit")?.name || "",
      pos: {x: game.p.x, z: game.p.z},
    })''')
    left = page.evaluate('''() => {
      const exit = (game.world.ents || []).find(item => item.kind === "exit");
      game.p.hp = game.p.maxHp = 10000;
      if (exit) { game.p.x = exit.x; game.p.z = exit.z + 0.4; game.camT = null; }
      const near = game.nearInteract?.();
      const used = exit ? game.useEntrance(exit) : false;
      return {used, exit: exit?.name || "", near: near?.label || near?.k || null};
    }''')
    assert left['used'], left
    page.wait_for_function('!game.dg && !game.world.inDungeon && !game.dungeonTransition', timeout=90000)
    return {'inside': inside, 'left': left}

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/local/bin/google-chrome', headless=True,
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.set_default_timeout(120000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL, timeout=120000)
    page.evaluate('localStorage.clear()')
    page.reload(timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game.sewers && game.state==="play" && document.getElementById("fieldArchive")', timeout=120000)
    page.wait_for_function("game.world.ents.some(e=>e.kind==='metro'&&!e.sewer)", timeout=120000)

    open_archive(page)
    before = archive_text(page)
    assert 'спусков ещё нет' in before, before
    assert all(word not in before for word in FORBIDDEN), before
    page.screenshot(path=str(ART / 'field-archive-before.png'))
    page.keyboard.press('Escape')
    page.locator('#fieldArchive').wait_for(state='hidden')
    assert page.locator('#inv').is_visible()
    page.evaluate('game.ui.closeAll()')

    metro = page.evaluate('''() => {
      const ent = game.world.ents.find(item => item.kind === "metro" && !item.sewer);
      return {x: ent.x, z: ent.z, name: ent.name, kind: ent.kind};
    }''')
    first = descend(page, metro)
    open_archive(page)
    after_metro = archive_text(page)
    cards = page.locator('.fieldArchiveCard').count()
    assert cards == 1, after_metro
    assert first['inside']['name'] in after_metro, (first, after_metro)
    assert first['inside']['key'] in after_metro, (first, after_metro)
    assert first['inside']['exit'] in after_metro and first['inside']['exit'] == 'Выход в город', (first, after_metro)
    assert first['inside']['banner'] and first['inside']['banner'] in after_metro, (first, after_metro)
    assert 'ур..' not in after_metro and 'город..' not in after_metro, after_metro
    assert all(word not in after_metro for word in FORBIDDEN), after_metro
    page.screenshot(path=str(ART / 'field-archive-metro.png'))
    page.keyboard.press('Escape')
    page.evaluate('game.ui.closeAll()')

    again = descend(page, metro)
    open_archive(page)
    assert page.locator('.fieldArchiveCard').count() == 1, archive_text(page)
    page.keyboard.press('Escape')
    page.evaluate('game.ui.closeAll()')

    collector = page.evaluate('''() => {
      const ent = game.world.ents.find(item => item.sewer);
      return {x: ent.x, z: ent.z, name: ent.name, kind: ent.kind};
    }''')
    second = descend(page, collector)
    page.evaluate('''() => { game.p.hp = game.p.maxHp = 10000; game.p.x = 90; game.p.z = -60; game.camT = null; }''')
    gagarin = None
    try:
        page.wait_for_function('''() => {
          game.p.hp = game.p.maxHp = 10000;
          if (!game.world.inDungeon) { game.p.x = 90; game.p.z = -60; game.camT = null; }
          return game.world.ents.some(item => item.kind === "metro" && !item.sewer && String(item.name).includes("Гагаринская"));
        }''', timeout=40000)
        gagarin_entry = page.evaluate('''() => {
          const ent = game.world.ents.find(item => item.kind === "metro" && String(item.name).includes("Гагаринская"));
          return {x: ent.x, z: ent.z, name: ent.name, kind: ent.kind};
        }''')
        gagarin = descend(page, gagarin_entry)
    except Exception as error:
        gagarin = {'error': str(error)}

    page.evaluate('window.__archiveLoop = game.loop; game.loop = () => {}; game.save()')
    before_sheet = save_shape(page)
    open_archive(page)
    final_text = archive_text(page)
    final_cards = page.locator('.fieldArchiveCard')
    count = final_cards.count()
    assert count >= 2, (count, final_text, gagarin)
    assert count <= 5, final_text
    assert second['inside']['name'] in final_text, (second, final_text)
    assert second['inside']['exit'] == 'Лестница на поверхность' and second['inside']['exit'] in final_text, (second, final_text)
    assert 'Кольцевая' not in final_text and 'Эпицентр' not in final_text, final_text
    if gagarin and gagarin.get('inside'):
        assert 'Гагаринская' in final_text, (gagarin, final_text)
        assert count == 3, (count, final_text)
    else:
        assert 'Гагаринская' not in final_text, final_text
    page.screenshot(path=str(ART / 'field-archive-records.png'))
    desk = layout(page)
    assert not desk['sheetOverflow'] and not desk['bodyOverflow'] and not desk['cardOverflow'], (desk, final_text)
    assert desk['closeInside'] and desk['closeSize'] and not desk['closeOverCard'], desk
    page.keyboard.press('Escape')
    page.locator('#fieldArchive').wait_for(state='hidden')
    assert 'hidden' not in (page.locator('#inv').get_attribute('class') or '')
    page.evaluate('game.save()')
    after_sheet = save_shape(page)
    page.evaluate('game.loop = window.__archiveLoop; null')
    assert before_sheet['player'] == after_sheet['player'], (before_sheet['player'], after_sheet['player'])
    assert not any('archive' in item.lower() or item.endswith('.visits') for item in after_sheet['paths'] - before_sheet['paths'])
    assert 'Полевой архив' not in after_sheet['raw'] and 'fieldArchive' not in after_sheet['raw'] and 'Выход в город' not in after_sheet['raw']
    assert before_sheet['campV'] == after_sheet['campV']
    assert before_sheet['fieldCompanion'] == after_sheet['fieldCompanion']
    assert before_sheet['notes'] == after_sheet['notes']

    for name, width, height in (('narrow', 320, 568), ('phone', 390, 844)):
        page.set_viewport_size({'width': width, 'height': height})
        page.locator('#fieldArchiveOpen').scroll_into_view_if_needed()
        page.locator('#fieldArchiveOpen').click()
        page.wait_for_selector('#fieldArchive:not(.hidden)')
        page.wait_for_timeout(50)
        page.locator('#fieldArchiveBody').evaluate('element => element.scrollTop = 0')
        fit = layout(page)
        assert not fit['sheetOverflow'] and not fit['bodyOverflow'] and not fit['cardOverflow'], (name, fit, final_text)
        assert fit['closeInside'] and fit['closeSize'] and not fit['closeOverCard'], (name, fit)
        page.screenshot(path=str(ART / f'field-archive-{name}.png'))
        page.locator('#fieldArchiveClose').focus()
        page.keyboard.press('Escape')
        page.locator('#fieldArchive').wait_for(state='hidden')
        page.locator('#invBody').evaluate('element => element.scrollTop = 0')
        fit_closed = layout(page)
        assert not fit_closed['openOverFoot'] and not fit_closed['openOverTabs'] and fit_closed['openSize'], (name, fit_closed)

    page.evaluate('game.ui.closeAll()')
    page.reload(timeout=120000)
    page.locator('#mContinue').click()
    page.wait_for_function('game.state==="play" && game.sewers && document.getElementById("fieldArchive")', timeout=120000)
    open_archive(page)
    loaded = archive_text(page)
    assert metro['name'] in loaded and '90,84' in loaded and 'Выход в город' in loaded, loaded
    assert 'Канализация' in loaded and 'Лестница на поверхность' in loaded, loaded
    assert 'Редкое логово' not in loaded and 'Кольцевая' not in loaded and 'Эпицентр' not in loaded, loaded
    if gagarin and gagarin.get('inside'):
        assert 'Гагаринская' in loaded, loaded
    page.screenshot(path=str(ART / 'field-archive-after-load.png'))
    assert not errors, errors

    report = {
        'metro': first, 'repeatExit': again['left']['exit'], 'collector': second, 'gagarin': gagarin,
        'cards': count, 'text': final_text, 'before': before, 'desktop': desk,
        'savePathsSame': True, 'campV': after_sheet['campV'], 'notes': after_sheet['notes'],
        'tps': after_sheet['tps'], 'domains': after_sheet['domains'], 'loaded': loaded, 'errors': errors,
    }
    (ART / 'field-archive-visits.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('PASS', count, 'cards', 'gagarin' if gagarin and gagarin.get('inside') else 'no-gagarin', flush=True)
    browser.close()
