"""Collector HUD regression with a disposable real game.

Tracks a surface story goal and, when offered, a native camp contract. Exercises
actual entry, both pumps and exit; detached UI fixtures cover boss/reward targets
without repeating the protected boss-kill/reload suite.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright, expect

expect.set_options(timeout=30000)
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-sewer-navigation-qa'))
out.mkdir(parents=True, exist_ok=True)

CHECK_TARGET = """({index, label}) => {
  const room=game.dg.ch.rooms[index], target={x:room.x+(index===6?0:4),z:room.z};
  const quest=JSON.stringify({story:game.story,data:game.storyData,contracts:game.p.camp.contracts.active});
  const story=game.storyTarget, contract=game.camp.contractTarget, terrain=window.TERRA_H;
  const ownStory=Object.getOwnPropertyDescriptor(game,'storyTarget');
  const ownContract=Object.getOwnPropertyDescriptor(game.camp,'contractTarget');
  const sameDescriptor=(a,b)=>a===undefined?b===undefined:!!b&&
    ['value','get','set','writable','enumerable','configurable'].every(key=>a[key]===b[key]);
  const height=terrain(target.x,target.z);
  game.ui.arrow();
  const expected=game.tmpV.clone().set(target.x,1,target.z).project(game.cam);
  const projectionError=game.tmpV.distanceTo(expected);
  const distance=Math.hypot(game.p.x-target.x,game.p.z-target.z), arrowDistance=game.ui.tgtD;
  const stars=[], context=game.ui.mm, draw=context.fillText;
  const ownDraw=Object.getOwnPropertyDescriptor(context,'fillText');
  try {
    context.fillText=function(text,x,y,...rest){if(text==='★')stars.push({x,y});return draw.call(this,text,x,y,...rest);};
    game.ui.minimap();
  } finally {if(ownDraw)Object.defineProperty(context,'fillText',ownDraw);else delete context.fillText;}
  let dx=(target.x-game.p.x)*1.2,dz=(target.z-game.p.z)*1.2,r=Math.hypot(dx,dz);
  if(r>66){dx=dx/r*66;dz=dz/r*66;}
  game.ui.hudT=0;game.ui.hud(0);
  return {
    height,projectionError,distance,arrowDistance,stars,expectedStar:{x:75+dx-6,y:75+dz+5},
    detail:document.getElementById('objD').textContent,
    expectedDetail:label+' · '+Math.round(distance)+' м',
    questUnchanged:quest===JSON.stringify({story:game.story,data:game.storyData,contracts:game.p.camp.contracts.active}),
    restored:game.storyTarget===story&&game.camp.contractTarget===contract&&window.TERRA_H===terrain&&
      sameDescriptor(ownStory,Object.getOwnPropertyDescriptor(game,'storyTarget'))&&
      sameDescriptor(ownContract,Object.getOwnPropertyDescriptor(game.camp,'contractTarget')),
  };
}"""

with sync_playwright() as p:
    browser = p.chromium.launch(
        executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome'),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width':390,'height':844}, has_touch=True, is_mobile=True)
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    page.goto(os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8080/play/'),timeout=90000)
    page.locator('#mNew').tap(); page.locator('#skip').tap()
    page.wait_for_function('game.sewers && game.state==="play"')
    baseline = page.evaluate("""() => {
      game.p.hp=game.p.maxHp=10000;
      game.story=7;game.storyData={prog:'3/5',moved:true};
      game.p.x=12;game.p.z=-10;game.camT=null;
      if(!game.p.camp.contracts.board.length)game.camp.refreshContracts();
      let selected=null;
      for(const type of ['bounty','rescue','clear']) {
        for(const offer of [...game.p.camp.contracts.board].filter(c=>c.type===type)) {
          if(!game.camp.takeContract(offer.id).ok)continue;
          selected=game.p.camp.contracts.active.find(c=>c.id===offer.id);break;
        }
        if(selected)break;
      }
      game.ui.objective();game.ui.hudT=0;game.ui.hud(0);
      window.__navigationBaseline={story:game.story,data:JSON.stringify(game.storyData),
        storyProvider:game.storyTarget,contractProvider:game.camp.contractTarget,
        contractId:selected?.id,contract:selected?JSON.stringify(selected):null};
      return {title:document.getElementById('objT').textContent,story:game.storyTarget(),
        contract:selected?{id:selected.id,type:selected.type,target:game.camp.contractTarget()}:null};
    }""")
    assert baseline['story']=={'x':121,'z':-67},baseline
    print('Native surface fixture:',baseline,flush=True)
    page.locator('#sewerAction').tap()
    page.wait_for_function('game.dg?.sewer && !game.dungeonTransition')

    def check_target(index, label):
        result = page.evaluate(CHECK_TARGET, {'index':index,'label':label})
        assert result['height']==0 and result['projectionError']<1e-9,result
        assert abs(result['arrowDistance']-result['distance'])<1e-9,result
        assert result['detail']==result['expectedDetail'],result
        assert len(result['stars'])==1,result
        assert all(abs(result['stars'][0][axis]-result['expectedStar'][axis])<1e-9 for axis in ['x','y']),result
        assert result['restored'],result
        assert result['questUnchanged'],result
        assert result['distance']<100,result

    check_target(1,'Насос 1')
    expect(page.locator('#objT')).to_have_text('Коллектор · насосы 0/2')
    page.locator('#objectiveToggle').tap()
    expect(page.locator('#objectiveDetailTitle')).to_have_text('Коллектор · насосы 0/2')
    page.screenshot(path=str(out/'pump-guidance-portrait.png'))
    page.keyboard.press('Escape')
    for index in [1,3]:
        page.evaluate('(i)=>{const r=game.dg.ch.rooms[i];game.p.x=r.x+4;game.p.z=r.z;game.camT=null}',index)
        expect(page.locator('#sewerAction')).to_have_text('Включить насос [E]')
        page.locator('#sewerAction').tap()
        page.wait_for_function('(i)=>game.sewers.pumps.includes(i)',arg=index)
        check_target(3 if index==1 else 6,'Насос 2' if index==1 else 'Нижняя камера')
    expect(page.locator('#objT')).to_have_text('Коллектор · нижняя камера')
    page.set_viewport_size({'width':844,'height':390})
    page.screenshot(path=str(out/'chamber-guidance-landscape.png'))

    # Presentation states only: no fake victory/receipt is written to the real
    # player. This also verifies scoped provider restoration on render failure.
    states = page.evaluate("""async () => {
      const {installSewerNavigation}=await import('./ui/sewer-navigation.js');
      const inherited=()=>({x:-123,z:-456}), contract=()=>({x:-100,z:-100});
      const fake=Object.assign(Object.create({storyTarget:inherited}),{
        p:{x:48008,z:48010},dg:{key:'12,-10',ch:{cx:1000,cz:1000,ents:[{kind:'exit',x:48008,z:48004}]}},
        camp:{contractTarget:contract},defeated:{},ui:{objective(){},hud(){},minimap(){},arrow(){
          if(throws)throw Error('navigation render fixture');return fake.storyTarget();
        }},
      });
      let throws=true,hunter=null;
      const receipt={domain:'dungeon',key:'12,-10',kind:'boss',x:54,z:58,items:[{id:'scrap',n:1}]};
      installSewerNavigation(fake,{active:()=>true,pumps:()=>new Set([1,3]),
        center:()=>({x:48056,z:48056}),boss:()=>hunter});
      try{fake.ui.arrow();}catch(error){if(error.message!=='navigation render fixture')throw error;}
      const restoredAfterThrow=!Object.hasOwn(fake,'storyTarget')&&fake.storyTarget===inherited&&fake.camp.contractTarget===contract;
      throws=false;hunter={x:48055,z:48059};const boss={...fake.ui.arrow()};
      hunter.x+=2;const movingBoss={...fake.ui.arrow()};
      fake.defeated['12,-10']=1;fake.p.durableChests={entries:[receipt]};const reward=fake.ui.arrow();
      fake.p.durableChests.entries=[];const exit=fake.ui.arrow();
      return {restoredAfterThrow,boss:{x:boss.x,z:boss.z},movingBoss:{x:movingBoss.x,z:movingBoss.z},reward,exit,
        restored:!Object.hasOwn(fake,'storyTarget')&&fake.camp.contractTarget===contract};
    }""")
    assert states['restoredAfterThrow'] and states['restored'],states
    assert states['boss']=={'x':48055,'z':48059},states
    assert states['movingBoss']=={'x':48057,'z':48059},states
    assert states['reward']=={'x':48054,'z':48058},states
    assert states['exit']=={'kind':'exit','x':48008,'z':48004},states
    page.evaluate('game.exitDungeon()')
    page.wait_for_function('!game.dg && !game.dungeonTransition')
    page.wait_for_function('!document.getElementById("objT").textContent.startsWith("Коллектор")')
    restored = page.evaluate("""() => {
      game.ui.hudT=0;game.ui.hud(0);
      const b=window.__navigationBaseline,goal=game.camp.contractTarget()||game.storyTarget();
      return {story:game.story===b.story&&JSON.stringify(game.storyData)===b.data,
        providers:game.storyTarget===b.storyProvider&&game.camp.contractTarget===b.contractProvider,
        contract:b.contractId?JSON.stringify(game.p.camp.contracts.active.find(c=>c.id===b.contractId))===b.contract:true,
        distance:game.ui.tgtD,expected:Math.hypot(game.p.x-goal.x,game.p.z-goal.z),
        detail:document.getElementById('objD').textContent};
    }""")
    assert restored['story'] and restored['providers'] and restored['contract'],restored
    assert abs(restored['distance']-restored['expected'])<1e-9,restored
    assert ('◎' in restored['detail']) if baseline['contract'] else ('3/5' in restored['detail']),restored
    assert not errors,errors
    print('PASS local pumps/chamber, native arrow floor/projection and minimap star, same-frame progress; moving boss/reward/exit UI states and throw recovery; native story/contract restored, JS errors 0',flush=True)
    browser.close()
