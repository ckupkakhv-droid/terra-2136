"""[defense] Проверка турелей в браузере: сервер на :8080, Python Playwright и Chromium/Chrome.

1. Старое сохранение: турель turretB без dk/mag и без camp.defense. Сейв делается на сборке
   TERRA_BASELINE_URL (если задана, тот же origin, например main), иначе на текущей.
2. После загрузки: турель на месте, dk по умолчанию «pkm», магазин 0, рюкзак не тронут при загрузке.
3. Ставим Гвоздомёт и Огнемёт, кладём боеприпасы на склад, назначаем двух подносчиков,
   ждём доставку — магазины заполнены, склад уменьшился.
4. Спавним врагов — турели стреляют, магазины расходуются, враги получают урон.
5. Сохранение/загрузка сохраняет dk, lvl, mag и подносчиков. В консоли нет ошибок.
Скриншоты: TERRA_QA_OUTPUT (по умолчанию /tmp/terra-defense-qa).
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright, expect

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
BASE_URL = os.environ.get('TERRA_BASELINE_URL') or URL
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-defense-qa'))
out.mkdir(parents=True, exist_ok=True)
IGNORED = ('favicon', 'Download the React DevTools')


def start(page, url, new=True):
    page.goto(url, wait_until='load', timeout=120000)
    if new:
        page.locator('#mNew').click()
        page.locator('#skip').click()
    else:
        page.locator('#mContinue').click()
    page.wait_for_function('window.game && game.state === "play" && game.p && game.scene', timeout=120000)
    page.wait_for_timeout(1500)


with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
    page.on('console', lambda m: m.type == 'error' and not any(s in m.text for s in IGNORED) and errors.append('console: ' + m.text))

    # 1. «старое» сохранение
    start(page, BASE_URL)
    legacy = page.evaluate("""async () => {
      const p = game.p, h = game.homePos();
      p.level = 6; p.camp.rep = 1000;
      for (const id of ['qa-1', 'qa-2']) if (!game.camp.recruit({id}).ok) throw Error('recruit failed');
      const x = h.x + 7, z = h.z + 1;
      p.base.push({t: 'turretB', x, z, r: 0});
      p.inv.a545 = 40; game.baseDirty = true;
      const r = await game.save();
      return {ok: r?.ok !== false, x, z, base: p.base.filter(o => o.t === 'turretB').map(o => Object.keys(o).sort().join(',')), defense: !!p.camp.defense};
    }""")
    assert legacy['ok'] and legacy['base'] == ['r,t,x,z'] and not legacy['defense'], legacy

    # 2. загрузка в новой сборке
    errors.clear()
    start(page, URL, new=False)
    st = page.evaluate('terraDefense.getState()')
    assert st['ready'] and st['limit']['max'] == 4, st['limit']
    assert len(st['turrets']) == 1 and st['turrets'][0]['dk'] == 'pkm' and st['turrets'][0]['lvl'] == 1 and st['turrets'][0]['mag'] == 0, st['turrets']
    assert page.evaluate('game.p.inv.a545') == 40, 'рюкзак изменился при загрузке'
    assert page.evaluate("Object.keys(game.p.base.find(o => o.t === 'turretB')).sort().join(',')") == 'r,t,x,z', 'загрузка переписала запись турели'

    page.evaluate('game.toggleBuild(true); game.build.sel = "dNail"; game.renderBuildBar(); document.querySelector(\'[data-b="dNail"]\').scrollIntoView({inline: "center"})')
    assert page.evaluate('["turretB", "dNail", "dFlame"].every(k => document.querySelector(`[data-b="${k}"]`))'), 'турелей нет в меню'
    page.wait_for_timeout(600)
    page.screenshot(path=str(out / '00-build-menu.png'))
    page.evaluate('game.toggleBuild(false)')

    # 3. новые турели, склад, подносчики
    page.evaluate("""() => {
      const p = game.p, h = game.homePos();
      p.base.push({t: 'turretB', dk: 'nail', x: h.x + 7, z: h.z + 5, r: 0});
      p.base.push({t: 'turretB', dk: 'flame', x: h.x + 3, z: h.z + 7, r: 0});
      Object.assign(p.camp.res, {a545: 300, nails: 200, gas: 12});
      p.x = h.x + 1; p.z = h.z + 2; game.baseDirty = true;
    }""")
    # подносчик qa-1 — кнопкой во вкладке «Оборона» (terraCampUI), qa-2 — через API
    page.locator('#bCamp').click()
    page.evaluate("game.ui.campPanel.select('defense')")
    section = page.locator('#campBody > .campSection[data-camp-section="defense"]')
    expect(section.locator('[data-porter="qa-1"]')).to_be_visible()
    section.locator('[data-porter="qa-1"]').click()
    expect(section.locator('[data-porter="qa-1"]')).to_have_attribute('aria-pressed', 'true')
    page.locator('#campPanel .panelFoot [data-close]').click()
    assert page.evaluate("terraDefense.assign('qa-2', true).ok")
    page.wait_for_function("terraDefense.getState().porters.some(p => p.turretId)", timeout=60000)
    page.wait_for_timeout(2500)
    page.screenshot(path=str(out / '01-porters-walking.png'))
    page.wait_for_function("terraDefense.getState().turrets.every(t => t.mag >= t.magMax * 0.6)", timeout=90000)
    st = page.evaluate('terraDefense.getState()')
    res = page.evaluate('({...game.p.camp.res})')
    assert res['a545'] < 300 and res['nails'] < 200 and res['gas'] < 12, res
    assert page.evaluate('terraDefense._debug().stats.refills') >= 3
    page.screenshot(path=str(out / '02-turrets-loaded.png'))

    # 4. бой
    before = page.evaluate('terraDefense.getState().turrets.map(t => t.mag)')
    page.evaluate("""() => {
      const h = game.homePos();
      window.__qaEnemies = [];
      for (let i = 0; i < 6; i++) { const e = game.spawnEnemy('zombie', h.x + 12 + (i % 3) * 1.5, h.z + 1 + i * 1.3, {force: 1}); e && __qaEnemies.push(e); }
      window.__qaHp0 = __qaEnemies.reduce((s, e) => s + e.hp, 0);
    }""")
    page.wait_for_function("terraDefense._debug().pool > 0 || terraDefense._debug().stats.shots > 3", timeout=60000)
    page.screenshot(path=str(out / '03-turrets-firing.png'))
    page.wait_for_function("terraDefense._debug().stats.shots >= 12", timeout=60000)
    page.wait_for_timeout(1500)
    fight = page.evaluate("""() => ({shots: terraDefense._debug().stats.shots, hp: __qaEnemies.reduce((s, e) => s + Math.max(0, e.dead ? 0 : e.hp), 0), hp0: __qaHp0,
      dead: __qaEnemies.filter(e => e.dead).length, mags: terraDefense.getState().turrets.map(t => t.mag), pool: terraDefense._debug().poolMax})""")
    assert fight['hp'] < fight['hp0'], fight
    assert any(a < b for a, b in zip(fight['mags'], before)), (before, fight)

    # 5. вкладка «Оборона» и сохранение
    page.wait_for_timeout(300)
    if page.locator('#campPanel').is_hidden():
        page.locator('#bCamp').click()
    if page.locator('#campPanel').is_hidden():
        page.evaluate('game.ui.campPanel.open()')
    expect(page.locator('#campPanel')).to_be_visible()
    page.evaluate("game.ui.campPanel.select('defense')")
    section = page.locator('#campBody > .campSection[data-camp-section="defense"]')
    expect(section.locator('.campSection__list .campItemCard[data-defense-id]')).to_have_count(3)
    expect(section.locator('.campItemCard[data-defense-id]').first).to_be_visible()
    assert page.evaluate("document.querySelector('#campTabs [data-camp-tab=\"defense\"]') !== null"), 'нет вкладки «Оборона»'
    page.evaluate("(() => { const b = document.getElementById('campBody'), s = b.querySelector(':scope > .campSection[data-camp-section=\"defense\"]'); b.scrollTop += s.getBoundingClientRect().top - b.getBoundingClientRect().top; window.scrollTo(0, 0); })()")
    page.wait_for_timeout(800)
    page.screenshot(path=str(out / '04-defense-tab.png'))
    section.locator('.campItemCard[data-defense-id] .campInfoButton').first.click()
    expect(page.locator('.campInfoSheet')).to_be_visible()
    page.screenshot(path=str(out / '04b-defense-info.png'))
    page.locator('.campInfoSheet .campInfoClose').click()
    # полоски прочности родной вкладки подписаны видом турели, а не «Турель»
    labels = page.evaluate("""() => [...document.querySelectorAll('#campPanel .defGrid > .defCard[data-dk]')].map(c => c.firstChild.nodeValue)""")
    names = page.evaluate("terraDefense.getState().turrets.map(t => t.name)")
    assert len(labels) == 3 and sorted(l.split(' · ')[0] for l in labels) == sorted(names), (labels, names)
    assert page.evaluate("""() => ![...document.querySelectorAll('#campPanel .defGrid > .defCard')].some(c => c.firstChild?.nodeValue === 'Турель')"""), 'осталась подпись «Турель»'
    page.evaluate("(() => { const b = document.getElementById('campBody'), c = document.querySelector('#campPanel .defGrid > .defCard[data-dk]'); b.scrollTop += c.getBoundingClientRect().top - b.getBoundingClientRect().top - 40; window.scrollTo(0, 0); })()")
    page.wait_for_timeout(500)
    page.screenshot(path=str(out / '04d-defense-hp-labels.png'))
    # телефон: вкладка «Оборона» под большим пальцем
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(500)
    page.evaluate("game.ui.campPanel.select('defense')")
    expect(section.locator('.campItemCard[data-defense-id]').first).to_be_visible()
    section.locator('.campItemCard[data-defense-id]').first.scroll_into_view_if_needed()
    page.screenshot(path=str(out / '04c-defense-phone.png'))
    page.set_viewport_size({'width': 1280, 'height': 800})
    page.wait_for_timeout(300)
    page.locator('#campPanel .panelFoot [data-close]').click()
    sv = page.evaluate('async () => { const r = await game.save(); return r && [r.ok, r.status, r.reason]; }')
    assert sv and sv[0], sv
    saved = page.evaluate("({base: game.p.base.filter(o => o.t === 'turretB').map(o => ({dk: o.dk, mag: o.mag})), porters: game.p.camp.defense.porters})")
    start(page, URL, new=False)
    again = page.evaluate("({base: game.p.base.filter(o => o.t === 'turretB').map(o => ({dk: o.dk, mag: o.mag})), porters: game.p.camp.defense?.porters})")
    assert again['porters'] == saved['porters'] == ['qa-1', 'qa-2'], again
    assert [b['dk'] for b in again['base']] == [b['dk'] for b in saved['base']], again
    assert all(abs((a['mag'] or 0) - (b['mag'] or 0)) < 1.01 for a, b in zip(again['base'], saved['base'])), (saved, again)
    # 5b. снос: возврат от собственной цены вида и вложенных улучшений
    refunds = page.evaluate("""async () => {
      const p = game.p, out = {}, R = TERRA_DEFENSE_CTX.B.refund;
      for (const [dk, lvl] of [['nail', 2], ['flame', 1]]) {
        const o = p.base.find(b => b.t === 'turretB' && b.dk === dk); o.lvl = lvl;
        const want = Li_cost(dk, lvl), inv0 = {...p.inv};
        game.toggleBuild(true); Object.assign(game.build, {demo: true, gx: o.x, gz: o.z}); p.x = o.x + 2; p.z = o.z + 2;
        let r = null, tries = [];
        for (let i = 0; i < 4 && !r?.ok; i++) {  // сразу после загрузки защита сохранения может быть ещё занята
          if (i) await new Promise(f => setTimeout(f, 1000));
          game.toggleBuild(true); Object.assign(game.build, {demo: true, gx: o.x, gz: o.z});
          r = await game.commitBaseAction(); tries.push(r && (r.reason || r.status));
        }
        game.toggleBuild(false);
        const got = {}; for (const k of new Set([...Object.keys(p.inv), ...Object.keys(want)])) { const d = (p.inv[k] || 0) - (inv0[k] || 0); if (d) got[k] = d; }
        const exp = {}; for (const [k, v] of Object.entries(want)) { const e = Math.floor(v * R); if (e) exp[k] = e; }
        out[dk] = {ok: r?.ok, tries, gone: !p.base.includes(o), got, exp};
      }
      return out;
      function Li_cost(dk, lvl) { const t = terraDefense.getState().catalog.find(c => c.dk === dk), c = {...t.cost};
        const up = {nail: [null, {scrap: 8, wood: 6}], flame: [null]}[dk];
        for (let i = 1; i < lvl; i++) for (const [k, v] of Object.entries(up[i])) c[k] = (c[k] || 0) + v; return c; }
    }""")
    print('REFUND:', refunds)
    for dk, r in refunds.items():
        assert r['ok'] and r['gone'] and r['got'] == r['exp'] and r['got'], (dk, r)
    assert refunds['nail']['got'] != refunds['flame']['got']
    # 5c. блок camp.defense из более новой версии: модуль замирает и ничего не переписывает
    fut = page.evaluate("""async () => {
      const d = game.p.camp.defense, keep = JSON.stringify(d), base0 = JSON.stringify(game.p.base);
      d.v = 2; d.extra = {x: 1};
      await new Promise(f => setTimeout(f, 1500));
      const r = {state: terraDefense.getState().future, assign: terraDefense.assign('qa-1', false).reason,
        same: JSON.stringify(game.p.camp.defense) === JSON.stringify({...JSON.parse(keep), v: 2, extra: {x: 1}}), base: JSON.stringify(game.p.base) === base0};
      const d2 = game.p.camp.defense; delete d2.extra; d2.v = 1;  // объект мог смениться: лагерь пишет через копию
      await new Promise(f => setTimeout(f, 800));
      const g = terraDefense.getState(); r.back = g.ready === true && !g.future; if (!r.back) r.dbg = {ready: g.ready, future: g.future, v: game.p.camp?.defense?.v, hasP: !!game.p, ctx: !!window.TERRA_DEFENSE_CTX};
      return r;
    }""")
    print('FUTURE:', fut)
    assert fut == {'state': True, 'assign': 'future', 'same': True, 'base': True, 'back': True}, fut
    # 6. нагрузка: 18 турелей (максимум «Города») и 30 врагов на текущем пресете графики
    page.evaluate("""() => {
      const h = game.homePos(), p = game.p, kinds = ['pkm', 'nail', 'flame'];
      for (let i = 0; i < 17; i++) p.base.push({t: 'turretB', dk: kinds[i % 3], x: h.x - 9 + (i % 5) * 4, z: h.z - 9 - Math.floor(i / 5) * 4, r: 0, mag: 40});
      Object.assign(p.camp.res, {a545: 2000, nails: 2000, gas: 200});
      for (let i = 0; i < 30; i++) game.spawnEnemy(i % 5 ? 'zombie' : 'mutant', h.x - 10 + (i % 6) * 3, h.z - 22 - Math.floor(i / 6) * 2, {force: 1});
      game.baseDirty = true; p.x = h.x; p.z = h.z - 14;
      window.__fr = 0; window.__f0 = performance.now(); const f = () => { __fr++; __fr < 100000 && requestAnimationFrame(f); }; requestAnimationFrame(f);
    }""")
    page.wait_for_timeout(8000)
    stress = page.evaluate("({fps: __fr / ((performance.now() - __f0) / 1000), preset: game.qk, turrets: terraDefense.getState().turrets.length, ...terraDefense._debug()})")
    page.screenshot(path=str(out / '05-stress-18.png'))
    assert stress['turrets'] == 18 and stress['ms'] < 4, stress
    assert not errors, errors
    print('STRESS:', stress)
    print('PASS: legacy save loads (dk=pkm, mag=0, backpack untouched), porters refilled', len(st['turrets']), 'turrets,',
          'shots', fight['shots'], 'enemy hp', round(fight['hp0']), '->', round(fight['hp']), 'killed', fight['dead'],
          '| save/load keeps dk, mag, porters | JS errors: 0 | screenshots:', out)
    browser.close()
