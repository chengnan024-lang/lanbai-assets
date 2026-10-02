"""Generic bus shell for the in-bus gate frames (ART BIBLE v2 §4.1 / §4.6 / §4.8): windscreen wrapping round
the front corners, A-pillars, dashboard edge, header with the destination blind, roof with the 0.6 m skylight,
door glass, side windows, the empty driver's seat + wheel, the radio's warm dial, two rows of dying tube lights.

Built from the bible's ANGULAR spec seen from the hero eye (Unity bus-relative (0.55, 1.70, 2.05)):
windscreen az -50..+25, el -15..+22; door glass +30..+65; skylight az ~-5..+25, el +40..+68.
Not the current Unity bus: a new bus may come; the angles are the contract.
Unity bus-relative coordinates here (x right, y up, z forward), converted to CF at time t.
"""
import math
import os
import sys

import numpy as np

import gate_layout as G
import bpy
from mathutils import Matrix

sys.path.insert(0, os.path.join(G.LAN, 'tear', 'v2'))
import render_tear as RT  # noqa: E402
from bl import NB, new_mat, mesh_from_numpy  # noqa: E402

FRONT_Z = 3.35          # windscreen glass plane (the bus nose is at +3.5)
HALF_W = 1.04
FLOOR_Y = 0.62
CEIL_Y = 2.45
WS_BOT, WS_TOP = 1.36, 2.24     # windscreen glass bottom / top (el -15 / +22 from the eye at 1.3 m)
SKY_C = np.array([0.55, CEIL_Y, 2.80])   # skylight centre; round 4: straight above-ahead of the hero seat (az 0, el 45 from the
                                         # seated eye), so at U8 + 7 the wound fills it (r3: 0.42 / 2.75, az -10.5)
SKY_HALF = 0.30


def lin(h):
    return tuple(RT.hexlin(h))


class Shell:
    def __init__(self, t):
        self.t = t
        self.objs = []
        self.mats = {}

    def mat(self, name, albedo, rough=0.5, metal=0.0, emit=None, emit_k=0.0, amb=0.3, spec=None):
        if name in self.mats:
            return self.mats[name]
        m, b = new_mat('Bus_' + name)
        m.blend_method = 'OPAQUE' if hasattr(m, 'blend_method') else None
        bs = b.N('ShaderNodeBsdfPrincipled')
        bs.inputs['Base Color'].default_value = (*albedo, 1)
        bs.inputs['Roughness'].default_value = rough
        bs.inputs['Metallic'].default_value = metal
        if spec is not None:      # round 3 (B9): the frame's rubber / trim must not light up as a neon outline
            bs.inputs['Specular IOR Level'].default_value = spec
        sh = bs.outputs[0]
        # _Udon_CabinAmbient at the gate: moon #232A3A x 0.3 (bible 4.8), as albedo x ambient
        ambc = np.array(lin('#232A3A')) * amb
        e = np.array(albedo) * ambc
        if emit is not None:
            e = e + np.array(emit) * emit_k
        sh = b.add(sh, b.emission(tuple(e)))
        b.out(sh)
        self.mats[name] = m
        return m

    def box(self, name, lo, hi, mat):
        """axis-aligned box in Unity bus coordinates."""
        lo, hi = np.array(lo, float), np.array(hi, float)
        V = np.array([[lo[0], lo[1], lo[2]], [hi[0], lo[1], lo[2]], [hi[0], hi[1], lo[2]], [lo[0], hi[1], lo[2]],
                      [lo[0], lo[1], hi[2]], [hi[0], lo[1], hi[2]], [hi[0], hi[1], hi[2]], [lo[0], hi[1], hi[2]]])
        F = np.array([(0, 3, 2, 1), (4, 5, 6, 7), (0, 1, 5, 4), (2, 3, 7, 6), (1, 2, 6, 5), (0, 4, 7, 3)])
        return self.mesh(name, V, F, mat)

    def mesh(self, name, V, F, mat, smooth=False):
        Vc = G.bus_to_cf(np.asarray(V, float), self.t)
        ob = mesh_from_numpy(name, Vc, np.asarray(F), smooth=smooth)
        ob.data.materials.append(mat)
        self.objs.append(ob)
        return ob

    def quad(self, name, p0, p1, p2, p3, mat, uv=True):
        V = np.array([p0, p1, p2, p3], float)
        Vc = G.bus_to_cf(V, self.t)
        ob = mesh_from_numpy(name, Vc, np.array([(0, 1, 2, 3)]),
                             uvs=[('UVMap', np.array([(0, 0), (1, 0), (1, 1), (0, 1)], float))] if uv else None, smooth=False)
        ob.data.materials.append(mat)
        self.objs.append(ob)
        return ob


