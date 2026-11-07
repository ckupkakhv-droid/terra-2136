"""Насос I коллектора: собственная процедурная геометрия, три LOD.

Запуск из корня репозитория:
  python3 tools/art/sewer_pump/pump_gen.py

Нужны numpy и gltfpack (переменная GLTFPACK или /tmp/terra-gltfpack).
Сторонние модели, текстуры и шрифты не читаются. Надпись — собственные штрихи.
Грязь и бетон в игре берутся из уже подключённого статического материала сцены.
"""
import hashlib
import json
import math
import os
import subprocess
import sys

import numpy as np

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
import meshlib
from meshlib import Mat, Mesh, beam, box, cyl, rotX, rotY, write_glb

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..', '..'))
OUT = os.path.join(ROOT, 'play', 'assets', 'sewer', 'pump', 'pump1.glb')
# Прежний примитив: box 1.4×1.3×1.2 от y=0.2 и сплюснутая сфера до y=1.76.
LIMIT = {'x': 0.70, 'y0': 0.20, 'y1': 1.76, 'z': 0.60}
SEG = {0: 12, 1: 8, 2: 5}

BODY = Mat('#567567', mt=6, var=.08, rust=.42, rustcol='#6a3a28', rustmt=9,
           streak=.28, dirt=.5, moss=.06, mossh=.55, seed=11)
BRASS = Mat('#b78745', mt=0, var=.05, rust=.2, rustcol='#6e4a32', rustmt=9,
            streak=.08, dirt=.16, seed=19)
PIPE = Mat('#4a5553', mt=9, var=.06, rust=.62, rustcol='#5c331f', rustmt=9,
           streak=.34, dirt=.38, seed=23)
PLATE = Mat('#e2b84a', mt=0, var=.03, streak=.16, dirt=.12, seed=31)
INK = Mat('#16110d', mt=0, var=.02, seed=37)
DARK = Mat('#2a2622', mt=6, var=.04, dirt=.35, rust=.15, rustmt=9, seed=41)


def rot_from_y(direction):
    y = np.asarray(direction, float)
    y = y / np.linalg.norm(y)
    up = np.array([0.0, 1.0, 0.0])
    c = float(np.clip(np.dot(up, y), -1, 1))
    if c > 0.9999:
        return np.eye(3)
    if c < -0.9999:
        return rotX(math.pi)
    axis = np.cross(up, y)
    axis = axis / np.linalg.norm(axis)
    s = math.sqrt(max(0.0, 1 - c * c))
    K = np.array([[0, -axis[2], axis[1]], [axis[2], 0, -axis[0]], [-axis[1], axis[0], 0]])
    return np.eye(3) + K * s + (K @ K) * (1 - c)


def pipe(p0, p1, radius, seg, mat, caps=True):
    p0 = np.asarray(p0, float)
    p1 = np.asarray(p1, float)
    length = float(np.linalg.norm(p1 - p0))
    mesh = cyl(radius, radius, 0, length, seg, mat, cap_bottom=caps, cap_top=caps)
    return mesh.xform(rot_from_y(p1 - p0), p0)


def octagon(hx, hz, chamfer):
    c = min(chamfer, hx * .45, hz * .45)
    return [(-hx + c, -hz), (hx - c, -hz), (hx, -hz + c), (hx, hz - c),
            (hx - c, hz), (-hx + c, hz), (-hx, hz - c), (-hx, -hz + c)]


def prism(profile, y0, y1, mat):
    mesh = Mesh()
    n = len(profile)
    cx = sum(p[0] for p in profile) / n
    cz = sum(p[1] for p in profile) / n
    for i in range(n):
        x0, z0 = profile[i]
        x1, z1 = profile[(i + 1) % n]
        mesh.quad([x0, y0, z0], [x1, y0, z1], [x1, y1, z1], [x0, y1, z0], mat)
        mesh.tri([cx, y1, cz], [x0, y1, z0], [x1, y1, z1], mat)
        mesh.tri([cx, y0, cz], [x1, y0, z1], [x0, y0, z0], mat)
    return mesh


def arc(cx, cy, radius, a0, a1, steps):
    pts = [(cx + radius * math.cos(a0 + (a1 - a0) * i / steps),
            cy + radius * math.sin(a0 + (a1 - a0) * i / steps)) for i in range(steps + 1)]
    return [(pts[i][0], pts[i][1], pts[i + 1][0], pts[i + 1][1]) for i in range(steps)]


GLYPH = {
    'Н': [(0.08, 0.06, 0.08, 0.94), (0.92, 0.06, 0.92, 0.94), (0.08, 0.50, 0.92, 0.50)],
    'А': [(0.06, 0.06, 0.50, 0.98), (0.94, 0.06, 0.50, 0.98), (0.22, 0.40, 0.78, 0.40)],
    'С': arc(0.58, 0.50, 0.40, math.radians(55), math.radians(305), 4),
    'О': arc(0.50, 0.50, 0.38, 0, math.tau, 6),
    'I': [(0.46, 0.06, 0.46, 0.94)],
}


