"""Offline geometry/export regression checks for the shared defense GLB."""
import importlib.util
import json
import math
from pathlib import Path
import struct
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('turret_gen', ROOT / 'tools/art/turret_gen.py')
generator = importlib.util.module_from_spec(spec)
spec.loader.exec_module(generator)


class TurretAssets(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        raw = (ROOT / 'play/assets/defense/turrets.glb').read_bytes()
        magic, version, length = struct.unpack_from('<4sII', raw)
        assert (magic, version, length) == (b'glTF', 2, len(raw))
        json_length, kind = struct.unpack_from('<II', raw, 12)
        assert kind == 0x4e4f534a
        cls.gltf = json.loads(raw[20:20 + json_length])
        binary_length, kind = struct.unpack_from('<II', raw, 20 + json_length)
        assert kind == 0x004e4942
        cls.binary = raw[28 + json_length:28 + json_length + binary_length]

    def accessor(self, index):
        accessor = self.gltf['accessors'][index]
        view = self.gltf['bufferViews'][accessor['bufferView']]
        components = {'SCALAR': 1, 'VEC2': 2, 'VEC3': 3, 'VEC4': 4}[accessor['type']]
        component_type = {5123: 'H', 5125: 'I', 5126: 'f'}[accessor['componentType']]
        layout = '<' + component_type * components
        offset = view.get('byteOffset', 0) + accessor.get('byteOffset', 0)
        stride = view.get('byteStride', struct.calcsize(layout))
        return [struct.unpack_from(layout, self.binary, offset + index * stride)
                for index in range(accessor['count'])]

    def test_degenerate_cap_uvs_have_surface_tangents(self):
        # These caps reproduced the original zero-tangent export on +/-X faces.
        faces = [((1, 0, 0), (0, 1, 0), (0, 0, 1)),
                 ((-1, 0, 0), (0, 0, 1), (0, 1, 0)),
                 ((0, 1, 0), (0, 0, 1), (1, 0, 0)),
                 ((0, 0, 1), (1, 0, 0), (0, 1, 0))]
        for normal, b, c in faces:
            with self.subTest(normal=normal):
                mesh = generator.Mesh()
                mesh.tri((0, 0, 0), b, c,
                         normal, normal, normal, (0, 0), (0, 0), (0, 0))
                _, normals, _, tangents, _ = generator._to_indexed(mesh)
                for n, t in zip(normals, tangents):
                    self.assertAlmostEqual(sum(float(x * x) for x in t[:3]), 1, places=5)
                    self.assertAlmostEqual(sum(float(a * b) for a, b in zip(n, t[:3])), 0, places=5)
                    self.assertIn(float(t[3]), (-1, 1))

    def test_shipped_geometry_is_finite_and_tangent_frames_are_valid(self):
        triangles = 0
        for mesh in self.gltf['meshes']:
            for primitive in mesh['primitives']:
                with self.subTest(mesh=mesh['name']):
                    attributes = primitive['attributes']
                    self.assertEqual({key for key in attributes if key.startswith('TEXCOORD_')}, {'TEXCOORD_0'})
                    positions = self.accessor(attributes['POSITION'])
                    normals = self.accessor(attributes['NORMAL'])
                    tangents = self.accessor(attributes['TANGENT'])
                    self.assertEqual(len(normals), len(positions))
                    self.assertEqual(len(tangents), len(positions))
                    indices = [value[0] for value in self.accessor(primitive['indices'])]
                    self.assertEqual(len(indices) % 3, 0)
                    self.assertLess(max(indices), len(positions))
                    triangles += len(indices) // 3
                    for index in attributes.values():
                        self.assertTrue(all(math.isfinite(value) for row in self.accessor(index) for value in row))
                    for n, t in zip(normals, tangents):
                        self.assertAlmostEqual(sum(x * x for x in n), 1, places=4)
                        self.assertAlmostEqual(sum(x * x for x in t[:3]), 1, places=4)
                        self.assertAlmostEqual(sum(a * b for a, b in zip(n, t[:3])), 0, places=4)
                        self.assertIn(t[3], (-1, 1))
        self.assertEqual(triangles, 4234)

    def test_pkm_has_a_continuous_central_mount(self):
        primitive = next(mesh for mesh in self.gltf['meshes'] if mesh['name'] == 'pkm-base')['primitives'][0]
        positions = self.accessor(primitive['attributes']['POSITION'])
        indices = [value[0] for value in self.accessor(primitive['indices'])]
        spans = []
        for offset in range(0, len(indices), 3):
            triangle = [positions[index] for index in indices[offset:offset + 3]]
            if all(math.hypot(vertex[0], vertex[2]) < .08 for vertex in triangle):
                spans.append(max(vertex[1] for vertex in triangle) - min(vertex[1] for vertex in triangle))
        self.assertGreater(max(spans), .3, 'The central barrel-to-gun mounting shaft is disconnected')

    def test_normal_map_handedness_matches_each_uv_face(self):
        def subtract(a, b):
            return tuple(x - y for x, y in zip(a, b))

        def cross(a, b):
            return (a[1] * b[2] - a[2] * b[1], a[2] * b[0] - a[0] * b[2], a[0] * b[1] - a[1] * b[0])

        for mesh in self.gltf['meshes']:
            primitive = mesh['primitives'][0]
            attributes = primitive['attributes']
            positions = self.accessor(attributes['POSITION'])
            normals = self.accessor(attributes['NORMAL'])
            tangents = self.accessor(attributes['TANGENT'])
            uv = self.accessor(attributes['TEXCOORD_0'])
            indices = [value[0] for value in self.accessor(primitive['indices'])]
            for offset in range(0, len(indices), 3):
                a, b, c = indices[offset:offset + 3]
                edge1, edge2 = subtract(positions[b], positions[a]), subtract(positions[c], positions[a])
                duv1, duv2 = subtract(uv[b], uv[a]), subtract(uv[c], uv[a])
                determinant = duv1[0] * duv2[1] - duv2[0] * duv1[1]
                if abs(determinant) < 1e-9:
                    continue  # A constant cap UV has no defined texture direction.
                bitangent = tuple((e2 * duv1[0] - e1 * duv2[0]) / determinant for e1, e2 in zip(edge1, edge2))
                for index in (a, b, c):
                    orientation = sum(x * y for x, y in zip(cross(normals[index], tangents[index][:3]), bitangent))
                    if abs(orientation) > 1e-6:
                        self.assertEqual(tangents[index][3], -1 if orientation < 0 else 1,
                                         (mesh['name'], offset // 3, index))

    def test_embedded_webp_contract_and_gameplay_nodes(self):
        self.assertIn('EXT_texture_webp', self.gltf['extensionsRequired'])
        for texture in self.gltf['textures']:
            self.assertNotIn('source', texture)  # No false PNG/JPEG fallback.
            source = texture['extensions']['EXT_texture_webp']['source']
            image = self.gltf['images'][source]
            self.assertEqual(image['mimeType'], 'image/webp')
            self.assertIn('bufferView', image)
            self.assertNotIn('uri', image)
        nodes = self.gltf['nodes']
        roots = self.gltf['scenes'][0]['nodes']
        self.assertEqual({nodes[index]['name'] for index in roots}, {'pkm', 'nail', 'flame'})
        for index in roots:
            self.assertEqual({nodes[child]['name'] for child in nodes[index]['children']},
                             {'base', 'lv2', 'lv3', 'gun'})


if __name__ == '__main__':
    unittest.main()
