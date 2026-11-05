"""Compare district seams before/after while keeping geometry and interiors exact."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-terrain-blend-qa'));out.mkdir(exist_ok=True)
reports=[]
with sync_playwright() as p:
 for baseline in [True,False]:
  browser=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=browser.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(60000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'low',post:false,dpr:1}))")
  errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
  if baseline:
   offline='/terra.html' in url
   source=root/('terra.html' if offline else 'play/index.html')
   html=source.read_text().replace('let V=0,Y=1-1/Q,Z=e.hv[w];','let V=0,Y=1-1/P,Z=e.hv[w];')
   if offline:
    code=(root/'play/art/terrain-blend.js').read_text().replace('</script','<\\/script')
    assert code in html
    html=html.replace(code,'')
   else:page.route('**/art/terrain-blend.js',lambda r:r.fulfill(body='',content_type='application/javascript'))
   page.route(url,lambda r:r.fulfill(body=html,content_type='text/html'))
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click()
  page.wait_for_function('game.sewers && game.state==="play"')
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,pairs=[];
   const hash=async value=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(value))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   function make(cx,cz){const c=new C(cx,cz);c.prep();c.terrain();return c;}
   function edge(c,axis,value) {
    const map=new Map(),tr=c.tr;
    for(let i=0;i<tr.p.length;i+=3)if(Math.abs(tr.p[i+axis]-value)<1e-8) {
     const key=tr.p[i]+','+tr.p[i+2];
     map.set(key,{p:tr.p.slice(i,i+3),n:tr.n.slice(i,i+3),c:tr.c.slice(i,i+3),w:tr.ws.slice(i/3*8,i/3*8+8)});
    }
    return map;
   }
   for(const [cx,cz,axis] of [[0,0,0],[0,1,0],[-1,-1,0],[1,0,2],[2,2,2],[-2,1,2]]) {
    const a=make(cx,cz),b=make(cx+(axis===0?1:0),cz+(axis===2?1:0));
    const value=(axis===0?cx+1:cz+1)*48,A=edge(a,axis,value),B=edge(b,axis,value);
    const jumps=[];
    for(const [key,v] of A) {
     const other=B.get(key);if(!other)throw Error('Missing shared boundary vertex');
     jumps.push({key,color:Math.max(...v.c.map((x,i)=>Math.abs(x-other.c[i]))),weights:Math.max(...v.w.map((x,i)=>Math.abs(x-other.w[i]))),height:Math.abs(v.p[1]-other.p[1]),normal:Math.max(...v.n.map((x,i)=>Math.abs(x-other.n[i])))});
    }
    const interior=[];
    for(const c of [a,b])for(let i=0;i<c.tr.p.length;i+=3) {
     const x=c.tr.p[i]-c.ox,z=c.tr.p[i+2]-c.oz;
     if(x>4&&x<44&&z>4&&z<44)interior.push(...c.tr.c.slice(i,i+3),...c.tr.ws.slice(i/3*8,i/3*8+8));
    }
    pairs.push({key:cx+','+cz+','+axis,kinds:[a.d,b.d],jumps,
     geometry:await hash([a.tr.p,a.tr.n,b.tr.p,b.tr.n]),
     metadata:await hash([a.cols,b.cols,[a.r(),a.r(),b.r(),b.r()]]),interior:await hash(interior)});
   }
   return pairs;
  }''')
  reports.append(report)
  (out/('baseline.json' if baseline else 'updated.json')).write_text(json.dumps(report,indent=2))
  maximum=max(v['color'] for pair in report for v in pair['jumps'])
  weight=max(v['weights'] for pair in report for v in pair['jumps'])
  print(('BASELINE' if baseline else 'UPDATED'),'colour jump',maximum,'weight jump',weight,flush=True)
  timings=page.evaluate('''()=>{
   const samples=[];
   for(let i=0;i<9;i++){const c=new TERRA_SEWER_BRIDGE.Chunk(2,2);c.prep();const t=performance.now();c.terrain();if(i>1)samples.push(performance.now()-t);}
   samples.sort((a,b)=>a-b);return {medianMs:samples[3],samples};
  }''')
  (out/('timing-baseline.json' if baseline else 'timing-updated.json')).write_text(json.dumps(timings))
  print('Terrain generation timing',timings,flush=True)
  if not baseline:
   assert max(v['color'] for pair in reports[0] for v in pair['jumps'])>.005,'Fixture did not contain a visible seam'
   assert maximum<1e-6 and weight<1e-6,report
   for old,new in zip(reports[0],report):
    assert all(old[k]==new[k] for k in ['geometry','metadata','interior']),(old,new)
  # Actual gameplay at the crash/outskirts boundary, with world props and UI.
  page.evaluate('game.p.x=48;game.p.z=20;game.p.hp=game.p.maxHp=10000;game.camT=null')
  page.wait_for_function('game.world.chunks.has("0,0")&&game.world.chunks.has("1,0")')
  page.wait_for_timeout(5000);page.screenshot(path=str(out/('before.png' if baseline else 'after.png')))
  assert not errors,errors
  browser.close()
print('PASS 6 terrain boundaries, continuous colour/weights, unchanged positions/normals/interior/metadata/RNG; JS0')
