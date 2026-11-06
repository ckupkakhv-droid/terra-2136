/* The render pass lifts ordinary scene roots onto terrain, but deliberately
 * skips instanced meshes. Match that height for the live hero's six-part rig.
 * Keep the native root/hand matrices local: the weapon render pass lifts them. */
(function () {
  'use strict';
  const ART=window.TERRA_ART=window.TERRA_ART||{};
  ART.groundHeroRig=function(rig,poses) {
    if(ART.actorGroundingEnabled===false||rig!==window.game?.heroRig||typeof window.TERRA_H!=='function')return;
    let slot=0;
    for(const pose of poses) {
      if(slot>=rig.max)break;
      const height=window.TERRA_H(pose.x,pose.z);
      if(Number.isFinite(height)&&height!==0) {
        for(const {im} of rig.parts)if(slot<im.count)im.instanceMatrix.array[slot*16+13]+=height;
      }
      slot++;
    }
    // The native update already queued each attribute for its next GPU upload.
    // Isolated rigs and inventory previews are not the live world hero.
  };
})();
