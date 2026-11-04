/* Static kit in chamber 2. Source geometry/materials remain loader-owned;
 * the expedition owns only its cloned scene nodes and two unshadowed lights. */
export const LAB_TERMINAL = Object.freeze({x:-6,z:-4});
export function buildSewerLab(chunk, game, bridge) {
  const source = game.glb?.sewer_lab?.src, room = chunk.rooms?.[2];
  const names = ['vault_4m','bulkhead','hermodoor','vat','vat_broken','lab_table','crate_bio','growth_cluster','lamp_cage'];
  if (!room || !source || names.some(name => !source.getObjectByName(name))) return null;
  const group = new bridge.Group();
  group.name = 'sewerLab'; group.position.set(room.x,0,room.z);
  const put = (name,x,z,ry=0,y=0) => {
    const node = source.getObjectByName(name).clone(true);
    node.position.set(x,y,z); node.rotation.y=ry;
    node.traverse(mesh => { if(mesh.isMesh) { mesh.frustumCulled=true; mesh.castShadow=false; } });
    group.add(node); return node;
  };
  const block = (x,z,w,d,h) => chunk.col(room.x+x-w/2,room.z+z-d/2,room.x+x+w/2,room.z+z+d/2,h);
  // North and east are the connected routes. Dress only the closed walls.
  for (const z of [-6,-2,2,6]) put('vault_4m',-7.8,z,Math.PI/2);
  for (const x of [-6,2,6]) put('vault_4m',x,7.8,Math.PI);
  const bulkhead = put('bulkhead',-2,7.8,Math.PI);
  // Sealed archive door against an already collidable exterior wall.
  put('hermodoor',bulkhead.position.x+1.17,7.8,Math.PI);
  for (const z of [-5,5]) { put('vat',6,z,-Math.PI/2); block(6,z,1.1,1.1,2.7); }
  put('lab_table',LAB_TERMINAL.x,LAB_TERMINAL.z,Math.PI/2);
  block(LAB_TERMINAL.x,LAB_TERMINAL.z,.9,1.9,1.5);
  put('crate_bio',-5.5,5); block(-5.5,5,.9,.7,.65);
  put('crate_bio',5,6); block(5,6,.9,.7,.65);
  put('vat_broken',-6.1,1,Math.PI/2); block(-6.1,1,1.8,2.1,1.5);
  put('growth_cluster',6.4,6.5);
  put('lamp_cage',-7.55,-3,Math.PI/2,2.6);
  put('lamp_cage',3,7.55,Math.PI,2.6);
  const lightSource = [game.muzzle,game.boomL,...game.world.scene.children].find(l=>l?.isPointLight);
  if (lightSource) for (const [x,z,color,intensity] of [[-5,-3,0xffbc75,2],[5,4,0x5dbca8,1.6]]) {
    const light = lightSource.clone(); light.color.setHex(color); light.intensity=intensity;
    light.distance=11; light.decay=2; light.castShadow=false;
    light.position.set(x,2.3,z); group.add(light);
  }
  return group;
}
