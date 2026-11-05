"""Real scene labels -> resident dossier / building blueprint / selected turret.

Disposable profile, native menu clicks and queued-navigation cancellation.
"""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-camp-scene-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 390, 'height': 844}, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/'), timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.locator('#bCamp').click()
    page.wait_for_function('window.terraCampLive && terraDefense.getState().ready')
    fixture = page.evaluate('''()=>{
      const g=game,h=g.homePos();g.p.camp.rep=1000;g.p.level=6;g.p.hp=10000;
      for(const [id,name] of [['qa-scene','Марфа'],['qa-other','Иван']]){
        if(!g.camp.recruit({id}).ok)throw Error('Fixture recruitment failed');
        g.p.camp.settlers[id].name=name;
        g.p.camp.settlers[id].pos=id==='qa-scene'?{x:h.x+1.6,z:h.z+3.8}:{x:h.x-10,z:h.z-3};
      }
      for(const [i,dk] of ['pkm','nail','flame'].entries())
        g.p.base.push({t:'turretB',dk,x:h.x+4+i*3,z:h.z+4,r:0});
      g.p.camp.buildings.workshop={type:'workshop',lvl:1,hp:TERRA_DEFENSE_CTX.B.camp.buildings.workshop.hp};
      g.p.x=h.x;g.p.z=h.z+5;g.p.yaw=Math.PI;g.baseDirty=true;
      window.__campReadOrders=0;
      for(const [api,keys] of [[g.camp,['assign','upgrade']],[terraDefense,['repair','reload','upgrade']]])
        for(const key of keys){const fn=api[key];api[key]=function(...args){if(g.state==='modal')window.__campReadOrders++;return fn.apply(this,args)}}
      return {turret:terraDefense.getState().turrets.find(t=>t.dk==='flame')};
    }''')

    def close_camp():
        page.evaluate('game.ui.close("campPanel")')
        expect(page.locator('#campPanel')).not_to_be_visible()

    def menu(kind, id):
        page.wait_for_function('''v=>terraCampLive.anchors().some(a=>a.kind===v.kind&&a.id===v.id)''', arg={'kind': kind, 'id': id})
        anchor = page.evaluate('''v=>terraCampLive.anchors().find(a=>a.kind===v.kind&&a.id===v.id)''', {'kind': kind, 'id': id})
        page.evaluate('''a=>{game.p.x=a.x+3.5;game.p.z=a.z+8;game.p.yaw=Math.atan2(a.x-game.p.x,a.z-game.p.z)}''', anchor)
        page.locator(f'.campLiveTag[data-kind="{kind}"]').filter(has_text=anchor['name']).tap()
        expect(page.locator('#campLiveMenu')).to_be_visible()

    def selected(selector):
        node = page.locator(selector)
        expect(node).to_be_focused()
        assert node.evaluate('''e=>{
          const r=e.getBoundingClientRect(),b=document.getElementById('campBody').getBoundingClientRect();
          return Math.min(r.bottom,b.bottom)>Math.max(r.top,b.top) && getComputedStyle(e).outlineStyle==='solid';
        }'''), selector

    close_camp()
    page.wait_for_function("terraCampLive.anchors().some(a=>a.kind==='building'&&a.id==='workshop')")
    building = 'workshop'
    for name, width, height in [('portrait', 390, 844), ('landscape', 844, 390), ('desktop', 1280, 800)]:
        page.set_viewport_size({'width': width, 'height': height})
        page.locator('#bCamp').click()
        page.locator('#campTabs [data-camp-tab="settlers"]').click()
        page.locator('#residentSearchInput').fill('никогонет')
        expect(page.locator('.residentRow:visible')).to_have_count(0)
        close_camp()
        menu('settler', 'qa-scene')
        if name == 'portrait':
            # Queue the real action, close its destination, then execute it.
            # It must not open a dossier after the user has left the panel.
            cancelled = page.evaluate('''()=>{
              const raf=window.requestAnimationFrame,queue=[];
              window.requestAnimationFrame=fn=>{queue.push(fn);return 0};
              try{
                document.querySelector('#campLiveMenu [aria-label$="Дело"]').click();
                game.ui.close('campPanel');
                for(const fn of queue)fn(performance.now());
                return {queued:queue.length,state:game.state,dossier:!!document.querySelector('.residentIdentityHead')};
              }finally{window.requestAnimationFrame=raf}
            }''')
            assert cancelled['queued'] and cancelled['state']=='play' and not cancelled['dossier'], cancelled
            menu('settler', 'qa-scene')
        page.locator('#campLiveMenu [aria-label$="Дело"]').tap()
        expect(page.locator('.dossier [data-resident-biography="qa-scene"]')).to_be_attached()
        expect(page.locator('.dossierDial')).to_contain_text('из 2')
        page.locator('[data-camp-back="list"]').click()
        expect(page.locator('#residentSearchInput')).to_have_value('')
        expect(page.locator('.residentRow:visible')).to_have_count(2)
        close_camp()
        menu('building', building)
        page.locator('#campLiveMenu [aria-label$="Чертёж"]').tap()
        selected(f'.campCard[data-building="{building}"]')
        page.screenshot(path=str(out / f'{name}-blueprint.png'))
        close_camp()
        menu('defense', fixture['turret']['id'])
        page.locator('#campLiveMenu [aria-label$="Карточка"]').tap()
        selected(f'[data-defense-id="{fixture["turret"]["id"]}"]')
        assert page.locator('[data-defense-id]').count()==3
        page.screenshot(path=str(out / f'{name}-turret.png'))
        close_camp()
        assert page.evaluate('__campReadOrders')==0, 'Viewing issued an order'
        print(f'PASS {name}: hidden resident opens directly, correct blueprint/turret focused, no orders', flush=True)
    assert not errors, errors
    print('PASS scene navigation and cancellation; JS0')
    browser.close()
