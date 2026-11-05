"""Build connected tree meshes with Blender 4.3.2, keeping native dimensions.

blender -b --python-exit-code 1 --python tools/art/nature/build_meshes.py -- --output /tmp/terra-nature
Sources are pinned glTF 2.0 files. GLBs are review artifacts; runtime entries use
the existing 24-byte triangle format, without an extra loader or draw batch.
"""
import argparse
import base64
import hashlib
import json
import struct
import sys
from collections import Counter
from pathlib import Path

import bmesh
import bpy
from mathutils import Vector

ROOT = Path(__file__).resolve().parent
args = argparse.ArgumentParser()
args.add_argument('--output', type=Path, required=True)
options = args.parse_args(sys.argv[sys.argv.index('--') + 1:])
options.output.mkdir(parents=True, exist_ok=True)
(options.output / 'entries.json').unlink(missing_ok=True)
layout = json.loads((ROOT / 'native-layout.json').read_text())
lock = json.loads((ROOT / 'source-lock.json').read_text())


def root_center(vertices, bark):
    low = min(vertices[i].z for i in bark)
    high = max(vertices[i].z for i in bark)
    points = {tuple(round(v, 6) for v in vertices[i]) for i in bark
              if vertices[i].z <= low + (high - low) * .01}
    return sum((Vector(p) for p in points), Vector()) / len(points)


def fit(vertices, target, bark):
    """Blender is Z-up; native runtime uses Y-up, with the same handedness."""
    low = Vector(tuple(min(p[i] for p in vertices) for i in range(3)))
    high = Vector(tuple(max(p[i] for p in vertices) for i in range(3)))
    pivot = root_center(vertices, bark)
    scale = Vector((target['w'] * .5 / max(abs(low.x - pivot.x), abs(high.x - pivot.x)),
                    target['d'] * .5 / max(abs(low.y - pivot.y), abs(high.y - pivot.y)),
                    target['h'] / (high.z - low.z)))
    for p in vertices:
        p.x = (p.x - pivot.x) * scale.x
        p.y = (p.y - pivot.y) * scale.y
        p.z = (p.z - low.z) * scale.z
    # Native harvesting hides the standing mesh inside a circle derived from
    # max(w,d)/2, plus a small wind margin. Keep the whole crown in that circle
    # so asymmetrical branches cannot remain suspended after the tree falls.
    radius = max(p.xy.length for p in vertices)
    limit = max(target['w'], target['d']) * .5 * .99
    if radius > limit:
        factor = limit / radius
        for p in vertices:
            p.x *= factor
            p.y *= factor


def topology(mesh):
    mesh.calc_loop_triangles()
    edges = Counter()
    bark = 0
    for face in mesh.loop_triangles:
        if mesh.polygons[face.polygon_index].material_index:
            continue
        bark += 1
        points = [tuple(round(v, 6) for v in mesh.vertices[i].co) for i in face.vertices]
        for a, b in zip(points, points[1:] + points[:1]):
            edges[tuple(sorted((a, b)))] += 1
    return {'triangles': len(mesh.loop_triangles), 'barkTriangles': bark,
            'openBarkEdges': sum(n == 1 for n in edges.values()),
            'nonManifoldBarkEdges': sum(n > 2 for n in edges.values())}


