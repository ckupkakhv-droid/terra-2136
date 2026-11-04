/* Surface architecture uses the native chunk builder and its shared instanced
 * geometries. Entries, collision and fast-travel identifiers stay native. */
const installed = new WeakSet();
export function installMetroArchitecture(bridge) {
  const proto=bridge?.Chunk?.prototype, L=bridge?.shapes;
  if (!proto || installed.has(proto) || !L?.cyl5 || !L?.sph || !L?.box) return;
  const original=proto.metro;
  if (typeof original!=='function') return;
  proto.metro=function(x,z,kind,name) {
    if(kind!=='metro') return original.call(this,x,z,kind,name);
    const s=this.s;
    // Build one level structure even on sloped terrain. The embedded pavement
    // fills the ground edge; restore all shared builders before other scenery.
    const saved=[s.oy,this.g.oy,this.n.oy], random=s.r, ground=s.Y(x,z);
    s.oy=this.g.oy=this.n.oy=ground;
    s.r=()=>.5;
    try {
    // Weathered pavement, deep shadow and descending treads: visual only.
    s.box(x,0,z,6,.12,7,'#575b55');
    s.box(x,.015,z+.5,4,.06,5,'#131916');
    for(let i=0;i<7;i++) {
      const zz=z+2.35-i*.7,yy=.045+i*.025;
      s.box(x,yy,zz,3.75,.065,.46,i%2?'#565a50':'#62655a');
      s.box(x,yy+.037,zz-.19,3.75,.018,.035,'#989180');
    }
    // Low retaining walls have separate caps, joints and weathered edges.
    for(const side of [-1,1]) {
      s.box(x+side*2.6,0,z,.4,1.1,7,'#6a6b5e');
      s.box(x+side*2.6,1.08,z,.56,.12,7.1,'#999589');
      for(const dz of [-2.6,-.9,.9,2.6]) s.box(x+side*2.36,.63,z+dz,.045,.52,.035,'#414943');
      // Handrail stays inside the existing retaining-wall collision boundary.
      for(const dz of [-2.2,-.4,1.4,2.8]) s.add(L.cyl5,x+side*2.22,1.05,z+dz,.055,1.1,.055,'#514a3d');
      s.add(L.cyl5,x+side*2.22,1.62,z+.3,.07,5.2,.07,'#a18b66',0,Math.PI/2);
    }
    s.box(x,0,z-3.3,5.6,1.1,.4,'#66695f');
    s.box(x,1.08,z-3.3,5.8,.12,.55,'#999589');
    // The back arch is open toward the actual interaction point at z+1.5.
    for(const side of [-1,1]) {
      s.box(x+side*2.15,1.1,z-3.1,.34,2.25,.4,'#535c52');
      s.box(x+side*2.15,3.22,z-3.1,.5,.15,.55,'#8b8e7b');
    }
    s.box(x,3.27,z-3.1,4.8,.28,.5,'#777a6c');
    s.box(x,3.42,z-3.1,5,.08,.6,'#a5a08b');
    for(const side of [-1,1]) s.add(L.cyl5,x+side*1.45,2.75,z-3.05,.045,1.9,.045,'#776f5c');
    // Reuse the existing red route marker and sign atlas; no new textures.
    s.add(L.cyl5,x-3.2,1.8,z+3,.16,3.6,.16,'#5a5a52');
    this.g.add(L.sph,x-3.2,3.9,z+3,.46,.46,.46,'#b84732');
    this.sign(x,2.6,z+3.6,4.2,.7,32,0,-.6);
    } finally {
      [s.oy,this.g.oy,this.n.oy]=saved;
      s.r=random;
    }
    // Original metro consumed twelve surface-builder colour samples before
    // its vines; preserve the world's seeded random stream for later objects.
    for(let i=0;i<12;i++)this.r();
    this.col(x-2.8,z-3.5,x-2.4,z+3.5,1.1);
    this.col(x+2.4,z-3.5,x+2.8,z+3.5,1.1);
    this.col(x-2.8,z-3.5,x+2.8,z-3.1,1.1);
    for(let i=0;i<3;i++)this.vine(x+this.R(-2,2),z-3.1,this.R(.6,1.1),4,Math.PI,.41);
    this.ents.push({x,z:z+1.5,kind,name});
    this.map.push({x0:x-3,z0:z-3.5,x1:x+3,z1:z+3.5,c:'#ff3a3a'});
    this.tps.push({id:'m'+this.cx+'_'+this.cz,type:'metro',name,x,z:z+5.5});
  };
  installed.add(proto);
}

/* Native 650 ms transition continues to own input, fading, save and rollback.
 * A non-interactive overlay follows the existing transition; it never starts it. */
export function installMetroTransition(game) {
  const original=game.runDungeonTransition;
  if (typeof original!=='function') return;
  game.runDungeonTransition=function(descriptor,instant,...args) {
    const entering=descriptor?.theme==='metro' && !descriptor.sewer && !this.world.inDungeon && !instant;
    const result=original.call(this,descriptor,instant,...args);
    if (entering && !descriptor.sewer && result && this.dungeonTransition) {
      const owner=this.p, token=this.dungeonTransition, nativeCamera=this.cam, post=this.post;
      const reduced=window.matchMedia?.('(prefers-reduced-motion: reduce)').matches;
      const camera=!reduced && nativeCamera?.clone?.();
      const previous=post?.render;
      const started=performance.now();
      let wrapped=null, frame=0, cleaned=false;
      const active=()=>this.p===owner && owner?.alive && this.state==='play' && this.dungeonTransition===token && !this.world.inDungeon &&
        this.cam===nativeCamera && this.post===post;
      if(camera && typeof previous==='function') {
        wrapped=function(scene,view,...renderArgs) {
          if (!active()) return previous.call(this,scene,view,...renderArgs);
          const progress=Math.min(1,Math.max(0,(performance.now()-started)/650));
          const x=descriptor.from?.x ?? owner.x,z=descriptor.from?.z ?? owner.z;
          const ground=window.TERRA_H?.(x,z)||0;
          camera.copy(nativeCamera);
          camera.position.lerp(camera.position.clone().set(x,ground+2.2,z),progress*.14);
          camera.lookAt(x,ground+.7,z);
          camera.quaternion.slerpQuaternions(nativeCamera.quaternion,camera.quaternion,progress*.55);
          camera.updateMatrixWorld();
          return previous.call(this,scene,camera,...renderArgs);
        };
        post.render=wrapped;
      }
      const screen=document.createElement('div');
      screen.className='metroTransition'; screen.setAttribute('aria-hidden','true');
      const text=document.createElement('span');text.textContent='МЕТРО · СПУСК';screen.append(text);
      document.body.append(screen);
      // Remove even when native transition is cancelled or a CSS animation is disabled.
      const cleanup=()=>{
        if(cleaned)return; cleaned=true; cancelAnimationFrame(frame); screen.remove();
        if(wrapped && post?.render===wrapped)post.render=previous;
      };
      const watch=()=>{if(!active()||performance.now()-started>1500)cleanup();else frame=requestAnimationFrame(watch);};
      screen.addEventListener('animationend',cleanup,{once:true});
      setTimeout(cleanup,1500);
      frame=requestAnimationFrame(watch);
    }
    return result;
  };
}
