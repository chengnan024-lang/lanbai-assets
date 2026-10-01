"""蓝白 / Lanbai · 触手之门 v2 · timeline, layout and poses (numpy; imported by gate_scene.py).

FRAMES
  CF (cloud frame, used for everything here and as the Blender world of every render):
      origin = the tear's foot = lens axis x cloud-top plane; x = right (seen from the bus), y = away from
      the bus (the bus drives toward +y), z = up; z = 0 is the cloud-sea top. Metres.
  GateRoot local (Unity): origin = the ENTRY POINT = CF (0, 0, ENTRY_H) (where the bus origin passes the tear
      plane at U9); Unity axes x right, y up, z forward (away from the bus). unity = (cx, cz - ENTRY_H, cy).
  Unity world (bus fixed at the origin facing +Z): GateRoot.position(t) = (0, gate_y(t), gate_z(t)).
  Library meshes: Blender local (x, y, z) -> Unity mesh local B2U @ v = (-x, z, -y) (lib/export_unity.py).
"""
import json
import math
import zlib
import os
import pickle
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
LAN = os.path.dirname(HERE)
for p in (os.path.join(LAN, 'tentacles', 'final'), os.path.join(LAN, 'tear', 'v2'), os.path.join(LAN, 'lib')):
    if p not in sys.path:
        sys.path.insert(0, p)
import build_library as BL      # noqa: E402  tentacle library v2.1 (centrelines, variant tubes, preview material)
import tear_def as TD           # noqa: E402  tear kit v2 geometry
import arms4 as A4              # noqa: E402  round 3: custom-centreline gate arms (patches BL.variant_parts)

WIP = os.path.join(HERE, 'wip')
os.makedirs(WIP, exist_ok=True)

# gate-only variant 'K' (round 2): 'der Engel', a shepherd's crook. H's body, skin and frayed end, but it rises,
# hooks over through ~160 deg and lets its last third HANG (the end at half its height): the giant bending over the
# wound. Baked per instance like every gate arm (GateArms_v2.fbx); material / occlusion = H's (TEX_KEY).
import copy as _copy
if 'K' not in BL.VARIANTS:
    _K = _copy.deepcopy(BL.VARIANTS['H'])
    _K.update(phase=0.311, vofs=0.27,
              bends=[(0.05, 0.06, 10, 280), (0.30, 0.20, 16, 95), (0.56, 0.12, 82, 92), (0.70, 0.12, 78, 96)],
              helix=dict(u0=0.10, u1=0.60, turns=0.45, a=0.05, ease=0.15, grow=0.4, hand=-1),
              tips=[dict(u0=0.88, u1=0.975, deg=55, psi=200, twist=30, p=1.4)])
    BL.VARIANTS['K'] = _K
TEX_KEY = {'K': 'H'}

# ============================================================================================ timeline
CUE = dict(U6k=129.10, U6=133.80, U7=150.30, U7b=155.10, U8=166.15, U8b=167.90, U8c=171.40, U9=179.55,
           U10=185.95, U11=202.40, U12=248.64)
V_G = 2700.0 / (CUE['U9'] - CUE['U6'])          # 59.02 m/s, constant from U6 to U9 (bible 3->4: already 60 m/s)
ENTRY_H = 150.0                                   # bus origin above the cloud top at U9 = 15 % of H(U9) = 1000 m
CLIMB_T0 = CUE['U9'] - 19.05                      # 160.50: 60 -> 150 m smoothstep; peak 6*90/19.05^2 = 1.49 m/s^2
EYE_SEATED = np.array([0.55, 1.70, 2.05])         # Unity, bus-relative (hero seat, generic shell, see gate_bus.py)
EYE_STAND_REAR = np.array([0.0, 1.95, -2.75])     # in the aisle, leaning over the rear bench toward the rear window
EYE_AISLE = np.array([0.05, 2.0, -1.6])           # standing in the aisle behind the hero seat (U8b)


def ss(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


BAND_EL = (12.0, 34.0, 5.0)     # round 3 (critique B7.2): full to ~+13, 0.37 at +18, 0.17 at +20, 0.002 at +26, void by +34
S4_RAMP = 30.0                  # bible 3 -> 4: S4 (and the band) rise with a 30 s smoothstep from U6


def band_ramp(t):
    """how far the luminous band has come up (bible 3 -> 4: S4 smoothstep over 30 s from U6); 0 before U6."""
    return float(ss((t - CUE['U6']) / S4_RAMP))


def band_el(el):
    """vertical profile of the luminous haze band: (1 - smoothstep(lo, hi, el))^pw (BAND_EL), the same in Lanbai/Sky,
    LanbaiFog.cginc and Lanbai_TentacleSway (_BandEl = (lo, hi, pw))."""
    lo, hi, pw = BAND_EL
    el = np.asarray(el, float)
    return (1.0 - ss((el - lo) / (hi - lo))) ** pw


def gate_z(t):
    """GateRoot.z(t) (Unity world): distance from the bus to the tear plane. Linear = constant v_g."""
    return V_G * (CUE['U9'] - t)


def h_bus(t):
    """bus origin (Unity y 0) above the cloud-sea top. Bible: U6 40 m -> U8 ~60 m -> U9 150 m. The last climb
    is stretched to 19.05 s so its smoothstep peak acceleration is 1.49 m/s^2 (bible 1.8: <= 1.5)."""
    if t <= CUE['U6']:
        return 40.0
    if t < CLIMB_T0:
        return 40.0 + 20.0 * float(ss((t - CUE['U6']) / (CLIMB_T0 - CUE['U6'])))
    return 60.0 + 90.0 * float(ss((t - CLIMB_T0) / (CUE['U9'] - CLIMB_T0)))


def gate_y(t):
    """GateRoot.y(t) (Unity world) = ENTRY_H - h_bus(t): the cloud top is at world y = -h_bus(t)."""
    return ENTRY_H - h_bus(t)


# tear height above the cloud top: solved so the TOP of the tear sits at the bible's screen elevations at the
# measured cue distances (U6 +11.0 deg, U7 +18.0 deg, U8 +42.2 deg), then 1000 m at the entry; monotone PCHIP.
_H_KNOTS = [(CUE['U6'], 565.0), (CUE['U7'], 616.0), (CUE['U7b'], 640.0), (160.5, 715.0), (CUE['U8'], 799.0),
            (CUE['U9'], 1000.0)]     # round 3 (tech minor): + (160.5, 715): near-linear growth U7b -> U8


def tear_H(t):
    from scipy.interpolate import PchipInterpolator
    xs, ys = zip(*_H_KNOTS)
    return float(PchipInterpolator(xs, ys, extrapolate=False)(np.clip(t, xs[0], xs[-1])))


def tear_open(t):
    """_Udon_TearOpen: width 18 % (U6) -> 22 % (U7) -> 30 % (U8) of H, smoothstep between the phrases."""
    if t <= CUE['U6']:
        return 0.0
    if t < CUE['U7']:
        return 0.333 * float(ss((t - CUE['U6']) / (CUE['U7'] - CUE['U6'])))
    if t < CUE['U8']:
        return 0.333 + 0.667 * float(ss((t - CUE['U7']) / (CUE['U8'] - CUE['U7'])))
    return 1.0


def rip_progress(t):
    """_Udon_RipProgress: the two branch rips run open from U7 over 16 s (<= 0.5 deg/s)."""
    return float(ss((t - CUE['U7']) / 16.0))


def eye_cf(t, eye=EYE_SEATED):
    """Unity bus-relative eye -> CF at time t."""
    return np.array([eye[0], eye[2] - gate_z(t), eye[1] + h_bus(t)])


def bus_to_cf(p, t):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2] - gate_z(t), p[..., 1] + h_bus(t)], -1)


def cf_to_unity_local(p):
    p = np.asarray(p, float)
    return np.stack([p[..., 0], p[..., 2] - ENTRY_H, p[..., 1]], -1)


M_W = np.array([[1.0, 0, 0], [0, 0, 1.0], [0, 1.0, 0]])          # CF / Blender world axes -> Unity axes
B2U = BL.B2U                                                        # Blender mesh local -> Unity mesh local


def rot_to_unity(R_cf):
    """rotation of a library mesh (Blender local -> CF) -> Unity rotation of the imported FBX mesh."""
    return M_W @ R_cf @ B2U.T


def quat_from_matrix(R):
    """(x, y, z, w) of a proper rotation matrix."""
    q = BL._quat_from_matrix(R)
    return q


# ============================================================================================ small math
def rodrigues(axis, ang):
    a = np.asarray(axis, float)
    a = a / np.linalg.norm(a)
    K = np.array([[0, -a[2], a[1]], [a[2], 0, -a[0]], [-a[1], a[0], 0]])
    return np.eye(3) + math.sin(ang) * K + (1 - math.cos(ang)) * (K @ K)


def rot_between(a, b):
    a = np.asarray(a, float) / np.linalg.norm(a)
    b = np.asarray(b, float) / np.linalg.norm(b)
    v = np.cross(a, b)
    s = np.linalg.norm(v)
    c = float(np.dot(a, b))
    if s < 1e-9:
        if c > 0:
            return np.eye(3)
        perp = np.cross(a, [1, 0, 0]) if abs(a[0]) < 0.9 else np.cross(a, [0, 1, 0])
        return rodrigues(perp, math.pi)
    return rodrigues(v / s, math.atan2(s, c))


def unit(v):
    v = np.asarray(v, float)
    return v / np.linalg.norm(v, axis=-1, keepdims=True)


def dir_azel(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.sin(a) * math.cos(e), math.cos(a) * math.cos(e), math.sin(e)])


def azel_of(v):
    v = np.asarray(v, float)
    az = np.degrees(np.arctan2(v[..., 0], v[..., 1]))
    el = np.degrees(np.arctan2(v[..., 2], np.hypot(v[..., 0], v[..., 1])))
    return az, el


MOON_AZ, MOON_EL = -12.0, 8.0
L_MOON = dir_azel(MOON_AZ, MOON_EL)


# ============================================================================================ variant geometry
_PARTS = {}


def parts(key, lod=1):
    """[(centres (n,3), radii (n,), u (n,)), ...] of a library variant (Blender local), cached on disk."""
    k = (key, lod)
    if k in _PARTS:
        return _PARTS[k]
    if A4.is_custom(key):
        ps, _ = BL.variant_parts(key, lod)
        _PARTS[k] = [(p['C'].copy(), p['r'].copy(), p['ur'].copy()) for p in ps]
        return _PARTS[k]
    fn = os.path.join(WIP, 'parts_%s_%d.pkl' % (key, lod))
    if os.path.exists(fn):
        _PARTS[k] = pickle.load(open(fn, 'rb'))
        return _PARTS[k]
    ps, _ = BL.variant_parts(key, lod)
    out = [(p['C'].copy(), p['r'].copy(), p['ur'].copy()) for p in ps]
    pickle.dump(out, open(fn, 'wb'))
    _PARTS[k] = out
    return out


def cl_points(key, step=12):
    cl = BL.centreline(key)
    return cl['P'][::step], cl['u'][::step]


# ============================================================================================ instances
def aim_rotation(key, root, scale, chord_dir, tip_target, roll_jitter=0.0, tip_from=0.86):
    """R (Blender local -> CF) whose chord (root -> tip) points along chord_dir and whose END (last 14 %) is
    rolled to point most nearly at tip_target (+ jitter, deg)."""
    P = BL.centreline(key)['P']
    ch = unit(P[-1] - P[0])
    d = unit(chord_dir)
    R0 = rot_between(ch, d)
    i = int(tip_from * (len(P) - 1))
    tipT0 = unit(P[-1] - P[i])
    best, broll = -9.0, 0.0
    for r_ in range(0, 360, 4):
        R = rodrigues(d, math.radians(r_)) @ R0
        tp = np.asarray(root) + scale * (R @ P[-1])
        s_ = float(np.dot(R @ tipT0, unit(np.asarray(tip_target) - tp)))
        if s_ > best:
            best, broll = s_, float(r_)
    return rodrigues(d, math.radians(broll + roll_jitter)) @ R0


