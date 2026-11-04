"""Serve only terra.html; verify assets, reward-save startup and the actual lab.

Run scripts/build-offline.py first. This HTTP isolation test does not claim a
direct file:// playtest, which may be blocked by the execution environment.
"""
from functools import partial
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import os, shutil, tempfile, threading
from urllib.parse import urlsplit
from playwright.sync_api import sync_playwright, expect

root = Path(__file__).resolve().parents[1]
source = Path(os.environ.get('TERRA_OFFLINE_FILE', root / 'terra.html'))
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-assets-offline-qa'))
out.mkdir(parents=True, exist_ok=True)
expect.set_options(timeout=30000)

class QuietHandler(SimpleHTTPRequestHandler):
    def log_message(self, *_):
        pass

with tempfile.TemporaryDirectory(prefix='terra-offline-only-') as folder:
    shutil.copyfile(source, Path(folder) / 'terra.html')
    server = ThreadingHTTPServer(('127.0.0.1', 0), partial(QuietHandler, directory=folder))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(
                executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome'),
                args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
            page = browser.new_page(viewport={'width':1280,'height':800})
            page.set_default_timeout(60000)
            errors, forbidden = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            def isolated(route):
                path = urlsplit(route.request.url).path
                if path in ['/terra.html','/favicon.ico']:
                    route.continue_()
                else:
                    forbidden.append(route.request.url)
                    route.abort()
            page.route('http://**/*', isolated)
            url = f'http://127.0.0.1:{server.server_port}/terra.html'
            page.goto(url, timeout=120000)
            page.wait_for_function('TERRA_BOOT_STATE.status==="ready" && window.game && game.sewers', timeout=120000)
            assert page.evaluate('TERRA_ASSETS.sewer_lab==="url:assets/sewer/lab/lab_kit.glb" && TERRA_ASSETS.sewer_mutant==="url:assets/sewer/mutant.glb"')
            assert page.evaluate('Object.hasOwn(TERRA_SEWER_BRIDGE.weapons,"sewer_sai")')
            page.locator('#mNew').click(); page.locator('#skip').click()
            page.wait_for_function('game.state==="play" && game.glb.hero && game.glb.sewer_lab && game.glb.sewer_mutant', timeout=120000)
            uid = page.evaluate('''() => {
              const weapon=game.makeWeapon('katana',0,0,null);weapon.wt='sewer_sai';
              game.p.weapons.push(weapon);game.p.eq[game.p.slot]=weapon;
              const saved=game.save();if(!saved?.ok)throw Error('Offline fixture save failed');return weapon.uid;
            }''')
            page.reload(timeout=120000)
            page.wait_for_function('TERRA_BOOT_STATE.status==="ready" && game.sewers', timeout=120000)
            page.locator('#mContinue').click()
            page.wait_for_function('(uid)=>game.state==="play" && game.p.weapons.some(w=>w.uid===uid && w.wt==="sewer_sai")', arg=uid)
            page.wait_for_function('game.glb.sewer_lab && game.glb.sewer_mutant', timeout=120000)
            page.evaluate('game.p.hp=game.p.maxHp=10000;game.p.x=12;game.p.z=-10;game.camT=null')
            page.locator('#sewerAction').click()
            page.wait_for_function('game.dg?.sewer && !game.dungeonTransition')
            page.evaluate('const r=game.dg.ch.rooms[2];game.p.x=r.x;game.p.z=r.z;game.camT=null')
            page.wait_for_function('game.world.scene.getObjectByName("sewerLab")?.visible')
            lab = page.evaluate('''() => {
              const lab=game.world.scene.getObjectByName('sewerLab');let meshes=0;
              lab.traverse(node=>{if(node.isMesh)meshes++;});
              return {meshes,source:!!game.glb.sewer_lab.src.getObjectByName('vat'),mutant:!!game.glb.sewer_mutant.src};
            }''')
            assert lab['meshes']>0 and lab['source'] and lab['mutant'],lab
            page.screenshot(path=str(out / 'offline-laboratory.png'))
            assert not forbidden,forbidden
            assert not errors,errors
            browser.close()
            print('PASS standalone HTML: embedded pack, save/reload/continue with sewer_sai, actual lab and mutant; external requests 0, JS errors 0',lab,flush=True)
    finally:
        server.shutdown(); server.server_close()
