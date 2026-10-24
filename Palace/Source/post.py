# -*- coding: utf-8 -*-
"""参考渲染的后期 = Unity 里那几步的 numpy 版：
  1. 表面（Cycles 渲的烘焙光照近似，按灯组分开，可在这里改强度不重渲）
  2. LanbaiApplyFog：Exp 雾，密度 0.018，雾色 = 方向的水色（上 / 平 / 下），按眼到表面的直线距离
  3. 无雾的发光体（_FogMode 2，exp(−d·0.004)）：门里的光、灯焰序列帧、灯晕卡（公告板，朝两眼中点，深度测试）
  4. PPv2：S7b 引擎参数 + bloom（grade.py）
  5. 量数：APL、最亮点、紫的占比、色板偏差
"""
import json
import math
import os
import sys

import numpy as np
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import palace_layout as L  # noqa: E402
from grade import grade, srgb_to_lin  # noqa: E402
from shots import SHOTS  # noqa: E402

B2U = np.array([[-1.0, 0, 0], [0, 0, 1.0], [0, -1.0, 0]])

# ---- 参数（全部写进 PalaceLayout.json 的 render 块）
FOG_DENSITY = 0.018
FOG_UP = srgb_to_lin('#182930')       # 屏幕 #06202C（填值由 grade.solve_fill 求）
FOG_MID = srgb_to_lin('#0D1920')      # 屏幕 #04121E（第 4 轮：评审量到背景中位 #040F1B，抬 2–3 码）
FOG_DOWN = srgb_to_lin('#020302')     # 屏幕 #02070F（深渊）
FLAME_ATTEN = 0.004
FLAME_GOLD = np.array([1.396, 0.536, 0.142])          # 金 #E0A860 在 S7b 下的线性值（海 README §2.6 的做法：不靠色调映射的肩部）
FLAME_FILL = FLAME_GOLD * 2.2                         # 灯焰身：金
FLAME_CORE = np.array([1.0, 0.82, 0.55]) * 2.6        # 灯焰芯：白热（m⁴ 加权），屏幕上核心到 255、外缘是金 #FFC46A 一带
HALO_MID = srgb_to_lin('#446282')                    # 灯晕卡中段，屏幕 #2A557B
HALO_R = 1.5
GROUP_GAIN = {'amb': 1.0, 'warm': 1.0, 'indigo': 1.0, 'door': 1.0}


def read_exr(path):
    import OpenEXR
    f = OpenEXR.File(path)
    out = {}
    for p in f.parts:
        for k, ch in p.channels.items():
            a = np.asarray(ch.pixels, np.float32)
            out[k.replace('ViewLayer.', '')] = a
    return out


def cam_basis(yaw, pitch):
    y, p = math.radians(yaw), math.radians(pitch)
    f = np.array([math.sin(y) * math.cos(p), math.sin(p), math.cos(y) * math.cos(p)])
    r = np.array([math.cos(y), 0.0, -math.sin(y)])
    u = np.cross(f, r)
    return f, r, u


def rays(shot, W, H):
    t, yaw, pitch, hfov, _ = SHOTS[shot]
    f, r, u = cam_basis(yaw, pitch)
    tx = math.tan(math.radians(hfov) / 2)
    xs = ((np.arange(W) + 0.5) / W * 2 - 1) * tx
    ys = (1 - (np.arange(H) + 0.5) / H * 2) * tx * H / W
    X, Y = np.meshgrid(xs, ys)
    d = f[None, None] + X[..., None] * r[None, None] + Y[..., None] * u[None, None]
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def project(shot, P, W, H):
    """Unity 宫殿坐标的点 → 像素 (x, y) 与沿视线的深度、距离。"""
    t, yaw, pitch, hfov, _ = SHOTS[shot]
    e = L.eye(t)
    f, r, u = cam_basis(yaw, pitch)
    v = np.asarray(P, float) - e
    zc = v @ f
    tx = math.tan(math.radians(hfov) / 2)
    px = (v @ r) / np.maximum(zc, 1e-6) / tx
    py = (v @ u) / np.maximum(zc, 1e-6) / (tx * H / W)
    return (px + 1) / 2 * W, (1 - py) / 2 * H, zc, np.linalg.norm(v, axis=-1)


def fog_color(d):
    y = d[..., 1:2]
    up = FOG_MID + (FOG_UP - FOG_MID) * smooth(np.clip(y, 0, 1))
    dn = FOG_MID + (FOG_DOWN - FOG_MID) * smooth(np.clip(-y, 0, 1))
    return np.where(y >= 0, up, dn)


def smooth(x):
    return x * x * (3 - 2 * x)


def lamp_points():
    return L.flame_points()


VEIL = L.FRAME['palace_veil']


def veil_density(t):
    c = VEIL['curve']
    ts = [p['t'] for p in c]
    return float(np.interp(t, ts, [p['x'] for p in c]))