def build(t, sh, look, lamps):
    """the shell + cabin lights; lamps = [moon, tear, fill] sun objects (light linking set here)."""
    S = Shell(t)
    # round 8 (tech r4 m10): the placeholder shell must not be the brightest thing in the side frames: those shots
    # darken the paint (look shell_paint); the wipers are no longer a mirror (roughness 0.25 -> 0.55: U8fwd sill glint)
    paint = S.mat('Wall', lin(look.get('shell_paint', '#D9D4C5')), 0.55 if 'shell_paint' not in look else 0.7)
    ceil = S.mat('Ceiling', lin('#E2DDCF'), 0.75)
    rubber = S.mat('Seal', lin('#2B2B2B'), 0.85, spec=0.15)
    dash = S.mat('Dash', lin('#353637'), 0.8, spec=0.25)
    floor = S.mat('Floor', lin('#323634'), 0.78)
    alu = S.mat('Alu', lin('#B8BBBD'), 0.55, 1.0)
    steel = S.mat('Steel', lin('#9A9C9D'), 0.62, 1.0)      # brushed (0.3 mirrored the tear lamp as a hot line)
    vinyl = S.mat('Vinyl', lin('#5A2126'), 0.5)
    linen = S.mat('Linen', lin('#262626'), 0.9, spec=0.2)
    bake = S.mat('Bakelite', lin('#2E2E2E'), 0.45)
    W, fz = HALF_W, FRONT_Z
    if look.get('clean_shell', 0) > 0:
        # round 4 (AD round 3 item 6: 'the bus shell is a PLACEHOLDER: clean framing only'): U8a sees ONE flat dark
        # ceiling with the 0.6 m skylight in a 4 cm dark frame, the light falling in (beam + dust), nothing else
        # the floor spot (L* 60-75) bounces a faint cold light onto the ceiling (Unity: the cabin lightmap)
        dark = S.mat('CeilDark', lin('#16171B'), 0.85, spec=0.1, emit=np.array(lin('#2A2E3A')), emit_k=look.get('ceil_bounce', 0.55))
        sx0, sx1 = SKY_C[0] - SKY_HALF, SKY_C[0] + SKY_HALF
        sz0, sz1 = SKY_C[2] - SKY_HALF, SKY_C[2] + SKY_HALF
        E = 6.0
        for nm, lo, hi in (('RoofA', (-E, CEIL_Y, -E), (E, CEIL_Y + 0.08, sz0)),
                           ('RoofB', (-E, CEIL_Y, sz1), (E, CEIL_Y + 0.08, E)),
                           ('RoofC', (-E, CEIL_Y, sz0), (sx0, CEIL_Y + 0.08, sz1)),
                           ('RoofD', (sx1, CEIL_Y, sz0), (E, CEIL_Y + 0.08, sz1))):
            S.box(nm, lo, hi, dark)
        fw = 0.04
        frame = S.mat('SkyFrameDark', lin('#0E0F12'), 0.6, spec=0.3)
        # round 8 (awe r4 M3 / tech M7: 'no light visibly falls in'): the REVEAL faces of the well catch the wound's light
        # (L* 40-60, brighter toward the glass) and the ceiling round the opening glows faintly (L* 30 -> 20 within 0.5 m)
        if look.get('well_lit', 0.0) > 0:
            mw, bw_ = new_mat('SkyWellLit')
            gz = bw_.sep(bw_.N('ShaderNodeTexCoord').outputs['Generated'])[2]
            wl = bw_.scale(bw_.rgb(tuple(np.array(lin('#9A98B4')))), bw_.math('MULTIPLY', bw_.smooth(gz, 0.0, 1.0, 0.45, 1.0), look['well_lit']))
            bw_.out(bw_.emission(wl))
            frame = mw
        for nm, lo, hi in (('SkyF0', (sx0 - fw, CEIL_Y - 0.02, sz0 - fw), (sx1 + fw, CEIL_Y + 0.12, sz0)),
                           ('SkyF1', (sx0 - fw, CEIL_Y - 0.02, sz1), (sx1 + fw, CEIL_Y + 0.12, sz1 + fw)),
                           ('SkyF2', (sx0 - fw, CEIL_Y - 0.02, sz0), (sx0, CEIL_Y + 0.12, sz1)),
                           ('SkyF3', (sx1, CEIL_Y - 0.02, sz0), (sx1 + fw, CEIL_Y + 0.12, sz1))):
            S.box(nm, lo, hi, frame)
            if look.get('well_lit', 0.0) > 0:      # an unlit glow (Unity: unlit), not a lamp for the rest of the cabin
                S.objs[-1].visible_diffuse = False
                S.objs[-1].visible_glossy = False
        if look.get('well_ring', 0.0) > 0:     # the glow ring on the ceiling round the opening (additive, under it)
            mr, br = new_mat('SkyRing')
            uvr = br.uv('UVMap')
            ur, vr, _ = br.sep(uvr)
            kr = br.math('MULTIPLY', br.math('POWER', vr, 2.5), look['well_ring'])
            br.out(br.add(br.emission(br.scale(br.rgb(tuple(np.array(lin('#5C5F70')))), br.math('POWER', kr, 1.6))), br.transparent()))
            Rr = SKY_HALF + 0.5
            y_ = CEIL_Y - 0.005
            # four trapezoids round the opening; UV v = 0 at the outer edge -> 0.5 at the opening
            for i, ((ax, az), (bx, bz)) in enumerate((((-1, -1), (1, -1)), ((1, -1), (1, 1)), ((1, 1), (-1, 1)), ((-1, 1), (-1, -1)))):
                po = [(SKY_C[0] + ax * Rr, y_, SKY_C[2] + az * Rr), (SKY_C[0] + bx * Rr, y_, SKY_C[2] + bz * Rr)]
                pi = [(SKY_C[0] + bx * (SKY_HALF + fw), y_, SKY_C[2] + bz * (SKY_HALF + fw)), (SKY_C[0] + ax * (SKY_HALF + fw), y_, SKY_C[2] + az * (SKY_HALF + fw))]
                S.quad('SkyRing%d' % i, po[0], po[1], pi[0], pi[1], mr)
                S.objs[-1].visible_shadow = False
                S.objs[-1].visible_diffuse = False
                S.objs[-1].visible_glossy = False
        S.box('Floor', (-E, FLOOR_Y - 0.1, -E), (E, FLOOR_Y, E), floor)
        skylight_spot(S, dict(look, spot=look.get('spot', 1.0)))
        m, b = new_mat('SkyGlassClean')
        tr = b.N('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (0.94, 0.945, 0.94, 1)
        b.out(tr.outputs[0])
        S.quad('SkyGlass', (sx0, CEIL_Y + 0.1, sz0), (sx1, CEIL_Y + 0.1, sz0), (sx1, CEIL_Y + 0.1, sz1), (sx0, CEIL_Y + 0.1, sz1), m)
        S.objs[-1].visible_shadow = False
        _link_lamps(S, lamps)
        return S
    # ---- floor, roof (with the skylight hole), walls below / above the windows, nose
    S.box('Floor', (-W, FLOOR_Y - 0.1, -3.5), (W, FLOOR_Y, 3.5), floor)
    sx0, sx1 = SKY_C[0] - SKY_HALF, SKY_C[0] + SKY_HALF
    sz0, sz1 = SKY_C[2] - SKY_HALF, SKY_C[2] + SKY_HALF
    for nm, lo, hi in (('RoofA', (-W, CEIL_Y, -3.5), (W, CEIL_Y + 0.08, sz0)),
                       ('RoofB', (-W, CEIL_Y, sz1), (W, CEIL_Y + 0.08, fz + 0.2)),
                       ('RoofC', (-W, CEIL_Y, sz0), (sx0, CEIL_Y + 0.08, sz1)),
                       ('RoofD', (sx1, CEIL_Y, sz0), (W, CEIL_Y + 0.08, sz1))):
        S.box(nm, lo, hi, ceil)
    # skylight frame (aluminium, 4 cm) and its well
    fw = 0.04
    for nm, lo, hi in (('SkyF0', (sx0 - fw, CEIL_Y - 0.03, sz0 - fw), (sx1 + fw, CEIL_Y + 0.12, sz0)),
                       ('SkyF1', (sx0 - fw, CEIL_Y - 0.03, sz1), (sx1 + fw, CEIL_Y + 0.12, sz1 + fw)),
                       ('SkyF2', (sx0 - fw, CEIL_Y - 0.03, sz0), (sx0, CEIL_Y + 0.12, sz1)),
                       ('SkyF3', (sx1, CEIL_Y - 0.03, sz0), (sx1 + fw, CEIL_Y + 0.12, sz1))):
        S.box(nm, lo, hi, alu)
    # left wall: solid below the windows, pillars between side windows, header strip above
    for side in (-1, 1):
        x0, x1 = (side * W - 0.06, side * W) if side > 0 else (side * W, side * W + 0.06)
        S.box('WallLow%d' % side, (min(x0, x1), FLOOR_Y, -3.5), (max(x0, x1), 1.30, fz - 0.25), paint)
        S.box('WallTop%d' % side, (min(x0, x1), 2.25, -3.5), (max(x0, x1), CEIL_Y, fz - 0.25), paint)
        zs = np.arange(-3.3, fz - 0.4, 1.12)
        for j, z in enumerate(zs):
            if side > 0 and 2.2 < z < 3.1:
                continue            # the door
            S.box('Pillar%d_%d' % (side, j), (min(x0, x1) - 0.01, 1.30, z), (max(x0, x1) + 0.01, 2.25, z + 0.09), paint)
    # rear wall round the big rear window (glass 1.08..2.33), the rear bench below it
    S.box('RearWallLow', (-W, FLOOR_Y, -3.56), (W, 1.08, -3.48), paint)
    S.box('RearWallTop', (-W, 2.33, -3.56), (W, CEIL_Y, -3.48), paint)
    for side in (-1, 1):
        S.box('RearPost%d' % side, (min(side * W, side * (W - 0.10)), 1.08, -3.56),
              (max(side * W, side * (W - 0.10)), 2.33, -3.48), S.mat('PillarTrim', lin('#3C3B39'), 0.8, spec=0.2))
    S.box('RearSeal', (-W + 0.08, 1.05, -3.50), (W - 0.08, 1.09, -3.44), rubber)
    S.box('RearBench', (-W + 0.05, FLOOR_Y, -3.45), (W - 0.05, 1.05, -2.95), vinyl)
    # the door (right front): opening z 2.30..3.05, frame + glass band 0.9..2.3
    S.box('DoorPostB', (W - 0.07, FLOOR_Y, 2.22), (W, CEIL_Y, 2.30), paint)      # painted (alu glinted in U8side)
    S.box('DoorLow', (W - 0.05, FLOOR_Y, 2.30), (W, 0.92, 3.05), paint)
    S.box('DoorTop', (W - 0.05, 2.28, 2.30), (W, CEIL_Y, 3.05), paint)
    S.box('DoorMid', (W - 0.05, 1.58, 2.30), (W, 1.62, 3.05), rubber)
    # A-pillars behind the wrap-round corners of the windscreen
    for side in (-1, 1):
        xa = side * (W - 0.05)
        S.box('APillar%d' % side, (min(xa, xa + side * 0.06) - 0.03, FLOOR_Y, fz - 0.28),
              (max(xa, xa + side * 0.06) + 0.03, CEIL_Y, fz - 0.12), S.mat('PillarTrim', lin('#3C3B39'), 0.8, spec=0.2))
    # nose below the windscreen + dashboard (sloping top at WS_BOT) + header with the destination blind
    S.box('Nose', (-W, FLOOR_Y, fz), (W, WS_BOT, fz + 0.15), paint)
    V = np.array([[-W, WS_BOT - 0.02, fz + 0.02], [W, WS_BOT - 0.02, fz + 0.02], [W, WS_BOT - 0.06, fz - 0.55],
                  [-W, WS_BOT - 0.06, fz - 0.55], [-W, 1.05, fz - 0.62], [W, 1.05, fz - 0.62]])
    S.mesh('DashTop', V, np.array([(0, 1, 2, 3), (3, 2, 5, 4)]), dash)
    S.box('DashBody', (-W, FLOOR_Y, fz - 0.62), (W, 1.05, fz), dash)
    S.box('Header', (-W, WS_TOP, fz - 0.22), (W, CEIL_Y, fz + 0.1), linen)
    S.box('HeaderLip', (-W, WS_TOP - 0.03, fz - 0.24), (W, WS_TOP + 0.01, fz + 0.02), rubber)
    # windscreen seal (a thin frame round the glass) + the wiper-free glass
    # round 2 (critique minor): ONE windscreen pane (no central mullion beside the wound)
    for nm, lo, hi in (('SealB', (-W, WS_BOT - 0.03, fz - 0.02), (W, WS_BOT + 0.02, fz + 0.03)),
                       ('SealT', (-W, WS_TOP - 0.02, fz - 0.02), (W, WS_TOP + 0.03, fz + 0.03))):
        S.box(nm, lo, hi, rubber)
    # parked wipers (outside the glass, along its bottom edge): dark arms whose top edge catches the wound's light
    wip = S.mat('Wiper', lin('#2A2B2C'), 0.55, 1.0)
    for x0, x1 in ((-0.95, -0.12), (0.05, 0.86)):
        V = np.array([[x0, WS_BOT + 0.035, fz + 0.035], [x1, WS_BOT + 0.075, fz + 0.035], [x1, WS_BOT + 0.095, fz + 0.04],
                      [x0, WS_BOT + 0.05, fz + 0.04]])
        S.mesh('Wiper%d' % int(x0 > 0), V, np.array([(0, 1, 2, 3)]), wip)
        S.box('WiperArm%d' % int(x0 > 0), (x0 - 0.01, WS_BOT + 0.02, fz + 0.03), (x0 + 0.02, WS_BOT + 0.05, fz + 0.06), wip)
    # rear-view mirror (top centre): a dark silhouette on its stalk
    # round 3 (B9): a small mirror on a stalk (the 32 cm slab read as a projector)
    S.box('MirrorStalk', (-0.010, WS_TOP - 0.07, fz - 0.21), (0.010, WS_TOP + 0.02, fz - 0.19), bake)
    S.box('Mirror', (-0.11, WS_TOP - 0.115, fz - 0.235), (0.11, WS_TOP - 0.065, fz - 0.215), bake)
    S.box('MirrorRim', (-0.112, WS_TOP - 0.117, fz - 0.238), (0.112, WS_TOP - 0.063, fz - 0.236), alu)
    # two-pane windscreen: a 40 mm centre post (bible 4.6 / critique B9), dark rubber
    S.box('CentrePost', (-0.02, WS_BOT, fz - 0.035), (0.02, WS_TOP, fz + 0.02), rubber)
    # the destination blind 「蓝白」 (bible 4.7): black linen, cut-out letters lit from behind, MIRRORED from inside
    destination_blind(S, fz)
    # driver's seat (left front) + wheel (thin bakelite ring) + the radio (warm dial)
    S.box('DriverSeat', (-0.85, FLOOR_Y + 0.35, 1.95), (-0.25, 1.62, 2.15), vinyl)
    S.box('DriverSeatBase', (-0.85, FLOOR_Y, 2.0), (-0.25, FLOOR_Y + 0.45, 2.55), vinyl)
    wheel(S, (-0.55, 1.28, fz - 0.55), 0.24, bake)
    # the radio sits IN the dashboard face (only the little warm dial window glows: the cabin's one warm light)
    radio_mat = S.mat('RadioDial', (0.05, 0.03, 0.02), 0.5, 0.0, emit=np.array(lin('#FF9A3C')) * 0.55, emit_k=1.0)
    S.box('Radio', (0.06, 1.17, fz - 0.635), (0.24, 1.25, fz - 0.60), S.mat('RadioCase', lin('#3A2A20'), 0.45))
    S.box('RadioDial', (0.09, 1.195, fz - 0.64), (0.21, 1.225, fz - 0.632), radio_mat)
    # stanchion by the door (grab pole) and the front handrail of the hero seat
    pole(S, (0.95, 2.28), steel)
    # tube lights (two rows, dim: base E 0.25 at the gate, the tubes are dying)
    tubes(S, look)
    if look.get('spot', 0) > 0:
        skylight_spot(S, look)
    # glass: windscreen (flat front + wrap-round corners), door glass, side windows, skylight
    glass(S, look)
    objs = S.objs
    _link_lamps(S, lamps)
    return S


def _link_lamps(S, lamps):
    # light linking: the tear light is shadowed only by the shell (Unity: no shadows; the skylight spot is a card
    # there); the fill-from-below never lights the cabin
    objs = S.objs
    moon, tear_l, fill = lamps
    col = bpy.data.collections.new('BusShell')
    for o in objs:
        col.objects.link(o)
    # the tube lights light the cabin only (Unity: _CabinTubeLM, a baked cabin-only lightmap; they never reach the
    # tentacles: without this their area-light speculars painted pale sheens on the near arms through the glass)
    for lo in [o for o in bpy.context.scene.objects if o.type == 'LIGHT' and o.name.startswith('TubeL')]:
        lo.light_linking.receiver_collection = col
        lo.visible_glossy = False          # no lamp images mirrored in the glass / skin
    # nor does the tentacles' wet skin mirror the cabin (Unity: reflection probes of the sky world only)
    for o in objs:
        o.visible_glossy = False
    try:
        tear_l.data.use_shadow = True
        tear_l.light_linking.blocker_collection = col
    except Exception as e:
        print('shadow linking failed', e)
    ex = bpy.data.collections.new('BusNoFill')
    for o in objs:
        ex.objects.link(o)
    for co in ex.collection_objects:
        co.light_linking.link_state = 'EXCLUDE'
    rc = fill.light_linking.receiver_collection
    if rc is None:
        fill.light_linking.receiver_collection = ex
    else:
        for o in objs:
            rc.objects.link(o)
        for co in rc.collection_objects:
            co.light_linking.link_state = 'EXCLUDE'
    return objs


BLIND_TEX = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'Textures', 'Bus_DestinationBlind_1024x256.png')
BLIND_FONT = os.path.join(G.LAN, 'work_sign', 'fonts', 'SourceHanSansCN-Heavy.otf')


