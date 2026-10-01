"""蓝白 / Lanbai · gate · the cloud sea as a VOLUMETRIC IMPOSTOR seen from the bus eye.

The delivered CloudSea strips are exactly this idea (a cumulus deck seen from 58 m above, 130-690 m out), but lit
for scene 3 (moon right-front-high) and only 62 deg wide. For the gate frames we render our own decks with the
cloud workshop's density builder (deliver/Clouds/Source/make_clouds.py), lit by the GATE's lights (low moon
front-left -12/+8 = back-lit silver crests; the tear's violet-white light from straight ahead; the haze-band sky),
110 deg wide, then reproject them in gate_scene.py onto a camera-facing quad: from the eye it is pixel-exact; a
deck rendered for eye height h is valid for any eye height k*h if the quad is scaled by k (similar triangles).

  python3 cloud_deck.py near [--scale 0.25] [--samples 24]      # 100-900 m (rendered once, used by U6/U7/key/U8)
  python3 cloud_deck.py far  [--scale 0.25]                     # 0.7-6 km band to the horizon
  python3 cloud_deck.py rear [--scale 0.25]                     # near deck, lights from behind (the rear window)
Output: wip/deck_<name>.npz  (prem rgb + alpha, scene-linear fill space, camera spec) + a preview PNG.
"""
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAN = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(LAN, 'deliver', 'Clouds', 'Source'))
import make_clouds as MC  # noqa: E402  (resets the factory scene on import)
import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

sys.path.insert(0, os.path.join(LAN, 'tear', 'v2'))
import render_tear as RT  # noqa: E402

EYE_H = 59.6          # U7b eye above the cloud top (gate_layout: h_bus(U7b) + 1.7)
F = RT.F

# a deck = sub-grids (y0, y1, voxel m at q 1, cell m, blob r range, heads, z top, fade-in m at y0, fade-out m at y1)
NEAR_GRIDS = [dict(y0=95.0, y1=720.0, vox=1.3, cell=17.0, r=(11.0, 20.0), heads=14, top=52.0, fin=0.0, fout=70.0),
              dict(y0=640.0, y1=2500.0, vox=3.0, cell=28.0, r=(17.0, 32.0), heads=40, top=80.0, fin=70.0,
                   fout=500.0)]
FAR_GRID = dict(y0=2300.0, y1=9000.0, vox=7.0, cell=60.0, r=(36.0, 70.0), heads=40, top=170.0, fin=200.0, fout=1500.0)
DECKS = {
    'near': dict(grids=NEAR_GRIDS, hfov=112.0, pitch=-9.0, res=(3600, 560), sigma=1.4, moon_rel=-12.0, seed=0),
    'rear': dict(grids=NEAR_GRIDS + [FAR_GRID], hfov=112.0, pitch=-9.0, res=(3600, 560), sigma=1.4, moon_rel=168.0,
                 seed=5),
    # round 2: ONE forward deck for every forward shot (U6, U7, key, U8): out to 9 km (no shelf at 2.5 km), lit by the
    # moon + a desaturated cold sky only; the tear's pool, its shadow lanes and the violet spill are added per pixel
    # in gate_scene.deck_impostor (Unity: Tear_CloudGlow x a baked lane mask), so the deck is valid at any t
    # round 2 rear deck: front-lit by the low moon behind the viewer, the arms' LONG SHADOWS on it (arms are invisible
    # shadow casters posed at the rear shot's time), lit silver, no violet
    'rear3': dict(grids=NEAR_GRIDS + [FAR_GRID], hfov=112.0, pitch=-9.0, res=(3600, 560), sigma=1.4, moon_rel=168.0,
                  seed=5, sky_desat=0.8, arms=True),
    'gate3': dict(grids=NEAR_GRIDS + [FAR_GRID], hfov=112.0, pitch=-9.0, res=(3600, 560), sigma=1.4, moon_rel=-12.0,
                  seed=0, no_tear=True, sky_desat=0.65),
    # round 3 (tech M9): the rear deck WITHOUT the baked arm shadows (Unity's cloud cards receive none)
    'rear4': dict(grids=NEAR_GRIDS + [FAR_GRID], hfov=112.0, pitch=-9.0, res=(3600, 560), sigma=1.4, moon_rel=168.0,
                  seed=5, sky_desat=0.8, arms=False),
    # round 3 (awe B10 / U8side): the same deck looking RIGHT (yaw +100 from the tear): the moon at -112 relative
    'side3': dict(grids=NEAR_GRIDS + [FAR_GRID], hfov=112.0, pitch=-9.0, res=(3600, 560), sigma=1.4, moon_rel=-112.0,
                  seed=3, no_tear=True, sky_desat=0.65),
}


