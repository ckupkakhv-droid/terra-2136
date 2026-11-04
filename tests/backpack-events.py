"""Регрессии обработчиков рюкзака в Chrome, без мира и записи сохранений.
Запуск: python3 tests/backpack-events.py (Playwright и Chrome/Chromium).
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

source = Path(__file__).resolve().parents[1] / 'play/ui/backpack.js'
chrome = os.environ.get('TERRA_CHROMIUM') or shutil.which('google-chrome') or shutil.which('chromium')
if not chrome:
    raise SystemExit('Не найден Chrome/Chromium')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=chrome)
    page = browser.new_page()
    page.set_content('<div id="inv"><div id="invBody"><div class="tile" data-w="1">Предмет</div></div></div>')
    page.evaluate('''() => {
      window.calls = {equip: 0, select: 0, mutations: 0};
      window.game = {
        p: {weapons: [{uid: 1, wt: 'stick'}], slot: 0},
        ui: {tab: 'eq', renderInv() {}},
        equipWeapon(uid, slot) {
          if (uid !== 1 || slot !== 0) throw Error('Неверный предмет/слот');
          calls.equip++; return true;
        }
      };
      document.getElementById('inv').addEventListener('click', () => calls.select++);
      new MutationObserver(records => calls.mutations += records.length)
        .observe(document.getElementById('inv'), {attributes:true, attributeFilter:['class']});
      window.clickTile = () => document.querySelector('.tile').dispatchEvent(
        new MouseEvent('click', {bubbles:true, cancelable:true}));
      window.delay = ms => new Promise(resolve => setTimeout(resolve, ms));
    }''')
    page.add_script_tag(path=str(source))
    page.wait_for_function("document.getElementById('inv').classList.contains('bp')")
    page.wait_for_timeout(150)
    initial = page.evaluate('calls.mutations')
    page.wait_for_timeout(250)
    assert page.evaluate('calls.mutations') == initial, 'Оформление повторно изменяет class каждый кадр'
    assert initial == 1, initial
    single = page.evaluate('''async () => {
      clickTile(); await delay(220);
      const early = calls.select;
      await delay(220);
      return {early, select: calls.select, equip: calls.equip};
    }''')
    assert single == {'early': 0, 'select': 1, 'equip': 0}, single
    # Второй тап после прежнего таймера 280 мс, но внутри окна 380 мс.
    double = page.evaluate('''async () => {
      calls.select = 0; clickTile(); await delay(320); clickTile();
      await delay(420);
      return {select: calls.select, equip: calls.equip};
    }''')
    assert double == {'select': 0, 'equip': 1}, double
    separate = page.evaluate('''async () => {
      calls.select = 0; calls.equip = 0;
      clickTile(); await delay(440); clickTile(); await delay(440);
      return {select: calls.select, equip: calls.equip};
    }''')
    assert separate == {'select': 2, 'equip': 0}, separate
    browser.close()
    print('PASS: оформление стабильно; одиночный, двойной 320 мс и раздельные клики')
