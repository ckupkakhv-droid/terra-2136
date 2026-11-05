"""Compare published 0.4.25 with the new closed rocks in the native renderer.

Serve published terra.html separately; set TERRA_BASELINE_URL as needed.
TERRA_TEST_URL accepts the working play/ or a standalone HTTP build.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

baseline=os.environ.get('TERRA_BASELINE_URL','http://127.0.0.1:8182/terra-v25.html')
updated=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-rocks-qa'));out.mkdir(exist_ok=True)
reports=[]
with sync_playwright() as p:
 for label,url in [('before',baseline),('after',updated)]:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1200]) if m.type=='error' else None)
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.sewers && game.state==="play" && TERRA_KITS.ready')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,result={chunks:[],surfaces:[],models:{}};
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   for(const [x,z] of [[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]) {
    const c=new C(x,z);c.build();result.chunks.push({key:x+','+z,hash:await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,
     brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})});
   }
   const mat=[...game.world.chunks.values()].flatMap(c=>c.meshes).find(m=>m.geometry?.attributes.mt&&m.material?.vertexColors)?.material;
   if(!mat)throw Error('Native static material absent');
   const fixture=new C(1,1);fixture.prep();fixture.anc=1;fixture.setOY(1.25);
   const prop=fixture.s.prop,placed=[];
   fixture.s.prop=function(...args){placed.push(args);return prop.apply(this,args)};
   for(let i=0;i<24;i++)fixture.rock(80+i*3,80,[.7,1,1.4][i%3]);
   result.native={placed,cols:fixture.cols,next:[fixture.r(),fixture.r(),fixture.r()],
    aligned:fixture.s.m.length===fixture.s.p.length/3,finite:fixture.s.p.every(Number.isFinite)};
   for(let i=1;i<=3;i++) {
    const name='qn_rock_medium_'+i,c=new C(1,1);c.prep();c.anc=1;c.setOY(0);
    const dimensions=c.s.prop(name,0,0,0,.35,1.8,1),mesh=c.s.mesh(mat);mesh.updateMatrixWorld(true);
    const rays=[];for(let j=0;j<8;j++) {
     const angle=j*Math.PI/4,ray=new game.ray.constructor();ray.ray.origin.set(Math.cos(angle)*6,.9,Math.sin(angle)*6);
     ray.ray.direction.copy(ray.ray.origin).setY(0).normalize().negate();rays.push(ray.intersectObject(mesh).length>0);
    }
    mesh.geometry.computeBoundingBox();const box=mesh.geometry.boundingBox;
    result.surfaces.push({name,rays,dimensions,base:box.min.y,top:box.max.y,
     aligned:c.s.m.length===c.s.p.length/3,material:c.s.m.every(v=>v===7),
     finite:c.s.p.every(Number.isFinite)&&c.s.n.every(Number.isFinite)});
    mesh.geometry.dispose();result.models[name]=TERRA_PROPS.idx[name].t;
   }
   const c=new C(1,1);c.prep();c.anc=1;c.setOY(0);
   for(let row=0;row<2;row++)for(let col=0;col<3;col++)c.s.prop('qn_rock_medium_'+(col+1),(col-1)*4,0,row*4.5,row*.9,1.8,1);
   c.s.mt=-1;c.s.add(TERRA_SEWER_BRIDGE.shapes.box,0,-.2,2.25,15,.4,12,'#41483d',0,0,0,0);
   const scene=new game.scene.constructor();scene.background=game.scene.background.clone();scene.add(game.hemi.clone());
   const sun=game.sun.clone();sun.position.set(-5,15,13);sun.target.position.set(0,0,2);sun.intensity=2.2;scene.add(sun,sun.target);
   sun.castShadow=true;sun.shadow.autoUpdate=true;sun.shadow.camera.left=-13;sun.shadow.camera.right=13;sun.shadow.camera.top=13;sun.shadow.camera.bottom=-13;
   sun.shadow.camera.near=1;sun.shadow.camera.far=60;sun.shadow.camera.updateProjectionMatrix();
   const mesh=c.s.mesh(mat);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);
   const cam=game.cam.clone();cam.position.set(5,8.5,16);cam.lookAt(0,.7,2.2);cam.zoom=1.2;cam.updateProjectionMatrix();
   game.ren.shadowMap.enabled=true;game.ren.shadowMap.autoUpdate=true;game.ren.shadowMap.needsUpdate=true;
   game.ren.info.reset();game.post.render(scene,cam,0);window.__rocks={scene,cam};
   result.render={calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,error:game.ren.getContext().getError()};return result;
  }''')
  assert report['native']['aligned'] and report['native']['finite']
  assert len({v[0] for v in report['native']['placed']})==3,'Fixture should exercise all native rock choices'
  for s in report['surfaces']:
   assert s['aligned'] and s['material'] and s['finite'] and abs(s['base'])<1e-6,s
   # Published metadata rounds dimensions to millimetres; its quantised top
   # may differ slightly from the nominal height used by prop().
   assert abs(s['top']-1.8)<.001,s
  if label=='before':assert report['models']['qn_rock_medium_1']==report['models']['qn_rock_medium_3']==260
  else:
   assert report['chunks']==reports[0]['chunks'] and report['native']==reports[0]['native'],'World/RNG/native collisions changed'
   assert report['models']['qn_rock_medium_1']<260 and report['models']['qn_rock_medium_3']<260
   for old,new in zip(reports[0]['surfaces'],report['surfaces']):
    assert new['dimensions']==old['dimensions'] and all(new['rays']),new
   assert report['render']['calls']==reports[0]['render']['calls'] and report['render']['triangles']<reports[0]['render']['triangles']
  assert report['render']['error']==0 and not errors,errors
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/(label+'.png')))
  page.evaluate('''()=>{__rocks.cam.position.set(6.5,3.8,8);__rocks.cam.lookAt(4,.7,4.5);__rocks.cam.zoom=1.5;__rocks.cam.updateProjectionMatrix();game.post.render(__rocks.scene,__rocks.cam,0)}''')
  page.screenshot(path=str(out/(label+'-close.png')))
  assert page.evaluate('game.ren.getContext().getError()')==0 and not errors
  report['errors']=errors;(out/(label+'.json')).write_text(json.dumps(report,indent=2));reports.append(report)
  print(label,report['models'],report['render'],'native rocks',len(report['native']['placed']),'JS0',flush=True);browser.close()
print('PASS 9 chunks, all native rock choices/RNG/collisions, bounds/materials/8-angle rays, same batches/lower triangles, JS0/GL0')
