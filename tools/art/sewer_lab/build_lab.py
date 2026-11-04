# Набор лаборатории «Объект 7 · НИИ „Полынь“» -> lab_kit.glb. Blender 4.2, запуск: blender -b --python build_lab.py
# Оси Blender: Z вверх, «лицо» модуля смотрит в −Y (в glTF это +Z). Единицы — метры. Все узлы в начале координат.
import bpy, bmesh, math, os, random, json
from mathutils import Vector, Matrix
random.seed(7)
TEX=os.environ.get('LAB_TEX','/workspace/art-sewer/lab/tex/'); OUT=os.environ.get('LAB_OUT','/workspace/art-sewer/lab/out/lab_raw.glb'); OUTDIR=os.path.dirname(OUT); os.makedirs(OUTDIR,exist_ok=True)
DEC=json.load(open(TEX+'decals.json'))
bpy.ops.wm.read_factory_settings(use_empty=True)
sc=bpy.context.scene
def sel(o):
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
# ---------- материалы ----------
def img(name,cs='sRGB'):
    i=bpy.data.images.load(TEX+name); i.colorspace_settings.name=cs; return i
def mat(name,tex=None,col=(1,1,1,1),emit=None,estr=1.0,alpha=None,normal=None):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; p=nt.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value=1.0; p.inputs['Metallic'].default_value=0.0; p.inputs['Base Color'].default_value=col
    if tex:
        t=nt.nodes.new('ShaderNodeTexImage'); t.image=img(tex); t.name='SRC'; nt.links.new(t.outputs['Color'],p.inputs['Base Color'])
        if alpha=='MASK': nt.links.new(t.outputs['Alpha'],p.inputs['Alpha'])
    if normal:
        t=nt.nodes.new('ShaderNodeTexImage'); t.image=img(normal,'Non-Color'); nm=nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(t.outputs['Color'],nm.inputs['Color']); nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
    if emit:
        p.inputs['Emission Color'].default_value=emit; p.inputs['Emission Strength'].default_value=estr
    if isinstance(alpha,float): p.inputs['Alpha'].default_value=alpha
    if alpha is not None:
        try: m.blend_method='BLEND' if isinstance(alpha,float) else 'CLIP'
        except Exception: pass
    m.use_backface_culling=False
    return m
M=dict(
 brick=mat('lab_brick','brick.png',normal='brick_n.png'), conc=mat('lab_concrete','concrete.png'),
 glow=mat('lab_glow_teal',col=(.1,.5,.42,1),emit=(.2,.85,.7,1),estr=1.0), warm=mat('lab_glow_warm',col=(1,.8,.5,1),emit=(1,.72,.38,1),estr=3.0),
 glass=mat('lab_glass',col=(.55,.85,.8,1),alpha=.22), dec=mat('lab_decals','decals.png',alpha='MASK'))
SRC=dict(steel='steel.png',rust='rust.png',haz='hazard.png',olive='olive.png',fun='fungus.png',top='tabletop.png',rub='rubber.png',paper='paper.png')
for k,v in SRC.items(): M[k]=mat('src_'+k,v)
PROPS={M[k].name for k in SRC}
# ---------- примитивы ----------
def boxuv(o,tile):
    me=o.data; uv=me.uv_layers.get('UVMap') or me.uv_layers.new(name='UVMap'); mw=o.matrix_world
    for p in me.polygons:
        n=(mw.to_3x3()@p.normal); ax=max(range(3),key=lambda i:abs(n[i]))
        for li in p.loop_indices:
            c=mw@me.vertices[me.loops[li].vertex_index].co
            u,v={0:(c.y,c.z),1:(c.x,c.z),2:(c.x,c.y)}[ax]; uv.data[li].uv=(u/tile,v/tile)
def done(o,m,tile=1.0):
    sel(o); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    o.data.materials.clear(); o.data.materials.append(m)
    if m.name!='lab_decals': boxuv(o,tile)
    return o
def box(m,x0,x1,y0,y1,z0,z1,tile=1.0):
    bpy.ops.mesh.primitive_cube_add(location=((x0+x1)/2,(y0+y1)/2,(z0+z1)/2)); o=bpy.context.object; o.scale=((x1-x0)/2,(y1-y0)/2,(z1-z0)/2); return done(o,m,tile)
