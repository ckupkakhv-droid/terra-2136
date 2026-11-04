"""Native render-camera lease with a disposable, teleported character.
This inspects staging and cancellation; it does not exercise reward writes.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright, expect

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-sewer-camera-qa'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('chromium') or shutil.which('google-chrome'),
        args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 800})
    page.set_default_timeout(30000)
    errors = []
    page.on('pageerror', lambda error: errors.append(error.stack))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), timeout=90000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game.sewers && game.glb.sewer_mutant')
    page.evaluate('game.p.x=12;game.p.z=-10;game.camT=null')
    page.locator('#sewerAction').click()
    page.wait_for_function('game.dg?.sewer && !game.dungeonTransition')
    page.evaluate('''async () => {
        const {installRaphael}=await import('./ui/sewer-raphael.js');
        const {showRecording}=await import('./ui/sewer-cinematic.js');
        const {leaseSewerCamera}=await import('./ui/sewer-camera.js');
        const room=game.dg.ch.rooms[6];game.p.x=room.x;game.p.z=room.z;game.camT=null;
        for(let i=game.enemies.length-1;i>=0;i--)game.removeEnemy(i);
        const subject=installRaphael(game,TERRA_SEWER_BRIDGE).spawn(room.x,room.z+3);
        subject.dmg=0;game.cameraUpdate(1);
        const post=game.post,original=post.render,probe={count:0,camera:null};
        function recordingRender(scene,camera,time){probe.count++;probe.camera=camera;return original.call(this,scene,camera,time);}
        post.render=recordingRender;
        const snapshot=()=>({position:game.cam.position.toArray(),quaternion:game.cam.quaternion.toArray(),
            camT:game.camT?.toArray(),camY:game.camY,camZoom:game.camZoom,shake:game.shakeA,plane:game.plane.constant});
        const nativeLights=()=>[game.muzzle,game.boomL,game.hemi].map(light=>({uuid:light.uuid,
            color:light.color.getHex(),intensity:light.intensity,position:light.position.toArray(),
            shadow:light.castShadow,distance:light.distance,decay:light.decay}));
        const lights=()=>game.world.scene.children.filter(light=>light.userData?.sewerCinematicLight);
        window.cameraQA={subject,probe,post,recordingRender,snapshot,nativeLights,lights,finished:0,show(){
            this.before=JSON.stringify(snapshot());
            this.lightBefore=JSON.stringify(nativeLights());
            this.recording=showRecording(game,'Я — Рафаэль. Последний из клана.',{subject,
                heading:'ВСТРЕЧА · ПОСЛЕДНИЙ ИЗ КЛАНА',skipLabel:'К бою',finishLabel:'Начать бой',
                frames:[['ШАГИ ЗА ВОДОСБРОСОМ','Из темноты выходит охотник в красной повязке. В руках — два сая.'],
                    ['РАФАЭЛЬ','AGI забрал моих братьев и учителя. Из зелёного клана остался я.'],
                    ['НЕ ТРОГАЙ КРЫС','Уходите с линии рывка и бейте, пока охотник восстанавливается.']],
                onFinish:()=>this.finished++});
            return !!this.recording.camera;
        }};
        if(leaseSewerCamera({...game,post:null},subject)!==null)throw Error('Missing-post fallback failed');
        const absent={...subject,inst:null,mdl:'absent',base:'absent'};
        if(leaseSewerCamera({...game,enemies:[absent],glb:{}},absent)!==null)throw Error('Missing-model fallback failed');
        if(!cameraQA.show())throw Error('Native subject camera was not acquired');
    }''')
    page.wait_for_function('cameraQA.probe.camera === cameraQA.recording.camera.camera')
    assert page.evaluate('''() => {
        const e=cameraQA.subject, meshes=[];
        e.inst.root.traverse(n=>{if(n.isMesh)meshes.push(n);});
        return meshes.length===1 && meshes[0].isSkinnedMesh &&
            meshes[0].skeleton.bones.length===53 && !!meshes[0].material.map &&
            !!meshes[0].material.normalMap && e.sc===1.05 &&
            ['idle','walk','run','attack','attack2','hit','death','scream','emerge'].every(k=>!!e.inst.A[k]);
    }'''), 'Authored model, texture/normal map, skeleton or clips missing'
    expect(page.locator('#hud')).not_to_be_visible(timeout=30000)
    assert page.evaluate('cameraQA.before === JSON.stringify(cameraQA.snapshot())'), 'Native follow camera changed in modal'
    assert page.evaluate('cameraQA.lights().length===1 && cameraQA.lights()[0].isPointLight && !cameraQA.lights()[0].castShadow')
    assert page.evaluate('cameraQA.lightBefore === JSON.stringify(cameraQA.nativeLights())'), 'Native lighting was mutated'
    framing = page.evaluate('''() => {
        const {subject,probe}=cameraQA,c=probe.camera;
        const point=y=>{const v=subject.inst.root.position.clone();v.y+=y;v.project(c);return {x:(v.x+1)*game.W/2,y:(1-v.y)*game.H/2};};
        return {head:point(1.87),feet:point(0),card:document.querySelector('.recordingCard').getBoundingClientRect().top};
    }''')
    assert 0 < framing['head']['x'] < 1280 and 0 < framing['head']['y'] < framing['card'], framing
    assert framing['feet']['y'] - framing['head']['y'] > 70, framing
    page.screenshot(path=str(out / 'raphael-camera.png'))
    page.locator('#recordingSkip').click()
    expect(page.locator('#sewerRecording')).to_have_count(0, timeout=30000)
    expect(page.locator('#hud')).to_be_visible(timeout=30000)
    page.wait_for_function('!!cameraQA.subject.inst._rim')
    assert page.evaluate('cameraQA.subject.inst.mats.every(m=>!!m.normalMap && !!m.map)'), 'Native boss rim lost textures'
    assert page.evaluate('game.state === "play" && game.post.render === cameraQA.recordingRender && !cameraQA.recording.camera.active')
    assert page.evaluate('cameraQA.lights().length===0'), 'Cinematic light survived skip'
    assert page.evaluate('cameraQA.finished') == 1

    page.emulate_media(reduced_motion='reduce')
    page.evaluate('cameraQA.show()')
    page.wait_for_function('cameraQA.probe.camera === cameraQA.recording.camera.camera')
    still = page.evaluate('cameraQA.probe.camera.position.toArray()')
    for _ in range(2):
        count = page.evaluate('cameraQA.probe.count')
        page.locator('#recordingNext').click()
        page.wait_for_function('(n)=>cameraQA.probe.count>n', arg=count)
        assert page.evaluate('cameraQA.probe.camera.position.toArray()') == still
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_function('Math.abs(cameraQA.probe.camera.aspect-390/844)<.00001')
    page.screenshot(path=str(out / 'raphael-camera-portrait.png'))
    page.locator('#recordingNext').click()
    expect(page.locator('#sewerRecording')).to_have_count(0, timeout=30000)
    assert page.evaluate('game.state === "play" && game.post.render === cameraQA.recordingRender && cameraQA.finished===2')
    assert page.evaluate('cameraQA.lights().length===0'), 'Cinematic light survived completion'

    page.evaluate('cameraQA.show();const panel=document.createElement("section");panel.id="cameraExternalModal";panel.className="modal";panel.style.cssText="position:fixed;inset:0";document.body.append(panel)')
    expect(page.locator('#sewerRecording')).to_have_count(0, timeout=30000)
    assert page.evaluate('game.state === "modal" && game.post.render === cameraQA.recordingRender && cameraQA.finished===2')
    assert page.evaluate('cameraQA.lights().length===0'), 'Cinematic light survived modal takeover'
    page.evaluate('''() => {document.getElementById("cameraExternalModal").remove();game.state="play";cameraQA.show();
        cameraQA.replacement=function(...args){return cameraQA.recordingRender.apply(this,args)};
        game.post.render=cameraQA.replacement;}''')
    expect(page.locator('#sewerRecording')).to_have_count(0, timeout=30000)
    assert page.evaluate('game.state === "play" && !cameraQA.recording.camera.active && game.post.render === cameraQA.replacement && cameraQA.finished===2')
    assert page.evaluate('cameraQA.lights().length===0'), 'Cinematic light survived renderer takeover'
    page.evaluate('game.post.render=cameraQA.recordingRender;cameraQA.show();cameraQA.oldPlayer=game.p;game.p={...game.p}')
    expect(page.locator('#sewerRecording')).to_have_count(0, timeout=30000)
    assert page.evaluate('game.state === "modal" && !cameraQA.recording.camera.active && game.post.render === cameraQA.recordingRender && cameraQA.finished===2')
    assert page.evaluate('cameraQA.lights().length===0'), 'Cinematic light survived player replacement'
    page.evaluate('game.p=cameraQA.oldPlayer;game.state="play";cameraQA.show();game.p.alive=false')
    expect(page.locator('#sewerRecording')).to_have_count(0, timeout=30000)
    assert page.evaluate('game.state !== "play" && !cameraQA.recording.camera.active && game.post.render === cameraQA.recordingRender && cameraQA.finished===2')
    assert page.evaluate('cameraQA.lights().length===0'), 'Cinematic light survived death'
    assert not errors, errors
    print('PASS: real arena boss framed/lit; native camera/follow/lights unchanged; HUD hides/restores; skip, finish, reduced motion, resize, renderer/modal/player/death cancellation; light cleanup; no JS errors')
    browser.close()
