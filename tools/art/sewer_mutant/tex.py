from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageChops
import numpy as np, random
random.seed(3); rng=np.random.default_rng(3)
import os
D=os.environ.get('MUT_TEX','/workspace/art-sewer/v2/tex/'); U=os.environ.get('MUT_SRC','/workspace/art-sewer/cc0')+'/ubc/Universal Base Characters[Standard]/Base Characters/Godot - UE/'
FB='/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
def noise(n,s,oct=4):
    acc=np.zeros((n,n));amp=1
    for o in range(oct):
        k=max(2,int(s*2**o));a=rng.random((k,k));im=Image.fromarray((a*255).astype('uint8')).resize((n,n),Image.BICUBIC);acc+=np.asarray(im)/255*amp;amp*=.5
    return acc/acc.max()
N=1024
# skin: luminance of UBC -> green; underwear (dark, low sat) -> dark brown cloth
src=np.asarray(Image.open(U+'T_Superhero_Male_Dark.png').convert('RGB').resize((N,N),Image.LANCZOS)).astype(float)/255
lum=src@[.3,.59,.11]; sat=src.max(2)-src.min(2)
nz=noise(N,8); sp=noise(N,40,2)
g=np.stack([.13+.30*lum,.18+.36*lum,.08+.16*lum],2)
g*= (0.8+0.35*nz)[...,None]
g=g*(1-.25*(sp>.72)[...,None])  # darker spots
g[...,0]+=.06*(nz>.7)  # rusty-brown blotches
cloth=(sat<.08)&(lum<.35)
g[cloth]=np.stack([.20+.3*lum,.16+.25*lum,.12+.2*lum],2)[cloth]
im=Image.fromarray((np.clip(g,0,1)*255).astype('uint8'))
d=ImageDraw.Draw(im)
for i in range(18):  # scars
    x,y=random.randint(0,N),random.randint(0,N);l=random.randint(15,45);a=random.random()*3.14
    d.line([x,y,x+l*np.cos(a),y+l*np.sin(a)],fill=(150,120,95),width=3)
im.save(D+'skin.png')
Image.open(U+'T_Superhero_Male_Normal.png').convert('RGB').resize((N,N),Image.LANCZOS).save(D+'skin_n.png')
# vatnik quilting: v along height; horizontal seams every 32px, vertical every 128
n=512;a=np.ones((n,n,3))*[.36,.40,.46]; a*= (0.75+.4*noise(n,6))[...,None]
v=np.arange(n)%40; q=np.clip(np.abs(v-20)/20,0,1)  # puffy
a*= (0.7+.45*(1-q**2))[:,None,None]
a[(np.arange(n)%40)<2]*=.45
a[:,(np.arange(n)%170)<2]*=.6
w=noise(n,20,2)>.78; a[w]=a[w]*.6+np.array([.35,.3,.22])*.4  # wear / dirt
Image.fromarray((np.clip(a,0,1)*255).astype('uint8')).save(D+'vatnik.png')
# plastron: ochre plates, horizontal grooves
a=np.ones((n,n,3))*[.62,.50,.26]; a*=(0.75+.35*noise(n,10))[...,None]
for y in range(0,n,85): a[max(0,y-4):y+4]*=.35
a[:,n//2-3:n//2+3]*=.35
a[noise(n,30,2)>.8]*=.7
Image.fromarray((np.clip(a,0,1)*255).astype('uint8')).save(D+'plastron.png')
# carapace: scutes (hex-ish) dark olive-brown with rim and rust stains
a=np.ones((n,n,3))*[.42,.38,.22]; a*=(0.7+.45*noise(n,8))[...,None]
im=Image.fromarray((np.clip(a,0,1)*255).astype('uint8'));d=ImageDraw.Draw(im)
for r in range(5):
    for c in range(5):
        cx=c*n/4+(r%2)*n/8;cy=r*n/4
        pts=[(cx+60*np.cos(t),cy+60*np.sin(t)) for t in np.linspace(0,2*np.pi,7)[:-1]+np.pi/6]
        d.polygon(pts,outline=(25,22,12),width=7)
for i in range(30):
    x,y=random.randint(0,n),random.randint(0,n);d.line([x,y,x+random.randint(-40,40),y+random.randint(-40,40)],fill=(150,135,100),width=2)
im=im.filter(ImageFilter.GaussianBlur(.6));im.save(D+'carapace.png')
# bandana red worn
a=np.ones((256,256,3))*[.62,.07,.05]; a*=(0.65+.5*noise(256,6))[...,None]; a[noise(256,25,2)>.75]*=.6
Image.fromarray((np.clip(a,0,1)*255).astype('uint8')).save(D+'bandana.png')
# khaki canvas
a=np.ones((256,256,3))*[.33,.33,.20]; a*=(0.7+.4*noise(256,10))[...,None]
Image.fromarray((np.clip(a,0,1)*255).astype('uint8')).save(D+'khaki.png')
# rust metal
a=np.ones((256,256,3))*[.42,.42,.43]; r=noise(256,12)>.55; a[r]=a[r]*.4+np.array([.45,.22,.10])*.6; a*=(0.75+.35*noise(256,20,2))[...,None]
Image.fromarray((np.clip(a,0,1)*255).astype('uint8')).save(D+'rustmetal.png')
# patch МОСВОДОСТОК (own design: no official logo)
im=Image.new('RGB',(512,256),(30,46,78));d=ImageDraw.Draw(im)
d.rounded_rectangle([6,6,505,249],24,outline=(200,180,90),width=8)
f=ImageFont.truetype(FB,50);d.text((256,105),'МОСВОДОСТОК',font=f,fill=(225,215,180),anchor='mm')
f2=ImageFont.truetype(FB,34);d.text((256,185),'КОЛЛЕКТОР № 14',font=f2,fill=(200,180,90),anchor='mm')
for x in range(40,480,18): d.arc([x,212,x+18,232],0,180,fill=(120,170,210),width=3)
a=np.asarray(im).astype(float)/255;a*=(0.8+.25*noise(256,16,2)[:, :, None].repeat(2,1)[:, :512] if False else 1)
im.save(D+'patch.png')
print('ok')