def cyl(m,loc,r,h,seg=12,rot=(0,0,0),cap='NGON',scale=(1,1,1),tile=1.0):
    bpy.ops.mesh.primitive_cylinder_add(vertices=seg,radius=r,depth=h,location=loc,rotation=rot,end_fill_type=cap); o=bpy.context.object; o.scale=scale; return done(o,m,tile)
def sph(m,loc,r,sub=1,scale=(1,1,1),jit=0.0,tile=1.0):
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=sub,radius=r,location=loc); o=bpy.context.object; o.scale=scale
    for v in o.data.vertices: v.co*=1+random.uniform(-jit,jit)
    return done(o,m,tile)
def torus(m,loc,R,r,seg=16,mseg=4,rot=(0,0,0)):
    bpy.ops.mesh.primitive_torus_add(major_segments=seg,minor_segments=mseg,major_radius=R,minor_radius=r,location=loc,rotation=rot); return done(sel_ret(),m)
def sel_ret(): return bpy.context.object
def decal(name,w,h,loc,rot=(math.pi/2,0,0)):
    # плоскость с куском decals.png; по умолчанию смотрит в −Y
    x,y,W,H=DEC[name]; bpy.ops.mesh.primitive_plane_add(size=1,location=loc,rotation=rot); o=bpy.context.object; o.scale=(w,h,1)
    me=o.data; uv=me.uv_layers.active
    for l in me.loops:
        c=me.vertices[l.vertex_index].co; u=(x+(c.x+.5)*W)/1024; v=1-(y+(.5-c.y)*H)/1024; uv.data[l.index].uv=(u,v)
    return done(o,M['dec'])
def prof(m,pts,x0,x1,tile=1.0):
    # замкнутый профиль в плоскости YZ, вытянутый по X
    bm=bmesh.new(); a=[bm.verts.new((x0,y,z)) for y,z in pts]; b=[bm.verts.new((x1,y,z)) for y,z in pts]; n=len(pts)
    for i in range(n): j=(i+1)%n; bm.faces.new([a[i],a[j],b[j],b[i]])
    bm.faces.new(a[::-1]); bm.faces.new(b); bmesh.ops.recalc_face_normals(bm,faces=bm.faces)
    me=bpy.data.meshes.new('p'); bm.to_mesh(me); bm.free(); o=bpy.data.objects.new('p',me); sc.collection.objects.link(o); return done(o,m,tile)
def join(name,parts):
    sel(parts[0])
    for p in parts[1:]: p.select_set(True)
    bpy.ops.object.join(); o=bpy.context.object; o.name=name; o.data.name=name
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.remove_doubles(threshold=.0005); bpy.ops.object.mode_set(mode='OBJECT')
    return o
NODES=[]
# ---------- vault_4m: стена 4 м с пятой свода (сверху свод срезан под вид сверху) ----------
P=[]
P.append(box(M['conc'],-2,2,-.06,.45,0,.5,2))
P.append(box(M['brick'],-2,2,0,.4,.5,2.6,2))
arc=lambda r,c,n:[(c[0]+r*math.cos(t),c[1]+r*math.sin(t)) for t in [i/n*math.pi/2 for i in range(n+1)]]
inner=arc(.9,(-.9,2.6),8); outer=arc(1.3,(-.9,2.6),8)
pts=[(.4,2.6)]+[(p[0],p[1]) for p in inner]  # от стены по дуге
pr=[(.4,2.6),(0,2.6)]+[p for p in inner[1:]]+[(-.9,3.4)]
pr=[(0.4,2.5),(0.4,3.4),(-.9,3.4)]+[ (y,z) for (y,z) in reversed(inner)]
P.append(prof(M['brick'],[(y,min(z,3.4)) for y,z in pr],-2,2,2))
for sx in (-1,1):
    x=sx*1.82
    P.append(box(M['brick'],x-.16,x+.16,-.14,0,.5,2.55,2))
    rib=[(0,2.5),(0,2.55)]+[(y-.12*math.cos(i/8*math.pi/2),z+.0) for i,(y,z) in enumerate(inner[1:],1)]
    ri=arc(.78,(-.9,2.6),8); ro=arc(.9,(-.9,2.6),8)
    P.append(prof(M['conc'],[(y,min(z,3.42)) for y,z in ro]+[(y,min(z,3.42)) for y,z in reversed(ri)],x-.16,x+.16,2))
