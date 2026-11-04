/* Ambient residents of Raphael's chamber. Borrow the already loaded native rat
 * pool without joining rats.live: the surface controller clears it underground.
 * No enemies, loot, model loads, timers, or save data belong to this module.
 */
const installed = new WeakMap();
const HOMES = [[-3.6, -3], [3.6, -2.5], [3.6, 3]];
const FLOOR = .2;

export function installSewerRats(game) {
  if (installed.has(game)) return installed.get(game);
  const residents = [];
  let context = null;

  function play(rat, moving) {
    const names = moving ? ['walk', 'walk2', 'walk3'] : ['idle', 'idle2', 'idle3'];
    const action = rat.inst.A[names[rat.index]] || rat.inst.A[names[0]];
    if (!action) return;
    action.timeScale = moving ? .65 : .8;
    if (rat.inst.cur === action) return;
    action.reset().fadeIn(.2).play();
    rat.inst.cur?.fadeOut(.2);
    rat.inst.cur = action;
  }

  function clear() {
    for (const {inst, source} of residents) {
      inst.mixer.stopAllAction();
      inst.cur = null;
      // release removes the root and retains shared GLB geometry/materials.
      source.release(inst);
    }
    residents.length = 0;
    context = null;
  }

  function populate(source, world, center) {
    for (const [index, [dx, dz]] of HOMES.entries()) {
      const inst = source.make();
      inst.mixer.stopAllAction();
      inst.cur = null;
      inst.root.visible = true; // A surface rat can enter the pool while hidden.
      inst.root.scale.set(1, 1, 1); // Native Ke has scaled the inner rig already.
      inst.root.rotation.set(0, 0, 0);
      inst.root.traverse(mesh => {
        if (!mesh.isMesh) return;
        mesh.visible = true;
        mesh.castShadow = game.qk === 'high';
        // Animated bounds from a previous surface pose must not hide this rig.
        if (mesh.isSkinnedMesh) mesh.frustumCulled = false;
      });
      const rat = {inst, source, index, home: {x: center.x + dx, z: center.z + dz},
        angle: index * Math.PI * 2 / 3, elapsed: index * 3.1};
      const x = rat.home.x + Math.sin(rat.angle) * .32;
      const z = rat.home.z + Math.cos(rat.angle) * .8;
      inst.root.position.set(x, FLOOR, z);
      play(rat, false);
      inst.mixer.update(0);
      world.scene.add(inst.root);
      residents.push(rat);
    }
  }

  function update(dt, roomCenter) {
    const world = game.world, dungeon = game.dg, source = game.rats?.src;
    if (!game.p || game.p.alive === false || !world?.inDungeon || dungeon?.sewer !== true ||
        game.dungeonTransition || !Number.isFinite(roomCenter?.x) || !Number.isFinite(roomCenter?.z)) {
      clear();
      return;
    }
    if (context && (context.player !== game.p || context.dungeon !== dungeon || context.key !== dungeon.key || context.world !== world ||
        context.source !== source || context.x !== roomCenter.x || context.z !== roomCenter.z)) clear();
    // Native rats load asynchronously. The next ordinary update retries; no
    // second GLB loader or independent animation loop is needed.
    if (game.state !== 'play' || !source?.make || !source?.release || !world.scene) return;
    if (!context) {
      context = {player: game.p, dungeon, key: dungeon.key, world, source, x: roomCenter.x, z: roomCenter.z};
      populate(source, world, roomCenter);
    }
    const step = Number.isFinite(dt) ? Math.max(0, Math.min(dt, .1)) : 0;
    for (const rat of residents) {
      rat.elapsed += step;
      let moving = rat.elapsed % 12 < 7.5;
      if (moving && step > 0) {
        const root = rat.inst.root, old = root.position, angle = rat.angle + step * .34;
        const next = {x: rat.home.x + Math.sin(angle) * .32,
          z: rat.home.z + Math.cos(angle) * .8};
        const blocked = world.segHit?.(old.x, old.z, next.x, next.z, .3) >= 0;
        if (!blocked) world.collide?.(next, .12);
        const safe = !blocked && Math.abs(next.x - rat.home.x) < .55 &&
          Math.abs(next.z - rat.home.z) < 1.05 && Math.hypot(next.x - old.x, next.z - old.z) < .15;
        if (safe) {
          const dx = next.x - old.x, dz = next.z - old.z;
          if (Math.hypot(dx, dz) > .00001) {
            const yaw = Math.atan2(dx, dz), difference = yaw - root.rotation.y;
            root.rotation.y += Math.atan2(Math.sin(difference), Math.cos(difference)) * Math.min(1, step * 7);
          }
          root.position.set(next.x, FLOOR, next.z);
          rat.angle = angle;
        } else moving = false;
      }
      play(rat, moving);
      rat.inst.mixer.update(step);
    }
  }

  const api = {update, clear, get count() { return residents.length; }};
  installed.set(game, api);
  return api;
}
