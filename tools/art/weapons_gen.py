"""Held weapons and tools of the hero (Xg / $g, except the 3 special blades) -> play/assets/art/held.glb.
Run: python3 tools/art/weapons_gen.py   (numpy + gltfpack 1.3.0).
Local frame and extents match the primitive layout of Xg/$g (hand at origin, melee items hang along -y,
guns lie along +z at y≈-0.66 before the game's own rotation), so grips and hit poses stay where they were.
All geometry is original procedural work of the TERRA team."""
import math, os, sys, shutil, subprocess, tempfile
import numpy as np
sys.path.insert(0, os.path.dirname(__file__))
import meshlib
from meshlib import Mesh, Mat, box, beam, lathe, cyl, blob, rotX, rotY, rotZ, hash1, write_glb
meshlib.NOISE_SCALE = 9.0
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '../..'))
SRC = os.path.join(tempfile.gettempdir(), 'terra-art', 'held.src.glb')
OUT = os.path.join(ROOT, 'play/assets/art/held.glb')
TAU = 2 * math.pi

def M(c, var=.12, rust=0.0, rc='#5e3420', streak=0.0, seed=0): return Mat(c, 0, var=var, rust=rust, rustcol=rc, streak=streak, dirt=0, seed=seed)
WOOD = M('#7a5534', .2, streak=.4, seed=1); WOOD_D = M('#4a3220', .18, streak=.3, seed=2); BARK = M('#6a5030', .25, seed=3)
STEEL = M('#a8aeb4', .1, rust=.3, rc='#6a4028', seed=4); STEEL_D = M('#4a4e54', .1, rust=.35, rc='#5a3420', seed=5)
EDGE = M('#e4e8ec', .05, seed=6); BLACK = M('#26272a', .08, rust=.2, rc='#4a3a2a', seed=7); GUN = M('#34363a', .08, rust=.25, rc='#5a3a22', seed=8)
TAPE = M('#2c2c2c', .2, seed=9); CLOTH = M('#c8c0a8', .2, seed=10); RAG = M('#8adf62', .15, seed=11); LEAF = M('#5f8a3a', .25, seed=12)
GOLD = M('#c8a83a', .1, rust=.2, rc='#5a4a2a', seed=13); WRAP = M('#3a1a3a', .15, seed=14); WRAP2 = M('#d8d0c0', .1, seed=15)
RED = M('#a8322a', .12, rust=.3, rc='#4a2a1a', seed=16); RUBBER = M('#1e1e20', .1, seed=17); GLOWC = M('#7af0ff', .02, seed=18)
SCIFI = M('#3a4450', .08, rust=.15, rc='#4a3a30', seed=19); SCIFI_D = M('#232a32', .08, seed=20); GLASS = M('#4f7a62', .12, seed=21)
LABEL = M('#d8d0b8', .1, seed=22); TIN = M('#b8b0a0', .1, rust=.35, rc='#6a4a30', seed=23); WHITE = M('#ece8de', .08, seed=24)
BRASS = M('#b89a4a', .1, seed=25); POLY = M('#3a3a2a', .1, seed=26)

def rodY(y0, y1, r, mat, seg=8, x=0, z=0, r1=None):
    return cyl(r, r if r1 is None else r1, y0, y1, seg, mat, cap_top=True, cap_bottom=True).xform(t=(x, 0, z))
def rodZ(z0, z1, r, mat, seg=8, x=0, y=0, r1=None):
    m = cyl(r, r if r1 is None else r1, z0, z1, seg, mat, cap_top=True, cap_bottom=True)  # along y, then rotate y->z
    return m.xform(rotX(math.pi / 2)).xform(t=(x, y, 0))
def bands(m, y0, y1, n, r, mat, seg=8):
    for k in range(n):
        y = y0 + (y1 - y0) * (k + .5) / n; m.add(rodY(y - .012, y + .012, r, mat, seg))
