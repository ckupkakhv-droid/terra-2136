"""Проверка кадра куклы на разных DPR и восстановления renderer после draw.
Сервер из корня репозитория; TERRA_TEST_URL по умолчанию http://127.0.0.1:8080/play/.
"""
from pathlib import Path
import os, shutil
from playwright.sync_api import sync_playwright

out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-backpack-preview'))
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=os.environ.get('TERRA_CHROMIUM') or shutil.which('google-chrome') or shutil.which('chromium'), args=['--use-angle=swiftshader', '--enable-unsafe-swiftshader', '--disable-dev-shm-usage'])
    page = browser.new_page(viewport={'width':1280,'height':800})
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8080/play/'), wait_until='load', timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function("game.state==='play'")
    page.keyboard.press('KeyI')
    page.wait_for_function('game.ui.equipmentPreview?.inst')
    for name,w,h,dpr in [('desktop',1280,800,.75),('portrait',390,844,1.1),('landscape',844,390,2)]:
        page.set_viewport_size({'width':w,'height':h})
        page.wait_for_timeout(200)
        result = page.evaluate('''dpr => {
          const p=game.ui.equipmentPreview,r=game.ren;
          r.setPixelRatio(dpr);
          const state=()=>({viewport:r.getViewport(p.target.viewport.clone()).toArray(),
            scissor:r.getScissor(p.target.scissor.clone()).toArray(),test:r.getScissorTest(),
            alpha:r.getClearAlpha(),auto:r.autoClear,pixelRatio:r.getPixelRatio()});
          const target=r.getRenderTarget(), before=JSON.stringify(state());
          p.draw();
          const restored=target===r.getRenderTarget()&&before===JSON.stringify(state());
          const c=p.canvas, data=c.getContext('2d').getImageData(0,0,c.width,c.height).data;
          let minX=c.width,minY=c.height,maxX=-1,maxY=-1;
          for(let y=0;y<c.height;y++) for(let x=0;x<c.width;x++) if(data[(y*c.width+x)*4+3]>24){
            minX=Math.min(minX,x);maxX=Math.max(maxX,x);minY=Math.min(minY,y);maxY=Math.max(maxY,y);
          }
          return {restored,top:minY,bottom:c.height-1-maxY,left:minX,right:c.width-1-maxX,span:(maxY-minY)/c.height};
        }''',dpr)
        assert result['restored'], result
        assert min(result[k] for k in ['top','bottom','left','right'])>=3,result
        assert result['span']>.5,result
        print(name,dpr,result,flush=True)
        page.screenshot(path=str(out/(name+'.png')))
    page.keyboard.press('Escape')
    page.wait_for_function("game.state==='play'")
    page.wait_for_timeout(300)
    page.screenshot(path=str(out/'world-after-preview.png'))
    assert not errors,errors
    browser.close()
    print('PASS кадр, состояние renderer, возврат в игру')