entries = {}
sources = {source['file']: source for source in lock['files']}
for name, settings in layout.items():
    source = sources[settings['source']]
    path = ROOT / 'sources' / source['file']
    if hashlib.sha256(path.read_bytes()).hexdigest() != source['sha256']:
        raise ValueError('Source changed: ' + source['file'])
    target = settings['layout']
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.import_scene.gltf(filepath=str(path))
    vertices, faces, material_indices = [], [], []
    for obj in [o for o in bpy.context.scene.objects if o.type == 'MESH']:
        mesh = obj.data
        mesh.calc_loop_triangles()
        offset = len(vertices)
        vertices.extend([obj.matrix_world @ v.co for v in mesh.vertices])
        for face in mesh.loop_triangles:
            material = obj.material_slots[face.material_index].name.lower()
            if material not in ('brown', 'green', 'darkgreen'):
                raise ValueError('Unknown material: ' + material)
            faces.append(tuple(offset + i for i in face.vertices))
            material_indices.append({'brown': 0, 'green': 1, 'darkgreen': 2}[material])
    bark = {v for face, material in zip(faces, material_indices) if not material for v in face}
    if name.startswith('qn_pine_'):
        pivot = root_center(vertices, bark)
        for i in bark:
            vertices[i].x = pivot.x + (vertices[i].x - pivot.x) * .62
            vertices[i].y = pivot.y + (vertices[i].y - pivot.y) * .62
    fit(vertices, target, bark)
    for old in list(bpy.context.scene.objects):
        bpy.data.objects.remove(old, do_unlink=True)
    mesh = bpy.data.meshes.new(name)
    mesh.from_pydata(vertices, [], faces)
    mesh.update()
    obj = bpy.data.objects.new(name, mesh)
    bpy.context.collection.objects.link(obj)
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)
    for label, color in [('bark', settings['bark']), ('leaves', settings['leaves']),
                         ('leaves_dark', [round(c * .82) for c in settings['leaves']])]:
        material = bpy.data.materials.new(label)
        material.diffuse_color = tuple((c / 255) ** 2.2 for c in color) + (1,)
        mesh.materials.append(material)
    for polygon, index in zip(mesh.polygons, material_indices):
        polygon.material_index = index
    bm = bmesh.new()
    bm.from_mesh(mesh)
    bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=1e-6)
    variant = settings.get('variant')
    if variant:
        # Gentle height-dependent bends and twists create three distinct
        # crooked trunks. Subdivision supplies intermediate curve points;
        # connected collapse later brings them back inside the native budget.
        from math import cos, sin, pi
        long_edges = [edge for edge in bm.edges if edge.calc_length() > target['h'] * .12]
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=2, use_grid_fill=True)
        for vertex in bm.verts:
            t = max(0., min(1., vertex.co.z / target['h']))
            angle = variant['twist'] * t
            x, y = vertex.co.x, vertex.co.y
            vertex.co.x = x*cos(angle) - y*sin(angle) + target['h']*.25*variant['bend']*t*t
            vertex.co.y = x*sin(angle) + y*cos(angle) + target['h']*.08*sin(pi*t)*t
    bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
    bm.to_mesh(mesh)
    bm.free()
    before = topology(mesh)
    if before['openBarkEdges'] or before['nonManifoldBarkEdges']:
        raise ValueError('Source bark is not closed: ' + name)
    # Reserve geometry for chamfered bark edges, adjusting only the collapse
    # budget when a bevel needs more triangles. Every attempt starts at the
    # original connected source; no repeated destructive simplification.
    source_mesh = mesh.copy()
    collapse_budget = target['t'] - 96
    for attempt in range(6):
        obj.data = source_mesh.copy()
        obj.modifiers.clear()
        if before['triangles'] > collapse_budget:
            modifier = obj.modifiers.new('Connected collapse', 'DECIMATE')
            modifier.decimate_type = 'COLLAPSE'
            modifier.ratio = collapse_budget / before['triangles']
            modifier.use_collapse_triangulate = True
            bpy.ops.object.modifier_apply(modifier=modifier.name)
        mesh = obj.data
        bm = bmesh.new()
        bm.from_mesh(mesh)
        candidates = [edge for edge in bm.edges if len(edge.link_faces) == 2
                      and all(face.material_index == 0 for face in edge.link_faces)
                      and edge.calc_length() > target['h'] * .05
                      and edge.calc_face_angle(0) > .6]
        candidates.sort(key=lambda edge: edge.calc_length(), reverse=True)
        bmesh.ops.bevel(bm, geom=candidates[:12], offset=target['h'] * .003,
                        offset_type='OFFSET', segments=1, affect='EDGES',
                        clamp_overlap=True, material=0)
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        bark = {i for polygon in mesh.polygons if not polygon.material_index for i in polygon.vertices}
        fit([v.co for v in mesh.vertices], target, bark)
        # Validate the actual shipping precision, not just Blender floats.
        # Tiny bevel slivers can collapse on the native int16 grid.
        step = target['s']
        bm = bmesh.new()
        bm.from_mesh(mesh)
        for vertex in bm.verts:
            vertex.co = Vector(tuple(round(v / step) * step for v in vertex.co))
        bmesh.ops.remove_doubles(bm, verts=list(bm.verts), dist=step * .1)
        bmesh.ops.dissolve_degenerate(bm, edges=list(bm.edges), dist=step * .1)
        bmesh.ops.triangulate(bm, faces=list(bm.faces), quad_method='BEAUTY', ngon_method='BEAUTY')
        bmesh.ops.recalc_face_normals(bm, faces=list(bm.faces))
        bm.to_mesh(mesh)
        bm.free()
        mesh.update()
        after = topology(mesh)
        if after['openBarkEdges'] or after['nonManifoldBarkEdges']:
            raise ValueError('Simplification opened the bark: ' + name)
        excess = after['triangles'] - target['t']
        if excess <= 0:
            break
        collapse_budget -= excess + 8
    else:
        raise ValueError('Simplification exceeded the native triangle budget: ' + name)
    for unused in list(bpy.data.meshes):
        if unused != mesh and unused.users == 0:
            bpy.data.meshes.remove(unused)
    mesh.name = name
    obj.name = name
    bpy.ops.export_scene.gltf(filepath=str(options.output / (name + '.glb')),
                             export_format='GLB', use_selection=True,
                             export_materials='EXPORT', export_draco_mesh_compression_enable=False)
    packed = bytearray()
    for face in mesh.loop_triangles:
        points = [Vector((mesh.vertices[i].co.x, mesh.vertices[i].co.z, -mesh.vertices[i].co.y))
                  for i in face.vertices]
        a, b, c = points
        normal = (b - a).cross(c - a)
        if normal.length < 1e-10:
            raise ValueError('Degenerate triangle: ' + name)
        normal.normalize()
        positions = [round(v / target['s']) for p in points for v in p]
        if max(map(abs, positions)) > 32767:
            raise ValueError('Quantisation overflow: ' + name)
        material = mesh.polygons[face.polygon_index].material_index
        rgb = settings['leaves'] if material else settings['bark']
        if material == 2:
            rgb = [round(c * .82) for c in rgb]
        packed.extend(struct.pack('<9h3b3B', *positions,
                      *[max(-127, min(127, round(v * 127))) for v in normal], *rgb))
    entries[name] = {'layout': {**target, 't': len(packed) // 24},
                     'bin': base64.b64encode(packed).decode(),
                     'source': before, 'result': after}
    print(name, json.dumps({'source': before, 'result': after}), flush=True)

(options.output / 'entries.json').write_text(json.dumps(entries, separators=(',', ':')))
print('Built', len(entries), 'connected trees with Blender', bpy.app.version_string)
