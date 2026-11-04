"""[defense] Приказы window.terraDefense и отказ записи сохранения (сервер :8080, Python Playwright, Chromium).

Для каждого приказа (upgrade, repair, reload, assign, setPriority, deposit):
  1. localStorage.setItem бросает QuotaExceededError для ключа сохранения → {ok:false, reason:'save-failed'},
     рюкзак, склад, турели, camp.defense и сам сейв в localStorage не изменились, события успеха нет;
  2. запись снова работает → тот же приказ проходит (повтор);
  3. холодная загрузка (новая страница с тем же localStorage) → изменение на месте.
Отказ всех записей (резервная копия, игра останавливает записи) → откат, повтор тоже отказ, после перезагрузки всё работает.
build() только открывает режим стройки (постройку пишет родной защищённый путь) — сейв не трогает.
Фон: подносчик доставляет при отказе записи — склад + магазин сохраняются, после холодной загрузки нет ни потери, ни дубля.
Сообщение об отказе видно во вкладке «Оборона».
"""
from pathlib import Path
import json
import os
import shutil
from playwright.sync_api import sync_playwright, expect

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-defense-save-qa'))
out.mkdir(parents=True, exist_ok=True)
IGNORED = ('favicon', 'Download the React DevTools')

HELPERS = """() => {
  if (window.__qa) return;
  const orig = Storage.prototype.setItem;
  window.__qa = {mode: null, events: [], orig};
  Storage.prototype.setItem = function (k, v) {
    const m = __qa.mode;
    if (m === 'all' || (m === 'main' && k === 'terra_save')) throw new DOMException('QA quota', 'QuotaExceededError');
    return orig.call(this, k, v);
  };
  window.addEventListener('terra:defense-change', e => __qa.events.push(e.detail));
  window.__snap = () => JSON.stringify({
    inv: game.p.inv, res: game.p.camp.res, def: game.p.camp.defense ?? null,
    base: game.p.base.filter(o => o.t === 'turretB'), raw: localStorage.getItem('terra_save')
  });
  window.__t = dk => terraDefense.getState().turrets.find(t => t.dk === dk);
  terraDefense.getState();
}"""

