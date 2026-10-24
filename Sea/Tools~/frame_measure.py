# -*- coding: utf-8 -*-
"""Measure the sea's reference frames the way the final review did (sRGB -> Lab D65, CIEDE2000).
  ~/bpy/bin/python Sea/Tools~/frame_measure.py K2 <dir with graded.png + metrics.json>   (also K3, K4, K6)
Prints a JSON of the numbers the review asked for and writes measure.json next to the frame."""
import json
import math
import os
import sys

import numpy as np
from PIL import Image


def srgb_lin(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lab(rgb8):
    lin = srgb_lin(rgb8)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > 216 / 24389, np.cbrt(xyz), (24389 / 27 * xyz + 16) / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def de2000(l1, l2):
    L1, a1, b1 = np.moveaxis(l1, -1, 0); L2, a2, b2 = np.moveaxis(np.broadcast_to(l2, l1.shape), -1, 0)
    C1 = np.hypot(a1, b1); C2 = np.hypot(a2, b2); Cm = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cm ** 7 / (Cm ** 7 + 25 ** 7)))
    a1p = (1 + G) * a1; a2p = (1 + G) * a2
    C1p = np.hypot(a1p, b1); C2p = np.hypot(a2p, b2)
    h1 = np.degrees(np.arctan2(b1, a1p)) % 360; h2 = np.degrees(np.arctan2(b2, a2p)) % 360
    dL = L2 - L1; dC = C2p - C1p
    dh = h2 - h1; dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh)); dh = np.where(C1p * C2p == 0, 0, dh)
    dH = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lm = (L1 + L2) / 2; Cpm = (C1p + C2p) / 2
    hs = h1 + h2; hm = np.where(np.abs(h1 - h2) > 180, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2), hs / 2); hm = np.where(C1p * C2p == 0, hs, hm)
    T = 1 - 0.17 * np.cos(np.radians(hm - 30)) + 0.24 * np.cos(np.radians(2 * hm)) + 0.32 * np.cos(np.radians(3 * hm + 6)) - 0.2 * np.cos(np.radians(4 * hm - 63))
    dth = 30 * np.exp(-((hm - 275) / 25) ** 2); RC = 2 * np.sqrt(Cpm ** 7 / (Cpm ** 7 + 25 ** 7))
    SL = 1 + 0.015 * (Lm - 50) ** 2 / np.sqrt(20 + (Lm - 50) ** 2); SC = 1 + 0.045 * Cpm; SH = 1 + 0.015 * Cpm * T
    RT = -np.sin(np.radians(2 * dth)) * RC
    return np.sqrt((dL / SL) ** 2 + (dC / SC) ** 2 + (dH / SH) ** 2 + RT * (dC / SC) * (dH / SH))


def hexc(c):
    return '#%02X%02X%02X' % tuple(int(round(x)) for x in c)


def tgt(h):
    return lab(np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)], np.float64))


def luma8(img):
    return img @ np.array([0.2126, 0.7152, 0.0722])


def region(img, mask):
    px = img[mask]
    L = lab(px)
    med = np.median(px, 0)
    ml = lab(med)
    return dict(median=hexc(med), Lstar=round(float(ml[0]), 1), h_ab=round(float(math.degrees(math.atan2(ml[2], ml[1])) % 360), 1),
                C=round(float(math.hypot(ml[1], ml[2])), 1), pct=round(float(mask.mean() * 100), 2)), L