def deck_field(d, g, q, k):
    rng = np.random.default_rng(71 + d.get('seed', 0) + 13 * k)
    t = math.tan(math.radians(d['hfov'] / 2))
    y0, y1 = g['y0'], g['y1']
    xh = t * y1 + 60.0
    trap = lambda x, y: 1.0 if abs(x) < 40.0 + t * (y + 20.0) else 0.0
    sc = g['cell'] / 17.0
    masses = MC.layer_masses(rng, -xh, xh, y0 - 20, y1, g['cell'], g['r'][0], g['r'][1], 6.0 * sc,
                             1 / (260.0 * sc), 0.20, taper=trap)
    extra = []
    for y in rng.uniform(y0 + 0.25 * (y1 - y0), y1 - 0.08 * (y1 - y0), g['heads']):
        x = rng.uniform(-1, 1) * (t * y)
        extra.append((x, y, 15 * sc, rng.uniform(15, 26) * sc))
    blobs = MC.sheet_blobs(rng, masses, 0.5, levels=1) + MC.mound_blobs(rng, extra, levels=2, n_range=(3, 6),
                                                                        ratio=(0.35, 0.55))
    st = 30.0 * sc
    for x in np.arange(-xh, xh, st):
        for y in np.arange(y0 - 20, y1, st):
            if trap(x, y + st / 2) or trap(x + st, y + st / 2) or trap(x - st, y + st / 2):
                blobs.append((np.array([x + st / 2, y + st / 2, 3.0 * sc], np.float32), 24.0 * sc, (1.0, 1.0, 0.28)))
    vox = g['vox'] / q
    grid = MC.Grid((-xh - 10, y0 - 30, -4 * sc), (xh + 10, y1 + 10, g['top']), vox)
    inner = MC.cumulus_field(blobs, K=2.5 * sc, base_z=0.0, top_z=24.0 * sc, edge=0.7 * sc,
                             disp=(4.0 * sc, 1.0 * sc, 0.5 * sc), fringe=3.0 * sc, warp_amp=10.0 * sc,
                             warp_freq=1 / (150.0 * sc), seed_off=(0.3 + 0.2 * k, 0.5, 0.2), wisp_amt=0.10,
                             bill_f=1 / (30.0 * sc), bill_hi_f=1 / (12.0 * sc), fuzz_f=1 / (6.0 * sc))
    fin, fout = g['fin'], g['fout']

    def fn(P):
        y = P[..., 1]
        w = MC.sstep(y1, y1 - fout, y)
        if fin > 0:
            w = w * MC.sstep(y0, y0 + fin, y)
        # outside the view wedge: nothing (saves the renderer)
        w = w * (np.abs(P[..., 0]) < 60.0 + t * (y + 40.0))
        return inner(P) * w
    return grid, fn


