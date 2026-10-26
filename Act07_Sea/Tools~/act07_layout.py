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


# ---------------------------------------------------------------------------------------------------- act 7c
def act7c():
    """第 7c 幕 · 海底即天 (F8 835.16 -> exit 922.36; bible §6·7c, D-23). Everything by TIME (the 7a keys go by depth).
    The mirror = the same Lanbai/Sea BELOW, flipped (M_07c_SeaMirror), a second Sea_Disc under R_Sea at the water y the EYE
    crosses at the exit (README_Sea接口 §5), centred under the bus (fwd is constant in 7c)."""
    tE = AM.EXIT
    plane_y = -AM.depth(tE) + float(EYE[1])
    deep = water_keys()[-1]
    neutral_down = np.array([0.040, 0.035, 0.060])          # D-23 layering (Sea K3 r17): looking down, a dark neutral
    fog = [
        (L['F8'], deep['density'], np.asarray(deep['up']), np.asarray(deep['mid']), np.asarray(deep['down'])),
        (L['F8b'], 0.018, fill('#04121E', 'S7b') * 0.75, fill('#04121E', 'S7b'), fill('#04121E', 'S7b')),
        (897.96, 0.010, srgb_lin('#3E2C2B') * 0.75, srgb_lin('#3E2C2B'), neutral_down),
        (L['F8c'], 0.009, srgb_lin('#3E2C2B') * 0.75, srgb_lin('#3E2C2B'), neutral_down),
        (921.4, 0.006, srgb_lin('#4B312C') * 0.75, srgb_lin('#4B312C'), np.array([0.050, 0.040, 0.062])),
    ]
    return dict(
        about='bible §6·7c + D-23; the sea kit look is M_07c_SeaMirror (Sea/SeaMaterials.json, K3 r17)',
        mirror=dict(object='Sea_Disc.fbx, second instance under R_Sea', water_y=round(plane_y, 3), water_z=round(AM.fwd(L['F8']), 3),
                    on_t=L['F8'], material='M_07c_SeaMirror', sea_mode=4,
                    note='on from F8 (the fog hides it until ~F8a: 110 m below at 0.018 / m is 87 % fog); the 7a surface plane goes off at F8'),
        wave_amp=keys((L['F8'], 0.3), (L['F8b'], 0.3), (L['F8b'] + 6.0, 0.09)),
        wave_note='bible F8b: the waves decay to 30 % in 6 s; the mirror keeps them x _MirrorWave 0.25 (the lamps settle into points)',
        window=keys((L['F8b'], 0.0), (897.96, 1.0)),
        window_note='x the material _WindowGain (0.25) and _WindowSunGain: the window settles at 897.96',
        fog=[dict(t=round(t, 2), density=d, up=R(u), mid=R(m), down=R(dn)) for t, d, u, m, dn in fog],
        fog_note='mid = the bible (#04121E -> #2E2228 fill #3E2C2B -> #3A2629 fill #4B312C), up = mid x 0.75, down = a dark neutral '
                 '(D-23 layering: the window indigo is not drowned in rose); the fog thins (bible F8c 雾在变薄): 0.018 -> 0.006 / m',
        caustics=dict(t0=L['F8c'], ramp_s=round(921.4 - L['F8c'], 2), direction=-1.0, colour=R(fill('#E2C08E', 'S7b')),
                      note='F8c: the caustics come from BELOW for the first time (bible §4.8), strength 0 -> 1 with the window\'s dusk, '
                           'F8c -> 921.4 (smoothstep; LanbaiCaustics.cginc header), gold #E2C08E h 80 (D-08: never rose)'),
        rose_lights=dict(positions_bus=[[0.0, 0.5, 4.6], [1.5, 0.3, 0.8]], colour_hex='#E7A0A0', range_m=7.0,
                         E=keys((L['F8b'], 0.0), (897.96, 0.8), (921.4, 1.1)),
                         culling='Bus + Player + PlayerLocal, no shadows, Not Important (folded into SH: free)',
                         note='bible: 1-2 realtime point lights under the bus turn rose, following the arc in the window (the arc is '
                              'forward, az 0): one low ahead of the windscreen, one low on the right. Grey-card check locally'),
        trilight=dict(sky=keys((L['F8'], 0.0), (921.4, 0.0)), sky_hex='#1A1C26', equator_hex='#2A2228',
                      ground=[dict(t=L['F8'], hex='#1A1422'), dict(t=921.4, hex='#3A1C18')],
                      note='bible §6·7c 光: Trilight ground #1A1422 -> #3A1C18 (7c end); sky / equator are not in the bible: a dark '
                           'neutral and the fog\'s rose (sRGB values for RenderSettings)'),
        apl_targets=dict(F8b=20, t897=30, t921_4=34),
        waterline=dict(entry=[round(L['F2h'] - 0.5, 2), round(L['F2h'] + 2.0, 2)], exit=[round(tE - 0.5, 2), round(tE + 1.0, 2)],
                       note='Lanbai/SeaWaterline on COPIES of the glass meshes (wired locally, README §0): on in these windows, '
                            '_WaterBelow +1 at the entry, -1 at the exit; it reads _Udon_SeaLevel (the clouds write it after the exit)'),
    )


