"""Live Chromium check of the existing build-project card.

Uses a disposable profile: recruit, gather, and upgrade go through the
current camp commands. One observed step is a real play-state tick.
SwiftShader is not a phone, Safari, or a GPU measurement.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/opt/cursor/artifacts'))
out.mkdir(parents=True, exist_ok=True)
url = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')

READ = r'''() => {
  const titles = ["Новичок","Следопыт","Разведчик","Проводник","Ветеран","Мастер вылазок"];
  const card = document.querySelector('[data-building="sawmill"]');
  const note = card ? card.querySelector(':scope > .campCrewProgress') : null;
  const member = note ? note.querySelector('.campCrewMember') : null;
  const id = member ? member.dataset.settler : null;
  const camp = game.p.camp;
  const settler = id ? camp.settlers[id] : null;
  const building = camp.buildings.sawmill;
  const project = building && building.project;
  const rankIndex = settler ? Math.min(5, settler.lvl - 1) : null;
  const fv = settler && ["builder","engineer"].includes(settler.prof) && Number.isSafeInteger(settler.lvl) && settler.lvl > 0
    ? Math.min(titles.length - 1, settler.lvl - 1) * 0.04 : 0;
  const buildEffect = settler && ["builder","engineer"].includes(settler.prof)
    ? "Стройка: +" + Math.round(fv * 100) + "% к скорости работы. Материалы и XP без бонуса." : null;
  const art = card ? card.querySelector('.fbBlueprintArt') : null;
  const body = document.getElementById('campBody');
  return {
    state: game.state,
    tab: game.ui.campPanel.tab,
    hasNote: !!note,
    noteCount: document.querySelectorAll('.campCrewProgress').length,
    cardsWithoutCrew: [...document.querySelectorAll('[data-building]')].filter(c => !c.querySelector('.campCrewProgress')).map(c => c.dataset.building),
    goal: note ? note.querySelector('.campProjectGoal').textContent : null,
    remain: note ? note.querySelector('.campProjectRemain').textContent : null,
    rank: member ? member.querySelector('.campCrewRank').textContent : null,
    xp: member ? member.querySelector('.campCrewXp').textContent : null,
    effect: member ? member.querySelector('.residentBuildEffect')?.textContent || null : null,
    data: note ? {from: note.dataset.fromLevel, to: note.dataset.toLevel, remaining: note.dataset.remaining, settler: id, rank: member.dataset.rank, level: member.dataset.level, xp: member.dataset.xp, need: member.dataset.need, effect: member.querySelector('.residentBuildEffect')?.dataset.buildEffect || null} : null,
    internal: settler ? {
      id, name: settler.name, prof: settler.prof, lvl: settler.lvl, xp: settler.xp, skill: settler.skills.build,
      job: settler.job, status: settler.status, order: settler.order, title: titles[rankIndex],
      need: 60 * settler.lvl, next: titles[rankIndex + 1] || null, buildEffect, fv,
      buildingLevel: building.lvl || 0, projectLevel: project ? project.lvl : null,
      remaining: project ? project.remaining : null, paused: !!(project && project.paused)
    } : {buildingLevel: building ? (building.lvl || 0) : null, project: project || null},
    heroXp: game.p.xp || 0,
    fieldCompanion: game.p.fieldCompanion || null,
    campV: camp.v,
    playerV: game.p.v,
    classProfile: game.p.classProfile || null,
    tick: camp.sim.tick,
    art: art ? {h: art.getBoundingClientRect().height, bg: getComputedStyle(art).backgroundImage} : null,
    overflow: card && body ? {
      card: card.scrollWidth - card.clientWidth,
      body: body.scrollWidth - body.clientWidth,
      note: note ? note.scrollWidth - note.clientWidth : null
    } : null
  };
}'''

def snap(page):
    return page.evaluate(READ)

def open_build(page):
    page.evaluate('''() => { game.ui.campPanel.open(); game.ui.campPanel.select("build"); }''')
    page.wait_for_function('''() => game.state==="modal" && game.ui.campPanel.tab==="build" && !!document.querySelector("[data-building=sawmill]")''')
    page.locator('[data-building="sawmill"]').scroll_into_view_if_needed()

def close_camp(page):
    page.locator('#campPanel footer [data-close="campPanel"]').click()
    page.wait_for_function('() => game.state==="play"')

def one_tick(page):
    return page.evaluate('''() => new Promise(resolve => {
      const start = game.p.camp.sim.tick;
      const read = (id) => {
        const s = game.p.camp.settlers[id];
        const project = game.p.camp.buildings.sawmill.project;
        return {
          tick: game.p.camp.sim.tick, xp: s.xp, lvl: s.lvl, skill: s.skills.build,
          status: s.status, job: s.job,
          remaining: project ? project.remaining : null, paused: !!(project && project.paused),
          buildingLevel: game.p.camp.buildings.sawmill.lvl || 0,
          heroXp: game.p.xp || 0,
          fieldCompanion: game.p.fieldCompanion ? JSON.stringify(game.p.fieldCompanion) : null
        };
      };
      const before = read("b1");
      const timer = setInterval(() => {
        if (game.state !== "play") return;
        if (game.p.camp.sim.tick === start) return;
        const after = read("b1");
        game.ui.campPanel.open();
        game.ui.campPanel.select("build");
        clearInterval(timer);
        resolve({before, after, ticks: after.tick - start});
      }, 16);
    })''')

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM', '/usr/local/bin/google-chrome'), args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-gpu', '--no-sandbox'])
    page = browser.new_page(viewport={'width': 1440, 'height': 900})
    page.set_default_timeout(90000)
    errors, warnings = [], []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.on('console', lambda msg: errors.append(msg.text) if msg.type == 'error' else warnings.append(msg.text) if msg.type == 'warning' else None)
    page.goto(url, wait_until='load', timeout=180000)
    page.wait_for_selector('#mNew', timeout=180000)
    page.wait_for_function('() => !document.querySelector("#terraBoot")')
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('() => window.game && game.state==="play" && game.p.camp')
    page.wait_for_function('() => !!window.terraCampUI')

    hired = page.evaluate(r'''() => {
      game.ui.campPanel.open();
      game.p.camp.rep = 40;
      return game.camp.recruit({id:"b1", prof:"builder", name:"Архивариус Серафима Длинноименованная"});
    }''')
    if not hired.get('ok'):
        raise SystemExit('recruit failed ' + json.dumps(hired, ensure_ascii=False))

    def pull(job, key, need):
        order = page.evaluate('''(job) => game.camp.assign("b1", job)''', job)
        if not order.get('ok'):
            return order
        steps = 0
        last = None
        while steps <= 4000:
            last = page.evaluate('''(key) => {
              const ctx = {...game.workerSceneContext(), ...(game.raidContext?.() || {})};
              game.camp.tick(40, ctx);
              const s = game.p.camp.settlers.b1;
              return {stock: game.p.camp.res[key] || 0, status: s.status, block: s.workBlock || null, work: s.work || 0, xp: s.xp};
            }''', key)
            steps += 40
            print(job, steps, last, flush=True)
            if last['stock'] >= need:
                return {'ok': True, 'steps': steps, **last}
            if last['status'] == 'blocked' and steps > 200:
                return {'ok': False, 'reason': 'blocked', 'steps': steps, **last}
        return {'ok': False, 'reason': 'gather-timeout', 'steps': steps, **(last or {})}

    wood = pull('gather:wood', 'wood', 10)
    scrap = pull('gather:scrap', 'scrap', 8) if wood.get('ok') else {'ok': False, 'reason': 'wood'}
    if not wood.get('ok') or not scrap.get('ok'):
        raise SystemExit('gather failed ' + json.dumps({'wood': wood, 'scrap': scrap}, ensure_ascii=False))
    setup = page.evaluate(r'''() => {
      const person = game.p.camp.settlers.b1;
      let recovered = 0;
      if ((person.needs.rest || 0) <= 25) {
        game.camp.assign("b1", "idle");
        const ctx = () => ({...game.workerSceneContext(), ...(game.raidContext?.() || {})});
        while ((game.p.camp.settlers.b1.needs.rest || 0) <= 25 && recovered < 2000) {
          game.camp.tick(20, ctx());
          recovered += 20;
        }
      }
      const idle = game.camp.assign("b1", "idle", {auto: 1});
      const ready = game.p.camp.settlers.b1;
      return {idle, recovered, xp: ready.xp, rest: ready.needs.rest, job: ready.job, order: ready.order, res: game.p.camp.res, tick: game.p.camp.sim.tick};
    }''')
    setup = {'hired': True, 'wood': wood, 'scrap': scrap, **setup}
    print('setup', json.dumps(setup, ensure_ascii=False)[:1500], flush=True)

    open_build(page)
    upgrade = page.locator('[data-building="sawmill"] button', has_text='Улучшить')
    expect(upgrade).to_be_enabled()
    upgrade.click()
    page.wait_for_function('''() => !!game.p.camp.buildings.sawmill.project && !document.querySelector("[data-building=sawmill] .campCrewProgress")''')
    absent = snap(page)
    assert absent['hasNote'] is False, absent

    assign = page.locator('[data-building="sawmill"] [data-quick-builder="sawmill"]')
    expect(assign).to_be_enabled()
    assign.click()
    page.wait_for_function('''() => game.p.camp.settlers.b1.job==="build" && !!document.querySelector("[data-building=sawmill] .campCrewProgress")''', timeout=20000)
    shown = snap(page)
    internal = shown['internal']
    assert internal['id'] == 'b1'
    assert shown['goal'] == f"Улучшение: ур. {internal['buildingLevel']} → {internal['projectLevel']}"
    assert shown['remain'] == f"Осталось {int(__import__('math').ceil(internal['remaining']))} ед. работы"
    assert shown['rank'] == f"{internal['name']} · {internal['title']} · ур. {internal['lvl']}"
    assert shown['xp'] == (f"До звания «{internal['next']}»: {int(internal['xp'])} / {internal['need']} опыта" if internal['next'] else "Высшее звание · уровень продолжает расти")
    assert shown['effect'] == internal['buildEffect']
    assert shown['data']['from'] == str(internal['buildingLevel'])
    assert shown['data']['to'] == str(internal['projectLevel'])
    assert abs(float(shown['data']['remaining']) - internal['remaining']) < 1e-9
    assert abs(float(shown['data']['xp']) - internal['xp']) < 1e-9
    assert shown['data']['need'] == str(internal['need'])
    assert shown['data']['level'] == str(internal['lvl'])
    assert 'b1' not in ''.join(shown['cardsWithoutCrew'])
    assert 'pump' in shown['cardsWithoutCrew']
    assert shown['art'] and shown['art']['h'] >= 40 and 'sawmill' in shown['art']['bg']
    assert shown['heroXp'] == 0
    assert shown['fieldCompanion'] is None
    assert shown['campV'] == 1

    shots = {}
    for name, width, height in [('1440x900', 1440, 900), ('390x844', 390, 844), ('320x568', 320, 568)]:
        page.set_viewport_size({'width': width, 'height': height})
        page.wait_for_timeout(150)
        open_build(page)
        metrics = snap(page)
        assert metrics['overflow']['card'] <= 1, (name, metrics['overflow'])
        assert metrics['overflow']['body'] <= 1, (name, metrics['overflow'])
        assert metrics['overflow']['note'] <= 1, (name, metrics['overflow'])
        assert metrics['art']['h'] >= 40, (name, metrics['art'])
        path = out / f'build-crew-{name}.png'
        page.screenshot(path=str(path), full_page=False)
        page.locator('[data-building="sawmill"] .campCrewProgress').screenshot(path=str(out / f'build-crew-card-{name}.png'))
        shots[name] = {'path': str(path), 'overflow': metrics['overflow'], 'art': metrics['art'], 'goal': metrics['goal'], 'rank': metrics['rank']}

    page.set_viewport_size({'width': 1440, 'height': 900})
    open_build(page)
    pause = page.locator('[data-building="sawmill"] [data-project-action="pause"]')
    pause.focus()
    expect(pause).to_be_focused()
    before_pause = snap(page)
    page.keyboard.press('Enter')
    page.wait_for_function('''() => game.p.camp.buildings.sawmill.project.paused===true && document.querySelector("[data-project-action=resume]")''')
    after_pause = snap(page)
    assert after_pause['internal']['xp'] == before_pause['internal']['xp']
    assert after_pause['internal']['remaining'] == before_pause['internal']['remaining']
    assert after_pause['hasNote'] is True

    close_camp(page)
    paused_tick = one_tick(page)
    assert paused_tick['ticks'] == 1
    assert paused_tick['after']['xp'] == paused_tick['before']['xp']
    assert paused_tick['after']['remaining'] == paused_tick['before']['remaining']
    assert paused_tick['after']['heroXp'] == paused_tick['before']['heroXp']
    assert paused_tick['after']['fieldCompanion'] == paused_tick['before']['fieldCompanion']
    assert paused_tick['after']['paused'] is True

    resume = page.locator('[data-building="sawmill"] [data-project-action="resume"]')
    resume.focus()
    page.keyboard.press('Enter')
    page.wait_for_function('''() => game.p.camp.buildings.sawmill.project.paused!==true && document.querySelector("[data-project-action=pause]")''')
    resumed = snap(page)
    assert resumed['internal']['xp'] == after_pause['internal']['xp']

    close_camp(page)
    live = one_tick(page)
    assert live['ticks'] == 1
    assert live['after']['paused'] is False
    dx = live['after']['xp'] - live['before']['xp']
    dr = live['before']['remaining'] - live['after']['remaining']
    fv = 0 if live['before']['lvl'] <= 1 else min(5, live['before']['lvl'] - 1) * 0.04
    assert dx > 0 and dr > 0
    assert abs(dr - (dx / 0.25) * (1 + fv)) < 1e-6
    assert live['after']['skill'] == live['before']['skill']
    assert live['after']['lvl'] == live['before']['lvl']
    assert live['after']['heroXp'] == live['before']['heroXp']
    assert live['after']['fieldCompanion'] == live['before']['fieldCompanion']
    assert live['after']['buildingLevel'] == live['before']['buildingLevel']
    page.locator('[data-building="sawmill"]').scroll_into_view_if_needed()
    reread = snap(page)
    assert reread['goal'].startswith('Улучшение: ур.')
    assert abs(float(reread['data']['xp']) - live['after']['xp']) < 1e-9
    assert abs(float(reread['data']['remaining']) - live['after']['remaining']) < 1e-9

    saved = page.evaluate('''() => {
      const result = game.save();
      const raw = localStorage.getItem("terra_save");
      return {result, hasName: !!raw && raw.includes("Архивариус Серафима Длинноименованная"), bytes: raw ? raw.length : 0};
    }''')
    assert saved['result'].get('ok') is True or saved['result'].get('status') == 'committed', saved
    assert saved['hasName'] is True
    page.reload(timeout=180000)
    page.wait_for_selector('#mContinue', timeout=180000)
    page.locator('#mContinue').click()
    page.wait_for_function('''() => game && game.state==="play" && game.p.camp.settlers.b1 && game.p.camp.buildings.sawmill.project''', timeout=180000)
    loaded = page.evaluate('''() => {
      const s = game.p.camp.settlers.b1;
      return {xp:s.xp, lvl:s.lvl, skill:s.skills.build, job:s.job, campV:game.p.camp.v, playerV:game.p.v, classProfile:game.p.classProfile||null, fieldCompanion:game.p.fieldCompanion||null, remaining:game.p.camp.buildings.sawmill.project.remaining, heroXp:game.p.xp||0};
    }''')
    assert loaded['xp'] == live['after']['xp']
    assert loaded['lvl'] == live['after']['lvl']
    assert loaded['skill'] == live['after']['skill']
    assert loaded['job'] == 'build'
    assert loaded['campV'] == 1
    assert loaded['fieldCompanion'] is None
    assert loaded['heroXp'] == live['after']['heroXp']
    assert abs(loaded['remaining'] - live['after']['remaining']) < 1e-9
    open_build(page)
    reloaded_card = snap(page)
    assert abs(float(reloaded_card['data']['xp']) - loaded['xp']) < 1e-9
    assert reloaded_card['effect'] == reloaded_card['internal']['buildEffect']

    # Ordinary sawmill project has pause, not a separate cancel control.
    assert page.locator('[data-building="sawmill"] [data-project-action="cancel"]').count() == 0

    close_camp(page)
    finish = page.evaluate(r'''() => new Promise(resolve => {
      const hired = game.camp.recruit({id:"b2", prof:"builder", name:"Илья"});
      const assigned = hired.ok ? game.camp.assign("b2", "build", {target:"sawmill"}) : null;
      const rows = [];
      const seen = new Set();
      const timer = setInterval(() => {
        if (game.state !== "play") return;
        const tick = game.p.camp.sim.tick;
        if (seen.has(tick)) return;
        seen.add(tick);
        const building = game.p.camp.buildings.sawmill;
        const crew = ["b1","b2"].map(id => game.p.camp.settlers[id]).filter(Boolean);
        rows.push({tick, remaining: building.project ? building.project.remaining : null, level: building.lvl||0, heroXp: game.p.xp||0, crew: crew.map(s => ({id:s.id, xp:s.xp, lvl:s.lvl, skill:s.skills.build, job:s.job}))});
        const doneRows = rows.filter(row => row.remaining === null).length;
        if (doneRows >= 2 || rows.length > 200) {
          clearInterval(timer);
          game.ui.campPanel.open();
          resolve({hired, assigned, rows, fieldCompanion: game.p.fieldCompanion||null});
        }
      }, 30);
    })''')
    rows = finish['rows']
    assert finish['hired']['ok'] and finish['assigned']['ok'], finish
    done_at = next(i for i, row in enumerate(rows) if row['remaining'] is None)
    assert done_at > 1
    for row, nxt in zip(rows[1:done_at], rows[2:done_at]):
        total = 0
        for a, b in zip(row['crew'], nxt['crew']):
            dx = b['xp'] - a['xp']
            fv = 0 if a['lvl'] <= 1 else min(5, a['lvl'] - 1) * 0.04
            assert dx > 0
            assert b['skill'] == a['skill'] and b['lvl'] == a['lvl']
            total += (dx / 0.25) * (1 + fv)
        assert abs((row['remaining'] - nxt['remaining']) - total) < 1e-6
        assert nxt['heroXp'] == row['heroXp']
    last_work = rows[done_at - 1]
    completed = rows[done_at]
    idle = rows[done_at + 1]
    for a, b in zip(last_work['crew'], completed['crew']):
        # The completing tick still pays that tick's XP and no separate bonus:
        # it stays in the same ballpark as the previous tick, far from a lump reward.
        prev = a['xp'] - rows[done_at - 2]['crew'][[c['id'] for c in rows[done_at - 2]['crew']].index(a['id'])]['xp']
        got = b['xp'] - a['xp']
        assert got > 0 and got < prev * 1.5 + 1e-6
        assert b['skill'] == a['skill']
    for a, b in zip(completed['crew'], idle['crew']):
        assert b['xp'] == a['xp'] and b['job'] != 'build'
    assert idle['heroXp'] == rows[0]['heroXp']
    assert finish['fieldCompanion'] is None
    assert completed['level'] == last_work['level'] + 1

    evidence = {
        'setup': setup,
        'beforeAssign': {'hasNote': absent['hasNote'], 'cardsWithoutCrew': absent['cardsWithoutCrew']},
        'shown': {'goal': shown['goal'], 'remain': shown['remain'], 'rank': shown['rank'], 'xp': shown['xp'], 'effect': shown['effect'], 'status': internal['status'], 'job': internal['job']},
        'pausedTick': paused_tick,
        'liveTick': live,
        'save': saved,
        'loaded': loaded,
        'completionTicks': len(rows),
        'completionLevel': completed['level'],
        'shots': shots,
        'pageErrors': errors,
        'warningCount': len(warnings),
        'cancelControlOnSawmill': False,
        'known': 'Обычная стройка отмечает working сразу при назначении, до прихода на площадку. Отмены у лесопилки нет: есть пауза. Завершение проекта не даёт отдельной награды. Уровень за этот проект не достигнут: порог 60 опыта.'
    }
    (out / 'build-crew-evidence.json').write_text(json.dumps(evidence, ensure_ascii=False, indent=2), encoding='utf-8')
    assert errors == [], errors
    browser.close()
    print('live ok', json.dumps({'live': live, 'loadedXp': loaded['xp'], 'shots': list(shots)}, ensure_ascii=False)[:2000])
