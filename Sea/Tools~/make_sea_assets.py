# -*- coding: utf-8 -*-
"""Sea kit meshes + fallback cubemaps. Run with Blender-as-a-module:  ~/bpy/bin/python Sea/Tools~/make_sea_assets.py

  Models/Sea_Disc.fbx      flat disc, r 40 km, polar rings (dense at the centre), normal +Y      (ABOVE / BELOW)
  Models/Sea_Ceiling.fbx   flat disc, r 3.2 km, faces DOWN (normal -Y)                          (CEILING)
  Textures/Cube_Dawn_256.exr       act-6 sky (syferfontein_6d_clear_puresky), sun at azimuth +45 deg   (_WindowCube 7a; ABOVE test)
  Textures/Cube_DuskLower_256.exr  act-8 sky (syferfontein_0d_clear_puresky), sun azimuth 0, LOWER hemisphere = the
                                   'other sky' (-x, -y, z) x 0.82 x (0.92, 0.95, 1.05) (bible §6·8 8-ii)     (_WindowCube 7c; ceiling reflection)
  Textures/Cube_Dusk_256.exr       act-8 sky, upper hemisphere; lower = horizon colour fading to the nadir #3B4A78 (fill)
                                   (the ceiling's _SkyBehindCube)
All three are FALLBACKS (no clouds, no cloud cover): the real ones are baked in Unity from the Sky's scene
(Sea/给总控.md §5). Layout: Unity 6-frame horizontal strip (+X -X +Y -Y +Z -Z), D3D face orientation, linear half EXR.
Scale: the HDRI is multiplied so that its zenith reads the bible's zenith FILL (dawn #5B7ED7, dusk #4B5997) in luminance;
every texel is clamped to max channel 16 (Lanbai/Sky clamps the HDRI sun at linear 16, bible §6·6 日盘).
"""
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
REPO = os.path.dirname(KIT)
sys.path.insert(0, HERE)
import sea_numpy as S  # noqa: E402

N_FACE = 256


def srgb_to_lin(h):
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def face_dirs(n):
    u = (np.arange(n) + 0.5) / n
    s, t = np.meshgrid(2 * u - 1, 2 * u - 1, indexing='xy')      # s right, t down
    one = np.ones_like(s)
    faces = [np.stack([one, -t, -s], -1), np.stack([-one, -t, s], -1), np.stack([s, one, t], -1),
             np.stack([s, -one, -t], -1), np.stack([s, -t, one], -1), np.stack([-s, -t, -one], -1)]
    return [S.normalize(f) for f in faces]


def strip_from(fn, n=N_FACE):
    return np.concatenate([fn(d) for d in face_dirs(n)], axis=1)     # [n, 6n, 3]


def zenith_scale(env, target_hex):
    z = env.lookup(np.array([[0.0, 1.0, 0.0]]))[0]
    tgt = srgb_to_lin(target_hex)
    return float((tgt @ [0.2126, 0.7152, 0.0722]) / max(z @ [0.2126, 0.7152, 0.0722], 1e-6))


def write_exr(arr, path):
    import bpy
    h, w = arr.shape[:2]
    img = bpy.data.images.new(os.path.basename(path), w, h, alpha=True, float_buffer=True)
    rgba = np.concatenate([arr, np.ones((h, w, 1), np.float32)], -1)
    img.pixels.foreach_set(np.flipud(rgba).astype(np.float32).ravel())     # Blender rows bottom-up
    img.filepath_raw = path
    img.file_format = 'OPEN_EXR'
    scn = bpy.context.scene
    scn.render.image_settings.file_format = 'OPEN_EXR'
    scn.render.image_settings.color_depth = '16'
    scn.render.image_settings.exr_codec = 'ZIP'
    img.save_render(path, scene=scn)
    bpy.data.images.remove(img)


def make_cubes():
    out = os.path.join(KIT, 'Textures')
    hd = os.path.join(REPO, 'FromLocal', 'hdri', 'hdr')
    dawn = S.Env(S.equirect_from_hdr(S.read_hdr(os.path.join(hd, 'syferfontein_6d_clear_puresky_1k.hdr')), 45.0))
    k = zenith_scale(dawn, '#5B7ED7')
    strip = S.clamp_max_channel(strip_from(lambda d: dawn.lookup(d)) * k, 16.0)
    # below the horizon: the bible's lower-hemisphere fog gradient (horizon colour -> nadir #6F8FA8), §6·6 大气
    write_exr(strip.astype(np.float32), os.path.join(out, 'Cube_Dawn_256.exr'))
    print('dawn scale', k)

    dusk = S.Env(S.equirect_from_hdr(S.read_hdr(os.path.join(hd, 'syferfontein_0d_clear_puresky_1k.hdr')), 0.0))
    kd = zenith_scale(dusk, '#4B5997')
    tint = np.array([0.92, 0.95, 1.05]) * 0.82

    def lower(d):
        up = dusk.lookup(d) * kd
        mir = dusk.lookup(d * np.array([-1.0, -1.0, 1.0])) * kd * tint
        w = S.smoothstep(0.0, math.sin(math.radians(1.0)), -d[..., 1:2])        # 1 deg soft seam at the horizon
        return S.clamp_max_channel(up * (1 - w) + mir * w, 16.0)
    write_exr(strip_from(lower).astype(np.float32), os.path.join(out, 'Cube_DuskLower_256.exr'))

    nadir = srgb_to_lin('#3B4A78')

    def behind(d):
        up = dusk.lookup(d) * kd
        hor = dusk.lookup(S.normalize(d * np.array([1.0, 0.0, 1.0]) + np.array([0.0, 0.02, 0.0]))) * kd
        w = S.smoothstep(0.0, 1.0, -d[..., 1:2])
        low = hor * (1 - w) + nadir * w
        return S.clamp_max_channel(np.where(d[..., 1:2] >= 0, up, low), 16.0)
    write_exr(strip_from(behind).astype(np.float32), os.path.join(out, 'Cube_Dusk_256.exr'))
    print('dusk scale', kd)


