# -*- coding: utf-8 -*-
"""美术审片 · 量图。一张截图（sRGB 8 位 PNG/JPG，已调色、含 bloom）对照 Review/targets.json 的一幕。

用法:
  python3 measure.py IMG --act 4 [--seg 4] [--crop x0,y0,x1,y1] [--mask-glass] [--json out.json] [--viz out.png]
  --act   targets.json 的幕号（1 2 3 4 4c 5 6 7a 7b 7c 8 8b 9 10 11 12）
  --seg   §2.2 的段（targets.json segments.key），给 APL 目标；不给就用该幕第一段
  --crop  只量画面的一块（例如只量透过挡风玻璃的那块）
  --viz   出一张诊断图：紫 / 纯黑纯白 / 最亮 2000 px / 暗部发暖 四种遮罩叠在灰度上

量的东西与定义（都写在 Review/标准.md 第 2 节）：
  APL = Rec.709 luma 在 sRGB 码值上的平均（0–255，和门的 gate_metrics.py、本地 metrics 同一定义）
  紫 = CIE Lab(D65) h_ab 290–325 且 C* > 15；第 6 幕再量 h 285–330 且 C* > 12；第 4 幕量 C* > 30 的紫
  “大于 2% 的区域” 同时报全画面占比和最大 8 连通块占比（降采样到 480 宽再连通，块 ≥ 2% 算违规）
  纯黑 = 三通道都 ≤ #030409 的对应通道（luma ≤ 3.5）；纯白 = luma ≥ 246（#F4F7FA）
  最亮点 = 最亮 2000 px 的连通块数、最大块占比、外框；以及 L* > 85 的像素
  色板 = 每个色板色在画面里最近的像素 ΔE2000（p0.1 分位，抗噪）+ ΔE < 5 的像素占比
  暗部发暖 = L* < 25 且 C* > 6 且 h 20–100 的像素占比（§1.3.2）
"""
import argparse, json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage

HERE = os.path.dirname(os.path.abspath(__file__))
TARGETS = os.path.join(os.path.dirname(HERE), 'targets.json')
LUMA = np.array([0.2126, 0.7152, 0.0722])


def srgb_lin(a):
    return np.where(a <= 0.04045, a / 12.92, ((a + 0.055) / 1.055) ** 2.4)


def lab(rgb01):
    lin = srgb_lin(rgb01)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    X = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(X > 216 / 24389, np.cbrt(X), (24389 / 27 * X + 16) / 116)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return np.stack([L, a, b], -1)


def lch(labv):
    L, a, b = labv[..., 0], labv[..., 1], labv[..., 2]
    return L, np.hypot(a, b), (np.degrees(np.arctan2(b, a)) + 360) % 360


def hex_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], float) / 255


def de2000(l1, l2):
    """CIEDE2000, l1 (...,3) vs l2 (3,)"""
    L1, a1, b1 = l1[..., 0], l1[..., 1], l1[..., 2]
    L2, a2, b2 = l2
    C1, C2 = np.hypot(a1, b1), np.hypot(a2, b2)
    Cb = (C1 + C2) / 2
    G = 0.5 * (1 - np.sqrt(Cb ** 7 / (Cb ** 7 + 25 ** 7)))
    a1p, a2p = (1 + G) * a1, (1 + G) * a2
    C1p, C2p = np.hypot(a1p, b1), np.hypot(a2p, b2)
    h1p = np.degrees(np.arctan2(b1, a1p)) % 360
    h2p = np.degrees(np.arctan2(b2, a2p)) % 360
    dLp = L2 - L1
    dCp = C2p - C1p
    dh = h2p - h1p
    dh = np.where(dh > 180, dh - 360, np.where(dh < -180, dh + 360, dh))
    dh = np.where(C1p * C2p == 0, 0, dh)
    dHp = 2 * np.sqrt(C1p * C2p) * np.sin(np.radians(dh / 2))
    Lbp = (L1 + L2) / 2
    Cbp = (C1p + C2p) / 2
    hs = h1p + h2p
    hbp = np.where(C1p * C2p == 0, hs, np.where(np.abs(h1p - h2p) > 180, np.where(hs < 360, (hs + 360) / 2, (hs - 360) / 2), hs / 2))
    T = 1 - 0.17 * np.cos(np.radians(hbp - 30)) + 0.24 * np.cos(np.radians(2 * hbp)) + 0.32 * np.cos(np.radians(3 * hbp + 6)) - 0.20 * np.cos(np.radians(4 * hbp - 63))
    dth = 30 * np.exp(-((hbp - 275) / 25) ** 2)
    Rc = 2 * np.sqrt(Cbp ** 7 / (Cbp ** 7 + 25 ** 7))
    Sl = 1 + 0.015 * (Lbp - 50) ** 2 / np.sqrt(20 + (Lbp - 50) ** 2)
    Sc = 1 + 0.045 * Cbp
    Sh = 1 + 0.015 * Cbp * T
    Rt = -np.sin(np.radians(2 * dth)) * Rc
    return np.sqrt((dLp / Sl) ** 2 + (dCp / Sc) ** 2 + (dHp / Sh) ** 2 + Rt * (dCp / Sc) * (dHp / Sh))


