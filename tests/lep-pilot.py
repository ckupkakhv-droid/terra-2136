"""Пилот уличной опоры ЛЭП. Один прогон Chromium, без подстановки метрик.

Ставит качество «среднее», post выключен, devicePixelRatio 1.
Смотрит трассу (highway, cx=-3, cz=-3) и промзону (ind, cx=11, cz=17)
в 1280×800 и 390×844. Временный профиль браузера, сохранение не пишется.

  python3 -m http.server 8080
  python3 tests/lep-pilot.py

TERRA_TEST_URL, TERRA_CHROMIUM, TERRA_LEP_OUT, TERRA_LEP_SAMPLE_MS.
"""
import json
import os
import shutil
from pathlib import Path

from playwright.sync_api import sync_playwright

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
OUT = Path(os.environ.get('TERRA_LEP_OUT', '/tmp/lep-pilot/after'))
CHROME = os.environ.get('TERRA_CHROMIUM') or shutil.which('google-chrome') or shutil.which('chromium')
SAMPLE_MS = int(os.environ.get('TERRA_LEP_SAMPLE_MS', '2500'))
ROAD = {'cx': -3, 'cz': -3, 'x': -132.8, 'z': -120.0, 'd': 'highway'}
IND = {'cx': 11, 'cz': 17, 'x': 552.0, 'z': 828.5, 'd': 'ind'}

OUT.mkdir(parents=True, exist_ok=True)

BOOT = """() => new Promise((resolve) => {
  const t = setInterval(() => {
    if (window.game && game.state === 'play' && game.p && game.world && game.ren) {
      clearInterval(t); resolve(true);
    }
  }, 100);
})"""

PLACE = """(p) => {
  game.p.x = p.x;
  game.p.z = p.z + 11;
  game.p.yaw = Math.PI;
  game.camZoom = 1.05;
  game.dayT = 13;
  game.p.hp = game.p.maxHp || 100;
  game.p.rad = 0;
  game.world.update(game.p.x, game.p.z, true);
  if (game.cameraUpdate) game.cameraUpdate(1);
  if (game.renderT) game.renderT();
  const ch = game.world.chunkAt(p.x, p.z);
  const mark = ch && (ch.map || []).find(m => m && m.c === '#6a7076');
  const cols = (ch && ch.cols || []).filter(c => c && c.x0 <= p.x && c.x1 >= p.x && c.z0 <= p.z && c.z1 >= p.z);
  return {
    d: ch && ch.d, qk: game.qk, dpr: game.ren.getPixelRatio(),
    post: !!(game.post && game.post.on),
    mark: mark || null,
    cols: cols.slice(0, 3).map(c => ({x0: c.x0, z0: c.z0, x1: c.x1, z1: c.z1, h: c.h})),
    lep: window.TERRA_LEP ? {ready: TERRA_LEP.ready, failed: TERRA_LEP.failed, stats: TERRA_LEP.stats, bounds: TERRA_LEP.bounds, models: TERRA_LEP.models} : null
  };
}"""

GLINFO = """() => {
  const gl = game.ren.getContext();
  const dbg = gl.getExtension('WEBGL_debug_renderer_info');
  const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
  return {
    renderer: dbg ? gl.getParameter(dbg.UNMASKED_RENDERER_WEBGL) : gl.getParameter(gl.RENDERER),
    version: gl.getParameter(gl.VERSION),
    disjointExt: ext ? 'EXT_disjoint_timer_query_webgl2' : null,
    gpuTier: (window.TERRA_GPU || {}).tier || null,
    qk: game.qk,
    pixelRatio: game.ren.getPixelRatio(),
    post: !!(game.post && game.post.on),
    size: {w: game.W, h: game.H}
  };
}"""