def stroke(mesh, ax, ay, bx, by, z, width, mat):
    dx, dy = bx - ax, by - ay
    length = math.hypot(dx, dy) or 1
    px, py = -dy / length * width / 2, dx / length * width / 2
    # Лицо +Z до наклона таблички, иначе надпись смотрит в пол.
    mesh.quad([ax - px, ay - py, z], [bx - px, by - py, z],
              [bx + px, by + py, z], [ax + px, ay + py, z], mat)


def legend(level):
    """Табличка смотрит к камере (+Z, сверху). Буквы — штрихи, без шрифта."""
    mesh = Mesh()
    mesh.add(box((0, 0, 0), (0.96, 0.30, 0.016), PLATE))
    mesh.add(box((0, 0, -0.006), (1.00, 0.34, 0.008), DARK))
    if level < 2:
        text = 'НАСОС I'
        height = 0.20
        advance = 0.128
        width = 0.16 * height
        cursor = -0.42
        z = 0.010
        for ch in text:
            if ch == ' ':
                cursor += advance * .55
                continue
            for x0, y0, x1, y1 in GLYPH[ch]:
                stroke(mesh, cursor + x0 * advance, -height / 2 + y0 * height,
                       cursor + x1 * advance, -height / 2 + y1 * height, z, width, INK)
            cursor += advance
    # Наклон к камере: лицо таблички получает +Y и +Z.
    return mesh.xform(rotX(-0.62), (0.02, 1.02, 0.30))


