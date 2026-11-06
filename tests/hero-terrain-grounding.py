"""Live six-part hero follows native terrain; hands, weapons and previews stay local."""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='4a4a181bd7ecca8daa2c237912c0e3e6300ed092'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-hero-ground'));out.mkdir(parents=True,exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-hero-ground-baseline/terra-v33.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='e3e5180be87fb0bdb209a14534ab65d3cc420717d02e046e84a5a1734e79058c'
asset=json.loads(gzip.decompress((ROOT/'play/assets/pack/TERRA_ASSETS.json.gz').read_bytes()))['hero']
hero=base64.b64decode(asset[3:] if asset.startswith('gz:') else asset)
if asset.startswith('gz:'):hero=gzip.decompress(hero)
reports=[]
with sync_playwright() as pw:
 for mode in ['before','grounded']:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(120000);pending=[];errors=[]
  page.route('**/qa/pending-hero.glb',lambda r:pending.append(r));page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:errors.append(m.text[:1000]) if m.type=='error' else None)
  page.add_init_script("""localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}));let assets;Object.defineProperty(window,'TERRA_ASSETS',{configurable:true,get(){return assets},set(v){assets=v;v.hero='url:'+location.origin+'/qa/pending-hero.glb'}});""")
  if mode=='before':page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
  page.goto(url,timeout=120000);page.wait_for_function('window.game && game.sewers && !game.glb.hero');assert len(pending)==1
  page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play"')
  page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
  report=page.evaluate('''async mode=>{
   const g=game,Rig=g.heroRig.constructor,scene=new g.scene.constructor(),control=new Rig(scene,'hero',1),hash=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(x=>x.toString(16).padStart(2,'0')).join('');
   g.state='modal';g.p.x=g.p.z=60;g.world.update(60,60,true);
   const points=[];for(let x=2;x<142;x+=2)for(let z=2;z<142;z+=2){if(!g.world.collide({x,z},.45))points.push({x,z,h:TERRA_H(x,z)})}points.sort((a,b)=>a.h-b.h);
   const chosen=[{...points[0],name:'low'},{...points.at(-1),name:'high'}];if(chosen[0].h>-.2||chosen[1].h<.2)throw Error('Missing nonflat loaded terrain');
   let stair=null;for(const e of g.world.ents){if(e.kind!=='metro')continue;const p=TERRA_SEWER_BRIDGE.metroProfileAt(e.x,e.z);if(!p)continue;const x=p.x,z=p.rear+.1,h=TERRA_H(x,z);if(Math.abs(h)>.1){stair={x,z,h,name:'stairs'};break;}}
   if(!stair)throw Error('No native metro stair sample');chosen.push(stair);
   const shapes=[['standing',{}],['walk',{ph:1.2,amp:.7}],['aim',{twist:.6,armR:-1.5,aimL:1.25}],['fall',{fall:.7,fallDir:-1,sc:.9}]],checks=[];
   const attrs=rig=>rig.parts.map(({im})=>Object.fromEntries(Object.entries(im.geometry.attributes).map(([k,v])=>[k,Array.from(v.array)])));
   const geometry=await hash(attrs(g.heroRig));if(geometry!==await hash(attrs(control)))throw Error('Main and local geometry differ');
   const check=(point,name,extra)=>{
    const pose={x:point.x,y:0,z:point.z,yaw:.3,ph:0,amp:0,...extra},native={...pose},versions=g.heroRig.parts.map(p=>p.im.instanceMatrix.version),sample=window.TERRA_H;let reads=0;
    window.TERRA_H=(...a)=>{reads++;return sample(...a)};try{control.update([native]);g.heroRig.update([pose]);}finally{window.TERRA_H=sample}
    let error=0;for(let i=0;i<6;i++){const a=g.heroRig.parts[i].im.instanceMatrix.array,b=control.parts[i].im.instanceMatrix.array;for(let k=0;k<16;k++){const expected=Math.fround(b[k]+(k===13&&mode!=='before'?point.h:0));error=Math.max(error,Math.abs(a[k]-expected));}if(g.heroRig.parts[i].im.instanceMatrix.version!==versions[i]+1)throw Error('Extra matrix upload');}
    if(error>1e-6||reads!==(mode==='before'?0:1))throw Error('Ground matrix or sample budget '+JSON.stringify({error,reads,point}));
    const local=pose._root.elements.every((v,i)=>v===native._root.elements[i])&&pose._armR.elements.every((v,i)=>v===native._armR.elements[i]);if(!local)throw Error('Local weapon/root pose changed');
    const first=g.heroRig.parts.map(p=>Array.from(p.im.instanceMatrix.array));g.heroRig.update([pose]);if(first.some((a,i)=>a.some((v,k)=>v!==g.heroRig.parts[i].im.instanceMatrix.array[k])))throw Error('Cumulative grounding');
    return{point:point.name,pose:name,height:point.h,error,reads,local,oneUpload:true,noDrift:true};
   };
   for(const p of chosen)for(const [name,extra] of shapes)checks.push(check(p,name,extra));
   const ch=g.world.enterDungeon({idx:73,theme:'metro',seed:'hero-ground'}),floor=ch.rooms[0],floorPoint={x:floor.x,z:floor.z,h:TERRA_H(floor.x,floor.z),name:'metro-floor'};
   if(ch.rooms.length!==16||floorPoint.h!==0)throw Error('Native underground floor changed');for(const [name,extra] of shapes)checks.push(check(floorPoint,name,extra));g.world.exitDungeon();
   const p=chosen[1];g.p.x=p.x;g.p.z=p.z;g.p.yaw=0;g.p.ph=g.p.moving=g.p.swing=0;g.p.alive=true;g.world.update(p.x,p.z,true);
   const w=g.makeWeapon('katana',0,0,null);g.p.weapons.push(w);g.p.eq[g.p.slot]=w;g.heroPose(0);
   const capture=()=>{let feet=Infinity,top=-Infinity;for(const {im} of g.heroRig.parts){const a=im.geometry.attributes.position.array,m=im.instanceMatrix.array;for(let i=0;i<a.length;i+=3){const y=m[1]*a[i]+m[5]*a[i+1]+m[9]*a[i+2]+m[13];feet=Math.min(feet,y);top=Math.max(top,y)}}return{feet,top,arm:g.heroH._armR.elements[13],weapon:g.wMesh.matrix.elements[13],weaponHeight:TERRA_H(g.wMesh.matrix.elements[12],g.wMesh.matrix.elements[14])}};
   const before=capture(),render=g.post.render;let during;g.post.render=()=>{during=capture()};try{g.renderT()}finally{g.post.render=render}const after=capture();
   if(before.feet!==during.feet||during.feet!==after.feet||Math.abs(during.weapon-before.weapon-before.weaponHeight)>1e-6||Math.abs(after.weapon-before.weapon)>1e-12)throw Error('Render pass double grounding or weapon regression');
   if(mode!=='before'&&Math.abs(before.feet-p.h)>.02)throw Error('Feet not on native surface');
   g.cam.position.set(p.x+4,p.h+4,p.z+6);g.cam.lookAt(p.x,p.h+.9,p.z);g.dayT=11;g.lighting(0);g.renderT();
   g.state='play';return{mode,chosen,checks,geometry,frame:{height:p.h,before,during,after},errors:[]};
  }''',mode)
  page.screenshot(path=str(out/(mode+'.png')))
  # Real inventory uses the same native rig constructor at local coordinates.
  page.keyboard.press('KeyI');page.wait_for_function('game.ui.equipmentPreview?.source?.isHeroFallback && !!game.ui.equipmentPreview.inst')
  preview=page.evaluate('''()=>{const p=game.ui.equipmentPreview,Rig=game.heroRig.constructor,s=new game.scene.constructor(),r=new Rig(s,'hero',1);r.update([{x:0,y:0,z:0,yaw:0,amp:0}]);const actual=p.inst.root.children;return{local:actual.every((im,i)=>im.instanceMatrix.array.every((v,k)=>v===r.parts[i].im.instanceMatrix.array[k])),fallback:true,terrain:TERRA_H(game.p.x,game.p.z)}}''')
  assert preview['local'] and preview['terrain']>.2,preview
  page.keyboard.press('Escape');assert page.evaluate('TERRA_ART.equipmentFallbacks.live===0 && TERRA_ART.equipmentFallbacks.watchers===0')
  pending[0].fulfill(body=hero,content_type='model/gltf-binary');page.wait_for_function('!!game.glb.hero')
  late=page.evaluate('''()=>{game.state='play';game.heroPose(0);const root=game.heroInst.root,before=root.position.y,expected=TERRA_H(game.p.x,game.p.z),render=game.post.render;let during;game.post.render=()=>{during=root.position.y};try{game.renderT()}finally{game.post.render=render}return{before,during,after:root.position.y,expected,fallback:game.heroRig.parts.filter(p=>p.im.visible).length,roots:game.scene.children.filter(o=>o===root).length,gl:game.ren.getContext().getError()}}''')
  assert late['before']==late['after']==0 and abs(late['during']-late['expected'])<1e-10 and late['fallback']==0 and late['roots']==1 and late['gl']==0,late
  report['preview']=preview;report['late']=late;report['errors']=errors;assert not errors,errors
  (out/(mode+'.json')).write_text(json.dumps(report,indent=2));reports.append(report);print(mode,'PASS',flush=True);browser.close()
assert reports[0]['geometry']==reports[1]['geometry']
for key in ['before','during','after']:
 for name in ['arm','weapon','weaponHeight']:assert reports[0]['frame'][key][name]==reports[1]['frame'][key][name]
assert reports[0]['frame']['during']['top']<reports[0]['frame']['height']
print('PASS loaded positive/negative/stair terrain and metro floor, four poses, one sample/upload, no drift, local root/hand/weapon unchanged, inventory local, late GLB grounded once, geometry unchanged, JS0/GL0',flush=True)