# ---------------------------------------------------------------------------------------------- arm form v3
# Round 2 (critique B2): the run-2 girth (g - 1)(1 - t)^1.5 made monotonic cones (horns, tusks). Now:
#   r(t) = r_lib(t) x (1 + (g - 1) P(t)) x W(t) x (1 + ridges + ellipse)
#   P(t) = 0.55 (1 - t)^2 + 0.45 exp(-((t - 0.22) / 0.12)^2)      a broad root + a muscular belly at 22 % of the arc
#   W(t) = K_GATE(t) / RAD_K(t)                                    the neck falls to ~30 % of the root by t 0.70 and
#                                                                  the whip is 2-3x the library thread (3-8 px at
#                                                                  1.5 km), tapering smoothly to the end
#   ridges  = 0.04 sin(3 theta + 2 pi turns t + rph)               three muscle bundles twisting 0.4-0.7 turn
#   ellipse = 0.11 cos(2 (theta - eph - pi turns t))               a 1 : 0.8 cross-section rotating with the twist
# (ridges + ellipse fade out over the neck, t 0.60 -> 0.80). theta = 2 pi UVMap.x. Baked per instance into the
# delivered meshes (GateArms_v2.fbx), so Unity needs no _Girth.
K_GATE = [(0.00, 1.00), (0.05, 1.06), (0.15, 1.00), (0.30, 0.90), (0.45, 0.76), (0.57, 0.58), (0.65, 0.42),
          (0.71, 0.31), (0.76, 0.25), (0.81, 0.20), (0.86, 0.16), (0.91, 0.115), (0.95, 0.075), (0.98, 0.035),
          (1.00, 0.006)]
_KG = None


def belly(t):
    t = np.clip(np.asarray(t, float), 0.0, 1.0)
    return 0.55 * (1.0 - t) ** 2 + 0.45 * np.exp(-((t - 0.22) / 0.12) ** 2)


def whip_mult(t):
    global _KG
    if _KG is None:
        _KG = (BL._pchip(K_GATE), BL._pchip(BL.RAD_K))
    t = np.clip(np.asarray(t, float), 0.0, 1.0)
    return np.maximum(_KG[0](t) / np.maximum(_KG[1](t), 1e-4), 1.0)


def form_mult(t, g, key=None):
    """r_gate / r_lib along the arc (without ridges / ellipse). Custom (v4) arms carry their whole form in the
    centreline radius (arms4.rad4): 1."""
    if key is not None and A4.is_custom(key):
        return np.ones_like(np.asarray(t, float))
    return (1.0 + (float(g) - 1.0) * belly(t)) * whip_mult(t)


def arm_radius(it, u):
    """skin radius (m) of an instance at arc fraction u (ridges / ellipse excluded)."""
    k = it['variant']
    return A4.rel_radius(k, u) * BL.VARIANTS[k]['R'] * it['scale'] * form_mult(u, it.get('girth', 1.0), k)


def diameter_ratio(it):
    """max diameter : length (the critique's 1:9 - 1:12)."""
    u = np.linspace(0, 1, 401)
    return float(2 * arm_radius(it, u).max() / (BL.VARIANTS[it['variant']]['L'] * it['scale']))


def inst(id_, layer, key, root, R, scale, lod=0, phase=None, anim=None, frame='gate', note='', girth=1.0, gp=None):
    rng = np.random.default_rng(zlib.crc32(id_.encode()))
    ph = float(rng.random()) if phase is None else float(phase)
    form = dict(turns=float(rng.uniform(0.2, 0.4) * (1 if rng.random() < 0.5 else -1)),
                rph=float(rng.uniform(0, 2 * math.pi)), eph=float(rng.uniform(0, math.pi)))
    return dict(id=id_, layer=layer, variant=key, root=np.asarray(root, float), R=np.asarray(R, float),
                scale=float(scale), lod=lod, girth=float(girth), form=form, phase=ph,
                anim=anim or [], frame=frame, note=note)


def angular_height(it, t, eye=None):
    """apparent height (deg) of the risen instance from the eye at time t."""
    e = eye_cf(t) if eye is None else eye
    P, u = cl_points(it['variant'], 30)
    W = it['root'] + it['scale'] * (P @ it['R'].T)
    W = W[W[:, 2] > 0]
    if len(W) == 0:
        return 0.0
    az, el = azel_of(W - e)
    return float(el.max() - max(el.min(), azel_of(np.array([W[0, 0], W[0, 1], 0.0]) - e)[1]))


def fit_rise(it, t0, vmax, t_min_end=None):
    """set the instance's rise so its own angular speed stays <= vmax deg/s (smoothstep peak = 1.5 x mean)."""
    for a in it['anim']:
        if a['type'] == 'rise':
            ang = angular_height(it, t0)
            dur = max(1.5 * ang / vmax, 4.0)
            a['t0'] = t0
            a['t1'] = t0 + dur
            if t_min_end is not None and a['t1'] < t_min_end:
                a['t1'] = t_min_end
    return it


def prof(x, kind='ss', e=0.2):
    """motion profile 0 -> 1. 'ss' = smoothstep (peak speed 1.5 x mean); 'trap' = trapezoidal velocity (constant
    speed with eases of fraction e at both ends: peak = mean / (1 - e))."""
    x = float(np.clip(x, 0.0, 1.0))
    if kind == 'beta':                 # fast early (far away), slow late (close): s = 1 - (1-x)^b (1 + b x)
        b = e if e > 1.0 else 3.5          # (ds/dx = b (b+1) x (1-x)^(b-1); peak at x = 1/b, ~1.9 x mean for b 3.5)
        return 1.0 - (1.0 - x) ** b * (1.0 + b * x)
    if kind == 'trap':
        vm = 1.0 / (1.0 - e)
        if x < e:
            return vm * x * x / (2 * e)
        if x > 1 - e:
            return 1.0 - vm * (1 - x) ** 2 / (2 * e)
        return vm * (x - e / 2)
    return float(ss(x))


def anim_s(a, t):
    return prof((t - a['t0']) / max(a['t1'] - a['t0'], 1e-6), a.get('prof', 'ss'), a.get('ease', 0.2))


def pose_at(it, t):
    """(root CF, R) of an instance at time t: rise = translate up out of the cloud; lean = rotate about the root
    (R is the FINAL pose; before / during a lean the arm is rotated back by deg x (1 - s)); close = lean in over the
    road after the bus has passed; drift = bus-relative arms."""
    root = it['root'].copy()
    R = it['R'].copy()
    for a in it['anim']:
        if a['type'] == 'drift':           # bus-relative arms: slide along +y (CF) at v m/s relative to the bus
            root[1] += a['v'] * (t - a['t_ref'])
            continue
        if a['type'] not in ('rise', 'lean'):
            continue
        s = anim_s(a, t)
        if a['type'] == 'rise':      # v4: along a direction (default straight up): an arm slides out along its own axis
            root -= np.asarray(a.get('dir', (0.0, 0.0, 1.0)), float) * a['depth'] * (1 - s)
        elif a['type'] == 'lean':
            R = rodrigues(a['axis'], -math.radians(a['deg']) * (1 - s)) @ R
    for a in it['anim']:                   # keyed tracking rotation about the root (colossus 2 holding the moon)
        if a['type'] == 'track':
            ks = a['keys']
            if t <= ks[0][0]:
                rv = np.asarray(ks[0][1], float)
            elif t >= ks[-1][0]:
                rv = np.asarray(ks[-1][1], float)
            else:
                j = max(i for i in range(len(ks)) if ks[i][0] <= t)
                f = float(ss((t - ks[j][0]) / (ks[j + 1][0] - ks[j][0])))
                rv = (1 - f) * np.asarray(ks[j][1], float) + f * np.asarray(ks[j + 1][1], float)
            ang = float(np.linalg.norm(rv))
            if ang > 1e-9:
                R = rodrigues(rv / ang, ang) @ R
    for a in it['anim']:                   # after the bus has passed: lean in over the road behind it (Orpheus)
        if a['type'] == 'close':
            R = rodrigues(a['axis'], math.radians(a['deg']) * anim_s(a, t)) @ R
    if it['frame'] == 'bus':               # x, y relative to the bus origin (moves with the bus); z relative to the
        root = root + np.array([0.0, -gate_z(t), 0.0])   # cloud-sea top (rooted in the cloud while the bus climbs)
    return root, R


def fog_scale_at(it, t):
    """per-instance LanbaiFog density scale at time t (the 'haze clears' reveal: Udon drives the layer
    material's _FogDensityScale through these keys, linear in time, smoothstep-eased)."""
    for a in it['anim']:
        if a['type'] == 'fog':
            ks = a['keys']
            if t <= ks[0][0]:
                return ks[0][1]
            for (t0, v0), (t1, v1) in zip(ks[:-1], ks[1:]):
                if t <= t1:
                    return v0 + (v1 - v0) * float(ss((t - t0) / max(t1 - t0, 1e-6)))
            return ks[-1][1]
    return it.get('fog', 1.0)


def world_centreline(it, t, step=12):
    root, R = pose_at(it, t)
    P, u = cl_points(it['variant'], step)
    return root + it['scale'] * (P @ R.T), u



# ============================================================================================ the layout (v4 · round 3)
# ---------------------------------------------------------------------------------------------------- v4 (round 3)
# Director's notes, round 3 (critique_awe_r2 / critique_tech_r2). ONE image; everything that does not serve it is cut.
# Few huge things and many tiny ones, nothing medium:
#   1. RIGHT GATE PILLAR close and dominant (0.5 km at az +30 at U7b, GateRoot local (+262, -1005)): it breaches as a
#      hump, leaves the cloud leaning in over the road and arches over it; its crown is always beyond the frame top.
#      LEFT PILLAR far (0.85 km, az -40, local (-546, -792)): only its whip comes into the key frame from the top left.
#   2. TWO HAND BUNDLES, unequal (left 600-700 m, nearer; right 450-550 m): braided forearms (3 fingers winding 0.6
#      turn, touching) rooted 250-400 m in front of the lens, leaving the cloud leaning ~40 deg toward the wound; the
#      upper third curls over and DOWN and the fingertips HOOK the flaps (left curl at 15-25 % H, right peel at
#      35-60 % H) at the tear plane, so the grip is physical (it survives the approach and VR parallax).
#   3. THE ENGEL: 2.2 km long, rooted 2.7 km away at az +24 in the band, leaning over the wound toward you; its crest
#      leaves the frame top, its last quarter hangs IN FRONT of the lens (local z -100) over the upper third / right lip.
#   4. Colossus 2 takes the moon (custom, its round side to the camera); colossus 1 behind the Rilke line;
#      6 background giants whose bodies stay inside the band (el <= 13 deg).
#   5. The SURGE RING: 22 small arms (200-350 m) at 2.5-4 km in the band (az +-8..+-55), all leaning toward the wound.
# No flame bundles, no side ring, no forks beyond 300 m (only the near arms keep the library's forked tips).
# Reveal (critique B8 / tech B1): GateRoot is switched on under the white cloud (U6 - 20 s); the giants are already
# standing, hidden inside towering cumulus (gate_layout.TOWERS) and by _Reveal = 0; the band brightens with S4
# (U6 -> U6 + 30 s smoothstep). Hands rise crown-first after a dome; the surge ring and the tide rise from U7.
T_HERO = CUE['U7b']
LAYOUT_CACHE = os.path.join(WIP, 'layout_v4.pkl')
E_HERO = eye_cf(T_HERO)


def at_az(az, d, z=0.0, eye=None):
    e = E_HERO if eye is None else eye
    a = math.radians(az)
    return np.array([e[0] + d * math.sin(a), e[1] + d * math.cos(a), z])


def tear_foot_cf():
    return np.zeros(3)


