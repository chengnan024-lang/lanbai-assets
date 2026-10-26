# -*- coding: utf-8 -*-
"""宫殿的 5 套 2048² 贴图（程序生成，可平铺）+ 梁枋云气纹带 + 灯焰 8 帧 + 灯晕。
每套：_Albedo（sRGB）、_Normal（线性，OpenGL +Y，Unity 选 Normal map）、_Mask（线性：R 金属 / 磨损、G 遮蔽、B 细节 / 虹彩厚度、A 光滑度）。
反照率均值按圣经 §6·7b 的表（屏幕外的材质值，§1.6 反照率纪律）；均值在生成后校正到目标。"""
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Textures')
S = int(os.environ.get('TEX_SIZE', 2048))
rng = np.random.default_rng(7)


def s2l(c):
    c = np.asarray(c, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def hexl(h):
    h = h.lstrip('#')
    return s2l(np.array([int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]))


def tnoise(n, scale, seed, octaves=5, persist=0.55):
    """可平铺的分形噪声（FFT 滤波的白噪声，天然周期）。scale = 最大特征的周期数。"""
    r = np.random.default_rng(seed)
    out = np.zeros((n, n))
    amp = 1.0
    for o in range(octaves):
        f = scale * 2 ** o
        w = r.normal(size=(n, n))
        F = np.fft.fft2(w)
        ky = np.fft.fftfreq(n) * n
        kx = np.fft.fftfreq(n) * n
        K = np.sqrt(ky[:, None] ** 2 + kx[None, :] ** 2)
        filt = np.exp(-(K / f) ** 2)
        filt[0, 0] = 0
        layer = np.real(np.fft.ifft2(F * filt))
        layer /= layer.std() + 1e-9
        out += amp * layer
        amp *= persist
    return out / (out.std() + 1e-9)


def normal_from_height(h, strength):
    gy, gx = np.gradient(np.pad(h, 1, mode='wrap'))
    gx, gy = gx[1:-1, 1:-1], gy[1:-1, 1:-1]
    n = np.stack([-gx * strength, gy * strength, np.ones_like(h)], -1)   # OpenGL：+Y 向上（图像行向下，所以 gy 取正）
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n


def save_rgb(a, name, srgb=True):
    a = l2s(a) if srgb else np.clip(a, 0, 1)
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, name), optimize=True)


