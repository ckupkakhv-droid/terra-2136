"""Кеш турелей и башен догоняет замену постройки в том же массиве base.

Длина и ссылка game.p.base не меняются: снос и стройка на месте, перенос, вышка
вместо стены. baseDirty не ставим — модуль должен заметить состав сам.
Сервер на :8080, Python Playwright и Chromium/Chrome.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
IGNORED = ('favicon', 'Download the React DevTools')


def start(page):
    page.goto(URL, wait_until='load', timeout=180000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function(
        'window.game && game.state === "play" && Array.isArray(game.p.base) && window.terraDefense',
        timeout=180000,
    )


with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: m.type == 'error' and not any(s in m.text for s in IGNORED) and errors.append('console: ' + m.text))
    start(page)

    placed = page.evaluate("""() => {
      const p = game.p, h = game.homePos(), n0 = p.base.length;
      p.base.push({t: 'wall', x: h.x + 2, z: h.z + 2, r: 0, hp: 180});
      p.base.push({t: 'turretB', dk: 'pkm', x: h.x + 6, z: h.z + 1, r: 0, lvl: 1, mag: 40, hp: 120});
      return {n0, n: p.base.length, ref: true};
    }""")
    assert placed['n'] == placed['n0'] + 2, placed
    page.wait_for_function(
        """() => {
          const d = terraDefense._debug();
          return d.views === 1 && d.slots.length === 1 && d.slots[0].dk === 'pkm' && d.towers.length === 0;
        }""",
        timeout=30000,
    )

    # другой вид и другая клетка, тот же массив и та же длина, без baseDirty
    swapped = page.evaluate("""() => {
      const p = game.p, h = game.homePos(), base = p.base, n = base.length;
      const i = base.findIndex(o => o.t === 'turretB');
      const x = Math.round((h.x + 9) * 100) / 100, z = Math.round((h.z + 4) * 100) / 100;
      base[i] = {t: 'turretB', dk: 'nail', x, z, r: 2, lvl: 1, mag: 40, hp: 120};
      return {n, same: base.length === n, dirty: game.baseDirty, x, z};
    }""")
    assert swapped['same'] and swapped['dirty'] is not True, swapped
    page.wait_for_function(
        """(want) => {
          const d = terraDefense._debug();
          const s = d.slots[0];
          return d.views === 1 && d.slots.length === 1 && s && s.dk === 'nail' && s.x === want.x && s.z === want.z && s.r === 2;
        }""",
        arg={'x': swapped['x'], 'z': swapped['z']},
        timeout=10000,
    )

    # перенос той же записи
    moved = page.evaluate("""() => {
      const o = game.p.base.find(b => b.t === 'turretB');
      o.x = Math.round((o.x + 3) * 100) / 100;
      o.z = Math.round((o.z - 2) * 100) / 100;
      return {x: o.x, z: o.z, n: game.p.base.length};
    }""")
    page.wait_for_function(
        """(want) => {
          const s = terraDefense._debug().slots[0];
          return s && s.x === want.x && s.z === want.z && s.dk === 'nail';
        }""",
        arg={'x': moved['x'], 'z': moved['z']},
        timeout=10000,
    )

    # стена на том же индексе становится вышкой — бонус дальности из кеша башен
    tower = page.evaluate("""() => {
      const base = game.p.base, n = base.length;
      const w = base.findIndex(o => o.t === 'wall');
      const turret = base.find(o => o.t === 'turretB');
      base[w] = {t: 'watchtower', x: turret.x + 1, z: turret.z, r: 0, hp: 300};
      return {n, same: base.length === n, bare: terraDefense.getState().turrets[0].range};
    }""")
    assert tower['same'], tower
    page.wait_for_function(
        """() => {
          const d = terraDefense._debug();
          const range = terraDefense.getState().turrets[0].range;
          return d.towers.length === 1 && d.towers[0].t === 'watchtower' && range === 16;
        }""",
        timeout=10000,
    )

    # вышка снова стена, длина та же — бонус пропадает (гвоздомёт 1 ур. = 10 м)
    page.evaluate("""() => {
      const base = game.p.base;
      const w = base.findIndex(o => o.t === 'watchtower');
      const h = game.homePos();
      base[w] = {t: 'wall', x: h.x + 2, z: h.z + 2, r: 0, hp: 180};
    }""")
    page.wait_for_function(
        """() => terraDefense._debug().towers.length === 0 && terraDefense.getState().turrets[0].range === 10""",
        timeout=10000,
    )

    # турель на месте становится стеной — в кеше стволов пусто, модель снята
    page.evaluate("""() => {
      const base = game.p.base, n = base.length;
      const i = base.findIndex(o => o.t === 'turretB');
      const h = game.homePos();
      base[i] = {t: 'wall', x: h.x + 4, z: h.z + 4, r: 0, hp: 180};
      if (base.length !== n) throw Error('length changed');
    }""")
    page.wait_for_function(
        """() => {
          const d = terraDefense._debug();
          return d.slots.length === 0 && d.views === 0 && terraDefense.getState().turrets.length === 0;
        }""",
        timeout=10000,
    )
    assert not errors, errors
    print('PASS: in-place replace, move, watchtower bonus and removal keep the same base length')
    browser.close()
