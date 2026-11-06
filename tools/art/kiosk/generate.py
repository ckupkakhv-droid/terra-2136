"""Author three native KIT kiosk meshes; reuse the unchanged existing atlas.

python3 tools/art/kiosk/generate.py /tmp/terra-kiosk-generated.json
The generator writes geometry only. install_pack.py performs the guarded splice.
"""
import gzip
import hashlib
import json
import math
from pathlib import Path
import sys


ROOT=Path(__file__).resolve().parents[3]


def unit(v):
    length=math.sqrt(sum(x*x for x in v))
    if length<1e-12:raise ValueError('Zero normal')
    return [x/length for x in v]


def cross(a,b):return [a[1]*b[2]-a[2]*b[1],a[2]*b[0]-a[0]*b[2],a[0]*b[1]-a[1]*b[0]]

class Mesh:
    def __init__(self,palette):self.p=[];self.n=[];self.uv=[];self.i=[];self.palette=palette;self.parts=[]
    def face(self,points,material,hint,uv_bounds=None):
        points=[list(p) for p in points]
        n=unit(cross([points[1][i]-points[0][i] for i in range(3)],[points[2][i]-points[0][i] for i in range(3)]))
        if sum(n[i]*hint[i] for i in range(3))<0:points.reverse();n=[-v for v in n]
        axis=max(range(3),key=lambda i:abs(n[i]));axes=[i for i in range(3) if i!=axis]
        lo=[min(p[a] for p in points) for a in axes];hi=[max(p[a] for p in points) for a in axes]
        if material=='paint' and min(hi[i]-lo[i] for i in range(2))<.12:material='paint_edge'
        if uv_bounds:lo=[uv_bounds[0],uv_bounds[2]];hi=[uv_bounds[1],uv_bounds[3]]
        u0,v0,u1,v1=self.palette[material]['uv'];start=len(self.p)//3
        for p in points:
            self.p.extend(p);self.n.extend(n)
            u=(p[axes[0]]-lo[0])/max(1e-12,hi[0]-lo[0]);v=(p[axes[1]]-lo[1])/max(1e-12,hi[1]-lo[1])
            self.uv.extend([u0+(u1-u0)*u,v0+(v1-v0)*v])
        for j in range(1,len(points)-1):self.i.extend([start,start+j,start+j+1])
    def begin(self,name,closed=True):return {'name':name,'start':len(self.i),'closed':closed}
    def end(self,part):part['end']=len(self.i);self.parts.append(part)
    def beam(self,name,a,b,width,depth,material='trim',bevel=0):
        part=self.begin(name);y=unit([b[i]-a[i] for i in range(3)]);ref=[0,0,1] if abs(y[2])<.9 else [1,0,0]
        x=unit(cross(y,ref));z=cross(x,y);length=math.dist(a,b);center=[(a[i]+b[i])*.5 for i in range(3)]
        wx,dz=width/2,depth/2;q=min(bevel,min(wx,dz)*.45)
        ring=[[-wx,-dz],[wx,-dz],[wx,dz],[-wx,dz]] if not q else [[-wx+q,-dz],[wx-q,-dz],[wx,-dz+q],[wx,dz-q],[wx-q,dz],[-wx+q,dz],[-wx,dz-q],[-wx,-dz+q]]
        def pt(p,along):return [center[i]+p[0]*x[i]+along*y[i]+p[1]*z[i] for i in range(3)]
        self.face([pt(p,-length/2) for p in ring],material,[-v for v in y]);self.face([pt(p,length/2) for p in ring],material,y)
        for j,p in enumerate(ring):
            q=ring[(j+1)%len(ring)];nx,nz=q[1]-p[1],p[0]-q[0];hint=[nx*x[i]+nz*z[i] for i in range(3)]
            self.face([pt(p,-length/2),pt(q,-length/2),pt(q,length/2),pt(p,length/2)],material,hint)
        self.end(part)
    def box(self,name,x,y,z,w,h,d,material='paint',bevel=0):self.beam(name,[x,y-h/2,z],[x,y+h/2,z],w,d,material,bevel)
    def side_prism(self,name,x,width,yz,material='paint'):
        part=self.begin(name);x0,x1=x-width/2,x+width/2
        self.face([[x0,y,z] for y,z in yz],material,[-1,0,0]);self.face([[x1,y,z] for y,z in yz],material,[1,0,0])
        for j,(y,z) in enumerate(yz):
            yy,zz=yz[(j+1)%len(yz)];self.face([[x0,y,z],[x1,y,z],[x1,yy,zz],[x0,yy,zz]],material,[0,z-zz,yy-y])
        self.end(part)
    def paint(self,name,points,material='rust',hint=(0,0,1),uv_bounds=None):
        part=self.begin(name,False);self.face(points,material,hint,uv_bounds);self.end(part)
    def roof(self,segments):
        part=self.begin('closed-corrugated-roof');width,depth=2.38,2.19
        def point(k,z,underside=False):
            wave=[-.012,-.012,.012,.012][k%4] if segments>4 else -.012
            return [-width/2+width*k/segments,3.015-z*.12+wave-(.026 if underside else 0),z]
        for j in range(segments):
            self.face([point(j,-depth/2),point(j+1,-depth/2),point(j+1,depth/2),point(j,depth/2)],'roof',[0,1,0],[-width/2,width/2,-depth/2,depth/2])
            self.face([point(j,-depth/2,True),point(j+1,-depth/2,True),point(j+1,depth/2,True),point(j,depth/2,True)],'dark',[0,-1,0],[-width/2,width/2,-depth/2,depth/2])
            for z in [-depth/2,depth/2]:self.face([point(j,z),point(j+1,z),point(j+1,z,True),point(j,z,True)],'trim',[0,0,z],[-width/2,width/2,3.015-z*.12-.038,3.015-z*.12+.012])
        for j in [0,segments]:self.face([point(j,-depth/2),point(j,depth/2),point(j,depth/2,True),point(j,-depth/2,True)],'trim',[-1 if j==0 else 1,0,0])
        self.end(part)
    def word(self):
        # Own straight-stroke sign, no font bitmap or external font dependency.
        glyphs=[[(0,0,1,1),(0,1,1,0)],[(0,0,.3,1),(.3,1,1,1),(1,1,1,0)],
                [(0,0,0,1),(0,0,1,0),(0,.5,.8,.5),(0,1,1,1)],
                [(0,0,0,1),(0,1,1,1),(0,.55,.9,.55),(.9,.55,.9,0),(.9,0,0,0)]]
        for i,strokes in enumerate(glyphs):
            for j,(ax,ay,bx,by) in enumerate(strokes):
                x0=-.58+i*.31+ax*.22;y0=3.195+ay*.225;x1=-.58+i*.31+bx*.22;y1=3.195+by*.225
                dx,dy=x1-x0,y1-y0;length=math.hypot(dx,dy);px,py=-dy/length*.012,dx/length*.012
                self.paint('sign-ink-%s-%s'%(i,j),[[x0+px,y0+py,-.848],[x1+px,y1+py,-.848],[x1-px,y1-py,-.848],[x0-px,y0-py,-.848]],'ink',uv_bounds=[-.60,.60,3.18,3.44])


