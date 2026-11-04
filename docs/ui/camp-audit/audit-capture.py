import json, os, sys
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
OUT=Path('/workspace/terra-ui-audit/shots'); OUT.mkdir(parents=True, exist_ok=True)
URL='http://127.0.0.1:8093/play/'
VIEWS=[('p390',390,844),('l844',844,390),('p360',360,740)]
MEASURE="""(sel) => {
  const root=document.querySelector(sel); if(!root) return null;
  const vw=innerWidth, vh=innerHeight;
  const els=[...root.querySelectorAll('button,summary,input,select,a,[role=button]')].filter(e=>{const r=e.getBoundingClientRect();return r.width>0&&r.height>0&&getComputedStyle(e).visibility!=='hidden'});
  const small=[]; let inView=0;
  for(const e of els){const r=e.getBoundingClientRect(); const vis=r.bottom>0&&r.top<vh&&r.right>0&&r.left<vw; if(vis) inView++;
    if(r.width<48||r.height<48) small.push({t:(e.getAttribute('aria-label')||e.textContent||e.className).trim().slice(0,40),w:Math.round(r.width),h:Math.round(r.height),cls:e.className.slice(0,40)});}
  const body=document.querySelector('#campBody');
  const text=(body?.innerText||'');
  const fonts={}; for(const e of root.querySelectorAll('*')){ if(!e.childNodes.length) continue; const own=[...e.childNodes].some(n=>n.nodeType===3&&n.textContent.trim()); if(!own) continue; const r=e.getBoundingClientRect(); if(!(r.width&&r.height)) continue; const fs=getComputedStyle(e).fontSize; fonts[fs]=(fonts[fs]||0)+1;}
  const win=root.querySelector('.win')?.getBoundingClientRect();
  const b=body?.getBoundingClientRect();
  return {controls:els.length,inView,small:small.slice(0,60),smallCount:small.length,textChars:text.length,words:text.split(/\\s+/).filter(Boolean).length,
    bodyScroll:body?[body.scrollHeight,body.clientHeight,body.scrollWidth,body.clientWidth]:null,fonts,
    win:win&&[Math.round(win.x),Math.round(win.y),Math.round(win.width),Math.round(win.height)],
    body:b&&[Math.round(b.x),Math.round(b.y),Math.round(b.width),Math.round(b.height)]};
}"""
report={}
with sync_playwright() as p:
    br=p.chromium.launch(executable_path='/usr/bin/google-chrome',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
    for vname,w,h in VIEWS:
        ctx=br.new_context(viewport={'width':w,'height':h},is_mobile=True,has_touch=True,device_scale_factor=2)
        page=ctx.new_page(); page.set_default_timeout(60000)
        errs=[]; page.on('pageerror',lambda e: errs.append(str(e)))
        page.goto(URL,wait_until='load',timeout=120000)
        page.locator('#mNew').tap(); page.locator('#skip').tap()
        expect(page.locator('#hud')).to_be_visible()
        page.wait_for_timeout(2500)
        page.screenshot(path=str(OUT/f'{vname}-00-hud.png'))
        hudinfo=page.evaluate("""()=>{const o={};for(const id of ['bCamp','bMap','bPause']){const e=document.getElementById(id);if(e){const r=e.getBoundingClientRect();o[id]=[Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]}}return o}""")
        page.locator('#bCamp').tap()
        page.evaluate("""()=>{ game.p.camp.rep=5000;
          const names=['Павел Оченьдлиннаяфамилияпоселенца','Мария Соколова','Иван Ржавый','Лида','Степан Кузнецов','Ольга Тихая'];
          for(let i=0;i<6;i++){ const r=game.camp.recruit({id:'qa-'+i}); if(!r.ok) throw Error('recruit '+i+': '+r.reason); game.p.camp.settlers['qa-'+i].name=names[i]; }
        }""")
        page.locator('[data-camp-tab="overview"]').tap(); page.wait_for_timeout(400)
        before=page.evaluate('JSON.stringify(game.p.camp)')
        R={'hud':hudinfo}
        def shot(name):
            page.wait_for_timeout(350)
            page.screenshot(path=str(OUT/f'{vname}-{name}.png'))
            R[name]=page.evaluate(MEASURE,'#campPanel')
        shot('01-overview')
        page.locator('#campBody').evaluate('e=>e.scrollTop=e.scrollHeight'); shot('01b-overview-bottom')
        page.locator('#campTabs [data-camp-tab="settlers"]').tap(); shot('02-residents')
        page.locator('#campBody').evaluate('e=>e.scrollTop=e.scrollHeight/2'); shot('02b-residents-mid')
        page.locator('#residentSearchInput').fill('мария'); shot('03-search')
        page.locator('#residentSearchInput').fill('')
        page.locator('[data-resident="qa-1"]').tap(); page.wait_for_timeout(300); shot('04-resident-card')
        page.locator('#campBody').evaluate('e=>e.scrollTop=e.scrollHeight'); shot('04b-resident-card-bottom')
        page.locator('[data-resident-job]').first.scroll_into_view_if_needed(); shot('05-jobs')
        # try a job with multiple targets (opens target list)
        opened=False
        for job in ['gather:wood','gather:water','gather:food','gather:scrap','guard','patrol','craft','scout']:
            b=page.locator(f'[data-resident-job="{job}"]')
            if b.count() and b.is_enabled():
                b.scroll_into_view_if_needed(); b.tap(); page.wait_for_timeout(400)
                if page.locator('[data-camp-back="resident"]').count():
                    shot('06-job-targets'); opened=True
                    page.locator('[data-camp-back="resident"]').tap(); break
                else:
                    R['assigned_direct']=job; break
        page.locator('#campTabs [data-camp-tab="build"]').tap(); shot('07-build')
        page.locator('#campBody').evaluate('e=>e.scrollTop=e.scrollHeight'); shot('07b-build-bottom')
        page.locator('#campTabs [data-camp-tab="expansion"]').tap(); shot('08-expansion')
        page.locator('#campTabs [data-camp-tab="more"]').tap(); shot('09-more')
        dests=page.evaluate("()=>[...document.querySelectorAll('#campBody .campDestination')].map(e=>e.dataset.campTab)")
        R['more_destinations']=dests
        for d in dests:
            if d=='territories': continue
            page.locator('#campTabs [data-camp-tab="more"]').tap(); page.wait_for_timeout(200)
            page.locator(f'#campBody [data-camp-tab="{d}"]').tap(); shot(f'10-{d}')
        R['tabs']=page.evaluate("""()=>[...document.querySelectorAll('#campTabs button')].map(e=>{const r=e.getBoundingClientRect();return [e.dataset.campTab,Math.round(r.x),Math.round(r.y),Math.round(r.width),Math.round(r.height)]})""")
        R['foot']=page.evaluate("""()=>{const f=document.querySelector('#campPanel .panelFoot');const r=f?.getBoundingClientRect();const x=document.querySelector('#campPanel .x').getBoundingClientRect();return {foot:r&&[Math.round(r.y),Math.round(r.height)],close:[Math.round(x.x),Math.round(x.y),Math.round(x.width),Math.round(x.height)]}}""")
        R['stateUnchangedExceptAssign']=page.evaluate('JSON.stringify(game.p.camp)')==before
        R['errors']=errs
        report[vname]=R
        ctx.close()
    br.close()
json.dump(report,open('/workspace/terra-ui-audit/measure.json','w'),ensure_ascii=False,indent=1)
print('done')
