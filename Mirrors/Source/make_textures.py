"""蓝白 · 白铜镜贴图（spec_conventions.md §2、§4、§5）。确定性：同样的代码出同样的图。

    ~/bpy/bin/python make_textures.py            -> Mirrors/Textures/*.png + Docs~/textures_preview.png

镜背一格 = 40 m 的博局（第 1 面镜 R = 20 m 正好一格）。格坐标 u 向东（物体 +X）、v 向北（物体 +Z），
图像第 0 行在顶上（v = 1），Unity 采样时 v = 0 在底：所以 row = (1 - v) * N。
构图照真镜（克利夫兰 1995.301 等，Docs~/实物参考_博局镜/）：钮座四叶 → 内方框 → 十二乳与十二地支（每边 4 乳 3 字，
角上的乳两边共用）→ 双线外方框 → T、L、V → 八乳（八瓣星形座 + 圆座）→ 四神细线 + 云气纹。
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFilter
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter, distance_transform_edt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
OUT = os.path.join(ROOT, 'Textures')
DOC = os.path.join(ROOT, 'Docs~')
os.makedirs(OUT, exist_ok=True)

N = 2048                  # output
SS = 2                    # supersampling for drawing
M = N * SS
TILE_M = 40.0
R_PX = M / 2.0            # canonical mirror radius (20 m) in canvas px
PX_M = TILE_M / N         # metres per output pixel
RELIEF_M = 0.016 * 40.0   # height 1.0 = 0.64 m (8 bosses)

# 铭文：照克利夫兰 1995.298（CC0，D-31）铭文带描的笔画中线（Source/glyph_traces/），不用字体、不用阈值。
# 字形是两汉镜铭的隶变篆书（缪篆一路），繁体古字形；原文未逐字释读，按照片上的顺序（从正上方顺时针）放进字表。
# 十二地支在镜背主区的照片里（1995.301），不在字表。
INSC_PHOTO = os.path.join(ROOT, 'Docs~', '实物参考_博局镜', 'CMA_1995.298.jpg')   # 1995.298 多乳钉博局镜，铭文带一圈 35 字
INSC_C = (1656.0, 1465.0, 1072.0)        # 镜心 x, y 与半径（照片像素，照片正拍、镜是正圆）
INSC_Q = (0.535, 0.655)                  # 铭文带 r/R（内线 .. 栉齿内线）
# 35 个字的中心：从正上方顺时针，单位 = 一周 4000
INSC_AT = [150, 290, 415, 540, 685, 840, 995, 1135, 1255, 1380, 1485, 1580, 1690, 1795, 1920, 2030, 2145, 2250,
           2365, 2465, 2565, 2645, 2740, 2845, 2965, 3060, 3150, 3230, 3325, 3430, 3565, 3655, 3775, 3875, 4005]
N_INSC = len(INSC_AT)
assert N_INSC == 35, N_INSC


def P(u, v):
    """cell (u east, v north; centre 0,0; unit = canonical R) -> canvas px (x, y)."""
    return (M / 2 + u * R_PX, M / 2 - v * R_PX)


class Layer:
    """a height layer drawn with PIL at canvas resolution; combined with max()."""
    def __init__(self):
        self.im = Image.new('L', (M, M), 0)
        self.d = ImageDraw.Draw(self.im)

    def line(self, pts, w, val=255):
        xy = [P(*p) for p in pts]
        self.d.line(xy, fill=val, width=max(1, int(round(w * R_PX))), joint='curve')
        r = w * R_PX / 2
        for (x, y) in (xy[0], xy[-1]):
            self.d.ellipse((x - r, y - r, x + r, y + r), fill=val)

    def poly(self, pts, val=255):
        self.d.polygon([P(*p) for p in pts], fill=val)

    def disc(self, c, r, val=255):
        x, y = P(*c); rr = r * R_PX
        self.d.ellipse((x - rr, y - rr, x + rr, y + rr), fill=val)

    def ring(self, c, r, w, val=255):
        x, y = P(*c); rr = r * R_PX
        self.d.ellipse((x - rr, y - rr, x + rr, y + rr), outline=val, width=max(1, int(w * R_PX)))

    def arr(self, blur_px=0.0):
        a = np.asarray(self.im, np.float32) / 255.0
        return gaussian_filter(a, blur_px, mode='wrap') if blur_px > 0 else a


def rot(p, a):
    c, s = math.cos(a), math.sin(a)
    return (p[0] * c - p[1] * s, p[0] * s + p[1] * c)


def C4(fn):
    """draw a motif defined for the NORTH quadrant (axis +v) four times, rotating clockwise (north -> east ...)."""
    for k in range(4):
        fn(lambda p, k=k: rot(p, -k * math.pi / 2), k)


def bezier(p0, p1, p2, p3, n=40):
    out = []
    for i in range(n + 1):
        t = i / n; a = 1 - t
        out.append((a ** 3 * p0[0] + 3 * a * a * t * p1[0] + 3 * a * t * t * p2[0] + t ** 3 * p3[0],
                    a ** 3 * p0[1] + 3 * a * a * t * p1[1] + 3 * a * t * t * p2[1] + t ** 3 * p3[1]))
    return out


def spiral(c, r0, turns, ccw=1, n=60):
    pts = []
    for i in range(n + 1):
        t = i / n
        a = ccw * 2 * math.pi * turns * t
        r = r0 * (1 - 0.8 * t)
        pts.append((c[0] + r * math.cos(a), c[1] + r * math.sin(a)))
    return pts


def dome(shape, centres, radius, power=1.0):
    """analytic domes (canvas px) -> 0..1 array; wraps."""
    H = np.zeros(shape, np.float32)
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]].astype(np.float32)
    for (u, v) in centres:
        cx, cy = P(u, v)
        dx = (xx - cx + M / 2) % M - M / 2
        dy = (yy - cy + M / 2) % M - M / 2
        d2 = (dx * dx + dy * dy) / (radius * R_PX) ** 2
        H = np.maximum(H, np.sqrt(np.clip(1 - d2, 0, 1)) ** power)
    return H


INSC_TRACE = os.path.join(HERE, 'glyph_traces', 'inscription_1995.298.json')
INSC_BOX = (19.0, 16.8)                  # trace units of one crop (x, y)
INSC_STROKE = 1.05                       # stroke width, trace units (the real band's strokes: ~10 px of the 2x unwrap)


def traced_glyph(polys, px):
    """one traced character -> px x px relief, the SAME scale and stroke width for every character (review r3 #2):
    the crop (19 x 16.8 units) is centred in the cell at px / 19.5 per unit; strokes are cast ridges with a round
    profile, continuous wherever the trace is."""
    k = 4
    big = px * k
    sc = big / 19.5
    ox = (big - INSC_BOX[0] * sc) / 2.0; oy = (big - INSC_BOX[1] * sc) / 2.0
    im = Image.new('L', (big, big), 0)
    d = ImageDraw.Draw(im)
    w = INSC_STROKE * sc
    for pl in polys:
        pts = [(ox + x * sc, oy + y * sc) for x, y in pl]
        d.line(pts, fill=255, width=int(round(w)), joint='curve')
        for x, y in pts:
            d.ellipse((x - w / 2, y - w / 2, x + w / 2, y + w / 2), fill=255)
    a = np.asarray(im, np.float32) / 255.0 > 0.5
    dist = distance_transform_edt(a) / (w / 2)                     # 0 at the edge .. 1 on the centre line
    h = np.sqrt(np.clip(dist * (2 - dist), 0, 1))                  # round ridge
    out = Image.fromarray((h * 255).astype(np.uint8)).resize((px, px), Image.LANCZOS)
    return np.asarray(out, np.float32) / 255.0


def photo_inscription():
    """35 traced glyphs (top of the glyph = outward, reading clockwise) and the matching photo crops (for the plate)."""
    import json
    from scipy.ndimage import map_coordinates
    tr = json.load(open(INSC_TRACE, encoding='utf-8'))
    L = np.asarray(Image.open(INSC_PHOTO).convert('L'), np.float32) / 255.0
    cx, cy, R = INSC_C
    W, Hh = 8000, 260
    th = np.linspace(-np.pi / 2, 1.5 * np.pi, W, endpoint=False)
    q = np.linspace(INSC_Q[1], INSC_Q[0], Hh)                     # row 0 = outer
    T, Q = np.meshgrid(th, q)
    st = map_coordinates(L, [cy + R * Q * np.sin(T), cx + R * Q * np.cos(T)], order=1)
    ext = np.concatenate([st[:, -400:], st, st[:, :400]], 1)
    crops = []
    for c in INSC_AT:
        x = 2 * c + 400
        crops.append(ext[78:246, x - 95:x + 95])
    return [tr[str(i)] for i in range(N_INSC)], crops


def relief_shade(h, strength=6.0, light=(-0.5, 0.6, 0.62)):
    """the glyph heights lit like the photo plate (raking light from the upper left), bronze tone."""
    h = gaussian_filter(h, 0.8)
    gy, gx = np.gradient(h)
    n = np.stack([-gx * strength, gy * strength, np.ones_like(h)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    l = np.array(light); l = l / np.linalg.norm(l)
    v = np.clip(n @ l, 0, 1) * (0.75 + 0.25 * h)
    return v


def inscription_plate(crops, traces, G):
    """Docs~/inscription_plate.png: every character three times -- the real one (photo), the photo with our stroke
    centre lines on it, and our relief as the atlas has it -- 9 a row."""
    def norm(a):
        lo, hi = np.percentile(a, 1), np.percentile(a, 99.5)
        return np.clip((a - lo) / (hi - lo + 1e-6), 0, 1)
    Z = 1.0
    cells = []
    for i in range(N_INSC):
        ph = Image.fromarray((norm(crops[i]) * 255).astype(np.uint8)).convert('RGB')
        ov = ph.copy(); d = ImageDraw.Draw(ov)
        for pl in traces[i]:
            d.line([(x * 10, y * 10) for x, y in pl], fill=(200, 30, 30), width=3, joint='curve')
        r, c = divmod(i, 8)
        g = G[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128]
        sh = relief_shade(g)
        tone = np.array([0.84, 0.80, 0.70])
        rl = Image.fromarray((sh[..., None] * tone * 255).astype(np.uint8)).resize((190, 190), Image.LANCZOS)
        col = Image.new('RGB', (190, 168 * 2 + 190 + 8), 'white')
        col.paste(ph, (0, 0)); col.paste(ov, (0, 168 + 4)); col.paste(rl, (0, 2 * 168 + 8))
        dd = ImageDraw.Draw(col); dd.text((4, 4), '#%d' % i, fill=(255, 220, 0))
        cells.append(col)
    per = 9
    rows = (len(cells) + per - 1) // per
    sheet = Image.new('RGB', (per * 196, rows * (cells[0].height + 14)), 'white')
    for i, cimg in enumerate(cells):
        sheet.paste(cimg, ((i % per) * 196, (i // per) * (cells[0].height + 14)))
    sheet.save(os.path.join(DOC, 'inscription_plate.png'), optimize=True)



def back_cell(centre_boss):
    H = np.zeros((M, M), np.float32)
    lines = Layer()     # 0.25 relief lines and bands
    fine = Layer()      # 0.12 fine-line relief (spirits, clouds)
    # --- knob seat: four pointed petals toward the square's corners (柿蒂), r 0.065 .. 0.23 ---------------------
    for k in range(4):
        a = math.pi / 4 + k * math.pi / 2
        tip = rot((0.0, 0.23), -a); l = rot((-0.07, 0.10), -a); r = rot((0.07, 0.10), -a)
        lines.poly([rot((0, 0.06), -a), l, tip, r])
    # --- inner square (half side 0.21) and the 12-boss / 12-branch band, outer double frame 0.37 / 0.40 --------
    def square(h, w, layer):
        layer.line([(-h, -h), (h, -h), (h, h), (-h, h), (-h, -h)], w)
    square(0.21, 0.012, lines)
    square(0.37, 0.016, lines)
    square(0.40, 0.022, lines)
    hb = 0.29                                                   # middle of the band (half side)
    small = []
    for k in range(12):                                         # bosses at bearings 15 + 30 k (corners included at 45)
        b = math.radians(15 + 30 * k + 30)
        s, c = math.sin(b), math.cos(b)
        m = max(abs(s), abs(c))
        small.append((hb * s / m, hb * c / m))
    small = [(x, y) for (x, y) in small]
    # 4 per side incl. corners: positions on each side at -1, -1/3, 1/3, 1 of the half side
    small = []
    for k in range(4):
        for t in (-1.0, -1 / 3, 1 / 3):
            small.append(rot((t * hb, hb), -k * math.pi / 2))
    Hs = dome((M, M), small, 0.032)
    Hseat = Layer()
    for c in small:
        Hseat.ring(c, 0.045, 0.006)
    # the twelve branch characters: none drawn here, the photo field (r/R 0.15 .. 0.72) carries 1995.301's own
    # --- T, L, V (C4; the L's all turn the same way) ---------------------------------------------------------------
    def tlv(R, k):
        lines.line([R((0, 0.40)), R((0, 0.47))], 0.028)                  # T stem
        lines.line([R((-0.075, 0.47)), R((0.075, 0.47))], 0.028)         # T bar
        lines.line([R((-0.08, 0.70)), R((0.06, 0.70))], 0.028)           # L along the outer circle
        lines.line([R((0.06, 0.70)), R((0.06, 0.62))], 0.028)            # L foot inward (same hand on all four)
        d = lambda p: rot(p, -math.pi / 4)                               # V on the diagonal (tip toward the corner)
        tip = d(R((0, 0.58)))
        lines.line([d(R((-0.06, 0.69))), tip, d(R((0.06, 0.69)))], 0.026)
    C4(tlv)
    # --- 8 bosses with eight-point star seats and a ring, +-20 deg of each T axis at r 0.53 -------------------------
    big8 = []
    seat = Layer()
    for k in range(4):
        for sgn in (-1, 1):
            a = -k * math.pi / 2 + sgn * math.radians(21)
            c = rot((0, 0.53), a)
            big8.append(c)
            seat.ring(c, 0.085, 0.010)
            for j in range(8):
                aa = j * math.pi / 4
                tip = (c[0] + 0.075 * math.sin(aa), c[1] + 0.075 * math.cos(aa))
                l = (c[0] + 0.04 * math.sin(aa - 0.35), c[1] + 0.04 * math.cos(aa - 0.35))
                r = (c[0] + 0.04 * math.sin(aa + 0.35), c[1] + 0.04 * math.cos(aa + 0.35))
                seat.poly([l, tip, r, c])
    Hb = dome((M, M), big8, 0.042, 0.8)
    if centre_boss:
        Hb = np.maximum(Hb, dome((M, M), [(0, 0)], 0.065, 0.8))
    # --- four spirits (fine line), one per quadrant around each axis: north 玄武, east 青龙, south 朱雀, west 白虎 ---
    def creature(R, k):
        side = 1
        if k == 0:      # 玄武: turtle (oval shell with hex lines) + the snake coiling round it
            c = (0.17, 0.62)
            for j in range(26):
                a0 = 2 * math.pi * j / 26; a1 = 2 * math.pi * (j + 1) / 26
                fine.line([R((c[0] + 0.07 * math.cos(a0), c[1] + 0.045 * math.sin(a0))), R((c[0] + 0.07 * math.cos(a1), c[1] + 0.045 * math.sin(a1)))], 0.010)
            fine.line([R(p) for p in bezier((0.07, 0.62), (0.11, 0.70), (0.25, 0.71), (0.27, 0.62))], 0.010)
            fine.line([R(p) for p in bezier((0.25, 0.60), (0.32, 0.52), (0.12, 0.50), (0.09, 0.57))], 0.011)
            fine.line([R((0.24, 0.62)), R((0.30, 0.64))], 0.012)
        elif k == 1:    # 青龙: long S body, head with horn, two legs, tail curl
            body = bezier((0.08, 0.58), (0.14, 0.70), (0.24, 0.50), (0.31, 0.63))
            fine.line([R(p) for p in body], 0.018)
            fine.line([R(p) for p in spiral((0.06, 0.56), 0.03, 1.2, -1)], 0.009)
            fine.line([R((0.31, 0.63)), R((0.35, 0.66)), R((0.33, 0.70))], 0.011)
            fine.line([R((0.33, 0.66)), R((0.37, 0.70))], 0.008)
            for (a, b) in (((0.15, 0.62), (0.15, 0.55)), ((0.25, 0.56), (0.27, 0.49))):
                fine.line([R(a), R(b), R((b[0] + 0.02, b[1] - 0.01))], 0.009)
        elif k == 2:    # 朱雀: bird, raised wings, long fanned tail
            fine.line([R(p) for p in bezier((0.14, 0.56), (0.18, 0.66), (0.26, 0.66), (0.29, 0.58))], 0.016)
            fine.line([R((0.29, 0.58)), R((0.33, 0.63)), R((0.36, 0.61))], 0.010)
            for j in range(4):
                fine.line([R(p) for p in bezier((0.20, 0.64), (0.20 - 0.02 * j, 0.70), (0.26 - 0.03 * j, 0.73), (0.28 - 0.035 * j, 0.70))], 0.008)
            for j in range(3):
                fine.line([R(p) for p in bezier((0.14, 0.56), (0.10, 0.53 + 0.03 * j), (0.07, 0.60 + 0.02 * j), (0.08, 0.66 + 0.015 * j))], 0.008)
        else:           # 白虎: crouching body, striped, tail raised
            fine.line([R(p) for p in bezier((0.10, 0.57), (0.16, 0.64), (0.25, 0.64), (0.30, 0.58))], 0.020)
            fine.line([R((0.30, 0.58)), R((0.34, 0.62)), R((0.36, 0.59))], 0.012)
            for j in range(5):
                x = 0.15 + 0.03 * j
                fine.line([R((x, 0.64)), R((x + 0.01, 0.60))], 0.006)
            fine.line([R(p) for p in spiral((0.08, 0.63), 0.035, 1.0, 1)], 0.009)
            for (a, b) in (((0.13, 0.58), (0.12, 0.52)), ((0.27, 0.59), (0.29, 0.53))):
                fine.line([R(a), R(b)], 0.009)
        # companion on the other side of the axis: a 羽人 / small bird among cloud scrolls (mirror-free: same hand)
        fine.line([R((-0.30, 0.58)), R((-0.24, 0.63)), R((-0.20, 0.60))], 0.010)
        fine.line([R(p) for p in spiral((-0.17, 0.66), 0.035, 1.3, 1)], 0.008)
        fine.line([R(p) for p in spiral((-0.29, 0.66), 0.03, 1.1, -1)], 0.008)
        fine.line([R(p) for p in bezier((-0.13, 0.57), (-0.10, 0.62), (-0.14, 0.66), (-0.11, 0.69))], 0.008)
    C4(creature)
    # --- outer circle of the main field (r 0.72) and the corner fill so the cell tiles ------------------------------
    lines.ring((0, 0), 0.72, 0.012)
    # the corners between the inscribed mirrors (review r3 #7): no random hooks.  One ornament, identical at every
    # corner (translation only, so the cell tiles): the corner boss, two rings, a closed stem round it with eight
    # C-curls turning alternately in and out, and four S-tendrils running into the cusps between the mirrors, all
    # strokes tapering head to tail (Han cloud-scroll drawing).
    def taper(pts, w0, w1, layer):
        n = len(pts) - 1
        for j in range(n):
            w = w0 + (w1 - w0) * (j + 0.5) / n
            layer.line([pts[j], pts[j + 1]], w)
    def corner(cx, cy):
        fine.ring((cx, cy), 0.095, 0.012)
        fine.ring((cx, cy), 0.30, 0.011)
        stem = [(cx + 0.20 * math.cos(2 * math.pi * j / 160), cy + 0.20 * math.sin(2 * math.pi * j / 160)) for j in range(161)]
        taper(stem, 0.010, 0.010, fine)
        for j in range(8):
            a = 2 * math.pi * j / 8 + math.pi / 8
            sgn = 1 if j % 2 else -1                                   # in / out
            p0 = (cx + 0.20 * math.cos(a), cy + 0.20 * math.sin(a))
            tang = (-math.sin(a), math.cos(a)); rad = (math.cos(a), math.sin(a))
            p1 = (p0[0] + 0.035 * tang[0] + sgn * 0.03 * rad[0], p0[1] + 0.035 * tang[1] + sgn * 0.03 * rad[1])
            c = (p0[0] + 0.05 * tang[0] + sgn * 0.055 * rad[0], p0[1] + 0.05 * tang[1] + sgn * 0.055 * rad[1])
            arm = bezier(p0, p1, (c[0] - 0.02 * tang[0], c[1] - 0.02 * tang[1]), (c[0] - 0.025 * rad[0] * sgn, c[1] - 0.025 * rad[1] * sgn), 16)
            curl = spiral(c, 0.025, 1.15, sgn, 30)
            taper(arm + curl[1:], 0.010, 0.0035, fine)
        for (dx, dy) in ((1, 0), (-1, 0), (0, 1), (0, -1)):        # same four at every corner: the cell tiles
            pts = []
            for j in range(41):
                t = j / 40.0
                d = 0.31 + 0.34 * t                                    # along the edge, into the cusp
                half = math.hypot(1.0, 1.0 - d) - 1.0                  # half-width of the cusp between two mirrors
                amp = 0.55 * half * math.sin(2 * math.pi * 1.5 * t)
                pts.append((cx + dx * d - dy * amp, cy + dy * d + dx * amp))
            taper(pts, 0.010, 0.003, fine)
            taper(spiral(pts[-1], 0.018, 1.0, 1, 20), 0.004, 0.0025, fine)
    for cx in (-1, 1):
        for cy in (-1, 1):
            corner(cx, cy)
    Hc = dome((M, M), [(1, 1)], 0.05, 0.8)
    # --- combine ----------------------------------------------------------------------------------------------
    H = np.maximum(H, lines.arr(1.2 * SS) * 0.25)
    H = np.maximum(H, seat.arr(1.0 * SS) * 0.30)
    H = np.maximum(H, Hseat.arr(1.0 * SS) * 0.2)
    H = np.maximum(H, fine.arr(1.0 * SS) * 0.13)
    H = np.maximum(H, Hs * 0.45)
    H = np.maximum(H, Hb * 1.0)
    H = np.maximum(H, Hc * 0.7)
    # downsample to N
    H = H.reshape(N, SS, N, SS).mean((1, 3))
    return H


PHOTO = os.path.join(ROOT, 'Docs~', '实物参考_博局镜', 'CMA_1995.301.jpg')   # Cleveland Museum of Art 1995.301, CC0
PHOTO_C = (1714.0, 1641.0, 1320.0)                                              # mirror centre x, y and radius in the photo (fitted)
# the photo's own bosses (read off the photo, px): the relief clip would press them into flat coins (r3 A7), so each
# gets back a dome of its real size
_K = 3400.0 / 1100.0
PHOTO_BOSS_BIG = [(x * _K, y * _K) for x, y in ((483, 348), (619, 348), (358, 473), (740, 473), (360, 607), (740, 607), (480, 730), (620, 730))]
PHOTO_BOSS_SMALL = [(x * _K, y * _K) for x, y in ((437, 428), (512, 428), (587, 428), (660, 428), (437, 505), (660, 505),
                                                   (437, 578), (660, 578), (437, 652), (512, 652), (590, 652), (660, 652))]


def photo_field(n=N):
    """the back (r/R 0.15 .. 0.985: field, inscription-free 1995.301's comb, sawtooth and cloud bands) of a real 四神博局镜 as a relief layer: luminance, the museum lighting and the
    patina blotches removed with a large high-pass and a local contrast normalisation (the photo is CC0: 小楠 10-24,
    '并不是参考，如果合适直接用')."""
    from scipy.ndimage import map_coordinates
    im = np.asarray(Image.open(PHOTO).convert('RGB'), np.float32) / 255.0
    L = im @ np.array([0.2126, 0.7152, 0.0722], np.float32)
    hp = L - gaussian_filter(L, 18)
    sd = np.sqrt(gaussian_filter(hp * hp, 40)) + 1e-3
    rel = np.clip(hp / sd / 2.5, -1, 1)
    cx, cy, r = PHOTO_C
    yy, xx = np.mgrid[0:n, 0:n].astype(np.float32)
    k = r / (n / 2.0)
    px = cx + (xx + 0.5 - n / 2.0) * k
    py = cy + (yy + 0.5 - n / 2.0) * k
    f = map_coordinates(rel, [py, px], order=1, mode='nearest')
    q = np.hypot(xx + 0.5 - n / 2.0, yy + 0.5 - n / 2.0) / (n / 2.0)
    w = np.clip((q - 0.15) / 0.04, 0, 1) * np.clip((0.985 - q) / 0.02, 0, 1)   # the whole real back out to its rim (r3 #7)
    return np.clip(0.5 + 0.5 * f, 0, 1), w


RIM_C = (1725.4, 1653.9, 1320.0)        # 1995.301 centre refitted on the rim band's own edge line (the field's PHOTO_C is
                                        # 12 px off for the outer rim)
RIM_Q = (1.0 - 0.25 * 92 / 329, 1.0 - 0.25 * 273 / 329)   # the 流云纹 band: outer .. inner edge, r/R 0.930 .. 0.793
RIM_UNITS = 15                          # the real band has 15 wave units (one up-scroll + one down-scroll) round the rim
RIM_X0 = 470 / 8000.0                   # the tile starts here (fraction of the turn from the top, clockwise): the cleanest
                                        # stretch of the band that is still level (perspective + corrosion elsewhere)


def photo_rim_cloud(w=2048, h=256):
    """the rim's 流云纹 band of 1995.301, unwrapped, two wave units as a seamless strip (Repeat in u): relief by the same
    band-pass + local normalisation as the field.  Also returns tile length / band height for the shader."""
    from scipy.ndimage import map_coordinates
    L = np.asarray(Image.open(PHOTO).convert('L'), np.float32) / 255.0
    cx, cy, R = RIM_C
    P = 2.0 / RIM_UNITS                                        # tile = 2 units (fraction of the turn)
    D = 64.0 / w * P                                           # seam cross-fade
    u = np.linspace(0.0, P, w, endpoint=False)
    def sample(u):
        th = -np.pi / 2 + 2 * np.pi * (RIM_X0 + u)
        q = np.linspace(RIM_Q[0], RIM_Q[1], h)                  # row 0 = outer (image top = band outer edge)
        T, Q = np.meshgrid(th, q)
        return map_coordinates(L, [cy + R * Q * np.sin(T), cx + R * Q * np.cos(T)], order=1)
    a0, a1 = sample(u), sample(u + P)
    wgt = np.clip(u / D, 0, 1)[None, :]
    tile = wgt * a0 + (1 - wgt) * a1                           # continuous across the wrap
    t3 = np.concatenate([tile] * 3, 1)
    hp = t3 - gaussian_filter(t3, 18 * h / 181.0)
    sd = np.sqrt(gaussian_filter(hp * hp, 40 * h / 181.0)) + 1e-3
    rel = np.clip(hp / sd / 2.5, -1, 1)[:, w:2 * w]
    qm = 0.5 * (RIM_Q[0] + RIM_Q[1])
    aspect = (P * 2 * np.pi * qm) / (RIM_Q[0] - RIM_Q[1])
    hgt = np.clip((rel + 0.6) / 1.5, 0, 1)
    return hgt * hgt * (3 - 2 * hgt), aspect


def periodic_noise(n, period_px, seed):
    rng = np.random.default_rng(seed)
    f = np.fft.fft2(rng.standard_normal((n, n)))
    ky = np.fft.fftfreq(n)[:, None]; kx = np.fft.fftfreq(n)[None, :]
    k = np.sqrt(kx * kx + ky * ky) * period_px
    a = np.real(np.fft.ifft2(f * np.exp(-k * k)))
    a -= a.mean(); a /= a.std() + 1e-9
    return a


def maps_from_height(H):
    # normal (OpenGL: green = +v = up in the image)
    s = RELIEF_M / PX_M
    gy, gx = np.gradient(gaussian_filter(H, 0.7, mode='wrap'))
    dhdu = gx * s
    dhdv = -gy * s                                # row grows downward = v decreases
    nz = 1.0 / np.sqrt(1 + dhdu ** 2 + dhdv ** 2)
    nx, ny = -dhdu * nz, -dhdv * nz
    nrm = np.stack([nx * 0.5 + 0.5, ny * 0.5 + 0.5, nz * 0.5 + 0.5], -1)
    # AO / cavity and worn ridges
    big = gaussian_filter(H, 6.0, mode='wrap')
    ao = np.clip(1.0 - 2.2 * np.clip(big - H, 0, None) - 0.15 * np.clip(gaussian_filter(H, 18, mode='wrap') - H, 0, None), 0.35, 1)
    worn = np.clip((H - gaussian_filter(H, 3.0, mode='wrap')) * 6.0 + (H > 0.6) * 0.5, 0, 1)
    pat = np.clip(0.5 + 0.22 * periodic_noise(N, 220, 3) + 0.10 * periodic_noise(N, 60, 4), 0, 1)
    mask = np.stack([np.clip(H, 0, 1), ao, worn, pat], -1)
    return nrm, mask


def save(arr, name):
    im = Image.fromarray((np.clip(arr, 0, 1) * 255 + 0.5).astype(np.uint8))
    im.save(os.path.join(OUT, name), optimize=True)
    return im


def shade(H, light=(-0.6, 0.5, 0.45)):
    s = RELIEF_M / PX_M
    gy, gx = np.gradient(H)
    n = np.stack([-gx * s, gy * s, np.ones_like(H)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array(light); L = L / np.linalg.norm(L)
    return np.clip(n @ L, 0, 1)


def main():
    previews = []
    pf, pw = photo_field()
    for centre, tag in ((True, ''), (False, 'Centre')):
        H = back_cell(centre_boss=centre)
        # the real mirror's field replaces the procedural one inside r/R 0.15 .. 0.72 (relief 0..0.5: its bosses and
        # lines stand out of the field as in the photo); the procedural cell keeps the seat, the corners and the tiling
        H = H * (1 - pw) + np.clip((pf - 0.45) * 0.9, 0, 0.5) * pw    # the field sits at 0 like the rest of the cell
        cx, cy, r = PHOTO_C
        uv = lambda pts: [((x - cx) / r, -(y - cy) / r) for x, y in pts]
        Hd = np.maximum(dome((M, M), uv(PHOTO_BOSS_BIG), 0.034, 0.8) * 0.9, dome((M, M), uv(PHOTO_BOSS_SMALL), 0.026, 0.8) * 0.65)
        Hd = Hd.reshape(N, SS, N, SS).mean((1, 3))
        H = np.maximum(H, Hd)                                          # round bosses with a real highlight (A7)
        nrm, mask = maps_from_height(H)
        pre = 'T_MirrorBack_' + (tag + '_' if tag else '')
        save(nrm, pre + 'Normal_2048.png')
        save(mask, pre + 'Mask_2048.png')
        previews.append((tag or 'cell', H, mask))
        print('back', tag or 'cell', 'height max %.2f' % H.max())
    # face texture: low-frequency, subtle
    fr = np.clip(0.5 + 0.18 * periodic_noise(N, 300, 11) + 0.06 * periodic_noise(N, 40, 12), 0, 1)
    fg = np.clip(0.5 + 0.20 * periodic_noise(N, 400, 13), 0, 1)
    sc = Layer()
    rng = np.random.default_rng(14)
    for _ in range(70):
        c = (rng.uniform(-0.9, 0.9), rng.uniform(-0.9, 0.9)); a = rng.uniform(0, math.pi); L = rng.uniform(0.05, 0.4)
        sc.line([(c[0] - L * math.cos(a), c[1] - L * math.sin(a)), (c[0] + L * math.cos(a), c[1] + L * math.sin(a))], 0.0015, val=int(rng.uniform(60, 200)))
    fb = sc.arr(0.6).reshape(N, SS, N, SS).mean((1, 3))
    fa = np.clip((periodic_noise(N, 160, 15) - 0.9) * 0.8, 0, 1)
    save(np.stack([fr, fg, fb, fa], -1), 'T_MirrorFace_2048.png')
    # rim cloud band (1995.301)
    rc, rc_aspect = photo_rim_cloud()
    Image.fromarray((rc * 255 + 0.5).astype(np.uint8)).save(os.path.join(OUT, 'T_MirrorRimCloud_2048x256.png'), optimize=True)
    print('rim cloud strip: tile length / band height = %.3f (LM_CLOUD_ASPECT)' % rc_aspect)
    # glyph atlas 8 x 8 x 128 px: the 35 traced inscription characters (1995.298); the twelve branches are in the
    # photo field itself (1995.301), not in the atlas
    G = np.zeros((1024, 1024), np.float32)
    traces, im_crops = photo_inscription()
    for i, polys in enumerate(traces):
        r, c = divmod(i, 8)
        G[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128] = traced_glyph(polys, 128)
    Image.fromarray((G * 255).astype(np.uint8)).save(os.path.join(OUT, 'T_MirrorGlyphs_1024.png'), optimize=True)
    inscription_plate(im_crops, traces, G)
    # preview: shaded cell, 3x3 tiling, mask channels, glyphs
    Hc = previews[0][1]
    sh = shade(Hc)
    small = np.asarray(Image.fromarray((sh * 255).astype(np.uint8)).resize((768, 768), Image.LANCZOS))
    tiled = np.tile(np.asarray(Image.fromarray((sh * 255).astype(np.uint8)).resize((256, 256), Image.LANCZOS)), (3, 3))
    cen = np.asarray(Image.fromarray((shade(previews[1][1]) * 255).astype(np.uint8)).resize((768, 768), Image.LANCZOS))
    gl = np.asarray(Image.fromarray((G * 255).astype(np.uint8)).resize((768, 768), Image.LANCZOS))
    sheet = np.concatenate([np.concatenate([cen, small], 1), np.concatenate([tiled, gl], 1)], 0)
    Image.fromarray(sheet).save(os.path.join(DOC, 'textures_preview.png'))
    print('done')


if __name__ == '__main__':
    main()
