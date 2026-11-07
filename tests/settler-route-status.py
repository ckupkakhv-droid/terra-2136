"""Подпись жителя: дорога к обычной стройке и сбор. Опыт стройки не переписывается."""
import json, os
from pathlib import Path
from playwright.sync_api import sync_playwright

url = os.environ.get("TERRA_TEST_URL", "http://127.0.0.1:8080/play/")
out = Path(os.environ.get("TERRA_QA_OUTPUT", "/opt/cursor/artifacts"))
out.mkdir(parents=True, exist_ok=True)

SETUP = r"""
() => {
  const g = game;
  g.loop = () => {};
  const h = g.homePos();
  g.p.x = h.x; g.p.z = h.z + 4;
  g.p.camp.rep = 1000;
  g.p.camp.res.wood = 80;
  g.p.camp.res.scrap = 80;
  const ctx = g.workerSceneContext();
  const site = ctx.worksites.sawmill;
  const far = {x: site.x + 40, z: site.z + 2};
  const keysBefore = Object.keys(g.p.camp.settlers);
  if (!g.camp.recruit({id:'qa-build', name:'Марфа Строева', prof:'builder', pos:far}).ok) throw Error('recruit build');
  if (!g.camp.recruit({id:'qa-gather', name:'Илья Сборщик', prof:'gatherer', pos:{x:h.x+14, z:h.z-8}}).ok) throw Error('recruit gather');
  g.p.camp.settlers['qa-build'].pos = {...far};
  g.p.camp.settlers['qa-gather'].pos = {x:h.x+14, z:h.z-8};
  const baseKeys = Object.keys(g.p.camp.settlers['qa-build']).sort();
  if (!g.camp.upgrade('sawmill').ok) throw Error('upgrade');
  if (!g.camp.assign('qa-build','build',{target:'sawmill'}).ok) throw Error('assign build');
  if (!g.camp.assign('qa-gather','gather:wood').ok) throw Error('assign gather');
  const hero = g.p.xp, comp = g.p.camp.fieldCompanion?.v ?? null, campV = g.p.camp.v;
  return {site, far, baseKeys, hero, comp, campV, settlersBefore: keysBefore.length};
}
"""