def tear_core_cf(t):
    """the white's centre: widest point of the lens (40 % of the height), a little behind the cloth."""
    S = tear_H(t) / TD.H
    return TD.P(TD.T_W, float(TD.path(np.array([TD.T_W]))[0]), 60.0)[()] * S


def tear_half_width(t):
    return 0.5 * (0.18 + 0.12 * tear_open(t)) * tear_H(t)


def lip_point(t, zf, side, out=0.0, y=-20.0):
    """a point on the left (side -1) / right (+1) lip at height fraction zf of H, pushed `out` m outward."""
    S = tear_H(t) / TD.H
    w = TD.width_mul(tear_open(t))
    tt = zf * TD.T_TOP
    aL, aR = TD.lips(np.array([tt]))
    a = float((aR[0] if side > 0 else aL[0]) * w) + side * out / S
    p = TD.P(tt, a, 0.0)[()] * S
    p[1] = y
    return p


def world_pts(key, root, R, scale, step=10):
    P, u = cl_points(key, step)
    return np.asarray(root) + scale * (P @ R.T), u


def _tear_avoid(eye, t, u_ok, w=6.0, rad=3.0):
    """keep the BODY (u < u_ok) off the white: sample points along the lens axis (screen avoid discs)."""
    Hh = tear_H(t)
    out = []
    for zf in (0.03, 0.15, 0.28, 0.42, 0.56, 0.70, 0.84):
        pa = TD.P(zf * TD.T_TOP, 0.0, 0.0)[()] * (Hh / TD.H)
        a_, e_ = azel_of(pa - eye)
        out.append((float(a_), float(e_), rad, 0.0, u_ok, w))
    for zf in (0.92, 1.0, 1.08):          # the needle tip stays clear for everyone
        pa = TD.P(zf * TD.T_TOP, 0.0, 0.0)[()] * (Hh / TD.H)
        a_, e_ = azel_of(pa - eye)
        out.append((float(a_), float(e_), 2.2, 0.0, 1.0, w))
    return out


def _score(W, u, eye, want, L3):
    az, el = azel_of(W - eye)
    s = 0.0
    if 'floor' in want:
        bad = (u > 0.2) & (W[:, 2] < want['floor'])
        s -= 30.0 * bad.mean()
    if 'crown' in want:
        a, e, w = want['crown']
        k = int(np.argmax(el))
        s -= w * (((az[k] - a) / 2.0) ** 2 + ((el[k] - e) / 2.0) ** 2) ** 0.5
    if 'tip' in want:
        a, e, w = want['tip']
        s -= w * (((az[-1] - a) / 2.0) ** 2 + ((el[-1] - e) / 2.0) ** 2) ** 0.5
    if 'tip3' in want:                 # world-space tip target (m)
        p, w = want['tip3']
        s -= w * float(np.linalg.norm(W[-1] - np.asarray(p))) / 40.0
    if 'tipdir' in want:
        p, w = want['tipdir']
        d = W[-1] - W[-5]
        d = d / (np.linalg.norm(d) + 1e-9)
        g = np.asarray(p) - W[-1]
        g = g / (np.linalg.norm(g) + 1e-9)
        s += w * float(d @ g)
    if 'profile' in want:
        ds = np.hypot(np.diff(az) * np.cos(np.radians(el[:-1])), np.diff(el)).sum()
        dist = np.linalg.norm(W.mean(0) - eye)
        s += want['profile'] * min(ds / max(math.degrees(L3 / dist), 1e-6), 1.0)
    for (a, e, r, u0, u1, w) in want.get('avoid', ()):
        m = (u >= u0) & (u <= u1)
        if m.any():
            dd = np.hypot((az[m] - a) * math.cos(math.radians(e)), el[m] - e)
            s -= w * float(np.clip(r - dd, 0, None).max())
    for (a0, a1, e1, w) in want.get('gaps', ()):     # screen column az a0..a1 below el e1 stays clear
        m = (az > a0) & (az < a1) & (el < e1) & (W[:, 2] > -5)
        s -= w * float(m.mean()) * 10
    if 'az_band' in want:                            # the whole visible arm stays inside az a0..a1
        a0, a1, w = want['az_band']
        vis = W[:, 2] > -5
        s -= w * float(np.clip(np.maximum(a0 - az[vis], az[vis] - a1), 0, None).max()) / 2.0
    if 'lean_to' in want:
        p, w = want['lean_to']
        c = W[-1] - W[0]
        c[2] = 0
        g = np.asarray(p, float) - W[0]
        g[2] = 0
        s += w * float(unit(c + 1e-9) @ unit(g + 1e-9))
    if 'bend' in want:                 # the gesture must read on screen + at least one inflection (no horn arcs)
        m = (u > 0.06) & (u < 0.9) & (W[:, 2] > -5)
        if m.sum() > 5:
            q = np.stack([az[m] * np.cos(np.radians(el[m])), el[m]], 1)
            c = q[-1] - q[0]
            cl = np.linalg.norm(c) + 1e-6
            nrm = np.array([-c[1], c[0]]) / cl
            dev = (q - q[0]) @ nrm
            sag = np.abs(dev).max() / cl
            s += want['bend'] * min(sag, 0.32) / 0.32
            d1 = np.diff(q, axis=0)
            cr = d1[:-1, 0] * d1[1:, 1] - d1[:-1, 1] * d1[1:, 0]
            sg = np.sign(cr[np.abs(cr) > 1e-9])
            s += 0.5 * want['bend'] * float(np.any(sg[:-1] != sg[1:])) if len(sg) > 2 else 0.0
    if 'avoid_cross' in want:
        s -= 2.0 * float((np.sign(W[:, 0]) != want['avoid_cross']).mean())
    if 'bus_path' in want:             # keep >= clear m from the bus's swept path (it climbs 60 -> 150 m to U9)
        clear, w = want['bus_path']
        yy = np.clip(W[:, 1], -2700.0, 0.0)
        tb = CUE['U9'] - (-yy) / V_G
        zb = np.array([h_bus(float(x)) for x in tb]) + 1.6
        dd = np.hypot(np.maximum(np.abs(W[:, 0]) - 1.3, 0.0), W[:, 2] - zb)
        dd = np.where(W[:, 1] < 30.0, dd, 1e9)
        s -= w * float(np.clip(clear - dd, 0, None).max()) / 10.0
    if 'y_max' in want:
        s -= 0.05 * float(np.clip(W[:, 1] - want['y_max'], 0, None).max())
    if want.get('moon'):
        s += 3.0 * _score_moon(W, u, eye, want.get('moon_u', (0.30, 0.55)))
    if 'top' in want:
        z0, w = want['top']
        s -= w * abs(W[:, 2].max() - z0) / 50.0
    return s


def solve_pose(key, root, scale, eye, want, alphas=range(0, 72, 6), betas=range(-180, 180, 12),
               gammas=range(0, 360, 12), step=12):
    P, u = cl_points(key, step)
    ch = unit(P[-1] - P[0])
    L3 = BL.VARIANTS[key]['L'] * scale
    best, bR = -1e18, None
    root = np.asarray(root, float)
    for al in alphas:
        for be in (betas if al else [0]):
            d = np.array([math.sin(math.radians(al)) * math.sin(math.radians(be)),
                          math.sin(math.radians(al)) * math.cos(math.radians(be)), math.cos(math.radians(al))])
            R0 = rot_between(ch, d)
            for ga in gammas:
                R = rodrigues(d, math.radians(ga)) @ R0
                W = root + scale * (P @ R.T)
                s = _score(W, u, eye, want, L3)
                if s > best:
                    best, bR = s, R
    return bR, best


def refine_pose(key, root, scale, eye, want, R, step=6, span=8.0):
    P, u = cl_points(key, step)
    L3 = BL.VARIANTS[key]['L'] * scale
    root = np.asarray(root, float)
    best = _score(root + scale * (P @ R.T), u, eye, want, L3)
    for it in range(3):
        sp = span / (2 ** it)
        improved = True
        while improved:
            improved = False
            for ax in np.eye(3):
                for sg in (-1, 1):
                    R2 = rodrigues(ax, math.radians(sg * sp)) @ R
                    s = _score(root + scale * (P @ R2.T), u, eye, want, L3)
                    if s > best + 1e-6:
                        best, R, improved = s, R2, True
    return R, best


def height_of(key, R, scale):
    P = BL.centreline(key)['P']
    return float(scale * (P @ R.T)[:, 2].max())


def _lean_axis(root, to=(0.0, 0.0)):
    return unit(np.cross(np.array([0, 0, 1.0]), unit(np.array([to[0] - root[0], to[1] - root[1], 0.0]) + 1e-9)))


def _hero_to_final(it, R_hero, lean):
    """lean = (t0, t1, deg[, axis]): the arm bends toward the wound by deg over t0..t1; R_hero is its pose at
    T_HERO; the stored R is the FINAL pose."""
    t0, t1, deg = lean[:3]
    ax = lean[3] if len(lean) > 3 else _lean_axis(it['root'])
    a = dict(type='lean', t0=t0, t1=t1, deg=deg, axis=np.asarray(ax, float), prof='ss')
    s = anim_s(a, T_HERO)
    it['R'] = rodrigues(a['axis'], math.radians(deg * (1 - s))) @ R_hero
    it['anim'].append(a)
    return it


def own_speed(it, t0, t1, dt=0.25, step=10):
    """max own angular speed (deg/s) of the arm's visible points (the bus's motion excluded: both samples from the
    same eye) over t0..t1: (speed, t, u)."""
    best, bt, bu = 0.0, None, None
    for t in np.arange(t0, t1, dt):
        e = eye_cf(t)
        A, u = world_centreline(it, t, step)
        B, _ = world_centreline(it, t + dt, step)
        vis = (A[:, 2] > 0) & (B[:, 2] > 0)
        if not vis.any():
            continue
        a1, e1 = azel_of(A[vis] - e)
        a2, e2 = azel_of(B[vis] - e)
        v = np.hypot((a2 - a1) * np.cos(np.radians(e1)), e2 - e1) / dt
        k = int(np.argmax(v))
        if v[k] > best:
            best, bt, bu = float(v[k]), float(t), float(u[vis][k])
    return best, bt, bu


def fit_rise(it, t0, vmax, depth, prof_='trap', ease=0.2, t1_min=None, t1_max=None, direction=None):
    """add a rise starting at t0: the SHORTEST duration whose own angular speed peaks at <= vmax. direction: the
    unit vector the arm slides out along (v4: its own axis at the cloud; default straight up)."""
    a = dict(type='rise', t0=t0, t1=t0 + 10.0, depth=depth, prof=prof_, ease=ease)
    if direction is not None:
        a['dir'] = [float(x) for x in unit(np.asarray(direction, float))]
    it['anim'].insert(0, a)
    best = None
    for T in list(np.arange(4.0, 30.0, 1.0)) + list(np.arange(30.0, 80.0, 4.0)):
        a['t1'] = t0 + T
        if t1_max is not None and a['t1'] > t1_max + 1e-6:
            break
        v, _, _ = own_speed(it, t0, min(t0 + T, CUE['U9'] + 2.0), dt=0.5, step=16)
        if best is None or v < best[1]:
            best = (T, v)
        if v <= vmax:
            best = (T, v)
            break
    a['t1'] = t0 + best[0]
    if t1_min is not None and a['t1'] < t1_min:
        a['t1'] = t1_min
    if t1_max is not None and a['t1'] > t1_max:
        a['t1'] = t1_max
    it['rise_vmax'] = round(float(own_speed(it, t0, min(a['t1'], CUE['U9'] + 2.0), dt=0.3, step=10)[0]), 2)
    return it


