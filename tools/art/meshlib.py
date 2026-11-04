"""Tiny procedural modelling kit for TERRA landmarks (no external deps except numpy).
Builds triangle soups with per-vertex material ids; colours are computed at export
from final positions (rust, soot streaks, moss near the ground), so the same source
produces LOD0/LOD1. Output: glTF 2.0 binary with POSITION, NORMAL and COLOR_0 (VEC4 u8,
rgb = linear albedo, alpha = TERRA surface-texture id: 0 none, 1 grass, 2 dirt, 3 moss,
4 gravel, 5 asphalt, 6 concrete, 7 rock, 8 brick, 9 rust, 10 wood)."""
import json, math, struct
import numpy as np

def srgb2lin(h):
    h = h.lstrip('#'); c = np.array([int(h[i:i+2], 16) for i in (0, 2, 4)]) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

class Mat:
    def __init__(self, col, mt=0, var=0.12, rust=0.0, rustcol='#5e3420', rustmt=9, streak=0.0,
                 moss=0.0, mossh=1.6, mossmt=3, dirt=0.25, seed=0):
        self.col = srgb2lin(col); self.mt = mt; self.var = var; self.rust = rust
        self.rustcol = srgb2lin(rustcol); self.rustmt = rustmt; self.streak = streak
        self.moss = moss; self.mossh = mossh; self.mossmt = mossmt; self.dirt = dirt; self.seed = seed

MOSS = srgb2lin('#3e5626'); DIRT = srgb2lin('#4a4032')

# ---------- noise ----------
def _hash(ix, iy, iz, seed):
    h = (ix * 374761393 + iy * 668265263 + iz * 2147483647 + seed * 144269504) & 0xffffffff
    h = ((h ^ (h >> 13)) * 1274126177) & 0xffffffff
    return ((h ^ (h >> 16)) & 0xffff) / 65535.0

def vnoise(p, seed=0):
    p = np.asarray(p, dtype=np.float64); i = np.floor(p).astype(np.int64); f = p - i
    u = f * f * (3 - 2 * f); out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (u[:, 0] if dx else 1 - u[:, 0]) * (u[:, 1] if dy else 1 - u[:, 1]) * (u[:, 2] if dz else 1 - u[:, 2])
                out = out + w * _hash(i[:, 0] + dx, i[:, 1] + dy, i[:, 2] + dz, seed)
    return out

def fbm(p, seed=0, oct=3):
    a, s, t = 0.5, 1.0, 0
    for k in range(oct):
        t = t + a * vnoise(p * s, seed + k * 17); a *= 0.5; s *= 2.03
    return t / (1 - 0.5 ** oct)

def hash1(*v):
    x = 0
    for k in v: x = (x * 1000003 + int(round(k * 1000))) & 0xffffffff
    return _hash(x & 0xffff, (x >> 16) & 0xffff, 7, 3)

# ---------- mesh ----------
class Mesh:
    def __init__(self):
        self.P = []; self.N = []; self.M = []  # per-vertex; triangles are consecutive triples
    def tri(self, a, b, c, mat, n=None):
        a, b, c = map(np.asarray, (a, b, c))
        if n is None:
            n = np.cross(b - a, c - a); l = np.linalg.norm(n)
            if l < 1e-10: return
            n = n / l; n = (n, n, n)
        self.P += [a, b, c]; self.N += list(n); self.M += [mat] * 3
    def quad(self, a, b, c, d, mat, nu=1, nv=1):
        a, b, c, d = map(np.asarray, (a, b, c, d))
        for i in range(nu):
            for j in range(nv):
                u0, u1, v0, v1 = i / nu, (i + 1) / nu, j / nv, (j + 1) / nv
                L = lambda u, v: a + (b - a) * u + (d - a) * v + (a - b + c - d) * u * v
                p00, p10, p11, p01 = L(u0, v0), L(u1, v0), L(u1, v1), L(u0, v1)
                self.tri(p00, p10, p11, mat); self.tri(p00, p11, p01, mat)
    def add(self, other):
        self.P += other.P; self.N += other.N; self.M += other.M; return self
    def xform(self, R=None, t=(0, 0, 0), s=1.0):
        if not self.P: return self
        P = np.array(self.P) * s; N = np.array(self.N)
        if R is not None: P = P @ R.T; N = N @ R.T
        P = P + np.asarray(t); self.P = list(P); self.N = list(N); return self
    @property
    def ntri(self): return len(self.P) // 3

