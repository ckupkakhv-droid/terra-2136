#!/usr/bin/env python3
"""Add riverbank coverage to this bundled terrain renderer, without changing physics.

The terrain batch's triangle method stores its last three arguments in aux.y.
Values 2 and 3 distinguish river triangles from ordinary water and encode whether
that corner has a river level. The water shader fades the colour at the edge but
never makes the blocked area fully transparent. This is a version-specific bridge:
refuse to modify an unfamiliar bundle rather than silently patch the wrong code.
"""
from pathlib import Path

path = Path(__file__).resolve().parents[1] / 'play' / 'index.html'
old = ('Q=Y=>e.wl[Y]>-50?e.wl[Y]:C;'
       'P.tri(w[0],Q(w[3]),w[2],E[0],Q(E[3]),E[2],k[0],Q(k[3]),k[2],N,N,N,W,W,W),'
       'P.tri(k[0],Q(k[3]),k[2],E[0],Q(E[3]),E[2],M[0],Q(M[3]),M[2],N,N,N,W,W,W)')
new = ('Q=Y=>e.wl[Y]>-50?e.wl[Y]:C,B=Y=>2+(e.wl[Y]>-50?1:0);'
       'P.tri(w[0],Q(w[3]),w[2],E[0],Q(E[3]),E[2],k[0],Q(k[3]),k[2],N,N,N,W,W,W,B(w[3]),B(E[3]),B(k[3])),'
       'P.tri(k[0],Q(k[3]),k[2],E[0],Q(E[3]),E[2],M[0],Q(M[3]),M[2],N,N,N,W,W,W,B(k[3]),B(E[3]),B(M[3]))')
text = path.read_text(encoding='utf-8')
if text.count(new) == 1 and old not in text:
    print('Shoreline bridge is already applied.')
elif text.count(old) == 1 and new not in text:
    path.write_text(text.replace(old, new, 1), encoding='utf-8')
    print('Shoreline bridge applied.')
else:
    raise SystemExit('Unexpected bundle: refusing to apply the shoreline bridge.')
