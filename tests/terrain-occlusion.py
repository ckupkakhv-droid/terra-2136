"""Check native AO against all eligible colliders, independently of its index.

Published 0.4.27 is the baseline. Set TERRA_BASELINE_FILE to its standalone HTML
when testing an offline build. No object, terrain geometry or gameplay rule
changes: only colours previously missing the native 1.6 m occlusion may differ.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='0216c60711208a2733d5f422779b3f0342e00694'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-terrain-occlusion'));out.mkdir(exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-ao-baseline/terra-v27.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='a83d7d1e2c7111855803ac54561d81fa1c48b4f31380ed52b0a35c633407a87e'
reports=[];reference=[];reference_points=[]
with sync_playwright() as p:
 for baseline in [True,False]:
  label='before' if baseline else 'after'
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1400]) if m.type=='error' else None)
  if baseline:page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.sewers && game.state==="play" && TERRA_KITS.ready')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async baseline=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,result={cases:[],chunks:[],colours:[],points:[],colliders:[]};
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   function ao(cols,x,z,ox,oz,indexed=false) {
    let shade=1;const gx=Math.floor((x-ox)/4),gz=Math.floor((z-oz)/4);
    for(const c of cols) {
     if(c.h<1)continue;
     if(indexed&&(gx<Math.floor((c.x0-ox)/4)||gx>Math.floor((c.x1-ox)/4)||gz<Math.floor((c.z0-oz)/4)||gz>Math.floor((c.z1-oz)/4)))continue;
     const distance=Math.hypot(Math.max(c.x0-x,0,x-c.x1),Math.max(c.z0-z,0,z-c.z1));
     if(distance<1.6){const t=distance/1.6;shade=Math.min(shade,.45+.55*t*t*(3-2*t));}
    }return shade;
   }
   function flat(cx,cz,cols) {
    const c=new C(cx,cz);c.prep();c.T.hg.fill(0);c.T.hv.fill(0);c.T.riv.fill(0);c.T.rd.fill(100);c.T.wl.fill(-99);c.T.cls.fill(null);
    c.pads=[];c.paths=[];c.ponds=[];c.d='outskirts';c.anc=1;c.setOY(0);c.cols.push(...cols);c.terrain();return c;
   }
   for(const [cx,cz] of [[1,1],[-2,-1]])for(let kind=0;kind<4;kind++) {
    const ox=cx*48,oz=cz*48,empty=flat(cx,cz,[]),
      shapes=[{x0:33.5,x1:35.5,z0:32,z1:40,h:2},{x0:32,x1:40,z0:33.5,z1:35.5,h:2},
              {x0:35.4,x1:35.6,z0:35.4,z1:35.6,h:3},{x0:33.5,x1:35.5,z0:32,z1:40,h:.7}],
      box=shapes[kind],cols=[{...box,x0:box.x0+ox,x1:box.x1+ox,z0:box.z0+oz,z1:box.z1+oz}],c=flat(cx,cz,cols);
    let maxError=0,wrong=0,count=0;
    for(let i=0;i<c.tr.p.length;i+=3) {
     const x=c.tr.p[i],z=c.tr.p[i+2],expected=ao(cols,x,z,ox,oz),ratio=c.tr.c[i]/empty.tr.c[i],error=Math.abs(ratio-expected);
     maxError=Math.max(maxError,error);if(error>1e-6)wrong++;if(expected<1)count++;
    }
    result.cases.push({key:cx+','+cz+','+kind,maxError,wrong,count,
     geometry:await hash([c.tr.p,c.tr.n,c.tr.ws,c.tr.a,c.grid,c.w.p,c.w.a]),
     meta:await hash([c.cols,c.r(),c.r(),c.r()])});
   }
   const terrain=C.prototype.terrain,edgeData=new Map();
   C.prototype.terrain=function(...args){
    this.__qaCols=this.cols.map(c=>({x0:c.x0,x1:c.x1,z0:c.z0,z1:c.z1,h:c.h}));
    // The installed terrain method already wraps metro clipping. Capture the
    // native emitted samples before that wrapper interpolates new vertices.
    const builder=this.tr,tri=builder.tri,own=Object.hasOwn(builder,'tri'),samples={p:[],c:[]};
    builder.tri=function(...a){samples.p.push(...a.slice(0,9));samples.c.push(...a[12],...a[13],...a[14]);return tri.apply(this,a)};
    try{const value=terrain.apply(this,args);this.__qaTerrain=samples;return value}
    finally{if(own)builder.tri=tri;else delete builder.tri;}
   };
   try {
    for(const [cx,cz] of [[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]) {
     const c=new C(cx,cz);c.build();let missing=0;const colours=[],points=[],edges=new Map();
     const raw=c.__qaTerrain;
     for(let i=0;i<raw.p.length;i+=3) {
      const x=raw.p[i],z=raw.p[i+2],full=ao(c.__qaCols,x,z,c.ox,c.oz),indexed=ao(c.__qaCols,x,z,c.ox,c.oz,true);
      if(indexed-full>1e-6)missing++;
      points.push([x,z,indexed,full,...raw.c.slice(i,i+3)]);
      for(let j=0;j<3;j++)colours.push(raw.c[i+j]*(baseline?full/indexed:1));
     }
     for(let i=0;i<c.tr.p.length;i+=3) {
      const x=c.tr.p[i],z=c.tr.p[i+2];
      if(x===c.ox||x===c.ox+48||z===c.oz||z===c.oz+48)edges.set(x+','+z,[c.tr.p[i+1],...c.tr.c.slice(i,i+3),...c.tr.ws.slice(i/3*8,i/3*8+8)]);
     }
     edgeData.set(cx+','+cz,{cx,cz,edges});result.colours.push(colours);result.points.push(points);result.colliders.push(c.__qaCols);
     result.chunks.push({key:cx+','+cz,missing,
      geometry:await hash([c.tr.p,c.tr.n,c.tr.ws,c.tr.a,c.grid,c.w.p,c.w.a]),
      meta:await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})});
    }
   }finally{C.prototype.terrain=terrain;}
   result.edges={height:0,color:0,weights:0};
   for(const a of edgeData.values())for(const [dx,dz] of [[1,0],[0,1]]) {
    const b=edgeData.get((a.cx+dx)+','+(a.cz+dz));if(!b)continue;
    for(const [key,v] of a.edges){const w=b.edges.get(key);if(!w)continue;
     result.edges.height=Math.max(result.edges.height,Math.abs(v[0]-w[0]));
     result.edges.color=Math.max(result.edges.color,...v.slice(1,4).map((x,i)=>Math.abs(x-w[i+1])));
     result.edges.weights=Math.max(result.edges.weights,...v.slice(4).map((x,i)=>Math.abs(x-w[i+4])));
    }
   }
   // A native wardrobe shows contact with the ground without a new game prop.
   const c=flat(1,1,[]);c.tr=new c.tr.constructor();c.wardrobe(82.5,84,0);c.terrain();
   const meshes=[...game.world.chunks.values()].flatMap(c=>c.meshes),terrainMat=meshes.find(m=>m.geometry?.attributes.w0)?.material,
    stat=meshes.find(m=>m.geometry?.attributes.mt&&m.material?.vertexColors)?.material;
   if(!terrainMat||!stat)throw Error('Native terrain materials absent');
   const material=terrainMat.clone(),compile=terrainMat.onBeforeCompile;
   material.onBeforeCompile=function(shader,renderer){compile.call(this,shader,renderer);shader.uniforms.uRain={value:0};window.__aoShader=shader};
   material.customProgramCacheKey=()=>terrainMat.customProgramCacheKey()+'-qa-contact';
   const scene=new game.scene.constructor();scene.background=game.scene.background.clone();const hemi=game.hemi.clone();
   hemi.color.set('#ffffff');hemi.groundColor.set('#ffffff');hemi.intensity=1;scene.add(hemi);
   scene.add(c.tr.mesh(material),c.s.mesh(stat));const cam=game.cam.clone();cam.position.set(88,5,91);cam.lookAt(83,.5,84);cam.zoom=1.8;cam.updateProjectionMatrix();
   game.ren.shadowMap.enabled=false;window.__ao={scene,cam};game.post.render(scene,cam,0);return result;
  }''',baseline)
  colours=report.pop('colours');points=report.pop('points');colliders=report.pop('colliders')
  if baseline:
   assert max(c['maxError'] for c in report['cases'])>.1;reference=colours;reference_points=points
  else:
   assert max(c['maxError'] for c in report['cases'])<1e-6,report['cases']
   for old,new in zip(reports[0]['cases'],report['cases']):assert new['geometry']==old['geometry'] and new['meta']==old['meta']
   for old,new in zip(reports[0]['chunks'],report['chunks']):assert new==old,(old,new)
   error=max(abs(a-b) for old,new in zip(reference,colours) for a,b in zip(old,new))
   if error>=1e-6:
    worst=max((abs(a-b),i,j) for i,(old,new) in enumerate(zip(reference,colours)) for j,(a,b) in enumerate(zip(old,new)))
    _,i,j=worst;x,z=points[i][j//3][:2]
    near=[c for c in colliders[i] if max(c['x0']-x,0,x-c['x1'])**2+max(c['z0']-z,0,z-c['z1'])**2<1.61**2]
    print('Reference mismatch',report['chunks'][i]['key'],reference_points[i][j//3],points[i][j//3],near,flush=True)
   assert error<1e-6,error;report['fullReferenceError']=error
  page.wait_for_function('__aoShader.uniforms.uPbr.value>.99')
  render=page.evaluate('''()=>{game.ren.info.reset();game.post.render(__ao.scene,__ao.cam,0);return {calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,error:game.ren.getContext().getError()}}''')
  assert render['error']==0 and not errors,errors
  if not baseline:assert render==reports[0]['render']
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}');page.screenshot(path=str(out/(label+'.png')))
  report.update(render=render,errors=errors);reports.append(report);(out/(label+'.json')).write_text(json.dumps(report,indent=2))
  print(label,'max AO error',max(c['maxError'] for c in report['cases']),'native missing vertices',sum(c['missing'] for c in report['chunks']),'render',render,'edges',report['edges'],'JS0',flush=True);browser.close()
print('PASS native AO radius on positive/negative grids, 9 actual chunks/full collider reference, geometry/water/metadata/RNG unchanged, same draw count, JS0/GL0')