def blade(m, y0, y1, w, t, mat, edge, tip=.12, curve=0.0, z=0.0, seg=6):
    """flat blade in the y-z plane (thin along x), back at -z, edge at +z, tip toward y1 (<y0). Two-sided."""
    out, m = m, Mesh()
    for k in range(seg):
        a, b = k / seg, (k + 1) / seg
        ya, yb = y0 + (y1 - y0) * a, y0 + (y1 - y0) * b
        wa = w * (1 if a <= 1 - tip else max(.08, (1 - a) / tip)); wb = w * (1 if b <= 1 - tip else max(.08, (1 - b) / tip))
        ca, cb = z + curve * a * a, z + curve * b * b
        for sx in (-1, 1):
            m.quad((sx * t / 2, ya, ca - w / 2), (sx * t / 2, yb, cb - w / 2), (sx * t / 2, yb, cb - w / 2 + wb), (sx * t / 2, ya, ca - w / 2 + wa), mat) if sx > 0 else \
            m.quad((sx * t / 2, ya, ca - w / 2 + wa), (sx * t / 2, yb, cb - w / 2 + wb), (sx * t / 2, yb, cb - w / 2), (sx * t / 2, ya, ca - w / 2), mat)
            m.quad((0, ya, ca - w / 2 + wa + .012), (0, yb, cb - w / 2 + wb + .012), (sx * t / 2, yb, cb - w / 2 + wb), (sx * t / 2, ya, ca - w / 2 + wa), edge) if sx < 0 else \
            m.quad((sx * t / 2, ya, ca - w / 2 + wa), (sx * t / 2, yb, cb - w / 2 + wb), (0, yb, cb - w / 2 + wb + .012), (0, ya, ca - w / 2 + wa + .012), edge)
        m.quad((-t / 2, ya, ca - w / 2), (-t / 2, yb, cb - w / 2), (t / 2, yb, cb - w / 2), (t / 2, ya, ca - w / 2), mat)
    meshlib.two_sided(m); out.add(m)
    return out

