"""Полевой альбом: реальные папки/поиск/дела/приказы и свободный игровой HUD."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-camp-fieldbook'));out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1382,'height':964},has_touch=True);page.set_default_timeout(90000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play"&&game.sewers&&TERRA_KITS.ready&&terraDefense.ready');page.evaluate('()=>{game.loop=()=>{};game.ui.campPanel.open()}')
 expect(page.locator('.fbHomeBoard')).to_be_visible();empty=page.evaluate('JSON.stringify({p:game.p,save:localStorage.getItem("terra_save")})')
 page.locator('[data-fieldbook-section="settlers"]').tap();expect(page.locator('.opsEmptyRoster')).to_be_visible();page.screenshot(path=str(out/'empty-residents.png'),animations='disabled')
 assert page.evaluate('JSON.stringify({p:game.p,save:localStorage.getItem("terra_save")})')==empty
 page.evaluate('''()=>{const h=game.homePos();game.p.x=h.x;game.p.z=h.z+5;game.p.camp.rep=1000;for(const [i,name,prof]of [[0,'Павел Ветров','scientist'],[1,'Ольга Соколова','engineer'],[2,'Илья Морозов','medic'],[3,'Джейк Морган','scout'],[4,'Вера Крылова','builder'],[5,'Алексей Серов','gatherer'],[6,'Марина Белова','medic'],[7,'Степан Зотов','engineer']]){const r=game.camp.recruit({id:'qa-book-'+i,name,prof,pos:h});if(!r.ok)throw Error('Recruit failed');game.p.camp.settlers['qa-book-'+i].pos={x:h.x+(i%4)*.8,z:h.z+Math.floor(i/4)*.8};}game.ui.campPanel.open()}''')
 page.evaluate('game.ui.campPanel.select("overview")');expect(page.locator('.fbHomeBoard')).to_be_visible();page.set_default_timeout(15000);report={'views':[]}
 def snap():return page.evaluate('JSON.stringify({p:game.p,save:localStorage.getItem("terra_save")})')
 before=snap()
 def fit():
  result=page.locator('#campBody').evaluate('''r=>{const b=r.getBoundingClientRect(),foot=document.querySelector('#campPanel footer').getBoundingClientRect(),head=document.querySelector('#campPanel h2').getBoundingClientRect();return{width:r.clientWidth,scroll:r.scrollWidth,headAbove:head.bottom<=b.top+1,footerBelow:foot.top>=b.bottom-1,escaped:[...r.querySelectorAll('button,input,summary')].filter(e=>e.getClientRects().length&&!e.closest('details:not([open]) > :not(summary)')).filter(e=>{const x=e.getBoundingClientRect();return x.left<b.left-2||x.right>b.right+2}).map(e=>e.getAttribute('aria-label')||e.textContent.slice(0,60))}}''')
  assert result['scroll']<=result['width']+1 and result['headAbove'] and result['footerBelow'] and not result['escaped'],result
  return result
 def shot(name):page.evaluate('game.renderT()');page.screenshot(path=str(out/(name+'.png')),animations='disabled')
 for name,w,h in [('desktop',1382,964),('portrait',390,844),('narrow',320,568),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});page.evaluate('game.ui.campPanel.select("overview")');expect(page.locator('.fbHomeBoard')).to_be_visible();home=fit();shot(name+'-home')
  page.locator('[data-fieldbook-section="settlers"]').tap();expect(page.locator('.residentRows .fbPhoto')).to_have_count(8)
  assert page.locator('.residentRows .fbPhoto').first.evaluate('''async e=>{const s=getComputedStyle(e).backgroundImage,url=s.slice(5,-2);return await new Promise(resolve=>{const im=new Image;im.onload=()=>resolve(im.naturalWidth===256);im.onerror=()=>resolve(false);im.src=url})}''')
  roster=fit();shot(name+'-residents')
  page.locator('#residentSearchInput').fill('Павел');expect(page.locator('.residentRow:not(.campSearchHidden)')).to_have_count(1);page.locator('[data-resident="qa-book-0"]').tap();expect(page.locator('.fbAssignment')).to_be_visible();expect(page.locator('.campJobs')).to_be_hidden();dossier=fit();shot(name+'-dossier')
  info=page.locator('.dossier .deskInfo');info.tap();expect(page.locator('.campInfoSheet')).to_be_visible();page.locator('.campInfoClose').tap();expect(info).to_be_focused()
  page.locator('.fbChangeJob').tap();expect(page.locator('.campJobs')).to_be_visible();page.locator('.fbChangeJob').tap();expect(page.locator('.campJobs')).to_be_hidden()
  page.locator('[data-camp-back="list"]').tap();expect(page.locator('#residentSearchInput')).to_have_value('Павел');page.locator('.residentSearch button').tap();expect(page.locator('#residentSearchInput')).to_be_focused()
  page.locator('.fbBack').tap();page.locator('[data-fieldbook-section="build"]').tap();expect(page.locator('.fbBlueprintArt')).to_have_count(4);plans=fit();shot(name+'-plans')
  page.locator('.fbOtherPlans summary').tap();expect(page.locator('.fbOtherPlans [data-building]')).to_have_count(6)
  page.locator('.fbBack').tap();page.locator('[data-fieldbook-section="expansion"]').tap();assert page.evaluate('game.ui.campPanel.tab')=='expansion'
  page.locator('.fbMore').tap();assert page.evaluate('game.ui.campPanel.tab')=='more'
  assert snap()==before,('Reading changed player/save',name)
  report['views'].append({'viewport':[w,h],'home':home,'roster':roster,'dossier':dossier,'plans':plans})
 print('PASS four sizes/home folders/photo roster/search/dossier/hidden orders/four illustrated plans/other native buildings/read-only player+save',flush=True)
 # The compact world layer groups close residents without overlapping HUD badges.
 page.locator('#campPanel footer [data-close="campPanel"]').tap();page.wait_for_function('game.state==="play"');page.set_viewport_size({'width':390,'height':844});page.evaluate('()=>{game.workerSceneContext();game.campLifeUpdate(.05);const h=game.homePos(),y=TERRA_DEFENSE_CTX.Y(h.x,h.z);game.cam.position.set(h.x,y+24,h.z+20);game.cam.lookAt(h.x,y+1,h.z);game.cam.updateMatrixWorld();game.renderT()}');page.wait_for_timeout(500)
 worldBefore=snap();shot('compact-world');badges=page.locator('.campLiveTag:not([hidden])');assert 0<badges.count()<=4,page.evaluate('({anchors:terraCampLive.anchors(),modals:[...document.querySelectorAll(".modal:not(.hidden),.screen:not(.hidden)")].map(n=>n.id),camera:game.cam.position.toArray(),size:[game.W,game.H],state:game.state})')
 report['badges']=badges.evaluate_all('''nodes=>nodes.map(e=>{const r=e.getBoundingClientRect();return{label:e.getAttribute('aria-label'),rect:r.toJSON(),nameClipped:getComputedStyle(e.querySelector('b')).clipPath!=='none'}})''')
 for i,a in enumerate(report['badges']):
  assert a['rect']['width']>=48 and a['rect']['height']>=48 and a['nameClipped']
  for c in report['badges'][i+1:]:
   x=a['rect'];y=c['rect'];assert min(x['right'],y['right'])<=max(x['left'],y['left']) or min(x['bottom'],y['bottom'])<=max(x['top'],y['top'])
 assert page.evaluate('Object.values(game.p.camp.settlers).every(s=>!game.npcV[s.id]?.tag?.visible)')
 shot('compact-world');badges.first.tap();expect(page.locator('#campLiveMenu h3')).to_be_visible();assert page.locator('#campLiveMenu').evaluate('e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.top>=0&&r.right<=innerWidth&&r.bottom<=innerHeight}')
 shot('context-card')
 page.set_viewport_size({'width':844,'height':390});page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
 page.locator('#campLiveMenu').evaluate('e=>e.scrollTop=e.scrollHeight');expect(page.locator('.campLiveClose')).to_be_in_viewport()
 page.keyboard.press('End');page.keyboard.press('Tab');expect(page.locator('.campLiveClose')).to_be_focused()
 page.set_viewport_size({'width':390,'height':844});page.evaluate('()=>new Promise(r=>requestAnimationFrame(()=>requestAnimationFrame(r)))')
 if page.locator('#campLiveMenu').get_attribute('data-kind')=='group':page.locator('#campLiveMenu [role="menuitem"]').first.tap()
 expect(page.locator('#campLiveMenu [aria-label$=": Дело"]')).to_be_visible();shot('resident-context')
 page.locator('#campLiveMenu [aria-label$=": Дело"]').tap();expect(page.locator('.residentIdentityHead')).to_be_visible()
 assert snap()==worldBefore,'World badge/dossier inspection changed player/save'
 assert not errors,errors
 report['errors']=errors;(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS compact grouped badges/no overlap/no repeated native names/context card inside viewport/read-only state; JS0',flush=True);b.close()