def blind_texture():
    """1024 x 256 RGBA: R = the letters' light mask (mirrored 「蓝白」, Source Han Sans Heavy, 140 mm on a 0.90 x 0.22 m
    blind), G = the linen weave (0..1), B = 0, A = 1. Unity: Lanbai/Cabin emission = mask x #F2F5F0 x 2.5 x
    _Udon_CabinLightmap; base = #262626 linen x weave."""
    if os.path.exists(BLIND_TEX):
        return BLIND_TEX
    from PIL import Image, ImageDraw, ImageFont, ImageOps, ImageFilter
    W_, H_ = 1024, 256
    m = Image.new('L', (W_, H_), 0)
    d = ImageDraw.Draw(m)
    px_m = W_ / 0.90
    f = ImageFont.truetype(BLIND_FONT, int(0.140 * px_m * 1.12))
    bb = d.textbbox((0, 0), '蓝白', font=f)
    tw, th = bb[2] - bb[0], bb[3] - bb[1]
    d.text(((W_ - tw) / 2 - bb[0], (H_ - th) / 2 - bb[1]), '蓝白', font=f, fill=255)
    m = ImageOps.mirror(m).filter(ImageFilter.GaussianBlur(1.2))
    rng = np.random.default_rng(5)
    weave = 0.75 + 0.25 * (np.sin(np.arange(W_)[None, :] * 1.9) * np.sin(np.arange(H_)[:, None] * 2.1)) + 0.05 * rng.standard_normal((H_, W_))
    img = np.stack([np.asarray(m, np.float32) / 255.0, np.clip(weave, 0, 1), np.zeros((H_, W_)), np.ones((H_, W_))], -1)
    os.makedirs(os.path.dirname(BLIND_TEX), exist_ok=True)
    Image.fromarray((img * 255 + 0.5).astype(np.uint8), 'RGBA').save(BLIND_TEX)
    return BLIND_TEX


