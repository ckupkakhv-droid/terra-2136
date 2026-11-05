/* Chunk-local subway opening, stairs and walking profile. No persistent state.
 * The optional native height-cache adapter is scripts/patch-metro-height.py. */
const STEPS=16, RUN=.3, RISE=.15, FRONT=2.5, REAR=-3.1, HALF=2.4;

export function makeMetroDescent(x,z,ground) {
  return {x,z,ground,left:x-HALF,right:x+HALF,front:z+FRONT,rear:z+REAR,depth:STEPS*RISE};
}
function contains(p,x,z) {return x>p.left&&x<p.right&&z>p.rear&&z<p.front;}
export function descentHeight(p,x,z) {
  if(!contains(p,x,z))return null;
  const step=Math.min(STEPS,Math.floor((p.front-z)/RUN)+1);
  return p.ground-.03-step*RISE;
}

function removeGroundRectangle(builder,p) {
  const fields=[['p',3],['n',3],['c',3],['a',2],['ws',8],['uv',2]]
    .filter(([key])=>Array.isArray(builder[key]));
  const out=Object.fromEntries(fields.map(([key])=>[key,[]]));
  const planes=[v=>v.p[0]-p.left,v=>p.right-v.p[0],v=>v.p[2]-p.rear,v=>p.front-v.p[2]];
  function clip(vertices,distance,inside) {
    const result=[];
    let previous=vertices.at(-1),a=distance(previous)*(inside?1:-1);
    for(const vertex of vertices) {
      const b=distance(vertex)*(inside?1:-1),inA=a>=0,inB=b>=0;
      if(inA!==inB) {
        const t=a/(a-b),point={};
        for(const [key] of fields)point[key]=previous[key].map((v,i)=>v+(vertex[key][i]-v)*t);
        result.push(point);
      }
      if(inB)result.push(vertex);
      previous=vertex;a=b;
    }
    return result;
  }
  function emit(polygon) {
    for(let i=1;i<polygon.length-1;i++) {
      const tri=[polygon[0],polygon[i],polygon[i+1]],a=tri[0].p,b=tri[1].p,c=tri[2].p;
      if(Math.abs((b[0]-a[0])*(c[2]-a[2])-(b[2]-a[2])*(c[0]-a[0]))<1e-10)continue;
      for(const vertex of tri)for(const [key] of fields)out[key].push(...vertex[key]);
    }
  }
  for(let i=0;i<builder.p.length/3;i+=3) {
    const triangle=[0,1,2].map(offset=>Object.fromEntries(fields.map(([key,size])=>
      [key,builder[key].slice((i+offset)*size,(i+offset+1)*size)])));
    const xs=triangle.map(v=>v.p[0]),zs=triangle.map(v=>v.p[2]);
    if(Math.max(...xs)<=p.left||Math.min(...xs)>=p.right||Math.max(...zs)<=p.rear||Math.min(...zs)>=p.front) {
      for(const vertex of triangle)for(const [key] of fields)out[key].push(...vertex[key]);
      continue;
    }
    let remainder=triangle;
    for(const plane of planes) {
      if(!remainder.length)break;
      emit(clip(remainder,plane,false));
      remainder=clip(remainder,plane,true);
    }
  }
  if(fields.some(([key,size])=>out[key].length/size!==out.p.length/3||!out[key].every(Number.isFinite)))
    throw Error('Invalid metro terrain opening');
  for(const [key] of fields)builder[key]=out[key];
}

export function finishMetroDescents(chunk,profiles,skipped=[]) {
  function cap(p) {
    const color=[.0953074666,.1046164841,.0908417112],normal=[0,1,0],y=p.ground+.12;
    const a=[p.left,y,p.rear],b=[p.left,y,p.front],c=[p.right,y,p.front],d=[p.right,y,p.rear];
    const start=chunk.s.m?.length;
    chunk.s.tri(...a,...b,...c,normal,normal,normal,color,color,color);
    chunk.s.tri(...a,...c,...d,normal,normal,normal,color,color,color);
    if(chunk.s.m)for(let i=start;i<chunk.s.m.length;i++)chunk.s.m[i]=6;
  }
  for(const p of skipped)cap(p);
  if(!profiles.length)return;
  const staged=Object.fromEntries(Object.entries(chunk.tr).filter(([,value])=>Array.isArray(value)));
  try {for(const profile of profiles)removeGroundRectangle(staged,profile);}
  catch (_) {for(const p of profiles)cap(p);return;}
  for(const [key,value] of Object.entries(staged))chunk.tr[key]=value;
  // The typed height grid is already owned by the native chunk cache. Its
  // optional function disappears with that grid when the chunk is unloaded.
  const sample=(x,z)=>{
    for(const p of profiles){const y=descentHeight(p,x,z);if(y!==null)return y;}
    return null;
  };
  sample.profileAt=(x,z)=>profiles.find(p=>contains(p,x,z))||null;
  chunk.grid.metroHeight=sample;
}

