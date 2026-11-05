"""Compare published tree gameplay metadata and render all replacement models.

Serve the published 0.4.22 standalone HTML separately and set
TERRA_BASELINE_URL; TERRA_TEST_URL points to the working game or standalone.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

baseline = os.environ.get('TERRA_BASELINE_URL', 'http://127.0.0.1:8181/terra-v22.html')
updated = os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/')
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-nature-qa'))
out.mkdir(exist_ok=True)
reports = []
with sync_playwright() as p:
    for label, url in [('before', baseline), ('after', updated)]:
        browser = p.chromium.launch(executable_path='/usr/bin/chromium',
            args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
        page = browser.new_page(viewport={'width': 1280, 'height': 900})
        page.set_default_timeout(90000)
        page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.on('console', lambda m: errors.append(m.text[:1400]) if m.type == 'error' else None)
        page.goto(url, timeout=120000)
        page.locator('#mNew').click()
        page.locator('#skip').click()
        page.wait_for_function('game.sewers && game.state==="play"')
        page.evaluate('game.loop=()=>{}')
        page.wait_for_timeout(100)
        report = page.evaluate('''async()=>{
          const C=TERRA_SEWER_BRIDGE.Chunk,result={chunks:[],firstModel:TERRA_PROPS.idx.qn_commontree_1.t};
          const hash=async v=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',new TextEncoder().encode(JSON.stringify(v))))].map(v=>v.toString(16).padStart(2,'0')).join('');
          for(const [x,z] of [[0,0],[1,0],[-1,0],[0,1],[0,-1],[1,1],[-1,-1],[-1,1],[1,-1]]) {
            const c=new C(x,z);c.build();
            result.chunks.push({key:x+','+z,meta:await hash({cols:c.cols,conts:c.conts,nodes:c.nodes,
              brk:c.brk,spawns:c.spawns,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r()]})});
          }
          game.ixInit();game.ixR.U.uTime.value=0;game.ixR.U.uCut.value=0;game.ixR.U.uFellN.value=0;
          const meshes=[...game.world.chunks.values()].flatMap(c=>c.meshes);
          const fol=meshes.find(m=>m.geometry?.attributes.terraLeaf)?.material;
          const stat=meshes.find(m=>m.geometry?.attributes.mt)?.material;
          if(!fol||!stat)throw Error('Native materials unavailable');
          const scene=new game.scene.constructor();scene.background=game.scene.background.clone();
          scene.add(game.hemi.clone());const sun=game.sun.clone();sun.position.set(0,28,36);
          sun.target.position.set(16,0,18);sun.intensity=2.4;scene.add(sun,sun.target);
          sun.shadow.camera.left=-27;sun.shadow.camera.right=27;sun.shadow.camera.top=27;sun.shadow.camera.bottom=-27;
          sun.shadow.camera.near=1;sun.shadow.camera.far=100;sun.shadow.camera.updateProjectionMatrix();
          const c=new C(1,1);c.prep();c.anc=1;c.hAt=()=>0;c.setOY(0);c.f.sw=.09;
          result.models=[];
          for(let row=0;row<4;row++)for(let col=0;col<(row===3?3:5);col++) {
            const name=['qn_commontree_','qn_pine_','qn_deadtree_','qn_twistedtree_'][row]+(col+1);
            const start=c.f.p.length;c.f.prop(name,(col+(row===3?1:0))*8,0,row*12,.25,6.2,1);
            result.models.push({name,triangles:(c.f.p.length-start)/9});
          }
          c.s.mt=-1;c.s.add(TERRA_SEWER_BRIDGE.shapes.box,16,-.15,18,43,.3,50,'#41493c',0,0,0,0);
          const floor=c.s.mesh(stat),trees=c.f.mesh(fol);floor.receiveShadow=true;trees.castShadow=true;
          scene.add(floor,trees);const cam=game.cam.clone();cam.position.set(16,52,80);cam.lookAt(16,3,18);
          cam.zoom=1;cam.updateProjectionMatrix();game.ren.shadowMap.enabled=true;
          window.__natureScene=scene;window.__natureCam=cam;window.__natureTrees=trees;
          game.ren.info.reset();game.post.render(scene,cam,0);
          result.render={calls:game.ren.info.render.calls,triangles:game.ren.info.render.triangles,error:game.ren.getContext().getError()};
          return result;
        }''')
        if label == 'before':
            assert report['firstModel'] == 900, 'Baseline must be published 0.4.22'
        else:
            assert report['firstModel'] != 900, 'Replacement archive was not loaded'
            assert report['chunks'] == reports[0]['chunks'], 'World metadata or RNG changed'
            for a, b in zip(reports[0]['models'], report['models']):
                assert a['name'] == b['name'] and 0 < b['triangles'] <= a['triangles'], (a, b)
            assert report['render']['calls'] == reports[0]['render']['calls']
        assert report['render']['error'] == 0
        page.add_style_tag(content='body > :not(canvas){visibility:hidden!important}')
        page.screenshot(path=str(out / ('models-' + label + '.png')))
        page.evaluate('''()=>{
          __natureTrees.visible=false;
          const node={k:'wood',x:16,z:12,tree:{k:'qn_commontree_1',x:16,z:12,y:0,h:8,tint:1,ry:.2}};
          const proxy=game.ixTreeProxy(node);__natureScene.add(proxy.mesh);
          proxy.fall={th:.65,w:.45,dir:.3,t:0,landed:false};game.ixTrees(1/60);
          window.__natureProxy=proxy;__natureCam.position.set(16,12,30);__natureCam.lookAt(16,3,12);
          __natureCam.zoom=1.15;__natureCam.updateProjectionMatrix();game.post.render(__natureScene,__natureCam,0);
        }''')
        report['fall'] = page.evaluate('''()=>({matrix:[...__natureProxy.mesh.matrix.elements],
          flags:__natureProxy.mesh.geometry.getAttribute('terraLeaf')?.count||0,
          vertices:__natureProxy.mesh.geometry.getAttribute('position').count,
          shadows:!!__natureProxy.mesh.customDepthMaterial&&!!__natureProxy.mesh.customDistanceMaterial,
          error:game.ren.getContext().getError()})''')
        page.screenshot(path=str(out / ('fall-' + label + '.png')))
        if label == 'after':
            assert report['fall']['matrix'] == reports[0]['fall']['matrix']
        assert report['fall']['flags'] == report['fall']['vertices'] and report['fall']['shadows']
        assert report['fall']['error'] == 0 and not errors, errors
        report['errors'] = errors
        reports.append(report)
        (out / (label + '.json')).write_text(json.dumps(report, indent=2))
        print(label, report['render'], 'models', len(report['models']), 'JS0', flush=True)
        browser.close()
print('PASS 9 chunks metadata/RNG, 18 native models/budgets, shared render batches, native falling pose')
