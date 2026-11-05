"""Fade chunk-local footpath paint into the underlying road/ground at its edge.

The original module sources are unavailable; strict anchors limit the edit to
local path colour, material weights and their existing wetness contribution.
"""
from pathlib import Path

path=Path(__file__).resolve().parents[1]/'play/index.html'
html=path.read_text(encoding='utf-8')
before='st<U[4]&&(tr(g,Mn.path,$s(U[4],U[4]*.35,st)*.85),d(1,$s(U[4],U[4]*.35,st)*.85),V=Math.max(V,.08))'
after='if(st<U[4]){let pathEdge=$s(0,4,Math.min(k-n,n+Qt-k,E-s,s+Qt-E)),pathMix=$s(U[4],U[4]*.35,st)*.85*pathEdge;tr(g,Mn.path,pathMix),d(1,pathMix),V=Math.max(V,.08*pathEdge)}'
if after in html and before in html:raise SystemExit('Mixed local-path paint versions')
if after not in html:
    if html.count(before)!=1:raise SystemExit('Native local-path paint anchor changed')
    html=html.replace(before,after,1)
if html.count(after)!=1:raise SystemExit('Local-path transition is ambiguous')
path.write_text(html,encoding='utf-8')
print('Local footpaths blend into the underlying ground over the last 4 m')
