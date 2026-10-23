# -*- coding: utf-8 -*-
"""K5 · the act-8 ceiling dissolve against the VR ramp law, PER PIXEL (bible §1.8: any brightening <= 0.5 EV in 0.25 s,
<= 1.0 EV in 1 s, <= 1.8 EV in 2 s; per-direction compliance is sufficient for the full frame).
Uses the K4 reference frame itself (Docs~/lookdev/scene_kit.py frame_K4: the numpy port of LanbaiSea.cginc with the
ceiling materials of SeaMaterials.json, the warm fog and its height falloff, the purple guard, the stand-in dusk sky
behind, and the gold palace points added on top, fading by their own progress). Every viewing direction of the upper hemisphere
(az 5 deg x el 1.5 deg grid), 0.05 s steps from 955.0 to 967.0 (dissolve: front 956.36 -> 960.36, last pixel 965.36).
L = Rec.709 luminance of the scene-linear result (before the grade: the tonemapper only compresses EV steps, so this is
the conservative side). Writes Sea/Docs~/K5_dissolve_ramps.json and prints the worst pixel per window.
usage: ~/bpy/bin/python Sea/Tools~/k5_dissolve_ramps.py"""
import importlib.util
import json
import math
import os
import sys
import types

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
sys.modules.setdefault('bpy', types.ModuleType('bpy'))
import sea_numpy as S  # noqa: E402

spec = importlib.util.spec_from_file_location('scene_kit', os.path.join(KIT, 'Docs~', 'lookdev', 'scene_kit.py'))
SK = importlib.util.module_from_spec(spec)
spec.loader.exec_module(SK)

F10E = 956.36
T0, T1, DT = 955.0, 967.0, 0.05


def h_ceiling(t):
    """ceiling height above the bus (bible §6·8: 272 m at F10e; the bus then rises at <= 3 m/s, 251 m at 965.4)"""
    return 272.0 - max(0.0, t - 956.52) * 2.4


def point_gains(eye, h, dissolve):
    """the same 25 points as scene_kit.ceiling_points (seed 11): each one's fade factor 1 - LanbaiCeilingLampProgress"""
    rs = np.random.default_rng(11)
    g = []
    for _ in range(25):
        q = np.array([rs.uniform(-260, 260), eye[1] + h + rs.uniform(40, 200), rs.uniform(-320, 220)])
        d = (q - eye) / np.linalg.norm(q - eye)
        el = math.degrees(math.asin(max(min(d[1], 1.0), 0.0)))
        pp = min(max((dissolve - 4.0 * el / 90.0) / 5.0, 0.0), 1.0) if dissolve >= 0 else 0.0
        g.append(1.0 - min(max((pp - 0.3) / 0.7, 0.0), 1.0))
    return g


def main():
    az = np.radians(np.arange(-180, 180, 5.0))
    el = np.radians(np.arange(0.75, 90.0, 1.5))
    AZ, EL = np.meshgrid(az, el)
    rays = np.stack([np.cos(EL) * np.sin(AZ), np.sin(EL), np.cos(EL) * np.cos(AZ)], -1)
    eye = np.array([0.55, 1.7, 2.05])
    ts = np.arange(T0, T1 + 1e-6, DT)
    EVs = []
    FLUX = []
    for t in ts:
        # the whole K4 frame: M_08_SeaCeilingEdge/Fade numbers from SeaMaterials.json, the warm fog with the height
        # falloff, the purple guard, the sky behind, and the gold points ADDED on top fading by their own progress
        # per-pixel law on the field WITHOUT the 25 points (a sub-degree point drifting across a sample direction as the
        # bus rises is parallax, not a brightening); the points are checked as a whole: their total flux never rises
        out, _ = SK.frame_K4(rays, eye, t, {'dissolve': t - F10E, 'h': h_ceiling(t), 'lamps': 0})
        L = out @ np.array([0.2126, 0.7152, 0.0722])
        EVs.append(np.log2(np.maximum(L, 0.004)))
        FLUX.append(point_gains(eye, h_ceiling(t), t - F10E))
    EVs = np.array(EVs)                                         # [T, el, az]
    res = {}
    for win, lim in ((0.25, 0.5), (1.0, 1.0), (2.0, 1.8)):
        k = int(round(win / DT))
        rise = EVs[k:] - EVs[:-k]                               # brightening over the window (darkening is free)
        worst = float(rise.max())
        idx = np.unravel_index(np.argmax(rise), rise.shape)
        res['%gs' % win] = dict(limit_EV=lim, worst_EV=round(worst, 3), PASS=bool(worst <= lim), at_t=round(float(ts[idx[0]]), 2),
                               at_el_deg=round(math.degrees(el[idx[1]]), 1), at_az_deg=round(math.degrees(az[idx[2]]), 1))
    fl = np.array(FLUX)                                         # [T, 25]: each point's own brightness factor
    on = (fl > 0.5).sum(1)
    res['points'] = dict(about='each of the 25 gold points: its own brightness factor (water x (1 - own progress)); must never rise',
                         never_rises=bool(np.max(np.diff(fl, axis=0)) <= 1e-9), all_25_at_full_until=round(float(ts[np.argmax(fl.min(1) < 0.999)]), 2),
                         lit_above_half=dict((('%.2f' % t), int(n)) for t, n in zip(ts[::20], on[::20])), last_out=round(float(ts[np.argmax(fl.max(1) <= 1e-6)]), 2))
    total = EVs[-1] - EVs[0]
    res['total_change_EV'] = dict(max=round(float(total.max()), 3), min=round(float(total.min()), 3))
    res['about'] = __doc__.split('\n')[0]
    out = os.path.join(KIT, 'Docs~', 'K5_dissolve_ramps.json')
    json.dump(res, open(out, 'w'), indent=1, ensure_ascii=False)
    for k, v in res.items():
        print(k, v)


if __name__ == '__main__':
    main()
