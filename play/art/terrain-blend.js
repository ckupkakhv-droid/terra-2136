/* District paint must be continuous in world coordinates. Blend only the base
 * colour/material weights before native roads, water, paths and AO are applied.
 * Heights, normals, collision and world/save generation are left to the engine. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},CELL=48,BAND=4;
  const mixedColor=new Float64Array(3),mixedWeights=new Float64Array(8),
    color=new Float64Array(3),weights=new Float32Array(8);
  // District classification is deterministic and relatively expensive. Retain
  // only small names, never chunks, with a fixed bound while exploring the map.
  const kinds=new Map();let kindSource=null;
  function region(cx,cz,district) {
    if(kindSource!==district){kinds.clear();kindSource=district;}
    const key=cx+','+cz;
    if(kinds.has(key))return kinds.get(key);
    const kind=district(cx,cz)?.d;
    if(kinds.size>=256)kinds.clear();
    kinds.set(key,kind);return kind;
  }
  const smooth=x=>{x=Math.max(0,Math.min(1,x));return x*x*(3-2*x);};
  function axis(value) {
    const index=Math.floor(value/CELL),offset=value-index*CELL;
    if(offset<BAND){const w=.5*(1-smooth(offset/BAND));return [[index-1,w],[index,1-w]];}
    if(offset>CELL-BAND){const w=.5*(1-smooth((CELL-offset)/BAND));return [[index,1-w],[index+1,w]];}
    return [[index,1]];
  }
  function baseWeights(kind,x,z,noise,out) {
    out.fill(0);
    const grass=Math.max(0,Math.min(1,noise(x*.05,z*.05,3,3)*1.4-.2));
    if(['market','mall','ind','camp'].includes(kind)){out[3]=.55;out[1]=.45;}
    else if(['crash','ruins'].includes(kind)){out[1]=.55;out[0]=.25;out[3]=.2;}
    else {out[0]=1-grass*.55;out[1]=grass*.55;}
    if(['park','outskirts','dacha'].includes(kind)) {
      const growth=noise(x*.035,z*.035,57,2);
      if(growth>.58) {
        const amount=smooth((growth-.58)/.12)*.8;
        for(let i=0;i<8;i++)out[i]*=1-amount;
        out[2]+=amount;
      }
    }
  }
  ART.blendTerrainBase=function(kind,x,z,nativeColor,nativeWeights,paint,noise,district) {
    if(ART.enabled===false||kind==='dungeon')return;
    const rx=x-Math.floor(x/CELL)*CELL,rz=z-Math.floor(z/CELL)*CELL;
    if(Math.min(rx,CELL-rx,rz,CELL-rz)>=BAND)return;
    try {
      const regions=[];
      for(const [cx,wx] of axis(x))for(const [cz,wz] of axis(z)) {
        const name=region(cx,cz,district),weight=wx*wz;
        if(!name||!Number.isFinite(weight))return;
        if(weight>0)regions.push([name,weight]);
      }
      if(regions.every(([name])=>name===kind))return;
      mixedColor.fill(0);mixedWeights.fill(0);
      for(const [name,weight] of regions) {
        const same=name===kind;
        if(!same){paint(name,x,z,color);baseWeights(name,x,z,noise,weights);}
        const sourceColor=same?nativeColor:color,sourceWeights=same?nativeWeights:weights;
        for(let i=0;i<3;i++)mixedColor[i]+=sourceColor[i]*weight;
        for(let i=0;i<8;i++)mixedWeights[i]+=sourceWeights[i]*weight;
      }
      if(!mixedColor.every(Number.isFinite)||!mixedWeights.every(Number.isFinite))return;
      for(let i=0;i<3;i++)nativeColor[i]=mixedColor[i];
      nativeWeights.set(mixedWeights);
    } catch (_) { /* A future generator keeps its native paint on failure. */ }
  };
})();
