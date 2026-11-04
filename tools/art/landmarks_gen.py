"""Generates play/assets/art/landmarks.glb (meshopt + quantization via gltfpack).
Run: python3 tools/art/landmarks_gen.py   (needs numpy and gltfpack: npm i -g gltfpack@1.3.0)
All geometry is original work of the TERRA team (procedural), no third-party meshes.
Local frames (metres, +z = south/front, y = up from the landmark's ground level) match the
primitive layout of Ie.prototype.landmark so colliders/containers stay where they were."""
import math, sys, os
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
from meshlib import *
from meshlib import two_sided

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SRC = os.path.join(__import__('tempfile').gettempdir(), 'terra-art', 'landmarks.src.glb')
OUT = os.path.join(ROOT, 'play/assets/art/landmarks.glb')
TAU = 2 * math.pi

# ---- shared materials ----
BRICK = Mat('#7a4232', 8, var=.16, streak=.55, moss=.55, mossh=2.6, dirt=.35, seed=1)
BRICK_D = Mat('#5a3022', 8, var=.12, streak=.4, moss=.4, seed=2)
CONC = Mat('#8a857a', 6, var=.14, streak=.5, moss=.45, mossh=1.4, seed=3)
CONC_D = Mat('#6a665e', 6, var=.12, streak=.4, moss=.3, seed=4)
PLASTER = Mat('#cfc8b8', 6, var=.10, streak=.75, moss=.35, mossh=2.0, dirt=.3, seed=5)
STEEL = Mat('#5a6066', 0, var=.10, rust=.55, rustcol='#6a3a20', streak=.45, seed=6)
STEEL_D = Mat('#3e4246', 0, var=.08, rust=.5, rustcol='#5a2e18', seed=7)
RUST = Mat('#6a3c24', 9, var=.18, rust=.3, rustcol='#4a2414', seed=8)
GOLD = Mat('#b8923a', 0, var=.10, rust=.38, rustcol='#4f5a3e', rustmt=9, streak=.25, seed=9)
PATINA = Mat('#3a6a5a', 0, var=.12, rust=.25, rustcol='#2a3a30', streak=.2, seed=10)
GLASS = Mat('#101418', 0, var=.05, dirt=0, seed=11)
GLASS_B = Mat('#24323c', 0, var=.12, dirt=0, seed=12)
WOOD = Mat('#5a4630', 10, var=.18, moss=.3, mossh=.8, seed=13)
WOOD_D = Mat('#3e3024', 10, var=.15, moss=.3, mossh=.8, seed=14)
FRAME = Mat('#b6b0a0', 0, var=.1, rust=.2, rustcol='#6a5a44', streak=.3, seed=15)
REDP = Mat('#9a3a2a', 0, var=.12, rust=.45, rustcol='#5a2a18', streak=.3, seed=16)
WHITEP = Mat('#d8d6cc', 0, var=.1, rust=.45, rustcol='#6a4a30', streak=.3, seed=17)
LEAF = Mat('#4a6a2a', 0, var=.25, dirt=0, seed=18)
LEAF_Y = Mat('#6a7a32', 0, var=.25, dirt=0, seed=19)
BARK = Mat('#d8d4c8', 0, var=.2, dirt=.1, seed=20)
ASPH = Mat('#3a3c3e', 5, var=.18, moss=.35, mossh=.3, dirt=0, seed=21)
GRASS = Mat('#2e4a24', 1, var=.25, dirt=0, seed=22)
DIRTM = Mat('#5a4a36', 2, var=.2, dirt=0, seed=23)
LINE = Mat('#a8a698', 0, var=.2, dirt=0, seed=24)
SEAT_R = Mat('#8a3a30', 0, var=.2, rust=.2, rustcol='#4a3a30', seed=25)
SEAT_B = Mat('#3a5a7a', 0, var=.2, rust=.2, rustcol='#3a3a38', seed=26)
SEAT_Y = Mat('#a8903a', 0, var=.2, rust=.2, rustcol='#4a4030', seed=27)
LAMP = Mat('#d8d0a0', 0, var=.1, dirt=0, seed=28)
GLOW_R = Mat('#ff3a2a', 0, var=0, dirt=0, seed=29)
GLOW_RD = Mat('#c02418', 0, var=.1, dirt=0, seed=30)
SOOT = Mat('#1c1a18', 0, var=.1, dirt=0, seed=31)

