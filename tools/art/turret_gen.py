#!/usr/bin/env python3
"""Самодельные турели обороны лагеря → play/assets/defense/turrets.glb.

Геометрия и атлас — собственные, процедурные (команда «Терры»).
Надписи на табличках набраны DejaVu Sans (уже в благодарностях проекта).
Один атлас на все виды: albedo + normal + ORM (R=AO, G=roughness, B=metalness), WebP.
Узлы: base / lv2 / lv3 и группа gun — как ждёт play/ui/defense.js
(ствол крутится отдельно, детали lv2/lv3 видны с соответствующего уровня).

Запуск: python3 tools/art/turret_gen.py
"""
import io, json, math, os, struct
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
OUT = os.path.join(ROOT, 'play/assets/defense/turrets.glb')
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
ATLAS = 1024
TILES = 4  # 4×4

# Дульный срез в пространстве модели (метры). defense.js умножает на scale.
MUZZLE = {
    'pkm': (0.0, 1.20, 1.30),
    'nail': (0.0, 1.14, 1.52),
    'flame': (0.0, 1.00, 1.05),
}

# Имена тайлов → колонка, ряд (ряд 0 сверху, V в glTF растёт вниз).
TILE = {
    'rust': (0, 0), 'olive': (1, 0), 'iron': (2, 0), 'soot': (3, 0),
    'tire': (0, 1), 'canvas': (1, 1), 'wood': (2, 1), 'red': (3, 1),
    'hazard': (0, 2), 'brass': (1, 2), 'tape': (2, 2), 'hose': (3, 2),
    'signA': (0, 3), 'signB': (1, 3), 'ammo': (2, 3), 'weld': (3, 3),
}
SIGNS = [
    'ПКМ', '5.45', 'ГВОЗДИ', 'ГАЗ', 'ПРОПАН', 'ОГОНЬ', 'НЕ ЛЕЗЬ', 'АРЕС-7',
    'II', 'III', 'ОПАСНО', '2136', 'ХЛАМ', 'СВАР', 'ПУСТО', 'А-7',
]


def rot_x(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], np.float32)


def rot_y(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], np.float32)


def rot_z(a):
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], np.float32)


def tile_uv(name, inset=0.012, spin=0):
    c, r = TILE[name]
    u0, v0 = (c + inset) / TILES, (r + inset) / TILES
    u1, v1 = (c + 1 - inset) / TILES, (r + 1 - inset) / TILES
    return (u0, v0, u1, v1, spin % 4)


def sign_uv(i):
    i = int(i) % 16
    tile = 'signA' if i < 8 else 'signB'
    k = i % 8
    c, r = TILE[tile]
    sc, sr = k % 2, k // 2
    du, dv = 1 / TILES / 2, 1 / TILES / 4
    pad = 0.003
    u0 = c / TILES + sc * du + pad
    v0 = r / TILES + sr * dv + pad
    u1 = c / TILES + (sc + 1) * du - pad
    v1 = r / TILES + (sr + 1) * dv - pad
    return (u0, v0, u1, v1, 0)


class Mesh:
    def __init__(self):
        self.P, self.N, self.UV = [], [], []

    def tri(self, a, b, c, na, nb, nc, ua, ub, uc):
        self.P += [np.asarray(a, np.float32), np.asarray(b, np.float32), np.asarray(c, np.float32)]
        self.N += [np.asarray(na, np.float32), np.asarray(nb, np.float32), np.asarray(nc, np.float32)]
        self.UV += [np.asarray(ua, np.float32), np.asarray(ub, np.float32), np.asarray(uc, np.float32)]

    def append(self, other, R=None, t=(0, 0, 0)):
        if not other.P:
            return self
        P = np.stack(other.P)
        N = np.stack(other.N)
        if R is not None:
            P = P @ np.asarray(R, np.float32).T
            N = N @ np.asarray(R, np.float32).T
        P = P + np.asarray(t, np.float32)
        self.P += list(P)
        self.N += list(N)
        self.UV += other.UV
        return self

    @property
    def tris(self):
        return len(self.P) // 3


def _uv_of(rect, u, v):
    u0, v0, u1, v1, spin = rect
    for _ in range(spin):
        u, v = v, 1 - u
    return np.array([u0 + (u1 - u0) * u, v0 + (v1 - v0) * v], np.float32)


def _n(a, b, c):
    n = np.cross(np.asarray(b) - a, np.asarray(c) - a)
    L = np.linalg.norm(n)
    return n / L if L > 1e-8 else np.array([0, 1, 0], np.float32)


def quad(m, p00, p10, p11, p01, rect, na=None, nb=None, nc=None, nd=None):
    p00, p10, p11, p01 = map(lambda p: np.asarray(p, np.float32), (p00, p10, p11, p01))
    if na is None:
        n = _n(p00, p10, p11)
        na = nb = nc = nd = n
    m.tri(p00, p10, p11, na, nb, nc, _uv_of(rect, 0, 1), _uv_of(rect, 1, 1), _uv_of(rect, 1, 0))
    m.tri(p00, p11, p01, na, nc, nd, _uv_of(rect, 0, 1), _uv_of(rect, 1, 0), _uv_of(rect, 0, 0))


def box(size, rect, center=(0, 0, 0)):
    """Ящик. size — полные рёбра. Каждая грань берёт весь тайл."""
    m = Mesh()
    hx, hy, hz = (np.asarray(size, np.float32) / 2)
    c = np.asarray(center, np.float32)
    faces = [
        # +x, -x, +y, -y, +z, -z  (p00, p10, p11, p01) обход против часовой снаружи
        ([(hx, -hy, hz), (hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz)], (1, 0, 0)),
        ([(-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz), (-hx, hy, -hz)], (-1, 0, 0)),
        ([(-hx, hy, hz), (hx, hy, hz), (hx, hy, -hz), (-hx, hy, -hz)], (0, 1, 0)),
        ([(-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz)], (0, -1, 0)),
        ([(-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)], (0, 0, 1)),
        ([(hx, -hy, -hz), (-hx, -hy, -hz), (-hx, hy, -hz), (hx, hy, -hz)], (0, 0, -1)),
    ]
    for pts, n in faces:
        n = np.array(n, np.float32)
        quad(m, *[c + np.array(p, np.float32) for p in pts], rect, n, n, n, n)
    return m


def face_box(size, faces_uv, center=(0, 0, 0)):
    """Как box, но UV грани задаётся словарём '+z','-x',..."""
    m = Mesh()
    hx, hy, hz = (np.asarray(size, np.float32) / 2)
    c = np.asarray(center, np.float32)
    spec = {
        '+x': ([(hx, -hy, hz), (hx, -hy, -hz), (hx, hy, -hz), (hx, hy, hz)], (1, 0, 0)),
        '-x': ([(-hx, -hy, -hz), (-hx, -hy, hz), (-hx, hy, hz), (-hx, hy, -hz)], (-1, 0, 0)),
        '+y': ([(-hx, hy, hz), (hx, hy, hz), (hx, hy, -hz), (-hx, hy, -hz)], (0, 1, 0)),
        '-y': ([(-hx, -hy, -hz), (hx, -hy, -hz), (hx, -hy, hz), (-hx, -hy, hz)], (0, -1, 0)),
        '+z': ([(-hx, -hy, hz), (hx, -hy, hz), (hx, hy, hz), (-hx, hy, hz)], (0, 0, 1)),
        '-z': ([(hx, -hy, -hz), (-hx, -hy, -hz), (-hx, hy, -hz), (hx, hy, -hz)], (0, 0, -1)),
    }
    for key, (pts, n) in spec.items():
        rect = faces_uv.get(key, faces_uv.get('*'))
        if rect is None:
            continue
        n = np.array(n, np.float32)
        quad(m, *[c + np.array(p, np.float32) for p in pts], rect, n, n, n, n)
    return m