def destination_blind(S, fz):
    from bl import load_img
    img = load_img(blind_texture(), 'Non-Color', 'STRAIGHT')
    m, b = new_mat('Bus_Blind')
    tx = b.tex(img, b.uv('UVMap'))
    r_, g_, _ = b.sepc(tx.outputs['Color'])
    lin_ = np.array(lin('#262626'))
    # round 4 (AD round 3 item 4: 'from inside it still reads 白蓝'): the INSIDE face is BLANK - a dark lightbox back
    # (#0A0C12) with a faint UNIFORM glow (#1A1E28, L* ~9), weave contrast <= 2 L*, no glyphs. The outside face keeps
    # 「蓝白」 for Acts 1 / 12 (the texture's R channel, read only by the outside material; README §0).
    # round 8 (tech r4 m13): x 2.3 -> screen L* ~7 under the S4 grade (was ~3); README §8.5: screen target L* 6-8
    base = b.scale(b.rgb(tuple(np.array(lin('#1A1E28')) * 2.3)), b.math('ADD', 0.96, b.math('MULTIPLY', g_, 0.04)))
    b.out(b.emission(base))
    # behind the top strip of the windscreen's left pane (as on a real bus: read from outside through the glass;
    # from the hero seat it hangs at el +20..+23, az -42..-11: left of the wound, never over it)
    x0, x1 = -0.74, -0.02
    y0, y1 = WS_TOP - 0.175, WS_TOP - 0.005
    z = fz - 0.06
    S.quad('DestinationBlind', (x0, y0, z), (x1, y0, z), (x1, y1, z), (x0, y1, z), m)      # u 0 at the viewer's left: the texture is already mirrored


