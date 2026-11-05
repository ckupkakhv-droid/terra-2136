/* Surface architecture uses the native chunk builder and its shared instanced
 * geometries. Entries, collision and fast-travel identifiers stay native. */
function foundation(builder,x,y,z,height) {
  // A small chamfer catches light at the foundation edge without another
  // material, mesh or collider. Coordinates passed to tri are already world-space.
  const lower=[[-3,0,-3.5],[-3,0,3.5],[3,0,3.5],[3,0,-3.5]];
  // Bury the lower edge below the perimeter terrain so a level base has no
  // daylight gap on a slope. The top and native walking height stay unchanged.
  let bottom=0;
  for(let edge=0;edge<4;edge++)for(let step=0;step<=8;step++) {
    const a=lower[edge],b=lower[(edge+1)%4],t=step/8;
    const sample=height(x+a[0]+(b[0]-a[0])*t,z+a[2]+(b[2]-a[2])*t);
    if(Number.isFinite(sample))bottom=Math.min(bottom,sample-y-.03);
  }
  for(const p of lower)p[1]=bottom;
  const shoulder=lower.map(([a,,b])=>[a,.075,b]);
  const top=lower.map(([a,,b])=>[Math.sign(a)*2.955,.12,Math.sign(b)*3.455]);
  const ink=[.0953074666,.1046164841,.0908417112]; // #575b55, linear RGB
  const point=p=>[p[0]+x,p[1]+y,p[2]+z];
  function triangle(a,b,c,tone) {
    const u=b.map((v,i)=>v-a[i]),v=c.map((n,i)=>n-a[i]);
    const n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
    const length=Math.hypot(...n);for(let i=0;i<3;i++)n[i]/=length;
    const color=ink.map(c=>c*tone),start=builder.m?.length;
    builder.tri(...point(a),...point(b),...point(c),n,n,n,color,color,color);
    if(builder.m)for(let i=start;i<builder.m.length;i++)builder.m[i]=6; // native concrete atlas
  }
  function quad(a,b,c,d,tone) {triangle(a,b,c,tone);triangle(a,c,d,tone);}
  quad(...top,1);
  for(let i=0;i<4;i++) {
    const next=(i+1)%4;
    quad(lower[i],lower[next],shoulder[next],shoulder[i],.84);
    quad(shoulder[i],shoulder[next],top[next],top[i],1.08);
  }
}

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
    // Paving belongs in front of the station, outside the stairs. Keep its
    // relief and thickness while bending it to the existing terrain height.
    // Roll back the kit batches on failure, then keep the station foundation.
    const previousKit=this.kb, lengths={};
    for(const [key,batches] of Object.entries(previousKit||{}))
      lengths[key]=batches.map(batch=>Object.fromEntries(['p','n','uv','c','i'].map(k=>[k,batch[k].length])));
    const stats=globalThis.TERRA_KITS?.stats, placed=stats?.placed;
    try {
      if(typeof this.kp_!=='function') throw Error('kit unavailable');
      for(const dx of [-1.1,1.1]) for(const dz of [4.2,5.6]) {
        const xx=x+dx,zz=z+dz;
        if(this.cols.some(c=>c.h>=.6 && xx+1.08>c.x0 && xx-1.08<c.x1 && zz+.68>c.z0 && zz-.68<c.z1))
          throw Error('approach obstructed');
        const starts=this.kb?.bld?.map(batch=>batch.p.length)||[0,0,0];
        const rotation=(dx<0)===(dz<5)?0:Math.PI;
        if(!this.kp_('slab',xx,zz,rotation,1,{y:0,sink:0,tint:.74+(dx>0?.04:0)-(dz>5?.02:0),sx:.72,sz:1.36/3})) throw Error('slab unavailable');
        let top=-Infinity;
        for(let b=0;b<this.kb.bld.length;b++)for(let i=starts[b];i<this.kb.bld[b].p.length;i+=3)
          top=Math.max(top,this.kb.bld[b].p[i+1]);
        if(!Number.isFinite(top))throw Error('empty paving');
        for(let b=0;b<this.kb.bld.length;b++) {
          const batch=this.kb.bld[b];
          for(let i=starts[b];i<batch.p.length;i+=3) {
            const vx=batch.p[i],vz=batch.p[i+2],height=this.hAt(vx,vz);
            const hx=(this.hAt(vx+.05,vz)-this.hAt(vx-.05,vz))/.1;
            const hz=(this.hAt(vx,vz+.05)-this.hAt(vx,vz-.05))/.1;
            if(![height,hx,hz].every(Number.isFinite))throw Error('invalid terrain');
            batch.p[i+1]+=height+.025-top;
            // Inverse transpose for y'=y+height(x,z), preserving side normals.
            const nx=batch.n[i]-hx*batch.n[i+1],ny=batch.n[i+1],nz=batch.n[i+2]-hz*batch.n[i+1];
            const length=Math.hypot(nx,ny,nz);
            if(!Number.isFinite(length)||length<1e-8)throw Error('invalid paving normal');
            batch.n[i]=nx/length;batch.n[i+1]=ny/length;batch.n[i+2]=nz/length;
          }
        }
      }
    } catch (_) {
      for(const [key,batches] of Object.entries(this.kb||{})) {
        if(!lengths[key]) delete this.kb[key];
        else batches.forEach((batch,index)=>{for(const name of ['p','n','uv','c','i'])batch[name].length=lengths[key][index][name];});
      }
      if(!previousKit) delete this.kb;
      if(Number.isFinite(placed))stats.placed=placed;
    }
    foundation(s,x,ground,z,(xx,zz)=>this.hAt(xx,zz));
    // Deep shadow and descending treads: visual only.
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
    // An open arch leaves the station approach and the existing interaction
    // point unobstructed, with no extra collision geometry.
    for(const side of [-1,1]) {
      s.box(x+side*2.15,1.1,z-3.1,.34,1.25,.4,'#535c52');
      s.box(x+side*2.15,2.32,z-3.1,.48,.13,.55,'#8b8e7b');
      // Weathered face plates and drain grates, all within old collision walls.
      s.box(x+side*2.38,.23,z+.15,.045,.17,4.9,'#454b46');
      for(const dz of [-2.05,-1.2,-.35,.5,1.35,2.2])
        s.box(x+side*2.30,.14,z+dz,.14,.025,.045,'#282f2d');
    }
    // A low, segmented steel-and-concrete arch frames the entrance. Reuses
    // chunk batches and does not add lights, textures, colliders or RNG calls.
    const sections=10, radius=2.15, spring=2.38, rise=.98;
    for(let i=0;i<sections;i++) {
      const a=i*Math.PI/sections,b=(i+1)*Math.PI/sections;
      const ax=Math.cos(a)*radius,ay=spring+Math.sin(a)*rise;
      const bx=Math.cos(b)*radius,by=spring+Math.sin(b)*rise;
      const dx=bx-ax,dy=by-ay,length=Math.hypot(dx,dy),angle=-Math.atan2(dx,dy);
      s.add(L.cyl5,x+(ax+bx)/2,(ay+by)/2,z-3.09,.17,length+.025,.17,'#85867a',0,0,angle,0);
      s.add(L.cyl5,x+(ax+bx)/2,(ay+by)/2,z-2.98,.045,length+.025,.045,'#766e5a',0,0,angle,0);
    }
    // Small weathered warning strips keep the opening legible at game scale.
    for(const side of [-1,1]) {
      s.box(x+side*1.8,.88,z-2.96,.09,.8,.025,'#c18b43');
      for(const y of [1.02,1.28,1.54]) s.box(x+side*1.8,y,z-2.94,.1,.065,.03,'#272d29');
    }
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
        // `from` is the surface *return* point, three metres in front of the
        // entry. Metro architecture puts the stair centre 1.5 m behind the
        // entry; aim at that centre instead of at the return point.
        const from=descriptor.from;
        const x=Number.isFinite(from?.x)?from.x:owner.x;
        const z=Number.isFinite(from?.z)?from.z-4.5:owner.z;
        const sampledGround=window.TERRA_H?.(x,z);
        const ground=Number.isFinite(sampledGround)?sampledGround:0;
        // Keep a separate target: slerpQuaternions copies its first argument
        // before reading the second, so passing camera.quaternion as both the
        // destination and target silently cancels the camera turn.
        const targetOrientation=nativeCamera.quaternion.clone();
        wrapped=function(scene,view,...renderArgs) {
          if (!active()) return previous.call(this,scene,view,...renderArgs);
          const progress=Math.min(1,Math.max(0,(performance.now()-started)/650));
          const eased=progress*progress*(3-2*progress),move=eased*.18;
          camera.copy(nativeCamera);
          camera.position.x+=(x-camera.position.x)*move;
          camera.position.y+=(ground+2.2-camera.position.y)*move;
          camera.position.z+=(z-camera.position.z)*move;
          camera.lookAt(x,ground+.7,z);
          targetOrientation.copy(camera.quaternion);
          camera.quaternion.slerpQuaternions(nativeCamera.quaternion,targetOrientation,eased*.7);
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

/* Keep ordinary metro entrances legible without a floating octahedron. The
 * existing batch still owns all interaction and non-metro markers. A shared
 * ring mesh is used only when the surface and its height are available; if
 * anything fails, the original marker remains visible. */
const markerInstallations = new WeakSet();
export function installMetroMarkers(game) {
  const markers=game?.markers, original=markers?.sync, base=markers?.im;
  const ring=game?.rings?.im, scene=game?.scene;
  if (!markers || markerInstallations.has(markers) || typeof original!=='function' ||
      !base?.isInstancedMesh || !ring?.geometry || !ring?.material || !scene) return;
  let instances;
  try {
    instances=new base.constructor(ring.geometry,ring.material,markers.max);
    instances.count=0;instances.frustumCulled=false;
    instances.userData.terraMetroMarkers=true;
    scene.add(instances);
  } catch (_) { return; }
  let placement=null,zero=null,tint=null;
  markers.sync=function(renderMarker) {
    const entries=game.world?.inDungeon ? [] : (game.world?.ents||[]);
    let count=0;
    const result=original.call(this,(item,matrix,color)=>{
      renderMarker(item,matrix,color);
      if(item.k!==2 || count>=markers.max || !entries.some(e=>
        e.kind==='metro' && !e.sewer && e.x===item.x && e.z===item.z)) return;
      try {
        // Metro's entry is 1.5 m ahead of the fixed-height station footprint.
        const ground=window.TERRA_H?.(item.x,item.z-1.5);
        if(!Number.isFinite(ground)) return;
        if(!placement) { placement=matrix.clone();zero=game.cam.position.clone().set(0,0,0);tint=color.clone(); }
        placement.makeScale(1.05,1,1.05).setPosition(item.x,ground+.24,item.z);
        instances.setMatrixAt(count,placement);
        instances.setColorAt(count,tint.setRGB(.28,.09,.025));
        count++;
        // Only suppress the original after the replacement is ready.
        matrix.scale(zero);
      } catch (_) { /* Leave the native marker intact. */ }
    });
    instances.count=count;
    instances.instanceMatrix.needsUpdate=true;
    if(instances.instanceColor)instances.instanceColor.needsUpdate=true;
    return result;
  };
  markerInstallations.add(markers);
}