def ivy(m, x0, x1, y1, z, nrm=1, seed=0, q=1.0, mat=LEAF):
    """clump of ivy leaves climbing a wall plane z (normal +z if nrm>0)."""
    n = int(max(2, (x1 - x0) * y1 * 0.9 * q))
    for k in range(n):
        u = hash1(seed, k, 1); v = hash1(seed, k, 2) ** 1.6
        x = x0 + (x1 - x0) * u; y = 0.2 + y1 * v * (1 - 0.6 * abs(u - .5))
        m.add(blob((x, y, z + nrm * 0.12), 0.35 + 0.25 * hash1(seed, k, 3), mat if k % 3 else LEAF_Y, (1, 0.8, 0.35), seed=k))

def sapling(m, f, x, y, z, h=2.2, seed=0):
    """young birch growing out of masonry (trunk -> s, leaves -> f)."""
    lean = (hash1(seed, 1) - .5) * .5
    top = (x + lean, y + h, z + (hash1(seed, 2) - .5) * .4)
    m.add(beam((x, y, z), top, .09, BARK))
    for k in range(4):
        c = (top[0] + (hash1(seed, k, 4) - .5) * .9, top[1] - .2 - .5 * hash1(seed, k, 5), top[2] + (hash1(seed, k, 6) - .5) * .9)
        f.add(blob(c, .55, LEAF if k % 2 else LEAF_Y, (1, .8, 1), seed=k + seed))

# ================= WATER TOWER =================
def water_tower(q):
    s, dt, f = Mesh(), Mesh(), Mesh(); seg = 18 if q > .7 else 10
    s.add(cyl(1.45, 1.4, 0, .55, seg, CONC_D, cap_top=True))
    s.add(cyl(1.15, 1.02, .55, 13.2, seg, BRICK, rings=8 if q > .7 else 3))
    for y in (3.4, 6.8, 10.2):  # corbelled brick bands
        s.add(cyl(1.2, 1.18, y, y + .28, seg, BRICK_D, cap_top=True, cap_bottom=True))
    # door + slit windows on the south (+z) side
    s.add(box((0, 1.05, 1.08), (.95, 2.0, .12), SOOT))
    s.add(box((.12, 1.0, 1.2), (.85, 1.9, .06), RUST, R=rotY(.5)))  # door ajar
    for y in (4.6, 8.0, 11.4):
        s.add(box((0, y, 1.06), (.32, .9, .1), SOOT)); s.add(box((0, y - .5, 1.1), (.5, .08, .16), CONC))
        s.add(box((-1.02, y + 1.7, 0), (.1, .8, .3), SOOT))
    # concrete corbel ring under the tank
    s.add(lathe([(1.02, 13.2), (1.5, 13.6), (2.6, 14.1), (3.0, 14.35), (3.0, 14.5)], seg, CONC, smooth=False))
    # tank
    s.add(cyl(3.2, 3.2, 14.5, 17.7, seg + 6, STEEL, rings=4 if q > .7 else 1))
    s.add(cyl(3.24, 3.24, 15.6, 15.75, seg + 6, STEEL_D)); s.add(cyl(3.24, 3.24, 16.7, 16.85, seg + 6, STEEL_D))
    if q > .7:
        for k in range(16):
            a = TAU * k / 16; dt.add(box((3.23 * math.sin(a), 16.1, 3.23 * math.cos(a)), (.08, 3.15, .06), STEEL_D, R=rotY(a)))
    # catwalk with damaged railing
    s.add(lathe([(3.2, 14.42), (3.95, 14.42), (3.95, 14.5), (3.2, 14.5)], seg + 6, RUST, smooth=False))
    n = 24 if q > .7 else 12
    for k in range(n):
        a0, a1 = TAU * k / n, TAU * (k + 1) / n
        if hash1(k, 7) < .18: continue
        p0 = (3.9 * math.sin(a0), 14.5, 3.9 * math.cos(a0)); dt.add(beam(p0, (p0[0], 15.55, p0[2]), .06, RUST))
        sag = .25 if hash1(k, 9) < .2 else 0
        dt.add(beam((p0[0], 15.55, p0[2]), (3.9 * math.sin(a1), 15.55 - sag, 3.9 * math.cos(a1)), .06, RUST))
    # roof: cone with a rusted-through hole + vent cap
    def hole(i, j): return (seg + 6) * .1 < i < (seg + 6) * .26 and j == 1
    s.add(lathe([(3.45, 17.7), (2.0, 18.5), (.35, 19.25)], seg + 6, RUST, smooth=False, skipfn=hole))
    s.add(cyl(.35, .35, 19.25, 19.6, 8, STEEL_D)); s.add(lathe([(.6, 19.6), (.0, 19.9)], 8, STEEL_D, smooth=False))
    # ladder (south-west), cage hoops on the upper half
    lx, lz = -.55, 1.18
    for x in (lx - .22, lx + .22): dt.add(beam((x, .55, lz), (x, 14.42, lz), .05, RUST))
    for k in range(int(23 * q) + 1):
        y = .9 + k * (13.4 / (int(23 * q) + 1)); dt.add(beam((lx - .22, y, lz), (lx + .22, y, lz), .04, RUST))
    if q > .7:
        for y in (8.5, 10.5, 12.5):
            for k in range(6):
                a0, a1 = math.pi * k / 6, math.pi * (k + 1) / 6
                dt.add(beam((lx - .35 * math.cos(a0), y, lz + .35 * math.sin(a0)), (lx - .35 * math.cos(a1), y, lz + .35 * math.sin(a1)), .04, RUST))
    # drain pipe from tank (original pipe position x=+3)
    dt.add(beam((2.9, 14.45, 0), (1.25, 13.0, 0), .16, STEEL_D)); dt.add(beam((1.25, 13.0, 0), (1.25, .5, 0), .16, STEEL_D))
    # fallen bricks + overgrowth at the base
    for k in range(int(14 * q)):
        a = TAU * hash1(k, 11); r = 1.6 + 1.4 * hash1(k, 12)
        dt.add(box((r * math.sin(a), .1, r * math.cos(a)), (.25, .12, .12), BRICK_D, R=rotY(hash1(k, 13) * 3)))
    ivy(f, -1.0, -.3, 4.5, 1.0, seed=3, q=q); ivy(f, .5, 1.0, 3.0, 1.0, seed=4, q=q)
    sapling(s, f, .6, 13.25, -.75, 1.8, seed=5)
    return {'s': s, 'dt': dt, 'f': f}

