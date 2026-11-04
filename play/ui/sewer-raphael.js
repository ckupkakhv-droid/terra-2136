/* Raphael uses the external art asset in a private pool, with the native
 * mutant decoration retained only as a fallback if the asset fails to load.
 * Victory and rewards belong to the protected native persistence flow.
 */
export const RAPHAEL_ID = 'sewer_raphael';
export const RAPHAEL_MODEL = 'sewer_raphael_model';
const installed = new WeakMap();

export function installRaphael(game, bridge) {
  if (installed.has(game)) return installed.get(game);
  const owned = new Map();
  const nativeAI = game.bossAI2;
  const nativeUpdate = game.enemyUpdate;
  const nativeSync = game.syncInst;
  const nativeRemove = game.removeEnemy;
  const nativeRim = game.bossRim;
  let authoredModel = false;
  const singlePlayer = () => !game._coopGuest && !game.net?.role;
  const sameExpedition = state => game.p === state.player && game.dg === state.dungeon &&
    game.dg?.key === state.key && game.dg?.sewer === true && game.world.inDungeon && singlePlayer();

  function ensurePool() {
    if (game.glb?.[RAPHAEL_MODEL]) return true;
    authoredModel = !!game.glb?.sewer_mutant;
    const source = game.glb?.sewer_mutant || game.glb?.mutant;
    if (!source?.make || !source?.release) return false;
    game.glb[RAPHAEL_MODEL] = Object.assign(Object.create(Object.getPrototypeOf(source)), source, {free: []});
    return true;
  }

  function mesh(geometry, color, position, scale, parent) {
    const part = new bridge.Mesh(geometry, new bridge.Material({color, roughness: .82}));
    part.position.set(...position); part.scale.set(...scale);
    part.castShadow = true; parent.add(part);
    return part;
  }

  function decorate(enemy) {
    const inst = enemy.inst;
    if (!inst || inst._sewerRaphaelDecorated) return;
    inst._sewerRaphaelDecorated = true;
    if (authoredModel) return; // Shell, band and sai are already skinned into this GLB.
    for (const material of inst.mats) material.color?.setHex(0x89a565);
    const root = inst.root;
    const sphere = new bridge.Sphere(1, 12, 8);
    const rod = (color, position, scale, parent) => mesh(sphere, color, position,
      [scale[0], scale[1] / 2, scale[2]], parent);
    mesh(sphere, 0x344637, [0, 1.35, -.42], [.72, .83, .3], root);
    mesh(sphere, 0x756544, [0, 1.3, .26], [.48, .61, .13], root);
    root.updateMatrixWorld(true);
    function boneGroup(name) {
      const bone = root.getObjectByName(name);
      if (!bone) return null;
      const group = new bridge.Group(); bone.add(group);
      // Bones inherit the GLB's unit conversion. Equipment uses game metres.
      const parentScale = bone.getWorldScale(root.position.clone());
      const rootScale = root.getWorldScale(root.position.clone());
      group.scale.set(rootScale.x / (parentScale.x || 1),
        rootScale.y / (parentScale.y || 1), rootScale.z / (parentScale.z || 1));
      return group;
    }
    const head = boneGroup('Head');
    if (head) {
      mesh(sphere, 0x9c2e2e, [0, .11, .015], [.27, .055, .25], head);
      rod(0x8a2727, [.2, .07, -.25], [.045, .3, .035], head).rotation.z = -.6;
    }
    for (const name of ['LeftHand', 'RightHand']) {
      const hand = boneGroup(name);
      if (!hand) continue;
      rod(0x332d27, [0, -.12, 0], [.035, .22, .035], hand);
      rod(0xb7b7a7, [0, .28, 0], [.022, .62, .022], hand);
      rod(0x939887, [0, .02, 0], [.022, .25, .022], hand).rotation.z = Math.PI / 2;
      for (const x of [-.12, .12]) rod(0x939887, [x, .1, 0], [.018, .18, .018], hand);
    }
    // The native rim pass collects these materials too. This pool is private.
  }

  function pose(enemy, name, duration = 1, hit = 0) {
    if (enemy.act?.n === name && ['idle', 'walk', 'run'].includes(name)) return;
    game.bossAct(enemy, name, duration, hit);
    enemy._actRef = null;
  }

  function recover(enemy, state, duration = .85) {
    state.phase = 'recover'; state.left = duration;
    state.hit = false; enemy.atk = 0; enemy.charge = 0;
    pose(enemy, 'idle');
  }

  function move(enemy, dx, dz, distance) {
    const ox = enemy.x, oz = enemy.z;
    const steps = Math.max(1, Math.ceil(distance / .3));
    for (let i = 0; i < steps; i++) {
      const x = enemy.x, z = enemy.z;
      enemy.x += dx * distance / steps; enemy.z += dz * distance / steps;
      const collision = game.world.collide(enemy, enemy.r);
      if (collision && Math.hypot(enemy.x - x, enemy.z - z) < distance / steps * .65) break;
    }
    return Math.hypot(enemy.x - ox, enemy.z - oz);
  }

  function turn(enemy, yaw, dt) {
    const delta = Math.atan2(Math.sin(yaw - enemy.yaw), Math.cos(yaw - enemy.yaw));
    enemy.yaw += delta * Math.min(1, dt * 8);
  }

  function clearShot(enemy, player) {
    return typeof game.world.segHit !== 'function' || game.world.segHit(enemy.x, enemy.z, player.x, player.z, 1.2) < 0;
  }

  function telegraph(enemy, state, dash) {
    const player = game.p;
    const distance = Math.hypot(player.x - enemy.x, player.z - enemy.z) || 1;
    state.dx = (player.x - enemy.x) / distance; state.dz = (player.z - enemy.z) / distance;
    state.yaw = Math.atan2(state.dx, state.dz); state.hit = false;
    state.phase = dash ? 'wind-dash' : 'wind-melee'; state.left = dash ? 1.05 : .8;
    enemy.yaw = state.yaw;
    pose(enemy, dash ? 'idle' : 'attack', 1.1, .8);
    game.ring?.(enemy.x, enemy.z, dash ? 1.2 : 2.45, '#c56b59', state.left, false);
    if (dash) for (const step of [2.5, 5, 7.5]) {
      game.ring?.(enemy.x + state.dx * step, enemy.z + state.dz * step, .65, '#c56b59', state.left, false);
    }
  }

  function updateRaphael(enemy, dt) {
    const state = owned.get(enemy);
    if (!state || !sameExpedition(state) || !game.p.alive || game.state !== 'play' || game.cine) return;
    dt = Math.max(0, Math.min(.1, Number.isFinite(dt) ? dt : 0));
    enemy.act.t += dt; enemy.aggro = true;
    state.dashCooldown = Math.max(0, state.dashCooldown - dt);
    if (enemy.rooted > 0) { recover(enemy, state); return; }
    const player = game.p, dx = player.x - enemy.x, dz = player.z - enemy.z;
    const distance = Math.hypot(dx, dz);
    if (state.phase === 'recover') {
      state.left -= dt;
      turn(enemy, Math.atan2(dx, dz), dt);
      if (state.left <= 0) state.phase = 'chase';
      return;
    }
    if (state.phase.startsWith('wind-')) {
      state.left -= dt;
      if (state.left > 0) return;
      if (state.phase === 'wind-dash') {
        state.phase = 'dash'; state.left = .7; state.dashCooldown = 7;
        pose(enemy, 'run');
      } else {
        const facing = (dx * state.dx + dz * state.dz) / (distance || 1);
        if (distance < 2.65 && facing > .25 && clearShot(enemy, player)) game.hurtPlayer(enemy.dmg, enemy);
        recover(enemy, state, .95);
      }
      return;
    }
    if (state.phase === 'dash') {
      state.left -= dt;
      const step = 10.5 * dt, travelled = move(enemy, state.dx, state.dz, step);
      enemy.yaw = state.yaw;
      if (!state.hit && Math.hypot(player.x - enemy.x, player.z - enemy.z) < enemy.r + .65 && clearShot(enemy, player)) {
        state.hit = true; game.hurtPlayer(enemy.dmg * 1.2, enemy);
      }
      if (state.hit || state.left <= 0 || travelled < step * .65) recover(enemy, state, 1.35);
      return;
    }
    if (distance < 2.25) { telegraph(enemy, state, false); return; }
    if (distance > 5 && distance < 11 && state.dashCooldown <= 0 && clearShot(enemy, player)) {
      telegraph(enemy, state, true); return;
    }
    const speed = enemy.spd * (enemy.slow ? 1 - enemy.slow[0] : 1);
    if (distance > .01) move(enemy, dx / distance, dz / distance, speed * dt);
    turn(enemy, Math.atan2(dx, dz), dt); pose(enemy, 'walk');
  }

  game.bossAI2 = function(enemy, dt, ...args) {
    if (enemy.boss === RAPHAEL_ID && owned.has(enemy)) return updateRaphael(enemy, dt);
    return nativeAI.call(this, enemy, dt, ...args);
  };
  game.syncInst = function(enemy) {
    const result = nativeSync.call(this, enemy);
    if (owned.has(enemy)) decorate(enemy);
    return result;
  };
  game.bossRim = function(enemy) {
    if (!owned.has(enemy) || !authoredModel) return nativeRim.call(this, enemy);
    // Native rim converts Standard to Phong and drops the imported normal map.
    const surfaces = [];
    enemy.inst.root.traverse(node => {
      if (node.isMesh && node.material?.normalMap) surfaces.push({node,
        normalMap:node.material.normalMap, normalScale:node.material.normalScale.clone(),
        alphaTest:node.material.alphaTest});
    });
    const result = nativeRim.call(this, enemy);
    for (const {node,normalMap,normalScale,alphaTest} of surfaces) {
      Object.assign(node.material,{normalMap,normalScale,alphaTest,needsUpdate:true});
    }
    return result;
  };
  game.removeEnemy = function(index) {
    const enemy = this.enemies[index];
    const result = nativeRemove.call(this, index);
    owned.delete(enemy);
    return result;
  };
  game.enemyUpdate = function(dt) {
    for (const [enemy, state] of owned) {
      if (!this.enemies.includes(enemy)) { owned.delete(enemy); continue; }
      if (!sameExpedition(state)) { this.removeEnemy(this.enemies.indexOf(enemy)); continue; }
      if (!enemy.dead && (enemy.stun > 0 || enemy.stagger > 0 || !this.p.alive) && state.phase !== 'recover') {
        recover(enemy, state);
      }
    }
    return nativeUpdate.call(this, dt);
  };

  const api = {
    spawn(x, z) {
      const definition = (bridge.bosses || bridge.Bosses)?.[RAPHAEL_ID];
      if (!Number.isFinite(x) || !Number.isFinite(z) || !singlePlayer() || game.state !== 'play' || !game.p?.alive ||
          !game.world.inDungeon || game.dg?.sewer !== true || !game.dg.key || game.defeated?.[game.dg.key] ||
          definition?.model !== RAPHAEL_MODEL || definition.base !== 'mutant' || !ensurePool()) return null;
      const existing = [...owned.keys()].find(enemy => !enemy.dead && game.enemies.includes(enemy));
      if (existing) return existing;
      const enemy = game.spawnEnemy(null, x, z, {boss: RAPHAEL_ID, force: 1, lvl: Math.max(1, game.p.level || 1)});
      if (!enemy) return null;
      if (authoredModel) { enemy.sc = 1.05; enemy.def = {...enemy.def,h:1.8}; }
      game.bossInit(enemy); enemy.revive = false;
      owned.set(enemy, {player: game.p, dungeon: game.dg, key: game.dg.key, phase: 'chase', left: 0, dashCooldown: 3});
      game.bossE = enemy;
      return enemy;
    },
    clear() {
      for (const enemy of [...owned.keys()]) {
        const index = game.enemies.indexOf(enemy);
        if (index >= 0) game.removeEnemy(index); else owned.delete(enemy);
      }
    },
    get enemy() { return [...owned.keys()].find(enemy => !enemy.dead && game.enemies.includes(enemy)) || null; },
  };
  installed.set(game, api);
  return api;
}