def cylinder(y0, y1, r0, r1, seg, rect, caps=True):
    m = Mesh()
    seg = int(seg)
    angs = [2 * math.pi * i / seg for i in range(seg)]

    def ring(y, r):
        return [np.array([r * math.sin(a), y, r * math.cos(a)], np.float32) for a in angs]

    def side_n(a, r0, r1, y0, y1):
        dy, dr = (y1 - y0), (r1 - r0)
        n = np.array([math.sin(a) * dy, -dr, math.cos(a) * dy], np.float32)
        L = np.linalg.norm(n)
        return n / L if L > 1e-8 else np.array([math.sin(a), 0, math.cos(a)], np.float32)

    bot, top = ring(y0, r0), ring(y1, r1)
    for i in range(seg):
        j = (i + 1) % seg
        ua, ub = i / seg, (i + 1) / seg
        n0, n1 = side_n(angs[i], r0, r1, y0, y1), side_n(angs[j], r0, r1, y0, y1)
        # v: низ = 1 (низ тайла в glTF-V), верх = 0
        quad(m, bot[i], bot[j], top[j], top[i], rect, n0, n1, n1, n0)
        # quad() сам считает UV из rect по углам 0/1 — перезапишем окружной u вручную
        # проще переложить последние 6 uv
        for k, (u, v) in enumerate(((ua, 1), (ub, 1), (ub, 0), (ua, 1), (ub, 0), (ua, 0))):
            m.UV[-6 + k] = _uv_of(rect, u, v)
    if caps and r0 > 1e-4:
        c = np.array([0, y0, 0], np.float32)
        n = np.array([0, -1, 0], np.float32)
        for i in range(seg):
            j = (i + 1) % seg
            m.tri(c, bot[j], bot[i], n, n, n, _uv_of(rect, .5, .5), _uv_of(rect, .5 + .45 * math.sin(angs[j]), .5 + .45 * math.cos(angs[j])), _uv_of(rect, .5 + .45 * math.sin(angs[i]), .5 + .45 * math.cos(angs[i])))
    if caps and r1 > 1e-4:
        c = np.array([0, y1, 0], np.float32)
        n = np.array([0, 1, 0], np.float32)
        for i in range(seg):
            j = (i + 1) % seg
            m.tri(c, top[i], top[j], n, n, n, _uv_of(rect, .5, .5), _uv_of(rect, .5 + .45 * math.sin(angs[i]), .5 + .45 * math.cos(angs[i])), _uv_of(rect, .5 + .45 * math.sin(angs[j]), .5 + .45 * math.cos(angs[j])))
    return m


def beam(p0, p1, w, h, rect):
    p0, p1 = np.asarray(p0, np.float32), np.asarray(p1, np.float32)
    d = p1 - p0
    L = np.linalg.norm(d)
    if L < 1e-5:
        return Mesh()
    ax = d / L
    up = np.array([0, 1, 0], np.float32)
    if abs(float(np.dot(ax, up))) > 0.92:
        up = np.array([1, 0, 0], np.float32)
    u = np.cross(ax, up)
    u /= np.linalg.norm(u)
    v = np.cross(u, ax)
    m = cylinder(0, L, 1, 1, 4, rect, caps=False)
    # цилиндр вдоль Y с радиусом 1 — заменим на брус через масштаб вершин
    # проще собрать 4 квада
    m = Mesh()
    corners = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]
    ring0 = [p0 + u * a + v * b for a, b in corners]
    ring1 = [p1 + u * a + v * b for a, b in corners]
    for i in range(4):
        j = (i + 1) % 4
        quad(m, ring0[j], ring0[i], ring1[i], ring1[j], rect)
    return m


def ellipsoid(rx, ry, rz, seg, rings, rect):
    m = Mesh()
    seg, rings = int(seg), int(rings)
    pts, nrm = [], []
    for i in range(rings + 1):
        phi = math.pi * i / rings
        y, r = math.cos(phi), math.sin(phi)
        rp, np_ = [], []
        for j in range(seg):
            th = 2 * math.pi * j / seg
            p = np.array([rx * r * math.sin(th), ry * y, rz * r * math.cos(th)], np.float32)
            n = np.array([p[0] / (rx * rx + 1e-8), p[1] / (ry * ry + 1e-8), p[2] / (rz * rz + 1e-8)], np.float32)
            n /= np.linalg.norm(n) + 1e-8
            rp.append(p)
            np_.append(n)
        pts.append(rp)
        nrm.append(np_)
    for i in range(rings):
        for j in range(seg):
            k = (j + 1) % seg
            # обход снаружи: против часовой, если смотреть снаружи
            quad(m, pts[i][k], pts[i][j], pts[i + 1][j], pts[i + 1][k], rect,
                 nrm[i][k], nrm[i][j], nrm[i + 1][j], nrm[i + 1][k])
            ua, ub = j / seg, (j + 1) / seg
            va, vb = i / rings, (i + 1) / rings
            for t, (u, v) in enumerate(((ub, 1 - va), (ua, 1 - va), (ua, 1 - vb), (ub, 1 - va), (ua, 1 - vb), (ub, 1 - vb))):
                m.UV[-6 + t] = _uv_of(rect, u, v)
    return m


def torus_y(R, r, n_maj, n_min, rect):
    m = Mesh()
    n_maj, n_min = int(n_maj), int(n_min)
    pts, nrm = [], []
    for i in range(n_maj):
        a = 2 * math.pi * i / n_maj
        ca, sa = math.cos(a), math.sin(a)
        rp, np_ = [], []
        for j in range(n_min):
            b = 2 * math.pi * j / n_min
            cb, sb = math.cos(b), math.sin(b)
            p = np.array([(R + r * cb) * ca, r * sb, (R + r * cb) * sa], np.float32)
            n = np.array([cb * ca, sb, cb * sa], np.float32)
            rp.append(p)
            np_.append(n)
        pts.append(rp)
        nrm.append(np_)
    for i in range(n_maj):
        ii = (i + 1) % n_maj
        for j in range(n_min):
            jj = (j + 1) % n_min
            quad(m, pts[i][j], pts[ii][j], pts[ii][jj], pts[i][jj], rect,
                 nrm[i][j], nrm[ii][j], nrm[ii][jj], nrm[i][jj])
            ua, ub = i / n_maj, (i + 1) / n_maj
            va, vb = j / n_min, (j + 1) / n_min
            for t, (u, v) in enumerate(((ua, va), (ub, va), (ub, vb), (ua, va), (ub, vb), (ua, vb))):
                m.UV[-6 + t] = _uv_of(rect, u, v)
    return m


def tube(path, radius, seg, rect):
    path = [np.asarray(p, np.float32) for p in path]
    if len(path) < 2:
        return Mesh()
    frames = []
    for i, p in enumerate(path):
        t = path[min(i + 1, len(path) - 1)] - path[max(i - 1, 0)]
        L = np.linalg.norm(t)
        if L < 1e-6:
            t = np.array([0, 0, 1], np.float32)
        else:
            t = t / L
        up = np.array([0, 1, 0], np.float32)
        if abs(float(np.dot(t, up))) > 0.92:
            up = np.array([1, 0, 0], np.float32)
        s = np.cross(t, up)
        s /= np.linalg.norm(s)
        u = np.cross(s, t)
        frames.append((s, u))
    rings = []
    normals = []
    for p, (s, u) in zip(path, frames):
        ring, ns = [], []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            n = s * math.cos(a) + u * math.sin(a)
            ring.append(p + n * radius)
            ns.append(n)
        rings.append(ring)
        normals.append(ns)
    m = Mesh()
    for i in range(len(path) - 1):
        for k in range(seg):
            j = (k + 1) % seg
            quad(m, rings[i][k], rings[i][j], rings[i + 1][j], rings[i + 1][k], rect,
                 normals[i][k], normals[i][j], normals[i + 1][j], normals[i + 1][k])
    return m


