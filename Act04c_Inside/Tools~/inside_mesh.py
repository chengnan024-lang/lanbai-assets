"""Export the act 4c meshes to FBX with the house settings (Tentacles/Source/lib/export_unity.py) and read them back.

  ~/bpy/bin/python inside_mesh.py      -> FBX/Inside_Lips.fbx, FBX/Inside_Extras.fbx (dome, dot quad, loose threads),
                                          FBX/Inside_Layout.fbx (empties), Tools~/out/fbx_verify.json
Unity <- Blender: Unity (x, y, z) = (-xb, zb, -yb)  (gate_layout.py B2U), so Blender = (-x, -z, y).
Each lip / ply object sits at InsideRoot-local (0, 0, z); its vertices carry the opening's offset and roll.
UV0 = 'UVMap', UV1 = 'UV1', UV2 = 'UV2', UV3 = 'UV3'; vertex colour 'Col' (linear, FBX colors_type LINEAR).
"""
import json
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(HERE, '..', '..', 'Tentacles', 'Source', 'lib'))
import inside_def as D  # noqa: E402
import inside_geom as GE  # noqa: E402
from export_unity import export_fbx  # noqa: E402

FBX = os.path.join(D.KIT, 'FBX')
os.makedirs(FBX, exist_ok=True)


def u2b(V):
    V = np.asarray(V, float)
    return np.stack([-V[:, 0], -V[:, 2], V[:, 1]], -1)


def make(name, o, loc_unity=(0.0, 0.0, 0.0)):
    V = u2b(o['V'])
    F = np.asarray(o['F'], np.int32)[:, ::-1]                # the axis change mirrors: keep the winding
    me = bpy.data.meshes.new(name)
    me.from_pydata(V.tolist(), [], F.tolist())
    me.update()
    li = F.ravel()
    for lname, key in (('UVMap', 'uv0'), ('UV1', 'uv1'), ('UV2', 'uv2'), ('UV3', 'uv3')):
        if key in o:
            lay = me.uv_layers.new(name=lname)
            lay.data.foreach_set('uv', np.asarray(o[key], np.float32)[li].ravel())
    if 'col' in o:
        at = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='POINT')
        at.data.foreach_set('color', np.asarray(o['col'], np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = tuple(u2b([loc_unity])[0])
    return ob


def readback(path, expect):
    """import the FBX into an empty scene with the inverse settings and compare vertex counts and bounds (Blender
    space) with what was exported."""
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.import_scene.fbx(filepath=path, axis_forward='-Z', axis_up='Y')
    got = {}
    for o in bpy.data.objects:
        if o.type != 'MESH':
            continue
        M = np.array(o.matrix_world)
        V = np.array([M[:3, :3] @ np.array(v.co) + M[:3, 3] for v in o.data.vertices])
        got[o.name] = (len(V), V.min(0).tolist(), V.max(0).tolist(), len(o.data.uv_layers))
    out = {}
    for name, (n, lo, hi) in expect.items():
        g = got.get(name)
        out[name] = dict(ok=bool(g and g[0] == n and np.allclose(g[1], lo, atol=0.01) and np.allclose(g[2], hi, atol=0.01)),
                         n=n, uv_layers=g[3] if g else 0)
    return out


def main():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    rep, objs, meta = GE.build()
    lips = []
    z_of = {L['k']: L['s'] for L in rep['lips']}
    for name, o in objs.items():
        if name.startswith('Lip8_Ply'):
            i = int(name[8])
            z = z_of[8] + rep['sleeve']['plies'][i]['dz']
        elif name.startswith('Lip8_Wall'):
            z = z_of[8]
        elif name.startswith('Lip'):
            z = z_of[int(name[3])]
        else:
            continue
        lips.append(make(name, o, (0.0, 0.0, z)))
    bpy.context.view_layer.update()
    expect = {}
    for ob in lips:
        M = np.array(ob.matrix_world)
        V = np.array([M[:3, :3] @ np.array(v.co) + M[:3, 3] for v in ob.data.vertices])
        expect[ob.name] = (len(V), V.min(0).tolist(), V.max(0).tolist())
    p1 = export_fbx(os.path.join(FBX, 'Inside_Lips.fbx'), lips)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    ex = [make('Inside_Dome', objs['Inside_Dome']), make('Inside_Dot', objs['Inside_Dot']), make('Inside_Loose', objs['Inside_Loose'])]
    p2 = export_fbx(os.path.join(FBX, 'Inside_Extras.fbx'), ex)
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    empties = []
    for L in rep['lips']:
        e = bpy.data.objects.new('LIP%d' % L['k'], None)
        bpy.context.scene.collection.objects.link(e)
        e.location = tuple(u2b([(0.0, 0.0, L['s'])])[0])
        empties.append(e)
    for p in rep['sleeve']['plies']:
        e = bpy.data.objects.new('LIP8_Ply%d' % p['i'], None)
        bpy.context.scene.collection.objects.link(e)
        e.location = tuple(u2b([(0.0, 0.0, z_of[8] + p['dz'])])[0])
        empties.append(e)
    root = bpy.data.objects.new('InsideRoot', None)
    bpy.context.scene.collection.objects.link(root)
    for e in empties:
        e.parent = root
    p3 = export_fbx(os.path.join(FBX, 'Inside_Layout.fbx'), [root] + empties)
    ver = readback(p1, expect)
    json.dump(dict(lips=ver, all_ok=all(v['ok'] for v in ver.values())), open(os.path.join(D.HERE, 'out', 'fbx_verify.json'), 'w'), indent=1)
    print('FBX:', p1, p2, p3, '| read-back ok:', all(v['ok'] for v in ver.values()), sum(1 for v in ver.values() if v['ok']), '/', len(ver))


if __name__ == '__main__':
    main()