export function buildMetroDescent(chunk,L,p) {
  const s=chunk.s;
  const rgb=hex=>[1,3,5].map(i=>{const v=parseInt(hex.slice(i,i+2),16)/255;return v<.04045?v/12.92:((v+.055)/1.055)**2.4;});
  const stone=rgb('#62655a'),riser=rgb('#42483f'),edge=rgb('#a49b7f'),drain=rgb('#303a34');
  const point=(x,y,z)=>[p.x+x,p.ground+y,p.z+z];
  function quad(points,color,material=6) {
    for(const [a,b,c] of [[points[0],points[1],points[2]],[points[0],points[2],points[3]]]) {
      const u=b.map((v,i)=>v-a[i]),v=c.map((n,i)=>n-a[i]);
      const normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
      const length=Math.hypot(...normal);for(let i=0;i<3;i++)normal[i]/=length;
      const start=s.m?.length;s.tri(...a,...b,...c,normal,normal,normal,color,color,color);
      if(s.m)for(let i=start;i<s.m.length;i++)s.m[i]=material;
    }
  }
  function top(left,right,back,front,y,color) {
    quad([point(left,y,back),point(left,y,front),point(right,y,front),point(right,y,back)],color);
  }
  for(let i=0;i<STEPS;i++) {
    const front=FRONT-i*RUN,back=front-RUN,y=.12-(i+1)*RISE,upper=i?y+RISE-.012:.12;
    top(-1.875,1.875,back+.025,front,y,stone.map(c=>c*(1+(i%3-1)*.035)));
    quad([point(-1.875,y-.012,back),point(-1.875,y,back+.025),
      point(1.875,y,back+.025),point(1.875,y-.012,back)],edge);
    quad([point(-1.875,y,front),point(-1.875,upper,front),
      point(1.875,upper,front),point(1.875,y,front)],riser);
    for(const side of [-1,1]) {
      const left=side<0?-HALF:1.875,right=side<0?-1.875:HALF;
      top(left,right,back,front,y-.012,drain);
      quad([point(left,y-.012,front),point(left,upper,front),point(right,upper,front),point(right,y-.012,front)],drain);
    }
  }
  const bottom=.12-STEPS*RISE;
  top(-HALF,HALF,REAR,FRONT-STEPS*RUN,bottom,stone.map(c=>c*.55));
  // Dark portal and a second, buried arch give the shaft a destination.
  quad([point(-1.5,bottom,-3.075),point(1.5,bottom,-3.075),
    point(1.5,bottom+1.95,-3.075),point(-1.5,bottom+1.95,-3.075)],rgb('#060a08'),0);
  for(const side of [-1,1]) {
    s.add(L.cyl5,p.x+side*1.6,bottom+.6,p.z-3.04,.16,1.2,.16,'#727365',0,0,0,0);
    chunk.seg(s,p.x+side*2.22,p.ground+.92,p.z+2.35,
      p.x+side*2.22,p.ground+bottom+.95,p.z-2.15,.045,'#8a7c60',true);
    for(const z of [1.9,.4,-1.7]) {
      const y=descentHeight(p,p.x,p.z+z)-p.ground+.15+.95;
      s.add(L.box,p.x+side*2.31,y,p.z+z,.2,.05,.08,'#655d4d',0,0,0,0);
    }
    chunk.g.add(L.box,p.x+side*1.67,bottom+1.6,p.z-2.98,.14,.16,.12,'#ba793c',0,0,0,0);
  }
  for(let i=0;i<10;i++) {
    const a=i*Math.PI/10,b=(i+1)*Math.PI/10,ax=Math.cos(a)*1.6,bx=Math.cos(b)*1.6;
    const ay=bottom+1.2+Math.sin(a)*.75,by=bottom+1.2+Math.sin(b)*.75;
    s.add(L.cyl5,p.x+(ax+bx)/2,(ay+by)/2,p.z-3.04,.13,Math.hypot(bx-ax,by-ay)+.02,.13,
      '#777969',0,0,-Math.atan2(bx-ax,by-ay),0);
  }
}

const interactionInstalled=new WeakSet();
export function installMetroDescentInteraction(game,bridge=globalThis.TERRA_SEWER_BRIDGE) {
  if(interactionInstalled.has(game)||!bridge?.metroProfileAt||typeof game.nearInteract!=='function'||
    typeof bridge.dungeonPromptInfo!=='function'||typeof bridge.dungeonPromptLabel!=='function')return;
  const near=game.nearInteract;
  game.nearInteract=function(...args) {
    const result=near.apply(this,args),p=this.p;
    if(this.state!=='play'||!p?.alive||this.world.inDungeon||this.dungeonTransition||
      (result&&!['ent','cont','node'].includes(result.k)))return result;
    const profile=bridge.metroProfileAt(p.x,p.z);
    if(!profile)return result;
    const entry=this.world.ents.find(e=>e.kind==='metro'&&!e.sewer&&e.x===profile.x&&e.z===profile.z+1.5);
    if(!entry||result?.o===entry)return result;
    const info=bridge.dungeonPromptInfo(this,entry);
    const name=String(entry.name).replaceAll('&','&amp;').replaceAll('<','&lt;').replaceAll('>','&gt;');
    return {k:'ent',o:entry,label:info?bridge.dungeonPromptLabel(entry,info):`Спуститься: <b>${name}</b>`,dungeonInfo:info};
  };
  interactionInstalled.add(game);
}
