# -*- coding: utf-8 -*-
"""蓝白 · 云卡 v2（Blender 5.0.1 / Cycles 体积）—— 光照分通道的场景线性云卡。

在 v1（Clouds/Source/make_clouds.py）上做：形状、体积导入、相机取景、alpha 清理沿用 v1（import 进来）；光与导出是新的。
和门的 `GateClouds`（Lanbai/GateCloudCard）同一个思路：**卡里存的是“白光下的光照”，颜色在 shader 里给**，
所以同一张卡在任何方位、任何时刻（晨、暮、蓝时变暗）都按当时的日色 / 天色亮。每个形状每组 5 遍白光渲染：

  _K.png  RGBA：R = 太阳在视线右侧 15°（几乎在云正后方：银边、暗的云体）
                G = 太阳在右侧 80°（侧光）
                B = 太阳在右侧 150°（几乎在身后：整朵受光）
                A = 覆盖率（直通 alpha）
  _S.png  RGB： R = 上半球均匀天光（辐亮度 1）
                G = 下半球均匀地光（辐亮度 1）
                B = 0（留空）
  太阳 = Unity 照度 E = 1 的白色平行光（Blender 强度 π），仰角按组（晨 6°、暮 1°）。
  每个通道存 sRGB(值 / 缩放)，缩放写在 Textures/cards_v2.json（材质 _KScale / _SScale）。
  太阳在卡的左边时 shader 水平镜像（和门一样）。

组（set）：dawn（晨，相机按形状默认，略俯）、duskU（暮，头顶那组：从下往上 12° 看）、duskD（暮，脚下那组：从上往下 12° 看，
另一批形状 / 随机种子：“下面的云是别的云”）。
用法：~/bpy/bin/python make_clouds_v2.py --set dawn --only Cumulus [--test]
"""
import os
import sys
import math
import json
import time
import argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.normpath(os.path.join(HERE, '..', '..', 'Clouds', 'Source')))
import make_clouds as M  # noqa: E402  (v1: shapes, volume import, camera framing, alpha cleanup)
import lb_common as C  # noqa: E402
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

OUT = os.path.normpath(os.path.join(HERE, '..', 'Textures'))
WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')
M.CACHE = os.path.join(WORK, 'cache')

KEY_ANGLES = (15.0, 80.0, 150.0)          # sun azimuth right of the view direction (0 = straight behind the cloud)
KSCALE = 3.0                              # stored = sRGB(value / scale); review r1 R9 (6 wasted ~1.3 bit)
SSCALE = 1.1
SETS = {
    'dawn': dict(sun_el=6.0, pitch=None, seed=0),
    'duskU': dict(sun_el=1.0, pitch=12.0, seed=0),
    'duskD': dict(sun_el=1.0, pitch=-12.0, seed=1),
}
PASSES = ('k0', 'k1', 'k2', 'up', 'dn')


def build_world_dome(which):
    """Uniform white upper ('up') or lower ('dn') hemisphere, black elsewhere."""
    w = bpy.data.worlds.new('Dome_' + which)
    bpy.context.scene.world = w
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    bg = nt.nodes.new('ShaderNodeBackground')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    cmp = nt.nodes.new('ShaderNodeMath')
    cmp.operation = 'GREATER_THAN' if which == 'up' else 'LESS_THAN'
    cmp.inputs[1].default_value = 0.0
    nt.links.new(sep.outputs['Z'], cmp.inputs[0])
    nt.links.new(cmp.outputs[0], bg.inputs['Strength'])
    bg.inputs['Color'].default_value = (1, 1, 1, 1)
    nt.links.new(bg.outputs[0], out.inputs['Surface'])
    return w


def build_black_world():
    w = bpy.data.worlds.new('Black')
    bpy.context.scene.world = w
    w.use_nodes = True
    w.node_tree.nodes['Background'].inputs['Strength'].default_value = 0.0
    return w


def build_key(rel_az, el_deg, cam):
    """White sun, Unity E = 1 (Blender strength pi), at rel_az right of the camera's horizontal view direction."""
    ld = bpy.data.lights.new('Key', 'SUN')
    ld.energy = math.pi
    ld.color = (1, 1, 1)
    ld.angle = math.radians(0.55)
    ob = bpy.data.objects.new('Key', ld)
    bpy.context.scene.collection.objects.link(ob)
    fwd = cam.matrix_world.to_3x3() @ Vector((0, 0, -1))
    yaw = math.atan2(fwd.x, fwd.y)
    el, az = math.radians(el_deg), yaw + math.radians(rel_az)
    sd = Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)))
    ob.rotation_euler = (-sd).to_track_quat('-Z', 'Y').to_euler()
    return ob


def shape_spec(name, setname, q):
    grid, fn, spec = M.SHAPES[name](q)
    S = SETS[setname]
    spec = dict(spec)
    if S['pitch'] is not None and 'cam_loc' not in spec:
        spec['pitch'] = S['pitch']
    return grid, fn, spec