def build(level,palette,layout):
    m=Mesh(palette);bevel=.012 if level==0 else 0
    top=lambda z:2.977-z*.12
    if level==2:
        # Keep real apertures in the far model: an opaque window substitute
        # changes the silhouette when the background is visible through it.
        def sheet(name,points,material,hint):
            m.paint(name+'-outside',points,material,hint)
            m.paint(name+'-inside',points,material,[-v for v in hint])
        m.box('plinth',0,.055,0,2.12,.11,1.94,'dark')
        for x in [-1.01,1.01]:
            for z in [-.91,.91]:m.box('corner-post',x,(.11+top(z))/2,z,.10,top(z)-.11,.10,'trim')
        for z in [-.91,.91]:
            for y in [1.11,top(z)-.05]:m.beam('fitted-crossbar',[-.96,y,z],[.96,y,z],.10,.10,'trim')
            sheet('lower-sheet',[[-.955,.16,z], [.955,.16,z], [.955,1.06,z],[-.955,1.06,z]],'paint',[0,0,z])
        sheet('front-fascia',[[-.955,2.42,.91],[.955,2.42,.91],[.955,top(.91)-.10,.91],[-.955,top(.91)-.10,.91]],'paint',[0,0,1])
        sheet('rear-sheet',[[-.955,1.16,-.93],[.955,1.16,-.93],[.955,top(-.91)-.10,-.93],[-.955,top(-.91)-.10,-.93]],'paint',[0,0,-1])
        for x in [-1.01,1.01]:
            m.beam('side-waist',[x,1.11,-.86],[x,1.11,.86],.10,.10,'trim')
            m.beam('sloped-crown',[x,top(-.86)-.05,-.86],[x,top(.86)-.05,.86],.10,.10,'trim')
            sheet('lower-side',[[x,.16,-.855],[x,.16,.855],[x,1.06,.855],[x,1.06,-.855]],'paint',[x,0,0])
            sheet('side-fascia',[[x,2.42,-.86],[x,2.42,.86],[x,top(.86)-.10,.86],[x,top(-.86)-.10,-.86]],'paint',[x,0,0])
        m.paint('inside-floor',[[-.95,.1425,-.855],[.95,.1425,-.855],[.95,.1425,.855],[-.95,.1425,.855]],'dark',[0,1,0])
        m.paint('shelf-top',[[-.80,1.2825,-.80],[.80,1.2825,-.80],[.80,1.2825,-.44],[-.80,1.2825,-.44]],'rust',[0,1,0])
        m.box('counter',0,1.17,1.005,1.72,.075,.28,'trim')
        m.roof(1);m.box('sign-board',0,3.30,-.90,1.82,.40,.085,'dark')
        m.paint('sign-inset',[[-.86,3.14,-.852],[.86,3.14,-.852],[.86,3.46,-.852],[-.86,3.46,-.852]],'paint')
        m.word()
        m.paint('door-frame',[[-.685,.19,-.985],[.065,.19,-.985],[.065,2.59,-.985],[-.685,2.59,-.985]],'dark',[0,0,-1])
        m.paint('door-panel',[[-.645,.24,-.9975],[.025,.24,-.9975],[.025,2.54,-.9975],[-.645,2.54,-.9975]],'paint',[0,0,-1])
        return finish(m,layout)
    # A 25 mm base chamfer also survives native Uint16 UV quantisation.
    m.box('plinth',0,.055,0,2.12,.11,1.94,'dark',.025 if level==0 else 0)
    for x in [-1.01,1.01]:
        for z in [-.91,.91]:m.box('corner-post',x,(.11+top(z))/2,z,.10,top(z)-.11,.10,'trim',bevel)
    for z in [-.91,.91]:
        for y in [1.11,top(z)-.05]:m.beam('fitted-crossbar',[-.96,y,z],[.96,y,z],.10,.10,'trim',bevel)
        if z>0:m.box('front-roof-fascia',0,(2.42+top(z)-.10)/2,z,1.91,top(z)-.10-2.42,.055,'paint')
    for x in [-1.01,1.01]:
        m.beam('fitted-side-waist',[x,1.11,-.86],[x,1.11,.86],.10,.10,'trim',bevel)
        m.beam('fitted-sloped-crown',[x,top(-.86)-.05,-.86],[x,top(.86)-.05,.86],.10,.10,'trim',bevel)
        m.side_prism('side-roof-fascia',x,.055,[[2.42,-.86],[2.42,.86],[top(.86)-.10,.86],[top(-.86)-.10,-.86]])
    # Inset sheets meet the frame without coplanar front faces.
    for z in [-.91,.91]:m.box('lower-panel',0,.61,z,1.91,.90,.055,'paint')
    for x in [-1.01,1.01]:m.box('side-lower-panel',x,.61,0,.055,.90,1.71,'paint')
    # Closed rear service door; sales windows and the left window remain open.
    m.box('rear-sheet',0,(1.155+top(-.91)-.10)/2,-.93,1.90,top(-.91)-.10-1.155,.04,'paint')
    m.box('service-door',-.31,1.39,-.967,.75,2.40,.025,'dark')
    m.box('door-inner-panel',-.31,1.39,-.987,.67,2.30,.016,'paint')
    if level<2:
        m.beam('door-handle',[-.10,1.20,-1.005],[-.10,1.38,-1.005],.023,.025,'trim')
        for y in [.43,2.24]:m.box('door-hinge',-.705,y,-.986,.06,.12,.035,'rust',bevel)
        m.box('interior-floor',0,.125,0,1.90,.035,1.71,'dark')
        m.box('inside-shelf',0,1.26,-.62,1.60,.045,.36,'rust')
        for x in [-.80,.80]:m.box('sales-jamb',x,1.81,.91,.035,1.30,.045,'trim')
        m.box('side-mullion',-1.01,1.78,0,.06,.035,1.71,'trim')
    m.box('counter',0,1.17,1.005,1.72,.075,.28,'trim',bevel)
    m.roof([32,16,4][level])
    m.box('sign-board',0,3.30,-.90,1.82,.40,.085,'dark',bevel)
    if level<2:
        m.box('sign-inset',0,3.30,-.854,1.72,.32,.004,'paint')
        m.word()
    if level==0:
        for x in [-.92,.92]:
            for y in [.23,.96,2.62]:m.box('fastener',x,y,.9435,.035,.035,.012,'rust',.005)
        for x,y in [(-.85,.24),(.62,.83),(-.38,.56)]:
            m.paint('paint-loss',[[x,y,.940],[x+.11,y+.02,.940],[x+.09,y+.07,.940],[x+.015,y+.095,.940],[x-.015,y+.04,.940]])
        for x in [-.92,.92]:
            m.paint('rust-below-fastener',[[x-.008,.94,.940],[x+.010,.94,.940],[x+.004,.65,.940],[x-.002,.58,.940]],'rust')
        for j in [2,10,18,26]:
            x=-1.19+(j+.5)*2.38/32
            pts=[[x-.012,-.72],[x+.014,-.66],[x+.008,.18],[x-.004,.28]]
            m.paint('roof-weather-streak',[[a,3.015-z*.12+.012+.002,z] for a,z in pts],'rust',[0,1,0])
        m.paint('small-glass-remnant',[[-.79,2.40,.935],[-.64,2.40,.935],[-.79,2.22,.935]],'glass')
        m.paint('small-glass-remnant',[[.79,1.23,.935],[.79,1.40,.935],[.65,1.23,.935]],'glass')
    return finish(m,layout)


