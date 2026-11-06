"""Own hero asset failure / late arrival, fitted suit geometry and native poses."""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='a52081ccb5c6db1dc540bafa261342f5a0ca5c07'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-hero-fallback'));out.mkdir(exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-fallback-baseline/terra-v31.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='9a5a7bf7ea447c98a2494ffa3f158382baa5360c27a92fcb1db1a79c54abe089'
a=json.loads(gzip.decompress((ROOT/'play/assets/pack/TERRA_ASSETS.json.gz').read_bytes()))['hero']
hero=base64.b64decode(a[3:] if a.startswith('gz:') else a)
if a.startswith('gz:'):hero=gzip.decompress(hero)
assert hero[:4]==b'glTF'
reports=[]
with sync_playwright() as p:
 for mode in ['before','failed-own-model','late-own-model']:
  baseline=mode=='before';fail=mode!='late-own-model'
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(120000);pending=[];errors=[];warnings=[]
  page.route('**/qa/pending-hero.glb',lambda r:pending.append(r))
  page.on('pageerror',lambda e:errors.append(str(e)))
  def console(m):
   expected=fail and ('ERR_FAILED' in m.text and '/qa/pending-hero.glb' in m.location.get('url','') or m.text.startswith('GLB hero '))
   if m.type=='error' and not expected:errors.append(m.text[:1200])
   if m.type=='warning':warnings.append(m.text[:400])
  page.on('console',console)
  page.add_init_script("""localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}));let assets;Object.defineProperty(window,'TERRA_ASSETS',{configurable:true,get(){return assets},set(v){assets=v;v.hero='url:'+location.origin+'/qa/pending-hero.glb'}});""")
  if baseline:page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
  page.goto(url,timeout=120000);page.wait_for_function('window.game && game.sewers && !game.glb.hero');assert len(pending)==1
  page.evaluate('''()=>{window.__heroRefresh=[];const refresh=game.refreshModelMode;game.refreshModelMode=function(...a){const had=!!this.heroInst,r=refresh.apply(this,a);__heroRefresh.push({full:!!this.g07Assets,created:!had&&!!this.heroInst,heroOnly:a[0]===true});return r}}''')
  page.locator('#mNew').click();page.wait_for_function('game.state==="intro"')
  intro=page.evaluate('({inst:!!game.heroInst,parts:game.heroRig.parts.map(p=>p.im.count)})')
  assert not intro['inst'] and all(v==0 for v in intro['parts'])
  page.locator('#skip').click();page.wait_for_function('game.state==="play" && game.heroRig.parts.every(p=>p.im.count===1)')
  early=page.evaluate('({pool:!!game.glb.hero,inst:!!game.heroInst,visible:game.heroRig.parts.filter(p=>p.im.visible).length})')
  assert not early['pool'] and not early['inst'] and early['visible']==6,early
  if fail:pending[0].abort('failed')
  else:pending[0].fulfill(body=hero,content_type='model/gltf-binary')
  page.wait_for_function('__heroRefresh.some(r=>r.full)')
  if not fail:page.wait_for_function('!!game.heroInst && game.heroInst.mixer.time>0')
  final=page.evaluate('''()=>({pool:!!game.glb.hero,inst:!!game.heroInst,rig:game.heroRig.parts.filter(p=>p.im.visible&&p.im.count).length,
   visible:!!game.heroInst?.root.visible,roots:game.heroInst?game.scene.children.filter(o=>o===game.heroInst.root).length:0,
   created:__heroRefresh.filter(r=>r.created).length,heroOnly:__heroRefresh.some(r=>r.created&&r.heroOnly)})''')
  if fail:assert not final['inst'] and not final['pool'] and final['rig']==(0 if baseline else 6),final
  else:
   assert final['inst'] and final['pool'] and final['visible'] and final['roots']==final['created']==1 and final['rig']==0 and final['heroOnly'],final
   assert page.evaluate('''()=>{game.heroInst.root.visible=false;game.heroPose(0);const kept=!game.heroInst.root.visible;game.heroInst.root.visible=true;return kept}''')
  page.screenshot(path=str(out/(mode+'-game.png')))
  session=None
  if not baseline:
   start=page.evaluate('game.p.x');page.keyboard.down('KeyD');page.wait_for_function('x=>Math.abs(game.p.x-x)>.12',arg=start);page.keyboard.up('KeyD')
   page.evaluate('''()=>{const w=game.makeWeapon('katana',0,0,null);game.p.weapons.push(w);game.p.eq[game.p.slot]=w;window.__fallbackWeapon=w.uid}''')
   page.wait_for_function('game.wMesh.visible && game.wMesh.matrix.elements.every(Number.isFinite)')
   session=page.evaluate('''()=>{const p=game.p,x=p.x,saved=game.save();game.p.x+=3;const loaded=game.continueGame();return{saved:!!saved?.ok,loaded:!!loaded?.ok,newPlayer:game.p!==p,x,weapon:game.p.weapons.some(w=>w.uid===__fallbackWeapon)}}''')
   assert all(session[k] for k in ['saved','loaded','newPlayer','weapon']),session
   page.wait_for_function('x=>game.state==="play"&&Math.abs(game.p.x-x)<.03',arg=session['x'])
   if fail:assert page.evaluate('!game.heroInst && game.heroRig.parts.every(p=>p.im.visible)')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  geometry=page.evaluate('''async baseline=>{
   const Rig=game.heroRig.constructor,scene=new game.scene.constructor(),rig=new Rig(scene,'hero',1),hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   const parts=[];for(const p of rig.parts){const g=p.im.geometry,P=g.getAttribute('position').array,N=g.getAttribute('normal').array,C=g.getAttribute('color').array,A=g.getAttribute('aux'),lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];let unit=0,winding=0,degenerate=0;
    for(let i=0;i<P.length;i++){lo[i%3]=Math.min(lo[i%3],P[i]);hi[i%3]=Math.max(hi[i%3],P[i]);}
    for(let i=0;i<N.length;i+=3)unit=Math.max(unit,Math.abs(Math.hypot(...N.slice(i,i+3))-1));
    for(let i=0;i<P.length;i+=9){const u=[0,1,2].map(k=>P[i+3+k]-P[i+k]),v=[0,1,2].map(k=>P[i+6+k]-P[i+k]),n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],length=Math.hypot(...n);if(length<1e-12){degenerate++;continue;}if(n.reduce((s,v,k)=>s+v*(N[i+k]+N[i+3+k]+N[i+6+k]),0)<=0)winding++;}
    parts.push({name:p.n,pivot:p.pivot,lo,hi,vertices:P.length/3,triangles:P.length/9,unit,winding,degenerate,finite:[...P,...N,...C].every(Number.isFinite),aligned:P.length===N.length&&P.length===C.length&&A.count===P.length/3});
   }
   const poses=[{x:0,z:0,yaw:0,ph:.4,amp:0},{x:1,z:-2,y:.3,yaw:.7,ph:1.2,amp:.8},{x:-2,z:3,yaw:-1.1,ph:2,armR:-1.5,aimL:1.25,twist:.6,bend:.15},{x:1,z:1,yaw:.2,fall:1,fallDir:-1,lean:.2,sc:1.3,flash:.5,tint:[.8,.9,1]}],matrices=[];
   for(const pose of poses){const p={...pose};rig.update([p]);matrices.push(await hash([rig.parts.map(p=>[...p.im.instanceMatrix.array,...p.im.instanceColor.array]),p._root.elements,p._armR.elements]));}
   let bypass=null,other=true,independent=true,rng=true;
   if(!baseline){const art=TERRA_ART,old=art.actorFallbacksEnabled;art.actorFallbacksEnabled=false;const a=new Rig(new scene.constructor(),'hero',1);art.actorFallbacksEnabled=old;const b=new Rig(new scene.constructor(),'hero',1);
    bypass=await hash(a.parts.map(p=>[...p.im.geometry.getAttribute('position').array,...p.im.geometry.getAttribute('normal').array]));
    independent=rig.parts.every((p,i)=>p.im.geometry!==b.parts[i].im.geometry&&p.im.geometry.getAttribute('position').array!==b.parts[i].im.geometry.getAttribute('position').array);
    for(const type of ['zombie','mutant','fungus','skeleton']){art.actorFallbacksEnabled=false;const c=new Rig(new scene.constructor(),type,1);art.actorFallbacksEnabled=old;const d=new Rig(new scene.constructor(),type,1);const data=r=>r.parts.map(p=>Object.values(p.im.geometry.attributes).map(a=>Array.from(a.array)));other=other&&(await hash(data(c)))===(await hash(data(d)))}
    const random=Math.random;let calls=0;Math.random=()=>{calls++;return random()};try{art.actorFallbacksEnabled=false;new Rig(new scene.constructor(),'hero',1);const first=calls;calls=0;art.actorFallbacksEnabled=old;new Rig(new scene.constructor(),'hero',1);rng=first===calls}finally{Math.random=random;art.actorFallbacksEnabled=old}
   }
   const nativeHash=await hash(rig.parts.map(p=>[...p.im.geometry.getAttribute('position').array,...p.im.geometry.getAttribute('normal').array]));
   rig.update([{x:0,z:0,yaw:0,ph:.4,amp:0}]);
   const hemi=game.hemi.clone();hemi.color.set('#ffffff');hemi.groundColor.set('#8a9199');hemi.intensity=1.6;scene.add(hemi);const sun=game.sun.clone();sun.position.set(-3,5,4);sun.target.position.set(0,1,0);sun.intensity=2;sun.castShadow=false;scene.add(sun,sun.target);
   const floor=new TERRA_SEWER_BRIDGE.WeaponBuilder(()=>.5);floor.b(0,-.07,0,4,.1,4,'#4b5048');const ground=new TERRA_SEWER_BRIDGE.Mesh(floor.geometry(),rig.parts[0].im.material);ground.receiveShadow=true;scene.add(ground);
   const cam=game.cam.clone();if(cam.isOrthographicCamera){cam.left=-1.55;cam.right=1.55;cam.top=1.25;cam.bottom=-1.25}else cam.fov=35;cam.position.set(2.8,2.1,4.6);cam.lookAt(0,1,0);cam.zoom=1;cam.updateProjectionMatrix();scene.background=game.scene.background.clone();game.ren.shadowMap.enabled=false;
   window.__fallbackScene={scene,cam,rig,sun};game.ren.info.reset();game.post.render(scene,cam,0);
   return{parts,matrices,bypass,nativeHash,other,independent,rng,cache:TERRA_ART.actorFallbacks?{count:TERRA_ART.actorFallbacks.templates,bytes:TERRA_ART.actorFallbacks.bytes,built:TERRA_ART.actorFallbacks.built,fallback:TERRA_ART.actorFallbacks.fallback}:null,
    render:{calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,glError:game.ren.getContext().getError()}};
  }''',baseline)
  assert all(p['finite'] and p['aligned'] and p['unit']<1e-6 and p['winding']==0 and p['degenerate']==0 for p in geometry['parts']),geometry['parts']
  assert geometry['render']['glError']==0 and not errors,(geometry,errors)
  if not baseline:
   assert geometry['matrices']==reports[0]['geometry']['matrices'] and geometry['bypass']==reports[0]['geometry']['nativeHash']
   assert geometry['other'] and geometry['independent'] and geometry['rng'] and geometry['cache']['count']==6 and geometry['cache']['fallback']==0,geometry
   assert sum(p['triangles'] for p in geometry['parts'])<=600
   for a,b in zip(reports[0]['geometry']['parts'],geometry['parts']):
    assert a['name']==b['name'] and a['pivot']==b['pivot']
    expected=[*a['lo'],*a['hi']];actual=[*b['lo'],*b['hi']]
    if b['name']=='torso':expected[1]-=.025
    assert max(abs(x-y) for x,y in zip(expected,actual))<1e-6,(a,b)
   assert geometry['render']['calls']==reports[0]['geometry']['render']['calls']
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/(mode+'.png')))
  page.evaluate('''()=>{__fallbackScene.cam.position.set(-2.8,2.1,-4.6);__fallbackScene.cam.lookAt(0,1,0);game.post.render(__fallbackScene.scene,__fallbackScene.cam,0)}''');page.screenshot(path=str(out/(mode+'-rear.png')))
  report={'mode':mode,'intro':intro,'early':early,'final':final,'session':session,'geometry':geometry,'errors':errors,'warnings':warnings};(out/(mode+'.json')).write_text(json.dumps(report,indent=2));reports.append(report)
  print(mode,json.dumps({'final':final,'geometry':geometry['render'],'cache':geometry['cache'],'session':session}),flush=True);browser.close()
print('PASS own model failure and late success, intro/visibility, move/weapon/save/continue, six-part suit bounds/poses/material calls, other rigs/native RNG/bypass independent, JS0/GL0')
