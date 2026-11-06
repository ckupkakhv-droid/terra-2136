"""Real inventory/craft controls, read-only browsing, native costs and cold save.

Disposable profile. TERRA_TEST_URL accepts /play/ or standalone HTML via HTTP.
"""
import json,os,re
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-field-kit'));out.mkdir(parents=True,exist_ok=True)
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
capture=os.environ.get('TERRA_QA_CAPTURE','all')
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1382,'height':964},has_touch=True);page.set_default_timeout(90000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)))
 page.on('console',lambda m:errors.append(m.text) if m.type=='error' and m.text.startswith('[field-kit]') else None)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
 page.wait_for_function('game.state==="play"&&TERRA_KITS.ready&&terraDefense.ready&&document.getElementById("food").textContent.trim()')
 page.evaluate('game.loop=()=>{};game.ui.openInv("items")')
 def snap():return page.evaluate('JSON.stringify({p:game.p,save:localStorage.getItem("terra_save")})')
 def tab(name):
  page.locator('#inv [data-tab='+name+']').tap()
  expect(page.locator('#inv')).to_have_class(re.compile(r'\bfieldKit\b'))
 def catalog():
  tab('craft')
  if page.locator('.kitBack').is_visible():page.locator('.kitBack').tap()
  expect(page.locator('.kitCatalog')).to_be_visible()
 def reset_filters():
  page.locator('[data-kit-search=craft]').fill('');page.locator('[data-kit-type=all]').tap()
  if page.locator('.kitReady').get_attribute('aria-pressed')=='true':page.locator('.kitReady').tap()
 def shot(name):
  if capture=='none' or capture=='focused' and name not in ['narrow-items','portrait-recipe']:return
  page.evaluate('game.renderT()');page.screenshot(path=str(out/(name+'.png')),animations='disabled')
 def fit():
  data=page.locator('#invBody').evaluate('''r=>{const b=r.getBoundingClientRect(),win=r.closest('.win'),head=win.querySelector('h2').getBoundingClientRect(),foot=win.querySelector('footer').getBoundingClientRect();return{width:r.clientWidth,scroll:r.scrollWidth,winOverflow:win.scrollWidth-win.clientWidth,headAbove:head.bottom<=b.top+1,footerBelow:foot.top>=b.bottom-1,bad:[...r.querySelectorAll('button,input,select,summary')].filter(e=>e.getClientRects().length&&!e.closest('[hidden]')&&!e.closest('details:not([open]) > :not(summary)')).filter(e=>{const a=e.getBoundingClientRect();return (!e.closest('.invChips.scroll')&&(a.left<b.left-2||a.right>b.right+2))||a.width<43.5||a.height<43.5}).map(e=>e.getAttribute('aria-label')||e.textContent.slice(0,35)),overflowCards:[...r.querySelectorAll('.kitItem')].filter(e=>!e.hidden&&e.scrollWidth>e.clientWidth+1).map(e=>e.textContent)}}''')
  assert data['scroll']<=data['width']+1 and data['winOverflow']<=1 and data['headAbove'] and data['footerBelow'] and not data['bad'] and not data['overflowCards'],data
  assert page.locator('#inv .x').evaluate('e=>{const r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth+1&&r.width>=44&&r.height>=44}')
  return data
 # Empty/default views keep reading separate from invocation.
 expect(page.locator('.kitItems .kitUse')).to_have_count(1);shot('empty-items');empty=snap();catalog()
 count=page.evaluate('TERRA_DEFENSE_CTX.B.recipes.length');expect(page.locator('.kitRecipeChoice')).to_have_count(count)
 page.locator('[data-kit-choose=bandage]').tap();expect(page.locator('[data-craft=bandage]')).to_be_disabled()
 page.locator('[data-kit-recipe=bandage] .kitRecipeArt').tap();assert snap()==empty
 page.keyboard.press('Escape');expect(page.locator('.kitCatalog')).to_be_visible();assert page.evaluate('game.state')=='modal';shot('empty-catalog')
 page.evaluate('''()=>{Object.assign(game.p.inv,{scrap:24,wood:12,chem:6,cloth:8,bandage:3,medkit:1,food:2,water:2,a545:30,powder:6,nails:9,gas:1,scrollNG:2,blessed:2});game.p.hp=55;game.p.food=45;game.p.water=30;game.p.inf=25;game.p.rad=15;game.p.base=[];game.inSafe=false;game.ui.renderInv()}''')
 tab('items');catalog();page.evaluate('game.save()');baseline=snap();report={'views':[]}
 expected=page.evaluate('TERRA_DEFENSE_CTX.B.recipes.map(r=>({id:r.id,ready:game.canCraft(r),type:r.out._weapon||r.out._armor?"gear":"supplies"}))')
 for name,w,h in [('desktop',1382,964),('portrait',390,844),('narrow',320,568),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});tab('items');page.locator('[data-kit-search=items]').fill('');page.locator('[data-item-category=all]').tap()
  page.locator('#invBody').evaluate('e=>e.scrollTop=0');items=fit();shot(name+'-items')
  if name=='narrow':
   card=page.locator('.kitItem').first.bounding_box();area=page.locator('#invBody').bounding_box();assert card['y']+card['height']<=area['y']+area['height']+1,('First supplies card requires scrolling',card,area)
  page.locator('[data-kit-search=items]').fill('БЛАГОСЛОВЛЕННЫЙ');expect(page.locator('.kitItem:visible')).to_have_count(1);expect(page.locator('.kitItem:visible .nm')).to_have_text('Благословлённый свиток');fit()
  page.locator('[data-kit-search=items]').fill('несуществующий');expect(page.locator('.kitItems > .kitEmpty')).to_be_visible();page.get_by_role('button',name='Очистить поиск',exact=True).tap()
  page.locator('[data-item-category=med]').tap();expect(page.locator('[data-item-category=med]')).to_be_focused();expect(page.locator('.kitPocket:visible')).to_have_count(1);assert page.locator('.kitItem:visible .nm').all_text_contents()==['Бинт','Аптечка']
  page.locator('[data-item-category=all]').tap();catalog();reset_filters()
  actual=page.locator('.kitRecipeChoice').evaluate_all('ns=>ns.map(n=>({id:n.dataset.kitChoose,ready:n.dataset.ready==="true"}))');assert actual==[{'id':r['id'],'ready':r['ready']} for r in expected]
  catalog_fit=fit();page.locator('#invBody').evaluate('e=>e.scrollTop=0');shot(name+'-catalog')
  page.locator('[data-kit-type=gear]').tap();assert page.locator('.kitRecipeChoice:visible').count()==sum(r['type']=='gear' for r in expected)
  page.locator('[data-kit-type=all]').tap();page.locator('.kitReady').tap();assert page.locator('.kitRecipeChoice:visible').count()==sum(r['ready'] for r in expected)
  page.locator('.kitReady').tap();page.locator('[data-kit-search=craft]').fill('МОНТИРОВКА');expect(page.locator('.kitRecipeChoice:visible')).to_have_count(1)
  page.locator('[data-kit-choose=crowbar]').tap();expect(page.locator('.kitRecipePosition')).to_have_text('1 / 1');expect(page.get_by_role('button',name='Следующий чертёж',exact=True)).to_be_disabled();page.keyboard.press('Escape');expect(page.locator('[data-kit-choose=crowbar]')).to_be_focused()
  page.locator('[data-kit-search=craft]').fill('ничего-похожего');expect(page.locator('.kitCraft > .kitEmpty')).to_be_visible();page.get_by_role('button',name='Очистить поиск',exact=True).tap()
  page.locator('[data-kit-choose=medkit]').tap();expect(page.locator('[data-kit-recipe=medkit]')).to_be_visible();expect(page.locator('[data-craft=medkit]')).to_be_enabled()
  assert page.locator('[data-kit-recipe=medkit] .kitNeedNumber').all_text_contents()==['6/2','8/2'];assert page.locator('[data-kit-recipe=medkit] .kitNeedName').all_text_contents()==['Химикаты','Ткань']
  recipe_fit=fit();shot(name+'-recipe');page.locator('[data-kit-recipe=medkit] .kitRecipeArt').tap();assert snap()==baseline,'Recipe reading/illustration invoked craft'
  page.keyboard.press('Escape');page.locator('[data-kit-choose=antirad]').tap();expect(page.locator('[data-craft=antirad]')).to_be_disabled();expect(page.locator('[data-kit-recipe=antirad] .kitConditions')).to_contain_text('хим. стол');fit();shot(name+'-locked-recipe')
  page.keyboard.press('Escape');page.locator('[data-kit-choose=axe2]').tap();expect(page.locator('[data-craft=axe2]')).to_be_disabled();expect(page.locator('[data-kit-recipe=axe2] .kitConditions')).to_contain_text('ур.4');page.keyboard.press('Escape')
  page.locator('[data-kit-choose=spear]').tap();assert page.locator('[data-kit-recipe=spear] .kitRecipeArt').evaluate('''e=>{const t=document.createElement('template');t.innerHTML=TERRA_FIELD_KIT_DATA.weaponIcon('spear');return e.firstElementChild.outerHTML===t.content.firstElementChild.outerHTML}''')
  page.locator('.kitBack').tap();page.locator('[data-kit-search=craft]').fill('бинт');page.evaluate('game.ui.renderInv()');expect(page.locator('[data-kit-search=craft]')).to_have_value('бинт');expect(page.locator('.kitRecipeChoice:visible')).to_have_count(1);page.locator('[data-kit-search=craft]').fill('')
  page.locator('#inv .x').focus();page.keyboard.press('Shift+Tab');expect(page.locator('#inv footer [data-close]')).to_be_focused();page.keyboard.press('Tab');expect(page.locator('#inv .x')).to_be_focused()
  assert snap()==baseline,('Read-only inventory/recipe browsing changed player/save',name)
  report['views'].append({'viewport':[w,h],'items':items,'catalog':catalog_fit,'recipe':recipe_fit});print('PASS field kit layout and read-only browsing '+name,flush=True)
 report['recipes']=len(expected);report['available']=sum(r['ready'] for r in expected)
 # A real native craft is invoked only by its semantic button, including keyboard.
 page.set_viewport_size({'width':390,'height':844});catalog();reset_filters();page.locator('[data-kit-choose=bandage]').tap();before=page.evaluate('({cloth:game.p.inv.cloth,bandage:game.p.inv.bandage})');page.locator('[data-craft=bandage]').focus();page.keyboard.press('Enter')
 page.wait_for_function('(x)=>game.p.inv.cloth===x.cloth-2&&game.p.inv.bandage===x.bandage+2',arg=before);expect(page.locator('[data-kit-recipe=bandage]')).to_be_visible();expect(page.locator('[data-craft=bandage]')).to_be_focused();shot('crafted-bandage')
 page.evaluate('''()=>{window.__kitClick=game.ui.invClick;game.ui.invClick=function(e){const r=__kitClick.call(this,e);document.querySelector('#inv [data-tab=items]').focus();return r}}''');page.locator('[data-craft=bandage]').tap();page.evaluate('()=>{game.ui.invClick=__kitClick}');expect(page.locator('#inv [data-tab=items]')).to_be_focused()
 catalog();page.locator('[data-kit-choose=spear]').tap();before_weapons=page.evaluate('game.p.weapons.length');cost=page.evaluate('TERRA_DEFENSE_CTX.B.recipes.find(r=>r.id==="spear").need');materials=page.evaluate('({...game.p.inv})');page.locator('[data-craft=spear]').tap();page.wait_for_function('(n)=>game.p.weapons.length===n+1',arg=before_weapons)
 weapon=page.evaluate('game.p.weapons.find(w=>w.wt==="spear")');assert weapon
 for key,amount in cost.items():assert page.evaluate('(k)=>game.p.inv[k]',key)==materials[key]-amount
 # Native use buttons: Enter and Space work; consuming the last item restores focus.
 tab('items');page.locator('[data-item-category=all]').tap();hp=page.evaluate('game.p.hp');bandages=page.evaluate('game.p.inv.bandage');page.locator('button[data-use=bandage]').focus();page.keyboard.press('Enter');page.wait_for_function('(n)=>game.p.inv.bandage===n-1',arg=bandages);assert page.evaluate('game.p.hp')>hp;expect(page.locator('button[data-use=bandage]')).to_be_focused()
 page.locator('button[data-use=medkit]').focus();page.keyboard.press('Space');page.wait_for_function('game.p.inv.medkit===0');expect(page.locator('.kitHeaderTitle')).to_be_focused();assert page.evaluate('game.p.hp')==100;shot('used-medicine')
 saved=page.evaluate('({inv:{...game.p.inv},weaponIds:game.p.weapons.map(w=>w.uid)})');page.evaluate('game.save()');page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('game.state==="play"&&TERRA_KITS.ready&&document.getElementById("food").textContent.trim()');page.evaluate('game.loop=()=>{};game.ui.openInv("craft")');expect(page.locator('.kitCatalog')).to_be_visible();expect(page.locator('[data-kit-search=craft]')).to_have_value('')
 assert page.evaluate('({...game.p.inv})')==saved['inv'];assert page.evaluate('game.p.weapons.map(w=>w.uid)')==saved['weaponIds'];assert page.evaluate('(id)=>game.p.weapons.some(w=>w.uid===id&&w.wt==="spear")',weapon['uid'])
 report['actions']={'bandageCost':{'cloth':2},'bandageOutput':2,'weapon':'spear','weaponCost':cost,'keyboardUse':True,'lastItemFocus':True,'otherFocusPreserved':True,'coldContinue':True};assert not errors,errors;report['errors']=errors
 (out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS native craft materials/output/UID, Enter+Space use, last-item focus, cold save; JS0',flush=True);b.close()
