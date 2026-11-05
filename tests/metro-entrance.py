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
   const positions=(c.kb?.bld||[]).flatMap(b=>b.p),normals=(c.kb?.bld||[]).flatMap(b=>b.n);
   const deltas=[],zs=[];for(let i=0;i<positions.length;i+=3){deltas.push(positions[i+1]-c.hAt(positions[i],positions[i+2]));zs.push(positions[i+2])}
   const lengths=[];for(let i=0;i<normals.length;i+=3)lengths.push(Math.hypot(...normals.slice(i,i+3)));
   return {entry:c.ents[0],tp:c.tps[0],cols:c.cols,kitTriangles:c.kb?.bld?.[0]?.i?.length||0,next:[c.r(),c.r(),c.r(),c.r()],
     paving:{zMin:Math.min(...zs),zMax:Math.max(...zs),low:Math.min(...deltas),high:Math.max(...deltas),normals:lengths.every(n=>Math.abs(n-1)<1e-5)}};}''')
 assert invariant['entry']=={'x':260,'z':301.5,'kind':'metro','name':'Тест'},invariant
 assert invariant['tp']['id']=='m5_6' and invariant['tp']['z']==305.5 and len(invariant['cols'])==3,invariant
 # The surface kit must not advance the seeded stream or leave partially
 # inserted geometry if a placement fails halfway through.
 assert invariant['next']==[0.8220946618821472,0.7601078576408327,0.7970146320294589,0.38742400682531297],invariant
 assert invariant['kitTriangles']>0,invariant
 assert invariant['paving']['zMin']>303.49 and invariant['paving']['zMax']<306.31,invariant
 assert abs(invariant['paving']['high']-.025)<1e-6 and invariant['paving']['low']<=.0250001 and invariant['paving']['normals'],invariant
 fallback=page.evaluate('''()=>{const c=new TERRA_SEWER_BRIDGE.Chunk(5,6), make=()=>({p:[0,0,0],n:[0,1,0],uv:[0,0],c:[1,1,1],i:[0]});
   c.kb={bld:[make(),make(),make()]};let calls=0;
   c.kp_=function(){const b=this.kb.bld[0];b.p.push(0,0,0);b.n.push(0,1,0);b.uv.push(0,0);b.c.push(1,1,1);b.i.push(1);if(++calls===2)throw Error('simulated failure');return {}};
   c.metro(260,300,'metro','Тест');return {lengths:['p','n','uv','c','i'].map(k=>c.kb.bld[0][k].length),surface:c.s.p.length,calls};}''')
 assert fallback['lengths']==[3,3,2,3,1] and fallback['surface']>0 and fallback['calls']==2,fallback
 obstacle=page.evaluate('''()=>{const c=new TERRA_SEWER_BRIDGE.Chunk(5,6);let calls=0;
   c.col(257,303.5,260,306.5,1);c.kp_=()=>{calls++;throw Error('unexpected paving')};c.metro(260,300,'metro','Тест');
   return {calls,kit:!!c.kb,cols:c.cols.length,surface:c.s.p.every(Number.isFinite)};}''')
 assert obstacle=={'calls':0,'kit':False,'cols':4,'surface':True},obstacle
 # Force a one-metre gap under a level station: its foundation must reach the
 # soil while leaving the walking deck and the three native colliders intact.
 skirt=page.evaluate('''()=>{const c=new TERRA_SEWER_BRIDGE.Chunk(5,6);
   c.s.oy=c.g.oy=c.n.oy=1;c.hAt=()=>0;c.metro(260,300,'metro','Тест');
   const ys=c.s.p.slice(0,162).filter((v,i)=>i%3===1);
   return {bottom:Math.min(...ys),top:Math.max(...ys),finite:c.s.p.every(Number.isFinite),cols:c.cols.length};}''')
 assert skirt['bottom']<0 and abs(skirt['top']-1.12)<1e-6 and skirt['finite'] and skirt['cols']==3,skirt
 page.wait_for_function("game.world.ents.some(e=>e.kind==='metro'&&!e.sewer)",timeout=90000)
 entry=page.evaluate("game.world.ents.find(e=>e.kind==='metro'&&!e.sewer)")
 page.evaluate('e=>{game.p.x=e.x;game.p.z=e.z+2;game.camT=null;game.p.hp=game.p.maxHp=10000}',entry)
 page.wait_for_function("game.scene.children.some(o=>o.userData.terraMetroMarkers && o.count>0)")
 # The ordinary station replaces just its own native marker and shares the
 # existing ring resources; the collector and resource markers stay intact.
 marker=page.evaluate("""e=>{
  const g=game, batch=g.scene.children.find(o=>o.userData.terraMetroMarkers);
  const matrix=new g.cam.matrix.constructor(),scale=i=>{g.markers.im.getMatrixAt(i,matrix);return Math.hypot(matrix.elements[0],matrix.elements[1],matrix.elements[2])};
  const entries=g.markers.items.map((item,i)=>({item,scale:scale(i)}));
  return {count:batch.count,shared:batch.geometry===g.rings.im.geometry && batch.material===g.rings.im.material,
   batches:g.scene.children.filter(o=>o.userData.terraMetroMarkers).length,entries,world:g.world.ents};
 }""",entry)
 assert marker['count']==1 and marker['shared'] and marker['batches']==1,marker
 station=next(m for m in marker['entries'] if m['item']['k']==2 and m['item']['x']==entry['x'] and m['item']['z']==entry['z'])
 collector=next(m for m in marker['entries'] if m['item']['k']==2 and m['item']['x']==12 and m['item']['z']==-10)
 assert station['scale']==0 and collector['scale']>0,marker
 assert all(m['scale']>0 for m in marker['entries'] if m['item']['k']!=2),marker
 # A height-provider failure must restore the native marker rather than hide it.
 fallback_marker=page.evaluate("""e=>{
  const g=game,old=window.TERRA_H,batch=g.scene.children.find(o=>o.userData.terraMetroMarkers);
  try {window.TERRA_H=()=>{throw Error('simulated failure')};
   g.markers.sync((item,m,c)=>{m.makeScale(1,1,1).setPosition(item.x,1,item.z);c.setRGB(1,1,1)});
   const i=g.markers.items.findIndex(item=>item.k===2&&item.x===e.x&&item.z===e.z),m=new g.cam.matrix.constructor();
   g.markers.im.getMatrixAt(i,m);return {count:batch.count,scale:Math.hypot(m.elements[0],m.elements[1],m.elements[2])};
  } finally {window.TERRA_H=old}
 }""",entry)
 assert fallback_marker=={'count':0,'scale':1},fallback_marker
 page.wait_for_function("game.scene.children.find(o=>o.userData.terraMetroMarkers).count===1")
 page.wait_for_timeout(800);page.screenshot(path=str(out/'metro-desktop.png'))
 page.set_viewport_size({'width':390,'height':844});page.wait_for_timeout(500);page.screenshot(path=str(out/'metro-portrait.png'))
 # Inspect three deterministic points of the actual camera wrapper. The scene
 # target is the stair centre, not the surface return position in descriptor.from.
 camera=page.evaluate('''e=>{
  const g=game,post=g.post,old=post.render,now=Object.getOwnPropertyDescriptor(performance,'now');
  let clock=1000,frames=[];Object.defineProperty(performance,'now',{configurable:true,value:()=>clock});
  post.render=function(scene,cam){
   const direction=cam.getWorldDirection(cam.position.clone());
   const profile=TERRA_SEWER_BRIDGE.metroProfileAt?.(e.x,e.z-1.5);
   const target=cam.position.clone().set(e.x,profile?profile.ground-.83:(window.TERRA_H?.(e.x,e.z-1.5)||0)+.7,e.z-1.5).sub(cam.position).normalize();
   frames.push({position:cam.position.toArray(),rotation:cam.quaternion.toArray(),alignment:direction.dot(target),native:cam===g.cam});
  };
  try{
   const key=Math.round(e.x)+','+Math.round(e.z);
   const ok=g.runDungeonTransition({theme:'metro',seed:key,key,idx:0,tier:1,from:{x:e.x,z:e.z+3},name:e.name},false);
   if(!ok)throw Error('camera probe transition refused');
   for(const t of [0,325,649]){clock=1000+t;post.render(g.scene,g.cam,0)}
   g.cancelDungeonTransition();return frames;
  }finally{g.cancelDungeonTransition?.();post.render=old;if(now)Object.defineProperty(performance,'now',now);else delete performance.now}
 }''',entry)
 assert len(camera)==3 and not any(frame['native'] for frame in camera),camera
 assert camera[2]['alignment'] > camera[0]['alignment'] + .002,camera
 dot=abs(sum(a*b for a,b in zip(camera[0]['rotation'],camera[2]['rotation'])))
 assert dot < .9999,camera  # catches aliased quaternion targets that never rotate
 assert camera[2]['position'][2] < camera[0]['position'][2],camera
 page.wait_for_function('!document.querySelector(".metroTransition") && !game.dungeonTransition')
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
 page.wait_for_function('game.scene.children.find(o=>o.userData.terraMetroMarkers).count===0')
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