# ================= CHURCH (top + bell turrets on the existing nave) =================
def onion(y0, r, h, seg, mat):
    prof = [(r * .82, y0), (r * 1.0, y0 + h * .18), (r * 1.06, y0 + h * .32), (r * .96, y0 + h * .48), (r * .7, y0 + h * .64),
            (r * .38, y0 + h * .8), (r * .14, y0 + h * .92), (r * .05, y0 + h)]
    return lathe(prof, seg, mat, smooth=True)

def orth_cross(c, sc, mat, tilt=0.0):
    m = Mesh(); x, y, z = c
    m.add(box((0, .9, 0), (.09, 1.8, .09), mat)); m.add(box((0, 1.25, 0), (.9, .09, .09), mat))
    m.add(box((0, 1.55, 0), (.45, .07, .07), mat)); m.add(box((0, .55, 0), (.55, .07, .07), mat, R=rotZ(-.35)))
    return m.xform(rotZ(tilt) @ rotX(tilt * .5), (x, y, z), sc)

def church_top(q, side_cols=('#c8a040', '#c8a040')):
    s, dt, f, g = Mesh(), Mesh(), Mesh(), Mesh(); seg = 16 if q > .7 else 10
    y0 = 6.3
    s.add(box((0, y0 + 1.5, 0), (6, 3, 6), PLASTER, sub=(3, 2, 3) if q > .7 else (1, 1, 1)))
    s.add(box((0, y0 + 3.1, 0), (6.4, .2, 6.4), CONC_D))  # cornice
    for sx in (-1, 1):
        for sz in (-1, 1): s.add(box((sx * 2.85, y0 + 1.5, sz * 2.85), (.5, 3, .5), PLASTER))  # pilasters
    # kokoshniks: half-round gables, 2 per side
    for side in range(4):
        R = rotY(side * math.pi / 2)
        for xo in (-1.4, 1.4):
            k = Mesh()
            prof = [(1.25 * math.cos(t), 1.25 * math.sin(t)) for t in np.linspace(0, math.pi, 7 if q > .7 else 4)]
            for (ax, ay), (bx, by) in zip(prof[:-1], prof[1:]):
                k.quad((ax, ay, .2), (bx, by, .2), (bx, by, -.2), (ax, ay, -.2), PLASTER)
                k.tri((0, 0, .2), (ax, ay, .2), (bx, by, .2), PLASTER)
            two_sided(k); k.xform(None, (xo, y0 + 3.2, 3.0)); s.add(k.xform(R))
    # drum with arched windows
    s.add(cyl(1.55, 1.5, y0 + 3.2, y0 + 5.4, 8, PLASTER, rings=2))
    for k in range(8):
        a = TAU * (k + .5) / 8
        s.add(box((1.47 * math.sin(a), y0 + 4.2, 1.47 * math.cos(a)), (.36, 1.1, .1), SOOT, R=rotY(a)))
    s.add(cyl(1.7, 1.7, y0 + 5.4, y0 + 5.6, 8, CONC_D, cap_bottom=True))
    # main onion dome (gilding peeled -> patina/rust patches) with a breach
    dome = onion(y0 + 5.6, 1.85, 3.9, seg, GOLD)
    s.add(dome)
    s.add(cyl(.18, .14, y0 + 9.4, y0 + 9.9, 6, GOLD))
    s.add(orth_cross((0, y0 + 9.85, 0), 1.0, GOLD, tilt=.09))
    # side bell turrets on the north corners (original positions o±4, a-6)
    for i, sx in enumerate((-4, 4)):
        col = side_cols[i]; dm = GOLD if col.lower() == '#c8a040' else PATINA
        s.add(cyl(.82, .8, y0, y0 + 2.7, 8, PLASTER, rings=1))
        for k in range(4):
            a = TAU * k / 4 + math.pi / 4
            s.add(box((sx + .78 * math.sin(a), y0 + 1.9, -6 + .78 * math.cos(a)), (.3, .8, .08), SOOT, R=rotY(a)))
        s.add(cyl(.95, .95, y0 + 2.7, y0 + 2.85, 8, CONC_D, cap_bottom=True))
        d = onion(y0 + 2.85, .95, 2.1, seg, dm); d.xform(t=(sx, 0, -6)); s.add(d)
        s.add(orth_cross((sx, y0 + 4.9, -6), .6, dm, tilt=-.12 if sx < 0 else .2))
    # birch growing from the cornice, ivy on the drum base
    sapling(s, f, 2.6, y0 + 3.2, 2.6, 2.4, seed=21)
    if q > .7: sapling(s, f, -4.4, y0 + 2.85, -5.6, 1.4, seed=22)
    ivy(f, -2.8, 2.8, 1.8, 3.0, seed=23, q=q * .7)
    return {'s': s, 'dt': dt, 'f': f, 'g': g}

