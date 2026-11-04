import bpy,bmesh,math,sys
from mathutils import Vector,Matrix
from mathutils.bvhtree import BVHTree
import os
SRC=os.environ.get('MUT_SRC','/workspace/art-sewer/cc0')
UBC=SRC+'/ubc/Universal Base Characters[Standard]/Base Characters/Godot - UE/Superhero_Male_FullBody.gltf'
UAL=SRC+'/ual/Universal Animation Library[Standard]/Unreal-Godot/UAL1_Standard.glb'
import os
OUT=os.environ.get('MUT_OUT','/workspace/art-sewer/v3/mutant_raw.glb'); OUTDIR=os.path.dirname(OUT)
SCR_SIGN=float(os.environ.get('SCR_SIGN','-1')); ARM_SIGN=float(os.environ.get('ARM_SIGN','1'))
T=os.environ.get('MUT_TEX','/workspace/art-sewer/v2/tex/')
bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.gltf(filepath=UBC)
for n in ['Eyebrows','Eyes','Icosphere']:
    o=bpy.data.objects.get(n)
    if o: bpy.data.objects.remove(o,do_unlink=True)
arm=[o for o in bpy.data.objects if o.type=='ARMATURE'][0]; arm.name='Rig'
body=bpy.data.objects['SuperHero_Male']; body.name='Body'
arm.data.pose_position='REST'
def sel(o):
    bpy.ops.object.mode_set(mode='OBJECT') if bpy.context.object and bpy.context.object.mode!='OBJECT' else None
    bpy.ops.object.select_all(action='DESELECT'); o.select_set(True); bpy.context.view_layer.objects.active=o
# --- body: delete head, decimate
sel(body); mw=body.matrix_world
bm=bmesh.new(); bm.from_mesh(body.data)
bmesh.ops.delete(bm,geom=[v for v in bm.verts if (mw@v.co).z>1.585],context='VERTS'); bm.to_mesh(body.data); bm.free()
d=body.modifiers.new('dec','DECIMATE'); d.ratio=0.58
bpy.ops.object.modifier_move_to_index(modifier='dec',index=0); bpy.ops.object.modifier_apply(modifier='dec')
# --- materials
def mat(name,tex=None,rough=.8,metal=0,col=(1,1,1,1),normal=None,emis=None):
    m=bpy.data.materials.new(name); m.use_nodes=True; nt=m.node_tree; p=nt.nodes['Principled BSDF']
    p.inputs['Roughness'].default_value=rough; p.inputs['Metallic'].default_value=metal; p.inputs['Base Color'].default_value=col
    if tex:
        t=nt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(T+tex); nt.links.new(t.outputs['Color'],p.inputs['Base Color'])
    if normal:
        t=nt.nodes.new('ShaderNodeTexImage'); t.image=bpy.data.images.load(T+normal); t.image.colorspace_settings.name='Non-Color'
        nm=nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(t.outputs['Color'],nm.inputs['Color']); nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
    if emis: p.inputs['Emission Color'].default_value=emis; p.inputs['Emission Strength'].default_value=1.0
    return m
M=dict(skin=mat('skin','skin.png',.75,normal='skin_n.png'),vat=mat('vatnik','vatnik.png',.95),pla=mat('plastron','plastron.png',.7),
 car=mat('carapace','carapace.png',.6),scu=mat('scute','carapace.png',.55,col=(.75,.72,.6,1)),grip=mat('grip',None,.8,col=(.32,.08,.05,1)),ban=mat('bandana','bandana.png',.85),kha=mat('khaki','khaki.png',.9),met=mat('rustmetal','rustmetal.png',.45,.7),
 pat=mat('patch','patch.png',.8),eye=mat('eyes',None,.3,col=(.92,.92,.85,1),emis=(.25,.25,.22,1)),rub=mat('rubber',None,.6,col=(.06,.07,.065,1)),
 lea=mat('leather',None,.7,col=(.10,.06,.035,1)),brass=mat('brass',None,.35,.8,col=(.55,.42,.18,1)),glass=mat('glass',None,.1,col=(.25,.3,.28,1)))
