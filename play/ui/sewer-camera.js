/* A temporary render camera. The native camera and its follow state remain
 * untouched; releasing this lease removes only the wrapper that we installed.
 */
export function leaseSewerCamera(game, subject, {owns = () => true, onCancel} = {}) {
  const post = game.post, nativeCamera = game.cam, scene = game.world?.scene;
  if (!subject || subject.dead || !game.enemies?.includes(subject) || !scene ||
      typeof post?.render !== 'function' || typeof nativeCamera?.clone !== 'function') return null;
  // The encounter opens inside dungeonUpdate. The normal GLB budget would not
  // run again once state becomes modal, so instantiate without advancing AI.
  if (!subject.inst && game.glb?.[subject.mdl || subject.base]?.make) {
    try { game.gbT = 0; game.glbBudget?.(0); game.syncInst?.(subject); }
    catch { return null; }
  }
  if (!subject.inst?.root) return null;
  // The fresh spawn has a random yaw and has not had an AI tick yet. Let the
  // encounter face the visitor before the modal freezes ordinary simulation.
  if (game.p && Math.hypot(game.p.x - subject.x, game.p.z - subject.z) > .01) {
    subject.yaw = Math.atan2(game.p.x - subject.x, game.p.z - subject.z);
    game.syncInst?.(subject);
  }
  const owner = game.p, world = game.world, dungeon = game.dg, key = dungeon?.key;
  const original = post.render, camera = nativeCamera.clone();
  const reduced = globalThis.matchMedia?.('(prefers-reduced-motion: reduce)');
  // Reuse the native light class, with its own resources. Native muzzle/boom
  // lights retain their colour, intensity, position and shadow configuration.
  const point = [game.muzzle, game.boomL, ...scene.children].find(light => light?.isPointLight && typeof light.clone === 'function');
  const template = point || [game.hemi, ...scene.children].find(light => light?.isHemisphereLight && typeof light.clone === 'function');
  const keyLight = template?.clone(false);
  if (keyLight) {
    keyLight.name = 'sewerEncounterKey';
    keyLight.userData.noT = true;
    keyLight.userData.sewerCinematicLight = true;
    keyLight.castShadow = false;
    keyLight.visible = true;
    keyLight.color.setHex(0xffddbb);
    keyLight.intensity = point ? 8 : .2;
    if (point) { keyLight.distance = 6.5; keyLight.decay = 2; }
    else keyLight.groundColor?.setHex(0x17221b);
    scene.add(keyLight);
  }
  let released = false, frame = 0;
  const valid = () => !released && game.p === owner && owner?.alive !== false &&
    game.world === world && game.dg === dungeon && game.dg?.key === key &&
    !game.dungeonTransition && game.cam === nativeCamera && game.post === post &&
    post.render === render && game.enemies.includes(subject) && !subject.dead && !!subject.inst?.root;

  function release() {
    if (released) return;
    released = true;
    if (post.render === render) post.render = original;
    keyLight?.removeFromParent();
    keyLight?.dispose?.();
  }
  function check() {
    if (released) return false;
    if (valid() && owns()) return true;
    release(); onCancel?.();
    return false;
  }
  function shot() {
    camera.copy(nativeCamera, false); // Includes the latest resize projection.
    const dx = owner.x - subject.x, dz = owner.z - subject.z;
    const distance = Math.hypot(dx, dz);
    const forwardX = distance > .01 ? dx / distance : Math.sin(subject.yaw || 0);
    const forwardZ = distance > .01 ? dz / distance : Math.cos(subject.yaw || 0);
    const index = reduced?.matches ? 1 : frame;
    const [away, side, up] = [[6.2, 2.4, 6], [4.4, 1.7, 4.2], [5.2, -1.8, 5.2]][index];
    let x = subject.x + forwardX * away + forwardZ * side;
    let z = subject.z + forwardZ * away - forwardX * side;
    const room = dungeon?.ch?.rooms?.reduce((best, candidate) =>
      !best || Math.hypot(candidate.x - subject.x, candidate.z - subject.z) <
        Math.hypot(best.x - subject.x, best.z - subject.z) ? candidate : best, null);
    if (room) {
      x = Math.max(room.x - 6.4, Math.min(room.x + 6.4, x));
      z = Math.max(room.z - 6.4, Math.min(room.z + 6.4, z));
    }
    const floor = globalThis.TERRA_H?.(subject.x, subject.z) || 0;
    camera.position.set(x, floor + up, z);
    // Look a little below the feet: the actor stays above the subtitle card.
    camera.lookAt(subject.x, floor - .3, subject.z);
    camera.updateMatrixWorld(true);
    if (keyLight) {
      keyLight.position.set(subject.x + forwardX * 1.6 + forwardZ * .7,
        floor + 2.5, subject.z + forwardZ * 1.6 - forwardX * .7);
      keyLight.updateMatrixWorld(true);
    }
  }
  function render(renderScene, renderCamera, time) {
    if (!check()) return original.call(this, renderScene, renderCamera, time);
    if (renderScene !== scene || renderCamera !== nativeCamera) return original.call(this, renderScene, renderCamera, time);
    shot();
    return original.call(this, renderScene, camera, time);
  }
  post.render = render;
  return {
    release, check,
    setFrame(index) { frame = Math.max(0, Math.min(2, Math.floor(index) || 0)); },
    get active() { return !released; },
    get camera() { return camera; },
  };
}