# ---------------------------------------------------------------------------------------------------- moon
def _score_moon(W, u, e, urange=(0.30, 0.55)):
    az, el = azel_of(W - e)
    if W[-1, 2] < 40:
        return -1e9
    k = int(np.argmax(el))
    sec = (u > urange[0]) & (u < urange[1])
    dm = np.hypot((az[sec] - MOON_AZ) * math.cos(math.radians(8)), el[sec] - MOON_EL)
    s = -20.0 * max(dm.min() - 0.05, 0.0)
    s -= 1.0 * max(0.0, (MOON_EL + 3.0) - el[k])
    s -= 0.6 * max(0.0, el[k] - (MOON_EL + 6.0))
    s += 0.2 * min(az[-1] - MOON_AZ, 6.0)
    return s


def moon_coverage(it, t, n=41):
    """fraction of the 1.2 deg moon disc hidden by the arm at time t (skin radius from arm_radius)."""
    m = L_MOON
    e1 = np.cross(m, [0, 0, 1.0])
    e1 /= np.linalg.norm(e1)
    e2 = np.cross(e1, m)
    g = np.linspace(-1, 1, n)
    X, Y = np.meshgrid(g, g)
    k = (X ** 2 + Y ** 2) <= 1
    ang = math.radians(0.6)
    D = m[None] + ang * (X[k][:, None] * e1[None] + Y[k][:, None] * e2[None])
    D /= np.linalg.norm(D, axis=1, keepdims=True)
    e = eye_cf(t)
    W, u = world_centreline(it, t, 2)
    r = arm_radius(it, u)
    vis = W[:, 2] > 0
    if not vis.any():
        return 0.0
    V = W[vis] - e
    dist = np.linalg.norm(V, axis=1)
    Vn = V / dist[:, None]
    angr = np.arcsin(np.clip(r[vis] / dist, 0, 1))
    ca = np.arccos(np.clip(D @ Vn.T, -1, 1))
    return float((ca < angr[None]).any(1).mean())


def refine_moon(it, t0, t1, n=3):
    """small rotations of the HERO pose so the moon disc is covered as fully as possible over t0..t1."""
    best = np.mean([moon_coverage(it, t, 25) for t in np.linspace(t0, t1, n)])
    R0 = it['R'].copy()
    for sp in (1.0, 0.5, 0.25, 0.12):
        improved = True
        while improved:
            improved = False
            for ax in np.eye(3):
                for sg in (-1, 1):
                    it['R'] = rodrigues(ax, math.radians(sg * sp)) @ R0
                    c = np.mean([moon_coverage(it, t, 25) for t in np.linspace(t0, t1, n)])
                    if c > best + 1e-4:
                        best, R0, improved = c, it['R'].copy(), True
    it['R'] = R0
    return best


def track_moon(it, t_from, t_to, dt=1.5, vmax=0.45, u_sec=0.42):
    """'track' keys (rotation vectors about the root, applied after rise / lean) that keep the occluding section on
    the moon ray as the bus approaches, each step limited so the own motion stays <= vmax."""
    keys = [(t_from, np.zeros(3))]
    it['anim'].append(dict(type='track', keys=keys))
    P, u = cl_points(it['variant'], 2)
    k_sec = int(np.argmin(np.abs(u - u_sec)))
    for t in np.arange(t_from + dt, t_to + 1e-6, dt):
        rv_prev = keys[-1][1]
        keys.append((float(t), rv_prev.copy()))
        root, _ = pose_at(it, t)
        W, _ = world_centreline(it, t, 2)
        e = eye_cf(t)
        Ps = W[k_sec]
        m = L_MOON
        Q = e + float((Ps - e) @ m) * m
        a, b_ = Ps - root, Q - root
        ax = np.cross(a, b_)
        if np.linalg.norm(ax) < 1e-9:
            continue
        ang = math.atan2(np.linalg.norm(ax), float(a @ b_))
        dist = np.linalg.norm(Ps - e)
        far = np.max(np.linalg.norm(W - root, axis=1))
        amax = math.radians(vmax) * dt * dist / max(far, 1.0)
        ang = min(ang, amax)
        rv_new = rv_prev + (ax / np.linalg.norm(ax)) * ang
        keys[-1] = (float(t), rv_new)
    it['anim'][-1]['keys'] = [(k, list(map(float, v))) for k, v in keys]
    return it


def track_points(it, targets, t_from, t_to, dt=1.0, vmax=0.8, u_tip=0.97):
    """'track' keys (rotation vectors about the root) that keep the arm's point at u_tip on a moving target
    targets(t) -> CF point (the hands' fingertips riding the flaps as the tear grows and opens), each step limited
    to vmax deg/s of own motion."""
    keys = [(t_from, np.zeros(3))]
    it['anim'].append(dict(type='track', keys=keys))
    P, u = cl_points(it['variant'], 2)
    k_tip = int(np.argmin(np.abs(u - u_tip)))
    for t in np.arange(t_from + dt, t_to + 1e-6, dt):
        rv_prev = np.asarray(keys[-1][1], float)
        keys.append((float(t), rv_prev.copy()))
        root, _ = pose_at(it, t)
        W, _ = world_centreline(it, t, 2)
        a, b_ = W[k_tip] - root, np.asarray(targets(t), float) - root
        ax = np.cross(a, b_)
        if np.linalg.norm(ax) < 1e-9:
            continue
        ang = math.atan2(np.linalg.norm(ax), float(a @ b_))
        dist = np.linalg.norm(W[k_tip] - eye_cf(t))
        amax = math.radians(vmax) * dt * dist / max(np.linalg.norm(a), 1.0)
        ang = min(ang, amax)
        keys[-1] = (float(t), rv_prev + (ax / np.linalg.norm(ax)) * ang)
    it['anim'][-1]['keys'] = [(k, list(map(float, v))) for k, v in keys]
    return it


# ---------------------------------------------------------------------------------------------------- the grip
# round 3 (resume): the fingertips land on the tear kit's OWN grip points (tear_def.GRIPS / grip_kit: the tented
# rolled lips of the two flaps and one point on the left lip), moved with the opening exactly as the Tear shader moves
# the flap (a += a_hinge * (w - 1)) and scaled by H(t). The old grips sat 0.6 flap-lengths OUTSIDE the lip, so the
# fingers stopped short of the white.
_GRIP_KIT = {}
GRIP_INDEX = {-1: (0, 1, 2), +1: (3, 4, 5)}


def grip_cf(t, side, k):
    kk = GRIP_INDEX[side][k]
    if kk not in _GRIP_KIT:
        _GRIP_KIT[kk] = TD.grip_kit(kk)
    g, ah = _GRIP_KIT[kk]
    S = tear_H(t) / TD.H
    w = TD.width_mul(tear_open(t))
    return (np.asarray(g, float) + TD.AC * (ah * (w - 1.0))) * S


def _along(p0, p1, f):
    return np.asarray(p0, float) + (np.asarray(p1, float) - np.asarray(p0, float)) * f


# ---------------------------------------------------------------------------------------------------- hero arms
FOG_PILLAR = 0.05         # LanbaiFog density scale (the only true blacks)
FOG_HAND = 0.30           # hands: a dark volume in the band (body L* 15-18 against 30-34; critique B1)
FOG_ENGEL = 0.80          # 'a pale shape leans out of the haze' (body band - 8..10; its hand dark against the glow)
FOG_BG = 1.0              # background giants: band - 8 (cap 0.92 beyond 1.3 km, x height falloff)
FOG_SURGE = 1.0
FOG_COL = 0.55            # colossus 1
FOG_C2 = 0.12             # colossus 2: a black notch in the moon's aureole (L* <= 12)


def _hero(id_, layer, role, key, P, R_root, note, thick=1.0, lod=0, lods=((40, 210), (24, 120), (12, 48))):
    rng = np.random.default_rng(zlib.crc32(id_.encode()))
    root = A4.register(key, P, R_root, float(rng.random()), lods=lods, thick=thick, vofs=float(rng.uniform(0, 1)))
    it = inst(id_, layer, key, root, np.eye(3), 1.0, lod=lod, note=note)
    it['role'] = role
    return it


def pillar_R_ctrl():
    """rears up out of the cloud at local (258, -1000) leaning ~30 deg to the right; its crown leaves the key frame
    through the top-right corner (you never see where it ends). (A breach hump in front of it was tried: at this girth
    it read as a black dome / rock, so the pillar breaches in one piece.) After the bus has passed it leans in over the
    road behind it ('close')."""
    return [(232, -1018, -160), (248, -1012, -60), (262, -1006, 30),
            (300, -995, 175), (365, -980, 345), (440, -958, 495), (520, -928, 615), (600, -888, 695),
            (670, -842, 722), (730, -792, 700), (770, -752, 640)]


def pillar_L_ctrl():
    """far left (0.85 km, az -40): the body rises leaning AWAY (toward the tear plane), out of the key frame; the crown
    arches over toward the road high up and only the whip comes down into the key frame's top-left corner."""
    # run 6: the whip no longer drops into the key frame (it hung from the frame top like a string); it droops but
    # stays above el +30 from the hero eye, so only the body is in the frame's left edge
    return [(-600, -880, -110), (-575, -835, 0), (-560, -760, 200), (-545, -690, 400), (-520, -630, 570),
            (-480, -590, 650), (-440, -575, 690), (-400, -566, 700), (-368, -560, 684), (-348, -556, 655)]


def engel_ctrl():
    """root 2.6 km away at az +24 (local (1080, 960)), behind the right pillar; the body leans hard over the wound
    toward the bus (a diagonal from the key frame's lower right to its top at x ~56 %); the crest (el ~28) leaves the
    frame top; the last quarter hangs IN FRONT of the lens (local z ~-100) over its upper third / right lip, the tip
    curling at el ~14 (60 % H), a quarter of the lens width right of the axis."""
    return [(1110, 990, -140), (1070, 950, 0), (930, 840, 260), (760, 700, 520), (575, 555, 780), (420, 430, 960),
            (300, 330, 1060), (195, 200, 1040), (135, 60, 925), (102, -40, 770), (82, -90, 640), (68, -108, 540),
            (62, -114, 478)]


def azel_pt(az, el, y, eye=None):
    """the CF point on the depth plane y seen at (az, el) from the U7b eye (design in screen terms)."""
    e = E_HERO if eye is None else eye
    dy = y - e[1]
    x = e[0] + dy * math.tan(math.radians(az))
    dh = dy / math.cos(math.radians(az))
    return np.array([x, y, e[2] + dh * math.tan(math.radians(el))])


def _finger_path(wrist, grip, bulge_el, spread_az, eye=None):
    """control points from the wrist (az, el, y) to a grip point (CF): an arc in screen space that crests a little
    above the straight line (the finger comes DOWN onto the lip) and fans by spread_az at its middle."""
    e = E_HERO if eye is None else eye
    v = np.asarray(grip, float) - e
    gaz = math.degrees(math.atan2(v[0], v[1]))
    gel = math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))
    waz, wel, wy = wrist
    pts = []
    for f in (0.30, 0.62, 0.86):
        az = waz + (gaz - waz) * f + spread_az * math.sin(math.pi * f)
        el = wel + (gel - wel) * f + bulge_el * math.sin(math.pi * f)
        y = wy + (grip[1] - wy) * f
        pts.append(azel_pt(az, el, y, e))
    return pts + [np.asarray(grip, float)]


# run 6: one finger of each hand is a WHIP that crosses the white and hooks the OPPOSITE lip (bible: 'fingertips
# interlacing in the lower half of the wound, as if closing it; it cannot be closed'). Left hand -> right lip at
# zf 0.24, right hand -> left lip at zf 0.36; in front of the lens (y -30), the tip curling down over the far lip.
CROSS = {-1: dict(zf=0.24, own_zf=0.27, bulge=0.07), +1: dict(zf=0.36, own_zf=0.44, bulge=0.06)}


def cross_target(t, side):
    c = CROSS[side]
    return lip_point(t, c['zf'], -side, out=10.0, y=-30.0)