body.data.materials.clear(); body.data.materials.append(M['skin'])
# --- helpers
dg=bpy.context.evaluated_depsgraph_get()
def bvh(o): return BVHTree.FromObject(o,bpy.context.evaluated_depsgraph_get())
def finish(o,m,bone=None,transfer=False,wfun=None):
    o.data.materials.clear(); o.data.materials.append(m)
    sel(o); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
    if bone:
        g=o.vertex_groups.new(name=bone); g.add(range(len(o.data.vertices)),1.0,'REPLACE')
    if wfun:
        for v in o.data.vertices:
            for b,w in wfun(v.co):
                g=o.vertex_groups.get(b) or o.vertex_groups.new(name=b); g.add([v.index],w,'REPLACE')
    if transfer:
        dt=o.modifiers.new('dt','DATA_TRANSFER'); dt.object=body; dt.use_vert_data=True; dt.data_types_verts={'VGROUP_WEIGHTS'}
        dt.vert_mapping='POLYINTERP_NEAREST'; dt.layers_vgroup_select_src='ALL'; dt.layers_vgroup_select_dst='NAME'
        bpy.ops.object.datalayout_transfer(modifier='dt'); bpy.ops.object.modifier_apply(modifier='dt')
    o.parent=arm; a=o.modifiers.new('arm','ARMATURE'); a.object=arm
    return o
def sphere(name,loc,scale,seg=16,ring=10,rot=(0,0,0)):
    bpy.ops.mesh.primitive_uv_sphere_add(segments=seg,ring_count=ring,location=loc,rotation=rot); o=bpy.context.object; o.name=name; o.scale=scale; return o
def cyl(name,loc,r,depth,seg=12,rot=(0,0,0),scale=(1,1,1),cap='NGON'):
    bpy.ops.mesh.primitive_cylinder_add(vertices=seg,radius=r,depth=depth,location=loc,rotation=rot,end_fill_type=cap); o=bpy.context.object; o.name=name; o.scale=scale; return o
def box(name,loc,size,rot=(0,0,0)):
    bpy.ops.mesh.primitive_cube_add(location=loc,rotation=rot); o=bpy.context.object; o.name=name; o.scale=(size[0]/2,size[1]/2,size[2]/2); return o
def tube(name,pts,r,seg=6):
    bm=bmesh.new(); rings=[]
    for i,p in enumerate(pts):
        p=Vector(p); t=(Vector(pts[min(i+1,len(pts)-1)])-Vector(pts[max(i-1,0)])).normalized()
        u=t.orthogonal().normalized(); v=t.cross(u)
        rr=r[i] if isinstance(r,(list,tuple)) else r
        rings.append([bm.verts.new(p+(u*math.cos(a)+v*math.sin(a))*rr) for a in [k*2*math.pi/seg for k in range(seg)]])
    for a,b in zip(rings,rings[1:]):
        for k in range(seg): bm.faces.new([a[k],a[(k+1)%seg],b[(k+1)%seg],b[k]])
    bm.faces.new(rings[-1][::-1]); bm.faces.new(rings[0])
    me=bpy.data.meshes.new(name); bm.to_mesh(me); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o); return o
def ring_band(name,c,axis,ref,h,off,n=20,tree=None,rad=.6):
    tree=tree or bvh(body); c=Vector(c); a=Vector(axis).normalized(); u=Vector(ref).normalized(); v=a.cross(u)
    bm=bmesh.new(); rows=[]
    for s in (-h/2,h/2):
        row=[]
        for k in range(n):
            ang=2*math.pi*k/n; dv=u*math.cos(ang)+v*math.sin(ang); o=c+a*s+dv*rad
            hit=tree.ray_cast(o,-dv,rad); p=(hit[0] if hit[0] else c+a*s+dv*.1)+dv*off
            row.append(bm.verts.new(p))
        rows.append(row)
    for k in range(n): bm.faces.new([rows[0][k],rows[0][(k+1)%n],rows[1][(k+1)%n],rows[1][k]])
    bm.normal_update(); me=bpy.data.meshes.new(name); bm.to_mesh(me); o=bpy.data.objects.new(name,me); bpy.context.collection.objects.link(o)
    sel(o); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.mesh.normals_make_consistent(inside=False)
    bpy.ops.uv.cylinder_project(); bpy.ops.object.mode_set(mode='OBJECT'); return o