P.append(cyl(M['rust'],(0,-.26,2.2),.11,4,14,rot=(0,math.pi/2,0)))
for x in (-1.2,1.2): P.append(box(M['steel'],x-.04,x+.04,-.3,0,2.05,2.12))
for i,z in enumerate((1.85,1.9,1.95)): P.append(cyl(M['rub'],(0,-.05-.02*i,z),.022,4,6,rot=(0,math.pi/2,0)))
for i in range(14):
    x=random.uniform(-1.6,1.6); z=random.uniform(.6,2.4); x=round(x/.26)*.26; z=.5+round((z-.5)/.0778)*.0778
    P.append(box(M['brick'],x-.12,x+.12,-.03,0,z,z+.068,2))
P.append(box(M['steel'],.5,.85,-.12,0,1.2,1.62)); P.append(cyl(M['rub'],(.62,-.05,1.78),.015,.36,6))
NODES.append(join('vault_4m',P))
# ---------- bulkhead: бетонная переборка 4 м с круглым проёмом Ø2,24 м (центр на 1,3 м) ----------
DOOR_R=1.05; DOOR_Z=1.4
def annulus(m,c,ri,ro,y,seg=32):
    bm=bmesh.new(); A=[bm.verts.new((c[0]+ri*math.cos(i/seg*2*math.pi),y,c[1]+ri*math.sin(i/seg*2*math.pi))) for i in range(seg)]; B=[bm.verts.new((c[0]+ro*math.cos(i/seg*2*math.pi),y,c[1]+ro*math.sin(i/seg*2*math.pi))) for i in range(seg)]
    for i in range(seg): j=(i+1)%seg; bm.faces.new([A[i],A[j],B[j],B[i]])
    me=bpy.data.meshes.new('an'); bm.to_mesh(me); bm.free(); o=bpy.data.objects.new('an',me); sc.collection.objects.link(o); return done(o,m)
P=[]
w=box(M['conc'],-2,2,0,.5,0,3.4,2); cut=cyl(M['conc'],(0,.25,DOOR_Z),DOOR_R,1.2,32,rot=(math.pi/2,0,0))
bo=w.modifiers.new('b','BOOLEAN'); bo.object=cut; bo.operation='DIFFERENCE'; bo.solver='EXACT'; sel(w); bpy.ops.object.modifier_apply(modifier='b'); bpy.data.objects.remove(cut); boxuv(w,2); P.append(w)
bpy.ops.mesh.primitive_cylinder_add(vertices=32,radius=DOOR_R,depth=.5,location=(0,.25,DOOR_Z),rotation=(math.pi/2,0,0),end_fill_type='NOTHING'); t=bpy.context.object; P.append(done(t,M['steel']))
P.append(torus(M['steel'],(0,-.05,DOOR_Z),DOOR_R+.06,.09,32,6,rot=(math.pi/2,0,0)))
P.append(annulus(M['haz'],(0,DOOR_Z),DOOR_R+.14,DOOR_R+.3,-.012))
P.append(decal('object7',1.76,.55,(0,-.012,3.08)))
P.append(decal('no_entry',.5,.25,(-1.7,-.012,1.35))); P.append(decal('biohazard',.5,.25,(1.7,-.012,1.35)))
P.append(cyl(M['steel'],(1.68,-.07,2.62),.07,.12,10,rot=(math.pi/2,0,0))); P.append(sph(M['warm'],(1.68,-.15,2.62),.06,1))
P.append(cyl(M['steel'],(1.86,-.1,1.7),.07,3.4,10)); P.append(box(M['steel'],-1.95,-1.6,-.12,0,2.25,2.6)); P.append(cyl(M['rub'],(-1.78,-.06,2.95),.02,.7,6))
for k in range(8):
    a=k/8*2*math.pi+math.pi/8; P.append(box(M['steel'],-.05,.05,-.12,0,-.05,.05))
    o=P[-1]; o.location=(math.cos(a)*(DOOR_R+.06),-.06,DOOR_Z+math.sin(a)*(DOOR_R+.06)); sel(o); bpy.ops.object.transform_apply(location=True)
