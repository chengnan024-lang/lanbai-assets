# -*- coding: utf-8 -*-
"""用小楠给的实物照片做贴图（Docs~/实物参考_汉代器物/，CC0；总导演 10-24：“并不是参考。如果合适直接用。”）
  1. 朱漆 T_07b_Lacquer_*：克利夫兰美术馆 1969.129（乐浪出土漆盘残片，新莽 9 CE）内面一块——细裂、剥落、刷痕都是真的。
     去光：除以大半径模糊（照片的灯光和高光是低频），只留细节；镜像平铺消缝；均值校到圣经 #A3201E（§6·7b），
     剥落处（比周围暗的块）当磨损遮罩（露黑漆底 #282426）。
  2. 梁枋带 T_07b_LacquerBand_*：克利夫兰美术馆 1991.7（西汉漆耳杯）口沿那条纹样带：把云纹笔画和心形叶纹抠成“印章”，
     沿梁重新排成一条带（耳杯上是黄褐色的纹，圣经要黑带里画朱红云纹，所以只取形、上朱色）。
颜色都过圣经的值；D-21 紫护栏：朱与黑都不在 290–330°。"""
import math
import os

import numpy as np
from PIL import Image
from scipy import ndimage
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))
REF = os.path.join(HERE, '..', '..', 'Docs~', '实物参考_汉代器物')
OUT = os.path.join(HERE, '..', '..', 'Textures')
S = int(os.environ.get('TEX_SIZE', 2048))

import make_textures as MT  # noqa: E402


def load(name):
    return np.asarray(Image.open(os.path.join(REF, name)).convert('RGB'), float) / 255.0


