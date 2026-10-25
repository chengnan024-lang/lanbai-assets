# -*- coding: utf-8 -*-
"""设计板的俯视图和剖面图（D-44 #2）：直接用 act06_vol 的覆盖率函数画，和参考帧是同一套几何。
-> Docs~/design_v3/plan.png、section.png"""
import os
import sys
import math
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import act06_vol as AV  # noqa: E402

OUT = os.path.join(AV.KIT, 'Docs~', 'design_v3')
FONT = os.path.join(AV.REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf')
if os.path.exists(FONT):
    font_manager.fontManager.addfont(FONT)
    plt.rcParams['font.family'] = font_manager.FontProperties(fname=FONT).get_name()
plt.rcParams['axes.unicode_minus'] = False


def cov(layer, X, Z, t):
    L = [l for l in AV.scene().layers if l.name == layer][0]
    return L.cov(X.ravel().astype(np.float32), Z.ravel().astype(np.float32), t).reshape(X.shape)


def plan():
    R = 14000.0
    n = 420
    xs = np.linspace(-R, R, n)
    X, Z = np.meshgrid(xs, xs[::-1])
    fig, axs = plt.subplots(1, 2, figsize=(16, 8.4))
    for ax, (t, title) in zip(axs, ((290.0, '290 s：上层 A（谷已散开）+ 三座塔'), (330.0, '330 s：下层 B（车下和朝日一侧已散开）'))):
        if t < 300:
            c = np.maximum(cov('A', X, Z, t), cov('T', X, Z, t))
            cmap = 'Greys'
        else:
            c = cov('B', X, Z, t)
            cmap = 'Blues'
        ax.imshow(c, extent=(-R, R, -R, R), cmap=cmap, vmin=0, vmax=1.1, origin='upper')
        s = AV.S_AX
        ax.annotate('', xy=(s[0] * 13000, s[1] * 13000), xytext=(0, 0), arrowprops=dict(arrowstyle='->', color='#E0A040', lw=2))
        ax.text(s[0] * 12500 + 300, s[1] * 12500, '太阳 方位 +30°', color='#C07010', fontsize=11)
        ax.plot([0], [0], 'o', color='#D02020', ms=7)
        ax.text(300, -700, '车的竖线（只下降，不平移）', color='#D02020', fontsize=10)
        ax.plot([0, 0], [0, 1600], color='#D02020', lw=1)
        ax.text(150, 1700, '正前（z）', color='#D02020', fontsize=9)
        if t < 300:
            # the sun ray ground tracks: where the ray from the eye meets the deck base / top
            tan = math.tan(math.radians(AV.SUN_EL))
            for tt, lab in ((305.4, '305.4'), (318.36, '318.36')):
                d, _ = AV.AL.descent(tt)
                r = (AV.GEO['A']['y0'] - (AV.A6.EYE[1] - d)) / tan
                ax.plot([s[0] * r], [s[1] * r], 'x', color='#C07010', ms=9, mew=2)
                ax.text(s[0] * r + 250, s[1] * r - 250, f'{lab} 日光穿过云底的点\n（{r / 1000:.2f} km）', color='#C07010', fontsize=9)
            for tw in AV.GEO['T']:
                a = math.radians(tw['az'])
                ax.text(tw['r'] * math.sin(a) + 900, tw['r'] * math.cos(a), f"塔 {tw['az']:+.0f}°", fontsize=10, color='#404040')
        ax.set_title(title, fontsize=14)
        ax.set_xlabel('x（m，右）')
        ax.set_ylabel('z（m，前）')
        ax.set_xlim(-R, R)
        ax.set_ylim(-R, R)
    fig.suptitle('第 6 幕云海（D-44 #2）俯视：覆盖率（深 = 云多）。只在这一圈里步进得细，外面是同一层、步子大的远景', fontsize=13)
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'plan.png'), dpi=110)


def section():
    """along the sun axis (a), the vertical through the bus; coverage at the bus's own across-offset"""
    a = np.linspace(-4000, 14000, 900)
    y = np.linspace(-2750, 1700, 450)
    Aa, Yy = np.meshgrid(a, y[::-1])
    X = Aa * AV.S_AX[0]
    Z = Aa * AV.S_AX[1]
    fig, ax = plt.subplots(figsize=(17, 7.6))
    img = np.ones(Aa.shape + (3,))
    for name, t, col in (('B', 330.0, (0.45, 0.6, 0.85)), ('A', 290.0, (0.55, 0.55, 0.6)), ('T', 290.0, (0.5, 0.5, 0.55))):
        L = [l for l in AV.scene().layers if l.name == name][0]
        c = L.cov(X.ravel().astype(np.float32), Z.ravel().astype(np.float32), t).reshape(X.shape)
        h = (Yy - L.y0) / (L.y1 - L.y0)
        inside = (h >= 0) & (h <= 1)
        prof = L.profile(np.clip(h, 0, 1), c) * inside
        k = np.clip(prof * c * 1.4, 0, 1)
        img = img * (1 - k[..., None]) + np.array(col)[None, None] * k[..., None]
    ax.imshow(img, extent=(a[0], a[-1], y[0], y[-1]), aspect='auto', origin='upper')
    ax.axhline(AV.SEA_Y, color='#1C3D63', lw=2)
    ax.text(a[0] + 200, AV.SEA_Y - 120, '海面（F2h 入水）', color='#1C3D63', fontsize=11)
    tan = math.tan(math.radians(AV.SUN_EL))
    for tt, lab, c in ((251.64, 'F0 251.6', '#202020'), (281.86, 'F1 281.9', '#202020'), (287.9, '进云 287.9', '#202020'),
                       (305.4, '出云底 305.4', '#202020'), (318.36, 'F1b1 318.4', '#202020'), (328.0, '穿下层 ~328', '#202020'),
                       (340.0, '340', '#202020'), (360.0, '360', '#202020')):
        d, _ = AV.AL.descent(tt)
        ey = AV.A6.EYE[1] - d
        ax.plot([0], [ey], 'o', color='#D02020', ms=5)
        ax.text(-3900, ey, f'{lab}  y {ey:.0f}', fontsize=9, va='center')
    for tt, c in ((300.6, '#C07010'), (305.4, '#C07010'), (318.36, '#E0A040')):
        d, _ = AV.AL.descent(tt)
        ey = AV.A6.EYE[1] - d
        ax.plot([0, 14000], [ey, ey + 14000 * tan], color=c, lw=1.2, ls='--')
        ax.text(9000, ey + 9000 * tan + 40, f'{tt} 的日光（仰角 5.8°）', color=c, fontsize=9)
    ds = [AV.AL.descent(t)[0] for t in np.linspace(251.64, 363.26, 200)]
    ax.plot([0] * 200, [AV.A6.EYE[1] - d for d in ds], color='#D02020', lw=2)
    ax.set_xlabel('沿太阳方向的距离 a（m）；车在 a = 0 竖直下降')
    ax.set_ylabel('高度 y（m，F0 眼高 = 0）')
    ax.set_title('剖面（沿太阳方位 +30°）：上层 A（灰）、塔、下层 B（蓝，330 s 已散开的样子）；虚线是日光', fontsize=13)
    ax.set_xlim(a[0], a[-1])
    ax.set_ylim(y[0], y[-1])
    fig.tight_layout()
    fig.savefig(os.path.join(OUT, 'section.png'), dpi=110)


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    plan()
    section()
    print('ok')
