/* Continue the native 1.6 m baked contact shade across loaded surface cells.
 * Keep the native grid paint, collider eligibility and triangle interpolation.
 * Only the existing colour attribute is updated; native save hooks stay intact. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},CELL=48,BUCKET=4,RADIUS=1.6,NONE=65535;
  const pending=new WeakMap(),worlds=new WeakMap();
  const totals={captures:0,updates:0,vertices:0,fallback:0};
  function failed(error) {
    if(!totals.fallback++)console.warn('TERRA terrain contact:',error?.message||String(error));
  }
  const cellKey=(x,z)=>x+','+z;
  function factor(x0,x1,z0,z1,x,z) {
    const d=Math.hypot(Math.max(x0-x,0,x-x1),Math.max(z0-z,0,z-z1));
    if(d>=RADIUS)return 1;
    const t=d/RADIUS;return .45+.55*(t*t*(3-2*t));
  }
  function localShade(index,x,z,ox,oz) {
    let shade=1;const boxes=index.get(cellKey(Math.floor((x-ox)/BUCKET),Math.floor((z-oz)/BUCKET)));
    if(boxes)for(const b of boxes)shade=Math.min(shade,factor(b.x0,b.x1,b.z0,b.z1,x,z));
    return shade;
  }
  function indexedShade(state,x,z) {
    let shade=1;const entries=state.index.get(cellKey(Math.floor(x/BUCKET),Math.floor(z/BUCKET)));
    if(entries)for(const {boxes,offset:i} of entries)shade=Math.min(shade,factor(boxes[i],boxes[i+1],boxes[i+2],boxes[i+3],x,z));
    return shade;
  }
  function eachBucket(boxes,i,visit) {
    const left=Math.floor((boxes[i]-RADIUS)/BUCKET),right=Math.floor((boxes[i+1]+RADIUS)/BUCKET),
      top=Math.floor((boxes[i+2]-RADIUS)/BUCKET),bottom=Math.floor((boxes[i+3]+RADIUS)/BUCKET);
    for(let x=left;x<=right;x++)for(let z=top;z<=bottom;z++)visit(cellKey(x,z));
  }
  ART.captureTerrainContact=function(chunk,grid,colours,index) {
    if(ART.terrainContactEnabled===false||chunk.d==='dungeon'||chunk.inDg)return;
    try {
      const xs=Float64Array.from(grid.xs),size=xs.length,count=size*size;
      if(count>=NONE||colours.length!==count*3||!colours.every(Number.isFinite)||xs[1]!==0||xs.at(-2)!==CELL||
         !xs.every((v,i)=>Number.isFinite(v)&&(!i||v>xs[i-1])))throw Error('Unsupported terrain grid');
      const unique=new Set();for(const boxes of index.values())for(const box of boxes)unique.add(box);
      const crossing=[];
      for(const b of unique) {
        const values=[b.x0,b.x1,b.z0,b.z1];
        if(!values.every(Number.isFinite)||b.x0>b.x1||b.z0>b.z1||
           (b.x1-b.x0+2*RADIUS)*(b.z1-b.z0+2*RADIUS)>BUCKET*BUCKET*65536)throw Error('Unsupported terrain occluder');
        // Interior occluders are already baked into this tile's native paint.
        // Index only sources whose 1.6 m halo can reach another surface cell.
        if(b.x0-RADIUS>=chunk.ox&&b.x1+RADIUS<=chunk.ox+CELL&&
           b.z0-RADIUS>=chunk.oz&&b.z1+RADIUS<=chunk.oz+CELL)continue;
        crossing.push(...values);
      }
      const boxes=Float64Array.from(crossing),local=new Float64Array(count);
      for(let z=0;z<size;z++)for(let x=0;x<size;x++)local[z*size+x]=localShade(index,chunk.ox+xs[x],chunk.oz+xs[z],chunk.ox,chunk.oz);
      pending.set(chunk,{cx:chunk.cx,cz:chunk.cz,ox:chunk.ox,oz:chunk.oz,xs,size,boxes,paint:colours.slice(),local,shared:local.slice()});
      totals.captures++;
    }catch(error){pending.delete(chunk);failed(error);}
  };
  function lower(xs,value) {
    let lo=1,hi=xs.length-2;
    while(lo+1<hi){const mid=(lo+hi)>>1;if(xs[mid]<=value)lo=mid;else hi=mid;}
    return lo;
  }
  function mapping(data,builder,mesh) {
    const position=mesh.geometry?.getAttribute('position'),colour=mesh.geometry?.getAttribute('color'),
      raw=builder.tr,vertices=raw?.p.length/3;
    if(!position||!colour||position.count!==vertices||colour.count!==vertices||colour.itemSize!==3||mesh.geometry.index||
       !(colour.array instanceof Float32Array)||!raw.c.every(Number.isFinite))throw Error('Unsupported terrain colour buffer');
    const source=new Uint16Array(vertices),interpolated=new Map(),{xs,size,paint}=data,lookup=new Map([...xs].map((v,i)=>[v,i]));
    for(let i=0;i<vertices;i++) {
      const x=raw.p[i*3]-data.ox,z=raw.p[i*3+2]-data.oz,gx=lookup.get(x),gz=lookup.get(z);
      if(gx!==undefined&&gz!==undefined){
        if(gx<1||gz<1||gx>=size-1||gz>=size-1)throw Error('Unexpected terrain ghost vertex');
        const id=gz*size+gx;
        for(let channel=0;channel<3;channel++)if(Math.abs(paint[id*3+channel]-colour.array[i*3+channel])>2e-6)throw Error('Terrain grid paint changed');
        source[i]=id;continue;
      }
      if(!Number.isFinite(x)||!Number.isFinite(z)||x<0||x>CELL||z<0||z>CELL)throw Error('Terrain point outside native grid');
      const ix=lower(xs,x),iz=lower(xs,z),u=(x-xs[ix])/(xs[ix+1]-xs[ix]),v=(z-xs[iz])/(xs[iz+1]-xs[iz]),a=iz*size+ix;
      let ids,weights;
      if((ix+iz)&1) {
        if(u+v<=1){ids=[a,a+size,a+1];weights=[1-u-v,v,u];}
        else{ids=[a+1,a+size,a+size+1];weights=[1-v,1-u,u+v-1];}
      }else if(u<=v){ids=[a,a+size,a+size+1];weights=[1-v,v-u,u];}
      else{ids=[a,a+size+1,a+1];weights=[1-u,v,u-v];}
      const original=colour.array.slice(i*3,i*3+3);
      for(let channel=0;channel<3;channel++) {
        const expected=ids.reduce((sum,id,k)=>sum+paint[id*3+channel]*weights[k],0);
        if(Math.abs(expected-original[channel])>2e-6)throw Error('Terrain clipping changed colour interpolation');
      }
      source[i]=NONE;interpolated.set(i,{ids,weights,original});
    }
    return{mesh,colour,source,interpolated};
  }
  function affected(data,set) {
    const boxes=data.boxes;
    set.add(cellKey(data.cx,data.cz));
    for(let i=0;i<boxes.length;i+=4) {
      const left=Math.floor((boxes[i]-RADIUS)/CELL),right=Math.floor((boxes[i+1]+RADIUS)/CELL),
        top=Math.floor((boxes[i+2]-RADIUS)/CELL),bottom=Math.floor((boxes[i+3]+RADIUS)/CELL);
      for(let x=left;x<=right;x++)for(let z=top;z<=bottom;z++)set.add(cellKey(x,z));
    }
  }
  function add(state,data) {
    data.entries=[];
    for(let i=0;i<data.boxes.length;i+=4) {
      const entry={boxes:data.boxes,offset:i};data.entries.push(entry);
      eachBucket(data.boxes,i,key=>{let bucket=state.index.get(key);if(!bucket)state.index.set(key,bucket=new Set());bucket.add(entry);});
    }
    state.records.set(cellKey(data.cx,data.cz),data);
  }
  function remove(state,data) {
    for(const entry of data.entries)eachBucket(entry.boxes,entry.offset,key=>{
      const bucket=state.index.get(key);if(bucket){bucket.delete(entry);if(!bucket.size)state.index.delete(key);}
    });
    state.records.delete(cellKey(data.cx,data.cz));
  }
  function update(state,data) {
    const {xs,size,local,shared,paint,colour,source}=data;
    if(data.mesh.geometry?.getAttribute('color')!==colour||colour.count!==source.length)throw Error('Terrain colour buffer replaced');
    let dirty=null;
    // Ghost rows are not rendered. Keep their original shade; the interpolation
    // map only references the visible native grid from 0 through 48 m.
    for(let z=1;z<size-1;z++)for(let x=1;x<size-1;x++) {
      const id=z*size+x,next=Math.min(local[id],indexedShade(state,data.ox+xs[x],data.oz+xs[z]));
      if(next!==shared[id]){dirty??=new Uint8Array(local.length);dirty[id]=1;shared[id]=next;}
    }
    if(!dirty)return;
    const array=colour.array;let first=Infinity,last=-1,writes=0;
    for(let i=0;i<source.length;i++) {
      const id=source[i],k=i*3;
      if(id!==NONE) {
        if(!dirty[id])continue;
        const ratio=shared[id]/local[id];
        for(let channel=0;channel<3;channel++)array[k+channel]=paint[id*3+channel]*ratio;
      }else {
        const point=data.interpolated.get(i);
        if(!point.ids.some(id=>dirty[id]))continue;
        if(point.ids.every(id=>shared[id]===local[id]))array.set(point.original,k);
        else for(let channel=0;channel<3;channel++)array[k+channel]=point.ids.reduce((sum,id,j)=>sum+paint[id*3+channel]*(shared[id]/local[id])*point.weights[j],0);
      }
      first=Math.min(first,k);last=k+3;writes++;
    }
    if(!writes)return;
    // One accumulated range stays bounded even while an offscreen chunk is not
    // drawn. Preserve pending earlier writes before the renderer consumes them.
    if(typeof colour.addUpdateRange==='function'&&typeof colour.clearUpdateRanges==='function') {
      for(const range of colour.updateRanges){first=Math.min(first,range.start);last=Math.max(last,range.start+range.count);}
      colour.clearUpdateRanges();colour.addUpdateRange(first,last-first);
    }
    colour.needsUpdate=true;totals.updates++;totals.vertices+=writes;
  }
  function repaint(state,keys) {
    for(const key of keys){const data=state.records.get(key);if(data)update(state,data);}
  }
  ART.attachTerrainContact=function(world,owner,builder,interior) {
    const data=pending.get(builder);pending.delete(builder);
    if(ART.terrainContactEnabled===false||interior||!data)return;
    let state;
    try {
      const meshes=owner.meshes.filter(m=>m.geometry?.getAttribute('w0'));
      if(meshes.length!==1)throw Error('Surface terrain mesh is ambiguous');
      Object.assign(data,mapping(data,builder,meshes[0]),{owner});
      state=worlds.get(world);if(!state)worlds.set(world,state={records:new Map(),index:new Map()});
      const keys=new Set(),previous=state.records.get(cellKey(data.cx,data.cz));
      if(previous){affected(previous,keys);remove(state,previous);}
      affected(data,keys);add(state,data);repaint(state,keys);
    }catch(error){
      if(state?.records.get(cellKey(data.cx,data.cz))===data){remove(state,data);try{const keys=new Set();affected(data,keys);repaint(state,keys);}catch(_) {}}
      failed(error);
    }
  };
  ART.detachTerrainContact=function(world,owner) {
    const state=worlds.get(world),data=state?.records.get(cellKey(owner.cx,owner.cz));
    if(!data||data.owner!==owner)return;
    try{const keys=new Set();affected(data,keys);remove(state,data);repaint(state,keys);}
    catch(error){failed(error);}
    if(!state.records.size)worlds.delete(world);
  };
  ART.terrainContact={
    totals,
    inspect(world) {
      const state=worlds.get(world);let bytes=0,boxes=0,vertices=0,interpolated=0,pendingRanges=0;
      if(state)for(const data of state.records.values()) {
        bytes+=data.xs.byteLength+data.boxes.byteLength+data.paint.byteLength+data.local.byteLength+data.shared.byteLength+data.source.byteLength;
        boxes+=data.boxes.length/4;vertices+=data.source.length;interpolated+=data.interpolated.size;
        for(const p of data.interpolated.values())bytes+=p.original.byteLength;
        pendingRanges+=data.colour.updateRanges?.length||0;
      }
      return{chunks:state?.records.size||0,buckets:state?.index.size||0,boxes,typedBytes:bytes,vertices,interpolated,pendingRanges};
    }
  };
})();
