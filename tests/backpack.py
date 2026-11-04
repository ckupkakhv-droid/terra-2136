"""Рюкзак: вёрстка, кадр модели, жесты. Сервер на :8080, Chrome с SwiftShader.
Сейв не читается. Скриншоты — в TERRA_QA_OUTPUT или /tmp/terra-backpack-qa.
"""
from pathlib import Path
import os
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-backpack-qa'))
out.mkdir(parents=True, exist_ok=True)
chrome = os.environ.get('TERRA_CHROMIUM', '/usr/local/bin/google-chrome')

ALPHA = '''(canvas) => {
  const ctx = canvas.getContext('2d');
  const w = canvas.width, h = canvas.height;
  const data = ctx.getImageData(0, 0, w, h).data;
  let minX = w, minY = h, maxX = -1, maxY = -1, n = 0;
  for (let y = 0; y < h; y += 1) {
    for (let x = 0; x < w; x += 2) {
      if (data[(y * w + x) * 4 + 3] > 24) {
        n++;
        if (x < minX) minX = x;
        if (y < minY) minY = y;
        if (x > maxX) maxX = x;
        if (y > maxY) maxY = y;
      }
    }
  }
  return {w, h, n, minX, minY, maxX, maxY,
    top: minY, bottom: h - 1 - maxY, left: minX, right: w - 1 - maxX,
    span: maxY >= 0 ? (maxY - minY) / h : 0};
}'''

SIZE = '''() => {
  const bad = [];
  for (const el of document.querySelectorAll('#inv .equipmentSlot, #inv .equipmentWeapon, #inv .tabs button, #inv .x')) {
    const r = el.getBoundingClientRect();
    if (r.width < 43.5 || r.height < 43.5) bad.push((el.getAttribute('aria-label') || el.className) + ' ' + Math.round(r.width) + 'x' + Math.round(r.height));
  }
  const win = document.querySelector('#inv .win');
  const body = document.getElementById('invBody');
  return {
    bad,
    winOverflow: win.scrollWidth - win.clientWidth,
    bodyOverflow: body.scrollWidth - body.clientWidth,
  };
}'''


def shot(page, name):
    page.screenshot(path=str(out / name))