with sync_playwright() as pw:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = pw.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    context = browser.new_context(viewport={'width': 1280, 'height': 800})
    errors = []
    state = {'page': None}

    def open_page(new):
        if state['page']:
            state['page'].close()
        page = context.new_page()
        page.set_default_timeout(60000)
        page.on('pageerror', lambda e: errors.append('pageerror: ' + str(e)))
        page.on('console', lambda m: m.type == 'error' and not any(s in m.text for s in IGNORED) and errors.append('console: ' + m.text))
        page.goto(URL, wait_until='load', timeout=120000)
        if new:
            page.locator('#mNew').click()
            page.locator('#skip').click()
        else:
            page.locator('#mContinue').click()
        page.wait_for_function('window.game && game.state === "play" && game.p && game.scene && window.terraDefense?.ready', timeout=120000)
        page.wait_for_timeout(1500)
        page.evaluate(HELPERS)
        state['page'] = page
        return page

    def save(page):
        r = page.evaluate('(() => { const r = game.save(); return r && [r.ok, r.status, r.reason]; })()')
        assert r and r[1] == 'committed', r

    page = open_page(True)
    page.evaluate("""() => {
      const p = game.p, h = game.homePos();
      p.level = 6; p.camp.rep = 1000;
      if (!game.camp.recruit({id: 'qa-1'}).ok) throw Error('recruit failed');
      p.base.push({t: 'turretB', dk: 'pkm', x: h.x + 7, z: h.z + 1, r: 0, hp: 60, mag: 0});
      p.base.push({t: 'turretB', dk: 'nail', x: h.x + 7, z: h.z + 5, r: 0, mag: 0});
      Object.assign(p.inv, {scrap: 200, chem: 50, wood: 50, cloth: 10, a545: 80, nails: 60});
      p.camp.res = p.camp.res || {};
      p.x = h.x + 1; p.z = h.z + 2; game.baseDirty = true;
    }""")
    save(page)

    ORDERS = [
        ('upgrade', "terraDefense.upgrade(__t('nail').id)", "__t('nail').lvl", 2),
        ('repair', "terraDefense.repair(__t('pkm').id)", "__t('pkm').hp", None),
        ('reload', "terraDefense.reload(__t('pkm').id)", "__t('pkm').mag", None),
        ('assign', "terraDefense.assign('qa-1', true)", "(game.p.camp.defense?.porters || []).includes('qa-1')", True),
        ('priority', "terraDefense.setPriority(__t('nail').id, 3)", "__t('nail').priority", 3),
        ('deposit', "terraDefense.deposit('nails', 20)", "game.p.camp.res.nails || 0", 20),
        ('assign', "terraDefense.assign('qa-1', false)", "(game.p.camp.defense?.porters || []).includes('qa-1')", False),
    ]
    report = []
    for kind, call, probe, want in ORDERS:
        fail = page.evaluate(f"""() => {{
          const v0 = {probe}, before = __snap(); __qa.events.length = 0; __qa.mode = 'main';
          let r; try {{ r = {call}; }} finally {{ __qa.mode = null; }}
          return {{r, same: __snap() === before, v0, v1: {probe}, events: __qa.events.map(e => e.reason)}};
        }}""")
        assert fail['r']['ok'] is False and fail['r']['reason'] == 'save-failed' and fail['r']['saveReason'] == 'storage-write', (kind, fail)
        assert fail['same'] and fail['v0'] == fail['v1'], (kind, 'состояние изменилось при отказе', fail)
        assert kind not in fail['events'] and fail['events'] == ['save-failed'], (kind, fail['events'])
        okr = page.evaluate(f"""() => {{
          const raw0 = localStorage.getItem('terra_save'); __qa.events.length = 0;
          const r = {call};
          return {{r, v: {probe}, wrote: localStorage.getItem('terra_save') !== raw0, events: __qa.events.map(e => e.reason)}};
        }}""")
        assert okr['r']['ok'] and okr['wrote'] and kind in okr['events'], (kind, okr)
        if want is not None:
            assert okr['v'] == want, (kind, okr)
        page = open_page(False)  # холодная загрузка: новая страница, тот же localStorage
        cold = page.evaluate(probe)
        assert cold == okr['v'], (kind, 'после холодной загрузки', cold, okr['v'])
        report.append(f"{kind}: fail→{fail['r']['saveReason']} без изменений, повтор ok, после загрузки {cold}")

    # build() только открывает режим стройки, сейв не трогает
    b = page.evaluate("() => { const s = __snap(); const r = terraDefense.build('flame'); game.toggleBuild(false); return {r, same: __snap() === s}; }")
    assert b['r']['ok'] and b['r']['reason'] == 'build-mode' and b['same'], b

    # сообщение во вкладке: кнопка «Улучшить» при отказе записи
    page.locator('#bCamp').click()
    page.evaluate("game.ui.campPanel.select('defense')")
    section = page.locator('#campBody > .campSection[data-camp-section="defense"]')
    card = section.locator('.campItemCard[data-defense-id]').first
    expect(card).to_be_visible()
    before = page.evaluate('__snap()')
    page.evaluate("__qa.mode = 'main'")
    card.get_by_role('button', name='Улучшить').first.click()
    page.evaluate("__qa.mode = null")
    expect(section.locator('.defenseSaveError')).to_be_visible()
    msg = section.locator('.defenseSaveError').inner_text()
    assert 'не смогла записать' in msg and 'не изменились' in msg, msg
    assert page.evaluate('__snap()') == before, 'кнопка изменила состояние при отказе'
    page.evaluate("(() => { const b = document.getElementById('campBody'), s = b.querySelector(':scope > .campSection[data-camp-section=\"defense\"]'); b.scrollTop += s.getBoundingClientRect().top - b.getBoundingClientRect().top; window.scrollTo(0, 0); })()")
    page.wait_for_timeout(600)
    page.screenshot(path=str(out / '01-save-failed-tab.png'))
    page.locator('#campPanel .panelFoot [data-close]').click()

    # отказ всех записей: игра останавливает записи до перезагрузки
    allf = page.evaluate("""() => {
      const s0 = __snap(); __qa.mode = 'all';
      let r1; try { r1 = terraDefense.upgrade(__t('pkm').id); } finally { __qa.mode = null; }
      const s1 = __snap(), r2 = terraDefense.upgrade(__t('pkm').id), s2 = __snap();
      return {r1, r2, same1: s1 === s0, same2: s2 === s0, lvl: __t('pkm').lvl};
    }""")
    assert allf['r1']['reason'] == 'save-failed' and allf['r1']['saveReason'] == 'backup-failed' and allf['same1'], allf
    assert allf['r2']['reason'] == 'save-failed' and allf['same2'] and allf['lvl'] == 1, allf
    page = open_page(False)
    r = page.evaluate("terraDefense.upgrade(__t('pkm').id)")
    assert r['ok'] and r['lvl'] == 2, r
    report.append(f"отказ всех записей: {allf['r1']['saveReason']}, повтор до перезагрузки — тоже отказ, без изменений; после перезагрузки ok")

    # фон: доставка подносчиком при отказе записи — ни потери, ни дубля
    page.evaluate("""() => {
      game.nearestEnemy = () => null;  // только для теста: турели не стреляют, расход боеприпасов = 0
      const o = game.p.base.find(b => b.t === 'turretB' && b.dk === 'nail'); o.mag = 0;
      game.p.camp.res.nails = 200;
    }""")
    assert page.evaluate("terraDefense.assign('qa-1', true).ok")
    total = "(() => (game.p.camp.res.nails || 0) + game.p.base.filter(b => b.t === 'turretB' && b.dk === 'nail').reduce((s, b) => s + (b.mag || 0), 0))()"
    t0 = page.evaluate(total)
    assert t0 == 200, t0
    raw0 = page.evaluate("localStorage.getItem('terra_save')")
    page.evaluate("__qa.mode = 'main'; __qa.events.length = 0")
    page.wait_for_function("__qa.events.some(e => e.reason === 'refill' && e.ammo === 'nails')", timeout=90000)
    bg = page.evaluate(f"""() => {{ const r = game.save(); return {{status: r.status, reason: r.reason, total: {total}, mag: __t('nail').mag, raw: localStorage.getItem('terra_save') === {json.dumps(raw0)}}}; }}""")
    page.evaluate("__qa.mode = null")
    assert bg['status'] != 'committed' and bg['total'] == t0 and bg['mag'] > 0 and bg['raw'], bg
    page = open_page(False)
    cold = page.evaluate(f"({{total: {total}, mag: __t('nail').mag}})")
    assert cold['total'] == t0 and cold['mag'] == 0, ('после отказа записи доставка не должна ни потеряться, ни задвоиться', cold)
    # то же с работающей записью: доставка, сохранение, холодная загрузка
    page.evaluate("game.nearestEnemy = () => null; __qa.events.length = 0")
    page.wait_for_function("__qa.events.some(e => e.reason === 'refill' && e.ammo === 'nails')", timeout=90000)
    mem = page.evaluate(f"({{total: {total}, mag: __t('nail').mag}})")
    save(page)
    page = open_page(False)
    cold2 = page.evaluate(f"({{total: {total}, mag: __t('nail').mag}})")
    assert cold2 == mem and mem['total'] == t0 and mem['mag'] > 0, (mem, cold2)
    report.append(f"фон: при отказе записи в памяти {bg['total']} (магазин {bg['mag']}), после загрузки {cold['total']} (магазин 0); с записью {cold2['total']} (магазин {cold2['mag']})")

    assert not errors, errors
    for line in report:
        print('  ' + line)
    print('PASS: защищённая запись приказов terraDefense, откат при QuotaExceededError, холодная загрузка, фон без потерь | JS errors: 0 | screenshots:', out)
    browser.close()
