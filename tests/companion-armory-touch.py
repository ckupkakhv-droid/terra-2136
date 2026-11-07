"""Касание 390×844: лагерь → житель → выдать → сдать.

Только touch (locator.tap). Мышиный click функционального прогона сюда не входит.
Ствол 9101 — тестовый. Сервер: TERRA_TEST_URL или http://127.0.0.1:8080/play/.
"""
from pathlib import Path
import json
import os
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/opt/cursor/artifacts'))
out.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')

SETUP = r"""() => {
  const id = 'qa-mate';
  const camp = game.p.camp;
  camp.rep = 1000;
  if (!game.camp.recruit({id}).ok) return {ok: false, reason: 'recruit'};
  const resident = camp.settlers[id];
  resident.name = 'Марфа Испытатель';
  resident.needs.rest = 80;
  resident.job = 'idle';
  resident.order = {};
  resident.work = 0;
  resident.wounded = false;
  resident.injuredUntil = 0;
  const origin = game.homePos();
  game.p.x = origin.x;
  game.p.z = origin.z;
  resident.pos = {x: origin.x + 0.4, z: origin.z};
  resident.mission = 'companion:' + id;
  resident.status = 'idle';
  camp.fieldCompanion = {
    v: 1, settlerId: id, mode: 'follow', home: {x: origin.x, z: origin.z},
    previous: {job: 'idle', order: {}, work: 0, status: 'idle'},
    departed: false, travelled: 0
  };
  const issued = {uid: 9101, wt: 'rifle', nm: 'Ствол испытания', mag: 4, g: 1, r: 2, e: 3, aff: [{id: 'qa-mark', v: 2}]};
  if (!Array.isArray(game.p.base)) game.p.base = [];
  game.p.base.push({t: 'chest', x: origin.x + 1, z: origin.z, r: 0, items: [{weapon: issued}]});
  return {ok: true};
}"""

PROBE = r"""() => {
  const button = document.getElementById('bCamp');
  const rect = button.getBoundingClientRect();
  const top = document.elementFromPoint(rect.x + rect.width / 2, rect.y + rect.height / 2);
  const chain = [];
  let node = top;
  for (let i = 0; node && i < 5; i += 1, node = node.parentElement) {
    const style = getComputedStyle(node);
    chain.push((node.id || node.className || node.tagName) + ' pe=' + style.pointerEvents);
  }
  return {
    moving: !!button.getAnimations().length,
    top: top && (top.id || top.className || top.tagName),
    chain,
    frames: window.__frames || 0,
  };
}"""


def frames(page):
    page.evaluate("() => { window.__frames = 0; let n = 0; const tick = () => { n += 1; window.__frames = n; if (n < 20) requestAnimationFrame(tick); }; requestAnimationFrame(tick); }")
    page.wait_for_timeout(400)
    return page.evaluate("() => window.__frames || 0")


with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get('TERRA_CHROMIUM', '/usr/local/bin/google-chrome'),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True, device_scale_factor=1)
    page.set_default_timeout(20000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(URL, wait_until='load', timeout=90000)
    page.wait_for_function("() => { const b = document.getElementById('mNew'); return b && b.textContent.includes('НОВ'); }")
    page.locator('#mNew').tap()
    page.locator('#skip').tap()
    expect(page.locator('#hud')).to_be_visible()
    alive = frames(page)
    prepared = page.evaluate(SETUP)
    assert prepared.get('ok'), prepared
    still = frames(page)
    probe = page.evaluate(PROBE)
    report = {'framesBefore': alive, 'framesAfterSetup': still, 'probe': probe, 'pageErrors': errors}
    assert still >= 1 and alive >= 1, report
    page.locator('#bCamp').tap()
    page.wait_for_function("() => !!document.querySelector('[data-fieldbook-section=settlers]')")
    page.locator('[data-fieldbook-section="settlers"]').tap()
    page.locator('[data-resident="qa-mate"]').tap()
    fold = page.locator('.fbCompanionFold')
    if fold.count() and not fold.first.evaluate('node => node.open'):
        fold.first.locator(':scope > summary').tap()
    button = page.locator('.campCompanion .ccArmory button')
    expect(button).to_be_visible()
    expect(button).to_be_enabled()
    button.tap()
    page.wait_for_function("() => game.p.camp.settlers['qa-mate'].gear.weapon?.uid === 9101", timeout=15000)
    issued = page.evaluate("() => terraArmory.owners(9101)")
    back = page.locator('.campCompanion .ccArmory button')
    expect(back).to_have_text('Сдать в сундук')
    back.tap()
    page.wait_for_function("() => !game.p.camp.settlers['qa-mate'].gear.weapon", timeout=8000)
    returned = page.evaluate("() => terraArmory.owners(9101)")
    page.screenshot(path=str(out / 'armory-touch-390.png'))
    report.update({'issuedOwners': issued, 'returnedOwners': returned, 'touch': 'tap', 'pageErrors': errors})
    (out / 'companion-armory-touch.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    assert issued == ['settler'], issued
    assert returned == ['chest'], returned
    assert not errors, errors
    browser.close()
    print('PASS touch', json.dumps(report, ensure_ascii=False), flush=True)
