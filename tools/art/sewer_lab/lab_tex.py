# Текстуры набора лаборатории «Объект 7»: тайлы (кирпич, бетон) + исходники для запекания + decals.png (RU/CN, логотип Ambrala)
import os, math, numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
D=os.environ.get('LAB_TEX','/workspace/art-sewer/lab/tex/'); os.makedirs(D,exist_ok=True)
CJK=os.environ.get('LAB_FONT','/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc')   # Noto Sans CJK SC Bold, SIL OFL 1.1
SYM='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'                              # только знак ☣
rng=np.random.default_rng(7)
def F(sz): return ImageFont.truetype(CJK,sz,index=2)
def noise(n,oct=5,seed=0):
    r=np.random.default_rng(seed); out=np.zeros((n,n))
    for o in range(oct):
        s=2**(o+2); g=r.random((s,s)); g=np.tile(g,(1,1))
        im=Image.fromarray((g*255).astype(np.uint8)).resize((n,n),Image.BICUBIC)
        out+=np.asarray(im)/255/(1.7**o)
    out-=out.min(); return out/out.max()
def tnoise(n,oct=5,seed=0):  # тайлящийся шум
    r=np.random.default_rng(seed); out=np.zeros((n,n))
    for o in range(oct):
        s=2**(o+2); g=r.random((s,s)); g=np.pad(g,((0,1),(0,1)),mode='wrap')
        im=np.asarray(Image.fromarray((g*255).astype(np.uint8)).resize((n+n//s,n+n//s),Image.BILINEAR))[:n,:n]/255
        out+=im/(1.7**o)
    out-=out.min(); return out/out.max()
def save(a,name): Image.fromarray(np.clip(a*255,0,255).astype(np.uint8)).save(D+name)
N=512
# кирпич: тайл 2×2 м, кирпич 0.25×0.065 + шов 0.01 -> 8 × 27 рядов
n=tnoise(N,6,1); b=np.zeros((N,N,3)); y,x=np.mgrid[0:N,0:N]
rows=27; rh=N/rows; row=(y//rh).astype(int); off=(row%2)*0.5
bx=((x/N*8+off)%1); by=(y%rh)/rh; joint=(bx<.045)|(by<.16)
bid=(row*31+((x/N*8+off)//1).astype(int)*17)%23/23
base=np.stack([.46+.14*bid,.24+.06*bid,.17+.03*bid],-1)
soot=tnoise(N,4,9)[...,None]
col=base*(.75+.35*n[...,None])*(1-.45*np.clip(soot-.45,0,1)*2)
col[joint]=np.array([.36,.34,.30])*(.8+.3*n[joint,None])
save(col,'brick.png')
# бетон: тайл 2×2 м, пятна, потёки
n=tnoise(N,6,2); n2=tnoise(N,3,3); st=np.clip((tnoise(N,2,4)-.5)*3,0,1)
c=np.stack([.47,.48,.45],-1)*(.75+.35*n[...,None]); c*= (1-.25*n2[...,None]*st[...,None])
c[...,1]+=.03*st; save(c,'concrete.png')
# окрашенная сталь (серо-зелёная «советская» краска со сколами до ржавчины)
n=tnoise(N,6,5); chip=tnoise(N,5,6)>.72; rust=np.stack([.42,.22,.10],-1)*(.7+.5*n[...,None])
c=np.stack([.33,.40,.36],-1)*(.85+.25*n[...,None]); c[chip]=rust[chip]; save(c,'steel.png')
# ржавчина
n=tnoise(N,6,8); c=np.stack([.40+.15*n,.21+.07*n,.10+.03*n],-1); save(c,'rust.png')
# жёлто-чёрная разметка (диагональ, тайл 1 м = 4 полосы)
s=(((x+y)/N*4)%1)<.5; c=np.where(s[...,None],np.array([.80,.62,.12]),np.array([.08,.08,.07]))*(.8+.25*tnoise(N,5,10)[...,None]); save(c,'hazard.png')
# оливковая краска ящика
n=tnoise(N,6,11); c=np.stack([.40,.44,.27],-1)*(.85+.3*n[...,None]); c[tnoise(N,5,12)>.78]*=.55; save(c,'olive.png')
# грибок: фиолетово-бурая масса с бирюзовыми прожилками
n=tnoise(N,6,13); v=np.abs(np.sin(tnoise(N,4,14)*25)); c=np.stack([.30+.12*n,.20+.05*n,.24+.08*n],-1); c=np.where((v<.12)[...,None],np.array([.15,.55,.48]),c); save(c,'fungus.png')
# столешница: светлая нержавейка, царапины
n=tnoise(N,5,15); c=np.stack([.62,.64,.62],-1)*(.85+.2*n[...,None]); save(c,'tabletop.png')
# бумага
save(np.stack([.82,.80,.72],-1)*(.9+.1*tnoise(N,4,17)[...,None]),'paper.png')
# нормаль кирпича (рельеф швов)
h=np.where(joint,0.,1.)*1.0; h=np.asarray(Image.fromarray((h*255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.5)))/255.
gy,gx=np.gradient(h); nn=np.stack([-gx*4,gy*4,np.ones_like(h)],-1); nn/=np.linalg.norm(nn,axis=-1,keepdims=True); save(nn*.5+.5,'brick_n.png')
# резина/уплотнитель
save(np.stack([.10,.10,.10],-1)*(.8+.4*tnoise(N,5,16)[...,None]),'rubber.png')
# ---------- decals.png 1024×1024 (вшивается в lab_kit.glb) ----------
def logo(g,cx,cy,R,col=(31,174,140),fg=(242,242,234)):
    pts=[(cx+math.cos(math.pi/3*i+math.pi/6)*R,cy+math.sin(math.pi/3*i+math.pi/6)*R) for i in range(6)]; g.polygon(pts,fill=col)
    w=max(2,int(R*.13))
    for k in (0,1):
        a=(cx-R*.55,cy+R*(.42-k*.32)); m=(cx,cy-R*(.48+k*.32)+R*.32); b=(cx+R*.55,cy+R*(.42-k*.32)); g.line([a,m,b],fill=fg,width=w,joint='curve')
    r=R*.11; g.ellipse([cx-r,cy+R*.5-r,cx+r,cy+R*.5+r],fill=fg)
def grime(im,k=260):
    g=ImageDraw.Draw(im,'RGBA'); w,h=im.size
    for i in range(k):
        x0,y0=rng.random()*w,rng.random()*h; r=1+rng.random()**3*h*.04; g.ellipse([x0-r,y0-r*.7,x0+r,y0+r*.7],fill=(90,60,30,int(20+rng.random()*55)))
    for i in range(6):  # потёки сверху
        x0=rng.random()*w; L=h*(.2+rng.random()*.5); g.rectangle([x0,0,x0+2+rng.random()*5,L],fill=(80,55,30,40))
def fit(g,txt,font_px,maxw):
    while font_px>14 and g.textlength(txt,font=F(font_px))>maxw: font_px-=2
    return F(font_px)
def bisign(w,h,ru,zh,sub=None,bg=(226,194,58),fg=(20,20,20),withlogo=False,bio=False):
    im=Image.new('RGB',(w,h),bg); g=ImageDraw.Draw(im); bw=max(6,h//32); g.rectangle([bw,bw,w-bw-1,h-bw-1],outline=fg,width=bw)
    x0=w/2; left=0
    if bio: g.text((h*.36,h*.52),'☣',font=ImageFont.truetype(SYM,int(h*.55)),fill=fg,anchor='mm'); left=h*.68
    if withlogo: logo(g,h*.36,h/2,h*.26); left=h*.68
    x0=left+(w-left)/2; mw=(w-left)-bw*6
    L=ru.split('|'); fr=fit(g,max(L,key=len),int(h*.2),mw)
    if len(L)>1:
        g.text((x0,h*.27),L[0],font=fr,fill=fg,anchor='mm'); g.text((x0,h*.27+fr.size*1.05),L[1],font=fr,fill=fg,anchor='mm'); yz=h*.76
    else: g.text((x0,h*.34),ru,font=fr,fill=fg,anchor='mm'); yz=h*.64
    g.text((x0,yz),zh,font=fit(g,zh,int(min(fr.size*1.2,h*.24)),mw),fill=fg,anchor='mm')
    if sub: g.text((x0,h*.87),sub,font=fit(g,sub,int(h*.075),mw),fill=fg,anchor='mm')
    grime(im); return im
def amblabel(w,h,l1,l2,bg=(217,220,212)):
    im=Image.new('RGB',(w,h),bg); g=ImageDraw.Draw(im); R=h*.22; logo(g,h*.3,h*.33,R)
    g.text((h*.58,h*.25),'AMBRALA',font=F(int(h*.2)),fill=(27,27,27),anchor='lm'); g.text((h*.6,h*.47),'安布拉拉',font=F(int(h*.12)),fill=(27,27,27),anchor='lm')
    g.rectangle([w*.04,h*.62,w*.96,h*.645],fill=(31,174,140))
    g.text((w*.05,h*.75),l1,font=fit(g,l1,int(h*.11),w*.9),fill=(27,27,27),anchor='lm'); g.text((w*.05,h*.9),l2,font=fit(g,l2,int(h*.11),w*.9),fill=(27,27,27),anchor='lm')
    grime(im,140); return im
A=Image.new('RGBA',(1024,1024),(0,0,0,0)); R={}
def put(name,im,x,y):
    A.paste(im.convert('RGBA'),(x,y)); R[name]=[x,y,im.size[0],im.size[1]]
put('object7',bisign(1024,320,'ОБЪЕКТ 7 · НИИ «ПОЛЫНЬ»','第7号设施 · AMBRALA 分部',None,(196,202,189),(27,27,27),withlogo=True),0,0)
put('biohazard',bisign(512,256,'БИОЛОГИЧЕСКАЯ|ОПАСНОСТЬ','生物危害',bio=True),0,320)
put('no_entry',bisign(512,256,'ВХОД ВОСПРЕЩЁН','禁止入内','ТОЛЬКО ДЛЯ ПЕРСОНАЛА · 仅限工作人员',(216,216,208),(138,16,16)),512,320)
put('hermozone',bisign(512,192,'ГЕРМОЗОНА','隔离区',None,(170,30,24),(240,236,226)),0,576)
put('vat_label',amblabel(512,256,'ШТАММ «ПОЛЫНЬ-7»','毒株 P-7 · 样本 01'),512,576)
put('crate_label',bisign(512,256,'БИОМАТЕРИАЛ|ХРАНИТЬ ПРИ −20 °C','生物材料 · 储存温度 −20 °C',bg=(226,194,58),bio=True),0,768)
lg=Image.new('RGBA',(192,192),(0,0,0,0)); logo(ImageDraw.Draw(lg),96,96,90); put('logo',lg,512,832)
put('vat_label_03',amblabel(320,192,'ШТАММ «ПОЛЫНЬ-7»','毒株 P-7 · 样本 03'),704,832)
A.save(D+'decals.png')
import json; json.dump(R,open(D+'decals.json','w'),ensure_ascii=False)
print('ok',os.path.getsize(D+'decals.png'))
