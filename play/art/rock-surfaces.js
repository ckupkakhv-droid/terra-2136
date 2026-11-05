/* Continuous normals and texture projection for the native rock layer.
 * Geometry, material ids, placement and seeded draws stay in the native path. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},previous=ART.hook;
  const names=/^(rock_a|rock_b|stones|qn_rock_medium_[123]|qn_pebble_round_[13])$/;
  const models=new Map(),materials=new WeakSet();let installed=false;
  const stats=ART.rockSurfaces={instances:0,shaders:0,fallback:0,
    get models(){return models.size;},get bytes(){let n=0;for(const m of models.values())n+=m.normals.byteLength;return n;}};

  // The native prop transform is YXZ with a uniform positive height scale.
  function rotation(yaw,pitch,roll) {
    const cy=Math.cos(yaw),sy=Math.sin(yaw),cx=Math.cos(pitch),sx=Math.sin(pitch),cz=Math.cos(roll),sz=Math.sin(roll);
    return [cy*cz+sy*sx*sz,-cy*sz+sy*sx*cz,sy*cx,cx*sz,cx*cz,-sx,-sy*cz+cy*sx*sz,sy*sz+cy*sx*cz,cy*cx];
  }
  function rotate(x,y,z,m,inverse=false) {
    return inverse?[m[0]*x+m[3]*y+m[6]*z,m[1]*x+m[4]*y+m[7]*z,m[2]*x+m[5]*y+m[8]*z]:
      [m[0]*x+m[1]*y+m[2]*z,m[3]*x+m[4]*y+m[5]*z,m[6]*x+m[7]*y+m[8]*z];
  }
  ART.smoothRock=function(batch,start,args) {
    if(ART.rockSurfacesEnabled===false||!names.test(String(args[0]))||!(args[5]>0))return false;
    const count=batch.p.length/3-start;if(!count||count%3||batch.n.length!==batch.p.length)return false;
    const matrix=rotation(args[4]||0,args[7]||0,args[8]||0),name=String(args[0]);
    if(!matrix.every(Number.isFinite)||!Number.isFinite(args[5]))return false;
    let cached=models.get(name);
    if(!cached||cached.count!==count) {
      const groups=new Map(),vertices=[];
      for(let i=0;i<count;i++) {
        const k=(start+i)*3,key=batch.p[k]+','+batch.p[k+1]+','+batch.p[k+2];
        let group=groups.get(key);if(!group){group={sum:[0,0,0],fallback:null};groups.set(key,group);}
        vertices.push(group);
      }
      for(let i=0;i<count;i+=3) {
        const k=(start+i)*3,p=batch.p,u=[p[k+3]-p[k],p[k+4]-p[k+1],p[k+5]-p[k+2]],
          v=[p[k+6]-p[k],p[k+7]-p[k+1],p[k+8]-p[k+2]],
          n=[u[1]*v[2]-u[2]*v[1],u[2]*v[0]-u[0]*v[2],u[0]*v[1]-u[1]*v[0]];
        for(let j=0;j<3;j++) {
          const group=vertices[i+j];group.fallback??=batch.n.slice(k,k+3);
          for(let axis=0;axis<3;axis++)group.sum[axis]+=n[axis];
        }
      }
      for(const group of groups.values()) {
        let n=group.sum,length=Math.hypot(...n);if(length<1e-10){n=group.fallback;length=Math.hypot(...n);}
        if(!Number.isFinite(length)||length<1e-10){stats.fallback++;return false;}
        group.normal=rotate(n[0]/length,n[1]/length,n[2]/length,matrix,true);
      }
      const normals=new Float32Array(count*3);
      for(let i=0;i<count;i++)normals.set(vertices[i].normal,i*3);
      cached={count,normals};models.set(name,cached);
    }
    for(let i=0;i<count;i++) {
      const k=i*3,n=cached.normals,m=matrix,a=n[k],b=n[k+1],c=n[k+2],
        x=m[0]*a+m[1]*b+m[2]*c,y=m[3]*a+m[4]*b+m[5]*c,z=m[6]*a+m[7]*b+m[8]*c,length=Math.hypot(x,y,z);
      if(!Number.isFinite(length)||length<1e-8){stats.fallback++;return false;}
      const target=(start+i)*3;batch.n[target]=x/length;batch.n[target+1]=y/length;batch.n[target+2]=z/length;
    }
    stats.instances++;return true;
  };

  // Other atlas layers keep their native dominant-axis projection. Only the
  // Rock030 layer blends all three world projections with continuous weights.
  function patch(material) {
    if(!material||materials.has(material)||typeof material.onBeforeCompile!=='function'||
        !/m1(?:-|$)/.test(material.customProgramCacheKey?.()||''))return;
    const compile=material.onBeforeCompile,key=material.customProgramCacheKey.bind(material);
    material.onBeforeCompile=function(shader,renderer) {
      compile.call(this,shader,renderer);
      const text=shader.fragmentShader,head=text.match(/\{int L=int\(vMt\+\.5\)-1;if\(L>=0&&L<(\d+)&&uPbr>0\.\)\{/),
        tail='pN=((nm.x*2.-1.)*pT+(nm.y*2.-1.)*pB)*uPbr;}}';
      const begin=head?text.indexOf(head[0]):-1,end=begin<0?-1:text.indexOf(tail,begin);
      if(begin<0||end<0){stats.fallback++;return;}
      const original=text.slice(begin,end+tail.length),projection=original.slice(head[0].length,original.indexOf('puv*=uSc[L];'));
      if(!projection.startsWith('vec2 puv;vec3 pT,pB;')){stats.fallback++;return;}
      const block=`{int L=int(vMt+.5)-1;if(L>=0&&L<${head[1]}&&uPbr>0.){
        vec3 al;
        if(L==6){
          vec3 weights=pow(abs(normalize(vWN)),vec3(4.));weights/=max(dot(weights,vec3(1.)),1e-5);
          vec2 ux=vWP.zy*uSc[L],uy=vWP.xz*uSc[L],uz=vWP.xy*uSc[L];
          al=texture(uTA,vec3(ux,float(L))).rgb*weights.x+texture(uTA,vec3(uy,float(L))).rgb*weights.y+texture(uTA,vec3(uz,float(L))).rgb*weights.z;
          vec2 nx=texture(uTN,vec3(ux,float(L))).xy*2.-1.,ny=texture(uTN,vec3(uy,float(L))).xy*2.-1.,nz=texture(uTN,vec3(uz,float(L))).xy*2.-1.;
          pN=(vec3(0.,nx.y,nx.x)*weights.x+vec3(ny.x,0.,ny.y)*weights.y+vec3(nz.x,nz.y,0.)*weights.z)*uPbr;
        }else{
          ${projection}puv*=uSc[L];al=texture(uTA,vec3(puv,float(L))).rgb;
          vec3 nm=texture(uTN,vec3(puv,float(L))).rgb;pN=((nm.x*2.-1.)*pT+(nm.y*2.-1.)*pB)*uPbr;
        }
        vec3 av=max(uAvg[L],vec3(.01));vec3 r=clamp(mix(vec3(dot(al,vec3(.3,.59,.11))/dot(av,vec3(.3,.59,.11))),al/av,.3),0.,2.4);
        diffuseColor.rgb*=mix(vec3(1.),r,uPbr*uStr[L]);}}`;
      shader.fragmentShader=text.slice(0,begin)+block+text.slice(end+tail.length);stats.shaders++;
    };
    material.customProgramCacheKey=()=>key()+'-stone-projection-1';
    material.needsUpdate=true;materials.add(material);
  }
  ART.hook=function(api) {
    if(typeof previous==='function')previous(api);
    if(installed||ART.rockSurfacesEnabled===false||!api?.ue?.prototype?.mesh)return;
    installed=true;const proto=api.ue.prototype,mesh=proto.mesh;
    proto.mesh=function(material,...args){patch(material);return mesh.call(this,material,...args);};
  };
})();