def wheel(S, c, r, mat, n=40, tube=0.018):
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    tilt = math.radians(55)
    pts = []
    for a in ang:
        p = np.array([r * math.cos(a), r * math.sin(a) * math.cos(tilt), r * math.sin(a) * math.sin(tilt)])
        pts.append(np.array(c) + p)
    V, F = [], []
    m = 8
    for i, p in enumerate(pts):
        q = pts[(i + 1) % n]
        tng = (q - p) / np.linalg.norm(q - p)
        nrm = np.cross(tng, [0, 1, 0]); nrm /= np.linalg.norm(nrm) + 1e-9
        bn = np.cross(tng, nrm)
        for j in range(m):
            b = 2 * np.pi * j / m
            V.append(p + tube * (math.cos(b) * nrm + math.sin(b) * bn))
    for i in range(n):
        for j in range(m):
            a0 = i * m + j
            a1 = i * m + (j + 1) % m
            b0 = ((i + 1) % n) * m + j
            b1 = ((i + 1) % n) * m + (j + 1) % m
            F.append((a0, a1, b1, b0))
    S.mesh('Wheel', np.array(V), np.array(F), mat, smooth=True)
    S.box('WheelColumn', (c[0] - 0.02, FLOOR_Y + 0.3, c[2] + 0.02), (c[0] + 0.02, c[1] - 0.05, c[2] + 0.08), mat)