def _cross_path(wrist, side, t=None, eye=None):
    """wrist (az, el, y) -> over the own lip -> an arc across the white -> the far lip -> a short downward curl."""
    t = T_HERO if t is None else t
    c = CROSS[side]
    H = tear_H(t)
    own = lip_point(t, c['own_zf'], side, out=-6.0, y=-34.0)
    far = cross_target(t, side)
    mid = 0.5 * (own + far) + np.array([0.0, -4.0, c['bulge'] * H])
    curl1 = far + np.array([-side * 14.0, -2.0, -0.05 * H])
    curl2 = far + np.array([-side * 6.0, 0.0, -0.085 * H])
    e = E_HERO if eye is None else eye
    v = own - e
    gaz = math.degrees(math.atan2(v[0], v[1]))
    gel = math.degrees(math.atan2(v[2], math.hypot(v[0], v[1])))
    waz, wel, wy = wrist
    pre = [azel_pt(waz + (gaz - waz) * f, wel + (gel - wel) * f + 0.8 * math.sin(math.pi * f), wy + (own[1] - wy) * f, e)
           for f in (0.35, 0.7)]
    return pre + [own, 0.5 * (own + mid) + np.array([0, 0, 0.02 * H]), mid, far, curl1, curl2]


def hand_ctrl(side):
    """(axis ctrl, [(R_root, finger ctrl beyond the wrist)]) of a bundle (round 3, resume): ONE braided forearm that
    leaves the cloud leaning ~40 deg toward the wound (on screen a diagonal, never a vertical stalk), crests and bends
    over at the wrist just outside the lip, and only its last ~22 % splits into three short fingers that come DOWN onto
    the flap's rolled lip and hook into the white (tear_def grips). The fingers stay together (a hand, not a fan of
    fronds). Right = the big hand on the right peel (~700 m); left = the small one on the left curl (~450 m)."""
    g = lambda k: grip_cf(T_HERO, side, k)
    if side < 0:      # LEFT: small, low
        axis = [azel_pt(-13.0, -6.0, -380) * np.array([1, 1, 0]) + np.array([0, 0, -70.0]),
                azel_pt(-11.6, -1.4, -340), azel_pt(-9.4, 2.6, -285), azel_pt(-7.1, 5.9, -230),
                azel_pt(-5.2, 7.9, -180)]
        wrist = (-5.2, 7.9, -180.0)
        f = [(23.0, _finger_path(wrist, g(0), 0.9, -0.35)),
             (19.0, _cross_path(wrist, -1)),                         # run 6: the whip across the white
             (19.0, _finger_path(wrist, g(2), 0.6, 0.35))]
    else:             # RIGHT: the big one
        axis = [azel_pt(21.5, -6.0, -470) * np.array([1, 1, 0]) + np.array([0, 0, -80.0]),
                azel_pt(19.8, -1.4, -430), azel_pt(16.8, 4.2, -365), azel_pt(13.4, 9.4, -300),
                azel_pt(10.4, 12.8, -235)]
        wrist = (10.4, 12.8, -235.0)
        f = [(34.0, _finger_path(wrist, g(0), 1.0, 0.5)),
             (27.0, _cross_path(wrist, +1)),                         # run 6: the whip across the white
             (28.0, _finger_path(wrist, g(2), 0.8, -0.5))]
    return axis, f


def build_heroes():
    U6, U7, U7b, U8 = CUE['U6'], CUE['U7'], CUE['U7b'], CUE['U8']
    out = []
    # --- gate pillars (standing at activation; revealed from their towers U7 - 2 .. U7b + 6)
    P = A4.curve(A4.hook_end(pillar_R_ctrl(), 30.0, 100.0, (0.3, 0.6, -1.0)))
    it = _hero('Pillar_R', 'colossus', 'pillar', 'PR', P, 54.0, 'right gate pillar: hump, leans in, arches over the road',
               thick=1.25)
    it['fog'] = FOG_PILLAR
    it['reveal'] = [(U7 - 2.0, 0.0), (U7b - 0.5, 1.0)]
    out.append(it)
    P = A4.curve(A4.hook_end(pillar_L_ctrl(), 24.0, 45.0, (0.5, -0.3, -1.0)))      # resume: no 'J' hook
    it = _hero('Pillar_L', 'colossus', 'pillar', 'PL', P, 36.0, 'left gate pillar: far; only its whip in the key frame',
               thick=1.2)
    it['fog'] = FOG_PILLAR
    it['reveal'] = [(U7 - 2.0, 0.0), (U7b - 0.5, 1.0)]
    out.append(it)
    # --- the Engel (bows in U7 - 1 .. U8 by 3 deg about its root)
    P = A4.curve(A4.hook_end(engel_ctrl(), 22.0, 55.0, (-0.6, -0.3, -0.4)))      # resume: a soft droop, not a '?'
    it = _hero('Colossus_3', 'colossus', 'engel', 'ENG', P, 104.0, "'der Engel': leans over the wound; its hand hangs "
               "in front of the lens", thick=1.15)
    it['fog'] = FOG_ENGEL
    it['reveal'] = [(U7 - 2.0, 0.0), (U7b - 1.0, 1.0)]
    _hero_to_final(it, np.eye(3), (U7 - 1.0, U8, 3.0, _lean_axis(it['root'], (0.0, 0.0))))
    out.append(it)
    # --- hands: braided bundles, crowns break the deck after a dome, slide out along their axis, then the fingertips
    # ride the flaps as the tear grows (track keys)
    for side, name in ((-1, 'L'), (1, 'R')):
        axis, fingers = hand_ctrl(side)
        Ps = A4.braid(axis, fingers, turns=0.62 if side < 0 else 0.55, phase0=0.4 if side < 0 else 2.1)
        cls = []
        for k, ((R0, _), P) in enumerate(zip(fingers, Ps)):
            P = A4.curve(A4.hook_end([P[i] for i in np.linspace(0, len(P) - 1, 30 if k == 1 else 26).astype(int)],
                                     6.0 * R0 / 15.0, 35.0 if k == 1 else 110.0, (-side * 1.0, -0.35, -0.6)), smooth=1.5)
            it = _hero('Hand_%s%d' % (name, k), 'mid', 'hand', 'H%s%d' % (name, k), P, R0,
                       'hand bundle %s, finger %d: hooks the %s' % (name, k, 'left curl' if side < 0 else 'right peel'))
            it['bundle'] = 'Hand_' + name
            it['fog'] = FOG_HAND * (1.0 if side < 0 else 1.25)
            # resume (awe: U6 + 13 s shows <= 2 arms): the hands rise hidden (renderer off, _Reveal 0) and come out of
            # the haze over U6 + 13.5 .. U7 + 3 while their crowns are still climbing
            it['reveal'] = [(U6 + 13.5, 0.0), (U7 + 3.0, 1.0)]
            cls.append(it)
        # the rise: along the forearm's axis at the cloud (crown first), U6 + 10 -> ~U7b (fitted <= 1.0 deg/s)
        ax0 = unit(np.asarray(axis[1], float) - np.asarray(axis[0], float))
        for it in cls:
            Wc, _ = world_centreline(it, T_HERO, 4)
            depth = float((Wc[:, 2].max() + 25.0) / max(ax0[2], 0.3))
            it['anim'].append(dict(type='dome', t0=U6 - 5.0, t1=U6 + 3.0, centre=[float(axis[1][0]), float(axis[1][1])],
                                   radius=float(1.6 * 2 * fingers[0][0]), height=45.0))
            it['anim'].insert(0, dict(type='rise', t0=U6 - 3.0, t1=U7b - 0.5, depth=depth, prof='trap', ease=0.25,
                                      dir=[float(x) for x in ax0]))
            it['rise_vmax'] = round(float(own_speed(it, U6 - 3.0, U7b, dt=0.3, step=10)[0]), 2)
            k = int(it['id'][-1])
            tgt = (lambda tt, s_=side: cross_target(tt, s_)) if k == 1 else (lambda tt, s_=side, k_=k: grip_cf(tt, s_, k_))
            track_points(it, tgt, U7b, CUE['U9'] - 1.0, dt=1.0, vmax=0.5 if k == 1 else 0.6, u_tip=0.93 if k == 1 else 0.97)
            out.append(it)
    return out


# ---------------------------------------------------------------------------------------------------- smaller arms
def _proc_arm(rng, e_cf, L, lean_deg, to_xy=(0.0, 0.0), curl=1.0, hook_scale=1.0):
    """a procedural arm in the v4 form language: leaves the cloud at e_cf leaning lean_deg toward to_xy, reaches
    forward in one long convex bend (a swan neck bowing toward the wound), crests at ~60 % of its length and lets the
    whip droop (tip 12-20 % of L below the crest) with one soft hook. Never a crozier / '?'."""
    e = np.asarray(e_cf, float)
    h = unit(np.array([to_xy[0] - e[0], to_xy[1] - e[1], 0.0]))
    pp = np.cross(np.array([0, 0, 1.0]), h)
    sl = math.tan(math.radians(lean_deg))
    w = rng.uniform(-0.07, 0.07) * L
    reach = rng.uniform(0.85, 1.15)
    droop = rng.uniform(0.10, 0.18) * curl
    pts2 = [(-0.10 * sl, -0.13), (0.0, 0.0), (0.13 * sl + 0.02, 0.24), (0.26 * sl + 0.07, 0.42),
            (0.38 * sl + 0.16 * reach, 0.54), (0.46 * sl + 0.30 * reach, 0.60), (0.50 * sl + 0.44 * reach, 0.60 - 0.3 * droop),
            (0.52 * sl + 0.56 * reach, 0.60 - 0.75 * droop), (0.53 * sl + 0.64 * reach, 0.60 - 1.0 * droop)]
    out = []
    for i, (hh, zz) in enumerate(pts2):
        lat = w * math.sin(math.pi * i / (len(pts2) - 1))
        out.append(e + h * hh * L + pp * lat + np.array([0, 0, zz * L]))
    return A4.hook_end(out, 0.025 * L, rng.uniform(18, 38) * hook_scale, h * 0.2 - np.array([0, 0, 1.0]), n=4)   # resume: a droop, not a candy cane


SURGE_SEED = 41
BACKGROUND = [   # (az from the U7b eye, distance m, length m): bodies inside the band (crest el <= 13 deg)
    (-24.0, 3600.0, 760.0), (-36.0, 3300.0, 820.0), (-50.0, 3800.0, 900.0),
    (21.0, 4100.0, 860.0), (38.0, 3400.0, 780.0), (52.0, 3900.0, 920.0),
]