def gate_world(moon_rel, desat=0.0):
    """the gate sky (haze band toward +y, void above) as the deck's ambient light (desat: toward a cold grey, so
    the moonlit deck reads silver, not lavender)."""
    w = bpy.data.worlds.new('DeckSky')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    from bl import NB
    b = NB(nt)
    tc = b.N('ShaderNodeTexCoord')
    x, y, z = b.sep(tc.outputs['Generated'])
    el = b.math('MULTIPLY', b.math('ARCSINE', b.math('MINIMUM', b.math('MAXIMUM', z, -1.0), 1.0)), 180 / math.pi)
    az = b.math('ABSOLUTE', b.math('MULTIPLY', b.math('ARCTAN2', x, y), 180 / math.pi))
    if moon_rel > 90:       # rear deck: the tear (and the band) are behind the camera
        az = b.math('SUBTRACT', 180.0, az)
    band = b.mix(b.smooth(az, 0, 50), tuple(F['HazeNear']), tuple(F['HazeFar']))
    wel = b.math('POWER', b.smooth(el, 4.0, 30.0, 1.0, 0.0), 1.5)
    wb = b.math('MULTIPLY', b.smooth(az, 50, 60, 1, 0), wel)
    sky = b.mix(wb, tuple(F['Void']), band)
    sky = b.scale(sky, b.smooth(el, -25, 0, 0.3, 1.0))
    if desat > 0:
        lum = b.vmath('DOT_PRODUCT', sky, b.vec((0.2126, 0.7152, 0.0722)))
        grey = b.rgbmul(b.gray(lum), b.rgb((0.92, 0.98, 1.12)))
        sky = b.mix(desat, sky, grey)
    bg = b.N('ShaderNodeBackground')
    b.L(sky, bg.inputs['Color'])
    o = b.N('ShaderNodeOutputWorld')
    b.L(bg.outputs[0], o.inputs['Surface'])


def sun(name, az, el, col_hex, E, angle=0.6):
    ld = bpy.data.lights.new(name, 'SUN')
    c = RT.hexlin(col_hex)
    ld.color = tuple(c / c.max())
    ld.energy = math.pi * E
    ld.angle = math.radians(angle)
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    a, e = math.radians(az), math.radians(el)
    to_light = Vector((math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)))
    ob.rotation_euler = (-to_light).to_track_quat('-Z', 'Y').to_euler()
    return ob


def shadow_arms(t, eye_h):
    """the gate arms at time t as invisible shadow casters in the REAR deck's frame (camera at the rear eye looking
    back: x' = -(x - ex), y' = -(y - ey))."""
    sys.path.insert(0, HERE)
    import gate_layout as G
    import gate_scene as GS
    from mathutils import Matrix
    e = G.eye_cf(t, G.EYE_STAND_REAR)
    T = np.eye(4)
    T[0, 0] = -1.0
    T[1, 1] = -1.0
    T[0, 3] = e[0]
    T[1, 3] = e[1]
    mat = bpy.data.materials.new('ShadowCaster')
    n = 0
    for it in G.build_layout():
        root, R = G.pose_at(it, t)
        W, _ = G.world_centreline(it, t, 40)
        if W[:, 2].max() < 0:
            continue
        me = GS.variant_mesh(it['variant'], 1, it.get('girth', 1.0), it.get('form'))
        ob = bpy.data.objects.new('Shadow_' + it['id'], me)
        bpy.context.scene.collection.objects.link(ob)
        M = np.eye(4)
        M[:3, :3] = R * it['scale']
        M[:3, 3] = root
        ob.matrix_world = Matrix((T @ M).tolist())
        ob.visible_camera = False
        ob.data.materials.clear()
        ob.data.materials.append(mat)
        n += 1
    print('shadow casters', n)


