"""Native class controls retain selection, migration confirmation and saves."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-class-dossier-qa'));out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1382,'height':964});page.set_default_timeout(90000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:errors.append(m.text[:1000]) if m.type=='error' else None)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play" && game.sewers && TERRA_KITS.ready && terraDefense.ready');page.evaluate('()=>{game.loop=()=>{};if(document.getElementById("inv").classList.contains("hidden"))game.ui.openInv("skills");else document.querySelector("#inv [data-tab=skills]").click()}')
 expect(page.locator('.classDossier')).to_be_visible()
 page.evaluate('''()=>{window.__classSnap=()=>JSON.stringify({p:game.p,save:localStorage.getItem('terra_save')});}''')
 before=page.evaluate('__classSnap()');report={'views':[]}
 def fit(name):
  result=page.locator('.classDossier').evaluate('''root=>{const r=root.getBoundingClientRect();return{width:root.clientWidth,scroll:root.scrollWidth,escaped:[...root.querySelectorAll('button,summary')].filter(x=>x.getClientRects().length).filter(x=>{const b=x.getBoundingClientRect();return b.left<r.left-1||b.right>r.right+1}).map(x=>x.textContent.trim().slice(0,100))}}''')
  assert result['scroll']<=result['width']+1 and not result['escaped'],(name,result)
  overlaps=page.locator('.classDossier').evaluate('''root=>[...root.querySelectorAll('.classRecord')].map(c=>{const a=c.querySelector('.classEmblem').getBoundingClientRect(),b=c.querySelector('h4').getBoundingClientRect();return{name:c.dataset.classRecord,overlap:Math.min(a.right,b.right)-Math.max(a.left,b.left)>1&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>1,a:a.toJSON(),b:b.toJSON()}}).filter(x=>x.overlap)''')
  assert not overlaps,(name,'Class symbol overlaps title',overlaps)
  page.locator('#invBody').evaluate('e=>e.scrollTop=0')
  page.screenshot(path=str(out/(name+'.png')),animations='disabled');return result
 for name,w,h in [('desktop',1382,964),('portrait',390,844),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});expect(page.locator('[data-class-record]')).to_have_count(4)
  info=page.locator('[aria-label="Правила: Полевой медик"]');info.click()
  expect(page.locator('.classFieldGuide')).to_have_attribute('open','')
  expect(page.locator('#class-guide-medic')).to_contain_text('После выбора старые версии игры')
  page.locator('.classGuideBack').click();expect(info).to_be_focused();expect(info).to_be_in_viewport()
  report['views'].append({'viewport':name,'fit':fit(name+'-unselected')})
  assert page.evaluate('__classSnap()')==before,'Viewing class guide changed player/save'
 print('PASS four readable native classes/three sizes/original compatibility guide/focus/read-only player and save',flush=True)
 page.set_viewport_size({'width':1382,'height':964})
 page.locator('[data-circuit-toggle="on"]').click();page.wait_for_function('game.p.classProfile?.classId==="contourist"')
 expect(page.locator('[data-class-record="circuit"]')).to_have_class('classRecord isSelected')
 expect(page.locator('[data-circuit-toggle="off"]')).to_be_focused();expect(page.locator('[data-circuit-skill]')).to_have_count(3)
 page.locator('[data-circuit-skill]').last.click();expect(page.locator('[data-circuit-skill]').last).to_have_attribute('aria-pressed','true')
 page.locator('[data-circuit-toggle="off"]').click();page.wait_for_function('game.p.classProfile?.classId!=="contourist"')
 unchanged=page.evaluate('__classSnap()')
 page.locator('[data-tech-toggle="on"]').click();expect(page.locator('.classConfirmation')).to_contain_text('Профиль класса перейдёт на v3')
 assert page.evaluate('__classSnap()')==unchanged,'Opening migration confirmation changed profile'
 report['confirmViews']=[]
 for name,w,h in [('desktop',1382,964),('portrait',390,844),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});report['confirmViews'].append({'viewport':name,'fit':fit(name+'-technician-confirmation')})
 page.set_viewport_size({'width':1382,'height':964});page.locator('[data-tech-cancel]').click();expect(page.locator('[data-tech-toggle="on"]')).to_be_focused()
 assert page.evaluate('__classSnap()')==unchanged,'Cancelling migration changed profile'
 page.locator('[data-tech-toggle="on"]').click();page.locator('[data-tech-toggle="confirm"]').click();page.wait_for_function('game.p.classProfile?.classId==="technician"')
 expect(page.locator('[data-class-record="tech"]')).to_have_class('classRecord isSelected');expect(page.locator('[data-tech-toggle="off"]')).to_be_focused()
 assert page.evaluate('game.p.classProfile.v===3 && JSON.parse(localStorage.getItem("terra_save")).p.classProfile.classId==="technician"')
 for name,w,h in [('desktop',1382,964),('portrait',390,844),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});fit(name+'-technician')
  page.locator('[data-tech-skill]').last.click();expect(page.locator('[data-tech-skill]').last).to_have_attribute('aria-pressed','true')
 print('PASS native contourist selection/skills/removal, technician migration confirmation/cancel/real saved v3 and selected skills',flush=True)
 page.set_viewport_size({'width':1382,'height':964});page.locator('[data-scout-toggle="on"]').click()
 expect(page.locator('.classConfirmation')).to_contain_text('Перед выбором создаётся локальная копия')
 page.locator('[data-scout-toggle="confirm"]').click();page.wait_for_function('game.p.classProfile?.classId==="scout"')
 expect(page.locator('[data-scout-skill]')).to_have_count(3);fit('scout-selected')
 page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('game.state==="play"');page.evaluate('()=>{game.loop=()=>{};game.ui.openInv("skills")}')
 expect(page.locator('[data-class-record="scout"]')).to_have_class('classRecord isSelected')
 assert page.evaluate('game.p.classProfile.v===3 && game.p.classProfile.classId==="scout"')
 # An unsupported native profile stays disabled, with its status outside help.
 page.evaluate('''()=>{game.p.classProfile={v:999,classId:'unknown'}}''')
 page.locator('#inv [data-tab="items"]').click();page.locator('#inv [data-tab="skills"]').click()
 expect(page.locator('.classRoster button[data-circuit-toggle]')).to_be_disabled()
 expect(page.locator('.classDossier > small[role="status"]')).to_be_visible();fit('unsupported-profile')
 assert not errors,errors
 report['native']={'contouristAndSkills':True,'techConfirmCancel':True,'technicianSavedV3':True,'scoutConfirmation':True,'coldContinue':True,'unsupportedGuard':True}
 report['errors']=errors;(out/'report.json').write_text(json.dumps(report,indent=2));print('PASS scout confirmation/real selection/cold continuation/unsupported profile guard; JS0',flush=True);b.close()
