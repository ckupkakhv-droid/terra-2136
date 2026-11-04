/* ТЕРРА · срочные визуальные правки мира (лужи, камни).
 * Вешается на TERRA_ART.hook после ориентиров и не трогает их обёртку.
 * ГСЧ чанка не расходуется: лужи и перекрас камней идут после штатных вызовов.
 */
(function () {
  'use strict';
  var ART = window.TERRA_ART = window.TERRA_ART || {};
  var prevHook = ART.hook;
  var L = null;
  var installed = false;

  function hash(x, z) {
    var s = Math.sin(x * 127.1 + z * 311.7) * 43758.5453;
    return s - Math.floor(s);
  }

  function colorHex(c) {
    if (typeof c === 'string') return c.toLowerCase();
    if (c && typeof c.getHexString === 'function') return '#' + c.getHexString();
    return '';
  }

  function puddlePrim(seed) {
    var seg = 22, p = [], n = [], edge = [];
    var radii = [];
    for (var i = 0; i < seg; i++) {
      var a = i / seg * Math.PI * 2;
      var w = 0.72 + 0.18 * Math.sin(a * 2 + seed * 6.28) + 0.1 * Math.sin(a * 5.3 + seed * 2.2);
      radii.push(0.5 * w);
    }
    function vert(x, z, e) {
      p.push(x, 0, z);
      n.push(0, 1, 0);
      edge.push(e);
    }
    for (var i = 0; i < seg; i++) {
      var i2 = (i + 1) % seg;
      var a1 = i / seg * Math.PI * 2, a2 = i2 / seg * Math.PI * 2;
      vert(0, 0, 0.08);
      vert(Math.cos(a1) * radii[i], Math.sin(a1) * radii[i], 1);
      vert(Math.cos(a2) * radii[i2], Math.sin(a2) * radii[i2], 1);
    }
    return { p: p, n: n, edge: edge };
  }

  function paintEdge(batch, prim, before) {
    var verts = (batch.p.length - before) / 3;
    var edge = prim.edge;
    if (!edge || verts !== edge.length || !batch.a) return;
    var base = batch.a.length - verts * 2;
    for (var i = 0; i < verts; i++) batch.a[base + i * 2] = edge[i];
  }

  function patchWater(mat) {
    if (!mat || mat.userData.terraPuddle) return;
    mat.userData.terraPuddle = 1;
    mat.polygonOffset = true;
    mat.polygonOffsetFactor = -2;
    mat.polygonOffsetUnits = -2;
    var prev = mat.onBeforeCompile;
    var prevKey = mat.customProgramCacheKey && mat.customProgramCacheKey.bind(mat);
    mat.onBeforeCompile = function (shader, renderer) {
      if (prev) prev.call(this, shader, renderer);
      if (shader.vertexShader.indexOf('vPuddle') === -1) {
        shader.vertexShader = 'attribute vec2 aux;\nvarying float vPuddle;\n' + shader.vertexShader;
        shader.vertexShader = shader.vertexShader.replace(
          'vWP=(modelMatrix*vec4(transformed,1.0)).xyz;',
          'vWP=(modelMatrix*vec4(transformed,1.0)).xyz;vPuddle=aux.x;'
        );
      }
      if (shader.fragmentShader.indexOf('vPuddle') === -1) {
        shader.fragmentShader = 'varying float vPuddle;\n' + shader.fragmentShader;
        shader.fragmentShader = shader.fragmentShader.replace(
          'gl_FragColor.rgb+=vec3(.03,.05,.05)*smoothstep(.6,1.,s);',
          'gl_FragColor.rgb+=vec3(.04,.07,.07)*smoothstep(.55,1.,s);' +
          'if(vPuddle>0.001){float e=smoothstep(0.2,0.98,vPuddle);gl_FragColor.a*=mix(0.58,0.0,e);gl_FragColor.rgb*=vec3(0.62,0.82,0.78);}'
        );
      }
    };
    mat.customProgramCacheKey = function () {
      return (prevKey ? prevKey() : 'water') + '-puddle1';
    };
    mat.needsUpdate = true;
  }

  function varyRock(batch, start) {
    var c = batch.c, p = batch.p, nrm = batch.n;
    if (!c || !p) return;
    for (var i = start; i < p.length; i += 3) {
      var h = hash(p[i], p[i + 2]);
      var ny = nrm ? nrm[i + 1] : 0;
      var k = 0.78 + h * 0.44;
      var moss = ny > 0.45 ? (ny - 0.45) * 0.7 : 0;
      var grit = (h - 0.5) * 0.08;
      c[i] = c[i] * k * (1 - moss) + (0.28 + grit) * moss;
      c[i + 1] = c[i + 1] * k * (1 - moss) + (0.32 + grit) * moss;
      c[i + 2] = c[i + 2] * k * (1 - moss * 0.85) + 0.18 * moss;
    }
  }

  function install(api) {
    if (installed) return;
    installed = true;
    var ue = api.ue, Ie = api.Ie;
    L = api.L;
    if (!ue || !ue.prototype || !Ie || !Ie.prototype || !L) return;

    var origMesh = ue.prototype.mesh;
    ue.prototype.mesh = function (mat) {
      var mesh = origMesh.call(this, mat);
      try {
        if (mat && mat.customProgramCacheKey && String(mat.customProgramCacheKey()).indexOf('water') === 0) patchWater(mat);
      } catch (e) {}
      return mesh;
    };

    var origAdd = ue.prototype.add;
    ue.prototype.add = function (prim, x, y, z, sx, sy, sz, color) {
      if (this._terraPuddle || !L || (prim !== L.disc && prim !== L.discH)) return origAdd.apply(this, arguments);
      var hex = colorHex(color);
      var water = hex === '#24383a' || hex === '#3a4a52';
      var mud = hex === '#3a3024' && prim === L.discH;
      if (!water && !mud) return origAdd.apply(this, arguments);
      // Preserve the native add() draw, including its default jitter. The new
      // geometry has a different tint, but must not move the chunk RNG stream.
      var jitter = arguments[11] === undefined ? 0.07 : arguments[11];
      if (jitter) this.r();
      var seed = hash(x, z);
      var prim2 = puddlePrim(seed);
      var before = this.p.length;
      var rotY = arguments[8] || 0;
      var scaleX = Math.abs(sx) || 1, scaleZ = Math.abs(sz) || scaleX;
      this._terraPuddle = true;
      try {
        if (water) {
          origAdd.call(this, prim2, x, 0.028, z, scaleX, 1, scaleZ, '#10242c', rotY, 0, 0, 0, 1);
          paintEdge(this, prim2, before);
        } else {
          origAdd.call(this, prim2, x, 0.012, z, scaleX * 1.08, 1, scaleZ * 1.08, '#2a2418', rotY + seed, 0, 0, 0, 1);
        }
      } finally {
        this._terraPuddle = false;
      }
      return this;
    };

    var origRock = Ie.prototype.rock;
    if (origRock) {
      Ie.prototype.rock = function () {
        var batch = this.s, start = batch && batch.p ? batch.p.length : 0;
        var result = origRock.apply(this, arguments);
        try { if (batch && batch.p && batch.p.length > start) varyRock(batch, start); } catch (e) {}
        return result;
      };
    }

  }

  ART.hook = function (api) {
    if (typeof prevHook === 'function') prevHook(api);
    try { install(api); } catch (e) { console.warn('TERRA visual', e); }
  };
})();