def grave_cross(q, var=0):
    s = Mesh(); mat = WOOD if var % 3 else RUST
    s.add(box((0, .65, 0), (.09, 1.3, .09), mat)); s.add(box((0, .98, 0), (.62, .08, .08), mat))
    s.add(box((0, 1.17, 0), (.32, .06, .06), mat)); s.add(box((0, .45, 0), (.38, .06, .06), mat, R=rotZ(-.4)))
    if var % 2 == 0:  # "golubets" roof
        s.add(box((-.12, 1.36, 0), (.3, .05, .2), WOOD_D, R=rotZ(.6))); s.add(box((.12, 1.36, 0), (.3, .05, .2), WOOD_D, R=rotZ(-.6)))
    s.add(box((0, .06, .35), (.5, .12, .8), DIRTM))  # grave mound
    return {'s': s}

# ================= SCHOOL / HOSPITAL facade (front = +z, wall face at z=+0.25) =================
def facade(q, floors, height, wallmat, hospital=False):
    s, dt, f, g = Mesh(), Mesh(), Mesh(), Mesh(); W = 30; z = .25
    for m_ in range(floors):
        for gi in range(9):
            x = -13.2 + gi * 3.3; y = m_ * 3 + 1
            if m_ == 0 and gi == 4: continue  # entrance
            hsh = hash1(m_, gi, 31 + hospital)
            kind = 'board' if hsh < .18 else 'empty' if hsh < .42 else 'glass'
            s.add(box((x, y + .7, z + .02), (1.8, 1.4, .04), GLASS if kind != 'glass' else GLASS_B))
            if kind == 'board':
                for k in range(3): dt.add(box((x, y + .3 + k * .42, z + .1), (1.95, .28, .05), WOOD if k % 2 else WOOD_D, R=rotZ((hash1(k, gi, m_) - .5) * .25)))
            else:
                fr = FRAME
                for xx in (x - .9, x + .9, x - .3, x + .3):
                    if kind == 'empty' and abs(xx - x) < .5 and hash1(xx, y) < .6: continue
                    dt.add(box((xx, y + .7, z + .07), (.07, 1.4, .07), fr))
                for yy in (y, y + 1.4, y + 1.0): dt.add(box((x, yy, z + .07), (1.86, .07, .07), fr))
            s.add(box((x, y - .06, z + .12), (2.0, .1, .24), CONC))  # sill
        if m_ > 0: s.add(box((0, m_ * 3 - .1, z + .08), (W + .2, .2, .16), CONC_D, sub=(6, 1, 1)))
    s.add(box((0, (2.9 + height - .9) / 2, 0), (3, height - .9 - 2.9, .5), wallmat, sub=(1, 2, 1)))  # infill above door
    for k in range(1, floors):
        y = k * 3 + 1; s.add(box((0, y + .7, z + .02), (1.8, 1.4, .04), GLASS_B))
        for xx in (-.9, .9, 0): dt.add(box((xx, y + .7, z + .07), (.07, 1.4, .07), FRAME))
    # entrance: canopy on two posts, steps, door leaves
    s.add(box((0, 3.0, z + .9), (4.4, .22, 1.8), CONC_D)); [s.add(box((sx, 1.45, z + 1.6), (.22, 2.9, .22), CONC)) for sx in (-1.9, 1.9)]
    s.add(box((0, .08, z + 1.1), (3.6, .16, 1.4), CONC)); s.add(box((0, .2, z + .7), (3.4, .12, .7), CONC))
    dt.add(box((-1.05, 1.25, -.05), (.95, 2.5, .06), RUST, R=rotY(-.9))); dt.add(box((.9, 1.25, .05), (.9, 2.5, .06), RUST, R=rotY(.25)))
    # drainpipes, soot above some windows, roof parapet & clutter
    for x in (-14.7, 14.7): dt.add(beam((x, 0, z + .14), (x, height + .2, z + .14), .14, STEEL_D))
    s.add(box((0, height + .58, .18), (30.6, .55, .25), CONC_D, sub=(8, 1, 1)))
    for sx in (-1, 1): s.add(box((sx * 15.18, height + .58, -5), (.25, .55, 10.6), CONC_D, sub=(1, 1, 3)))
    s.add(box((0, height + .58, -10.18), (30.6, .55, .25), CONC_D, sub=(8, 1, 1)))
    s.add(box((-8, height + 1.5, -6), (4, 2.4, 3), CONC_D))  # lift machine room
    dt.add(box((-8, height + 1.4, -4.48), (.9, 1.9, .05), RUST))
    for k, (x, zz) in enumerate([(6, -3), (9, -7), (2, -8)]):
        dt.add(cyl(.22, .22, height + .3, height + 1.3, 6, STEEL_D).xform(t=(x, 0, zz)))
    for k in range(int(10 * q)):  # bitumen patches + moss on the roof slab
        x = -14 + 28 * hash1(k, 41); zz = -9.6 + 9.2 * hash1(k, 42)
        dt.add(box((x, height + .31, zz), (1 + 2 * hash1(k, 43), .02, .8 + 1.5 * hash1(k, 44)), SOOT if k % 2 else Mat('#4a5a2a', 3, seed=k)))
    sapling(s, f, 12.5, height + .3, -1.2, 2.0, seed=51 + hospital)
    ivy(f, -15, -10, height * .75, z, seed=52 + hospital, q=q * .8); ivy(f, 9.5, 15, height * .5, z, seed=53 + hospital, q=q * .8)
    return {'s': s, 'dt': dt, 'f': f, 'g': g}