def sheet(w, h, nu, nv, rect, amp=0.0, along='x'):
    """Лист в плоскости XZ, y = волна. Центр в нуле."""
    m = Mesh()
    nu, nv = int(nu), int(nv)
    pts, nrm = [], []
    for j in range(nv + 1):
        v = j / nv
        row_p, row_n = [], []
        for i in range(nu + 1):
            u = i / nu
            x, z = (u - 0.5) * w, (v - 0.5) * h
            ph = (x if along == 'x' else z)
            y = amp * math.sin(ph * 18)
            # наклон
            dy = amp * 18 * math.cos(ph * 18)
            if along == 'x':
                n = np.array([-dy, 1, 0], np.float32)
            else:
                n = np.array([0, 1, -dy], np.float32)
            n /= np.linalg.norm(n)
            row_p.append(np.array([x, y, z], np.float32))
            row_n.append(n)
        pts.append(row_p)
        nrm.append(row_n)
    for j in range(nv):
        for i in range(nu):
            quad(m, pts[j][i], pts[j][i + 1], pts[j + 1][i + 1], pts[j + 1][i], rect,
                 nrm[j][i], nrm[j][i + 1], nrm[j + 1][i + 1], nrm[j + 1][i])
    return m


class Turret:
    def __init__(self):
        self.parts = {k: Mesh() for k in ('base', 'lv2', 'lv3', 'gun')}

    def put(self, part, mesh, R=None, t=(0, 0, 0)):
        self.parts[part].append(mesh, R, t)

    def cyl(self, part, y0, y1, r0, r1, seg, tile, t=(0, 0, 0), R=None, caps=True, spin=0):
        self.put(part, cylinder(y0, y1, r0, r1, seg, tile_uv(tile, spin=spin), caps), R, t)

    def box(self, part, center, size, tile, R=None, spin=0):
        self.put(part, box(size, tile_uv(tile, spin=spin)), R, np.asarray(center, np.float32))

    def beam(self, part, p0, p1, w, h, tile):
        self.put(part, beam(p0, p1, w, h, tile_uv(tile)))

    def bag(self, part, center, radii, tile='canvas', seg=10, rings=5):
        self.put(part, ellipsoid(*radii, seg, rings, tile_uv(tile)), t=center)

    def bolt(self, part, center, along='y', tile='brass', r=0.016, h=0.018):
        R = {'y': None, 'x': rot_z(math.pi / 2), 'z': rot_x(math.pi / 2)}[along]
        self.cyl(part, 0, h, r, r, 5, tile, t=center, R=R, caps=True)

    def sign(self, part, center, w, h, text_i, R=None, back='olive'):
        faces = {'+z': sign_uv(text_i), '*': tile_uv(back)}
        self.put(part, face_box((w, h, 0.012), faces), R, np.asarray(center, np.float32))

    def cable(self, part, path, radius=0.012, tile='hose', seg=5):
        self.put(part, tube(path, radius, seg, tile_uv(tile)))

    def tris(self):
        return {k: m.tris for k, m in self.parts.items()}


def build_pkm():
    t = Turret()
    # бочка-основание, чуть криво — как вкопали не по уровню
    t.cyl('base', 0.0, 0.56, 0.34, 0.33, 12, 'rust', R=rot_z(0.04))
    for y in (0.08, 0.28, 0.46):
        t.cyl('base', y, y + 0.028, 0.355, 0.355, 12, 'iron', caps=False)
    t.cyl('base', 0.54, 0.60, 0.30, 0.16, 10, 'iron')  # горловина
    t.cyl('base', 0.78, 0.86, 0.22, 0.22, 10, 'olive')  # погон
    t.cyl('base', 0.86, 0.90, 0.10, 0.10, 8, 'iron')
    # тренога
    foot = [(0.78, 0.0, 0.22), (-0.42, 0.0, 0.72), (-0.55, 0.0, -0.62)]
    hip = [(0.16, 0.62, 0.06), (-0.08, 0.62, 0.16), (-0.12, 0.60, -0.12)]
    for a, b in zip(hip, foot):
        t.beam('base', a, b, 0.055, 0.04, 'iron')
        t.box('base', (b[0], 0.02, b[2]), (0.14, 0.03, 0.10), 'rust', spin=1)
        t.beam('base', a, (a[0], a[1] + 0.02, a[2]), 0.02, 0.02, 'weld')
    # мешки и покрышка
    t.bag('base', (0.46, 0.16, 0.28), (0.30, 0.15, 0.20))
    t.bag('base', (0.18, 0.14, 0.52), (0.26, 0.13, 0.22))
    t.bag('base', (-0.48, 0.15, 0.18), (0.28, 0.14, 0.20))
    t.bag('base', (0.05, 0.13, -0.50), (0.32, 0.12, 0.18))
    t.put('base', torus_y(0.26, 0.09, 10, 6, tile_uv('tire')), rot_z(1.15) @ rot_x(0.2), (0.62, 0.30, -0.38))
    t.box('base', (0.55, 0.06, -0.22), (0.46, 0.04, 0.10), 'wood', R=rot_y(0.4))
    # кабель, табличка, заплатка, болты
    t.cable('base', [(0.22, 0.62, 0.10), (0.40, 0.40, 0.22), (0.58, 0.22, 0.05), (0.70, 0.08, -0.05)])
    t.sign('base', (0.34, 0.32, 0.02), 0.22, 0.10, 0, R=rot_y(math.pi / 2) @ rot_z(-0.08))
    t.box('base', (0.0, 0.22, 0.345), (0.16, 0.10, 0.012), 'olive', spin=2)  # заплатка
    t.beam('base', (-0.06, 0.18, 0.35), (0.08, 0.28, 0.36), 0.012, 0.012, 'weld')
    for ang in (0.2, 1.7, 3.0, 4.4):
        t.bolt('base', (0.20 * math.sin(ang), 0.82, 0.20 * math.cos(ang)))
    t.box('base', (-0.62, 0.10, -0.15), (0.08, 0.08, 0.08), 'rust', spin=3)  # камень-упор
    # ур.2 — юбка из разномастных листов
    for ang, tile, spin in ((0.3, 'olive', 0), (2.3, 'iron', 1), (4.1, 'rust', 2)):
        plate = sheet(0.34, 0.20, 3, 2, tile_uv(tile, spin=spin), amp=0.012)
        R = rot_y(ang) @ rot_x(0.55)
        t.put('lv2', plate, R, (0.40 * math.sin(ang), 0.62, 0.40 * math.cos(ang)))
        t.bolt('lv2', (0.34 * math.sin(ang), 0.70, 0.34 * math.cos(ang)))
    t.sign('lv2', (0.34, 0.78, 0.22), 0.10, 0.06, 8, R=rot_y(0.5))
    t.bag('lv2', (-0.22, 0.28, 0.48), (0.22, 0.12, 0.16))
    # ур.3 — короб с лентой и ещё лист
    t.box('lv3', (0.42, 0.14, -0.55), (0.28, 0.20, 0.18), 'ammo', R=rot_y(-0.3))
    t.sign('lv3', (0.42, 0.18, -0.45), 0.16, 0.07, 1, R=rot_y(-0.3))
    t.sign('lv3', (0.30, 0.26, -0.48), 0.08, 0.05, 9, R=rot_y(-0.3))
    t.put('lv3', sheet(0.40, 0.16, 4, 2, tile_uv('olive', spin=1), amp=0.01), rot_x(0.4) @ rot_y(0.2), (0.05, 0.70, 0.42))
    t.cable('lv3', [(0.30, 0.20, -0.48), (0.20, 0.40, -0.20), (0.05, 0.70, 0.10)], radius=0.01, tile='tape')
    for p in ((0.32, 0.22, -0.48), (0.50, 0.20, -0.60)):
        t.bolt('lv3', p, tile='iron')

    # ствол: спарка из труб, короб, щиток
    t.box('gun', (0, 1.05, 0.16), (0.20, 0.13, 0.34), 'iron')
    t.box('gun', (0, 1.145, 0.10), (0.10, 0.04, 0.22), 'olive', spin=1)
    for x, tile in ((-0.07, 'iron'), (0.075, 'rust')):
        t.cyl('gun', 0.20, 1.22, 0.026, 0.024, 8, tile, t=(x, 1.16, 0), R=rot_x(math.pi / 2))
        t.cyl('gun', 0.20, 0.62, 0.038, 0.034, 8, 'olive', t=(x, 1.16, 0), R=rot_x(math.pi / 2), caps=False, spin=2)
        t.cyl('gun', 1.16, 1.22, 0.034, 0.034, 8, 'soot', t=(x, 1.16, 0), R=rot_x(math.pi / 2), caps=False)
        t.cyl('gun', 0.55, 0.58, 0.032, 0.032, 8, 'tape', t=(x, 1.16, 0), R=rot_x(math.pi / 2), caps=False)
    # газовая трубка и рукоять
    t.cyl('gun', 0.28, 0.95, 0.01, 0.01, 5, 'iron', t=(0, 1.24, 0), R=rot_x(math.pi / 2), caps=False)
    t.box('gun', (0, 1.28, 0.55), (0.025, 0.06, 0.16), 'wood')
    # короб с лентой
    t.box('gun', (-0.22, 1.00, 0.06), (0.14, 0.20, 0.26), 'ammo', R=rot_y(0.08))
    t.sign('gun', (-0.22, 1.02, 0.20), 0.12, 0.06, 1, R=rot_y(0.08))
    for i, z in enumerate((0.02, 0.08, 0.14)):
        t.box('gun', (-0.12, 1.02, z), (0.06, 0.012, 0.03), 'brass', R=rot_z(0.4 if i % 2 else -0.3))
    # щиток из листа, щель — два куска
    shield = sheet(0.32, 0.22, 4, 2, tile_uv('olive'), amp=0.01)
    t.put('gun', shield, rot_x(0.35), (0, 1.12, 0.40))
    t.sign('gun', (0.10, 1.16, 0.48), 0.12, 0.05, 6, R=rot_x(0.35))
    t.beam('gun', (-0.10, 1.02, 0.30), (0.10, 1.14, 0.46), 0.016, 0.016, 'weld')
    t.cable('gun', [(0.10, 1.02, 0.05), (0.16, 0.92, 0.12), (0.08, 0.88, 0.22)], radius=0.008, tile='hose')
    for p in ((-0.08, 1.12, 0.32), (0.08, 1.12, 0.32), (0.09, 1.05, 0.0), (-0.09, 1.00, 0.28)):
        t.bolt('gun', p)
    # сошки-вилка
    t.beam('gun', (-0.10, 0.92, 0.02), (-0.10, 1.00, 0.02), 0.03, 0.03, 'iron')
    t.beam('gun', (0.10, 0.92, 0.02), (0.10, 1.00, 0.02), 0.03, 0.03, 'iron')
    t.box('gun', (0, 0.91, 0.02), (0.24, 0.03, 0.08), 'rust')
    return t


