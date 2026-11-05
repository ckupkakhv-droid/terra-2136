"""Rock normals, native gameplay data and a rendered atlas-projection seam.

The GPU fixture has two barely angled triangles and continuous normals. A
gradient atlas exposes the old abrupt switch of projection at the shared edge.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-rock-surfaces'));out.mkdir(exist_ok=True)
reports=[]
with sync_playwright() as p:
 for enabled in [False,True]:
  label='after' if enabled else 'before'
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  if not enabled:page.add_init_script('window.TERRA_ART={rockSurfacesEnabled:false}')
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1400]) if m.type=='error' else None)
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.sewers && game.state==="play" && TERRA_KITS.ready')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,L=TERRA_SEWER_BRIDGE.shapes,result={chunks:[],models:[],other:[]};
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   const names=['rock_a','rock_b','stones','qn_rock_medium_1','qn_rock_medium_2','qn_rock_medium_3','qn_pebble_round_1','qn_pebble_round_3'];
   for(const name of names)for(const pose of [[0,0,0,.8],[.7,.25,-.15,1.4],[-1.2,-.3,.5,.4]]) {
    const c=new C(1,1);c.prep();c.anc=1;c.setOY(1.25);const b=c.s;
    b.add(L.box,10,.5,20,1,1,1,'#8b6e43',0,0,0,0);const start=b.p.length/3,prefix=b.n.slice();
    const dimensions=b.prop(name,12,0,22,pose[0],pose[3],.9,pose[1],pose[2]),end=b.p.length/3;
    const groups=new Map(),ids=[];let mismatch=0,maxError=0;
    for(let i=start;i<end;i++) {
     const k=i*3,key=b.p[k]+','+b.p[k+1]+','+b.p[k+2];let g=groups.get(key);
     if(!g){g={sum:[0,0,0],first:b.n.slice(k,k+3),indices:[]};groups.set(key,g)}g.indices.push(i);ids.push(g);
    }
    for(let i=start;i<end;i+=3) {
     const k=i*3,u=b.p.slice(k+3,k+6).map((v,j)=>v-b.p[k+j]),v=b.p.slice(k+6,k+9).map((v,j)=>v-b.p[k+j]),
      n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
     for(let j=0;j<3;j++)for(let a=0;a<3;a++)ids[i-start+j].sum[a]+=n[a];
    }
    for(const g of groups.values()) {
     let expected=g.sum,length=Math.hypot(...expected);if(length<1e-10){expected=g.first;length=Math.hypot(...expected)}
     for(const i of g.indices) {
      const n=b.n.slice(i*3,i*3+3);maxError=Math.max(maxError,Math.hypot(...n.map((v,j)=>v-expected[j]/length)));
      if(Math.hypot(...n.map((v,j)=>v-g.first[j]))>1e-5)mismatch++;
     }
    }
    const unit=b.n.slice(start*3,end*3).every((_,i,a)=>i%3||Math.abs(Math.hypot(...a.slice(i,i+3))-1)<1e-5);
    b.add(L.box,14,.5,22,1,1,1,'#8b6e43',0,0,0,0);const lengths=[b.p.length,b.n.length,b.m.length];
    const missing=b.prop('__no_rock__',0,0,0,0,1);
    result.models.push({name,pose,vertices:end-start,dimensions,maxError,mismatch,unit,
     prefix:prefix.every((v,i)=>v===b.n[i]),material:b.m.slice(start,end).every(v=>v===7),
     aligned:b.p.length===b.n.length&&b.m.length===b.p.length/3,
     missing:missing===false&&[b.p.length,b.n.length,b.m.length].every((v,i)=>v===lengths[i]),
     data:await hash([b.p,b.a,b.m,b.uv]),next:[c.r(),c.r(),c.r()]});
   }
   for(const name of ['barrel','qn_commontree_1','workbench','bench']) {
    const c=new C(1,1);c.prep();c.anc=1;c.setOY(0);c.s.prop(name,12,0,22,.3,1,.9);
    result.other.push({name,hash:await hash([c.s.p,c.s.n,c.s.c,c.s.a,c.s.m,c.s.uv]),next:[c.r(),c.r(),c.r()]});
   }
   for(const [x,z] of [[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]) {
    const c=new C(x,z);c.build();result.chunks.push({key:x+','+z,
     meta:await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]}),
     terrain:await hash([c.tr.p,c.tr.n,c.tr.c,c.tr.ws,c.tr.a])});
   }
   const mat=[...game.world.chunks.values()].flatMap(c=>c.meshes).find(m=>m.geometry?.attributes.mt&&m.material?.vertexColors)?.material;
   if(!mat)throw Error('Native static material absent');result.material={type:mat.type,flat:mat.flatShading,key:mat.customProgramCacheKey()};
   const c=new C(1,1);c.prep();c.anc=1;c.setOY(0);
   for(let row=0;row<2;row++)for(let col=0;col<3;col++)c.s.prop('qn_rock_medium_'+(col+1),(col-1)*4,0,row*4.5,row*.9,1.8,1);
   c.s.mt=-1;c.s.add(L.box,0,-.2,2.25,15,.4,12,'#41483d',0,0,0,0);
   const scene=new game.scene.constructor();scene.background=game.scene.background.clone();scene.add(game.hemi.clone());
   const sun=game.sun.clone();sun.position.set(-5,15,13);sun.target.position.set(0,0,2);sun.intensity=2.2;scene.add(sun,sun.target);
   sun.castShadow=true;sun.shadow.autoUpdate=true;sun.shadow.camera.left=-13;sun.shadow.camera.right=13;sun.shadow.camera.top=13;sun.shadow.camera.bottom=-13;sun.shadow.camera.near=1;sun.shadow.camera.far=60;sun.shadow.camera.updateProjectionMatrix();
   const mesh=c.s.mesh(mat);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);
   const clone=mat.clone(),compile=mat.onBeforeCompile;clone.onBeforeCompile=function(shader,renderer){compile.call(this,shader,renderer);window.__rockShader=shader};
   clone.customProgramCacheKey=()=>mat.customProgramCacheKey()+'-qa-capture';mesh.material=clone;
   const cam=game.cam.clone();cam.position.set(5,8.5,16);cam.lookAt(0,.7,2.2);cam.zoom=1.2;cam.updateProjectionMatrix();
   game.ren.shadowMap.enabled=true;game.ren.shadowMap.autoUpdate=true;game.ren.shadowMap.needsUpdate=true;
   window.__rocks={scene,cam,mat,mesh};game.post.render(scene,cam,0);return result;
  }''')
  for m in report['models']:
   assert m['unit'] and m['prefix'] and m['material'] and m['aligned'] and m['missing'],m
   if enabled:assert m['maxError']<.00002 and m['mismatch']==0,m
  if enabled:
   assert report['chunks']==reports[0]['chunks'] and report['other']==reports[0]['other'],'Native world/terrain or unrelated props changed'
   for old,new in zip(reports[0]['models'],report['models']):
    for key in ['data','next','dimensions','vertices']:assert new[key]==old[key],(key,old,new)
  else:assert max(v['maxError'] for v in report['models'])>.1
  page.wait_for_function('__rockShader.uniforms.uPbr.value>.99')
  render=page.evaluate('''()=>{game.ren.info.reset();game.ren.shadowMap.needsUpdate=true;game.post.render(__rocks.scene,__rocks.cam,0);
   return {calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,error:game.ren.getContext().getError()}}''')
  assert render['error']==0
  if enabled:assert render==reports[0]['render']
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/(label+'.png')))
  page.evaluate('''()=>{__rocks.cam.position.set(6.5,3.8,8);__rocks.cam.lookAt(4,.7,4.5);__rocks.cam.zoom=1.5;__rocks.cam.updateProjectionMatrix();game.post.render(__rocks.scene,__rocks.cam,0)}''')
  page.screenshot(path=str(out/(label+'-close.png')))
  seam=page.evaluate('''()=>{
   const original=__rocks.mat,compile=original.onBeforeCompile,layerCount=10,width=64,height=4;
   const source=__rockShader.uniforms.uTA.value;if(!source.isDataArrayTexture)throw Error('Native PBR atlas is not ready');
   const albedo=new Uint8Array(width*height*layerCount*4),normal=new Uint8Array(albedo.length);
   for(let l=0;l<layerCount;l++)for(let y=0;y<height;y++)for(let x=0;x<width;x++) {
    const k=((l*height+y)*width+x)*4,v=Math.round(50+150*x/(width-1));albedo.set([v,v,v,255],k);normal.set([128,128,128,255],k);
   }
   // The diagnostic ramp is deliberately non-periodic; clamp it so a repeat
   // border outside the sampled seam cannot introduce a second test artefact.
   const make=data=>{const t=new source.constructor(data,width,height,layerCount);t.wrapS=t.wrapT=1001;t.minFilter=t.magFilter=1006;t.needsUpdate=true;return t};
   const atlas=make(albedo),normals=make(normal),canvas=document.createElement('canvas');canvas.width=canvas.height=1;
   const ctx=canvas.getContext('2d');ctx.fillStyle='#808080';ctx.fillRect(0,0,1,1);
   const grime=new __rockShader.uniforms.uGrime.value.constructor(canvas);grime.needsUpdate=true;
   const material=original.clone();material.onBeforeCompile=function(shader,renderer) {
    compile.call(this,shader,renderer);shader.uniforms.uTA={value:atlas};shader.uniforms.uTN={value:normals};shader.uniforms.uGrime={value:grime};
    shader.uniforms.uPbr={value:1};shader.uniforms.uNs={value:0};shader.uniforms.uSc={value:Array(10).fill(1/4.5)};
    shader.uniforms.uStr={value:Array(10).fill(1)};shader.uniforms.uAvg={value:Array.from({length:10},()=>game.cam.position.clone().set(.5,.5,.5))};
    shader.fragmentShader=shader.fragmentShader.replace('#include <dithering_fragment>','gl_FragColor=vec4(diffuseColor.rgb,1.);\\n#include <dithering_fragment>');
   };material.customProgramCacheKey=()=>original.customProgramCacheKey()+'-qa-gradient';
   const a=[.3,1,.7],b=[.3,1,2.7],c=[-.39,1.72,1.7],d=[1.02,.31,1.7],points=[a,c,b,a,b,d],n1=[.72,.69,0],n2=[.69,.72,0],shared=[1,1,0];
   const normalise=n=>{const h=Math.hypot(...n);return n.map(v=>v/h)},ns=[shared,n1,shared,shared,shared,n2].flatMap(normalise);
   const chunk=new TERRA_SEWER_BRIDGE.Chunk(1,1);chunk.prep();chunk.anc=1;chunk.setOY(0);chunk.s.mt=6;
   chunk.s.add({p:points.flat(),n:ns},0,0,0,1,1,1,'#ffffff',0,0,0,0);
   const mesh=chunk.s.mesh(original);mesh.material=material;const scene=new game.scene.constructor();scene.add(mesh);
   const cam=game.cam.clone();cam.position.set(4.3,5,1.7);cam.lookAt(.3,1,1.7);cam.zoom=1.4;cam.updateProjectionMatrix();cam.updateMatrixWorld(true);
   const gl=game.ren.getContext(),anchor=game.cam.position.clone().set(.3,1,1.7).project(cam),cx=Math.round((anchor.x+1)*game.ren.domElement.width/2),cy=Math.round((anchor.y+1)*game.ren.domElement.height/2);
   if(cx<3||cy<3||cx>=game.ren.domElement.width-3||cy>=game.ren.domElement.height-3)throw Error('GPU seam sample outside canvas');
   game.ren.shadowMap.enabled=false;const result=[];
   for(let layer=0;layer<10;layer++) {
    const mt=mesh.geometry.getAttribute('mt');mt.array.fill(layer+1);mt.needsUpdate=true;game.post.render(scene,cam,0);gl.finish();
    const up=new Uint8Array(4),down=new Uint8Array(4);gl.readPixels(cx,cy+2,1,1,gl.RGBA,gl.UNSIGNED_BYTE,up);gl.readPixels(cx,cy-2,1,1,gl.RGBA,gl.UNSIGNED_BYTE,down);
    result.push({layer,up:[...up],down:[...down],gap:Math.max(...up.slice(0,3).map((v,i)=>Math.abs(v-down[i])))});
   }
   mesh.geometry.getAttribute('mt').array.fill(7);mesh.geometry.getAttribute('mt').needsUpdate=true;game.post.render(scene,cam,0);
   window.__rockSeam={scene,cam};return {layers:result,error:gl.getError(),center:[cx,cy]};
  }''')
  page.screenshot(path=str(out/(label+'-gradient.png')))
  assert seam['error']==0 and all(v['up'][3]==v['down'][3]==255 for v in seam['layers']),seam
  if enabled:
   assert seam['layers'][6]['gap']<5 and seam['layers'][6]['gap']<reports[0]['seam']['layers'][6]['gap']*.2,seam
   for a,b in zip(reports[0]['seam']['layers'],seam['layers']):
    if a['layer']!=6:assert max(abs(x-y) for side in ['up','down'] for x,y in zip(a[side],b[side]))<=2,(a,b)
  else:assert seam['layers'][6]['gap']>15,seam
  stats=page.evaluate('({...TERRA_ART.rockSurfaces})')
  if enabled:assert stats['models']==8 and stats['bytes']==46656 and stats['shaders']>0 and stats['fallback']==0,stats
  assert not errors,errors
  report.update(render=render,seam=seam,stats=stats,errors=errors);reports.append(report)
  (out/(label+'.json')).write_text(json.dumps(report,indent=2))
  print(label,'models',len(report['models']),'render',render,'seam',seam['layers'][6],'stats',stats,'JS0',flush=True);browser.close()
print('PASS native world/terrain/RNG, 8 rocks × 3 poses, normals/cache/materials, actual GPU seam, nine unrelated layers, same geometry/draws, JS0/GL0')
