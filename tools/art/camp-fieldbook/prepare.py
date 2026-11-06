"""Pack the three generated source atlases into the camp's sixteen WebP assets.

Source images stay outside the runtime package. See README.md for provenance.
"""
import argparse
from pathlib import Path
from PIL import Image

p=argparse.ArgumentParser()
p.add_argument('--materials',type=Path,required=True)
p.add_argument('--portraits',type=Path,required=True)
p.add_argument('--blueprints',type=Path,required=True)
p.add_argument('--output',type=Path,default=Path(__file__).resolve().parents[3]/'play/assets/ui/camp')
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
im=Image.open(a.materials);w,h=im.size
for name,col,row in [('paper',0,0),('blueprint',1,0),('leather',0,1),('brass',1,1)]:
 im.crop((col*w//2,row*h//2,(col+1)*w//2,(row+1)*h//2)).resize((512,512)).convert('RGB').save(a.output/(name+'.webp'),quality=78,method=6)
im=Image.open(a.portraits).convert('RGB');w,h=im.size
for row in range(2):
 for col in range(4):
  cell=im.crop((round(col*w/4)+2,round(row*h/2)+2,round((col+1)*w/4)-2,round((row+1)*h/2)-2)).resize((256,256))
  cell.save(a.output/('portrait-'+str(row*4+col+1).zfill(2)+'.webp'),quality=83,method=6)
im=Image.open(a.blueprints).convert('RGBA')
if im.size!=(2172,724):raise SystemExit('Unexpected blueprint atlas; inspect transparent gutters before changing crop coordinates')
for name,left,right in [('sawmill',0,577),('generator',577,1145),('pump',1145,1705),('watch',1705,2172)]:
 cell=im.crop((left,0,right,im.height));bbox=cell.getchannel('A').point(lambda v:255 if v>30 else 0).getbbox();cell=cell.crop(bbox);cell.thumbnail((500,380))
 canvas=Image.new('RGBA',(520,400));canvas.alpha_composite(cell,((520-cell.width)//2,(400-cell.height)//2));canvas.save(a.output/(name+'.webp'),quality=83,method=6)
print(sum(x.stat().st_size for x in a.output.glob('*.webp')),'bytes')
