"""Packed geometry keeps one material id per vertex, including wreck rewinds."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

root=Path(__file__).resolve().parents[1]
url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-prop-materials-qa'));out.mkdir(exist_ok=True)
reports=[]
with sync_playwright() as p:
 for baseline in [True,False]:
  b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
  page=b.new_page(viewport={'width':1280,'height':800});page.set_default_timeout(90000)
  page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
  page.add_init_script('window.TERRA_ART={rockSurfacesEnabled:false}')
  errors=[];warnings=[];page.on('pageerror',lambda e:errors.append(str(e)))
  page.on('console',lambda m:warnings.append(m.text[:500]) if len(warnings)<80 and ('GL_INVALID_OPERATION' in m.text or 'buffer is not big enough' in m.text) else None)
  if baseline:
   offline='/terra.html' in url;source=root/('terra.html' if offline else 'play/index.html')
   html=source.read_text().replace('g.a.length=p/3*2,g.m&&(g.m.length=p/3),g.uv','g.a.length=p/3*2,g.uv')
   if offline:
    code=(root/'play/art/prop-materials.js').read_text().replace('</script','<\\/script');assert code in html;html=html.replace(code,'')
   else:page.route('**/art/prop-materials.js*',lambda r:r.fulfill(body='',content_type='application/javascript'))
   page.route(url,lambda r:r.fulfill(body=html,content_type='text/html'))
  page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.sewers && game.state==="play"')
  report=page.evaluate('''async()=>{
   const C=TERRA_SEWER_BRIDGE.Chunk,L=TERRA_SEWER_BRIDGE.shapes,result={chunks:[]};
   const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
   for(const [cx,cz] of [[0,0],[0,-1],[-1,0],[1,0],[0,1],[-1,-1],[1,-1],[-1,1],[1,1]]) {
    const c=new C(cx,cz);c.build();
    const meta=await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]});
    const geometry=cx===0&&cz===0||cx===1&&cz===0||cx===0&&cz===1?await hash([c.s.p,c.s.n,c.s.a,c.dt.p,c.dt.n,c.dt.a]):null;
    result.chunks.push({key:cx+','+cz,meta,geometry,buffers:['s','dt'].map(k=>({kind:k,vertices:c[k].p.length/3,materials:c[k].m.length}))});
   }
   const c=new C(1,1);c.prep();const s=c.s;
   s.add(L.box,90,.5,82,1,1,1,'#827052',0,0,0,0);const prefix=[...s.m],start=s.p.length/3;
   const prop=s.prop('rock_b',90,0,82,0,1.2),end=s.p.length/3;
   const stone=s.m.slice(start,end).length===end-start&&s.m.slice(start,end).every(v=>v===7);
   const rockPaint=s.c.slice(start*3,end*3);const meanRock=rockPaint.reduce((a,v)=>a+v,0)/rockPaint.length;
   s.add(L.box,92,.5,82,1,1,1,'#44494b',0,0,0,0);
   const beforeMissing=[s.p.length,s.m.length],missing=s.prop('__missing_prop__',0,0,0,0,1);
   result.mixed={prefix:prefix.every((v,i)=>s.m[i]===v),stone,meanRock,vertices:s.p.length/3,materials:s.m.length,missing:missing===false&&beforeMissing[0]===s.p.length&&beforeMissing[1]===s.m.length,dimensions:prop};
   const other=new C(1,1);other.prep();other.s.prop('barrel',90,0,82,0,1);
   result.paint={hash:await hash([other.s.p,other.s.n,other.s.c]),zero:other.s.m.length===other.s.p.length/3&&other.s.m.every(v=>v===0)};
   c.f.prop('qn_commontree_1',90,0,82,0,6);result.foliage={materials:c.f.m,vertices:c.f.p.length/3};
   const w=new C(1,1);w.prep();w.s.add(L.box,90,.5,82,1,1,1,'#827052',0,0,0,0);const cut=w.s.p.length;
   const raw=w.s.prop('kc_sedan',90,0,82,0,1.5);
   w.detailWreckBody({k:'kc_sedan',x:90,z:82,ry:0,h:1.5,tl:0,rl:0,tint:.8,r:raw,start:cut});
   const rewound=w.s.p.length===cut;w.s.add(L.box,92,.5,82,1,1,1,'#44494b',0,0,0,0);
   result.wreck={rewound,kit:!!w.kb,vertices:w.s.p.length/3,materials:w.s.m.length};
   return result;
  }''')
  reports.append(report)
  bad=[v for c in report['chunks'] for v in c['buffers'] if v['vertices']!=v['materials']]
  print(('BASELINE' if baseline else 'FIXED'),'mismatched batches',len(bad),'mixed',report['mixed'],'wreck',report['wreck'],flush=True)
  if baseline:assert len(bad)>0,'Fixture lost its mismatched material buffers'
  else:
   assert not bad,bad
   assert report['mixed']['stone'] and report['mixed']['prefix'] and report['mixed']['missing'],report['mixed']
   assert report['paint']['zero'] and report['paint']['hash']==reports[0]['paint']['hash'],report['paint']
   assert report['mixed']['meanRock']<reports[0]['mixed']['meanRock']*.6,report['mixed']
   assert report['mixed']['vertices']==report['mixed']['materials']
   assert report['wreck']['rewound'] and report['wreck']['kit'] and report['wreck']['vertices']==report['wreck']['materials'],report['wreck']
   assert report['foliage']['materials'] is None
   for old,new in zip(reports[0]['chunks'],report['chunks']):assert old['meta']==new['meta'] and old['geometry']==new['geometry'],(old,new)
  page.evaluate('game.p.x=48;game.p.z=20;game.p.hp=game.p.maxHp=10000;game.camT=null');page.wait_for_timeout(5000)
  page.screenshot(path=str(out/('world-before.png' if baseline else 'world-after.png')))
  page.evaluate('game.loop=function(){}');page.wait_for_timeout(100)
  gpu=page.evaluate('''()=>{
   const c=new TERRA_SEWER_BRIDGE.Chunk(1,1),L=TERRA_SEWER_BRIDGE.shapes;c.prep();c.anc=1;c.setOY(0);
   c.s.add(L.box,90,-.15,82,8,.3,5,'#525747',0,0,0,0);
   c.s.prop('rock_b',89,0,82,0,1.2);c.s.add(L.box,91,.5,82,1,1,1,'#827052',0,0,0,0);
   const material=[...game.world.chunks.values()].flatMap(c=>c.meshes).find(m=>m.geometry?.attributes.mt&&m.material?.vertexColors)?.material;
   if(!material)throw Error('Native static material unavailable');
   for(const node of game.scene.children)if(!node.isLight)node.visible=false;
   game.scene.add(c.s.mesh(material));
   const cam=game.cam.clone();cam.position.set(90,6,89);cam.lookAt(90,.5,82);cam.zoom=1.6;cam.updateProjectionMatrix();
   const gl=game.ren.getContext();for(let i=0;i<10;i++)if(gl.getError()===0)break;
   game.ren.info.reset();game.post.render(game.scene,cam,0);gl.finish();
   return {error:gl.getError(),calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,vertices:c.s.p.length/3,materials:c.s.m.length};
  }''')
  page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
  page.screenshot(path=str(out/('buffer-before.png' if baseline else 'buffer-after.png')))
  report['gpu']=gpu;report['warnings']=warnings
  (out/('baseline.json' if baseline else 'fixed.json')).write_text(json.dumps(report,indent=2))
  print('GPU',gpu,'warnings',len(warnings),flush=True)
  if not baseline:assert gpu['error']==0 and gpu['vertices']==gpu['materials'],gpu
  assert not errors,errors;b.close()
print('PASS material alignment across 9 chunks, packed/missing/non-atlas props, wreck rewind, unchanged geometry/metadata/RNG and native GPU draw; JS0')