def veil(Pu, e, t):
    """_Udon_PalaceVeil（海的约定）：眼 → 片元的线段落在雾带 [top − th, top] 里的长度 → 1 − exp(−x·L)。"""
    x = veil_density(t)
    if x <= 0:
        return np.zeros(Pu.shape[:2])
    top = VEIL['top_offset_palace_y']
    lo = top - VEIL['thickness_m']
    y0, y1 = e[1], Pu[..., 1]
    a, b = np.minimum(y0, y1), np.maximum(y0, y1)
    ov = np.clip(np.minimum(b, top) - np.maximum(a, lo), 0, None)
    seg = np.linalg.norm(Pu - e, axis=-1)
    Lb = seg * ov / np.maximum(b - a, 1e-3)
    return 1 - np.exp(-x * Lb)


def composite(exr, shot, gains=None, halo=True, flame_scale=1.0):
    g = dict(GROUP_GAIN, **(gains or {}))
    C = exr['Combined'][..., :3].astype(np.float64)
    H, W = C.shape[:2]
    groups = {k: exr['Combined_' + k][..., :3].astype(np.float64) for k in ('amb', 'warm', 'indigo', 'door', 'doorglow')
              if 'Combined_' + k in exr}
    S = sum(groups.values()) + 1e-9
    sb = gaussian_filter(S, (1.2, 1.2, 0)) + 1e-9
    surf = np.zeros_like(C)
    for k, G in groups.items():
        if k == 'doorglow':
            continue
        surf += C * (gaussian_filter(G, (1.2, 1.2, 0)) / sb) * g.get(k, 1.0)
    glow = C * (gaussian_filter(groups['doorglow'], (1.2, 1.2, 0)) / sb) if 'doorglow' in groups else 0.0
    t = SHOTS[shot][0]
    e = L.eye(t)
    D = rays(shot, W, H)
    Pb = np.stack([exr['Position.X'], exr['Position.Y'], exr['Position.Z']], -1).astype(np.float64)
    Pu = Pb @ B2U.T
    hit = exr['Depth.Z'] < 1e6
    dist = np.where(hit, np.linalg.norm(Pu - e, axis=-1), 1e9)
    F = 1 - np.exp(-FOG_DENSITY * np.minimum(dist, 1e5))
    fc = fog_color(D)
    img = np.where(hit[..., None], surf * (1 - F[..., None]) + fc * F[..., None], fc)
    # 门里的光（Lanbai/PalaceGlow，不透明、_FogMode 2）：那些像素就是 glow × exp(−d·0.004)，不混雾色
    if 'Combined_doorglow' in exr:
        gm = (groups['doorglow'].sum(-1) > 0.5 * S.sum(-1)) & hit
        g2 = C * np.exp(-FLAME_ATTEN * np.minimum(dist, 1e5))[..., None]
        img = np.where(gm[..., None], g2, img + glow * np.exp(-FLAME_ATTEN * np.minimum(dist, 1e5))[..., None] * (~gm)[..., None])
    vv = np.where(hit, veil(Pu, e, t), 0.0)
    if 'Object Index.X' in exr:                         # 台地（pass_index 3）：下缘的溶解（LanbaiPalaceLipVeil）
        rock = np.round(exr['Object Index.X']) == 3
        bottom = VEIL['top_offset_palace_y'] - VEIL['thickness_m']
        if veil_density(t) > 0:
            lip = np.clip((bottom - e[1]) / 3.0, 0, 1) * np.clip(1 - (Pu[..., 1] - bottom) / 5.0, 0, 1)
            vv = np.where(rock & hit, np.maximum(vv, lip), vv)
    vv = vv[..., None]
    img = img * (1 - vv) + fc * vv
    if halo:
        dz = dist.copy()
        if 'Normal.X' in exr:          # 背面（Unity 里被剔掉，不进深度缓冲）：灯晕的深度测试当它不存在
            Nb = np.stack([exr['Normal.X'], exr['Normal.Y'], exr['Normal.Z']], -1)
            Nu = Nb @ B2U.T
            back = (np.sum(Nu * (Pu - e), -1) > 0) & hit
            dz = np.where(back, 1e9, dz)
        img = draw_lamps(img, shot, dz, flame_scale)
    return img, dict(dist=dist, hit=hit, D=D)


