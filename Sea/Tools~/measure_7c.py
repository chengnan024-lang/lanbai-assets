"""7c window / mirror measurements for D-23 (the inverted Snell window seen from above it, the plane BELOW the eye).

  ~/bpy/bin/python Sea/Tools~/measure_7c.py <dir with graded.png> --pitch -45 [--yaw 0] [--hfov 90]

Bins by the view ray's angle from straight down, as a fraction r of the critical angle (48.6 deg):
  core  r 0.00-0.55   (D-23: the dusk sky's indigo, ~#2E3C66, L* <= 40)
  trans r 0.72-0.88   (the transition: must not pass through lilac, D-17 / D-21)
  ring  r 0.88-0.97   (D-23: the outer 25-30 % of the radius goes warm, to #4E3B39)
  tir   r 1.08-1.60   (the dark mirror around the window)
Lamps: the brightest 0.3 % pixels of the tir zone; their hue split by the reflected ray's elevation (near / far):
D-23 wants them yellower and greyer with distance (h_ab 78-80), never orange.
Prints medians (hex, L*, h_ab, C*) and dE2000 to the targets. Only the pixels the camera sees count."""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sea_numpy as S                                                  # noqa: E402

sys.path.insert(0, os.path.join(HERE, '..', '..', 'Engineering', 'render_harness'))
from lbh.measure import lab                                            # noqa: E402


def hexof(c):
    return '#%02X%02X%02X' % tuple(int(round(x)) for x in c)


def lab1(c):
    L, a, b = lab(np.asarray(c, float)[None, None, :])
    return float(L[0, 0]), float(a[0, 0]), float(b[0, 0])


def de2000(c1, c2):
    L1, a1, b1 = lab1(c1); L2, a2, b2 = lab1(c2)
    C1, C2 = math.hypot(a1, b1), math.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - math.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p, a2p = a1 * (1 + G), a2 * (1 + G)
    C1p, C2p = math.hypot(a1p, b1), math.hypot(a2p, b2)
    h1p = math.degrees(math.atan2(b1, a1p)) % 360; h2p = math.degrees(math.atan2(b2, a2p)) % 360
    dL, dC = L2 - L1, C2p - C1p
    dh = h2p - h1p
    if C1p * C2p == 0: dh = 0
    elif dh > 180: dh -= 360
    elif dh < -180: dh += 360
    dH = 2 * math.sqrt(C1p * C2p) * math.sin(math.radians(dh / 2))
    Lm, Cmp = (L1 + L2) / 2, (C1p + C2p) / 2
    hm = (h1p + h2p) / 2 if abs(h1p - h2p) <= 180 else (h1p + h2p + 360) / 2
    if C1p * C2p == 0: hm = h1p + h2p
    T = 1 - 0.17 * math.cos(math.radians(hm - 30)) + 0.24 * math.cos(math.radians(2 * hm)) + 0.32 * math.cos(math.radians(3 * hm + 6)) - 0.2 * math.cos(math.radians(4 * hm - 63))
    Sl = 1 + 0.015 * (Lm - 50) ** 2 / math.sqrt(20 + (Lm - 50) ** 2); Sc = 1 + 0.045 * Cmp; Sh = 1 + 0.015 * Cmp * T
    Rt = -2 * math.sqrt(Cmp ** 7 / (Cmp ** 7 + 25 ** 7)) * math.sin(math.radians(60 * math.exp(-((hm - 275) / 25) ** 2)))
    return math.sqrt((dL / Sl) ** 2 + (dC / Sc) ** 2 + (dH / Sh) ** 2 + Rt * (dC / Sc) * (dH / Sh))


def desc(px, target=None):
    if len(px) == 0:
        return None
    m = np.median(px, axis=0)
    L, a, b = lab1(m)
    o = dict(median=hexof(m), Lstar=round(L, 1), h_ab=round(math.degrees(math.atan2(b, a)) % 360, 1), C=round(math.hypot(a, b), 1), n=int(len(px)))
    if target:
        t = np.array([int(target[i:i + 2], 16) for i in (1, 3, 5)], float)
        o['dE2000_to_' + target.lstrip('#')] = round(de2000(m, t), 1)
    return o


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--pitch', type=float, default=-45.0)
    ap.add_argument('--yaw', type=float, default=0.0)
    ap.add_argument('--hfov', type=float, default=90.0)
    a = ap.parse_args()
    im = np.asarray(Image.open(os.path.join(a.dir, 'graded.png')).convert('RGB')).astype(float)
    H, W = im.shape[:2]
    rays = S.camera_rays(W, H, a.hfov, a.yaw, a.pitch)
    crit = math.asin(1 / 1.333)
    down = rays[..., 1] < -1e-3
    r = np.arccos(np.clip(-rays[..., 1], -1, 1)) / crit
    # the cabin shell / interior is near-black: leave it out
    lum = im @ np.array([0.2126, 0.7152, 0.0722])
    seen = down & (lum > 6)
    out = dict(core=desc(im[seen & (r < 0.55)], '#2E3C66'), trans=desc(im[seen & (r > 0.72) & (r < 0.88)]), ring=desc(im[seen & (r > 0.88) & (r < 0.97)], '#4E3B39'),
               tir=desc(im[seen & (r > 1.08) & (r < 1.6)]))
    tz = seen & (r > 1.02)
    if tz.sum() > 100:
        thr = np.percentile(lum[tz], 99.7)
        lamps = tz & (lum >= thr)
        el = np.degrees(np.arcsin(np.clip(-rays[..., 1], -1, 1)))          # depression below the horizon
        med = np.median(el[lamps])
        out['lamps_near'] = desc(im[lamps & (el >= med)])                  # steeper = nearer reflections
        out['lamps_far'] = desc(im[lamps & (el < med)])
    print(json.dumps(out, ensure_ascii=False))


if __name__ == '__main__':
    main()
