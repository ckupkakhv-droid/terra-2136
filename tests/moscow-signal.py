"""Actual radio-site clue with a disposable profile and progress fixtures."""
import os, shutil
from pathlib import Path
from playwright.sync_api import sync_playwright, expect

expect.set_options(timeout=30000)
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-moscow-signal-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium'),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':390,'height':844}, is_mobile=True, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), timeout=90000)
    page.locator('#mNew').tap(); page.locator('#skip').tap()
    page.wait_for_function('game.sewers && game.state === "play"')
    page.evaluate('game.p.x=23.5;game.p.z=124;game.camT=null')
    page.wait_for_function('TerraWorldSites.placements.some(p=>p.id==="signal")', timeout=90000)
    site = page.evaluate('''() => {
      const c=game.world.conts.find(c=>TerraWorldSites.placementForContainer(game,c)?.id==='signal');
      if (!c) throw Error('Radio site container is not loaded');
      for(let r=.6;r<2.2;r+=.2) for(let a=0;a<Math.PI*2;a+=Math.PI/12) {
        const x=c.x+Math.cos(a)*r,z=c.z+Math.sin(a)*r;
        if(!game.world.collide({x,z},.3) && game.world.segHit(x,z,c.x,c.z,1.1)<0) {
          game.p.x=x;game.p.z=z;game.camT=null;return {x:c.x,z:c.z};
        }
      }
      throw Error('No reachable radio site approach');
    }''')
    assert site
    expect(page.locator('#moscowSignalAction')).to_be_hidden()
    page.evaluate('''() => { window.signalToasts=[]; const toast=game.ui.toast;
      game.ui.toast=function(text,...args){if(text.includes('Московский перехват'))signalToasts.push(text);return toast.call(this,text,...args);}; }''')
    page.evaluate('game.defeated["12,-10"]=1')
    expect(page.locator('#moscowSignalAction')).to_be_hidden()
    page.evaluate('game.p.routeTransit={v:1,stage:2}')
    expect(page.locator('#moscowSignalAction')).to_be_visible()
    page.wait_for_function('signalToasts.length === 1')
    before = page.evaluate('''() => JSON.stringify({defeated:game.defeated,
      transit:game.p.routeTransit,inv:game.p.inv,weapons:game.p.weapons,chests:game.p.durableChests})''')
    page.locator('#moscowSignalAction').tap()
    expect(page.locator('#recordingTitle')).to_have_text('РУЧНАЯ ЛЕНТА')
    page.locator('#recordingNext').tap()
    expect(page.locator('#recordingText')).to_contain_text('Московский контур')
    page.screenshot(path=str(out/'signal-portrait.png'))
    page.locator('#recordingSkip').tap()
    expect(page.locator('#moscowSignalAction')).to_be_hidden()
    assert page.evaluate('document.activeElement.id') == 'c'
    page.wait_for_function('game.enemies.some(e=>e.moscowScout) && game.world.scene.getObjectByName("moscowScoutVisual")', timeout=90000)
    page.screenshot(path=str(out/'scout-portrait.png'))
    print('Scout projection:', page.evaluate('''() => {
      const v=game.world.scene.getObjectByName('moscowScoutVisual').position.clone().project(game.cam);
      const x=(v.x+1)*innerWidth/2,y=(1-v.y)*innerHeight/2;
      return {x,y,onScreen:x>=0&&x<innerWidth&&y>=0&&y<innerHeight,top:document.elementFromPoint(x,y)?.id};
    }'''), flush=True)
    page.set_viewport_size({'width':844,'height':390})
    page.wait_for_function('Math.abs(game.cam.aspect - 844/390) < .01')
    assert page.evaluate('''() => {
      const v=game.world.scene.getObjectByName('moscowScoutVisual').position.clone().project(game.cam);
      return Math.abs(v.x)<1 && Math.abs(v.y)<1;
    }''')
    page.screenshot(path=str(out/'scout-landscape.png'))
    page.set_viewport_size({'width':390,'height':844})
    page.wait_for_function('Math.abs(game.cam.aspect - 390/844) < .01')
    assert page.evaluate('''() => {
      const ally=game.droneM[0].getObjectByName('drone_body_LOD0');
      const scout=game.world.scene.getObjectByName('moscowScoutVisual').getObjectByName('drone_body_LOD0');
      return !!ally && !!scout && ally !== scout && ally.material !== scout.material && ally.geometry === scout.geometry;
    }''')
    assert page.evaluate('''() => {
      const ally=game.droneM[0].getObjectByName('rotor_BL');
      const rotor=game.world.scene.getObjectByName('moscowScoutVisual').getObjectByName('rotor_BL');
      const a=ally.rotation.y, r=rotor.rotation.y;game.enemyUpdate(.1);
      return rotor.rotation.y!==r && ally.rotation.y===a;
    }''')
    assert page.evaluate('''() => {
      const old=game.p;game.p={...old};game.enemyUpdate(.1);game.p=old;
      return !game.enemies.some(e=>e.moscowScout) && !game.world.scene.getObjectByName('moscowScoutVisual');
    }''')
    expect(page.locator('#moscowSignalAction')).to_be_visible()
    page.locator('#moscowSignalAction').tap()
    page.keyboard.press('Escape')
    page.wait_for_function('game.enemies.some(e=>e.moscowScout)', timeout=90000)
    assert page.evaluate('''() => {
      const p=game.p,x=p.x; p.x+=60; game.enemyUpdate(.1); p.x=x;
      return !game.enemies.some(e=>e.moscowScout) && !game.world.scene.getObjectByName('moscowScoutVisual');
    }''')
    expect(page.locator('#moscowSignalAction')).to_be_visible()
    page.locator('#moscowSignalAction').tap()
    expect(page.locator('#recordingTitle')).to_have_text('РУЧНАЯ ЛЕНТА')
    page.keyboard.press('Escape')
    expect(page.locator('#sewerRecording')).to_have_count(0)
    page.wait_for_function('game.enemies.some(e=>e.moscowScout)', timeout=90000)
    after = page.evaluate('''() => JSON.stringify({defeated:game.defeated,
      transit:game.p.routeTransit,inv:game.p.inv,weapons:game.p.weapons,chests:game.p.durableChests})''')
    assert before == after
    assert page.evaluate('signalToasts.length') == 1
    assert page.evaluate('game.enemies.filter(e=>e.moscowScout).length') == 1
    result = page.evaluate('''() => {
      for(let i=game.enemies.length-1;i>=0;i--)if(!game.enemies[i].moscowScout)game.removeEnemy(i);
      const drone=game.enemies.find(e=>e.moscowScout), ring=game.ring, beam=game.beam, hurt=game.hurtPlayer;
      const xp=game.p.xp, level=game.p.level, kills=game.p.kills;
      const start={x:game.p.x,z:game.p.z};let warnings=0, shots=0, attacks=0, dodge=true;
      let melee=false, spot=null;
      for(let a=0;a<Math.PI*2;a+=Math.PI/8){
        const x=drone.x+Math.sin(a)*.9,z=drone.z+Math.cos(a)*.9;
        if(game.world.free(x,z,.42)){spot={x,z};break;}
      }
      if(!spot)throw Error('No free melee position beside scout');
      game.p.x=spot.x;game.p.z=spot.z;game.p.yaw=Math.atan2(drone.x-spot.x,drone.z-spot.z);
      game.p.atkCd=0;game.p.stun=0;game.p.mv=null;
      const oldHp=drone.hp;game.attack('light');for(let i=0;i<10;i++)game.meleeUpdate(.1);
      melee=drone.hp<oldHp;game.p.x=start.x;game.p.z=start.z;game.cancelMelee();
      game.ring=function(...args){warnings++;if(dodge){game.p.x+=4;dodge=false;}return ring.apply(this,args);};
      game.beam=function(...args){shots++;return beam.apply(this,args);};
      game.hurtPlayer=function(d,e,...args){if(e===drone)attacks++;return hurt.call(this,d,e,...args);};
      let dodged=0;
      try {
        for(let i=0;i<60;i++)game.enemyUpdate(.1);
        dodged=attacks;game.p.x=start.x;game.p.z=start.z;
        for(let i=0;i<160;i++)game.enemyUpdate(.1);
      }
      finally { game.ring=ring;game.beam=beam;game.hurtPlayer=hurt; }
      const hp=drone.hp;game.hurtEnemy(drone,10,{});const damaged=drone.hp<hp;
      game.hurtEnemy(drone,10000,{});game.enemyUpdate(.01);
      return {melee,warnings,shots,attacks,dodged,damaged,noReward:game.p.xp===xp&&game.p.level===level&&game.p.kills===kills,
        removed:!game.enemies.includes(drone)&&!game.world.scene.getObjectByName('moscowScoutVisual')};
    }''')
    assert result['melee'] and result['warnings'] >= 1 and result['shots'] >= 1 and result['attacks'] >= 1 and result['dodged'] == 0 and result['damaged'] and result['removed'] and result['noReward'], result
    expect(page.locator('#moscowSignalAction')).to_be_visible()
    page.locator('#moscowSignalAction').tap()
    page.keyboard.press('Escape')
    assert not page.evaluate('game.enemies.some(e=>e.moscowScout)')
    page.evaluate('game.ui.openMap()')
    page.locator('#sewerLayerButton').tap()
    expect(page.locator('#moscowRoute')).to_contain_text('Московский перехват')
    page.locator('#moscowRoute summary').tap()
    expect(page.locator('#moscowRoute')).to_contain_text('Радиопост Ноль')
    page.set_viewport_size({'width':844,'height':390})
    assert page.locator('#sewerMap .win').evaluate('(e)=>e.scrollWidth<=e.clientWidth+1')
    page.screenshot(path=str(out/'journal-landscape.png'))
    assert not errors, errors
    print('PASS: radio-site clue, independent scout, native melee, attack warning/dodge, death and distance cleanup, unchanged progress and map journal; no JS errors')
    browser.close()