def hospital_cross(q):
    s, g = Mesh(), Mesh()
    for (w, h) in ((2.6, .9), (.9, 2.6)):
        s.add(box((0, 0, -.06), (w + .16, h + .16, .1), STEEL_D))
    # glowing panels: horizontal intact, vertical arm half-broken
    g.add(box((0, 0, .02), (2.4, .7, .06), GLOW_R))
    g.add(box((0, .75, .02), (.7, .9, .06), GLOW_R)); g.add(box((0, -.75, .02), (.7, .9, .06), GLOW_RD))
    s.add(beam((-.9, -1.3, -.1), (-1.1, -2.3, -.4), .08, RUST)); s.add(beam((.9, -1.3, -.1), (1.1, -2.3, -.4), .08, RUST))
    return {'s': s, 'g': g}

def school_yard(q):
    s, dt, f = Mesh(), Mesh(), Mesh()
    s.add(box((0, -.6 + .03, 0), (18, 1.26, 12), ASPH, sub=(6 if q > .7 else 2, 1, 4 if q > .7 else 1), skip=('-y',)))
    for k in range(int(9 * q)):  # cracks with weeds
        x = -8 + 16 * hash1(k, 61); zz = -5 + 10 * hash1(k, 62); a = hash1(k, 63) * 3
        dt.add(box((x, .045, zz), (2.5 + 2 * hash1(k, 64), .01, .07), SOOT, R=rotY(a)))
        f.add(blob((x, .12, zz), .3, LEAF, (1, .5, 1), seed=k))
    for sx in (-1, 1):  # rusty football goals at x=+-8 (posts .15, 2.4 high, bar along z 3 m)
        x = sx * 8
        for zz in (-1.45, 1.45): s.add(box((x, 1.2, zz), (.14, 2.4, .14), RUST))
        s.add(box((x, 2.33, 0), (.14, .14, 3.05), RUST, R=rotX(.04 * sx)))
        for zz in (-1.45, 1.45): dt.add(beam((x, 2.3, zz), (x + sx * 1.1, 0, zz), .06, RUST))
        if q > .7:
            for k in range(5): dt.add(beam((x, 2.3, -1.2 + k * .6), (x + sx * (.6 + .4 * hash1(k, sx)), .9 + .6 * hash1(k, 3), -1.2 + k * .6), .02, FRAME))
    return {'s': s, 'dt': dt, 'f': f}