def seamless(a):
    """错位交叉淡化做无缝平铺（不镜像，免得出现万花筒的对称）：原图与错开半幅的自己按到边的距离混合。"""
    h, w = a.shape[:2]
    b = np.roll(np.roll(a, h // 2, 0), w // 2, 1)
    y = np.minimum(np.arange(h), h - 1 - np.arange(h)) / (h / 2)
    x = np.minimum(np.arange(w), w - 1 - np.arange(w)) / (w / 2)
    wa = np.clip(np.minimum(y[:, None], x[None, :]) * 2.5, 0, 1)
    wa = wa * wa * (3 - 2 * wa)
    return a * wa[..., None] + b * (1 - wa[..., None])


def mirror_tile(a):
    """2×2 镜像拼成可平铺的方块（四边都无缝）。"""
    top = np.concatenate([a, a[:, ::-1]], 1)
    return np.concatenate([top, top[::-1]], 0)


def lacquer():
    img = load('CMA_1969.129.jpg')
    # 内面的一块：残片左上那片带细裂与剥落的平坦漆面（原图坐标）
    crop = img[900:1330, 900:1330]                          # 只取内面平坦的那块（细裂、剥落），不带口沿刻槽和中心纹饰
    lin = MT.s2l(crop)
    lum = lin @ np.array([0.2126, 0.7152, 0.0722])
    illum = gaussian_filter(lum, 40) + 1e-4
    detail = lin / illum[..., None]                         # 去掉低频的灯光与高光
    detail = np.clip(detail, 0.2, 2.2)
    # 剥落 / 磨损：比周围暗 25% 以上、且偏灰（饱和度低）的块
    sat = (lin.max(-1) - lin.min(-1)) / (lin.max(-1) + 1e-4)
    rel = lum / illum
    wear = np.clip((0.86 - rel) * 5.0, 0, 1) * np.clip((0.75 - sat) * 3.0, 0, 1)
    wear = gaussian_filter(wear, 1.0)
    T = seamless(detail)
    W = seamless(wear[..., None])[..., 0]
    T = np.asarray(Image.fromarray((np.clip(T / 2.4, 0, 1) * 255).astype(np.uint8)).resize((S, S), Image.LANCZOS), float) / 255 * 2.4
    W = np.asarray(Image.fromarray((W * 255).astype(np.uint8)).resize((S, S), Image.LANCZOS), float) / 255
    # 颜色：保留细节的明暗与轻微色偏，均值校到圣经的朱
    streak = gaussian_filter(MT.tnoise(S, 3, 11, 4), (0.5, 18), mode='wrap')
    streak /= streak.std()
    T = T * (1 + 0.04 * streak[..., None])                  # 程序的细刷痕叠在照片的细节上（照片放大 5 倍，最细的一层要补）
    dl = T @ np.array([0.2126, 0.7152, 0.0722])
    chroma = T / (dl[..., None] + 1e-4)
    chroma = 1 + 0.35 * (chroma - 1)                        # 照片的色偏只留三成
    base = MT.hexl('#A3201E')
    alb = base * chroma * dl[..., None] ** 0.8
    alb = alb * (1 - W[..., None]) + MT.hexl('#282426') * W[..., None]
    alb = MT.fit_mean(alb, '#A0201E')
    h = gaussian_filter(np.log(dl + 1e-3), 1.0) - 1.5 * W
    nrm = MT.normal_from_height(h, 1.2)
    sm = np.clip(0.80 - 0.4 * W - 0.05 * np.abs(np.log(dl + 1e-3)), 0, 1)
    ao = np.clip(1 - 0.2 * W, 0, 1)
    MT.save_rgb(alb, 'T_07b_Lacquer_Albedo.png')
    MT.save_normal(nrm, 'T_07b_Lacquer_Normal.png')
    MT.save_rgba(np.stack([W, ao, np.full_like(W, 0.5), sm], -1), 'T_07b_Lacquer_Mask.png')


def band():
    img = load('CMA_1991.7.jpg')
    crop = img[850:1200, 1350:2650]
    lum = crop @ np.array([0.2126, 0.7152, 0.0722])
    # 纹样带的区域：上下两道口沿线之间（粗略的弯带，按列找口沿的亮线）
    motif = (lum > 0.30) & (lum < 0.85)
    motif = ndimage.binary_opening(motif, iterations=1)
    lab, n = ndimage.label(motif)
    stamps = []
    for i, sl in enumerate(ndimage.find_objects(lab)):
        hh, ww = sl[0].stop - sl[0].start, sl[1].stop - sl[1].start
        area = (lab[sl] == i + 1).sum()
        # 纹样块：不太长（口沿线是很长的一条）、不太小
        if 18 <= hh <= 120 and 25 <= ww <= 260 and area > 250 and ww < 4 * hh + 60:
            m = (lab[sl] == i + 1).astype(float)
            stamps.append(gaussian_filter(m, 0.8))
    stamps.sort(key=lambda m: -m.sum())
    stamps = stamps[:10]
    Wd, Hd = S, S // 4
    canvas = np.zeros((Hd, Wd))
    rng = np.random.default_rng(5)
    x = 10
    k = 0
    while x < Wd - 10 and stamps:
        m = stamps[k % len(stamps)]
        if k % 2:
            m = m[:, ::-1]
        sc = (Hd * 0.62) / m.shape[0]
        mm = np.asarray(Image.fromarray((m * 255).astype(np.uint8)).resize((max(1, int(m.shape[1] * sc)), int(m.shape[0] * sc)), Image.LANCZOS), float) / 255
        y0 = int((Hd - mm.shape[0]) / 2 + rng.integers(-6, 7))
        if x + mm.shape[1] >= Wd - 4:
            break
        canvas[y0:y0 + mm.shape[0], x:x + mm.shape[1]] = np.maximum(canvas[y0:y0 + mm.shape[0], x:x + mm.shape[1]], mm)
        x += mm.shape[1] + int(Hd * 0.12)
        k += 1
    py = np.linspace(0, 1, Hd)[:, None]
    edge = (((py > 0.05) & (py < 0.075)) | ((py > 0.925) & (py < 0.95))).astype(float) * np.ones((1, Wd))
    red = np.clip(np.maximum(canvas, edge), 0, 1)
    jitter = MT.tnoise(Wd, 8, 21, 4)[:Hd, :] * 0.04
    alb = MT.hexl('#2A2527')[None, None] * (1 + jitter[..., None]) * (1 - red[..., None]) + MT.hexl('#9C2A1F') * red[..., None]
    alb = np.clip(alb, MT.hexl('#262224'), 0.8)
    sm = 0.78 - 0.04 * red
    MT.save_rgb(alb, 'T_07b_LacquerBand_Albedo.png')
    MT.save_rgba(np.stack([np.zeros_like(red), np.ones_like(red), red, sm * np.ones_like(red)], -1), 'T_07b_LacquerBand_Mask.png')
    print('stamps', len(stamps), 'placed', k)


if __name__ == '__main__':
    import sys
    sys.path.insert(0, os.path.join(HERE))
    for w in (sys.argv[1:] or ['lacquer', 'band']):
        globals()[w]()
        print('done', w)