parts=[]
# --- head (turtle)
h=sphere('Head',(0,-.012,1.70),(.10,.125,.115),24,16); s2=sphere('Snout',(0,-.085,1.662),(.082,.075,.058),20,12)
s3=sphere('Brow',(0,-.085,1.738),(.088,.055,.03),16,8); s4=sphere('Jaw',(0,-.06,1.628),(.075,.075,.035),16,8)
sel(h)
for o in (s2,s3,s4): o.select_set(True)
bpy.ops.object.join(); bpy.ops.object.transform_apply(location=True,rotation=True,scale=True)
rm=h.modifiers.new('rm','REMESH'); rm.mode='VOXEL'; rm.voxel_size=.007; bpy.ops.object.modifier_apply(modifier='rm')
sm=h.modifiers.new('sm','SMOOTH'); sm.iterations=6; sm.factor=.6; bpy.ops.object.modifier_apply(modifier='sm')
dc=h.modifiers.new('dc','DECIMATE'); dc.ratio=max(.05,900/max(1,len(h.data.polygons)*2)); bpy.ops.object.modifier_apply(modifier='dc')
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(angle_limit=1.2); bpy.ops.object.mode_set(mode='OBJECT')
bpy.ops.object.shade_smooth()
parts.append(finish(h,M['skin'],'Head'))
for sx in (-1,1): parts.append(finish(sphere('Nostril',(sx*.016,-.158,1.676),(.007,.004,.005),6,4),M['rub'],'Head'))
# mouth line
parts.append(finish(tube('Mouth',[(-.072,-.1,1.638),(-.045,-.142,1.632),(0,-.153,1.63),(.045,-.142,1.632),(.072,-.1,1.638)],.0045,5),M['rub'],'Head'))
# bandana band + eyes + knot + tails
bpy.ops.mesh.primitive_cylinder_add(vertices=28,radius=1,depth=1,location=(0,-.012,1.72),end_fill_type='NOTHING'); b=bpy.context.object; b.name='Bandana'; b.scale=(.108,.134,.046)
parts.append(finish(b,M['ban'],'Head'))
for sx in (-1,1):
    e=sphere('Eye',(sx*.043,-.143,1.722),(.024,.009,.013),12,8,rot=(0,0,-sx*.32)); parts.append(finish(e,M['eye'],'Head'))
k=sphere('Knot',(0,.125,1.72),(.025,.02,.022),10,6); parts.append(finish(k,M['ban'],'Head'))
for sx in (-1,1):
    pts=[(sx*.012,.135,1.72),(sx*.04,.19,1.66),(sx*.06,.235,1.57),(sx*.07,.25,1.47)]
    bm=bmesh.new(); prev=None
    for i,p in enumerate(pts):
        w=.022-.004*i; a=bm.verts.new((p[0]-w,p[1],p[2])); c=bm.verts.new((p[0]+w,p[1],p[2]))
        if prev: bm.faces.new([prev[0],prev[1],c,a])
        prev=(a,c)
    me=bpy.data.meshes.new('Tail'); bm.to_mesh(me); o=bpy.data.objects.new('Tail',me); bpy.context.collection.objects.link(o)
    sm=o.modifiers.new('s','SOLIDIFY'); sm.thickness=.006; sel(o); bpy.ops.object.modifier_apply(modifier='s')
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT')
    parts.append(finish(o,M['ban'],'Head'))
# --- carapace
def spine_w(co):
    z=co.z
    if z>1.36: return [('spine_03',1.0)]
    if z>1.16: t=(z-1.16)/.2; return [('spine_03',t),('spine_02',1-t)]
    t=max(0,(z-1.0)/.16); return [('spine_02',t),('spine_01',1-t)]
