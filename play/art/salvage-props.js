/* Readable replacements for the native supply-container placeholders.
 * Only geometry changes: native placement, loot, collisions, breakage and seeded
 * draws still run first. Small parts share the original chunk/instance batches. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},previous=ART.hook;
  let api,installed=false;
  const keys=['p','n','c','a','m','uv'];
  const stats=ART.salvage={replaced:0,breakable:0,fallback:0};

  function stage(real) {
    const b=new api.ue(()=>.5,!!real.uv);
    for(const key of ['oy','hf','sink','sw','swc','wet','mt'])b[key]=real[key];
    if(real.m)b.m=[];
    return b;
  }
  function valid(b) {
    return b.p.length>0&&b.p.length<=5400&&keys.every(k=>!b[k]||b[k].every(Number.isFinite));
  }
  function append(real,b,lengths=null) {
    for(const key of keys)if(real[key]&&b[key]) {
      if(lengths)real[key].length=lengths[key];
      real[key].push(...b[key]);
    }
  }
  function model(builder,kind,x,z,size=1,angle=0,army=false,low=false) {
    const L=api.L,c=Math.cos(angle),s=Math.sin(angle);
    const box=(a,y,b,w,h,d,color,ry=0,rx=0,rz=0)=>builder.add(L.box,
      x+(c*a+s*b)*size,y*size,z+(-s*a+c*b)*size,w*size,h*size,d*size,color,
      angle+ry,rx,rz,0);
    const cylinder=(a,y,b,w,h,d,color,ry=0,rx=0,rz=0)=>builder.add(L.cyl,
      x+(c*a+s*b)*size,y*size,z+(-s*a+c*b)*size,w*size,h*size,d*size,color,
      angle+ry,rx,rz,0);
    const plate=(a,y,b,w,h,color,ry=0)=>builder.add(L.vplane,
      x+(c*a+s*b)*size,y*size,z+(-s*a+c*b)*size,w*size,h*size,1,color,angle+ry,0,0,0);
    function quad(a,b,d,e,color) {
      const p=[...a,...b,...d,...a,...d,...e],u=b.map((v,i)=>v-a[i]),v=d.map((w,i)=>w-a[i]);
      const normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],length=Math.hypot(...normal);
      const n=Array.from({length:6},()=>normal.map(v=>v/length)).flat();
      builder.add({p,n},x,0,z,size,size,size,color,angle,0,0,0);
    }
    // An extruded bevelled section gives cases and lids their own silhouettes.
    // Geometry goes through add(), so native height/material/normal rules apply.
    function prism(section,depth,color,axis='z',offset=[0,0,0]) {
      const p=[],n=[];
      const point=(v,d)=>axis==='z'?[v[0]+offset[0],v[1]+offset[1],d+offset[2]]:
        [d+offset[0],v[1]+offset[1],v[0]+offset[2]];
      function tri(a,b,d) {
        const u=b.map((v,i)=>v-a[i]),v=d.map((w,i)=>w-a[i]);
        const normal=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],len=Math.hypot(...normal);
        if(len<1e-10)return;
        for(const q of [a,b,d]){p.push(...q);n.push(...normal.map(v=>v/len));}
      }
      // section is counter-clockwise in its XY plane.
      for(let i=0;i<section.length;i++) {
        const j=(i+1)%section.length,a=point(section[i],-depth/2),b=point(section[j],-depth/2),
          d=point(section[j],depth/2),e=point(section[i],depth/2);
        if(axis==='z'){tri(a,e,d);tri(a,d,b);}else{tri(a,b,d);tri(a,d,e);}
      }
      for(let i=1;i<section.length-1;i++) {
        const a=point(section[0],depth/2),b=point(section[i],depth/2),d=point(section[i+1],depth/2),
          e=point(section[0],-depth/2),f=point(section[i],-depth/2),g=point(section[i+1],-depth/2);
        if(axis==='z'){tri(a,b,d);tri(e,g,f);}else{tri(a,d,b);tri(e,f,g);}
      }
      builder.add({p,n},x,0,z,size,size,size,color,angle,0,0,0);
    }
    const iron='#414844',edge='#7b7968',dark='#252e29';
    if(kind==='crate') {
      if(army) {
        prism([[-.48,.04],[.48,.04],[.48,.79],[.43,.84],[-.43,.84],[-.48,.79]],.92,'#47513b');
        box(0,.895,0,.98,.09,.96,'#535e42');
        box(0,.845,0,.97,.018,.95,dark);
        for(const side of [-1,1]) {
          box(side*.36,.48,0,.055,.71,.97,'#687055');
          box(side*.48,.64,0,.025,.12,.32,iron);
          box(side*.5,.64,0,.025,.055,.21,dark);
          box(side*.32,.91,.488,.07,.1,.025,edge);
        }
        for(const a of [-.3,-.1,.1,.3])box(a,.951,0,.035,.018,.7,'#626b4b');
        for(const a of [-.37,.37])box(a,.025,0,.13,.05,.85,dark);
        // Two worn stencil bars, cut into the painted face rather than emissive.
        for(const a of [-.1,.04])box(a,.47,.468,.055,.14,.008,'#a09c72');
      } else {
        const wood=['#6a5b43','#76674c','#62563f','#807054'];
        box(0,.445,0,.91,.89,.88,'#302e25');
        const boards=low?3:4,step=.86/boards;
        for(let i=0;i<boards;i++)for(const side of [-1,1]) {
          const y=.09+(i+.5)*step;
          box(0,y,side*.45,.91,step-.012,.045,wood[i%4]);
          box(side*.455,y,0,.045,step-.012,.86,wood[(i+1)%4]);
        }
        for(let i=0;i<4;i++)box(-.345+i*.23,.94,0,.217,.055,.93,wood[(i+2)%4]);
        for(const side of [-1,1]) {
          for(const a of [-.36,.36])box(a,.51,side*.482,.095,.94,.047,'#827156');
          box(side*.481,.51,0,.045,.94,.095,'#7b6a51');
          for(const y of [.13,.84]) {
            plate(0,y,side*.524,.95,.075,iron,side<0?Math.PI:0);
            plate(side*.524,y,0,.97,.075,iron,side*Math.PI/2);
          }
          if(!low)for(const a of [-.36,.36])for(const y of [.14,.84])
            plate(a,y,side*.53,.026,.026,'#aaa18a',side<0?Math.PI:0);
        }
        box(-.1,.973,.07,.27,.008,.19,dark);
        if(!low)for(const a of [-.39,.39])quad([a-.022,.978,-.365],[a-.022,.978,-.295],
          [a+.022,.978,-.295],[a+.022,.978,-.365],'#b0a087');
      }
    } else if(kind==='toolbox') {
      prism([[-.405,.025],[.405,.025],[.45,.08],[.45,.34],[-.45,.34],[-.45,.08]],.445,'#744238');
      prism([[-.45,.355],[.45,.355],[.405,.45],[.25,.485],[-.25,.485],[-.405,.45]],.445,'#945347');
      box(0,.348,0,.89,.012,.448,dark);
      for(const a of [-.27,.27]) {
        box(a,.34,.232,.065,.13,.025,edge);
        box(a,.29,.249,.04,.025,.012,dark);
      }
      for(const a of [-.15,.15])cylinder(a,.535,0,.035,.13,.035,iron);
      cylinder(0,.595,0,.045,.3,.045,'#272c29',0,0,Math.PI/2);
      for(const a of [-.39,.39])for(const b of [-.18,.18])box(a,.035,b,.075,.07,.06,iron);
      if(!low)for(const a of [-.36,.34])box(a,.21,.229,.055,.035,.008,'#b39a7c');
    } else if(kind==='chest') {
      const w=1.2,d=.7;
      box(0,.33,0,w,.59,d,'#554733');
      for(const side of [-1,1])for(let i=0;i<3;i++)box(0,.14+i*.175,side*.358,1.17,.16,.03,['#746046','#67563d','#7d6849'][i]);
      const section=[[-.35,.64],[.35,.64]];
      for(let i=0;i<=8;i++){const a=i*Math.PI/8;section.push([Math.cos(a)*.35,.67+Math.sin(a)*.34]);}
      prism(section,1.2,'#7b674a','x');
      for(const a of [-.45,.45]) {
        box(a,.33,0,.055,.6,.73,iron);
        const ring=[[-.365,.637],[.365,.637]];
        for(let i=0;i<=8;i++){const q=i*Math.PI/8;ring.push([Math.cos(q)*.365,.67+Math.sin(q)*.355]);}
        // Thin straps follow the lid instead of becoming solid end plates.
        for(let i=2;i<ring.length-1;i++) {
          const u=ring[i],v=ring[i+1];
          quad([a-.029,u[1],u[0]],[a+.029,u[1],u[0]],
            [a+.029,v[1],v[0]],[a-.029,v[1],v[0]],iron);
        }
      }
      box(0,.625,.374,1.19,.025,.025,dark);
      box(0,.63,.389,.13,.19,.025,edge);
      box(0,.59,.407,.035,.045,.012,dark);
      for(const a of [-.49,.49])box(a,.03,0,.15,.06,.63,iron);
    } else return false;
    return true;
  }

  function install(h) {
    if(installed||!h?.ue||!h?.L?.box||!h.L.cyl||!h.Ie?.prototype)return;
    api=h;installed=true;
    for(const kind of ['crate','chest','toolbox']) {
      const original=h.Ie.prototype[kind];
      if(typeof original!=='function')continue;
      h.Ie.prototype[kind]=function(x,z,...args) {
        const real=this.s,lengths=Object.fromEntries(keys.map(k=>[k,real[k]?.length])),add=real.add;
        let first=null,result;
        real.add=function(...a){if(!first&&a[0]===h.L.box)first=a;return add.apply(this,a);};
        try{result=original.call(this,x,z,...args);}finally{real.add=add;}
        // The later native kit layer runs legacy methods against a no-op
        // builder to preserve their seeded draws. Never fill that shared sink
        // or replace a kit model that is already present in another batch.
        if(!first||real.p.length===lengths.p)return result;
        try {
          const b=stage(real),size=kind==='crate'?first[4]:1,angle=kind==='crate'?first[8]||0:0;
          if(model(b,kind,x,z,size,angle,args[0]==='army',window.game?.qk==='low')&&valid(b)) {
            append(real,b,lengths);stats.replaced++;
          } else stats.fallback++;
        } catch(_){stats.fallback++;}
        return result;
      };
    }
  }
  ART.buildBreakable=function(kind,real) {
    if(!api||kind!=='crate')return false;
    try {
      const b=stage(real);
      if(!model(b,'crate',0,0,1,0,false,window.game?.qk==='low')||!valid(b))return false;
      append(real,b);stats.breakable++;return true;
    } catch(_){stats.fallback++;return false;}
  };
  ART.hook=function(h){if(typeof previous==='function')previous(h);if(ART.enabled!==false)install(h);};
})();
