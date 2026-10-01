"""蓝白 / Lanbai · 触手之门 v2 · the gate, assembled at real scale (Blender 5.0.1 bpy, Cycles CPU).

    python3 gate_scene.py render SHOT W H SPP OUT_BASENAME [--set k:v,...] [--only layer,..] [--nobus]
    python3 gate_scene.py export                # GateLayout_v2.json + GateLayout_v2.fbx + GateTide_v2.fbx
    SHOT = U6 | U7 | U8 | rear | key

Every colour is a Unity FILL (scene-linear); lights are the bible's E values (Blender sun strength = pi x E);
the EXR goes through the bible's own PPv2 S4 simulator (tear/v2/s4.py: bloom, Neutral, desktop vignette) -> PNG.
Materials mirror the delivered shaders: tentacles = build_library.make_material (Lanbai/TentacleSway preview) +
LanbaiFog (view-dependent haze colour, cap, height falloff); tear = tear kit v2 (render_tear.kit_materials);
tide = Lanbai/TentacleTide (atlas, fog cap 0.92). The cloud floor is a stand-in heightfield (see README).
Blender world = CF of gate_layout.py (tear foot at the origin, cloud top z = 0, the bus toward -y).
"""
import json
import math
import os
import sys
import time

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import gate_layout as G  # noqa: E402

import bpy  # noqa: E402
from mathutils import Matrix, Vector  # noqa: E402

sys.path.insert(0, os.path.join(G.LAN, 'tear', 'v2'))
import render_tear as RT  # noqa: E402  (tear kit v2 materials / mesh builder, sky)
import kit_mesh as K  # noqa: E402
from bl import NB, new_mat, load_img, mesh_from_numpy  # noqa: E402
import s4  # noqa: E402

BL = G.BL
F = RT.F
TEXT = os.path.join(G.LAN, 'deliver', 'Tentacles', 'Textures')
CLOUDS = os.path.join(G.LAN, 'deliver', 'Clouds')
TEAR_TEX = os.path.join(G.LAN, 'deliver', 'Tear', 'Textures')
OUT = HERE

E_MOON, E_TEAR, E_FILL = 1.00, 0.80, 0.24          # bible §6·4 light table (E)
COL_MOON = RT.hexlin('#D6E4FF') / RT.hexlin('#D6E4FF').max()
COL_TEAR = RT.hexlin('#A99DE1') / RT.hexlin('#A99DE1').max()
COL_FILL = RT.hexlin('#5A6488') / RT.hexlin('#5A6488').max()

# the look: every tunable in one place (--set k:v overrides)
LOOK = dict(
    fog=0.0006, fog_extra=1.5, fog_extra_h=25.0, cap=0.92, cap_h=500.0, cap_from=1300.0, cap_to=1700.0,
    tide_cap=0.80, cap_h_col=5000.0, kit_glossy=0.0, fog_mid=1.0, fog_colossus=1.0, fog_pillar=1.0, fog_hero=1.0, fog_bg=1.0, arm_spec=1.0, near_spec=0.45, glow_fog=0.35, moon_glow_fog=0.35,
    rim_moon=0.80, rim_tear=0.08, tip_glow=1.0, rim_px=2.2, rim_px_near=5.0, rim_moon_px=1.3, rim_tear_px=2.2,
    rim_gain_near=1.0, rim_gain_pillar=0.25, rim_gain_mid=0.14, rim_gain_colossus=0.08, rim_gain_hero=0.06,
    rim_gain_bg=0.05, rim_gain_rear=0.1, rim_gain_surge=0.04, below_desat=0.6, fog_surge=1.0, spec_surge=0.15,
    spec_near=0.6, spec_pillar=0.08, spec_mid=0.3, spec_colossus=0.2, spec_hero=0.15, spec_bg=0.15, spec_rear=1.0,
    cloud_alb=0.72, cloud_moon=0.6, cloud_tear=1.0, cloud_glow=1.0, cloud_amb=1.0, cloud_rim=1.0, cloud_detail=0.0,
    card_fog=0.5, card_gain=1.0,
    shaft=0.8, halo=1.0, folds=0.55, intensity=1.0, aur_a=1.6, aur_k=0.9, aur_b=0.06,
    stars=1.0, dome_a=40.0, cloud_mist=0.7, floor='deck', mist=1.0, mist_gain=1.0, far_gain=0.6, deck_extra=0.5, deck_fog=1.0, deck_gain=0.52, deck_desat=0.8, row_gain=0.55, row_tint=(0.80, 0.86, 1.0), row_violet=1.3, row_moon=0.8,
    shells=10, shell_noise=1.0, tubes=1.15, deck_quiet=1.0, deck_quiet_near=0.30, deck_quiet_far=0.12,
    deck_quiet_px=28.0, deck_near_gain=0.7, streak_keep=0.8, pool=0.85,
    cards=0.0, puffs=0, puff_gain=0.5, puff_w=(0.08, 0.2), puff_vis=(0.12, 0.3),
    sleeves=0.0, root_dissolve=18.0,     # run 6: the root sleeve cards read as a striped 'barcode' band with a straight
                                         # top at the hand roots; retired. The arm's own cloud fade dissolves instead.
)


# ============================================================================================ scene basics
def setup(W, H, spp):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = spp
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02 if spp < 100 else 0.012
    sc.cycles.use_denoising = True
    try:
        sc.cycles.denoiser = 'OPENIMAGEDENOISE'
        sc.cycles.denoising_input_passes = 'RGB_ALBEDO_NORMAL'
        sc.cycles.denoising_prefilter = 'ACCURATE'
    except Exception:
        pass
    sc.cycles.max_bounces = 1
    sc.cycles.diffuse_bounces = 0
    sc.cycles.glossy_bounces = 1
    sc.cycles.transmission_bounces = 0
    sc.cycles.volume_bounces = 0
    sc.cycles.transparent_max_bounces = 128
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.cycles.pixel_filter_type = 'BLACKMAN_HARRIS'
    sc.cycles.filter_width = 1.5
    sc.cycles.sample_clamp_indirect = 4.0
    sc.render.resolution_x, sc.render.resolution_y = W, H
    sc.render.resolution_percentage = 100
    sc.view_settings.view_transform = 'Standard'
    sc.view_settings.look = 'None'
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_depth = '32'
    sc.render.threads_mode = 'FIXED'
    sc.render.threads = 4
    return sc


def sun(name, direction, strength, colour, angle_deg=0.5, shadow=True):
    ld = bpy.data.lights.new(name, 'SUN')
    ld.energy = strength
    ld.color = tuple(colour)
    ld.angle = math.radians(angle_deg)
    ld.use_shadow = shadow
    try:
        ld.cycles.cast_shadow = shadow
    except Exception:
        pass
    ob = bpy.data.objects.new(name, ld)
    bpy.context.scene.collection.objects.link(ob)
    d = Vector(tuple(direction)).normalized()               # direction the light TRAVELS
    ob.rotation_euler = (-d).to_track_quat('Z', 'Y').to_euler()
    return ob


def camera(pos, yaw, pitch, hfov, name='Cam', roll=0.0):
    cd = bpy.data.cameras.new(name)
    cd.sensor_fit = 'HORIZONTAL'
    cd.angle = math.radians(hfov)
    cd.clip_start = 0.02
    cd.clip_end = 60000.0
    cam = bpy.data.objects.new(name, cd)
    bpy.context.scene.collection.objects.link(cam)
    cam.location = tuple(pos)
    cam.rotation_euler = (math.radians(90 + pitch), math.radians(roll), math.radians(-yaw))
    bpy.context.scene.camera = cam
    return cam


def exclude_from(lamps, objs):
    """light linking: `lamps` do not light `objs`."""
    col = bpy.data.collections.new('LL_ex_%d' % len(bpy.data.collections))
    for o in objs:
        col.objects.link(o)
    for co in col.collection_objects:
        co.light_linking.link_state = 'EXCLUDE'
    for l in lamps:
        l.light_linking.receiver_collection = col
    return col