def build_others():
    U6, U7, U7b = CUE['U6'], CUE['U7'], CUE['U7b']
    rng = np.random.default_rng(SURGE_SEED)
    e = E_HERO
    out = []
    # --- background giants (standing; inside the band; revealed by their towers / _Reveal U7 - 2 .. U7b + 6)
    for i, (az, d, L) in enumerate(BACKGROUND):
        ep = at_az(az, d, 0.0)
        P = A4.curve(_proc_arm(rng, ep, L, rng.uniform(28, 40)))
        it = _hero('Colossus_bg_%02d' % i, 'colossus_bg', 'background', 'BG%d' % i, P, L / 22.0, 'background giant',
                   lod=1, lods=((28, 140), (18, 80), (10, 36)))
        it['fog'] = FOG_BG
        it['reveal'] = [(U7 - 2.0, 0.0), (U7b - 0.5, 1.0)]
        out.append(it)
    # --- colossus 1 (behind the Rilke line, az +24, 3.2 km at U7b): rises from U6 + 10 at <= 0.3 deg/s
    ep = at_az(24.5, 3200.0, 0.0)
    P = A4.curve(_proc_arm(rng, ep, 460.0, 30.0))
    it = _hero('Colossus_1', 'colossus', 'rilke', 'C1', P, 460.0 / 20.0, 'rises behind the Rilke line', lod=1,
               lods=((28, 140), (18, 80), (10, 36)))
    it['fog'] = FOG_COL
    h = float(world_centreline(it, T_HERO, 4)[0][:, 2].max())
    fit_rise(it, U6 + 10.0, 0.3, h + 40.0, prof_='beta', ease=3.5)
    it['reveal'] = [(U6 + 10.0, 0.0), (U6 + 16.0, 1.0)]      # tech B1
    out.append(it)
    # --- colossus 2 (takes the moon on '...abweisen'): custom, its round side toward the camera
    M = e + 2520.0 * L_MOON
    ctrl = [np.array([-1000.0, 1150.0, -110.0]), azel_pt(-18.6, -1.3, 1130), azel_pt(-16.6, 3.0, 1090),
            azel_pt(-14.2, 5.9, 1040), M, azel_pt(-10.4, 10.4, 965), azel_pt(-9.0, 11.3, 945),
            azel_pt(-7.8, 10.9, 935), azel_pt(-7.0, 9.6, 930)]
    # resume: the crown passes over the disc as a smooth shoulder and the whip runs on toward the wound, drooping
    # (the hooked 'cobra head' read as a '?' / shepherd's crook)
    P = A4.curve(A4.hook_end(ctrl, 14.0, 40.0, (0.1, -0.2, -1.0)))
    it = _hero('Colossus_2', 'colossus', 'moon', 'C2', P, 55.0, "takes the moon on '...abweisen'", thick=1.1)
    it['fog'] = FOG_C2
    ax_bow = unit(np.cross(unit(np.array([L_MOON[0], L_MOON[1], 0.0])), np.array([0, 0, 1.0])))
    _hero_to_final(it, np.eye(3), (U7b - 3.0, U7b + 1.0, -2.0, ax_bow))
    h = float(world_centreline(it, T_HERO, 4)[0][:, 2].max())
    # resume (tech minor): it rises sliding in from the LEFT of the disc (dir right-and-up), so at U6 + 8..13 its crown
    # breaks the deck left of the moon and travels right over it into the U7b eclipse
    c2dir = unit(np.array([0.6, 0.0, 0.8]))
    fit_rise(it, U6 - 12.0, 0.5, (h + 80.0) / c2dir[2], prof_='beta', ease=3.5, t1_max=U7b - 3.5, direction=c2dir)
    it['moon_cover_hero'] = round(refine_moon(it, U7b - 0.3, U7b + 1.0), 3)
    it['reveal'] = [(U6 + 8.0, 0.0), (U6 + 14.0, 1.0)]       # tech B1: C2 out of the haze U6 + 8 .. + 14
    track_moon(it, U7b + 1.0, CUE['U9'], dt=1.0, vmax=0.30, u_sec=0.36)   # run 6: 0.35 -> 0.30 (whip 0.57 deg/s near U9)
    out.append(it)
    # --- the surge ring: 22 small arms at 2.5-4 km in the band, az +-8..+-55, leaning toward the wound; they break the
    # deck crowns first from U7 (bible: 12 -> 30 in 12 s), <= 0.5 deg/s
    azs = [float(a + rng.uniform(-1.2, 1.2)) for a in np.linspace(-56.0, -18.0, 10)] + \
          [float(a + rng.uniform(-1.2, 1.2)) for a in np.linspace(16.0, 56.0, 12)]      # resume: clear of the foot
    for i, az in enumerate(sorted(azs)):
        d = float(rng.uniform(2500, 4000))
        L = float(rng.uniform(200, 350))
        ep = at_az(az, d, 0.0)
        P = A4.curve(_proc_arm(rng, ep, L, rng.uniform(22, 40), curl=0.7, hook_scale=0.3))    # run 6: reach, no fern hook
        it = _hero('Surge_%02d' % i, 'surge', 'surge', 'SG%02d' % i, P, L / 18.0, 'surge ring', lod=1,
                   lods=((20, 90), (12, 48), (8, 24)))
        it['fog'] = FOG_SURGE
        h = float(world_centreline(it, T_HERO, 4)[0][:, 2].max())
        t0 = U7 - 6.0 + 1.5 * rng.random() + 2.5 * (1.0 - abs(az) / 56.0)     # outer first; crowns break from U7 - 6
        fit_rise(it, t0, 0.5, h + 30.0, prof_='trap', ease=0.25)
        # resume: the surge is a wave: it recedes into the haze before U8 (from 1.5-3 km at U8 the drooping crowns read
        # as weeds at the wound's foot)
        it['reveal'] = [(U7 - 30.0, 1.0), (CUE['U8'] - 5.0, 1.0), (CUE['U8'] + 1.0, 0.0)]
        out.append(it)
    return out


# ---------------------------------------------------------------------------------------------------- near (U8)
NEAR_SPEC = [
    # (key, scale, girth, side, y at t_ref (bus-relative CF), v_rel m/s, target clearance m, rise t0, t1)
    ('D', 2.8, 1.15, -1.0, -10.0, -6.0, 11.0, CUE['U8'] - 6.0, CUE['U8'] + 1.5),
    ('C', 3.0, 1.10, 1.0, -25.0, 7.0, 11.0, 156.15, 164.65),      # critique blocker 2: rise moved earlier
    ('D', 2.2, 1.10, 1.0, 30.0, -4.0, 17.0, CUE['U8'] - 6.0, CUE['U8'] + 1.5),
]


def build_near():
    """2-3 arms at 8-20 m that surge WITH the bus toward the wound at U8: x, y bus-relative (Unity: children of a
    NearRoot fixed to the bus) drifting at v_rel m/s; z relative to the cloud-sea top. Clearance and the bible's
    |v_rel| <= 1.05 d are checked with the FULL relative velocity (drift + the bus climb + rise + lean)."""
    out = []
    t8 = CUE['U8']
    for i, (key, sc, g, side, y, v, target, r0, r1) in enumerate(NEAR_SPEC):
        eye = eye_cf(t8 + 3.0)
        want = dict(floor=-40.0, top=(h_bus(t8 + 3.0) + 55.0, 2.0), lean_to=(np.array([0.0, 2000.0, 0.0]), 1.0),
                    tipdir=(tear_core_cf(t8), 1.0), bend=1.0)
        root_w = np.array([side * 30.0, y - gate_z(t8 + 3.0), -35.0])
        want['avoid_cross'] = side
        R, s_ = solve_pose(key, root_w, sc, eye, want, alphas=range(4, 30, 5), betas=range(-180, 180, 30),
                           gammas=range(0, 360, 30), step=20)
        best = None
        for xm in np.arange(4.0, 140.0, 2.0):
            root = np.array([side * xm, y, -35.0])
            cand = inst('Near_%d' % i, 'near', key, root, R, sc, lod=0, frame='bus', girth=g,
                        anim=[dict(type='drift', v=v, t_ref=t8 + 3.0),
                              dict(type='rise', t0=r0, t1=r1, depth=200.0)])
            W, _ = world_centreline(cand, t8 + 3.0, 6)
            if np.any(np.sign(W[:, 0]) != side):
                continue
            chk = near_check(cand, CUE['U8'] - 8.0, CUE['U9'], step=0.2)
            ok = chk['worst_ratio'] <= 1.0
            if best is None or (ok and not best[1]['worst_ratio'] <= 1.0) or \
                    (ok == (best[1]['worst_ratio'] <= 1.0) and abs(chk['min_d'] - target) < abs(best[1]['min_d'] - target)):
                best = (cand, chk)
        it, chk = best
        it['role'] = 'near'
        it['clearance_m'] = round(float(chk['min_d']), 1)
        it['clearance_t'] = round(float(chk['t_min']), 2)
        it['speed_ratio'] = round(float(chk['worst_ratio']), 2)
        out.append(it)
    return out


BUS_BOX = (1.25, 4.0, 1.6)          # half extents (m) of the shell clearance box: 8 x 2.5 x 3.2 m (critique)
# round 3 (tech B2): the sway the JSON writes into every material (_SwayAmplitude rad, _SwayFrequency Hz,
# _SwaySecondary); stiffness 2 (bend ~ t^2). The near arms' tip excursion A_tip = amp x 1.17 x u^2 x |P(u) - root|
# is subtracted from the clearance and its speed 2 pi f A_tip added to the relative speed in near_check.
SWAY_KIND = dict(near=(0.015, 0.06, 0.6), pillar=(0.008, 0.04, 0.5), hero=(0.006, 0.03, 0.5), mid=(0.012, 0.05, 0.6),
                 colossus=(0.010, 0.04, 0.6), bg=(0.010, 0.04, 0.6), surge=(0.020, 0.06, 0.6), rear=(0.012, 0.05, 0.6))


def sway_of(it):
    r = it.get('role')
    k = 'pillar' if r == 'pillar' else 'hero' if r == 'engel' else 'surge' if it['layer'] == 'surge' else \
        {'colossus_bg': 'bg'}.get(it['layer'], it['layer'])
    return SWAY_KIND.get(k, SWAY_KIND['mid'])


def near_check(it, t0, t1, step=0.2, dt=0.05):
    """min skin distance to the bus shell box and the worst |v_rel| / (1.05 d) for d < 25 m, with the full relative
    velocity of the nearest skin point (drift, bus climb, rise, lean)."""
    P, u = cl_points(it['variant'], 3)
    r = arm_radius(it, u)
    amp, freq, sec = sway_of(it)
    best = dict(min_d=1e9, t_min=None, worst_ratio=0.0, t_ratio=None, eye_deg_s=0.0, sway_tip_m=0.0)
    for t in np.arange(t0, t1, step):
        W, _ = world_centreline(it, t, 3)
        W2, _ = world_centreline(it, t + dt, 3)
        b1 = bus_to_cf(np.array([0.0, 1.58, 0.0]), t)
        b2 = bus_to_cf(np.array([0.0, 1.58, 0.0]), t + dt)
        d = W - b1
        A_tip = amp * math.sqrt(1.0 + sec * sec) * u[:len(W)] ** 2 * np.linalg.norm(W - W[:1], axis=1)
        best['sway_tip_m'] = max(best['sway_tip_m'], float(A_tip.max()))
        dd = np.sqrt(np.maximum(np.abs(d[:, 0]) - BUS_BOX[0], 0) ** 2 + np.maximum(np.abs(d[:, 1]) - BUS_BOX[1], 0) ** 2 +
                     np.maximum(np.abs(d[:, 2]) - BUS_BOX[2], 0) ** 2) - r - A_tip
        vis = W[:, 2] > 0
        if not vis.any():
            continue
        dd = np.where(vis, dd, 1e9)
        k = int(np.argmin(dd))
        if dd[k] < best['min_d']:
            best['min_d'], best['t_min'] = float(dd[k]), float(t)
        if dd[k] < 25.0:
            v = np.linalg.norm((W2[k] - W[k]) - (b2 - b1)) / dt + 2.0 * math.pi * freq * A_tip[k]
            ratio = v / (1.05 * max(dd[k], 0.5))
            if ratio > best['worst_ratio']:
                e1, e2 = eye_cf(t), eye_cf(t + dt)
                a1, a2 = W[k] - e1, W2[k] - e2
                ang = math.degrees(math.acos(np.clip(a1 @ a2 / np.linalg.norm(a1) / np.linalg.norm(a2), -1, 1))) / dt
                best.update(worst_ratio=float(ratio), t_ratio=float(t), eye_deg_s=float(ang))
    return best


def near_clearance(it, t0=None, t1=None, step=0.25):
    c = near_check(it, CUE['U8'] - 6.0 if t0 is None else t0, CUE['U9'] if t1 is None else t1, step)
    return c['min_d'], c['t_min']


