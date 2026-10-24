# -*- coding: utf-8 -*-
"""The numbers every reference frame reports (same definitions as Gate/Source/gate_metrics.py and the local
gate_test, so cloud renders and Unity screenshots are directly comparable). Input = 8-bit sRGB display codes.

APL                 mean Rec.709 luma of the sRGB codes, 0..255 (bible §2 / §1.5 calibration step 4)
EV_display          log2(max(mean relative luminance (display-linear), 0.004)) (bible §1.8 ramp law's L)
brightest           the brightest 2000 px at 1920x1080 (scaled with the pixel count) by display luminance: bbox, centroid, centroid az / el (when a camera is
                    given), how many separate clusters they form (bible §1.3 #1: one brightest point per frame)
purple              % pixels with h_ab 290..325 and C* > 15 (bible §1.3 #4: <= 2 % outside acts 4 / 4c);
                    act-4 strong violet (C* > 30), act-6 lavender (h 285..330, C* > 12)
palette             per swatch of the act palette (Art/tools/v21/scene_data_v21.py): nearest pixels (p0.1 of CIEDE2000) and
                    % pixels within dE 5; per pixel: dE2000 to the nearest swatch (median, p90)
top25_Lstar         L* of the top quarter of the frame (mean, p50, p90) (gate test 'upper 25 %')
clip                pure black (every channel <= #030409) / pure white (luma >= 246, #F4F7FA): % and the largest connected
                    region % (bible §1.3 #5: no REGION > 2 %); warm_shadow_pct = L* < 25, C* > 6, h 20-100 (§1.3 #2)
                    — these and the palette ΔE2000 follow the art review's definitions (Review/标准.md §2)
luma_lt12, Lstar_gt85  % pixels (gate_metrics)
CIE Lab: sRGB D65, as gate's metrics.lab."""
import math

import numpy as np
from scipy.ndimage import label, binary_dilation

LUMA = np.array([0.2126, 0.7152, 0.0722])


def srgb_to_lin(c):
    c = np.asarray(c, np.float64) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lab(codes):
    """sRGB codes (..., 3) -> L*, a*, b* (D65)."""
    lin = srgb_to_lin(codes)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = lin @ M.T
    wp = np.array([0.95047, 1.0, 1.08883])
    t = xyz / wp
    d = 6.0 / 29.0
    f = np.where(t > d ** 3, np.cbrt(t), t / (3 * d * d) + 4.0 / 29.0)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b