def W(name):
    m = Mesh()
    if name == 'stick':
        pts = [(0, -.28, 0), (.01, -.55, .01), (-.01, -.85, .0), (.015, -1.15, -.01)]
        for a, b in zip(pts[:-1], pts[1:]): m.add(beam(a, b, .065, BARK))
        m.add(beam((.0, -.7, 0), (.09, -.86, .05), .025, BARK)); m.add(beam((-.0, -.95, 0), (-.08, -1.08, -.03), .02, BARK))
        bands(m, -.32, -.5, 2, .04, TAPE, 6)
        for k in range(4): m.add(blob((.02 * k - .03, -1.12 - .03 * k, .03 * (k % 2)), .06, LEAF, (1, .7, 1), seed=k))
    elif name == 'club':
        m.add(rodY(-.8, -.4, .04, TAPE)); bands(m, -.8, -.4, 5, .043, BLACK)
        m.add(cyl(.085, .045, -1.35, -.8, 10, WOOD, rings=3, cap_top=True, cap_bottom=True))
        for k in range(7):
            a = TAU * hash1(k, 3); y = -1.0 - .3 * hash1(k, 4); r = .075
            m.add(beam((r * .7 * math.sin(a), y, r * .7 * math.cos(a)), ((r + .07) * math.sin(a), y + .01, (r + .07) * math.cos(a)), .012, STEEL_D))
        m.add(rodY(-.42, -.38, .05, BLACK))
    elif name == 'machete':
        m.add(box((0, -.65, -.01), (.05, .24, .07), WOOD_D)); [m.add(rodZ(-.04, .03, .009, BRASS, 6, 0, y)) for y in (-.58, -.7)]
        m.add(box((0, -.775, .0), (.05, .025, .1), STEEL_D))
        blade(m, -.78, -1.38, .14, .018, STEEL, EDGE, tip=.25, curve=.05, z=.03, seg=6)
    elif name == 'katana':
        m.add(box((0, -.7, 0), (.045, .32, .05), WRAP))
        for k in range(7): m.add(box((0, -.57 - k * .045, 0), (.05, .018, .055), WRAP2, R=rotX(.5 if k % 2 else -.5)))
        m.add(rodY(-.55, -.53, .028, GOLD, 6))
        m.add(cyl(.075, .075, -.875, -.855, 10, GOLD, cap_top=True, cap_bottom=True))
        m.add(box((0, -.9, 0), (.035, .05, .06), GOLD))
        blade(m, -.92, -1.98, .075, .02, M('#d8e0ea', .05, rust=.08, seed=40), EDGE, tip=.08, curve=.06, z=.01, seg=8)
    elif name == 'greatsword':
        m.add(box((0, -.7, 0), (.06, .4, .065), WOOD_D)); bands(m, -.88, -.52, 4, .04, TAPE, 6)
        m.add(rodY(-.52, -.47, .05, STEEL_D, 8))
        m.add(box((0, -.92, 0), (.5, .065, .11), STEEL_D)); m.add(box((-.25, -.95, 0), (.06, .12, .12), STEEL_D)); m.add(box((.25, -.95, 0), (.06, .12, .12), STEEL_D))
        g = Mesh(); blade(g, -.95, -2.6, .24, .055, STEEL, EDGE, tip=.1, curve=0, z=0, seg=8); m.add(g.xform(rotY(math.pi / 2)))
        m.add(box((0, -1.6, 0), (.064, 1.1, .04), STEEL_D))  # fuller
    elif name == 'spear':
        m.add(rodY(-2.5, -.1, .026, WOOD, 7)); bands(m, -1.2, -.8, 3, .03, TAPE, 6)
        m.add(cyl(.032, .032, -2.48, -2.3, 7, RAG, cap_top=True, cap_bottom=True))
        m.add(beam((0, -2.34, .03), (.03, -2.55, .09), .03, RAG, h=.006)); m.add(beam((0, -2.36, -.03), (-.04, -2.6, -.07), .025, RAG, h=.006))
        m.add(rodY(-2.6, -2.45, .034, STEEL_D, 6))
        g = Mesh(); blade(g, -2.55, -2.98, .13, .025, STEEL, EDGE, tip=.55, z=0, seg=4); m.add(g); m.add(g.__class__().add(g).xform(rotY(math.pi / 2)))
    elif name == 'revolver':
        m.add(box((0, -.66, .1), (.085, .1, .16), GUN))
        m.add(cyl(.055, .055, -.0, .14, 8, STEEL_D, cap_top=True, cap_bottom=True).xform(rotX(math.pi / 2)).xform(t=(0, -.645, .03)))
        m.add(rodZ(.18, .42, .022, GUN, 8, 0, -.625)); m.add(box((0, -.6, .4), (.012, .02, .02), GUN))
        m.add(box((0, -.645, .32), (.03, .02, .2), GUN))
        m.add(box((0, -.75, -.02), (.065, .2, .08), WOOD_D, R=rotX(.3))); m.add(box((0, -.73, .05), (.012, .06, .05), STEEL_D))
        m.add(box((0, -.6, -.02), (.02, .04, .04), GUN, R=rotX(-.6)))
    elif name == 'shotgun':
        for x in (-.032, .032): m.add(rodZ(.05, .78, .03, GUN, 8, x, -.65))
        m.add(box((0, -.62, .1), (.1, .03, .1), STEEL_D)); m.add(box((0, -.675, .1), (.1, .09, .2), STEEL_D))
        m.add(box((0, -.69, .4), (.085, .05, .3), WOOD))
        m.add(box((0, -.7, -.18), (.08, .1, .34), WOOD, R=rotX(-.12))); m.add(box((0, -.73, -.34), (.085, .14, .04), RUBBER))
        m.add(box((0, -.735, .04), (.012, .05, .06), STEEL_D))
        m.add(box((0, -.68, .6), (.09, .012, .04), TAPE))
    elif name == 'rifle':
        m.add(box((0, -.65, .25), (.075, .11, .42), GUN)); m.add(box((0, -.59, .25), (.06, .02, .36), STEEL_D))
        m.add(box((0, -.65, .56), (.08, .08, .22), WOOD)); m.add(rodZ(.46, .9, .016, GUN, 7, 0, -.63)); m.add(rodZ(.88, .93, .022, BLACK, 7, 0, -.63))
        m.add(box((0, -.6, .78), (.01, .05, .015), GUN)); m.add(rodZ(.47, .66, .01, GUN, 6, 0, -.6))
        for k in range(5): m.add(box((0, -.73 - k * .025, .3 + k * .012), (.055, .03, .09), POLY, R=rotX(.25)))
        m.add(box((0, -.76, .12), (.05, .13, .05), WOOD_D, R=rotX(.35)))
        m.add(box((0, -.67, -.12), (.06, .1, .32), WOOD, R=rotX(-.08))); m.add(box((0, -.69, -.29), (.065, .14, .03), RUBBER))
        m.add(box((0, -.62, .1), (.03, .03, .06), STEEL_D)); m.add(box((0, -.64, .6), (.084, .03, .03), TAPE))
    elif name == 'railgun':
        m.add(box((0, -.66, .25), (.12, .14, .5), SCIFI)); m.add(box((0, -.6, .3), (.07, .05, .4), SCIFI_D))
        for x in (-.045, .045): m.add(box((x, -.66, .72), (.025, .09, .62), SCIFI_D))
        for k in range(6): m.add(box((0, -.66, .5 + k * .09), (.12, .11, .015), STEEL_D))
        m.add(box((0, -.66, .72), (.012, .03, .6), GLOWC)); m.add(box((.062, -.66, .25), (.004, .06, .36), GLOWC)); m.add(box((-.062, -.66, .25), (.004, .06, .36), GLOWC))
        m.add(box((0, -.77, .12), (.05, .13, .06), SCIFI_D, R=rotX(.3))); m.add(box((0, -.7, -.15), (.09, .13, .28), SCIFI_D))
        m.add(rodZ(-.02, .14, .028, GLOWC, 6, 0, -.57)); m.add(beam((.04, -.62, .0), (.06, -.6, .4), .012, RUBBER))
    return m