# ================= STADIUM (n = Ct - v1 - 2 = 38: landmark interior) =================
def stadium(q, n=38):
    s, dt, f, g = Mesh(), Mesh(), Mesh(), Mesh(); L = n - 6; FX, FZ = (n - 12) / 2, (n - 16) / 2
    sub = (10, 1, 8) if q > .7 else (4, 1, 3)
    pitch = box((0, -.6 + .03, 0), (n - 12, 1.26, n - 16), GRASS, sub=sub, skip=('-y',))
    s.add(pitch)
    # worn dirt patches: goal mouths, centre circle and random bald spots (irregular flat discs)
    spots = [(sx * (FX - 1.8), 0, 2.6, 2.0) for sx in (-1, 1)] + [(0, 0, 2.2, 2.2)]
    spots += [(-FX + 3 + (2 * FX - 6) * hash1(k, 77), -FZ + 2 + (2 * FZ - 4) * hash1(k, 78), 1 + 1.6 * hash1(k, 79), 1 + 1.2 * hash1(k, 80)) for k in range(int(7 * q) + 2)]
    for k, (x, zz, rx, rz) in enumerate(spots):
        segs = 10 if q > .7 else 7
        pts = [(x + rx * (.7 + .3 * hash1(k, j, 81)) * math.cos(TAU * j / segs), zz + rz * (.7 + .3 * hash1(k, j, 82)) * math.sin(TAU * j / segs)) for j in range(segs)]
        for j in range(segs):
            (ax, az), (bx, bz) = pts[j], pts[(j + 1) % segs]
            dt.tri((x, .062, zz), (bx, .062, bz), (ax, .062, az), DIRTM)
    lw = .1; y = .04  # faded lines
    for zz in (-FZ + .3, FZ - .3): dt.add(box((0, y, zz), (2 * FX - .6, .01, lw), LINE))
    for xx in (-FX + .3, FX - .3, 0): dt.add(box((xx, y, 0), (lw, .01, 2 * FZ - .6), LINE))
    for k in range(16 if q > .7 else 8):
        a0, a1 = TAU * k / (16 if q > .7 else 8), TAU * (k + 1) / (16 if q > .7 else 8)
        if hash1(k, 71) < .25: continue
        dt.add(beam((2.2 * math.sin(a0), y, 2.2 * math.cos(a0)), (2.2 * math.sin(a1), y, 2.2 * math.cos(a1)), lw, LINE, h=.01))
    for sx in (-1, 1):
        for zz in (-3, 3): dt.add(box((sx * (FX - 1.6), y, zz), (2.6, .01, lw), LINE))
        dt.add(box((sx * (FX - 2.9), y, 0), (lw, .01, 6), LINE))
    # goals at x = +-(n/2-9), 7 m wide (z), 2.4 m high
    for sx in (-1, 1):
        x = sx * (n / 2 - 9)
        for zz in (-3.5, 3.5): s.add(box((x, 1.2, zz), (.14, 2.4, .14), WHITEP))
        s.add(box((x, 2.35, 0), (.14, .14, 7.1), WHITEP, R=rotX(-.03 * sx)))
        for zz in (-3.5, 3.5): dt.add(beam((x, 2.35, zz), (x + sx * 1.4, 0, zz), .07, RUST))
        dt.add(beam((x + sx * 1.4, .05, -3.5), (x + sx * 1.4, .05, 3.5), .07, RUST))
        if q > .7:
            for k in range(8): dt.add(beam((x, 2.3, -3.2 + k * .9), (x + sx * (.8 + .5 * hash1(k, sx, 5)), .4 + .9 * hash1(k, 6), -3.2 + k * .9 + .2), .02, FRAME))
    # stands on both long sides: 6 tiers rising outward from z=n/2-7 to n/2-1 (collider band n/2-5..n/2-1)
    for side in (-1, 1):
        for t in range(6):
            z0, z1 = n / 2 - 7 + t, n / 2 - 6 + t; h = .45 + .42 * t; zc = side * (z0 + z1) / 2
            s.add(box((0, h / 2 - .3, zc), (L, h + .6, 1.0), CONC, sub=(8 if q > .7 else 3, 1, 1), skip=('-y',)))
            if q > .7:
                xs = -L / 2 + .6
                while xs < L / 2 - .6:
                    ln = 1.2 + 3.5 * hash1(xs, t, side); ln = min(ln, L / 2 - .6 - xs)
                    if hash1(xs, t, side, 2) > .28:
                        mat = (SEAT_R, SEAT_B, SEAT_Y)[int(hash1(t, side, 9) * 3)] if hash1(xs, t, 4) > .2 else SEAT_Y
                        s.add(box((xs + ln / 2, h + .18, zc - side * .1), (ln, .36, .45), mat))
                        s.add(box((xs + ln / 2, h + .42, zc + side * .18), (ln, .5, .08), mat))
                    xs += ln + .2 + 1.2 * hash1(xs, t, 7)
        s.add(box((0, 1.6, side * (n / 2 - .8)), (L, 3.2, .4), CONC_D, sub=(8, 1, 1)))  # back wall
        for k in range(int(L / 2)):  # front railing, some posts missing
            x = -L / 2 + 1 + k * 2
            if hash1(k, side, 81) < .2: continue
            dt.add(beam((x, 0, side * (n / 2 - 7.15)), (x, 1.0, side * (n / 2 - 7.15)), .06, RUST))
            if hash1(k, side, 82) > .25: dt.add(beam((x, 1.0, side * (n / 2 - 7.15)), (x + 2, 1.0 - (.4 if hash1(k, 83) < .15 else 0), side * (n / 2 - 7.15)), .05, RUST))
        # floodlight masts on the stand ends (inside the stand collider)
        for sx in (-1, 1):
            bx, bz = sx * (L / 2 - .7), side * (n / 2 - 1.8)
            s.add(cyl(.32, .16, 0, 15, 6, STEEL, rings=3).xform(t=(bx, 0, bz)))
            fr = Mesh(); fr.add(box((0, 15.6, 0), (2.6, 1.4, .2), STEEL_D))
            for i in range(4):
                for j in range(2):
                    if hash1(i, j, sx, side) < .3: fr.add(box((-.95 + i * .63, 15.25 + j * .7, -side * .14), (.5, .5, .06), SOOT))
                    else: fr.add(box((-.95 + i * .63, 15.25 + j * .7, -side * .14), (.5, .5, .06), LAMP))
            fr.xform(rotX(side * .35), (bx, 0, bz)); s.add(fr)
    ivy(f, -L / 2, -L / 2 + 6, 2.6, n / 2 - .6, seed=91, q=q); ivy(f, L / 2 - 5, L / 2, 2.2, -(n / 2 - .6), nrm=-1, seed=92, q=q)
    for k in range(int(10 * q)):
        f.add(blob((-FX + 2 * FX * hash1(k, 93), .15, -FZ + 2 * FZ * hash1(k, 94)), .4 + .3 * hash1(k, 95), LEAF, (1, .6, 1), seed=k))
    return {'s': s, 'dt': dt, 'f': f, 'g': g}