NODES.append(join('bulkhead',P))
# ---------- hermodoor: круглая створка; ось петель в начале координат (x=0, y=0 — плоскость стены), полотно по +X ----------
HR=1.11; cx=HR+.06; P=[]
P.append(cyl(M['steel'],(cx,-.28,DOOR_Z),HR,.16,32,rot=(math.pi/2,0,0)))
P.append(torus(M['steel'],(cx,-.37,DOOR_Z),HR-.05,.05,32,5,rot=(math.pi/2,0,0)))
P.append(cyl(M['glow'],(cx,-.365,DOOR_Z),.3,.01,24,rot=(math.pi/2,0,0))); P.append(cyl(M['glass'],(cx,-.39,DOOR_Z),.32,.01,24,rot=(math.pi/2,0,0)))
P.append(torus(M['rub'],(cx,-.39,DOOR_Z),.34,.04,24,5,rot=(math.pi/2,0,0)))
P.append(torus(M['steel'],(cx,-.46,DOOR_Z),.6,.035,28,5,rot=(math.pi/2,0,0)))
for k in range(4):
    a=k*math.pi/2+math.pi/4; P.append(cyl(M['steel'],(cx+math.cos(a)*.48,-.43,DOOR_Z+math.sin(a)*.48),.022,.26,6,rot=(0,math.pi/2-a,0)))
    o=P[-1]
for z in (DOOR_Z-.75,DOOR_Z+.75):
    P.append(box(M['steel'],0,.32,-.3,0,z-.1,z+.1)); P.append(cyl(M['steel'],(0,-.06,z),.05,.3,10))
for k in range(6):
    a=k/6*2*math.pi; P.append(box(M['haz'],-.07,.07,-.42,-.34,-.07,.07)); o=P[-1]; o.location=(cx+math.cos(a)*(HR-.18),0,DOOR_Z+math.sin(a)*(HR-.18)); sel(o); bpy.ops.object.transform_apply(location=True)
P.append(decal('hermozone',.68,.255,(cx,-.405,DOOR_Z+.78)))
NODES.append(join('hermodoor',P))
# ---------- vat / vat_broken ----------
def vat_base(P,label):
    P.append(cyl(M['steel'],(0,0,.16),.5,.32,16)); P.append(cyl(M['rub'],(0,0,.33),.44,.03,16))
    P.append(decal(label,.42,.21 if label=='vat_label' else .25,(0,-.505,.16)))
P=[]; vat_base(P,'vat_label')
P.append(cyl(M['glass'],(0,0,1.12),.42,1.6,20,cap='NOTHING')); P.append(cyl(M['glow'],(0,0,1.03),.3,1.38,16))

for i in range(9):
    a=random.uniform(0,2*math.pi); rr=random.uniform(.05,.3); P.append(sph(M['glow'] if i%3 else M['glass'],(rr*math.cos(a),rr*math.sin(a),random.uniform(.5,1.7)),random.uniform(.035,.07),1))
P.append(cyl(M['glow'],(0,0,.34),.3,.01,16))
P.append(cyl(M['steel'],(0,0,2.06),.5,.28,16)); P.append(torus(M['glow'],(0,0,2.205),.36,.03,20,4)); P.append(cyl(M['glass'],(0,0,2.205),.33,.006,20)); P.append(cyl(M['rust'],(.22,0,2.45),.06,.5,8)); P.append(cyl(M['rust'],(-.2,.1,2.35),.04,.3,8))
for i in range(3): a=i*2*math.pi/3+.5; P.append(cyl(M['steel'],(.47*math.cos(a),.47*math.sin(a),1.12),.022,1.6,6))
NODES.append(join('vat',P))
P=[]; vat_base(P,'vat_label_03')
bm=bmesh.new(); n=16; lo=[];hi=[]
for i in range(n):
    a=i/n*2*math.pi; lo.append(bm.verts.new((.42*math.cos(a),.42*math.sin(a),.34))); hi.append(bm.verts.new((.42*math.cos(a),.42*math.sin(a),.34+random.uniform(.15,.95)*(1 if i%2 else .55))))
