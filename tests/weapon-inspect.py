"""Осмотр конкретного ствола в штатном рюкзаке. Chrome/SwiftShader.
Сервер уже поднят. Адрес: TERRA_TEST_URL (по умолчанию http://127.0.0.1:8080/play/).
Кадры и отчёт: TERRA_QA_OUTPUT или /opt/cursor/artifacts.
"""
from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/opt/cursor/artifacts'))
out.mkdir(parents=True, exist_ok=True)
chrome = os.environ.get('TERRA_CHROMIUM', '/usr/local/bin/google-chrome')
url = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
offline = 'terra.html' in url
external_ui = []

SNAP = '''() => {
  const raw = localStorage.getItem('terra_save');
  let save = null;
  try { save = JSON.parse(raw); } catch (e) { save = {parse: false}; }
  const weapons = (game.p.weapons || []).map(w => JSON.parse(JSON.stringify(w)));
  return {
    raw,
    top: save && typeof save === 'object' ? Object.keys(save).sort() : [],
    version: save && (save.v ?? save.ver ?? null),
    weaponKeys: weapons[0] ? Object.keys(weapons[0]).sort() : [],
    weapons,
    eq: (game.p.eq || []).map(w => w && w.uid),
    campV: game.p.camp && game.p.camp.v,
  };
}'''

CARD = '''(uid) => {
  const item = game.p.weapons.find(w => w.uid === uid);
  const st = game.wstat(item);
  const card = document.getElementById('weaponInspect');
  const tile = document.querySelector('.tile[data-w="' + uid + '"]');
  const det = document.querySelector('.invDetail .det');
  const affixes = det ? [...det.querySelectorAll('span[title]')].map(s => s.textContent) : [];
  const text = (sel) => card.querySelector(sel).textContent;
  const box = card.getBoundingClientRect();
  const x = document.querySelector('#inv .x').getBoundingClientRect();
  const play = document.querySelector('#inv footer [data-close="inv"]').getBoundingClientRect();
  const win = document.querySelector('#inv .win').getBoundingClientRect();
  const owner = (rect) => {
    const node = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
    if (!node) return 'none';
    if (node.closest('#weaponInspect')) return 'card';
    if (node.closest('#inv .x')) return 'x';
    if (node.closest('[data-close="inv"]')) return 'play';
    return node.className || node.tagName;
  };
  return {
    uid: card.dataset.weaponUid,
    wt: card.dataset.weaponWt,
    name: text('[data-wi="name"]'),
    type: text('[data-wi="type"]'),
    state: text('[data-wi="state"]'),
    account: text('[data-wi="uid"]'),
    scheme: card.querySelector('figcaption').textContent,
    dmg: text('[data-wi="dmg"]'),
    speed: text('[data-wi="speed"]'),
    crit: text('[data-wi="crit"]'),
    extra: {
      mag: card.querySelector('[data-wi="mag"]')?.textContent || null,
      reload: card.querySelector('[data-wi="reload"]')?.textContent || null,
      reach: card.querySelector('[data-wi="reach"]')?.textContent || null,
      arc: card.querySelector('[data-wi="arc"]')?.textContent || null,
      pellets: st.pellets,
    },
    aff: card.querySelector('[data-wi="aff"]').textContent,
    affHidden: card.querySelector('[data-wi="aff"]').hidden,
    acts: [...card.querySelectorAll('[data-act]')].map(b => ({act: b.dataset.act, text: b.textContent, disabled: b.disabled})),
    expect: {
      name: game.wname(item),
      nm: item.nm,
      wt: item.wt,
      e: item.e,
      g: item.g,
      r: item.r,
      mag: item.mag,
      lock: !!item.lock,
      dmg: Math.round(st.dmg) + (st.pellets > 1 ? ' ×' + st.pellets : ''),
      speed: (st.rate > 0 ? (1 / st.rate).toFixed(1) : '—') + '/с',
      crit: Math.round((st.crit || 0) * 100) + '%',
      cap: String(st.mag),
      reload: Number(st.reload).toFixed(1) + ' с',
      stat: {dmg: st.dmg, rate: st.rate, crit: st.crit, mag: st.mag, reload: st.reload, reach: st.reach, arc: st.arc, ml: st.ml, pellets: st.pellets},
    },
    tile: tile ? {nm: tile.querySelector('.nm')?.textContent || '', aria: tile.getAttribute('aria-label'), text: tile.innerText} : null,
    detailHasDmg: det ? det.textContent.includes(String(Math.round(st.dmg))) : false,
    affixes,
    bounds: {
      card: {x: box.x, y: box.y, w: box.width, h: box.height},
      close: {x: x.x, y: x.y, w: x.width, h: x.height},
      play: {x: play.x, y: play.y, w: play.width, h: play.height},
      win: {w: win.width, h: win.height},
      pointOnClose: owner(x),
      pointOnPlay: owner(play),
      winOverflow: document.querySelector('#inv .win').scrollWidth - document.querySelector('#inv .win').clientWidth,
      bodyOverflow: document.getElementById('invBody').scrollWidth - document.getElementById('invBody').clientWidth,
    },
    focus: document.activeElement && (document.activeElement.className || document.activeElement.id || document.activeElement.tagName),
  };
}'''