def render_set(name, setname, samples=40, scale=1.0, bounces=14, cache=None, passes=PASSES, shape_fn=None):
    cache = {} if cache is None else cache
    S = SETS[setname]
    key = (name, S['seed'])
    q = max(scale, 0.5) if scale < 1 else 1.0
    if key not in cache:
        t0 = time.time()
        if shape_fn is not None:
            grid, fn, spec = shape_fn(q)
        else:
            grid, fn, spec = shape_spec(name, setname, q)
        if S['seed']:
            # duskD: the shape mirrored left-right (the shapes' blob layouts are seeded inside v1; a true re-seed needs
            # v1's shape functions to take a seed). 'Other clouds' comes mostly from the other shape list (README §2).
            fn0 = fn
            fn = lambda P, f=fn0: f(P * np.array([-1, 1, 1], np.float32))
        dens = M.evaluate(grid, fn)
        cache[key] = (grid, dens, spec)
        print(f'[{name}/{setname}] density {tuple(grid.res)} {time.time() - t0:.1f}s', flush=True)
    grid, dens, spec = cache[key]
    spec = dict(spec)
    if S['pitch'] is not None and 'cam_loc' not in spec:
        spec['pitch'] = S['pitch']
    prefix = 'CloudSea' if 'cam_loc' in spec else 'Cloud'
    base = f'{prefix}V2_{name}_{setname}'
    os.makedirs(os.path.join(WORK, 'exr'), exist_ok=True)
    res = (int(spec['res'][0] * scale), int(spec['res'][1] * scale))
    cam = None
    for i, ps in enumerate(passes):
        bpy.ops.wm.read_factory_settings(use_empty=True)
        mat = M.cloud_material(spec['sigma'], spec.get('g', 0.55))
        M.import_density('Cloud_' + name, dens, grid, mat)
        if 'cam_loc' in spec:
            cam = M.place_camera(spec['cam_loc'], spec['pitch'], spec['lens'])
        else:
            cam = M.frame_camera(M.occupied_points(dens, grid), res, spec['yaw'], spec['pitch'], spec['lens'],
                                 spec['fill'], spec.get('center_bias', (0, 0)))
        bpy.context.view_layer.update()
        if ps.startswith('k'):
            build_black_world()
            build_key(KEY_ANGLES[int(ps[1])], S['sun_el'], cam)
        else:
            build_world_dome(ps)
        M.setup_render(res, samples, dict(view='Standard', look='None', exposure=0.0), bounces)
        exr = os.path.join(WORK, 'exr', f'_{base}__{ps}.exr')
        bpy.context.scene.render.filepath = exr
        t1 = time.time()
        bpy.ops.render.render(write_still=True)
        print(f'[{base}/{ps}] {res[0]}x{res[1]} {time.time() - t1:.1f}s', flush=True)
    meta = dict(name=base, shape=name, set=setname, sun_el=S['sun_el'], key_angles=KEY_ANGLES, res=list(res),
                samples=samples, sigma=spec['sigma'], g=spec.get('g', 0.55), pitch=spec['pitch'],
                lens=spec['lens'], haze=spec.get('haze'), side_taper=spec.get('side_taper', 0.0),
                bottom_taper=spec.get('bottom_taper', 0.0),
                cam=dict(loc=list(cam.location), rot=list(cam.rotation_euler), lens=cam.data.lens))
    with open(os.path.join(WORK, 'exr', f'_{base}.json'), 'w') as f:
        json.dump(meta, f, indent=1, default=float)
    return base


# ---------------------------------------------------------------- post: alpha cleanup on all channels
def load_prem(exr):
    raw = M.load_float_image(exr)
    return raw[..., :3].astype(np.float64), np.clip(raw[..., 3], 0, 1).astype(np.float64)


def load_channels(base):
    ch, al = {}, []
    for ps in PASSES:
        p, a = load_prem(os.path.join(WORK, 'exr', f'_{base}__{ps}.exr'))
        ch[ps] = p.mean(-1)            # white light: R = G = B up to noise
        al.append(a)
    return ch, np.mean(al, 0)


def strip_tapers(ch, a, meta):
    """v1's strip-end break-up (CloudSea): fade follows the clouds, computed on a neutral preview mix."""
    st, sb = meta.get('side_taper', 0.0), meta.get('bottom_taper', 0.0)
    if st <= 0 and sb <= 0:
        return ch, a
    h, w = a.shape
    x = (np.arange(w) + 0.5) / w
    y = (np.arange(h) + 0.5) / h
    tx = M.sstep(0.0, st, x) * M.sstep(1.0, 1.0 - st, x) if st > 0 else np.ones(w)
    ty = M.sstep(1.0, 1.0 - sb, y) if sb > 0 else np.ones(h)
    t = ty[:, None] * tx[None, :]
    from scipy.ndimage import gaussian_filter
    lum = ch['k1'] + 0.5 * ch['up']
    Ls = gaussian_filter(lum, M.ERODE[2]) / np.maximum(gaussian_filter(a, M.ERODE[2]), 1e-4)
    big = gaussian_filter(Ls * a, 40.0) / np.maximum(gaussian_filter(a, 40.0), 1e-4)
    L = np.clip(Ls / np.maximum(1.5 * big, 1e-6), 0, 1)
    tp = M.sstep(0.0, 1.0, t * M.ERODE[0] - M.ERODE[1] * (1.0 - L))
    return {k: v * tp for k, v in ch.items()}, a * tp


