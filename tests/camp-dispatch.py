"""Actual native camp album: all sections, progression queries and contract actions.

Disposable profile, Chromium + local HTTP (TERRA_TEST_URL). Never reads a user's save.
"""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-camp-dispatch'));out.mkdir(parents=True,exist_ok=True)
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1382,'height':964},has_touch=True);page.set_default_timeout(90000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
 page.wait_for_function('game.state==="play"&&TERRA_KITS.ready&&terraDefense.ready&&document.getElementById("food").textContent.trim()&&window.terraCampLive')
 page.evaluate('game.loop=()=>{};game.ui.campPanel.open()')
 def snap():return page.evaluate('JSON.stringify({p:game.p,save:localStorage.getItem("terra_save")})')
 def select(tab):page.evaluate('(t)=>game.ui.campPanel.select(t)',tab)
 def shot(name):page.evaluate('game.renderT()');page.screenshot(path=str(out/(name+'.png')),animations='disabled')
 def fit():
  g=page.locator('#campBody').evaluate('''r=>{const b=r.getBoundingClientRect(),head=document.querySelector('#campPanel h2').getBoundingClientRect(),foot=document.querySelector('#campPanel footer').getBoundingClientRect();return{width:r.clientWidth,scroll:r.scrollWidth,headerAbove:head.bottom<=b.top+1,footerBelow:foot.top>=b.bottom-1,escaped:[...r.querySelectorAll('button,input,select,summary')].filter(e=>e.getClientRects().length&&!e.closest('[hidden]')&&!e.closest('details:not([open]) > :not(summary)')&&!e.closest('.dispatchContractRail')).filter(e=>{const x=e.getBoundingClientRect();return x.left<b.left-2||x.right>b.right+2||x.width<43.5||x.height<43.5}).map(e=>e.getAttribute('aria-label')||e.textContent.slice(0,30))}}''')
  assert g['scroll']<=g['width']+1 and g['headerAbove'] and g['footerBelow'] and not g['escaped'],g
  assert page.locator('#campPanel .x').evaluate('e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1}')
  return g
 def bridge():return page.evaluate('TERRA_CAMP_ALBUM_DATA.progression(game.p.camp)')
 select('contracts');expect(page.locator('.dispatchBoard')).to_be_visible();initial=snap()
 assert page.locator('.dispatchContractTab').count()==page.evaluate('game.p.camp.contracts.board.length')
 expect(page.locator('.dispatchHunt')).not_to_have_attribute('open','');fit();shot('empty-contracts')
 select('more');expect(page.locator('.dispatchIndex > button')).to_have_count(7)
 assert snap()==initial
 page.evaluate('''()=>{game.p.camp.rep=1000;for(const [i,name,prof]of [[0,'Павел Ветров','scientist'],[1,'Ольга Соколова','engineer'],[2,'Илья Морозов','medic'],[3,'Джейк Морган','scout']]){const r=game.camp.recruit({id:i===1?'s_olga':'qa-dispatch-'+i,name,prof});if(!r.ok)throw Error('Recruit failed')}game.p.camp.settlers['qa-dispatch-2'].injuredUntil=game.p.camp.sim.tick+100;game.p.camp.tier=2;game.camp.refreshContracts();game.ui.campPanel.select('more')}''')
 report={'views':[]};before=snap()
 select('settlers');nativePhoto=page.locator('[data-resident="s_olga"] .residentPortrait img').get_attribute('src');assert nativePhoto
 select('contracts');expect(page.locator('.contractCard:visible [data-resident-id="s_olga"] img')).to_have_attribute('src',nativePhoto);assert snap()==before;report['sameNativePortrait']=True
 for label,w,h in [('desktop',1382,964),('portrait',390,844),('narrow',320,568),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});select('more');expect(page.locator('.dispatchIndex')).to_be_visible();index=fit();shot(label+'-index')
  links=page.locator('.dispatchIndex > button').evaluate_all('ns=>ns.map(n=>n.dataset.campTab)');assert links==['defense','tech','territories','contracts','power','warehouses','pine'],links
  assert page.locator('.dispatchIndexText strong').evaluate_all('ns=>ns.every(e=>e.offsetHeight<=parseFloat(getComputedStyle(e).lineHeight)*e.textContent.trim().split(/\\s+/).length+2)'),'A section name breaks inside a word'
  assert page.locator('#campPanel footer [data-close]').evaluate('e=>{const r=document.createRange();r.selectNodeContents(e);return r.getClientRects().length===1}'),'Play footer wraps'
  for tab in links:
   page.locator('.dispatchIndex > [data-camp-tab="'+tab+'"]').tap();assert page.evaluate('game.ui.campPanel.tab')==tab
   page.locator('.fbBack').tap();assert page.evaluate('game.ui.campPanel.tab')=='more',tab
  page.locator('.fbMore').tap();assert page.evaluate('game.ui.campPanel.tab')=='overview'
  page.locator('[data-fieldbook-section="expansion"]').tap();expect(page.locator('.dispatchJourney [aria-current=step]')).to_have_count(1)
  expected=[g for g in bridge()['next'][0]['goals'] if g['max']>0]
  actual=page.locator('.dispatchTierChecks > li').evaluate_all('ns=>ns.map(n=>({text:n.children[1].textContent,value:n.querySelector("b").textContent,ok:n.dataset.met==="true"}))')
  assert actual==[{'text':g['label'].strip(),'value':str(g['value'])+' / '+str(g['max']),'ok':g['ok']} for g in expected]
  expansion=fit();shot(label+'-expansion')
  select('contracts');expect(page.locator('.dispatchBoard')).to_be_visible();assert page.locator('.contractCard:visible').count()==1
  assert page.locator('.dispatchDeckCount').evaluate('e=>{const r=document.createRange();r.selectNodeContents(e);return r.getClientRects().length===1}'),'Contract counter wraps'
  tab=page.locator('.dispatchContractTab[aria-selected=true]');expect(tab).to_have_attribute('tabindex','0')
  assert page.locator('.dispatchContractTab strong').evaluate_all('ns=>ns.every(e=>e.offsetHeight<=parseFloat(getComputedStyle(e).lineHeight)*e.textContent.trim().split(/\\s+/).length+2)'),'A contract name breaks inside a word'
  assert page.locator('.dispatchContractImage:visible').evaluate('''async e=>{const url=getComputedStyle(e).backgroundImage.slice(5,-2);return await new Promise(resolve=>{const im=new Image;im.onload=()=>resolve(im.naturalWidth>300);im.onerror=()=>resolve(false);im.src=url})}''')
  photo=page.locator('.contractCard:visible .dispatchMemberPhoto').first
  assert photo.evaluate('''async e=>{const url=getComputedStyle(e).backgroundImage.slice(5,-2);return await new Promise(resolve=>{const im=new Image;im.onload=()=>resolve(im.naturalWidth===256);im.onerror=()=>resolve(false);im.src=url})}''')
  card=page.locator('.contractCard:visible');expect(card.locator('[data-resident-id="qa-dispatch-2"]')).to_be_disabled()
  member=card.locator('.contractSquad > button:not(:disabled)').first;member.tap();expect(member).to_have_attribute('aria-pressed','true')
  chance=card.locator('.contractChance').inner_text();assert '% успеха' in chance
  cid=card.get_attribute('data-contract-id');page.locator('.dispatchDeckControls button').last.tap();page.locator('.dispatchContractTab[data-contract-id="'+cid+'"]').tap()
  expect(member).to_have_attribute('aria-pressed','true');expect(card.locator('.contractChance')).to_have_text(chance)
  expect(card.locator('[data-dispatch-action=send]')).to_be_enabled();member.tap()
  contracts=fit();shot(label+'-contracts-actions');page.locator('#campBody').evaluate('e=>e.scrollTop=0');shot(label+'-contracts')
  page.locator('.dispatchHunt > summary').tap();expect(page.locator('.campHunting select')).to_be_visible();fit();page.locator('.dispatchHunt > summary').tap()
  assert snap()==before,('Read-only navigation/crew preview changed player or save',label)
  report['views'].append({'viewport':[w,h],'index':index,'expansion':expansion,'contracts':contracts})
 print('PASS four sizes / seven native destinations / actual tier requirements / illustrated contract deck / original squad selection / read-only player+save',flush=True)
 # Keyboard selection, native tab panels, rotation and a genuinely missing requirement link.
 select('contracts');page.locator('.dispatchContractTab[aria-selected=true]').focus();page.keyboard.press('End');last=page.locator('.dispatchContractTab').last;expect(last).to_be_focused();expect(last).to_have_attribute('aria-selected','true');page.keyboard.press('ArrowRight');expect(page.locator('.dispatchContractTab').first).to_be_focused();page.keyboard.press('Home')
 page.set_viewport_size({'width':390,'height':844});fit();page.set_viewport_size({'width':844,'height':390});fit();assert snap()==before
 select('expansion');destination=page.evaluate('TERRA_CAMP_ALBUM_DATA.expansion(game).tab');page.locator('.dispatchTask > .campButton').first.tap();assert page.evaluate('game.ui.campPanel.tab')==destination
 # Native progression computes all five ranks; pure queries and illustration do not write p/save.
 ranks=[]
 for tier in range(1,6):
  page.evaluate('(t)=>game.p.camp.tier=t',tier);fixture=snap();select('expansion');expect(page.locator('.dispatchJourney [aria-current=step]')).to_have_text(['IСтоянка','IIЛагерь','IIIФорпост','IVПосёлок','VГород'][tier-1]);assert snap()==fixture
  ranks.append({'tier':tier,'next':len(bridge()['next'])})
 report['ranks']=ranks
 # A registered section may be added after the album has already decorated More.
 page.set_viewport_size({'width':390,'height':844});select('more');fixture=snap()
 assert page.evaluate('''()=>terraCampUI.registerSection({id:'qa-album',label:'Полевые записи',order:9,render(container){container.querySelector('.campSection__list').textContent='Записи экспедиции'}})''')
 custom=page.locator('.dispatchIndex > [data-camp-tab="qa-album"]');expect(custom).to_be_visible();expect(custom.locator('.dispatchIndexArt')).to_have_count(1);custom.tap();expect(page.locator('.campSection[data-camp-section="qa-album"]')).to_be_visible();page.locator('.fbBack').tap();assert page.evaluate('terraCampUI.tab')=='more';assert snap()==fixture
 print('PASS keyboard/wrap/rotation, native destination and five read-only progression ranks',flush=True)
 # The paid reroll is the original button: real reputation debit, saved and once per day.
 page.evaluate('game.p.camp.tier=2;game.p.camp.rep=40');select('contracts');rep=page.evaluate('game.p.camp.rep');page.locator('.dispatchBoardSummary button').tap()
 expect(page.locator('.dispatchBoardSummary button')).to_be_disabled();assert page.evaluate('game.p.camp.rep')==rep-page.evaluate('TERRA_DEFENSE_CTX.B.camp.contracts.rerollRep')
 assert page.evaluate('game.p.camp.contracts.rerollDay===game.p.camp.contracts.day')
 # Take the selected real offer; the original handler closes the menu and tracks it.
 chosen=page.evaluate('game.p.camp.contracts.board.find(c=>!["liberate","defend"].includes(c.type)).id')
 page.locator('.dispatchContractTab[data-contract-id="'+chosen+'"]').tap();page.locator('.contractCard:visible [data-dispatch-action=take]').tap();expect(page.locator('#campPanel')).to_be_hidden()
 assert page.evaluate('(id)=>game.p.camp.contracts.active.some(c=>c.id===id&&c.state==="player")',chosen)
 page.evaluate('game.ui.campPanel.open()');select('contracts');expect(page.locator('.contractCard:visible')).to_have_attribute('data-contract-id',chosen);expect(page.locator('.contractCard:visible')).to_have_attribute('data-contract-state','player')
 # Send a second actual offer with one available settler, without changing native commands.
 chosen2=page.evaluate('game.p.camp.contracts.board.find(c=>!["liberate","defend"].includes(c.type)).id')
 page.locator('.dispatchContractTab[data-contract-id="'+chosen2+'"]').tap();card=page.locator('.contractCard:visible');member=card.locator('.contractSquad > button:not(:disabled)').first;sid=member.get_attribute('data-resident-id');member.tap();card.locator('[data-dispatch-action=send]').tap()
 expect(page.locator('.contractCard:visible')).to_have_attribute('data-contract-state','squad');assert page.evaluate('({id,sid})=>game.p.camp.contracts.active.some(c=>c.id===id&&c.state==="squad"&&c.squad.includes(sid))',{'id':chosen2,'sid':sid})
 assert page.evaluate('(id)=>game.p.camp.settlers[id].mission',sid)
 page.evaluate('game.save()');raw=page.evaluate('localStorage.getItem("terra_save")');assert raw and chosen in raw and chosen2 in raw
 shot('active-squad');report['actions']={'rerollDebit':8,'playerActive':True,'squadActive':True,'nativeMission':True}
 page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('game.state==="play"&&TERRA_KITS.ready&&document.getElementById("food").textContent.trim()');page.evaluate('game.loop=()=>{};game.ui.campPanel.open()');select('contracts');expect(page.locator('.dispatchContractTab')).to_have_count(page.evaluate('game.p.camp.contracts.active.length+game.p.camp.contracts.board.length+game.p.camp.contracts.history.filter(c=>["done","failed"].includes(c.state)).slice(-3).length'))
 assert page.evaluate('({id,sid})=>game.p.camp.contracts.active.some(c=>c.id===id&&c.state==="squad"&&c.squad.includes(sid))',{'id':chosen2,'sid':sid})
 assert not errors,errors;report['errors']=errors;(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS native reroll debit/save/daily guard, personal take, squad dispatch/mission and cold continue; JS0',flush=True);b.close()
