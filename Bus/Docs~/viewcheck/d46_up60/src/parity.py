# Parity of erode.osl vs cabin_numpy.erode_field: orthographic top-down renders of a horizontal plane (Cycles CPU, OSL,
# 1 sample, 0.01 px box filter = the pixel centre), emission R = (s < 0), G = s + 20, B = n_uniform, 32-bit EXR.
#   ~/bpy/bin/python parity.py
import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import common as C  # noqa: E402
import bpy  # noqa: E402
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402
import cabin_numpy as CN  # noqa: E402

X0, X1, Z0, Z1 = -1.0, 1.0, -1.0, 3.5
PX = 0.005
W, H = int(round((X1 - X0) / PX)), int(round((Z1 - Z0) / PX))      # 400 x 900
OFF = 20.0
PDIR = os.path.join(C.OUT, 'parity')

TESTS = [  # name, unity y, t or fade, zen_on, extra inputs (resist, hole_open, door_bias)
    dict(name='y2.60_t387_zen1', y=2.60, t=387.0, zen=1),
    dict(name='y2.60_t506_zen1', y=2.60, t=506.0, zen=1),
    dict(name='y1.00_fade0.25_zen1', y=1.00, fade=0.25, zen=1),
    # extra checks (not asked): the field before D-46, the stanchion resist + door bias, the floor patch + D-26 hole
    dict(name='y2.60_t506_zen0', y=2.60, t=506.0, zen=0),
    dict(name='y2.60_t387_zen0', y=2.60, t=387.0, zen=0),
    dict(name='y2.00_fade0.25_resist0.30_door0.5', y=2.00, fade=0.25, zen=1, resist=0.30, door=0.5),
    dict(name='y0.64_fade0.25_hole0.75', y=0.64, fade=0.25, zen=1, hole=0.75),
    dict(name='y0.64_fade0.66_hole1.0', y=0.64, fade=0.66, zen=1, hole=1.0),
    dict(name='y1.00_fade0.55_zen1', y=1.00, fade=0.55, zen=1),           # walls at seat height go, the seat sphere holds
    dict(name='y1.00_fade0.985_zen1', y=1.00, fade=0.985, zen=1),         # the seat sphere half released
    dict(name='y2.45_t446_zen1', y=2.45, t=446.0, zen=1),                 # inside the D-46 ceiling gate ramp (2.40 .. 2.50)
]


def setup():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    C.cycles_osl(sc, samples=1, threads=3)
    sc.cycles.pixel_filter_type = 'BOX'
    sc.cycles.filter_width = 0.01
    sc.cycles.use_denoising = False
    sc.cycles.seed = 0
    sc.render.resolution_x, sc.render.resolution_y, sc.render.resolution_percentage = W, H, 100
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.image_settings.exr_codec = 'ZIP'
    wd = bpy.data.worlds.new('W')
    wd.use_nodes = True
    wd.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    sc.world = wd
    # plane, a bit larger than the window
    bpy.ops.mesh.primitive_plane_add(size=1.0)
    pl = bpy.context.active_object
    pl.scale = (3.0, 6.0, 1.0)
    pl.location = (0.0, 1.25, 0.0)
    m = bpy.data.materials.new('Erode')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    sn = C.script_node(nt)
    add = nt.nodes.new('ShaderNodeMath')
    add.operation = 'ADD'
    add.inputs[1].default_value = OFF
    nt.links.new(sn.outputs['s'], add.inputs[0])
    cc = nt.nodes.new('ShaderNodeCombineColor')
    nt.links.new(sn.outputs['removed'], cc.inputs[0])
    nt.links.new(add.outputs[0], cc.inputs[1])
    nt.links.new(sn.outputs['n_uniform'], cc.inputs[2])
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    nt.links.new(cc.outputs[0], em.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs['Surface'])
    pl.data.materials.append(m)
    cam_d = bpy.data.cameras.new('Top')
    cam_d.type = 'ORTHO'
    cam_d.ortho_scale = max(X1 - X0, Z1 - Z0)
    cam_d.sensor_fit = 'AUTO'
    cam_d.clip_start, cam_d.clip_end = 0.1, 100.0
    cam = bpy.data.objects.new('Top', cam_d)
    sc.collection.objects.link(cam)
    cam.location = ((X0 + X1) / 2, (Z0 + Z1) / 2, 20.0)
    cam.rotation_euler = (0.0, 0.0, 0.0)               # looks down -Z, image up = +Y (unity +z), right = +X
    sc.camera = cam
    return sc, pl, sn


def read_exr(path):
    img = bpy.data.images.load(path, check_existing=False)
    a = np.array(img.pixels[:], np.float32).reshape(img.size[1], img.size[0], 4)
    bpy.data.images.remove(img)
    return a                                           # row 0 = bottom


