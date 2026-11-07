/* Насос I, только существующая камера k===1.
 * Три LOD из assets/sewer/pump/pump1.glb. Материал — статический меш коллектора,
 * поэтому карты грязи и срез по высоте те же. Насос II остаётся прежним ящиком.
 * Сбой загрузки не трогает примитив: replace() возвращает false, ГСЧ не сдвигается.
 */
(function () {
  'use strict';
  var query = new URLSearchParams(location.search);
  var api = window.TERRA_PUMP1 = window.TERRA_PUMP1 || {};
  api.enabled = query.get('pump1') !== '0';
  api.ready = false;
  api.failed = false;
  api.bands = [34, 52];
  api.anchors = new WeakMap();
  api.errors = [];
  api.level = 0;
  api.distance = 0;
  api.group = null;
  api.packed = null;
  api.tris = null;
  var loaderApi = null;

  function note(err) { try { api.errors.push(String(err && err.message || err)); } catch (_) {} }

  function lodName(object) {
    var node = object, name = object.name || '';
    while (node && !/^pump1\|lod[012]\|s$/.test(name)) {
      node = node.parent;
      name = (node && node.name) || '';
    }
    return /^pump1\|(lod[012])\|s$/.exec(name);
  }

  function capture(source) {
    source.updateMatrixWorld(true);
    var packed = {};
    source.traverse(function (object) {
      if (!object.isMesh) return;
      var found = lodName(object);
      if (!found || packed[found[1]]) return;
      var geometry = object.geometry;
      var position = geometry.getAttribute('position');
      var normal = geometry.getAttribute('normal');
      var color = geometry.getAttribute('color');
      var index = geometry.getIndex();
      if (!position || !normal || !color) throw new Error('pump1 attributes');
      var count = index ? index.count : position.count;
      var world = object.matrixWorld.elements;
      var normalMatrix = new object.normalMatrix.constructor().getNormalMatrix(object.matrixWorld).elements;
      var p = new Float32Array(count * 3), n = new Float32Array(count * 3), c = new Float32Array(count * 3);
      var aux = new Float32Array(count * 2), mt = new Float32Array(count);
      for (var k = 0; k < count; k++) {
        var v = index ? index.getX(k) : k;
        var x = position.getX(v), y = position.getY(v), z = position.getZ(v);
        var py = world[1] * x + world[5] * y + world[9] * z + world[13];
        p[k * 3] = world[0] * x + world[4] * y + world[8] * z + world[12];
        p[k * 3 + 1] = py;
        p[k * 3 + 2] = world[2] * x + world[6] * y + world[10] * z + world[14];
        var nx = normal.getX(v), ny = normal.getY(v), nz = normal.getZ(v);
        var tx = normalMatrix[0] * nx + normalMatrix[3] * ny + normalMatrix[6] * nz;
        var ty = normalMatrix[1] * nx + normalMatrix[4] * ny + normalMatrix[7] * nz;
        var tz = normalMatrix[2] * nx + normalMatrix[5] * ny + normalMatrix[8] * nz;
        var length = Math.hypot(tx, ty, tz) || 1;
        n[k * 3] = tx / length; n[k * 3 + 1] = ty / length; n[k * 3 + 2] = tz / length;
        // Тот же вершинный свет, что у s.add: верх светлее, бок темнее.
        var light = ty / length > .6 ? Math.min(1, .86 + Math.max(0, py) * .1) : Math.min(1, .58 + Math.max(0, py) * .21);
        c[k * 3] = color.getX(v) * light; c[k * 3 + 1] = color.getY(v) * light; c[k * 3 + 2] = color.getZ(v) * light;
        mt[k] = Math.round(color.getW(v) * 255);
      }
      packed[found[1]] = {p: p, n: n, c: c, a: aux, m: mt, tris: count / 3};
    });
    if (!packed.lod0 || !packed.lod1 || !packed.lod2) throw new Error('pump1 lod');
    return packed;
  }

  var loadTries = 0;
  function load() {
    if (!api.enabled || !loaderApi || api.ready || api.failed) return;
    // GLTFLoader дочитывается ленивым модулем уже после хука арт-слоя.
    var GL = loaderApi.GL, MD = loaderApi.MD;
    if (!GL) {
      if (++loadTries > 80) { api.failed = true; note('no gltf loader'); return; }
      setTimeout(load, 50);
      return;
    }
    fetch(new URL('assets/sewer/pump/pump1.glb', document.baseURI)).then(function (response) {
      if (!response.ok) throw new Error('pump1.glb ' + response.status);
      return response.arrayBuffer();
    }).then(function (buffer) {
      return new Promise(function (resolve, reject) {
        var parser = new GL();
        if (MD) parser.setMeshoptDecoder(MD);
        parser.parse(buffer, '', resolve, reject);
      });
    }).then(function (gltf) {
      api.packed = capture(gltf.scene);
      api.tris = {lod0: api.packed.lod0.tris, lod1: api.packed.lod1.tris, lod2: api.packed.lod2.tris};
      api.ready = true;
    }).catch(function (err) { api.failed = true; api.ready = false; note(err); });
  }

  api.replace = function (chunk, batch, shapes, x, z, paint) {
    if (!api.enabled || api.failed || !api.ready || !api.packed) return false;
    if (!chunk || !chunk.cols || !batch || typeof batch.Y !== 'function' || typeof paint !== 'function') return false;
    // Пустая пачка делит ГСЧ с комнатой: следующие ящики сохраняют прежний цвет.
    var ghost = Object.create(batch);
    ghost.p = []; ghost.n = []; ghost.c = []; ghost.a = [];
    ghost.m = null; ghost.uv = null;
    paint(ghost, shapes, x, z);
    var ground = batch.Y(x + 4, z);
    api.anchors.set(chunk.cols, {x: x + 4, z: z, y: Number.isFinite(ground) ? ground : 0});
    return true;
  };

  function statMesh(game) {
    var meshes = game && game.dg && game.dg.ch && game.dg.ch.meshes;
    if (!meshes) return null;
    for (var i = 0; i < meshes.length; i++) {
      var mesh = meshes[i];
      if (mesh && mesh.geometry && mesh.geometry.getAttribute && mesh.geometry.getAttribute('aux') && mesh.material) return mesh;
    }
    return null;
  }

  function buildGeometry(sample, packed) {
    var attribute = sample.geometry.getAttribute('position').constructor;
    var geometry = new sample.geometry.constructor();
    geometry.setAttribute('position', new attribute(packed.p, 3));
    geometry.setAttribute('normal', new attribute(packed.n, 3));
    geometry.setAttribute('color', new attribute(packed.c, 3));
    geometry.setAttribute('aux', new attribute(packed.a, 2));
    geometry.setAttribute('mt', new attribute(packed.m, 1));
    geometry.computeBoundingBox();
    geometry.computeBoundingSphere();
    return geometry;
  }

  api.detach = function () {
    var group = api.group;
    api.group = null;
    if (!group) return;
    group.removeFromParent();
    for (var i = 0; i < group.children.length; i++) {
      var mesh = group.children[i];
      if (mesh.geometry) mesh.geometry.dispose();
    }
  };

  function attach(game, anchor, sample) {
    var bridge = window.TERRA_SEWER_BRIDGE;
    if (!bridge || !bridge.Group || !bridge.Mesh || !game.world || !game.world.scene) return false;
    var group = new bridge.Group();
    group.name = 'sewer-pump-1';
    group.position.set(anchor.x, anchor.y, anchor.z);
    group.frustumCulled = true;
    ['lod0', 'lod1', 'lod2'].forEach(function (level) {
      var mesh = new bridge.Mesh(buildGeometry(sample, api.packed[level]), sample.material);
      mesh.name = 'sewer-pump-1-' + level;
      mesh.frustumCulled = true;
      mesh.castShadow = !!sample.castShadow;
      mesh.receiveShadow = true;
      mesh.visible = false;
      group.add(mesh);
    });
    game.world.scene.add(group);
    api.group = group;
    return true;
  }

  api.select = function (camera) {
    var group = api.group;
    if (!group || !camera) return api.level;
    var at = group.position;
    var distance = Math.hypot(camera.position.x - at.x, camera.position.y - at.y, camera.position.z - at.z);
    api.distance = distance;
    var level = distance < api.bands[0] ? 0 : distance < api.bands[1] ? 1 : 2;
    api.level = level;
    group.frustumCulled = true;
    for (var i = 0; i < group.children.length; i++) {
      group.children[i].visible = i === level;
      // Загрузчик и обход сцены не должны оставлять насос без отсечения.
      group.children[i].frustumCulled = true;
    }
    return level;
  };

  api.frame = function (game) {
    try {
      if (!api.enabled || !api.ready) { api.detach(); return; }
      var sewer = game && game.dg && game.dg.sewer && game.dg.ch;
      var anchor = sewer ? api.anchors.get(game.dg.ch.cols) : null;
      if (!anchor) { api.detach(); return; }
      if (!api.group) {
        var sample = statMesh(game);
        if (!sample || !attach(game, anchor, sample)) return;
      }
      api.select(game.cam);
    } catch (err) { note(err); api.detach(); }
  };

  var art = window.TERRA_ART = window.TERRA_ART || {};
  var previous = art.hook;
  art.hook = function (hookApi) {
    if (typeof previous === 'function') previous(hookApi);
    loaderApi = hookApi;
    load();
  };
})();
