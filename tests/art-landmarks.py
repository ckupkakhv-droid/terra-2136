"""[art] Модели ориентиров: загрузка GLB, замена в чанке, откат ?art=0, отсутствие JS-ошибок.
Запуск: python3 -m http.server 8080 из корня репо, затем
TERRA_CHROMIUM=/usr/bin/google-chrome python3 tests/art-landmarks.py
Использует одноразовый профиль браузера, личные сохранения не трогает."""
import os, shutil
from playwright.sync_api import sync_playwright

base = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
if not chromium:
    raise SystemExit('Set TERRA_CHROMIUM to Chromium/Chrome.')

def run(p, query, expect_replaced):
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
    pg.evaluate("()=>{setInterval(()=>{game.p.hp=game.p.maxHp||100;game.p.rad=0},50);TERRA_ART.goto('water_tower',0,10)}")
    pg.wait_for_timeout(8000)
    st = pg.evaluate("()=>TERRA_ART.stats")
    b.close()
    assert not errors, errors[:3]
    assert not st['errors'], st['errors']
    assert (st['replaced'] > 0) == expect_replaced, st
    return st

with sync_playwright() as p:
    print('art on ', run(p, '?artpreview=landmarks', True))
    print('art off', run(p, '?artpreview=landmarks&art=0', False))
print('PASS landmark models load, replace, and fall back cleanly')
