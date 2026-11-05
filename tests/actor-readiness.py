"""Delay a real unrelated model while testing the first playable hero frame.

The controlled route simulates a slow trader GLB, then completes or fails it.
Disabling only the optional readiness helper reproduces the former behavior.
"""
import base64
import gzip
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-actor-ready-qa'));out.mkdir(exist_ok=True)
assets=json.loads(gzip.decompress((root/'play/assets/pack/TERRA_ASSETS.json.gz').read_bytes()))
source=assets['s_trader'];trader=base64.b64decode(source[3:] if source.startswith('gz:') else source)
if source.startswith('gz:'):trader=gzip.decompress(trader)
assert trader[:4]==b'glTF'
reports=[]
with sync_playwright() as p:
 for name,enabled,fail in [('before',False,False),('after',True,False),('failed-late-model',True,True)]:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(90000)
  pending=[];errors=[];warnings=[]
  page.route('**/qa/slow-trader.glb',lambda route:pending.append(route))
  page.on('pageerror',lambda e:errors.append(str(e)))
  def console(message):
   expected=fail and 'ERR_FAILED' in message.text and message.location.get('url','').endswith('/qa/slow-trader.glb')
   if message.type=='error' and not expected:errors.append(message.text[:1200])
   if message.type=='warning':warnings.append(message.text[:300])
  page.on('console',console)
  page.add_init_script('''localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}));
   let assets;Object.defineProperty(window,'TERRA_ASSETS',{configurable:true,enumerable:true,
    get(){return assets},set(v){assets=v;v.s_trader='url:'+location.origin+'/qa/slow-trader.glb'}});''')
  page.goto(url,timeout=120000)
  page.wait_for_function('TERRA_BOOT_STATE.status==="ready" && game.sewers && !!game.glb.s_farmer && !game.glb.s_trader')
  if not pending:page.wait_for_timeout(200)
  assert len(pending)==1,'Late-model fixture was not requested'
  assert page.evaluate('!game.heroInst && !!game.glb.hero && !game.g07Assets')
  if not enabled:page.evaluate('delete TERRA_ART.readyHero')
  page.evaluate('''()=>{
   window.__qaPoses={play:0,first:null};window.__qaRefreshes=[];
   const pose=game.heroPose,refresh=game.refreshModelMode;
   game.refreshModelMode=function(...args){const before=!!this.heroInst,result=refresh.apply(this,args);
    __qaRefreshes.push({created:!before&&!!this.heroInst,full:!!this.g07Assets,heroOnly:args[0]===true});return result};
   game.heroPose=function(...args){const result=pose.apply(this,args);if(this.state==='play'){
    __qaPoses.play++;__qaPoses.first??={pool:!!this.glb.hero,inst:!!this.heroInst,late:!!this.glb.s_trader};
   }return result};
  }''')
  page.locator('#mNew').click();page.wait_for_function('game.state==="intro"')
  intro=page.evaluate('game.heroPose(0);({state:game.state,inst:!!game.heroInst})')
  assert not intro['inst'],'Ready helper published the hero during the intro'
  page.locator('#skip').click();page.wait_for_function('__qaPoses.play>=3')
  first=page.evaluate('''()=>{
   let meshes=0;game.heroInst?.root.traverse(o=>{if(o.isSkinnedMesh)meshes++});
   return {pose:__qaPoses.first,pool:!!game.glb.hero,inst:!!game.heroInst,
    visible:!!game.heroInst?.root.visible,meshes,late:!!game.glb.s_trader,
    rigParts:game.heroRig.parts.filter(p=>p.im.visible&&p.im.count>0).length,
    full:!!game.g07Assets,uuid:game.heroInst?.root.uuid||null};
  }''')
  assert first['pool'] and not first['late'] and not first['full'],first
  if enabled:
   assert first['pose']['inst'] and first['inst'] and first['visible'] and first['meshes']>0,first
   hidden=page.evaluate('''()=>{game.heroInst.root.visible=false;game.heroPose(0);
    const kept=!game.heroInst.root.visible;game.heroInst.root.visible=true;return kept}''')
   assert hidden,'Existing cinematic visibility was overwritten'
   scope=page.evaluate('''()=>{
    const pool=game.glb.s_engineer,instance=pool.make(),enemy={base:'__qa_unready_base__',mdl:'s_engineer',inst:instance};
    const original=game.enemies;game.enemies=[enemy];let kept=false;
    try{game.refreshModelMode(true);kept=enemy.inst===instance}
    finally{game.enemies=original;if(enemy.inst===instance)pool.release(instance)}
    return kept&&__qaRefreshes.some(r=>r.created&&r.heroOnly);
   }''')
   assert scope,'Hero publication touched an unrelated native model instance'
  else:assert not first['pose']['inst'] and not first['inst'],first
  page.screenshot(path=str(out/(name+'-early.png')))
  session=None
  if enabled:
   origin=page.evaluate('game.p.x');page.keyboard.down('KeyD')
   page.wait_for_function('(x)=>Math.abs(game.p.x-x)>.12',arg=origin);page.keyboard.up('KeyD')
   page.evaluate('''()=>{const weapon=game.makeWeapon('katana',0,0,null);game.p.weapons.push(weapon);
    game.p.eq[game.p.slot]=weapon;window.__qaWeaponUid=weapon.uid}''')
   page.wait_for_function('game.wMesh.visible && game.wMesh.matrix.elements.every(Number.isFinite)')
   session=page.evaluate('''()=>{const before=game.p,uuid=game.heroInst.root.uuid,x=game.p.x;
    const saved=game.save();if(!saved?.ok)throw Error('Readiness fixture save failed');
    game.p.x+=3;const loaded=game.continueGame();
    return {saved:!!saved.ok,loaded:!!loaded?.ok,newPlayer:game.p!==before,x,uuid,
      restored:game.p.weapons.some(w=>w.uid===__qaWeaponUid&&w.wt==='katana')};}''')
   assert session['saved'] and session['loaded'] and session['newPlayer'] and session['restored'],session
   page.wait_for_function('(v)=>game.state==="play" && Math.abs(game.p.x-v.x)<.03 && Math.abs(game.heroInst.root.position.x-game.p.x)<.03',arg=session)
   assert page.evaluate('game.heroInst.root.uuid')==first['uuid'],'Continue duplicated the hero'
  if fail:pending[0].abort('failed')
  else:pending[0].fulfill(body=trader,content_type='model/gltf-binary')
  page.wait_for_function('__qaRefreshes.some(r=>r.full)')
  final=page.evaluate('''()=>({uuid:game.heroInst.root.uuid,visible:game.heroInst.root.visible,
   roots:game.scene.children.filter(o=>o===game.heroInst.root).length,
   published:__qaRefreshes.filter(r=>r.created).length,late:!!game.glb.s_trader,
   finite:game.heroInst.root.matrix.elements.every(Number.isFinite),time:game.heroInst.mixer.time})''')
  if enabled:assert final['uuid']==first['uuid'],final
  assert final['visible'] and final['roots']==1 and final['published']==1 and final['finite'] and final['time']>0,final
  assert final['late']!=fail,final
  assert not errors,errors
  report={'case':name,'intro':intro,'first':first,'session':session,'final':final,'errors':errors,'warnings':warnings}
  reports.append(report);(out/(name+'.json')).write_text(json.dumps(report,indent=2))
  print(name,'first',first,'final',final,'JS0',flush=True);browser.close()
print('PASS hero before unrelated models; intro/hidden visibility, movement/weapon, save/continue, late completion/failure, one native instance')