# ================= TV TOWER =================
def tv_tower(q):
    s, dt, f, g = Mesh(), Mesh(), Mesh(), Mesh(); H = 34; lv = 8
    leg = lambda t, sx, sz: np.array([sx * 2.4 * (1 - t * .85), t * H, sz * 2.4 * (1 - t * .85)])
    band = lambda t: REDP if int(t * 8) % 2 == 0 else WHITEP
    corners = [(-1, -1), (1, -1), (1, 1), (-1, 1)]
    for sx, sz in corners:
        for k in range(lv):
            t0, t1 = k / lv, (k + 1) / lv; s.add(beam(leg(t0, sx, sz), leg(t1, sx, sz), .26, band(t0)))
        s.add(box((sx * 2.4, .3, sz * 2.4), (.9, .6, .9), CONC_D))
    for k in range(1, lv + 1):
        t = k / lv
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            dt.add(beam(leg(t, *a), leg(t, *b), .12, band(t - .01)))
    for k in range(lv):
        t0, t1 = k / lv, (k + 1) / lv
        for i in range(4):
            if q < .7 and i in (0, 1): continue
            a, b = corners[i], corners[(i + 1) % 4]
            if hash1(k, i, 101) < .08: continue  # missing brace
            dt.add(beam(leg(t0, *a), leg(t1, *b), .09, band(t0))); dt.add(beam(leg(t0, *b), leg(t1, *a), .09, band(t0)))
    for t in (3 / 8, 6 / 8):  # service platforms with railing and antenna panels
        w = 2.4 * (1 - t * .85) + .7; y = t * H
        s.add(box((0, y, 0), (2 * w, .1, 2 * w), STEEL_D))
        for i in range(4):
            a, b = corners[i], corners[(i + 1) % 4]
            pa, pb = np.array([a[0] * w, y + 1, a[1] * w]), np.array([b[0] * w, y + 1, b[1] * w])
            dt.add(beam(pa, pb, .05, RUST)); dt.add(beam(pa - (0, 1, 0), pa, .05, RUST))
        for i, (ax, az) in enumerate(corners):
            if hash1(t, i) < .25: continue
            s.add(box((ax * (w - .2), y + 1.3, az * (w - .2)), (.35, 1.9, .15), WHITEP, R=rotY(math.atan2(ax, az))))
    # dishes: one hanging loose
    for i, (t, ang, tilt) in enumerate([(6 / 8, .6, .1), (6 / 8, 2.6, .9), (3 / 8, 4.2, .2)]):
        w = 2.4 * (1 - t * .85) + .8; c = np.array([math.sin(ang) * w, t * H + .9, math.cos(ang) * w])
        d = lathe([(0, 0), (.55, .18), (.8, .4)], 10 if q > .7 else 6, WHITEP, smooth=False)
        d.xform(rotY(ang) @ rotX(math.pi / 2 - tilt), c); s.add(d)
    # top: lamp housing (glow) + mast + lightning rod
    s.add(box((0, H, 0), (1.0, .3, 1.0), STEEL_D))
    g.add(blob((0, H + .4, 0), .32, GLOW_R, seed=3))
    s.add(beam((0, H + .2, 0), (0, H + 4, 0), .14, REDP)); s.add(beam((0, H + 4, 0), (0, H + 5.2, 0), .04, STEEL_D))
    g.add(blob((0, H + 3.2, 0), .16, GLOW_R, seed=4))
    # ladder along the south face (inside the leg frame)
    ladder_t = lambda t: np.array([0, t * H, 2.4 * (1 - t * .85) - .15])
    for x in (-.25, .25): dt.add(beam(ladder_t(0) + (x, 0, 0), ladder_t(.98) + (x, 0, 0), .05, RUST))
    nr = int(56 * q)
    for k in range(nr):
        t = (k + .5) / nr * .98; dt.add(beam(ladder_t(t) + (-.25, 0, 0), ladder_t(t) + (.25, 0, 0), .035, RUST))
    # sagging cables to the hut (hut at +5,-3)
    for k in range(3 if q > .7 else 1):
        p0 = leg(.18 + k * .05, 1, -1); p1 = np.array([5.2, 2.9, -2.6 + k * .3]); mid = (p0 + p1) / 2 - (0, 1.2, 0)
        dt.add(beam(p0, mid, .04, SOOT)); dt.add(beam(mid, p1, .04, SOOT))
    for k in range(int(8 * q)):
        a = TAU * hash1(k, 111); r = 1 + 1.2 * hash1(k, 112)
        f.add(blob((r * math.sin(a), .25, r * math.cos(a)), .45 + .3 * hash1(k, 113), LEAF if k % 2 else LEAF_Y, (1, .7, 1), seed=k))
    return {'s': s, 'dt': dt, 'f': f, 'g': g}