def main():
    os.makedirs(PDIR, exist_ok=True)
    sc, pl, sn = setup()
    xs = X0 + (np.arange(W) + 0.5) * PX
    zs = Z0 + (np.arange(H) + 0.5) * PX                # bottom row first, as Blender's pixels
    report = []
    for T in TESTS:
        fade = float(CN.fade(T['t'])) if 't' in T else float(T['fade'])
        resist, hole, door = T.get('resist', 0.0), T.get('hole', 0.0), T.get('door', 0.0)
        pl.location.z = T['y']
        sn.inputs['fade'].default_value = fade
        sn.inputs['zen_on'].default_value = float(T['zen'])
        sn.inputs['resist'].default_value = resist
        sn.inputs['hole_open'].default_value = hole
        sn.inputs['door_bias'].default_value = door
        path = os.path.join(PDIR, T['name'] + '.exr')
        sc.render.filepath = path
        t0 = time.time()
        bpy.ops.render.render(write_still=True)
        dt = time.time() - t0
        a = read_exr(path)
        rem_o = a[..., 0]
        s_o = a[..., 1].astype(np.float64) - OFF
        assert np.all((rem_o == 0) | (rem_o == 1)), 'removed channel not binary: colour management?'
        Xg, Zg = np.meshgrid(xs, zs)
        pos = np.stack([Xg, np.full_like(Xg, T['y']), Zg], -1)
        s_n = CN.erode_field(pos, fade, resist=resist, hole_open=hole, door_bias=door,
                             zen=CN.ERODE_ZENITH if T['zen'] else None)
        rem_n = (s_n < 0).astype(np.float32)
        dis = rem_o != rem_n
        # edge = the numpy mask changes within 1 px (4-neighbourhood) of the pixel
        m = rem_n.astype(bool)
        edge = np.zeros_like(m)
        edge[1:, :] |= m[1:, :] != m[:-1, :]
        edge[:-1, :] |= m[1:, :] != m[:-1, :]
        edge[:, 1:] |= m[:, 1:] != m[:, :-1]
        edge[:, :-1] |= m[:, 1:] != m[:, :-1]
        n_dis = int(dis.sum())
        n_dis_edge = int((dis & edge).sum())
        dS = np.linalg.norm(pos - np.array(CN.SEAT_SPHERE[:3]), axis=-1)
        # outside the protections (s ~ 10 there) and outside the seat sphere's 5 cm smoothstep band, where s changes by
        # ~(tau + 10) / 0.05 per metre, so the sub-pixel sample offset alone moves s by 1e-4 .. 1e-3 (never its sign)
        live = (s_n < 5.0) & ((dS < CN.SEAT_SPHERE[3] - 0.05) | (dS > CN.SEAT_SPHERE[3]))
        ds = np.abs(s_o - s_n)
        row = dict(test=T['name'], unity_y=T['y'], t=T.get('t'), fade=round(fade, 6), zen_on=T['zen'], resist=resist,
                   hole_open=hole, door_bias=door, pixels=int(dis.size), removed_numpy_pct=round(100 * float(rem_n.mean()), 3),
                   removed_osl_pct=round(100 * float(rem_o.mean()), 3), disagree_px=n_dis,
                   disagree_pct=round(100.0 * n_dis / dis.size, 4), disagree_on_edge_px=n_dis_edge,
                   max_abs_ds=float(ds.max()), max_abs_ds_live=float(ds[live].max()) if live.any() else None,
                   max_abs_s_at_disagree=float(np.abs(s_n[dis]).max()) if n_dis else 0.0, render_s=round(dt, 2))
        report.append(row)
        print('[parity] %-36s fade %.4f  removed numpy %6.2f%% osl %6.2f%%  disagree %d px (%.4f%%, %d on edges)  '
              'max|ds| %.2e  max|s| at disagree %.2e  (%.1f s)'
              % (T['name'], fade, row['removed_numpy_pct'], row['removed_osl_pct'], n_dis, row['disagree_pct'], n_dis_edge,
                 row['max_abs_ds'], row['max_abs_s_at_disagree'], dt))
        # picture: left osl, middle numpy, right diff (red = osl only, cyan = numpy only); top row = unity z 3.5
        vis = np.zeros((H, W * 3 + 8, 3), np.uint8) + 128
        for k, mm in enumerate((rem_o.astype(bool), m)):
            vis[:, k * (W + 4):k * (W + 4) + W] = np.where(mm[..., None], 255, 40)
        d = np.zeros((H, W, 3), np.uint8) + 40
        d[dis & (rem_o == 1)] = (255, 60, 60)
        d[dis & (rem_o == 0)] = (60, 255, 255)
        vis[:, 2 * (W + 4):] = d
        Image.fromarray(vis[::-1]).save(os.path.join(PDIR, T['name'] + '.png'))
    json.dump(dict(_about='erode.osl (Cycles OSL, CPU) vs Cabin/Tools~/cabin_numpy.erode_field on the same pixel centres; '
                          'plane x %.1f..%.1f, z %.1f..%.1f, %g m pixels (%d x %d); edge = the numpy mask changes within 1 px'
                          % (X0, X1, Z0, Z1, PX, W, H), rows=report),
              open(os.path.join(PDIR, 'parity.json'), 'w'), indent=1)
    print('[parity] ->', os.path.join(PDIR, 'parity.json'))


if __name__ == '__main__':
    main()