# ---------------------------------------------------------------------------------------------------- shafts
_SUN_AZ, _SUN_TILT = math.radians(30.0), math.asin(math.sin(math.radians(20.0)) / 1.333)
SUN_AXIS = np.array([-math.sin(_SUN_TILT) * math.sin(_SUN_AZ), -math.cos(_SUN_TILT), -math.sin(_SUN_TILT) * math.cos(_SUN_AZ)])   # down, away from the sun
LAST_FOOT_FROM = np.array([0.8, 1.0, 14.0])        # P2: ahead, through the windscreen
LAST_FOOT_TO = np.array([0.2, 0.95, -1.5])         # onto the seats (past the main seat at ~0.2 of the way... the sweep crosses it)


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
    # P1 (D-44 #5): six shafts AHEAD of the bus at the F4p depth (12-26 m out, within the windscreen +-30 deg): when they
    # gather (453 -> F4p) the vertex shader slides them toward the skylight, so the convergence crosses the windscreen. Their
    # axis is the same refracted sun (az +30, el 70 in air: 14.9 deg off vertical, top toward the sun): only their POSITION
    # moves, the sun does not (总导演 10-25 #1); their tops fade out ahead (the shader's ends)
    eye_y_F4p = -AM.depth(L['F4p']) + EYE[1]
    for k in range(6):
        azk = math.radians(-30.0 + 12.0 * k + rng.uniform(-3.0, 3.0)); dk = rng.uniform(12.0, 26.0)
        out.append(dict(centre=R([EYE[0] + dk * math.sin(azk), eye_y_F4p + rng.uniform(-3.0, 3.0), EYE[2] + dk * math.cos(azk)], 3),
                        axis=R(axis, 5), half_width=round(rng.uniform(0.6, 1.4), 3), length=round(rng.uniform(28.0, 38.0), 2),
                        seed=round(rng.uniform(), 4), alpha=round(rng.uniform(0.06, 0.08), 4), note='F4p forward'))
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
SNOW_NEAR, SNOW_SPHERE, SNOW_BOX = 2.0, 10.0, 20.0
SNOW_LIT = 2.2
SNOW_LIT_DEEP = 1.3           # D-44 #5 P6: below 30 m the flakes stay a little brighter than the dark water (was x 1)