SAMPLE = """(ms) => new Promise((resolve) => {
  const orig = game.loop.bind(game);
  const rows = [];
  let prev = null;
  game.loop = function (t) {
    const stamp = game.last;
    const a = performance.now();
    const r = orig(t);
    const b = performance.now();
    if (game.last !== stamp) {
      const i = game.ren.info;
      rows.push({loop: b - a, frame: prev == null ? null : t - prev, calls: i.render.calls, triangles: i.render.triangles, geometries: i.memory.geometries, textures: i.memory.textures});
      prev = t;
    }
    if (game.p) { game.p.hp = game.p.maxHp || 100; game.p.rad = 0; }
    return r;
  };
  setTimeout(() => {
    game.loop = orig;
    const stat = (key) => {
      const v = rows.map(r => r[key]).filter(x => Number.isFinite(x)).sort((a, b) => a - b);
      if (!v.length) return null;
      const q = p => v[Math.min(v.length - 1, Math.max(0, Math.round((v.length - 1) * p)))];
      return {n: v.length, min: +v[0].toFixed(3), p50: +q(0.5).toFixed(3), p95: +q(0.95).toFixed(3), max: +v[v.length - 1].toFixed(3)};
    };
    resolve({frames: rows.length, loopMs: stat('loop'), frameMs: stat('frame'), calls: stat('calls'), triangles: stat('triangles'), geometries: stat('geometries'), textures: stat('textures')});
  }, ms);
})"""

LODS = """() => {
  const px = game.p.x, pz = game.p.z;
  const farCx = -3, farCz = -9;
  const key = farCx + ',' + farCz;
  let built = false;
  if (!game.world.chunks.has(key)) { game.world.build(farCx, farCz); built = true; }
  const names = [0, 20, 48, 110].map(d => TERRA_LEP.lodName(d));
  const low = game.qk;
  game.qk = 'low';
  const lowName = TERRA_LEP.lodName(4);
  game.qk = low;
  const mesh = game.scene.getObjectByName('lep-batch');
  return {
    names, lowName,
    byLod: TERRA_LEP.stats.byLod,
    builtFar: built,
    material: mesh && mesh.material.customProgramCacheKey(),
    meshTris: TERRA_LEP.stats.tris,
    castShadow: !!(mesh && mesh.castShadow)
  };
}"""

FALLBACK = """() => {
  const before = TERRA_LEP.stats.fallback;
  const errors = TERRA_LEP.stats.errors.length;
  const restore = TERRA_LEP.debugDrop('lod0');
  const cx = 15, cz = 15;
  game.p.x = cx * 48 + 11.2;
  game.p.z = cz * 48 + 24;
  game.world.update(game.p.x, game.p.z, true);
  const after = {fallback: TERRA_LEP.stats.fallback, errors: TERRA_LEP.stats.errors.slice()};
  restore();
  return {before, errorsBefore: errors, after};
}"""

UNLOAD = """(p) => {
  const before = game.world.chunks.size;
  game.p.x = p.x + 5000; game.p.z = p.z + 5000;
  game.world.update(game.p.x, game.p.z, true);
  const away = game.world.chunks.size;
  game.p.x = p.x; game.p.z = p.z + 1.6;
  game.world.update(game.p.x, game.p.z, true);
  const ch = game.world.chunkAt(p.x, p.z);
  const mark = ch && (ch.map || []).some(m => m && m.c === '#6a7076');
  return {before, away, back: game.world.chunks.size, mark, replaced: TERRA_LEP.stats.replaced, errors: TERRA_LEP.stats.errors.slice()};
}"""

GPU = """() => new Promise((resolve) => {
  const gl = game.ren.getContext();
  const ext = gl.getExtension('EXT_disjoint_timer_query_webgl2');
  if (!ext) { resolve({gpuMs: null, reason: 'EXT_disjoint_timer_query_webgl2 unavailable'}); return; }
  const q = gl.createQuery();
  gl.beginQuery(ext.TIME_ELAPSED_EXT, q);
  game.ren.render(game.scene, game.cam);
  gl.endQuery(ext.TIME_ELAPSED_EXT);
  const t0 = performance.now();
  (function poll() {
    if (gl.getParameter(ext.GPU_DISJOINT_EXT)) { gl.deleteQuery(q); resolve({gpuMs: null, reason: 'GPU_DISJOINT_EXT'}); return; }
    if (gl.getQueryParameter(q, gl.QUERY_RESULT_AVAILABLE)) {
      const ns = gl.getQueryParameter(q, gl.QUERY_RESULT);
      gl.deleteQuery(q);
      resolve({gpuMs: ns / 1e6, disjoint: false});
      return;
    }
    if (performance.now() - t0 > 1500) { gl.deleteQuery(q); resolve({gpuMs: null, reason: 'timeout'}); return; }
    requestAnimationFrame(poll);
  })();
})"""


