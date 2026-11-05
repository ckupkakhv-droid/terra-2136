"""Leaf masks: unchanged trees, complete sidecar attributes and native GPU QA."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-leaf-qa'));out.mkdir(exist_ok=True)
reports=[]
with sync_playwright() as p:
 for enabled in [False,True]:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=b.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1200]) if m.type=='error' else None)
  page.goto(url+('?' if '?' not in url else '&')+'leaves='+('1' if enabled else '0'),timeout=120000)
  page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.sewers && game.state==="play"')
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,result=[];
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   for(const kind of ['rbirch','poplar','maple','pine','willow','qbush']) {
    const c=new C(1,1);c.prep();c[kind](90,82,.8);
    const geo=c.f.geometry(),leaf=geo?.getAttribute('terraLeaf');
    result.push({kind,data:await hash([c.f.p,c.f.n,c.f.c,c.f.a,c.cols,c.nodes,[c.r(),c.r(),c.r()]]),
      vertices:c.f.p.length/3,flags:leaf?.count||0,bytes:leaf?.array.BYTES_PER_ELEMENT||0,
      broad:leaf?[...leaf.array].filter(v=>v===1).length:0,needles:leaf?[...leaf.array].filter(v=>v===2).length:0});
    geo?.dispose();
   }
   return result;
  }''')
  reports.append(report)
  print(('UPDATED' if enabled else 'BASELINE'),report,flush=True)
  if enabled:
   for old,new in zip(reports[0],report):
    assert old['data']==new['data'] and old['vertices']==new['vertices'],(old,new)
    if new['kind']=='willow':assert new['flags']==0,'Bare twisted trunk was classified as leaves'
    else:assert new['flags']==new['vertices'] and new['bytes']==1 and new['broad']+new['needles']>0,new
  page.evaluate('game.loop=function(){}');page.wait_for_timeout(100)
  scene=page.evaluate('''()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,c=new C(1,1),meshes=[...game.world.chunks.values()].flatMap(c=>c.meshes);
   const fol=meshes.find(m=>m.geometry?.attributes.terraLeaf)?.material||meshes.find(m=>m.material?.isMeshLambertMaterial&&m.material.vertexColors&&!m.geometry?.attributes.mt&&!m.geometry?.attributes.w0&&!m.geometry?.attributes.uv&&m.geometry?.attributes.aux?.array.some((v,i)=>i%2===0&&v>.01))?.material;
   const stat=meshes.find(m=>m.geometry?.attributes.mt)?.material;
   if(!fol||!stat)throw Error('Native foliage/static material unavailable');
   c.prep();c.hAt=()=>0;c.anc=1;c.setOY(0);
   c.rbirch(86.8,82,.8);c.qtree0(90.5,82,'tree',.8);c.qtree0(94,82,'pine',.7);c.qbush(90.5,85,.8);
   c.s.add(TERRA_SEWER_BRIDGE.shapes.box,90,-.15,82,25,.3,22,'#465441',0,0,0,0);
   const scene=new game.scene.constructor();scene.fog=game.scene.fog.clone();scene.background=game.scene.background.clone();
   scene.add(game.hemi.clone());const sun=game.sun.clone();scene.add(sun,sun.target);
   window.__leafScene=scene;window.__leafSun=sun;
   const ground=c.s.mesh(stat),crown=c.f.mesh(fol);
   scene.add(ground,crown);window.__leafCrown=crown;window.__leafGround=ground;
   sun.position.set(82,24,95);sun.target.position.set(90,0,82);sun.intensity=2.4;
   const cam=game.cam.clone();cam.position.set(90,12,98);cam.lookAt(90,3,82);cam.zoom=.9;cam.updateProjectionMatrix();
   window.__leafCam=cam;game.ren.info.reset();game.post.render(__leafScene,cam,0);
   return {calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,flags:c.f.geometry().getAttribute('terraLeaf')?.count||0,material:fol.type};
  }''')
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/('canopies-after.png' if enabled else 'canopies-before.png')))
  timing=page.evaluate('''()=>{
   const gl=game.ren.getContext(),samples=[];
   for(let i=0;i<11;i++){const t=performance.now();game.ren.info.reset();game.post.render(__leafScene,__leafCam,0);gl.finish();if(i>1)samples.push(performance.now()-t);}
   samples.sort((a,b)=>a-b);return {medianMs:samples[4],samples,calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,error:gl.getError()};
  }''')
  print('Scene',scene,'timing',timing,flush=True)
  page.evaluate('__leafCam.position.set(87,8,89);__leafCam.lookAt(87,4.1,82);__leafCam.zoom=1.5;__leafCam.updateProjectionMatrix();game.post.render(__leafScene,__leafCam,0)')
  page.screenshot(path=str(out/('birch-after.png' if enabled else 'birch-before.png')))
  shadow=page.evaluate('''()=>{
   const crown=__leafCrown,ground=__leafGround,ren=game.ren;
   // A second leaf batch must reuse both shadow materials, while a non-leaf
   // batch using the same visible material supplies a constant zero attribute.
   const C=TERRA_SEWER_BRIDGE.Chunk,c=new C(1,1);c.prep();c.setOY(0);
   c.qbush(97,82,.8);const other=c.f.mesh(crown.material);__leafScene.add(other);
   const b=new C(1,1);b.prep();b.setOY(0);
   b.f.add(TERRA_SEWER_BRIDGE.shapes.box,96,1,86,1,2,1,'#617249',0,0,0,0);
   const plain=b.f.mesh(crown.material);__leafScene.add(plain);
   if(plain.geometry.hasAttribute('terraLeaf'))throw Error('Non-leaf geometry received a mask');
   const pair=!!crown.customDepthMaterial&&!!crown.customDistanceMaterial;
   const shared=pair&&other.customDepthMaterial===crown.customDepthMaterial&&other.customDistanceMaterial===crown.customDistanceMaterial;
   ground.receiveShadow=true;crown.castShadow=true;other.castShadow=true;plain.castShadow=true;
   ren.shadowMap.enabled=true;ren.shadowMap.autoUpdate=true;
   __leafSun.shadow.camera.left=-18;__leafSun.shadow.camera.right=18;
   __leafSun.shadow.camera.top=18;__leafSun.shadow.camera.bottom=-18;
   __leafSun.shadow.camera.near=1;__leafSun.shadow.camera.far=80;__leafSun.shadow.camera.updateProjectionMatrix();
   __leafCam.position.set(90,20,100);__leafCam.lookAt(90,1,82);__leafCam.zoom=.9;__leafCam.updateProjectionMatrix();
   ren.info.reset();game.post.render(__leafScene,__leafCam,3);
   window.__leafTestMeshes=[other,plain];
   return {pair,shared,defaultZero:crown.material.defaultAttributeValues?.terraLeaf?.[0]===0,
    shadowMap:!!__leafSun.shadow.map,calls:ren.info.render.calls,triangles:ren.info.render.triangles,error:ren.getContext().getError()};
  }''')
  page.screenshot(path=str(out/('shadows-after.png' if enabled else 'shadows-before.png')))
  assert shadow['shadowMap'] and shadow['error']==0,shadow
  if enabled:assert shadow['pair'] and shadow['shared'] and shadow['defaultZero'],shadow
  # Compile the point-light shadow variant as well. The game already owns point
  # lights; borrow only their constructor, never alter an existing light.
  distance=page.evaluate('''()=>{
   let Point;game.scene.traverse(o=>{if(o.isPointLight)Point=o.constructor});
   if(!Point)throw Error('Native point-light constructor unavailable');
   const light=new Point(0xffe5c2,3,32);light.position.set(92,9,86);light.castShadow=true;
   light.shadow.mapSize.set(256,256);__leafScene.add(light);__leafSun.castShadow=false;
   game.ren.info.reset();game.post.render(__leafScene,__leafCam,4);
   const result={shadowMap:!!light.shadow.map,error:game.ren.getContext().getError()};
   __leafScene.remove(light);light.dispose();__leafSun.castShadow=true;return result;
  }''')
  assert distance['shadowMap'] and distance['error']==0,distance
  page.evaluate('''()=>{
   game.ren.shadowMap.enabled=false;__leafTestMeshes.forEach(m=>m.visible=false);
   __leafCam.position.set(90,25,148);__leafCam.lookAt(90,3,82);__leafCam.zoom=.9;__leafCam.updateProjectionMatrix();
   game.post.render(__leafScene,__leafCam,4);
  }''')
  page.screenshot(path=str(out/('distance-after.png' if enabled else 'distance-before.png')))
  proxy=page.evaluate('''async()=>{
   game.ixInit();const node={k:'wood',x:90,z:82,tree:{k:'qn_commontree_1',x:90,z:82,y:0,h:8,tint:1,ry:.2}};
   const proxy=game.ixTreeProxy(node);if(!proxy)throw Error('Native tree proxy missing');
   __leafCrown.visible=false;__leafScene.add(proxy.mesh);
   proxy.fall={th:.65,w:.45,dir:.3,t:0,landed:false};game.ixTrees(1/60);
   const geo=proxy.mesh.geometry,flags=geo.getAttribute('terraLeaf'),native=[];
   for(const name of ['position','normal','color','aux'])native.push([...geo.getAttribute(name).array]);
   native.push([...proxy.mesh.matrix.elements]);
   const data=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(native))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   __leafCam.position.set(90,13,99);__leafCam.lookAt(90,3,82);__leafCam.zoom=1;__leafCam.updateProjectionMatrix();
   game.post.render(__leafScene,__leafCam,4);
   const result={data,vertices:geo.getAttribute('position').count,flags:flags?.count||0,
     shadows:!!proxy.mesh.customDepthMaterial,shadowKey:proxy.mesh.customDepthMaterial?.customProgramCacheKey(),side:proxy.mesh.material.side,error:game.ren.getContext().getError()};
   return result;
  }''')
  page.screenshot(path=str(out/('falling-after.png' if enabled else 'falling-before.png')))
  if enabled:assert proxy['data']==baseline_proxy['data'] and proxy['flags']==proxy['vertices'] and proxy['shadows'] and proxy['side']==2 and 'f0m0' in proxy['shadowKey'],proxy
  else:baseline_proxy=proxy
  assert proxy['error']==0,proxy
  print('Shadows',shadow,'point light',distance,'falling',proxy,flush=True)
  (out/('updated.json' if enabled else 'baseline.json')).write_text(json.dumps({'trees':report,'scene':scene,'timing':timing,'shadow':shadow,'distanceShadow':distance,'proxy':proxy,'errors':errors},indent=2))
  assert timing['error']==0 and not errors,errors
  b.close()
print('PASS tree metadata/RNG/geometry, complete byte attributes, native shader compilation and GPU rendering')
