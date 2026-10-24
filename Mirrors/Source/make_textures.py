"""蓝白 · 白铜镜贴图（spec_conventions.md §2、§4、§5）。确定性：同样的代码出同样的图。

    ~/bpy/bin/python make_textures.py            -> Mirrors/Textures/*.png + Docs~/textures_preview.png

镜背一格 = 40 m 的博局（第 1 面镜 R = 20 m 正好一格）。格坐标 u 向东（物体 +X）、v 向北（物体 +Z），
图像第 0 行在顶上（v = 1），Unity 采样时 v = 0 在底：所以 row = (1 - v) * N。
构图照真镜（克利夫兰 1995.301 等，Docs~/实物参考_博局镜/）：钮座四叶 → 内方框 → 十二乳与十二地支（每边 4 乳 3 字，
角上的乳两边共用）→ 双线外方框 → T、L、V → 八乳（八瓣星形座 + 圆座）→ 四神细线 + 云气纹。
"""
import math, os
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter
from scipy.ndimage import gaussian_filter, maximum_filter, minimum_filter, distance_transform_edt

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
REPO = os.path.dirname(ROOT)
OUT = os.path.join(ROOT, 'Textures')
DOC = os.path.join(ROOT, 'Docs~')
os.makedirs(OUT, exist_ok=True)
FONT = os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Medium.otf')

N = 2048                  # output
SS = 2                    # supersampling for drawing
M = N * SS
TILE_M = 40.0
R_PX = M / 2.0            # canonical mirror radius (20 m) in canvas px
PX_M = TILE_M / N         # metres per output pixel
RELIEF_M = 0.016 * 40.0   # height 1.0 = 0.64 m (8 bosses)

INSCRIPTION = '尚方作竟真大巧上有仙人不知老渴饮玉泉饥食枣浮游天下敖四海寿如金石为国保'
BRANCHES = '子丑寅卯辰巳午未申酉戌亥'
assert len(INSCRIPTION) == 35, len(INSCRIPTION)


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