def main():
    kind, d = sys.argv[1], sys.argv[2]
    img = np.asarray(Image.open(os.path.join(d, 'graded.png')).convert('RGB'), np.float64)
    H, W = img.shape[:2]
    y = luma8(img)
    lin = srgb_lin(img) @ np.array([0.2126, 0.7152, 0.0722])
    out = dict(APL=round(float(y.mean()), 1))
    if kind == 'K2':
        cam = json.load(open(os.path.join(d, 'metrics.json')))['cam']
        tx = math.tan(math.radians(cam['hfov_deg']) / 2); ty = tx * H / W
        X, Y = np.meshgrid(((np.arange(W) + 0.5) / W * 2 - 1) * tx, (1 - (np.arange(H) + 0.5) / H * 2) * ty)
        pc, ps = math.cos(math.radians(cam['pitch_deg'])), math.sin(math.radians(cam['pitch_deg']))
        dy = (Y * pc + ps) / np.sqrt(X * X + Y * Y + 1)
        zen = np.degrees(np.arccos(np.clip(dy, -1, 1)))          # angle from straight up; the window rim is at 48.6
        win = zen < 15.0
        rimz = (zen > 38.0) & (zen < 50.0)
        out['regions'] = 'core = within 15 deg of the zenith; rim = 38..50 deg from the zenith (critical angle 48.6)'
        r, Lw = region(img, win)
        out['core'] = r
        out['core_dE2000_to_E6F3F8_median'] = round(float(np.median(de2000(Lw, tgt('#E6F3F8')))), 1)
        out['core_brightest_luma'] = round(float(y[win].max()), 1)
        out['core_mean_lin'] = float(lin[win].mean())
        rest = rimz
        out['rim_brightest_luma'] = round(float(y[rest].max()), 1)
        out['rim_p99.9_minus_core_median_EV'] = round(math.log2(float(np.percentile(lin[rest], 99.9)) / float(np.percentile(lin[win], 50))), 2)
        out['rim_peak_minus_core_peak_EV'] = round(math.log2(float(lin[rest].max()) / float(lin[win].max())), 2)
        out['frame_brightest_zenith_deg'] = round(float(zen.ravel()[np.argmax(y)]), 1)
        dark = (zen > 52.0) & (zen < 62.0)                    # the dark mirror just outside the window
        if dark.sum() < 50:
            dark = zen > 52.0
        r2, Ld = region(img, dark) if dark.sum() >= 50 else (dict(median='n/a'), np.zeros((1, 3)))
        out['dark_mirror'] = r2
        out['dark_mirror_dE2000_to_11395E_median'] = round(float(np.median(de2000(Ld, tgt('#11395E')))), 1)
    if kind == 'K3':
        top = y >= np.percentile(y, 99.8)
        out['brightest_0.2pct'], Lb = region(img, top)
        out['brightest_luma'] = round(float(y.max()), 1)
        out['arc_dE2000_to_C98A7A'] = round(float(np.median(de2000(Lb, tgt('#C98A7A')))), 1)
        Lall = lab(img)
        hh = np.degrees(np.arctan2(Lall[..., 2], Lall[..., 1])) % 360
        vals, counts = np.unique((img // 4).reshape(-1, 3), axis=0, return_counts=True)
        out['most_common_colour_pct'] = round(float(counts.max() / counts.sum() * 100), 1)
        out['most_common_colour'] = hexc(vals[counts.argmax()] * 4 + 2)
    if kind == 'K4':
        cam = json.load(open(os.path.join(d, 'metrics.json')))['cam']
        tx = math.tan(math.radians(cam['hfov_deg']) / 2); ty = tx * H / W
        X, Y = np.meshgrid(((np.arange(W) + 0.5) / W * 2 - 1) * tx, (1 - (np.arange(H) + 0.5) / H * 2) * ty)
        pc, ps = math.cos(math.radians(cam['pitch_deg'])), math.sin(math.radians(cam['pitch_deg']))
        el = np.degrees(np.arcsin(np.clip((Y * pc + ps) / np.sqrt(X * X + Y * Y + 1), -1, 1)))
        band = (el > 2.0) & (el < 7.0)
        if band.sum() > 50:
            out['mirror_band_el_2_7'], _ = region(img, band)
        # left / right ripple symmetry: mean |high-pass| of luma in the ceiling (el > 4), left third vs right third
        from scipy.ndimage import gaussian_filter
        hp = np.abs(y - gaussian_filter(y, 3.0))
        ceil = el > 4.0
        lt = ceil.copy(); lt[:, W // 3:] = False
        rt = ceil.copy(); rt[:, :2 * W // 3] = False
        if lt.sum() > 50 and rt.sum() > 50:
            out['ripple_right_over_left'] = round(float(hp[rt].mean() / max(hp[lt].mean(), 1e-6)), 2)
        # the lamp points: local maxima well above their surroundings
        from scipy.ndimage import maximum_filter
        loc = (y == maximum_filter(y, 15)) & (y - gaussian_filter(y, 8.0) > 20) & (el > 8.0)
        pts = img[loc]
        if len(pts):
            Lp = lab(pts)
            hh = np.degrees(np.arctan2(Lp[:, 2], Lp[:, 1])) % 360
            out['lamp_points'] = dict(n=int(len(pts)), cores=[hexc(p) for p in pts[:12]], h_ab_range=[round(float(hh.min()), 1), round(float(hh.max()), 1)],
                                      h_ab_median=round(float(np.median(hh)), 1), C_median=round(float(np.median(np.hypot(Lp[:, 1], Lp[:, 2]))), 1),
                                      Lstar_median=round(float(np.median(Lp[:, 0])), 1))
        Lall = lab(img)
        hh = np.degrees(np.arctan2(Lall[..., 2], Lall[..., 1])) % 360
        Ca = np.hypot(Lall[..., 1], Lall[..., 2])
        sel = (hh >= 290) & (hh <= 330) & (el > 0.5)
        out['max_C_in_h290_330_above_horizon'] = round(float(Ca[sel].max()), 1) if sel.any() else 0.0
    json.dump(out, open(os.path.join(d, 'measure.json'), 'w'), indent=1)
    print(json.dumps(out, indent=1))


if __name__ == '__main__':
    main()
