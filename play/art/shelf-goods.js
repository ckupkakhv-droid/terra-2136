/* Replace the native coloured shelf blocks after their seeded placement.
 * The metal carcass, occupancy, loot and collisions keep their native data.
 * All parts join the existing static batch; no textures or new draw calls. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},previous=ART.hook;
  const keys=['p','n','c','a','m','uv'],settings=['oy','hf','sink','sw','swc','wet'];
  const stats=ART.shelfGoods={shelves:0,goods:0,fallback:0};
  let api,installed=false;
  const cache=new Map();

  function primitive() {
    const p=[],n=[];
    return {p,n,tri(a,b,c) {
      const u=b.map((v,i)=>v-a[i]),v=c.map((w,i)=>w-a[i]);
      const q=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]],h=Math.hypot(...q);
      if(h<1e-10)return;
      for(const point of [a,b,c]){p.push(...point);n.push(...q.map(v=>v/h));}
    }};
  }
  function revolve(profile,segments,caps=true) {
    const mesh=primitive(),point=(r,y,i)=>[r*Math.cos(i*2*Math.PI/segments),y,r*Math.sin(i*2*Math.PI/segments)];
    for(let row=0;row<profile.length-1;row++)for(let i=0;i<segments;i++) {
      const [r,y]=profile[row],[r1,y1]=profile[row+1],a=point(r,y,i),b=point(r1,y1,i),
        c=point(r1,y1,i+1),d=point(r,y,i+1);
      mesh.tri(a,b,c);mesh.tri(a,c,d);
    }
    if(caps)for(let i=0;i<segments;i++) {
      const [r,y]=profile[0],[r1,y1]=profile[profile.length-1];
      mesh.tri([0,y,0],point(r,y,i),point(r,y,i+1));
      mesh.tri([0,y1,0],point(r1,y1,i+1),point(r1,y1,i));
    }
    return mesh;
  }
  function carton() {
    const mesh=primitive(),section=[[-.1,0],[.1,0],[.1,.22],[.012,.28],[-.012,.28],[-.1,.22]];
    const point=(v,z)=>[v[0],v[1],z];
    for(let i=0;i<section.length;i++) {
      const j=(i+1)%section.length,a=point(section[i],-.09),b=point(section[j],-.09),
        c=point(section[j],.09),d=point(section[i],.09);
      mesh.tri(a,b,c);mesh.tri(a,c,d);
    }
    for(let i=1;i<section.length-1;i++) {
      mesh.tri(point(section[0],.09),point(section[i],.09),point(section[i+1],.09));
      mesh.tri(point(section[0],-.09),point(section[i+1],-.09),point(section[i],-.09));
    }
    return mesh;
  }
  function shapes(low) {
    if(cache.has(low))return cache.get(low);
    const count=low?6:8,result={
      can:revolve([[.082,0],[.09,.012],[.09,.22],[.082,.23]],count),
      canLabel:revolve([[.091,.055],[.091,.17]],count,false),
      canTop:revolve([[.077,.231],[.077,.235]],count),
      bottle:revolve([[.059,0],[.073,.018],[.073,.205],[.029,.255],[.027,.285]],count),
      bottleLabel:revolve([[.074,.065],[.074,.16]],count,false),
      cap:revolve([[.031,.283],[.031,.3]],count),carton:carton()
    };
    cache.set(low,result);return result;
  }
  function item(batch,record,low) {
    const a=record.args,x=a[1],y=a[2]-.15,z=a[3],angle=a[8]||0,s=shapes(low);
    const type={'#c84a3a':0,'#e8c84a':2,'#4a8ac8':1,'#5ac84a':1,'#e8e8e8':2,'#c87a3a':0}[a[7]]??0;
    for(const key of settings)batch[key]=record[key];
    batch.mt=-1;
    const put=(mesh,color)=>batch.add(mesh,x,y,z,1,1,1,color,angle,0,0,0);
    // Labels are opaque paper/paint. Their radii sit outside the body, so no
    // coincident faces or alpha-sorted glass enter the shared static material.
    if(type===0) {
      put(s.can,'#73796c');put(s.canLabel,a[7]==='#c84a3a'?'#77483b':'#998565');put(s.canTop,'#8b8d7a');
    } else if(type===1) {
      put(s.bottle,a[7]==='#4a8ac8'?'#485b5c':'#4b5941');put(s.bottleLabel,'#b0a98d');put(s.cap,'#4c5148');
    } else {
      put(s.carton,a[7]==='#e8e8e8'?'#aaa28a':'#9b8862');
      // Two faded bands and a folded seam give the packet a readable front.
      const c=Math.cos(angle),sn=Math.sin(angle),plate=(yy,w,h,color)=>
        batch.add(api.L.vplane,x+sn*.091,y+yy,z+c*.091,w,h,1,color,angle,0,0,0);
      plate(.085,.17,.055,'#6c6751');plate(.18,.12,.022,'#c4bca1');plate(.267,.024,.018,'#746f5c');
    }
    if(!low) {
      const c=Math.cos(angle),sn=Math.sin(angle),front=type===2?.092:type===1?.076:.093;
      for(let i=0;i<3;i++)batch.add(api.L.vplane,x+c*(i-1)*.025+sn*front,y+.11-i*.013,
        z-sn*(i-1)*.025+c*front,.015,.006,1,'#5e5b4d',angle,0,0,0);
    }
  }
  function install(h) {
    if(installed||!h?.ue||!h.L?.box||!h.L.vplane||!h.Ie?.prototype?.shelf)return;
    installed=true;api=h;
    const original=h.Ie.prototype.shelf;
    h.Ie.prototype.shelf=function(...args) {
      const real=this.s,starts=Object.fromEntries(keys.map(k=>[k,real[k]?.length])),records=[];
      const add=real.add,ownAdd=Object.hasOwn(real,'add');
      let result;
      real.add=function(...a) {
        // Strict native signature identifies goods, never metal frame parts.
        const good=a[0]===h.L.box&&a[4]===.35&&a[5]===.3&&a[6]===.5;
        const record=good?{args:a,start:Object.fromEntries(keys.map(k=>[k,this[k]?.length]))}:null;
        if(record)for(const key of settings)record[key]=this[key];
        const value=add.apply(this,a);
        if(record){record.end=Object.fromEntries(keys.map(k=>[k,this[k]?.length]));records.push(record);}
        return value;
      };
      try{result=original.apply(this,args);}finally{if(ownAdd)real.add=add;else delete real.add;}
      // Do not populate the native kit's no-op legacy sink.
      if(!records.length||real.p.length===starts.p)return result;
      try {
        const batch=new h.ue(()=>.5,!!real.uv);if(real.m)batch.m=[];
        for(const key of keys)if(real[key]) {
          let cursor=starts[key];
          for(const record of records) {
            batch[key].push(...real[key].slice(cursor,record.start[key]));cursor=record.end[key];
          }
          batch[key].push(...real[key].slice(cursor));
        }
        const low=window.game?.qk==='low';
        for(const record of records)item(batch,record,low);
        const count=batch.p.length/3;
        if(count>records.length*450+400||!keys.every(k=>!batch[k]||batch[k].every(Number.isFinite))||
            batch.n.length!==count*3||batch.c.length!==count*3||batch.a.length!==count*2||
            (batch.m&&batch.m.length!==count)||(batch.uv&&batch.uv.length!==count*2))throw Error('Invalid shelf batch');
        for(const key of keys)if(real[key]){real[key].length=starts[key];real[key].push(...batch[key]);}
        stats.shelves++;stats.goods+=records.length;
      }catch(_){stats.fallback++;}
      return result;
    };
  }
  ART.hook=function(h) {
    if(typeof previous==='function')previous(h);
    if(ART.shelvesEnabled!==false)install(h);
  };
})();