def motor(level, seg):
    mesh = Mesh()
    mesh.add(cyl(0.20, 0.22, 1.08, 1.16, seg, DARK, cap_bottom=True))
    mesh.add(cyl(0.18, 0.18, 1.16, 1.50, seg, BRASS))
    mesh.add(cyl(0.10, 0.16, 1.50, 1.66, max(5, seg // 2), BRASS, cap_top=True))
    mesh.add(cyl(0.23, 0.23, 1.28, 1.31, seg, PIPE))
    if level == 0:
        mesh.add(cyl(0.05, 0.05, 1.66, 1.72, 6, DARK, cap_top=True))
    return mesh


def valve(level, seg):
    mesh = Mesh()
    hub = cyl(0.025, 0.025, 0, 0.04, max(6, seg // 2), BRASS, cap_top=True)
    rim = cyl(0.09, 0.09, 0.012, 0.02, seg, BRASS)
    mesh.add(hub).add(rim)
    spokes = 4 if level == 0 else 2
    for i in range(spokes):
        ang = math.tau * i / spokes
        mesh.add(beam((0, 0.016, 0), (math.cos(ang) * 0.08, 0.016, math.sin(ang) * 0.08), 0.012, DARK))
    return mesh.xform(rotY(-math.pi / 2), (0.50, 0.72, 0.02))


def gauge(seg):
    mesh = Mesh()
    mesh.add(cyl(0.028, 0.028, 0, 0.07, max(6, seg // 2), PIPE, cap_bottom=True))
    mesh.add(cyl(0.055, 0.055, 0.07, 0.082, seg, PLATE, cap_top=True))
    mesh.add(box((0.0, 0.086, 0.0), (0.006, 0.004, 0.04), INK))
    return mesh.xform(None, (0.30, 1.00, 0.12))


def build(level):
    seg = SEG[level]
    mesh = Mesh()
    mesh.add(prism(octagon(0.64, 0.52, 0.07), 0.20, 0.28, DARK))
    mesh.add(prism(octagon(0.46, 0.34, 0.05), 0.28, 1.04, BODY))
    mesh.add(motor(level, seg))
    mesh.add(legend(level))
    if level == 2:
        mesh.add(pipe((-0.02, 0.58, -0.56), (-0.02, 0.58, 0.56), 0.06, seg, PIPE))
    else:
        for x in (-0.16, 0.16):
            mesh.add(pipe((x, 0.62, -0.56), (x, 0.62, -0.34), 0.055, seg, PIPE))
            mesh.add(pipe((x, 0.62, 0.34), (x, 0.62, 0.56), 0.055, seg, PIPE))
            mesh.add(cyl(0.09, 0.09, 0.30, 0.36, seg, DARK).xform(rotX(math.pi / 2), (x, 0.62, 0)))
        mesh.add(valve(level, seg))
        for sx, sz in ((-0.48, -0.38), (0.48, -0.38), (-0.48, 0.38), (0.48, 0.38)):
            mesh.add(cyl(0.028, 0.028, 0.28, 0.33, 6, DARK, cap_top=True).xform(None, (sx, 0, sz)))
    if level == 0:
        mesh.add(gauge(seg))
        for y in (0.42, 0.58, 0.74, 0.90):
            mesh.add(box((0.47, y, 0), (0.02, 0.035, 0.46), DARK))
        mesh.add(pipe((0.16, 0.62, 0.50), (0.34, 0.78, 0.50), 0.04, 6, PIPE))
    return mesh


def bounds(mesh):
    P = np.array(mesh.P)
    return P.min(0), P.max(0)


def check(parts):
    ink = 0
    for name, mesh, _salt in parts:
        if not mesh.P:
            raise SystemExit(f'пустой меш {name}')
        lo, hi = bounds(mesh)
        if lo[0] < -LIMIT['x'] - 1e-3 or hi[0] > LIMIT['x'] + 1e-3:
            raise SystemExit(f'{name} вышел по X {lo[0]:.3f}..{hi[0]:.3f}')
        if lo[2] < -LIMIT['z'] - 1e-3 or hi[2] > LIMIT['z'] + 1e-3:
            raise SystemExit(f'{name} вышел по Z {lo[2]:.3f}..{hi[2]:.3f}')
        if lo[1] < LIMIT['y0'] - 1e-3 or hi[1] > LIMIT['y1'] + 1e-3:
            raise SystemExit(f'{name} вышел по Y {lo[1]:.3f}..{hi[1]:.3f}')
        if name.endswith('|lod0|s') and mesh.ntri > 2000:
            raise SystemExit(f'LOD0 {mesh.ntri} треугольников, предел 2000')
        if 'lod0' in name:
            ink += sum(1 for m in mesh.M if m is INK) // 3
            up = 0
            P = np.array(mesh.P)
            for k in range(0, len(mesh.P), 3):
                if mesh.M[k] is not INK:
                    continue
                a, b, c = P[k], P[k + 1], P[k + 2]
                normal = np.cross(b - a, c - a)
                up += normal[1]
            if up <= 0:
                raise SystemExit('штрихи таблички смотрят вниз')
    if ink < 8:
        raise SystemExit('на ближнем LOD нет штрихов таблички')
    counts = [mesh.ntri for name, mesh, _salt in parts]
    if not (counts[0] > counts[1] > counts[2] > 0):
        raise SystemExit(f'LOD не убывают: {counts}')


def gltfpack():
    env = os.environ.get('GLTFPACK')
    if env:
        return env
    local = os.path.expanduser('~/.local/bin/gltfpack')
    if os.path.isfile(local):
        return local
    cli = '/tmp/terra-gltfpack/node_modules/gltfpack/cli.js'
    if os.path.isfile(cli):
        return cli
    raise SystemExit('gltfpack не найден')


def main():
    parts = []
    for level, lod in ((0, 'lod0'), (1, 'lod1'), (2, 'lod2')):
        parts.append((f'pump1|{lod}|s', build(level), 0))
    check(parts)
    for name, mesh, _salt in parts:
        lo, hi = bounds(mesh)
        print(f'{name:16} {mesh.ntri:4} tris  '
              f'[{lo[0]:.2f},{lo[1]:.2f},{lo[2]:.2f}] [{hi[0]:.2f},{hi[1]:.2f},{hi[2]:.2f}]')
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    raw = OUT + '.raw.glb'
    write_glb(raw, parts, extras={'kit': 'sewer-pump-1', 'author': 'Команда «Терры»'})
    pack = gltfpack()
    cmd = ['node', pack, '-i', raw, '-o', OUT, '-cc', '-kn', '-km'] if pack.endswith('.js') else \
        [pack, '-i', raw, '-o', OUT, '-cc', '-kn', '-km']
    subprocess.run(cmd, check=True)
    os.remove(raw)
    raw_bytes = open(OUT, 'rb').read()
    counts = {name.split('|')[1]: mesh.ntri for name, mesh, _salt in parts}
    manifest = {
        'id': 'sewer_pump_1',
        'name': 'Насос I · аварийный агрегат коллектора',
        'file': 'pump/pump1.glb',
        'bytes': len(raw_bytes),
        'sha256': hashlib.sha256(raw_bytes).hexdigest(),
        'author': 'Команда «Терры»',
        'license': '© 2026 Команда «Терры». Все права защищены.',
        'source': 'tools/art/sewer_pump/pump_gen.py',
        'third_party': [],
        'plate': 'НАСОС I',
        'plate_note': 'Кириллица собрана из собственных прямых штрихов. Файла шрифта нет.',
        'materials': 'Отдельных текстур нет. В игре меш берёт статический материал сцены: vertex color, aux, mt и уже подключённые карты грязи.',
        'triangles': counts,
        'budget_lod0': 2000,
        'envelope_m': {'x': [-0.70, 0.70], 'y': [0.20, 1.76], 'z': [-0.60, 0.60]},
        'floor_local_y': 0.20,
        'lod_camera_m': [34, 52],
        'compression': ['EXT_meshopt_compression', 'KHR_mesh_quantization'],
        'nodes': ['pump1|lod0|s', 'pump1|lod1|s', 'pump1|lod2|s'],
    }
    manifest_path = os.path.join(os.path.dirname(OUT), 'manifest.json')
    with open(manifest_path, 'w', encoding='utf-8') as handle:
        json.dump(manifest, handle, ensure_ascii=False, indent=2)
        handle.write('\n')
    print('wrote', OUT, len(raw_bytes), manifest['sha256'])


if __name__ == '__main__':
    main()