def pole(S, xz, mat, r=0.016, n=12):
    x, z = xz
    ang = np.linspace(0, 2 * np.pi, n, endpoint=False)
    V = [(x + r * math.cos(a), y, z + r * math.sin(a)) for y in (FLOOR_Y, CEIL_Y) for a in ang]
    F = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    S.mesh('Pole', np.array(V), np.array(F), mat, smooth=True)


def tubes(S, look):
    k = look.get('tubes', 1.0)
    em_col = np.array(lin('#E7FEFF')) * 2 ** 1.03 * 0.30 * k     # lamp cover fill x the dying-light factor
    for side in (-0.62, 0.62):
        zs = np.linspace(-2.6, 2.3, 5) if side < 0 else np.linspace(-2.6, 1.4, 4)   # right row stops short of the skylight
        for j, z in enumerate(zs):
            m, b = new_mat('TubeCover_%d_%d' % (int(side > 0), j))
            b.out(b.emission(tuple(em_col)))
            S.box('Tube_%d_%d' % (int(side > 0), j), (side - 0.06, CEIL_Y - 0.05, z - 0.6), (side + 0.06, CEIL_Y - 0.005, z + 0.6), m)
            # the tube's light (area lamp, pointing down); base E ~0.25 at the seat
            ld = bpy.data.lights.new('TubeL', 'AREA')
            ld.shape = 'RECTANGLE'
            ld.size, ld.size_y = 0.12, 1.2
            ld.energy = 7.0 * k
            ld.color = tuple(np.array(lin('#E4F1F3')) / max(lin('#E4F1F3')))
            lo = bpy.data.objects.new('TubeL', ld)
            bpy.context.scene.collection.objects.link(lo)
            lo.location = tuple(G.bus_to_cf(np.array([side, CEIL_Y - 0.06, z]), S.t))
            lo.rotation_euler = (0, 0, 0)          # area lights point down -Z (CF z = Unity y)
            ld.use_shadow = True


