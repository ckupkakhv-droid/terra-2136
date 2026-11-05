"""Common terrain edge lighting with exact native height and collision data.

Compare the actual published v0.4.29, the optional bypass, and the default fix.
Only source-grid normals have an analytic reference: metro clipping interpolates
extra vertices later. Final geometry and height fields are always compared.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='79232bcdf0c7a1f397fd01a14523fbf2e6bdddd8'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-edge-normals'));out.mkdir(exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-normal-baseline/terra-v29.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='d32757ff8f4d0827e0f86d48e34d11c686465ed20ef492b9dd534620c1582f9e'
reports=[]
with sync_playwright() as p:
 for mode in ['before','bypass','after']:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  if mode=='bypass':page.add_init_script('window.TERRA_ART={terrainEdgeNormalsEnabled:false}')
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1200]) if m.type=='error' else None)
  if mode=='before':page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.state==="play" && game.sewers && TERRA_KITS.ready')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async mode=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,result={cases:[],chunks:[]},chunks=new Map(),raws=new Map();
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   function flat(cx,cz,kind,axis=0){
    const c=new C(cx,cz);c.prep();const xs=c.T.xs,size=xs.length,ox=c.ox,oz=c.oz;
    for(let z=0;z<size;z++)for(let x=0;x<size;x++)c.T.hg[z*size+x]=c.T.hv[z*size+x]=.03*(ox+xs[x])-.02*(oz+xs[z]);
    c.T.riv.fill(0);c.T.rd.fill(100);c.T.wl.fill(-99);c.T.cls.fill(null);c.cols=[];c.paths=[];c.pads=[];c.ponds=[];c.d='outskirts';c.anc=1;c.setOY(0);
    if(kind==='pad'){
     const bounds=[[40,18,46.2,38],[1.8,18,8,38],[18,40,38,46.2],[18,1.8,38,8]][axis];
     c.pads=[{x0:ox+bounds[0],z0:oz+bounds[1],x1:ox+bounds[2],z1:oz+bounds[3],y:.03*(ox+24)-.02*(oz+24)+2,nc:true}];
    }else if(kind==='interior')c.pads=[{x0:ox+20,z0:oz+20,x1:ox+28,z1:oz+28,y:.03*(ox+24)-.02*(oz+24)+2,nc:true}];
    else if(kind==='pond'){const x=ox+(axis===0?43.4:30),z=oz+(axis===0?30:43.4);c.ponds=[[x,z,1.8,.03*x-.02*z-.6]];}
    const raw=c.T.hv.slice();c.terrain();return{c,raw};
   }
   function analyse(c,raw,enabled){
    const xs=c.T.xs,size=xs.length,points=new Map();let maxError=0,maxUnit=0,checked=0,interpolated=0;
    for(let i=0;i<c.tr.p.length;i+=3){const x=c.tr.p[i],z=c.tr.p[i+2],gx=xs.indexOf(x-c.ox),gz=xs.indexOf(z-c.oz),edge=Math.min(x-c.ox,c.ox+48-x,z-c.oz,c.oz+48-z);
     const actual=c.tr.n.slice(i,i+3);if(!actual.every(Number.isFinite))throw Error('Nonfinite terrain normal');
     if(gx<0||gz<0){interpolated++;continue}
     if(points.has(x+','+z))continue;
     // Independent divided differences use physical grid coordinates. The first
     // visible row has 1 m cells, so skip its +1 sample for the symmetric +/-2 stencil.
     const left=gx-1,right=gx===1?gx+2:gx+1,top=gz-1,bottom=gz===1?gz+2:gz+1;
     const gradient=h=>[-(h[gz*size+right]-h[gz*size+left])/(xs[right]-xs[left]),-(h[bottom*size+gx]-h[top*size+gx])/(xs[bottom]-xs[top])];
     const original=gradient(raw),local=gradient(c.T.hv),t=Math.max(0,Math.min(1,edge/4)),weight=t*t*(3-2*t),g=enabled&&edge<4?original.map((v,j)=>v+(local[j]-v)*weight):local;
     const expected=[g[0],1,g[1]],length=Math.hypot(...expected);
     maxError=Math.max(maxError,...actual.map((v,j)=>Math.abs(v-expected[j]/length)));maxUnit=Math.max(maxUnit,Math.abs(Math.hypot(...actual)-1));checked++;
     points.set(x+','+z,{p:c.tr.p.slice(i,i+3),n:actual,c:c.tr.c.slice(i,i+3),w:c.tr.ws.slice(i/3*8,i/3*8+8),a:c.tr.a.slice(i/3*2,i/3*2+2),edge});
    }
    return{points,maxError,maxUnit,checked,interpolated};
   }
   for(const [cx,cz]of[[1,1],[-2,-1]])for(const [kind,axis]of[['pad',0],['pad',1],['pad',2],['pad',3],['pond',0],['pond',1],['interior',0],['empty',0]]){
    const {c,raw}=flat(cx,cz,kind,axis),empty=flat(cx,cz,'empty').c,check=analyse(c,raw,mode==='after'),emptyEdge=new Map();
    for(let i=0;i<empty.tr.p.length;i+=3){const x=empty.tr.p[i],z=empty.tr.p[i+2];if(x===empty.ox||x===empty.ox+48||z===empty.oz||z===empty.oz+48)emptyEdge.set(x+','+z,[...empty.tr.n.slice(i,i+3),...empty.tr.c.slice(i,i+3),...empty.tr.ws.slice(i/3*8,i/3*8+8),...empty.tr.a.slice(i/3*2,i/3*2+2)]);}
    let boundaryError=0;const interior=[];
    for(const [key,p]of check.points){if(p.edge>=4)interior.push(p);if(p.edge===0){const ref=emptyEdge.get(key),value=[...p.n,...p.c,...p.w,...p.a];if(!ref)throw Error('Missing reference edge');boundaryError=Math.max(boundaryError,...value.map((v,i)=>Math.abs(v-ref[i])));}}
    const {points,...numbers}=check;
    result.cases.push({key:cx+','+cz+','+kind+','+axis,...numbers,boundaryError,
     geometry:await hash([c.tr.p,c.grid,c.T.hg,c.T.hv,c.T.wl,c.w.p,c.w.n,c.w.a]),paint:await hash([c.tr.n,c.tr.c,c.tr.ws,c.tr.a]),interior:await hash(interior),meta:await hash([Object.keys(c),c.pads,c.ponds,c.cols,c.r(),c.r()])});
   }
   for(const [cx,cz]of[[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]){
    const base=new C(cx,cz);base.prep();const c=new C(cx,cz);c.build();chunks.set(cx+','+cz,c);raws.set(cx+','+cz,base.T.hv);
    const check=analyse(c,base.T.hv,mode==='after'),interior=[],edges={};
    for(const [key,p]of check.points){if(p.edge>=4)interior.push(p);if(p.edge===0)edges[key]=p;}
    const {points,...numbers}=check;
    result.chunks.push({key:cx+','+cz,cx,cz,kind:c.d,pads:c.pads,ponds:c.ponds,...numbers,edges,
     geometry:await hash([c.tr.p,c.grid,c.T.hg,c.T.hv,c.T.wl,c.w.p,c.w.n,c.w.a]),paint:await hash([c.tr.n,c.tr.c,c.tr.ws,c.tr.a]),interior:await hash(interior),
     metadata:await hash({keys:Object.keys(c),cols:c.cols,conts:c.conts,nodes:c.nodes,brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})});
   }
   result.edges={height:0,normal:0,color:0,weights:0};let count=0;
   for(const a of result.chunks)for(const [dx,dz]of[[1,0],[0,1]]){
    const b=result.chunks.find(c=>c.cx===a.cx+dx&&c.cz===a.cz+dz);if(!b)continue;
    for(const [key,v]of Object.entries(a.edges)){const w=b.edges[key];if(!w)continue;count++;
     result.edges.height=Math.max(result.edges.height,Math.abs(v.p[1]-w.p[1]));
     for(const [name,field]of[['normal','n'],['color','c'],['weights','w']])result.edges[name]=Math.max(result.edges[name],...v[field].map((x,i)=>Math.abs(x-w[field][i])));
    }
   }result.edges.samples=count;
   const meshes=[...game.world.chunks.values()].flatMap(c=>c.meshes),source=meshes.find(m=>m.geometry?.attributes.w0)?.material;
   if(!source)throw Error('Native terrain material absent');
   const material=source.clone(),compile=source.onBeforeCompile;
   material.onBeforeCompile=function(shader,renderer){compile.call(this,shader,renderer);shader.uniforms.uRain={value:0};window.__edgeShader=shader};material.customProgramCacheKey=()=>source.customProgramCacheKey()+'-qa-edge-normal';
   const scene=new game.scene.constructor();scene.background=game.scene.background.clone();const hemi=game.hemi.clone();hemi.color.set('#ffffff');hemi.groundColor.set('#ffffff');hemi.intensity=.35;scene.add(hemi);
   const sun=game.sun.clone();sun.position.set(52,16,65);sun.target.position.set(70,0,48);sun.intensity=2;sun.castShadow=false;scene.add(sun,sun.target);
   for(const key of ['1,0','1,1'])scene.add(chunks.get(key).tr.mesh(material));
   const cam=game.cam.clone();cam.position.set(75,8,59);cam.lookAt(70,-.2,48);cam.zoom=1.65;cam.updateProjectionMatrix();
   game.ren.shadowMap.enabled=false;window.__edgeScene={scene,cam};game.post.render(scene,cam,0);return result;
  }''',mode)
  for chunk in report['chunks']:chunk.pop('edges')
  assert max(v['maxError'] for v in report['cases']+report['chunks'])<1e-6,(mode,report['cases'],report['chunks'])
  assert max(v['maxUnit'] for v in report['cases']+report['chunks'])<1e-6
  if mode=='bypass':
   assert report=={k:v for k,v in reports[0].items() if k not in ['render','errors']},'Bypass must exactly reproduce published v29 data'
  if mode=='after':
   assert report['edges']['normal']==report['edges']['weights']==report['edges']['height']==0,report['edges']
   assert reports[0]['edges']['normal']>.5 and reports[0]['edges']['weights']>.2
   for a,b in zip(reports[0]['cases'],report['cases']):
    assert all(a[k]==b[k] for k in ['key','geometry','interior','meta']),(a,b)
    assert b['boundaryError']<1e-6,b
    if ',interior,' in b['key'] or ',empty,' in b['key']:assert a['paint']==b['paint'],(a,b)
   for a,b in zip(reports[0]['chunks'],report['chunks']):
    assert all(a[k]==b[k] for k in ['key','kind','pads','ponds','geometry','interior','metadata']),(a['key'],b['key'])
    if not b['pads'] and not b['ponds']:assert a['paint']==b['paint'],(a['key'],b['key'])
  page.wait_for_function('__edgeShader.uniforms.uPbr.value>.99')
  render=page.evaluate('''()=>{game.ren.info.reset();game.post.render(__edgeScene.scene,__edgeScene.cam,0);return{calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,glError:game.ren.getContext().getError()}}''')
  assert render['glError']==0 and not errors,(render,errors)
  if reports:assert render==reports[0]['render']
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/(mode+'.png')))
  report['render']=render;report['errors']=errors
  (out/(mode+'.json')).write_text(json.dumps(report,indent=2));reports.append(report)
  print(mode,json.dumps({'edges':report['edges'],'referenceError':max(v['maxError'] for v in report['cases']+report['chunks']),'render':render}),flush=True);browser.close()
print('PASS published v29 / exact bypass / default: 16 controls, 9 populated chunks; original-grid analytic normals, exact heights/water/physics/metadata/RNG/interiors; JS0/GL0')
