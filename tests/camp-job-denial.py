"""Причины отказа в личном деле: известный запрет, срыв доставки, занятый курьер.

Сервер из корня репозитория, Python Playwright и Chromium/Chrome.
Чистый профиль: сохранённая игра не читается. Приказы идут штатной кнопкой
game.camp.assign. Поля profile не добавляются.
"""
import os
import shutil
from pathlib import Path
from playwright.sync_api import expect, sync_playwright

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-job-denial'))
out.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
GENERIC = {'', 'Нет доступной цели', 'Сейчас недоступно', 'Сейчас нельзя', 'Простой'}

CASES = r"""() => {
  const api = window.terraCampFieldbook;
  const camp = {sim:{tick:10}, buildings:{}, routes:{}, res:{wood:0}, settlers:{}, warehouseCourier:null};
  const free = {id:'a', job:'idle', status:'idle', needs:{rest:80}, order:{}};
  const stick = {id:'a', job:'idle', status:'idle', needs:{rest:80}, order:{stick:1}};
  const hurt = {id:'a', job:'idle', status:'injured', injuredUntil:40, needs:{rest:80}, order:{stick:1}};
  const healed = {id:'a', job:'idle', status:'idle', needs:{rest:80}, order:{stick:1}};
  const haul = {id:'a', job:'haul:qa', status:'blocked', needs:{rest:80}, order:{stick:1}};
  camp.routes.qa = {from:'camp', res:'wood'};
  const denied = {
    operate: api.jobHold({buildings:{}, routes:{}, settlers:{}}, {id:'a', prof:'gatherer', job:'idle', order:{}}, 'operate'),
    build: api.jobHold({buildings:{}, routes:{}, settlers:{}}, {id:'a', prof:'gatherer', job:'idle', order:{}}, 'build'),
    haul: api.jobHold({buildings:{}, routes:{}, settlers:{}}, {id:'a', prof:'gatherer', job:'idle', order:{}}, 'haul'),
    courier: api.jobHold({buildings:{}, routes:{}, settlers:{}, warehouseCourier:{settlerId:'a'}}, {id:'a', prof:'engineer', job:'idle', order:{}}, 'gather:wood'),
    cargo: api.jobHold({buildings:{}, routes:{}, settlers:{}}, {id:'a', prof:'gatherer', trip:{amount:1}, order:{}}, 'gather:wood'),
  };
  return {
    courier: api.denialText('courier-busy'),
    cargo: api.denialText('cargo'),
    unknown: api.denialText('not-a-status'),
    free: api.activity(free, camp),
    stick: api.activity(stick, camp),
    hurt: api.activity(hurt, camp),
    healed: api.activity(healed, camp),
    delivery: api.activity(haul, camp),
    denied,
  };
}"""


def visible_count(page, phrase):
    return page.evaluate("""phrase => [...document.querySelectorAll('body *')].filter(node => {
      const own = [...node.childNodes].filter(item => item.nodeType === 3).map(item => item.textContent).join('');
      if (!own.includes(phrase)) return false;
      const style = getComputedStyle(node);
      return style.display !== 'none' && style.visibility !== 'hidden' && node.getClientRects().length
        && !node.closest('[hidden], details:not([open]) > :not(summary)');
    }).length""", phrase)


def shot(page, name):
    page.screenshot(path=str(out / name), animations='disabled')


def open_card(page):
    if page.locator('.fbAssignment').count() == 0:
        resident = page.locator('[data-resident="qa-denial"]')
        if resident.count() == 0:
            folder = page.locator('[data-fieldbook-section="settlers"]')
            if folder.count() and folder.is_visible():
                folder.tap()
            else:
                page.evaluate("game.ui.campPanel.select('settlers')")
        page.locator('[data-resident="qa-denial"]').tap()
    expect(page.locator('.fbAssignment')).to_be_visible()


def show_jobs(page):
    open_card(page)
    if page.locator('.campJobs').evaluate('node => getComputedStyle(node).display === "none"'):
        page.locator('.fbChangeJob').tap()
    expect(page.locator('.campJobs')).to_be_visible()