def snap(page, who):
    return page.evaluate("""(who) => {
      const g = game, s = g.p.camp.settlers[who];
      const site = g.workerSceneContext().worksites?.sawmill;
      const dist = site && s.pos ? Math.hypot(s.pos.x-site.x, s.pos.z-site.z) : null;
      const b = g.p.camp.buildings.sawmill;
      g.ui.campPanel.open();
      g.ui.campPanel.select('settlers');
      document.querySelector('[data-resident="'+who+'"]')?.click();
      const badge = [...document.querySelectorAll('[data-resident="'+who+'"] .residentBadge')].map(n => n.textContent);
      return {
        job:s.job, status:s.status, work:s.work, xp:s.xp, lvl:s.lvl,
        pos:s.pos?{x:s.pos.x,z:s.pos.z}:null, dist, remaining:b?.project?.remaining??null,
        paused:!!b?.project?.paused, wood:g.p.camp.res.wood, hero:g.p.xp,
        activity: terraCampFieldbook.activity(s),
        enRoute: terraCampFieldbook.buildEnRoute(s),
        live: document.querySelector('.residentLiveStatus')?.textContent || '',
        badge, keys: Object.keys(s).sort(),
        campV: g.p.camp.v, comp: g.p.camp.fieldCompanion?.v ?? null,
      };
    }""", who)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get("TERRA_CHROMIUM", "/usr/bin/google-chrome"),
        args=["--use-angle=swiftshader", "--enable-unsafe-swiftshader", "--disable-dev-shm-usage"])
    page = browser.new_page(viewport={"width": 1280, "height": 800})
    page.set_default_timeout(90000)
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
    page.goto(url, timeout=120000)
    page.wait_for_function("!document.getElementById('terraBoot')", timeout=120000)
    page.evaluate("localStorage.clear()")
    page.reload(timeout=120000)
    page.wait_for_function("!document.getElementById('terraBoot')", timeout=120000)
    page.locator("#mNew").click()
    page.locator("#skip").click()
    page.wait_for_function("game.state==='play' && TERRA_KITS.ready && terraDefense.ready")
    meta = page.evaluate(SETUP)
    page.wait_for_timeout(200)
    assigned = snap(page, "qa-build")
    gather_assigned = snap(page, "qa-gather")
    # One real second on the road. Construction XP is recorded, not altered.
    walked = page.evaluate("""() => { game.camp.tick(1, game.workerSceneContext()); return true; }""")
    on_road = snap(page, "qa-build")
    page.locator(".fbActivity").scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    page.screenshot(path=str(out / "route-desktop.png"))
    gather_road = page.evaluate("""() => {
      for (let i=0;i<2;i++) game.camp.tick(1, game.workerSceneContext());
      const s = game.p.camp.settlers['qa-gather'];
      return {status:s.status, xp:s.xp, work:s.work, wood:game.p.camp.res.wood, activity:terraCampFieldbook.activity(s)};
    }""")
    # Build may have moved during the gather ticks. Re-read, then walk until arrival.
    page.set_viewport_size({"width": 320, "height": 568})
    page.locator(".fbActivity").scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    narrow = page.evaluate("""() => {
      const body = document.getElementById('campBody');
      const act = document.querySelector('.fbActivity');
      const panel = document.querySelector('#campPanel .win');
      const box = el => el ? {sw:el.scrollWidth, cw:el.clientWidth, sh:el.scrollHeight, ch:el.clientHeight, text:el.textContent} : null;
      const pr = panel?.getBoundingClientRect();
      return {body: box(body), act: box(act), panel: pr ? {w:pr.width, h:pr.height, right:pr.right, bottom:pr.bottom} : null,
        inner: {w:innerWidth, h:innerHeight},
        overflow: body ? body.scrollWidth > body.clientWidth + 1 : null};
    }""")
    page.screenshot(path=str(out / "route-320.png"))
    page.set_viewport_size({"width": 1280, "height": 800})
    arrived = page.evaluate("""() => {
      const g = game, s = g.p.camp.settlers['qa-build'];
      const log = [];
      for (let i=0;i<30;i++) {
        const site = g.workerSceneContext().worksites.sawmill;
        const dist = Math.hypot(s.pos.x-site.x, s.pos.z-site.z);
        const row = {t:i, dist, xp:s.xp, rem:g.p.camp.buildings.sawmill.project.remaining, status:s.status, act:terraCampFieldbook.activity(s)};
        log.push(row);
        if (dist <= 0.4) return {log, arrived:row};
        g.camp.tick(1, g.workerSceneContext());
      }
      throw Error('builder did not arrive');
    }""")
    at_work = snap(page, "qa-build")
    page.locator(".fbActivity").scroll_into_view_if_needed()
    page.wait_for_timeout(200)
    page.screenshot(path=str(out / "work-desktop.png"))
    # Pause from the real project button, then one tick outside the album.
    page.evaluate("""() => { game.ui.campPanel.select('build'); }""")
    page.wait_for_timeout(150)
    pause_btn = page.locator('[data-project-action="pause"]')
    assert pause_btn.count() >= 1, "pause button missing"
    xp_before_pause = page.evaluate("game.p.camp.settlers['qa-build'].xp")
    rem_before_pause = page.evaluate("game.p.camp.buildings.sawmill.project.remaining")
    pause_btn.first.click()
    assert page.evaluate("game.p.camp.buildings.sawmill.project.paused===true")
    page.locator('#campPanel footer [data-close="campPanel"]').click()
    page.wait_for_function("game.state==='play'")
    paused = page.evaluate("""() => {
      const before = {xp: game.p.camp.settlers['qa-build'].xp, rem: game.p.camp.buildings.sawmill.project.remaining};
      game.camp.tick(1, game.workerSceneContext());
      const s = game.p.camp.settlers['qa-build'];
      return {before, status:s.status, xp:s.xp, rem:game.p.camp.buildings.sawmill.project.remaining, activity:terraCampFieldbook.activity(s), job:s.job};
    }""")
    page.evaluate("game.ui.campPanel.open(); game.ui.campPanel.select('build')")
    page.locator('[data-project-action="resume"]').first.click()
    assert page.evaluate("game.p.camp.buildings.sawmill.project.paused!==true")
    # Cancel the order from the resident file, then give it back.
    page.evaluate("game.ui.campPanel.select('settlers'); document.querySelector('[data-resident=\"qa-build\"]').click()")
    page.wait_for_timeout(100)
    page.locator(".fbChangeJob").click()
    page.locator('[data-resident-job="idle"]').click()
    cancelled = page.evaluate("""() => {
      const s = game.p.camp.settlers['qa-build'];
      return {job:s.job, status:s.status, activity:terraCampFieldbook.activity(s), xp:s.xp};
    }""")
    again = page.evaluate("""() => {
      const r = game.camp.assign('qa-build','build',{target:'sawmill'});
      const s = game.p.camp.settlers['qa-build'];
      return {ok:!!r.ok, reason:r.reason||null, job:s.job, status:s.status};
    }""")
    # Save while still not at the site: move the builder back out and tick once.
    saved = page.evaluate("""() => {
      const g = game, s = g.p.camp.settlers['qa-build'];
      const site = g.workerSceneContext().worksites.sawmill;
      s.pos = {x: site.x + 24, z: site.z};
      g.camp.tick(1, g.workerSceneContext());
      const snap = {xp:s.xp, status:s.status, pos:{...s.pos}, rem:g.p.camp.buildings.sawmill.project.remaining, keys:Object.keys(s).sort(), campV:g.p.camp.v, hero:g.p.xp, comp:g.p.camp.fieldCompanion??null};
      if (g.state!=='play') { g.ui.campPanel.close?.(); }
      const result = g.save();
      const inspected = g.saveStore().inspectNew();
      const raw = localStorage.getItem('terra_save');
      if (!raw) return {result, snap, bytes: 0};
      const data = JSON.parse(raw);
      const stored = data.p.camp.settlers['qa-build'];
      return {result, inspected: inspected && {ok:inspected.ok, status:inspected.status, reason:inspected.reason||null, bytes:(inspected.raw||'').length}, snap, bytes: raw.length, saveKeys: Object.keys(data).sort(), campV: data.p.camp.v,
        stored: {status:stored.status, xp:stored.xp, job:stored.job, keys:Object.keys(stored).sort(), pos:stored.pos},
        profile: data.p.profile ?? data.profile ?? null, envelope: data.v ?? data.ver ?? null};
    }""")
    print("SAVE", json.dumps({"result": saved.get("result"), "inspected": saved.get("inspected"), "bytes": saved.get("bytes"), "campV": saved.get("campV"), "stored": saved.get("stored")}, ensure_ascii=False)[:2000])
    assert saved.get("result", {}).get("status") == "committed", saved.get("result")
    page.reload(timeout=120000)
    page.wait_for_function("!document.getElementById('terraBoot')", timeout=120000)
    menu = page.evaluate("""() => ({
      hidden: document.getElementById('mContinue')?.className,
      state: window.game?.state,
      inspect: window.game?.saveStore?.().inspectNew?.(),
      hasSave: !!localStorage.getItem('terra_save'),
      notice: document.getElementById('menuNotice')?.textContent || ''
    })""")
    print("MENU", json.dumps({k: (menu[k] if k!='inspect' else {kk: menu['inspect'].get(kk) for kk in ('ok','status','reason') if menu.get('inspect')}) for k in menu}, ensure_ascii=False, default=str)[:2000])
    page.wait_for_selector("#mContinue", state="visible", timeout=15000)
    page.evaluate("document.getElementById('mContinue').click()")
    page.wait_for_function("game.state==='play' && TERRA_KITS.ready")
    loaded = page.evaluate("""() => {
      game.loop = () => {};
      const s = game.p.camp.settlers['qa-build'];
      const site = game.workerSceneContext().worksites.sawmill;
      const dist = Math.hypot(s.pos.x-site.x, s.pos.z-site.z);
      game.ui.campPanel.open(); game.ui.campPanel.select('settlers');
      document.querySelector('[data-resident="qa-build"]').click();
      return {dist, status:s.status, xp:s.xp, job:s.job, activity:terraCampFieldbook.activity(s),
        live: document.querySelector('.residentLiveStatus')?.textContent || '',
        campV: game.p.camp.v, hero: game.p.xp, comp: game.p.camp.fieldCompanion??null,
        enRoute: terraCampFieldbook.buildEnRoute(s)};
    }""")
    page.wait_for_timeout(150)
    page.screenshot(path=str(out / "route-after-load.png"))
    renderer = page.evaluate("""() => {
      const canvas = document.querySelector('canvas');
      const gl = canvas?.getContext('webgl2') || canvas?.getContext('webgl');
      const ext = gl?.getExtension('WEBGL_debug_renderer_info');
      return {renderer: ext ? gl.getParameter(ext.UNMASKED_RENDERER_WEBGL) : null,
        vendor: ext ? gl.getParameter(ext.UNMASKED_VENDOR_WEBGL) : null, ua: navigator.userAgent};
    }""")
    report = {
      "meta": meta, "assigned": assigned, "gatherAssigned": gather_assigned, "onRoad": on_road,
      "gatherRoad": gather_road, "narrow": narrow, "arrived": arrived, "atWork": at_work,
      "xpBeforePause": xp_before_pause, "remBeforePause": rem_before_pause, "paused": paused,
      "cancelled": cancelled, "again": again, "saved": saved, "loaded": loaded,
      "renderer": renderer, "errors": errors,
      "heroOnLoad": {"before": meta["hero"], "saved": saved["snap"]["hero"], "loaded": loaded["hero"]},
    }
    (out / "settler-route-status.json").write_text(json.dumps(report, ensure_ascii=False, indent=2))

    assert assigned["dist"] > 10 and assigned["xp"] == 0
    assert assigned["status"] == "working"  # save field stays the old value
    assert assigned["activity"] == "Идёт к стройке", assigned
    assert "в пути" in assigned["live"], assigned["live"]
    assert "работает" not in assigned["live"]
    assert on_road["dist"] > 10 and on_road["xp"] > 0 and on_road["remaining"] < 45
    assert on_road["activity"] == "Идёт к стройке"
    assert on_road["status"] == "working"
    assert gather_assigned["activity"] == "Назначено"
    assert "назначено" in gather_assigned["live"]
    assert gather_road["status"] == "travel" and gather_road["xp"] == 0 and gather_road["work"] == 0
    assert gather_road["activity"] == "Идёт за ресурсом" and gather_road["wood"] == on_road["wood"]
    assert narrow["overflow"] is False, narrow
    assert narrow["panel"]["right"] <= 320 + 1 and narrow["panel"]["bottom"] <= 568 + 1
    assert at_work["dist"] <= 0.4 and at_work["activity"] == "Работает"
    assert "работает" in at_work["live"]
    assert at_work["xp"] > on_road["xp"]
    assert paused["xp"] == paused["before"]["xp"] and paused["rem"] == paused["before"]["rem"]
    assert paused["status"] == "blocked" and paused["job"] == "build"
    assert cancelled["job"] == "idle" and cancelled["status"] == "idle"
    assert again["ok"] and again["job"] == "build"
    assert saved["stored"]["status"] == "working"
    assert saved["stored"]["keys"] == saved["snap"]["keys"]
    assert saved["campV"] == 1 and loaded["campV"] == 1
    assert loaded["dist"] > 2 and loaded["activity"] == "Идёт к стройке" and loaded["enRoute"] is True
    assert "в пути" in loaded["live"]
    assert saved["snap"]["hero"] == meta["hero"], (saved["snap"]["hero"], meta["hero"])
    assert loaded["comp"] is None and meta["comp"] is None
    assert not errors, errors
    print("PASS route label, gather travel, arrival, pause, cancel, save/load; JS0")
    print(json.dumps({"onRoad": {k: on_road[k] for k in ("dist","xp","remaining","activity","status","live")},
                      "atWork": {k: at_work[k] for k in ("dist","xp","remaining","activity","live")},
                      "gatherRoad": gather_road, "paused": paused, "loaded": loaded, "renderer": renderer}, ensure_ascii=False, indent=2))
    browser.close()
