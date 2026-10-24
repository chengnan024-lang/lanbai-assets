# -*- coding: utf-8 -*-
"""Act 7a (F2h -> F5, 363.26 -> 644.96) layout: Act07_Sea/Act07_Layout.json, THE single data source of the 7a package.
The Unity builder (Act07_Sea/Editor/LanbaiAct07Builder.cs, menu 蓝白/Build/Act07a) reads it and generates every mesh
(particles, shafts, the ridge wall, the warm point) and fills the driver's arrays; the reference frames
(Act07_Sea/Docs~/lookdev/scene_7a.py) read it too. Bible v2.1 §6·7a + Art/总导演裁决.md (D-09, D-17, D-21, D-23).

Frames (README_Act07a.md §1):
  WORLD  Unity, bus fixed at the origin, heading +z (treadmill).
  WATER  x right, y up from the sea surface (= -depth), z = bus heading. The bus origin sits at bus_w(t) = (0, -depth(t),
         fwd(t)) in it; R_Sea (the root of everything fixed in the water) is placed at world -bus_w(t) = (0, depth(t), -fwd(t)).
  BUS    = world (bus coordinates). Trails and bubbles live here (objects at the world origin).
Every time curve is a function of the timeline second t (labels: act07_motion.L = FromLocal/cues.json, falling back to the
bible §2.1 seconds for the v2.1 sub-labels cues.json does not have yet).
  ~/bpy/bin/python Act07_Sea/Tools~/act07_layout.py"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.dirname(HERE)
REPO = os.path.dirname(PKG)
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'Sea', 'Tools~'))
import act07_motion as AM  # noqa: E402
import grade as G  # noqa: E402

L = AM.L
EYE = np.array([0.55, 1.70, 2.05])          # main seat eye (Gate cameras.U7 = render harness 'hero'); README §1
R = lambda x, n=4: [round(float(v), n) for v in np.ravel(x)]   # noqa: E731


# the bioluminescence fill: the bible's #5E7AFF @ +2.73 (screen #8AC6FF under S7a) crosses the D-21 line under S7b (seed
# cores h_ab 291, L* 40.7, 11_F5_warm r1). #5E84FF @ +2.73: 0 pixels over the line from S7a through the blend to S7b (all
# intensities 0.002-3 x, on black and on the 145 m water), screen #8AD1FF under S7a (dE small, same family)
BIO_FILL = '#5E84FF'


def srgb_lin(h, ev=0.0):
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4) * 2.0 ** ev


def fill(screen_hex, sid):
    return np.asarray(G.fill_for(screen_hex, sid), np.float64)


def eye_under_t():
    """the first t at which the eye (y 1.70) is under the surface (plane world y = depth(t))"""
    t = L['F2h']
    while AM.depth(t) < EYE[1]:
        t += 0.005
    return round(t, 3)


def profile_json(P):
    return dict(T0=P.T0, v0=P.v0, segs=[dict(t0=round(a, 3), dur=round(b, 3), dv=round(c, 4)) for a, b, c in P.segs],
                law='v(t) = v0 + sum dv * smoothstep((t - t0) / dur); x(t) = exact integral from T0 (x(T0) = 0); '
                    'smoothstep integral: x^3 - x^4 / 2 on [0, 1], then 0.5 + (x - 1)')


# ---------------------------------------------------------------------------------------------------- water (fog)
# bible §6·7a 大气: 0-15 m Exp 0.040, fog fill #77A0D2 (screen #507DA6); 15-60 m 0.030, fill #334E69 (30 m: L3); deep 0.018,
# fill #0D181F. 'Up' and 'down' are the dome (§6·7a 天空盒渐变 上 -> 下): 0-15 #94CAE9 -> #0A3A52, 15-60 #3E6486 -> #03101A,
# deep #06202C -> #010407 (SCREEN colours, solved to fills under the grade of that depth: S7a above 27 m, S7b at depth).
# The shallow 'up' is the dark mirror's colour (#294B72 x 0.38, kit frame 29_K2_r06): looking up you see the mirror.
def water_keys():
    keys = []
    for dep, dens, mid, up, down, sid in (
            (0.0, 0.040, srgb_lin('#77A0D2'), srgb_lin('#294B72') * 0.38, np.array([0.0159, 0.0733, 0.1275]), 'S7a'),
            (15.0, 0.040, srgb_lin('#77A0D2'), srgb_lin('#294B72') * 0.38, np.array([0.0159, 0.0733, 0.1275]), 'S7a'),
            (30.0, 0.030, srgb_lin('#334E69'), fill('#3E6486', 'S7a'), fill('#03101A', 'S7a'), 'S7a'),
            (60.0, 0.030, srgb_lin('#334E69'), fill('#3E6486', 'S7b'), fill('#03101A', 'S7b'), 'S7b'),
            (145.0, 0.018, srgb_lin('#0D181F'), fill('#06202C', 'S7b'), fill('#010407', 'S7b'), 'S7b'),
            (250.0, 0.018, srgb_lin('#0D181F'), fill('#06202C', 'S7b'), fill('#010407', 'S7b'), 'S7b')):
        keys.append(dict(depth=dep, density=dens, up=R(up), mid=R(mid), down=R(down), grade=sid))
    return keys


# ---------------------------------------------------------------------------------------------------- shafts
def shafts(rng):
    """<= 16 light shafts fixed in the WATER frame (the surface makes them; the bus sinks past them), axis = the refracted
    sun (air elevation 70 deg -> in water 14.9 deg off vertical), 1-4 m wide, 20-40 m long, alpha 0.04-0.08; centres 6-20 m
    deep, 3-28 m from the bus axis (never within 1.5 m of the eye's vertical line), spread around the sun azimuth's side."""
    sun_az = math.radians(30.0)                    # D-12: the dawn sun azimuth +30
    tilt = math.asin(math.sin(math.radians(20.0)) / 1.333)
    axis = np.array([-math.sin(tilt) * math.sin(sun_az), -math.cos(tilt), -math.sin(tilt) * math.cos(sun_az)])   # pointing DOWN, away from the sun
    out = []
    # F3 forward (终审 7a 一 #5): three shafts in front of the windscreen, 7 / 10.5 / 14 m out, inside its azimuth range
    # (bus_shell bible_v2: -50..25 from the main eye) and clear of the centre post (-11), at the eye's depth at F3 so the
    # 'shafts slanting down past the windscreen' read in the first frame of 7a; alpha at the bible's top (0.08)
    eye_y_F3 = -AM.depth(L['F3']) + EYE[1]
    for dx, dz, hw, ln, al in ((-2.0, 7.0, 0.8, 28.0, 0.08), (1.6, 10.5, 1.1, 30.0, 0.075), (-0.6, 14.0, 0.7, 26.0, 0.08)):
        out.append(dict(centre=R([EYE[0] + dx, eye_y_F3 - 2.0, EYE[2] + dz], 3), axis=R(axis, 5), half_width=hw, length=ln,
                        seed=round(rng.uniform(), 4), alpha=al, note='F3 forward'))
    tries = 0
    while len(out) < 16 and tries < 5000:
        tries += 1
        r = rng.uniform(3.0, 28.0); a = rng.uniform(0, 2 * math.pi)
        x, z = r * math.sin(a), r * math.cos(a) + EYE[2]
        if math.hypot(x - EYE[0], z - EYE[2]) < 1.5:
            continue
        if any(math.hypot(x - s['centre'][0], z - s['centre'][2]) < 3.0 for s in out):
            continue
        out.append(dict(centre=R([x, -rng.uniform(6.0, 20.0), z], 3), axis=R(axis, 5), half_width=round(rng.uniform(0.5, 2.0), 3),
                        length=round(rng.uniform(20.0, 40.0), 2), seed=round(rng.uniform(), 4), alpha=round(rng.uniform(0.04, 0.08), 4)))
    return out


# ---------------------------------------------------------------------------------------------------- particles
SNOW_NEAR, SNOW_SPHERE, SNOW_BOX = 2.0, 10.0, 24.0
SNOW_LIT = 2.2


def snow(rng, n=1200):
    """海雪: 1 200 (bible: in a 25 m sphere; here in the 2-10 m shell around the eye / 24 m wrap box: the bible's 25 m sphere gave ~2 flakes within
    5 m of the eye and no sinking cue -- 给总控 第五批 #9; 40 % toward the windscreen), 0.8-2.5 cm, screen #697987,
    alpha 0.3-0.6, sinking 1.5 cm/s (the bus sinks faster: they rise past the windows). WATER-frame positions around the
    bus at F3, never inside the cabin's 1.2 m around the eye (they are drawn outside the glass anyway)."""
    c = fill('#697987', 'S7a')
    # uniform DIRECTION, radius in the 2-10 m shell (not uniform-in-volume): the sinking cue has to read in every
    # direction (VR), so put the flakes where the eye can resolve them instead of mostly out at the sphere's rim
    dirs = rng.normal(size=(n, 3)); dirs /= np.linalg.norm(dirs, axis=1, keepdims=True)
    # 40 % of them toward the windscreen (bus_shell bible_v2 from the main eye: az -50..25, el -15..22): the first frame of
    # 7a looks forward (终审 7a 一 #5). The bus does not move forward in 7a (fwd = 0 until F5), so the azimuth bias holds
    # while the wrap box recycles them vertically
    nf = int(0.4 * n)
    az = np.radians(rng.uniform(-50.0, 25.0, nf)); el = np.radians(rng.uniform(-15.0, 22.0, nf))
    dirs[:nf] = np.stack([np.cos(el) * np.sin(az), np.sin(el), np.cos(el) * np.cos(az)], -1)
    r = rng.uniform(SNOW_NEAR, SNOW_SPHERE, n)
    pts = EYE[None, :] + dirs * r[:, None]
    pts = pts + np.array([0.0, -AM.depth(L['F3']), AM.fwd(L['F3'])])
    rad = rng.uniform(0.004, 0.0125, n)
    a = rng.uniform(0.3, 0.6, n)
    return dict(kind='SNOW', count=n, colour=R(c), positions=R(pts, 3), radius=R(rad, 5), alpha=R(a, 3), seed=R(rng.uniform(size=n), 4))


def seeds(rng, n=200):
    """播下的光: 200 births from F3i to F5, density rising toward ...die starben! (628-644: the densest), each a 0.2 s
    birth flash then a steady 12-15 % glow FIXED IN THE WATER; >= 5 m from the eye at birth, <= 3 cm, and never two flashes
    at once inside one 5 deg cone (checked here: a birth is moved later until it is clear). Colour = the bioluminescence
    #8AC6FF (fill #5E7AFF @ +2.73). Positions: around and above the bus at its birth depth (by F5 '~200 still cold points
    around and overhead')."""
    t0, t1 = L['F3i'], L['F5'] - 0.5
    u = rng.uniform(size=n * 3)
    ts = np.sort(t0 + (t1 - t0) * (1.0 - (1.0 - u) ** 0.55))[:n * 3]           # density rises toward the end
    ts = np.sort(rng.choice(ts, n, replace=False))
    births, dirs, pos = [], [], []
    for tb in ts:
        for _ in range(200):
            r = rng.uniform(5.5, 22.0)
            el = math.radians(rng.uniform(-35.0, 70.0)); az = rng.uniform(0, 2 * math.pi)
            d = np.array([math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az)])
            clash = any(abs(tb - t2) < 0.25 and math.degrees(math.acos(min(1.0, float(d @ d2)))) < 5.0 for t2, d2 in zip(births, dirs))
            if not clash:
                break
            tb += 0.05
        births.append(tb); dirs.append(d)
        busw = np.array([0.0, -AM.depth(tb), AM.fwd(tb)])
        pos.append(busw + EYE + d * r)
    rad = rng.uniform(0.006, 0.015, n)
    steady = rng.uniform(0.12, 0.15, n)
    return dict(kind='SEED', count=n, colour=R(srgb_lin(BIO_FILL, 2.73)), positions=R(np.array(pos), 3), radius=R(rad, 5),
                birth_t=R(births, 3), steady=R(steady, 4), seed=R(rng.uniform(size=n), 4),
                check=dict(min_birth_distance_m=5.5, cone_deg=5.0, flash_s=0.2))


def hull_points(rng, n):
    """points 5-30 cm outside the bus hull (bus_shell.json body: 2.08 wide, y 0.42..2.74, z -3.5..3.5), sides and bottom"""
    pts = []
    while len(pts) < n:
        side = rng.uniform()
        z = rng.uniform(-3.5, 3.5)
        off = rng.uniform(0.05, 0.30)
        if side < 0.4:
            pts.append([1.04 + off, rng.uniform(0.45, 2.7), z])
        elif side < 0.8:
            pts.append([-1.04 - off, rng.uniform(0.45, 2.7), z])
        else:
            pts.append([rng.uniform(-1.0, 1.0), 0.42 - off, z])
    return np.array(pts)


def trails(rng):
    """船体生物荧光 (F4 on): 300 births / s, life 1.5-3 s, 1-3 cm with a soft glow, screen #8AC6FF (fill #5E7AFF @ +2.73);
    a pool of 900 quads at hull points (BUS frame); the shader streams them back with the water (-_Udon_SeaBusVel x age)"""
    n = 900
    pts = hull_points(rng, n)
    ph = rng.uniform(size=n)
    # the first 90 of the pool: three lines along the right side (y 0.9 / 1.55 / 2.2, 26 cm out), each born front -> back
    # over 0.3 s, so 'the first bioluminescence lights up ALONG the hull' reads as lines, not stars (终审 7a 二)
    for i in range(90):
        line, j = divmod(i, 30)
        pts[i] = [1.30, (0.9, 1.55, 2.2)[line], 3.5 - 7.0 * j / 29.0]
        ph[i] = 0.1 * j / 29.0 + 0.33 * line
    return dict(kind='TRAIL', count=n, colour=R(srgb_lin(BIO_FILL, 2.73)), positions=R(pts, 3),
                radius=R(rng.uniform(0.005, 0.015, n), 5), phase=R(ph, 4), life=R(rng.uniform(1.5, 3.0, n), 3),
                seed=R(rng.uniform(size=n), 4), T0=L['F4'], rate=300.0, pool=n, alpha=1.0)


def bubbles(rng):
    """入水 120 bubbles on the glass (one-shot at F2h, delays 0-1.5 s, 0.6-1.5 s each) + 40 from the seat seams (loop 6 s).
    BUS frame. Glass: the side windows' planes x = +-1.0 (just inside), y 1.0-2.3; seats: rows z -2.6..2.4 (step 0.75),
    x +-(0.35..0.95), y 0.62 + 0.45 (the seat seam)."""
    g = []
    for _ in range(120):
        s = 1 if rng.uniform() < 0.5 else -1
        g.append([s * 1.0, rng.uniform(1.0, 2.3), rng.uniform(-3.2, 3.2)])
    seats = []
    for i in range(40):
        z = -2.6 + 0.75 * (i % 7)
        s = 1 if (i // 7) % 2 else -1
        seats.append([s * rng.uniform(0.35, 0.95), 1.07, z + rng.uniform(-0.1, 0.1)])
    return [dict(kind='BUBBLE', name='Glass', count=120, positions=R(np.array(g), 3), radius=R(rng.uniform(0.002, 0.006, 120), 5),
                 delay=R(rng.uniform(0.0, 1.5, 120), 3), duration=R(rng.uniform(0.6, 1.5, 120), 3), alpha=0.55, T0=L['F2h'], loop=0.0,
                 rise=0.6, colour=R(np.array([0.55, 0.70, 0.80])), queue=2990, seed=R(rng.uniform(size=120), 4)),
            dict(kind='BUBBLE', name='Seats', count=40, positions=R(np.array(seats), 3), radius=R(rng.uniform(0.002, 0.005, 40), 5),
                 delay=R(rng.uniform(0.0, 1.0, 40), 3), duration=R(rng.uniform(2.0, 4.0, 40), 3), alpha=0.45, T0=L['F2h'], loop=6.0,
                 rise=1.2, colour=R(np.array([0.45, 0.60, 0.72])), queue=3010, seed=R(rng.uniform(size=40), 4))]


# ---------------------------------------------------------------------------------------------------- the ridge wall
def ridge(rng):
    """F3e2 (532.36, 105 m): 'a ridge's rock wall rises past the right window: >= 12 m away, relative 1.5 m/s, low
    contrast, only edged by the hull's bioluminescence'. A heightfield in the WATER frame: the face is the plane
    x = 12.0 + bulge(y, z) >= 12.0 (to the bus's right), from depth 80 to 135 m (it takes ~37 s to pass the window at
    1.5 m/s), z -45 .. +45. Grid 1 m (91 x 56 vertices). Offsets: fbm, 0.4 .. 3 m OUTWARD only (the nearest point stays
    at 12 m: VR §1.8 'rock >= 12 m')."""
    zs = np.arange(-45.0, 45.01, 1.0)
    ys = np.arange(-135.0, -79.99, 1.0)
    Z, Y = np.meshgrid(zs, ys)
    off = np.zeros_like(Z)
    for k, amp in ((1 / 23.0, 1.6), (1 / 9.0, 0.4), (1 / 3.7, 0.10)):          # the finest octave down (it read as veins)
        ph = rng.uniform(0, 2 * math.pi, 4)
        off += amp * (np.sin(2 * math.pi * k * Z + ph[0]) * np.sin(2 * math.pi * k * 1.3 * Y + ph[1]) + 0.5 * np.sin(2 * math.pi * k * (0.7 * Z + 0.9 * Y) + ph[2]))
    # horizontal strata (终审 7a 二: 'only the outline and the horizontal bedding catch the light'): a ledge every 4 m, its lip
    # sticking out 1.2 m, gently wavy along z so the bedding is rock, not a ruler
    wav = 0.6 * np.sin(2 * math.pi * Z / 31.0 + 1.3)
    tt = np.mod((Y + wav) / 4.0, 1.0)
    off += 1.2 * np.clip((tt - 0.7) / 0.3, 0.0, 1.0) ** 2
    off = off - off.min() + 0.4
    # the face tilts back a little at the top and bottom (a ridge, not a wall of a box)
    tilt = 4.0 * (np.clip((Y + 107.0) / 28.0, -1, 1) ** 2)
    X = 12.0 + off + tilt
    return dict(frame='WATER', x_min_m=round(float(X.min()), 3), grid=dict(z0=-45.0, dz=1.0, nz=len(zs), y0=-135.0, dy=1.0, ny=len(ys)),
                x=R(X, 3), back_thickness_m=6.0,
                material=dict(shader='Lanbai/SeaRidge', base=R(fill('#0B1A26', 'S7b') * 0.8), rim=R(srgb_lin('#8AC6FF') * 1.2),
                              rim_reach_m=8.0, rim_near_m=12.0, rim_wrap=0.55, rim_face=0.04, rim_edge=4.0,
                              note='low contrast: the faces sit just above the water fog of 105 m; only the silhouettes catch the '
                                   'hull bioluminescence #8AC6FF (bible: 只被船体生物荧光描出一道边), full strength out to rim_near_m, '
                                   'falling off over rim_reach_m beyond; wrap: the trails run along the whole hull'),
                passes=dict(enters_window_t=round(L['F3e2'] - 12.0, 2), centre_t=L['F3e2'], leaves_window_t=round(L['F3e2'] + 14.0, 2)))


# ---------------------------------------------------------------------------------------------------- the warm point
def warm_point():
    """F5 644.96: 'far below, one warm point: the palace's nearest lamp'. Position = the PalaceFrame lamp nearest the bus
    at F5, in the WATER frame (palace frame: y 0 = terrace top at depth frame.terrace_top_depth_m, z 0 = the bus origin at
    F5). Drawn by Lanbai/SeaSpecks (one point), gold #E0A860 solved under S7b; the palace session's own lamp replaces it
    (README_Act07a §6)."""
    PF = json.load(open(os.path.join(PKG, 'PalaceFrame_约定.json'), encoding='utf-8'))
    td = PF['frame']['terrace_top_depth_m']
    busw = np.array([0.0, -AM.depth(L['F5']), AM.fwd(L['F5'])])
    # the nearest lamp SEEN from the main seat: through the windscreen (bus_shell bible_v2: az -50..25, el -15..22) with
    # 0.5 deg to spare at the lower edge, >= 2 deg off the centre post (az -11): Lamp_R01 (55 m) sits right behind the
    # post and on the sill (review r1 #6), so it is Lamp_L01 (61 m, az -27.8, el -13.7)
    best = None
    for lp in PF['lamps']:
        p = np.array(lp['flame_pos']) + np.array([0.0, -td, AM.fwd(L['F5'])])
        dv = p - (busw + EYE)
        dist = np.linalg.norm(dv)
        az, el = math.degrees(math.atan2(dv[0], dv[2])), math.degrees(math.asin(dv[1] / dist))
        if not (-50.0 < az < 25.0 and -14.5 < el < 22.0) or abs(az + 11.0) < 2.0:
            continue
        if best is None or dist < best[0]:
            best = (dist, lp['id'], p)
    return dict(id=best[1], position_water=R(best[2], 3), distance_at_F5_m=round(best[0], 2), t_on=L['F5'], fade_in_s=3.0,
                colour=R(fill('#E0A860', 'S7b')), flux=3.0, radius_m=0.25, halo_radius_m=0.85, halo_flux=0.7,
                halo_note='a soft halo of ~1.6 deg (<= 2 deg) around the point so it can be found at 640 px (终审 7a 二): a second, wider and '
                          'dimmer point in the same mesh',
                replaced_by='Palace/PalaceLayout.json (the palace session)')


# ---------------------------------------------------------------------------------------------------- curves
def keys(*pairs):
    return [dict(t=round(float(t), 3), v=(R(v, 5) if hasattr(v, '__len__') else round(float(v), 5))) for t, v in pairs]


def main():
    rng = np.random.default_rng(707)
    tu = eye_under_t()
    sun = srgb_lin('#B0D9F2')
    J = dict(
        about='蓝白 · 第 7a 幕（F2h → F5）布局：唯一的数据源。Act07_Sea/Tools~/act07_layout.py 生成；搭建脚本 蓝白/Build/Act07a 读它建网格、填驱动；'
              '参考帧 Act07_Sea/Docs~/lookdev/scene_7a.py 也读它。圣经 v2.1 §6·7a，总导演裁决 D-09 / D-17 / D-21 / D-23。',
        version=1,
        frames=dict(world='Unity, bus fixed at the origin, heading +z', water='x right, y up from the sea surface (= -depth), z = bus heading',
                    bus_water='(0, -depth(t), fwd(t))', R_Sea_world='(0, depth(t), -fwd(t))', eye=R(EYE, 3),
                    eye_note='main seat eye = Gate cameras.U7 = render harness hero; LB_Journey.heroEye is (0.70, 1.77, 0.20)'),
        labels={k: dict(t=L[k], source=AM.LSRC[k]) for k in ('F2h', 'F3', 'F4', 'F4p', 'F3e', 'F3e1', 'F3e2', 'F3e3', 'F3i', 'F5', 'F8', 'F9s')},
        window=dict(t0=round(L['F2h'] - 1.0, 2), t1=round(AM.EXIT + 1.0, 2),
                    note='the act-7 driver owns F2h - 1 .. exit + 1; this package fills 7a (to F5) and holds the 7a end state after F5 until 7b / 7c arrive'),
        motion=dict(D0=AM.D0, sink=profile_json(AM.SINK), forward=profile_json(AM.FWD),
                    check=dict((k, dict(depth=round(AM.depth(L[k]), 2), v_sink=round(AM.SINK.v(L[k]), 3))) for k in ('F2h', 'F3', 'F4', 'F4p', 'F3e', 'F3e1', 'F3e2', 'F3e3', 'F3i', 'F5'))),
        handover=dict(entry_t=L['F2h'], eye_under_t=tu, plane_y_at_entry=AM.D0,
                      note='F2h: the Clouds driver switches its sea off, this one switches the plane on (same y, ABOVE material M_06_Sea); '
                           'at eye_under_t (the waterline covers the eye) the plane takes M_07a_SeaSurface, _Udon_Underwater 0 -> 1 '
                           '(README_Sea接口 §5)'),
        sea=dict(object='Sea_Disc.fbx under R_Sea at water y 0', materials=dict(above='M_06_Sea', below='M_07a_SeaSurface'),
                 window_gain=keys((L['F3e1'], 1.0), (L['F3e1'] + 8.0, 0.04)),
                 window_gain_note='F3e1: 窗在 8 秒里从藍白缩暗成一枚暗币 (smoothstep), x the material _WindowGain (18)',
                 window_core_desktop=[4.45, 3.0, 2.0, 1.0], window_core_vr=[3.2, 4.0, 2.0, 1.0],
                 window_core_vr_law='VR: lerp(desktop, vr, smoothstep(0, 1, erosion(t) / 0.25)) with erosion(t) = the cabin fade '
                                    '0 -> 0.25 linear F2h -> F5 (bible §4.8 table); the roof still there = the desktop numbers (D-23 #2)',
                 sea_mode=2),
        water=dict(keys=water_keys(), law='by the bus ORIGIN depth: linear between keys (density, up, mid, down); _Udon_Fog = (density, 0, 0, 1), '
                                          'RenderSettings.fogDensity = density, _Udon_FogBase = 0, _Udon_WaterFog{Up,Mid,Down} = (rgb, 1)'),
        caustics=dict(colour=R(srgb_lin('#9FCBFF', 1.46)), strength_by_depth=[[0.0, 1.0], [15.0, 0.0]], direction=1.0, tiling=1.0,
                      texture='Sea/Textures/Caustics_8x8_2048.png', note='x = strength (cabin floor depth = bus origin depth), z = t'),
        sun=dict(kind='the world main light (D-24: the one shadowed directional = RenderSettings.sun), driven, never switched off',
                 elevation_deg=70.0, azimuth_deg=30.0, colour_hex='#B0D9F2', colour_linear=R(sun),
                 E_by_depth=[[0.0, 1.6], [15.0, 0.001]], E_floor=0.001,
                 takeover='writeMainLight (LB_Journey.extSun): at eye_under_t (the waterline covers the turn) the driver turns it to '
                          'el 70 / az +30, #B0D9F2, E; its shadows and culling (bible §1.6: Bus + Tentacles + Player + PlayerLocal) '
                          'are left as they are; from the exit (922.36) the next act writes it',
                 cookie='CRT Lanbai/SeaCausticsCookie 256 ARGBHalf, size 1.5 m, put on the main light under water and taken off at the '
                        'exit (fallback Sea/Textures/CausticsCookie_Static_256.png)'),
        ambient_trilight=dict(sky=R(srgb_lin('#8FB8DE')), equator=R(srgb_lin('#3876AB')), ground=R(srgb_lin('#0F2E4E')),
                              note='RenderSettings Trilight (bible §6·7a 补光); written by the owner of RenderSettings (给总控 第五批)'),
        cabin=dict(note='the timeline / cabin driver writes these (bible §4.8 table), listed so the reference frames use the same numbers',
                   bleach=[[L['F2h'], 0.10], [L['F5'], 0.25]], erosion=[[L['F2h'], 0.0], [L['F5'], 0.25]],
                   ambient=[[0.0, R(srgb_lin('#6186A7') * 0.6)], [60.0, R(srgb_lin('#0F1E30') * 0.3)]], ambient_by='depth m'),
        shafts=dict(items=shafts(rng), material=dict(colour=R(srgb_lin('#8AB2FF', 1.30)), streak_scroll=[0.02, -0.035]),
                    gain_by_depth=[[0.0, 1.0], [18.0, 1.0], [25.0, 0.0]],
                    gain_law='g = depth fade until 453; 453 -> F4p: lerp(depth fade, 1, smoothstep) (they gather and brighten: F4p is their brightest); F4p -> 467.6: x (1 - smoothstep) to 0 (review r1 #1)',
                    gather=dict(t0=453.0, t1=L['F4p'], point_bus=[0.55, 2.74, 1.2], note='F4p: the shafts converge on the skylight hole in 9 s; the '
                                'gather point is the skylight (bus frame); the driver writes _GatherPoint in R_Sea object space each frame'),
                    after_F4p_fade=[[L['F4p'], 1.0], [467.6, 0.0]],
                    last_shaft=dict(t_in=L['F3e1'], fade_in_s=2.0, sweep_s=4.0, fade_out_s=2.0, half_width=2.2, length=34.0, alpha=0.10,
                                    from_bus=[3.0, 14.0, -2.0], to_bus=[-1.5, 14.0, 4.5], target_from_bus=[1.0, 0.95, -2.0], target_to_bus=[0.0, 0.95, 3.5],
                                    top_above_centre_m=2.0,
                                    note='F3e1: the last wide shaft sweeps across the seats (2 s in, 4 s sweep, 2 s out; seats <= luma 120): its '
                                         'foot moves from target_from to target_to (past the main seat at ~0.58), the beam light rides with it; '
                                         'the quad starts 2 m above its moving centre so the seats sit at uv.y ~0.45 (full strength), then all shafts are gone')),
        beam=dict(kind='Spot (bus frame, under R_Act07Bus), culling Bus + Player + PlayerLocal (no shadows): the light that lands on the seats and your hands',
                  colour_hex='#B0D9F2', spot_angle_deg=28.0, range_m=20.0,
                  gather=dict(pos_bus=[0.87, 5.16, 1.76], aim_bus=[0.55, 1.1, 1.75], E_peak=9.0,
                              curve='smoothstep 0 -> 1 from 453 to F4p 462.36, then smoothstep 1 -> 0 to 467.6'),
                  last=dict(E_peak=7.5, curve='the last shaft\'s alpha; position = the shaft centre, aim = its moving foot'),
                  note='Inspector intensity = E (D-00: VRChat forces lightsUseLinearIntensity = true; the bible §1.5 trap 1 is void). Spot lights use Unity\'s legacy range falloff (trap 2): '
                       'check against the grey card locally, the seats must stay <= luma 120 and <= 6 % of the frame. Expected (cloud estimate: Built-in diffuse = albedo x colour x E x atten + the cabin ambient of §cabin, legacy atten ~ 1 / (1 + 25 d^2 / range^2), graded): F4p the worn seat #6A3434 luma ~79, the base vinyl #5A2126 ~57, a mid-grey hand ~155; F3e1 (E 7.5) worn ~72, base ~52. Range 20 m so the falloff over the 4 m throw is 0.49, not 0.16 (range 9 needed E ~44)'),
        particles=dict(snow=snow(rng), seeds=seeds(rng), trails=trails(rng), bubbles=bubbles(rng),
                       snow_sink=0.015, snow_sphere=SNOW_SPHERE, snow_box=SNOW_BOX, snow_lit=dict(gain=SNOW_LIT, depth_full=12.0, depth_none=30.0, note='sunlit flakes in the shallow water: the bible screen colour #697987 has the luma of the water behind it at F3 (both ~118) and the flakes vanish; x gain until 12 m, smoothstep to x 1 (the bible colour) by 30 m (给总控 第五批 #9)'), near_fade=[0.3, 0.8], min_px=1.5),
        ridge=ridge(rng),
        warm_point=warm_point(),
        grade=dict(note='LB_Journey.ApplyGrades owns the PPv2 weights; the driver writes none of them. These are the data for its '
                        'table (README_集成 §2 / §5): one dEV per frame, all events summed (bible §1.4)',
                   ramp=[L['F3e'], L['F5']],
                   events=[
                       dict(kind='EXPO', volume='EXPO_DOWN', at='F2h', t=L['F2h'], dEV=-0.5, down_s=0.3, up_s=1.0, shape='linear in EV down, linear back',
                            w_peak=0.156, note='bible §6·7a 入水 / score 22: the first gulp of dark under the water'),
                       dict(kind='GRADE', volumes=['S6', 'S7a'], at='the waterline over the window tops', t=363.9, dur_s=1.5, end_t=365.4,
                            shape='smoothstep S6 -> S7a (colour change, hidden behind the waterline)', note='bible §6·7a / score 23'),
                       dict(kind='GRADE', volumes=['S7a', 'S7b'], at='F3e', t=L['F3e'], dur_s=round(L['F5'] - L['F3e'], 2), end_t=L['F5'],
                            shape='linear weight (an exposure change: constant EV / s)', note='the 7a cross-fade (purple guard S7a~)'),
                   ]),
        apl_targets=dict(F3=85, F3e=60, F3e1=46, F3e2=35, F3e3=25, F5=16),
    )
    # ---- the same numbers, flat, for the Unity builder (JsonUtility reads no nested arrays): README_Act07a §2
    W = J['water']['keys']
    sh = J['shafts']; ls = sh['last_shaft']
    J['unity'] = dict(
        window_t0=J['window']['t0'], window_t1=J['window']['t1'], entry=L['F2h'], eye_under=tu, exit=AM.EXIT, F3i=L['F3i'], F4=L['F4'], F5=L['F5'],
        D0=AM.D0, sink_T0=AM.SINK.T0, sink_v0=AM.SINK.v0, sink_seg_t0=[a for a, _, _ in AM.SINK.segs], sink_seg_dur=[b for _, b, _ in AM.SINK.segs],
        sink_seg_dv=[c for _, _, c in AM.SINK.segs], fwd_T0=AM.FWD.T0, fwd_v0=AM.FWD.v0, fwd_seg_t0=[a for a, _, _ in AM.FWD.segs],
        fwd_seg_dur=[b for _, b, _ in AM.FWD.segs], fwd_seg_dv=[c for _, _, c in AM.FWD.segs],
        water_depth=[k['depth'] for k in W], water_density=[k['density'] for k in W],
        water_up=sum([k['up'] for k in W], []), water_mid=sum([k['mid'] for k in W], []), water_down=sum([k['down'] for k in W], []),
        caustics_colour=J['caustics']['colour'], caustics_depth0=0.0, caustics_depth1=15.0,
        sun_colour=J['sun']['colour_linear'], sun_E0=1.6, sun_depth1=15.0, sun_elevation=70.0, sun_azimuth=30.0,
        amb_sky=J['ambient_trilight']['sky'], amb_equator=J['ambient_trilight']['equator'], amb_ground=J['ambient_trilight']['ground'],
        win_gain_t=[k['t'] for k in J['sea']['window_gain']], win_gain_v=[k['v'] for k in J['sea']['window_gain']],
        core_desktop=J['sea']['window_core_desktop'], core_vr=J['sea']['window_core_vr'], erosion_t0=L['F2h'], erosion_t1=L['F5'], erosion_max=0.25,
        shaft_centre=sum([x['centre'] for x in sh['items']], []), shaft_axis=sum([x['axis'] for x in sh['items']], []),
        shaft_half_width=[x['half_width'] for x in sh['items']], shaft_length=[x['length'] for x in sh['items']],
        shaft_seed=[x['seed'] for x in sh['items']], shaft_alpha=[x['alpha'] for x in sh['items']],
        shaft_colour=sh['material']['colour'], shaft_depth_full=18.0, shaft_depth_gone=25.0,
        gather_t0=sh['gather']['t0'], gather_t1=sh['gather']['t1'], shafts_gone_t=467.6, gather_point_bus=sh['gather']['point_bus'],
        last_t0=ls['t_in'], last_in=ls['fade_in_s'], last_sweep=ls['sweep_s'], last_out=ls['fade_out_s'], last_half_width=ls['half_width'],
        last_length=ls['length'], last_alpha=ls['alpha'], last_from=ls['from_bus'], last_to=ls['to_bus'], last_target=ls['target_from_bus'], last_target_to=ls['target_to_bus'], last_top=ls['top_above_centre_m'],
        beam_angle=J['beam']['spot_angle_deg'], beam_range=J['beam']['range_m'], beam_gather_pos=J['beam']['gather']['pos_bus'],
        beam_gather_aim=J['beam']['gather']['aim_bus'], beam_gather_E=J['beam']['gather']['E_peak'], beam_last_E=J['beam']['last']['E_peak'],
        snow_sphere=SNOW_SPHERE, snow_box=SNOW_BOX, snow_lit=SNOW_LIT, snow_lit_d0=12.0, snow_lit_d1=30.0,
        warm_position=J['warm_point']['position_water'], warm_colour=J['warm_point']['colour'], warm_flux=J['warm_point']['flux'],
        warm_radius=J['warm_point']['radius_m'], warm_fade=J['warm_point']['fade_in_s'],
        warm_halo_radius=J['warm_point']['halo_radius_m'], warm_halo_flux=J['warm_point']['halo_flux'],
        ridge_base=J['ridge']['material']['base'], ridge_rim=J['ridge']['material']['rim'], ridge_reach=J['ridge']['material']['rim_reach_m'], ridge_near=J['ridge']['material']['rim_near_m'],
        ridge_wrap=J['ridge']['material']['rim_wrap'], ridge_face=J['ridge']['material']['rim_face'], ridge_edge=J['ridge']['material']['rim_edge'],
    )
    out = os.path.join(PKG, 'Act07_Layout.json')
    json.dump(J, open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('wrote', out, os.path.getsize(out) // 1024, 'KB; eye under at', tu, '; warm point', J['warm_point']['id'], J['warm_point']['distance_at_F5_m'], 'm')
    print('shafts', len(J['shafts']['items']), 'seeds births', J['particles']['seeds']['birth_t'][:3], '...', J['particles']['seeds']['birth_t'][-3:])


if __name__ == '__main__':
    main()