with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, is_mobile=True, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.add_init_script("localStorage.removeItem('terra_save')")
    page.goto(URL, wait_until='load', timeout=120000)
    page.locator('#mNew').tap()
    page.locator('#skip').tap()
    expect(page.locator('#hud')).to_be_visible()
    page.wait_for_function('() => window.terraCampFieldbook && window.terraCampFieldbook.denialText')
    cases = page.evaluate(CASES)
    assert cases['courier'] == 'Житель выполняет поручение курьера', cases
    assert cases['cargo'] == 'Дождитесь доставки груза', cases
    assert cases['unknown'] == '', cases
    assert cases['free'] == 'Свободен', cases
    assert cases['stick'] == 'Ручной отдых · автоназначение выключено', cases
    assert 'Свободен' not in cases['stick'] and 'Простой' not in cases['stick']
    assert cases['hurt'] == 'Ранен · ждёт восстановления', cases
    assert cases['healed'] == cases['stick'], cases
    assert cases['delivery'] == 'Нет груза на складе отправления', cases
    assert cases['denied'] == {
        'operate': 'Нужен инженер',
        'build': 'Нет свободной стройки',
        'haul': 'Маршрут недоступен',
        'courier': 'Житель выполняет поручение курьера',
        'cargo': 'Дождитесь доставки груза',
    }, cases['denied']
    live = Path(__file__).resolve().parents[1].joinpath('play/ui/camp-live.js').read_text(encoding='utf-8')
    assert 'terraCampFieldbook?.denialText' in live

    recruited = page.evaluate("""() => {
      game.p.camp.rep = Math.max(game.p.camp.rep || 0, 1000);
      const result = game.camp.recruit({id:'qa-denial', name:'Павел Испытатель', prof:'gatherer'});
      return result;
    }""")
    assert recruited.get('ok'), recruited
    save_after_recruit = page.evaluate("localStorage.getItem('terra_save')")
    page.locator('#bCamp').tap()
    expect(page.locator('#campPanel')).to_be_visible()
    open_card(page)
    shot(page, 'before-card.png')
    assert page.locator('.fbActivity').inner_text() == 'Свободен'
    show_jobs(page)
    reasons = page.evaluate("""() => Object.fromEntries([...document.querySelectorAll('.campJobs [data-resident-job]:disabled')].map(button => {
      const note = document.getElementById((button.getAttribute('aria-describedby') || '').split(' ').pop());
      return [button.dataset.residentJob, {title: button.title, note: note ? note.textContent : '', described: !!note}];
    }))""")
    for job, expected in (('operate', 'Нужен инженер'), ('build', 'Нет свободной стройки'), ('haul', 'Маршрут недоступен')):
        assert reasons[job]['title'] == expected, reasons[job]
        assert reasons[job]['note'] == expected, reasons[job]
        assert reasons[job]['title'] not in GENERIC
        assert reasons[job]['described']
    assert len({reasons['operate']['note'], reasons['build']['note'], reasons['haul']['note']}) == 3
    link = page.locator('[data-resident-job="build"]').locator('..').locator('.residentJobLink')
    expect(link).to_be_visible()
    assert link.bounding_box()['height'] >= 44
    shot(page, 'after-denied-jobs.png')

    page.locator('[data-resident-job="idle"]').tap()
    expect(page.locator('.campResidents')).to_contain_text('Назначение принято')
    assert page.evaluate("game.p.camp.settlers['qa-denial'].order.stick === 1")
    assert page.evaluate("game.p.camp.settlers['qa-denial'].job === 'idle'")
    expect(page.locator('.fbActivity')).to_have_text('Ручной отдых · автоназначение выключено')
    assert visible_count(page, 'Ручной отдых · автоназначение выключено') == 1
    assert visible_count(page, 'Свободен') == 0
    shot(page, 'after-stick.png')

    page.evaluate("""() => {
      const settler = game.p.camp.settlers['qa-denial'];
      settler.status = 'injured';
      settler.injuredUntil = game.p.camp.sim.tick + 80;
      game.ui.campPanel.select('settlers');
    }""")
    open_card(page)
    expect(page.locator('.fbActivity')).to_have_text('Ранен · ждёт восстановления')
    assert visible_count(page, 'Ранен') == 1
    assert visible_count(page, 'Ручной отдых') == 0
    assert visible_count(page, 'Свободен') == 0
    shot(page, 'after-injured.png')

    page.evaluate("""() => {
      const settler = game.p.camp.settlers['qa-denial'];
      delete settler.injuredUntil;
      settler.status = 'idle';
      game.ui.campPanel.select('settlers');
    }""")
    open_card(page)
    expect(page.locator('.fbActivity')).to_have_text('Ручной отдых · автоназначение выключено')
    assert visible_count(page, 'Ранен') == 0
    assert visible_count(page, 'Ручной отдых · автоназначение выключено') == 1
    assert visible_count(page, 'Свободен') == 0
    assert visible_count(page, 'Простой') == 0
    shot(page, 'after-healed-stick.png')

    page.evaluate("""() => {
      game.p.camp.routes['qa-denial'] = {from:'camp', to:'camp', res:'wood'};
      game.p.camp.res.wood = 0;
      game.ui.campPanel.select('settlers');
    }""")
    show_jobs(page)
    page.locator('[data-resident-job="haul"]').tap()
    target = page.locator('.campTargets button').filter(has_text='qa-denial')
    if target.count():
        target.tap()
    expect(page.locator('.campResidents')).to_contain_text('Назначение принято')
    assert page.evaluate("game.p.camp.settlers['qa-denial'].job === 'haul:qa-denial'")
    page.evaluate("""() => {
      const settler = game.p.camp.settlers['qa-denial'];
      settler.status = 'blocked';
      delete settler.workBlock;
      game.p.camp.res.wood = 0;
      game.ui.campPanel.select('settlers');
    }""")
    open_card(page)
    expect(page.locator('.fbActivity')).to_have_text('Нет груза на складе отправления')
    assert visible_count(page, 'Простой') == 0
    assert visible_count(page, 'Свободен') == 0
    shot(page, 'after-delivery-failure.png')

    page.evaluate("""() => {
      game.p.camp.settlers['qa-denial'].trip = {amount:2, res:'wood', returning:false};
      game.ui.campPanel.select('settlers');
    }""")
    show_jobs(page)
    page.locator('[data-resident-job="gather:wood"]').tap()
    expect(page.locator('.campResidents p.campReason')).to_have_text('Дождитесь доставки груза')
    assert visible_count(page, 'Дождитесь доставки груза') == 1
    page.locator('[data-resident-job="gather:wood"]').tap()
    expect(page.locator('.campResidents p.campReason')).to_have_count(1)
    assert visible_count(page, 'Дождитесь доставки груза') == 1
    shot(page, 'after-cargo.png')

    page.evaluate("""() => {
      const settler = game.p.camp.settlers['qa-denial'];
      delete settler.trip;
      game.p.camp.warehouseCourier = {v:1, shipmentId:'qa-ship', settlerId:'qa-denial'};
      game.ui.campPanel.select('settlers');
    }""")
    show_jobs(page)
    page.locator('[data-resident-job="gather:wood"]').tap()
    expect(page.locator('.campResidents p.campReason')).to_have_text('Житель выполняет поручение курьера')
    assert visible_count(page, 'Житель выполняет поручение курьера') == 1
    page.locator('[data-resident-job="gather:wood"]').tap()
    expect(page.locator('.campResidents p.campReason')).to_have_count(1)
    assert visible_count(page, 'Сейчас нельзя') == 0
    shot(page, 'after-courier-busy.png')

    page.locator('[data-camp-back="list"]').tap()
    page.locator('.fbCardOrder summary').tap()
    order = page.locator('[data-resident-order="qa-denial"]')
    expect(order).to_be_disabled()
    phrase = order.get_attribute('title')
    assert phrase not in GENERIC
    described = order.get_attribute('aria-describedby')
    assert described
    expect(page.locator('#' + described)).to_have_text(phrase)
    assert visible_count(page, phrase) == 1
    assert visible_count(page, 'Курьер · недоступен') == 0
    assert order.bounding_box()['height'] >= 44
    shot(page, 'after-order-command.png')

    keys = page.evaluate("""() => Object.keys(game.p.camp.settlers['qa-denial']).sort()""")
    assert 'v' not in keys
    assert page.evaluate("localStorage.getItem('terra_save')") == save_after_recruit
    assert not errors, errors
    print('PASS denied job reasons, delivery failure, cargo, courier-busy, injury and stick; no duplicate line; save untouched; JS 0')
    browser.close()