def snow(rng, n=2400):
    """海雪: 2 400 (总导演 10-24: up to 2x the bible's 1 200 in the near shell and toward the windscreen, the first 'in the
    sea' cue; min 1.5 px unchanged). Bible: 1 200 in a 25 m sphere (that gave ~2 flakes within 5 m of the eye and no sinking
    cue); here uniform in a 20 m wrap box, faded out by 10 m (the shader's sphere); 0.8-2.5 cm, screen
    #697987, alpha 0.3-0.6, sinking 1.5 cm/s (the bus sinks faster: they rise past the windows). WATER-frame positions at F3.
    The cabin is flooded in act 7, so a flake drifting through it is right; the shader's near fade keeps them off the eye."""
    c = fill('#697987', 'S7a')
    # UNIFORM in the wrap box: the shader recycles every flake through a box that rides with the bus, so any bias around
    # the eye slides away as the bus moves -- vertically every box height of descent, horizontally in 7b's 307 m forward
    # (r1-r2 biased a shell / a column around the eye: 0 flakes in view at 560 s). The density comes from the count and
    # the box: 2 400 in a 20 m box = 0.3 / m3 everywhere, at every moment (the bible's 1 200 in a 25 m sphere ~ 0.02)
    pts = EYE[None, :] + rng.uniform(-0.5, 0.5, (n, 3)) * SNOW_BOX
    pts = pts + np.array([0.0, -AM.depth(L['F3']), AM.fwd(L['F3'])])
    rad = rng.uniform(0.004, 0.0125, n)
    a = rng.uniform(0.3, 0.6, n)
    return dict(kind='SNOW', count=n, colour=R(c), positions=R(pts, 3), radius=R(rad, 5), alpha=R(a, 3), seed=R(rng.uniform(size=n), 4))


def seeds(rng, n=200):
    """播下的光: 200 births from F3i to F5, density rising toward ...die starben! (628-644: the densest), each a 0.2 s
    birth flash then a steady 12-15 % glow FIXED IN THE WATER; >= 5 m from the eye at birth, <= 3 cm, and never two flashes
    at once inside one 5 deg cone (checked here: a birth is moved later until it is clear). Colour = the bioluminescence
    #8AC6FF (fill #5E84FF @ +2.73). Positions: 60 % in the FORWARD field (az +-35, el -10..+5, 12-24 m: D-44 #5 P4 --
    born ahead, they rise across the windscreen as the bus sinks), the rest around and above the bus at its birth depth
    (by F5 '~200 still cold points around and overhead'). The 5 deg / 0.25 s birth rule is checked over all of them."""
    t0, t1 = L['F3i'], L['F5'] - 0.5
    u = rng.uniform(size=n * 3)
    ts = np.sort(t0 + (t1 - t0) * (1.0 - (1.0 - u) ** 0.55))[:n * 3]           # density rises toward the end
    ts = np.sort(rng.choice(ts, n, replace=False))
    births, dirs, pos = [], [], []
    for tb in ts:
        fwd_birth = rng.uniform() < 0.6
        for _ in range(200):
            if fwd_birth:              # P4 (D-44 #5): born in the forward field, then they rise across the windscreen as the bus sinks
                r = rng.uniform(12.0, 24.0)    # low and far: ~10 s to rise across the windscreen at ~1 m/s
                el = math.radians(rng.uniform(-10.0, 5.0)); az = math.radians(rng.uniform(-35.0, 35.0))
            else:
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


def trails_front(rng, n=270):
    """D-44 #5 P5: 30 % of the hull bioluminescence on the FRONT of the bus (just outside the face below and across the
    windscreen, z 3.70); the water streams up past a sinking bus, so they flow UP the windscreen, along the body's surface
    (the shader moves them by -_Udon_SeaBusVel x age: straight up while there is no forward speed). The main eye's +-10 deg
    (x 0.28 .. 0.82 at the glass) gets only 10 % of the density (总导演 10-25 #3: not in front of the picture). A separate
    renderer because from F5 the bus moves forward and these would stream back THROUGH the glass: the driver fades them
    out over the 5 s before F5. Born y 0.5 .. 1.2 (below the windscreen), life 1.5 - 3 s at 1-1.5 m/s = over the glass."""
    pts = []
    while len(pts) < n:
        x = rng.uniform(-0.95, 0.95)
        if 0.28 < x < 0.82 and rng.uniform() > 0.1:
            continue
        pts.append([x, rng.uniform(0.5, 1.2), 3.70])           # 0.2 m off the front face: the shader jitters +-0.125
    return dict(kind='TRAIL', count=n, colour=R(srgb_lin(BIO_FILL, 2.73)), positions=R(np.array(pts), 3),
                radius=R(rng.uniform(0.005, 0.015, n), 5), phase=R(rng.uniform(size=n), 4), life=R(rng.uniform(1.5, 3.0, n), 3),
                seed=R(rng.uniform(size=n), 4), T0=L['F4'], rate=90.0, pool=n, alpha=1.0, fade_out=[round(L['F5'] - 5.0, 2), L['F5']])


