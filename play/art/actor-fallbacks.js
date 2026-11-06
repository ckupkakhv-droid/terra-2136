/* A complete suit for the native six-part hero rig. Keep its pivots, instancing,
 * material, pose/weapon matrices and overall standing bounds; the ready GLB still replaces it. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},templates=new Map();
  const stats={built:0,fallback:0,get templates(){return templates.size},get bytes(){let n=0;for(const {builder} of templates.values())for(const k of ['p','n','c','a'])n+=builder[k]?.byteLength||0;return n;}};
  ART.actorFallbacks=stats;
  function shape(){return{p:[],n:[]}}
  function triangle(g,a,b,c,na,nb,nc) {
    const u=b.map((v,i)=>v-a[i]),v=c.map((v,i)=>v-a[i]),cross=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
    if(Math.hypot(...cross)<1e-12)return;
    if(cross.reduce((sum,v,i)=>sum+v*(na[i]+nb[i]+nc[i]),0)<0){[b,c]=[c,b];[nb,nc]=[nc,nb];}
    g.p.push(...a,...b,...c);g.n.push(...na,...nb,...nc);
  }
  const unit=n=>{const length=Math.hypot(...n);return n.map(v=>v/length)};
  function tube(x,z,rings,segments=8,closed=true) {
    const g=shape(),point=(ring,j)=>{const a=j/segments*Math.PI*2;return[x+ring[1]*Math.sin(a),ring[0],z+ring[2]*Math.cos(a)]},norm=(i,j)=>{
      const a=j/segments*Math.PI*2,left=rings[Math.max(0,i-1)],right=rings[Math.min(rings.length-1,i+1)],
        dx=(right[1]-left[1])/(right[0]-left[0]),dz=(right[2]-left[2])/(right[0]-left[0]),r=rings[i];
      return unit([r[2]*Math.sin(a),-(r[2]*dx*Math.sin(a)**2+r[1]*dz*Math.cos(a)**2),r[1]*Math.cos(a)]);
    };
    for(let i=0;i<rings.length-1;i++)for(let j=0;j<segments;j++) {
      const a=point(rings[i],j),b=point(rings[i],j+1),c=point(rings[i+1],j+1),d=point(rings[i+1],j),
        na=norm(i,j),nb=norm(i,j+1),nc=norm(i+1,j+1),nd=norm(i+1,j);
      triangle(g,a,b,d,na,nb,nd);triangle(g,b,c,d,nb,nc,nd);
    }
    if(closed)for(const i of [0,rings.length-1]) {
      const normal=[0,i?1:-1,0],ring=rings[i];
      for(let j=1;j<segments-1;j++)triangle(g,point(ring,0),point(ring,j),point(ring,j+1),normal,normal,normal);
    }
    return g;
  }
  function sphere(x,y,z,rx,ry,rz,segments=10,rows=5,angles=[-Math.PI,Math.PI,-Math.PI/2,Math.PI/2]) {
    const g=shape(),point=(i,j)=>{
      const theta=angles[0]+(angles[1]-angles[0])*i/segments,phi=angles[2]+(angles[3]-angles[2])*j/rows,
        sx=Math.sin(theta)*Math.cos(phi),sy=Math.sin(phi),sz=Math.cos(theta)*Math.cos(phi);
      return{p:[x+rx*sx,y+ry*sy,z+rz*sz],n:unit([sx/rx,sy/ry,sz/rz])};
    };
    for(let j=0;j<rows;j++)for(let i=0;i<segments;i++) {
      const a=point(i,j),b=point(i+1,j),c=point(i+1,j+1),d=point(i,j+1);
      triangle(g,a.p,b.p,d.p,a.n,b.n,d.n);triangle(g,b.p,c.p,d.p,b.n,c.n,d.n);
    }return g;
  }
  function pack(){
    const g=shape(),cross=[[-.19,-.13],[.19,-.13],[.23,-.09],[.23,.09],[.19,.13],[-.19,.13],[-.23,.09],[-.23,-.09]],
      p=(i,y)=>[cross[i][0],y,cross[i][1]-.30];
    for(let i=0;i<8;i++){
      const j=(i+1)%8,a=p(i,.08),b=p(j,.08),c=p(j,.58),d=p(i,.58),n=unit([b[2]-a[2],0,a[0]-b[0]]);
      triangle(g,a,b,d,n,n,n);triangle(g,b,c,d,n,n,n);
    }
    for(const y of [.08,.58])for(let j=1;j<7;j++){const n=[0,y===.08?-1:1,0];triangle(g,p(0,y),p(j,y),p(j+1,y),n,n,n);}
    return g;
  }
  function patch(x0,x1,y0,y1,z,color,builder) {
    const g=shape(),n=[0,0,z<0?-1:1],a=[x0,y0,z],b=[x1,y0,z],c=[x1,y1,z],d=[x0,y1,z];
    triangle(g,a,b,d,n,n,n);triangle(g,b,c,d,n,n,n);builder.o(g,0,0,0,1,1,1,color);
  }
  function surfacePatch(surface,builder,rect,color) {
    const g=shape(),planes=[v=>v.p[0]-rect[0],v=>rect[1]-v.p[0],v=>v.p[1]-rect[2],v=>rect[3]-v.p[1]];
    for(let i=0;i<surface.p.length;i+=9) {
      let polygon=[0,3,6].map(k=>({p:surface.p.slice(i+k,i+k+3),n:surface.n.slice(i+k,i+k+3)}));
      if(polygon.reduce((sum,v)=>sum+v.n[2],0)<=.6)continue;
      for(const distance of planes) {
        const out=[];let previous=polygon.at(-1);if(!previous)break;let a=distance(previous);
        for(const current of polygon) {
          const b=distance(current);
          if((a>=0)!==(b>=0)){const t=a/(a-b);out.push({p:previous.p.map((v,j)=>v+(current.p[j]-v)*t),n:previous.n.map((v,j)=>v+(current.n[j]-v)*t)})}
          if(b>=0)out.push(current);previous=current;a=b;
        }polygon=out;
      }
      for(let j=1;j<polygon.length-1;j++) {
        const tri=[polygon[0],polygon[j],polygon[j+1]],p=tri.map(v=>[v.p[0],v.p[1],v.p[2]+.003]),n=tri.map(v=>unit(v.n));
        triangle(g,...p,...n);
      }
    }
    builder.o(g,0,0,0,1,1,1,color);
  }
  function build(name,b) {
    const put=(g,color)=>b.o(g,0,0,0,1,1,1,color),suit='#bbbcb4',seam='#686c66',boot='#454039',orange='#b56639';
    if(name==='torso') {
      const body=tube(0,0,[[-.01,.31,.19],[.28,.31,.19],[.61,.265,.17]]);put(body,suit);
      put(pack(),'#858b83');
      put(tube(0,0,[[.565,.14,.14],[.62,.13,.13]],6),'#555e5e');
      put(tube(0,0,[[.015,.316,.196],[.085,.316,.196]],8,false),'#514b42');
      surfacePatch(body,b,[-.19,.19,.16,.43],orange);
      patch(-.13,.13,.35,.47,-.434,'#33565e',b);patch(-.10,.10,.39,.415,-.436,'#6d9ba0',b);
      surfacePatch(body,b,[.17,.23,.46,.52],'#924c43');
    }else if(name==='head') {
      put(sphere(0,.17,0,.25,.25,.25),'#c8cac3');
      put(sphere(0,.17,0,.255,.255,.255,6,2,[-.88,.88,-.26,.50]),'#57625f');
      put(sphere(0,.17,0,.258,.258,.258,6,2,[-.78,.78,-.18,.43]),'#22333e');
      put(sphere(0,.17,0,.260,.260,.260,3,1,[-.57,.12,.28,.32]),'#91abb3');
    }else if(name==='armL'||name==='armR') {
      put(tube(0,0,[[-.60,.083,.083],[-.29,.097,.092],[.01,.12,.13]],6),suit);
      put(tube(0,0,[[-.39,.101,.097],[-.33,.102,.097]],6,false),seam);
      put(tube(0,0,[[-.605,.085,.085],[-.535,.09,.09]],6,false),boot);
      put(sphere(0,-.62,0,.08,.06,.08,6,3),boot);
    }else if(name==='legL'||name==='legR') {
      const leg=tube(0,0,[[-.64,.09,.10],[-.30,.114,.125],[0,.12,.13]],6);put(leg,suit);
      put(tube(0,.035,[[-.93,.095,.125],[-.86,.11,.15],[-.55,.10,.12]],6),boot);
      surfacePatch(leg,b,[-.08,.08,-.32,-.20],orange);
    }else return false;
    return true;
  }
  function fit(builder,source,name) {
    const bounds=p=>{const lo=[Infinity,Infinity,Infinity],hi=[-Infinity,-Infinity,-Infinity];for(let i=0;i<p.length;i++) {const a=i%3;lo[a]=Math.min(lo[a],p[i]);hi[a]=Math.max(hi[a],p[i]);}return{lo,hi};},a=bounds(builder.p),b=bounds(source.p),scale=a.lo.map((v,i)=>(b.hi[i]-b.lo[i])/(a.hi[i]-v));
    if(!scale.every(v=>Number.isFinite(v)&&v>0))throw Error('Invalid fallback bounds');
    for(let i=0;i<builder.p.length;i++) {const axis=i%3,low=axis===1&&name==='torso'?b.lo[axis]-.025:b.lo[axis],s=axis===1&&name==='torso'?(b.hi[axis]-low)/(a.hi[axis]-a.lo[axis]):scale[axis];builder.p[i]=low+(builder.p[i]-a.lo[axis])*s;}
    if(name==='torso')scale[1]=(b.hi[1]-b.lo[1]+.025)/(a.hi[1]-a.lo[1]);
    for(let i=0;i<builder.n.length;i+=3){const n=unit([builder.n[i]/scale[0],builder.n[i+1]/scale[1],builder.n[i+2]/scale[2]]);builder.n.splice(i,3,...n);}
    for(const key of ['p','n','c','a'])builder[key]=Float32Array.from(builder[key]);
  }
  ART.fallbackActorGeometry=function(type,name,source) {
    if(ART.actorFallbacksEnabled===false||type!=='hero')return null;
    try {
      let cached=templates.get(name);
      if(!cached||cached.source!==source) {
        const builder=new source.constructor(()=>.5);
        if(!build(name,builder))return null;
        fit(builder,source,name);if(builder.p.length/9>160)throw Error('Fallback part exceeds triangle budget');
        cached={source,builder};templates.set(name,cached);stats.built++;
      }
      return cached.builder.geometry();
    }catch(error){if(!stats.fallback++)console.warn('TERRA actor fallback:',error.message);return null;}
  };
})();