def launch(p, width, height):
    browser = p.chromium.launch(
        executable_path=CHROME,
        args=['--ignore-gpu-blocklist', '--enable-webgl', '--use-gl=angle', '--enable-unsafe-swiftshader'],
    )
    ctx = browser.new_context(viewport={'width': width, 'height': height}, device_scale_factor=1, has_touch=width < 700)
    ctx.add_init_script(
        "localStorage.setItem('terra_set', JSON.stringify({q:'med', vol:0, vm:0, vs:0, va:0, post:false, fps:false, dpr:1, shake:false}));"
    )
    page = ctx.new_page()
    page.set_default_timeout(180000)
    errors = []
    page.on('pageerror', lambda e: errors.append('page:' + str(e)))
    page.on('console', lambda m: errors.append('console:' + m.text) if m.type == 'error' else None)
    return browser, page, errors


def boot(page, query=''):
    page.goto(URL + query, wait_until='load')
    page.wait_for_function("() => window.TERRA_LEP && (TERRA_LEP.ready || TERRA_LEP.failed)")
    ready = page.evaluate("() => ({ready: TERRA_LEP.ready, failed: TERRA_LEP.failed, errors: TERRA_LEP.stats.errors, models: TERRA_LEP.models, bounds: TERRA_LEP.bounds})")
    page.locator('#mNew').click()
    try:
        page.locator('#skip').click(timeout=15000)
    except Exception:
        pass
    page.wait_for_function(BOOT)
    return ready


def shoot(page, name):
    page.evaluate("() => { for (const el of document.body.children) if (el.id !== 'c') el.style.visibility = 'hidden'; }")
    page.wait_for_timeout(400)
    path = OUT / name
    page.screenshot(path=str(path))
    page.evaluate("() => { for (const el of document.body.children) el.style.visibility = ''; }")
    return str(path)


def check_place(row, label):
    lep = row['lep']
    assert lep and lep['ready'] and not lep['failed'], (label, lep)
    stats = lep['stats']
    assert stats['replaced'] > 0, stats
    assert stats['anchorErrMax'] <= 0.001, stats
    assert not stats['errors'], stats['errors']
    assert row['qk'] == 'med' and row['dpr'] == 1 and row['post'] is False, row
    assert row['d'] == (ROAD['d'] if label == 'road' else IND['d']), row['d']
    assert row['mark'] and row['mark']['c'] == '#6a7076', row['mark']
    box = next((c for c in row['cols'] if abs((c['x1'] - c['x0']) - 3) < 0.05 and abs((c['z1'] - c['z0']) - 3) < 0.05), None)
    assert box and abs(box['h'] - 2) < 0.05, row['cols']
    for key, bound in (lep.get('bounds') or {}).items():
        assert bound and bound['maxX'] <= 1.51 and bound['maxZ'] <= 1.51, (key, bound)