def glyph_img(ch, px, heavy=True):
    """one character, squared toward Han mirror script: bold, square strokes, square terminals."""
    big = px * 4
    im = Image.new('L', (big, big), 0)
    f = ImageFont.truetype(FONT, int(big * 0.86))
    d = ImageDraw.Draw(im)
    bb = d.textbbox((0, 0), ch, font=f)
    w, h = bb[2] - bb[0], bb[3] - bb[1]
    # stretch to fill a near-square cell (mirror script fills its box)
    tmp = Image.new('L', (w + 8, h + 8), 0)
    ImageDraw.Draw(tmp).text((4 - bb[0], 4 - bb[1]), ch, font=f, fill=255)
    tmp = tmp.resize((int(big * 0.84), int(big * 0.84)), Image.LANCZOS)
    im.paste(tmp, ((big - tmp.width) // 2, (big - tmp.height) // 2))
    a = np.asarray(im, np.float32) / 255.0
    a = (a > 0.45).astype(np.float32)
    # square the strokes: max over a square then min over a slightly smaller square (blocky, even weight)
    k = max(5, big // 22)
    a = minimum_filter(maximum_filter(a, size=k + 2), size=k)
    a = gaussian_filter(a, big / 220)
    out = Image.fromarray((np.clip(a, 0, 1) * 255).astype(np.uint8)).resize((px, px), Image.LANCZOS)
    return np.asarray(out, np.float32) / 255.0


def paste_glyph(H, ch, c, size, ang, val):
    """paste a glyph (size in canonical-R units) centred at c, top of the glyph toward angle ang (radians, 0 = north)."""
    px = int(size * R_PX)
    g = glyph_img(ch, px)
    im = Image.fromarray((g * 255).astype(np.uint8)).rotate(math.degrees(ang), resample=Image.BICUBIC, expand=True)
    g = np.asarray(im, np.float32) / 255.0
    x, y = P(*c)
    x0, y0 = int(x - g.shape[1] / 2), int(y - g.shape[0] / 2)
    sl = H[y0:y0 + g.shape[0], x0:x0 + g.shape[1]]
    H[y0:y0 + g.shape[0], x0:x0 + g.shape[1]] = np.maximum(sl, g[:sl.shape[0], :sl.shape[1]] * val)


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
    # branch characters at 0, +-2/3 of each side, top of the glyph toward the outside
    for k in range(4):
        for j, t in enumerate((-2 / 3, 0.0, 2 / 3)):
            idx = (k * 3 + j - 1) % 12                         # 子 in the middle of the north side, clockwise
            c = rot((t * hb, hb), -k * math.pi / 2)
            paste_glyph(H, BRANCHES[idx], c, 0.085, -k * math.pi / 2, 0.22)
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
    def corner(cx, cy):
        # cloud scrolls and a boss round the cell corner (shared by four cells)
        for j in range(8):
            a = j * math.pi / 4 + math.pi / 8
            c = (cx + 0.18 * math.cos(a), cy + 0.18 * math.sin(a))
            fine.line([(lambda p: p)(p) for p in spiral(c, 0.05, 1.2, 1 if j % 2 else -1)], 0.009)
        fine.ring((cx, cy), 0.10, 0.012)
        fine.ring((cx, cy), 0.28, 0.010)
    for cx in (-1, 1):
        for cy in (-1, 1):
            corner(cx, cy)
    Hc = dome((M, M), [(1, 1)], 0.05, 0.8)
    # --- 云气纹 fill: the real mirrors' field is dense with scrolls (克利夫兰 1995.301); fill every free gap --------
    occ = np.maximum.reduce([lines.arr(), seat.arr(), Hseat.arr(), fine.arr(), (Hs > 0).astype(np.float32),
                             (Hb > 0).astype(np.float32), (Hc > 0).astype(np.float32), (H > 0.02).astype(np.float32)])
    occ = occ.reshape(512, M // 512, 512, M // 512).max((1, 3)) > 0.05
    cell = M / 512 / R_PX                                        # canonical units per occupancy cell
    free = distance_transform_edt(~occ) * cell                   # distance to the nearest feature
    rng = np.random.default_rng(7)
    placed = 0
    for _ in range(6000):
        u, v = rng.uniform(-1, 1, 2)
        r = math.hypot(u, v)
        inner = r < 0.70
        size = rng.uniform(0.035, 0.055) if inner else rng.uniform(0.05, 0.08)
        if (0.69 < r < 0.75) or (inner and r < 0.42):
            continue
        iy = int((1 - (v + 1) / 2) * 511); ix = int((u + 1) / 2 * 511)
        if free[iy, ix] < size * 1.15:
            continue
        a = rng.uniform(0, 2 * math.pi)
        ccw = 1 if rng.random() < 0.5 else -1
        # a C / S scroll: a short arc ending in a spiral, the other end a hook
        p0 = (u - size * math.cos(a), v - size * math.sin(a)); p3 = (u + size * math.cos(a), v + size * math.sin(a))
        mid = (u + 0.6 * size * math.cos(a + ccw * math.pi / 2), v + 0.6 * size * math.sin(a + ccw * math.pi / 2))
        fine.line(bezier(p0, mid, mid, p3, 20), 0.008)
        fine.line(spiral(p3, size * 0.45, 1.1, ccw, 40), 0.008)
        if rng.random() < 0.5:
            fine.line(spiral(p0, size * 0.3, 0.8, -ccw, 30), 0.007)
        # mark occupied
        yy0 = max(0, iy - int(size * 1.6 / cell)); yy1 = min(512, iy + int(size * 1.6 / cell) + 1)
        xx0 = max(0, ix - int(size * 1.6 / cell)); xx1 = min(512, ix + int(size * 1.6 / cell) + 1)
        free[yy0:yy1, xx0:xx1] = 0
        placed += 1
    print('cloud scrolls placed', placed)
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


def photo_field(n=N):
    """the main field (r/R 0.15 .. 0.72) of a real 四神博局镜 as a relief layer: luminance, the museum lighting and the
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
    w = np.clip((q - 0.15) / 0.04, 0, 1) * np.clip((0.73 - q) / 0.04, 0, 1)
    return np.clip(0.5 + 0.5 * f, 0, 1), w


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
    # glyph atlas 8 x 8 x 128 px: inscription 0..34, branches 35..46
    G = np.zeros((1024, 1024), np.float32)
    for i, ch in enumerate(INSCRIPTION + BRANCHES):
        g = glyph_img(ch, 112)
        r, c = divmod(i, 8)
        G[r * 128 + 8:r * 128 + 120, c * 128 + 8:c * 128 + 120] = g
    Image.fromarray((G * 255).astype(np.uint8)).save(os.path.join(OUT, 'T_MirrorGlyphs_1024.png'), optimize=True)
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
