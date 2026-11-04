"""Real-game screenshots and rendering contracts for the shared turret GLB.
Uses disposable placements; source meshes still load through the native loader.
"""
from pathlib import Path
import os
import shutil
from playwright.sync_api import sync_playwright

URL = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/')
OUT = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-turret-art-qa'))
OUT.mkdir(parents=True, exist_ok=True)

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome'),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    errors = []

    def start(page):
        page.set_default_timeout(30000)
        page.on('pageerror', lambda error: errors.append(error.stack))
        page.goto(URL, timeout=120000)
        page.locator('#mNew').click()
        page.locator('#skip').click()
        page.wait_for_function('game.state==="play" && terraDefense.ready')

    def put(page):
        return page.evaluate('''() => {
            const h=game.homePos();game.p.level=6;game.p.camp.tier=5;
            game.p.base=game.p.base.filter(o=>o.t!=="turretB");
            const sites=[];
            for(let x=-24;x<=24;x+=4)for(let z=-24;z<=24;z+=4)sites.push({x:h.x+x,z:h.z+z,d:Math.hypot(x,z)});
            sites.sort((a,b)=>a.d-b.d);
            const site=sites.find(site=>[0,1,2].every(i=>[0,4].every(dz=>game.world.free(site.x+i*3,site.z+dz,1))));
            if(!site)throw Error("No clear 3x2 turret fixture site near camp");
            const rows=[];
            for(const [index,dk] of ["pkm","nail","flame"].entries())for(const lvl of [1,3]) {
                const o={t:"turretB",dk,lvl,mag:0,hp:120,r:0,x:site.x+index*3,z:site.z+(lvl===3?4:0)};
                game.p.base.push(o);rows.push({...o});
            }
            game.p.x=site.x+3;game.p.z=site.z+2;game.baseDirty=true;
            game.aqDone=true;game.qk="med";game.dayT=12;
            window.__turretArt={rows,meshes:()=>game.scene.children.filter(o=>o.isInstancedMesh&&o.name.startsWith("defense-"))};
            return rows;
        }''')

    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    downloads = []
    page.on('request', lambda request: downloads.append(request.url) if request.url.endswith('/assets/defense/turrets.glb') else None)
    start(page)
    rows = put(page)
    page.wait_for_function('__turretArt.meshes().length===12 && __turretArt.meshes().every(o=>o.count===2)')
    assert len(downloads) == 1, downloads
    asset = page.evaluate('''() => {
        const meshes=__turretArt.meshes(),materials=[...new Set(meshes.map(m=>m.material))];
        const scale=(m,slot)=>Math.hypot(...Array.from(m.instanceMatrix.array.slice(slot*16,slot*16+3)));
        return {materials:materials.length,pbr:materials.every(m=>m.isMeshStandardMaterial&&m.map&&m.normalMap&&m.roughnessMap&&m.metalnessMap&&m.aoMap),
            layers:meshes.filter(m=>/-lv[23]$/.test(m.name)).map(m=>({name:m.name,low:scale(m,0),high:scale(m,1)}))};
    }''')
    assert asset['materials'] == 1 and asset['pbr'], asset
    assert len(asset['layers']) == 6 and all(layer['low'] == 0 and layer['high'] > 1 for layer in asset['layers']), asset
    for quality in ['low', 'med', 'high']:
        page.evaluate('(quality)=>game.qk=quality', quality)
        page.wait_for_function('(high)=>__turretArt.meshes().every(o=>o.castShadow===high)', arg=quality == 'high')
    page.evaluate('''() => {
        game.qk="med";
        __turretArt.nativeCamera=game.cameraUpdate;
        game.cameraUpdate=function(dt){__turretArt.nativeCamera.call(this,dt);const f=__turretArt.frame;if(!f)return;
            const y=TERRA_H(f.x,f.z);this.cam.position.set(f.x+f.side,y+f.up,f.z+f.away);
            this.cam.lookAt(f.x,y+.65,f.z);this.cam.updateMatrixWorld(true);};
    }''')
    center = {'x': sum(row['x'] for row in rows) / 6, 'z': sum(row['z'] for row in rows) / 6,
              'side': 6, 'up': 9, 'away': 10}
    for day, label in [(12, 'day'), (23, 'night')]:
        frame_before = page.evaluate('game.frameN')
        page.evaluate('({frame,day})=>{__turretArt.frame=frame;game.dayT=day}', {'frame': center, 'day': day})
        page.wait_for_function('(before)=>game.frameN>=before+3', arg=frame_before)
        page.screenshot(path=str(OUT / f'{label}-levels-1-and-3.png'))
    for row in rows:
        if row['lvl'] != 3:
            continue
        frame = {**row, 'side': 2.6, 'up': 2.5, 'away': 3.4}
        frame_before = page.evaluate('game.frameN')
        page.evaluate('(frame)=>{__turretArt.frame=frame;game.dayT=12}', frame)
        page.wait_for_function('(before)=>game.frameN>=before+3', arg=frame_before)
        page.screenshot(path=str(OUT / (row['dk'] + '-close.png')))

    # Aiming writes only the gun matrix; the static base/layers retain main's cache policy.
    page.evaluate('''() => {
        game.cameraUpdate=__turretArt.nativeCamera;
        const turret=game.p.base.find(o=>o.t==="turretB"&&o.dk==="pkm"&&o.lvl===1);
        turret.mag=60;game.baseDirty=true;
        __turretArt.shooter=turret;
    }''')
    page.wait_for_timeout(500)
    before = page.evaluate('''() => {
        const meshes=__turretArt.meshes().filter(o=>o.name.startsWith("defense-pkm"));
        __turretArt.beforeVersions=meshes.map(o=>({name:o.name,version:o.instanceMatrix.version}));
        const o=__turretArt.shooter;
        let point=null;
        for(let i=0;i<16;i++){const a=i*Math.PI/8,x=o.x+Math.sin(a)*5,z=o.z+Math.cos(a)*5;
            if(game.world.free(x,z,.6)&&game.world.segHit(o.x,o.z,x,z,2.7)<0){point={x,z};break;}}
        if(!point)throw Error("No clear target position in fixture");
        const enemy=game.spawnEnemy("zombie",point.x,point.z,{force:1,aggro:1});enemy.spd=0;enemy.dmg=0;enemy.hp=enemy.maxHp=10000;
        return terraDefense._debug().stats.shots;
    }''')
    page.wait_for_function('(before)=>terraDefense._debug().stats.shots>before', arg=before)
    versions = page.evaluate('''() => __turretArt.beforeVersions.map(before=>({name:before.name,
        changed:__turretArt.meshes().find(o=>o.name===before.name).instanceMatrix.version>before.version}))''')
    assert all(item['changed'] == item['name'].endswith('-gun') for item in versions), versions
    page.close()

    # Model completion after entering a dungeon must not flash surface turrets underground.
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    held = []
    page.route('**/assets/defense/turrets.glb', lambda route: held.append(route))
    start(page)
    put(page)
    page.wait_for_function('game.world.ents.some(e=>e.sewer)')
    page.evaluate('''() => {const entry=game.world.ents.find(e=>e.sewer);
        game.p.x=entry.x;game.p.z=entry.z;game.camT=null;game.useEntrance(entry);}''')
    page.wait_for_function('game.world.inDungeon && !game.dungeonTransition')
    assert len(held) == 1, held
    held[0].continue_()
    page.wait_for_function('__turretArt.meshes().length===12')
    assert page.evaluate('__turretArt.meshes().every(o=>!o.visible)'), 'Late-loaded surface models visible underground'
    page.screenshot(path=str(OUT / 'dungeon-late-load.png'))
    page.evaluate('game.exitDungeon()')
    page.wait_for_function('!game.world.inDungeon && !game.dungeonTransition')
    page.wait_for_function('__turretArt.meshes().every(o=>o.visible)')
    assert not errors, errors
    print('PASS: shared PBR textures, single download, level layers, low/med/high shadows, gun-only matrix updates, native firing, dungeon late-load/exit; day/night game screenshots; JS errors 0')
    browser.close()