for i in range(n): j=(i+1)%n; bm.faces.new([lo[i],lo[j],hi[j],hi[i]])
me=bpy.data.meshes.new('g'); bm.to_mesh(me); bm.free(); g=bpy.data.objects.new('g',me); sc.collection.objects.link(g); P.append(done(g,M['glass']))
P.append(cyl(M['glow'],(0,0,.37),.38,.04,16))
bm=bmesh.new(); c=bm.verts.new((.15,-.45,.004)); ring=[bm.verts.new((.15+math.cos(i/14*2*math.pi)*random.uniform(.55,.95),-.45+math.sin(i/14*2*math.pi)*random.uniform(.45,.75),.004)) for i in range(14)]
for i in range(14): bm.faces.new([c,ring[i],ring[(i+1)%14]])
me=bpy.data.meshes.new('pd'); bm.to_mesh(me); bm.free(); g=bpy.data.objects.new('pd',me); sc.collection.objects.link(g); P.append(done(g,M['glow']))
P.append(cyl(M['steel'],(.82,.3,.17),.5,.28,16,rot=(.12,.08,0)))   # сорванная крышка на полу
P.append(cyl(M['steel'],(.0,.47,.9),.022,1.2,6,rot=(.35,0,0)))
for i in range(7):
    bm=bmesh.new(); x,y=random.uniform(-.7,.8),random.uniform(-1.0,-.2); v=[bm.verts.new((x+random.uniform(-.09,.09),y+random.uniform(-.09,.09),.006)) for _ in range(3)]; bm.faces.new(v)
    me=bpy.data.meshes.new('sh'); bm.to_mesh(me); bm.free(); g=bpy.data.objects.new('sh',me); sc.collection.objects.link(g); P.append(done(g,M['glass']))
for (x,y,r) in [(-.45,-.35,.12),(-.3,-.55,.08),(.5,-.2,.1)]: P.append(sph(M['fun'],(x,y,r*.4),r,1,scale=(1,1,.6),jit=.2))
NODES.append(join('vat_broken',P))
# ---------- lab_table ----------
P=[box(M['top'],-.9,.9,-.4,.4,.87,.92)]
for x in (-.85,.85):
    for y in (-.35,.35): P.append(box(M['steel'],x-.025,x+.025,y-.025,y+.025,0,.87))
P.append(box(M['steel'],-.85,.85,-.35,.35,.24,.27))
P.append(box(M['steel'],-.75,-.33,-.25,.05,.92,1.24)); P.append(box(M['glow'],-.72,-.36,-.252,-.25,.97,1.2)); P.append(box(M['rub'],-.72,-.36,-.38,-.27,.92,.94))
P.append(box(M['steel'],.05,.45,.1,.22,.92,.97))
for i in range(6):
    x=.09+i*.065; P.append(cyl(M['glass'],(x,.16,1.03),.02,.16,8,cap='NOTHING'))
    if i%3!=2: P.append(cyl(M['glow'] if i%2==0 else M['fun'],(x,.16,.99),.015,.08,8))
for (x,y) in ((.6,-.15),(.32,-.2)):
    bpy.ops.mesh.primitive_cone_add(vertices=10,radius1=.08,radius2=.02,depth=.2,location=(x,y,1.02)); P.append(done(bpy.context.object,M['glass']))
    bpy.ops.mesh.primitive_cone_add(vertices=10,radius1=.07,radius2=.045,depth=.08,location=(x,y,.965)); P.append(done(bpy.context.object,M['glow']))
P.append(box(M['paper'],-.25,.05,-.3,-.08,.92,.925))
P.append(box(M['steel'],-.9,.9,.36,.4,.92,1.5)); P.append(decal('biohazard',.5,.25,(.45,.355,1.25)))
NODES.append(join('lab_table',P))
# ---------- crate_bio ----------
P=[box(M['olive'],-.4,.4,-.3,.3,0,.6)]
for x in (-.4,.4):
    for y in (-.3,.3): P.append(box(M['steel'],x-.03,x+.03,y-.03,y+.03,0,.62))