# ---------------------------------------------------------------------------------------------------- rear (Orpheus)
def build_rear(seed=23):
    """The Orpheus shot (round 2): two groups rooted 1.0-1.6 km behind the bus's U9 position, 300-520 m either side
    of the road, rise once the bus is >= 600 m past them (>= 25 s, <= 1 deg/s) and lean in over the road so their
    whips cross the road axis 400-700 m behind the bus (el +8..+15 from the rear window): a hand closing."""
    rng = np.random.default_rng(seed)
    out = []
    t_r = CUE['U9'] - 2.0
    e = eye_cf(t_r, EYE_STAND_REAR)
    spec = [(-1, -1150.0, 'G', 760.0), (1, -1220.0, 'F', 820.0), (-1, -1400.0, 'F', 640.0), (1, -1480.0, 'G', 700.0),
            (-1, -1650.0, 'C', 780.0), (1, -1700.0, 'F', 600.0), (-1, -1900.0, 'G', 720.0), (1, -1950.0, 'C', 760.0)]
    for i, (side, y, key, L_) in enumerate(spec):
        x = side * rng.uniform(300.0, 520.0)
        sc = L_ / BL.VARIANTS[key]['L']
        root = np.array([x, y + rng.uniform(-40, 40), -rng.uniform(40.0, 70.0)])
        # whip over the road axis, 400-700 m behind the bus at t_r, el 8-15 from the rear eye
        yb = e[1] - rng.uniform(420.0, 700.0)
        dist = e[1] - yb
        zt = e[2] + dist * math.tan(math.radians(rng.uniform(8.0, 15.0)))
        tgt = np.array([-side * rng.uniform(0.0, 60.0), yb, zt])
        want = dict(floor=-60.0, tip3=(tgt, 2.0), tipdir=(tgt + np.array([-side * 200.0, 0.0, -60.0]), 1.0),
                    bend=2.0, profile=1.0)
        R, s_ = solve_pose(key, root, sc, e, want, alphas=range(10, 70, 5), betas=range(-180, 180, 15),
                           gammas=range(0, 360, 15), step=14)
        R, s_ = refine_pose(key, root, sc, e, want, R)
        it = inst('Rear_%02d' % i, 'rear', key, root, R, sc, lod=0, girth=rng.uniform(1.5, 1.7))
        it['role'] = 'rear'
        t_pass = CUE['U9'] - (-y) / V_G
        # round 3: no rise (a 700 m arm cannot rise in the ~20 s between the bus passing it and U9 at <= 1 deg/s, so
        # at the rear-window moment they were still under the cloud). They STAND from activation, hidden (_Reveal 0,
        # renderer off) while they are still ahead of / beside the bus, and come out of the haze only once the bus is
        # 470-940 m past them (t_pass + 8 .. + 16 s; their whips reach forward over the road): out of the forward view.
        it['reveal'] = [(t_pass + 8.0, 0.0), (t_pass + 16.0, 1.0)]     # whip included: out of the forward view
        out.append(it)
    return out


def add_close(L):
    """the arms the bus has passed (gate pillars, the front flames) lean in over the road behind it once it is
    1.5 s past them, so the rear window sees the densest arms closing like a hand (bible: Orpheus shot).
    Speed <= 1 deg/s (checked by motion_check.py)."""
    for it in L:
        if it.get('role') not in ('pillar', 'flame'):
            continue
        root = it['root']
        t_pass = CUE['U9'] - (-root[1]) / V_G
        to_road = unit(np.array([-root[0], -150.0, 0.0]))
        ax = unit(np.cross(np.array([0, 0, 1.0]), to_road))
        if it.get('role') == 'pillar':      # colossus class: <= 0.5 deg/s own motion (motion_check.py)
            it['anim'].append(dict(type='close', t0=t_pass + 1.5, t1=t_pass + 1.5 + 34.0, deg=11.0, axis=ax,
                                   prof='trap', ease=0.25))
        else:                                # mid class: <= 1.0 deg/s
            it['anim'].append(dict(type='close', t0=t_pass + 1.5, t1=t_pass + 1.5 + 28.0, deg=10.0, axis=ax, prof='ss'))
    return L


def build_layout(cache=True):
    """the v4 layout (cached on disk with the custom variants it registered)."""
    if cache and os.path.exists(LAYOUT_CACHE):
        try:
            d = pickle.load(open(LAYOUT_CACHE, 'rb'))
            if d.get('sig') == _layout_sig():
                for k, (sp, cl, cu) in d.get('custom', {}).items():
                    BL.VARIANTS[k] = sp
                    BL._CLINE[k] = cl
                    A4.CUSTOM[k] = cu
                return d['L']
        except Exception as ex:
            print('layout cache unusable:', ex)
    L = add_close(build_heroes() + build_others() + build_near() + build_rear())
    custom = {k: (BL.VARIANTS[k], BL._CLINE[k], A4.CUSTOM[k]) for k in A4.CUSTOM}
    pickle.dump(dict(sig=_layout_sig(), L=L, custom=custom), open(LAYOUT_CACHE, 'wb'))
    return L


def TD_SIG():
    import hashlib
    return hashlib.md5(open(TD.__file__).read().encode()).hexdigest()


def reveal_at(it, t):
    """_Reveal (0..1) of an instance at time t (round 3, tech B1): applied AFTER the fog cap, f = lerp(1, f, _Reveal);
    the renderer is off while it is 0. Keys are (t, value), smoothstep between."""
    ks = it.get('reveal')
    if not ks:
        return 1.0
    if t <= ks[0][0]:
        return float(ks[0][1])
    for (t0, v0), (t1, v1) in zip(ks[:-1], ks[1:]):
        if t <= t1:
            return float(v0 + (v1 - v0) * ss((t - t0) / max(t1 - t0, 1e-6)))
    return float(ks[-1][1])


def _layout_sig():
    import hashlib
    src = open(os.path.abspath(__file__)).read()
    a = src.index('# ======================================================================================' +
                  '====== the layout (v4')
    b = src.index('# ======================================================================================' +
                  '====== tide')
    return hashlib.md5((src[a:b] + open(A4.__file__).read() + TD_SIG()).encode()).hexdigest()


# ============================================================================================ tide
TIDE = dict(n=360, seed=13, dist=(4800.0, 12000.0), az=(-70.0, 70.0), size=(560.0, 1350.0), crest=600.0)
TIDE_ATLAS_V3 = os.path.join(HERE, 'Textures', 'TentacleTide_v3_Atlas.json')


def tide_cells():
    """the v3 atlas cells (run 6: v4 arm form, half of them clusters of 2-4 arms)."""
    return json.load(open(TIDE_ATLAS_V3))['cells']


def build_tide(cells=None, cfg=TIDE):
    """Run 6 (v3): the v2 tide (thin blades, uniform height, every base cut on the cloud-top line) read as a fringe of
    GRASS along the horizon. v3:
      - cells = TentacleTide_v3 (thick swan-neck arms; half of them clusters of 2-4 arms from one root area);
      - WAVES, not a lawn: the blades are grouped in surges along the azimuth (density 0.15..1 by a slow wave in az,
        so there are gaps of open haze between masses) and in crest rows 600 m apart in distance (phase lines);
      - the wave rises TOWARD THE WOUND: size x (0.55 .. 1.25) growing from az 70 to az 14, and nearer rows taller;
      - roots sunk 40-160 m into the deck and dissolved over a 60-180 m mist height (scene + shader), so there is no
        common base line;
      - nothing at the wound's foot (|az| < 13).
    (cells argument kept for old callers; v3 cells are always used.)"""
    cells = tide_cells()
    rng = np.random.default_rng(cfg['seed'])
    out = []
    n_crest = int((cfg['dist'][1] - cfg['dist'][0]) / cfg['crest'])
    singles = [c for c in cells if c['kind'] == 'single']
    clusters = [c for c in cells if c['kind'] != 'single']
    ph_l, ph_r = rng.uniform(0, 6.28), rng.uniform(0, 6.28)
    tries = 0
    while len(out) < cfg['n'] and tries < 200000:
        tries += 1
        az = float(rng.uniform(24.0, 70.0)) * (1 if rng.random() < 0.5 else -1)      # run 6: clear of the hands' feet
        # surges along the azimuth: a slow wave of density (period ~11 deg) -> masses with haze gaps between them
        ph = ph_r if az > 0 else ph_l
        dens = 0.15 + 0.85 * (0.5 + 0.5 * math.sin(math.radians(abs(az)) * 32.0 + ph)) ** 2
        dens *= 1.25 - 0.6 * (abs(az) - 24.0) / 46.0          # more toward the wound
        if rng.random() > dens:
            continue
        k = int(rng.integers(0, n_crest + 1))
        dt = cfg['dist'][0] + k * cfg['crest'] + rng.normal(0.0, 110.0)
        if not (cfg['dist'][0] <= dt <= cfg['dist'][1]):
            continue
        a = math.radians(az)
        toward = 1.25 - 0.70 * (abs(az) - 24.0) / 46.0              # the wave rises toward the wound
        near = 1.15 - 0.35 * (dt - cfg['dist'][0]) / (cfg['dist'][1] - cfg['dist'][0])
        tsc = float(os.environ.get('LANBAI_TIDE_SCALE', cfg.get('scale', 1.0)))      # (test hook)
        size = float(np.clip(rng.uniform(*cfg["size"]) * toward * near * tsc, 380.0 * tsc, 1600.0 * tsc))
        pool = clusters if rng.random() < 0.5 else singles
        c = pool[int(rng.integers(len(pool)))]
        sink = float(rng.uniform(40.0, 160.0))
        root = np.array([dt * math.sin(a), dt * math.cos(a), -sink])
        lean = float(rng.uniform(4.0, 16.0))
        t0 = CUE['U6'] + 4.0 + 6.5 * (cfg['dist'][1] - dt) / (cfg['dist'][1] - cfg['dist'][0])
        t0 += float(os.environ.get('LANBAI_TIDE_T0SHIFT', cfg.get('t0_shift', 0.0)))      # (test hook)
        depth = size * c['cell_height_in_lengths'] * math.cos(math.radians(lean)) * 0.85 + 40.0
        dist_e = float(np.linalg.norm(root - E_HERO))
        dur = float(np.clip(1.5 * math.degrees(depth / dist_e) / 0.45, 12.0, 48.0))     # run 6: crest peak <= ~0.45 deg/s
        out.append(dict(id='Tide_%03d' % len(out), cell=c, root=root, size=size, dist=dist_e,
                        dist_tear=float(dt), phase=float(dt / 600.0), lean=lean, sink=sink,
                        mist_h=float(rng.uniform(60.0, 180.0)),
                        anim=[dict(type='rise', t0=t0, t1=t0 + dur, depth=float(depth))]))
    return out


TIDE_REVEAL = [(CUE['U8'] - 5.0, 1.0), (CUE['U8'] + 1.0, 0.0)]


def tide_reveal(t):
    """the tide material's _Reveal (one value for all blades): it recedes into the haze before U8."""
    (t0, v0), (t1, v1) = TIDE_REVEAL
    return float(v0 + (v1 - v0) * ss((t - t0) / (t1 - t0)))


def tide_root_at(td, t):
    r = td['root'].copy()
    for a in td['anim']:
        if a['type'] == 'rise':
            r[2] -= a['depth'] * (1 - float(ss((t - a['t0']) / (a['t1'] - a['t0']))))
    return r