def ring_mesh(name, r0, r1, rings, segs, down=False):
    """annulus r0..r1 (the ceiling's transparent edge ring)"""
    import bpy
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    radii = [r0 + (r1 - r0) * i / (rings - 1) for i in range(rings)]
    ringv = [[bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), 0.0)) for j in range(segs)] for r in radii]
    for a, b in zip(ringv[:-1], ringv[1:]):
        for j in range(segs):
            bm.faces.new((a[j], b[j], b[(j + 1) % segs], a[(j + 1) % segs]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.normal_update()
        if (f.normal.z < 0) != down:
            f.normal_flip()
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / 1000.0, l.vert.co.y / 1000.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def disc_mesh(name, radius, rings, segs, down=False):
    import bpy
    import bmesh
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    centre = bm.verts.new((0.0, 0.0, 0.0))
    radii = [0.5 * (radius / 0.5) ** (i / (rings - 1)) for i in range(rings)]      # geometric: dense near the bus
    ringv = []
    for r in radii:
        ringv.append([bm.verts.new((r * math.cos(2 * math.pi * j / segs), r * math.sin(2 * math.pi * j / segs), 0.0)) for j in range(segs)])
    for j in range(segs):
        bm.faces.new((centre, ringv[0][j], ringv[0][(j + 1) % segs]))
    for a, b in zip(ringv[:-1], ringv[1:]):
        for j in range(segs):
            bm.faces.new((a[j], b[j], b[(j + 1) % segs], a[(j + 1) % segs]))
    bmesh.ops.triangulate(bm, faces=bm.faces[:])
    for f in bm.faces:
        f.normal_update()
        if (f.normal.z < 0) != down:
            f.normal_flip()
    uv = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for l in f.loops:
            l[uv].uv = (l.vert.co.x / 1000.0, l.vert.co.y / 1000.0)
    bm.to_mesh(me)
    bm.free()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def make_meshes():
    import bpy
    sys.path.insert(0, os.path.join(REPO, 'Tentacles', 'Source', 'lib'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    ob = disc_mesh('Sea_Disc', 40000.0, 40, 96)
    export(ob, os.path.join(KIT, 'Models', 'Sea_Disc.fbx'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # the underwater dome at its real size (bounds!), any orientation: an icosphere r 1800 m, normals in
    bpy.ops.wm.read_factory_settings(use_empty=True)
    bpy.ops.mesh.primitive_ico_sphere_add(subdivisions=4, radius=1800.0)
    dome = bpy.context.active_object
    dome.name = 'Sea_Dome'
    export(dome, os.path.join(KIT, 'Models', 'Sea_Dome.fbx'))
    bpy.ops.wm.read_factory_settings(use_empty=True)
    # the act-8 ceiling in two pieces (README_Sea接口 §2.4, chief engineer #6): an OPAQUE inner disc r <= 2.4 km and a
    # TRANSPARENT edge ring 2.4 .. 3.2 km that carries the soft edge (alpha 0.5 at 2.7 km, band 500 m)
    inner = disc_mesh('Sea_Ceiling_Inner', 2400.0, 26, 96, down=True)
    ring = ring_mesh('Sea_Ceiling_Edge', 2400.0, 3200.0, 9, 192, down=True)
    from export_unity import export_fbx
    export_fbx(os.path.join(KIT, 'Models', 'Sea_Ceiling.fbx'), [inner, ring])
    print('wrote Sea_Ceiling.fbx (Inner + Edge)')


def export(ob, path):
    """the repo's one FBX setting (Tentacles/Source/lib/export_unity.py): Blender Z-up -> Unity Y-up, metres"""
    from export_unity import export_fbx
    os.makedirs(os.path.dirname(path), exist_ok=True)
    export_fbx(path, [ob])
    print('wrote', path)


if __name__ == '__main__':
    make_meshes()
    make_cubes()
