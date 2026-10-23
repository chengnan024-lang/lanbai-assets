"""蓝白 / Lanbai · gate clouds kit · CLOUD CARDS v2 for the gate (Blender / Cycles, true volumes).

The v1 cards (Clouds/) were lit for scene 3 (moon right-front-HIGH, 26 deg) and baked through the Neutral display
transform. The gate needs its own light: the low moon (el +8) BEHIND the towers, at 20-90 deg to the side depending
on where the tower stands. v2 cards are SCENE-LINEAR and carry their light in separate channels, so the shader can
light each card for its own place in the gate:

    R = moonlight from behind-right at 35 deg  (the moon nearly behind the cloud: dark body, broad silver lining)
    G = moonlight from behind-right at 70 deg  (the moon off to the side: a lit right flank)
    B = sky light (the gate's haze band above the horizon, the moonlit deck below)
    A = coverage (straight alpha)
  each channel stored as sRGB-encoded (channel / scale) in 8 bits (Unity: sRGB ON -> the shader reads channel / scale
  linear); the scales are in gate_cards.json. The moon is on the RIGHT in the card: mirror the card when the moon is
  on the left of it (Lanbai_GateCloudCard does this from the moon direction, per card).

Uses the cloud workshop's shapes (Clouds/Source/make_clouds.py: same density builder as the v1 cards and the
renders' deck).

  python3 gate_cards.py [--only Congestus Bank] [--scale 0.5] [--samples 96] [--out ../Textures]
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(REPO, 'Clouds', 'Source'))
import make_clouds as MC  # noqa: E402  (resets the factory scene on import)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402
from scipy.ndimage import gaussian_filter, median_filter  # noqa: E402

MOON_EL = 8.0
LIGHTS = (('moon35', 35.0), ('moon70', 70.0))
SHAPES = ['Congestus', 'Bank', 'Strato', 'Puff', 'Wisp']
SUN_E = 4.0


def gate_world(strength=1.0):
    """luminance-only gate sky as the ambient light: the haze band at the horizon, the void overhead, the moonlit
    deck below."""
    w = bpy.data.worlds.new('GateSky')
    bpy.context.scene.world = w
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputWorld')
    bg = N('ShaderNodeBackground')
    tc = N('ShaderNodeTexCoord')
    sep = N('ShaderNodeSeparateXYZ')
    L(tc.outputs['Generated'], sep.inputs[0])
    up = sep.outputs['Z']
    # above: 1.0 at the horizon -> 0.12 by z = 0.4 ; below: 0.55 (the deck)
    m1 = N('ShaderNodeMapRange'); m1.inputs['From Min'].default_value = 0.0; m1.inputs['From Max'].default_value = 0.4
    m1.inputs['To Min'].default_value = 1.0; m1.inputs['To Max'].default_value = 0.12
    m1.interpolation_type = 'SMOOTHSTEP'
    L(up, m1.inputs['Value'])
    m2 = N('ShaderNodeMapRange'); m2.inputs['From Min'].default_value = -0.03; m2.inputs['From Max'].default_value = 0.0
    m2.inputs['To Min'].default_value = 0.0; m2.inputs['To Max'].default_value = 1.0
    m2.interpolation_type = 'SMOOTHSTEP'
    L(up, m2.inputs['Value'])
    mix = N('ShaderNodeMix'); mix.data_type = 'FLOAT'
    L(m2.outputs[0], mix.inputs['Factor'])
    mix.inputs['A'].default_value = 0.55
    L(m1.outputs[0], mix.inputs['B'])
    L(mix.outputs['Result'], bg.inputs['Strength'])
    bg.inputs['Color'].default_value = (strength, strength, strength, 1.0)
    L(bg.outputs[0], out.inputs['Surface'])
    w.lightgroup = 'sky'
    return w


def moon(name, az):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = SUN_E
    ld.color = (1.0, 1.0, 1.0)
    ld.angle = math.radians(0.55)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    el, a = math.radians(MOON_EL), math.radians(az)
    d = Vector((math.cos(el) * math.sin(a), math.cos(el) * math.cos(a), math.sin(el)))
    ob.rotation_euler = (-d).to_track_quat('-Z', 'Y').to_euler()
    ob.lightgroup = name
    return ob


def read_layers(path):
    import OpenEXR
    with OpenEXR.File(path, separate_channels=True) as f:
        ch = {}
        for part in f.parts:
            for k, v in part.channels.items():
                ch[k] = np.asarray(v.pixels, np.float32)
    return ch


def pick(ch, layer, comps='RGB'):
    keys = list(ch.keys())
    out = []
    for c in comps:
        cand = [k for k in keys if k.endswith('.' + c) and layer in k.split('.')[-2:-1]] or \
               [k for k in keys if k == layer + '.' + c] or [k for k in keys if k.endswith(layer + '.' + c)]
        if not cand:
            raise KeyError('%s.%s not in %s' % (layer, c, keys))
        out.append(ch[sorted(cand, key=len)[0]])
    return np.stack(out, -1)


def render_shape(name, out_dir, samples, scale, cache):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    t0 = time.time()
    if name not in cache:
        grid, fn, spec = MC.SHAPES[name](max(scale, 0.5) if scale < 1 else 1.0)
        dens = MC.evaluate(grid, fn)
        cache[name] = (grid, dens, spec)
        print('[%s] density %s %.0fs' % (name, tuple(grid.res), time.time() - t0), flush=True)
    grid, dens, spec = cache[name]
    mat = MC.cloud_material(spec['sigma'], spec.get('g', 0.62))
    MC.import_density('Cloud_' + name, dens, grid, mat)
    res = (int(spec['res'][0] * scale), int(spec['res'][1] * scale))
    MC.frame_camera(MC.occupied_points(dens, grid), res, spec['yaw'], spec['pitch'], spec['lens'], spec['fill'],
                    spec.get('center_bias', (0, 0)))
    sc = bpy.context.scene
    vl = sc.view_layers[0]
    for lg in ('moon35', 'moon70', 'sky'):
        vl.lightgroups.add(name=lg)
    gate_world()
    for lg, az in LIGHTS:
        moon(lg, az)
    p = dict(MC.PRESETS['moon'])
    p.update(view='Standard', look='None', exposure=0.0)
    MC.setup_render(res, samples, p, 16)
    sc.render.image_settings.media_type = 'MULTI_LAYER_IMAGE'
    sc.render.image_settings.file_format = 'OPEN_EXR_MULTILAYER'
    sc.render.image_settings.color_depth = '32'
    exr = os.path.join(out_dir, '_gate_%s.exr' % name)
    sc.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    t1 = time.time()
    ch = read_layers(exr)
    h, w = res[1], res[0]
    comb = pick(ch, 'Combined', 'RGBA').reshape(h, w, 4)
    passes = [pick(ch, 'Combined_' + lg, 'RGB').reshape(h, w, 3) for lg in ('moon35', 'moon70', 'sky')]
    os.remove(exr)
    return comb, passes, (t1 - t0)


def post(comb, passes, alpha_floor=0.004):
    """denoised Combined luminance split by the (smoothed) light-group ratios -> three clean channels, straight alpha"""
    lumw = np.array([0.2126, 0.7152, 0.0722], np.float32)
    a = np.clip(comb[..., 3], 0, 1)
    L = np.maximum(comb[..., :3], 0) @ lumw
    Pl = [np.maximum(p, 0) @ lumw for p in passes]
    Ps = [gaussian_filter(x, 1.5) for x in Pl]
    tot = np.maximum(sum(Ps), 1e-9)
    prem = np.stack([L * (x / tot) for x in Ps], -1)
    a_g = MC.guided_alpha(prem, median_filter(a, size=3), r=4, eps=2e-4)
    wgt = MC.sstep(0.97, 0.995, np.minimum(a, a_g))
    a = a * wgt + a_g * (1 - wgt)
    straight = MC.push_pull_colour(prem, np.maximum(a, 1e-8), conf=0.03)
    a = np.clip((a - alpha_floor) / (1 - alpha_floor), 0, 1)
    return straight, a


def srgb_encode(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def main():
    a = sys.argv[1:]
    only = SHAPES
    if '--only' in a:
        i = a.index('--only') + 1
        only = []
        while i < len(a) and not a[i].startswith('--'):
            only.append(a[i])
            i += 1
    scale = float(a[a.index('--scale') + 1]) if '--scale' in a else 1.0
    spp = int(a[a.index('--samples') + 1]) if '--samples' in a else 96
    out = os.path.abspath(a[a.index('--out') + 1]) if '--out' in a else os.path.join(os.path.dirname(HERE), 'Textures')
    os.makedirs(out, exist_ok=True)
    meta_path = os.path.join(out, 'gate_cards.json')
    meta = json.load(open(meta_path)) if os.path.exists(meta_path) else {}
    meta['_about'] = ('Gate cloud cards v2: R = moon behind-right 35 deg, G = 70 deg, B = sky; each = sRGB(linear / '
                      'scale); A = straight alpha. moon el %.0f, sun strength %.1f (= MoonE 1 in the shader is this '
                      'light), sky = luminance gradient (horizon 1, zenith 0.12, deck 0.55). cloud_base_v: v of '
                      'the flat cloud base (v = 0 bottom).' % (MOON_EL, SUN_E))
    from PIL import Image
    cache = {}
    for name in only:
        comb, passes, tr = render_shape(name, out, spp, scale, cache)
        straight, al = post(comb, passes)
        solid = al > 0.5
        scales = [float(max(np.percentile(straight[..., k][solid], 99.7), 1e-6)) for k in range(3)]
        enc = np.stack([srgb_encode(straight[..., k] / scales[k]) for k in range(3)], -1)
        rng = np.random.default_rng(1)
        d = (rng.random(al.shape) - rng.random(al.shape))[..., None] * 0.5
        rgba = np.concatenate([enc, al[..., None]], -1) * 255 + 0.5 + d
        rgba = np.clip(rgba, 0, 255).astype(np.uint8)
        rgba[..., 3][al < 1.5 / 255] = 0
        png = os.path.join(out, 'GateCard_%s.png' % name)
        Image.fromarray(rgba, 'RGBA').save(png, optimize=True)
        ys, xs = np.nonzero(al > 0.03)
        h, w = al.shape
        rows = np.nonzero((al > 0.5).sum(1) > 0.25 * (al > 0.5).sum(1).max())[0]
        meta[name] = dict(file=os.path.basename(png), size=[w, h], scale=[round(s, 6) for s in scales],
                          bbox_uv=[round(xs.min() / w, 4), round(1 - ys.max() / h, 4), round(xs.max() / w, 4),
                                   round(1 - ys.min() / h, 4)],
                          cloud_base_v=round(1 - (rows.max() + 1) / h, 4) if len(rows) else 0.0,
                          render_s=round(tr, 1))
        json.dump(meta, open(meta_path, 'w'), indent=1)
        print('[%s] %dx%d render %.0fs scales %s -> %s' % (name, w, h, tr, np.round(scales, 4), png), flush=True)


if __name__ == '__main__':
    main()