car=sphere('Carapace',(0,.085,1.24),(.255,.165,.33),24,16)
bm=bmesh.new(); bm.from_mesh(car.data); bmesh.ops.delete(bm,geom=[v for v in bm.verts if (car.matrix_world@v.co).y<0.0],context='VERTS'); bm.to_mesh(car.data); bm.free()
parts.append(finish(car,M['car'],wfun=spine_w))
# bolted rust plate on carapace
pl=box('Plate',(.09,.255,1.12),(.12,.012,.1),rot=(0,0,.25)); parts.append(finish(pl,M['met'],wfun=spine_w))
ct=BVHTree.FromObject(car,bpy.context.evaluated_depsgraph_get())
for (x,z,r) in [(0,1.5,.06),(0,1.37,.065),(0,1.24,.065),(0,1.11,.06),(0,.99,.05),(.135,1.43,.055),(-.135,1.43,.055),(.15,1.27,.06),(-.15,1.27,.06),(.14,1.1,.055),(-.14,1.1,.055)]:
    hit=ct.ray_cast(Vector((x,.8,z)),Vector((0,-1,0)),2)
    if not hit[0]: continue
    bpy.ops.mesh.primitive_cylinder_add(vertices=6,radius=r,depth=.016,location=hit[0]+hit[1]*.004); sc=bpy.context.object; sc.name='Scute'
    sc.rotation_mode='QUATERNION'; sc.rotation_quaternion=Vector((0,0,1)).rotation_difference(hit[1]); sc.scale=(1,.85,1)
    parts.append(finish(sc,M['scu'],wfun=spine_w))
# --- plastron: duplicate torso front faces
sel(body); bpy.ops.object.duplicate(); pla=bpy.context.object; pla.name='Plastron'
for m in list(pla.modifiers): pla.modifiers.remove(m)
bm=bmesh.new(); bm.from_mesh(pla.data)
keep=[f for f in bm.faces if .95<f.calc_center_median().z<1.47 and abs(f.calc_center_median().x)<.13 and f.normal.y<-.25]
bmesh.ops.delete(bm,geom=[f for f in bm.faces if f not in set(keep)],context='FACES')
for v in bm.verts: v.co+=v.normal*.008
uv=bm.loops.layers.uv.active or bm.loops.layers.uv.new()
for f in bm.faces:
    for l in f.loops: l[uv].uv=(l.vert.co.x*2+.5,(l.vert.co.z-.95)*1.9)
bm.to_mesh(pla.data); bm.free(); pla.data.materials.clear(); pla.data.materials.append(M['pla']); pla.parent=arm; pla.modifiers.new('arm','ARMATURE').object=arm; parts.append(pla)
# --- vatnik: cylinder shrinkwrapped on body+carapace
sel(body); bpy.ops.object.duplicate(); tgt=bpy.context.object
for m in list(tgt.modifiers): tgt.modifiers.remove(m)
sel(car); bpy.ops.object.duplicate(); c2=bpy.context.object
for m in list(c2.modifiers): c2.modifiers.remove(m)
c2.parent=None
sel(tgt); c2.select_set(True); bpy.ops.object.join(); tgt.name='WrapTarget'
bm=bmesh.new(); NS,NR=36,14; grid=[]
for r in range(NR+1):
    z=.955+.58*r/NR; grid.append([bm.verts.new((.42*math.sin(2*math.pi*k/NS),.03-.42*math.cos(2*math.pi*k/NS),z)) for k in range(NS)])
uvl=bm.loops.layers.uv.new()
for r in range(NR):
    for k in range(NS):
        f=bm.faces.new([grid[r][k],grid[r][(k+1)%NS],grid[r+1][(k+1)%NS],grid[r+1][k]])
        for l,(uu,vv) in zip(f.loops,[(k,r),(k+1,r),(k+1,r+1),(k,r+1)]): l[uvl].uv=(uu/NS*3,vv/NR*1.6)