def rotY(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]])
def rotX(a):
    c, s = math.cos(a), math.sin(a); return np.array([[1, 0, 0], [0, c, -s], [0, s, c]])
def rotZ(a):
    c, s = math.cos(a), math.sin(a); return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]])

def box(c, size, mat, R=None, sub=(1, 1, 1), skip=()):
    """Axis box centred at c (after optional rotation R about its centre). skip: faces to omit ('-y','+y',...)"""
    m = Mesh(); hx, hy, hz = np.asarray(size) / 2; sx, sy, sz = sub
    v = lambda x, y, z: np.array([x * hx, y * hy, z * hz])
    F = {'+x': (v(1, -1, 1), v(1, -1, -1), v(1, 1, -1), v(1, 1, 1), sz, sy),
         '-x': (v(-1, -1, -1), v(-1, -1, 1), v(-1, 1, 1), v(-1, 1, -1), sz, sy),
         '+y': (v(-1, 1, 1), v(1, 1, 1), v(1, 1, -1), v(-1, 1, -1), sx, sz),
         '-y': (v(-1, -1, -1), v(1, -1, -1), v(1, -1, 1), v(-1, -1, 1), sx, sz),
         '+z': (v(-1, -1, 1), v(1, -1, 1), v(1, 1, 1), v(-1, 1, 1), sx, sy),
         '-z': (v(1, -1, -1), v(-1, -1, -1), v(-1, 1, -1), v(1, 1, -1), sx, sy)}
    for k, (a, b, cc, d, nu, nv) in F.items():
        if k in skip: continue
        m.quad(a, b, cc, d, mat, nu, nv)
    return m.xform(R, c)

