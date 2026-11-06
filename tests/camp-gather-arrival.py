"""Сбор: настоящий наряд, дорога без добычи, возвращение и продолжение сейва."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright,expect

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-camp-gather-arrival'));out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage'])
 page=b.new_page(viewport={'width':1382,'height':964});page.set_default_timeout(90000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text) if m.type=='error' else None)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play"&&game.sewers&&TERRA_KITS.ready&&terraDefense.ready');page.evaluate('''()=>{game.loop=()=>{};const h=game.homePos();game.p.x=h.x;game.p.z=h.z+4;game.p.camp.rep=1000;game.camp.recruit({id:'qa-arrival',name:'Павел Ветров',prof:'engineer',pos:h});const s=game.p.camp.settlers['qa-arrival'];s.legacy=true;s.facility='sawmill';s.job='gather:wood';game.ui.campPanel.open();game.ui.campPanel.select('settlers')}''')
 page.locator('[data-resident="qa-arrival"]').click();page.locator('.fbChangeJob').click();page.locator('[data-resident-job="gather:wood"]').click()
 assert page.evaluate('game.p.camp.settlers["qa-arrival"].job==="gather:wood"&&!game.p.camp.settlers["qa-arrival"].facility')
 page.locator('#campPanel footer [data-close="campPanel"]').click();page.wait_for_function('game.state==="play"')
 report={}
 report['closedRoom']=page.evaluate('''()=>{game.camp.tick(1,game.workerSceneContext());const c=game.p.camp,s=c.settlers['qa-arrival'],h={...s.pos},walls=[{x0:h.x-3,x1:h.x-2,z0:h.z-3,z1:h.z+3},{x0:h.x+2,x1:h.x+3,z0:h.z-3,z1:h.z+3},{x0:h.x-3,x1:h.x+3,z0:h.z-3,z1:h.z-2},{x0:h.x-3,x1:h.x+3,z0:h.z+2,z1:h.z+3}];for(let i=0;i<10;i++)game.camp.tick(1,{...game.workerSceneContext(),resourcePoints:[{k:'wood',x:h.x+12,z:h.z,used:false}],workerObstacles:walls});const result={status:s.status,reason:s.workBlock,wood:c.res.wood,work:s.work,xp:s.xp};game.camp.tick(1,game.workerSceneContext());return{...result,recovered:s.status!=='blocked'&&!s.workBlock}}''')
 assert report['closedRoom']=={'status':'blocked','reason':'obstacle','wood':0,'work':0,'xp':0,'recovered':True},report['closedRoom']
 # Obstruct a disposable worker with a synthetic closed box: no phantom output.
 report['blocked']=page.evaluate('''()=>{const c=game.p.camp,s=c.settlers['qa-arrival'];game.camp.tick(1,game.workerSceneContext());const h={...s.pos};if(!Number.isFinite(h.x)||!Number.isFinite(h.z))throw Error('Worker not initialized');const before={work:s.work,wood:c.res.wood,xp:s.xp};for(let i=0;i<80;i++)game.camp.tick(1,{...game.workerSceneContext(),resourcePoints:[{k:'wood',x:h.x+12,z:h.z,used:false}],workerObstacles:[{x0:h.x+3,x1:h.x+4,z0:h.z-100000,z1:h.z+100000,h:3}]});return{before,after:{work:s.work,wood:c.res.wood,xp:s.xp},status:s.status,pos:s.pos}}''')
 assert report['blocked']['before']==report['blocked']['after'],report['blocked']
 assert report['blocked']['status']=='travel'
 print('PASS native UI reassignment removes obsolete facility; 80s trapped worker gets no work, XP or wood',flush=True)
 # Actual loaded world nodes and obstacles, no injected waypoint or free resource.
 report['outbound']=page.evaluate('''()=>{const c=game.p.camp,s=c.settlers['qa-arrival'],start={...s.pos},before={wood:c.res.wood,work:s.work};const log=[];for(let i=0;i<500;i++){const was={...s.pos},work=s.work,wood=c.res.wood;game.camp.tick(1,game.workerSceneContext());if(i%10===0)log.push({t:i,pos:{...s.pos},status:s.status,work:s.work,wood:c.res.wood});if(s.status==='travel'&&work===0&&s.work!==0)throw Error('Work advanced on outbound travel');if(s.work>=TERRA_DEFENSE_CTX.B.camp.work.gatherPeriod*.75&&s.status==='travel')return{start,before,now:{pos:s.pos,wood:c.res.wood,work:s.work,status:s.status},log};}throw Error('Worker never began return leg')}''')
 assert report['outbound']['now']['wood']==report['outbound']['before']['wood']
 assert len(report['outbound']['log'])>1
 page.evaluate('''()=>{game.campLifeUpdate(.05);game.renderT()}''');page.screenshot(path=str(out/'returning.png'),animations='disabled')
 assert page.evaluate('!!game.npcV["qa-arrival"]?.carry?.visible'),'Return cargo not visible'
 saved=page.evaluate('''()=>{game.save();const x=JSON.parse(localStorage.getItem('terra_save')).p.camp;return{work:x.settlers['qa-arrival'].work,pos:x.settlers['qa-arrival'].pos,wood:x.res.wood}}''')
 assert saved['work']>=33.75
 print('PASS actual world journey, resource work and return with visible cargo; no wood credited before deposit; native save in transit',flush=True)
 page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('game.state==="play"&&TERRA_KITS.ready&&terraDefense.ready');page.evaluate('game.loop=()=>{}')
 report['continued']=page.evaluate('''()=>{const c=game.p.camp,s=c.settlers['qa-arrival'],before=c.res.wood,log=[];for(let i=0;i<400;i++){game.camp.tick(1,game.workerSceneContext());if(i%10===0)log.push({t:i,pos:{...s.pos},status:s.status,work:s.work,wood:c.res.wood});if(c.res.wood>before)return{before,after:c.res.wood,work:s.work,pos:s.pos,home:game.homePos(),log};}throw Error('Return never delivered')}''')
 assert report['continued']['after']==saved['wood']+1,report['continued']
 home=report['continued']['home'];pos=report['continued']['pos'];assert (pos['x']-home['x'])**2+(pos['z']-home['z'])**2<64
 page.evaluate('game.save()');page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('game.state==="play"');page.evaluate('game.loop=()=>{}')
 assert page.evaluate('game.p.camp.res.wood')==report['continued']['after'],'Cold continue duplicated delivery'
 assert not errors,errors
 report['coldContinue']=True;report['errors']=errors;(out/'report.json').write_text(json.dumps(report,ensure_ascii=False,indent=2));print('PASS save on return, cold continue, exactly one delivery near home and second cold continue without duplicate; JS0',flush=True);b.close()