me=bpy.data.meshes.new('Vatnik'); bm.to_mesh(me); bm.free(); v=bpy.data.objects.new('Vatnik',me); bpy.context.collection.objects.link(v)
bm=bmesh.new(); bm.from_mesh(v.data)
dead=[]
for f in bm.faces:
    c=v.matrix_world@f.calc_center_median(); ang=math.degrees(math.atan2(c.x,-(c.y-.03)))  # 0=front
    if abs(ang)<26-8*max(0,(c.z-1.3)/.25): dead.append(f)                                   # open front
    elif abs(abs(ang)-90)<34 and c.z>1.36: dead.append(f)             # armholes
    elif abs(abs(ang)-180)<22 and 1.06<c.z<1.27 and (abs(ang)>170 or c.z>1.1): dead.append(f)  # torn hole on back
bmesh.ops.delete(bm,geom=dead,context='FACES'); bm.to_mesh(v.data); bm.free()
sw=v.modifiers.new('sw','SHRINKWRAP'); sw.target=tgt; sw.wrap_method='PROJECT'; sw.use_project_x=False; sw.use_negative_direction=True; sw.use_positive_direction=True; sw.offset=.028
sel(v); bpy.ops.object.modifier_apply(modifier='sw')

sel(v); bpy.ops.object.shade_smooth()
parts.append(finish(v,M['vat'],transfer=True))
bpy.ops.mesh.primitive_torus_add(major_segments=18,minor_segments=6,major_radius=.095,minor_radius=.028,location=(0,.015,1.51)); co=bpy.context.object; co.name='Collar'; co.scale=(1.05,1.0,.8)
bpy.ops.object.shade_smooth()
bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT')
parts.append(finish(co,M['vat'],transfer=True))
# patch on left chest
vt=bvh(v); hit=vt.ray_cast(Vector((.11,-.6,1.36)),Vector((0,1,0)),1)
if hit[0]:
    p=hit[0]+hit[1]*.004; bpy.ops.mesh.primitive_plane_add(size=1,location=p); pt=bpy.context.object; pt.name='Patch'; pt.scale=(.1,.05,1)
    pt.rotation_mode='QUATERNION'; pt.rotation_quaternion=Vector((0,0,1)).rotation_difference(hit[1])
    parts.append(finish(pt,M['pat'],'spine_03'))
# --- belt, buckle, pouch, gas mask
tb=bvh(body)
bt=ring_band('Belt',(0,.02,.99),(0,0,1),(1,0,0),.05,.012,24,tb); parts.append(finish(bt,M['lea'],transfer=True))
hb=tb.ray_cast(Vector((0,-.6,.99)),Vector((0,1,0)),1)[0]
parts.append(finish(box('Buckle',(0,hb.y-.018,.99),(.06,.012,.045)),M['brass'],'pelvis'))
parts.append(finish(box('Pouch',(-.17,-.05,.93),(.1,.055,.11),rot=(0,0,.5)),M['kha'],'pelvis'))
parts.append(finish(box('PouchFlap',(-.172,-.062,.975),(.105,.06,.03),rot=(0,0,.5)),M['kha'],'pelvis'))
gm=sphere('GasMask',(.185,-.04,.9),(.05,.035,.065),14,10,rot=(0,0,-.4)); parts.append(finish(gm,M['rub'],'pelvis'))
for dz in (.02,):
    for sx in (-1,1):
        parts.append(finish(cyl('MaskEye',(.185+sx*.022-.01,-.073+sx*.006,.915),.016,.01,12,rot=(math.pi/2,0,-.4)),M['glass'],'pelvis'))
