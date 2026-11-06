"""Compare the published kiosk and shipped replacement in the native renderer.

TERRA_TEST_URL accepts play/ or standalone terra.html served over HTTP.
The published baseline routes its own HTML, manifest and KIT archive together.
"""
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='5f64bb12451c08830c63c1fee03a8b9e9858cd9f'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-kiosk-qa'));out.mkdir(parents=True,exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-kiosk-baseline/terra-v34.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='0d6e3a6185459ea177f0b8f711422a6b509fba9fca4da20b0ab11244a332ef43'
reports=[]
with sync_playwright() as pw:
 for label in ['before','after']:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(120000);errors=[]
  page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1000]) if m.type=='error' else None)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  if label=='before':
   page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
   if not offline:
    for path in ['manifest.json','TERRA_KIT.json.gz']:
     content=subprocess.check_output(['git','show',BASE+':play/assets/pack/'+path],cwd=ROOT)
     page.route('**/assets/pack/'+path+'*',lambda r,request,content=content:r.fulfill(body=content,content_type='application/octet-stream'))
  page.goto(url,timeout=120000);page.wait_for_function('window.game && game.sewers && TERRA_KITS.ready')
  page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play"')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async()=>{
   const g=game,C=TERRA_SEWER_BRIDGE.Chunk,result={chunks:[],entries:{},kiosk:[],renders:[]};
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',v))].map(v=>v.toString(16).padStart(2,'0')).join('');
   const jsonHash=v=>hash(new TextEncoder().encode(JSON.stringify(v)));
   // Hash the exact view, not the shared backing buffer used by index arrays.
   for(const [name,entry] of Object.entries(TERRA_KITS.P)){
    const data={...entry,lods:[]};for(const lod of entry.lods){const attrs={};for(const key of ['p','n','uv','i']){const a=lod[key];attrs[key]=await hash(new Uint8Array(a.buffer,a.byteOffset,a.byteLength));}data.lods.push(attrs);}
    result.entries[name]=data;
   }
   for(const [x,z] of [[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]){
    const c=new C(x,z);c.build();result.chunks.push({key:x+','+z,hash:await jsonHash({cols:c.cols,conts:c.conts,nodes:c.nodes,brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})});
   }
   const c=new C(0,0);c.prep();if(!c.kp_('kiosk',0,0,0,1,{y:0,sink:0,tint:1}))throw Error('Native kiosk unavailable');
   const meshes=c.kb.decor.map(m=>m.mesh(TERRA_KITS.mats.decor));
   for(let lod=0;lod<3;lod++){
    const mesh=meshes[lod];mesh.geometry.computeBoundingBox();mesh.updateMatrixWorld(true);
    const box=mesh.geometry.boundingBox,ray=new g.ray.constructor();ray.ray.origin.set(6,1.90,.30);ray.ray.direction.set(-1,0,0);
    const side=ray.intersectObject(mesh).map(x=>x.distance);ray.ray.origin.set(0,1.90,6);ray.ray.direction.set(0,0,-1);
    const front=ray.intersectObject(mesh).map(x=>x.distance);
    result.kiosk.push({lod,vertices:mesh.geometry.attributes.position.count,triangles:mesh.geometry.index.count/3,min:box.min.toArray(),max:box.max.toArray(),side,front,finite:mesh.geometry.attributes.position.array.every(Number.isFinite)&&mesh.geometry.attributes.normal.array.every(Number.isFinite)});
   }
   const scene=new g.scene.constructor();scene.background=g.scene.background.clone();scene.add(g.hemi.clone());
   const sun=g.sun.clone();sun.position.set(-4,6,5);sun.target.position.set(0,1.5,0);sun.intensity=2.2;sun.castShadow=false;scene.add(sun,sun.target,...meshes);
   const cam=g.cam.clone();cam.zoom=1;cam.updateProjectionMatrix();window.__kiosk={scene,cam,meshes};
   return result;
  }''')
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  for lod in range(3):
   for name,pos in [('front',[5,3.4,6]),('rear',[-5,3.4,-6]),('side',[7,2.5,.3])]:
    frame=page.evaluate('''a=>{const v=__kiosk;v.meshes.forEach((m,i)=>m.visible=i===a.lod);v.cam.position.set(...a.pos);v.cam.lookAt(0,1.5,0);game.ren.info.reset();game.ren.render(v.scene,v.cam);return{lod:a.lod,angle:a.name,calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,gl:game.ren.getContext().getError()}}''',{'lod':lod,'pos':pos,'name':name})
    assert frame['calls']==1 and frame['gl']==0,frame
    report['renders'].append(frame);page.screenshot(path=str(out/(label+'-'+str(lod)+'-'+name+'.png')))
  report['world']=page.evaluate('''()=>{const g=game;g.p.x=140;g.p.z=14;g.p.yaw=0;g.world.update(140,14,true);g.dayT=11;g.lighting(0);g.heroPose(0);const h=TERRA_H(137,13);g.cam.position.set(143,h+6,20);g.cam.lookAt(137,h+1.2,13);g.cam.zoom=1;g.cam.updateProjectionMatrix();g.ren.info.reset();g.renderT();return{height:h,calls:g.ren.info.render.calls,triangles:g.ren.info.render.triangles,gl:g.ren.getContext().getError()}}''')
  page.screenshot(path=str(out/(label+'-world.png')))
  assert report['world']['gl']==0
  if label=='after':
   assert report['chunks']==reports[0]['chunks'],'World collisions/containers/loot/entries/terrain/RNG changed'
   assert report['entries'].keys()==reports[0]['entries'].keys()
   for name,entry in report['entries'].items():
    if name!='kiosk':assert entry==reports[0]['entries'][name],('Unrelated native asset changed',name)
   for key in report['entries']['kiosk']:
    if key!='lods':assert report['entries']['kiosk'][key]==reports[0]['entries']['kiosk'][key],key
   for entry in report['kiosk']:
    assert entry['finite'] and not entry['side'],'Window should remain open across LODs'
    assert entry['front'] and 6.7<min(entry['front'])<7.1,'Ray should pass sales window and hit rear sheet'
    assert abs(entry['min'][1])<1e-6 and abs(entry['max'][1]-3.5)<1e-6,'LOD base or top changed'
    assert entry['triangles']<reports[0]['kiosk'][entry['lod']]['triangles']
   assert report['kiosk'][0]['min']==report['kiosk'][1]['min']==report['kiosk'][2]['min']
   assert report['kiosk'][0]['max']==report['kiosk'][1]['max']==report['kiosk'][2]['max']
  assert not errors,errors
  report['errors']=errors;(out/(label+'.json')).write_text(json.dumps(report,indent=2));reports.append(report)
  print(label,'PASS',report['kiosk'],'JS0/GL0',flush=True);browser.close()
print('PASS native packed asset, all unrelated decoded attributes exact, nine chunks/RNG/collisions unchanged; three LODs/base/bounds/windows, one call per isolated model, lower triangles, JS0/GL0')