def largest_component_pct(mask, work_w=480):
    if not mask.any():
        return 0.0
    h, w = mask.shape
    s = max(1, w // work_w)
    m = mask[:h - h % s, :w - w % s].reshape(h // s, s, w // s, s).mean((1, 3)) > 0.5
    if not m.any():
        return 0.0
    lab_, n = ndimage.label(m, structure=np.ones((3, 3)))
    sizes = ndimage.sum(m, lab_, range(1, n + 1))
    return float(sizes.max() / m.size * 100)


def measure(path, act, seg=None, crop=None, viz=None):
    T = json.load(open(TARGETS, encoding='utf-8'))
    A = T['acts'][act]
    im = Image.open(path).convert('RGB')
    if crop:
        im = im.crop(crop)
    a8 = np.asarray(im).astype(np.float64)
    a = a8 / 255
    H, W = a.shape[:2]
    luma = a8 @ LUMA
    LAB = lab(a)
    L, C, h = lch(LAB)
    r = {'file': os.path.relpath(path), 'size': [W, H], 'act': act}
    # --- APL & distribution
    r['APL'] = round(float(luma.mean()), 1)
    r['luma_lt12_pct'] = round(float((luma < 12).mean() * 100), 1)
    r['luma_p50_p95_p99'] = [round(float(np.percentile(luma, q)), 1) for q in (50, 95, 99)]
    top = L[: H // 4]
    r['top25_Lstar_p90'] = round(float(np.percentile(top, 90)), 1)
    r['Lstar_max'] = round(float(L.max()), 1)
    r['pct_Lstar_gt85'] = round(float((L > 85).mean() * 100), 2)
    segs = [s for s in T['segments'] if s['act'] == act]
    S = next((s for s in T['segments'] if s['key'] == seg), segs[0] if segs else None)
    if S:
        lo, hi = min(S['APL']) * 0.85, max(S['APL']) * 1.15
        r['APL_target'] = {'seg': S['key'], 'name': S['name'], 'APL': S['APL'], 'range_pm15': [round(lo, 1), round(hi, 1)],
                           'pass': bool(lo <= r['APL'] <= hi)}
    # --- violet
    v15 = (h >= 290) & (h <= 325) & (C > 15)
    v30 = (h >= 290) & (h <= 325) & (C > 30)
    lav = (h >= 285) & (h <= 330) & (C > 12)
    r['violet_h290_325_C15'] = {'pct': round(float(v15.mean() * 100), 2), 'largest_region_pct': round(largest_component_pct(v15), 2)}
    r['violet_C30_pct'] = round(float(v30.mean() * 100), 2)
    r['lavender_h285_330_C12'] = {'pct': round(float(lav.mean() * 100), 2), 'largest_region_pct': round(largest_component_pct(lav), 2)}
    rule = A.get('violet', 'global')
    if rule in ('global', 'global_except_cowrie'):
        r['violet_pass'] = r['violet_h290_325_C15']['largest_region_pct'] <= 2.0
    elif rule == 'act6':
        r['violet_pass'] = r['violet_h290_325_C15']['largest_region_pct'] <= 2.0 and r['lavender_h285_330_C12']['largest_region_pct'] <= 2.0
    else:
        r['violet_pass'] = r['violet_C30_pct'] <= 10.0
    # --- black / white
    blk = np.all(a8 <= np.array([3, 4, 9]), -1)
    wht = luma >= 246
    r['pure_black'] = {'pct': round(float(blk.mean() * 100), 2), 'largest_region_pct': round(largest_component_pct(blk), 2)}
    r['pure_white'] = {'pct': round(float(wht.mean() * 100), 2), 'largest_region_pct': round(largest_component_pct(wht), 2)}
    r['black_white_pass'] = r['pure_black']['largest_region_pct'] <= 2 and r['pure_white']['largest_region_pct'] <= 2
    r['red_zero_pct'] = round(float(((a8[..., 0] == 0) & (luma < 20)).mean() * 100), 2)
    r['min_code'] = [int(x) for x in a8.reshape(-1, 3).min(0)]
    # --- brightest point
    flat = luma.ravel()
    k = min(2000, flat.size - 1)
    thr = np.partition(flat, -k)[-k]
    bm = luma >= thr
    lb, n = ndimage.label(ndimage.binary_dilation(bm, iterations=6))
    sizes = ndimage.sum(bm, lb, range(1, n + 1)) if n else np.array([0])
    ys, xs = np.nonzero(bm)
    big = sizes[sizes >= 0.05 * sizes.sum()] if n else []
    r['brightest_2000'] = {'clusters_ge5pct': int(len(big)), 'largest_share_pct': round(float(sizes.max() / max(sizes.sum(), 1) * 100), 1),
                           'bbox': [int(xs.min()), int(ys.min()), int(xs.max()), int(ys.max())], 'centroid_xy01': [round(float(xs.mean() / W), 3), round(float(ys.mean() / H), 3)],
                           'threshold_luma': round(float(thr), 1)}
    r['one_brightest_pass'] = len(big) <= 1
    # --- warm shadows
    warmsh = (L < 25) & (C > 6) & (h >= 20) & (h <= 100)
    r['warm_shadow_pct'] = round(float(warmsh.mean() * 100), 2)
    # --- palette
    step = max(1, int(np.sqrt(W * H / 250000)))
    sub = LAB[::step, ::step].reshape(-1, 3)
    pal = []
    for sw in A.get('palette', []):
        tl = lab(hex_rgb(sw['hex']))
        d = de2000(sub, tl)
        pal.append({'name': sw['name'], 'hex': sw['hex'], 'nearest_dE_p0.1': round(float(np.percentile(d, 0.1)), 1),
                    'pct_within_dE5': round(float((d < 5).mean() * 100), 2)})
    r['palette'] = pal
    # --- mean colour of frame (for the overview strip)
    lin = srgb_lin(a).reshape(-1, 3).mean(0)
    mc = np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)
    r['mean_colour_hex'] = '#%02X%02X%02X' % tuple(int(round(x * 255)) for x in np.clip(mc, 0, 1))
    if viz:
        g = (luma[..., None] / 255 * 0.55).repeat(3, -1)
        g[v15] = [0.75, 0.2, 0.9]
        g[blk] = [0, 0.6, 1.0]
        g[wht] = [1, 1, 0]
        g[warmsh] = [1, 0.45, 0]
        g[bm] = [1, 0, 0]
        Image.fromarray((np.clip(g, 0, 1) * 255).astype(np.uint8)).save(viz)
    return r


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('img', nargs='+')
    ap.add_argument('--act', required=True)
    ap.add_argument('--seg')
    ap.add_argument('--crop')
    ap.add_argument('--json')
    ap.add_argument('--viz')
    o = ap.parse_args()
    crop = tuple(int(x) for x in o.crop.split(',')) if o.crop else None
    res = [measure(p, o.act, o.seg, crop, o.viz if len(o.img) == 1 else None) for p in o.img]
    s = json.dumps(res if len(res) > 1 else res[0], ensure_ascii=False, indent=1)
    if o.json:
        open(o.json, 'w', encoding='utf-8').write(s)
    print(s)
