"""Real browser persistence integration, with teleported disposable character.
Combat damage/AI presentation is inspected separately; this test injects lethal
hits and one synchronous localStorage failure to exercise native durable paths.
"""
from pathlib import Path
import os,shutil
from playwright.sync_api import sync_playwright,expect
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-sewer-boss-qa'));out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome'),args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(30000);errors=[]
 page.on('pageerror',lambda e:(print('PAGEERROR',e.stack,flush=True),errors.append(str(e))))
 page.goto(os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8082/play/'),timeout=90000)
 page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.sewers')
 def enter():
  page.evaluate('game.p.x=12;game.p.z=-10;game.camT=null');page.locator('#sewerAction').click();page.wait_for_function('!!game.dg && !game.dungeonTransition')
 def chamber():
  page.evaluate('const r=game.dg.ch.rooms[6];game.p.x=r.x;game.p.z=r.z;game.camT=null')
 def continue_save():
  page.reload();page.locator('#mContinue').click();page.wait_for_function('game.state==="play" && !!game.sewers')
 enter()
 for i in [1,3]:
  page.evaluate('(i)=>{const r=game.dg.ch.rooms[i];game.p.x=r.x+4;game.p.z=r.z;game.camT=null}',i)
  expect(page.locator('#sewerAction')).to_have_text('Включить насос [E]');page.locator('#sewerAction').click();page.wait_for_function('(i)=>game.sewers.pumps.includes(i)',arg=i)
 chamber();expect(page.locator('#sewerRecording')).to_be_visible()
 page.keyboard.press('m');page.keyboard.press('m');page.keyboard.press('i');page.keyboard.press('l')
 expect(page.locator('#sewerRecording')).to_be_visible();expect(page.locator('#wmap')).not_to_be_visible()
 assert not page.locator('#sewerRecording').evaluate('(e)=>e.inert')
 page.locator('#recordingSkip').click()
 page.wait_for_function('game.enemies.some(e=>e.boss==="sewer_raphael"&&e.inst)')
 page.wait_for_function('game.sewers.ratCount===3')
 # Stop ordinary enemies during the diagnostic image; no persistence is altered.
 page.evaluate('game.camT=null;for(const e of game.enemies)e.dmg=0')
 page.wait_for_timeout(800);page.screenshot(path=str(out/'raphael.png'))
 outcome=page.evaluate('''() => {
 const boss=game.enemies.find(e=>e.boss==='sewer_raphael'),hp=boss.hp,uid=game.p.uid;
 const set=Storage.prototype.setItem;
 try {Storage.prototype.setItem=function(){throw new DOMException('Injected fixture','QuotaExceededError')};game.hurtEnemy(boss,hp+10000);}
 finally {Storage.prototype.setItem=set;}
 const failed={dead:boss.dead,hp:boss.hp,def:game.defeated[game.dg.key],uid:game.p.uid,chests:game.p.durableChests?.entries.length||0};
 game.hurtEnemy(boss,boss.hp+10000);
 return {before:{hp,uid},failed,dead:boss.dead,def:game.defeated[game.dg.key],entries:game.p.durableChests?.entries};
 }''')
 assert not outcome['failed']['dead'] and outcome['failed']['hp']==outcome['before']['hp'],outcome
 assert not outcome['failed'].get('def') and outcome['failed']['chests']==0,outcome
 assert outcome['failed']['uid']==outcome['before']['uid'],outcome
 assert outcome['dead'] and outcome['def']==1 and len(outcome['entries'])==1,outcome
 reward=outcome['entries'][0]['items'][0]['weapon'];assert reward['wt']=='sewer_sai' and reward['r']==4,reward
 uid=reward['uid'];print('PASS real browser failed-write veto and retry, committed chest UID',uid,flush=True)
 # Victory commit itself saves the surface return state. Reload before collecting.
 print('Cold reload with chest',flush=True)
 continue_save();assert page.evaluate('!!game.defeated["12,-10"]')
 assert page.evaluate('game.p.durableChests.entries[0].items[0].weapon.wt')=='sewer_sai'
 enter();chamber();page.wait_for_function('game.world.conts.some(c=>c.durableId)')
 assert not page.evaluate('game.enemies.some(e=>e.boss==="sewer_raphael"&&!e.dead)')
 assert page.evaluate('game.p.durableChests.entries.length')==1
 print('Reentered; collecting',flush=True)
 page.evaluate('game.ui.openLoot(game.world.conts.find(c=>c.durableId))')
 expect(page.locator('#loot')).to_be_visible();page.locator('#lootAll').click()
 page.wait_for_function('game.p.weapons.some(w=>w.wt==="sewer_sai")')
 assert page.evaluate('game.p.durableChests.entries.length')==0
 assert page.evaluate('game.p.weapons.filter(w=>w.wt==="sewer_sai").map(w=>w.uid)')==[uid]
 print('Cold reload after collect',flush=True)
 continue_save()
 assert page.evaluate('game.p.weapons.filter(w=>w.wt==="sewer_sai").map(w=>w.uid)')==[uid]
 assert page.evaluate('game.p.durableChests.entries.length')==0
 assert page.evaluate('!!game.defeated["12,-10"]')
 page.wait_for_function('game.wGeoCache.sewer_sai?.attributes?.position?.count>0 && game.wMesh.geometry===game.wGeoCache.sewer_sai')
 page.screenshot(path=str(out/'held-sai-after-reload.png'))
 assert page.evaluate('TERRA_SEWER_BRIDGE.grades[game.p.weapons.find(w=>w.wt==="sewer_sai").g].lvl<=game.p.level')
 target=page.evaluate('''() => {
 let point;for(let i=0;i<12;i++){const a=i*Math.PI/6,x=game.p.x+Math.sin(a)*1.4,z=game.p.z+Math.cos(a)*1.4;if(game.world.free(x,z,.4)){point={x,z};break;}}
 if(!point)throw Error('No free melee fixture position');
 const enemy=game.spawnEnemy('zombie',point.x,point.z,{force:1,lvl:1});enemy.dmg=0;window.__saiTarget=enemy;
 const v=game.cam.position.clone().set(enemy.x,1,enemy.z).project(game.cam);
 return {x:(v.x*.5+.5)*innerWidth,y:(-v.y*.5+.5)*innerHeight};
 }''')
 page.mouse.move(target['x'],target['y']);page.mouse.down();page.wait_for_timeout(220);page.mouse.up()
 page.wait_for_function('__saiTarget.hp<__saiTarget.maxHp')
 assert not errors,errors
 print('PASS cold reload of reward-only weapon, no boss respawn, native loot UI transfer, second reload same one UID; JS errors 0',flush=True)
 b.close()
