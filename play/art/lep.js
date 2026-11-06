/* ТЕРРА · уличная опора ЛЭП.
 * Песочница Ie.prototype.lep: исходный вызов сохраняет ГСЧ, col 3×3×2, карту и top
 * для lepLine (шаг 48 м). В чанк примитивы не вливаются. Три LOD из assets/art/lep.glb
 * выбираются по дистанции и качеству и сидят одним батчем на материале me.stat
 * (вершинный цвет + TERRA_TEX). Нет запрошенного LOD — возвращаются старые треугольники.
 * Это не замена TERRA_KIT.pylon и не 2-LOD слой ориентиров.
 * ?art=0 или ?lep=0 выключают слой.
 */
(function () {
  'use strict';
  var Q = new URLSearchParams(location.search);
  var ART = window.TERRA_ART = window.TERRA_ART || {};
  var LEP = window.TERRA_LEP = window.TERRA_LEP || {};
  LEP.enabled = Q.get('art') !== '0' && Q.get('lep') !== '0';
  LEP.stats = { replaced: 0, fallback: 0, tris: 0, errors: [], byLod: { lod0: 0, lod1: 0, lod2: 0 }, anchorErrMax: 0, mesh: null };
  LEP.ready = false;
  LEP.failed = false;
  LEP.bounds = null;
  var lib = null, loading = null, H = null;
  var towers = [];
  var mesh = null;
  var applied = '';
  var libGen = 0;
  var flushQueued = false;
  // lep() на this вызывает только эти три метода. Приёмник — чанк, не прокси.
  var HELPERS = { hAt: 1, seg: 1, col: 1 };
  var ANCHORS = [[-4.2, 10.8, 0], [4.2, 10.8, 0], [3, 13.2, 0]];
  var STAT_KEY = 'p01101f2m1';

  function note(code) {
    var tag = 'lep:' + code;
    var list = LEP.stats.errors;
    if (list.indexOf(tag) >= 0 || list.length >= 12) return;
    list.push(tag);
  }

  function extract(scene) {
    var out = {};
    scene.updateMatrixWorld(true);
    scene.traverse(function (o) {
      if (!o.isMesh) return;
      var nm = o.name, a = o;
      while (a && !/\|/.test(nm || '')) { a = a.parent; nm = a && a.name; }
      if (!nm || nm.indexOf('lep|') !== 0) return;
      var g = o.geometry, P = g.attributes.position, N = g.attributes.normal, C = g.attributes.color, I = g.index;
      if (!P || !N || !C) throw new Error('lep attrs ' + nm);
      var cnt = I ? I.count : P.count, mw = o.matrixWorld.elements;
      var nmx = new (o.normalMatrix.constructor)().getNormalMatrix(o.matrixWorld).elements;
      var p = new Float32Array(cnt * 3), n = new Float32Array(cnt * 3), c = new Float32Array(cnt * 3), m = new Uint8Array(cnt);
      for (var k = 0; k < cnt; k++) {
        var v = I ? I.getX(k) : k, x = P.getX(v), y = P.getY(v), z = P.getZ(v);
        p[k * 3] = mw[0] * x + mw[4] * y + mw[8] * z + mw[12];
        p[k * 3 + 1] = mw[1] * x + mw[5] * y + mw[9] * z + mw[13];
        p[k * 3 + 2] = mw[2] * x + mw[6] * y + mw[10] * z + mw[14];
        var nx = N.getX(v), ny = N.getY(v), nz = N.getZ(v);
        var tx = nmx[0] * nx + nmx[3] * ny + nmx[6] * nz, ty = nmx[1] * nx + nmx[4] * ny + nmx[7] * nz, tz = nmx[2] * nx + nmx[5] * ny + nmx[8] * nz;
        var len = Math.hypot(tx, ty, tz) || 1;
        n[k * 3] = tx / len; n[k * 3 + 1] = ty / len; n[k * 3 + 2] = tz / len;
        c[k * 3] = C.getX(v); c[k * 3 + 1] = C.getY(v); c[k * 3 + 2] = C.getZ(v);
        m[k] = Math.round(C.getW(v) * 255);
      }
      var parts = nm.split('|');
      (out[parts[0] + '|' + parts[1]] = out[parts[0] + '|' + parts[1]] || {})[parts[2]] = { p: p, n: n, c: c, m: m };
    });
    return out;
  }

  function footingBounds(part) {
    var p = part && part.p, maxX = 0, maxZ = 0, n = 0;
    if (!p) return null;
    for (var i = 0; i < p.length; i += 3) {
      if (p[i + 1] > 0.4) continue;
      maxX = Math.max(maxX, Math.abs(p[i]));
      maxZ = Math.max(maxZ, Math.abs(p[i + 2]));
      n++;
    }
    return { n: n, maxX: maxX, maxZ: maxZ };
  }

  function load() {
    if (loading || !H) return loading;
    try {
      var GL = H.GL;
      if (!GL) return null;
      loading = fetch(new URL('assets/art/lep.glb', document.baseURI)).then(function (r) {
        if (!r.ok) throw new Error('lep.glb ' + r.status);
        return r.arrayBuffer();
      }).then(function (buf) {
        return new Promise(function (res, rej) {
          var ld = new GL();
          if (H.MD) ld.setMeshoptDecoder(H.MD);
          ld.parse(buf, '', res, rej);
        });
      }).then(function (gltf) {
        lib = extract(gltf.scene);
        var need = ['lep|lod0', 'lep|lod1', 'lep|lod2'];
        for (var i = 0; i < need.length; i++) {
          var part = lib[need[i]];
          if (!part || !part.s || !part.dt) throw new Error('lep group ' + need[i]);
        }
        LEP.bounds = {
          lod0: footingBounds(lib['lep|lod0'].s),
          lod1: footingBounds(lib['lep|lod1'].s),
          lod2: footingBounds(lib['lep|lod2'].s)
        };
        LEP.models = Object.keys(lib);
        LEP.ready = true;
      }).catch(function () { note('glb'); LEP.ready = false; LEP.failed = true; });
    } catch (e) { note('glb'); LEP.failed = true; }
    return loading;
  }

  // Три настоящих LOD. Пропавший уровень не подменяется соседним.
  LEP.debugDrop = function (lod) {
    var key = 'lep|' + lod, saved = lib ? lib[key] : null;
    if (lib) lib[key] = null;
    libGen++;
    applied = '';
    return function () {
      if (lib && saved) lib[key] = saved;
      libGen++;
      applied = '';
    };
  };

  LEP.lodName = function (dist) {
    var g = window.game;
    var q = g && g.qk || 'med';
    if (q === 'low') return 'lod2';
    var det = g && g.Q && g.Q.detR || (q === 'high' ? 40 : 28);
    var d = Number.isFinite(dist) ? dist : 0;
    if (d < det * 0.65) return 'lod0';
    if (d < det * 2.2) return 'lod1';
    return 'lod2';
  };

  function append(b, part, x, y, z, ry) {
    if (!b || !part) return 0;
    var p = part.p, n = part.n, c = part.c, m = part.m;
    var cs = Math.cos(ry || 0), sn = Math.sin(ry || 0);
    for (var k = 0, i = 0; k < m.length; k++, i += 3) {
      var lx = p[i], ly = p[i + 1], lz = p[i + 2];
      b.p.push(x + cs * lx + sn * lz, y + ly, z - sn * lx + cs * lz);
      var nx = n[i], ny = n[i + 1], nz = n[i + 2];
      b.n.push(cs * nx + sn * nz, ny, -sn * nx + cs * nz);
      var V = ny > .6 ? Math.min(1, .86 + Math.max(0, ly) * .1) : Math.min(1, .58 + Math.max(0, ly) * .21);
      b.c.push(c[i] * V, c[i + 1] * V, c[i + 2] * V);
      b.a.push(0, 0);
      if (b.m) b.m.push(m[k]);
      if (b.uv) b.uv.push(.001, .999);
    }
    return m.length / 3;
  }

  function anchorError(x, y, z, ry, top) {
    if (!top || top.length !== 3) return Infinity;
    var cs = Math.cos(ry || 0), sn = Math.sin(ry || 0), err = 0;
    for (var i = 0; i < 3; i++) {
      var lx = ANCHORS[i][0], ly = ANCHORS[i][1], lz = ANCHORS[i][2];
      var dx = (x + cs * lx + sn * lz) - top[i][0];
      var dz = (z - sn * lx + cs * lz) - top[i][1];
      var dy = (y + ly) - top[i][2];
      err = Math.max(err, Math.hypot(dx, dy, dz));
    }
    return err;
  }

  function playerDist(x, z) {
    var p = window.game && game.p;
    if (!p) return 0;
    return Math.hypot(p.x - x, p.z - z);
  }

  function findStat(world) {
    if (!world) return null;
    for (var it = world.chunks.values(), step = it.next(); !step.done; step = it.next()) {
      var meshes = step.value && step.value.meshes || [];
      for (var i = 0; i < meshes.length; i++) {
        var mat = meshes[i].material;
        if (!mat || mat.type !== 'MeshPhongMaterial' || !mat.customProgramCacheKey) continue;
        if (String(mat.customProgramCacheKey()).indexOf(STAT_KEY) === 0) return mat;
      }
    }
    return null;
  }

  function dropMesh() {
    if (!mesh) return;
    var id = mesh.geometry && mesh.geometry.uuid;
    if (mesh.parent) mesh.parent.remove(mesh);
    if (mesh.geometry) mesh.geometry.dispose();
    mesh = null;
    LEP.stats.mesh = null;
    if (id) {
      LEP.stats.invalidated = LEP.stats.invalidated || [];
      if (LEP.stats.invalidated.length < 8) LEP.stats.invalidated.push(id);
    }
  }

  function liveSignature() {
    var g = window.game, bits = [];
    var dungeon = !!(g && g.world && g.world.inDungeon);
    for (var i = 0; i < towers.length; i++) {
      var t = towers[i];
      bits.push(t.cx + ',' + t.cz + ':' + LEP.lodName(playerDist(t.x, t.z)));
    }
    return libGen + (dungeon ? '|d|' : '|s|') + bits.join(';');
  }

  function groupOf(lod) {
    var part = lib && lib['lep|' + lod];
    if (!part || !part.s || !part.dt) return null;
    return part;
  }

  // Пропавший LOD не обнуляет подпись и не пересобирает батч каждые 200 мс.
  // Опоры с живой группой остаются в меше. Чанк, собранный без группы, хранит
  // один слитый примитив — его буфер здесь не трогаем.
  LEP.flush = function () {
    var g = window.game;
    if (!g || !g.scene || !lib) return false;
    var sign = liveSignature();
    if (sign === applied) return true;
    var counts = { lod0: 0, lod1: 0, lod2: 0 };
    if (!towers.length || (g.world && g.world.inDungeon)) {
      dropMesh();
      applied = sign;
      LEP.stats.byLod = counts;
      LEP.stats.tris = 0;
      return true;
    }
    var drawable = [], blocked = null;
    for (var i = 0; i < towers.length; i++) {
      var t = towers[i];
      var lod = LEP.lodName(playerDist(t.x, t.z));
      var part = groupOf(lod);
      if (!part) { blocked = lod; continue; }
      drawable.push({ t: t, lod: lod, part: part });
    }
    if (blocked) note('lod-missing:' + blocked);
    var mat = findStat(g.world);
    if (!mat || !H) {
      note('material');
      applied = sign;
      return false;
    }
    if (!drawable.length) {
      dropMesh();
      applied = sign;
      LEP.stats.byLod = counts;
      LEP.stats.tris = 0;
      return true;
    }
    var batch = new H.ue(function () { return 0.5; });
    batch.m = [];
    var tris = 0;
    for (var k = 0; k < drawable.length; k++) {
      var d = drawable[k];
      tris += append(batch, d.part.s, d.t.x, d.t.y, d.t.z, d.t.ry);
      tris += append(batch, d.part.dt, d.t.x, d.t.y, d.t.z, d.t.ry);
      counts[d.lod]++;
    }
    var next = batch.mesh(mat);
    if (!next) { note('mesh'); applied = sign; return false; }
    next.name = 'lep-batch';
    next.matrixAutoUpdate = false;
    next.castShadow = !!(g.world && g.world.shadows);
    next.receiveShadow = true;
    next.frustumCulled = true;
    g.scene.add(next);
    dropMesh();
    mesh = next;
    applied = sign;
    LEP.stats.mesh = { calls: 1, shadow: next.castShadow, material: mat.customProgramCacheKey(), tris: tris, towers: drawable.length };
    LEP.stats.byLod = counts;
    LEP.stats.tris = tris;
    return true;
  };

  function scheduleFlush() {
    if (flushQueued) return;
    flushQueued = true;
    queueMicrotask(function () { flushQueued = false; try { LEP.flush(); } catch (e) { note('flush'); } });
  }

  function dropChunk(cx, cz) {
    var next = [];
    for (var i = 0; i < towers.length; i++) if (towers[i].cx !== cx || towers[i].cz !== cz) next.push(towers[i]);
    if (next.length === towers.length) return;
    towers = next;
    applied = '';
    scheduleFlush();
  }

  function arm(world) {
    if (!world || world.build && world.build.__terraLep) return;
    var build = world.build, discard = world.discardChunk;
    world.build = function () {
      var chunk = build.apply(this, arguments);
      try { LEP.flush(); } catch (e) { note('flush'); }
      return chunk;
    };
    world.build.__terraLep = true;
    if (typeof discard === 'function') {
      world.discardChunk = function (chunk) {
        if (chunk) dropChunk(chunk.cx, chunk.cz);
        return discard.apply(this, arguments);
      };
    }
  }

  function sinkFor(real) {
    var b = new H.ue(real.r);
    b.m = real.m ? [] : null;
    b.uv = real.uv ? [] : null;
    b.oy = real.oy; b.hf = real.hf; b.sink = real.sink;
    b.sw = real.sw; b.swc = real.swc; b.wet = real.wet; b.mt = real.mt;
    return b;
  }

  function merge(real, b) {
    if (!b || !b.p || !b.p.length) return;
    Array.prototype.push.apply(real.p, b.p);
    Array.prototype.push.apply(real.n, b.n);
    Array.prototype.push.apply(real.c, b.c);
    Array.prototype.push.apply(real.a, b.a);
    if (real.m && b.m) Array.prototype.push.apply(real.m, b.m);
    if (real.uv && b.uv) Array.prototype.push.apply(real.uv, b.uv);
  }

  function hook(h) {
    H = h;
    if (!LEP.enabled) return;
    var P = h.Ie.prototype, orig = P.lep;
    if (typeof orig !== 'function' || orig.__terraLep) return;
    var wrapped = function (x, z, ry) {
      if (!LEP.enabled) return orig.apply(this, arguments);
      if (!lib) {
        if (!LEP.failed) load();
        LEP.stats.fallback++;
        return orig.apply(this, arguments);
      }
      var self = this, real = { s: this.s, dt: this.dt }, sk;
      try { sk = { s: sinkFor(real.s), dt: sinkFor(real.dt) }; }
      catch (e) { note('sink'); LEP.stats.fallback++; return orig.apply(this, arguments); }
      var syncIn = function () {
        ['s', 'dt'].forEach(function (k) { sk[k].oy = real[k].oy; sk[k].sink = real[k].sink; });
      };
      syncIn();
      var proxy = new Proxy(this, {
        get: function (tg, key) {
          if (key === 's' || key === 'dt') return sk[key];
          var v = Reflect.get(tg, key, tg);
          if (HELPERS[key] && typeof v === 'function') {
            return function () {
              var r = v.apply(tg, arguments);
              syncIn();
              return r;
            };
          }
          return v;
        },
        set: function (tg, key, val) {
          if (key === 's' || key === 'dt') return true;
          tg[key] = val;
          return true;
        }
      });
      var res;
      try { res = orig.call(proxy, x, z, ry || 0); }
      catch (e) {
        note('throw');
        LEP.stats.fallback++;
        return orig.apply(self, arguments);
      }
      var y = res && res.top && res.top[0] ? res.top[0][2] - 10.8 : NaN;
      var err = anchorError(x, y, z, ry || 0, res && res.top);
      var lod = LEP.lodName(playerDist(x, z));
      var part = groupOf(lod);
      if (!(err <= 0.001) || !part) {
        if (!(err <= 0.001)) note('anchor');
        else note('lod-missing:' + lod);
        merge(real.s, sk.s);
        merge(real.dt, sk.dt);
        LEP.stats.fallback++;
        return res;
      }
      towers.push({ cx: self.cx, cz: self.cz, x: x, y: y, z: z, ry: ry || 0 });
      LEP.stats.replaced++;
      if (err > LEP.stats.anchorErrMax) LEP.stats.anchorErrMax = err;
      if (self.T) arm(self.T);
      applied = '';
      scheduleFlush();
      return res;
    };
    wrapped.__terraLep = true;
    P.lep = wrapped;
    setTimeout(load, 0);
    setInterval(function () { if (lib && towers.length) try { LEP.flush(); } catch (e) { note('flush'); } }, 200);
  }

  var previous = ART.hook;
  ART.hook = function (h) {
    if (typeof previous === 'function') previous(h);
    try { hook(h); } catch (e) { note('hook'); }
  };
})();
