"""Упаковать девять независимых иллюстраций альбома, не включая промежутки атласа."""
from pathlib import Path
import argparse,json,hashlib
from PIL import Image
parser=argparse.ArgumentParser();parser.add_argument('source',type=Path);args=parser.parse_args()
root=Path(__file__).resolve().parents[3];out=root/'play/assets/ui/camp';out.mkdir(parents=True,exist_ok=True)
im=Image.open(args.source).convert('RGB');assert im.size==(1536,1024),im.size
columns=[(14,500),(522,1014),(1037,1521)];rows=[(15,316),(342,649),(676,1009)]
names=['scene-camp','scene-outpost','scene-map','scene-defense','scene-tech','scene-power','scene-warehouse','scene-convoy','scene-trail'];exports={}
for index,name in enumerate(names):
 x0,x1=columns[index%3];y0,y1=rows[index//3];art=im.crop((x0,y0,x1,y1));art.thumbnail((492,312),Image.Resampling.LANCZOS);path=out/(name+'.webp');art.save(path,'WEBP',quality=82,method=6)
 data=path.read_bytes();exports[path.name]={'size':list(art.size),'bytes':len(data),'sha256':hashlib.sha256(data).hexdigest()}
manifest={'generator':'OpenAI Image Generation','date':'2026-11-06','source':{'file':args.source.name,'sha256':hashlib.sha256(args.source.read_bytes()).hexdigest(),'size':list(im.size)},'exports':exports}
(Path(__file__).parent/'provenance.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n');print('Packed',len(exports),'illustrations /',sum(e['bytes'] for e in exports.values()),'bytes')