def run_view(p, width, height, key, deep):
    browser, page, errors = launch(p, width, height)
    try:
        ready = boot(page, '')
        assert ready['ready'] and not ready['failed'], ready
        road = page.evaluate(PLACE, ROAD)
        page.wait_for_timeout(200)
        shots = {'road': shoot(page, f'{key}-road.png')}
        ind = page.evaluate(PLACE, IND)
        page.wait_for_timeout(200)
        shots['ind'] = shoot(page, f'{key}-ind.png')
        check_place(road, 'road')
        check_place(ind, 'ind')
        page.evaluate(PLACE, ROAD)
        page.wait_for_timeout(400)
        sample = page.evaluate(SAMPLE, SAMPLE_MS) if deep else None
        gl = page.evaluate(GLINFO)
        gpu = page.evaluate(GPU) if deep else None
        lods = page.evaluate(LODS) if deep else None
        unload = page.evaluate(UNLOAD, ROAD) if deep else None
        fallback = page.evaluate(FALLBACK) if deep else None
        final = page.evaluate("() => TERRA_LEP.stats")
        return {
            'viewport': {'w': width, 'h': height}, 'ready': ready, 'road': road, 'ind': ind,
            'shots': shots, 'sample': sample, 'gl': gl, 'gpu': gpu, 'lods': lods,
            'unload': unload, 'fallback': fallback, 'final': final, 'errors': errors,
        }
    finally:
        browser.close()


def main():
    if not CHROME:
        raise SystemExit('Chromium не найден')
    report = {'url': URL, 'chrome': CHROME}
    with sync_playwright() as p:
        report['desktop'] = run_view(p, 1280, 800, '1280x800', True)
        report['phone'] = run_view(p, 390, 844, '390x844', False)
        # Тот же кадр и та же трасса без слоя: примитивы Ie.prototype.lep.
        browser, page, errors = launch(p, 1280, 800)
        try:
            page.goto(URL + '?lep=0', wait_until='load')
            page.locator('#mNew').click()
            try:
                page.locator('#skip').click(timeout=15000)
            except Exception:
                pass
            page.wait_for_function(BOOT)
            off = page.evaluate("() => !!(window.TERRA_LEP && TERRA_LEP.enabled === false)")
            page.evaluate(PLACE, ROAD)
            page.evaluate("() => { for (const el of document.body.children) if (el.id !== 'c') el.style.visibility = 'hidden'; }")
            page.screenshot(path=str(OUT / '1280x800-road-primitive.png'))
            sample = page.evaluate(SAMPLE, SAMPLE_MS)
            report['primitive'] = {'enabled': off, 'errors': errors, 'sample': sample}
        finally:
            browser.close()
    (OUT / 'report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    desk = report['desktop']
    assert not desk['errors'], desk['errors'][:4]
    assert not report['phone']['errors'], report['phone']['errors'][:4]
    assert desk['lods']['names'] == ['lod0', 'lod1', 'lod1', 'lod2'], desk['lods']
    assert desk['lods']['lowName'] == 'lod2', desk['lods']
    assert desk['lods']['byLod']['lod0'] >= 1, desk['lods']
    assert desk['lods']['byLod']['lod2'] >= 1, desk['lods']
    assert str(desk['lods']['material']).startswith('p01101f2m1'), desk['lods']
    assert desk['fallback']['after']['fallback'] > desk['fallback']['before'], desk['fallback']
    assert any('missing' in e for e in desk['fallback']['after']['errors']), desk['fallback']
    assert desk['unload']['mark'] is True, desk['unload']
    assert desk['gpu']['gpuMs'] is None
    print('PASS')
    print('renderer', desk['gl']['renderer'])
    print('lods', json.dumps(desk['lods'], ensure_ascii=False))
    print('sample', json.dumps(desk['sample'], ensure_ascii=False))
    print('gpu', desk['gpu'])
    print('unload', desk['unload'])
    print('fallback', desk['fallback']['before'], '->', desk['fallback']['after']['fallback'], desk['fallback']['after']['errors'][:3])
    print('anchor', desk['final']['anchorErrMax'], 'replaced', desk['final']['replaced'], 'tris', desk['final']['tris'])
    prim = report['primitive']
    assert prim['enabled'] is True, prim
    assert not prim['errors'], prim['errors'][:4]
    print('primitive', json.dumps(prim['sample'], ensure_ascii=False))
    print('phone tris anchor', report['phone']['final']['anchorErrMax'], 'replaced', report['phone']['final']['replaced'])


if __name__ == '__main__':
    main()
