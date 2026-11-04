"""Expose a reviewed terrain builder bridge without replacing the compiled game."""
from pathlib import Path
import hashlib,re
root=Path(__file__).resolve().parents[1];p=root/'play/index.html';raw=p.read_bytes()
BASELINES = {
 '858fe60ec39a73b663dc0c5a915da3597afa99aefeddc414c7b6b3aaf2046cc9', # main 6f5aaf0, до арт-слоя
 '39463103ffc3c49e92a68d503e3795cbcf13de5f51e8523f2985e4f62fba054c', # main 23484d1, проверен хук ориентиров PR #13
}
if hashlib.sha256(raw).hexdigest() not in BASELINES:
 raise SystemExit('Unsupported baseline; review the bundle before adapting this bridge')
s=raw.decode();assert s.count('rot();})();')==1
s=s.replace('rot();})();','rot();window.TERRA_SEWER_BRIDGE={Chunk:Ie,shapes:L,Mesh:$t,Sphere:Hc,Material:vn,Group:Pi,bosses:vi,weapons:Tt,grades:ai,WeaponBuilder:ld};})();')
weapon_hook='function Xg(e){'
assert s.count(weapon_hook)==1
s=s.replace(weapon_hook,weapon_hook+'if(e==="sewer_sai")return window.TERRA_SEWER_BRIDGE.makeSaiGeometry();')
s=s.replace('</head>','<script type="module" src="ui/sewer-bootstrap.js"></script>\n</head>',1)
a=s.index('function recommendResident(');b=s.index('function _et(',a)
s=s[:a]+s[b:]
s=s.replace('</head>','<script src="ui/resident-recommendation.js"></script>\n</head>',1)
assert len(s.encode())<=len(raw)
p.write_text(s)