def build_nail():
    t = Turret()
    # поддон
    t.box('base', (0, 0.04, 0.05), (0.90, 0.05, 0.62), 'wood')
    for x in (-0.28, 0.28):
        t.box('base', (x, 0.09, 0.05), (0.08, 0.06, 0.70), 'wood', spin=1)
    t.box('base', (0, 0.11, 0.05), (0.78, 0.025, 0.10), 'wood', spin=2)
    t.box('base', (0, 0.11, -0.22), (0.78, 0.025, 0.10), 'wood', spin=1)
    # стойка и ресиверная тумба
    t.cyl('base', 0.10, 0.98, 0.055, 0.048, 8, 'rust')
    t.cyl('base', 0.96, 1.02, 0.10, 0.10, 8, 'iron')
    t.beam('base', (0.0, 0.4, 0.0), (0.55, 0.08, 0.28), 0.04, 0.035, 'iron')
    t.beam('base', (0.0, 0.4, 0.0), (-0.20, 0.08, 0.42), 0.035, 0.03, 'rust')
    # баллон компрессора — ржавый, с латунным вентилем
    t.cyl('base', 0.08, 0.92, 0.16, 0.15, 10, 'rust', t=(-0.46, 0, -0.12))
    t.cyl('base', 0.92, 1.02, 0.05, 0.04, 6, 'brass', t=(-0.46, 0, -0.12))
    t.cyl('base', 0.30, 0.34, 0.175, 0.175, 10, 'tape', t=(-0.46, 0, -0.12), caps=False)
    t.cyl('base', 0.62, 0.66, 0.172, 0.172, 10, 'iron', t=(-0.46, 0, -0.12), caps=False)
    t.sign('base', (-0.46, 0.55, 0.05), 0.20, 0.09, 2, R=rot_y(0))
    t.sign('base', (-0.28, 0.78, -0.12), 0.10, 0.05, 3, R=rot_y(math.pi / 2))
    # покрышка-груз и мешки
    t.put('base', torus_y(0.24, 0.085, 10, 6, tile_uv('tire')), t=(0.48, 0.12, -0.22))
    t.bag('base', (0.22, 0.22, 0.36), (0.28, 0.13, 0.18))
    t.bag('base', (-0.10, 0.20, 0.40), (0.24, 0.12, 0.16))
    t.cable('base', [(-0.46, 0.98, -0.12), (-0.30, 0.80, 0.05), (-0.08, 0.70, 0.02), (0.0, 0.98, 0.0)], radius=0.014)
    t.box('base', (0.36, 0.16, 0.22), (0.16, 0.08, 0.012), 'olive', R=rot_y(0.4), spin=1)  # заплатка на воздухе — табличка-накладка
    for p in ((0.0, 0.12, 0.32), (-0.36, 0.12, 0.16), (0.40, 0.12, -0.05)):
        t.bolt('base', p, tile='iron', r=0.02, h=0.012)
    # ур.2 — бронещиток перед стойкой и ещё мешок
    t.put('lv2', sheet(0.36, 0.28, 3, 2, tile_uv('olive'), amp=0.012), rot_x(0.15), (0.0, 0.55, 0.28))
    t.beam('lv2', (-0.16, 0.40, 0.16), (-0.16, 0.62, 0.30), 0.02, 0.02, 'weld')
    t.beam('lv2', (0.16, 0.40, 0.16), (0.16, 0.62, 0.30), 0.02, 0.02, 'iron')
    t.sign('lv2', (0.10, 0.62, 0.34), 0.08, 0.05, 8, R=rot_x(0.15))
    t.bag('lv2', (0.55, 0.22, 0.16), (0.20, 0.11, 0.16))
    # ур.3 — второй баллон и короб гвоздей
    t.cyl('lv3', 0.10, 0.55, 0.10, 0.09, 8, 'red', t=(0.42, 0, 0.22))
    t.cyl('lv3', 0.22, 0.26, 0.112, 0.112, 8, 'tape', t=(0.42, 0, 0.22), caps=False)
    t.box('lv3', (-0.22, 0.18, -0.28), (0.26, 0.16, 0.18), 'ammo', R=rot_y(0.2))
    t.sign('lv3', (-0.22, 0.20, -0.18), 0.14, 0.06, 2, R=rot_y(0.2))
    t.sign('lv3', (0.42, 0.40, 0.33), 0.08, 0.05, 9)
    t.cable('lv3', [(0.42, 0.55, 0.22), (0.20, 0.70, 0.10), (0.0, 0.96, 0.02)], radius=0.01)

    # ствол: длинная труба, бункер, вентиль
    t.box('gun', (0, 1.08, 0.12), (0.16, 0.12, 0.22), 'iron')
    t.cyl('gun', 0.18, 1.46, 0.028, 0.022, 8, 'iron', t=(0, 1.12, 0), R=rot_x(math.pi / 2))
    for z in (0.45, 0.78, 1.10):
        t.cyl('gun', z, z + 0.03, 0.038, 0.038, 8, 'rust', t=(0, 1.12, 0), R=rot_x(math.pi / 2), caps=False)
    t.cyl('gun', 1.40, 1.48, 0.04, 0.03, 8, 'soot', t=(0, 1.12, 0), R=rot_x(math.pi / 2))
    t.cyl('gun', 0.62, 0.68, 0.034, 0.034, 8, 'tape', t=(0, 1.12, 0), R=rot_x(math.pi / 2), caps=False)
    # бункер — ящик и усечённая воронка
    t.box('gun', (0, 1.26, 0.08), (0.16, 0.10, 0.18), 'olive', spin=1)
    t.cyl('gun', 1.30, 1.46, 0.09, 0.045, 8, 'rust', t=(0, 0, 0.08), caps=False)
    # гвозди торчат
    for i, x in enumerate((-0.04, 0, 0.035, 0.02)):
        t.cyl('gun', 1.44, 1.52, 0.004, 0.004, 4, 'brass', t=(x, 0, 0.08 + (i % 2) * 0.02), caps=False)
    # маховик вентиля
    t.put('gun', torus_y(0.05, 0.012, 8, 4, tile_uv('brass')), rot_z(math.pi / 2), (-0.12, 1.08, 0.10))
    t.cyl('gun', 0, 0.04, 0.012, 0.012, 5, 'brass', t=(-0.12, 1.08, 0.10), R=rot_z(math.pi / 2))
    t.box('gun', (0.0, 1.02, -0.02), (0.04, 0.10, 0.08), 'wood', R=rot_x(-0.5))
    t.sign('gun', (0.0, 1.34, 0.18), 0.12, 0.05, 2)
    t.cable('gun', [(0.0, 0.98, 0.0), (0.08, 1.02, 0.08), (0.0, 1.06, 0.16)], radius=0.01)
    t.beam('gun', (0.06, 1.10, 0.22), (0.06, 1.16, 0.34), 0.012, 0.012, 'weld')
    for p in ((0.07, 1.12, 0.22), (-0.07, 1.12, 0.0)):
        t.bolt('gun', p)
    return t