with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chrome, args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader',
        '--ignore-gpu-blocklist', '--disable-dev-shm-usage',
    ])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), wait_until='domcontentloaded', timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    expect(page.locator('#hud')).to_be_visible()
    save_before = page.evaluate('localStorage.getItem("terra_save")')
    profile = page.evaluate('''() => {
      const raw = localStorage.getItem('terra_save');
      if (!raw) return null;
      try { const j = JSON.parse(raw); return {keys: Object.keys(j).sort(), v: j.v ?? j.ver ?? j.version ?? null}; }
      catch (e) { return {raw: true}; }
    }''')
    quiet = page.evaluate('''() => {
      const p = game.p;
      return JSON.stringify({level: p.level, xp: p.xp, weapons: p.weapons.length, armor: (p.armor||[]).length, wear: p.wear||{}, eq: (p.eq||[]).map(w => w && w.uid)});
    }''')
    page.keyboard.press('KeyI')
    expect(page.locator('#inv.bp .equipmentSheet')).to_be_visible()
    page.wait_for_function('''() => {
      const c = document.querySelector('[data-equipment-preview] canvas');
      const label = document.querySelector('.equipmentPreviewStatus');
      return c && c.width > 20 && label && label.textContent === '';
    }''', timeout=20000)
    page.wait_for_timeout(400)
    frame = page.evaluate(ALPHA, page.locator('[data-equipment-preview] canvas').element_handle())
    print('FRAME', frame)
    assert frame['n'] > 100, frame
    assert frame['top'] >= 4 and frame['bottom'] >= 4, frame
    assert frame['left'] >= 2 and frame['right'] >= 2, frame
    assert frame['span'] >= 0.55, frame
    empty = page.locator('#inv .equipmentSlot.is-empty')
    expect(empty).to_have_count(7)
    assert page.evaluate('''() => [...document.querySelectorAll('#inv .is-empty .bp-clip')].every(el => {
      const r = el.getBoundingClientRect();
      return r.width <= 2 && r.height <= 2;
    })''')
    moved = page.evaluate('''() => {
      const preview = document.querySelector('[data-equipment-preview]');
      const man = game.ui.equipmentPreview;
      const before = man.yaw || 0;
      const r = preview.getBoundingClientRect();
      const down = {pointerId: 1, clientX: r.x + r.width / 2, clientY: r.y + 40, bubbles: true, pointerType: 'mouse'};
      preview.dispatchEvent(new PointerEvent('pointerdown', down));
      preview.dispatchEvent(new PointerEvent('pointermove', Object.assign({}, down, {clientX: down.clientX + 120})));
      preview.dispatchEvent(new PointerEvent('pointerup', down));
      return Math.abs((man.yaw || 0) - before);
    }''')
    print('YAW', moved)
    assert moved > 0.4, moved

    ids = page.evaluate('''() => {
      const w = game.makeWeapon('machete', 1, 3);
      const weak = game.makeWeapon('stick', 0, 0);
      game.addWeapon(w, false, true);
      game.addWeapon(weak, false, true);
      const a = game.makeArmor('vest', 1, 2);
      const worn = game.makeArmor('jacket', 0, 0);
      game.addArmor(worn);
      game.addArmor(a);
      game.wearArmor(worn.uid);
      game.ui.renderInv();
      return {w: w.uid, weak: weak.uid, a: a.uid};
    }''')
    page.wait_for_timeout(200)
    expect(page.locator('.bp-meter')).to_be_visible()
    page.locator(f'.tile[data-w="{ids["weak"]}"]').hover()
    expect(page.locator('#bpTip')).to_be_visible()
    expect(page.locator('#bpTip')).to_contain_text('Урон')
    page.evaluate('''(uid) => new Promise(ok => {
      const tile = document.querySelector('.tile[data-w="' + uid + '"]');
      const fire = () => tile.dispatchEvent(new MouseEvent('click', {bubbles: true, cancelable: true}));
      fire();
      setTimeout(() => { fire(); ok(true); }, 70);
    })''', ids['weak'])
    page.wait_for_timeout(250)
    armed = page.locator('[data-equipment-weapon="0"]')
    expect(armed).not_to_contain_text('Пусто')
    page.locator('[data-gear="armor"]').click()
    page.locator(f'.tile[data-armor="{ids["a"]}"]').hover()
    expect(page.locator('#bpTip')).to_contain_text('Броня')
    page.locator(f'.tile[data-armor="{ids["a"]}"]').drag_to(page.locator('[data-equipment-armor="body"]'))
    page.wait_for_timeout(300)
    assert page.evaluate('''(uid) => game.wornArmor("body") && game.wornArmor("body").uid === uid''', ids['a'])

    for tab in ('items', 'craft', 'skills', 'settle', 'log', 'eq'):
        page.locator(f'#inv .tabs button[data-tab="{tab}"]').click()
        page.wait_for_timeout(150)
        expect(page.locator('#invBody')).to_be_visible()
    page.locator('#inv .tabs button[data-tab="skills"]').click()
    expect(page.locator('.circuitClass, .sk').first).to_be_visible()
    shot(page, 'after-desktop-skills.png')
    page.locator('#inv .tabs button[data-tab="eq"]').click()
    page.locator('[data-gear="weapons"]').click()
    page.wait_for_timeout(300)
    shot(page, 'after-desktop.png')
    size = page.evaluate(SIZE)
    print('SIZE', size)
    assert not size['bad'], size
    assert size['winOverflow'] <= 1
    assert size['bodyOverflow'] <= 1

    for name, width, height in (('portrait', 390, 844), ('landscape', 844, 390)):
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(350)
        page.locator('#invBody').evaluate('e => e.scrollTop = 0')
        page.wait_for_function('''() => {
          const c = document.querySelector('[data-equipment-preview] canvas');
          return c && c.width > 20;
        }''')
        page.wait_for_timeout(250)
        box = page.evaluate(ALPHA, page.locator('[data-equipment-preview] canvas').element_handle())
        print(name, box)
        assert box['top'] >= 3 and box['bottom'] >= 3, box
        assert box['span'] >= 0.5, box
        page.locator('[data-equipment-preview]').scroll_into_view_if_needed()
        preview = page.locator('[data-equipment-preview]').bounding_box()
        assert preview['width'] > 40 and preview['height'] > 80, preview
        for sel in page.locator('#inv .equipmentSlot, #inv .equipmentWeapon').all():
            sel.scroll_into_view_if_needed()
            r = sel.bounding_box()
            assert r and r['width'] >= 43.5 and r['height'] >= 43.5, (name, r)
        fit = page.evaluate(SIZE)
        assert fit['winOverflow'] <= 1, (name, fit)
        assert fit['bodyOverflow'] <= 1, (name, fit)
        overlap = page.evaluate('''() => {
          const chip = document.querySelector('#inv .invChips');
          const slot = document.querySelector('#inv .equipmentWeapon');
          if (!chip || !slot) return false;
          const a = chip.getBoundingClientRect();
          const b = slot.getBoundingClientRect();
          return !(a.bottom < b.top + 1 || a.top > b.bottom - 1 || a.right < b.left + 1 || a.left > b.right - 1);
        }''')
        assert not overlap, name
        if name == 'portrait':
            clipped = page.evaluate('''() => [...document.querySelectorAll('#inv .tabs button span')].filter(s => s.scrollWidth > s.clientWidth + 1).map(s => s.textContent)''')
            assert not clipped, clipped
        shot(page, f'after-{name}.png')

    quiet_tabs = page.evaluate('''() => {
      const p = game.p;
      return {level: p.level, xp: p.xp};
    }''')
    assert '"level":' in quiet
    profile_after = page.evaluate('''() => {
      const raw = localStorage.getItem('terra_save');
      if (!raw) return null;
      try { const j = JSON.parse(raw); return {keys: Object.keys(j).sort(), v: j.v ?? j.ver ?? j.version ?? null}; }
      catch (e) { return {raw: true}; }
    }''')
    if profile and profile_after and profile.get('keys'):
        assert profile_after.get('keys') == profile['keys']
        assert profile_after.get('v') == profile.get('v')
    assert quiet_tabs['level'] == page.evaluate('(' + quiet + ').level')
    assert not errors, errors
    print('PASS', 'save-before', bool(save_before), 'profile', profile)
    browser.close()
