/* ТЕРРА · арт-слой: оружие и инструменты в руках героя (PR [art] №2).
 * Заменяет геометрию Xg (оружие героя) и $g (инструмент взаимодействия героя) моделями из
 * assets/art/held.glb. Особые клинки (TERRA_SWORDS) идут своим путём и не затрагиваются; инструменты
 * строителей лагеря и оружие жителей тоже (они строятся отдельными вызовами Xg/$g, которые не патчатся).
 * Геометрия подменяется на месте в том же BufferGeometry, меш и материал прежние — 0 новых draw calls.
 * Если модели нет или GLB не загрузился — остаётся исходная геометрия. ?art=0 выключает слой.
 * ?artpreview=weapons — витрина всех предметов рядом с героем (для скриншотов).
 */
(function () {
  'use strict';
  var ART = window.TERRA_ART = window.TERRA_ART || {};
  var Q = new URLSearchParams(location.search);
  if (ART.enabled === undefined) ART.enabled = Q.get('art') !== '0';
  var lib = null, HH = null;
  ART.heldStats = { replaced: 0, pending: 0, missing: 0, errors: [] };

  function apply(geo, key) {
    var md = lib[key + '|lod0'], part = md && md.s;
    if (!part) { ART.heldStats.missing++; return false; }
    var A = geo.attributes.position.constructor, cnt = part.m.length;
    geo.setIndex(null);
    ['uv', 'mt', 'aux'].forEach(function (k) { if (geo.attributes[k]) geo.deleteAttribute(k); });
    geo.setAttribute('position', new A(part.p.slice(), 3));
    geo.setAttribute('normal', new A(part.n.slice(), 3));
    geo.setAttribute('color', new A(part.c.slice(), 3));
    geo.setAttribute('aux', new A(new Float32Array(cnt * 2), 2));
    geo.computeBoundingBox(); geo.computeBoundingSphere();
    geo.userData.terraArt = key; ART.heldStats.replaced++;
    return true;
  }
  // вызывается из бандла: TERRA_ART.held(geometry, "w_rifle" | "t_axe"); всегда возвращает ту же geometry
  ART.held = function (geo, key) {
    try {
      if (!ART.enabled || !geo || !geo.attributes || !geo.attributes.position) return geo;
      if (lib) apply(geo, key); else ART.heldStats.pending++;
    } catch (e) { ART.heldStats.errors.push(String(e && e.message || e)); }
    return geo;
  };
  // самодостаточная загрузка (не зависит от версии landmarks.js в кэше браузера)
  function extract(scene) {
    var out = {};
    scene.updateMatrixWorld(true);
    scene.traverse(function (o) {
      if (!o.isMesh) return;
      var a = o, nm = o.name;
      while (a && !/\|/.test(nm || '')) { a = a.parent; nm = a && a.name; }
      if (!nm) return;
      var g = o.geometry, P = g.attributes.position, N = g.attributes.normal, C = g.attributes.color, I = g.index;
      var cnt = I ? I.count : P.count, e = o.matrixWorld.elements, nm3 = new (o.normalMatrix.constructor)().getNormalMatrix(o.matrixWorld).elements;
      var p = new Float32Array(cnt * 3), n = new Float32Array(cnt * 3), c = new Float32Array(cnt * 3), m = new Uint8Array(cnt);
      for (var k = 0; k < cnt; k++) {
        var v = I ? I.getX(k) : k, x = P.getX(v), y = P.getY(v), z = P.getZ(v), nx = N.getX(v), ny = N.getY(v), nz = N.getZ(v);
        p[k * 3] = e[0] * x + e[4] * y + e[8] * z + e[12]; p[k * 3 + 1] = e[1] * x + e[5] * y + e[9] * z + e[13]; p[k * 3 + 2] = e[2] * x + e[6] * y + e[10] * z + e[14];
        var tx = nm3[0] * nx + nm3[3] * ny + nm3[6] * nz, ty = nm3[1] * nx + nm3[4] * ny + nm3[7] * nz, tz = nm3[2] * nx + nm3[5] * ny + nm3[8] * nz, l = Math.hypot(tx, ty, tz) || 1;
        n[k * 3] = tx / l; n[k * 3 + 1] = ty / l; n[k * 3 + 2] = tz / l;
        c[k * 3] = C.getX(v); c[k * 3 + 1] = C.getY(v); c[k * 3 + 2] = C.getZ(v); m[k] = Math.round(C.getW(v) * 255);
      }
      var q = nm.split('|'); (out[q[0] + '|' + q[1]] = out[q[0] + '|' + q[1]] || {})[q[2]] = { p: p, n: n, c: c, m: m };
    });
    return out;
  }
  function load() {
    if (!ART.enabled || !HH || !HH.GL) return;
    fetch(new URL('assets/art/held.glb', document.baseURI)).then(function (r) {
      if (!r.ok) throw new Error('held.glb ' + r.status); return r.arrayBuffer();
    }).then(function (buf) {
      return new Promise(function (res, rej) { var ld = new HH.GL(); if (HH.MD) ld.setMeshoptDecoder(HH.MD); ld.parse(buf, '', res, rej); });
    }).then(function (gltf) {
      lib = extract(gltf.scene); ART.heldReady = true;
      // предметы, собранные до загрузки, пересобираются игрой заново (кэши героя сбрасываются),
      // чтобы её собственные повороты для огнестрела применились к новой геометрии
      var g = window.game;
      if (g && ART.heldStats.pending) {
        if (g.wGeoCache) Object.keys(g.wGeoCache).forEach(function (k) { delete g.wGeoCache[k]; });
        g.wMeshType = null;
        if (g.ixR && g.ixR.geo) Object.keys(g.ixR.geo).forEach(function (k) { if (/^t_/.test(k)) delete g.ixR.geo[k]; });
      }
    }).catch(function (e) { ART.heldStats.errors.push(String(e && e.message || e)); });
  }
  ART.hookHeld = function (h) { HH = h; setTimeout(load, 0); };

  // ---------- витрина ?artpreview=weapons ----------
  var W = ['stick', 'club', 'machete', 'katana', 'greatsword', 'spear', 'revolver', 'shotgun', 'rifle', 'railgun'];
  var T = ['axe', 'wrench', 'crowbar', 'lockpick', 'hammer', 'bandage', 'bottle', 'can'];
  ART.heldShowcase = function () {
    var g = window.game; if (!g || !g.scene || !g.wMesh || !HH) return null;
    var Mesh = g.wMesh.constructor, mat = g.wMat, made = [];
    var px = g.p.x, pz = g.p.z, py = (g.p.y || 0) + .9;
    function put(geo, x, z, gun) {
      var m = new Mesh(geo, mat);
      if (gun) m.rotation.set(0, Math.PI / 2, Math.PI / 2, 'YXZ'); else m.rotation.set(0, 0, Math.PI / 2);
      m.position.set(x, py, z); m.userData.noT = !0; g.scene.add(m); made.push(m);
    }
    // два столбца ниже героя на экране: оружие слева, инструменты справа
    W.forEach(function (k, i) { var geo = HH.Xg(k); ART.held(geo, 'w_' + k); put(geo, px - 3.4 + (i >= 6 ? .9 : 0), pz + .7 + i * .4 + (i >= 6 ? .3 + (i - 6) * .1 : 0), i >= 6); });
    T.forEach(function (k, i) { var geo = HH.Tg(k); ART.held(geo, 't_' + k); put(geo, px + .7, pz + .7 + i * .48, false); });
    ART._showcase = made; return made.length;
  };
})();