def finish(m,layout):
    # Keep the pinned near-model envelope in every LOD, including the base.
    lo=[min(m.p[i::3]) for i in range(3)];hi=[max(m.p[i::3]) for i in range(3)]
    scale=[layout['sc'][i]/(hi[i]-lo[i]) for i in range(3)]
    for k in range(0,len(m.p),3):
        for i in range(3):m.p[k+i]=layout['mn'][i]+(m.p[k+i]-lo[i])*scale[i]
        m.n[k:k+3]=unit([m.n[k+i]/scale[i] for i in range(3)])
    return {'p':m.p,'n':m.n,'uv':m.uv,'i':m.i,'parts':m.parts}


if __name__=='__main__':
    part=json.loads(gzip.decompress((ROOT/'play/assets/pack/TERRA_KIT.json.gz').read_bytes()))['decor']
    layout=json.loads((Path(__file__).parent/'native-layout.json').read_text(encoding='utf-8'))
    for key,expected in layout['textures'].items():assert hashlib.sha256(part[key].encode()).hexdigest()==expected,(key,'Atlas changed')
    palette=json.loads((Path(__file__).parent/'palette.json').read_text(encoding='utf-8'))
    lods=[build(i,palette,layout['bounds']) for i in range(3)]
    result={'layout':layout,'palette':palette,'lods':lods}
    Path(sys.argv[1]).write_text(json.dumps(result,separators=(',',':')),encoding='utf-8')
    print('Kiosk triangles:',[len(l['i'])//3 for l in lods]);print('Atlas palette:',{k:v['color'] for k,v in palette.items()})
