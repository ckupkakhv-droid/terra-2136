#!/usr/bin/env python3
"""Опора ЛЭП для песочницы Ie.prototype.lep.

Своя процедурная геометрия на tools/art/meshlib.py. Три LOD, группы s/dt,
COLOR_0 (линейный RGB, alpha = id поверхности TERRA_TEX), без UV и без проводов.
Провода, шаг 48 м и коллизия остаются в игре.

Запуск: python3 tools/art/lep_gen.py
Пишет play/assets/art/lep.glb. gltfpack не вызывается.
"""
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(__file__))
from meshlib import Mat, Mesh, beam, box, cyl, write_glb

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
OUT = os.path.join(ROOT, 'play/assets/art/lep.glb')
H = 15.0
LEG0, LEG1 = 1.4, 0.35
ARM_LO = (0.78 * H, 4.2)  # y=11.7, полуразмах 4.2
ARM_HI = (0.94 * H, 3.0)  # y=14.1, полуразмах 3.0

STEEL = Mat('#5a6066', 0, var=.10, rust=.55, rustcol='#6a3a20', streak=.45, seed=6)
STEEL_D = Mat('#3e4246', 0, var=.08, rust=.5, rustcol='#5a2e18', seed=7)
RUST = Mat('#6a3c24', 9, var=.18, rust=.3, rustcol='#4a2414', seed=8)
CONC = Mat('#6a665e', 6, var=.12, streak=.3, moss=.25, mossh=.8, seed=4)
INS = Mat('#8a9a9a', 0, var=.08, rust=.25, rustcol='#5a4a38', seed=16)


def leg_pt(t, sx, sz):
    span = LEG0 * (1 - t) + LEG1 * t
    return np.array([sx * span, t * H, sz * span], float)


def build(lod=0):
    s, dt = Mesh(), Mesh()
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    # Плиты 0.498 м: край ±1.499 при центрах ±1.25, внутри коллайдера ±1.5.
    # Мелкий мусор вокруг пят не ставится.
    for sx, sz in corners:
        s.add(box((sx * 1.25, 0.18, sz * 1.25), (0.498, 0.36, 0.498), CONC))
    segs = 6 if lod == 0 else (4 if lod == 1 else 2)
    w_leg = 0.16 if lod < 2 else 0.20
    for sx, sz in corners:
        for k in range(segs):
            t0, t1 = k / segs, (k + 1) / segs
            mat = STEEL if (int(t0 * 8) % 2 == 0) else STEEL_D
            s.add(beam(leg_pt(t0, sx, sz), leg_pt(t1, sx, sz), w_leg, mat))
    rings = 4 if lod == 0 else (3 if lod == 1 else 2)
    for h in range(1, rings + 1):
        t = h / (rings + 1)
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            dt.add(beam(leg_pt(t, *a), leg_pt(t, *b), 0.09 if lod else 0.10, STEEL_D if h % 2 else STEEL))
        if lod <= 1:
            for i in range(4):
                if lod == 1 and i % 2:
                    continue
                a, b = corners[i], corners[(i + 1) % 4]
                t0 = (h - 1) / (rings + 1)
                t1 = h / (rings + 1)
                dt.add(beam(leg_pt(t0, *a), leg_pt(t1, *b), 0.07, RUST if (h + i) % 3 == 0 else STEEL))
                dt.add(beam(leg_pt(t0, *b), leg_pt(t1, *a), 0.07, STEEL_D))
    for y, half in (ARM_LO, ARM_HI):
        s.add(beam((-half, y, 0), (half, y, 0), 0.22 if lod < 2 else 0.26, STEEL))
        if lod == 0:
            for x in (-half, half):
                dt.add(box((x, y, 0), (0.18, 0.28, 0.18), STEEL_D))
                dt.add(beam((x, y, 0), (x, y - 0.35, 0), 0.06, RUST))
        # Низ гирлянды = y-0.9, это точка провода. Цилиндр собран в нуле и сдвигается.
        for x in (-half, 0.0, half):
            if lod == 2:
                dt.add(cyl(0.16, 0.16, y - 0.9, y - 0.35, 6, INS, cap_top=True, cap_bottom=True).xform(t=(x, 0, 0)))
                dt.add(cyl(0.06, 0.06, y - 0.35, y - 0.05, 5, STEEL_D, cap_top=True).xform(t=(x, 0, 0)))
            elif lod == 1:
                dt.add(cyl(0.11, 0.14, y - 0.9, y - 0.55, 6, INS, cap_top=True).xform(t=(x, 0, 0)))
                dt.add(cyl(0.14, 0.11, y - 0.55, y - 0.15, 6, INS, cap_bottom=True).xform(t=(x, 0, 0)))
            else:
                for k, (r0, r1, y0, y1) in enumerate([
                    (0.08, 0.16, y - 0.90, y - 0.72),
                    (0.16, 0.10, y - 0.72, y - 0.55),
                    (0.10, 0.17, y - 0.55, y - 0.38),
                    (0.17, 0.09, y - 0.38, y - 0.18),
                    (0.06, 0.06, y - 0.18, y - 0.05),
                ]):
                    dt.add(cyl(r0, r1, y0, y1, 8, INS if k % 2 == 0 else STEEL_D,
                               cap_top=True, cap_bottom=True).xform(t=(x, 0, 0)))
    if lod <= 1:
        s.add(beam((0, H - 0.35, 0), (0, H, 0), 0.08, STEEL_D))
    return {'s': s, 'dt': dt}


def main():
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    parts, stats = [], {}
    for lod in (0, 1, 2):
        built = build(lod)
        for name, mesh in built.items():
            if mesh.P:
                parts.append((f'lep|lod{lod}|{name}', mesh, lod * 17))
                stats[f'lep|lod{lod}'] = stats.get(f'lep|lod{lod}', 0) + mesh.ntri
    write_glb(OUT, parts, extras={
        'kind': 'lep',
        'H': H,
        'collision': {'x0': -1.5, 'z0': -1.5, 'x1': 1.5, 'z1': 1.5, 'h': 2},
        'top_local': [[-4.2, 10.8, 0], [4.2, 10.8, 0], [3.0, 13.2, 0]],
        'wires': 'lepLine',
        'uv': 'none; chunk batch writes 0.001/0.999, TERRA_TEX is triplanar',
        'COLOR_0_a': 'surface id, not opacity',
        'tris': stats,
        'origin': 'TERRA procedural, no third-party mesh',
    })
    for key, count in sorted(stats.items()):
        print(f'{key:16} {count:6} tris')
    print('wrote', OUT, os.path.getsize(OUT))


if __name__ == '__main__':
    main()