def main():
    parts = []; stats = {}
    for lod, q in (('lod0', 1.0), ('lod1', .5)):
        models = {'water_tower': water_tower(q), 'church_top_gg': church_top(q, ('#c8a040', '#c8a040')),
                  'church_top_gp': church_top(q, ('#c8a040', '#3a6a5a')), 'church_top_pg': church_top(q, ('#3a6a5a', '#c8a040')),
                  'church_top_pp': church_top(q, ('#3a6a5a', '#3a6a5a')),
                  'school_facade': facade(q, 3, 9, Mat('#9a5a42', 8, var=.15, streak=.5, moss=.4, seed=33)),
                  'hospital_facade': facade(q, 4, 12, PLASTER, hospital=True), 'hospital_cross': hospital_cross(q),
                  'school_yard': school_yard(q), 'stadium': stadium(q), 'tv_tower': tv_tower(q)}
        for v in range(4): models[f'grave_cross_{v}'] = grave_cross(q, v)
        for name, d in models.items():
            for b, m in d.items():
                if m.P: parts.append((f'{name}|{lod}|{b}', m, 0)); stats[f'{name}|{lod}'] = stats.get(f'{name}|{lod}', 0) + m.ntri
    os.makedirs(os.path.dirname(SRC), exist_ok=True)
    write_glb(SRC, parts, extras={'tris': stats})
    for k, v in sorted(stats.items()): print(f'{k:28} {v:6} tris')
    import shutil, subprocess
    gp = os.environ.get('GLTFPACK') or shutil.which('gltfpack') or os.path.expanduser('~/.local/bin/gltfpack')
    subprocess.run([gp, '-i', SRC, '-o', OUT, '-cc', '-kn', '-km'], check=True)
    print('wrote', OUT, os.path.getsize(OUT))

if __name__ == '__main__':
    main()