def beam(p0, p1, w, mat, h=None, up=(0, 1, 0)):
    """Square-section beam between two points (4 sides, no caps)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float); d = p1 - p0; L = np.linalg.norm(d)
    if L < 1e-6: return Mesh()
    ax = d / L; up = np.asarray(up, float)
    if abs(np.dot(ax, up)) > 0.95: up = np.array([1.0, 0, 0])
    u = np.cross(ax, up); u /= np.linalg.norm(u); v = np.cross(u, ax); h = w if h is None else h
    m = Mesh(); cs = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for i in range(4):
        a, b = cs[i], cs[(i + 1) % 4]
        oa = u * a[0] * w / 2 + v * a[1] * h / 2; ob = u * b[0] * w / 2 + v * b[1] * h / 2
        m.quad(p0 + ob, p0 + oa, p1 + oa, p1 + ob, mat)
    return m

def lathe(profile, seg, mat, a0=0.0, a1=2 * math.pi, smooth=True, cap_bottom=False, cap_top=False, skipfn=None, center=(0, 0, 0)):
    """profile: list of (r, y) from bottom to top. skipfn(i_seg, j_ring)->True omits that face (damage)."""
    m = Mesh(); cx, cy, cz = center; pr = np.asarray(profile, float)
    # profile normals (2D)
    nrm = []
    for j in range(len(pr)):
        a = pr[max(j - 1, 0)]; b = pr[min(j + 1, len(pr) - 1)]; t = b - a
        n2 = np.array([t[1], -t[0]]); n2 /= (np.linalg.norm(n2) + 1e-12); nrm.append(n2)
    def P(r, y, ang): return np.array([cx + r * math.sin(ang), cy + y, cz + r * math.cos(ang)])
    def Nn(n2, ang): return np.array([n2[0] * math.sin(ang), n2[1], n2[0] * math.cos(ang)])
    for i in range(seg):
        g0 = a0 + (a1 - a0) * i / seg; g1 = a0 + (a1 - a0) * (i + 1) / seg
        for j in range(len(pr) - 1):
            if skipfn and skipfn(i, j): continue
            (r0, y0), (r1, y1) = pr[j], pr[j + 1]
            A, B, C, D = P(r0, y0, g0), P(r0, y0, g1), P(r1, y1, g1), P(r1, y1, g0)
            if smooth:
                nA, nB, nC, nD = Nn(nrm[j], g0), Nn(nrm[j], g1), Nn(nrm[j + 1], g1), Nn(nrm[j + 1], g0)
                if r0 > 1e-6: m.tri(A, B, C, mat, (nA, nB, nC))
                if r1 > 1e-6: m.tri(A, C, D, mat, (nA, nC, nD))
            else:
                if r0 > 1e-6: m.tri(A, B, C, mat)
                if r1 > 1e-6: m.tri(A, C, D, mat)
        if cap_bottom and pr[0][0] > 0:
            r, y = pr[0]; m.tri(np.array([cx, cy + y, cz]), P(r, y, g1), P(r, y, g0), mat)
        if cap_top and pr[-1][0] > 0:
            r, y = pr[-1]; m.tri(np.array([cx, cy + y, cz]), P(r, y, g0), P(r, y, g1), mat)
    return m

def cyl(r0, r1, y0, y1, seg, mat, rings=1, **kw):
    prof = [(r0 + (r1 - r0) * k / rings, y0 + (y1 - y0) * k / rings) for k in range(rings + 1)]
    return lathe(prof, seg, mat, smooth=kw.pop('smooth', False), **kw)

def blob(c, r, mat, squash=(1, 1, 1), seed=0, det=1):
    """Irregular low-poly leaf/rubble cluster (octahedron or subdivided)."""
    m = Mesh(); c = np.asarray(c, float); s = np.asarray(squash, float)
    V = [np.array(v, float) for v in [(1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0), (0, 0, 1), (0, 0, -1)]]
    F = [(0, 2, 4), (4, 2, 1), (1, 2, 5), (5, 2, 0), (0, 4, 3), (4, 1, 3), (1, 5, 3), (5, 0, 3)]
    tris = [(V[a], V[b], V[cc]) for a, b, cc in F]
    for _ in range(det):
        nt = []
        for a, b, cc in tris:
            ab, bc, ca = [(x + y) / np.linalg.norm(x + y) for x, y in ((a, b), (b, cc), (cc, a))]
            nt += [(a, ab, ca), (ab, b, bc), (ca, bc, cc), (ab, bc, ca)]
        tris = nt
    def J(v):
        k = 0.75 + 0.5 * hash1(v[0] + seed, v[1], v[2]); return c + v * r * k * s
    for a, b, cc in tris: m.tri(J(a), J(b), J(cc), mat)
    return m

def two_sided(m):
    """append reversed copies of all triangles (for thin open shells)."""
    P, N, M = list(m.P), list(m.N), list(m.M)
    for k in range(0, len(P), 3):
        m.P += [P[k], P[k + 2], P[k + 1]]; m.N += [-N[k], -N[k + 2], -N[k + 1]]; m.M += [M[k]] * 3
    return m

# ---------- colouring & export ----------
def shade(mesh, salt=0):
    P = np.array(mesh.P); N = np.array(mesh.N); mats = mesh.M; n = len(P)
    C = np.zeros((n, 3)); MT = np.zeros(n, dtype=np.int64)
    uniq = {}
    for k, m in enumerate(mats): uniq.setdefault(id(m), (m, []))[1].append(k)
    for m, idx in uniq.values():
        idx = np.array(idx); p = P[idx]; col = np.tile(m.col, (len(idx), 1))
        sd = m.seed + salt
        nz = fbm(p * 0.9, sd); col *= (1 + m.var * (nz[:, None] - 0.5) * 2)
        # per-face centroid for mt patches
        tri_c = p.reshape(-1, 3, 3).mean(axis=1)
        mtv = np.full(len(idx) // 3, m.mt)
        if m.rust > 0:
            rv = fbm(p * np.array([1.1, 0.7, 1.1]), sd + 5)
            k = np.clip((rv - (1 - m.rust)) / 0.18, 0, 1)[:, None]
            col = col * (1 - k) + m.rustcol * (0.75 + 0.5 * nz[:, None]) * k
            rc = fbm(tri_c * np.array([1.1, 0.7, 1.1]), sd + 5)
            mtv = np.where(rc > 1 - m.rust + 0.06, m.rustmt, mtv)
        if m.streak > 0:
            st = fbm(p * np.array([2.6, 0.18, 2.6]), sd + 9)
            col *= (1 - m.streak * np.clip(st - 0.35, 0, 1)[:, None] * 1.6)
        if m.dirt > 0:
            g = np.clip(1 - p[:, 1] / 1.2, 0, 1)[:, None] * m.dirt
            col = col * (1 - g) + DIRT * g
        if m.moss > 0:
            mz = fbm(p * 1.7, sd + 13)
            h = np.clip(1 - p[:, 1] / m.mossh, 0, 1) * m.moss + np.clip(N[idx][:, 1], 0, 1) * m.moss * 0.35
            k = np.clip((mz * 0.9 + h - 0.75) / 0.25, 0, 1)[:, None]
            col = col * (1 - k) + MOSS * (0.8 + 0.4 * mz[:, None]) * k
            mc = fbm(tri_c * 1.7, sd + 13); hc = np.clip(1 - tri_c[:, 1] / m.mossh, 0, 1) * m.moss
            mtv = np.where(mc * 0.9 + hc - 0.75 > 0.12, m.mossmt, mtv)
        C[idx] = np.clip(col, 0, 1); MT[idx] = np.repeat(mtv, 3)
    return P.astype(np.float32), N.astype(np.float32), C, MT

def write_glb(path, parts, extras=None):
    """parts: list of (node_name, Mesh, salt). Non-indexed triangle soups."""
    bin_ = bytearray(); bviews = []; accs = []; meshes = []; nodes = []
    def push(arr, target=34962):
        nonlocal bin_
        while len(bin_) % 4: bin_.append(0)
        off = len(bin_); b = arr.tobytes(); bin_ += b
        bviews.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(b), 'target': target}); return len(bviews) - 1
    for name, mesh, salt in parts:
        if not mesh.P: continue
        P, N, C, MT = shade(mesh, salt)
        N = N / (np.linalg.norm(N, axis=1, keepdims=True) + 1e-12)
        col = np.zeros((len(P), 4), dtype=np.uint8)
        col[:, :3] = np.round(C * 255); col[:, 3] = MT
        a = []
        bv = push(P.astype(np.float32)); accs.append({'bufferView': bv, 'componentType': 5126, 'count': len(P), 'type': 'VEC3', 'min': P.min(0).tolist(), 'max': P.max(0).tolist()}); a.append(len(accs) - 1)
        bv = push(N.astype(np.float32)); accs.append({'bufferView': bv, 'componentType': 5126, 'count': len(P), 'type': 'VEC3'}); a.append(len(accs) - 1)
        bv = push(col); accs.append({'bufferView': bv, 'componentType': 5121, 'normalized': True, 'count': len(P), 'type': 'VEC4'}); a.append(len(accs) - 1)
        meshes.append({'name': name, 'primitives': [{'attributes': {'POSITION': a[0], 'NORMAL': a[1], 'COLOR_0': a[2]}, 'material': 0}]})
        nodes.append({'name': name, 'mesh': len(meshes) - 1})
    gl = {'asset': {'version': '2.0', 'generator': 'terra tools/art/meshlib.py'},
          'scene': 0, 'scenes': [{'nodes': list(range(len(nodes)))}], 'nodes': nodes, 'meshes': meshes,
          'materials': [{'name': 'terra_vertex', 'pbrMetallicRoughness': {'baseColorFactor': [1, 1, 1, 1], 'metallicFactor': 0, 'roughnessFactor': 1}}],
          'accessors': accs, 'bufferViews': bviews, 'buffers': [{'byteLength': len(bin_)}]}
    if extras: gl['asset']['extras'] = extras
    js = json.dumps(gl, separators=(',', ':')).encode()
    while len(js) % 4: js += b' '
    while len(bin_) % 4: bin_.append(0)
    out = struct.pack('<III', 0x46546C67, 2, 12 + 8 + len(js) + 8 + len(bin_))
    out += struct.pack('<II', len(js), 0x4E4F534A) + js + struct.pack('<II', len(bin_), 0x004E4942) + bytes(bin_)
    open(path, 'wb').write(out)
