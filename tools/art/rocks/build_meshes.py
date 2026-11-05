"""Build closed native rock meshes from pinned CC0 glTF sources, Blender 4.3.2.

blender -b --python-exit-code 1 --python tools/art/rocks/build_meshes.py -- --output /tmp/terra-rocks
"""
import argparse
import base64
from collections import Counter
import hashlib
import json
from pathlib import Path
import struct
import sys

import bmesh
import bpy
from mathutils import Vector

ROOT=Path(__file__).resolve().parent
parser=argparse.ArgumentParser();parser.add_argument('--output',type=Path,required=True)
options=parser.parse_args(sys.argv[sys.argv.index('--')+1:]);options.output.mkdir(parents=True,exist_ok=True)
(options.output/'entries.json').unlink(missing_ok=True)
layout=json.loads((ROOT/'native-layout.json').read_text())
lock=json.loads((ROOT/'source-lock.json').read_text());sources={s['file']:s for s in lock['files']}


def topology(mesh):
    mesh.calc_loop_triangles();edges=Counter()
    for face in mesh.loop_triangles:
        points=[tuple(round(v,7) for v in mesh.vertices[i].co) for i in face.vertices]
        for a,b in zip(points,points[1:]+points[:1]):edges[tuple(sorted((a,b)))]+=1
    return {'triangles':len(mesh.loop_triangles),'boundaryEdges':sum(v==1 for v in edges.values()),
            'nonManifoldEdges':sum(v>2 for v in edges.values())}


def fit(mesh,target):
    low=Vector(tuple(min(v.co[i] for v in mesh.vertices) for i in range(3)))
    high=Vector(tuple(max(v.co[i] for v in mesh.vertices) for i in range(3)))
    extent=high-low;center=(low+high)*.5
    for vertex in mesh.vertices:
        v=vertex.co;v.x=(v.x-center.x)*target['w']/extent.x
        v.y=(v.y-center.y)*target['d']/extent.y;v.z=(v.z-low.z)*target['h']/extent.z
    mesh.update()


entries={}
for name,settings in layout.items():
    path=ROOT/'sources'/settings['source'];source=sources[settings['source']];raw=path.read_bytes()
    assert len(raw)==source['bytes'] and hashlib.sha256(raw).hexdigest()==source['sha256'],name
    assert hashlib.sha1(('blob '+str(len(raw))+'\0').encode()+raw).hexdigest()==source['blob'],name
    target=settings['layout'];bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    vertices=[];faces=[]
    for original in [o for o in bpy.context.scene.objects if o.type=='MESH']:
        mesh=original.data;mesh.calc_loop_triangles();offset=len(vertices)
        vertices.extend([original.matrix_world@v.co for v in mesh.vertices])
        faces.extend([tuple(offset+i for i in face.vertices) for face in mesh.loop_triangles])
    for original in list(bpy.context.scene.objects):bpy.data.objects.remove(original,do_unlink=True)
    mesh=bpy.data.meshes.new(name);mesh.from_pydata(vertices,[],faces);mesh.update()
    bm=bmesh.new();bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=1e-6)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    source_topology=topology(mesh)
    if source_topology['boundaryEdges'] or source_topology['nonManifoldEdges']:raise ValueError('Source is open: '+name)
    # Weather the old pack's stepped terraces before fitting. Two restrained
    # neighbour passes keep its asymmetry without a stack-of-boxes silhouette.
    bm=bmesh.new();bm.from_mesh(mesh)
    for _ in range(2):bmesh.ops.smooth_vert(bm,verts=list(bm.verts),factor=.45,use_axis_x=True,use_axis_y=True,use_axis_z=True)
    bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free()
    fit(mesh,target)
    obj=bpy.data.objects.new(name,mesh);bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active=obj;obj.select_set(True)
    original=mesh.copy();budget=target['t']-96
    for attempt in range(6):
        obj.data=original.copy();obj.modifiers.clear()
        if source_topology['triangles']>budget:
            modifier=obj.modifiers.new('Connected collapse','DECIMATE');modifier.decimate_type='COLLAPSE'
            modifier.ratio=budget/source_topology['triangles'];modifier.use_collapse_triangulate=True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh=obj.data;bm=bmesh.new();bm.from_mesh(mesh)
        candidates=[e for e in bm.edges if len(e.link_faces)==2 and e.calc_face_angle(0)>.5]
        candidates.sort(key=lambda e:e.calc_length(),reverse=True)
        bmesh.ops.bevel(bm,geom=candidates[:16],offset=min(target['w'],target['h'],target['d'])*.008,
                        segments=1,affect='EDGES',clamp_overlap=True)
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();fit(mesh,target)
        # Audit the int16 grid actually shipped, including bevel slivers.
        step=target['s'];bm=bmesh.new();bm.from_mesh(mesh)
        for vertex in bm.verts:vertex.co=Vector(tuple(round(v/step)*step for v in vertex.co))
        bmesh.ops.remove_doubles(bm,verts=list(bm.verts),dist=step*.1)
        bmesh.ops.dissolve_degenerate(bm,edges=list(bm.edges),dist=step*.1)
        bmesh.ops.triangulate(bm,faces=list(bm.faces),quad_method='BEAUTY',ngon_method='BEAUTY')
        bmesh.ops.recalc_face_normals(bm,faces=list(bm.faces));bm.to_mesh(mesh);bm.free();mesh.update()
        result=topology(mesh)
        if result['boundaryEdges'] or result['nonManifoldEdges']:raise ValueError('Packed rock is open: '+name)
        excess=result['triangles']-target['t']
        if excess<=0:break
        budget-=excess+8
    else:raise ValueError('Triangle budget exceeded: '+name)
    mesh.name=name;material=bpy.data.materials.new('native-rock-paint')
    material.diffuse_color=tuple((c/255)**2.2 for c in settings['paint'])+(1,);mesh.materials.append(material)
    packed=bytearray()
    for face in mesh.loop_triangles:
        points=[Vector((mesh.vertices[i].co.x,mesh.vertices[i].co.z,-mesh.vertices[i].co.y)) for i in face.vertices]
        normal=(points[1]-points[0]).cross(points[2]-points[0])
        if normal.length<1e-10:raise ValueError('Degenerate triangle: '+name)
        normal.normalize();positions=[round(v/target['s']) for p in points for v in p]
        if max(map(abs,positions))>32767:raise ValueError('Quantisation overflow: '+name)
        packed.extend(struct.pack('<9h3b3B',*positions,*[max(-127,min(127,round(v*127))) for v in normal],*settings['paint']))
    bpy.ops.export_scene.gltf(filepath=str(options.output/(name+'.glb')),export_format='GLB',use_selection=True,
                             export_materials='EXPORT',export_draco_mesh_compression_enable=False)
    entries[name]={'layout':{**target,'t':len(packed)//24},'bin':base64.b64encode(packed).decode(),
                   'source':source_topology,'result':result}
    print(name,json.dumps({'source':source_topology,'result':result}),flush=True)
(options.output/'entries.json').write_text(json.dumps(entries,separators=(',',':')))
print('Built',len(entries),'closed rocks with Blender',bpy.app.version_string)
