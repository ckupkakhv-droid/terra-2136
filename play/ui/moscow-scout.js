/* One optional surface encounter. The native player modules and save schema are
 * untouched: the scout has its own model instance and encounter lifetime. */
export function installMoscowScout(game) {
  let enemy = null, visual = null, owner = null, world = null, origin = null, rotors = [];
  let pending = false, spentPlayer = null, phase = 'search', left = 0, aim = null, clock = 0;
  let retry = 0, remaining = 0;
  const originalUpdate = game.enemyUpdate, originalKill = game.killEnemy;
  const originalHit = game.fxHit, originalMobSound = game.sfx?.mob;

  function remove() {
    if (visual) {
      visual.removeFromParent();
      visual.traverse(node => {
        if (node.userData?.scoutMaterial) {
          for (const material of Array.isArray(node.material) ? node.material : [node.material]) material?.dispose();
        }
      });
    }
    if (enemy) {
      const index = game.enemies.indexOf(enemy);
      if (index >= 0) game.enemies.splice(index, 1);
    }
    enemy = null; visual = null; origin = null; aim = null; pending = false; owner = null; world = null; rotors = [];
  }

  function valid() {
    return game.p === owner && owner?.alive && game.world === world && !world.inDungeon &&
      !game.dungeonTransition && !game._coopGuest && !game.net?.role;
  }

  function place() {
    const source = game.droneM?.[0]?.children?.find(child => child.getObjectByName?.('drone_body'));
    if (!source || !valid()) return false;
    const p = game.p;
    let spot = null;
    for (const r of [3, 4, 5]) {
      for (let a = 0; a < Math.PI * 2; a += Math.PI / 4) {
        const candidate = {x:p.x + Math.cos(a)*r, z:p.z + Math.sin(a)*r};
        if (!world.collide(candidate, .5) && world.segHit(p.x,p.z,candidate.x,candidate.z,1.1) < 0) {
          spot = candidate; break;
        }
      }
      if (spot) break;
    }
    if (!spot) return false;
    const model = source.clone(true);
    model.name = 'moscowScoutVisual';
    model.scale.setScalar(1.4);
    const modelRotors = [];
    model.traverse(node => {
      if (/^rotor_(BL|BR|FL|FR)$/.test(node.name)) modelRotors.push(node);
      if (!node.isMesh) return;
      node.material = Array.isArray(node.material) ? node.material.map(m => m.clone()) : node.material.clone();
      node.userData.scoutMaterial = true;
      for (const material of Array.isArray(node.material) ? node.material : [node.material]) {
        if (material.emissive) material.emissive.setRGB(.3,.035,.02);
      }
    });
    const scout = game.spawnEnemy('zombie',spot.x,spot.z,{force:1,lvl:1,aggro:1});
    if (!scout) {
      model.traverse(node => { if (node.userData?.scoutMaterial) for (const material of Array.isArray(node.material) ? node.material : [node.material]) material?.dispose(); });
      return false;
    }
    enemy = scout; visual = model; origin = spot; rotors = modelRotors; enemy.moscowScout = true;
    enemy.def = {...enemy.def,h:2.3,name:'Разведчик AGI'}; enemy.name='Разведчик AGI';
    enemy.r = .8; enemy.sc = 1; enemy.hp = enemy.maxHp = 90;
    enemy.revive = false; enemy.xp = 0;
    visual.position.set(spot.x,(window.TERRA_H?.(spot.x,spot.z)||0)+1.65,spot.z);
    visual.rotation.y=Math.atan2(p.x-spot.x,p.z-spot.z);
    world.scene.add(visual); phase = 'search'; left = 4; clock = 0; aim = null;
    game.ring(spot.x,spot.z,.9,'#ff866b',1.4,false);
    game.ui.toast('Сигнал обнаружен: разведчик ведёт поиск');
    return true;
  }

  function tick(dt) {
    if (!Number.isFinite(dt) || dt <= 0) return;
    if ((enemy || pending) && !valid()) { remove(); return; }
    if (game.state !== 'play') return;
    if (pending && !enemy) {
      remaining -= Math.min(dt,.1); retry -= Math.min(dt,.1);
      if (remaining <= 0) { remove(); return; }
      if (retry <= 0) { retry=.5; if (place()) pending = false; }
      return;
    }
    if (!enemy) return;
    if (enemy.dead || !game.enemies.includes(enemy) || Math.hypot(game.p.x-origin.x,game.p.z-origin.z) > 35) { remove(); return; }
    for (const kind of ['bleed','burn']) {
      const effect=enemy[kind];
      if (!effect) continue;
      effect[1]-=dt;
      game.hurtEnemy(enemy,effect[0]*Math.min(dt,Math.max(0,effect[1]+dt)),{dot:true,wt:effect[2]?.wt,deathSt:effect[2]?.st});
      if (effect[1]<=0) enemy[kind]=null;
      if (enemy.dead) { remove(); return; }
    }
    clock += Math.min(dt,.1);
    const x=origin.x+Math.cos(clock*.6), z=origin.z+Math.sin(clock*.6);
    if (!world.collide({x,z},.5)) { enemy.x=x; enemy.z=z; }
    const floor=window.TERRA_H?.(enemy.x,enemy.z)||0;
    visual.position.set(enemy.x,floor+1.65+Math.sin(clock*2)*.12,enemy.z);
    visual.rotation.y=Math.atan2(game.p.x-enemy.x,game.p.z-enemy.z);
    for (const rotor of rotors) rotor.rotation.y += dt*10;
    left -= Math.min(dt,.1);
    if (phase === 'search' && left <= 0) {
      if (Math.hypot(game.p.x-enemy.x,game.p.z-enemy.z)>12 || world.segHit(enemy.x,enemy.z,game.p.x,game.p.z,1.1)>=0) { left=1; return; }
      aim={x:game.p.x,z:game.p.z}; phase='aim'; left=1.1;
      game.ring(aim.x,aim.z,1.35,'#e86c54',1.1,false);
      game.ui.toast('Разведчик наводится — уходите с отметки');
    } else if (phase === 'aim' && left <= 0) {
      if (aim && world.segHit(enemy.x,enemy.z,aim.x,aim.z,1.1)<0) {
        game.beam(enemy.x,enemy.z,aim.x,aim.z,'#ff866b',.18,.045);
        game.sfx?.modShot?.('drone',enemy);
        if (Math.hypot(game.p.x-aim.x,game.p.z-aim.z)<1.35 && world.segHit(enemy.x,enemy.z,game.p.x,game.p.z,1.1)<0) game.hurtPlayer(8,enemy);
      }
      phase='search'; left=3.5; aim=null;
    }
  }

  game.enemyUpdate = function(dt, ...args) {
    const actor = enemy, list = this.enemies, index = actor ? list.indexOf(actor) : -1;
    if (index >= 0) list.splice(index,1);
    try { return originalUpdate.call(this,dt,...args); }
    finally {
      if (index >= 0 && actor === enemy && !actor.dead) list.splice(Math.min(index,list.length),0,actor);
      tick(dt);
    }
  };
  game.killEnemy = function(target,...args) {
    if (target !== enemy) return originalKill.call(this,target,...args);
    target.dead=true; spentPlayer=owner;
    this.ring(target.x,target.z,1.2,'#ffb777',.35,true);
    this.ui.toast('Разведчик выведен из строя');
  };
  if (typeof originalHit === 'function') game.fxHit = function(target,...args) {
    if (target !== enemy) return originalHit.call(this,target,...args);
    // Reuse the native metal sparks without changing the actor's combat type.
    game.sfx?.impactHit?.(target,'metal');
    return originalHit.call(this,{...target,boss:'moloh',bt:{armorOff:false}},...args);
  };
  if (typeof originalMobSound === 'function') game.sfx.mob = function(target,...args) {
    if (target !== enemy) return originalMobSound.call(this,target,...args);
  };
  return Object.freeze({
    start() {
      if (spentPlayer === game.p || enemy || pending || game.state !== 'play' || !game.p?.alive ||
          game.world.inDungeon || game.dungeonTransition || game._coopGuest || game.net?.role) return false;
      owner=game.p; world=game.world; pending=true; retry=0; remaining=30;
      return true;
    },
    check() {
      if (spentPlayer && spentPlayer !== game.p) spentPlayer = null;
      if ((enemy || pending) && !valid()) remove();
    },
    get engaged() { return pending || (!!enemy && !enemy.dead); },
    get active() { return !!enemy && !enemy.dead; },
  });
}
