from pathlib import Path
from playwright.sync_api import sync_playwright
import base64,os
# Optional developer tool. Uses only the existing GLB, loader and renderer.
out=Path(os.environ.get('TERRA_ART_OUTPUT','/tmp/terra-gun-renders'));out.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path='/usr/bin/chromium',args=['--use-angle=swiftshader','--enable-unsafe-swiftshader','--disable-dev-shm-usage']);page=b.new_page();page.set_default_timeout(90000)
 page.add_init_script("localStorage.setItem('terra_set',JSON.stringify({q:'med',post:false,dpr:1}))")
 page.goto(os.environ.get('TERRA_TEST_URL','http://127.0.0.1:8180/play/'),timeout=120000);page.locator('#mNew').click();page.locator('#skip').click();page.wait_for_function('game.state==="play"&&terraDefense.ready&&document.querySelector("#food").textContent.trim()');page.evaluate('game.loop=()=>{}')
 results=page.evaluate('''async()=>{
 const c=TERRA_DEFENSE_CTX,loader=new c.G();loader.setMeshoptDecoder(c.M);const gltf=await loader.loadAsync('assets/defense/turrets.glb');
 const r=new game.ren.constructor({alpha:true,antialias:true,preserveDrawingBuffer:true});r.setSize(512,340);r.setPixelRatio(1);r.setClearColor(0,0);r.toneMapping=game.ren.toneMapping;r.toneMappingExposure=1.4;
 const output={};for(const kind of ['pkm','nail','flame'])for(const level of [1,2,3]){const scene=new game.scene.constructor(),root=gltf.scene.getObjectByName(kind).clone(true);scene.add(root);
 root.traverse(m=>{const tier=m.name.match(/lv([23])/);if(tier)m.visible=+tier[1]<=level;});scene.updateMatrixWorld(true);
 let box=null;root.traverse(m=>{if(!m.isMesh||!m.visible||m.parent&&!m.parent.visible)return;m.geometry.computeBoundingBox();const bb=m.geometry.boundingBox.clone().applyMatrix4(m.matrixWorld);if(!box)box=bb;else box.union(bb);});
 const center=box.getCenter(new c.V()),size=box.getSize(new c.V());const cam=game.cam.clone();cam.aspect=512/340;cam.fov=33;cam.zoom=2.1;cam.left=-1.7;cam.right=1.7;cam.top=1.13;cam.bottom=-1.13;cam.near=.01;cam.far=100;cam.position.copy(center).add(new c.V(2.8,1.8,3.7).multiplyScalar(Math.max(size.x,size.y,size.z)*.78));cam.lookAt(center);cam.updateProjectionMatrix();
 const lights=[];game.scene.traverse(o=>{if(o.isHemisphereLight||o.isDirectionalLight){const l=o.clone();l.intensity=o.isHemisphereLight?2.7:3.5;l.castShadow=false;lights.push(l);}});scene.add(...lights);r.render(scene,cam);output[kind+'-'+level]=r.domElement.toDataURL('image/webp',.83);
 }r.dispose();return output;
 }''')
 for k,v in results.items():
  raw=base64.b64decode(v.split(',')[1]);(out/(k+'.webp')).write_bytes(raw);print(k,len(raw),flush=True)
 b.close()
