/* Keep packed props' atlas ids aligned; natural stones use the existing rock
 * layer. Legacy pastel stones receive a muted granite palette and surface moss. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{},previous=ART.hook;
  const installed=new WeakSet();
  ART.hook=function(api) {
    if(typeof previous==='function')previous(api);
    const proto=api?.ue?.prototype;
    if(!proto||installed.has(proto)||typeof proto.prop!=='function')return;
    const original=proto.prop;
    proto.prop=function(...args) {
      const before=this.p.length/3,materials=this.m?.length,result=original.apply(this,args);
      const name=String(args[0]),stone=/^(rock_a|rock_b|stones|qn_rock_medium_[123]|qn_pebble_round_[13])$/.test(name),
        legacy=/^(rock_a|rock_b|stones)$/.test(name);
      if(Array.isArray(this.m)&&materials===before&&this.m.length===materials) {
        const count=this.p.length/3;
        for(let i=before;i<count;i++)this.m.push(stone?7:0); // Rock030 is atlas layer 6 + encoded offset 1.
      }
      if(legacy)for(let i=before*3;i<this.p.length;i+=3) {
        const light=(this.c[i]*.21+this.c[i+1]*.72+this.c[i+2]*.07)*.5;
        const noise=Math.sin(this.p[i]*12.9898+this.p[i+2]*78.233)*43758.5453;
        const moss=Math.max(0,this.n[i+1]-.4)*Math.max(0,(noise-Math.floor(noise))-.45)*.55;
        this.c[i]=light*.96*(1-moss)+.055*moss;
        this.c[i+1]=light*(1-moss)+.085*moss;
        this.c[i+2]=light*.91*(1-moss)+.035*moss;
      }
      return result;
    };
    installed.add(proto);
  };
})();