def build_flame():
    t = Turret()
    # сварная рама
    for x, z in ((-0.42, -0.28), (0.42, -0.28), (-0.36, 0.36), (0.36, 0.36)):
        t.beam('base', (x, 0.0, z), (x * 0.55, 0.72, z * 0.45), 0.04, 0.035, 'iron')
        t.box('base', (x, 0.02, z), (0.12, 0.025, 0.10), 'rust')
    t.beam('base', (-0.24, 0.70, -0.12), (0.24, 0.70, -0.12), 0.04, 0.03, 'iron')
    t.beam('base', (-0.20, 0.70, 0.16), (0.20, 0.70, 0.16), 0.04, 0.03, 'rust')
    t.beam('base', (0, 0.70, -0.12), (0, 0.70, 0.16), 0.035, 0.03, 'iron')
    # красный баллон стоя и ржавый лёжа
    t.cyl('base', 0.0, 0.92, 0.145, 0.135, 10, 'red', t=(-0.28, 0, -0.02))
    t.cyl('base', 0.92, 1.02, 0.045, 0.035, 6, 'brass', t=(-0.28, 0, -0.02))
    t.cyl('base', 0.55, 0.60, 0.155, 0.155, 10, 'tape', t=(-0.28, 0, -0.02), caps=False)
    t.sign('base', (-0.28, 0.48, 0.13), 0.18, 0.08, 4)
    t.sign('base', (-0.28, 0.66, 0.13), 0.12, 0.05, 5)
    t.cyl('base', -0.32, 0.32, 0.12, 0.11, 8, 'rust', t=(0.22, 0.18, -0.22), R=rot_z(math.pi / 2))
    t.cyl('base', -0.08, 0.08, 0.135, 0.135, 8, 'tape', t=(0.22, 0.18, -0.22), R=rot_z(math.pi / 2), caps=False)
    t.beam('base', (-0.05, 0.30, -0.22), (0.48, 0.30, -0.22), 0.015, 0.012, 'iron')  # хомут
    t.cable('base', [(-0.28, 0.98, -0.02), (-0.10, 0.78, 0.05), (0.05, 0.74, 0.10)], radius=0.016)
    # мешки-бруствер и «опасность»
    t.bag('base', (0.05, 0.16, 0.48), (0.34, 0.14, 0.16))
    t.bag('base', (-0.32, 0.15, 0.42), (0.26, 0.13, 0.16))
    t.bag('base', (0.38, 0.14, 0.40), (0.22, 0.12, 0.15))
    hazard = face_box((0.28, 0.16, 0.012), {'+z': tile_uv('hazard'), '*': tile_uv('iron')})
    t.put('base', hazard, rot_x(0.15) @ rot_y(-0.2), (0.46, 0.40, 0.16))
    t.sign('base', (0.34, 0.28, 0.30), 0.14, 0.06, 10, R=rot_y(-0.4))
    t.beam('base', (-0.18, 0.2, 0.12), (-0.18, 0.55, 0.12), 0.014, 0.014, 'weld')
    t.box('base', (0.05, 0.22, -0.05), (0.10, 0.08, 0.012), 'olive', spin=2)
    # ур.2 — тепловой экран
    t.put('lv2', sheet(0.50, 0.32, 4, 2, tile_uv('iron', spin=1), amp=0.016, along='z'), rot_x(0.9), (0.05, 0.48, 0.22))
    t.beam('lv2', (-0.18, 0.36, 0.10), (-0.18, 0.36, 0.28), 0.016, 0.016, 'weld')
    t.beam('lv2', (0.22, 0.36, 0.10), (0.22, 0.36, 0.28), 0.016, 0.016, 'weld')
    t.sign('lv2', (0.16, 0.55, 0.30), 0.08, 0.05, 8)
    t.bag('lv2', (0.22, 0.30, 0.50), (0.20, 0.10, 0.14))
    # ур.3 — запасной баллон и накладка
    t.cyl('lv3', 0.0, 0.42, 0.09, 0.08, 8, 'red', t=(0.40, 0.0, -0.02))
    t.cyl('lv3', 0.16, 0.20, 0.10, 0.10, 8, 'tape', t=(0.40, 0.0, -0.02), caps=False)
    t.sign('lv3', (0.40, 0.24, 0.09), 0.10, 0.05, 9)
    t.put('lv3', sheet(0.26, 0.18, 3, 2, tile_uv('olive'), amp=0.01), rot_y(0.8) @ rot_x(0.3), (-0.48, 0.40, 0.10))
    for p in ((-0.42, 0.48, 0.16), (0.36, 0.20, 0.02)):
        t.bolt('lv3', p, tile='iron')

    # ствол: короткий раструб, клетка, рукоять
    t.box('gun', (0, 0.92, 0.10), (0.14, 0.12, 0.20), 'iron')
    t.cyl('gun', 0.18, 0.72, 0.04, 0.045, 8, 'rust', t=(0, 0.98, 0), R=rot_x(math.pi / 2))
    t.cyl('gun', 0.70, 1.02, 0.05, 0.085, 8, 'soot', t=(0, 0.98, 0), R=rot_x(math.pi / 2))
    t.cyl('gun', 0.40, 0.46, 0.055, 0.055, 8, 'tape', t=(0, 0.98, 0), R=rot_x(math.pi / 2), caps=False)
    # клетка вокруг сопла
    for x, y in ((-0.07, 1.06), (0.07, 1.06), (-0.07, 0.90), (0.07, 0.90)):
        t.cyl('gun', 0.55, 1.02, 0.008, 0.008, 4, 'iron', t=(x, y, 0), R=rot_x(math.pi / 2), caps=False)
    t.beam('gun', (-0.07, 1.06, 1.00), (0.07, 1.06, 1.00), 0.012, 0.012, 'rust')
    t.beam('gun', (-0.07, 0.90, 1.00), (0.07, 0.90, 1.00), 0.012, 0.012, 'rust')
    # пилот и шланг
    t.cyl('gun', 0.85, 1.00, 0.008, 0.008, 4, 'brass', t=(0.06, 1.00, 0), R=rot_x(math.pi / 2), caps=False)
    t.cable('gun', [(0, 0.88, -0.02), (-0.08, 0.78, 0.05), (0.0, 0.74, 0.12)], radius=0.014)
    t.box('gun', (0, 0.84, 0.02), (0.035, 0.10, 0.07), 'wood', R=rot_x(-0.6))
    t.sign('gun', (0, 1.08, 0.55), 0.12, 0.05, 5, R=rot_x(0.2))
    t.beam('gun', (-0.04, 0.96, 0.30), (0.05, 1.00, 0.55), 0.012, 0.012, 'weld')
    for p in ((0.06, 0.96, 0.20), (-0.06, 0.96, 0.18)):
        t.bolt('gun', p)
    t.box('gun', (0, 0.74, 0.08), (0.18, 0.025, 0.10), 'olive')  # вертлюг
    return t


