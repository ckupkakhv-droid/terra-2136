"""Native world load order, shared AO, clipped triangles and bounded teardown.

Use published v0.4.30 as the independent baseline. Reference AO traverses all
eligible colliders; interpolated metro vertices use generic triangle barycentrics.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='54b1c7d9692b3943e52be17ea0da9ebf7c73e7ff'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-shared-contact'));out.mkdir(exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-shared-contact-baseline/terra-v30.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='0c725b9ca28dd6cddfb469392eeb0f82e16b444e462f3bd4d9cc1f78d6db1ba0'
reports=[]
with sync_playwright() as p:
 for mode in ['before','bypass','after']:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(120000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  if mode=='bypass':page.add_init_script('window.TERRA_ART={terrainContactEnabled:false}')
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1400]) if m.type in ['error','warning'] else None)
  if mode=='before':page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.state==="play" && game.sewers && TERRA_KITS.ready')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  initial=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,W=game.world.constructor,coords=[[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]],captures=new Map(),terrain=C.prototype.terrain;
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   const key=(x,z)=>x+','+z;
   function shade(boxes,x,z){let a=1;for(const b of boxes){if(b.h<1)continue;const d=Math.hypot(Math.max(b.x0-x,0,x-b.x1),Math.max(b.z0-z,0,z-b.z1));if(d<1.6){let t=d/1.6;t=t*t*(3-2*t);a=Math.min(a,.45+.55*t)}}return a}
   C.prototype.terrain=function(...args){
    const b=this.tr,tri=b.tri,own=Object.hasOwn(b,'tri'),points=[],lookup=new Map(),triangles=[],cols=this.cols.map(b=>({x0:b.x0,x1:b.x1,z0:b.z0,z1:b.z1,h:b.h}));
    b.tri=function(...a){for(let i=0;i<3;i++){const p=a.slice(i*3,i*3+3),k=key(p[0],p[2]);let id=lookup.get(k);if(id===undefined){id=points.length;lookup.set(k,id);points.push({p,c:[...a[12+i]]})}triangles.push(id)}return tri.apply(this,a)};
    try{const r=terrain.apply(this,args);captures.set(key(this.cx,this.cz),{builder:this,cols,points,lookup,triangles});return r}
    finally{if(own)b.tri=tri;else delete b.tri;}
   };
   function world(){const w=new W(new game.scene.constructor()),calls={built:0,unload:0,allow:true},seen=new WeakSet(),onBuilt=r=>{calls.built++;seen.add(r)},onUnload=()=>{calls.unload++;return calls.allow};w.onSurfaceBuilt=onBuilt;w.onSurfaceBeforeUnload=onUnload;return{w,calls,onBuilt,onUnload,seen}}
   function mesh(r){const m=r.meshes.filter(m=>m.geometry?.getAttribute('w0'));if(m.length!==1)throw Error('Native terrain mesh absent');return m[0]}
   async function build(ctx,x,z){const r=ctx.w.build(x,z),cap=captures.get(key(x,z)),c=cap.builder;cap.next=[c.r(),c.r(),c.r()];
    cap.physical=await hash([c.tr.p,c.tr.n,c.tr.ws,c.tr.a,c.grid,c.T.hg,c.T.hv,c.T.wl,c.w.p,c.w.n,c.w.a]);cap.nativePaint=await hash(c.tr.c);
    cap.meta=await hash({cols:r.cols.map(b=>[b.x0,b.x1,b.z0,b.z1,b.h,b.water,b.cliff]),conts:r.conts.map(v=>[v.x,v.z,v.key,v.looted,v.items]),nodes:r.nodes.map(v=>[v.x,v.z,v.key,v.kind,v.used]),spawns:r.spawns,map:r.map,doors:r.doors.map(v=>[v.key,v.x,v.z,v.open,v.col.h]),brk:r.brk.map(v=>[v.key,v.kind,v.x,v.z,v.dead,v.col.h]),ents:r.ents.map(v=>[v.x,v.z,v.kind,v.name]),d:r.d,tier:r.tier,tps:r.tps,hz:r.hz,next:cap.next});return r;}
   function expected(cap,x,y,z,boxes){
    const id=cap.lookup.get(key(x,z));
    const colour=p=>p.c.map(v=>v*shade(boxes,p.p[0],p.p[2])/shade(cap.cols,p.p[0],p.p[2]));
    if(id!==undefined)return{colour:colour(cap.points[id]),clipped:false};
    for(let i=0;i<cap.triangles.length;i+=3){const p=cap.triangles.slice(i,i+3).map(id=>cap.points[id]),[a,b,c]=p.map(v=>v.p),cross=(a,b,c)=>(b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]),point=[x,y,z],area=cross(a,b,c),weights=[cross(b,c,point)/area,cross(c,a,point)/area,cross(a,b,point)/area];
     if(weights.some(v=>v< -1e-8||v>1+1e-8)||Math.abs(p.reduce((sum,v,j)=>sum+v.p[1]*weights[j],0)-y)>1e-6)continue;
     const colors=p.map(colour);return{colour:[0,1,2].map(k=>colors.reduce((sum,v,j)=>sum+v[k]*weights[j],0)),clipped:true};
    }throw Error('Rendered point is outside original native triangles: '+x+','+z);
   }
   async function snapshot(ctx){
    const {w}=ctx,boxes=[...w.chunks.keys()].flatMap(k=>captures.get(k)?.cols||[]),chunks=[],edges=new Map();let error=0,changed=0,clipped=0,checked=0;
    for(const [k,r]of [...w.chunks].sort(([a],[b])=>a.localeCompare(b))){const cap=captures.get(k),c=cap.builder,m=mesh(r),g=m.geometry,colour=g.getAttribute('color').array;
     for(let i=0;i<c.tr.p.length;i+=3){const x=c.tr.p[i],y=c.tr.p[i+1],z=c.tr.p[i+2],ref=expected(cap,x,y,z,boxes);checked++;if(ref.clipped)clipped++;
      error=Math.max(error,...ref.colour.map((v,j)=>Math.abs(v-colour[i+j])));
      if(colour.slice(i,i+3).some((v,j)=>v!==Math.fround(c.tr.c[i+j])))changed++;
      if(x===c.ox||x===c.ox+48||z===c.oz||z===c.oz+48){let values=edges.get(key(x,z));if(!values)edges.set(key(x,z),values=[]);values.push([...colour.slice(i,i+3)]);}
     }
     chunks.push({key:k,physical:cap.physical,nativePaint:await hash(c.tr.c),metadata:cap.meta,renderPhysical:await hash(['position','normal','aux','w0','w1'].map(n=>Array.from(g.getAttribute(n).array))),colour:await hash(Array.from(colour))});
    }
    let edgeJump=0;for(const values of edges.values()){const first=values[0];for(const c of values)edgeJump=Math.max(edgeJump,...c.map((v,j)=>Math.abs(v-first[j])));}
    const receiver=w.chunks.get('0,1');let target=null;
    if(receiver){const c=captures.get('0,1').builder,index=c.tr.p.findIndex((v,i)=>i%3===0&&v===0&&c.tr.p[i+2]===62);target=[...mesh(receiver).geometry.getAttribute('color').array.slice(index,index+3)];}
    return{chunks,maxReferenceError:error,changedVertices:changed,clippedVertices:clipped,checked,edgeJump,target,hookIdentity:w.onSurfaceBuilt===ctx.onBuilt&&w.onSurfaceBeforeUnload===ctx.onUnload};
   }
   const stats=w=>TERRA_ART.terrainContact?.inspect(w)||{chunks:0,buckets:0,boxes:0,typedBytes:0,vertices:0,interpolated:0,pendingRanges:0};
   const ctx=world();for(const [x,z]of coords)await build(ctx,x,z);
   const initial=await snapshot(ctx),initialStats=stats(ctx.w);
   const scene=new game.scene.constructor();scene.background=game.scene.background.clone();const hemi=game.hemi.clone();hemi.color.set('#ffffff');hemi.groundColor.set('#ffffff');hemi.intensity=1;scene.add(hemi);
   const source=mesh(ctx.w.chunks.get('0,1')).material,material=source.clone(),compile=source.onBeforeCompile;
   material.onBeforeCompile=function(shader,renderer){compile.call(this,shader,renderer);shader.uniforms.uRain={value:0};window.__sharedShader=shader};material.customProgramCacheKey=()=>source.customProgramCacheKey()+'-qa-shared-contact';
   for(const k of ['-1,1','0,1']){const m=mesh(ctx.w.chunks.get(k)).clone();m.material=material;scene.add(m);}
   const cam=game.cam.clone();cam.position.set(4,5,69);cam.lookAt(0,-3.7,62);cam.zoom=2.3;cam.updateProjectionMatrix();game.ren.shadowMap.enabled=false;
   window.__sharedPhoto={scene,cam};game.post.render(scene,cam,0);
   window.__sharedQA={async finish(mode){
    const report={initial,initialStats};
    if(mode!=='bypass'){
     const provider=ctx.w.chunks.get('-1,1');ctx.calls.allow=false;const stopped=ctx.w.unload(provider);report.blocked={stopped,stats:stats(ctx.w),same:JSON.stringify((await snapshot(ctx)).chunks)===JSON.stringify(initial.chunks)};
     ctx.calls.allow=true;ctx.w.unload(provider);report.unloaded=await snapshot(ctx);report.unloadedStats=stats(ctx.w);
     for(let cycle=0;cycle<3;cycle++){if(cycle)ctx.w.unload(ctx.w.chunks.get('-1,1'));await build(ctx,-1,1);}
     report.restored=await snapshot(ctx);report.restoredStats=stats(ctx.w);
    }
    for(const r of [...ctx.w.chunks.values()])ctx.w.discardChunk(r);
    report.cleanup={stats:stats(ctx.w),chunks:ctx.w.chunks.size,meshes:ctx.w.scene.children.length};report.calls=ctx.calls;
    if(mode!=='bypass'){
     const reverse=world();for(const [x,z]of [...coords].reverse())await build(reverse,x,z);report.reverse=await snapshot(reverse);report.reverseStats=stats(reverse.w);
     for(const r of [...reverse.w.chunks.values()])reverse.w.discardChunk(r);
     report.reverseCleanup={stats:stats(reverse.w),chunks:reverse.w.chunks.size,meshes:reverse.w.scene.children.length};
    }
    C.prototype.terrain=terrain;report.fallback=TERRA_ART.terrainContact?.totals.fallback||0;return report;
   }};return{edgeJump:initial.edgeJump,referenceError:initial.maxReferenceError,stats:initialStats};
  }''')
  print(mode,'initial',json.dumps(initial),flush=True)
  page.wait_for_function('__sharedShader.uniforms.uPbr.value>.99')
  render=page.evaluate('''()=>{game.ren.info.reset();game.post.render(__sharedPhoto.scene,__sharedPhoto.cam,0);return{calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,glError:game.ren.getContext().getError()}}''')
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/(mode+'.png')))
  report=page.evaluate('(mode)=>__sharedQA.finish(mode)',mode);report['render']=render;report['errors']=errors
  assert render['glError']==0 and not errors and report['fallback']==0,(render,errors,report['fallback'])
  assert report['initial']['hookIdentity']
  for name in ['cleanup','reverseCleanup']:
   if name in report:assert all(v==0 for v in report[name]['stats'].values()) and report[name]['chunks']==report[name]['meshes']==0,report[name]
  if mode!='bypass':
   assert report['blocked']['stopped'] is False and report['blocked']['same']
   assert report['initial']['chunks']==report['restored']['chunks']==report['reverse']['chunks'],'Load order or unload/rebuild changed native world data or colour'
   stable=lambda stats:{k:v for k,v in stats.items() if k!='pendingRanges'}
   assert stable(report['initialStats'])==stable(report['restoredStats'])==stable(report['reverseStats']),'Metadata grew'
   assert all(report[name]['pendingRanges']<=report[name]['chunks'] for name in ['initialStats','restoredStats','reverseStats'])
  if mode in ['before','bypass']:
   assert report['initial']['edgeJump']>.02 and report['initial']['maxReferenceError']>.02
   assert report['initial']['changedVertices']==0
  if mode=='bypass':assert report['initial']==reports[0]['initial'] and report['render']==reports[0]['render']
  if mode=='after':
   for case in ['initial','unloaded','restored','reverse']:
    assert report[case]['maxReferenceError']<2e-7 and report[case]['edgeJump']<2e-7,(case,report[case])
   assert report['initial']['changedVertices']>0 and report['initialStats']['chunks']==9 and report['unloadedStats']['chunks']==8
   assert report['initialStats']['pendingRanges']<=report['initialStats']['chunks']
   for a,b in zip(reports[0]['initial']['chunks'],report['initial']['chunks']):assert all(a[k]==b[k] for k in ['key','physical','nativePaint','metadata','renderPhysical']),(a,b)
   assert report['render']==reports[0]['render']
  (out/(mode+'.json')).write_text(json.dumps(report,indent=2));reports.append(report)
  print(mode,'PASS',json.dumps({'edgeJump':report['initial']['edgeJump'],'reference':report['initial']['maxReferenceError'],'changed':report['initial']['changedVertices'],'stats':report['initialStats'],'render':render}),flush=True);browser.close()
print('PASS actual native World: published30/bypass/default, both load orders, guarded unload, three rebuild cycles, reference AO + clipped interpolation, exact physical/native data, bounded metadata, JS0/GL0')
