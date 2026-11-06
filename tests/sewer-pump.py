"""Насос I: жизненный цикл модели, три LOD, откат к старому ящику.

Один прогон. Не выпускает игру и не пишет profile v3.
Скриншоты и цифры: docs/art/sewer-pump1/ и TERRA_QA_OUTPUT.
"""
import hashlib
import json
import os
import shutil
from pathlib import Path

from PIL import Image
from playwright.sync_api import expect, sync_playwright

ROOT = Path(__file__).resolve().parents[1]
OUT = Path(os.environ.get('TERRA_QA_OUTPUT', ROOT / 'docs' / 'art' / 'sewer-pump1'))
OUT.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
expect.set_options(timeout=30000)

GLB = ROOT / 'play/assets/sewer/pump/pump1.glb'
MANIFEST = json.loads((ROOT / 'play/assets/sewer/pump/manifest.json').read_text(encoding='utf-8'))
raw = GLB.read_bytes()
assert hashlib.sha256(raw).hexdigest() == MANIFEST['sha256']
assert raw[:4] == b'glTF'
assert b'EXT_meshopt_compression' in raw
assert MANIFEST['triangles'] == {'lod0': 774, 'lod1': 483, 'lod2': 158}
assert MANIFEST['triangles']['lod0'] <= 2000
assert MANIFEST['third_party'] == []
print('packed', MANIFEST['bytes'], 'bytes', MANIFEST['sha256'][:12], flush=True)

CHUNK = r'''
() => {
  const bridge = window.TERRA_SEWER_BRIDGE;
  const pump = window.TERRA_PUMP1;
  function build(enabled) {
    const prev = pump.enabled;
    pump.enabled = enabled;
    const chunk = new bridge.Chunk(4, -2);
    chunk.dungeon('metro', '12,-10');
    pump.enabled = prev;
    return chunk;
  }
  function excise(full, part) {
    if (part.length >= full.length || (full.length - part.length) % 3) return null;
    let i = 0;
    while (i < part.length && full[i] === part[i]) i++;
    let j = 0;
    while (j < part.length - i && full[full.length - 1 - j] === part[part.length - 1 - j]) j++;
    if (i + j !== part.length) return null;
    return {at: i, removed: full.length - part.length};
  }
  function hash(arr) {
    let h = 2166136261;
    for (let k = 0; k < arr.length; k++) h = Math.imul(h ^ Math.round(arr[k] * 1e6), 16777619);
    return h >>> 0;
  }
  const offA = build(false), offB = build(false), on = build(true);
  const same = offA.s.p.length === offB.s.p.length && offA.s.p.every((v, i) => v === offB.s.p[i] && offA.s.c[i] === offB.s.c[i]);
  const pos = excise(offA.s.p, on.s.p), col = excise(offA.s.c, on.s.c);
  let pumpVerts = 0;
  if (pos) for (let k = pos.at; k < pos.at + pos.removed; k += 3) {
    if (Math.abs(offA.s.p[k] - 220) < 1.2 && Math.abs(offA.s.p[k + 2] + 88) < 1.2) pumpVerts++;
  }
  const cont = JSON.stringify(offA.conts) === JSON.stringify(on.conts);
  return {
    same, pos, col, pumpVerts, cont,
    cols: offA.cols.length === on.cols.length,
    hash: hash(offA.s.p) ^ hash(offA.s.c),
    onHash: hash(on.s.p) ^ hash(on.s.c),
  };
}
'''

SHOT = r'''
(distance) => {
  const pump = TERRA_PUMP1, group = pump.group, cam = game.cam;
  const at = group.position;
  const dir = {x: 0.15, y: 0.72, z: 1};
  const len = Math.hypot(dir.x, dir.y, dir.z);
  cam.position.set(at.x + dir.x / len * distance, at.y + dir.y / len * distance, at.z + dir.z / len * distance);
  cam.lookAt(at.x, at.y + 0.7, at.z);
  cam.updateMatrixWorld();
  const level = pump.select(cam);
  game.ren.info.reset();
  game.post.render(game.world.scene, cam, 0);
  const info = game.ren.info;
  const mesh = group.children[level];
  return {
    level, distance: pump.distance,
    calls: info.render.calls, triangles: info.render.triangles,
    geometries: info.memory.geometries, textures: info.memory.textures,
    meshTris: mesh.geometry.attributes.position.count / 3,
    culled: group.children.every(child => child.frustumCulled === true),
  };
}
'''