parts.append(finish(cyl('MaskFilter',(.18,-.075,.855),.026,.05,12,rot=(math.pi/2-.4,0,-.4)),M['kha'],'pelvis'))
parts.append(finish(tube('MaskStrap',[(.17,-.03,.96),(.17,-.02,.99)],.006,5),M['rub'],'pelvis'))
# --- knee pads & forearm wraps
for sx in (-1,1):
    kh=tb.ray_cast(Vector((sx*.105,-.6,.5)),Vector((0,1,0)),1)[0]
    kp=sphere('KneePad',(kh.x,kh.y+.016,kh.z+.005),(.058,.028,.07),12,8); parts.append(finish(kp,M['lea'],'calf_l' if sx>0 else 'calf_r'))
    fw=ring_band('Wrap',(sx*.56,.065,1.456),(1,0,0),(0,1,0),.12,.007,12,tb,.12); parts.append(finish(fw,M['kha'],'lowerarm_l' if sx>0 else 'lowerarm_r'))
# --- sai (in hands), blade along -Y (forward) at rest
def sai(name,hand,grip):
    g=Vector(grip); objs=[]
    hdl=cyl('h',g+Vector((0,.06,0)),.015,.12,8,rot=(math.pi/2,0,0))
    objs.append(sphere('pm',g+Vector((0,.125,0)),(.02,.02,.02),8,6))
    objs.append(tube('bl',[g+Vector((0,0,0)),g+Vector((0,-.2,0)),g+Vector((0,-.38,0))],[.012,.010,.0015],8))
    for sx in (-1,1):
        objs.append(tube('yk',[g+Vector((0,-.005,0)),g+Vector((0,-.02,sx*.04)),g+Vector((0,-.085,sx*.05))],[.0075,.007,.0025],6))
    sel(objs[0])
    for o in objs: o.select_set(True)
    bpy.ops.object.join(); o=bpy.context.object; o.name=name
    sel(hdl); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT'); parts.append(finish(hdl,M['grip'],hand)); sel(o)
    bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT'); bpy.ops.uv.smart_project(); bpy.ops.object.mode_set(mode='OBJECT')
    return finish(o,M['met'],hand)
hr=arm.matrix_world@arm.data.bones['hand_r'].head_local; hl=arm.matrix_world@arm.data.bones['hand_l'].head_local
parts.append(sai('Sai_R','hand_r',hr+Vector((-.075,0,-.025)))); parts.append(sai('Sai_L','hand_l',hl+Vector((.075,0,-.025))))
# cleanup temp
bpy.data.objects.remove(tgt,do_unlink=True)
# --- join everything into one skinned mesh
for p in parts: pass
sel(body)
for p in parts: p.select_set(True)
bpy.ops.object.join(); body.name='Rafael'
# drop leaf bones
sel(arm); bpy.ops.object.mode_set(mode='EDIT')
for b in [b for b in arm.data.edit_bones if 'leaf' in b.name]: arm.data.edit_bones.remove(b)
bpy.ops.object.mode_set(mode='OBJECT')
leafs={g.index:g for g in body.vertex_groups if 'leaf' in g.name}
par={'ball_leaf_l':'ball_l','ball_leaf_r':'ball_r'}
for g in leafs.values():
    n=g.name; par.setdefault(n,n.replace('_04_leaf_','_03_'))
for v in body.data.vertices:
    for ge in list(v.groups):
        if ge.group in leafs and ge.weight>0:
            body.vertex_groups[par[leafs[ge.group].name]].add([v.index],ge.weight,'ADD')
for g in list(leafs.values()): body.vertex_groups.remove(g)
zero=sum(1 for v in body.data.vertices if sum(ge.weight for ge in v.groups)<1e-4); print('ZEROW',zero)
# --- animations from UAL1 (CC0)
before=set(bpy.data.actions.keys()); before_obj=set(bpy.data.objects.keys())
bpy.ops.import_scene.gltf(filepath=UAL)
for n in set(bpy.data.objects.keys())-before_obj: bpy.data.objects.remove(bpy.data.objects[n],do_unlink=True)
new=[a for a in bpy.data.actions if a.name not in before]
print('UAL actions sample',[a.name for a in new][:6])
MAP={'idle':'Sword_Idle','walk':'Walk_Loop','run':'Jog_Fwd_Loop','attack':'Sword_Attack','attack2':'Punch_Cross','hit':'Hit_Chest','death':'Death01','crawl':'Crouch_Fwd_Loop','_crouch':'Crouch_Idle_Loop'}
keep=[]
for dst,src in MAP.items():
    a=next((x for x in new if x.name==src or x.name.startswith(src+'_') or x.name.startswith(src+'.')),None)
    if a: a.name=dst; a.use_fake_user=True; keep.append(a)
    else: print('MISSING',src)
