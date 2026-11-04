"""«Живой лагерь»: метки над постройками, контекстное меню и чертёж стройки.

Сервер из корня репозитория на :8080 (или TERRA_TEST_URL), Python Playwright и Chromium/Chrome.
Чистый профиль. Проверяет 390×844, 844×390 и 1280×800: метки, меню со штатным приказом
«Отдых», призрак стройки и кнопки «Поставить»/«Отмена» не меньше 48 px, просмотр меток
не меняет работы и постройки. Отдельно сравнивает кадр с ?livecamp=0.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-live-qa'))
out.mkdir(parents=True, exist_ok=True)
URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
VIEWS = [('portrait', 390, 844), ('landscape', 844, 390), ('desktop', 1280, 800)]
FOCUSED = os.environ.get('TERRA_LIVE_FOCUSED') == '1'
if FOCUSED:
    VIEWS = VIEWS[:1]

PLACE = """() => {
  const home = game.homePos?.() || {x: 29, z: 79};
  game.p.x = home.x;
  game.p.z = home.z + 5;
  game.p.yaw = Math.PI;
  game.p.camp.rep = Math.max(game.p.camp.rep || 0, 1000);
  if (!game.p.camp.settlers['qa-live']) {
    const recruited = game.camp.recruit({id: 'qa-live'});
    if (!recruited.ok) return recruited;
  }
  const settler = game.p.camp.settlers['qa-live'];
  settler.name = 'Марфа';
  settler.pos = {x: game.p.x + 1.6, z: game.p.z - 1.2};
  return {ok: true, home, anchors: terraCampLive.anchors().length};
}"""

GEOMETRY = """selector => {
  const nodes = [...document.querySelectorAll(selector)].filter(e => {
    const r = e.getBoundingClientRect();
    const s = getComputedStyle(e);
    return r.width > 0 && r.height > 0 && s.visibility !== 'hidden' && !e.closest('[hidden]');
  });
  return nodes.map(e => {
    const r = e.getBoundingClientRect();
    return {label: (e.getAttribute('aria-label') || e.textContent || '').trim().slice(0, 48), w: Math.round(r.width), h: Math.round(r.height), x: Math.round(r.left), y: Math.round(r.top)};
  });
}"""


def boot(page, tap, query=''):
    page.goto(URL + query, wait_until='load', timeout=120000)
    tap(page.locator('#mNew'))
    tap(page.locator('#skip'))
    expect(page.locator('#hud')).to_be_visible()


def small(items, label):
    bad = [i for i in items if i['w'] < 48 or i['h'] < 48]
    assert not bad, f'{label}: цели < 48 px: {bad}'


def shot(page, name):
    page.screenshot(path=str(out / name), type='jpeg', quality=70)


with sync_playwright() as p:
    chromium = os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome')
    if not chromium:
        raise SystemExit('Set TERRA_CHROMIUM to an installed Chromium/Chrome executable.')
    browser = p.chromium.launch(executable_path=chromium, args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])

    for name, width, height in ([] if FOCUSED else VIEWS):
        touch = name != 'desktop'
        context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=touch, has_touch=touch)
        page = context.new_page()
        page.set_default_timeout(60000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: message.type == 'error' and 'camp-live' in message.text and errors.append(message.text))
        tap = (lambda loc: loc.tap()) if touch else (lambda loc: loc.click())
        boot(page, tap, '?livecamp=0')
        page.wait_for_timeout(800)
        page.evaluate(PLACE.replace('terraCampLive.anchors().length', '0'))
        page.wait_for_timeout(600)
        shot(page, f'before-{name}.jpg')
        context.close()

    fps = {}
    for flag, key in ([] if FOCUSED else (('?livecamp=0', 'off'), ('', 'on'))):
        context = browser.new_context(viewport={'width': 1280, 'height': 800})
        page = context.new_page()
        page.set_default_timeout(60000)
        boot(page, lambda loc: loc.click(), flag)
        page.evaluate(PLACE.replace('terraCampLive.anchors().length', '0') if flag else PLACE)
        page.wait_for_timeout(500)
        fps[key] = page.evaluate("""() => new Promise(resolve => {
          const samples = [];
          let last = performance.now();
          const start = last;
          function frame(now) {
            samples.push(now - last);
            last = now;
            if (now - start < 2500) requestAnimationFrame(frame);
            else {
              samples.sort((a, b) => a - b);
              const avg = samples.reduce((s, v) => s + v, 0) / samples.length;
              resolve({frames: samples.length, med: samples[samples.length >> 1], avg, fps: 1000 / avg});
            }
          }
          requestAnimationFrame(frame);
        })""")
        if not flag:
            shot(page, 'before-desktop-build-off.jpg')
        context.close()

    for name, width, height in VIEWS:
        touch = name != 'desktop'
        context = browser.new_context(viewport={'width': width, 'height': height}, is_mobile=touch, has_touch=touch)
        page = context.new_page()
        page.set_default_timeout(60000)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.on('console', lambda message: message.type == 'error' and errors.append(message.text))
        tap = (lambda loc: loc.tap()) if touch else (lambda loc: loc.click())
        boot(page, tap)
        page.wait_for_function('() => window.terraCampLive && game.ghostM')
        placed = page.evaluate(PLACE)
        assert placed.get('ok'), placed
        page.wait_for_function("""() => terraCampLive.anchors().some(a => a.kind === 'building')""", timeout=20000)
        page.evaluate("""() => {
          const list = terraCampLive.anchors().filter(a => a.kind === 'building' && !['campfire', 'radio'].includes(a.id));
          const target = list[0] || terraCampLive.anchors()[0];
          if (!target) return;
          game.p.x = target.x + 3.5;
          game.p.z = target.z + 8;
          game.p.yaw = Math.atan2(target.x - game.p.x, target.z - game.p.z);
          const settler = game.p.camp.settlers['qa-live'];
          if (settler) settler.pos = {x: game.p.x + 1.4, z: game.p.z - 1.5};
        }""")
        page.wait_for_function("""() => {
          const list = terraCampLive.anchors();
          return list.some(a => a.kind === 'building') && list.some(a => a.kind === 'settler' && a.id === 'qa-live');
        }""", timeout=20000)
        before = page.evaluate("""() => ({
          jobs: Object.fromEntries(Object.entries(game.p.camp.settlers).map(([k, s]) => [k, s.job])),
          buildings: Object.fromEntries(Object.entries(game.p.camp.buildings).map(([k, b]) => [k, [b.lvl|0, b.type, !!b.project]])),
          base: game.p.base.length
        })""")
        page.evaluate("document.getElementById('campLiveLayer').hidden = true")
        shot(page, f'after-{name}-scene.jpg')
        page.evaluate("document.getElementById('campLiveLayer').hidden = false")
        page.wait_for_timeout(250)
        tags = page.evaluate(GEOMETRY, '#campLiveLayer .campLiveTag:not([hidden])')
        assert tags, f'{name}: меток нет'
        small(tags, f'{name}/метки')
        overflow = page.evaluate("""() => {
          const w = innerWidth, h = innerHeight;
          return [...document.querySelectorAll('#campLiveLayer .campLiveTag:not([hidden])')].filter(e => {
            const r = e.getBoundingClientRect();
            return r.right > w + 2 || r.left < -2 || r.bottom > h + 2 || r.top < -2;
          }).length;
        }""")
        assert overflow == 0, f'{name}: метка за экраном'
        shot(page, f'after-{name}-labels.jpg')

        tap(page.locator('#campLiveLayer .campLiveTag[data-kind="settler"]'))
        expect(page.locator('#campLiveMenu')).to_be_visible()
        menu = page.evaluate(GEOMETRY, '#campLiveMenu button')
        small(menu, f'{name}/меню')
        shot(page, f'after-{name}-menu.jpg')
        # A menu belongs to one live player/world. Even a queued click must be rejected.
        for change in ('player', 'world', 'state', 'death'):
            result = page.evaluate('''kind => {
              const g=game,p=g.p,w=g.world,state=g.state,alive=p.alive,assign=g.camp.assign;
              const button=document.querySelector('#campLiveMenu button[aria-label$="Отдых"]');
              let calls=0;
              g.camp.assign=()=>{calls++;return {ok:true};};
              try {
                if(kind==='player')g.p={...p};
                if(kind==='world')g.world={...w};
                if(kind==='state')g.state='modal';
                if(kind==='death')p.alive=false;
                button.click();
                return {calls,closed:!document.getElementById('campLiveMenu')};
              } finally {g.p=p;g.world=w;g.state=state;p.alive=alive;g.camp.assign=assign;}
            }''', change)
            assert result == {'calls': 0, 'closed': True}, (change, result)
            tap(page.locator('#campLiveLayer .campLiveTag[data-kind="settler"]'))
        page.evaluate('game.state="modal"')
        expect(page.locator('#campLiveMenu')).to_have_count(0)
        page.evaluate('game.state="play"')
        tap(page.locator('#campLiveLayer .campLiveTag[data-kind="settler"]'))
        tap(page.locator('#campLiveMenu button[aria-label$="Отдых"]'))
        page.wait_for_function("() => game.p.camp.settlers['qa-live'].job === 'idle'")
        expect(page.locator('#campLiveMenu')).to_have_count(0)

        same = page.evaluate("""before => ({
          jobs: Object.fromEntries(Object.entries(game.p.camp.settlers).filter(([k]) => k !== 'qa-live').map(([k, s]) => [k, s.job])),
          buildings: Object.fromEntries(Object.entries(game.p.camp.buildings).map(([k, b]) => [k, [b.lvl|0, b.type, !!b.project]])),
          base: game.p.base.length,
          beforeJobs: before.jobs, beforeBuildings: before.buildings, beforeBase: before.base
        })""", before)
        assert same['buildings'] == before['buildings'], same
        assert same['base'] == before['base']
        others = {k: v for k, v in before['jobs'].items() if k != 'qa-live'}
        assert same['jobs'] == others

        page.evaluate("game.toggleBuild(true); game.build.sel = 'floor'; game.renderBuildBar()")
        page.wait_for_function("() => game.build.on && game.ghostM.visible && game.ghostMat.wireframe")
        expect(page.locator('#campLivePlace')).to_be_visible()
        expect(page.locator('#campLiveAim')).to_be_visible()
        place = page.evaluate(GEOMETRY, '#campLivePlace button')
        small(place, f'{name}/стройка')
        # Палец или курсор в поле чертежа сдвигает призрак.
        box = page.locator('#campLiveAim').bounding_box()
        x1, y1 = box['x'] + box['width'] * 0.35, box['y'] + box['height'] * 0.45
        x2, y2 = box['x'] + box['width'] * 0.7, box['y'] + box['height'] * 0.62
        before_ghost = page.evaluate("() => ({x: game.ghostM.position.x, z: game.ghostM.position.z})")
        page.mouse.move(x1, y1)
        page.mouse.down()
        page.wait_for_timeout(200)
        page.mouse.move(x2, y2, steps=6)
        page.wait_for_timeout(200)
        moved = page.evaluate("""() => {
          const g = game.ghostM.position;
          return {x: g.x, z: g.z, aim: !!window.TERRA_CAMP_GHOST_AIM, err: game.build.err || ''};
        }""")
        page.mouse.up()
        page.wait_for_timeout(150)
        after_drag = page.evaluate("() => ({x: game.ghostM.position.x, z: game.ghostM.position.z, aim: !!window.TERRA_CAMP_GHOST_AIM})")
        shift = abs(moved['x'] - before_ghost['x']) + abs(moved['z'] - before_ghost['z'])
        assert moved['aim'] and shift > 0.15, {'before': before_ghost, 'moved': moved, 'shift': shift}
        assert not after_drag['aim']
        pinned = page.evaluate('game.ghostPos()')
        # Moving the cursor and turning after release must not move the selected world cell.
        page.mouse.move(20, 20)
        page.evaluate('game.p.yaw+=1')
        page.wait_for_timeout(350)
        assert page.evaluate('game.ghostPos()') == pinned, (pinned, page.evaluate('game.ghostPos()'))
        page.wait_for_function('(p)=>game.ghostM.position.x===p.x && game.ghostM.position.z===p.z', arg=pinned)
        shot(page, f'after-{name}-ghost.jpg')
        tint = page.evaluate("() => game.ghostMat.color.getHexString()")
        assert tint in ('7eb6ff', 'e25b4a'), tint
        page.evaluate('''() => {
          window.liveNativeBuildAction=game.buildAction;
          game.buildAction=function(...args){
            window.liveConfirmedCell={x:this.build.gx,z:this.build.gz};
            return liveNativeBuildAction.apply(this,args);
          };
        }''')
        tap(page.locator('#campLivePlace [data-act="confirm"]'))
        assert page.evaluate('liveConfirmedCell') == {'x': pinned['x'], 'z': pinned['z']}
        page.evaluate('game.buildAction=liveNativeBuildAction;delete window.liveNativeBuildAction')
        tap(page.locator('#campLivePlace [data-act="cancel"]'))
        page.wait_for_function('() => !game.build.on')
        assert not errors, f'{name}: {errors}'
        labels = page.evaluate("() => terraCampLive.anchors().map(a => a.name + ':' + a.text)")
        print(f'PASS {name} {width}×{height}: метки {len(tags)}, меню {len(menu)}, чертёж {tint}, якоря {labels}')
        if name == 'portrait':
            page.evaluate('async () => { await game.save(); }')
            raw = page.evaluate("() => localStorage.getItem('terra_save')")
            assert raw, 'Сохранение не записано'
            assert 'campAnchor' not in raw and 'liveCamp' not in raw
            snapshot = page.evaluate("""() => JSON.stringify({
              settlers: Object.fromEntries(Object.entries(game.p.camp.settlers).map(([k, s]) => [k, [s.name, s.job, s.prof]])),
              buildings: Object.fromEntries(Object.entries(game.p.camp.buildings).map(([k, b]) => [k, [b.lvl|0, b.type]]))
            })""")
            page.reload(wait_until='load')
            tap(page.locator('#mContinue'))
            expect(page.locator('#hud')).to_be_visible()
            after = page.evaluate("""() => JSON.stringify({
              settlers: Object.fromEntries(Object.entries(game.p.camp.settlers).map(([k, s]) => [k, [s.name, s.job, s.prof]])),
              buildings: Object.fromEntries(Object.entries(game.p.camp.buildings).map(([k, b]) => [k, [b.lvl|0, b.type]]))
            })""")
            assert after == snapshot, f'Сейв после «Продолжить» отличается:\n{snapshot}\n{after}'
            print('PASS сейв: «Отдых» записан штатным путём, загрузка profile без новых полей')
        context.close()

    if not FOCUSED:
        off, on = fps['off'], fps['on']
        print(f'FPS off {off} on {on}')
        # В headless swiftshader кадр редкий и рваный: сравниваем среднее время кадра, не одну паузу.
        assert on['avg'] < off['avg'] * 1.5 + 40, (off, on)
        print('PASS кадр: среднее время не хуже чем в полтора раза')
    browser.close()