def glass(S, look):
    """BusGlass: multiply #E9EFEA, alpha ~0.06, grime at the corners; faint cabin reflection."""
    m, b = new_mat('Glass')
    uvn = b.uv('UVMap')
    u, v, _ = b.sep(uvn)
    edge = b.math('MINIMUM', b.math('MINIMUM', u, b.math('SUBTRACT', 1.0, u)), b.math('MINIMUM', v, b.math('SUBTRACT', 1.0, v)))
    grime = b.math('MULTIPLY', b.smooth(edge, 0.06, 0.0), 0.10)
    nz = b.N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 7.0; nz.inputs['Detail'].default_value = 6.0
    b.L(uvn, nz.inputs['Vector'])
    grime = b.math('MULTIPLY', grime, b.math('ADD', 0.4, nz.outputs['Fac']))
    grime = b.math('ADD', grime, b.math('MULTIPLY', b.smooth(nz.outputs['Fac'], 0.62, 0.8), 0.012))
    tr = b.N('ShaderNodeBsdfTransparent'); tr.inputs['Color'].default_value = (0.94, 0.945, 0.94, 1)   # Unity BusGlass: alpha 0.06 blend -> ~94 % through
    gl = b.N('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = look.get('glass_rough', 0.3)   # 0.06 mirrored the tear lamp as a flare
    fres = b.N('ShaderNodeFresnel'); fres.inputs['IOR'].default_value = 1.5
    clear = b.mixs(b.math('MULTIPLY', fres.outputs[0], 0.12), tr.outputs[0], gl.outputs[0])
    # dried rain streaks (critique minor): thin, mostly vertical runs, lit by the wound (diffuse dirt)
    sk = b.N('ShaderNodeMapping'); sk.inputs['Scale'].default_value = (90.0, 6.0, 1.0)
    b.L(uvn, sk.inputs['Vector'])
    ns = b.N('ShaderNodeTexNoise'); ns.inputs['Scale'].default_value = 1.0; ns.inputs['Detail'].default_value = 4.0
    b.L(sk.outputs['Vector'], ns.inputs['Vector'])
    streak = b.math('MULTIPLY', b.smooth(ns.outputs['Fac'], 0.60, 0.72), b.math('MULTIPLY', b.smooth(v, 0.95, 0.45), look.get('rain', 0.10)))
    grime = b.math('ADD', grime, streak)
    dirt = b.N('ShaderNodeBsdfDiffuse'); dirt.inputs['Color'].default_value = (*lin('#6D6A60'), 1)
    sh = b.mixs(grime, clear, dirt.outputs[0])
    b.out(sh)
    W, fz = HALF_W, FRONT_Z
    S.quad('Windscreen', (-W + 0.1, WS_BOT, fz), (W - 0.1, WS_BOT, fz), (W - 0.1, WS_TOP, fz - 0.02), (-W + 0.1, WS_TOP, fz - 0.02), m)
    for side in (-1, 1):       # wrap-round corners
        x0 = side * (W - 0.1)
        S.quad('WsCorner%d' % side, (x0, WS_BOT, fz), (side * W, WS_BOT, fz - 0.14), (side * W, WS_TOP, fz - 0.16),
               (x0, WS_TOP, fz - 0.02), m)
    S.quad('DoorGlass', (W - 0.02, 0.95, 2.31), (W - 0.02, 0.95, 3.04), (W - 0.02, 2.27, 3.04), (W - 0.02, 2.27, 2.31), m)
    for side in (-1, 1):
        S.quad('SideGlass%d' % side, (side * (W - 0.03), 1.30, -3.4), (side * (W - 0.03), 1.30, fz - 0.3),
               (side * (W - 0.03), 2.25, fz - 0.3), (side * (W - 0.03), 2.25, -3.4), m)
    sx0, sx1 = SKY_C[0] - SKY_HALF, SKY_C[0] + SKY_HALF
    sz0, sz1 = SKY_C[2] - SKY_HALF, SKY_C[2] + SKY_HALF
    S.quad('SkyGlass', (sx0, CEIL_Y + 0.1, sz0), (sx1, CEIL_Y + 0.1, sz0), (sx1, CEIL_Y + 0.1, sz1), (sx0, CEIL_Y + 0.1, sz1), m)
    S.quad('RearGlass', (-W + 0.1, 1.09, -3.47), (W - 0.1, 1.09, -3.47), (W - 0.1, 2.33, -3.47), (-W + 0.1, 2.33, -3.47), m)
    for o in S.objs[-8:]:
        if o.name.endswith('Glass') or 'Glass' in o.name or 'Windscreen' in o.name or 'WsCorner' in o.name:
            o.visible_shadow = False


def skylight_spot_quad(t):
    """the skylight's four corners projected along the light from the wound's core onto the floor (Unity bus
    coordinates): bible 4.8 (Udon does exactly this each frame; the JSON carries samples per t)."""
    core = G.tear_core_cf(t)
    sx0, sx1 = SKY_C[0] - SKY_HALF, SKY_C[0] + SKY_HALF
    sz0, sz1 = SKY_C[2] - SKY_HALF, SKY_C[2] + SKY_HALF
    out = []
    for (x, z) in ((sx0, sz0), (sx1, sz0), (sx1, sz1), (sx0, sz1)):
        p = np.array([x, CEIL_Y + 0.1, z])
        pc = G.bus_to_cf(p, t)
        d = pc - core
        d = d / np.linalg.norm(d)
        # CF -> bus: x same, y_cf -> z_bus, z_cf -> y_bus
        db = np.array([d[0], d[2], d[1]])
        k = (FLOOR_Y + 0.003 - p[1]) / db[1]
        out.append(p + db * k)
    return np.array(out)


def skylight_spot(S, look):
    """the light spot on the floor + its beam through the cabin dust (additive cards; Unity: UnlitCardHDR additive,
    white card reads #99A1AD, display luma 170-200, #E2E8F3, 3 cm soft edge)."""
    q = skylight_spot_quad(S.t)
    # round 3 (awe B9.3): the wound is far larger than the skylight seen from the floor, so the spot is the aperture
    # convolved with the INVERTED wound: a soft lens, longer along the aisle, with 12-20 cm soft edges, and the
    # floor's studs visible in it. The card is drawn 0.22 m larger than the projected aperture (the penumbra).
    c0 = q.mean(0)
    qe = np.array([c0 + (p - c0) * 1.0 + (p - c0) / np.linalg.norm(p - c0) * 0.22 for p in q])
    m, b = new_mat('SkySpot')
    uvn = b.uv('UVMap')
    u, v, _ = b.sep(uvn)
    du = b.math('MULTIPLY', b.math('SUBTRACT', u, 0.5), 2.0)
    dv = b.math('MULTIPLY', b.math('SUBTRACT', v, 0.5), 2.0)
    box = b.math('MULTIPLY', b.smooth(b.math('ABSOLUTE', du), 1.0, 0.55), b.smooth(b.math('ABSOLUTE', dv), 1.0, 0.55))
    rr = b.math('ADD', b.math('POWER', b.math('DIVIDE', du, 0.80), 2.0), b.math('POWER', b.math('DIVIDE', dv, 1.05), 2.0))
    lens = b.math('ADD', 0.35, b.math('MULTIPLY', b.smooth(rr, 1.0, 0.25), 0.65))      # the inverted lens, faint
    geo = b.N('ShaderNodeNewGeometry')
    P = geo.outputs['Position']
    px, py, _ = b.sep(P)
    gx = b.math('SUBTRACT', b.math('FRACT', b.math('DIVIDE', px, 0.05)), 0.5)
    gy = b.math('SUBTRACT', b.math('FRACT', b.math('DIVIDE', py, 0.05)), 0.5)
    stud = b.smooth(b.math('SQRT', b.math('ADD', b.math('MULTIPLY', gx, gx), b.math('MULTIPLY', gy, gy))), 0.25, 0.18)
    e = b.math('MULTIPLY', b.math('MULTIPLY', box, lens), b.math('ADD', 0.944, b.math('MULTIPLY', stud, 0.056)))   # round 8 (m1): studs x 0.4 (a speaker grille)
    col = np.array(lin('#E2E8F3')) * look.get('spot_gain', 1.15) * look.get('spot', 1.0)      # round 4 (m7): luma 170-200
    b.out(b.add(b.emission(b.scale(b.rgb(tuple(col)), e)), b.transparent()))
    S.quad('SkySpot', qe[0], qe[1], qe[2], qe[3], m)
    # the beam: the prism between the skylight and the spot, additive, brightest near the floor
    mb, bb = new_mat('SkyBeam')
    uvb = bb.uv('UVMap')
    ub, vb, _ = bb.sep(uvb)
    k = bb.math('MULTIPLY', bb.math('MULTIPLY', bb.smooth(ub, 0.0, 0.3), bb.smooth(ub, 1.0, 0.7)), bb.math('ADD', 0.4, bb.math('MULTIPLY', vb, 0.6)))
    bcol = np.array(lin('#E2E8F3')) * look.get('beam_gain', 0.035) * look.get('spot', 1.0)
    bb.out(bb.add(bb.emission(bb.scale(bb.rgb(tuple(bcol)), k)), bb.transparent()))
    sx0, sx1 = SKY_C[0] - SKY_HALF, SKY_C[0] + SKY_HALF
    sz0, sz1 = SKY_C[2] - SKY_HALF, SKY_C[2] + SKY_HALF
    top = np.array([[sx0, CEIL_Y + 0.05, sz0], [sx1, CEIL_Y + 0.05, sz0], [sx1, CEIL_Y + 0.05, sz1], [sx0, CEIL_Y + 0.05, sz1]])
    for i in range(4):
        j = (i + 1) % 4
        S.quad('SkyBeam%d' % i, q[i], q[j], top[j], top[i], mb)
    # dust in the beam (300 motes, 3-6 mm, bright only inside the beam)
    if look.get('dust_gain', 1.2) <= 0:          # round 8 (U8a): no dust at all (specks over the shell / the white)
        for o in S.objs[-6:]:
            o.visible_shadow = False
        return
    rng = np.random.default_rng(4)
    md, bd = new_mat('Dust')
    bd.out(bd.emission(tuple(np.array(lin('#E2E8F3')) * look.get('dust_gain', 1.2) * look.get('spot', 1.0))))
    V, F = [], []
    for n in range(300):
        a, c = rng.random(), rng.random()
        f = rng.random() ** 0.45            # round 4 (M5): denser near the skylight, only inside the beam
        lo = q[0] + (q[1] - q[0]) * a + (q[3] - q[0]) * c
        hi = top[0] + (top[1] - top[0]) * a + (top[3] - top[0]) * c
        p = lo + (hi - lo) * f
        r = rng.uniform(0.0007, 0.0014)     # round 4: <= 1.5 px (3-6 mm read as a starfield)
        k0 = len(V)
        V += [p + np.array([r, 0, 0]), p + np.array([-r, 0, 0]), p + np.array([0, r, 0]), p + np.array([0, 0, r])]
        F += [(k0, k0 + 2, k0 + 3), (k0 + 1, k0 + 3, k0 + 2), (k0, k0 + 1, k0 + 2), (k0, k0 + 3, k0 + 1)]
    S.mesh('Dust', np.array(V), np.array(F), md)
    for o in S.objs[-7:]:
        o.visible_shadow = False
