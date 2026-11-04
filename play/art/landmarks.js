/* ТЕРРА · арт-слой ориентиров (PR [art] №1).
 * Заменяет кубические примитивы Ie.prototype.landmark (водонапорная башня, церковь, школа,
 * больница, стадион, телевышка) моделями из assets/art/landmarks.glb.
 * Принципы:
 *  - оригинальный landmark() выполняется целиком: ГСЧ чанка, коллайдеры, контейнеры, hall/lockRoom/
 *    sign/table/rubble остаются байт-в-байт; в «песочницу» уходят только прямые вызовы s/dt/g;
 *  - геометрия моделей вливается в те же батчи чанка (0 новых draw calls, те же триплан-текстуры CC0);
 *  - если GLB не загрузился/нет модели — песочница сливается обратно: ровно старая геометрия;
 *  - ?art=0 — выключить слой; ?artpreview=landmarks — панель перехода к ориентирам (режим скриншотов).
 */
(function () {
  'use strict';
  var Q = new URLSearchParams(location.search);
  var ART = window.TERRA_ART = window.TERRA_ART || {};
  ART.enabled = Q.get('art') !== '0';
  ART.stats = { replaced: 0, fallback: 0, tris: 0, errors: [] };
  var lib = null, loading = null, H = null;
  var KINDS = ['water_tower', 'church', 'school', 'hospital', 'stadium', 'tv_tower'];

  function warn(e) { try { ART.stats.errors.push(String(e && e.message || e)); } catch (_) {} }

  // ---------- GLB → массивы треугольников {p,n,c,m} в локальной СК модели ----------
  function extract(scene) {
    var out = {};
    scene.updateMatrixWorld(true);
    scene.traverse(function (o) {
      if (!o.isMesh) return;
      var nm = o.name, a = o;
      while (a && !/\|/.test(nm || '')) { a = a.parent; nm = a && a.name; }
      if (!nm) return;
      var g = o.geometry, P = g.attributes.position, N = g.attributes.normal, C = g.attributes.color, I = g.index;
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
        var l = Math.hypot(tx, ty, tz) || 1; n[k * 3] = tx / l; n[k * 3 + 1] = ty / l; n[k * 3 + 2] = tz / l;
        c[k * 3] = C.getX(v); c[k * 3 + 1] = C.getY(v); c[k * 3 + 2] = C.getZ(v);
        m[k] = Math.round(C.getW(v) * 255);
      }
      var parts = nm.split('|'), key = parts[0] + '|' + parts[1];
      (out[key] = out[key] || {})[parts[2]] = { p: p, n: n, c: c, m: m };
    });
    return out;
  }

  function load() {
    if (loading || !H) return loading;
    try {
      var GL = H.GL, MD = H.MD;
      if (!GL) return null;
      loading = fetch(new URL('assets/art/landmarks.glb', document.baseURI)).then(function (r) {
        if (!r.ok) throw new Error('landmarks.glb ' + r.status);
        return r.arrayBuffer();
      }).then(function (buf) {
        return new Promise(function (res, rej) {
          var ld = new GL(); if (MD) ld.setMeshoptDecoder(MD);
          ld.parse(buf, '', res, rej);
        });
      }).then(function (gltf) {
        lib = extract(gltf.scene); ART.ready = true;
        ART.models = Object.keys(lib);
      }).catch(function (e) { warn(e); ART.ready = false; });
    } catch (e) { warn(e); }
    return loading;
  }

  function lod() {
    var g = window.game, q = g && (g.qk || g.autoQ);
    return q === 'low' ? 'lod1' : 'lod0';
  }
  function model(name) { return lib && (lib[name + '|' + lod()] || lib[name + '|lod0']); }

  // ---------- вливание модели в батч чанка (без расхода ГСЧ) ----------
  function append(b, part, x, y, z, ry, light) {
    if (!b || !part) return 0;
    var p = part.p, n = part.n, c = part.c, m = part.m, cs = Math.cos(ry || 0), sn = Math.sin(ry || 0);
    var sw = b.sw, swc = b.swc, wet = b.wet, f = light !== false;
    for (var k = 0, i = 0; k < m.length; k++, i += 3) {
      var lx = p[i], ly = p[i + 1], lz = p[i + 2];
      b.p.push(x + cs * lx + sn * lz, y + ly, z - sn * lx + cs * lz);
      var nx = n[i], ny = n[i + 1], nz = n[i + 2];
      b.n.push(cs * nx + sn * nz, ny, -sn * nx + cs * nz);
      var V = f ? (ny > .6 ? Math.min(1, .86 + Math.max(0, ly) * .1) : Math.min(1, .58 + Math.max(0, ly) * .21)) : 1;
      b.c.push(c[i] * V, c[i + 1] * V, c[i + 2] * V);
      b.a.push(swc != null ? swc : (sw ? Math.max(0, ly) * sw : 0), wet);
      if (b.m) b.m.push(m[k]);
      if (b.uv) b.uv.push(.001, .999);
    }
    return m.length / 3;
  }
  function place(T, name, x, y, z, ry) {
    var md = model(name); if (!md) return -1;
    var t = 0;
    t += append(T.s, md.s, x, y, z, ry); t += append(T.dt, md.dt, x, y, z, ry);
    t += append(T.g, md.g, x, y, z, ry, false); t += append(T.f, md.f, x, y, z, ry);
    return t;
  }
  function hsh(a, b) { var s = Math.sin(a * 12.9898 + b * 78.233) * 43758.5453; return s - Math.floor(s); }

  // ---------- сборка ориентира по записям песочницы ----------
  var BUILD = {
    water_tower: function (T, R) {
      var r = R.s.find(function (q) { return q.sx === 2.2 && q.sy === 14; }); if (!r) return -1;
      return place(T, 'water_tower', r.x, r.Y, r.z, 0);
    },
    church: function (T, R) {
      var top = R.s.find(function (q) { return q.sx === 6 && q.sz === 6; }); if (!top) return -1;
      var side = R.g.filter(function (q) { return q.sx === 1.9; }).map(function (q) { return /3a6a5a/i.test(q.col) ? 'p' : 'g'; });
      if (side.length !== 2) return -1;
      var t = place(T, 'church_top_' + side[0] + side[1], top.x, top.Y, top.z, 0); if (t < 0) return -1;
      R.s.filter(function (q) { return q.sx === .1 && q.sy === 1.1; }).forEach(function (q, i) {
        var v = Math.floor(hsh(q.x, q.z) * 4), ry = (hsh(q.z, q.x) - .5) * .5;
        var r2 = place(T, 'grave_cross_' + v, q.x, q.Y, q.z, ry); if (r2 > 0) t += r2;
      });
      return t;
    },
    school: function (T, R) { return facade(T, R, 'school'); },
    hospital: function (T, R) { return facade(T, R, 'hospital'); },
    stadium: function (T, R) {
      var f = R.s.find(function (q) { return q.sx === 26 && q.sz === 22; }); if (!f) return -1;  // n=38
      return place(T, 'stadium', f.x, f.Y, f.z, 0);
    },
    tv_tower: function (T, R) {
      var b = R.g.find(function (q) { return q.geo === 'sph'; }); if (!b) return -1;
      return place(T, 'tv_tower', b.x, b.Y, b.z, 0);
    }
  };
  function facade(T, R, kind) {
    var w = R.s.find(function (q) { return q.sx === 1.8 && q.sy === 1.4; }); if (!w) return -1;
    var o = w.x + 13.2, front = w.z - .27, Y = w.Y;
    var t = place(T, kind + '_facade', o, Y, front, 0); if (t < 0) return -1;
    if (kind === 'hospital') {
      var c = R.g.find(function (q) { return q.sx === 2.4; });
      if (c) { var r = place(T, 'hospital_cross', c.x, c.Y + c.y + .5, c.z + .05, 0); if (r > 0) t += r; }
    } else {
      var y = R.s.find(function (q) { return q.sx === 18 && q.sz === 12; });
      if (y) { var r2 = place(T, 'school_yard', y.x, y.Y, y.z, 0); if (r2 > 0) t += r2; }
    }
    return t;
  }

  // ---------- песочница ----------
  var SYNC = ['oy', 'sink'];
  function sinkFor(H, real) {
    var b = new H.ue(real.r);
    b.m = real.m ? [] : null; b.uv = real.uv ? [] : null;
    b.oy = real.oy; b.hf = real.hf; b.sink = real.sink; b.sw = real.sw; b.swc = real.swc; b.wet = real.wet; b.mt = real.mt;
    var rec = b._rec = [], geoName = new Map();
    Object.keys(H.L).forEach(function (k) { geoName.set(H.L[k], k); });
    var add = b.add;
    b.add = function (geo, x, y, z, sx, sy, sz, col) {
      rec.push({ geo: geoName.get(geo) || '?', x: x, y: y, z: z, sx: sx, sy: sy, sz: sz, col: String(col), Y: this.Y(x, z) });
      return add.apply(this, arguments);
    };
    return b;
  }
  function merge(real, b) {
    if (!b.p.length) return;
    Array.prototype.push.apply(real.p, b.p); Array.prototype.push.apply(real.n, b.n);
    Array.prototype.push.apply(real.c, b.c); Array.prototype.push.apply(real.a, b.a);
    if (real.m && b.m) Array.prototype.push.apply(real.m, b.m);
    if (real.uv && b.uv) Array.prototype.push.apply(real.uv, b.uv);
  }

  function wrap(H) {
    var P = H.Ie.prototype, orig = P.landmark;
    if (typeof orig !== 'function' || orig.__terraArt) return;
    var wrapped = function (kind, t, i, n) {
      if (!ART.enabled || !BUILD[kind]) return orig.apply(this, arguments);
      if (!lib) { load(); ART.stats.fallback++; return orig.apply(this, arguments); }
      var self = this, real = { s: this.s, dt: this.dt, g: this.g }, sk;
      try { sk = { s: sinkFor(H, real.s), dt: sinkFor(H, real.dt), g: sinkFor(H, real.g) }; }
      catch (e) { warn(e); return orig.apply(this, arguments); }
      var syncIn = function () { ['s', 'dt', 'g'].forEach(function (k) { SYNC.forEach(function (f) { sk[k][f] = real[k][f]; }); }); };
      var proxy = new Proxy(this, {
        get: function (tg, key) {
          if (key === 's' || key === 'dt' || key === 'g') return sk[key];
          var v = Reflect.get(tg, key, tg);
          if (typeof v === 'function') return function () { var r = v.apply(tg, arguments); syncIn(); return r; };
          return v;
        },
        set: function (tg, key, val) { if (key === 's' || key === 'dt' || key === 'g') return true; tg[key] = val; return true; }
      });
      var res = orig.call(proxy, kind, t, i, n);
      var R = { s: sk.s._rec, dt: sk.dt._rec, g: sk.g._rec }, tris = -1;
      try {
        tris = BUILD[kind]({ s: real.s, dt: real.dt, g: real.g, f: self.f }, R);
      } catch (e) { warn(e); tris = -1; }
      if (tris < 0) { merge(real.s, sk.s); merge(real.dt, sk.dt); merge(real.g, sk.g); ART.stats.fallback++; }
      else { ART.stats.replaced++; ART.stats.tris += tris; (ART.log = ART.log || []).push({ kind: kind, cx: self.cx, cz: self.cz, tris: tris }); }
      return res;
    };
    wrapped.__terraArt = true;
    P.landmark = wrapped;
  }

  ART.hook = function (h) {
    H = h;
    if (!ART.enabled) return;
    try { wrap(h); } catch (e) { warn(e); return; }
    // загрузка после инициализации бандла (лоадеры объявляются ленивыми модулями)
    setTimeout(load, 0);
  };

  // ---------- режим превью для скриншотов: ?artpreview=landmarks ----------
  ART.find = function (kind, R) {
    if (!H) return null; R = R || 40;
    var best = null;
    for (var cx = -R; cx <= R; cx++) for (var cz = -R; cz <= R; cz++) {
      var w = H.Wr(cx, cz), lm = w && w.lm;
      if (!lm || lm.kind !== kind) continue;
      if (/^(crash|camp|tower|highway|mall)$/.test(w.d)) continue;
      var d = Math.abs(cx) + Math.abs(cz);
      if (!best || d < best.d) best = { cx: cx, cz: cz, d: d };
    }
    if (!best) return null;
    var C = H.Ct, o = 8 + 2 + (C - 10) / 2;
    return { kind: kind, cx: best.cx, cz: best.cz, x: best.cx * C + o, z: best.cz * C + o };
  };
  ART.goto = function (kind, dx, dz) {
    var f = ART.find(kind), g = window.game; if (!f || !g || !g.p) return null;
    g.p.x = f.x + (dx || 0); g.p.z = f.z + (dz == null ? 24 : dz); return f;
  };
  if (Q.get('artpreview') === 'landmarks') {
    ART.preview = true;
    addEventListener('load', function () {
      var bar = document.createElement('div');
      bar.id = 'artPreview';
      bar.style.cssText = 'position:fixed;left:8px;bottom:8px;z-index:99999;display:flex;flex-wrap:wrap;gap:4px;max-width:96vw;font:12px sans-serif';
      KINDS.forEach(function (k) {
        var b = document.createElement('button'); b.textContent = k; b.type = 'button';
        b.style.cssText = 'padding:4px 6px;background:#222c;color:#ffd23a;border:1px solid #ffd23a88;border-radius:4px';
        b.onclick = function () { ART.goto(k); };
        bar.appendChild(b);
      });
      document.body.appendChild(bar);
      setInterval(function () { var g = window.game; if (g && g.p) { g.p.hp = g.p.maxHp || 100; g.p.rad = 0; } }, 50);
    });
  }
})();