def chrome():
    return os.environ.get('TERRA_CHROMIUM') or shutil.which('google-chrome') or shutil.which('chromium')


def launch(playwright):
    path = chrome()
    if not path:
        raise SystemExit('Нет Chrome/Chromium, кадр не снят')
    args = ['--no-sandbox', '--disable-dev-shm-usage', '--use-angle=swiftshader', '--enable-unsafe-swiftshader']
    return playwright.chromium.launch(executable_path=path, args=args)


def boot(page, query=''):
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' and 'favicon' not in message.location.get('url', '') else None)
    page.goto(URL + query, timeout=120000)
    page.wait_for_function('!document.getElementById("terraBoot")', timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('window.game && game.sewers && window.TERRA_PUMP1', timeout=120000)
    return errors


def enter(page):
    page.evaluate('game.p.x=12; game.p.z=-10; game.p.hp=game.p.maxHp=10000')
    page.locator('#sewerAction').wait_for(state='visible')
    page.locator('#sewerAction').click()
    page.wait_for_function('!!game.dg && !game.dungeonTransition && game.dg.sewer === true')


def shoot(page, name):
    temporary = OUT / f'{name}.png'
    page.screenshot(path=str(temporary))
    Image.open(temporary).convert('RGB').save(OUT / f'{name}.jpg', quality=80, optimize=True)
    temporary.unlink()


def settle(page, times=4):
    page.evaluate('''(n) => { for (let i = 0; i < n; i++) game.loop(performance.now()); }''', times)


def main():
    report = {'manifest': MANIFEST['triangles'], 'bytes': MANIFEST['bytes'], 'sha256': MANIFEST['sha256']}
    with sync_playwright() as playwright:
        browser = launch(playwright)
        page = browser.new_page(viewport={'width': 1280, 'height': 800})
        page.set_default_timeout(30000)
        errors = boot(page)
        page.wait_for_function('TERRA_PUMP1.ready === true && TERRA_PUMP1.tris.lod0 === 774', timeout=60000)
        baseline = page.evaluate(CHUNK)
        assert baseline['same'], baseline
        assert baseline['pos'] and baseline['col'] and baseline['pos']['at'] == baseline['col']['at'], baseline
        assert baseline['pos']['removed'] == baseline['col']['removed'], baseline
        assert baseline['pumpVerts'] == baseline['pos']['removed'] // 3, baseline
        assert baseline['cont'] and baseline['cols'], baseline
        report['excisedVertices'] = baseline['pos']['removed']
        report['primitiveHash'] = baseline['hash']
        print('geometry fallback matches, excised pump I verts', baseline['pos']['removed'], flush=True)
        saved = page.evaluate('''() => { game.save(); const data = JSON.parse(localStorage.getItem('terra_save')); return {v: data.v, keys: Object.keys(data).sort(), profile: data.p.classProfile ? data.p.classProfile.v : null}; }''')

        enter(page)
        settle(page, 6)
        page.wait_for_function('game.dg.flood === true')
        page.evaluate('game.ui.openMap()')
        page.locator('#sewerLayerButton').click()
        expect(page.locator('#sewerMap')).to_be_visible()
        text = page.locator('#sewerMap').inner_text()
        assert 'Насос I' in text and 'Насос II' in text, text
        page.locator('#sewerMap .x').click()
        page.keyboard.press('Escape')
        page.wait_for_function('game.state === "play"')

        page.wait_for_function('TERRA_PUMP1.group && TERRA_PUMP1.group.parent === game.world.scene')
        body = page.evaluate(r'''() => {
          const group = TERRA_PUMP1.group;
          const stat = game.dg.ch.meshes.find(mesh => mesh.geometry.getAttribute('aux'));
          const box = group.children[0].geometry.boundingBox;
          const top = group.position.y + box.max.y;
          const names = group.children.map(child => child.name);
          return {
            shared: group.children.every(child => child.material === stat.material),
            culled: group.children.every(child => child.frustumCulled === true),
            lights: group.children.every(child => !child.isLight) && ![...group.children].some(child => child.type === 'Light'),
            top, playerY: game.p.y, floor: group.position.y + box.min.y,
            box: {min: box.min.toArray(), max: box.max.toArray()},
            names,
            save: (game.save(), JSON.parse(localStorage.getItem('terra_save')).v),
            profile: game.p.classProfile ? game.p.classProfile.v : null,
          };
        }''')
        assert body['shared'] and body['culled'], body
        assert body['top'] < body['playerY'] + 2.35, body
        assert body['box']['min'][1] >= 0.19 and body['box']['max'][1] <= 1.77, body
        assert abs(body['box']['min'][0]) <= 0.71 and body['box']['max'][0] <= 0.71, body
        assert body['names'] == ['sewer-pump-1-lod0', 'sewer-pump-1-lod1', 'sewer-pump-1-lod2']
        report['body'] = body
        save_version = body['save']

        room = page.evaluate(r'''() => {
          const room = game.dg.ch.rooms[1];
          const samples = [];
          for (let step = 0; step <= 8; step++) {
            const x = room.x + 4 * step / 8, z = room.z;
            samples.push(game.world.collide({x, z}, 0.3));
          }
          game.p.x = room.x + 4; game.p.z = room.z;
          return {samples, blocked: samples.some(Boolean)};
        }''')
        assert room['blocked'] is False, room

        page.wait_for_function('document.getElementById("sewerAction").textContent.includes("насос")')
        page.locator('#sewerAction').click()
        page.wait_for_function('game.sewers.pumps.length === 1 && game.sewers.pumps[0] === 1')
        state = page.evaluate('''() => {
          const room = game.dg.ch.rooms[1];
          game.p.x = room.x; game.p.z = room.z; game.p.hp = 10000;
          game.dungeonUpdate(0);
          return {flood: game.dg.flood, pumps: [...game.sewers.pumps]};
        }''')
        assert state['flood'] is True and state['pumps'] == [1], state
        inv = page.evaluate('JSON.stringify(game.p.inv)')
        page.evaluate("game.rollLoot('sewer_raphael')")
        assert page.evaluate('JSON.stringify(game.p.inv)') == inv
        kept = page.evaluate('''() => { const result = game.save(); const data = JSON.parse(localStorage.getItem('terra_save')); return {result, v: data.v, keys: Object.keys(data).sort(), profile: data.p.classProfile ? data.p.classProfile.v : null}; }''')
        assert kept['result']['reason'] == 'dungeon' and kept['v'] == saved['v'] and kept['keys'] == saved['keys'] and kept['profile'] == saved['profile'], kept

        page.evaluate('''(flag) => { game.world.scene.traverse(obj => { if (obj.isMesh) { obj.userData._cull = obj.frustumCulled; obj.frustumCulled = flag; } }); TERRA_PUMP1.frame(game); }''', False)
        assert page.evaluate('TERRA_PUMP1.group.children.every(child => child.frustumCulled === true)')
        page.evaluate('''() => { game.world.scene.traverse(obj => { if (obj.isMesh && obj.userData._cull !== undefined) obj.frustumCulled = obj.userData._cull; }); }''')

        page.evaluate('const room = game.dg.ch.rooms[1]; game.p.x = room.x + 1.1; game.p.z = room.z + 2.4')
        settle(page, 6)
        assert page.evaluate('TERRA_PUMP1.level === 0 && TERRA_PUMP1.distance < TERRA_PUMP1.bands[0]')
        play = page.evaluate(r'''() => {
          const info = game.ren.info;
          return {calls: info.render.calls, triangles: info.render.triangles, geometries: info.memory.geometries, textures: info.memory.textures, level: TERRA_PUMP1.level, distance: TERRA_PUMP1.distance};
        }''')
        shoot(page, 'after-desktop')
        page.set_viewport_size({'width': 390, 'height': 844})
        settle(page, 4)
        shoot(page, 'after-mobile')
        page.set_viewport_size({'width': 1280, 'height': 800})
        settle(page, 2)
        report['play'] = play

        hidden = page.evaluate(r'''() => {
          const group = TERRA_PUMP1.group;
          group.visible = false;
          game.ren.info.reset();
          game.post.render(game.world.scene, game.cam, 0);
          const hiddenInfo = {calls: game.ren.info.render.calls, triangles: game.ren.info.render.triangles, geometries: game.ren.info.memory.geometries, textures: game.ren.info.memory.textures};
          group.visible = true;
          TERRA_PUMP1.select(game.cam);
          game.ren.info.reset();
          game.post.render(game.world.scene, game.cam, 0);
          const shown = {calls: game.ren.info.render.calls, triangles: game.ren.info.render.triangles, geometries: game.ren.info.memory.geometries, textures: game.ren.info.memory.textures};
          return {hidden: hiddenInfo, shown};
        }''')
        report['draw'] = {
            'calls': hidden['shown']['calls'] - hidden['hidden']['calls'],
            'triangles': hidden['shown']['triangles'] - hidden['hidden']['triangles'],
            'geometries': hidden['shown']['geometries'],
            'textures': hidden['shown']['textures'],
            'texturesUnchanged': hidden['shown']['textures'] == hidden['hidden']['textures'],
        }
        assert report['draw']['texturesUnchanged']
        assert report['draw']['calls'] >= 1
        assert 0 < report['draw']['triangles'] <= 2000 * 4, report['draw']

        lods = []
        for distance, name in ((18, 'lod0'), (40, 'lod1'), (64, 'lod2')):
            shot = page.evaluate(SHOT, distance)
            assert shot['level'] == ['lod0', 'lod1', 'lod2'].index(name), shot
            assert shot['meshTris'] == MANIFEST['triangles'][name], shot
            assert shot['culled']
            shoot(page, name)
            lods.append({'name': name, **shot})
        report['lod'] = lods
        settle(page, 2)

        released = page.evaluate(r'''() => {
          const before = game.ren.info.memory.geometries;
          const ids = TERRA_PUMP1.group.children.map(child => child.uuid);
          TERRA_PUMP1.detach();
          return {
            before, after: game.ren.info.memory.geometries,
            left: !!game.world.scene.getObjectByName('sewer-pump-1'),
            ids,
            gone: ids.every(id => !game.world.scene.getObjectByProperty('uuid', id)),
          };
        }''')
        assert released['left'] is False and released['gone'] and released['after'] == released['before'] - 3, released
        page.evaluate('game.exitDungeon()')
        page.wait_for_function('!game.dg && !game.dungeonTransition')
        page.evaluate('TERRA_PUMP1.frame(game)')
        assert page.evaluate('!TERRA_PUMP1.group')
        report['disposed'] = released

        enter(page)
        page.wait_for_function('game.sewers.pumps.length === 0')
        page.wait_for_function('TERRA_PUMP1.group && TERRA_PUMP1.group.parent')
        fresh = page.evaluate('TERRA_PUMP1.group.children.map(child => child.uuid)')
        assert set(fresh).isdisjoint(released['ids']), fresh
        assert not errors, errors
        print('play draw delta', report['draw'], 'lod', [(item['name'], item['level'], item['distance'], item['meshTris']) for item in lods], flush=True)
        page.close()

        blank = browser.new_page(viewport={'width': 1280, 'height': 800})
        blank.set_default_timeout(30000)
        blank_errors = boot(blank, '?pump1=0')
        assert blank.evaluate('TERRA_PUMP1.enabled === false && TERRA_PUMP1.ready === false')
        off = blank.evaluate(CHUNK)
        assert off['hash'] == baseline['hash'], (off['hash'], baseline['hash'])
        assert off['onHash'] == off['hash']
        enter(blank)
        page_group = blank.evaluate('!!TERRA_PUMP1.group')
        assert page_group is False
        blank.evaluate('const room = game.dg.ch.rooms[1]; game.p.x = room.x + 1.1; game.p.z = room.z + 2.4')
        settle(blank, 6)
        shoot(blank, 'before-desktop')
        blank.set_viewport_size({'width': 390, 'height': 844})
        settle(blank, 4)
        shoot(blank, 'before-mobile')
        textures = blank.evaluate('game.ren.info.memory.textures')
        report['fallbackTextures'] = textures
        report['textureDelta'] = report['draw']['textures'] - textures
        assert not blank_errors, blank_errors
        blank.close()

        failed = browser.new_page(viewport={'width': 1280, 'height': 800})
        failed.set_default_timeout(30000)
        failed.route('**/assets/sewer/pump/pump1.glb*', lambda route: route.abort())
        failed_errors = boot(failed)
        failed.wait_for_function('TERRA_PUMP1.failed === true && TERRA_PUMP1.ready === false', timeout=60000)
        failed_chunk = failed.evaluate(CHUNK)
        assert failed_chunk['hash'] == baseline['hash'], failed_chunk
        enter(failed)
        assert failed.evaluate('!TERRA_PUMP1.group')
        assert failed.evaluate('game.dg.flood === true')
        webgl = failed.evaluate('!!game.ren.getContext()')
        assert webgl
        assert not [item for item in failed_errors if 'pump1' not in item and 'Failed to load' not in item and 'net::' not in item], failed_errors
        browser.close()

    (OUT / 'measures.json').write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n', encoding='utf-8')
    print('PASS', json.dumps({k: report[k] for k in ('excisedVertices', 'draw', 'disposed', 'textureDelta')}, ensure_ascii=False), flush=True)


if __name__ == '__main__':
    main()
