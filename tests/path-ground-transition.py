"""Published 0.4.28 vs faded local footpaths: native geometry stays exact.

Disable the later edge-normal correction in both modes to keep this historical
comparison focused on footpath paint. Its default is tested separately.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='3bcd1caa8ab1bcaa78b9b007efc9cd87ad1576a8'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-path-transition'));out.mkdir(exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-path-baseline/terra-v28.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='d511d43d7aa32310b02da216dfdec6b98868f8ea0622917ff9fd7e6c040ef92f'
reports=[];samples=[]
with sync_playwright() as p:
 for baseline in [True,False]:
  label='before' if baseline else 'after'
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}));window.TERRA_ART={terrainEdgeNormalsEnabled:false}")
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1000]) if m.type=='error' else None)
  if baseline:page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.state==="play" && game.sewers && TERRA_KITS.ready')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,result={cases:[],chunks:[],samples:[]},chunks=new Map();
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   function flat(cx,cz,path){
    const c=new C(cx,cz);c.prep();c.T.hg.fill(0);c.T.hv.fill(0);c.T.riv.fill(0);c.T.rd.fill(100);c.T.wl.fill(-99);c.T.cls.fill(null);
    c.pads=[];c.cols=[];c.ponds=[];c.paths=path?[path]:[];c.d='outskirts';c.anc=1;c.setOY(0);c.terrain();return c;
   }
   for(const [cx,cz] of [[1,1],[-2,-1]])for(let axis=0;axis<4;axis++)for(const width of [1.5,3.2]){
    const ox=cx*48,oz=cz*48,lines=[[ox+20,oz+30,ox+48,oz+30,width],[ox,oz+30,ox+28,oz+30,width],[ox+30,oz+20,ox+30,oz+48,width],[ox+30,oz,ox+30,oz+28,width]],path=lines[axis],c=flat(cx,cz,path),empty=flat(cx,cz,null),points=[];
    for(let i=0;i<c.tr.p.length;i+=3){const x=c.tr.p[i],z=c.tr.p[i+2];points.push({x,z,edge:Math.min(x-ox,ox+48-x,z-oz,oz+48-z),color:c.tr.c.slice(i,i+3),weights:c.tr.ws.slice(i/3*8,i/3*8+8),wet:c.tr.a[i/3*2+1],emptyColor:empty.tr.c.slice(i,i+3),emptyWeights:empty.tr.ws.slice(i/3*8,i/3*8+8),emptyWet:empty.tr.a[i/3*2+1]});}
    result.cases.push({key:cx+','+cz+','+axis+','+width,path,geometry:await hash([c.tr.p,c.tr.n,c.grid,c.w.p,c.w.a]),metadata:await hash([c.cols,c.paths,c.pads,c.r(),c.r()])});result.samples.push(points);
   }
   const terrain=C.prototype.terrain;
   for(const [cx,cz] of [[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]){
    const c=new C(cx,cz);c.build();chunks.set(cx+','+cz,c);const noPaths=new C(cx,cz);
    C.prototype.terrain=function(...args){const paths=this.paths;this.paths=[];try{return terrain.apply(this,args)}finally{this.paths=paths}};
    try{noPaths.build()}finally{C.prototype.terrain=terrain}
    const edges={},interior=[],outerNoPath=[];let boundaryError=0;
    for(let i=0;i<c.tr.p.length;i+=3){const x=c.tr.p[i],z=c.tr.p[i+2],distance=Math.min(x-c.ox,c.ox+48-x,z-c.oz,c.oz+48-z),color=c.tr.c.slice(i,i+3),w=c.tr.ws.slice(i/3*8,i/3*8+8),wet=c.tr.a[i/3*2+1];
     if(distance>=4)interior.push(...color,...w,wet);
     if(distance===0){const key=x+','+z;edges[key]={color,w,wet};const empty=[...noPaths.tr.c.slice(i,i+3),...noPaths.tr.ws.slice(i/3*8,i/3*8+8),noPaths.tr.a[i/3*2+1]],actual=[...color,...w,wet];boundaryError=Math.max(boundaryError,...actual.map((v,j)=>Math.abs(v-empty[j])));outerNoPath.push(...empty);}
    }
    result.chunks.push({key:cx+','+cz,kind:c.d,paths:c.paths,edges,boundaryError,emptyBoundary:await hash(outerNoPath),interior:await hash(interior),geometry:await hash([c.tr.p,c.tr.n,c.grid,c.w.p,c.w.n,c.w.a]),metadata:await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})});
   }
   result.seams=[];
   for(const [point,a,b]of[['0,-6','-1,-1','0,-1'],['46,0','0,-1','0,0'],['-6,48','-1,0','-1,1'],['86,48','1,0','1,1']]){
    const A=result.chunks.find(c=>c.key===a).edges[point],B=result.chunks.find(c=>c.key===b).edges[point];
    result.seams.push({point,a,b,color:Math.max(...A.color.map((v,i)=>Math.abs(v-B.color[i]))),weights:Math.max(...A.w.map((v,i)=>Math.abs(v-B.w[i]))),wet:Math.abs(A.wet-B.wet)});
   }
   const meshes=[...game.world.chunks.values()].flatMap(c=>c.meshes),source=meshes.find(m=>m.geometry?.attributes.w0)?.material;
   if(!source)throw Error('Native terrain material absent');
   const material=source.clone(),compile=source.onBeforeCompile;
   material.onBeforeCompile=function(shader,renderer){compile.call(this,shader,renderer);shader.uniforms.uRain={value:0};window.__pathShader=shader};
   material.customProgramCacheKey=()=>source.customProgramCacheKey()+'-qa-footpath';
   const scene=new game.scene.constructor();scene.background=game.scene.background.clone();const hemi=game.hemi.clone();hemi.color.set('#ffffff');hemi.groundColor.set('#ffffff');hemi.intensity=1;scene.add(hemi);
   for(const key of ['-1,-1','0,-1'])scene.add(chunks.get(key).tr.mesh(material));
   const cam=game.cam.clone();cam.position.set(4,6,1);cam.lookAt(0,-2.5,-6);cam.zoom=2.8;cam.updateProjectionMatrix();
   game.ren.shadowMap.enabled=false;window.__pathScene={scene,cam};game.post.render(scene,cam,0);return result;
  }''')
  current_samples=report.pop('samples');samples.append(current_samples)
  if not baseline:
   max_error=0;changed=0;interior=0
   for old_case,new_case,old_points,new_points in zip(reports[0]['cases'],report['cases'],samples[0],samples[1]):
    assert old_case==new_case,(old_case,new_case)
    for a,b in zip(old_points,new_points):
     t=max(0,min(1,b['edge']/4));fade=t*t*(3-2*t)
     assert all(a[k]==b[k] for k in ['x','z','edge','emptyColor','emptyWeights','emptyWet'])
     for key,empty in [('color','emptyColor'),('weights','emptyWeights')]:
      expected=[v+(w-v)*fade for v,w in zip(a[empty],a[key])]
      max_error=max(max_error,*[abs(v-w) for v,w in zip(expected,b[key])])
     max_error=max(max_error,abs(b['wet']-a['wet']*fade))
     if b['edge']>=4:
      assert a==b,(new_case['key'],a,b)
      interior+=1
     if a!=b:changed+=1
   assert max_error<2e-7,max_error;assert changed>0
   for a,b in zip(reports[0]['chunks'],report['chunks']):
    assert all(a[k]==b[k] for k in ['key','kind','paths','interior','geometry','metadata','emptyBoundary']),(a['key'],b['key'])
    assert b['boundaryError']==0,(b['key'],b['boundaryError'])
   assert max(c['boundaryError'] for c in reports[0]['chunks'])>.7
   assert all(s['weights']<1e-6 for s in report['seams']),report['seams']
   report['reference']={'maxError':max_error,'changedEmittedVertices':changed,'unchangedInteriorVertices':interior}
  page.wait_for_function('__pathShader.uniforms.uPbr.value>.99')
  render=page.evaluate('''()=>{const {scene,cam}=__pathScene;game.ren.info.reset();game.post.render(scene,cam,0);return{calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,glError:game.ren.getContext().getError()}}''')
  assert render['glError']==0,render;assert not errors,errors
  page.screenshot(path=str(out/(label+'.png')));report['render']=render;report['errors']=errors
  for chunk in report['chunks']:chunk.pop('edges',None)
  (out/(label+'.json')).write_text(json.dumps(report,indent=2));reports.append(report)
  print(label,json.dumps({'seams':report['seams'],'render':render,'reference':report.get('reference')}),flush=True);browser.close()
 assert reports[0]['render']==reports[1]['render']
print('PASS 16 directional/width/negative-coordinate cases, 9 populated districts, exact geometry/metadata/RNG/interiors; JS0/GL0')
