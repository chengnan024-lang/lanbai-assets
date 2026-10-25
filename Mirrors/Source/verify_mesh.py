"""Re-import BronzeMirror.fbx and check it against spec_conventions.md §1 -> Docs~/mesh_check.txt.

Run:  ~/bpy/bin/python verify_mesh.py
Coordinates are reported in UNITY object space (Blender (x, y, z) -> Unity (-x, z, -y)).
"""
import math
import os
import bpy  # noqa: F401
import bmesh

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
FBX = os.path.join(ROOT, 'Models', 'BronzeMirror.fbx')
OUT = os.path.join(ROOT, 'Docs~', 'mesh_check.txt')
RHO, SAG, RF = 7.6875, 0.015, 0.48

bpy.ops.wm.read_factory_settings(use_empty=True)
bpy.ops.import_scene.fbx(filepath=FBX, colors_type='LINEAR')   # the file holds raw (linear) values, as Unity reads them
lines = []
ok_all = True
def log(s):
    lines.append(s); print(s)
names = sorted(o.name for o in bpy.data.objects)
log('objects: %s' % names)
ok_all &= all(n in names for n in ('BronzeMirror', 'BronzeMirror_LOD0', 'BronzeMirror_LOD1', 'BronzeMirror_LOD2'))
for i in range(3):
    ob = bpy.data.objects['BronzeMirror_LOD%d' % i]
    me = ob.data
    M = ob.matrix_world
    U = [((M @ v.co).x * -1, (M @ v.co).z, -(M @ v.co).y) for v in me.vertices]
    xs = [u[0] for u in U]; ys = [u[1] for u in U]; zs = [u[2] for u in U]
    tris = sum(len(p.vertices) - 2 for p in me.polygons)
    col = me.color_attributes[0] if len(me.color_attributes) else None
    regs = set()
    if col is not None:
        for d in col.data:
            regs.add(round(d.color[0], 2))
    uv = me.uv_layers[0].data if me.uv_layers else []
    umin = min((d.uv[0] for d in uv), default=0); umax = max((d.uv[0] for d in uv), default=0)
    # face cap deviation (vertices with y > 0 and r < 0.48)
    dev = 0.0
    for (x, y, z) in U:
        r = math.hypot(x, z)
        if r < RF - 1e-4 and y > -1e-4:
            dev = max(dev, abs(y - (math.sqrt(RHO * RHO - r * r) - (RHO - SAG))))
    bm = bmesh.new(); bm.from_mesh(me); bm.transform(M)
    nonman = sum(1 for e in bm.edges if not e.is_manifold)
    # outward normals: the face-cap polygons must point +Y
    bm.normal_update()
    up = sum(1 for f in bm.faces if f.calc_center_median().z > 0.005 and f.normal.z > 0)
    capf = sum(1 for f in bm.faces if f.calc_center_median().z > 0.005)
    bm.free()
    diam = max(xs) - min(xs)
    ok = abs(diam - 1.0) < 1e-3 and abs(max(ys) - SAG) < 1e-4 and abs(min(ys) + 0.065) < 1e-3 and dev < 1e-5 \
        and regs >= {0.0, 0.25, 0.5, 0.75, 1.0} and up == capf and nonman == 0
    ok_all &= ok
    log('LOD%d: %d tris, %d verts, diameter %.4f, y %.4f..%.4f, regions %s, UV0 u %.3f..%.3f, cap deviation %.2e, '
        'non-manifold edges %d, cap faces up %d/%d -> %s' % (i, tris, len(me.vertices), diam, min(ys), max(ys), sorted(regs),
                                                             umin, umax, dev, nonman, up, capf, 'OK' if ok else 'FAIL'))
log('ALL: %s' % ('PASS' if ok_all else 'FAIL'))
open(OUT, 'w').write('\n'.join(lines) + '\n')