def trails(rng):
    """船体生物荧光 (F4 on): 300 births / s, life 1.5-3 s, 1-3 cm with a soft glow, screen #8AC6FF (fill #5E7AFF @ +2.73);
    a pool of 900 quads at hull points (BUS frame); the shader streams them back with the water (-_Udon_SeaBusVel x age)"""
    n = 630                                        # + 270 on the front (trails_front, D-44 #5 P5): 900 as before
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
                seed=R(rng.uniform(size=n), 4), T0=L['F4'], rate=210.0, pool=n, alpha=1.0)


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
RIDGE_YAW = -55.0             # P3: the nearest part from abeam (az 90) to ahead-right (az +35)
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
    # P3 (D-44 #5): turned about the bus's vertical axis (water x = z = 0) so the nearest part is ahead-right (az +35 from the
    # eye) instead of abeam: it rises across the right of the windscreen. Turned, the eye (0.55, 2.05 off the axis) comes
    # closer, so the wall is pushed out until every vertex is >= 12.2 m from the eye (the bible's >= 12 m; it sinks past
    # vertically, so the relative speed is still 1.5 m/s). Local x' = x cos(yaw) + z sin(yaw), z' = -x sin(yaw) + z cos(yaw)
    yaw = math.radians(RIDGE_YAW)
    push = 0.0
    for _ in range(200):
        Xr = (X + push) * math.cos(yaw) + Z * math.sin(yaw); Zr = -(X + push) * math.sin(yaw) + Z * math.cos(yaw)
        dmin = float(np.min(np.hypot(Xr - EYE[0], Zr - EYE[2])))
        if dmin >= 12.2:
            break
        push += 0.1
    X = X + push
    return dict(frame='WATER', yaw_deg=RIDGE_YAW, pushed_out_m=round(push, 2), min_dist_from_eye_m=round(dmin, 2),
                yaw_note='vertices: x\' = x cos(yaw) + z sin(yaw), z\' = -x sin(yaw) + z cos(yaw) about the water origin (the bus axis); '
                         'nearest part at az +35 from the main eye (D-44 #5 P3)',
                x_min_m=round(float(X.min()), 3), grid=dict(z0=-45.0, dz=1.0, nz=len(zs), y0=-135.0, dy=1.0, ny=len(ys)),
                x=R(X, 3), back_thickness_m=6.0,
                material=dict(shader='Lanbai/SeaRidge', base=R(fill('#0B1A26', 'S7b') * 0.8), rim=R(srgb_lin('#8AC6FF') * 2.4),
                              rim_reach_m=14.0, rim_near_m=22.0, rim_wrap=0.55, rim_face=0.02, rim_edge=4.0,
                              note='low contrast: the faces sit just above the water fog of 105 m; only the silhouettes catch the '
                                   'hull bioluminescence #8AC6FF (bible: 只被船体生物荧光描出一道边), full strength out to rim_near_m, '
                                   'falling off over rim_reach_m beyond; wrap: the trails run along the whole hull. 10-25 (总导演, 阿白 0949: '
                                   '"描边要读得出来"): after the P3 turn the visible ridge is 12-27 m away, so full strength out to 22 m, rim x 2, '
                                   'faces halved (rim_face 0.02) so the faces stay where they were and only the edge reads'),
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
    # the nearest lamp SEEN from the main seat at F5 and through its 3 s fade-in:
    #  * through the windscreen of the REAL bus (PAZ-672): the bus package's viewcheck grid Bus/Docs~/viewcheck/
    #    hero_occlusion.npz (0.25 deg, from the main eye), every cell within 1 deg of the lamp must be WindscreenL / R
    #    (10-26: the old bible_v2 rule picked Lamp_L01 at el -13.5, which in the PAZ bus is behind the cowl);
    #  * not behind a que: the palace's que body (que.py round 10: half-widths 3.95 x 5.95 m, 40 m high) as a box.
    # Without the grid (a checkout without Bus/) the old bible_v2 window box is the fallback.
    grid = os.path.join(REPO, 'Bus', 'Docs~', 'viewcheck', 'hero_occlusion.npz')
    if os.path.exists(grid):
        G = np.load(grid, allow_pickle=True)
        gids, gaz, gel = G['ids'], G['az'], G['el']
        wins = json.loads(str(G['windows']))
        glass_ids = {-(wins.index(w) + 2) for w in ('WindscreenL', 'WindscreenR')}

        def through(az, el):
            ii = np.clip(np.searchsorted(gel, [el - 1.0, el + 1.0]), 0, len(gel) - 1)
            jj = np.clip(np.searchsorted(gaz, [az - 1.0, az + 1.0]), 0, len(gaz) - 1)
            cells = gids[ii[0]:ii[1] + 1, jj[0]:jj[1] + 1]
            return cells.size > 0 and all(int(c) in glass_ids for c in cells.ravel())
    else:
        def through(az, el):
            return -50.0 < az < 25.0 and -14.5 < el < 22.0 and abs(az + 11.0) >= 2.0

    def behind_que(e, p):
        d = p - e
        for q in PF['que']:
            lo = np.array([q['pos'][0] - 3.95, 0.0 - td, q['pos'][2] - 5.95 + AM.fwd(L['F5'])])
            hi = np.array([q['pos'][0] + 3.95, q['height_m'] - td, q['pos'][2] + 5.95 + AM.fwd(L['F5'])])
            t0, t1 = 0.0, 1.0
            for k in range(3):
                if abs(d[k]) < 1e-9:
                    if e[k] < lo[k] or e[k] > hi[k]:
                        t0, t1 = 1.0, 0.0
                    continue
                u, v = sorted(((lo[k] - e[k]) / d[k], (hi[k] - e[k]) / d[k]))
                t0, t1 = max(t0, u), min(t1, v)
            if t0 <= t1:
                return True
        return False

    best = None
    for lp in PF['lamps']:
        p = np.array(lp['flame_pos']) + np.array([0.0, -td, AM.fwd(L['F5'])])
        dv = p - (busw + EYE)
        dist = np.linalg.norm(dv)
        az, el = math.degrees(math.atan2(dv[0], dv[2])), math.degrees(math.asin(dv[1] / dist))
        if not through(az, el):
            continue
        if any(behind_que(np.array([0.0, -AM.depth(t), AM.fwd(t)]) + EYE, p) for t in np.arange(L['F5'], L['F5'] + 3.01, 0.5)):
            continue
        if best is None or dist < best[0]:
            best = (dist, lp['id'], p, az, el)
    return dict(id=best[1], position_water=R(best[2], 3), distance_at_F5_m=round(best[0], 2), az_el_at_F5=[round(best[3], 1), round(best[4], 1)],
                picked_by='PAZ-672 viewcheck grid (1 deg margin) + que bodies' if os.path.exists(grid) else 'bible_v2 window box (fallback)',
                t_on=L['F5'], fade_in_s=3.0,
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
        labels={k: dict(t=L[k], source=AM.LSRC[k]) for k in ('F2h', 'F3', 'F4', 'F4p', 'F3e', 'F3e1', 'F3e2', 'F3e3', 'F3i', 'F5', 'F8', 'F8a', 'F8b', 'F8c', 'F8r', 'F9s')},
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
                    last_shaft=dict(t_in=round(L['F3e1'] - 2.0, 2), fade_in_s=2.0, sweep_s=4.0, fade_out_s=2.0, half_width=2.2, length=34.0, alpha=0.10,
                                    from_bus=R(LAST_FOOT_FROM - SUN_AXIS * 14.0, 3), to_bus=R(LAST_FOOT_TO - SUN_AXIS * 14.0, 3),
                                    target_from_bus=R(LAST_FOOT_FROM, 3), target_to_bus=R(LAST_FOOT_TO, 3),
                                    p2_note='D-44 #5 P2: PARALLEL to the refracted sun at both ends (the centre is 14 m up the sun axis from '
                                            'the foot, so foot - centre is constant): the sun never moves (总导演 10-25 #1); the foot '
                                            'sweeps from 14 m AHEAD (seen through the windscreen, the top fades out ahead-right toward '
                                            'the sun) over the roof onto the seats',
                                    t_note='10-25 (总导演, 阿白 0949): full strength ON the F3e1 beat -- in from F3e1 - 2 s, the 4 s sweep starts at '
                                           'F3e1 with the foot still ~14 m ahead in the windscreen, out by F3e1 + 6 s (the window\'s dark-coin curve still starts at F3e1)',
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
        particles=dict(snow=snow(rng), seeds=seeds(rng), trails=trails(rng), trails_front=trails_front(rng), bubbles=bubbles(rng),
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
        act7c=act7c(),
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
        turn_deg=AM.TURN_DEG, turn_t0=AM.TURN_T0, turn_t1=AM.TURN_T1, turn_dt=0.25,
        turn_drift=sum([[round(v, 4) for v in AM.drift(AM.TURN_T0 + 0.25 * i)] for i in range(int(round((AM.TURN_T1 - AM.TURN_T0) / 0.25)) + 2)], []),
        turn_note='F7 (D-34 #5 / D-49 #4 option C): the bus steers right into the stop; the driver turns R_Palace only (PalaceFrame_约定 bus_turn); drift = (x, z) pairs every turn_dt from turn_t0',
        snow_sphere=SNOW_SPHERE, snow_box=SNOW_BOX,
        # act 7c (README_Act07a §9)
        F8=L['F8'], F8b=L['F8b'], F8c=L['F8c'],
        c7_mirror_y=J['act7c']['mirror']['water_y'], c7_mirror_z=J['act7c']['mirror']['water_z'],
        c7_wave_t=[k['t'] for k in J['act7c']['wave_amp']], c7_wave_v=[k['v'] for k in J['act7c']['wave_amp']],
        c7_win_t=[k['t'] for k in J['act7c']['window']], c7_win_v=[k['v'] for k in J['act7c']['window']],
        c7_fog_t=[k['t'] for k in J['act7c']['fog']], c7_fog_density=[k['density'] for k in J['act7c']['fog']],
        c7_fog_up=sum([k['up'] for k in J['act7c']['fog']], []), c7_fog_mid=sum([k['mid'] for k in J['act7c']['fog']], []),
        c7_fog_down=sum([k['down'] for k in J['act7c']['fog']], []),
        c7_caus_t0=J['act7c']['caustics']['t0'], c7_caus_ramp=J['act7c']['caustics']['ramp_s'], c7_caus_colour=J['act7c']['caustics']['colour'],
        c7_rose_pos=sum(J['act7c']['rose_lights']['positions_bus'], []), c7_rose_range=J['act7c']['rose_lights']['range_m'],
        c7_rose_colour=R(srgb_lin(J['act7c']['rose_lights']['colour_hex'])),
        c7_rose_t=[k['t'] for k in J['act7c']['rose_lights']['E']], c7_rose_v=[k['v'] for k in J['act7c']['rose_lights']['E']],
        c7_tri_sky=R(srgb_lin(J['act7c']['trilight']['sky_hex'])), c7_tri_equator=R(srgb_lin(J['act7c']['trilight']['equator_hex'])),
        c7_tri_ground_t=[k['t'] for k in J['act7c']['trilight']['ground']],
        c7_tri_ground=sum([list(R(srgb_lin(k['hex']))) for k in J['act7c']['trilight']['ground']], []),
        wl_entry=J['act7c']['waterline']['entry'], wl_exit=J['act7c']['waterline']['exit'], snow_lit=SNOW_LIT, snow_lit_d0=12.0, snow_lit_d1=30.0, snow_lit_deep=SNOW_LIT_DEEP,
        trails_front_fade=[round(L['F5'] - 5.0, 2), L['F5']], ridge_yaw=RIDGE_YAW,
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
