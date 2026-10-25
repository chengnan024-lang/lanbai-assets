# -*- coding: utf-8 -*-
"""参考场景：第 2 幕（夜路）、第 11 幕（假醒）、第 1 幕（站灯），全部在“Unity 单位”下渲（lk_bpy 的约定），
从主座位眼位（车坐标 (0.55, 1.70, 2.05)，Unity x 右 / y 上 / z 前 → Blender (x, z, y)）。

车固定在原点，世界往后流：时间 t 的路程 s_bus(t)（圣经 §6·1→2：U1 17.50 起 12 s smoothstep 到 10 m/s）。
路灯在路程 s = 20 + 32k（k = 0..4，§6·2），杆在左侧路肩外 x = −10.40（灯头中心离眼睛水平 ≥ 9.4 m、三维 ≥ 10.5 m）。
usage: python lk_scene.py <act> <out.exr> W H SPP [key=value ...]
  act = act2 | act11 | stop | detail
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import lk_bpy as B  # noqa: E402
import lk_geom as G  # noqa: E402
import lk_mats as MT  # noqa: E402

REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
TEX = os.environ.get('LK_TEX', os.path.join(REPO, 'Lamps', 'Textures'))
GROUND = os.environ.get('LK_GROUND', '/tmp/lk/ground')
ROAD_MASK = os.path.join(REPO, 'Rain', 'Textures', 'Stop', 'Road_WetMask_2048x512.png')

EYE = (0.55, 2.05, 1.70)            # Blender (x, y fwd, z up) = Unity (0.55, 1.70, 2.05)
POLE_X = -10.40
LAMP_S = [20.0 + 32.0 * k for k in range(5)]
ROAD_X = (-4.9, 1.6)
SODIUM = MT.hexlin('#FF941D')        # 2050 K light colour (bible §4.8)
HEAD_FILL = tuple(np.array(MT.hexlin('#FF7B00')) * 2 ** 1.14)      # S2 "钠灯灯头经过" fill (calib §B)
HEADLIGHT = MT.hexlin('#FFC47A')
UPLIGHT = 0.06                                # refractor spill above the horizon (lights the crossarm, the wires)
HALO_R, HALO_K, HALO_P = 3.0, 0.22, 0.0      # sodium halo card: radius m, peak (x the light colour), (unused)


def s_bus(t):
    """Road distance (m) the world has moved by time t (bible §6·1→2, v2.1 E7: 0 -> 10 m/s, 12 s smoothstep from U1)."""
    t0, dur, v = 17.50, 12.0, 10.0
    if t <= t0:
        return 0.0
    u = min((t - t0) / dur, 1.0)
    s = v * dur * (u ** 3 - u ** 4 / 2)
    if t > t0 + dur:
        s += v * (t - t0 - dur)
    return s


def link(ob):
    return ob


def make_mats(wet):
    mats = {k: MT.lampkit(k, TEX, wet) for k in MT.KIT}
    return mats


def lamp_standard(name, y, mats, glow_mat_fn, lod=0, flip=None, wire_tops=None, pole_mat='M_Lamps_Concrete'):
    """One act-2 standard at road position y (Blender world). flip: None, or dict(sea_z, head_bottom) for act 11."""
    d, info = G.road_lamp(lod)
    if pole_mat != 'M_Lamps_Concrete':
        d[pole_mat] = d.pop('M_Lamps_Concrete'); d[pole_mat].mat = pole_mat
    arc_parts = d.pop('M_Lamps_ArcTube', None)
    # world transform: the pole at (POLE_X, y), +X toward the road
    if flip is None:
        M = G.trans(POLE_X, y, 0.0)
    else:
        # act 11: the same standard hung upside down: z -> head_bottom + (6.5 + 7) ... mirror about z = (6.52 + flip.head_bottom) / 2
        zc = info['refractor_low'] + flip['head_bottom']
        M = G.trans(POLE_X, y, zc) @ np.diag([1.0, 1.0, -1.0, 1.0])
    for p in d.values():
        p.transform(M)
        if flip is not None:
            p.f = [tuple(reversed(f)) for f in p.f]
            p.uv = [list(reversed(u)) for u in p.uv]
    # glow material needs the arc in world space
    ac = np.array(info['arc_centre'], float)
    a = ac + np.array([-0.06 * math.cos(G.ARM_TILT), 0, -0.06 * math.sin(G.ARM_TILT)])
    b = ac + np.array([0.06 * math.cos(G.ARM_TILT), 0, 0.06 * math.sin(G.ARM_TILT)])
    A = (M @ np.r_[a, 1])[:3]; Bp = (M @ np.r_[b, 1])[:3]
    gm = glow_mat_fn(name + '_glow', A, Bp)
    allm = dict(mats); allm['M_Lamps_Refractor'] = gm
    ob = B.obj_from_parts(name, d, allm)
    centre = (A + Bp) / 2
    tops = [(M @ np.r_[np.asarray(t, float), 1])[:3] for t in info['insulator_tops']]
    return ob, centre, tops, info


def spot(name, loc, power_unity, col, size_deg=150.0, blend=0.6, rot=(0, 0, 0), radius=0.03, shadow=True):
    l = bpy.data.lights.new(name, 'SPOT')
    l.energy = B.unity_point_power(power_unity)
    l.color = col
    l.spot_size = math.radians(size_deg)
    l.spot_blend = blend
    l.shadow_soft_size = radius
    l.use_shadow = shadow
    ob = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    ob.rotation_euler = rot
    return ob


def cobra_light(name, loc, peak_I, col, radius=0.06, rot_z=0.0):
    """A cobra-head distribution (IESNA type II-ish, medium cutoff), as a Cycles point light with a direction-driven
    strength: I(theta) relative to the peak, theta from the nadir:
        0.55 at the nadir, rising to 1.0 at 68 deg, falling to 0.10 at 85 deg and 0.03 above the horizon (uplight).
    Wider along the road (y) than across it (x): the across-road term is x0.75 beyond 45 deg.
    peak_I in Unity units (E = I / d^2 at the peak direction)."""
    l = bpy.data.lights.new(name, 'POINT')
    l.energy = B.unity_point_power(peak_I)
    l.color = col
    l.shadow_soft_size = radius
    l.use_nodes = True
    nt = l.node_tree
    em = nt.nodes.get('Emission')
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(tc.outputs['Normal'], sep.inputs[0])
    ac = nt.nodes.new('ShaderNodeMath'); ac.operation = 'ARCCOSINE'
    neg = nt.nodes.new('ShaderNodeMath'); neg.operation = 'MULTIPLY'; neg.inputs[1].default_value = -1.0
    nt.links.new(sep.outputs[2], neg.inputs[0]); nt.links.new(neg.outputs[0], ac.inputs[0])
    deg = nt.nodes.new('ShaderNodeMath'); deg.operation = 'MULTIPLY'; deg.inputs[1].default_value = 180 / math.pi
    nt.links.new(ac.outputs[0], deg.inputs[0])
    curve = nt.nodes.new('ShaderNodeFloatCurve')
    cm = curve.mapping
    cm.clip_max_x = 180; cm.clip_max_y = 1
    pts = [(0, 0.55), (40, 0.75), (68, 1.0), (78, 0.55), (85, 0.10), (95, 0.03), (180, 0.02)]
    c = cm.curves[0]
    while len(c.points) < len(pts):
        c.points.new(0, 0)
    for p, (x, y) in zip(c.points, pts):
        p.location = (x / 180.0, y)
    cm.clip_max_x = 1.0
    cm.update()
    sc_ = nt.nodes.new('ShaderNodeMath'); sc_.operation = 'DIVIDE'; sc_.inputs[1].default_value = 180.0
    nt.links.new(deg.outputs[0], sc_.inputs[0]); nt.links.new(sc_.outputs[0], curve.inputs['Value'])
    nt.links.new(curve.outputs[0], em.inputs['Strength'])
    ob = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc; ob.rotation_euler = (0, 0, rot_z)
    return ob


def point(name, loc, power_unity, col, radius=0.03):
    l = bpy.data.lights.new(name, 'POINT')
    l.energy = B.unity_point_power(power_unity)
    l.color = col
    l.shadow_soft_size = radius
    ob = bpy.data.objects.new(name, l)
    bpy.context.scene.collection.objects.link(ob)
    ob.location = loc
    return ob


def plane(name, x0, x1, y0, y1, z, mat, nx=1, ny=1):
    me = bpy.data.meshes.new(name)
    xs = np.linspace(x0, x1, nx + 1); ys = np.linspace(y0, y1, ny + 1)
    V = [(x, y, z) for y in ys for x in xs]
    F = [(j * (nx + 1) + i, j * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i + 1, (j + 1) * (nx + 1) + i) for j in range(ny) for i in range(nx)]
    me.from_pydata(V, [], F); me.update()
    me.materials.append(mat)
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def wire(name, pts, mat, r=0.0055):
    cu = bpy.data.curves.new(name, 'CURVE')
    cu.dimensions = '3D'
    cu.bevel_depth = r
    cu.bevel_resolution = 2
    sp = cu.splines.new('POLY')
    sp.points.add(len(pts) - 1)
    for i, p in enumerate(pts):
        sp.points[i].co = (*p, 1.0)
    cu.materials.append(mat)
    ob = bpy.data.objects.new(name, cu)
    bpy.context.scene.collection.objects.link(ob)
    return ob


def box_obj(name, c, half, mat):
    p = G.Part('x'); G.box(p, c, half)
    me = bpy.data.meshes.new(name); me.from_pydata(p.v, [], p.f); me.update(); me.materials.append(mat)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    return ob


# ---------------------------------------------------------------------------------------------- the cabin frame
def cabin(tube_on=1.0, door_open=True):
    """A plain stand-in for the bus interior (the real cabin is the director's), built from the bible's angular
    spec from the hero eye: windscreen az -50..+25 / el -15..+18, door glass +30..+65, right windows +60..+150,
    skylight az -5..+23 / el +40..+68. Blender coords (x right, y fwd, z up)."""
    m_wall = MT.simple('Cab_Wall', '#D9D4C5', 0.55)
    m_ceil = MT.simple('Cab_Ceiling', '#E2DDCF', 0.75)
    m_seat = MT.simple('Cab_Seat', '#5A2126', 0.45)
    m_floor = MT.simple('Cab_Floor', '#323634', 0.78)
    m_dash = MT.simple('Cab_Dash', '#353637', 0.7)
    m_frame = MT.simple('Cab_Frame', '#B8BBBD', 0.5, metal=1.0)
    m_rubber = MT.simple('Cab_Rubber', '#2B2B2B', 0.7)
    m_glass = MT.glass('Cab_Glass', refl=1.0)
    m_tube = MT.emissive('Cab_Tube', MT.hexlin('#E7FEFF'), 2.0 ** 1.03 * tube_on)
    XW = 1.12; Y0 = -5.2; YF = 3.35; ZF = 0.62; ZC = 2.45
    objs = []
    # floor, ceiling (with the skylight hole), back wall
    objs.append(box_obj('cab_floor', (0, (Y0 + YF) / 2, ZF - 0.05), (XW, (YF - Y0) / 2, 0.05), m_floor))
    sky_c = (0.55, 2.80); sky_h = 0.30
    # ceiling split around the skylight
    objs.append(box_obj('cab_ceil_a', (0, (Y0 + sky_c[1] - sky_h) / 2, ZC + 0.03), (XW, (sky_c[1] - sky_h - Y0) / 2, 0.03), m_ceil))
    objs.append(box_obj('cab_ceil_b', (0, (sky_c[1] + sky_h + YF) / 2, ZC + 0.03), (XW, (YF - sky_c[1] - sky_h) / 2, 0.03), m_ceil))
    objs.append(box_obj('cab_ceil_c', ((-XW + sky_c[0] - sky_h) / 2, sky_c[1], ZC + 0.03), ((sky_c[0] - sky_h + XW) / 2, sky_h, 0.03), m_ceil))
    objs.append(box_obj('cab_ceil_d', ((XW + sky_c[0] + sky_h) / 2, sky_c[1], ZC + 0.03), ((XW - sky_c[0] - sky_h) / 2, sky_h, 0.03), m_ceil))
    objs.append(box_obj('cab_back', (0, Y0 - 0.05, (ZF + ZC) / 2), (XW, 0.05, (ZC - ZF) / 2), m_wall))
    # windscreen: frame below 1.36, header above 2.24; glass in between
    objs.append(box_obj('cab_dash', (0, YF - 0.30, 1.05), (XW, 0.30, 0.30), m_dash))
    objs.append(box_obj('cab_front_low', (0, YF + 0.04, (ZF + 1.36) / 2), (XW, 0.04, (1.36 - ZF) / 2), m_wall))
    objs.append(box_obj('cab_header', (0, YF + 0.04, (2.24 + ZC) / 2 + 0.03), (XW, 0.04, (ZC - 2.24) / 2 + 0.03), m_wall))
    objs.append(box_obj('cab_ws_glass', (0, YF + 0.06, 1.80), (XW, 0.004, 0.44), m_glass))
    # destination blind box above the windscreen (lit, blank-ish from inside: a dim panel)
    objs.append(box_obj('cab_blind', (-0.2, YF - 0.06, 2.34), (0.7, 0.05, 0.09), MT.simple('Cab_Blind', '#1A1E28', 0.6)))
    # A-pillars (corner posts) and the centre post
    for x in (-XW + 0.05, XW - 0.05):
        objs.append(box_obj('cab_apillar', (x, YF - 0.02, 1.80), (0.06, 0.06, 0.48), m_rubber))
    objs.append(box_obj('cab_wspost', (-0.05, YF + 0.03, 1.80), (0.025, 0.03, 0.44), m_rubber))
    # side walls with a window band 1.25..2.05 (left: full length; right: the door 2.20..3.20 is an opening)
    for side in (-1, 1):
        x = side * (XW + 0.04)
        objs.append(box_obj('cab_wall_low%d' % side, (x, (Y0 + YF) / 2, (ZF + 1.25) / 2), (0.04, (YF - Y0) / 2, (1.25 - ZF) / 2), m_wall))
        objs.append(box_obj('cab_wall_top%d' % side, (x, (Y0 + YF) / 2, (2.05 + ZC) / 2), (0.04, (YF - Y0) / 2, (ZC - 2.05) / 2), m_wall))
        objs.append(box_obj('cab_win%d' % side, (x, (Y0 + YF) / 2, 1.65), (0.004, (YF - Y0) / 2, 0.40), m_glass))
        ys = np.arange(Y0 + 0.4, YF - 0.2, 1.10)
        for yy in ys:
            objs.append(box_obj('cab_post%d' % side, (x, yy, 1.65), (0.05, 0.035, 0.40), m_frame))
    # the door opening on the right front: cut the low wall there (a dark gap) - an open door frame
    if door_open:
        objs.append(box_obj('cab_door_gap', (XW + 0.06, 2.70, (ZF + 1.25) / 2), (0.05, 0.50, (1.25 - ZF) / 2 + 0.01), MT.simple('Cab_Gap', '#05070A', 0.9)))
    # seats: pairs every 0.80 m, both sides, from 1.65 backward (the hero seat is the first right row at y 1.65)
    for side in (-1, 1):
        for k, yy in enumerate(np.arange(1.65, Y0 + 0.6, -0.80)):
            if side == -1 and k == 0:
                continue
            cx = side * 0.60
            objs.append(box_obj('seat_c', (cx, yy, 1.02), (0.42, 0.24, 0.07), m_seat))
            objs.append(box_obj('seat_b', (cx, yy - 0.24, 1.36), (0.42, 0.06, 0.32), m_seat))
            objs.append(box_obj('seat_rail', (cx, yy - 0.27, 1.72), (0.42, 0.02, 0.02), m_frame))
    # driver's seat and wheel (left front), the radio (warm dial) on the dashboard at az -20 / el -12
    objs.append(box_obj('drv_seat', (-0.55, 2.35, 1.02), (0.25, 0.24, 0.07), m_seat))
    objs.append(box_obj('drv_back', (-0.55, 2.10, 1.40), (0.25, 0.06, 0.36), m_seat))
    whl = bpy.data.meshes.new('wheel')
    import bmesh
    bm = bmesh.new()
    bmesh.ops.create_circle(bm, cap_ends=False, radius=0.22, segments=24)
    bm.to_mesh(whl); bm.free()
    wo = bpy.data.objects.new('wheel', whl); bpy.context.scene.collection.objects.link(wo)
    wo.location = (-0.55, 2.90, 1.42); wo.rotation_euler = (math.radians(60), 0, 0)
    mod = wo.modifiers.new('sk', 'SKIN') if False else None
    cu = bpy.data.curves.new('wheelc', 'CURVE'); cu.dimensions = '3D'; cu.bevel_depth = 0.014
    sp = cu.splines.new('POLY'); n = 32; sp.points.add(n)
    for i in range(n + 1):
        a = 2 * math.pi * i / n
        sp.points[i].co = (0.22 * math.cos(a), 0.22 * math.sin(a), 0, 1)
    cu.materials.append(MT.simple('Cab_Wheel', '#2E2E2E', 0.55))
    wc = bpy.data.objects.new('wheelc', cu); bpy.context.scene.collection.objects.link(wc)
    wc.location = wo.location; wc.rotation_euler = wo.rotation_euler
    bpy.data.objects.remove(wo)
    # radio dial (bible §6·2: screen #E19867, fill #FF7703 @ +0.71)
    d_r = 1.12
    rx = EYE[0] + d_r * math.sin(math.radians(-20)); ry = EYE[1] + d_r * math.cos(math.radians(-20)); rz = EYE[2] - d_r * math.tan(math.radians(12))
    objs.append(box_obj('console', (rx, ry + 0.06, (1.36 + rz) / 2 - 0.02), (0.13, 0.08, (rz - 1.36) / 2 + 0.03), m_dash))
    objs.append(box_obj('radio', (rx, ry - 0.025, rz), (0.075, 0.004, 0.018), MT.emissive('Cab_Radio', tuple(np.array(MT.hexlin('#FF7703')) * 2 ** 0.71))))
    # tube lights: 2 rows x 5, 1.2 m, on the ceiling at x +-0.55 (bible §4.3), + area lights so the seat cushion gets E ~0.8
    for side in (-1, 1):
        for k in range(5):
            yy = 2.2 - k * 1.6
            objs.append(box_obj('tube', (side * 0.55, yy, ZC - 0.02), (0.05, 0.6, 0.012), m_tube))
            if tube_on > 0:
                l = bpy.data.lights.new('tubeL', 'AREA'); l.shape = 'RECTANGLE'; l.size = 0.12; l.size_y = 1.2
                l.energy = 9.0 * tube_on; l.color = MT.hexlin('#E4F1F3')
                lo = bpy.data.objects.new('tubeL', l); bpy.context.scene.collection.objects.link(lo)
                lo.location = (side * 0.55, yy, ZC - 0.04)
                lo.visible_glossy = False          # the tube meshes themselves are what glass and chrome reflect
    return objs


# ---------------------------------------------------------------------------------------------- the world around the road
def landscape(s_off, wet, road_mat=None):
    """Road (x -4.9..1.6), gravel shoulders, grass verges, paddy water beyond, a dark tree line."""
    road_mat = road_mat or MT.wet_road('LK_Road', GROUND, ROAD_MASK, s_off, wet=wet)
    Y0, Y1 = -60, 420
    plane('road', ROAD_X[0], ROAD_X[1], Y0, Y1, 0.0, road_mat, 4, 120)
    gravel = MT.ground_noise('LK_Gravel', '#3A3A36', '#2A2A27', 0.35 if wet else 0.8, scale=8)
    plane('shoulderL', -6.2, ROAD_X[0], Y0, Y1, -0.01, gravel, 1, 60)
    plane('shoulderR', ROAD_X[1], 3.8, Y0, Y1, -0.01, gravel, 1, 60)
    grass = MT.ground_noise('LK_Grass', '#2B3A22', '#1E2618', 0.45 if wet else 0.8, scale=3, bump=0.6)
    plane('vergeL', -14.0, -6.2, Y0, Y1, -0.06, grass, 2, 60)
    plane('vergeR', 3.8, 9.0, Y0, Y1, -0.06, grass, 1, 60)
    water = MT.paddy_water('LK_Paddy', rough=0.05 if wet else 0.02)
    plane('paddyL', -400, -14.0, Y0 - 200, Y1 + 600, -0.25, water, 1, 1)
    plane('paddyR', 9.0, 400, Y0 - 200, Y1 + 600, -0.25, water, 1, 1)
    # bunds between paddies (dark earth strips)
    earth = MT.ground_noise('LK_Bund', '#2A2620', '#1C1A16', 0.6, scale=2)
    for x in (-38, -70, 30, 62):
        plane('bund', x - 0.5, x + 0.5, Y0 - 200, Y1 + 600, -0.12, earth, 1, 1)
    # a far tree line (dark silhouettes), 180-320 m, irregular heights
    rng = np.random.default_rng(3)
    tree = MT.simple('LK_Tree', '#0B0F0B', 0.9)
    for k in range(60):
        x = rng.uniform(-420, 420); y = rng.uniform(260, 420)
        if abs(x) < 12:
            continue
        h = rng.uniform(6, 14); r = rng.uniform(3, 7)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=6, radius=1, location=(x, y, h * 0.6))
        o = bpy.context.object; o.scale = (r, r, h * 0.6); o.data.materials.append(tree)


def halo(name, centre, cam, radius, col_lin, power=3.0, alpha=0.18):
    """Lanbai/LampHalo (README §3): an additive card facing the camera, I(r) = col * alpha * (1 - r/R)^power,
    the soft glow of a lamp in drizzle (rain kit §11: a soft body + a long tail, not a disc with an edge)."""
    c = np.asarray(centre, float); e = np.asarray(cam, float)
    f = e - c; f /= np.linalg.norm(f)
    up = np.array([0, 0, 1.0]); r = np.cross(up, f); r /= np.linalg.norm(r); u = np.cross(f, r)
    V = [tuple(c + radius * (sx * r + sy * u)) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    me = bpy.data.meshes.new(name); me.from_pydata(V, [], [(0, 1, 2, 3)]); me.update()
    uvl = me.uv_layers.new(); uvl.data.foreach_set('uv', [0, 0, 1, 0, 1, 1, 0, 1])
    b = MT.NB(name)
    uv = b.N('ShaderNodeTexCoord').outputs['UV']
    rr = b.math('MULTIPLY', b.vmath('LENGTH', b.vmath('SUBTRACT', uv, (0.5, 0.5, 0.0))), 2.0 * radius)    # metres
    # core: exp(-(r / 0.30)^2); tail: (1 + (r / 0.45)^2)^-1.5; both faded to 0 at the card edge (no visible rim)
    core = b.math('EXPONENT', b.math('MULTIPLY', -1.0, b.math('POWER', b.math('DIVIDE', rr, 0.30), 2.0)))
    tail = b.math('POWER', b.math('ADD', 1.0, b.math('POWER', b.math('DIVIDE', rr, 0.45), 2.0)), -1.5)
    edge = b.math('POWER', b.math('MAXIMUM', b.math('SUBTRACT', 1.0, b.math('DIVIDE', rr, radius)), 0.0), 2.0)
    k = b.math('MULTIPLY', b.math('ADD', b.math('MULTIPLY', core, 0.6), b.math('MULTIPLY', tail, 0.4)), edge)
    em = b.N('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col_lin, 1)
    b.L(b.math('MULTIPLY', k, alpha), em.inputs['Strength'])
    tr = b.N('ShaderNodeBsdfTransparent')
    add = b.N('ShaderNodeAddShader'); b.L(em.outputs[0], add.inputs[0]); b.L(tr.outputs[0], add.inputs[1])
    b.L(add.outputs[0], b.out.inputs[0])
    me.materials.append(b.m)
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    ob.visible_shadow = False; ob.visible_diffuse = False; ob.visible_glossy = False
    return ob


def sky(col_hex):
    w = bpy.context.scene.world
    bg = w.node_tree.nodes.get('Background')
    if bg is None:
        w.node_tree.nodes.clear()
        bg = w.node_tree.nodes.new('ShaderNodeBackground')
        o = w.node_tree.nodes.new('ShaderNodeOutputWorld')
        w.node_tree.links.new(bg.outputs[0], o.inputs[0])
    bg.inputs[0].default_value = (*MT.hexlin(col_hex), 1)
    bg.inputs[1].default_value = 1.0


# ---------------------------------------------------------------------------------------------- act 2
def act2(t=27.0, lamp_I=40.0, cam_yaw=0.0, cam_pitch=0.0, hfov=90.0, W=960, H=540, wires=True, cabin_on=True, cam=None, look=None):
    sb = s_bus(t)
    sky('#060405')                       # bible §6·2 sky fill (-> screen #05080F under S2)
    mats = make_mats(wet=1.0)
    m_wire = MT.simple('LK_Wire', '#1E1F1F', 0.40)
    landscape(sb, 1.0)
    heads, all_tops = [], []
    for k, s in enumerate(LAMP_S + [LAMP_S[-1] + 32.0]):
        y = s - sb                       # lamp road position relative to the bus (the bus nose at y ~3.5)
        if y < -60 or y > 400:
            continue
        lit = k < 5                      # lamps end at U2b (the 6th standard is unlit: the dark stretch starts)
        glow = (lambda n, A, Bp: MT.lampglow(n, TEX, A, Bp, HEAD_FILL, tuple(np.array(HEAD_FILL) * np.array([2.2, 2.6, 4.0])), 1.0)) if lit else \
            (lambda n, A, Bp: MT.simple(n, '#5A5248', 0.3))
        ob, c, tops, info = lamp_standard('lamp%d' % k, y, mats, glow)
        all_tops.append(tops)
        if lit:
            heads.append(c)
            spot('sodium%d' % k, tuple(c + np.array([0, 0, -0.04])), lamp_I, SODIUM, size_deg=160, blend=0.85, radius=0.06)
            point('uplight%d' % k, tuple(c + np.array([0, 0, 0.02])), lamp_I * UPLIGHT, SODIUM, radius=0.10)
            halo('halo%d' % k, c + np.array([0, 0, -0.05]), tuple(float(v) for v in cam.split(',')) if cam else EYE, HALO_R, tuple(np.array(SODIUM) * HALO_K), HALO_P, 1.0)
    if wires:
        for a, b in zip(all_tops[:-1], all_tops[1:]):
            for i in range(3):
                wire('wire', G.catenary(a[i], b[i], 0.60, 32), m_wire)
        # spans continuing beyond the first / last standard
        for tops, dy in ((all_tops[0], -32.0), (all_tops[-1], 32.0)):
            for i in range(3):
                q = np.array(tops[i]) + (0, dy, 0)
                wire('wire', G.catenary(tops[i], q, 0.60, 32), m_wire)
    # headlights (bible §4.9: one realtime spot pair, 3200 K, 30 m, 35 deg; E 0.9 at 10 m -> I 90)
    for x in (-0.80, 0.80):
        spot('head', (x, 3.55, 0.75), 90.0, HEADLIGHT, size_deg=38, blend=0.35, rot=(math.radians(90 - 4.5), 0, 0), radius=0.08)
    if cabin_on:
        cabin()
    sc = bpy.context.scene
    loc = EYE
    if cam is not None:
        loc = tuple(float(v) for v in cam.split(','))
        if look is not None:
            tg = np.array([float(v) for v in look.split(',')]) - np.array(loc)
            cam_yaw = math.degrees(math.atan2(tg[0], tg[1]))
            cam_pitch = math.degrees(math.atan2(tg[2], math.hypot(tg[0], tg[1])))
    B.camera('cam', loc, cam_yaw, cam_pitch, hfov, W, H, sc)
    return dict(t=t, s_bus=sb, heads=[list(map(float, h)) for h in heads])


def render(act, out, W, H, spp, **kw):
    sc = B.reset_scene(W, H, spp)
    meta = {'act2': act2}[act](W=W, H=H, **kw)
    rgb = B.render_to(out, sc)
    # depth: same scene, every material replaced by an emitter of the view distance, 1 sample-ish
    vl = sc.view_layers[0]
    dm = MT.depth_material()
    vl.material_override = dm
    w = sc.world
    sc.world = bpy.data.worlds.new('Wdepth'); sc.world.use_nodes = True
    sc.world.node_tree.nodes['Background'].inputs[0].default_value = (1e6, 1e6, 1e6, 1)
    lights = [o for o in bpy.data.objects if o.type == 'LIGHT']
    for o in lights:
        o.hide_render = True
    sc.cycles.samples = 4
    sc.cycles.max_bounces = 0
    dpath = out.replace('.exr', '_depth.exr')
    dep = B.render_to(dpath, sc)
    vl.material_override = None; sc.world = w
    np.save(out.replace('.exr', '.npy'), rgb[..., :3].astype(np.float32))
    np.save(out.replace('.exr', '_depth.npy'), dep[..., 0].astype(np.float32))
    json.dump(meta, open(out.replace('.exr', '.json'), 'w'), indent=1)
    return meta


if __name__ == '__main__':
    act, out, W, H, spp = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5])
    kw = {}
    for a in sys.argv[6:]:
        k, v = a.split('=')
        kw[k] = float(v) if v.replace('.', '', 1).replace('-', '', 1).isdigit() else v
    print(render(act, out, W, H, spp, **kw))
