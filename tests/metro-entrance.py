"""Real station architecture and native travel transition on a disposable profile."""
import os
from pathlib import Path
from playwright.sync_api import sync_playwright
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-metro-qa'));out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1280,'height':800},has_touch=True);page.set_default_timeout(60000)
 errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:print('BROWSER',m.text[:500],flush=True) if m.type=='error' and 'favicon' not in m.text else None)
 page.goto(os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8117/play/'),timeout=120000)
 page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.sewers && game.state==="play"')
 # Local generator invariants include native collision and fast-travel ids.
 invariant=page.evaluate('''()=>{const c=new TERRA_SEWER_BRIDGE.Chunk(5,6);c.metro(260,300,'metro','Тест');
   return {entry:c.ents[0],tp:c.tps[0],cols:c.cols,kitTriangles:c.kb?.bld?.[0]?.i?.length||0,next:[c.r(),c.r(),c.r(),c.r()]};}''')
 assert invariant['entry']=={'x':260,'z':301.5,'kind':'metro','name':'Тест'},invariant
 assert invariant['tp']['id']=='m5_6' and invariant['tp']['z']==305.5 and len(invariant['cols'])==3,invariant
 # The surface kit must not advance the seeded stream or leave partially
 # inserted geometry if a placement fails halfway through.
 assert invariant['next']==[0.8220946618821472,0.7601078576408327,0.7970146320294589,0.38742400682531297],invariant
 assert invariant['kitTriangles']>0,invariant
 fallback=page.evaluate('''()=>{const c=new TERRA_SEWER_BRIDGE.Chunk(5,6), make=()=>({p:[1],n:[2],uv:[3],c:[4],i:[5]});
   c.kb={bld:[make(),make(),make()]};let calls=0;
   c.kp_=function(){for(const k of ['p','n','uv','c','i'])this.kb.bld[0][k].push(99);if(++calls===2)throw Error('simulated failure');return {}};
   c.metro(260,300,'metro','Тест');return {lengths:['p','n','uv','c','i'].map(k=>c.kb.bld[0][k].length),surface:c.s.p.length,calls};}''')
 assert fallback['lengths']==[1,1,1,1,1] and fallback['surface']>0 and fallback['calls']==2,fallback
 page.wait_for_function("game.world.ents.some(e=>e.kind==='metro'&&!e.sewer)",timeout=90000)
 entry=page.evaluate("game.world.ents.find(e=>e.kind==='metro'&&!e.sewer)")
 page.evaluate('e=>{game.p.x=e.x;game.p.z=e.z+2;game.camT=null;game.p.hp=game.p.maxHp=10000}',entry)
 page.wait_for_timeout(800);page.screenshot(path=str(out/'metro-desktop.png'))
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500);page.screenshot(path=str(out/'metro-portrait.png'))
 result=page.evaluate('''e=>{
  const post=game.post, old=post.render;window.__oldMetroRender=old;window.__nativeCamera=game.cam;
  window.__meterRender=function(scene,camera,...rest){if(camera!==window.__nativeCamera)window.__metroTemporaryRendered=true;};
  post.render=window.__meterRender;
  const key=Math.round(e.x)+','+Math.round(e.z);
  const descriptor={theme:'metro',seed:key,key,idx:game.dgIdx?.[key]||0,tier:1,from:{x:e.x,z:e.z+3},name:e.name};
  const ok=game.runDungeonTransition(descriptor,false);
  if(post.render!==window.__meterRender) post.render(game.scene,game.cam,0);
  return {ok,overlay:!!document.querySelector('.metroTransition'),wrapped:post.render!==window.__meterRender,originalCamera:game.cam===window.__nativeCamera,key};
 }''',entry)
 print('Transition started',flush=True)
 assert {k:result[k] for k in ('ok','overlay','wrapped','originalCamera')}=={'ok':True,'overlay':True,'wrapped':True,'originalCamera':True},result
 page.wait_for_function('key=>game.dg?.key===key && !game.dungeonTransition',arg=result['key'],timeout=90000)
 page.wait_for_function('!document.querySelector(".metroTransition") && game.post.render===window.__meterRender')
 assert page.evaluate('game.cam===window.__nativeCamera && !!game.world.inDungeon')
 assert page.evaluate('!!window.__metroTemporaryRendered'), 'Render did not use the temporary camera'
 print('Entered metro and camera restored',flush=True)
 ex=page.evaluate('''()=>{game.post.render=window.__oldMetroRender;const ok=game.exitDungeon();return {ok,state:game.state,alive:game.p.alive,transition:!!game.dungeonTransition};}''');print('Exit requested',ex,flush=True);assert ex['ok'] is True,ex;page.wait_for_function('!game.dg && !game.dungeonTransition')
 # Cancel immediately in reduced-motion mode; no camera swap or stuck overlay.
 page.emulate_media(reduced_motion='reduce')
 reduced=page.evaluate("""()=>{const old=game.post.render,p=game.p;
  const ok=game.runDungeonTransition({theme:'metro',seed:'qa-cancel',key:'qa-cancel',idx:0,tier:1,from:{x:p.x,z:p.z},name:'Тест'},false);
  const unchanged=game.post.render===old;game.cancelDungeonTransition();return {ok,unchanged};}""")
 assert reduced=={'ok':True,'unchanged':True},reduced
 page.wait_for_function('!document.querySelector(".metroTransition") && !game.dungeonTransition')
 page.emulate_media(reduced_motion='no-preference')
 # Existing collector enters without an ordinary-metro cinematic overlay.
 page.evaluate('game.p.x=12;game.p.z=-10;game.camT=null');page.locator('#sewerAction').click()
 page.wait_for_function('game.dg?.sewer && !game.dungeonTransition',timeout=90000)
 assert page.locator('.metroTransition').count()==0
 assert not errors,errors
 print('PASS surface station, identity/collision, temporary camera, transition cleanup and collector compatibility; JS0',flush=True)
 b.close()
