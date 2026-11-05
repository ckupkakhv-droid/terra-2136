/* Fine leaf silhouettes on existing crown geometry. Sidecar flags belong only
 * to transient builders and GPU geometry; gameplay state and RNG stay native. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},previous=ART.hook;
  const builders=new WeakMap(),materials=new WeakSet(),installed=new WeakSet(),models=new Map(),shadows=new WeakMap();
  let bridge;
  const enabled=new URLSearchParams(location.search).get('leaves')!=='0';
  function record(builder,start,flags) {
    if(!flags.some(v=>v>0))return;
    let ranges=builders.get(builder);if(!ranges)builders.set(builder,ranges=[]);
    ranges.push({start,flags});
  }
  const declarations=`varying float vTerraLeaf;varying vec3 vTerraLeafP;varying vec3 vTerraLeafN;`;
  const fragment=`
if(vTerraLeaf>.5){
 vec3 an=abs(vTerraLeafN);vec2 uv;
 if(an.y>an.x&&an.y>an.z)uv=vTerraLeafP.xz+vTerraLeafP.y*vec2(.27,.41);
 else if(an.x>an.z)uv=vTerraLeafP.zy+vTerraLeafP.x*vec2(.27,.41);
 else uv=vTerraLeafP.xy+vTerraLeafP.z*vec2(.27,.41);
 uv*=8.;float footprint=max(length(dFdx(uv)),length(dFdy(uv)));
 if(footprint<1.2){
  // Union neighbouring leaves instead of clipping one leaf to each square.
  // Jitter, rotation and size break the visible lattice on closed canopies.
  vec2 base=floor(uv);float field=9.,seed=0.,vein=0.;
  for(int y=0;y<2;y++)for(int x=0;x<2;x++){
   vec2 cell=base+vec2(float(x),float(y));
   vec3 h=fract(vec3(cell.xyx)*.1031);h+=dot(h,h.yzx+33.33);
   float s=fract((h.x+h.y)*h.z),size=.82+.3*fract(s*29.17);
   vec2 turn=normalize(vec2(s-.5,fract(s*17.73)-.5)+vec2(.001));
   vec2 center=cell+vec2(fract(s*7.37)-.5,fract(s*11.17)-.5)*.36;
   vec2 q=(uv-center)/size;q=mat2(turn.x,-turn.y,turn.y,turn.x)*q;
   float width=.44*max(0.,1.-pow(abs(q.y)/.60,2.));
   float f=max(abs(q.y)-.60,abs(q.x)-width);
   if(vTerraLeaf>1.5){
    float sprig=.47*pow(max(0.,1.-abs(q.y)/.52),.35);
    sprig-=.035*abs(fract(q.y*9.+q.x)*2.-1.);
    f=max(abs(q.y)-.5,abs(q.x)-sprig);
   }
   f*=size;
   if(f<field){field=f;seed=s;vein=1.-smoothstep(.008,.025,abs(q.x));}
  }
  float aa=clamp(footprint*.7,.008,.15),coverage=1.-smoothstep(-aa,aa,field);
  float detail=1.-smoothstep(.55,1.2,footprint);
  if(mix(1.,coverage,detail)<.5)discard;
  diffuseColor.rgb*=mix(1.,.91+seed*.14+vein*.045,detail);
 }
}
`;
  function patch(material) {
    if(typeof material?.onBeforeCompile!=='function'||typeof material.customProgramCacheKey!=='function'||materials.has(material))return;
    const compile=material.onBeforeCompile,key=material.customProgramCacheKey.bind(material);
    // Leaf cards must remain visible from below and while the tree falls.
    // Keep native front-face culling for unflagged bark/grass sharing the batch.
    const frontOnly=material.side===0;
    if(frontOnly)material.side=2;
    material.defaultAttributeValues={...material.defaultAttributeValues,terraLeaf:[0]};
    material.onBeforeCompile=function(shader,renderer) {
      compile.call(this,shader,renderer);
      if(!shader.vertexShader.includes('#include <begin_vertex>')||!shader.fragmentShader.includes('#include <alphatest_fragment>'))return;
      shader.vertexShader='attribute float terraLeaf;'+declarations+'\n'+shader.vertexShader;
      shader.vertexShader=shader.vertexShader.replace('#include <begin_vertex>',
        '#include <begin_vertex>\nvTerraLeaf=terraLeaf;vTerraLeafP=position;vTerraLeafN=normal;');
      shader.fragmentShader=declarations+'\n'+shader.fragmentShader;
      shader.fragmentShader=shader.fragmentShader.replace('#include <alphatest_fragment>',
        (frontOnly?'if(!gl_FrontFacing&&vTerraLeaf<.5)discard;\n':'')+fragment+'\n#include <alphatest_fragment>');
    };
    material.customProgramCacheKey=()=>key()+'-terra-leaf-canopies-2';
    material.needsUpdate=true;materials.add(material);
  }
  function applyMesh(result) {
    if(!result?.geometry?.getAttribute('terraLeaf'))return result;
    const material=result.material;patch(material);
    if(typeof bridge?.makeLeafShadows==='function') {
      let pair=shadows.get(material);
      if(!pair) {
        const key=material.customProgramCacheKey(),wind=key.startsWith('p1'),fell=Number(key.match(/f([012])m/)?.[1]||0);
        pair=bridge.makeLeafShadows(wind,fell);pair.forEach(patch);shadows.set(material,pair);
      }
      [result.customDepthMaterial,result.customDistanceMaterial]=pair;
    }
    return result;
  }
  ART.hook=function(api) {
    if(typeof previous==='function')previous(api);
    const proto=api?.ue?.prototype,L=api?.L;
    if(!enabled||ART.enabled===false||!proto||!L||installed.has(proto))return;
    bridge=api;ART.applyLeafMesh=applyMesh;
    installed.add(proto);
    const prop=proto.prop,add=proto.add,geometry=proto.geometry,mesh=proto.mesh;
    proto.prop=function(...args) {
      const start=this.p.length/3,result=prop.apply(this,args),name=String(args[0]);
      if(!/^(qn_commontree_[1-5]|qn_pine_[1-5]|qn_twistedtree_[1-3]|qn_bush_common)$/.test(name))return result;
      const count=this.p.length/3-start,cached=models.get(name);
      if(!count)return result;
      if(cached?.length===count){record(this,start,cached);return result;}
      const flags=new Uint8Array(count),tint=Array.isArray(args[6])?args[6]:[1,1,1];
      let minY=Infinity,maxY=-Infinity;
      for(let i=start*3+1;i<this.p.length;i+=3){minY=Math.min(minY,this.p[i]);maxY=Math.max(maxY,this.p[i]);}
      const height=maxY-minY,bush=name==='qn_bush_common';
      for(let i=0;i<count;i+=3) {
        let r=0,g=0,b=0;
        for(let j=0;j<3;j++){const k=(start+i+j)*3;r+=this.c[k]/Math.max(.001,tint[0]);g+=this.c[k+1]/Math.max(.001,tint[1]);b+=this.c[k+2]/Math.max(.001,tint[2]);}
        const points=[0,1,2].map(j=>this.p.slice((start+i+j)*3,(start+i+j)*3+3)),
          edges=points.map((p,j)=>Math.hypot(...p.map((v,k)=>v-points[(j+1)%3][k]))),
          u=points[1].map((v,k)=>v-points[0][k]),v=points[2].map((v,k)=>v-points[0][k]),
          area=Math.hypot(u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0])*.5;
        const card=!name.startsWith('qn_twistedtree_')&&Math.min(...edges)>Math.max(...edges)*.18&&area>height*height*(bush?.0008:.0015)&&
          (bush||points.reduce((sum,p)=>sum+p[1],0)/3>minY+height*.32);
        if(card||(g>r*1.06&&g>b*1.1))flags.fill(name.startsWith('qn_pine')?2:1,i,i+3);
      }
      if(!args[7]&&!args[8])models.set(name,flags);
      record(this,start,flags);return result;
    };
    proto.add=function(...args) {
      const start=this.p.length/3,result=add.apply(this,args);
      if(this.sw>0&&Math.min(Math.abs(args[4]),Math.abs(args[5]),Math.abs(args[6]))>.55&&
          [L.ico,L.sph,L.cone,L.cone4].includes(args[0])) {
        record(this,start,new Uint8Array(this.p.length/3-start).fill(args[0]===L.cone||args[0]===L.cone4?2:1));
      }
      return result;
    };
    proto.geometry=function(...args) {
      const result=geometry.apply(this,args),ranges=builders.get(this);
      if(!result||!ranges?.length)return result;
      const count=result.getAttribute('position').count,flags=new Uint8Array(count);
      for(const range of ranges)if(range.start<count)flags.set(range.flags.subarray(0,count-range.start),range.start);
      const Attribute=Object.getPrototypeOf(result.getAttribute('position').constructor);
      result.setAttribute('terraLeaf',new Attribute(flags,1));return result;
    };
    proto.mesh=function(material,...args) {
      return applyMesh(mesh.call(this,material,...args));
    };
  };
})();