def de2000(l1, l2):
    """CIEDE2000, l1 (..., 3) vs l2 (3,) — same code as Review/Tools~/measure.py (the art review's definition)."""
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp, dCp, dh = L2 - L1, C2p - C1p, h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(C1p * C2p == 0, 0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp, Cbp, hs = (L1 + L2) / 2, (C1p + C2p) / 2, h1p + h2p
    hbp = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) > 180, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2), hs / 2))
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    dth = 30 * np.exp(-((hbp - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc, Sh = 1 + 0.045 * Cbp, 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def largest_region_pct(mask, work_w=480):
    """bible §1.3 '>2 % of the frame' read as the largest 8-connected region (downsampled to 480 wide) = Review's rule."""
    if not mask.any():
        return 0.0
    h, w = mask.shape
    s = max(1, w // work_w)
    m = mask[:h - h % s, :w - w % s].reshape(h // s, s, w // s, s).mean((1, 3)) > 0.5
    if not m.any():
        return 0.0
    lab_, n = label(m, structure=np.ones((3, 3)))
    sizes = np.bincount(lab_.ravel())[1:]
    return float(sizes.max() / m.size * 100)


def hex_codes(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float)


def pix_azel(cam, W, H):
    """per-pixel (az, el) in degrees for a harness camera dict (yaw/pitch/hfov; pinhole, square pixels)."""
    hf = math.radians(cam['hfov_deg'])
    fx = (W / 2.0) / math.tan(hf / 2.0)
    xs = (np.arange(W) + 0.5 - W / 2.0) / fx
    ys = -(np.arange(H) + 0.5 - H / 2.0) / fx
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([X, Y, np.ones_like(X)], -1)
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    p = math.radians(cam.get('pitch_deg', 0.0))
    y = math.radians(cam.get('yaw_deg', 0.0))
    Rx = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])   # pitch up (+el)
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])   # yaw right (+az)
    # camera space x right, y up, z forward (Unity); world = Ry @ Rx @ d
    dw = d @ (Ry @ Rx).T
    az = np.degrees(np.arctan2(dw[..., 0], dw[..., 2]))
    el = np.degrees(np.arcsin(np.clip(dw[..., 1], -1, 1)))
    return az, el


def measure(codes, act=None, cam=None, n_bright=2000, mask=None):
    """codes: (H, W, 3) uint8/float display codes. act: palette key ('04', '06', ...) or None.
    mask: optional bool (H, W): restrict to these pixels (e.g. through the glass)."""
    im = np.asarray(codes, np.float64)[..., :3]
    H, W = im.shape[:2]
    sel = np.ones((H, W), bool) if mask is None else mask
    luma = im @ LUMA
    lum_lin = srgb_to_lin(im) @ LUMA
    L, a, b = lab(im)
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360
    n = float(sel.sum())
    o = dict(size=[W, H])
    o['APL'] = round(float(luma[sel].mean()), 2)
    o['EV_display'] = round(float(np.log2(max(lum_lin[sel].mean(), 0.004))), 3)
    o['luma_lt12_pct'] = round(float((luma[sel] < 12).sum() / n * 100), 2)
    o['Lstar_gt85_pct'] = round(float((L[sel] > 85).sum() / n * 100), 3)
    blk = np.all(im <= np.array([3, 4, 9]), -1) & sel          # <= #030409 per channel (Review's definition)
    wht = (luma >= 246) & sel                                   # >= luma of #F4F7FA
    o['clip_black_pct'] = round(float(blk.sum() / n * 100), 3)
    o['clip_white_pct'] = round(float(wht.sum() / n * 100), 3)
    o['clip_black_largest_region_pct'] = round(largest_region_pct(blk), 2)
    o['clip_white_largest_region_pct'] = round(largest_region_pct(wht), 2)
    warm = (L < 25) & (C > 6) & (h >= 20) & (h <= 100) & sel   # §1.3 #2: no warm colour in the shadows
    o['warm_shadow_pct'] = round(float(warm.sum() / n * 100), 2)
    pur = (h >= 290) & (h <= 325) & (C > 15) & sel
    o['purple_pct'] = round(float(pur.sum() / n * 100), 3)
    o['purple_largest_region_pct'] = round(largest_region_pct(pur), 2)
    o['violet_strong_pct'] = round(float(((h >= 290) & (h <= 325) & (C > 30) & sel).sum() / n * 100), 3)
    o['lavender_act6_pct'] = round(float(((h >= 285) & (h <= 330) & (C > 12) & sel).sum() / n * 100), 3)
    # brightest 2000 px
    flat = np.where(sel, lum_lin, -1).ravel()
    k = min(max(50, int(round(n_bright * H * W / (1920.0 * 1080.0)))), int(n))   # 2000 px at 1080p, scaled with the frame
    idx = np.argpartition(-flat, k - 1)[:k]
    ys, xs = np.unravel_index(idx, (H, W))
    bm = np.zeros((H, W), bool)
    bm[ys, xs] = True
    lab_, nlab = label(binary_dilation(bm, iterations=max(2, W // 400)))
    sizes = np.bincount(lab_[bm])[1:] if nlab else np.array([])
    big = int((sizes >= 0.05 * k).sum()) if sizes.size else 0
    br = dict(bbox=[int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())],
              centroid=[round(float(xs.mean()), 1), round(float(ys.mean()), 1)],
              clusters=int(nlab), clusters_ge5pct=big,
              min_luma=round(float(luma[ys, xs].min()), 1))
    if cam is not None:
        az, el = pix_azel(cam, W, H)
        br['centroid_az_el'] = [round(float(az[ys, xs].mean()), 2), round(float(el[ys, xs].mean()), 2)]
    o['brightest'] = br
    # top quarter L*
    top = L[: H // 4][sel[: H // 4]]
    if top.size:
        o['top25_Lstar'] = dict(mean=round(float(top.mean()), 2), p50=round(float(np.percentile(top, 50)), 2),
                                p90=round(float(np.percentile(top, 90)), 2))
    if act is not None:
        o['palette'] = palette_dev(L, a, b, sel, act)
    return o


def palette_dev(L, a, b, sel, act):
    from . import paths
    sd = paths.import_scene_data()
    sc = [s for s in sd.SCENES if s['id'] == act or s['key'] == act]
    if not sc:
        return dict(error='no palette for act %r' % act)
    pal = sc[0]['pal']
    lab_px = np.stack([L[sel], a[sel], b[sel]], -1)
    if lab_px.shape[0] > 200000:                     # subsample for speed (deterministic stride)
        lab_px = lab_px[:: lab_px.shape[0] // 200000 + 1]
    sw = []
    dmin = np.full(lab_px.shape[0], np.inf)
    for hx, zh, en in pal:
        Ls, as_, bs = lab(hex_codes(hx)[None, :])
        d = de2000(lab_px, np.array([Ls[0], as_[0], bs[0]]))
        dmin = np.minimum(dmin, d)
        sw.append(dict(hex=hx, role=zh, nearest_dE2000_p01=round(float(np.percentile(d, 0.1)), 1),
                       within_dE5_pct=round(float((d < 5).mean() * 100), 2)))
    return dict(act=sc[0]['id'], metric='CIEDE2000 (as Review/Tools~/measure.py)', swatches=sw,
                pixel_to_nearest_dE_median=round(float(np.median(dmin)), 1),
                pixel_to_nearest_dE_p90=round(float(np.percentile(dmin, 90)), 1),
                pixels_within5_pct=round(float((dmin < 5).mean() * 100), 1))


def apl_target(t):
    """bible §2 APL (desktop) at timeline second t, from scene_data_v21.PHASES (linear or x^p shape)."""
    from . import paths
    sd = paths.import_scene_data()
    for ph in sd.PHASES:
        t0, t1, name, (a0, a1) = ph[0], ph[1], ph[2], ph[3]
        if t0 <= t < t1:
            p = ph[8] if len(ph) > 8 else 1.0
            x = (t - t0) / max(t1 - t0, 1e-6)
            return dict(phase=name, APL=round(a0 + (a1 - a0) * x ** p, 1), grade=ph[7], range=[a0, a1])
    return None
