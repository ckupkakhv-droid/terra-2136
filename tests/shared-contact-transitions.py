"""Shared surface shade survives native transition rollback, save and cold loot reload."""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

url=os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/')
out=Path(os.environ.get('TERRA_QA_OUTPUT','/tmp/terra-contact-transitions'));out.mkdir(exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader'])
 page=b.new_page(viewport={'width':1280,'height':900});page.set_default_timeout(120000);errors=[]
 page.on('pageerror',lambda e:errors.append(str(e)));page.on('console',lambda m:errors.append(m.text[:1600]) if m.type in ['error','warning'] else None)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(url,timeout=120000);page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play" && game.sewers && TERRA_KITS.ready');page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
 transitions=page.evaluate('''async()=>{
 const w=game.world,A=TERRA_ART.terrainContact,built=w.onSurfaceBuilt,unload=w.onSurfaceBeforeUnload;
 const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
 const colours=()=>[...w.chunks].filter(([,r])=>!r.dg).sort(([a],[b])=>a.localeCompare(b)).map(([k,r])=>[k,Array.from(r.meshes.find(m=>m.geometry?.getAttribute('w0')).geometry.getAttribute('color').array)]);
 const before={stats:A.inspect(w),colour:await hash(colours()),keys:[...w.chunks.keys()].sort()},stable=stats=>Object.fromEntries(Object.entries(stats).filter(([k])=>k!=='pendingRanges'));
 const compare=async name=>{const stats=A.inspect(w);if(JSON.stringify(stable(stats))!==JSON.stringify(stable(before.stats))||await hash(colours())!==before.colour||JSON.stringify([...w.chunks.keys()].sort())!==JSON.stringify(before.keys))throw Error(name+' did not restore surface shade');return stats;};
 // Preparing a return can build new surface tiles before activation. Rollback
 // must remove their index entries and restore shadows on surviving buffers.
 const staged=w.prepareDungeonTransition(null,{x:game.p.x+48,z:game.p.z}),duringSurface=A.inspect(w);if(duringSurface.chunks<=before.stats.chunks)throw Error('Rollback fixture did not load new surface tiles');staged.rollback();const surfaceRollback=await compare('Surface rollback');
 const desc={idx:73,theme:'metro',seed:'contact-transition'};
 const entry=w.prepareDungeonTransition(desc);entry.activate();const duringDungeon=A.inspect(w);if(duringDungeon.chunks!==before.stats.chunks)throw Error('Dungeon registered as surface');entry.rollback();const entryRollback=await compare('Entry rollback');
 const ch=w.enterDungeon({...desc,idx:74});if(ch.rooms.length!==16||A.inspect(w).chunks!==before.stats.chunks)throw Error('Ordinary metro changed');w.exitDungeon();const returned=await compare('Metro exit');
 if(w.onSurfaceBuilt!==built||w.onSurfaceBeforeUnload!==unload)throw Error('Native save callbacks replaced');
 if(![...w.chunks.values()].every(r=>r._surfaceOwner===game.p))throw Error('Surface owner missing');
 if(A.totals.fallback)throw Error('Contact fallback');
 return{before,duringSurface,surfaceRollback,duringDungeon,entryRollback,returned,hooksPreserved:true,ownersPreserved:true};
 }''')
 print('Transitions PASS',flush=True)
 loot=page.evaluate('''()=>{
 const w=game.world;if(!w.chunks.has('0,-3'))w.build(0,-3);
 const shelf=w.conts.find(c=>c.type==='shelf'&&!c.looted);if(!shelf)throw Error('Native market shelf missing');
 game.openContainer(shelf);if(!shelf.items?.length)throw Error('Native shelf is empty');const key=shelf.key,items=structuredClone(shelf.items),before={...game.p.inv};
 while(shelf.items.length){const count=shelf.items.length;game.takeLoot(shelf,0);if(shelf.items.length>=count)throw Error('Loot did not transfer')}
 for(const i of items)if(i.id&&game.p.inv[i.id]<(before[i.id]||0)+i.n)throw Error('Inventory did not receive loot');
 if(!shelf.looted||!w.looted.has(key))throw Error('Shelf not marked searched');game.ui.close('loot');
 const saved=game.save();if(!saved?.ok)throw Error('Save refused');const raw=localStorage.getItem('terra_save');if(raw.includes('terrainContact'))throw Error('Transient AO leaked to save');
 return{key,items,inventory:items.filter(i=>i.id).map(i=>({id:i.id,n:game.p.inv[i.id]})),saved:true,owner:shelf.ch._surfaceOwner===game.p};
 }''')
 page.reload(timeout=120000);page.locator('#mContinue').click();page.wait_for_function('key=>game.state==="play" && game.world.looted.has(key)',arg=loot['key']);page.wait_for_function('game.sewers && TERRA_KITS.ready');page.evaluate('game.loop=()=>{}');page.wait_for_timeout(100)
 restored=page.evaluate('''loot=>{
 for(const i of loot.inventory)if(game.p.inv[i.id]<i.n)throw Error('Cold inventory lost loot');
 const w=game.world;if(!w.chunks.has('0,-3'))w.build(0,-3);const shelf=w.conts.find(c=>c.key===loot.key);
 if(!shelf?.looted||shelf.ch._surfaceOwner!==game.p)throw Error('Cold shelf state/owner lost');
 const stats=TERRA_ART.terrainContact.inspect(w);if(stats.chunks!==w.chunks.size||stats.pendingRanges>stats.chunks||TERRA_ART.terrainContact.totals.fallback)throw Error('Cold AO state invalid');
 return{looted:shelf.looted,owner:true,stats,glError:game.ren.getContext().getError()};
 }''',loot)
 assert loot['owner'] and restored['glError']==0 and not errors,(loot,restored,errors)
 report={'transitions':transitions,'loot':loot,'restored':restored,'errors':errors};(out/'report.json').write_text(json.dumps(report,indent=2));b.close()
print('PASS native surface/dungeon rollback and metro return, preserved save callbacks/owners, real loot/save/cold continue; transient AO excluded from profile; JS0/GL0')
