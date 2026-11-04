"""[art] Оружие и инструменты в руках героя: модели из held.glb подменяют геометрию Xg/$g героя,
?art=0 оставляет исходную; JS-ошибок нет. Одноразовый профиль браузера, личные сохранения не трогаются.
Запуск: python3 -m http.server 8080 из корня репо, затем
TERRA_CHROMIUM=/usr/bin/google-chrome python3 tests/art-held.py"""
import os, shutil
from playwright.sync_api import sync_playwright

base = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
if not chromium:
    raise SystemExit('Set TERRA_CHROMIUM to Chromium/Chrome.')
EQUIP = "(k)=>{const it=Object.assign({},game.p.eq[game.p.slot]||{},{wt:k,uid:'test-'+k,r:0,g:0,e:0,mag:6});delete it.m;game.p.eq[game.p.slot]=it}"

def run(p, query, art):
    b = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    pg = b.new_page(viewport={'width': 390, 'height': 844}); pg.set_default_timeout(90000)
    errors = []
    pg.on('pageerror', lambda e: errors.append(str(e)))
    pg.on('console', lambda m: errors.append(m.text) if m.type == 'error' else None)
    pg.goto(base + query, wait_until='load'); pg.wait_for_timeout(2500)
    pg.locator('#mNew').click(); pg.wait_for_timeout(800)
    try: pg.locator('#skip').click(timeout=15000)
    except Exception: pass
    pg.wait_for_timeout(3000)
    pg.evaluate("()=>{game.p.level=30;setInterval(()=>{game.p.hp=game.p.maxHp||100},50)}")
    seen = {}
    for k in ['katana', 'rifle', 'stick']:
        pg.evaluate(EQUIP, k); pg.wait_for_timeout(1200)
        seen[k] = pg.evaluate("()=>game.wMesh.geometry.userData.terraArt||null")
    shown = pg.evaluate("()=>TERRA_ART.heldShowcase()")
    st = pg.evaluate("()=>TERRA_ART.heldStats")
    b.close()
    assert not errors, errors[:3]
    assert not st['errors'], st['errors']
    for k, v in seen.items():
        assert (v == 'w_' + k) if art else v is None, (k, v)
    assert shown == 18, shown
    return seen, st

with sync_playwright() as p:
    print('art on ', run(p, '?artpreview=weapons', True))
    print('art off', run(p, '?artpreview=weapons&art=0', False))
print('PASS held weapon/tool models replace hero geometry and fall back cleanly')
