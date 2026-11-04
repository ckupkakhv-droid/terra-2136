"""Lab runtime integration: native collision, asset sharing and expedition cleanup."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-lab-qa'));out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(60000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto(os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8110/play/'),timeout=120000)
 page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.sewers && game.glb.sewer_lab')
 def enter():
  page.evaluate('game.p.x=12;game.p.z=-10;game.camT=null')
  page.locator('#sewerAction').click();page.wait_for_function('game.dg?.sewer && !game.dungeonTransition')
  page.evaluate('const r=game.dg.ch.rooms[2];game.p.x=r.x;game.p.z=r.z;game.camT=null')
  page.wait_for_function('game.world.scene.getObjectByName("sewerLab")?.visible')
 enter()
 audit=page.evaluate('''()=>{
  const g=game.world.scene.getObjectByName('sewerLab'),r=game.dg.ch.rooms[2],meshes=[];
  window.labFirst=g;g.traverse(n=>{if(n.isMesh)meshes.push(n)});
  const free=(dx,dz)=>{const p={x:r.x+dx,z:r.z+dz};game.world.collide(p,.3);return Math.hypot(p.x-r.x-dx,p.z-r.z-dz)<.01};
  return {lights:g.children.filter(n=>n.isLight).length,shadow:g.children.some(n=>n.isLight&&n.castShadow),
   meshes:meshes.length,culled:meshes.every(n=>n.frustumCulled),source:!!game.glb.sewer_lab.src.getObjectByName('vat'),
   vatBlocked:!free(6,-5),north:free(0,-7),east:free(7,0),center:free(0,0)};
 }''')
 assert audit['lights']==2 and not audit['shadow'] and audit['meshes']>0 and audit['culled'] and audit['source'],audit
 assert audit['vatBlocked'] and audit['north'] and audit['east'] and audit['center'],audit
 page.wait_for_timeout(700);page.screenshot(path=str(out/'lab-desktop.png'))
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(700);page.screenshot(path=str(out/'lab-portrait.png'))
 page.evaluate('const r=game.dg.ch.rooms[6];game.p.x=r.x;game.p.z=r.z')
 page.wait_for_function('!labFirst.visible && labFirst.children.filter(n=>n.isLight).every(n=>!n.visible)')
 page.evaluate('game.exitDungeon()');page.wait_for_function('!game.dg && !game.dungeonTransition && !labFirst.parent')
 enter();assert page.evaluate('game.world.scene.children.filter(n=>n.name==="sewerLab").length===1 && game.world.scene.getObjectByName("sewerLab")!==labFirst')
 assert not errors,errors
 print('PASS lab kit, two unshadowed lights, collider/connected paths, desktop/portrait, distance culling, exit/reentry cleanup, JS0',audit)
 b.close()
