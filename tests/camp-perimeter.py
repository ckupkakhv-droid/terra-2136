"""Mobile camp geometry, read-only gun selection and original saved defense commands.
Uses disposable fixtures. TERRA_TEST_URL accepts the online or standalone HTTP build.
"""
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
import json,os
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-perimeter42'));out.mkdir(exist_ok=True)
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':390,'height':844},has_touch=True);page.set_default_timeout(90000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play"&&terraDefense.ready&&TERRA_KITS.ready&&document.querySelector("#food").textContent.trim()');page.evaluate('game.loop=()=>{};game.ui.campPanel.open()');page.set_default_timeout(15000)
 def tab(t):page.evaluate('t=>game.ui.campPanel.select(t)',t);expect(page.locator('#campBody')).to_have_attribute('data-fieldbook-view',t)
 def shot(name):
  page.evaluate('game.renderT()');page.screenshot(path=str(out/(name+'.png')),animations='disabled')
 def snap():return page.evaluate('JSON.stringify({p:game.p,save:localStorage.getItem("terra_save")})')
 def fit():
  r=page.locator('#campBody').evaluate('''e=>{const a=e.getBoundingClientRect(),f=document.querySelector('#campPanel footer').getBoundingClientRect(),h=document.querySelector('#campPanel h2').getBoundingClientRect();return {width:e.clientWidth,scroll:e.scrollWidth,bodyHeight:Math.round(a.height),header:h.bottom<=a.top+1,footer:f.top>=a.bottom-1,buttons:[...e.querySelectorAll('button,input,select,summary')].filter(n=>n.checkVisibility()&&!n.closest('.territoryMapViewport,.perimeterRail,.dispatchContractRail')&&!n.closest('details:not([open]) > :not(summary)')).filter(n=>{const r=n.getBoundingClientRect();return r.width<43.5||r.height<43.5||r.left<a.left-2||r.right>a.right+2}).map(n=>n.getAttribute('aria-label')||n.textContent.trim().slice(0,45))}}''')
  assert r['scroll']<=r['width']+1 and r['header'] and r['footer'] and not r['buttons'],r
  return r
 tab('defense');expect(page.locator('.perimeterEmpty')).to_be_visible();expect(page.locator('.opsCatalog [data-defense-build]')).to_have_count(3);before=snap();fit();shot('empty-defense');assert before==snap()
 ids=page.evaluate('''()=>{const h=game.homePos();game.p.x=h.x;game.p.z=h.z;game.p.camp.rep=1000;game.p.level=6;for(const [id,name,prof]of [['qa-p','Павел Ветров','scientist'],['s_olga','Ольга Соколова','engineer'],['qa-m','Илья Морозов','medic'],['qa-s','Джейк Морган','scout']])game.camp.recruit({id,name,prof});for(const [i,dk]of ['pkm','nail','flame'].entries())game.p.base.push({t:'turretB',dk,x:h.x+7,z:h.z+1+i*3,r:0,hp:90,mag:0});Object.assign(game.p.inv,{scrap:200,chem:50,wood:50,cloth:10,a545:80,nails:30,gas:4});Object.assign(game.p.camp.res,{a545:15,nails:2,gas:1});game.baseDirty=true;const st=terraDefense.getState();game.save();return st.turrets.map(t=>t.id)}''')
 # Pending native recruit refreshes settle before measuring the modal.
 save_version=page.evaluate('JSON.parse(localStorage.getItem("terra_save")).v');page.wait_for_timeout(250);page.evaluate('game.ui.campPanel.open()');tab('defense');baseline=snap();report={'views':[]}
 for name,w,h in [('portrait',390,844),('narrow',320,568),('landscape',844,390),('desktop',1382,964)]:
  page.set_viewport_size({'width':w,'height':h});tab('defense');expect(page.locator('[data-defense-id]:visible')).to_have_count(1);g=fit()
  for i in [2,1,0]:
   button=page.locator('[data-perimeter-select]').nth(i);button.tap();expect(button).to_have_attribute('aria-pressed','true');expect(page.locator('[data-defense-id]:visible')).to_have_attribute('data-defense-id',ids[i]);assert snap()==baseline
   assert page.locator('[data-defense-id]:visible .perimeterDrawing').evaluate('''async e=>{const url=getComputedStyle(e).backgroundImage.slice(5,-2);return await new Promise(r=>{const i=new Image;i.onload=()=>r(i.naturalWidth===512);i.onerror=()=>r(false);i.src=url})}''')
  page.locator('[data-perimeter-select]').first.focus();page.keyboard.press('End');expect(page.locator('[data-perimeter-select]').last).to_be_focused();expect(page.locator('[data-defense-id]:visible')).to_have_attribute('data-defense-id',ids[0]);page.keyboard.press('Enter');expect(page.locator('[data-defense-id]:visible')).to_have_attribute('data-defense-id',ids[2]);page.keyboard.press('Home');page.keyboard.press('Space');expect(page.locator('[data-defense-id]:visible')).to_have_attribute('data-defense-id',ids[0]);
  page.locator('#campBody').evaluate('e=>e.scrollTop=0');page.wait_for_timeout(250);shot(name+'-defense')
  info=page.locator('[data-defense-id]:visible .campInfoButton');info.tap();expect(page.locator('.campInfoSheet')).to_be_visible();page.keyboard.press('Escape');expect(info).to_be_focused()
  supply=page.locator('[data-perimeter-fold=supply]');supply.locator('summary').tap();expect(supply).to_have_attribute('open','');expect(page.locator('[data-porter]')).to_have_count(4);fit();page.locator('.opsPorters').scroll_into_view_if_needed();shot(name+'-supply');supply.locator('summary').tap()
  page.locator('.opsPosts > summary').tap();expect(page.locator('.opsPositions > .defCard')).to_have_count(4);fit();page.locator('.opsPosts > summary').tap()
  # Every camp destination remains reachable and fits the same mobile shell.
  for dest in ['overview','settlers','build','expansion','more','tech','power','warehouses','contracts','territories']:
   tab(dest);fit()
  assert snap()==baseline,('read-only UI changed player or save',name)
  report['views'].append({'size':[w,h],'defense':g});print('PASS '+name+' camp routes, read-only selection, help, supply and guards',flush=True)
 # Virtual notch + home indicator; footer and close remain in the safe rectangle.
 page.set_viewport_size({'width':390,'height':844});page.evaluate("document.documentElement.style.cssText+=';--st:28px;--sb:30px;--sl:12px;--sr:12px'");tab('defense');fit()
 assert page.locator('#campPanel footer').evaluate('e=>e.getBoundingClientRect().bottom<=innerHeight-29')
 assert page.locator('#campPanel .x').evaluate('e=>e.getBoundingClientRect().top>=27')
 shot('safe-area');page.evaluate("for(const k of ['--st','--sb','--sl','--sr'])document.documentElement.style.removeProperty(k)")
 page.emulate_media(reduced_motion='reduce');assert page.locator('#campBody').evaluate('e=>getComputedStyle(e).scrollBehavior')=='auto';page.emulate_media(reduced_motion='no-preference')
 # Original transaction fails safely, then retries exactly once.
 page.locator('[data-perimeter-select]').nth(1).tap();page.locator('[data-perimeter-fold=supply] > summary').tap();before=snap()
 page.evaluate('''()=>{window.__storage=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='terra_save')throw new DOMException('QA quota','QuotaExceededError');return __storage.call(this,k,v)}}''')
 deposit=page.locator('[data-defense-deposit=nails]');deposit.tap();expect(page.locator('.defenseSaveError')).to_be_visible();page.evaluate('()=>{Storage.prototype.setItem=__storage}');assert snap()==before
 expect(page.locator('[data-defense-id]:visible')).to_have_attribute('data-defense-id',ids[1]);expect(page.locator('[data-perimeter-fold=supply]')).to_have_attribute('open','')
 page.locator('[data-defense-deposit=nails]').tap();assert page.evaluate('game.p.inv.nails===0&&game.p.camp.res.nails===32')
 # Fold state and selected turret survive real redraw, assigning changes only native order.
 porter=page.locator('[data-porter=s_olga]');porter.focus();page.keyboard.press('Enter');expect(page.locator('[data-porter=s_olga]')).to_have_attribute('aria-pressed','true');expect(page.locator('[data-porter=s_olga]')).to_be_focused();expect(page.locator('[data-defense-id]:visible')).to_have_attribute('data-defense-id',ids[1])
 page.locator('[data-perimeter-fold=supply] > summary').tap();page.locator('[data-perimeter-select]').first.tap()
 reload=page.locator('[data-defense-id]:visible [data-defense-focus^=reload]');reload.focus();page.keyboard.press('Enter');expect(page.locator('[data-defense-id]:visible [data-defense-focus^=reload]')).to_be_focused();assert page.evaluate('terraDefense.getState().turrets[0].mag')==60
 upgrade=page.locator('[data-defense-id]:visible [data-defense-focus^=upgrade]');cost=page.evaluate('terraDefense.getState().turrets[0].upgradeCost');inv=page.evaluate('({...game.p.inv})');upgrade.focus();page.keyboard.press('Space');expect(page.locator('[data-defense-id]:visible [data-defense-focus^=upgrade]')).to_be_focused();assert page.evaluate('terraDefense.getState().turrets[0].lvl')==2
 for k,v in cost.items():assert page.evaluate('k=>game.p.inv[k]',k)==inv[k]-v
 shot('saved-orders');assert page.evaluate('JSON.parse(localStorage.getItem("terra_save")).v')==save_version
 page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('game.state==="play"&&terraDefense.ready&&document.querySelector("#food").textContent.trim()');page.evaluate('game.loop=()=>{};game.ui.campPanel.open()');tab('defense')
 assert page.evaluate('game.p.camp.res.nails===32&&terraDefense.getState().turrets[0].mag===60&&terraDefense.getState().turrets[0].lvl===2&&terraDefense.getState().porters.some(s=>s.id==="s_olga")')
 expect(page.locator('[data-perimeter-fold=supply]')).not_to_have_attribute('open','');before=snap();page.locator('[data-perimeter-fold=plans] > summary').tap();page.locator('[data-defense-build=flame]').tap();expect(page.locator('#campPanel')).to_be_hidden();assert page.evaluate('game.build.on&&game.build.sel==="dFlame"&&game.state==="play"');assert before==snap()
 assert not errors,errors
 report['orders']={'saveEnvelopeVersion':save_version,'failedWriteRollback':True,'stock':32,'magazine':60,'level':2,'upgradeCost':cost,'porter':'s_olga','coldContinue':True,'previewNoCost':True};report['errors']=errors
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS safe area, reduced motion, native transactions, focus, cold continue and read-only construction preview; JS0',flush=True);b.close()
