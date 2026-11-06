"""Real own-model delay/failure: visible inventory, late swap and owned cleanup."""
import base64
import gzip
import hashlib
import json
import os
from pathlib import Path
import subprocess
from playwright.sync_api import sync_playwright

ROOT=Path(__file__).resolve().parents[1]
BASE='f56f8bfc16e97088ad0b9fd6e88315c06778e17a'
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-equipment-fallback'));out.mkdir(parents=True,exist_ok=True)
offline='/terra.html' in url
old=Path(os.environ.get('TERRA_BASELINE_FILE','/tmp/terra-preview-baseline/terra-v32.html')).read_bytes() if offline else subprocess.check_output(['git','show',BASE+':play/index.html'],cwd=ROOT)
if offline:assert hashlib.sha256(old).hexdigest()=='648e7678eb12e483660d53f5ce58bb22ea0e52eade0decdb2968a9c43e27e053'
asset=json.loads(gzip.decompress((ROOT/'play/assets/pack/TERRA_ASSETS.json.gz').read_bytes()))['hero']
hero=base64.b64decode(asset[3:] if asset.startswith('gz:') else asset)
if asset.startswith('gz:'):hero=gzip.decompress(hero)
assert hero[:4]==b'glTF'

FRAME='''()=>{const p=game.ui.equipmentPreview,c=p.canvas,d=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
 let x0=c.width,y0=c.height,x1=-1,y1=-1,pixels=0,hash=2166136261;
 for(let y=0;y<c.height;y++)for(let x=0;x<c.width;x++){const i=(y*c.width+x)*4;for(let k=0;k<4;k++)hash=Math.imul(hash^d[i+k],16777619);if(d[i+3]>24){pixels++;x0=Math.min(x0,x);x1=Math.max(x1,x);y0=Math.min(y0,y);y1=Math.max(y1,y)}}
 return{width:c.width,height:c.height,pixels,hash:hash>>>0,left:x0,right:c.width-1-x1,top:y0,bottom:c.height-1-y1,span:(y1-y0)/c.height,
 label:p.label.textContent,fallback:!!p.source?.isHeroFallback,localRoot:p.inst.root.parent===p.scene,worldRoot:p.inst.root.parent===game.scene,timer:!!p.timer};}'''

def frame(page):
    d=page.evaluate(FRAME)
    assert d['pixels']>300 and min(d[k] for k in ['left','right','top','bottom'])>=3 and d['span']>.5,d
    assert d['localRoot'] and not d['worldRoot'] and not d['timer'] and d['label']=='',d
    return d