def main():
    a = sys.argv[1:]
    name = a[0]
    scale = float(a[a.index('--scale') + 1]) if '--scale' in a else 1.0
    spp = int(a[a.index('--samples') + 1]) if '--samples' in a else 24
    q = float(a[a.index('--q') + 1]) if '--q' in a else 1.0
    tag = a[a.index('--tag') + 1] if '--tag' in a else name
    eye_h = float(a[a.index('--eye_h') + 1]) if '--eye_h' in a else EYE_H
    # the tear core relative to the eye (x right, y ahead, z up), from gate_layout at the shot time
    tear = tuple(float(v) for v in a[a.index('--tear') + 1].split(',')) if '--tear' in a else (20.0, 1503.0, 196.0)
    d = DECKS[name]
    t0 = time.time()
    bpy.ops.wm.read_factory_settings(use_empty=True)
    mat = MC.cloud_material(d['sigma'], 0.62)
    for k, g in enumerate(d['grids']):
        grid, fn = deck_field(d, g, q, k)
        dens = MC.evaluate(grid, fn)
        print('[%s/%d] density %s = %.1fM voxels, %.0fs, occ %.3f' % (name, k, tuple(grid.res), dens.size / 1e6,
                                                                    time.time() - t0, (dens > 0.02).mean()))
        MC.import_density('Deck_%s_%d' % (name, k), dens, grid, mat)
        del dens
    # camera at the eye, looking +y, pitch
    cd = bpy.data.cameras.new('Cam')
    cd.sensor_fit = 'HORIZONTAL'
    cd.angle = math.radians(d['hfov'])
    cd.clip_start = 1.0
    cd.clip_end = 1e5
    cam = bpy.data.objects.new('Cam', cd)
    bpy.context.scene.collection.objects.link(cam)
    bpy.context.scene.camera = cam
    cam.location = (0.0, 0.0, eye_h)
    pt = math.radians(d['pitch'])
    cam.rotation_euler = Vector((0.0, math.cos(pt), math.sin(pt))).to_track_quat('-Z', 'Y').to_euler()
    W, H = int(d['res'][0] * scale), int(d['res'][1] * scale)
    # vfov check: the horizontal fit decides; H follows the requested aspect
    gate_world(d['moon_rel'], d.get('sky_desat', 0.0))
    mr = d['moon_rel']
    sun('Moon', mr, 8.0, '#D6E4FF', 1.0, 1.0)
    if mr < 90 and not d.get('no_tear'):
        # the tear's light on the deck: a point at the core (Blender W; irradiance pi x E at r: P = 4 pi^2 r^2 E),
        # E 0.8 at 500 m (the ring), so the deck glows violet-white round the tear's foot and only faintly near
        # the bus; + the bible's directional tear light (E 0.8) at 25 % for the general violet edge of the crests
        ld = bpy.data.lights.new('TearPt', 'POINT')
        c = RT.hexlin('#A99DE1')
        ld.color = tuple(c / c.max())
        ld.energy = 4 * math.pi ** 2 * 500.0 ** 2 * 0.8
        ld.shadow_soft_size = 60.0
        ob = bpy.data.objects.new('TearPt', ld)
        bpy.context.scene.collection.objects.link(ob)
        ob.location = (tear[0], tear[1], tear[2] + eye_h)
        sun('Tear', 0.0, 8.0, '#A99DE1', 0.2, 3.0)
    if d.get('arms'):
        shadow_arms(float(a[a.index('--t') + 1]), eye_h)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    MC._set_enum(sc.cycles, 'denoiser', 'OPENIMAGEDENOISE')
    sc.cycles.volume_bounces = 10
    sc.cycles.max_bounces = 14
    sc.cycles.diffuse_bounces = 0
    sc.cycles.glossy_bounces = 0
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.sample_clamp_indirect = 10.0
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.view_settings.exposure = 0.0
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '32'
    exr = os.path.join(HERE, 'wip', '_deck_%s.exr' % tag)
    sc.render.filepath = exr
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    print('[%s] %dx%d render %.0fs' % (name, W, H, time.time() - t1))
    raw = MC.load_float_image(exr)
    prem, al = raw[..., :3], np.clip(raw[..., 3], 0, 1)
    a_g = MC.guided_alpha(prem, MC.median_filter(al, size=3), r=4, eps=2e-4)
    w = MC.sstep(0.97, 0.995, np.minimum(al, a_g))
    al2 = al * w + a_g * (1 - w)
    prem = np.maximum(prem, 0) * (al2 / np.maximum(al, 1e-6))[..., None] * (al > 1e-6)[..., None] + \
        np.maximum(prem, 0) * (al <= 1e-6)[..., None]
    out = os.path.join(HERE, 'wip', 'deck_%s.npz' % tag)
    np.savez_compressed(out, prem=prem.astype(np.float16), alpha=al2.astype(np.float16), hfov=d['hfov'],
                        pitch=d['pitch'], eye_h=eye_h, res=(W, H), moon_rel=mr, tear=tear)
    # preview: straight colour over the haze, simple display
    sys.path.insert(0, os.path.join(LAN, 'tear', 'v2'))
    import s4
    bgc = F['HazeFar'][None, None]
    comp = prem + bgc * (1 - al2[..., None])
    s4.save(s4.to_display(comp, bloom=False, vignette=False), os.path.join(HERE, 'wip', 'deck_%s.png' % tag))
    print('[%s] total %.0fs -> %s' % (tag, time.time() - t0, out))


if __name__ == '__main__':
    main()
