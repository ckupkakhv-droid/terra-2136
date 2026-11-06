"""Native roster/defense: empty and populated views, navigation and saved orders.

Disposable profile only; TERRA_TEST_URL may be play/ or standalone HTTP HTML.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-camp-operations-qa'));out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=browser.new_page(viewport={'width':1382,'height':964});page.set_default_timeout(90000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:errors.append(m.text[:1000]) if m.type=='error' else None)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
 page.wait_for_function('window.terraCampUI && terraDefense.ready && document.querySelector(".campOperations")')
 page.evaluate('game.loop=()=>{}');page.locator('#bCamp').click()
 page.evaluate('''()=>{terraDefense.getState();window.__opsSnap=()=>JSON.stringify({camp:game.p.camp,inv:game.p.inv,base:game.p.base,save:localStorage.getItem('terra_save')});}''')
 def tab(name):
  button=page.locator('#campTabs [data-camp-tab="'+name+'"]')
  if not button.count() or not button.is_visible():
   page.locator('#campTabs [data-camp-tab="more"]').click();page.locator('.campMore [data-camp-tab="'+name+'"]:visible').click()
  else:button.click()
  page.wait_for_function('t=>terraCampUI.tab===t',arg=name)
 def fit(name):
  result=page.locator('#campBody').evaluate('''e=>{const r=e.getBoundingClientRect();return{width:e.clientWidth,scroll:e.scrollWidth,escaped:[...e.querySelectorAll('button,input,summary')].filter(x=>x.getClientRects().length&&getComputedStyle(x).visibility!=='hidden').filter(x=>{const b=x.getBoundingClientRect();return b.left<r.left-1||b.right>r.right+1}).map(x=>x.textContent.trim().slice(0,90))}}''')
  assert result['scroll']<=result['width']+1 and not result['escaped'],(name,result)
  page.screenshot(path=str(out/(name+'.png')));return result
 report={'empty':[],'populated':[]}
 initial=page.evaluate('__opsSnap()')
 for name,w,h in [('desktop',1382,964),('portrait',390,844),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});tab('settlers')
  expect(page.locator('.opsRosterEmpty')).to_be_visible();expect(page.locator('.residentSearch')).not_to_be_visible()
  expect(page.locator('.residentTasks')).not_to_be_visible();expect(page.locator('.residentRecommendation')).not_to_be_visible()
  a=fit(name+'-empty-residents');page.locator('.opsRecruit > summary').click()
  expect(page.locator('.opsRecruit .campCard')).to_be_visible();fit(name+'-recruitment')
  page.locator('.opsRecruit > summary').click();tab('defense')
  page.locator('.opsPosts > summary').click();expect(page.locator('.opsPositions > .defCard')).to_have_count(4)
  page.locator('.opsPositions .defAction').first.click();expect(page.locator('.defPicker .campReason')).to_be_visible()
  fit(name+'-guard-posts');page.locator('.opsPosts > summary').click()
  info=page.locator('[aria-label="Как работает снабжение обороны"]');info.click()
  expect(page.locator('.campInfoSheet')).to_contain_text('больше чем на треть')
  page.keyboard.press('Escape');expect(info).to_be_focused()
  b=fit(name+'-empty-defense');assert page.evaluate('__opsSnap()')==initial,'Reading empty sections issued an order'
  report['empty'].append({'viewport':name,'roster':a,'defense':b})
 print('PASS empty roster/recruitment/four real posts/empty picker/defense guide + focus/three sizes/read-only state',flush=True)
 page.set_viewport_size({'width':1382,'height':964})
 fixture=page.evaluate('''()=>{
  const g=game,h=g.homePos();g.p.camp.rep=1000;g.p.level=6;
  for(const [id,name] of [['ops-1','Марфа Оченьдлиннаяфамилияпоселенца'],['ops-2','Павел']]){if(!g.camp.recruit({id}).ok)throw Error('Fixture recruitment failed');g.p.camp.settlers[id].name=name;}
  for(const [i,dk] of ['pkm','nail','flame'].entries())g.p.base.push({t:'turretB',dk,x:h.x+7,z:h.z+1+i*3,r:0,hp:90,mag:0});
  Object.assign(g.p.inv,{scrap:200,chem:50,wood:50,cloth:10,a545:80,nails:30,gas:4});
  Object.assign(g.p.camp.res,{a545:15,nails:2,gas:1});g.baseDirty=true;terraDefense.getState();
  const r=g.save();if(!r.ok)throw Error('Fixture save failed');return{pkm:terraDefense.getState().turrets.find(t=>t.dk==='pkm').id,saveVersion:JSON.parse(localStorage.getItem('terra_save')).v};
 }''')
 tab('settlers');snapshot=page.evaluate('__opsSnap()')
 page.locator('.opsQuickOrder > summary').click();page.locator('[data-worker-task="wood"]').click()
 expect(page.locator('.opsQuickOrder')).to_have_attribute('open','')
 expect(page.locator('.opsQuickOrder > summary')).to_contain_text('Дерево')
 expect(page.locator('.residentRecommendation')).to_be_visible();page.locator('.opsQuickOrder > summary').click()
 for name,w,h in [('desktop',1382,964),('portrait',390,844),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});tab('settlers')
  expect(page.locator('.opsRosterEmpty')).to_have_count(0);search=page.locator('#residentSearchInput');expect(search).to_be_visible()
  search.fill('марфа');expect(page.locator('.residentRow:visible')).to_have_count(1)
  page.locator('[data-worker-filter="free"]').click();expect(search).to_have_value('марфа')
  page.locator('.residentRow:visible .residentSummary').click();expect(page.locator('.dossier')).to_be_visible()
  page.locator('[data-camp-back="list"]').click();expect(search).to_have_value('марфа')
  page.locator('.residentSearch button').click();expect(search).to_be_focused();expect(page.locator('.residentRow:visible')).to_have_count(2)
  expect(page.locator('.opsRosterHead')).to_be_visible()
  a=fit(name+'-residents');tab('defense');expect(page.locator('[data-defense-id]')).to_have_count(3)
  b=fit(name+'-defense');assert page.evaluate('__opsSnap()')==snapshot,'Reading populated sections issued an order'
  report['populated'].append({'viewport':name,'roster':a,'defense':b})
 print('PASS populated roster/filter/search/dossier return/three native turret kinds/three sizes/read-only state',flush=True)
 page.set_viewport_size({'width':1382,'height':964})
 # Drive the real rendered transfer button through failure and confirmed retry.
 before=page.evaluate('__opsSnap()')
 page.evaluate('''()=>{window.__opsStorage=Storage.prototype.setItem;Storage.prototype.setItem=function(k,v){if(k==='terra_save')throw new DOMException('QA quota','QuotaExceededError');return __opsStorage.call(this,k,v)}}''')
 page.locator('[data-defense-deposit="nails"]').click()
 page.evaluate('()=>{Storage.prototype.setItem=__opsStorage}')
 expect(page.locator('.defenseSaveError')).to_be_visible();assert page.evaluate('__opsSnap()')==before,'Failed transfer changed saved resources'
 page.locator('[data-defense-deposit="nails"]').click()
 assert page.evaluate('game.p.inv.nails===0 && game.p.camp.res.nails===32')
 assert page.evaluate('JSON.parse(localStorage.getItem("terra_save")).v')==fixture['saveVersion'],'Saved envelope version changed'
 page.locator('[aria-label="Зарядить из рюкзака: Спарка ПКМ"]').click()
 assert page.evaluate('id=>terraDefense.getState().turrets.find(t=>t.id===id).mag',fixture['pkm'])==60
 fit('saved-defense-orders')
 # Cold continuation proves that rendered actions reached the native save path.
 page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('game.state==="play" && terraDefense.ready')
 page.evaluate('game.loop=()=>{}');assert page.evaluate('game.p.camp.res.nails===32 && terraDefense.getState().turrets.find(t=>t.dk==="pkm").mag===60')
 page.locator('#bCamp').click();tab('defense')
 page.evaluate('''()=>{window.__opsSnap=()=>JSON.stringify({camp:game.p.camp,inv:game.p.inv,base:game.p.base,save:localStorage.getItem('terra_save')})}''')
 saved=page.evaluate('__opsSnap()');page.locator('[data-defense-build="flame"]').click()
 expect(page.locator('#campPanel')).not_to_be_visible()
 assert page.evaluate('game.build.on && game.build.sel==="dFlame" && game.state==="play"')
 assert page.evaluate('__opsSnap()')==saved,'Blueprint preview spent resources'
 report['orders']={'failedTransferRollback':True,'retryStock':32,'reloadMagazine':60,'coldContinuation':True,'previewOnly':True}
 assert not errors,errors
 report['errors']=errors;(out/'report.json').write_text(json.dumps(report,indent=2));print('PASS native transfer failure/rollback/retry/save/reload/cold continuation/build preview; JS0',flush=True)
 browser.close()