reports=[]
with sync_playwright() as pw:
 for mode in ['before','failed-own-model','late-open','late-closed']:
  browser=pw.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
  page=browser.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(120000)
  if mode=='late-closed':page.emulate_media(reduced_motion='reduce')
  pending=[];errors=[];warnings=[];fail=mode in ['before','failed-own-model']
  page.route('**/qa/pending-hero.glb',lambda r:pending.append(r))
  page.on('pageerror',lambda e:errors.append(str(e)))
  def console(m):
   expected=fail and ('ERR_FAILED' in m.text and '/qa/pending-hero.glb' in m.location.get('url','') or m.text.startswith('GLB hero '))
   if m.type=='error' and not expected:errors.append(m.text[:1000])
   if m.type=='warning':warnings.append(m.text[:300])
  page.on('console',console)
  page.add_init_script("""localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}));let assets;Object.defineProperty(window,'TERRA_ASSETS',{configurable:true,get(){return assets},set(v){assets=v;v.hero='url:'+location.origin+'/qa/pending-hero.glb'}});""")
  if mode=='before':
   page.route(url,lambda r:r.fulfill(body=old,content_type='text/html'))
   if not offline:
    old_module=subprocess.check_output(['git','show',BASE+':play/art/actor-fallbacks.js'],cwd=ROOT)
    page.route('**/art/actor-fallbacks.js?*',lambda r:r.fulfill(body=old_module,content_type='application/javascript'))
    old_backpack=subprocess.check_output(['git','show',BASE+':play/ui/backpack.js'],cwd=ROOT)
    page.route('**/ui/backpack.js',lambda r:r.fulfill(body=old_backpack,content_type='application/javascript'))
  page.goto(url,timeout=120000);page.wait_for_function('window.game && game.sewers && !game.glb.hero');assert len(pending)==1
  page.evaluate('''()=>{const refresh=game.refreshModelMode;game.refreshModelMode=function(...a){const r=refresh.apply(this,a);if(a[0]!==true)window.__previewFullReady=true;return r}}''')
  page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play"')
  profile=page.evaluate('localStorage.getItem("terra_save")')
  page.keyboard.press('KeyI');page.wait_for_function('game.state==="modal" && game.ui.equipmentPreview?.host')
  if mode=='before':
   pending[0].abort('failed');page.wait_for_function('window.__previewFullReady===true');page.wait_for_timeout(1000)
   report=page.evaluate('''()=>{const p=game.ui.equipmentPreview;return{mode:'before',instance:!!p.inst,label:p.label.textContent,timer:!!p.timer,frame:!!p.frame}}''')
   assert not report['instance'] and (report['timer'] or report['frame']) and report['label']=='Загрузка модели…',report
   page.screenshot(path=str(out/'before.png'))
  else:
   page.wait_for_function('game.ui.equipmentPreview?.source?.isHeroFallback && game.ui.equipmentPreview.canvas.width>20')
   initial=frame(page);assert initial['fallback'],initial
   page.screenshot(path=str(out/(mode+'-pending.png')))
   ownership=page.evaluate('''()=>{const p=game.ui.equipmentPreview,parts=p.inst.root.children;
    window.__previewDisposed={geometry:0,mesh:0,material:0,target:0};
    for(const im of parts){im.geometry.addEventListener('dispose',()=>__previewDisposed.geometry++);im.addEventListener('dispose',()=>__previewDisposed.mesh++);}
    parts[0].material.addEventListener('dispose',()=>__previewDisposed.material++);p.target.addEventListener('dispose',()=>__previewDisposed.target++);
    window.__previewDraws=0;const draw=p.draw;p.draw=function(...a){__previewDraws++;return draw.apply(this,a)};
    return{parts:parts.length,separate:parts.every(im=>game.heroRig.parts.every(w=>im!==w.im&&im.geometry!==w.im.geometry&&im.geometry.attributes.position.array!==w.im.geometry.attributes.position.array)),material:parts.every(im=>im.material===game.heroRig.parts[0].im.material),stats:{...TERRA_ART.equipmentFallbacks}}}''')
   assert ownership['parts']==6 and ownership['separate'] and ownership['material'] and ownership['stats']['live']==1 and ownership['stats']['watchers']==1,ownership
   # All operations below are synchronous inside each evaluate; live world poses must stay untouched.
   renderer=page.evaluate('''()=>{const p=game.ui.equipmentPreview,r=game.ren;
    const world=()=>JSON.stringify(game.heroRig.parts.map(o=>({m:Array.from(o.im.instanceMatrix.array),visible:o.im.visible,count:o.im.count}))),w=world();
    const save=()=>({target:r.getRenderTarget(),viewport:r.getViewport(p.target.viewport.clone()),scissor:r.getScissor(p.target.scissor.clone()),test:r.getScissorTest(),color:r.getClearColor(game.wMat.color.clone()),alpha:r.getClearAlpha(),auto:r.autoClear,dpr:r.getPixelRatio()});
    const restore=s=>{r.setPixelRatio(s.dpr);r.setRenderTarget(s.target);r.setViewport(s.viewport);r.setScissor(s.scissor);r.setScissorTest(s.test);r.setClearColor(s.color,s.alpha);r.autoClear=s.auto};
    const signature=s=>JSON.stringify({viewport:s.viewport.toArray(),scissor:s.scissor.toArray(),test:s.test,color:s.color.toArray(),alpha:s.alpha,auto:s.auto,dpr:s.dpr}),original=save(),target=new p.target.constructor(13,17);let checked=0,fault=false;
    try{for(const dpr of [.75,1.1,2]){r.setPixelRatio(dpr);r.setRenderTarget(target);r.setViewport(2,3,7,9);r.setScissor(1,2,5,6);r.setScissorTest(true);r.setClearColor(0x213547,.37);r.autoClear=false;
     const before=save();p.draw();const after=save();if(before.target!==after.target||signature(before)!==signature(after))throw Error('Renderer state changed');checked++;
     const read=r.readRenderTargetPixels;r.readRenderTargetPixels=()=>{throw Error('QA readback')};try{p.draw();fault=p.label.textContent==='Предпросмотр модели недоступен'&&signature(before)===signature(save())&&before.target===r.getRenderTarget()}finally{r.readRenderTargetPixels=read;}p.draw();}
    }finally{restore(original);target.dispose();}return{checked,fault,worldUnchanged:w===world(),gl:r.getContext().getError()};}''')
   assert renderer=={'checked':3,'fault':True,'worldUnchanged':True,'gl':0},renderer
   yaw=page.evaluate('game.ui.equipmentPreview.yaw');page.locator('[data-equipment-rotate="1"]').click();page.wait_for_function('Math.abs(game.ui.equipmentPreview.yaw - '+str(yaw)+')>.5')
   rotated=frame(page);assert rotated['hash']!=initial['hash']
   if mode=='late-closed':
    page.keyboard.press('Escape');page.wait_for_function('game.state==="play"')
    created=page.evaluate('TERRA_ART.equipmentFallbacks.created')
    pending[0].fulfill(body=hero,content_type='model/gltf-binary');page.wait_for_function('window.__previewFullReady===true')
    assert page.evaluate('TERRA_ART.equipmentFallbacks.created')==created
    assert page.evaluate('!game.ui.equipmentPreview.host && !game.ui.equipmentPreview.inst && !TERRA_ART.equipmentFallbacks.watchers && !TERRA_ART.equipmentFallbacks.live')
    page.keyboard.press('KeyI');page.wait_for_function('game.ui.equipmentPreview?.source===game.glb.hero && !!game.ui.equipmentPreview.inst')
   else:
    if fail:pending[0].abort('failed')
    else:pending[0].fulfill(body=hero,content_type='model/gltf-binary')
    page.wait_for_function('window.__previewFullReady===true')
    if not fail:page.wait_for_function('game.ui.equipmentPreview?.source===game.glb.hero')
   final=frame(page);assert final['fallback']==fail,final
   disposed=page.evaluate('({...__previewDisposed})')
   assert disposed['geometry']==(0 if fail else 6) and disposed['mesh']==(0 if fail else 6) and disposed['material']==0,disposed
   # The static suit has no timer. A ready GLB retains its existing idle loop;
   # reduced motion still renders model readiness without animation polling.
   page.wait_for_timeout(200);draws=page.evaluate('__previewDraws');page.wait_for_timeout(1100)
   motion=page.evaluate('''()=>({draws:__previewDraws,pump:!!game.ui.equipmentPreview._bpPump,timer:!!game.ui.equipmentPreview.timer,reduced:matchMedia('(prefers-reduced-motion: reduce)').matches})''')
   assert not motion['timer'],motion
   if mode=='late-open':assert motion['draws']>draws and motion['pump'] and not motion['reduced'],motion
   else:assert motion['draws']==draws and not motion['pump'],motion
   sizes=[]
   for name,w,h in [('desktop',1280,900),('portrait',390,844),('landscape',844,390)]:
    page.set_viewport_size({'width':w,'height':h});page.locator('#invBody').evaluate('e=>e.scrollTop=0');page.wait_for_timeout(200)
    f=frame(page);sizes.append({'name':name,**f});page.screenshot(path=str(out/(mode+'-'+name+'.png')))
   page.keyboard.press('Escape');page.wait_for_function('game.state==="play"')
   closed=page.evaluate('''()=>{const p=game.ui.equipmentPreview;return{stats:{...TERRA_ART.equipmentFallbacks},disposed:{...__previewDisposed},refs:!!(p.inst||p.source||p.target||p.bytes||p.scene||p.camera||p.host||p.observer||p.modelUnwatch||p.frame||p.timer||p._bpPump||p._bpLit)}}''')
   assert not closed['refs'] and closed['stats']['live']==closed['stats']['watchers']==0 and closed['stats']['created']==closed['stats']['released'],closed
   assert closed['disposed']['geometry']==6 and closed['disposed']['mesh']==6 and closed['disposed']['material']==0 and closed['disposed']['target']>=1,closed
   for _ in range(3):
    page.keyboard.press('KeyI');page.wait_for_function('!!game.ui.equipmentPreview?.inst');frame(page)
    page.locator('#inv .tabs [data-tab="items"]').click();page.wait_for_function('!game.ui.equipmentPreview.host')
    assert page.evaluate('TERRA_ART.equipmentFallbacks.live===0 && TERRA_ART.equipmentFallbacks.watchers===0')
    page.keyboard.press('Escape');page.wait_for_function('game.state==="play"')
   assert page.evaluate('localStorage.getItem("terra_save")')==profile
   report={'mode':mode,'initial':initial,'rotated':rotated,'ownership':ownership,'renderer':renderer,'final':final,'sizes':sizes,'closed':closed,'motion':motion,'motionCorrect':True,'saveUnchanged':True,
    'cache':page.evaluate('({templates:TERRA_ART.actorFallbacks.templates,bytes:TERRA_ART.actorFallbacks.bytes,fallback:TERRA_ART.actorFallbacks.fallback})')}
   assert report['cache']=={'templates':6,'bytes':76296,'fallback':0},report['cache']
  report['errors']=errors;report['warnings']=warnings;assert not errors,errors
  (out/(mode+'.json')).write_text(json.dumps(report,ensure_ascii=False,indent=2));reports.append(report);print(mode,'PASS',flush=True);browser.close()
print('PASS own failure / late open / late closed, visible suit / rotate / 3 layouts, static suit / native idle / reduced motion, renderer normal+fault, ownership/cleanup/no save writes, JS0/GL0',flush=True)