# ---------- атлас ----------
def _noise(n, octaves=5, seed=0):
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n), np.float32)
    acc = 0
    for o in range(octaves):
        s = 2 ** (o + 2)
        g = rng.random((s + 1, s + 1), np.float32)
        im = np.asarray(Image.fromarray((g * 255).astype(np.uint8)).resize((n, n), Image.BILINEAR), np.float32) / 255
        w = 1 / (1.65 ** o)
        out += im * w
        acc += w
    out /= acc
    return out


def _normal_from_height(h, scale=4.0):
    gy, gx = np.gradient(h.astype(np.float32))
    n = np.stack((-gx * scale, gy * scale, np.ones_like(h)), -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True) + 1e-8
    return np.clip(n * 0.5 + 0.5, 0, 1)


def _scratches(n, seed, count, width=1):
    im = Image.new('L', (n, n), 0)
    d = ImageDraw.Draw(im)
    rng = np.random.default_rng(seed)
    for _ in range(count):
        x, y = rng.random() * n, rng.random() * n
        a = rng.random() * math.pi
        L = n * (0.08 + rng.random() * 0.45)
        d.line([(x, y), (x + math.cos(a) * L, y + math.sin(a) * L)], fill=255, width=width)
    return np.asarray(im, np.float32) / 255


def _rgb(h, rgb):
    return np.stack([np.full_like(h, c, np.float32) for c in rgb], -1)


