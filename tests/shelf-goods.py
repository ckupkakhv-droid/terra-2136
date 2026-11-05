"""Compare shelf geometry with native occupancy, carcass, loot and seeded draws.

The optional art module is disabled in the baseline; the rest of the game and
assets are identical. TERRA_TEST_URL also accepts the standalone HTTP build.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-shelf-qa'));out.mkdir(exist_ok=True)
reports=[]
with sync_playwright() as p:
 for baseline in [True,False]:
  label='before' if baseline else 'after'
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  if baseline:page.add_init_script('window.TERRA_ART={shelvesEnabled:false}')
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1200]) if m.type=='error' else None)
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.sewers && game.state==="play"')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,result={cases:[],chunks:[]},keys=['p','n','c','a','m','uv'];
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   for(const q of ['low','high'])for(const width of [1,3,5])for(const angle of [0,Math.PI/2,-.4]) {
    game.qk=q;const c=new C(1,1);c.prep();c.anc=1;c.setOY(3.25);
    const add=c.s.add,goods=[];c.s.add=function(...a){
     if(a[0]===TERRA_SEWER_BRIDGE.shapes.box&&a[4]===.35&&a[5]===.3&&a[6]===.5)goods.push({x:a[1],y:a[2]+this.Y(a[1],a[3]),z:a[3],angle:a[8],color:a[7]});
     return add.apply(this,a);
    };
    c.shelf(90,82,angle,width,width!==1);delete c.s.add;
    const vertices=c.s.p.length/3,carcass=Object.fromEntries(keys.filter(k=>c.s[k]).map(k=>[k,c.s[k].slice(0,252*(k==='p'||k==='n'||k==='c'?3:k==='m'?1:2))]));
    let winding=true,normals=true,inside=true;
    for(let i=0;i<c.s.p.length;i+=9) {
     const a=c.s.p.slice(i,i+3),b=c.s.p.slice(i+3,i+6),d=c.s.p.slice(i+6,i+9),n=c.s.n.slice(i,i+3),
       u=b.map((v,k)=>v-a[k]),v=d.map((w,k)=>w-a[k]),cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
     if(cross.reduce((s,v,k)=>s+v*n[k],0)<=1e-10)winding=false;
    }
    for(let i=0;i<c.s.n.length;i+=3)if(Math.abs(Math.hypot(...c.s.n.slice(i,i+3))-1)>1e-5)normals=false;
    for(let i=756;i<c.s.p.length;i+=3) {
     const [x,y,z]=c.s.p.slice(i,i+3);
     if(!goods.some(g=>{const co=Math.cos(g.angle),sn=Math.sin(g.angle),dx=x-g.x,dz=z-g.z;
       return Math.abs(dx*co-dz*sn)<=.175001&&Math.abs(dx*sn+dz*co)<=.250001&&y>=g.y-.150001&&y<=g.y+.150001}))inside=false;
    }
    result.cases.push({q,width,angle,goods,carcass:await hash(carcass),
     metadata:{cols:c.cols,conts:c.conts,next:[c.r(),c.r(),c.r()]},triangles:vertices/3,inside,winding,normals,
     finite:keys.every(k=>!c.s[k]||c.s[k].every(Number.isFinite)),
     aligned:c.s.n.length===vertices*3&&c.s.c.length===vertices*3&&c.s.a.length===vertices*2&&c.s.m.length===vertices&&(!c.s.uv||c.s.uv.length===vertices*2),
     plainGoods:c.s.m.slice(252).every(v=>v===0)});
   }
   // No occupied cells is a legitimate shelf, not a failed replacement.
   const empty=new C(1,1);empty.prep();empty.anc=1;empty.setOY(0);empty.ch=()=>false;empty.shelf(90,82,.4,3,false);
   result.empty={triangles:empty.s.p.length/9,geometry:await hash(keys.map(k=>empty.s[k])),metadata:{cols:empty.cols,conts:empty.conts,next:[empty.r(),empty.r()]}};
   game.qk='med';
   for(const [x,z] of [[0,0],[1,1],[2,1]]) {
    const c=new C(x,z);c.build();result.chunks.push({key:x+','+z,hash:await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,
     brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})});
   }
   search:for(let x=-5;x<=5;x++)for(let z=-5;z<=5;z++) {
    const c=new C(x,z);if(c.d!=='market')continue;c.build();if(!c.conts.some(v=>v.type==='shelf'))continue;
    result.market={x,z,hash:await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})};break search;
   }
   if(!result.market)throw Error('Native market fixture absent');
   result.stats={...TERRA_ART.shelfGoods};return result;
  }''')
  assert len(report['cases'])==18
  for case in report['cases']:
   assert case['finite'] and case['aligned'] and case['normals'] and case['winding'] and case['inside'],case
   assert case['triangles']<=84+len(case['goods'])*150,case
  if not baseline:
   for old,new in zip(reports[0]['cases'],report['cases']):
    for key in ['q','width','angle','goods','carcass','metadata']:assert new[key]==old[key],(key,old,new)
    assert new['plainGoods'] and new['triangles']>old['triangles'],new
   assert report['chunks']==reports[0]['chunks'] and report['market']==reports[0]['market'] and report['empty']==reports[0]['empty']
   assert report['stats']['goods']>0 and report['stats']['fallback']==0,report['stats']
   loot=page.evaluate('''market=>{
    if(!game.world.chunks.has(market.x+','+market.z))game.world.build(market.x,market.z);
    const shelf=game.world.conts.find(c=>c.type==='shelf'&&!c.looted);
    if(!shelf)throw Error('Native shelf fixture absent');
    game.openContainer(shelf);if(!shelf.items?.length)throw Error('No native shelf loot');
    const key=shelf.key,items=structuredClone(shelf.items),inventory={...game.p.inv};
    while(shelf.items.length){const count=shelf.items.length;game.takeLoot(shelf,0);if(shelf.items.length>=count)throw Error('Shelf loot did not transfer')}
    for(const item of items)if(item.id&&game.p.inv[item.id]<(inventory[item.id]||0)+item.n)throw Error('Inventory lost shelf loot');
    if(!shelf.looted||!game.world.looted.has(key))throw Error('Shelf not marked searched');
    game.ui.close('loot');const save=game.save();if(!save?.ok)throw Error('Shelf save refused');
    return {key,items,inventory:items.map(i=>({id:i.id,n:game.p.inv[i.id]})),saved:save.ok};
   }''',report['market'])
   page.reload(timeout=120000);page.locator('#mContinue').click()
   page.wait_for_function('key=>game.state==="play" && game.world.looted.has(key)',arg=loot['key'])
   for item in loot['inventory']:assert page.evaluate('(id)=>game.p.inv[id]',item['id'])>=item['n']
   report['loot']=loot
   page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  view=page.evaluate('''()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,c=new C(1,1);c.prep();c.anc=1;c.setOY(0);game.qk='high';
   c.shelf(-4.5,0,0,3,false);c.shelf(0,0,.32,3,false);c.shelf(4.5,0,Math.PI/2,3,false);
   c.s.mt=-1;c.s.add(TERRA_SEWER_BRIDGE.shapes.box,0,-.15,0,16,.3,8,'#45483e',0,0,0,0);
   const mat=[...game.world.chunks.values()].flatMap(c=>c.meshes).find(m=>m.geometry?.attributes.mt&&m.material?.vertexColors)?.material;
   if(!mat)throw Error('Native static material absent');
   const scene=new game.scene.constructor();scene.background=game.scene.background.clone();scene.add(game.hemi.clone());
   const sun=game.sun.clone();sun.position.set(-5,15,10);sun.target.position.set(0,0,0);sun.intensity=2.2;scene.add(sun,sun.target);
   sun.castShadow=true;sun.shadow.camera.left=-12;sun.shadow.camera.right=12;sun.shadow.camera.top=12;sun.shadow.camera.bottom=-12;
   sun.shadow.camera.near=1;sun.shadow.camera.far=60;sun.shadow.camera.updateProjectionMatrix();
   const mesh=c.s.mesh(mat);mesh.castShadow=true;mesh.receiveShadow=true;scene.add(mesh);
   const cam=game.cam.clone();cam.position.set(7,6.7,13);cam.lookAt(0,.7,0);cam.zoom=1.3;cam.updateProjectionMatrix();
   window.__shelves={scene,cam};const metrics={};
   // The native game throttles shadow updates. A fresh QA scene needs an
   // explicit update instead of inheriting the last world frame's flag.
   game.ren.shadowMap.autoUpdate=true;sun.shadow.autoUpdate=true;
   for(const shadow of [false,true]){game.ren.shadowMap.enabled=shadow;game.ren.shadowMap.needsUpdate=true;sun.shadow.needsUpdate=true;game.ren.info.reset();game.post.render(scene,cam,0);
    metrics[shadow?'shadow':'plain']={calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,error:game.ren.getContext().getError()};}
   return metrics;
  }''')
  assert view['plain']['error']==0 and view['shadow']['error']==0,view
  if not baseline:
   for key in ['plain','shadow']:assert view[key]['calls']==reports[0]['render'][key]['calls'],view
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/(label+'.png')))
  page.evaluate('''()=>{__shelves.cam.position.set(-4.5,2.3,3.6);__shelves.cam.lookAt(-4.5,.9,0);__shelves.cam.zoom=1;__shelves.cam.updateProjectionMatrix();game.post.render(__shelves.scene,__shelves.cam,0)}''')
  page.screenshot(path=str(out/(label+'-close.png')))
  assert not errors,errors
  report['render']=view;report['errors']=errors;reports.append(report)
  (out/(label+'.json')).write_text(json.dumps(report,indent=2))
  print(label,'cases',len(report['cases']),'stats',report['stats'],'render',view,'JS0',flush=True);browser.close()
print('PASS 18 shelf cases, native carcass/occupancy/metadata/RNG, empty shelf, 3 chunks+market, bounds/normals/materials, native loot/save/reload, shared batch')