# ============================================================================================ LanbaiFog
class Fog:
    """Per-render constants of the gate's aerial perspective (bible 1.6 / 6.4): exponential density 0.0006
    (+ 0.5 x exp(-h / 60 m) over the cloud tops); beyond 1.3-1.7 km capped (0.6) and x exp(-h / 500 m) so
    far arms dissolve FEET first and are never brighter than the sky at that elevation. Fog COLOUR is
    view-dependent: the haze band (LanbaiHorizon) + the moon's air (its halo) + the tear's air (its halo
    cards, only in front of them)."""

    def __init__(self, t, cam_pos, look):
        self.t = t
        self.cam = np.asarray(cam_pos, float)
        self.k = look
        self.S = G.tear_H(t) / G.TD.H
        self.halo_img = load_img(os.path.join(TEAR_TEX, 'Halo_512.png'), 'sRGB', 'CHANNEL_PACKED')

    def nodes(self, b, cap=True, cap_v=None, cap_h=None, dens=1.0, extra=True, glow=True, reveal=1.0):
        """(factor, colour) sockets in node builder b."""
        k = self.k
        geo = b.N('ShaderNodeNewGeometry')
        camd = b.N('ShaderNodeCameraData')
        dist = camd.outputs['View Distance']
        P = geo.outputs['Position']
        V = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)          # camera -> point
        z = b.sep(P)[2]
        h = b.math('MAXIMUM', z, 0.0)
        rho = k['fog'] * dens
        if extra:        # the mist lying on the cloud sea is the same for every layer (the density scale is not)
            rho = b.math('MULTIPLY', b.math('ADD', dens, b.math('MULTIPLY', b.math('EXPONENT', b.math('DIVIDE', h, -k['fog_extra_h'])),
                                                                             k['fog_extra'])), k['fog'])
        f = b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('MULTIPLY', b.math('MULTIPLY', dist, rho), -1.0)))
        if cap:
            cv = k['cap'] if cap_v is None else cap_v
            fc = b.math('MINIMUM', f, cv)
            ch = k['cap_h'] if cap_h is None else cap_h
            if ch:
                fc = b.math('MULTIPLY', fc, b.math('EXPONENT', b.math('DIVIDE', h, -ch)))
            f = b.mixf(b.smooth(dist, k['cap_from'], k['cap_to']), f, fc)
        if reveal < 0.999:          # round 3 (tech B1): _Reveal after the cap: f = lerp(1, f, _Reveal)
            f = b.math('SUBTRACT', 1.0, b.math('MULTIPLY', b.math('SUBTRACT', 1.0, f), float(reveal)))
        col = self.colour(b, V, dist, glow)
        return f, col

    def colour(self, b, V, dist=None, glow=True):
        """LanbaiHorizon(V) + moon air + tear air (fill space)."""
        sky = horizon_nodes(b, V, self.k)
        # the moon's air (identical to the sky's halo term)
        cosm = b.vmath('DOT_PRODUCT', V, b.vec(G.L_MOON))
        ang = b.math('MULTIPLY', b.math('ARCCOSINE', b.math('MINIMUM', cosm, 1.0)), 180 / math.pi)
        hi = b.math('ADD', b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', ang, -self.k.get('aur_k', 1.1))), self.k.get('aur_a', 0.55)),
                    b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', ang, -0.32)), self.k.get('aur_b', 0.05)))
        sky = b.rgbadd(sky, b.scale(b.rgb(tuple(RT.hexlin('#8FA3C8'))), b.math('MULTIPLY', hi, self.k['moon_glow_fog'])))
        if glow and self.k['glow_fog'] > 0:
            sky = b.rgbadd(sky, b.scale(self.tear_air(b, V, dist), self.k['glow_fog']))
        return sky

    def tear_air(self, b, V, dist):
        """the halo cards (and the widest halo layer of the folds card) seen along V, where they are BEHIND the
        shaded point (the cards themselves are drawn on top of anything behind them)."""
        S = self.S
        c_a = float(G.TD.path(np.array([K.HALO_T]))[0]) + 12.0
        AX, AC = G.TD.AX, G.TD.AC
        y_plane = 50.0 * S
        dy = y_plane - self.cam[1]
        vx, vy, vz = b.sep(V)
        tpl = b.math('DIVIDE', dy, b.math('MAXIMUM', vy, 1e-4))                 # ray distance to the plane
        in_front = b.math('GREATER_THAN', vy, 1e-3)
        if dist is not None:
            in_front = b.math('MULTIPLY', in_front, b.math('LESS_THAN', dist, tpl))
        px = b.math('ADD', self.cam[0], b.math('MULTIPLY', vx, tpl))
        pz = b.math('ADD', self.cam[2], b.math('MULTIPLY', vz, tpl))
        acc = None
        cards = list(K.HALO_CARDS)          # v4: (w, h, depth, phase, gain); the widest layer is gone since v3
        for i, (w, h, d, ph, gk) in enumerate(cards):
            c = G.TD.P(K.HALO_T, c_a, d)[()] * S
            rx = b.math('SUBTRACT', px, c[0])
            rz = b.math('SUBTRACT', pz, c[2])
            u = b.math('ADD', 0.5, b.math('DIVIDE', b.math('ADD', b.math('MULTIPLY', rx, AC[0]), b.math('MULTIPLY', rz, AC[2])), w * S))
            v = b.math('ADD', 0.5, b.math('DIVIDE', b.math('ADD', b.math('MULTIPLY', rx, AX[0]), b.math('MULTIPLY', rz, AX[2])), h * S))
            uv = b.N('ShaderNodeCombineXYZ')
            b.L(u, uv.inputs[0]); b.L(v, uv.inputs[1])
            tx = b.tex(self.halo_img, uv.outputs[0])
            g = b.scale(tx.outputs['Color'], gk)
            acc = g if acc is None else b.rgbadd(acc, g)
        acc = b.scale(acc, b.math('MULTIPLY', in_front, self.k['halo'] * self.k['intensity']))
        return acc


def fog_wrap(mat, fog, clip=True, **kw):
    """insert LanbaiFog into a finished material: out = mix(surface, emission(fog colour), fog factor); clip = the
    arm ends at the cloud-sea top (Unity: clip(worldPos.y - _Udon_CloudTopY + 2), see README_GateLayout)."""
    nt = mat.node_tree
    b = NB(nt)
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs['Surface'].links[0].from_socket
    f, col = fog.nodes(b, **kw)
    em = b.emission(col)
    sh = b.mixs(f, src, em)
    if clip:
        # round 2 (critique M13): the last ~25 m above the cloud top fade toward the lit cloud-top colour (noisy, so
        # the arm goes INTO the sea, not onto a shelf); clipped only below cloudTop - 5 m
        # (Unity: _CloudTopColor, _Udon_CloudTop.x, _CloudFade 25)
        geo = b.N('ShaderNodeNewGeometry')
        z = b.sep(geo.outputs['Position'])[2]
        nz = b.N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0 / 18.0; nz.inputs['Detail'].default_value = 3.0
        b.L(geo.outputs['Position'], nz.inputs['Vector'])
        # resume: the fade must be complete where the deck impostor's plane (z = 12 m x k) starts hiding the arm,
        # else the body stands on that plane with a straight cut (Unity: the real cloud cards are bumpy; keep 25 m)
        zp = float(fog.k.get('zplane', 0.0))
        zf = b.math('ADD', b.math('SUBTRACT', z, zp), b.math('MULTIPLY', b.math('SUBTRACT', nz.outputs['Fac'], 0.5), 44.0))
        ctc = fog.k.get('cloud_top_col', (0.050, 0.056, 0.068))      # resume: = the lit deck at the roots (was 0.026: a dark cut)
        sh = b.mixs(b.smooth(zf, 46.0, 4.0), sh, b.emission(b.mix(f, tuple(ctc), col)))
        # run 6: the lowest part of the fade DISSOLVES (noisy alpha) instead of standing as a flat cloud-coloured band:
        # where a braided root crosses the deck plane at a grazing angle the band read as a striped 'barcode' with a
        # straight top (Unity: the same _CloudFade zone with a dithered clip / alpha-to-coverage, the cloud cards behind)
        rd = float(fog.k.get('root_dissolve', 18.0))
        if rd > 0:
            sh = b.mixs(b.smooth(zf, rd, -2.0), sh, b.transparent())
        sh = b.mixs(b.smooth(z, -6.0, -4.0), b.transparent(), sh)
    b.L(sh, out.inputs['Surface'])
    return mat


# ============================================================================================ sky
def horizon_nodes(b, V, k):
    """LanbaiHorizon v2.1 (run 2), fill space, world direction V: the luminous haze band (#484D63 next to the tear
    -> #2A3041 at 50 deg az), full up to +4 deg el and fading to the void by ~+30 (gate_layout.band_el), void
    #070A14 elsewhere; below the horizon x 0.55..1. Azimuth from +y (the tear direction; the bus drives along +y).
    The Unity side: Lanbai/Sky band + LanbaiFog.cginc LanbaiHorizon() use the same profile (README_GateLayout)."""
    x, y, z = b.sep(V)
    el = b.math('MULTIPLY', b.math('ARCSINE', b.math('MINIMUM', b.math('MAXIMUM', z, -1.0), 1.0)), 180 / math.pi)
    az = b.math('ABSOLUTE', b.math('MULTIPLY', b.math('ARCTAN2', x, y), 180 / math.pi))
    band = b.mix(b.smooth(az, 0, 50), tuple(F['HazeNear']), tuple(F['HazeFar']))
    if k.get('band_ramp', 1.0) < 0.999:      # round 3: the band comes up with S4 (30 s smoothstep from U6): before
        # it, the horizon is act 3's moonlit night (fog fill #242A40)
        band = b.mix(k['band_ramp'], tuple(RT.hexlin('#242A40')), band)
    lo, hi, pw = G.BAND_EL
    wel = b.math('POWER', b.smooth(el, lo, hi, 1.0, 0.0), pw)
    wb = b.math('MULTIPLY', b.smooth(az, 50, 60, 1, 0), wel)
    sky = b.mix(wb, tuple(F['Void']), band)
    # round 2 (critique B8): below the horizon the air over the cloud sea is moonlit silver, not the lavender band
    # (Unity: LanbaiHorizon(), dir.y < 0: lerp(band, luminance x (0.92, 0.98, 1.12), _BelowDesat x saturate(-el / 4)))
    if k.get('below_desat', 0) > 0:
        lum = b.vmath('DOT_PRODUCT', sky, b.vec((0.2126, 0.7152, 0.0722)))
        grey = b.rgbmul(b.gray(lum), b.rgb((0.92, 0.98, 1.12)))
        sky = b.mix(b.math('MULTIPLY', b.smooth(el, 0.0, -4.0), k['below_desat']), sky, grey)
    return b.scale(sky, b.smooth(el, -25, 0, 0.55, 1.0))


def world(look):
    """Lanbai/Sky night + haze band v2.1 + moon disc and halo + sparse stars (gain 0.12: bright ones only)."""
    w = bpy.data.worlds.new('GateSky')
    bpy.context.scene.world = w
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    b = NB(nt)
    tc = b.N('ShaderNodeTexCoord')
    V = tc.outputs['Generated']
    sky = horizon_nodes(b, V, look)
    x, y, z = b.sep(V)
    el = b.math('MULTIPLY', b.math('ARCSINE', b.math('MINIMUM', b.math('MAXIMUM', z, -1.0), 1.0)), 180 / math.pi)
    md = b.vec(G.L_MOON)
    cosang = b.vmath('DOT_PRODUCT', V, md)
    ang = b.math('MULTIPLY', b.math('ARCCOSINE', b.math('MINIMUM', cosang, 1.0)), 180 / math.pi)
    disc = b.smooth(ang, 0.62, 0.56)
    limb = b.smooth(ang, 0.62, 0.0, 0.78, 1.0)
    # round 3: the Udon rule (JSON moon.udon_rule): once colossus 2 has taken the disc (U7b - 0.5 .. + 1.5) the disc
    # fades out over 2 s and only the aureole stays
    moon = b.scale(b.rgb(tuple(F['MoonDisc'])), b.math('MULTIPLY', b.math('MULTIPLY', disc, limb), look.get('moon_disc', 1.0)))
    # round 2 (critique B6.3): a real aureole: ~L* 55 at 1 deg falling to the band by ~8 deg (#5A6A88 silver)
    halo_i = b.math('ADD', b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', ang, -look.get('aur_k', 1.1))), look.get('aur_a', 0.55)),
                    b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', ang, -0.32)), look.get('aur_b', 0.05)))
    halo = b.scale(b.rgb(tuple(RT.hexlin('#8FA3C8'))), b.math('MULTIPLY', halo_i, b.math('SUBTRACT', 1.0,
                   b.math('MULTIPLY', disc, look.get('moon_disc', 1.0)))))      # no hole where the faded disc was
    sky = b.rgbadd(b.rgbadd(sky, moon), halo)
    if look['stars'] > 0:
        for sc_, thr, gain in ((260.0, 0.94, 0.9), (520.0, 0.975, 0.5)):
            vor = b.N('ShaderNodeTexVoronoi')
            vor.inputs['Scale'].default_value = sc_
            b.L(V, vor.inputs['Vector'])
            core = b.math('POWER', b.smooth(vor.outputs['Distance'], 0.0, 0.06, 1.0, 0.0), 6.0)
            r_, g_, bb_ = b.sepc(vor.outputs['Color'])
            keep = b.math('POWER', b.smooth(r_, thr, 1.0), 2.0)
            st = b.math('MULTIPLY', b.math('MULTIPLY', core, keep), gain * look['stars'])
            st = b.math('MULTIPLY', st, b.smooth(el, 10, 32, 0.0, 1.0))     # not in the haze band
            sky = b.rgbadd(sky, b.rgbmul(b.gray(st), b.mix(g_, (0.85, 0.9, 1.0), (1.0, 0.97, 0.92))))
    bg = b.N('ShaderNodeBackground')
    b.L(sky, bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 1.0
    o = b.N('ShaderNodeOutputWorld')
    b.L(bg.outputs[0], o.inputs['Surface'])


# ============================================================================================ tentacles
_MESH = {}
_MAT = {}


def variant_mesh(key, lod, girth=1.0, form=None):
    """library mesh with the arm form v3 baked in (gate_layout: form_mult x (1 + ridges + ellipse)): every vertex
    moves along its normal by r_lib x (m - 1), r_lib = Col.B x R, t = Col.R, theta = 2 pi UVMap.x. A float
    attribute 'GR' = r_gate / R_lib is added for the pixel rim (Col stays the library's: Unity reads its B as the
    thinness for the tip inflation / transmission, which keeps its meaning)."""
    g = round(float(girth), 3)
    form = form or {}
    fk = tuple(round(float(form.get(n, 0.0)), 3) for n in ('turns', 'rph', 'eph'))
    k = (key, lod, g) + fk
    if k in _MESH:
        return _MESH[k]
    base = (key, lod)
    if base not in _MESH:
        ob = BL.variant_object(key, lod, name='V_%s_LOD%d' % (key, lod))
        _MESH[base] = ob.data
        bpy.data.objects.remove(ob, do_unlink=True)
    me = _MESH[base].copy()
    me.name = 'V_%s_LOD%d_g%.2f_%d' % (key, lod, g, len(_MESH))
    n = len(me.vertices)
    co = np.zeros(n * 3, np.float32)
    me.vertices.foreach_get('co', co)
    nr = np.zeros(n * 3, np.float32)
    me.vertex_normals.foreach_get('vector', nr)
    col = np.zeros(n * 4, np.float32)
    me.color_attributes['Col'].data.foreach_get('color', col)
    cc = col.reshape(-1, 4)
    # theta per vertex from the loops' UVMap.x
    nl = len(me.loops)
    lvi = np.zeros(nl, np.int32)
    me.loops.foreach_get('vertex_index', lvi)
    uvd = np.zeros(nl * 2, np.float32)
    me.uv_layers['UVMap'].data.foreach_get('uv', uvd)
    th = np.zeros(n, np.float32)
    th[lvi] = 2 * np.pi * uvd.reshape(-1, 2)[:, 0]
    R = BL.VARIANTS[key]['R']
    tt = np.clip(cc[:, 0], 0.0, 1.0)
    rl = cc[:, 2] * R
    m = G.form_mult(tt, g, key)
    if form:
        fade = 1.0 - G.ss((tt - 0.60) / 0.20)
        tw = 2 * np.pi * form['turns'] * tt
        rid = 0.02 * np.sin(3 * th + tw + form['rph'])      # round 3 (B5.6): ridges <= 2 % of r, <= 0.4 turn
        ell = 0.11 * np.cos(2 * (th - form['eph'] - 0.5 * tw))
        m = m * (1.0 + (rid + ell) * fade)
    co = co.reshape(-1, 3) + nr.reshape(-1, 3) * (rl * (m - 1.0))[:, None]
    me.vertices.foreach_set('co', co.ravel())
    at = me.attributes.new('GR', 'FLOAT', 'POINT')
    at.data.foreach_set('value', (cc[:, 2] * m).astype(np.float32))
    me.update()
    _MESH[k] = me
    return me


def tentacle_mat(key, kind, fog, t, pix_angle, dens=1.0, reveal=1.0, tiling=None):
    """Lanbai/TentacleSway preview + rim ladder + LanbaiFog with the instance's density scale and _Reveal (round 3:
    f = lerp(1, f, _Reveal) after the cap). Cap 0.92 x height falloff only for the far kinds."""
    dens = round(float(dens), 2)
    reveal = round(float(reveal), 2)
    tiling = tiling or (None, None)
    k = (key, kind, dens, reveal, tiling)
    if k in _MAT:
        return _MAT[k]
    core = G.tear_core_cf(t)
    if G.A4.is_custom(key):
        colossus = G.A4.is_colossus(key)
        occl = G.A4.occlusion_path(key, os.path.join(OUT, 'Textures', 'Occlusion'))
    else:
        colossus = key in 'GHK'
        occl = os.path.join(TEXT, 'T_Tentacle_%s_Occlusion.png' % G.TEX_KEY.get(key, key))
    m = BL.make_material('M_%s_%s_%.2f_%.2f' % (kind, key, dens, reveal), tex_dir=TEXT, pix_angle=pix_angle, fog=None,
                         rim_dir=tuple(G.L_MOON), rim=dict(moon=fog.k['rim_moon'], tear=fog.k['rim_tear']),
                         translucency=fog.k['tip_glow'], tear_pos=tuple(core), occl=occl, colossus=colossus,
                         tiling=tiling[0], detail_tiling=tiling[1])
    spec_scale(m, fog.k['arm_spec'] * fog.k.get('spec_' + kind, 1.0), SPEC_RANGE.get(kind, (250.0, 800.0)),
               fog.k.get('streak_keep', 0.8))
    add_pixel_rim(m, fog, t, pix_angle, kind)
    far = kind in ('colossus', 'bg', 'hero', 'surge')
    fog_wrap(m, fog, cap=far, dens=dens, cap_h=fog.k['cap_h_col'] if far else None, reveal=reveal)
    _MAT[k] = m
    return m


SPEC_RANGE = dict(pillar=(150.0, 450.0))      # tech M1: _ReflFarRange per kind (default 250-800 m)


def spec_scale(m, k, rng=(250.0, 800.0), streak_keep=0.0):
    """scale the BSDF's specular INCLUDING its grazing Fresnel (Unity: _ReflectionScale on the specular term): mix
    the principled BSDF with a copy that has no specular, by lerp(1, k, smoothstep(_ReflFarRange, d)). Round 3: the
    long mucus runs keep their specular (x lerp(1, streak_keep, wet mask), wet mask = smoothstep(0.80, 0.90,
    smoothness)): the far arms lose the satin sheen (vinyl) but keep 2-4 long wet streaks (critique B5.7)."""
    if abs(k - 1.0) < 1e-3:
        return
    nt = m.node_tree
    p = [n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED'][0]
    q = nt.nodes.new('ShaderNodeBsdfPrincipled')
    for inp in p.inputs:
        if inp.name not in q.inputs:
            continue
        qi = q.inputs[inp.name]
        if inp.links:
            nt.links.new(inp.links[0].from_socket, qi)
        elif hasattr(inp, 'default_value') and hasattr(qi, 'default_value'):
            try:
                qi.default_value = inp.default_value
            except Exception:
                pass
    q.inputs['Specular IOR Level'].default_value = 0.0
    mix = nt.nodes.new('ShaderNodeMixShader')
    b = NB(nt)
    camd = b.N('ShaderNodeCameraData')
    fac = b.smooth(camd.outputs['View Distance'], rng[0], rng[1], 0.0, float(np.clip(1.0 - k, 0.0, 1.0)))
    if streak_keep > 0:
        msn = [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image and 'MetallicSmoothness' in n.image.name]
        if msn:
            wet = b.smooth(msn[0].outputs['Alpha'], 0.80, 0.90)
            fac = b.math('MULTIPLY', fac, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', wet, float(streak_keep))))
    b.L(fac, mix.inputs[0])
    outs = list(p.outputs[0].links)
    nt.links.new(p.outputs[0], mix.inputs[1])
    nt.links.new(q.outputs[0], mix.inputs[2])
    for l in outs:
        nt.links.new(mix.outputs[0], l.to_socket)


def arm_kind(it):
    r = it.get('role')
    if r == 'pillar':
        return 'pillar'
    if r == 'engel':
        return 'hero'
    return {'colossus_bg': 'bg'}.get(it['layer'], it['layer'])     # 'surge' stays 'surge'


# rim ladder (critique B3): screen-width (px) and gain per kind; every rim x T_uncapped(d) x clamp((900/d)^1.2, .12, 1)
RIM_PX = dict(near=5.0, pillar=3.5, mid=2.0, colossus=1.0, bg=1.0, rear=2.5, hero=1.2, surge=1.0)
RIM_DENS = dict(near=1.0, pillar=1.0, mid=1.0, colossus=1.0, bg=1.0, rear=1.0, hero=1.0, surge=1.0)


def rim_ladder(b, kind, k):
    """T_uncapped(d) x clamp((900 / d)^1.2, 0.12, 1): the fog cap must not keep a far rim bright."""
    camd = b.N('ShaderNodeCameraData')
    d = b.math('MAXIMUM', camd.outputs['View Distance'], 1.0)
    T = b.math('EXPONENT', b.math('MULTIPLY', d, -k['fog'] * RIM_DENS.get(kind, 1.0)))
    lad = b.math('MINIMUM', b.math('MAXIMUM', b.math('POWER', b.math('DIVIDE', 900.0, d), 1.2), 0.12), 1.0)
    return b.math('MULTIPLY', T, lad)


def add_pixel_rim(mat, fog, t, pix_angle, kind):
    """the bible's continuous 1-3 px outline (far) / 3-8 px (near), round-2 version: only on LIGHT-FACING edges
    of a BACK-LIT arm (moon side: N.L_moon > 0 and the moon in front of the view; wound side: facing the wound and
    the wound in front), width by layer (RIM_PX), intensity x rim_ladder x (0.6 + 0.8 wet streaks) (+-40 % along
    the arm). The rim region is ndv < thr, thr = sqrt(2 N px_footprint / r) (r = GR x R_root x scale).
    The library material's own bible rims get the same ladder and back-lit factor (fix_material_rims)."""
    nt = mat.node_tree
    b = NB(nt)
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    src = out.inputs['Surface'].links[0].from_socket
    k = fog.k
    geo = b.N('ShaderNodeNewGeometry')
    camd = b.N('ShaderNodeCameraData')
    oi = b.N('ShaderNodeObjectInfo')
    Rr = b.sepc(oi.outputs['Color'])[0]
    gr = b.attr('GR').outputs['Fac']
    r = b.math('MULTIPLY', b.math('MAXIMUM', gr, 0.02), Rr)
    foot = b.math('MULTIPLY', camd.outputs['View Distance'], pix_angle)
    npx = RIM_PX.get(kind, 2.0) * k.get('rim_px_scale', 1.0)
    thr = b.math('MINIMUM', b.math('SQRT', b.math('DIVIDE', b.math('MULTIPLY', foot, 2.0 * npx), r)), 0.75)
    N = geo.outputs['Normal']
    Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)         # camera -> point
    ndv = b.math('ABSOLUTE', b.vmath('DOT_PRODUCT', N, geo.outputs['Incoming']))
    mask = b.math('POWER', b.math('SUBTRACT', 1.0, b.math('MINIMUM', b.math('DIVIDE', ndv, thr), 1.0)), 1.5)
    nlm = b.vmath('DOT_PRODUCT', N, b.vec(G.L_MOON))
    moonk = b.smooth(nlm, -0.05, 0.55)
    if kind != 'rear':      # shader _RimBackOnly 1; the rear-window material has 0 (tech M9: rims on front-lit arms)
        moonk = b.math('MULTIPLY', moonk, b.smooth(b.vmath('DOT_PRODUCT', Vd, b.vec(G.L_MOON)), -0.15, 0.45))
    core = G.tear_core_cf(t)
    tv = b.vmath('SUBTRACT', b.vec(core), geo.outputs['Position'])
    tdir = b.vmath('NORMALIZE', tv)
    facing = b.math('MULTIPLY', b.smooth(b.vmath('DOT_PRODUCT', N, tdir), 0.0, 0.6),
                    b.smooth(b.vmath('DOT_PRODUCT', Vd, tdir), -0.2, 0.4))
    prox = b.smooth(b.vmath('LENGTH', tv), 200.0, 1600.0, 1.0, 0.0)
    ms = load_img(os.path.join(TEXT, 'T_Tentacle_MetallicSmoothness.png'), 'Non-Color', 'STRAIGHT')
    wet = b.math('ADD', 0.6, b.math('MULTIPLY', b.smooth(b.tex(ms, b.uv('UVMap')).outputs['Alpha'], 0.55, 0.9), 0.8))
    lad = b.math('MULTIPLY', rim_ladder(b, kind, k), wet)
    gk = k.get('rim_gain_' + kind, 1.0)
    rm = b.scale(b.rgb(tuple(RT.hexlin('#9DB8FF'))), b.math('MULTIPLY', b.math('MULTIPLY', mask, moonk), k['rim_moon_px'] * gk))
    rt = b.scale(b.rgb(tuple(RT.hexlin('#A99DE1'))), b.math('MULTIPLY', b.math('MULTIPLY', mask, b.math('MULTIPLY', facing, prox)),
                                                         k['rim_tear_px'] * gk))
    em = b.emission(b.scale(b.rgbadd(rm, rt), lad))
    b.L(b.add(src, em), out.inputs['Surface'])
    fix_material_rims(mat, kind, k)


def fix_material_rims(mat, kind, k):
    """multiply the library preview's bible rims (emission nodes coloured #9DB8FF / #A99DE1) by the ladder and,
    for the moon rim, by 'the moon is in front' (no rim on a front-lit arm)."""
    nt = mat.node_tree
    b = NB(nt)
    moonc = np.array(BL.RIM['moon_color'])
    tearc = np.array(BL.RIM['tear_color'])
    for n in list(nt.nodes):
        if n.type != 'EMISSION' or not n.inputs['Strength'].links:
            continue
        c = np.array(n.inputs['Color'].default_value[:3])
        if np.allclose(c, moonc, atol=1e-4) or np.allclose(c, tearc, atol=1e-4):
            s_ = n.inputs['Strength'].links[0].from_socket
            f = rim_ladder(b, kind, k)
            if np.allclose(c, moonc, atol=1e-4) and kind == 'rear':
                pass                 # _RimBackOnly 0 (rear window)
            elif np.allclose(c, moonc, atol=1e-4):
                geo = b.N('ShaderNodeNewGeometry')
                Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
                f = b.math('MULTIPLY', f, b.smooth(b.vmath('DOT_PRODUCT', Vd, b.vec(G.L_MOON)), -0.15, 0.45))
            else:                    # v2.3: the wound rim only when the wound is in front of the view (backT)
                f = b.math('MULTIPLY', f, _tear_back(b, nt))
            b.L(b.math('MULTIPLY', s_, b.math('MULTIPLY', f, k.get('rim_gain_' + kind, 1.0))), n.inputs['Strength'])
    for n in list(nt.nodes):         # thin-tip transmission: only when the wound is behind the tip (shader: back^2)
        if n.type == 'BSDF_TRANSLUCENT' and n.inputs['Color'].links:
            src = n.inputs['Color'].links[0].from_socket
            bk = _tear_back(b, nt, sq=True)
            b.L(_scale_vec(b, src, bk), n.inputs['Color'])


def _tear_back(b, nt, sq=False):
    """smoothstep(-0.2, 0.4, dot(camera->point, point->tear)) (shader v2.3 backT); sq: saturate(dot)^2 (back^2)"""
    tp = [x for x in nt.nodes if x.label == 'tear_pos'][0]
    geo = b.N('ShaderNodeNewGeometry')
    Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
    to_t = b.vmath('NORMALIZE', b.vmath('SUBTRACT', tp.outputs[0], geo.outputs['Position']))
    d = b.vmath('DOT_PRODUCT', Vd, to_t)
    if sq:
        c = b.math('MAXIMUM', d, 0.0)
        return b.math('MULTIPLY', c, c)
    return b.smooth(d, -0.2, 0.4)


def _scale_vec(b, src, f):
    v = b.N('ShaderNodeVectorMath'); v.operation = 'SCALE'
    b.L(src, v.inputs[0]); b.L(f, v.inputs['Scale'])
    return v.outputs[0]


def place_tentacles(layout, t, fog, pix_angle, only=None):
    obs = []
    for it in layout:
        if only and it['layer'] not in only:
            continue
        rv = G.reveal_at(it, t) if fog.k.get('reveal', True) else 1.0
        if rv <= 0.0:
            continue                                   # _Reveal 0: the renderer is off
        root, R = G.pose_at(it, t)
        top = (root + it['scale'] * (G.cl_points(it['variant'], 40)[0] @ R.T))[:, 2].max()
        if top < -2.0:
            continue                                   # still under the cloud
        me = variant_mesh(it['variant'], it['lod'], it.get('girth', 1.0), it.get('form'))
        kind = arm_kind(it)
        Rm = BL.VARIANTS[it['variant']]['R'] * it['scale']
        til = G.A4.skin_tiling(Rm) if G.A4.is_custom(it['variant']) else (None, None)
        mat = tentacle_mat(it['variant'], kind, fog, t, pix_angle, G.fog_scale_at(it, t) * fog.k.get('fog_' + kind, 1.0),
                           reveal=rv, tiling=til)
        ob = bpy.data.objects.new(it['id'], me)
        bpy.context.scene.collection.objects.link(ob)
        M = np.eye(4)
        M[:3, :3] = R * it['scale']
        M[:3, 3] = root
        ob.matrix_world = Matrix(M.tolist())
        if not ob.data.materials:
            ob.data.materials.append(mat)
        ob.material_slots[0].link = 'OBJECT'
        ob.material_slots[0].material = mat
        ob.color = (Rm, 0, 0, 1)
        if not G.A4.is_custom(it['variant']) and (kind in ('pillar', 'hero', 'near') or it.get('role') == 'moon'):
            sm = ob.modifiers.new('Smooth', 'SUBSURF')          # library meshes: GateArms bakes these at level 1
            sm.levels = sm.render_levels = 1
        obs.append(ob)
    return obs


# ============================================================================================ tide
def tide_billboards(tide, t, cam_pos, fog, look):
    cells_atl = sorted({td['cell']['atlas'] for td in tide})
    verts, faces, uvs, mats, mist = [], [], [], [], []
    for td in tide:
        r = G.tide_root_at(td, t)
        c = td['cell']
        Hq = c['cell_height_in_lengths'] * td['size']
        Wq = Hq * 0.5
        d = np.array([r[0] - cam_pos[0], r[1] - cam_pos[1]])
        d /= np.linalg.norm(d)
        rt = np.array([d[1], -d[0], 0.0])                 # camera-right, horizontal
        mirror = r[0] > 0                                  # right of the tear: lean left, toward it
        u0, v0, u1, v1 = c['uv_rect']
        ru = c['root_u']
        offs = (-(1 - ru) * Wq, ru * Wq) if mirror else (-ru * Wq, (1 - ru) * Wq)
        us = (u1, u0) if mirror else (u0, u1)
        # round 2: the blade LEANS toward the wound in the billboard plane (lean deg)
        lean = math.radians(td.get('lean', 0.0)) * (-1.0 if mirror else 1.0)
        up_ = np.array([0, 0, 1.0]) * math.cos(lean) + rt * math.sin(lean)
        rt_ = rt * math.cos(lean) - np.array([0, 0, 1.0]) * math.sin(lean)
        k0 = len(verts)
        for (o, u), (hy, vv) in (((offs[0], us[0]), (0.0, v0)), ((offs[1], us[1]), (0.0, v0)),
                                 ((offs[1], us[1]), (Hq, v1)), ((offs[0], us[0]), (Hq, v1))):
            verts.append(r + rt_ * o + up_ * hy)
            uvs.append((u, vv))
            mist.append((td.get('mist_h', 12.0), td.get('sink', 0.0)))
        faces.append((k0, k0 + 1, k0 + 2, k0 + 3))
        mats.append(cells_atl.index(c['atlas']))
    V = np.array(verts)
    ob = mesh_from_numpy('Tide', V, np.array(faces), uvs=[('UVMap', np.array(uvs)), ('TideMist', np.array(mist))],
                         smooth=False)
    for a in cells_atl:
        m, b = new_mat('M_Tide_' + a)
        pth = os.path.join(TEXT, a + '.png')
        if not os.path.exists(pth):                       # run 6: the v3 atlas lives in gate/Textures
            pth = os.path.join(HERE, 'Textures', a + '.png')
        img = load_img(pth, 'sRGB', 'STRAIGHT')
        tx = b.tex(img, b.uv('UVMap'))
        # round 3: the tide is a wave; it recedes into the haze U8 - 5 .. U8 + 1 (material _Reveal; from U8 its near
        # crest band, 4.5-6 km away and less fogged, read as weeds at the wound's foot)
        rv_t = float(G.tide_reveal(t))
        f, col = fog.nodes(b, cap=True, cap_v=look['tide_cap'], cap_h=0.0)
        vv = b.sep(b.uv('UVMap'))[1]
        # round 3 (awe B1 / tech M3): base 0.68 -> tips 0.58 (dL* -4..-6 against the band); the painted moon rim is
        # scaled by the far-rim falloff (x 0.3 at 6-13 km), so no crest is ever brighter than the sky
        f = b.math('MINIMUM', f, b.mixf(b.smooth(b.sep(b.N('ShaderNodeNewGeometry').outputs['Position'])[2], 0.0, 400.0),
                                        look.get('tide_fog_base', 0.58), look.get('tide_fog_tip', 0.48)))
        if rv_t < 0.999:      # the reveal comes after the base/tip cap (shader v2.1: fo = 1 - (1 - fo) x _Reveal)
            f = b.math('SUBTRACT', 1.0, b.math('MULTIPLY', b.math('SUBTRACT', 1.0, f), rv_t))
        surf = b.emission(b.mix(f, b.scale(tx.outputs['Color'], look.get('tide_rim', 0.3)), col))
        geo = b.N('ShaderNodeNewGeometry')
        # run 6: the base dissolves over the blade's own mist height (60-180 m, UV 'TideMist'), not on one line
        mh = b.sep(b.uv('TideMist'))[0]
        zc = b.math('POWER', b.math('MINIMUM', 1.0, b.math('MAXIMUM', 0.0, b.math('DIVIDE', b.math('ADD', b.sep(geo.outputs['Position'])[2], 8.0), mh))), 1.6)
        b.out(b.mixs(b.math('MULTIPLY', tx.outputs['Alpha'], zc), b.transparent(), surf))
        ob.data.materials.append(m)
    ob.data.polygons.foreach_set('material_index', np.array(mats, np.int32))
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


# ============================================================================================ cloud floor
def cloud_floor(t, cam_pos, fog, look, yaw=0.0, span=100.0, full=False, z_off=0.0):
    """Stand-in cloud-sea top: a polar heightfield around the camera (billowed domes, heaped round the tear's foot)
    shaded PER PIXEL in fill space: moon diffuse (wrap) + forward-scattered silver rims toward the low moon +
    tear light + the kit's violet glow card under the tear (#696F8D fill, r 1.1 km x S) + sky ambient, all in
    LanbaiFog. Detail billows come from procedural bump at 7-30 m."""
    t0 = time.time()
    S = G.tear_H(t) / G.TD.H
    n_r, n_th = 900, (2600 if full else 1500)
    r = 25.0 * (26000.0 / 25.0) ** np.linspace(0, 1, n_r)
    if full:
        th = np.radians(np.linspace(-180, 180, n_th))
    else:
        th = np.radians(np.linspace(yaw - span, yaw + span, n_th))
    R_, TH = np.meshgrid(r, th, indexing='ij')
    X, Y = cam_pos[0] + R_ * np.sin(TH), cam_pos[1] + R_ * np.cos(TH)
    fx, fy = 0.0, 0.0

    def heap(Xa, Ya):
        rr = np.hypot(Xa - fx, (Ya - fy) * 0.8)
        return (38.0 * RT.worley_domes(Xa, Ya, 150.0, 8) + 14.0 * RT.worley_domes(Xa, Ya, 55.0, 9)) * \
            np.exp(-(rr / (520.0 * max(S, 0.6))) ** 2)

    def zf(Xa, Ya):
        # cumulus-top sea: cauliflower = rounded domes whose height is a large share of their width at the
        # small scales (puffs on puffs), gentle at the large scales; + slow rolls
        A = look['dome_a'] / 40.0
        h = A * (22.0 * RT.worley_domes(Xa, Ya, 700.0, 11) + 28.0 * RT.worley_domes(Xa, Ya, 210.0, 12)
                 + 18.0 * RT.worley_domes(Xa, Ya, 80.0, 13) + 6.0 * RT.worley_domes(Xa, Ya, 34.0, 14)) \
            + 10.0 * RT.rollnoise(Xa, Ya, 6)
        return h - 45.0 * A + heap(Xa, Ya)
    Z = zf(X, Y) + z_off
    top = np.clip((Z + 45.0 * look['dome_a'] / 40.0) / (70.0 * look['dome_a'] / 40.0), 0, 1)
    P = np.stack([X, Y, Z], -1).reshape(-1, 3)
    faces = K._grid_faces(n_r, n_th, flip=True)
    col = np.stack([top, top, top, np.ones_like(top)], -1).reshape(-1, 4)
    ob = mesh_from_numpy('CloudFloor', P, faces, point_colors=[('Top', col)], smooth=True)
    k = look
    m, b = new_mat('M_CloudFloor')
    geo = b.N('ShaderNodeNewGeometry')
    Pw = geo.outputs['Position']
    Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
    topv = b.sepc(b.attr('Top').outputs['Color'])[0]
    # detail billows (cauliflower): rounded Voronoi cells at 2 scales in the bump; noise only for cavities
    nz1 = b.N('ShaderNodeTexNoise'); nz1.inputs['Scale'].default_value = 1.0 / 90.0
    nz1.inputs['Detail'].default_value = 3.0; nz1.inputs['Roughness'].default_value = 0.5
    b.L(Pw, nz1.inputs['Vector'])
    hsum = None
    for sc_, amp, rnd in ((1.0 / 60.0, 1.0, 0.0), (1.0 / 21.0, 0.45, 0.3), (1.0 / 7.5, 0.18, 0.3)):
        vo = b.N('ShaderNodeTexVoronoi'); vo.feature = 'SMOOTH_F1'; vo.inputs['Scale'].default_value = sc_
        try:
            vo.inputs['Smoothness'].default_value = 1.0
        except KeyError:
            pass
        b.L(Pw, vo.inputs['Vector'])
        dome = b.math('SQRT', b.math('MAXIMUM', b.math('SUBTRACT', 1.0, b.math('POWER', vo.outputs['Distance'], 2.0)), 0.0))
        hh = b.math('MULTIPLY', dome, amp)
        hsum = hh if hsum is None else b.math('ADD', hsum, hh)
    hsum = b.math('ADD', hsum, b.math('MULTIPLY', nz1.outputs['Fac'], 0.6))
    bump = b.N('ShaderNodeBump'); bump.inputs['Strength'].default_value = 0.9 * k['cloud_detail']
    bump.inputs['Distance'].default_value = 30.0
    b.L(hsum, bump.inputs['Height'])
    N = bump.outputs['Normal']
    ndv = b.math('MAXIMUM', b.math('MULTIPLY', b.vmath('DOT_PRODUCT', N, Vd), -1.0), 0.0)
    edge = b.math('POWER', b.math('SUBTRACT', 1.0, ndv), 3.0)
    cav = b.math('ADD', 0.45, b.math('MULTIPLY', b.smooth(nz1.outputs['Fac'], 0.3, 0.7), 0.55))
    alb = k['cloud_alb']
    crest = b.smooth(topv, 0.35, 1.0)
    # LIT by the moon lamp (real soft shadows: with the moon 8 deg up, the billows shadow each other and only the
    # crests catch it) + a translucent term: the backlit crest edges glow silver (light through thin cloud)
    albc = b.scale(b.rgb((alb, alb, alb)), b.math('MULTIPLY', cav, k['cloud_moon']))
    dif = b.N('ShaderNodeBsdfDiffuse'); b.L(albc, dif.inputs['Color']); b.L(N, dif.inputs['Normal'])
    tr = b.N('ShaderNodeBsdfTranslucent')
    b.L(b.scale(b.rgb((alb, alb, alb)), b.math('MULTIPLY', b.math('ADD', 0.15, b.math('MULTIPLY', crest, 0.85)), k['cloud_rim'] * 0.9)),
        tr.inputs['Color'])
    b.L(N, tr.inputs['Normal'])
    lit = b.add(dif.outputs[0], tr.outputs[0])
    occ = b.math('MULTIPLY', b.math('ADD', 0.25, b.math('MULTIPLY', topv, 0.75)), cav)
    # tear: light from the core (point-like, 1/(1 + (d/1.2 km)^2)) + the kit's cloud glow card under the tear
    core = G.tear_core_cf(t)
    Lt = b.vmath('SUBTRACT', b.vec(core), Pw)
    dt = b.vmath('LENGTH', Lt)
    Ltn = b.vmath('NORMALIZE', Lt)
    ndt = b.vmath('DOT_PRODUCT', N, Ltn)
    fall = b.math('DIVIDE', 1.0, b.math('ADD', 1.0, b.math('POWER', b.math('DIVIDE', dt, 1200.0), 2.0)))
    dif_t = b.math('MULTIPLY', b.math('MULTIPLY', b.math('MAXIMUM', b.math('DIVIDE', b.math('ADD', ndt, 0.2), 1.2), 0.0), alb * E_TEAR), fall)
    mut = b.vmath('DOT_PRODUCT', Vd, Ltn)
    g2 = 0.5
    hgt_ = b.math('DIVIDE', (1 - g2 * g2) / 12.566, b.math('POWER', b.math('SUBTRACT', 1 + g2 * g2, b.math('MULTIPLY', mut, 2 * g2)), 1.5))
    rim_t = b.math('MULTIPLY', b.math('MULTIPLY', hgt_, edge), b.math('MULTIPLY', crest, fall))
    tear = b.scale(b.rgb(tuple(COL_TEAR)), b.math('MULTIPLY', b.math('ADD', b.math('MULTIPLY', dif_t, occ),
                                                                         b.math('MULTIPLY', rim_t, 1.4)), k['cloud_tear']))
    px, py, pz = b.sep(Pw)
    rg = b.math('DIVIDE', b.math('SQRT', b.math('ADD', b.math('POWER', px, 2.0),
                                                 b.math('POWER', b.math('SUBTRACT', py, 150.0 * S), 2.0))), K.CLOUD_GLOW_R * S)
    card = b.math('ADD', b.math('DIVIDE', 0.62, b.math('POWER', b.math('ADD', 1.0, b.math('POWER', b.math('DIVIDE', rg, 0.16), 2.0)), 1.15)),
                  b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', b.math('POWER', b.math('DIVIDE', rg, 0.55), 2.0), -1.0)), 0.38))
    card = b.math('MULTIPLY', b.math('MAXIMUM', b.math('SUBTRACT', card, 0.02), 0.0), b.smooth(rg, 1.0, 0.72))
    glow = b.scale(b.rgb(tuple(F['CloudGlow'])), b.math('MULTIPLY', b.math('MULTIPLY', card, b.math('ADD', 0.35, b.math('MULTIPLY', topv, 0.65))),
                                                        0.9 * k['cloud_glow']))
    amb = b.scale(b.rgb(tuple(F['Void'] * 1.2 + F['HazeFar'] * 0.35)), b.math('MULTIPLY', occ, alb * k['cloud_amb']))
    emis = b.emission(b.rgbadd(tear, b.rgbadd(glow, amb)))
    surf = b.add(lit, emis)
    f, fcol = fog.nodes(b, cap=False, extra=False, dens=1.0)
    # mist lying in the hollows of the cloud sea (softens the billows; the haze colour of that direction)
    mist = b.math('MULTIPLY', b.math('SUBTRACT', 1.0, b.smooth(topv, 0.05, 0.75)), k['cloud_mist'])
    f = b.math('ADD', f, b.math('MULTIPLY', b.math('SUBTRACT', 1.0, f), mist))
    b.out(b.mixs(f, surf, b.emission(fcol)))
    ob.data.materials.append(m)
    ob.visible_shadow = True           # the billows shadow each other (moon lamp)
    ob.visible_diffuse = False
    ob.visible_glossy = False
    print('cloud floor %.1fs (%d verts)' % (time.time() - t0, len(P)))
    return ob


# ============================================================================================ cloud cards
def cloud_card(name, card, loc, width, face_to, brightness, mirror, fog, look, tear_dir=None):
    meta = json.load(open(os.path.join(CLOUDS, 'clouds_meta.json')))
    img = load_img(os.path.join(CLOUDS, card + '.png'), 'sRGB', 'STRAIGHT')
    w, h = img.size
    height = width * h / w
    base_v = meta.get(card, {}).get('cloud_base_v', 0.15)
    d = np.array(face_to) - np.array(loc)
    d[2] = 0
    d /= np.linalg.norm(d)
    right = np.array([d[1], -d[0], 0.0]) * (-1 if mirror else 1)
    up = np.array([0, 0, 1.0])
    o = np.array(loc) + up * (-base_v * height)
    V = np.array([o - right * width / 2, o + right * width / 2, o + right * width / 2 + up * height, o - right * width / 2 + up * height])
    ob = mesh_from_numpy(name, V, np.array([(0, 1, 2, 3)]), uvs=[('UVMap', np.array([(0, 0), (1, 0), (1, 1), (0, 1)]))], smooth=False)
    m, b = new_mat('M_' + name)
    tx = b.tex(img, b.uv('UVMap'))
    col = b.scale(tx.outputs['Color'], brightness * look['card_gain'])
    if tear_dir is not None:          # violet spill from the tear on the side facing it (per pixel)
        geo = b.N('ShaderNodeNewGeometry')
        Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
        c = b.math('POWER', b.math('MAXIMUM', b.vmath('DOT_PRODUCT', Vd, b.vec(tear_dir)), 0.0), 20.0)
        col = b.rgbmul(col, b.mix(c, (0.95, 1.0, 1.08), (1.05, 1.0, 1.35)))
    f, fcol = fog.nodes(b, cap=False, extra=False, dens=look['card_fog'])
    surf = b.emission(b.mix(f, col, fcol))
    b.out(b.mixs(tx.outputs['Alpha'], b.transparent(), surf))
    ob.data.materials.append(m)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    return ob


def cloud_rows(t, cam_pos, fog, look, yaw=0.0, span=60.0, seed=21,
               rows=((230.0, 4), (300.0, 4), (390.0, 4), (510.0, 5), (660.0, 5), (860.0, 5), (1120.0, 6), (1460.0, 6),
                     (1900.0, 6), (2500.0, 6), (3300.0, 6), (4400.0, 6), (6000.0, 6), (8200.0, 6))):
    """the cloud sea as receding rows of the delivered CloudSea strips (volumetric renders), tops at the cloud-top
    height, feathered ends, per-pixel violet spill toward the tear and a moon lane, in LanbaiFog (stand-in for the
    Unity cloud-sea cards)."""
    rng = np.random.default_rng(seed)
    meta = json.load(open(os.path.join(CLOUDS, 'clouds_meta.json')))
    core = G.tear_core_cf(t)
    tdir = G.unit(core - cam_pos)
    mats = {}
    for card in ('CloudSea_1_moon', 'CloudSea_2_moon'):
        img = load_img(os.path.join(CLOUDS, card + '.png'), 'sRGB', 'STRAIGHT')
        m, b = new_mat('M_Row_' + card)
        uvn = b.uv('UVMap')
        tx = b.tex(img, uvn)
        col = b.scale(tx.outputs['Color'], look['row_gain'])
        geo = b.N('ShaderNodeNewGeometry')
        Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
        ct = b.math('POWER', b.math('MAXIMUM', b.vmath('DOT_PRODUCT', Vd, b.vec(tdir)), 0.0), 60.0)
        cm = b.math('POWER', b.math('MAXIMUM', b.vmath('DOT_PRODUCT', Vd, b.vec(G.L_MOON)), 0.0), 40.0)
        tint = b.mix(ct, tuple(look['row_tint']), tuple(F['CloudGlow'] / F['CloudGlow'].max() * look['row_violet']))
        col = b.rgbmul(col, tint)
        col = b.rgbadd(col, b.scale(b.rgbmul(tx.outputs['Color'], b.rgb(tuple(COL_MOON))), b.math('MULTIPLY', cm, look['row_moon'])))
        f, fcol = fog.nodes(b, cap=False, extra=False, dens=1.0)
        surf = b.emission(b.mix(f, col, fcol))
        u = b.sep(uvn)[0]
        fe = b.math('MULTIPLY', b.smooth(u, 0.03, 0.22), b.smooth(u, 0.97, 0.78))
        b.out(b.mixs(b.math('MULTIPLY', tx.outputs['Alpha'], fe), b.transparent(), surf))
        mats[card] = (m, img.size, meta[card]['cloud_base_v'], meta[card]['opaque_bbox_uv'][3])
    V, Fc, UV, MI = [], [], [], []
    cards = list(mats)
    for ri, (d, n) in enumerate(rows):
        w = 2 * d * math.tan(math.radians(span)) / n * 1.8
        for j in range(n):
            az = yaw - span + (j + 0.5) * 2 * span / n + rng.uniform(-4, 4)
            card = cards[(ri + j) % 2]
            m, (iw, ih), base_v, top_v = mats[card]
            hgt = w * ih / iw
            dd = d * rng.uniform(0.96, 1.04)
            a = math.radians(az)
            c = np.array([cam_pos[0] + dd * math.sin(a), cam_pos[1] + dd * math.cos(a), 0.0])
            dv = G.unit(np.array([c[0] - cam_pos[0], c[1] - cam_pos[1], 0.0]))
            right = np.array([dv[1], -dv[0], 0.0])
            if (ri + j) % 3 == 0:
                right = -right
            ztop = rng.uniform(-6.0, 6.0)
            z0 = ztop - (top_v - 0.0) * hgt * 0.92
            o = c + np.array([0, 0, z0])
            k0 = len(V)
            V += [o - right * w / 2, o + right * w / 2, o + right * w / 2 + np.array([0, 0, hgt]), o - right * w / 2 + np.array([0, 0, hgt])]
            UV += [(0, 0), (1, 0), (1, 1), (0, 1)]
            Fc.append((k0, k0 + 1, k0 + 2, k0 + 3))
            MI.append(cards.index(card))
    ob = mesh_from_numpy('CloudRows', np.array(V), np.array(Fc), uvs=[('UVMap', np.array(UV, float))], smooth=False)
    for c in cards:
        ob.data.materials.append(mats[c][0])
    ob.data.polygons.foreach_set('material_index', np.array(MI, np.int32))
    ob.visible_shadow = False
    ob.visible_diffuse = False
    return ob


def cloud_puffs(t, cam_pos, fog, look, yaw=0.0, span=60.0, seed=5, n=700, r0=150.0, r1=9000.0):
    """cumulus-top sea from the delivered cloud cards: camera-facing puffs sunk into the floor, sized with distance,
    darkened (back-lit night) and tinted per pixel (violet toward the tear, silver toward the moon), LanbaiFog."""
    rng = np.random.default_rng(seed)
    meta = json.load(open(os.path.join(CLOUDS, 'clouds_meta.json')))
    core = G.tear_core_cf(t)
    tdir = G.unit(core - cam_pos)
    names = ['Cloud_Cumulus_moon', 'Cloud_Puff_moon', 'Cloud_Strato_moon', 'Cloud_Bank_moon', 'Cloud_Congestus_moon']
    mats = {}
    for nm in names:
        img = load_img(os.path.join(CLOUDS, nm + '.png'), 'sRGB', 'STRAIGHT')
        m, b = new_mat('M_Puff_' + nm)
        uvn = b.uv('UVMap')
        tx = b.tex(img, uvn)
        col = b.scale(tx.outputs['Color'], look['puff_gain'])
        geo = b.N('ShaderNodeNewGeometry')
        Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
        ct = b.math('POWER', b.math('MAXIMUM', b.vmath('DOT_PRODUCT', Vd, b.vec(tdir)), 0.0), 40.0)
        cm = b.math('POWER', b.math('MAXIMUM', b.vmath('DOT_PRODUCT', Vd, b.vec(G.L_MOON)), 0.0), 30.0)
        tint = b.mix(ct, tuple(look['row_tint']), tuple(F['CloudGlow'] / F['CloudGlow'].max() * look['row_violet']))
        col = b.rgbmul(col, tint)
        col = b.rgbadd(col, b.scale(b.rgbmul(tx.outputs['Color'], b.rgb(tuple(COL_MOON))), b.math('MULTIPLY', cm, look['row_moon'])))
        f, fcol = fog.nodes(b, cap=False, extra=False, dens=1.0)
        surf = b.emission(b.mix(f, col, fcol))
        b.out(b.mixs(tx.outputs['Alpha'], b.transparent(), surf))
        mats[nm] = (m, img.size, meta[nm]['cloud_base_v'])
    V, Fc, UV, MI = [], [], [], []
    # uniform in screen: r log-distributed, azimuth uniform in the view
    for i in range(n):
        r = r0 * (r1 / r0) ** (rng.random() ** 1.15)
        az = yaw + rng.uniform(-span, span)
        if r < 1200:
            nm = names[rng.choice([0, 1, 0, 1, 4])]
        elif r < 4000:
            nm = names[rng.choice([0, 2, 3, 0])]
        else:
            nm = names[rng.choice([2, 3])]
        m, (iw, ih), base_v = mats[nm]
        w = float(np.clip(r * rng.uniform(*look['puff_w']), 20.0, 2500.0))
        hgt = w * ih / iw
        a = math.radians(az)
        c = np.array([cam_pos[0] + r * math.sin(a), cam_pos[1] + r * math.cos(a), 0.0])
        dv = G.unit(np.array([c[0] - cam_pos[0], c[1] - cam_pos[1], 0.0]))
        right = np.array([dv[1], -dv[0], 0.0]) * (1 if rng.random() < 0.5 else -1)
        # only the top of each puff breaks the cloud-sea surface
        vis = rng.uniform(*look['puff_vis']) * (1.6 if nm in names[2:4] else 1.0)
        z0 = -(1.0 - vis) * hgt * 0.72 - base_v * hgt
        o = c + np.array([0, 0, z0])
        k0 = len(V)
        V += [o - right * w / 2, o + right * w / 2, o + right * w / 2 + np.array([0, 0, hgt]), o - right * w / 2 + np.array([0, 0, hgt])]
        UV += [(0, 0), (1, 0), (1, 1), (0, 1)]
        Fc.append((k0, k0 + 1, k0 + 2, k0 + 3))
        MI.append(names.index(nm))
    # far to near does not matter for Cycles; one mesh, 5 materials
    ob = mesh_from_numpy('CloudPuffs', np.array(V), np.array(Fc), uvs=[('UVMap', np.array(UV, float))], smooth=False)
    for nm in names:
        ob.data.materials.append(mats[nm][0])
    ob.data.polygons.foreach_set('material_index', np.array(MI, np.int32))
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


def cloud_top_height(X, Y, look, S):
    """the cloud-sea top (m above the nominal top z = 0): rolls + domes, heaped round the tear's foot."""
    A = look['dome_a']
    h = (A * RT.worley_domes(X, Y, 640.0, 11) + 0.55 * A * RT.worley_domes(X, Y, 210.0, 12)
         + 0.25 * A * RT.worley_domes(X, Y, 70.0, 13) + 12.0 * RT.rollnoise(X, Y, 6)) - 0.9 * A
    rr = np.hypot(X, Y * 0.8)
    h += (30.0 * RT.worley_domes(X, Y, 150.0, 8) + 10.0 * RT.worley_domes(X, Y, 55.0, 9)) * np.exp(-(rr / (520.0 * max(S, 0.6))) ** 2)
    return h


def cloud_shells(t, cam_pos, fog, look, yaw=0.0, span=60.0, full=False):
    """Stand-in cloud sea with a SOFT top: n transparent shells between top - 22 m and top + 12 m (fur-style
    shell texturing) whose coverage is a 3-D density = top - z + billow noise, over an opaque base. Emission in
    fill space: moon (wrap, dimming with depth into the cloud) + silver where the fuzzy edge is back-lit by the
    low moon + tear light + the kit's cloud glow card (#696F8D, r 1.1 km x S) + sky ambient; LanbaiFog."""
    t0 = time.time()
    S = G.tear_H(t) / G.TD.H
    k = look
    n_sh = int(k['shells'])
    lo, hi = -22.0, 12.0
    n_r, n_th = 420, (1500 if full else 760)
    r = 20.0 * (26000.0 / 20.0) ** np.linspace(0, 1, n_r)
    th = np.radians(np.linspace(-180, 180, n_th) if full else np.linspace(yaw - span, yaw + span, n_th))
    R_, TH = np.meshgrid(r, th, indexing='ij')
    X, Y = cam_pos[0] + R_ * np.sin(TH), cam_pos[1] + R_ * np.cos(TH)
    Top = cloud_top_height(X, Y, look, S)
    e = 1.0 + R_ * 0.004
    dzdx = (cloud_top_height(X + e, Y, look, S) - cloud_top_height(X - e, Y, look, S)) / (2 * e)
    dzdy = (cloud_top_height(X, Y + e, look, S) - cloud_top_height(X, Y - e, look, S)) / (2 * e)
    Nn = np.stack([-dzdx, -dzdy, np.ones_like(Top)], -1)
    Nn /= np.linalg.norm(Nn, axis=-1, keepdims=True)
    # shells collapse onto the top beyond ~5 km (only the base is needed there)
    wr = 1.0 - G.ss((R_ - 4000.0) / 2500.0)
    faces = K._grid_faces(n_r, n_th, flip=True)
    CS = np.stack([Top, np.zeros_like(Top), Nn[..., 0], Nn[..., 1]], -1)
    m, b = new_mat('M_CloudShell')
    geo = b.N('ShaderNodeNewGeometry')
    Pw = geo.outputs['Position']
    Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
    cs = b.attr('CS')
    topz, layer, nx, ny = (*b.sepc(cs.outputs['Color']), cs.outputs['Alpha'])
    nxy = b.N('ShaderNodeCombineXYZ'); b.L(nx, nxy.inputs[0]); b.L(ny, nxy.inputs[1])
    nz_ = b.math('SQRT', b.math('MAXIMUM', b.math('SUBTRACT', 1.0, b.math('ADD', b.math('POWER', nx, 2.0), b.math('POWER', ny, 2.0))), 0.0))
    b.L(nz_, nxy.inputs[2])
    Ntop = nxy.outputs[0]
    px, py, pz = b.sep(Pw)
    # billow density
    n1 = b.N('ShaderNodeTexNoise'); n1.inputs['Scale'].default_value = 1.0 / 34.0; n1.inputs['Detail'].default_value = 3.0
    b.L(Pw, n1.inputs['Vector'])
    n2 = b.N('ShaderNodeTexNoise'); n2.inputs['Scale'].default_value = 1.0 / 9.0; n2.inputs['Detail'].default_value = 2.0
    b.L(Pw, n2.inputs['Vector'])
    vo = b.N('ShaderNodeTexVoronoi'); vo.feature = 'SMOOTH_F1'; vo.inputs['Scale'].default_value = 1.0 / 22.0
    b.L(Pw, vo.inputs['Vector'])
    cauli = b.math('SQRT', b.math('MAXIMUM', b.math('SUBTRACT', 1.0, b.math('POWER', vo.outputs['Distance'], 2.0)), 0.0))
    D = b.math('SUBTRACT', topz, pz)
    D = b.math('ADD', D, b.math('MULTIPLY', b.math('SUBTRACT', n1.outputs['Fac'], 0.5), 30.0 * k['shell_noise']))
    D = b.math('ADD', D, b.math('MULTIPLY', b.math('SUBTRACT', n2.outputs['Fac'], 0.5), 10.0 * k['shell_noise']))
    D = b.math('ADD', D, b.math('MULTIPLY', b.math('SUBTRACT', cauli, 0.55), 14.0 * k['shell_noise']))
    alpha = b.smooth(D, -2.5, 2.5)
    alpha = b.math('MAXIMUM', alpha, b.math('LESS_THAN', layer, 0.01))            # the lowest shell is the base
    depth = b.math('MAXIMUM', D, 0.0)
    ext = b.math('EXPONENT', b.math('DIVIDE', depth, -10.0))                        # light reaching into the cloud
    alb = k['cloud_alb']
    ndl = b.vmath('DOT_PRODUCT', Ntop, b.vec(G.L_MOON))
    wrapm = b.math('MAXIMUM', b.math('DIVIDE', b.math('ADD', ndl, 0.35), 1.35), 0.0)
    mu = b.vmath('DOT_PRODUCT', Vd, b.vec(G.L_MOON))
    g = 0.8
    hg = b.math('DIVIDE', (1 - g * g) / 12.566, b.math('POWER', b.math('SUBTRACT', 1 + g * g, b.math('MULTIPLY', mu, 2 * g)), 1.5))
    edgez = b.math('MULTIPLY', b.smooth(D, -2.5, 0.5), b.smooth(D, 6.0, 1.0))          # the fuzzy rim
    moon = b.math('MULTIPLY', b.math('MULTIPLY', wrapm, ext), alb * E_MOON * 0.55 * k['cloud_moon'])
    silver = b.math('MULTIPLY', b.math('MULTIPLY', hg, edgez), 1.3 * k['cloud_rim'] * E_MOON)
    mooncol = b.scale(b.rgb(tuple(COL_MOON)), b.math('ADD', moon, silver))
    core = G.tear_core_cf(t)
    Lt = b.vmath('SUBTRACT', b.vec(core), Pw)
    dt = b.vmath('LENGTH', Lt)
    Ltn = b.vmath('NORMALIZE', Lt)
    ndt = b.vmath('DOT_PRODUCT', Ntop, Ltn)
    fall = b.math('DIVIDE', 1.0, b.math('ADD', 1.0, b.math('POWER', b.math('DIVIDE', dt, 1100.0), 2.0)))
    mut = b.vmath('DOT_PRODUCT', Vd, Ltn)
    g2 = 0.55
    hgt_ = b.math('DIVIDE', (1 - g2 * g2) / 12.566, b.math('POWER', b.math('SUBTRACT', 1 + g2 * g2, b.math('MULTIPLY', mut, 2 * g2)), 1.5))
    tearv = b.math('MULTIPLY', fall, b.math('ADD', b.math('MULTIPLY', b.math('MULTIPLY', b.math('MAXIMUM', b.math('DIVIDE', b.math('ADD', ndt, 0.3), 1.3), 0.0), ext), alb * E_TEAR * 0.6),
                                             b.math('MULTIPLY', b.math('MULTIPLY', hgt_, edgez), 1.2 * E_TEAR)))
    tearcol = b.scale(b.rgb(tuple(COL_TEAR)), b.math('MULTIPLY', tearv, k['cloud_tear']))
    rg = b.math('DIVIDE', b.math('SQRT', b.math('ADD', b.math('POWER', px, 2.0), b.math('POWER', b.math('SUBTRACT', py, 150.0 * S), 2.0))), K.CLOUD_GLOW_R * S)
    card = b.math('ADD', b.math('DIVIDE', 0.62, b.math('POWER', b.math('ADD', 1.0, b.math('POWER', b.math('DIVIDE', rg, 0.16), 2.0)), 1.15)),
                  b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', b.math('POWER', b.math('DIVIDE', rg, 0.55), 2.0), -1.0)), 0.38))
    card = b.math('MULTIPLY', b.math('MAXIMUM', b.math('SUBTRACT', card, 0.02), 0.0), b.smooth(rg, 1.0, 0.72))
    glow = b.scale(b.rgb(tuple(F['CloudGlow'])), b.math('MULTIPLY', b.math('MULTIPLY', card, b.math('ADD', 0.3, b.math('MULTIPLY', ext, 0.7))), 0.9 * k['cloud_glow']))
    amb = b.scale(b.rgb(tuple(F['Void'] * 1.5 + F['HazeFar'] * 0.45)), b.math('MULTIPLY', b.math('ADD', 0.25, b.math('MULTIPLY', ext, 0.75)), alb * k['cloud_amb']))
    colr = b.rgbadd(b.rgbadd(mooncol, tearcol), b.rgbadd(glow, amb))
    f, fcol = fog.nodes(b, cap=False, extra=False, dens=1.0)
    surf = b.emission(b.mix(f, colr, fcol))
    b.out(b.mixs(alpha, b.transparent(), surf))
    obs = []
    for i in range(n_sh):
        fr = i / (n_sh - 1)
        z = Top + (lo + (hi - lo) * fr) * wr
        P = np.stack([X, Y, z], -1).reshape(-1, 3)
        CS[..., 1] = fr
        ob = mesh_from_numpy('CloudShell_%02d' % i, P, faces, point_colors=[('CS', CS.reshape(-1, 4).copy())], smooth=True)
        ob.data.materials.append(m)
        ob.visible_shadow = False
        ob.visible_diffuse = False
        ob.visible_glossy = False
        obs.append(ob)
    print('cloud shells %.1fs (%d x %d verts)' % (time.time() - t0, n_sh, X.size))
    return obs


# ============================================================================================ mist strata + far clouds
def mist_card(name, spec, cam_pos, fog, look, kind='mist'):
    """a cloud-kit card as a camera-facing (yaw only) alpha plane. kind 'mist': a luminous veil = LanbaiFog colour of
    its direction x (0.85 + 0.6 x card luminance), alpha x opacity (the haze lying between depth layers);
    kind 'far': the card's own moonlit colour in LanbaiFog (towering cumulus on the horizon)."""
    meta = json.load(open(os.path.join(CLOUDS, 'clouds_meta.json')))
    card = spec['card']
    img = load_img(os.path.join(CLOUDS, card + '.png'), 'sRGB', 'STRAIGHT')
    iw, ih = img.size
    w = spec['width']
    h = w * ih / iw * spec.get('sag_y', 1.0)
    base_v = meta.get(card, {}).get('cloud_base_v', 0.15)
    loc = np.asarray(spec['loc'], float)
    d = loc - np.asarray(cam_pos)
    d[2] = 0
    d /= np.linalg.norm(d)
    right = np.array([d[1], -d[0], 0.0]) * (-1 if spec['mirror'] else 1)
    up = np.array([0, 0, 1.0])
    o = loc + up * (-base_v * h)
    V = np.array([o - right * w / 2, o + right * w / 2, o + right * w / 2 + up * h, o - right * w / 2 + up * h])
    ob = mesh_from_numpy(name, V, np.array([(0, 1, 2, 3)]), uvs=[('UVMap', np.array([(0, 0), (1, 0), (1, 1), (0, 1)]))],
                         smooth=False)
    m, b = new_mat('M_' + name)
    tx = b.tex(img, b.uv('UVMap'))
    geo = b.N('ShaderNodeNewGeometry')
    Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
    fcol = fog.colour(b, Vd, None, glow=True)
    lum = b.math('ADD', b.math('MULTIPLY', b.sepc(tx.outputs['Color'])[2], 0.6), 0.85)
    if kind == 'mist':
        col = b.scale(fcol, b.math('MULTIPLY', lum, look['mist_gain']))
        al = b.math('MULTIPLY', tx.outputs['Alpha'], spec['opacity'] * look['mist'])
    else:
        # round 3: towers / far cumulus read as solid silver weather, not wisps (density x 0.45, no cap)
        f, fc2 = fog.nodes(b, cap=False, extra=False, dens=look.get('far_fog', 0.45))
        col = b.mix(f, b.scale(tx.outputs['Color'], look['far_gain']), fc2)
        al = b.math('MULTIPLY', tx.outputs['Alpha'], spec['opacity'])
        # resume: the base melts into the deck over its lowest ~120 m (no straight cut where the deck plane hides it)
        zz = b.sep(b.N('ShaderNodeNewGeometry').outputs['Position'])[2]
        al = b.math('MULTIPLY', al, b.smooth(zz, 10.0, 140.0))
    b.out(b.mixs(al, b.transparent(), b.emission(col)))
    ob.data.materials.append(m)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


# ============================================================================================ root collars
COLLAR_CARDS = ('Cloud_Puff_moon', 'Cloud_Cumulus_moon')


def collar_specs(layout, t, cam_pos, seed=3):
    """(round 2, critique B5.3) where each arm leaves the cloud sea, a collar of up-welled cloud 1.2-1.6 x its
    diameter, 20-60 m tall: 2-3 camera-facing puff cards (Unity: Cloud_Puff / Cloud_Cumulus cards, queue 3000,
    children of the arm's root, yaw-billboarded)."""
    rng = np.random.default_rng(seed)
    out = []
    for it in layout:
        if it['layer'] in ('rear',) and t < G.CUE['U9'] - 10:
            continue
        if it['layer'] == 'near':        # 10-50 m from the eye a 50 m puff card reads as a heap of rocks: the near
            continue                     # arms plough the sea (Unity: their root wake is a TODO, README 12)
        W, u = G.world_centreline(it, t, 4)
        above = np.nonzero(W[:, 2] >= 0.0)[0]
        if len(above) == 0 or above[0] == 0:
            continue
        k = above[0]
        P0 = W[k].copy()
        P0[2] = 0.0
        d = np.linalg.norm(P0[:2] - cam_pos[:2])
        if d < 60.0 or d > 6000.0:
            continue
        if math.degrees(math.atan2(float(cam_pos[2]), d)) > 6.0:
            continue    # a vertical puff card seen from > 6 deg above reads as a heap of rocks (U8: eye 80-150 m up);
                        # Unity: collar alpha x smoothstep(8, 5, depression angle in deg)
        r = float(G.arm_radius(it, np.array([u[k]]))[0])
        D = 2 * r
        dv = (P0[:2] - cam_pos[:2]) / d
        right = np.array([dv[1], -dv[0], 0.0])
        n = 3 if D > 40 else 2
        for j in range(n):
            w = max(D * rng.uniform(1.5, 2.2) * (1.0 if j == 0 else rng.uniform(0.6, 0.85)), 50.0)
            off = right * (rng.uniform(-0.55, 0.55) * D) - np.array([dv[0], dv[1], 0.0]) * rng.uniform(0.2, 0.6) * D
            out.append(dict(card=COLLAR_CARDS[j % 2], loc=P0 + off, width=w, height_frac=rng.uniform(0.35, 0.6),
                            mirror=bool(rng.random() < 0.5), arm=it['id']))
    return out


def root_collars(layout, t, cam_pos, fog, look, zplane=12.0):
    meta = json.load(open(os.path.join(CLOUDS, 'clouds_meta.json')))
    mats = {}
    for card in COLLAR_CARDS:
        img = load_img(os.path.join(CLOUDS, card + '.png'), 'sRGB', 'STRAIGHT')
        m, b = new_mat('M_Collar_' + card)
        tx = b.tex(img, b.uv('UVMap'))
        lum = b.vmath('DOT_PRODUCT', tx.outputs['Color'], b.vec((0.2126, 0.7152, 0.0722)))
        silver = b.rgbmul(b.gray(lum), b.rgb((0.92, 0.98, 1.12)))
        col = b.scale(silver, look.get('collar_gain', 1.3))
        f, fcol = fog.nodes(b, cap=False, extra=False, dens=1.0 + look['deck_extra'])
        b.out(b.mixs(tx.outputs['Alpha'], b.transparent(), b.emission(b.mix(f, col, fcol))))
        mats[card] = (m, img.size, meta.get(card, {}).get('cloud_base_v', 0.15))
    V, Fc, UV, MI = [], [], [], []
    for c in collar_specs(layout, t, cam_pos):
        m, (iw, ih), base_v = mats[c['card']]
        w = c['width']
        h = w * ih / iw
        d = np.asarray(c['loc'], float) - cam_pos
        d[2] = 0
        d /= np.linalg.norm(d)
        right = np.array([d[1], -d[0], 0.0]) * (-1 if c['mirror'] else 1)
        # the deck impostor's plane (z = 12 m x k) hides everything below it: the collar's cloud base sits just under
        # that plane (Unity: on the cloud-sea top), so the plane never cuts through the puff's body
        o = np.asarray(c['loc'], float) + np.array([0, 0, zplane - 8.0 - base_v * h])
        k0 = len(V)
        V += [o - right * w / 2, o + right * w / 2, o + right * w / 2 + np.array([0, 0, h]), o - right * w / 2 + np.array([0, 0, h])]
        UV += [(0, 0), (1, 0), (1, 1), (0, 1)]
        Fc.append((k0, k0 + 1, k0 + 2, k0 + 3))
        MI.append(list(mats).index(c['card']))
    if not V:
        return None
    ob = mesh_from_numpy('Collars', np.array(V), np.array(Fc), uvs=[('UVMap', np.array(UV, float))], smooth=False)
    for card in mats:
        ob.data.materials.append(mats[card][0])
    ob.data.polygons.foreach_set('material_index', np.array(MI, np.int32))
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


# ============================================================================================ root sleeves (round 3)
def sleeve_specs(layout, t, cam_pos):
    """critique B6.1: where an arm leaves the sea the deck is raised into a DOME (1.2-1.8 x the root diameter, 30-60 m
    high) and soft MIST climbs 60-150 m up the body with a ragged, downward-streaming top (Gate_RootSleeve_512). One
    pair per root (a braided bundle shares one). Unity: two yaw-billboarded cards per root, children of the arm's root,
    queue 3000, fogged like the body, alpha x smoothstep(8, 5, depression deg)."""
    out = []
    for it in layout:
        if it['layer'] == 'near' or (it['layer'] == 'rear' and t < G.CUE['U9'] - 10):
            continue
        if G.reveal_at(it, t) <= 0.0:
            continue
        W, u = G.world_centreline(it, t, 4)
        above = np.nonzero(W[:, 2] >= 0.0)[0]
        if len(above) == 0 or above[0] == 0:
            continue
        k = above[0]
        P0 = W[k].copy()
        P0[2] = 0.0
        d = np.linalg.norm(P0[:2] - cam_pos[:2])
        if d < 450.0 or d > 7000.0:      # resume: closer than ~450 m the card's top edge reads as a band round the body
            continue
        if math.degrees(math.atan2(float(cam_pos[2]), d)) > 8.0:
            continue
        r = float(G.arm_radius(it, np.array([u[k]]))[0])
        D = 2 * r
        if it.get('bundle'):
            D *= 1.9
        if any(np.linalg.norm(P0[:2] - o['loc'][:2]) < 0.8 * max(D, o['D']) for o in out):
            continue
        out.append(dict(loc=P0, D=D, arm=it['id'], kind='sleeve', width=1.7 * D, height=float(np.clip(1.5 * D, 60.0, 150.0))))
        if d > 900.0:      # resume: the dome card read as a flat dark slab at the 0.5 km pillar
            out.append(dict(loc=P0, D=D, arm=it['id'], kind='dome', width=2.6 * D, height=float(np.clip(0.55 * D, 30.0, 60.0))))
    return out


def _deck_colour_at(tag, cam_pos, P, yaw=0.0, win=40):
    """mean straight colour of the deck impostor around the point P (on the deck plane), as seen from cam_pos."""
    fn = os.path.join(G.WIP, 'deck_%s.npz' % tag)
    if not os.path.exists(fn):
        return np.array([0.03, 0.033, 0.04])
    if fn not in _DECK_NP:
        d = np.load(fn)
        st = d['prem'].astype(np.float32) / np.maximum(d['alpha'].astype(np.float32), 1e-3)[..., None]
        _DECK_NP[fn] = (st, float(d['hfov']), float(d['pitch']))
    st, hfov, pitch = _DECK_NP[fn]
    H, W = st.shape[:2]
    y, p = math.radians(yaw), math.radians(pitch)
    f = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
    r = np.array([math.cos(y), -math.sin(y), 0.0])
    u = np.cross(r, f)
    tx_ = math.tan(math.radians(hfov / 2))
    ty_ = tx_ * H / W
    dv = np.asarray(P, float) - np.asarray(cam_pos, float)
    dz = float(dv @ f)
    ux, uy = float(dv @ r) / (dz * tx_), float(dv @ u) / (dz * ty_)
    cx, cy = int((ux + 1) / 2 * W), int((1 - (uy + 1) / 2) * H)
    sub = st[max(cy - win // 4, 0):cy + win // 4 + 1, max(cx - win, 0):cx + win + 1]
    if sub.size == 0:
        return np.array([0.03, 0.033, 0.04])
    flat = sub.reshape(-1, 3)
    lum = flat @ np.array([0.2126, 0.7152, 0.0722])
    return flat[lum >= np.percentile(lum, 70)].mean(0)       # the lit cloud tops round the root, not the valleys


_DECK_NP = {}


def root_sleeves(layout, t, cam_pos, fog, look, zplane=12.0, tag=None):
    """the sleeve / dome cards, coloured like the deck where they stand (sampled from the deck impostor; Unity: the
    JSON's per-sleeve tint) so they swallow the arm's cut at the cloud top without a visible edge."""
    specs = sleeve_specs(layout, t, cam_pos)
    if not specs:
        return None
    img = load_img(os.path.join(OUT, 'Textures', 'Gate_RootSleeve_512.png'), 'sRGB', 'STRAIGHT')
    m, b = new_mat('M_RootSleeve')
    tx = b.tex(img, b.uv('UVMap'))
    lum = b.sepc(tx.outputs['Color'])[0]
    tint = b.attr('Tint').outputs['Color']
    base = b.scale(tint, b.math('MULTIPLY', b.math('ADD', 0.55, b.math('MULTIPLY', lum, 0.75)), look.get('sleeve_gain', 1.0)))
    f, fcol = fog.nodes(b, cap=False, extra=False, dens=1.0 + look['deck_extra'])
    al = b.math('MULTIPLY', tx.outputs['Alpha'], look.get('sleeve_alpha', 0.92))
    b.out(b.mixs(al, b.transparent(), b.emission(b.mix(f, base, fcol))))
    V, Fc, UV, COL = [], [], [], []
    for c in specs:
        w, h = c['width'], c['height']
        dv = np.asarray(c['loc'], float) - cam_pos
        dv[2] = 0
        dv /= np.linalg.norm(dv)
        right = np.array([dv[1], -dv[0], 0.0])
        o = np.asarray(c['loc'], float) - dv * 0.85 * c['D'] + np.array([0, 0, zplane - 4.0])     # clear of the skin
        col = _deck_colour_at(tag, cam_pos, np.asarray(c['loc'], float) + np.array([0, 0, zplane]),
                              180.0 if (tag or '').startswith('rear') else 0.0) * look.get('deck_gain', 0.52)
        k0 = len(V)
        V += [o - right * w / 2, o + right * w / 2, o + right * w / 2 + np.array([0, 0, h]), o - right * w / 2 + np.array([0, 0, h])]
        UV += [(0, 0), (1, 0), (1, 1), (0, 1)]
        COL += [tuple(col) + (1.0,)] * 4
        Fc.append((k0, k0 + 1, k0 + 2, k0 + 3))
    ob = mesh_from_numpy('RootSleeves', np.array(V), np.array(Fc), uvs=[('UVMap', np.array(UV, float))],
                         point_colors=[('Tint', np.array(COL, float))], smooth=False)
    ob.data.materials.append(m)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    return ob


# ============================================================================================ cloud deck impostor
DECK_FOR_SHOT = {'U6': 'gate3', 'U7': 'gate3', 'key': 'gate3', 'U8': 'gate3', 'U8a': 'gate3', 'U8b': 'gate3',
                 'U8side': 'side3', 'U8fwd': 'gate3', 'rear': 'rear4'}


def deck_impostor(tag, t, cam_pos, fog, look, yaw=0.0):
    """the volumetric cloud deck rendered by cloud_deck.py from the eye, reprojected on a quad perpendicular to its
    camera axis, D m in front of the eye (in front of every arm: below the cloud line the deck is opaque and hides
    what is under the cloud top; above it the deck is transparent). Pixel-exact from the eye; a deck rendered for
    eye height h serves an eye at k*h unchanged (similar triangles). LanbaiFog per pixel at the distance where the
    ray meets the deck top (z = 12 m x k), density 0.0006 x (1 + deck_extra)."""
    fn = os.path.join(G.WIP, 'deck_%s.npz' % tag)
    d = np.load(fn)
    prem = d['prem'].astype(np.float32)
    al = d['alpha'].astype(np.float32)
    H, W = al.shape
    soft = float(look.get('deck_soft', 0.0))
    hfov, pitch, eye_h = float(d['hfov']), float(d['pitch']), float(d['eye_h'])
    if soft > 0 or look.get('deck_quiet', 0.0) > 0:
        # round 3 (critique B6.2): QUIET the deck. Per row (row -> depression angle -> distance on the cloud plane):
        # the billow detail above a ~1 deg scale is compressed (near: x deck_quiet_near, at 1 km: x deck_quiet_far),
        # leaving large soft cells; the near rows are darkened toward deck_near_gain (key: near deck L* <= 14).
        # (The rear deck's 'deck_soft' is the old uniform version.)
        from scipy.ndimage import gaussian_filter
        st = prem / np.maximum(al, 1e-3)[..., None]
        lum = st @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        tyv = math.tan(math.radians(hfov / 2)) * H / W
        rows = np.arange(H)
        el = pitch + np.degrees(np.arctan((0.5 - (rows + 0.5) / H) * 2 * tyv))
        dist = eye_h / np.tan(np.radians(np.clip(-el, 0.05, 89.0)))
        if look.get('deck_quiet', 0.0) > 0:
            qn, qf = look.get('deck_quiet_near', 0.30), look.get('deck_quiet_far', 0.55)
            keep = qn + (qf - qn) * np.clip((dist - 300.0) / 900.0, 0.0, 1.0)
            base = gaussian_filter(lum, look.get('deck_quiet_px', 28.0))
            tgt = base + (lum - base) * keep[:, None]
            ng = look.get('deck_near_gain', 0.7)
            g = ng + (1.0 - ng) * np.clip((dist - 150.0) / 700.0, 0.0, 1.0)
            tgt = np.maximum(tgt * g[:, None], 0.0)
        else:
            base = gaussian_filter(lum, look.get('deck_soft_px', 6.0))
            tgt = np.maximum(base + (lum - base) * (1.0 - soft), 0.0)
        prem = st * (tgt / np.maximum(lum, 1e-5))[..., None] * al[..., None]
    k = float(cam_pos[2]) / eye_h
    img = bpy.data.images.new('Deck_' + tag, W, H, alpha=True, float_buffer=True, is_data=True)
    img.alpha_mode = 'CHANNEL_PACKED'
    rgba = np.concatenate([prem, al[..., None]], -1)[::-1]
    img.pixels.foreach_set(np.ascontiguousarray(rgba, np.float32).ravel())
    img.update()
    y, p = math.radians(yaw), math.radians(pitch)
    f = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
    r = np.array([math.cos(y), -math.sin(y), 0.0])
    u = np.cross(r, f)
    tx_ = math.tan(math.radians(hfov / 2))
    ty_ = tx_ * H / W
    # run 2b: the deck image is projected (from the eye) onto the cloud-top PLANE (z = 12 m x k) instead of a card in
    # front of the eye, so arms are hidden by the cloud at their own depth (their feet go INTO the sea) rather than
    # cut along the horizon line
    zp = 12.0 * k
    R0 = 20000.0
    cx, cy = float(cam_pos[0]), float(cam_pos[1])
    V = np.array([[cx - R0, cy - R0, zp], [cx + R0, cy - R0, zp], [cx + R0, cy + R0, zp], [cx - R0, cy + R0, zp]])
    ob = mesh_from_numpy('CloudDeck_' + tag, V, np.array([(0, 1, 2, 3)]), smooth=False)
    m, b = new_mat('M_Deck_' + tag)
    geo0 = b.N('ShaderNodeNewGeometry')
    dv = b.vmath('SUBTRACT', geo0.outputs['Position'], b.vec(tuple(np.asarray(cam_pos, float))))
    dz = b.vmath('DOT_PRODUCT', dv, b.vec(tuple(f)))
    ux = b.math('DIVIDE', b.vmath('DOT_PRODUCT', dv, b.vec(tuple(r))), b.math('MULTIPLY', b.math('MAXIMUM', dz, 1e-3), tx_))
    uy = b.math('DIVIDE', b.vmath('DOT_PRODUCT', dv, b.vec(tuple(u))), b.math('MULTIPLY', b.math('MAXIMUM', dz, 1e-3), ty_))
    uvc = b.N('ShaderNodeCombineXYZ')
    b.L(b.math('ADD', 0.5, b.math('MULTIPLY', ux, 0.5)), uvc.inputs[0])
    b.L(b.math('ADD', 0.5, b.math('MULTIPLY', uy, 0.5)), uvc.inputs[1])
    tx = b.tex(img, uvc.outputs[0])
    tx.interpolation = 'Cubic'
    inside = b.math('MULTIPLY', b.math('GREATER_THAN', dz, 1.0),
                    b.math('MULTIPLY', b.math('LESS_THAN', b.math('ABSOLUTE', ux), 1.0), b.math('LESS_THAN', b.math('ABSOLUTE', uy), 1.0)))
    a = b.math('MULTIPLY', tx.outputs['Alpha'], inside)
    geo = b.N('ShaderNodeNewGeometry')
    Vd = b.vmath('SCALE', geo.outputs['Incoming'], None, -1.0)
    vz = b.sep(Vd)[2]
    tpl = b.math('DIVIDE', -(float(cam_pos[2]) - 12.0 * k), b.math('MINIMUM', vz, -1e-4))
    rho = look['fog'] * (1.0 + look['deck_extra'])
    fg = b.math('SUBTRACT', 1.0, b.math('EXPONENT', b.math('MULTIPLY', tpl, -rho)))
    fg = b.math('MULTIPLY', fg, look['deck_fog'])
    fcol = fog.colour(b, Vd, None, glow=True)
    dc = tx.outputs['Color']
    if look.get('deck_gamma', 1.0) != 1.0:      # lift the deck's shadows (prem colour / alpha, ^gamma, x alpha)
        st = b.N('ShaderNodeVectorMath'); st.operation = 'DIVIDE'
        b.L(dc, st.inputs[0]); b.L(b.N('ShaderNodeCombineXYZ').outputs[0], st.inputs[1])
        cx = st.inputs[1].links[0].from_node
        for i in range(3):
            b.L(b.math('MAXIMUM', a, 1e-3), cx.inputs[i])
        pw = b.N('ShaderNodeMath'); pw.operation = 'POWER'
        sep = b.sep(st.outputs[0])
        cc = b.N('ShaderNodeCombineXYZ')
        for i in range(3):
            b.L(b.math('POWER', sep[i], look['deck_gamma']), cc.inputs[i])
        dc = b.scale(cc.outputs[0], a)
    dc = b.scale(dc, look['deck_gain'])
    if look.get('deck_desat', 0.0) > 0:      # moonlit cloud is cold silver (h 255-268, C* <= 6), not lavender (B8)
        lum = b.vmath('DOT_PRODUCT', dc, b.vec((0.2126, 0.7152, 0.0722)))
        dc = b.mix(look['deck_desat'], dc, b.rgbmul(b.gray(lum), b.rgb((0.92, 0.98, 1.12))))
    add = None
    if not tag.startswith('rear'):
        dc, add = deck_tear_light(b, dc, a, t, look)
    elif look.get('glory', 1.0) > 0:
        # round 3 (awe rear): the bus's own shadow at the anti-moon point (~8 deg below the horizon behind it) inside a
        # faint COLOURLESS moon glory (ring r ~3.2 deg, +5..7 L*, C* <= 6). Unity: MoonGlory card (JSON 'glory').
        am = b.vmath('DOT_PRODUCT', Vd, b.vec(tuple(-G.L_MOON)))
        ang = b.math('MULTIPLY', b.math('ARCCOSINE', b.math('MINIMUM', am, 1.0)), 180.0 / math.pi)
        ring = b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', b.math('POWER', b.math('DIVIDE', b.math('SUBTRACT', ang, 3.2), 0.75), 2.0), -1.0)), 0.30)
        core = b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', b.math('POWER', b.math('DIVIDE', ang, 1.7), 2.0), -1.0)), 0.16)
        g = b.math('MULTIPLY', b.math('ADD', ring, core), look.get('glory', 1.0))
        lum = b.vmath('DOT_PRODUCT', dc, b.vec((0.2126, 0.7152, 0.0722)))
        dc = b.rgbadd(dc, b.scale(b.rgbmul(b.gray(lum), b.rgb((0.97, 1.0, 1.04))), g))
        shadow = b.smooth(ang, 0.30, 0.16)
        dc = b.scale(dc, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', shadow, 0.55)))
    col = b.rgbadd(b.scale(dc, b.math('SUBTRACT', 1.0, fg)),
                   b.scale(fcol, b.math('MULTIPLY', a, fg)))
    if add is not None:      # the kit's Tear_CloudGlow / Tear_Foot are unfogged additive sky objects (bible 1.6)
        col = b.rgbadd(col, add)
    em = b.emission(col)
    tr = b.N('ShaderNodeBsdfTransparent')
    b.L(b.gray(b.math('SUBTRACT', 1.0, a)), tr.inputs['Color'])
    b.out(b.add(em, tr.outputs[0]))
    ob.data.materials.append(m)
    ob.visible_shadow = False
    ob.visible_diffuse = False
    ob.visible_glossy = False
    print('deck %s: k %.2f, %dx%d' % (tag, k, W, H))
    return ob


_LANES = {}


def lanes_image(t):
    """the radial shadow-lane mask (gate_layout.lane_mask) as a Blender image (cached on disk per layout)."""
    lay = G.build_layout()
    fn = os.path.join(G.WIP, 'lanes_%s.png' % G._layout_sig()[:8])
    if not os.path.exists(fn):
        from PIL import Image
        M = G.lane_mask(lay, t)
        Image.fromarray((np.clip(M, 0, 1) * 255 + 0.5).astype(np.uint8)).save(fn)
    if fn not in _LANES:
        _LANES[fn] = load_img(fn, 'Non-Color', 'STRAIGHT')
    return _LANES[fn]


def deck_tear_light(b, dc, a, t, look):
    """the wound's light on the cloud sea, per pixel on the deck plane (Unity: Tear_CloudGlow x Tear_CloudLanes +
    Tear_Foot): (1) the pool (#495270 target) centred 150 m x S behind the foot, cut by the shadow lanes;
    (2) the foot crevasse running 700 m toward the bus, its floor #C0B9E4 and dark walls; (3) a cold silver lift
    toward the moon (h 255-268) instead of the lavender band."""
    S = G.tear_H(t) / G.TD.H
    geo = b.N('ShaderNodeNewGeometry')
    P = geo.outputs['Position']
    px, py, pz = b.sep(P)
    x0, x1, y0, y1 = G.LANES_RECT
    uvl = b.N('ShaderNodeCombineXYZ')
    b.L(b.math('DIVIDE', b.math('SUBTRACT', px, x0), x1 - x0), uvl.inputs[0])
    b.L(b.math('DIVIDE', b.math('SUBTRACT', py, y0), y1 - y0), uvl.inputs[1])
    lanes = b.tex(lanes_image(t), uvl.outputs[0], ext='EXTEND').outputs['Color']
    lanes = b.sepc(lanes)[0]
    rg = b.math('DIVIDE', b.math('SQRT', b.math('ADD', b.math('POWER', px, 2.0),
                                                 b.math('POWER', b.math('SUBTRACT', py, 150.0 * S), 2.0))), 1.0)
    # pool: full within ~300 m, half by ~650 m, gone by ~1.3 km
    pool = b.math('ADD', b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', b.math('POWER', b.math('DIVIDE', rg, 420.0), 2.0), -1.0)), 0.75),
                  b.math('MULTIPLY', b.math('EXPONENT', b.math('MULTIPLY', b.math('DIVIDE', rg, 900.0), -1.0)), 0.25))
    pool = b.math('MULTIPLY', b.math('MULTIPLY', pool, lanes), look.get('pool', 1.1))
    # v3b: the pool LIGHTS the cloud it falls on (multiply-add, Unity: Tear_CloudGlow with Blend DstColor One, i.e.
    # dst x (1 + glow)): the billows keep their modelling; a flat additive veil (v3) washed the U8 foreground flat.
    # A small additive floor (25 %) keeps the gaps between billows from going black under the wound.
    cg = np.asarray(F['CloudGlow'], float)
    tint = tuple(cg / max(float(cg @ np.array([0.2126, 0.7152, 0.0722])), 1e-6))
    glow = b.rgbadd(b.scale(b.rgbmul(dc, b.rgb(tint)), b.math('MULTIPLY', pool, look.get('pool_mul', 0.7))),
                    b.scale(b.rgb(tuple(F['CloudGlow'])), b.math('MULTIPLY', pool, b.math('MULTIPLY', a, 0.25))))
    out = b.rgbmul(dc, b.mix(b.math('MINIMUM', pool, 1.0), (1.0, 1.0, 1.0), (0.95, 0.95, 1.08)))
    # crevasse
    L = G.CREVASSE['length']
    w0 = G.CREVASSE['w0_frac'] * 2 * G.tear_half_width(t)
    s = b.math('MINIMUM', b.math('MAXIMUM', b.math('DIVIDE', b.math('MULTIPLY', py, -1.0), L), 0.0), 1.0)
    w = b.math('MULTIPLY', w0, b.math('POWER', b.math('SUBTRACT', 1.0, s), 0.8))
    xc0 = 0.5 * float(G.TD.path(np.array([0.0]))[0]) * S
    xc = b.math('ADD', xc0, b.math('MULTIPLY', b.math('MULTIPLY', b.math('SINE', b.math('DIVIDE', py, 97.0)), s), G.CREVASSE['wander']))
    nz = b.N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 1.0 / 40.0; nz.inputs['Detail'].default_value = 3.0
    b.L(P, nz.inputs['Vector'])
    q = b.math('DIVIDE', b.math('ABSOLUTE', b.math('SUBTRACT', px, xc)), b.math('MAXIMUM', b.math('MULTIPLY', w, 0.5), 0.5))
    q = b.math('ADD', q, b.math('MULTIPLY', b.math('SUBTRACT', nz.outputs['Fac'], 0.5), 0.6))
    inside = b.math('MULTIPLY', b.smooth(q, 1.0, 0.55), b.smooth(py, 30.0, -10.0))
    inside = b.math('MULTIPLY', inside, b.smooth(s, 1.0, 0.85))
    wall = b.math('MULTIPLY', b.smooth(q, 1.25, 0.95), b.math('SUBTRACT', 1.0, inside))
    wall = b.math('MULTIPLY', wall, b.smooth(py, 30.0, -10.0))
    floor_ = b.scale(b.rgb(tuple(F['Glow'])), b.math('MULTIPLY', b.math('MULTIPLY', b.math('POWER', b.math('SUBTRACT', 1.0, s), 1.3),
                                                                                       b.smooth(q, 0.9, 0.0, 0.35, 1.0)), look.get('crevasse', 0.35)))
    out = b.scale(out, b.math('SUBTRACT', 1.0, b.math('MULTIPLY', b.math('MAXIMUM', wall, inside), look.get('crev_dark', 0.3))))
    add = b.rgbadd(glow, b.scale(floor_, b.math('MULTIPLY', inside, a)))
    return out, add


# ============================================================================================ tear kit + shafts
def tear_kit(t, cam_pos, look, hfov, W, ctop=4.0):
    """ctop = the cloud-top height the kit's foot dissolves into (Unity: _Udon_CloudTop): the deck impostor's plane
    (12 m x k) + 2 m, so the 40 m foot fade starts where the rendered cloud starts hiding the cards."""
    S = G.tear_H(t) / G.TD.H
    D = max(np.linalg.norm(cam_pos - G.tear_core_cf(t)), 50.0)
    cfg = dict(open=0.18 + 0.12 * G.tear_open(t), rip=G.rip_progress(t), halo=look['halo'], folds=look['folds'],
               intensity=look['intensity'], shaft=look['shaft'], ctop=float(ctop))
    px_m = D * math.tan(math.radians(hfov / W)) / S
    fog = Fog(t, cam_pos, look)
    obs = RT.build_kit(cfg, S, (0.0, 0.0, 0.0), tuple(cam_pos), px_m, skip=('Tear_Shafts',),
                       sky_fn=lambda b, V: fog.colour(b, V, None, glow=False))   # the cloth occludes the halo
    # as in Unity: the kit is unlit cards that the tentacles do not reflect (their tear light is the directional
    # light + the shader's tear rim); Cycles would otherwise mirror the halo cards' back faces on every arm
    for o in obs:
        o.visible_glossy = look['kit_glossy'] > 0
        o.visible_diffuse = False
        o.visible_transmission = False
    return obs, cfg


def _ribbon(items, t, cam_pos, nl=24, kit=True):
    """camera-facing ribbons about each item's axis (start, axis, length, half_width, widen); per-vertex 'Fade' =
    side-view fade x near fade x gain; UV.y along."""
    S = G.tear_H(t) / G.TD.H
    V, Fc, UV, FA = [], [], [], []
    for s_ in items:
        k = S if s_.get('kit_space') else 1.0
        p0 = np.asarray(s_['start']) * k
        ax = np.asarray(s_['axis'])
        L = s_['length'] * k
        hw0 = s_['half_width'] * k
        wid = s_.get('widen', 2.2)
        b0 = len(V)
        for j in range(nl):
            f = j / (nl - 1)
            p = p0 + ax * L * f
            view = cam_pos - p
            side = np.cross(ax, view)
            side /= np.linalg.norm(side) + 1e-9
            vd = view / np.linalg.norm(view)
            perp = math.sqrt(max(0.0, 1 - float(np.dot(ax, vd)) ** 2))
            fd = min(perp * 1.4, 1.0) ** 2.0 * float(np.clip((np.linalg.norm(view) - 250.0) / 450.0, 0, 1)) ** 1.5
            fd *= s_.get('gain', s_.get('alpha', 1.0))
            hw = hw0 * (1.0 + (wid - 1.0) * min(L * f / 1500.0, 1.0))
            for x in (0.0, 1.0):
                V.append(p + side * (x - 0.5) * 2 * hw)
                UV.append((x, f))
                FA.append((fd, fd, fd, 1.0))
        for j in range(nl - 1):
            q = b0 + 2 * j
            Fc.append((q, q + 1, q + 3, q + 2))
    return np.array(V), np.array(Fc), np.array(UV), np.array(FA)


def shafts(shaft_pair, t, cam_pos, look):
    """beam cards (Lanbai/Tear Part=Shaft, Shaft_Gradient: 3 beams across, bright at the wound): additive ShaftBeam
    fill x shaft; + the shadow WEDGES in the band (multiplicative: transparent x (1 - alpha x profile))."""
    beams, wedges = shaft_pair
    img = load_img(os.path.join(TEAR_TEX, 'Shaft_Gradient_256x1024.png'), 'Non-Color', 'CHANNEL_PACKED')
    obs = []
    if beams and look['shaft'] > 0:
        m, b = new_mat('M_Shafts')
        uvn = b.uv('UVMap')
        u_, v_, _ = b.sep(uvn)
        # round 3 (B7.1): one soft lobe across, no internal striation (Unity: Shaft_Gradient v4)
        lobe = b.math('POWER', b.smooth(b.math('ABSOLUTE', b.math('SUBTRACT', u_, 0.5)), 0.5, 0.0), 1.6)
        along = b.math('MULTIPLY', b.smooth(v_, 0.0, 0.06), b.math('POWER', b.math('SUBTRACT', 1.0, v_), 1.3))
        fade = b.sepc(b.attr('Fade').outputs['Color'])[0]
        k = b.math('MULTIPLY', b.math('MULTIPLY', lobe, along), b.math('MULTIPLY', fade, look['shaft']))
        b.out(b.add(b.emission(b.scale(b.rgb(tuple(F['ShaftBeam'])), k)), b.transparent()))
        V, Fc, UV, FA = _ribbon(beams, t, cam_pos)
        ob = mesh_from_numpy('Shafts', V, Fc, uvs=[('UVMap', UV)], point_colors=[('Fade', FA)], smooth=False)
        ob.data.materials.append(m)
        obs.append(ob)
    if wedges and look.get('wedge', 1.0) > 0:
        m, b = new_mat('M_Wedges')
        uvn = b.uv('UVMap')
        u, v, _ = b.sep(uvn)
        prof = b.math('MULTIPLY', b.smooth(b.math('ABSOLUTE', b.math('SUBTRACT', u, 0.5)), 0.5, 0.15),
                      b.math('MULTIPLY', b.smooth(v, 0.0, 0.15), b.smooth(v, 1.0, 0.55)))
        fade = b.sepc(b.attr('Fade').outputs['Color'])[0]
        al = b.math('MULTIPLY', b.math('MULTIPLY', prof, fade), look.get('wedge', 1.0))
        tr = b.N('ShaderNodeBsdfTransparent')
        b.L(b.gray(b.math('SUBTRACT', 1.0, al)), tr.inputs['Color'])
        b.out(tr.outputs[0])
        V, Fc, UV, FA = _ribbon(wedges, t, cam_pos, nl=12, kit=False)
        ob = mesh_from_numpy('Wedges', V, Fc, uvs=[('UVMap', UV)], point_colors=[('Fade', FA)], smooth=False)
        ob.data.materials.append(m)
        obs.append(ob)
    for ob in obs:
        ob.visible_shadow = False
        ob.visible_diffuse = False
        ob.visible_glossy = False
    return obs


# ============================================================================================ shots
from gate_scene_shots import SHOTS  # noqa: E402  (single source)


def build(shot, W, H, spp, look=None, only=None, nobus=False, sh=None):
    sh = dict(SHOTS[shot], **(sh or {}))
    look = dict(LOOK, **dict(sh.get('look', {}), **(look or {})))
    t = sh['t']
    look.setdefault('band_ramp', G.band_ramp(t))
    t_fade = G.CUE['U7b'] + 1.5
    look.setdefault('moon_disc', float(np.clip(1.0 - (t - t_fade) / 2.0, 0.0, 1.0)))
    sc = setup(W, H, spp)
    sc.cycles.glossy_bounces = int(look.get('gloss_b', 1))
    sc.cycles.max_bounces = max(1, int(look.get('gloss_b', 1)))
    cam_pos = G.eye_cf(t, sh['eye'])
    world(look)
    cam = camera(cam_pos, sh['yaw'], sh['pitch'], sh['hfov'])
    fog = Fog(t, cam_pos, look)
    core = G.tear_core_cf(t)
    # lights (Unity: realtime directionals; sun strength = pi x E)
    moon = sun('L_Moon', -G.L_MOON, math.pi * E_MOON, COL_MOON, angle_deg=1.2, shadow=True)
    tear_l = sun('L_Tear', G.unit(cam_pos - core), math.pi * E_TEAR, COL_TEAR, angle_deg=4.0, shadow=False)
    fill = sun('L_Fill', (0, 0, 1.0), math.pi * E_FILL, COL_FILL, angle_deg=30.0, shadow=False)
    layout = G.build_layout()
    pix_angle = math.radians(sh['hfov']) / W
    want = lambda k: (only is None) or (k in only)
    # the deck impostor's plane (z = 12 m x k, k = eye height / the deck's render eye height) hides everything below
    # it: the kit's foot fade and the root collars start there, not at z = 0 (U8: k ~ 1.9, plane at ~22 m)
    tag0 = look.get('deck_tag') or sh.get('deck', DECK_FOR_SHOT.get(shot))
    fn0 = os.path.join(G.WIP, 'deck_%s.npz' % tag0) if tag0 else ''
    zplane = 12.0 * float(cam_pos[2]) / float(np.load(fn0)['eye_h']) if (fn0 and os.path.exists(fn0)) else 2.0
    look['zplane'] = zplane
    if want('tear'):
        tear_kit(t, cam_pos, look, sh['hfov'], W, ctop=zplane + 2.0)
    if want('arms'):
        place_tentacles(layout, t, fog, pix_angle)
    if want('tide'):
        cells = json.load(open(os.path.join(TEXT, 'TentacleTide_Atlas.json')))['cells']
        tide_billboards(G.build_tide(cells), t, cam_pos, fog, look)
    if want('shafts'):
        shafts(G.build_shafts(), t, cam_pos, look)
    if want('clouds'):
        tag = look.get('deck_tag') or sh.get('deck', DECK_FOR_SHOT.get(shot))
        if tag and os.path.exists(os.path.join(G.WIP, 'deck_%s.npz' % tag)) and look['floor'] == 'deck':
            deck_impostor(tag, t, cam_pos, fog, look, yaw=180.0 if tag.startswith('rear') else 100.0 if tag.startswith('side') else 0.0)
        elif look['floor'] in ('field', 'both', 'deck'):
            cloud_floor(t, cam_pos, fog, look, yaw=sh['yaw'], span=sh['hfov'] * 0.5 + 25, full=(shot == 'rear'))
            if 'CloudFloor' in bpy.data.objects:
                exclude_from([tear_l, fill], [bpy.data.objects['CloudFloor']])
        if look.get('collars', 0.0) > 0:          # round 3: the crisp collars are retired (B6.1); sleeves instead
            root_collars(layout, t, cam_pos, fog, look, zplane=zplane)
        if look.get('sleeves', 1.0) > 0:
            root_sleeves(layout, t, cam_pos, fog, look, zplane=zplane, tag=tag0)
        if look['mist'] > 0:
            for i, spc in enumerate(G.mist_positions(G.MIST)):
                mist_card('Mist_%02d' % i, spc, cam_pos, fog, look, 'mist')
            for i, spc in enumerate(G.mist_positions(G.FAR_CLOUDS)):
                mist_card('FarCloud_%02d' % i, spc, cam_pos, fog, look, 'far')
        if look.get('relief', 1.0) > 0:       # run 6: horizon relief (the tide rises from behind cloud heads)
            for i, spc in enumerate(G.mist_positions(G.horizon_relief())):
                mist_card('Relief_%02d' % i, spc, cam_pos, fog, look, 'far')
        if look.get('towers', 1.0) > 0:       # round 3 (B8): the giants' cloud towers (sag after the reveal)
            for spc in G.tower_specs(layout):
                sg = float(np.interp(t, [k[0] for k in spc['sag']], [k[1] for k in spc['sag']]))
                spc = dict(spc, width=spc['width'], opacity=spc['opacity'] * float(np.interp(t, [k[0] for k in spc['alpha']], [k[1] for k in spc['alpha']])))
                spc['sag_y'] = sg
                mist_card(spc['id'], spc, cam_pos, fog, look, 'far')
        tdir = G.unit(core - cam_pos)
        if look['cards'] > 0:
            for i, (card, x, y, z, w, face, br, mir, role) in enumerate(G.CLOUD_CARDS):
                cloud_card('Card_%02d' % i, card, (x, y, z), w, cam_pos, br, mir, fog, look, tear_dir=tdir)
    if sh.get('bus') and not nobus and want('bus'):
        import gate_bus
        gate_bus.build(t, sh, look, [moon, tear_l, fill])
    return sc, cam_pos


def render(shot, W, H, spp, base, look=None, only=None, nobus=False, sh=None, border=None):
    t0 = time.time()
    sc, cam_pos = build(shot, W, H, spp, look, only, nobus, sh)
    if border:
        x0, x1, y0, y1 = border
        sc.render.use_border = True
        sc.render.use_crop_to_border = True
        sc.render.border_min_x, sc.render.border_max_x = x0, x1
        sc.render.border_min_y, sc.render.border_max_y = y0, y1
    exr = base + '.exr'
    sc.render.filepath = exr
    bpy.ops.render.render(write_still=True)
    print('render %.0fs' % (time.time() - t0))
    im = bpy.data.images.load(exr, check_existing=False)
    w, h = im.size
    lin = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    np.save(base + '_lin.npy', lin.astype(np.float16))
    d = s4.to_display(lin, bloom=True, vignette=True)
    s4.save(d, base + '.png')
    print('wrote', base + '.png')
    return base + '.png'


LAYER_CODE = {'near': 1, 'mid': 2, 'colossus': 3, 'colossus_bg': 4, 'rear': 5, 'pillar': 7, 'hero': 6, 'surge': 8}


def _alpha_tested(b, ob, code):
    """emission (0, 0, code) where the object's own texture alpha > 0.5, transparent elsewhere."""
    src = None
    for m in ob.data.materials:
        if m and m.node_tree:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image is not None:
                    src = n
                    break
        if src:
            break
    if src is None:
        b.out(b.emission((0.0, 0.0, code)))
        return
    vec = src.inputs['Vector'].links[0].from_socket if src.inputs['Vector'].links else None
    if vec is None or vec.node.type not in ('UVMAP', 'TEX_COORD'):
        uvname = 'UVMap'
        tx = b.tex(src.image, b.uv(uvname))
    else:
        tx = b.tex(src.image, b.uv(getattr(vec.node, 'uv_map', 'UVMap') or 'UVMap'))
    b.out(b.mixs(b.math('GREATER_THAN', tx.outputs['Alpha'], 0.5), b.transparent(), b.emission((0.0, 0.0, code))))


def id_materials(base=None):
    """round 2 (critique BLOCKER 4): every object gets an OBJECT-linked ID emission. Arms: R = (index + 1) / 128 (the
    index -> id / layer / role table is written to <base>_idmap.json), G = arc fraction t (UVSway.x), B = 0; the
    clip below the cloud top kept. Tear lens / flaps (alpha-tested) B = 0.25; cloud deck (alpha > 0.5) B = 0.5;
    tide (alpha-tested) B = 0.75; the bus shell B = 1 (glass see-through); glows, halo, folds, shafts, mist: none."""
    lay = G.build_layout()
    idx = {it['id']: i for i, it in enumerate(lay)}
    table = {}
    for ob in bpy.context.scene.objects:
        if ob.type != 'MESH':
            continue
        nm = ob.name
        m, b = new_mat('ID_' + nm)
        if nm in idx:
            it = lay[idx[nm]]
            table[idx[nm] + 1] = dict(id=nm, layer=it['layer'], role=it.get('role'), kind=arm_kind(it))
            tt = b.sep(b.uv('UVSway'))[0]
            c = b.N('ShaderNodeCombineXYZ')
            c.inputs[0].default_value = (idx[nm] + 1) / 128.0
            b.L(tt, c.inputs[1])
            geo = b.N('ShaderNodeNewGeometry')
            z = b.sep(geo.outputs['Position'])[2]
            b.out(b.mixs(b.math('GREATER_THAN', z, -1.0), b.transparent(), b.emission(c.outputs[0])))
        elif nm.startswith('CloudDeck'):
            src = [n for n in ob.data.materials[0].node_tree.nodes if n.type == 'TEX_IMAGE'][0]
            # the deck's own projection UV (same node tree): re-use its vector input
            tx = b.tex(src.image, b.uv('UVMap'))
            m = ob.data.materials[0].copy()
            nt = m.node_tree
            out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
            bb = NB(nt)
            srcn = [n for n in nt.nodes if n.type == 'TEX_IMAGE' and n.image is src.image][0]
            bb.L(bb.mixs(bb.math('GREATER_THAN', srcn.outputs['Alpha'], 0.5), bb.transparent(), bb.emission((0, 0, 0.5))),
                 out.inputs['Surface'])
        elif nm == 'Tide':
            _alpha_tested(b, ob, 0.75)
        elif nm.startswith(('Tear_Lens', 'Tear_Flap')):
            _alpha_tested(b, ob, 0.25)
        elif nm.startswith(('Tower_', 'RootSleeves', 'FarCloud_')):
            _alpha_tested(b, ob, 0.5)          # round 3: cloud towers / sleeves count as cloud (they hide what is behind)
        elif nm.startswith(('Tear_', 'Mist_', 'FarCloud_', 'Shafts', 'Wedges', 'Card_', 'Collar')):
            b.out(b.transparent())
        else:                               # the bus shell (glass is see-through)
            if 'Glass' in nm or 'Windscreen' in nm or 'WsCorner' in nm or 'Rain' in nm:
                b.out(b.transparent())
            else:
                b.out(b.emission((0.0, 0.0, 1.0)))
        for sl in ob.material_slots:
            sl.link = 'OBJECT'
            sl.material = m
    w = bpy.context.scene.world
    w.node_tree.nodes.clear()
    bw = NB(w.node_tree)
    bg = bw.N('ShaderNodeBackground')
    bg.inputs['Color'].default_value = (0, 0, 0, 1)
    o = bw.N('ShaderNodeOutputWorld')
    bw.L(bg.outputs[0], o.inputs['Surface'])
    if base:
        json.dump(table, open(base + '_idmap.json', 'w'), indent=0)
    return table


def render_ids(shot, W, H, base, look=None, sh=None):
    sc, cam_pos = build(shot, W, H, 4, look, None, False, sh)
    id_materials(base)
    sc.cycles.use_adaptive_sampling = False
    sc.cycles.use_denoising = False
    sc.cycles.pixel_filter_type = 'BOX'
    sc.cycles.filter_width = 0.01
    sc.cycles.samples = 1
    for l in [o for o in sc.objects if o.type == 'LIGHT']:
        bpy.data.objects.remove(l, do_unlink=True)
    sc.render.filepath = base + '_id.exr'
    bpy.ops.render.render(write_still=True)
    im = bpy.data.images.load(base + '_id.exr', check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], np.float32).reshape(h, w, 4)[::-1, :, :3]
    np.save(base + '_id.npy', a.astype(np.float16))
    print('wrote', base + '_id.npy')


def _parse_set(args):
    look, sh = {}, {}
    for a in args:
        if a.startswith('--set='):
            for kv in a[6:].split(','):
                k, v = kv.split(':')
                try:
                    v = float(v)
                except ValueError:
                    pass
                (sh if k in ('t', 'yaw', 'pitch', 'hfov') else look)[k] = v
    return look, sh


if __name__ == '__main__':
    a = sys.argv[1:]
    if a[0] == 'render':
        shot, W, H, spp, base = a[1], int(a[2]), int(a[3]), int(a[4]), a[5]
        look, sh = _parse_set(a)
        only = None
        for x in a:
            if x.startswith('--only='):
                only = x[7:].split(',')
        border = None
        for x in a:
            if x.startswith('--border='):
                border = tuple(float(v) for v in x[9:].split(','))
        render(shot, W, H, spp, base, look, only, '--nobus' in a, sh, border)
    elif a[0] == 'ids':
        shot, W, H, base = a[1], int(a[2]), int(a[3]), a[4]
        look, sh = _parse_set(a)
        render_ids(shot, W, H, base, look, sh)
    elif a[0] == 'export':
        import gate_export
        gate_export.main()
