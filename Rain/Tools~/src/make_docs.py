"""Docs~ sheets for the Rain kit (v2): what every texture is and what the v2 maths do, drawn so a human can read it.
usage: python3 make_docs.py <kit_dir> [sheet ...]   (reads textures via rainpaths.find, writes <kit>/Docs~)"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rainpaths as RP
KIT = sys.argv[1]
DOCS = os.path.join(KIT, 'Docs~'); os.makedirs(DOCS, exist_ok=True)
LAN = RP.lanbai_root()
FONTS = os.path.join(LAN, 'deliver2', 'Sign', 'Fonts')
F = lambda s: ImageFont.truetype(os.path.join(FONTS, 'SourceHanSerifCN-Regular.otf'), s)
FB = lambda s: ImageFont.truetype(os.path.join(FONTS, 'SourceHanSerifCN-Medium.otf'), s)
BG = (14, 17, 24); FG = (222, 230, 234); DIM = (140, 150, 160); ACC = (120, 170, 220)


def load(name):
    return np.asarray(Image.open(RP.find(name)), np.float32) / 255.0


def u8(a):
    return (np.clip(a, 0, 1) * 255).astype(np.uint8)


def shade_normal(rgb, L=(-0.45, 0.55, 0.70)):
    n = rgb[..., :3] * 2 - 1
    n[..., 2] = np.sqrt(np.clip(1 - n[..., 0] ** 2 - n[..., 1] ** 2, 0, 1))
    return np.clip((n * np.array(L)).sum(-1), 0, 1)


def mirror_puddle(rgb):
    """a normal map seen as a puddle in perspective reflecting the night: a tube and a lit window as bars."""
    n = rgb[..., :3] * 2 - 1
    nz = np.sqrt(np.clip(1 - n[..., 0] ** 2 - n[..., 1] ** 2, 1e-4, 1))
    Hh = rgb.shape[0]
    V = np.array([0.0, -np.cos(np.radians(25)), -np.sin(np.radians(25))])
    N = np.stack([n[..., 0], n[..., 1], nz], -1)
    R = V - 2 * (N @ V)[..., None] * N
    delta = np.degrees(np.arcsin(np.clip(R[..., 2], -1, 1))) - 25.0
    rows = np.arange(Hh)[:, None] / Hh
    e = 8.0 + 34.0 * (1 - rows) + delta
    sky = 0.035 + 0.06 * np.clip(e / 45, 0, 1)
    tube = np.exp(-((e - 22.0) / 0.9) ** 2) * 1.8
    win = np.exp(-((e - 31.0) / 0.5) ** 2) * 0.9
    col = np.stack([sky * 0.7 + tube * 0.90 + win * 0.80, sky * 0.8 + tube * 0.95 + win * 0.86, sky * 1.0 + tube * 0.97 + win * 0.88], -1)
    return np.clip(col, 0, 1) ** (1 / 2.2)


def slope_to_rgb(sx, sy):
    n = np.stack([-sx, -sy, np.ones_like(sx)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return n * 0.5 + 0.5


def canvas(w, h):
    im = Image.new('RGB', (w, h), BG); return im, ImageDraw.Draw(im)


def title(d, x, y, zh, en):
    d.text((x, y), zh, font=FB(34), fill=FG); d.text((x, y + 44), en, font=F(20), fill=DIM)


def cap(d, x, y, s, size=18, fill=DIM):
    for k, line in enumerate(s.split('\n')):
        d.text((x, y + k * (size + 6)), line, font=F(size), fill=fill)


def paste(im, arr, x, y, w=None, h=None, nearest=False):
    a = Image.fromarray(u8(arr) if arr.dtype != np.uint8 else arr)
    if w and h:
        a = a.resize((w, h), Image.NEAREST if nearest else Image.LANCZOS)
    im.paste(a, (x, y))


def lut_view(L, ch):
    s = (L[..., ch] * 2 - 1) * np.exp2(L[..., ch + 1] * 14 - 12)
    return np.tanh(s / np.percentile(np.abs(s), 99.5) * 1.5) * 0.5 + 0.5


# ------------------------------------------------------------------ 1. puddles
def sheet_puddle():
    im, d = canvas(2200, 1330)
    title(d, 60, 40, '水洼：雨纹与滴水涟漪', 'Puddles: RainRipple flipbook, RippleRing LUT, DripRipple LUT  (bible §1.6, §5.4, §5.5, §6·1)')
    at = load('RainRipple_Flip8x8_2048.png')
    fr = lambda k: at[(k // 8) * 256:(k // 8 + 1) * 256, (k % 8) * 256:(k % 8 + 1) * 256]
    x = 60
    for i, k in enumerate(range(0, 64, 8)):
        paste(im, mirror_puddle(fr(k)), x + i * 262, 150, 256, 256)
        d.text((x + i * 262 + 6, 410), 'frame %d  t=%.2fs' % (k, k / 32), font=F(16), fill=DIM)
    for i, k in enumerate(range(0, 64, 8)):
        paste(im, u8(fr(k)), x + i * 262, 450, 256, 256)
    cap(d, 60, 720, 'RainRipple_Flip8x8_2048.png（较密的可选项：约 20 滴/m²/s，水田与远处水面用；默认是下面的程序化环）— 上排：把法线当作一片水洼，映出一根灯管和一扇亮窗；下排：法线原图。\n'
        '一格 = 0.5 m × 0.5 m 水面 · 64 帧 · 循环 2.0 s（32 fps）· 空间与时间都无缝。物理：有限水深毛细-重力波色散 + 黏性与表面膜阻尼（Hankel 变换精确解）。')
    t = mirror_puddle(np.tile(fr(21), (2, 2, 1)))
    paste(im, t, 60, 820, 440, 440)
    cap(d, 60, 1268, '同一帧 2 × 2 平铺：看不到接缝', 18)
    for j, (name, rmax, tmax, lab) in enumerate((('RippleRing_LUT_256x128.png', 0.25, 1.25, 'RippleRing_LUT_256x128 — 默认的程序化雨纹（一滴 0.95 mm 毛毛雨）'),
                                                 ('DripRipple_LUT_512x256.png', 0.5, 2.5, 'DripRipple_LUT_512x256 — 灯臂 / 站牌 / 公告箱的滴水（4.5 mm，2–4 m 落下）'))):
        L = load(name)
        x0 = 560 + j * 820
        paste(im, lut_view(L, 0), x0, 840, 380, 300)
        paste(im, lut_view(L, 2), x0 + 400, 840, 380, 300)
        d.text((x0, 1146), 'R,G：全频带', font=F(17), fill=FG); d.text((x0 + 400, 1146), 'B,A：按 4 mm 像素足迹低通（v2）', font=F(17), fill=FG)
        cap(d, x0, 1180, lab + '\n横轴 = 半径 0→%.2f m，纵轴 = 时间 0→%.2f s（下 → 上）；灰 = 平，亮暗 = 坡度。\n编码：坡度 = (R·2−1)·2^(G·14−12)；低通版同样用 B、A。shader 按像素足迹在两者之间插值：\n足迹 ≤ 0.8 mm 用全频带，≥ 1.8 mm 用低通——新落下的一滴不再糊成摩尔纹圆盘，头显里不闪。' % (rmax, tmax), 16)
    im.save(os.path.join(DOCS, 'Sheet_Puddles.png'))


# ------------------------------------------------------------------ 1b. procedural cells (default) - full band vs band-limited
def sheet_cells():
    import cells_ref as CR
    N = 1600; xs = (np.arange(N) + 0.5) / N * 1.0                   # 1 m: 400 px of 2.5 mm, each the mean of 4 x 4 samples
    X, Y = np.meshgrid(xs, xs[::-1])
    def pixel_mean(rgb, k=4):                                       # what a pixel integrates (LanbaiSpecAA approximates it)
        lin = rgb.astype(np.float64) ** 2.2
        lin = lin.reshape(lin.shape[0] // k, k, lin.shape[1] // k, k, 3).mean((1, 3))
        return lin ** (1 / 2.2)
    cx0, cy0, cw = 0.07, 0.25, 0.30                                 # the close-up window (m)
    M = 480; xc = cx0 + (np.arange(M) + 0.5) / M * cw; yc = cy0 + (np.arange(M) + 0.5) / M * cw   # 0.625 mm / px
    Xc, Yc = np.meshgrid(xc, yc[::-1])
    im, d = canvas(2200, 1200)
    title(d, 60, 30, '默认的程序化雨纹：1 m² 水洼里的 1 秒（4 个/m²/s）', "LanbaiRippleCells v2 in a 1 x 1 m puddle (the bible's 3-5 rings / m^2 / s), viewed as a puddle mirror")
    bl_far = float(CR.ring_band(0.0025)); bl_near = float(CR.ring_band(0.000625))
    d.text((60, 112), '坐着看 2 m 外的水洼：像素足迹 2.5 mm → LanbaiRingBand = %.2f（全部用低通行）；每像素取 4 × 4 平均，即 LanbaiSpecAA 逼近的结果' % bl_far, font=F(19), fill=FG)
    d.text((60, 612), '凑近看（上排白框里的 0.30 m，像素足迹 0.6 mm → LanbaiRingBand = %.2f，全频带）' % bl_near, font=F(19), fill=FG)
    for i, t in enumerate((3.0, 3.25, 3.5, 3.75)):
        sx, sy = CR.cells(X, Y, t, 4.0, bl_far)
        x0 = 60 + i * 520
        paste(im, pixel_mean(mirror_puddle(slope_to_rgb(sx, sy))), x0, 145, 480, 440)
        bx0 = x0 + cx0 * 480; by0 = 145 + (1 - cy0 - cw) * 440
        d.rectangle([bx0, by0, bx0 + cw * 480, by0 + cw * 440], outline=(235, 235, 235), width=2)
        d.text((x0, 590), 't = %.2f s' % t, font=F(16), fill=DIM)
        sx, sy = CR.cells(Xc, Yc, t, 4.0, bl_near)
        paste(im, mirror_puddle(slope_to_rgb(sx, sy)), x0, 645, 480, 440)
        d.text((x0, 1090), 't = %.2f s' % t, font=F(16), fill=DIM)
    cap(d, 60, 1130, '每个 0.6 m 格子在随机时刻、随机位置落一滴（大小 ×0.8–1.2），两层错开；平滑、从不重复。第 1 幕所有水洼（包括主角水洼）默认用它。\n'
        '远处的一滴是几圈干净的环；凑近才看得到毛细细纹。（t = 3.75 s 时第二滴正好落在第一滴的环心——两层格子是独立的，偶尔会这样。）', 17)
    im.save(os.path.join(DOCS, 'Sheet_PuddleCells.png'))


# ------------------------------------------------------------------ 2. glass
def sheet_glass():
    from glass_ref import Glass, shade, wiper_since
    import runners_ref as RR
    G = Glass()
    im, d = canvas(2200, 2290)
    title(d, 60, 40, '玻璃上的雨：静止水珠 + 流动的水滴 + 雨刮（v2）', 'Glass: RainBeads (static) + GlassRunners lanes (running drops, v2 model) + wiper arcs  (bible §4.6, 1→2)')
    for i, var in enumerate(('Vertical', 'Horizontal')):
        n = load('RainBeads_%s_Normal_1024.png' % var)[:512, :512]
        paste(im, shade_normal(n), 60 + i * 540, 150, 512, 512)
        cap(d, 60 + i * 540, 670, 'RainBeads_%s（%s）\n平铺 0.20 m；沉积 + 并合模拟，%s' %
            (var, '车窗、挡风、站牌、车身' if var == 'Vertical' else '天窗顶面、公告箱顶、长凳', '大于 2.1 mm 的滑走成流滴' if var == 'Vertical' else '不滑落，可到 3.4 mm'), 17)
    dd = load('RainBeads_Vertical_Data_1024.png')[:512, :512]
    for k, lab in enumerate(('R 厚度', 'G 残留阈值（按面积）', 'B 覆盖', 'A 尺寸')):
        paste(im, np.repeat(dd[..., k:k + 1], 3, 2), 1120 + (k % 2) * 228, 150 + (k // 2) * 256, 220, 220)
        d.text((1120 + (k % 2) * 228, 150 + (k // 2) * 256 + 222), lab, font=F(17), fill=DIM)
    fl = load('GlassRunners_Flow_512x1024.png')
    for k, lab in enumerate(('R 偏移', 'G 泳道', 'B 路径斜率', 'A 遮罩')):
        paste(im, np.repeat(fl[:, :, k:k + 1], 3, 2), 1600 + k * 145, 150, 128, 256)
        d.text((1600 + k * 145, 412), lab, font=F(17), fill=DIM)
    cap(d, 1600, 450, 'GlassRunners_Flow_512x1024：0.20 × 0.40 m，\n12 条蜿蜒的泳道；水滴沿 −v 流，\n头部、拖痕、残留小珠在 shader 里算。', 17)
    cap(d, 1120, 680, 'v2：G 已按“剩下多少水珠面积”重排——rainAmount = a 时\n约剩 a 的水珠面积（大珠最后走，小珠先蒸发）：\n醒 0.4 = 剩 40% 的大水珠；公告箱 0.25 = 稀疏几颗。', 17)
    Wp, Hp = 420, 560; w, h = 0.10, 0.1333
    xs = (np.arange(Wp) + 0.5) / Wp * w; ys = (np.arange(Hp) + 0.5) / Hp * h
    X, Y = np.meshgrid(xs, ys[::-1]); P = np.stack([X + 1.33, Y + 0.71], -1).astype(np.float32)
    states = [('第 1 幕 站台：静止 + 偶尔慢流 3 cm/s（密度 0.05）', dict(t=787.5, amount=1.0, speed=0.03, density=0.05)),
              ('第 2 幕 夜路：被风推向后斜 50°（10 m/s）', dict(t=40.0, amount=1.0, flow_dir=(-0.766, -0.643), speed=0.22, density=0.75, stretch=0.8)),
              ('离地：向上向后拉丝、正在蒸发（0.5）', dict(t=40.0, amount=0.5, flow_dir=(-0.8, 0.6), speed=0.35, density=0.8, stretch=1.6)),
              ('第 12 幕 醒：0.4 = 剩 40% 的水珠（大的）', dict(t=40.0, amount=0.4, speed=0.03, density=0.0))]
    Y0 = 790
    cap(d, 60, Y0, 'Lanbai/BusGlass 的数学（Tools~/src/glass_ref.py 是它的 numpy 版本，逐行对应）在四种雨状态下的样子（0.10 × 0.13 m 玻璃，光从左上）：', 18, FG)
    for i, (lab, kw) in enumerate(states):
        t = kw.pop('t')
        su, sv, _, _ = G.slopes(P, t, **kw)
        paste(im, shade(su, sv), 60 + i * 530, Y0 + 40, Wp, Hp)
        cap(d, 60 + i * 530, Y0 + 40 + Hp + 6, lab, 17, FG)
    # wiper sequence: a 0.9 x 0.55 m windscreen patch (pivot bottom left) seen at night against the headlights' glow:
    # every bead catches light (haze), a wiped arc is black glass. 3 x 3 samples per pixel (beads are 0.1-2 mm).
    Y1 = Y0 + 40 + Hp + 60
    ww, wh, k3 = 0.9, 0.55, 3
    nx, ny = 500, 305; px_ = ww / nx
    xs = (np.arange(nx * k3) + 0.5) * px_ / k3; ys = (np.arange(ny * k3) + 0.5) * px_ / k3
    X, Y = np.meshgrid(xs, ys[::-1]); P2 = np.stack([X, Y], -1).astype(np.float32)
    piv, rmin, rmax, sweep, stroke = (0.12, 0.02), 0.14, 0.66, np.radians(95), 0.65
    cap(d, 60, Y1, '雨刮（LanbaiWipers.cs → _Udon_Wiper*；挡风玻璃材质 _Wipers = 1）：一次往返 2 × 0.65 s、每 5 s 一次；刮过的弧里水珠按各自的 G 一颗颗回来（_WipeRefill 3 s），\n'
        '流滴随后再形成；刮片前沿推着一条细水线。下图：0.9 × 0.55 m 挡风玻璃，夜里迎着车灯的光看——每颗水珠都亮，刮净的弧是黑的玻璃（深色线 = 刮片）。', 18, FG)
    for i, tau in enumerate((0.35, 1.0, 1.8, 2.8, 4.5)):
        ws = wiper_since(P2, piv, (1.0, 0.0), sweep, rmin, rmax, tau, 0.0, stroke=stroke, prev=False)
        su, sv, th, hh = G.slopes(P2 + 3.0, 50.0, amount=1.0, flow_dir=(0.0, 1.0), speed=0.05, density=0.3, wipe_since=ws)
        slope = np.hypot(su, sv)
        glint = np.clip(slope * 1.6, 0, 1) * 0.85 + np.clip((th + hh) / 0.0004, 0, 1) * 0.15
        g = glint.reshape(ny, k3, nx, k3).mean((1, 3))
        v = np.clip(0.035 + g * 1.25, 0, 1) ** (1 / 1.6)
        rgb = np.dstack([v * 0.93, v * 0.97, v])
        x0 = 60 + i * 422; y0 = Y1 + 66
        paste(im, rgb, x0, y0, 410, 250)
        if tau <= 2 * stroke:                                       # the blade (forward, then back, then parked)
            to = tau if tau <= stroke else 2 * stroke - tau
            phi = sweep * (1 - np.cos(np.pi * to / stroke)) / 2
        else:
            phi = 0.0
        sc = 410 / ww
        def pt(r):
            return (x0 + (piv[0] + r * np.cos(phi)) * sc, y0 + 250 - (piv[1] + r * np.sin(phi)) * sc)
        d.line([pt(0.0), pt(rmin)], fill=(60, 64, 70), width=3)
        d.line([pt(rmin), pt(rmax)], fill=(8, 9, 11), width=5)
        d.text((x0, y0 + 256), '刮片起步后 %.2f s' % tau, font=F(16), fill=DIM)
    # kymograph: runners v2 (no headless channels, no pops)
    Y2 = Y1 + 66 + 250 + 50
    cap(d, 60, Y2, '流滴 v2（验收第 2 轮 M3）：头停下后变成一颗水珠、先停留再蒸发；拖痕按“头经过后的时间”逐渐被新水珠占回，并跨过周期边界——\n'
        '不再有“没有水滴的通道往前长、然后一帧之内整条复原”。120 s 站台参数实测（runner_metrics.py，单层）：无头通道 0.09 个/m²（旧 3.9）、一帧复原 0 次/m²/min（旧 126）、\n同时在滑的水滴两层合计 6.8 个/m²（旧 45，“偶尔慢流”）。', 17)
    try:
        kym = RP.find('kymo_runners_stop.png')     # written by runner_metrics.py
    except FileNotFoundError:
        kym = None
    if kym:
        k = np.asarray(Image.open(kym).convert('RGB'))
        kw_, kh_ = 2080, 300                            # a kymograph: the aspect is free
        paste(im, k, 60, Y2 + 80, kw_, kh_)
        cap(d, 60, Y2 + 80 + kh_ + 8, '五条最忙的泳道，各 120 s（站台：3 cm/s，密度 0.05）。每格：横轴 = 时间 0 → 120 s，纵轴 = 沿泳道的位置（0.40 m，上 → 下）；'
            '红 = 水滴头，灰 = 被刷干净的通道（越亮越干净）。\n头一路滑下 → 停住（红色横线 = 停着的那颗水珠）→ 蒸发；通道从最早经过的地方开始慢慢长回水珠，没有一处突然消失。', 16)
    im.save(os.path.join(DOCS, 'Sheet_Glass.png'))


# ------------------------------------------------------------------ 3. drops
def srgb(lin):
    lin = np.clip(lin, 0, None)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * np.power(np.minimum(lin, 1.0), 1 / 2.4) - 0.055)


def night_env(t):
    """a stand-in for the probe the drops refract (pane frame: x right, y up, z out of the bus): the night field,
    the tube 20 deg to the right at 6-7.5 deg elevation, and its long reflection in the paddy below the horizon."""
    t = t / np.maximum(np.linalg.norm(t, axis=-1, keepdims=True), 1e-6)
    el = np.degrees(np.arcsin(np.clip(t[..., 1], -1, 1))); az = np.degrees(np.arctan2(t[..., 0], np.maximum(t[..., 2], 1e-4)))
    sky = np.where(el > 0, 0.010 + 0.010 * np.exp(-el / 12), 0.004)
    tube = (np.abs(az - 20) < 12) * np.exp(-((el - 6.8) / 0.6) ** 2) * 3.0
    refl = (np.abs(az - 20) < 9) * np.exp(-((el + 6.8) / 1.6) ** 2) * 0.35 * (el < 0)
    glow = 0.05 * np.exp(-(((az - 20) / 18) ** 2 + ((el - 6.8) / 7) ** 2))
    v = sky + tube + refl + glow
    return np.stack([v * 0.90, v * 0.97, v * 1.0], -1)


def drop_optics_panels(im, d, x0, y0):
    """M2: one 4 mm bead (55 deg contact angle) on the OUTER face, seen from the cabin through the pane, exactly
    LanbaiDropExit + LanbaiDropRadiance (TIR -> insideColour * 0.6), at view angles 0 / 30 / 45 / 60 deg."""
    from glass_ref import drop_exit
    a = 0.002; R = a / np.sin(np.radians(55)); N = 300; ext = 0.0034
    xs = (np.arange(N) + 0.5) / N * 2 * ext - ext
    X, Y = np.meshgrid(xs, xs[::-1]); r = np.hypot(X, Y); inside = r < a
    zc = np.sqrt(np.maximum(R * R - r * r, 0))
    Nd = np.stack([X, Y, zc], -1) / R; Nd[~inside] = (0, 0, 1)
    Np = np.broadcast_to(np.array([0, 0, 1.0]), Nd.shape)
    cabin = np.array([0.050, 0.056, 0.062])
    fr = []
    for i, th in enumerate((0, 30, 45, 60)):
        I = np.broadcast_to(np.array([np.sin(np.radians(th)), 0.0, np.cos(np.radians(th))]), Nd.shape)
        t = drop_exit(I, Np, Nd)
        tir = (np.sum(t * t, -1) < 1e-4) & inside
        col = np.where(tir[..., None], cabin * 0.6, night_env(np.where(tir[..., None], I, t)))
        col = np.where(inside[..., None], col, night_env(I))
        fr.append(tir.sum() / inside.sum())
        w = max(1, int(round(260 * np.cos(np.radians(th)))))           # the pane foreshortened as the eye sees it
        paste(im, srgb(col * 2.2), x0 + i * 290 + (260 - w) // 2, y0, w, 260)
        d.text((x0 + i * 290, y0 + 266), '视角 %d°：全反射 %d %%' % (th, round(fr[-1] * 100)), font=F(16), fill=DIM)
    return fr


def case_panels(im, d, x0, y0):
    """M6: the notice-case glass seen from outside at 1.2 m, lit paper behind it - LanbaiDropOutside composited over
    the paper (premultiplied: out = rgb + paper * (1 - a)), at _RainOverride 1.0 (scene 1) and 0.25 (scene 12)."""
    from glass_ref import Glass
    G = Glass(); N = 300; w = 0.045
    xs = (np.arange(N) + 0.5) / N * w
    X, Y = np.meshgrid(xs, xs[::-1]); P = np.stack([X + 0.37, Y + 0.52], -1).astype(np.float32)
    rng = np.random.default_rng(7)
    paper = np.full((N, N), 1.0)
    for row in range(7):                                            # lines of small print (5 mm leading)
        yy = 0.004 + row * 0.0058
        xk = 0.003
        while xk < w - 0.004:
            cw = rng.uniform(0.0026, 0.0034)
            if rng.random() > 0.08:
                m = (X > xk) & (X < xk + cw * 0.86) & (Y > w - yy - 0.0034) & (Y < w - yy)
                paper = np.where(m, 0.18 + 0.1 * rng.random(), paper)
            xk += cw
    paper_lin = paper[..., None] * np.array([0.52, 0.50, 0.44])     # #C0BCB2-ish under the case light
    behind = np.array([0.52, 0.50, 0.44]) * 0.35                     # _BehindColour x CaseLight at the rim (x 0.35)
    for i, (amt, lab) in enumerate(((1.0, '第 1 幕：_RainOverride 1.0'), (0.25, '第 12 幕：_RainOverride 0.25'))):
        su, sv, th, _ = G.slopes(P, 10.0, amount=amt, density=0.0)
        n = np.stack([-su, -sv, np.ones_like(su)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
        c = np.clip(n[..., 2], 0, 1); Fr = 0.02 + 0.98 * (1 - c) ** 5
        tilt = np.sqrt(np.clip(1 - c * c, 0, 1))
        rimDark = np.clip((tilt - 0.45) / 0.40, 0, 1); rimDark = rimDark * rimDark * (3 - 2 * rimDark) * 0.55
        I = np.broadcast_to(np.array([0, 0, -1.0]), n.shape)
        rdir = I - 2 * (I * n).sum(-1, keepdims=True) * n
        refl = night_env(np.stack([rdir[..., 0], rdir[..., 1], -rdir[..., 2]], -1)) * 0.6
        aT = Fr + (1 - Fr) * rimDark
        out = refl * Fr[..., None] + behind * ((1 - Fr) * rimDark)[..., None] + paper_lin * (1 - aT)[..., None]
        paste(im, srgb(out), x0 + i * 320, y0, 300, 300)
        d.text((x0 + i * 320, y0 + 306), lab, font=F(16), fill=DIM)


def sheet_drops():
    im, d = canvas(2200, 1640)
    title(d, 60, 40, '“那一滴雨”、悬滴、踏步湿斑', "'That one raindrop', the pendant drip, the wet door step  (bible §3.3, §4.6, §5.4, §6·12)")
    def shade_atlas(a):
        s = shade_normal(a); cov = a[..., 3]
        return np.dstack([s * cov + 0.06 * (1 - cov)] * 3)
    p = load('PendantDrop_Flip4x4_512.png'); h = load('OneDrop_Head_Flip4x4_512.png')
    paste(im, shade_atlas(p), 60, 150, 512, 512, nearest=True)
    cap(d, 60, 670, 'PendantDrop_Flip4x4_512 — 天窗框角 / 灯罩端 /\n公告箱顶的悬滴。帧 0–11：Young–Laplace 解，\n唇口半径 1.5 mm（Ø3 mm），体积长到 4.8e-8 m³（≈Ø4.5 mm）；\n12–14：颈缩、断裂（卫星滴）；15：回弹。\n一帧 10 × 10 mm，唇口在顶边中点。', 17)
    paste(im, shade_atlas(h), 640, 150, 512, 512, nearest=True)
    cap(d, 640, 670, 'OneDrop_Head_Flip4x4_512 — 4 mm 的那一滴：\n帧 0 静止（重力下垂），帧 15 滑动（前沿陡、后尾拉长）。\n_Slide 由速度决定：停顿时它变圆。\n一帧 12 × 12 mm，锚点 (0.5, 0.40)。', 17)
    t = load('OneDrop_Trail_128x1024.png')
    v = np.dstack([np.clip(t[..., 2] * 0.35 + t[..., 1] * 1.2, 0, 1)] * 3)
    paste(im, v, 1220, 150, 96, 768, nearest=True)
    cap(d, 1330, 150, 'OneDrop_Trail_128x1024\n贴花 12 × 96 mm\n\n起点：顶下 8 mm\n停顿：+20 mm（第 1 幕，\n  1 cm/s，玩家坐下时）\n终点：+80 mm，落到胶条\n  （第 12 幕，8 秒）\n\nR 路径中线\nG 残留小水珠\nB 湿痕', 17)
    sw = load('StepWet_Decal_256.png')
    paste(im, np.dstack([np.clip(sw[..., 0] * 0.5 + sw[..., 1] * 1.5 + sw[..., 2] * 0.4, 0, 1)] * 3), 1650, 150, 400, 400)
    cap(d, 1650, 560, 'StepWet_Decal_256 — 车门踏步上\n天窗滴水积出的湿斑（0.12 m）：\n中心水膜、边缘水环、飞溅小珠。\n_Wet 每滴 +0.12，慢慢变干。', 17)
    d.text((60, 900), '水滴的光学（v2）', font=F(24), fill=FG)
    fr = drop_optics_panels(im, d, 60, 950)
    cap(d, 60, 1250, '从车内看外表面上的一颗 4 mm 水珠（接触角 55°），LanbaiDropExit：车内空气 → 平板 → 水 → 弯曲的水面 → 空气，两次折射。\n'
        '中间是倒过来的夜景（灯管在右 20°，田里的倒影在下），边缘一圈全反射，只映出车厢（insideColour × 0.6）。\n'
        '全反射的面积随视角增大：%s（v1 只算一次界面，比例错）。左右按视角压扁，就是眼睛看到的样子。' % '、'.join('%d°→%d %%' % (a, round(f * 100)) for a, f in zip((0, 30, 45, 60), fr)), 16)
    case_panels(im, d, 1260, 950)
    cap(d, 1260, 1290, '公告箱玻璃，从外面 1.2 m 看，后面是亮着的纸（LanbaiDropOutside）：\n'
        '水珠大部分透明（反射 F，其余透过），只有陡的边缘偏折到别处、\n'
        '取 _BehindColour × _Udon_CaseLight 的暗一点的颜色——字读得出来，\n'
        '不再是一片黑色圆点。第 12 幕 0.25 = 只剩约 23 % 的水珠面积。', 16)
    gl = os.environ.get('HERO_CROP')
    if gl and os.path.exists(gl):
        g = np.asarray(Image.open(gl).convert('RGB'))
        paste(im, g, 60, 1340, 260, 260)
        cap(d, 340, 1350, '在 BusGlass 水珠之中的那一滴（静止在 2 cm 停顿处，Tools~/src/glass_normals.py 用套件数学合成）：\n它扫过的那条窄带上大水珠被带走，只留细小残珠（_Udon_OneDropA/B → LanbaiOneDropSwept）。\nv2：Hide() 在 1.5 s 内把它和这条窄带一起淡出——第 2–11 幕窗上不会留下一条空带。', 17, FG)
    im.save(os.path.join(DOCS, 'Sheet_Drops.png'))


# ------------------------------------------------------------------ 4. particles
def sheet_particles():
    im, d = canvas(2200, 1100)
    title(d, 60, 40, '雨丝与溅花', 'Rain streak atlas and crown splash flipbook  (bible §6·1: lit only where lit)')
    st = load('RainStreak_Atlas8x1_512.png')
    lum = st[..., 0] * st[..., 3]
    names = json.load(open(RP.find('streaks.json')))['cells']
    for i in range(8):
        cell = lum[:, i * 64:(i + 1) * 64]
        tint = np.array([0.82, 0.90, 0.95])
        paste(im, cell[..., None] * tint, 60 + i * 150, 150, 128, 640)
        d.text((60 + i * 150, 800), '%d %s' % (i, names[i]), font=F(16), fill=DIM)
    cap(d, 60, 840, 'RainStreak_Atlas8x1_512（一格 64 × 512，横向放大 2 倍显示）：亮度 + alpha，颜色和明暗由灯决定（× _Tint #DCE7F3）。\n'
        '可见的线（半高全宽）= 四边形宽的 1/8：Start Size 0.032–0.048 m → 线宽 4–6 mm（圣经值）。v = 1（上）= 头部，v = 0 = 尾。\n'
        '水滴下落时以 ~120 Hz 振荡，1/30 s 的拖影里留下 3–6 个“珠”；反射与折射两个高光分开时成双线（Garg & Nayar）。', 17)
    sp = load('RainSplash_Flip4x4_512.png')
    paste(im, np.dstack([sp[..., 0]] * 3) * np.array([0.85, 0.93, 0.97]), 1320, 150, 800, 800)
    for k in range(1, 4):                                     # cell borders
        d.line([(1320 + k * 200, 150), (1320 + k * 200, 950)], fill=(40, 48, 60)); d.line([(1320, 150 + k * 200), (2120, 150 + k * 200)], fill=(40, 48, 60))
    cap(d, 1320, 960, 'RainSplash_Flip4x4_512：Ø2.2 mm、5 m/s 的雨滴落在 0.3 mm 水膜上，\nCycles 16 帧（0–32 ms，播 0.12 s）。\nv2：外圈飞沫淡出、整帧绕撞击点缩到 0.84——每格四边留 ≥ 6 px 空白，\n不再被格子边切直、不串格。一格 = 57 mm（Start Size ×1/0.84），撞击点仍在 (0.5, 0.125)。', 17)
    im.save(os.path.join(DOCS, 'Sheet_Particles.png'))


# ------------------------------------------------------------------ 5. wet masks
def viz_mask(m):
    R, G, B, A = [m[..., k] for k in range(4)]
    v = np.stack([0.20 + 0.32 * G] * 3, -1)
    v = v * (1 - B[..., None]) + B[..., None] * np.array([0.78, 0.52, 0.24])
    v = v * (1 - A[..., None]) + A[..., None] * 0.95
    pud = np.clip(R * 1.4, 0, 1)[..., None]
    return v * (1 - pud) + pud * np.array([0.10, 0.36, 0.85])


def sheet_wetmask():
    m = load('Stop_WetMask_2048x512.png'); rm = load('Road_WetMask_2048x512.png')
    lay = json.load(open(RP.find('Stop_Layout.json')))
    im, d = canvas(2200, 1200)
    title(d, 60, 30, 'Stop_WetMask + Road_WetMask 布局（从上往下看，车头朝右）', 'Plan view: R puddles (blue), G film retention (grey level), B shelter under the bus (orange), A worn paint (white)')
    X0, Y0, S = 76, 150, 2048 / 48.0
    paste(im, viz_mask(m), X0, Y0, 2048, 512)
    def P(x, y):
        return (X0 + (x + 22) * S, Y0 + (7 - y) * S)
    L = lay['layout_stage']
    def dot(x, y, col, lab, dx=10, dy=-26):
        px, py = P(x, y); d.ellipse([px - 6, py - 6, px + 6, py + 6], fill=col)
        tw = d.textlength(lab, font=F(17))
        d.rectangle([px + dx - 3, py + dy - 1, px + dx + tw + 3, py + dy + 22], fill=(10, 12, 18))
        d.text((px + dx, py + dy), lab, font=F(17), fill=col)
    dot(*L['tube'][:2], (240, 245, 250), '灯管 tube (z 3.9)', dx=12, dy=-30)
    dot(*L['sign'][:2], (180, 210, 255), '站牌 sign', dx=-110, dy=10)
    dot(*L['notice_case'], (200, 190, 255), '公告箱 notice case', dx=12, dy=12)
    dot(*L['spawn'], (255, 140, 140), '出生点 spawn')
    dot(*L['hero_eye'][:2], (140, 255, 170), '主座位眼 hero eye', dy=8)
    offs = dict(lamp=(14, -6), sign=(14, 34), case=(14, -40))
    for k, v in L['drips'].items():
        dot(v[0], v[1], (255, 220, 120), '滴 drip: ' + k, dx=offs[k][0], dy=offs[k][1])
    bx0, bx1 = L['bus_x']; by0, by1 = L['bus_y']
    a, b_ = P(bx0, by1), P(bx1, by0); d.rectangle([a[0], a[1], b_[0], b_[1]], outline=(255, 200, 120), width=2)
    d.text((a[0] + 10, a[1] + 8), '中巴 bus（B = 干矩形）→ 车头', font=F(18), fill=(255, 200, 120))
    for hname, h in lay['hero_puddles'].items():
        pts = [P(x, y) for (x, y) in h['outline_stage_xy']]
        d.line(pts + [pts[0]], fill=(120, 230, 255), width=2)
    for i in range(0, 49, 3):
        px = X0 + i * S; d.line([px, Y0 + 512, px, Y0 + 520], fill=DIM)
    # the road mask: one 60 m period, and the continuity across the stop rect's ends
    Sr = 2048 / 60.0 * 0.6
    cap(d, 76, 690, 'Road_WetMask_2048x512：同一条路面的一个 60 m 周期（= R_Road 模块长度），沿路无缝平铺（Wrap U = Repeat，V = Clamp）。下图：站台遮罩放回它所在的路上（红线 = 站台矩形的两端）。', 18, FG)
    Zw = np.arange(-58, 62, 120 / 2048)
    s = (Zw + 21) % 60; xi = s / 60 * 2048 - 0.5; i0 = np.floor(xi).astype(int) % 2048; fr_ = xi - np.floor(xi); i1 = (i0 + 1) % 2048
    strip = rm[:, i0] * (1 - fr_[None, :, None]) + rm[:, i1] * fr_[None, :, None]
    inside = (Zw >= -22) & (Zw < 26)
    ui = np.clip(((Zw[inside] + 22) / 48 * 2048).astype(int), 0, 2047)
    strip[:, inside] = m[:, ui]
    sv = viz_mask(strip)
    lo = np.argmax(inside); hi = len(Zw) - np.argmax(inside[::-1])
    sv[:, max(lo - 1, 0):lo + 1] = [1, 0.2, 0.2]; sv[:, hi - 1:hi + 1] = [1, 0.2, 0.2]
    paste(im, sv, 76, 730, 2048, 256)
    fr = lay
    cap(d, 76, 1010,
        '映射（R_Stop 局部，+Z = 车头方向，+X = 车门 / 站牌一侧）：站台 u = (Z + 22) / 48，v = (5 − X) / 12（2.34 cm / 像素，刻度 3 m）；道路 u = (Z + 21) / 60 或 R_Road 网格 UV2.x / 60（2.93 cm / 像素）。\n'
        '站台遮罩的最后 3 m 与道路遮罩逐像素一致：Lanbai/WetSurface 在矩形外自动接上道路遮罩，路一直延伸进雾里，虚线、水洼、水膜都不断。\n'
        '水洼不是画的：一条 60 m 周期的路面高度场（2%% 路拱、轮辙、边缘沉降、补丁、坑洞）→ 优先洪泛填洼；站台再叠加自己的地形（门口的纵向凹、车道更深的轮辙、路肩旧车辙、四个主角水洼），并向两端淡出。\n'
        '实测有水比例：站台路面 %.1f%%、路肩 %.1f%%；道路遮罩路面 %.1f%%、路肩 %.1f%%（圣经 15–25%%）。浅蓝轮廓 = 主角水洼（模板镜像），Stop_Layout.json 给出轮廓与滴水落点。\n'
        'G：路拱最先干，轮辙、边缘、水洼周围最湿。B：车下潮而不湿（反照率 ×0.8、光滑度 0.45）。A：中心虚线 3 m 实、每 60/7 = 8.57 m 一段（模块内整数段），磨掉 60%%；两侧边线断续、剩 40%%；没有黄线。\n'
        '滴水落点：灯臂 → lamp_drip 水洼；公告箱顶沿 → notice_case 水洼；站牌下缘 → 混凝土基座顶面那一层积水（WetSurface 的 _WetMaskDefault，见 README「滴水」一节）。'
        % (fr['stop_road_puddle_fraction'] * 100, fr['stop_shoulder_puddle_fraction'] * 100, fr['road_mask_road_puddle_fraction'] * 100, fr['road_mask_shoulder_puddle_fraction'] * 100), 17)
    im.save(os.path.join(DOCS, 'Stop_WetMask_Layout.png'))


if __name__ == '__main__':
    which = sys.argv[2:] or ['puddle', 'cells', 'glass', 'drops', 'particles', 'wetmask']
    for w in which:
        globals()['sheet_' + w]()
        print('sheet', w)
    print('docs written to', DOCS)