def save_rgba(a, name):
    Image.fromarray((np.clip(a, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, name), optimize=True)


def save_normal(n, name):
    save_rgb(n * 0.5 + 0.5, name, srgb=False)


def fit_mean(alb, target_hex):
    """把反照率的（线性）均值校到目标色。"""
    t = hexl(target_hex)
    m = alb.reshape(-1, 3).mean(0)
    return np.clip(alb * (t / np.maximum(m, 1e-6)), 0, 0.82)


# ------------------------------------------------------------------ 1. 漆（朱漆 #A3201E，刷痕，磨损处露黑漆底 #282426）
def lacquer():
    n = S
    y = np.linspace(0, 1, n, endpoint=False)
    streak = tnoise(n, 3, 11, 4)            # 沿 u 方向的刷痕：把噪声在 v 方向压扁
    streak = gaussian_filter(streak, (0.5, 18), mode='wrap')
    streak /= streak.std()
    low = tnoise(n, 2, 12, 3)
    wear = tnoise(n, 6, 13, 5)
    wear_mask = np.clip((wear - 1.6) * 2.0, 0, 1)           # 少量点状磨损（真正的边角磨损由 shader 按曲率 / 世界高度加）
    base = hexl('#A3201E') * (1 + 0.06 * streak[..., None] + 0.05 * low[..., None])
    alb = base * (1 - wear_mask[..., None]) + hexl('#282426') * wear_mask[..., None]
    alb = fit_mean(alb, '#A0201E')
    h = 0.6 * streak + 0.2 * low - 1.5 * wear_mask
    nrm = normal_from_height(gaussian_filter(h, 1.0, mode='wrap'), 0.35)
    ao = 1 - 0.15 * wear_mask
    sm = np.clip(0.80 + 0.03 * streak - 0.35 * wear_mask, 0, 1)
    save_rgb(alb, 'T_07b_Lacquer_Albedo.png')
    save_normal(nrm, 'T_07b_Lacquer_Normal.png')
    save_rgba(np.stack([wear_mask, ao, 0.5 + 0.5 * np.tanh(low), sm], -1), 'T_07b_Lacquer_Mask.png')


# ------------------------------------------------------------------ 1b. 梁枋的带子：黑漆底上朱绘云气纹（楚漆），u 沿梁（4 m）、v 横截面
def lacquer_band():
    W, H = S, S // 4
    u = np.linspace(0, 1, W, endpoint=False)[None, :]
    v = np.linspace(0, 1, H, endpoint=False)[:, None]
    img = np.zeros((H, W))
    # 卷云：每 1 m 一个 S 形卷，四个周期；用参数化的螺线笔触画
    yy, xx = np.mgrid[0:H, 0:W]
    px, py = xx / W * 4.0, yy / H            # px 0..4（米），py 0..1
    stroke = np.zeros((H, W))
    def spiral(cx, cy, r0, turns, sgn, w):
        th = np.linspace(0, turns * 2 * math.pi, 400)
        r = r0 * (1 - th / (turns * 2 * math.pi + 0.5))
        X = cx + sgn * r * np.cos(th) * 0.55
        Y = cy + r * np.sin(th)
        return X, Y, w * (0.4 + 0.6 * (1 - th / th[-1]))
    pts = []
    for k in range(4):
        cx = k + 0.5
        for sgn, cy, ox in ((1, 0.42, -0.22), (-1, 0.58, 0.22)):
            X, Y, Wd = spiral(cx + ox, cy, 0.20, 1.6, sgn, 0.030)
            pts.append((X, Y, Wd))
        # 连接两卷的长弧（气）
        t = np.linspace(0, 1, 200)
        X = cx - 0.45 + 0.9 * t
        Y = 0.5 + 0.16 * np.sin(2 * math.pi * t + k)
        pts.append((X, Y, 0.022 * np.ones_like(t)))
        # 小的勾
        X2, Y2, W2 = spiral(cx + 0.02, 0.22 if k % 2 else 0.78, 0.07, 1.2, 1 if k % 2 else -1, 0.016)
        pts.append((X2, Y2, W2))
    from scipy.spatial import cKDTree
    Pall = np.concatenate([np.stack([p[0] % 4.0, p[1]], -1) for p in pts])
    Wall = np.concatenate([p[2] for p in pts])
    # 周期：把点复制到 ±4 m
    P2 = np.concatenate([Pall, Pall + [4.0, 0], Pall - [4.0, 0]])
    W2a = np.concatenate([Wall, Wall, Wall])
    tree = cKDTree(P2 * [1.0, 1.0 / 4.0 * 4.0])
    q = np.stack([px.ravel(), py.ravel()], -1)
    d, i = tree.query(q, k=1)
    stroke = np.clip(1.0 - (d.reshape(H, W) - W2a[i].reshape(H, W)) / 0.006, 0, 1)
    # 上下两条朱色细边
    edge = ((py < 0.06) | (py > 0.94)).astype(float) * ((py < 0.045) | (py > 0.955) == False)
    red = np.clip(stroke + edge, 0, 1)
    jitter = tnoise(W, 8, 21, 4)[:H, :] * 0.04
    alb = hexl('#2A2527')[None, None] * (1 + jitter[..., None]) * (1 - red[..., None]) + hexl('#9C2A1F') * red[..., None]
    alb = np.clip(alb, hexl('#262224'), 0.8)
    sm = 0.78 - 0.04 * red
    save_rgb(alb, 'T_07b_LacquerBand_Albedo.png')
    save_rgba(np.stack([np.zeros_like(red), np.ones_like(red), red, sm * np.ones_like(red)], -1), 'T_07b_LacquerBand_Mask.png')


# ------------------------------------------------------------------ 2. 鱼鳞瓦（珍珠母）：交叠的圆头鳞，2 m 平铺 → 每行 6 片（约 0.33 m）
FS_STRENGTH = 60.0


def fishscale():
    n = S
    rows, cols = 8, 6
    yy, xx = np.mgrid[0:n, 0:n] / n
    h = np.full((n, n), -1.0)
    rid = np.zeros((n, n))
    for r in range(rows + 1):
        off = 0.5 * (r % 2)
        cy = (r + 0.5) / rows
        for c in range(-1, cols + 1):
            cx = (c + 0.5 + off) / cols
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    X = xx - (cx + dx)
                    Y = yy - (cy + dy)
                    rad = 0.62 / cols
                    # 圆头朝下（v 向下 = 檐口方向），上半被上一行盖住
                    d = np.sqrt((X / rad) ** 2 + (np.maximum(Y, 0) / (rad * 1.15)) ** 2 + (np.minimum(Y, 0) / (rad * 2.2)) ** 2)
                    hh = np.where(d < 1, (1 - d ** 2) ** 0.5 * 0.8 + (Y / rad) * 0.5 + r * 0.0, -1)
                    take = (hh > -0.99) & ((yy - (cy + dy)) > -rad * 2.2)
                    upd = take & (r + dy * rows >= 0) & (hh + 0.0 > h - 2 + 0 * hh) & (np.full_like(h, r + dy * rows) >= rid)
                    h = np.where(upd, hh, h)
                    rid = np.where(upd, r + dy * rows, rid)
    edge = np.clip(1 - (h + 0.2) * 3, 0, 1)
    fine = tnoise(n, 24, 31, 3)
    alb = hexl('#CFCBC4') * (1 + 0.03 * fine[..., None] - 0.10 * edge[..., None])
    alb = fit_mean(alb, '#C9C5BE')
    # 第 8 轮（评审 r5 #7）：原来的 4.0 是按像素算的坡度，鳞几乎是平的（中位倾角 0°）。按鳞半径 ≈ 0.21 m、拱高 ≈ 0.04 m 换算：
    # strength = 拱高 / 0.8 × (像素/米)，鳞的下缘倾到 50–70°，在各个角度都有一小片朝着灯
    nrm = normal_from_height(gaussian_filter(h * 1.0 + 0.02 * fine, 2.0, mode="wrap"), FS_STRENGTH * n / 2048)
    thick = np.clip(0.5 + 0.25 * tnoise(n, 3, 32, 3) + 0.2 * h, 0, 1)        # 虹彩的“膜厚”变化（B 通道）
    ao = 1 - 0.45 * edge
    sm = np.clip(0.86 - 0.12 * edge, 0, 1)
    save_rgb(alb, 'T_07b_FishScale_Albedo.png')
    save_normal(nrm, 'T_07b_FishScale_Normal.png')
    save_rgba(np.stack([np.zeros_like(h), ao, thick, sm], -1), 'T_07b_FishScale_Mask.png')


# ------------------------------------------------------------------ 3. 宝贝（紫贝）贴面：1 m 平铺 ≈ 9×9 枚 8–12 cm 的贝，隆起 + POM 高度
def cowrie():
    n = S
    k = 9
    yy, xx = np.mgrid[0:n, 0:n] / n
    h = np.zeros((n, n))
    spots = np.zeros((n, n))
    slit = np.zeros((n, n))
    r = np.random.default_rng(41)
    sp = tnoise(n, 60, 42, 2)
    for i in range(k):
        for j in range(k + 1):
            cx = (i + 0.5 + 0.5 * (j % 2) + 0.12 * (r.random() - 0.5)) / k
            cy = (j + 0.12 * (r.random() - 0.5)) / k
            a = 0.46 / k * (0.9 + 0.2 * r.random())
            b = a * 0.68
            ang = 0.25 * (r.random() - 0.5)
            for dx in (-1, 0, 1):
                for dy in (-1, 0, 1):
                    X = xx - cx - dx
                    Y = yy - cy - dy
                    Xr = X * math.cos(ang) - Y * math.sin(ang)
                    Yr = X * math.sin(ang) + Y * math.cos(ang)
                    d = (Xr / b) ** 2 + (Yr / a) ** 2
                    dome = np.sqrt(np.clip(1 - d, 0, 1))
                    h = np.maximum(h, dome)
                    slit = np.maximum(slit, (np.abs(Xr) < b * 0.07) * (np.abs(Yr) < a * 0.75) * (d < 1) * 1.0)
                    spots = np.maximum(spots, (d < 0.8) * (sp > 0.9) * 1.0)
    alb = hexl('#5B2A4E') * (1 + 0.12 * tnoise(n, 30, 43, 2)[..., None]) * (1 - spots[..., None]) + hexl('#B89AB0') * spots[..., None]
    alb = alb * (1 - 0.6 * slit[..., None])
    gap = (h < 0.02)
    alb = np.where(gap[..., None], hexl('#2B2A26'), alb)
    # 第 10c 轮（复核 r10b #2）：以前把整张（含暗缝）的均值校到 #5E3050，贝面被推到 (111, 37, 90)、C* 42，灯旁读成品红。
    # 现在只校贝面（不含缝和背斑）：#58325A（h 325、C* 30）——宫灯的暖光把色相往红推约 8°，灯旁才落在 #7A4A6E 一带（h 335、C* 29）
    shell = ~gap & (spots < 0.5)
    m = alb[shell].mean(0)
    alb = np.where(shell[..., None], np.clip(alb * (hexl('#58325A') / np.maximum(m, 1e-6)), 0, 0.82), alb)
    nrm = normal_from_height(gaussian_filter(h - 0.4 * slit, 1.0, mode='wrap'), 6.0)
    sm = np.where(gap, 0.25, 0.92 - 0.2 * slit)
    ao = np.clip(0.35 + 0.65 * h, 0, 1)
    save_rgb(alb, 'T_07b_Cowrie_Albedo.png')
    save_normal(nrm, 'T_07b_Cowrie_Normal.png')
    save_rgba(np.stack([gaussian_filter(h, 1, mode='wrap'), ao, spots, sm], -1), 'T_07b_Cowrie_Mask.png')   # R = POM 高度


# ------------------------------------------------------------------ 4. 石（#3B3F3A）：4 m 平铺，条石 1×0.5 m 错缝，凿痕
def stone():
    n = S
    yy, xx = np.mgrid[0:n, 0:n] / n
    rows = 8
    row = np.floor(yy * rows)
    off = (row % 2) * 0.5 / 4
    cols = 4
    u = (xx + off) * cols
    jx = np.abs(u - np.round(u)) * (n / cols)
    jy = np.abs(yy * rows - np.round(yy * rows)) * (n / rows)
    joint = np.clip(1 - np.minimum(jx, jy) / 6.0, 0, 1)
    blockid = (row * 13 + np.floor(u) * 7) % 17
    tone = 1 + 0.07 * (blockid / 17 - 0.5)
    chisel = tnoise(n, 40, 51, 3)
    big = tnoise(n, 3, 52, 4)
    alb = hexl('#3B3F3A') * (tone * (1 + 0.06 * chisel + 0.08 * big))[..., None] * (1 - 0.4 * joint[..., None])
    alb = fit_mean(alb, '#3B3F3A')
    hgt = -joint * 1.0 + 0.08 * chisel + 0.15 * big
    nrm = normal_from_height(gaussian_filter(hgt, 1.2, mode='wrap'), 2.5)
    ao = 1 - 0.5 * joint
    sm = np.clip(0.30 + 0.04 * chisel, 0, 1)
    save_rgb(alb, 'T_07b_Stone_Albedo.png')
    save_normal(nrm, 'T_07b_Stone_Normal.png')
    save_rgba(np.stack([np.zeros_like(ao), ao, 0.5 + 0.5 * np.tanh(big), sm], -1), 'T_07b_Stone_Mask.png')


# ------------------------------------------------------------------ 5. 青铜（金属 #BA926A；铜绿 #3E7A68 与暗化处按电介质，D-29）
def bronze():
    n = S
    big = tnoise(n, 4, 61, 5)
    fine = tnoise(n, 30, 62, 3)
    verd = np.clip((big - 1.35) * 1.8 + 0.25 * fine, 0, 1)
    dark = np.clip((tnoise(n, 6, 63, 4) - 1.2) * 1.4, 0, 1) * (1 - verd)
    metal = np.clip(1 - verd * 2 - dark * 2, 0, 1)
    metal = (metal > 0.5).astype(float)
    metal = gaussian_filter(metal, 0.8, mode='wrap')                      # 1–2 px 的过渡
    alb = hexl('#BA926A') * (1 + 0.05 * fine[..., None])
    alb = alb * metal[..., None] + (hexl('#3E7A68') * verd[..., None] + hexl('#3A332A') * dark[..., None]) / np.maximum(verd + dark, 1e-3)[..., None] * (1 - metal[..., None])
    nrm = normal_from_height(gaussian_filter(0.3 * fine - 0.8 * verd, 1.0, mode='wrap'), 1.5)
    sm = 0.55 * metal + (0.32 * verd + 0.5 * dark) / np.maximum(verd + dark, 1e-3) * (1 - metal)
    save_rgb(alb, 'T_07b_Bronze_Albedo.png')
    save_normal(nrm, 'T_07b_Bronze_Normal.png')
    save_rgba(np.stack([metal, 1 - 0.3 * verd, verd, sm], -1), 'T_07b_Bronze_Mask.png')


# ------------------------------------------------------------------ 岩（台地崖壁、顶面的淤泥地：#33362F），8 m 平铺，层理 + 裂隙
def rock():
    n = S
    big = tnoise(n, 3, 71, 6, 0.6)
    yy = np.linspace(0, 1, n, endpoint=False)[:, None]
    strata = np.sin((yy * 9 + 0.15 * big) * 2 * math.pi) * 0.5 + 0.5
    crack = np.abs(tnoise(n, 5, 72, 4))
    crack = np.clip(1 - crack / 0.12, 0, 1)
    fine = tnoise(n, 50, 73, 3)
    h = 0.6 * big + 0.35 * strata - 0.8 * crack + 0.08 * fine
    alb = hexl('#33362F') * (1 + 0.10 * big[..., None] + 0.05 * fine[..., None] - 0.25 * crack[..., None])
    alb = fit_mean(alb, '#33362F')
    nrm = normal_from_height(gaussian_filter(h, 1.5, mode='wrap'), 3.0)
    ao = 1 - 0.5 * crack
    sm = np.clip(0.22 + 0.05 * fine, 0, 1)
    save_rgb(alb, 'T_07b_Rock_Albedo.png')
    save_normal(nrm, 'T_07b_Rock_Normal.png')
    save_rgba(np.stack([np.zeros_like(ao), ao, 0.5 + 0.5 * np.tanh(big), sm], -1), 'T_07b_Rock_Mask.png')


# ------------------------------------------------------------------ 灯焰 8 帧（4×2 图集，每帧 256×512）+ 灯晕
def flame():
    fw, fh = 256, 512
    atlas = np.zeros((fh * 2, fw * 4))
    yy, xx = np.mgrid[0:fh, 0:fw]
    X = (xx - fw / 2) / (fw / 2)
    Y = 1 - yy / fh                       # 0 底 → 1 顶
    for k in range(8):
        ph = 2 * math.pi * k / 8
        sway = 0.06 * math.sin(ph) * Y ** 2 + 0.03 * math.sin(2 * ph + 1) * Y ** 3
        w = 0.78 * np.clip(np.sin(np.clip(Y, 0, 1) * math.pi * 0.95 + 0.15), 0, 1) * (1 - 0.6 * Y) ** 0.8 * (1 + 0.05 * math.sin(ph + 2))
        top = 0.86 + 0.06 * math.sin(ph * 1 + 0.5)
        d = np.abs(X - sway) / np.maximum(w, 1e-3)
        body = np.clip(1 - d, 0, 1) ** 0.7 * (Y < top) * np.clip((top - Y) / 0.25, 0, 1) * np.clip(Y / 0.08, 0, 1)
        core = np.clip(1 - d * 1.6, 0, 1) * np.clip((0.55 - Y) / 0.3, 0, 1) * np.clip(Y / 0.05, 0, 1)
        img = np.clip(0.65 * body + 0.6 * core, 0, 1)
        img = gaussian_filter(img, 2.0)
        r, c = divmod(k, 4)
        atlas[r * fh:(r + 1) * fh, c * fw:(c + 1) * fw] = img
    Image.fromarray((atlas * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, 'T_07b_Flame_Flip4x2.png'), optimize=True)
    # 灯晕：径向，R = 中心暖（灯焰的辉）、G = 靛中段，A = 总的轮廓（shader 里按 #FFC46A → #2A557B → 0 上色）
    m = 256
    yy, xx = np.mgrid[0:m, 0:m]
    rr = np.hypot(xx - m / 2 + 0.5, yy - m / 2 + 0.5) / (m / 2)
    warm = np.exp(-(rr / 0.12) ** 2)
    ind = np.clip(1 - rr, 0, 1) ** 2
    Image.fromarray((np.stack([warm, ind, np.zeros_like(rr), np.clip(warm + ind, 0, 1)], -1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'T_07b_Halo_256.png'))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    which = sys.argv[1:] or ['lacquer', 'lacquer_band', 'fishscale', 'cowrie', 'stone', 'bronze', 'rock', 'flame']
    for w in which:
        globals()[w]()
        print('done', w)