# ============================================================================================ shafts
def build_shafts(ring=None, seed=17):
    """Round 3 (critique B7.1): TWO beams, one per gap, never a fan: each leaves the lens at ~35-45 % of its height,
    passes through a clean gap (left: between the left hand and colossus 2; right: between the right hand and the
    Engel's body) and runs up and out into the dark, ending by el +25. 4-8 deg wide at 1.5 km, a smooth profile with no
    internal striation (Unity: Shaft_Gradient v4 = one soft lobe), unequal (left 1.0, right 0.6). Plus one
    multiplicative SHADOW WEDGE behind each hand bundle inside the band."""
    t = T_HERO
    S = tear_H(t) / TD.H
    e = E_HERO
    beams = [  # side, lens height frac, end az, end el, half-width (m at the lips), gain
        (-1, 0.38, -13.5, 17.0, 34.0, 1.0),
        (1, 0.44, 13.0, 21.0, 30.0, 0.6),
    ]
    out = []
    for i, (side, zf, az_e, el_e, hw, gain) in enumerate(beams):
        tt = zf * TD.T_TOP
        aL, aR = TD.lips(np.array([tt]))
        aa = float((aL[0] if side < 0 else aR[0]) * TD.width_mul(tear_open(t)) * 0.6)
        start = TD.P(tt, aa, -8.0)[()] * S
        E = e + 950.0 * dir_azel(az_e, el_e)
        ax = unit(E - start)
        length = 2200.0
        out.append(dict(id='Shaft_%02d' % i, start=start / S, axis=ax, half_width=hw / S, length=length / S,
                        kit_space=True, gain=float(gain), end_azel=(az_e, el_e), widen=3.2))
    wedges = []
    rng = np.random.default_rng(seed)
    for name, caz, cd in (('Hand_L', -7.5, 1130.0), ('Hand_R', 10.0, 1180.0)):
        side = -1.0 if caz < 0 else 1.0
        el0 = 5.0
        p0 = at_az(caz, cd + 80.0, 0.0)
        p0[2] = e[2] + (cd + 80.0) * math.tan(math.radians(el0))
        E = e + 700.0 * dir_azel(caz * 1.9 + side * 3.0, el0 + 5.0)
        ax = unit(E - p0)
        wedges.append(dict(id='Wedge_%s' % name, start=p0, axis=ax, half_width=80.0, length=900.0,
                           alpha=float(rng.uniform(0.15, 0.22)), widen=2.5))
    return out, wedges


# ============================================================================================ mist + far clouds
# Cloud kit cards placed as luminous mist strata between the depth layers (feet dissolving) and towering cumulus on
# the far horizon. (card, az deg from the U7b eye, distance m, base z m, width m, opacity, mirror, role)
MIST = [
    # round 3 (critique B1 / B6): no mist cards across arm bodies (they read as transparency / stripes); only low
    # wisps lying ON the deck (base <= 60 m) far out, and the root sleeves (gate_scene.root_sleeves)
    ('Cloud_Wisp_moon', -44.0, 3500.0, 8.0, 2600.0, 0.45, True, 'far left, on the deck'),
    ('Cloud_Wisp_moon', 44.0, 3300.0, 8.0, 2600.0, 0.45, False, 'far right, on the deck'),
]
FAR_CLOUDS = [
    ('Cloud_Congestus_moon', -36.0, 8200.0, -260.0, 3200.0, 0.8, True, 'towering cumulus far left'),
    ('Cloud_Congestus_moon', 41.0, 9000.0, -280.0, 3600.0, 0.8, False, 'towering cumulus far right'),
    ('Cloud_Bank_moon', -14.0, 7200.0, -200.0, 2700.0, 0.8, True, 'bank far left of the tear'),   # run 6: lower (the tide crowns rise above it)
    ('Cloud_Bank_moon', 17.0, 7600.0, -200.0, 2900.0, 0.8, False, 'bank far right of the tear'),
]


def mist_positions(spec):
    e = eye_cf(T_HERO)
    out = []
    for (card, az, d, z, w, op, mir, role) in spec:
        a = math.radians(az)
        out.append(dict(card=card, loc=np.array([e[0] + d * math.sin(a), e[1] + d * math.cos(a), z]), width=w,
                        opacity=op, mirror=mir, role=role))
    return out


# ---------------------------------------------------------------------------------------------- horizon relief (run 6)
def horizon_relief(seed=91, n=22):
    """Run 6: a flat far deck makes a ruler-straight horizon on which every tide base sits (the 'lawn' read). A band of
    low moonlit cloud masses (Cumulus / Puff / Bank / Strato cards, 4.2-9.5 km, az +-14..70, 90-330 m showing above
    the deck) interleaved in depth with the tide rows gives the horizon relief: the arms rise from behind cloud heads
    at different heights, as the giants rise from their towers. Same 'far' card material as FAR_CLOUDS / towers
    (Unity: the Clouds/ moon cards, sorted with the tide, queue 2990)."""
    rng = np.random.default_rng(seed)
    cards = [('Cloud_Strato_moon', 0.19), ('Cloud_Bank_moon', 0.22), ('Cloud_Puff_moon', 0.33), ('Cloud_Wisp_moon', 0.15),
             ('Cloud_Strato_moon', 0.19)]
    out = []
    for i in range(n):
        side = -1 if i % 2 == 0 else 1
        az = side * float(rng.uniform(14.0, 70.0))
        d = float(rng.uniform(4200.0, 9500.0))
        card, hk = cards[int(rng.integers(len(cards)))]
        vis = float(rng.uniform(90.0, 230.0))                 # m showing above the deck
        sink = float(rng.uniform(50.0, 110.0))
        w = (vis + sink) / hk
        out.append((card, az, d, -sink, w, 0.9, bool(rng.random() < 0.5), 'horizon relief'))
    return out


# ============================================================================================ towers (round 3, B8)
# Every colossus is born inside a towering cumulus (deliver/Clouds Cloud_Congestus_moon / Cloud_Bank_moon, 450-850 m
# tall) standing on the deck at its root, a little in front of it: at U6 the frame holds only the wound, the moon and
# this silver weather; on its _Reveal the crown tears out of the tower top, and the tower then SAGS (scale y 1 -> 0.72
# over 25 s, pivot at its base) and thins (alpha 1 -> 0.8) as if the arm had dragged cloud down with it.
TOWER_FOR = ('background', 'rilke', 'engel', 'moon')


def tower_specs(layout):
    e = eye_cf(T_HERO)
    rng = np.random.default_rng(77)
    out = []
    for it in layout:
        if it.get('role') not in TOWER_FOR:
            continue
        r = np.asarray(it['root'], float)
        d = r[:2] - e[:2]
        dist = float(np.linalg.norm(d))
        tow = -d / dist                                   # toward the eye
        h = float(rng.uniform(480.0, 820.0)) * (1.15 if it['role'] == 'engel' else 1.0)
        card = 'Cloud_Congestus_moon' if rng.random() < 0.7 else 'Cloud_Bank_moon'
        w = h / (0.81 if card == 'Cloud_Congestus_moon' else 0.45)
        loc = np.array([r[0] + tow[0] * 140.0, r[1] + tow[1] * 140.0, -25.0])
        rev = it.get('reveal') or []
        t_rev = float(rev[0][0]) if rev else float(next((a['t0'] for a in it['anim'] if a['type'] == 'rise'), CUE['U6']))
        out.append(dict(id='Tower_' + it['id'], card=card, loc=loc, width=float(w), height=float(h), opacity=0.92,
                        mirror=bool(r[0] < e[0] + 400.0), role='tower', hides=it['id'],
                        sag=[[t_rev, 1.0], [t_rev + 25.0, 0.72]],
                        # tech M11: the towers have done their work once the giants stand; they thin and are gone by
                        # U8 - 1 (U8 / U8 + 7 overdraw budget)
                        alpha=[[t_rev, 1.0], [max(t_rev + 6.0, CUE['U7b'] + 4.0), 0.8], [CUE['U8'] - 1.0, 0.0]]))
    return out


# ============================================================================================ cloud cards
# gate-specific cloud cards (CF, relative to the tear foot) are generated in gate_scene.cloud_sea() and exported
# from there (GateLayout_v2.json 'clouds').


if __name__ == '__main__':
    import time
    t0 = time.time()
    lay = build_layout(cache='--nocache' not in sys.argv)
    print(len(lay), 'instances in %.1fs' % (time.time() - t0))
    from collections import Counter
    print(Counter(it['layer'] for it in lay))
    for t in ('U6', 'U7', 'U7b', 'U8', 'U9'):
        tt = CUE[t]
        e = eye_cf(tt)
        H = tear_H(tt)
        top = math.degrees(math.atan((H - e[2]) / gate_z(tt))) if gate_z(tt) > 1 else 90
        print(t, 'z %.1f  h_bus %.1f  H %.0f  top %.1f deg  open %.3f rip %.2f' % (gate_z(tt), h_bus(tt), H, top,
                                                                                  tear_open(tt), rip_progress(tt)))
    e = eye_cf(T_HERO)
    for it in lay:
        if it['layer'] in ('colossus',):
            W, u = world_centreline(it, T_HERO, 6)
            az, el = azel_of(W - e)
            k = int(np.argmax(el))
            print('%-12s root az %6.1f d %6.0f  crown az %6.1f el %5.1f  top %5.0f m  girth %.2f' % (
                it['id'], *azel_of(it['root'] - e)[:1], np.linalg.norm(it['root'] - e), az[k], el[k], W[:, 2].max(),
                it['girth']))


# ============================================================================================ cloud-sea light pool
# Round 2 (critique B5): the wound lights the cloud it stands on: a pool (Tear_CloudGlow, #495270 target, L* 30-36
# within 300 m of the foot -> plain cloud by 1.2 km) cut by RADIAL SHADOW LANES cast by the ring's roots (light from
# the white core), root-wide, 400-1200 m long, penumbra growing 1:8. Baked into a 1024^2 mask (Unity:
# Tear_CloudLanes_1024.png multiplied into Tear_CloudGlow; same CF rectangle LANES_RECT) and a foot CREVASSE: the
# tear runs on into the cloud toward the bus, 700 m long, its floor glowing #C0B9E4.
LANES_RECT = (-2000.0, 2000.0, -2400.0, 1600.0)     # x0, x1, y0, y1 (CF m, tear foot = origin)
CREVASSE = dict(length=240.0, w0_frac=0.32, wander=8.0)   # run 6: 700 m read as a crack / river drawn to the camera; now the foot's own split


def lane_mask(layout, t=None, n=1024):
    t = T_HERO if t is None else t
    x0, x1, y0, y1 = LANES_RECT
    X, Y = np.meshgrid(np.linspace(x0, x1, n), np.linspace(y1, y0, n))      # row 0 = far (+y): image top
    core = tear_core_cf(t)
    M = np.ones_like(X)
    rng = np.random.default_rng(5)
    for it in layout:
        if it['layer'] not in ('mid', 'colossus') or it.get('frame') == 'bus':
            continue
        r0 = it['root']
        rc = np.array([r0[0], r0[1]])
        if np.hypot(*rc) > 1600.0 or rc[1] > 300.0:
            continue
        rr = float(arm_radius(it, np.array([0.08]))[0])
        d = rc - core[:2]
        dl = np.linalg.norm(d)
        if dl < 1e-3:
            continue
        dn = d / dl
        L = rng.uniform(400.0, 1200.0) * (1.4 if it.get('role') == 'pillar' else 1.0)
        px, py = X - rc[0], Y - rc[1]
        s = px * dn[0] + py * dn[1]                      # along the lane (from the root, away from the light)
        q = np.abs(-px * dn[1] + py * dn[0])             # across
        hw = rr + np.maximum(s, 0) / 16.0                # umbra half-width (penumbra grows 1:8 overall)
        pen = 2.0 + np.maximum(s, 0) / 8.0
        lane = G_ss((hw + pen - q) / pen) * G_ss(s / 20.0) * G_ss((L - s) / (0.35 * L))
        M *= 1.0 - 0.85 * lane
    return M.astype(np.float32)


def G_ss(x):
    return ss(np.asarray(x, float))


def crevasse_xw(y, t=None):
    """centre x and full width (m) of the foot crevasse at CF y (y < 0 toward the bus); width 0 outside."""
    t = T_HERO if t is None else t
    y = np.asarray(y, float)
    L = CREVASSE['length']
    s = np.clip(-y / L, 0.0, 1.0)
    w0 = CREVASSE['w0_frac'] * 2 * tear_half_width(t)
    w = w0 * (1.0 - s) ** 0.8 * (y < 20.0)
    xc = CREVASSE['wander'] * np.sin(y / 97.0) * s + 0.5 * TD.path(np.array([0.0]))[0] * tear_H(t) / TD.H
    return xc, w