for a in new:
    if a not in keep: bpy.data.actions.remove(a)
for a in keep:
    for fc in [fc for fc in a.fcurves if 'leaf' in fc.data_path]: a.fcurves.remove(fc)
from mathutils import Quaternion
FPS=bpy.context.scene.render.fps
def pose_at(act,fr):
    P={}
    for fc in act.fcurves:
        if not fc.data_path.startswith('pose.bones'): continue
        b=fc.data_path.split('"')[1]; prop=fc.data_path.rsplit('.',1)[1]
        P.setdefault(b,{}).setdefault(prop,[0,0,0,0] if prop=='rotation_quaternion' else [0,0,0])[fc.array_index]=fc.evaluate(fr)
    return P
def blend(A,B,t):
    O={}
    for b in A:
        O[b]={}
        for p,v in A[b].items():
            w=B.get(b,{}).get(p,v)
            if p=='rotation_quaternion':
                qa=Quaternion(v); qb=Quaternion(w)
                if qa.dot(qb)<0: qb.negate()
                O[b][p]=list(qa.slerp(qb,t))
            else: O[b][p]=[x+(y-x)*t for x,y in zip(v,w)]
    return O
def write(name,frames):
    act=bpy.data.actions.new(name); act.use_fake_user=True; act.id_root='OBJECT'; curves={}
    for fr,P in frames:
        for b,props in P.items():
            for p,v in props.items():
                for i,x in enumerate(v):
                    k=(b,p,i)
                    if k not in curves: curves[k]=act.fcurves.new(f'pose.bones["{b}"].{p}',index=i,action_group=b)
                    curves[k].keyframe_points.insert(fr,x,options={'FAST'})
    keep.append(act); return act
def addrot(P,b,axis,ang):
    if b in P and 'rotation_quaternion' in P[b]:
        q=Quaternion(P[b]['rotation_quaternion'])@Quaternion(axis,ang); P[b]['rotation_quaternion']=list(q)
sm=lambda x:0 if x<=0 else 1 if x>=1 else x*x*(3-2*x)
idle=bpy.data.actions['idle']; crouch=bpy.data.actions['_crouch']
i0=idle.frame_range[0]
# scream: 1.6 s roar — head and chest up, arms open, small shake
fr=[]
for f in range(0,int(1.6*FPS)+1,2):
    t=f/FPS; e=sm(t/.35)*(1-sm((t-1.15)/.45)); P=pose_at(idle,i0+f*.5)
    sh=math.sin(t*38)*.04*e
    addrot(P,'spine_03',(1,0,0),SCR_SIGN*(.32*e)); addrot(P,'neck_01',(1,0,0),SCR_SIGN*(.22*e)); addrot(P,'Head',(1,0,0),SCR_SIGN*(.38*e)+sh)
    addrot(P,'upperarm_l',(0,0,1),ARM_SIGN*.55*e); addrot(P,'upperarm_r',(0,0,1),-ARM_SIGN*.55*e)
    fr.append((f,P))
write('scream',fr)
# emerge: rises from water (pelvis -1.1 m), from crouch to fighting stance, 2.0 s
fr=[]; c0=crouch.frame_range[0]
for f in range(0,int(2.0*FPS)+1,2):
    t=f/FPS; P=blend(pose_at(crouch,c0+f*.5),pose_at(idle,i0),sm((t-.7)/1.0))
    if 'pelvis' in P and 'location' in P['pelvis']: P['pelvis']['location'][1]+=-1.1*(1-sm(t/1.3))
    addrot(P,'spine_03',(1,0,0),-SCR_SIGN*.35*(1-sm((t-.5)/1.0)))
    fr.append((f,P))