def draw_lamps(img, shot, dist, flame_scale=1.0):
    H, W = img.shape[:2]
    P = lamp_points()
    px, py, zc, dd = project(shot, P, W, H)
    tx = math.tan(math.radians(SHOTS[shot][3]) / 2)
    ppm = W / 2 / tx                                     # 每米每单位深度的像素
    yy, xx = np.mgrid[0:H, 0:W]
    for i in range(len(P)):
        if zc[i] < 0.3:
            continue
        rpx = HALO_R * ppm / zc[i]
        if px[i] < -rpx or px[i] > W + rpx or py[i] < -rpx or py[i] > H + rpx:
            continue
        att = math.exp(-FLAME_ATTEN * dd[i])
        x0, x1 = int(max(px[i] - rpx - 2, 0)), int(min(px[i] + rpx + 2, W))
        y0, y1 = int(max(py[i] - rpx - 2, 0)), int(min(py[i] + rpx + 2, H))
        if x1 <= x0 or y1 <= y0:
            continue
        sx, sy = xx[y0:y1, x0:x1] - px[i], yy[y0:y1, x0:x1] - py[i]
        r = np.sqrt(sx ** 2 + sy ** 2) / max(rpx, 1e-6)                     # 0..1 在晕卡半径内
        vis = (dist[y0:y1, x0:x1] > dd[i] - 0.6).astype(float)              # 深度测试（卡在灯焰处）
        soft = np.clip((dist[y0:y1, x0:x1] - dd[i]) / 1.0 + 0.6, 0, 1)        # 软粒子：靠近别的面时淡出（不切成半月）
        # 晕卡（第 4 轮）：暖芯很小、靛环从 0.15 r 才起，两者不重叠，免得加色混出丁香紫
        warm = np.exp(-(r / 0.08) ** 2)[..., None] * FLAME_FILL * 0.05
        ring = (np.clip((r - 0.12) / 0.28, 0, 1) ** 2 * (3 - 2 * np.clip((r - 0.12) / 0.28, 0, 1)) * np.clip(1 - r, 0, 1) ** 2)
        ind = ring[..., None] * HALO_MID * 1.4
        add = (warm + ind) * att * (vis * soft)[..., None]
        # 灯焰：竖着的软椭圆，0.16 × 0.34 m
        # 灯焰 = shader 的式子：半尺寸 (0.09, 0.19) m，小于 _MinPixels（1.2 px）时放大 s 倍、亮度 / s（Lanbai/PalaceFlame）
        fw, fh = 0.09 * ppm / zc[i] * flame_scale, 0.19 * ppm / zc[i] * flame_scale
        sc = max(1.0, 1.2 / max(fw, 1e-6))
        fw, fh = fw * sc, fh * sc
        # 从下面看（视线很陡）时 shader 把火转成球状公告板：屏幕上不再是竖的细条（这里用屏幕上的圆近似）
        vdir = (P[i] - L.eye(SHOTS[shot][0]))
        steep = min(1.0, max(0.0, (abs(vdir[1]) / (np.linalg.norm(vdir) + 1e-9) - 0.5) * 3.0))
        fh = fh * (1 - steep) + fw * steep
        fl = np.exp(-((sx / fw) ** 2 + ((sy + fh * 0.3) / fh) ** 2) * 2.0) * 0.6
        add += (fl[..., None] * FLAME_FILL + (fl ** 4)[..., None] * FLAME_CORE * 4.0) * att / sc * vis[..., None]
        img[y0:y1, x0:x1] += add
    return img


# ---------------------------------------------------------------- 量数
def lab(codes):
    c = np.clip(codes / 255.0, 0, 1)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    X = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(X > 0.008856, np.cbrt(X), 7.787 * X + 16 / 116)
    Lb = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return Lb, a, b


def metrics(codes):
    luma = codes @ np.array([0.2126, 0.7152, 0.0722])
    Lb, a, b = lab(codes)
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360
    purple = ((h >= 290) & (h <= 325) & (C > 15)).mean()
    d21 = ((h >= 290) & (h <= 330) & (C > 8) & (Lb > 40)).mean()        # D-21 修订的紫色护栏
    H, W = luma.shape
    sm = gaussian_filter(luma, 3)
    iy, ix = np.unravel_index(np.argmax(sm), sm.shape)
    return {'APL': round(float(luma.mean()), 2), 'max_luma': round(float(luma.max()), 1),
            'brightest_xy_frac': [round(ix / W, 3), round(iy / H, 3)],
            'purple_frac': round(float(purple), 4), 'purple_D21_frac': round(float(d21), 5), 'frac_luma_gt_200': round(float((luma > 200).mean()), 4)}


def save_png(codes, path, scale=1):
    from PIL import Image
    im = Image.fromarray(np.clip(np.round(codes), 0, 255).astype(np.uint8))
    if scale != 1:
        im = im.resize((int(im.width * scale), int(im.height * scale)), Image.LANCZOS)
    im.save(path)


def process(exr_path, shot, out_png, gains=None):
    exr = read_exr(exr_path)
    img, aux = composite(exr, shot, gains)
    codes = grade(img)
    save_png(codes, out_png)
    m = metrics(codes)
    np.save(out_png.replace('.png', '_lin.npy'), img.astype(np.float32))
    return m


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('dir')
    ap.add_argument('--shots', default='')
    ap.add_argument('--gains', default='{}')
    a = ap.parse_args()
    shots = a.shots.split(',') if a.shots else [f[:-4] for f in sorted(os.listdir(a.dir)) if f.endswith('.exr')]
    res = {}
    for s in shots:
        m = process(os.path.join(a.dir, s + '.exr'), s, os.path.join(a.dir, s + '.png'), json.loads(a.gains))
        res[s] = m
        print(s, m)
    json.dump(res, open(os.path.join(a.dir, 'metrics.json'), 'w'), indent=1)