for z in (.1,.5): P.append(box(M['steel'],-.41,.41,-.31,.31,z-.025,z+.025))
for x in (-.42,.42): P.append(box(M['steel'],x-.015,x+.015,-.08,.08,.36,.42))
P.append(decal('crate_label',.5,.25,(0,-.312,.3))); P.append(decal('crate_label',.56,.28,(0,.08,.605),rot=(0,0,0))); P.append(decal('logo',.2,.2,(-.26,-.19,.605),rot=(0,0,0))); P.append(decal('logo',.22,.22,(.412,0,.3),rot=(math.pi/2,0,math.pi/2)))
NODES.append(join('crate_bio',P))
# ---------- growth_cluster ----------
P=[]
bm=bmesh.new(); c=bm.verts.new((0,0,.01)); ring=[bm.verts.new((math.cos(i/12*2*math.pi)*random.uniform(.5,.75),math.sin(i/12*2*math.pi)*random.uniform(.5,.75),.01)) for i in range(12)]
for i in range(12): bm.faces.new([c,ring[i],ring[(i+1)%12]])
me=bpy.data.meshes.new('gm'); bm.to_mesh(me); bm.free(); g=bpy.data.objects.new('gm',me); sc.collection.objects.link(g); P.append(done(g,M['fun']))
for i in range(6):
    a=random.uniform(0,2*math.pi); d=random.uniform(.05,.42); r=random.uniform(.12,.22); sz=random.uniform(.6,1.0)
    P.append(sph(M['fun'],(math.cos(a)*d,math.sin(a)*d,r*sz*.5),r,2,scale=(1,1,sz),jit=.12))
for i in range(9):
    a=random.uniform(0,2*math.pi); d=random.uniform(.0,.55); h=random.uniform(.15,.55); r=random.uniform(.05,.11); x,y=math.cos(a)*d,math.sin(a)*d
    bpy.ops.mesh.primitive_cone_add(vertices=6,radius1=.035,radius2=.015,depth=h,location=(x,y,h/2)); P.append(done(bpy.context.object,M['fun']))
    P.append(sph(M['glow'],(x,y,h+r*.7),r,2,scale=(1,1,.85)))
NODES.append(join('growth_cluster',P))
# ---------- lamp_cage: крепление к стене в начале координат, лампа выступает в −Y и вниз ----------
P=[box(M['steel'],-.06,.06,-.03,0,-.09,.09),cyl(M['steel'],(0,-.17,0),.018,.28,8,rot=(math.pi/2,0,0)),cyl(M['steel'],(0,-.32,-.04),.045,.08,10),sph(M['warm'],(0,-.32,-.15),.075,2,scale=(1,1,1.25))]
for z in (-.1,-.18,-.25): P.append(torus(M['steel'],(0,-.32,z),.105,.006,12,3))
for i in range(4): a=i*math.pi/2; P.append(cyl(M['steel'],(.105*math.cos(a),-.32+.105*math.sin(a),-.18),.006,.18,4))
P.append(cyl(M['rub'],(0,-.012,.35),.012,.52,6))
NODES.append(join('lamp_cage',P))
# ---------- атлас реквизита: UV по выбранным (props) граням всех узлов + запекание ----------
for o in NODES:
    me=o.data; at=me.uv_layers.new(name='atlas'); me.uv_layers.active=at
bpy.ops.object.select_all(action='DESELECT')
for o in NODES: o.select_set(True)
bpy.context.view_layer.objects.active=NODES[0]; bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='DESELECT'); bpy.ops.object.mode_set(mode='OBJECT')
for o in NODES:
    for p in o.data.polygons: p.select=o.data.materials[p.material_index].name in PROPS
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.003,area_weight=0.0,scale_to_bounds=True); bpy.ops.object.mode_set(mode='OBJECT')
# временные копии только с props-гранями
sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=1
atl=bpy.data.images.new('lab_props',1024,1024)
for mm in [M[k] for k in SRC]:
    nt=mm.node_tree; n=nt.nodes.new('ShaderNodeTexImage'); n.image=atl; n.name='BAKE'
    u=nt.nodes.new('ShaderNodeUVMap'); u.uv_map='atlas'; nt.links.new(u.outputs['UV'],n.inputs['Vector']); nt.nodes.active=n
    s=nt.nodes['SRC']; u2=nt.nodes.new('ShaderNodeUVMap'); u2.uv_map='UVMap'; nt.links.new(u2.outputs['UV'],s.inputs['Vector'])