write('emerge',fr)
keep=[a for a in keep if a!=crouch]; bpy.data.actions.remove(crouch)
arm.animation_data_create(); arm.animation_data.action=bpy.data.actions['idle']
# ---- bake single atlas
sc=bpy.context.scene; sc.render.engine='CYCLES'; sc.cycles.device='CPU'; sc.cycles.samples=4; sc.cycles.bake_type='DIFFUSE'
arm.data.pose_position='REST'
me=body.data; src_uv=me.uv_layers[0]; src_uv.active_render=True
at=me.uv_layers.new(name='atlas'); me.uv_layers.active=at
sel(body); bpy.ops.object.mode_set(mode='EDIT'); bpy.ops.mesh.select_all(action='SELECT')
bpy.ops.uv.smart_project(angle_limit=math.radians(60),island_margin=.004,area_weight=0.0,scale_to_bounds=True); bpy.ops.object.mode_set(mode='OBJECT')
img=bpy.data.images.new('mutant_d',1024,1024); imgn=bpy.data.images.new('mutant_n',512,512); imgn.colorspace_settings.name='Non-Color'
def target(im):
    for m in me.materials:
        nt=m.node_tree; p=nt.nodes['Principled BSDF']; p.inputs['Metallic'].default_value=0
        n=nt.nodes.get('BAKE') or nt.nodes.new('ShaderNodeTexImage'); n.name='BAKE'; n.image=im
        uvn=nt.nodes.get('BAKEUV') or nt.nodes.new('ShaderNodeUVMap'); uvn.name='BAKEUV'; uvn.uv_map='atlas'; nt.links.new(uvn.outputs['UV'],n.inputs['Vector'])
        nt.nodes.active=n; n.select=True
target(img); bpy.ops.object.bake(type='DIFFUSE',pass_filter={'COLOR'},margin=4,uv_layer='atlas')
target(imgn); bpy.ops.object.bake(type='NORMAL',normal_space='TANGENT',margin=4,uv_layer='atlas')
img.filepath_raw=OUTDIR+'/mutant_d.png'; img.file_format='PNG'; img.save(); imgn.filepath_raw=OUTDIR+'/mutant_n.png'; imgn.file_format='PNG'; imgn.save()
fm=bpy.data.materials.new('mutant'); fm.use_nodes=True; fm.use_backface_culling=False; nt=fm.node_tree; p=nt.nodes['Principled BSDF']
p.inputs['Roughness'].default_value=.85; p.inputs['Metallic'].default_value=0
t1=nt.nodes.new('ShaderNodeTexImage'); t1.image=img; nt.links.new(t1.outputs['Color'],p.inputs['Base Color'])
t2=nt.nodes.new('ShaderNodeTexImage'); t2.image=imgn; nm=nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(t2.outputs['Color'],nm.inputs['Color']); nt.links.new(nm.outputs['Normal'],p.inputs['Normal'])
me.materials.clear(); me.materials.append(fm)
for poly in me.polygons: poly.material_index=0
me.uv_layers.remove(me.uv_layers[0]); me.uv_layers['atlas'].active=True; me.uv_layers['atlas'].active_render=True
arm.data.pose_position='POSE'
body.data.name='Rafael'; body.name='Rafael'
tris=sum(len(p.vertices)-2 for p in body.data.polygons)
print('TRIS',tris,'BONES',len(arm.data.bones),'MATS',len(body.data.materials),'ACTIONS',[a.name for a in keep])
bpy.ops.wm.save_as_mainfile(filepath=OUT.replace('.glb','.blend'))
sel(arm); body.select_set(True)
for a in list(bpy.data.actions):
    if a not in keep: bpy.data.actions.remove(a)
bpy.ops.export_scene.gltf(filepath=OUT,export_format='GLB',use_selection=True,export_animation_mode='ACTIONS',export_image_format='WEBP',export_image_quality=82,export_yup=True,export_skins=True,export_apply=False,export_force_sampling=True,export_frame_step=2,export_vertex_color='NONE')
print('EXPORTED',OUT)
