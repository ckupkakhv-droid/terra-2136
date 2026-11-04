"""Transition/pump/map integration test. Teleports a disposable test character;
not a combat playthrough or a physical-phone test.
"""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, expect
# Native software rendering can exceed 5 s when CI shares the CPU. Keep the
# assertion budget consistent with the existing 30 s integration waits.
expect.set_options(timeout=30000)
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-sewer-qa'));out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome'),args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1280,'height':800},has_touch=True);page.set_default_timeout(30000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' and 'favicon' not in m.location.get('url','') else None)
 page.goto(os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8080/play/'),timeout=90000)
 page.locator('#mNew').tap();page.locator('#skip').tap();page.wait_for_function('window.game.sewers')
 assert page.evaluate("(()=>{const c=new window.TERRA_SEWER_BRIDGE.Chunk(1000,1000);c.dungeon('metro','qa-original');return c.rooms.length===16})()"), 'Ordinary metro generator changed'
 assert page.evaluate('game.world.free(12,-10,.4)'), 'Entrance is blocked on the surface'
 page.evaluate('game.p.x=12;game.p.z=-10;game.p.hp=game.p.maxHp=10000')
 page.locator('#sewerAction').tap();page.wait_for_function('!!game.dg && !game.dungeonTransition')
 assert page.evaluate('game.dg.sewer && game.world.inDungeon && game.dg.ch.rooms.length===7')
 # Every pair of consecutive rooms has an unblocked center path.
 assert page.evaluate('''() => {
 const r=game.dg.ch.rooms;
 for(let k=1;k<r.length;k++)for(let n=1;n<32;n++) {
 const x=r[k-1].x+(r[k].x-r[k-1].x)*n/32,z=r[k-1].z+(r[k].z-r[k-1].z)*n/32;
 if(game.world.collide({x,z},.3))return false;
 }return true;}''')
 print('Entered and corridors checked',flush=True)
 page.wait_for_function('game.dg.flood===true')
 page.screenshot(path=str(out/'tunnel.png'))
 def pumps_on():
  for index in [1,3]:
   page.evaluate('(i)=>{const r=game.dg.ch.rooms[i];game.p.x=r.x+4;game.p.z=r.z}',index)
   expect(page.locator('#sewerAction')).to_have_text('Включить насос [E]')
   page.locator('#sewerAction').tap()
   page.wait_for_function('(i)=>game.sewers.pumps.includes(i)',arg=index)
   page.wait_for_function('game.dg.flood===false')
   page.evaluate('(i)=>{const r=game.dg.ch.rooms[i];game.p.x=r.x;game.p.z=r.z}',index)
   page.wait_for_function('game.dg.flood==='+('true' if index==1 else 'false'))
 pumps_on()
 page.wait_for_function('game.dg.flood===false');print('Pumps drained',flush=True)
 page.emulate_media(reduced_motion='reduce');page.keyboard.down('w')
 page.evaluate('const r=game.dg.ch.rooms[6];game.p.x=r.x;game.p.z=r.z;game.camT=null')
 expect(page.locator('#sewerRecording')).to_be_visible();assert page.evaluate('game.state')=='modal'
 assert page.evaluate('!game.keys.has("KeyW") && !game.stL.on && !game.stR.on')
 page.keyboard.press('m');page.keyboard.press('m');page.keyboard.press('i');page.keyboard.press('l')
 expect(page.locator('#wmap')).not_to_be_visible();expect(page.locator('#sewerRecording')).to_be_visible()
 page.locator('#recordingNext').click();expect(page.locator('#recordingText')).to_contain_text('Рафаэль')
 page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(out/'recording.png'))
 page.keyboard.press('Escape');expect(page.locator('#sewerRecording')).to_have_count(0);assert page.evaluate('game.state')=='play'
 page.keyboard.up('w')
 page.evaluate('game.ui.openMap()');page.locator('#sewerLayerButton').tap()
 expect(page.locator('#sewerMap')).to_be_visible();expect(page.locator('.sewerCell')).to_have_count(7)
 assert not page.locator('#sewerMap').evaluate('(e)=>e.inert')
 expect(page.locator('.sewerPipe')).to_have_count(6);expect(page.locator('.sewerPlayer')).to_have_count(1)
 page.keyboard.press('Tab');assert page.locator('#sewerMap').evaluate('(e)=>e.contains(document.activeElement)')
 page.locator('#sewerMap summary').first.click();expect(page.locator('#sewerMap details').first).to_have_attribute('open','')
 page.locator('#sewerMap .x').tap();expect(page.locator('#sewerMap')).not_to_be_visible()
 assert not page.locator('#wmBody').evaluate('(e)=>e.inert')
 page.locator('#sewerLayerButton').tap()
 for name,w,h in [('portrait',390,844),('landscape',844,390)]:
  page.set_viewport_size({'width':w,'height':h});page.screenshot(path=str(out/(name+'.png')))
  assert page.locator('#sewerMap .win').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
 page.locator('#sewerMap .x').press('Escape');expect(page.locator('#sewerMap')).not_to_be_visible()
 page.keyboard.press('Escape');assert page.evaluate('game.state')=='play';page.evaluate('game.exitDungeon()');page.wait_for_function('!game.dg && !game.dungeonTransition')
 assert page.evaluate('!game.world.inDungeon && Math.hypot(game.p.x-12,game.p.z+7)<.1')
 print('Exited',flush=True)
 page.evaluate('game.save()');page.reload();page.locator('#mContinue').click();page.wait_for_function('game.state==="play"');page.wait_for_function('window.game.sewers')
 assert page.evaluate('!game.world.inDungeon')
 page.evaluate('game.p.x=12;game.p.z=-10');page.locator('#sewerAction').tap();page.wait_for_function('!!game.dg && !game.dungeonTransition');page.wait_for_function('game.sewers.pumps.length===0')
 pumps_on()
 page.evaluate('const r=game.dg.ch.rooms[6];game.p.x=r.x;game.p.z=r.z;game.camT=null')
 expect(page.locator('#sewerRecording')).to_be_visible()
 for _ in range(3):page.locator('#recordingNext').click()
 expect(page.locator('#sewerRecording')).to_have_count(0);assert page.evaluate('game.state')=='play'
 page.evaluate('game.exitDungeon()');page.wait_for_function('!game.dg && !game.dungeonTransition')
 assert not errors,errors
 print('PASS: native entry/exit, seven connected sectors, two pumps/drainage, map in two orientations, save/reload and re-entry reset; recording skip/completion/input release in reduced-motion; no JS/transition errors')
 b.close()
