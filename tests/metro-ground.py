"""Station support uses native rendered/walking terrain without changing borders.

Optional TERRA_BASELINE_MODULE points to a prior metro-entrance.js for recording
the original metadata and border references in a disposable browser profile.
"""
import json
import os
from pathlib import Path
from playwright.sync_api import sync_playwright

# v0.4.16 references: coordinates, collisions, points, pads, RNG and borders.
EXPECTED = {
    '1,1': {'metadata': '1cfb10385ce15ce3da2197641a07d78d765a9f536080e7f1419b6e1ba44d03fd',
            'border': '4ea97c6a2889ccdfc449cf666a410a4da4fbaaab50f2c4362db6e197c964a4e7'},
    '1,-2': {'metadata': 'b3eeb505d0b184df49202924be186d5b8cab583057c2adb344eccb2c9c41bd55',
             'border': 'fe543cc6b715f4914ae2a8dbe251bae3e106acc8ac98cbae8b1b7cc29150ad7b'},
    '2,1': {'metadata': '7224d4ac475760b2269d6e87048ad43338a7469aa13c9ae43e8923daa5982da0',
            'border': '698a8f31951ca8eb47eb1ecb80e58da14d0da97e9241ecc1977ee11fba8bfea1'},
}
out = Path(os.environ.get('TERRA_QA_OUTPUT', '/tmp/terra-metro-ground-qa'))
out.mkdir(parents=True, exist_ok=True)
baseline = os.environ.get('TERRA_BASELINE_MODULE')
with sync_playwright() as p:
    browser = p.chromium.launch(executable_path='/usr/bin/chromium', args=[
        '--use-angle=swiftshader', '--enable-unsafe-swiftshader'])
    page = browser.new_page(viewport={'width': 1280, 'height': 800}, has_touch=True)
    page.set_default_timeout(60000)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    if baseline:
        page.route('**/ui/metro-entrance.js', lambda route: route.fulfill(
            path=baseline, content_type='application/javascript'))
    page.goto(os.environ.get('TERRA_TEST_URL', 'http://127.0.0.1:8180/play/'), timeout=120000)
    page.locator('#mNew').click()
    page.locator('#skip').click()
    page.wait_for_function('game.sewers && game.state==="play"')
    report = page.evaluate('''async()=>{
      const C=TERRA_SEWER_BRIDGE.Chunk,metro=C.prototype.metro;
      const hash=async data=>[...new Uint8Array(await crypto.subtle.digest('SHA-256',
        new TextEncoder().encode(JSON.stringify(data))))].map(v=>v.toString(16).padStart(2,'0')).join('');
      const result={};
      for(const [cx,cz] of [[1,1],[1,-2],[2,1]]){
        let station=null;
        C.prototype.metro=function(x,z,kind,name){
          const start=this.s.p.length,r=metro.apply(this,arguments);
          if(kind==='metro')station={x,z,deck:Math.max(...this.s.p.slice(start,start+162).filter((v,i)=>i%3===1))};
          return r;
        };
        const c=new C(cx,cz);
        try{c.build()}finally{C.prototype.metro=metro}
        const metadata={cols:c.cols,conts:c.conts,nodes:c.nodes,spawns:c.spawns,
          entries:c.ents,map:c.map,tps:c.tps,pads:c.pads,next:[c.r(),c.r(),c.r(),c.r()]};
        const border=[],xs=c.T.xs,n=xs.length;
        for(let z=0;z<n;z++)for(let x=0;x<n;x++)if(xs[x]<=2||xs[x]>=46||xs[z]<=2||xs[z]>=46)
          border.push(c.T.hg[z*n+x],c.T.hv[z*n+x]);
        for(let i=0;i<c.tr.p.length;i+=3){const x=c.tr.p[i],z=c.tr.p[i+2];
          if(x===c.ox||x===c.ox+48||z===c.oz||z===c.oz+48)
            border.push(...c.tr.p.slice(i,i+3),...c.tr.n.slice(i,i+3));
        }
        if(station){
          const visual=[],walking=[];
          for(let x=station.x-1.8;x<station.x+1.8;x+=.2)
            for(let z=station.z-2.8;z<station.z+3;z+=.2){visual.push(c.lerpG(c.T.hv,x,z));walking.push(c.hAt(x,z))}
          station.visualMax=Math.max(...visual);station.visualMin=Math.min(...visual);
          station.walkDifference=Math.max(...visual.map((v,i)=>Math.abs(v-walking[i])));
          station.ground=c.hAt(station.x,station.z);
          const paving=[],ground=[];
          const cross=(a,b,p)=>(b[0]-a[0])*(p[2]-a[2])-(b[2]-a[2])*(p[0]-a[0]);
          const inside=p=>p[0]>=station.x-2.19&&p[0]<=station.x+2.19&&p[2]>=station.z+3.51&&p[2]<=station.z+6.29;
          for(let i=0;i<c.tr.p.length;i+=9)ground.push([0,3,6].map(o=>c.tr.p.slice(i+o,i+o+3)));
          function renderedHeight(p){
            for(const [a,b,d] of ground){const area=cross(a,b,d);
              const w=[cross(b,d,p)/area,cross(d,a,p)/area,cross(a,b,p)/area];
              if(w.every(v=>v>=-1e-8))return a[1]*w[0]+b[1]*w[1]+d[1]*w[2];
            }
            return NaN;
          }
          let normals=true;
          for(const b of c.kb?.bld||[])for(let i=0;i<b.i.length;i+=3){
            const triangle=b.i.slice(i,i+3).map(v=>b.p.slice(v*3,v*3+3));
            if(!triangle.every(inside)||Math.abs(cross(...triangle))<1e-10)continue;
            const center=[0,1,2].map(k=>triangle.reduce((sum,p)=>sum+p[k],0)/3);
            for(const p of [...triangle,center])paving.push(p[1]-renderedHeight(p));
            for(const v of b.i.slice(i,i+3))normals&&=Math.abs(Math.hypot(...b.n.slice(v*3,v*3+3))-1)<1e-5;
          }
          station.pavingError=Math.max(...paving.map(v=>Math.abs(v-.025)));
          station.pavingCount=paving.length;station.pavingNormals=normals;
        }
        result[cx+','+cz]={metadata:await hash(metadata),border:await hash(border),station};
      }
      return result;
    }''')
    print(json.dumps(report, ensure_ascii=False), flush=True)
    if baseline:
        assert not errors, errors
        browser.close()
        raise SystemExit(0)
    for key, reference in EXPECTED.items():
        assert report[key]['metadata']==reference['metadata'], (key, 'metadata changed', report[key])
        assert report[key]['border']==reference['border'], (key, 'border changed', report[key])
    for key in ['1,1', '1,-2']:
        station = report[key]['station']
        assert station and station['visualMax'] < station['deck']-.1, station
        assert station['visualMax']-station['visualMin'] < 1e-6, station
        assert station['walkDifference'] < 1e-6 and station['pavingCount']>0 and station['pavingError'] < 1e-5 and station['pavingNormals'], station
    guards = page.evaluate('''()=>{
      const C=TERRA_SEWER_BRIDGE.Chunk,result=[];
      for(const mode of ['edge','existing-pad','wet','basement']){
        const a=new C(1,1),b=new C(1,1);a.prep();b.prep();
        if(mode==='existing-pad'){a.pad(86,78,94,86);b.pad(86,78,94,86)}
        if(mode==='wet')a.wet=()=>true;
        a.metro(mode==='edge'?95:90,82,mode==='basement'?'basement':'metro','Тест');
        a.terrain();b.terrain();
        result.push({mode,same:[...a.grid].every((v,i)=>v===b.grid[i]),pads:a.pads.length===b.pads.length});
      }
      return result;
    }''')
    assert all(v['same'] and v['pads'] for v in guards), guards
    station = report['1,1']['station']
    page.wait_for_function('game.world.ents.some(e=>e.kind==="metro"&&e.x===90)')
    assert abs(page.evaluate('TERRA_H(90,82)')-station['ground']) < 1e-6, 'Walking cache differs from generated ground'
    page.evaluate('game.p.x=90;game.p.z=83.7;game.p.hp=game.p.maxHp=10000;game.camT=null')
    page.wait_for_timeout(6000)
    page.screenshot(path=str(out / 'station-desktop.png'))
    page.set_viewport_size({'width': 390, 'height': 844})
    page.wait_for_timeout(600)
    page.screenshot(path=str(out / 'station-portrait.png'))
    assert not errors, errors
    print('PASS station ground: rendered/walking height, fitted paving, metadata/RNG, borders, edge/overlap/wet/basement guards; JS0')
    browser.close()