def make_tiles(n=256):
    """Возвращает albedo, height, rough, metal, ao — каждый (n,n) или (n,n,3)."""
    tiles = {}

    def pack(name, alb, height, rough, metal, ao):
        tiles[name] = (
            np.clip(alb, 0, 1).astype(np.float32),
            np.clip(height, 0, 1).astype(np.float32),
            np.clip(rough, 0, 1).astype(np.float32),
            np.clip(metal, 0, 1).astype(np.float32),
            np.clip(ao, 0, 1).astype(np.float32),
        )

    nz = _noise(n, 5, 1)
    pit = _noise(n, 4, 2)
    flake = _noise(n, 5, 3) > 0.62
    base = _rgb(nz, (0.45, 0.24, 0.12)) * (0.75 + 0.4 * nz[..., None])
    dark = pit[..., None]
    alb = base * (1 - 0.35 * dark)
    alb[flake] *= np.array([1.15, 0.85, 0.7], np.float32)
    scr = _scratches(n, 4, 12)
    alb = np.clip(alb + scr[..., None] * 0.08, 0, 1)
    height = (0.35 + 0.4 * pit) * (1 - 0.5 * flake) + scr * 0.15
    pack('rust', alb, height, 0.78 + 0.2 * pit, 0.18 + 0.2 * flake, 0.75 + 0.25 * nz)

    nz = _noise(n, 5, 5)
    chip = (_noise(n, 5, 6) > 0.70) | (_scratches(n, 7, 20) > 0)
    paint = _rgb(nz, (0.32, 0.38, 0.26)) * (0.82 + 0.28 * nz[..., None])
    rustc = _rgb(nz, (0.42, 0.20, 0.09))
    alb = np.where(chip[..., None], rustc, paint)
    edge = _scratches(n, 8, 8, 2)
    alb = np.clip(alb * (1 - 0.25 * edge[..., None]) + edge[..., None] * 0.15, 0, 1)
    pack('olive', alb, 0.25 + 0.2 * nz + chip * 0.45, np.where(chip, 0.7, 0.62), np.where(chip, 0.42, 0.08), 0.8 + 0.2 * nz)

    nz = _noise(n, 5, 9)
    scr = _scratches(n, 10, 28)
    alb = _rgb(nz, (0.28, 0.30, 0.32)) * (0.85 + 0.25 * nz[..., None])
    alb = np.clip(alb + scr[..., None] * 0.18, 0, 1)
    rustm = _noise(n, 4, 11) > 0.78
    alb[rustm] = np.array([0.40, 0.22, 0.12], np.float32)
    pack('iron', alb, 0.2 + scr * 0.55 + rustm * 0.2, np.where(scr > 0, 0.38, 0.5), np.where(rustm, 0.3, 0.48), 0.82 + 0.15 * nz)

    nz = _noise(n, 4, 12)
    heat = np.clip((np.linspace(0, 1, n)[None, :] - 0.55) * 2, 0, 1)  # к одному краю теплее — дульный срез
    alb = _rgb(nz, (0.07, 0.06, 0.05)) * (0.7 + 0.4 * nz[..., None])
    alb += heat[..., None] * np.array([0.18, 0.07, 0.02], np.float32)
    pack('soot', alb, 0.15 + 0.3 * nz, 0.92 - 0.1 * heat, 0.04, 0.7 + 0.2 * nz)

    nz = _noise(n, 4, 13)
    yy = np.linspace(0, 1, n)
    tread = (np.sin(yy * math.pi * 10) > 0.2).astype(np.float32)
    alb = _rgb(nz, (0.07, 0.07, 0.075)) * (0.85 + 0.3 * nz[..., None])
    alb *= (0.75 + 0.35 * tread)[..., None]
    pack('tire', alb, 0.2 + tread * 0.7, 0.9, 0.0, 0.65 + 0.2 * tread)

    nz = _noise(n, 4, 14)
    weave_x = (np.sin(np.arange(n) * 0.55) * 0.5 + 0.5)
    weave = (weave_x[None, :] * 0.5 + weave_x[:, None] * 0.5)
    alb = _rgb(nz, (0.78, 0.68, 0.48)) * (0.88 + 0.22 * weave[..., None]) * (0.94 + 0.1 * nz[..., None])
    dirt = np.clip(np.linspace(0.4, 1, n)[:, None] * _noise(n, 3, 15), 0, 1)
    alb *= (1 - 0.28 * dirt[..., None])
    # верёвка посреди мешка
    band = (np.abs(np.linspace(-1, 1, n)[:, None]) < 0.06).astype(np.float32)
    alb = alb * (1 - 0.45 * band[..., None]) + np.array([0.28, 0.20, 0.12]) * band[..., None]
    pack('canvas', alb, 0.35 + weave * 0.4 + band * 0.25, 0.9, 0.0, 0.82 + 0.15 * (1 - dirt))

    nz = _noise(n, 4, 16)
    grain = (np.sin(np.arange(n) * 0.35 + nz * 2) * 0.5 + 0.5)
    plank = ((np.arange(n)[:, None] // (n // 4)) % 2) * 0.08
    alb = _rgb(nz, (0.42, 0.28, 0.14)) * (0.75 + 0.4 * grain[..., None])
    alb[..., 0] += plank
    pack('wood', alb, 0.25 + grain * 0.35 + plank, 0.86, 0.0, 0.78 + 0.15 * nz)

    nz = _noise(n, 5, 17)
    chip = _noise(n, 5, 18) > 0.66
    paint = _rgb(nz, (0.55, 0.12, 0.10)) * (0.8 + 0.3 * nz[..., None])
    bare = _rgb(nz, (0.55, 0.56, 0.58))
    alb = np.where(chip[..., None], bare * 0.7 + np.array([0.15, 0.05, 0.02]) , paint)
    band = (np.abs(np.linspace(-1, 1, n)[:, None]) < 0.12).astype(np.float32)
    alb = alb * (1 - 0.75 * band[..., None]) + np.array([0.85, 0.82, 0.74]) * band[..., None]
    alb = np.clip(alb * (0.9 + 0.1 * nz[..., None]), 0, 1)
    pack('red', alb, 0.2 + chip * 0.5 + band * 0.15, np.where(chip, 0.45, 0.6), np.where(chip, 0.4, 0.12), 0.8)

    diag = ((np.indices((n, n)).sum(0) / n * 6) % 1 < 0.5)
    grime = _noise(n, 4, 19)
    yel = np.array([0.78, 0.58, 0.08], np.float32)
    blk = np.array([0.06, 0.06, 0.05], np.float32)
    alb = np.where(diag[..., None], yel, blk) * (0.75 + 0.35 * grime[..., None])
    pack('hazard', alb, 0.15 + grime * 0.2, 0.7, 0.06, 0.85)

    nz = _noise(n, 4, 20)
    tarn = _noise(n, 4, 21) > 0.72
    scr = _scratches(n, 22, 16)
    alb = _rgb(nz, (0.72, 0.55, 0.22)) * (0.85 + 0.2 * nz[..., None])
    alb[tarn] = np.array([0.25, 0.38, 0.22], np.float32)
    alb = np.clip(alb + scr[..., None] * 0.2, 0, 1)
    pack('brass', alb, 0.15 + scr * 0.4, np.where(scr > 0, 0.28, 0.42), np.where(tarn, 0.2, 0.55), 0.84)

    nz = _noise(n, 3, 23)
    # край мотка изоленты
    edge = (np.linspace(0, 1, n) > 0.82).astype(np.float32)
    alb = _rgb(nz, (0.08, 0.08, 0.09)) * (0.85 + 0.3 * nz[..., None])
    alb += edge[:, None, None] * 0.05
    pack('tape', alb, 0.1 + edge[:, None] * 0.4, 0.75, 0.02, 0.9)

    nz = _noise(n, 3, 24)
    rib = (np.sin(np.linspace(0, 18 * math.pi, n)) * 0.5 + 0.5).astype(np.float32)
    alb = _rgb(nz, (0.10, 0.10, 0.11)) * (0.8 + 0.25 * rib[:, None, None])
    pack('hose', alb, 0.2 + rib[:, None] * 0.6, 0.88, 0.0, 0.8)

    nz = _noise(n, 4, 25)
    chip = _noise(n, 4, 26) > 0.75
    alb = _rgb(nz, (0.28, 0.36, 0.22)) * (0.85 + 0.2 * nz[..., None])
    alb[chip] *= 0.55
    # рёбра ящика
    rib = ((np.linspace(0, 1, n) < 0.08) | (np.linspace(0, 1, n) > 0.92)).astype(np.float32)
    alb *= (0.85 + 0.2 * rib)[:, None, None]
    pack('ammo', alb, 0.2 + rib[:, None] * 0.35 + chip * 0.3, 0.66, np.where(chip, 0.35, 0.1), 0.78)

    nz = _noise(n, 5, 27)
    blob = _noise(n, 3, 28)
    alb = _rgb(nz, (0.62, 0.64, 0.66)) * (0.7 + 0.5 * blob[..., None])
    alb *= (0.85 + 0.2 * nz[..., None])
    pack('weld', alb, 0.2 + blob * 0.8, 0.55 + 0.3 * nz, 0.35, 0.7 + 0.2 * nz)

    # таблички дорисовываются отдельно поверх знакового фона
    nz = _noise(n, 4, 29)
    bg = _rgb(nz, (0.34, 0.36, 0.28)) * (0.88 + 0.2 * nz[..., None])
    pack('signA', bg, 0.12 + 0.1 * nz, np.full((n, n), 0.7), np.full((n, n), 0.06), np.full((n, n), 0.9))
    nz = _noise(n, 4, 30)
    bg = _rgb(nz, (0.40, 0.32, 0.22)) * (0.88 + 0.2 * nz[..., None])
    pack('signB', bg, 0.12 + 0.1 * nz, np.full((n, n), 0.72), np.full((n, n), 0.05), np.full((n, n), 0.9))
    return tiles


def paint_signs(alb, rough):
    """Рисует трафаретные надписи в тайлы signA/signB. alb — float 0..1, RGB, верх изображения = v 0."""
    n = alb.shape[0]
    im = Image.fromarray((np.clip(alb, 0, 1) * 255).astype(np.uint8), 'RGB')
    draw = ImageDraw.Draw(im)
    rng = np.random.default_rng(11)
    cell_w, cell_h = n // TILES // 2, n // TILES // 4
    for i, text in enumerate(SIGNS):
        tile = 0 if i < 8 else 1
        k = i % 8
        sc, sr = k % 2, k // 2
        c, r = TILE['signA' if tile == 0 else 'signB']
        x0 = int((c / TILES) * n + sc * cell_w)
        y0 = int((r / TILES) * n + sr * cell_h)
        # размер шрифта под клетку
        size = 54 if len(text) <= 3 else 36 if len(text) <= 5 else 28
        font = ImageFont.truetype(FONT, size)
        while size > 16 and draw.textlength(text, font=font) > cell_w - 10:
            size -= 2
            font = ImageFont.truetype(FONT, size)
        # лёгкий перекос: рисуем на временной картинке и вклеиваем
        plate = Image.new('RGBA', (cell_w, cell_h), (0, 0, 0, 0))
        pd = ImageDraw.Draw(plate)
        col = (232, 214, 150, 255) if i % 3 else (210, 48, 32, 255)
        pd.text((cell_w / 2, cell_h / 2), text, font=font, fill=col, anchor='mm')
        plate = plate.rotate(float(rng.uniform(-4, 4)), resample=Image.BICUBIC)
        im.paste(plate, (x0, y0), plate)
        # потёк
        if rng.random() > 0.4:
            dx = x0 + cell_w * 0.5 + rng.uniform(-8, 8)
            draw.line([(dx, y0 + cell_h * 0.55), (dx + rng.uniform(-2, 2), y0 + cell_h * 0.95)], fill=col[:3], width=2)
    arr = np.asarray(im, np.float32) / 255
    # сколы краски букв — вернуть фон пятнами
    chip = _noise(n, 5, 40) > 0.86
    arr = np.where(chip[..., None], alb, arr)
    return arr


def build_atlas():
    n = ATLAS // TILES
    tiles = make_tiles(n)
    alb = np.zeros((ATLAS, ATLAS, 3), np.float32)
    height = np.zeros((ATLAS, ATLAS), np.float32)
    rough = np.zeros((ATLAS, ATLAS), np.float32)
    metal = np.zeros((ATLAS, ATLAS), np.float32)
    ao = np.ones((ATLAS, ATLAS), np.float32)
    for name, (c, r) in TILE.items():
        a, h, ro, me, oc = tiles[name]
        y0, x0 = r * n, c * n
        alb[y0:y0 + n, x0:x0 + n] = a
        height[y0:y0 + n, x0:x0 + n] = h
        rough[y0:y0 + n, x0:x0 + n] = ro
        metal[y0:y0 + n, x0:x0 + n] = me
        ao[y0:y0 + n, x0:x0 + n] = oc
    alb = paint_signs(alb, rough)
    # впекаем AO в альбедо, чтобы читалось и без uv2
    alb *= (0.55 + 0.45 * ao)[..., None]
    normal = _normal_from_height(height, 3.2)
    orm = np.stack([ao, rough, metal], -1)
    return alb, normal, orm


def _to_indexed(mesh):
    if not mesh.P:
        return None
    P = np.stack(mesh.P).astype(np.float32)
    N = np.stack(mesh.N).astype(np.float32)
    UV = np.stack(mesh.UV).astype(np.float32)
    N /= np.linalg.norm(N, axis=1, keepdims=True) + 1e-8
    T = np.zeros_like(P)
    W = np.ones(len(P), np.float32)
    for i in range(0, len(P), 3):
        p0, p1, p2 = P[i:i + 3]
        u0, u1, u2 = UV[i:i + 3]
        dp1, dp2 = p1 - p0, p2 - p0
        duv1, duv2 = u1 - u0, u2 - u0
        det = duv1[0] * duv2[1] - duv2[0] * duv1[1]
        if abs(float(det)) < 1e-12:
            t = np.array([1, 0, 0], np.float32)
            b = np.array([0, 1, 0], np.float32)
        else:
            t = (dp1 * duv2[1] - dp2 * duv1[1]) / det
            b = (dp2 * duv1[0] - dp1 * duv2[0]) / det
        w = 1.0 if np.dot(np.cross(N[i], t), b) >= 0 else -1.0
        T[i:i + 3] = t
        W[i:i + 3] = w
    T -= N * np.sum(N * T, axis=1, keepdims=True)
    T /= np.linalg.norm(T, axis=1, keepdims=True) + 1e-8
    key = {}
    idx = []
    P2, N2, UV2, T2, Ws = [], [], [], [], []
    qp = np.round(P, 4)
    qn = np.round(N, 3)
    qu = np.round(UV, 4)
    for i in range(len(P)):
        k = (qp[i, 0], qp[i, 1], qp[i, 2], qn[i, 0], qn[i, 1], qn[i, 2], qu[i, 0], qu[i, 1])
        j = key.get(k)
        if j is None:
            j = len(P2)
            key[k] = j
            P2.append(P[i])
            N2.append(N[i])
            UV2.append(UV[i])
            T2.append(T[i])
            Ws.append(W[i])
        idx.append(j)
    P2 = np.stack(P2).astype(np.float32)
    N2 = np.stack(N2).astype(np.float32)
    UV2 = np.stack(UV2).astype(np.float32)
    Tan = np.concatenate([np.stack(T2), np.asarray(Ws, np.float32)[:, None]], 1).astype(np.float32)
    return P2, N2, UV2, Tan, np.asarray(idx, np.uint32)


def export_glb(turrets, images):
    """turrets: name -> Turret. images: list of (bytes, mime)."""
    bin_ = bytearray()
    views, accs, meshes, nodes = [], [], [], []

    def pad(n=4):
        while len(bin_) % n:
            bin_.append(0)

    def push(arr, target=None):
        pad()
        off = len(bin_)
        raw = arr.tobytes()
        bin_.extend(raw)
        v = {'buffer': 0, 'byteOffset': off, 'byteLength': len(raw)}
        if target:
            v['target'] = target
        views.append(v)
        return len(views) - 1

    def acc(view, comp, count, typ, extra=None):
        a = {'bufferView': view, 'componentType': comp, 'count': count, 'type': typ}
        if extra:
            a.update(extra)
        accs.append(a)
        return len(accs) - 1

    # images first so bufferViews of geometry come after? order doesn't matter
    image_views = []
    for blob, _mime in images:
        pad()
        off = len(bin_)
        bin_.extend(blob)
        views.append({'buffer': 0, 'byteOffset': off, 'byteLength': len(blob)})
        image_views.append(len(views) - 1)

    mesh_of = {}  # (turret, part) -> mesh index

    def add_mesh(name, mesh):
        packed = _to_indexed(mesh)
        if packed is None:
            return None
        P, N, UV, Tan, idx = packed
        ip = acc(push(P, 34962), 5126, len(P), 'VEC3', {'min': P.min(0).tolist(), 'max': P.max(0).tolist()})
        inn = acc(push(N, 34962), 5126, len(N), 'VEC3')
        iuv = acc(push(UV, 34962), 5126, len(UV), 'VEC2')
        iuv2 = acc(push(UV, 34962), 5126, len(UV), 'VEC2')  # TEXCOORD_2 = uv2 для aoMap
        it = acc(push(Tan, 34962), 5126, len(Tan), 'VEC4')
        itype = 5123 if len(idx) < 65535 and len(P) < 65535 else 5125
        idata = idx.astype(np.uint16 if itype == 5123 else np.uint32)
        ii = acc(push(idata, 34963), itype, len(idx), 'SCALAR')
        meshes.append({
            'name': name,
            'primitives': [{
                'attributes': {'POSITION': ip, 'NORMAL': inn, 'TEXCOORD_0': iuv, 'TEXCOORD_2': iuv2, 'TANGENT': it},
                'indices': ii,
                'material': 0,
            }],
        })
        return len(meshes) - 1

    root_ids = []
    for name, tur in turrets.items():
        children = []
        for part in ('base', 'lv2', 'lv3'):
            mi = add_mesh(name + '-' + part, tur.parts[part])
            if mi is None:
                continue
            nodes.append({'name': part if part != 'base' else 'base', 'mesh': mi})
            # lv2/lv3 должны называться именно так, base — base
            children.append(len(nodes) - 1)
        gun_children = []
        mi = add_mesh(name + '-gun', tur.parts['gun'])
        if mi is not None:
            nodes.append({'name': 'gun', 'mesh': mi})
            gun_children.append(len(nodes) - 1)
        if gun_children:
            nodes.append({'name': 'gun', 'children': gun_children})
            # ВАЖНО: и меш, и группа не могут оба зваться gun, если меш сам называется gun —
            # three.js даст мешу имя узла. Родитель с именем gun надёжнее, меш пусть будет телом.
            # Переименуем меш-узел, группа останется gun.
            nodes[gun_children[0]]['name'] = 'body'
            children.append(len(nodes) - 1)
        nodes.append({'name': name, 'children': children})
        root_ids.append(len(nodes) - 1)

    samplers = [{'magFilter': 9729, 'minFilter': 9987, 'wrapS': 33071, 'wrapT': 33071}]
    images_json = [{'mimeType': mime, 'bufferView': bv} for bv, (_blob, mime) in zip(image_views, images)]
    textures = [{
        'sampler': 0,
        'source': i,
        'extensions': {'EXT_texture_webp': {'source': i}},
    } for i in range(len(images))]
    material = {
        'name': 'scrap',
        'pbrMetallicRoughness': {
            'baseColorFactor': [1, 1, 1, 1],
            'metallicFactor': 1,
            'roughnessFactor': 1,
            'baseColorTexture': {'index': 0},
            'metallicRoughnessTexture': {'index': 2},
        },
        'normalTexture': {'index': 1, 'scale': 1},
        'occlusionTexture': {'index': 2, 'strength': 0.65},
        'doubleSided': False,
    }
    gl = {
        'asset': {'version': '2.0', 'generator': 'terra tools/art/turret_gen.py',
                  'extras': {'muzzle': {k: list(v) for k, v in MUZZLE.items()}}},
        'extensionsUsed': ['EXT_texture_webp'],
        'scene': 0,
        'scenes': [{'name': 'turrets', 'nodes': root_ids}],
        'nodes': nodes,
        'meshes': meshes,
        'materials': [material],
        'textures': textures,
        'images': images_json,
        'samplers': samplers,
        'accessors': accs,
        'bufferViews': views,
        'buffers': [{'byteLength': len(bin_)}],
    }
    js = json.dumps(gl, separators=(',', ':')).encode()
    while len(js) % 4:
        js += b' '
    pad()
    total = 12 + 8 + len(js) + 8 + len(bin_)
    out = struct.pack('<III', 0x46546C67, 2, total)
    out += struct.pack('<II', len(js), 0x4E4F534A) + js
    out += struct.pack('<II', len(bin_), 0x004E4942) + bytes(bin_)
    return out


def main():
    print('atlas…')
    alb, nrm, orm = build_atlas()
    # нормаль — качество чуть выше, ORM можно пожёстче
    def webp(arr, q):
        im = Image.fromarray((np.clip(arr, 0, 1) * 255).astype(np.uint8), 'RGB')
        buf = io.BytesIO()
        im.save(buf, 'WEBP', quality=q, method=4)
        return buf.getvalue()
    images = [(webp(alb, 70), 'image/webp'), (webp(nrm, 78), 'image/webp'), (webp(orm, 62), 'image/webp')]
    print('webp', [len(b) for b, _ in images])
    Image.fromarray((alb * 255).astype(np.uint8)).save('/tmp/turret-atlas-albedo.png')

    turrets = {'pkm': build_pkm(), 'nail': build_nail(), 'flame': build_flame()}
    for name, tur in turrets.items():
        info = tur.tris()
        total = sum(info.values())
        print(f'{name}: {info} total {total}  muzzle {MUZZLE[name]}')
        if total > 4000:
            raise SystemExit(f'{name} слишком тяжёлая: {total} треуг.')
    blob = export_glb(turrets, images)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    open(OUT, 'wb').write(blob)
    print('wrote', OUT, len(blob))


if __name__ == '__main__':
    main()