def finish(base, out_dir, alpha_floor=0.004):
    from scipy.ndimage import median_filter
    meta = json.load(open(os.path.join(WORK, 'exr', f'_{base}.json')))
    ch, a = load_channels(base)
    ch, a = strip_tapers(ch, a, meta)
    # guide = a neutral mix of all passes (denoised colour), same filter as v1
    guide = np.stack([ch['k0'] + ch['k1'], ch['k2'] + ch['up'], ch['dn'] + ch['k1']], -1)
    a_g = M.guided_alpha(np.maximum(guide, 0), median_filter(a, size=3), r=4, eps=2e-4)
    wgt = M.sstep(0.97, 0.995, np.minimum(a, a_g))
    a2 = a * wgt + a_g * (1 - wgt)
    a2 = np.maximum(a2, 1e-8)
    straight = {}
    for grp in (('k0', 'k1', 'k2'), ('up', 'dn', 'k1')):
        prem = np.stack([np.maximum(ch[k], 0) for k in grp], -1)
        st = M.push_pull_colour(prem, a2, conf=0.03)
        for i, k in enumerate(grp):
            straight.setdefault(k, st[..., i])
    af = np.clip((a2 - alpha_floor) / (1 - alpha_floor), 0, 1)
    K = np.stack([straight['k0'], straight['k1'], straight['k2']], -1) / KSCALE
    Sx = np.stack([straight['up'], straight['dn'], np.zeros_like(a)], -1) / SSCALE
    os.makedirs(out_dir, exist_ok=True)
    M.write_rgba(os.path.join(out_dir, f'{base}_K.png'), C.srgb_enc(np.clip(K, 0, 1)), af)
    from PIL import Image
    s8 = np.clip(C.srgb_enc(np.clip(Sx, 0, 1)) * 255 + 0.5, 0, 255).astype(np.uint8)
    Image.fromarray(s8, 'RGB').save(os.path.join(out_dir, f'{base}_S.png'), optimize=True)
    clipK = float((K[af > 0.05] >= 0.999).mean())
    clipS = float((Sx[..., :2][af > 0.05] >= 0.999).mean())
    info = dict(name=base, shape=meta['shape'], set=meta['set'], size=[int(a.shape[1]), int(a.shape[0])],
                sun_el=meta['sun_el'], key_angles=meta['key_angles'], kscale=KSCALE, sscale=SSCALE,
                clipped_K=clipK, clipped_S=clipS, pitch=meta['pitch'], lens=meta['lens'],
                k_p999=[float(np.percentile(straight[k][af > 0.5], 99.9)) for k in ('k0', 'k1', 'k2')])
    rows = np.nonzero((af > 0.5).mean(1) > 0.02)[0]
    cols = np.nonzero((af > 0.5).mean(0) > 0)[0]
    h, w = af.shape
    if len(rows):
        info['cloud_base_v'] = round(1 - (rows[-1] + 1) / h, 4)
        info['opaque_bbox_uv'] = [round(cols[0] / w, 4), round(1 - (rows[-1] + 1) / h, 4),
                                  round((cols[-1] + 1) / w, 4), round(1 - rows[0] / h, 4)]
    with open(os.path.join(out_dir, f'{base}.json'), 'w') as f:
        json.dump(info, f, indent=1)
    np.savez_compressed(os.path.join(WORK, f'{base}_ch.npz'), K=(K * KSCALE).astype(np.float16),
                        S=(Sx[..., :2] * SSCALE).astype(np.float16), a=af.astype(np.float16))
    print(f'[{base}] finished: clip K {clipK:.4f} S {clipS:.4f}, k p99.9 {info["k_p999"]}', flush=True)
    return info


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--set', nargs='*', default=['dawn'])
    ap.add_argument('--only', nargs='*', default=['Cumulus'])
    ap.add_argument('--out', default=OUT)
    ap.add_argument('--samples', type=int, default=40)
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--bounces', type=int, default=14)
    ap.add_argument('--finish-only', action='store_true')
    ap.add_argument('--test', action='store_true')
    a = ap.parse_args()
    if a.test:
        a.scale = min(a.scale, 0.35)
        a.samples = min(a.samples, 24)
    cache = {}
    for n in a.only:
        for s in a.set:
            base = (f'CloudV2_{n}_{s}' if n not in ('1', '2') else f'CloudSeaV2_{n}_{s}')
            if not a.finish_only:
                base = render_set(n, s, a.samples, a.scale, a.bounces, cache)
            finish(base, a.out)
        cache.clear()


if __name__ == '__main__':
    main()
