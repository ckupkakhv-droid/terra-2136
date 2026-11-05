"""Container art: native metadata/RNG, instanced destruction/save, visual review.

Two disposable browser profiles compare the native geometry with its replacement.
Close-ups use the game's renderer/material under its own lights; the world shot
uses normal gameplay. TERRA_TEST_URL may also point at standalone terra.html.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-salvage-qa'));out.mkdir(exist_ok=True)
reports=[]
with sync_playwright() as p:
 for baseline in [True,False]:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(60000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'low',post:false,dpr:1}))")
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  if baseline:
   if '/terra.html' in url:
    # The optional hook and script must also have a clean disabled path offline.
    page.add_init_script("Object.defineProperty(window,'__salvageBaseline',{value:true})")
    # Inline the same reviewed standalone except this one classic source.
    source=Path(__file__).resolve().parents[1]/'terra.html'
    art=(source.parent/'play/art/salvage-props.js').read_text()
    html=source.read_text().replace(art.replace('</script','<\\/script'),'')
    assert html!=source.read_text(),'Offline baseline source not found'
    page.route('**/terra.html',lambda r:r.fulfill(body=html,content_type='text/html'))
   else:page.route('**/art/salvage-props.js',lambda r:r.fulfill(body='',content_type='application/javascript'))
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.sewers && game.state==="play" && game.brkM')
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,result={cases:[],chunks:[]};
   for(const q of ['low','high'])for(const kind of ['crate','army','chest','toolbox','sofa','wardrobe'])for(const angle of (['sofa','wardrobe'].includes(kind)?[0,Math.PI/2]:[0])) {
    const c=new C(1,1);c.prep();game.qk=q;
    const kit=TERRA_KITS,ready=kit.ready,failed=kit.failed;
    try {
     // Normal static crates already use native kit art; exercise the fallback
     // as well, without changing the kit's state for the world comparison.
     if(kind==='crate'||kind==='army'){kit.ready=false;kit.failed=true;}
     c[kind==='army'?'crate':kind](90,82,...(kind==='army'?['army']:['sofa','wardrobe'].includes(kind)?[angle]:[]));
    }finally{kit.ready=ready;kit.failed=failed;}
    const pos=c.s.p,norm=c.s.n,ys=pos.filter((_,i)=>i%3===1);
    let rayHeight=null;
    if(['sofa','wardrobe'].includes(kind)) {
     const mesh=c.s.mesh(game.brkM.crate.material),ray=new game.ray.constructor(),localX=kind==='sofa'?.88:0;
     mesh.updateMatrixWorld();ray.ray.origin.set(90+localX*Math.cos(angle),30,82-localX*Math.sin(angle));ray.ray.direction.set(0,-1,0);
     rayHeight=ray.intersectObject(mesh)[0]?.point.y-c.hAt(90,82);mesh.geometry.dispose();
    }
    result.cases.push({q,kind,angle,rayHeight,metadata:{cols:c.cols,conts:c.conts,next:[c.r(),c.r(),c.r()]},
     triangles:pos.length/9,finite:[...pos,...norm,...c.s.c].every(Number.isFinite),
     normals:norm.every((_,i)=>i%3||Math.abs(Math.hypot(...norm.slice(i,i+3))-1)<1e-5),
     top:Math.max(...ys)-c.hAt(90,82),plainVertices:c.s.m?.filter(v=>v===0).length||0});
   }
   game.qk='low';
   for(const [cx,cz] of [[0,0],[1,1],[2,1]]) {
    const c=new C(cx,cz);c.build();
    const data=JSON.stringify({cols:c.cols,conts:c.conts,nodes:c.nodes,ents:c.ents,brk:c.brk,
      spawns:c.spawns,pads:c.pads,next:[c.r(),c.r(),c.r()]});
    const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(data)))].map(v=>v.toString(16).padStart(2,'0')).join('');
    result.chunks.push({key:cx+','+cz,hash});
   }
   const geometry=game.brkM.crate.geometry;geometry.computeBoundingBox();
   result.dynamic={triangles:geometry.getAttribute('position').count/3,bounds:[geometry.boundingBox.min.toArray(),geometry.boundingBox.max.toArray()]};
   result.stats=window.TERRA_ART.salvage||null;return result;
  }''')
  reports.append(report)
  assert all(v['finite'] and v['normals'] for v in report['cases']),report
  if not baseline:
   assert report['stats']['replaced']>0 and report['stats']['breakable']==1 and report['stats']['fallback']==0,report
   for old,new in zip(reports[0]['cases'],report['cases']):
    assert new['metadata']==old['metadata'],(old,new)
    assert new['triangles']>old['triangles'] and new['triangles']<=600,(old,new)
    assert abs(new['top']-old['top'])<.25,(old,new)
    if new['kind']=='sofa':assert new['plainVertices']>0,'Fabric inherited a masonry texture'
    if new['kind'] in ['sofa','wardrobe']:
     assert abs(new['rayHeight']-(.735 if new['kind']=='sofa' else 2.07))<1e-5,('Missing outward-facing roof',new)
   assert report['chunks']==reports[0]['chunks'],report
   assert report['dynamic']['triangles']<=600
   assert abs(report['dynamic']['bounds'][0][1])<1e-6,'Crate base floats above its native anchor'
   key=page.evaluate('''()=>{
    const item=game.brkList().find(v=>v.kind==='crate');if(!item)throw Error('No native crate');
    const geometry=game.brkM.crate.geometry,before=game.brkList().length;
    game.hurtProp(item,1000);game.brkSync();
    if(!item.dead||item.col.h!==0||!game.world.broken.has(item.key)||game.brkList().length!==before-1||game.brkM.crate.geometry!==geometry)throw Error('Breakage changed');
    const save=game.save();if(!save?.ok)throw Error('Fixture save refused');return item.key;
   }''')
   page.reload(timeout=120000);page.locator('#mContinue').click()
   page.wait_for_function('key=>game.state==="play" && game.world.broken.has(key)',arg=key)
   page.evaluate('game.p.x=90;game.p.z=85;game.p.hp=game.p.maxHp=10000;game.camT=null')
   page.wait_for_timeout(6000);page.screenshot(path=str(out/'world.png'))
  # Freeze only the QA scene after gameplay/save checks, then render close-ups.
  page.evaluate('game.loop=function(){}');page.wait_for_timeout(100)
  view=page.evaluate('''()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,c=new C(1,1);c.prep();c.anc=1;c.setOY(0);
   const ready=TERRA_KITS.ready,failed=TERRA_KITS.failed;
   try{TERRA_KITS.ready=false;TERRA_KITS.failed=true;c.crate(87.8,82);c.crate(89.3,82,'army');}
   finally{TERRA_KITS.ready=ready;TERRA_KITS.failed=failed;}
   c.chest(91,82);c.toolbox(92.6,82);
   c.s.add(TERRA_SEWER_BRIDGE.shapes.box,90,-4,82,16,8,12,'#474a40',0,0,0,0);
   for(const node of game.scene.children)if(!node.isLight)node.visible=false;
   const mesh=c.s.mesh(game.brkM.crate.material);game.scene.add(mesh);
   const cam=game.cam.clone();cam.position.set(90,7,90);cam.lookAt(90,.3,82);cam.zoom=1.4;cam.updateProjectionMatrix();
   window.__salvageCamera=cam;game.ren.info.reset();game.post.render(game.scene,cam,0);
   return {calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles};
  }''')
  page.add_style_tag(content='body > :not(canvas) {visibility:hidden!important}')
  page.screenshot(path=str(out/('before.png' if baseline else 'after.png')))
  page.evaluate('''()=>{
   for(const node of game.scene.children)if(!node.isLight)node.visible=false;
   const c=new TERRA_SEWER_BRIDGE.Chunk(1,1);c.prep();c.anc=1;c.setOY(0);
   c.sofa(88.2,82,0);c.sofa(90.5,81.8,Math.PI/2);c.wardrobe(92.6,82,0);
   c.s.add(TERRA_SEWER_BRIDGE.shapes.box,90,-4,82,16,8,12,'#474a40',0,0,0,0);
   const material=[...game.world.chunks.values()].flatMap(c=>c.meshes).find(m=>m.geometry?.attributes.mt&&m.material?.vertexColors)?.material;
   if(!material)throw Error('Native static material not found');
   game.scene.add(c.s.mesh(material));
   __salvageCamera.position.set(90,6,90);__salvageCamera.lookAt(90,.65,82);__salvageCamera.zoom=1.4;__salvageCamera.updateProjectionMatrix();
   game.post.render(game.scene,__salvageCamera,0);
  }''')
  page.screenshot(path=str(out/('furniture-before.png' if baseline else 'furniture-after.png')))
  if not baseline:
   page.set_viewport_size({'width':390,'height':844})
   page.evaluate('game.resize();__salvageCamera.aspect=390/844;__salvageCamera.zoom=.9;__salvageCamera.updateProjectionMatrix();game.post.render(game.scene,__salvageCamera,0)')
   page.screenshot(path=str(out/'portrait.png'))
  assert not errors,errors
  (out/('baseline.json' if baseline else 'updated.json')).write_text(json.dumps(report,indent=2))
  print(('BASELINE' if baseline else 'UPDATED'),[(v['q'],v['kind'],v['triangles']) for v in report['cases']],report['dynamic'],report['stats'],view,flush=True)
  browser.close()
print('PASS native metadata/RNG, 3 chunks, low/high geometry budget, instanced breakage/save/reload, visual captures; JS0')