def T(name):
    m = Mesh()
    if name == 'axe':
        m.add(rodY(-1.48, -.5, .028, WOOD, 7)); bands(m, -.75, -.55, 3, .031, TAPE, 6)
        m.add(box((0, -1.4, .04), (.05, .14, .12), STEEL_D)); g = Mesh(); blade(g, -1.32, -1.5, .2, .035, STEEL, EDGE, tip=.0, z=.18, seg=2)
        g.P = [np.array([p[0], -1.41 + (p[1] + 1.41) * (1 + 2.5 * max(0, p[2] - .1)), p[2]]) for p in g.P]; m.add(g)
        m.add(box((0, -1.4, -.06), (.07, .1, .08), STEEL_D))
    elif name == 'wrench':
        m.add(box((0, -.88, 0), (.03, .5, .07), STEEL)); m.add(box((0, -.86, 0), (.034, .3, .03), STEEL_D))
        m.add(box((0, -1.15, -.07), (.04, .12, .05), STEEL)); m.add(box((0, -1.15, .07), (.04, .1, .05), STEEL)); m.add(box((0, -1.1, 0), (.04, .04, .2), STEEL))
        m.add(cyl(.05, .05, -.02, .02, 10, STEEL, cap_top=True, cap_bottom=True).xform(rotZ(math.pi / 2)).xform(t=(0, -.64, 0)))
        m.add(cyl(.028, .028, -.025, .025, 6, BLACK, cap_top=True, cap_bottom=True).xform(rotZ(math.pi / 2)).xform(t=(0, -.64, 0)))
    elif name == 'crowbar':
        m.add(rodY(-1.4, -.5, .02, M('#2a2c30', .1, rust=.45, rc='#6a3a1a', seed=50), 6)); m.add(rodY(-.92, -.6, .024, RED, 6))
        m.add(beam((0, -1.4, 0), (0, -1.5, .07), .04, STEEL_D)); m.add(beam((0, -1.5, .07), (0, -1.49, .16), .04, STEEL_D))
        m.add(beam((0, -.5, 0), (0, -.42, -.06), .04, STEEL_D)); m.add(box((0, -.4, -.1), (.012, .03, .05), STEEL_D))
    elif name == 'lockpick':
        m.add(box((0, -.7, 0), (.04, .08, .03), RUBBER)); m.add(rodY(-.94, -.74, .006, EDGE, 4)); m.add(box((0, -.945, .01), (.006, .012, .025), EDGE))
        m.add(beam((.02, -.72, 0), (.05, -.86, 0), .01, STEEL)); m.add(beam((.05, -.86, 0), (.05, -.9, .02), .01, STEEL))
    elif name == 'hammer':
        m.add(rodY(-1.16, -.6, .024, WOOD, 7)); bands(m, -.75, -.62, 2, .027, TAPE, 6)
        m.add(box((0, -1.16, .02), (.07, .08, .2), STEEL_D)); m.add(rodZ(.12, .2, .045, STEEL, 8, 0, -1.16))
        m.add(beam((0, -1.16, -.07), (0, -1.12, -.17), .05, STEEL_D, h=.015))
    elif name == 'bandage':
        m.add(cyl(.065, .065, -.775, -.665, 12, WHITE, cap_top=True, cap_bottom=True)); m.add(cyl(.025, .025, -.778, -.662, 6, M('#b8b0a0', seed=60), cap_top=True))
        m.add(box((.05, -.83, .055), (.09, .12, .006), WHITE, R=rotY(.4))); m.add(box((0, -.72, .066), (.04, .04, .008), RED)); m.add(box((0, -.72, .067), (.014, .04, .009), WHITE))
    elif name == 'bottle':
        m.add(lathe([(.0, -.86), (.05, -.86), (.05, -.66), (.045, -.64), (.02, -.6), (.02, -.56), (.0, -.56)], 10, GLASS))
        m.add(rodY(-.575, -.55, .022, M('#8a3a2a', seed=61), 8)); m.add(box((0, -.76, .05), (.07, .08, .006), LABEL))
        m.add(beam((0, -.555, 0), (.02, -.5, .01), .02, CLOTH))
    elif name == 'can':
        m.add(cyl(.055, .055, -.79, -.65, 12, TIN, cap_top=True, cap_bottom=True)); m.add(cyl(.057, .057, -.73, -.7, 12, TIN)); m.add(cyl(.0565, .0565, -.785, -.655, 12, RED))
        m.add(cyl(.057, .057, -.77, -.765, 12, TIN)); m.add(box((0, -.72, .058), (.05, .04, .004), LABEL))
    return m

WEAPONS = ['stick', 'club', 'machete', 'katana', 'greatsword', 'spear', 'revolver', 'shotgun', 'rifle', 'railgun']
TOOLS = ['axe', 'wrench', 'crowbar', 'lockpick', 'hammer', 'bandage', 'bottle', 'can']

def main():
    parts = []
    for n in WEAPONS: parts.append((f'w_{n}|lod0|s', W(n), 0))
    for n in TOOLS: parts.append((f't_{n}|lod0|s', T(n), 0))
    for name, m, _ in parts: print(f'{name:22} {m.ntri:5} tris')
    os.makedirs(os.path.dirname(SRC), exist_ok=True); write_glb(SRC, parts)
    gp = os.environ.get('GLTFPACK') or shutil.which('gltfpack') or os.path.expanduser('~/.local/bin/gltfpack')
    subprocess.run([gp, '-i', SRC, '-o', OUT, '-cc', '-kn', '-km', '-vp', '16'], check=True)
    print('wrote', OUT, os.path.getsize(OUT))

if __name__ == '__main__':
    main()