def shot(page, name):
    page.mouse.move(8, 8)
    page.evaluate('''() => { const tip = document.getElementById('bpTip'); if (tip) tip.hidden = true; }''')
    page.locator('#weaponInspect').scroll_into_view_if_needed()
    page.screenshot(path=str(out / name))


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chrome, args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
        '--ignore-gpu-blocklist', '--disable-dev-shm-usage',
    ])
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('request', lambda req: external_ui.append(req.url) if '/ui/' in req.url else None)
    page.goto(url, wait_until='domcontentloaded', timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    expect(page.locator('#hud')).to_be_visible()
    page.keyboard.press('KeyI')
    expect(page.locator('#inv')).to_be_visible()
    made = page.evaluate('''() => {
      for (let i = 0; i < 4; i++) game.addWeapon(game.makeWeapon('stick', 0, 0), false, true);
      const rifle = game.makeWeapon('rifle', 1, 2);
      const shotgun = game.makeWeapon('shotgun', 0, 1);
      const blade = game.makeWeapon('machete', 2, 4);
      rifle.nm = '«АК-2136»';
      shotgun.nm = '«ТОЗ-34»';
      blade.nm = '«Сердце кристалла»';
      game.addWeapon(rifle, false, true);
      game.addWeapon(shotgun, false, true);
      game.addWeapon(blade, false, true);
      game.ui.renderInv();
      const eq = game.p.eq.map(w => w && w.uid);
      return {
        rifle: rifle.uid, shotgun: shotgun.uid, blade: blade.uid,
        eq,
        free: [rifle.uid, shotgun.uid, blade.uid].every(id => !eq.includes(id)),
      };
    }''')
    assert made['free'], made
    before = page.evaluate(SNAP)
    clicks = []

    def open_uid(uid):
        page.locator(f'.tile[data-w="{uid}"]').click()
        clicks.append({'click': f'.tile[data-w="{uid}"]', 'uid': uid})
        page.wait_for_selector(f'#weaponInspect[data-weapon-uid="{uid}"]')
        page.wait_for_function('''() => document.activeElement && document.activeElement.classList.contains('wi-close')''')

    def read(uid):
        data = page.evaluate(CARD, uid)
        assert data['name'] == data['expect']['name'], data['name']
        assert data['expect']['nm'] in data['name']
        assert data['uid'] == str(uid)
        assert data['wt'] == data['expect']['wt']
        assert data['scheme'] == 'схема'
        assert data['type'].startswith('Тип: ')
        assert data['dmg'] == data['expect']['dmg']
        assert data['speed'] == data['expect']['speed']
        assert data['crit'] == data['expect']['crit']
        assert data['account'] == 'Учёт № ' + str(uid)
        assert 'заточка +' + str(data['expect']['e']) in data['state']
        assert 'в рюкзаке' in data['state']
        assert data['detailHasDmg']
        if data['expect']['wt'] in ('rifle', 'shotgun', 'revolver', 'railgun'):
            assert data['extra']['mag'] == data['expect']['cap']
            assert data['extra']['reload'] == data['expect']['reload']
            assert 'патроны ' + str(data['expect']['mag']) in data['state']
        for line in data['affixes']:
            assert line in data['aff'] or data['affHidden'] and not line
        if data['tile']:
            assert data['tile']['nm'] != data['name']
            assert data['tile']['nm'] in data['name']
            assert data['name'] in (data['tile']['aria'] or '')
        assert data['bounds']['pointOnClose'] != 'card', data['bounds']
        assert data['bounds']['pointOnPlay'] != 'card', data['bounds']
        assert data['bounds']['winOverflow'] <= 1, data['bounds']
        assert data['bounds']['bodyOverflow'] <= 1, data['bounds']
        assert any(act['act'].startswith('slot') for act in data['acts']), data['acts']
        return data

    open_uid(made['rifle'])
    rifle = read(made['rifle'])
    shot(page, 'weapon-card-rifle-1440.png')
    nxt = page.locator('#invBody [data-inv-step="1"]')
    target = int(nxt.get_attribute('data-inv-to'))
    assert target == made['shotgun'], (target, made)
    nxt.click()
    clicks.append({'click': '[data-inv-step="1"]', 'uid': target})
    page.wait_for_selector(f'#weaponInspect[data-weapon-uid="{target}"]')
    second = read(target)
    assert second['name'] != rifle['name']
    assert second['dmg'] != rifle['dmg'] or second['expect']['wt'] != rifle['expect']['wt']

    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(200)
    second_bounds = read(target)
    shot(page, 'weapon-card-shotgun-390.png')

    page.locator('#weaponInspect .wi-close').click()
    clicks.append({'click': '.wi-close'})
    expect(page.locator('#weaponInspect')).to_have_count(0)
    expect(page.locator('.invDetail')).to_be_visible()
    mid = page.evaluate(SNAP)
    assert mid['raw'] == before['raw']
    assert mid['weapons'] == before['weapons']
    assert mid['eq'] == before['eq']
    assert mid['top'] == before['top']
    assert mid['weaponKeys'] == before['weaponKeys']

    page.keyboard.press('Escape')
    clicks.append({'key': 'Escape', 'afterClose': 'back-to-list'})
    expect(page.locator('#invBody')).not_to_have_class('showDetail')
    expect(page.locator('#weaponInspect')).to_have_count(0)

    page.set_viewport_size({'width': 320, 'height': 568})
    page.wait_for_timeout(150)
    open_uid(made['blade'])
    blade = read(made['blade'])
    assert '«Сердце кристалла»' in blade['name']
    assert len(blade['name']) > 20
    shot(page, 'weapon-card-long-320.png')
    focused = page.evaluate('''() => {
      const card = document.getElementById('weaponInspect');
      const close = document.activeElement;
      const inside = card.contains(close);
      close.blur();
      card.querySelector('.wi-close').focus();
      return {inside, tag: document.activeElement.className};
    }''')
    assert focused['inside'] and 'wi-close' in focused['tag']
    page.keyboard.press('Tab')
    tabbed = page.evaluate('''() => {
      const inv = document.getElementById('inv');
      const el = document.activeElement;
      return {inInv: inv.contains(el), text: (el.innerText || el.getAttribute('aria-label') || '').slice(0, 80)};
    }''')
    assert tabbed['inInv'], tabbed
    clicks.append({'key': 'Tab', 'focus': tabbed['text']})
    page.keyboard.press('Escape')
    clicks.append({'key': 'Escape', 'expect': 'card-closed-detail-open'})
    expect(page.locator('#weaponInspect')).to_have_count(0)
    expect(page.locator('.invDetail')).to_be_visible()
    expect(page.locator('[data-inv-back]')).to_be_focused()
    after_keys = page.evaluate(SNAP)
    assert after_keys['raw'] == before['raw']
    assert after_keys['weapons'] == before['weapons']
    assert after_keys['eq'] == before['eq']
    assert after_keys['campV'] == before['campV']

    page.keyboard.press('Escape')
    clicks.append({'key': 'Escape', 'expect': 'list'})
    expect(page.locator('#invBody.showDetail')).to_have_count(0)
    open_uid(made['rifle'])
    page.locator('#weaponInspect [data-act="slot0"]').click()
    clicks.append({'click': '#weaponInspect [data-act="slot0"]', 'uid': made['rifle']})
    page.wait_for_function('''(uid) => game.p.eq[0] && game.p.eq[0].uid === uid''', arg=made['rifle'])
    page.keyboard.press('Escape')
    page.keyboard.press('Escape')
    expect(page.locator('#invBody.showDetail')).to_have_count(0)
    open_uid(made['shotgun'])
    page.locator('#weaponInspect [data-act="slot0"]').click()
    clicks.append({'click': '#weaponInspect [data-act="slot0"]', 'uid': made['shotgun']})
    page.wait_for_function('''(uid) => game.p.eq[0] && game.p.eq[0].uid === uid''', arg=made['shotgun'])
    equipped = page.evaluate(SNAP)
    assert equipped['weapons'] == before['weapons']
    assert equipped['weaponKeys'] == before['weaponKeys']
    assert equipped['top'] == before['top']
    assert equipped['eq'][0] == made['shotgun']
    assert made['rifle'] not in equipped['eq']
    assert not errors, errors
    if offline:
        assert not external_ui, external_ui

    # Плитки списка по-прежнему без клейма: это исходный пробел, карточка его не подменяет.
    page.keyboard.press('Escape')
    page.keyboard.press('Escape')
    tiles = page.evaluate('''(ids) => ids.map(id => {
      const tile = document.querySelector('.tile[data-w="' + id + '"]');
      const item = game.p.weapons.find(w => w.uid === id);
      return {uid: id, tile: tile && tile.querySelector('.nm').textContent, wname: game.wname(item)};
    })''', [made['rifle'], made['shotgun']])
    page.set_viewport_size({'width': 320, 'height': 568})
    page.locator(f'.tile[data-w="{made["rifle"]}"]').scroll_into_view_if_needed()
    page.screenshot(path=str(out / 'weapon-tiles-320.png'))

    report = {
        'url': url,
        'offline': offline,
        'externalUi': external_ui if offline else [],
        'gap': {
            'tileShowsTypeOnly': tiles,
            'tipUsesTileName': True,
            'statsCollapsedUntilDisclosure': True,
        },
        'rifle': {'card': {k: rifle[k] for k in ('uid', 'wt', 'name', 'type', 'state', 'account', 'scheme', 'dmg', 'speed', 'crit', 'extra', 'aff', 'acts')}, 'expect': rifle['expect'], 'tile': rifle['tile']},
        'other': {'card': {k: second[k] for k in ('uid', 'wt', 'name', 'type', 'state', 'account', 'scheme', 'dmg', 'speed', 'crit', 'extra', 'aff')}, 'expect': second['expect']},
        'longName': {'name': blade['name'], 'type': blade['type'], 'state': blade['state'], 'bounds': blade['bounds']},
        'bounds390': second_bounds['bounds'],
        'clicks': clicks,
        'save': {
            'top': before['top'],
            'weaponKeys': before['weaponKeys'],
            'campV': before['campV'],
            'version': before['version'],
            'unchangedByOpen': True,
            'weaponsJsonSameAfterEquip': True,
            'eqAfter': equipped['eq'],
        },
        'pageErrors': errors,
    }
    (out / ('weapon-inspect-offline.json' if offline else 'weapon-inspect.json')).write_text(
        json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('OK', made['rifle'], rifle['name'], rifle['dmg'], '->', second['name'], second['dmg'])
    browser.close()