tmp=[]
for o in NODES:
    sel(o); bpy.ops.object.duplicate(); d=bpy.context.object
    bm=bmesh.new(); bm.from_mesh(d.data); bmesh.ops.delete(bm,geom=[f for f in bm.faces if d.data.materials[f.material_index].name not in PROPS],context='FACES'); bm.to_mesh(d.data); bm.free()
    d.data.uv_layers.active=d.data.uv_layers['atlas']; tmp.append(d)
bpy.ops.object.select_all(action='DESELECT')
for d in tmp: d.select_set(True)
bpy.context.view_layer.objects.active=tmp[0]
bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'},margin=4,uv_layer='atlas')
atl.filepath_raw=OUTDIR+'/lab_props.png'; atl.file_format='PNG'; atl.save()
for d in tmp: bpy.data.objects.remove(d)
pm=mat('lab_props'); nt=pm.node_tree; t=nt.nodes.new('ShaderNodeTexImage'); t.image=atl; nt.links.new(t.outputs['Color'],nt.nodes['Principled BSDF'].inputs['Base Color'])
for k in ('brick','conc','dec','glow','warm','glass'):
    pass
# итог: один UV-слой 'atlas' (для не-props граней в нём лежат исходные тайловые UV), props -> lab_props
for o in NODES:
    me=o.data; me.uv_layers.remove(me.uv_layers['UVMap']); me.uv_layers['atlas'].active_render=True
    names=[]; remap={}
    for i,m in enumerate(me.materials):
        nm=pm if m.name in PROPS else m
        if nm.name not in names: names.append(nm.name)
        remap[i]=names.index(nm.name)
    idx=[remap[p.material_index] for p in me.polygons]
    me.materials.clear()
    for n in names: me.materials.append(bpy.data.materials[n])
    for p,i in zip(me.polygons,idx): p.material_index=i
for k in SRC: M[k].node_tree.nodes.remove(M[k].node_tree.nodes['BAKE'])
# все UV для glTF: материалы с текстурой берут TEXCOORD_0
for m in [M['brick'],M['conc'],M['dec']]:
    for n in m.node_tree.nodes:
        if n.type=='TEX_IMAGE':
            u=m.node_tree.nodes.new('ShaderNodeUVMap'); u.uv_map='atlas'; m.node_tree.links.new(u.outputs['UV'],n.inputs['Vector'])
st={}
for o in NODES:
    sel(o); bpy.ops.object.shade_smooth(); o.data.set_sharp_from_angle(angle=math.radians(40))
    st[o.name]={'tris':sum(len(p.vertices)-2 for p in o.data.polygons),'mats':[m.name for m in o.data.materials],'bbox':[[round(min((o.matrix_world@Vector(c))[i] for c in o.bound_box),3) for i in range(3)],[round(max((o.matrix_world@Vector(c))[i] for c in o.bound_box),3) for i in range(3)]]}
print('STATS',json.dumps(st)); print('TRIS',sum(v['tris'] for v in st.values()))
json.dump(st,open(OUTDIR+'/stats.json','w'))
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb','.blend'))
# корневые узлы-пустышки: квантование meshopt переносит смещение/масштаб в узел меша, а корень остаётся чистым (position.set безопасен)
for o in NODES:
    nm=o.name; o.name=nm+'_mesh'; e=bpy.data.objects.new(nm,None); sc.collection.objects.link(e); o.parent=e
bpy.ops.object.select_all(action='DESELECT')
for o in sc.objects: o.select_set(True)
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',use_selection=True,export_image_format='WEBP',export_image_quality=85,export_yup=True,export_apply=True,export_animations=False,export_vertex_color='NONE')
print('EXPORTED',OUT)
