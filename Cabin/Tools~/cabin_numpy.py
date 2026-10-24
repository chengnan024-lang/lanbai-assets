#!/usr/bin/env python3
# =====================================================================================================
#  Cabin/Tools~/cabin_numpy.py   蓝白 · Lanbai/Cabin 的颜色数学的 numpy 版（与 LanbaiCabinCommon.cginc 1:1）
#
#  Ports: tube LM term, cabin ambient x AO, bleach, erosion threshold (prose / literal) + noise remap + 3 cm rim,
#  seat sphere / floor patch / D-26 hole, D-08 wound-light limiter and the D-21 band guard (CIE Lab, D65).
#  Self-test (python3 Cabin/Tools~/cabin_numpy.py): asserts + writes PNGs into Cabin/Docs~/:
#    swatch_d08_limiter.png    cabin surfaces under the raw wound light vs. the limited one (+ Lab numbers)
#    swatch_bleach.png         each surface at bleach 0 / 0.10 / 0.25 / 0.5 / 0.8 / 1 under the act's ambient
#    curve_cabin_timeline.png  tubes / bleach / fade / hole curves of LanbaiCabinDriver over t
#    erosion_zones.png         eroded fraction per cabin zone vs. fade, prose and literal forms
#    erosion_floor_d26.png     plan view of the floor at 897.96 (D-26 hole, floor patch, seat sphere)
#  and prints erosion_zones as a table (the README copies it).
#  Only numpy + PIL. No rendering. Colour = linear sRGB; PNGs are sRGB-encoded clamps (swatches, not tonemapped).
# =====================================================================================================
import os
import sys
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.normpath(os.path.join(HERE, '..', 'Docs~'))

# ---------------------------------------------------------------------------------------------------
# material defaults (= the shader Properties)
ERODE_COEF = (0.45, 0.25, 0.35, 0.8)
ERODE_NOISE = (0.55, 0.30, 0.70, 0.03)        # patch m, uniformise lo, hi, rim m
NOISE_RANGE = (-0.20, 0.25)
CABIN_BOX = (0.62, 2.62, -3.65, 3.50)
SKY_RECT = (0.55, 2.62, 2.80, 0.30)
SEAT_SPHERE = (0.55, 1.05, 2.05, 0.9)
FLOOR_PATCH = (-0.16, 1.04, 0.85, 2.45)
HOLE_FULL = (0.55, 2.925, 0.45, 0.475)
HOLE_MIN = (0.55, 3.04, 0.30, 0.26)
HOLE_SHAPE = (0.22, 0.10, 0.70)
DOOR_BOX_MIN = (0.80, 0.45, 2.38, 0.15)       # D-33 #7a: xyz min, w soft margin
DOOR_BOX_MAX = (1.60, 3.00, 3.45)


def srgb2lin(h):
    if isinstance(h, str):
        c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])
    else:
        c = np.asarray(h, float)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def lin2srgb(c):
    c = np.clip(np.asarray(c, float), 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def luma(c):
    return np.tensordot(np.asarray(c, float), [0.2126, 0.7152, 0.0722], axes=([-1], [0]))


# ---------------------------------------------------------------------------------------------------
# Lab (same constants as the shader)
M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
MI = np.array([[3.2406, -1.5372, -0.4986], [-0.9689, 1.8758, 0.0415], [0.0557, -0.2040, 1.0570]])
WP = np.array([0.95047, 1.0, 1.08883])


def lin2lab(c):
    X = np.maximum(np.asarray(c, float) @ M.T / WP, 0)
    f = np.where(X > 0.008856, np.cbrt(X), 7.787 * X + 16 / 116)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def lab2lin(lab):
    lab = np.asarray(lab, float)
    fy = (lab[..., 0] + 16) / 116
    f = np.stack([fy + lab[..., 1] / 500, fy, fy - lab[..., 2] / 200], -1)
    X = np.where(f > 0.206893, f ** 3, (f - 16 / 116) / 7.787) * WP
    return np.maximum(X @ MI.T, 0)


def lch(c):
    lab = lin2lab(c)
    return lab[..., 0], np.hypot(lab[..., 1], lab[..., 2]), np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360


def smoothstep(a, b, x):
    t = np.clip((np.asarray(x, float) - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def purple_band(c):
    """D-21: only h 290-330, C* > 8, L* > 40 -> C* 8 (soft 2 deg / 2 L*)."""
    lab = lin2lab(c)
    C = np.hypot(lab[..., 1], lab[..., 2])
    h = np.degrees(np.arctan2(lab[..., 2], lab[..., 1])) % 360
    w = smoothstep(288, 292, h) * (1 - smoothstep(328, 332, h)) * smoothstep(38, 42, lab[..., 0])
    Ct = C + (np.minimum(C, 8) - C) * w
    k = np.where(C > 1e-4, Ct / np.maximum(C, 1e-4), 0)
    lab = lab.copy()
    lab[..., 1] *= k
    lab[..., 2] *= k
    return lab2lin(lab)


def wound_light_limit(lc):
    """D-08 on the wound light's colour (scale invariant at Y 0.5): C* <= 12, hue in 290-330 pulled to 290."""
    lc = np.asarray(lc, float)
    Y = luma(lc)
    lab = lin2lab(lc * (0.5 / Y))
    C = np.hypot(lab[1], lab[2])
    h = np.degrees(np.arctan2(lab[2], lab[1])) % 360
    pull = smoothstep(288, 292, h) * (1 - smoothstep(338, 342, h))
    hn = h + (290 - h) * pull * np.clip((h - 290) / 2 + 0.5, 0, 1)
    Cn = min(C, 12.0)
    r = np.radians(hn)
    out = lab2lin(np.array([lab[0], np.cos(r) * Cn, np.sin(r) * Cn]))
    return out * (Y / 0.5)


# ---------------------------------------------------------------------------------------------------
# light terms
def cabin_diffuse(albedo, lm_rgb, lm_on, ambient, ao, metallic=0.0):
    """albedo x (LM.rgb x _Udon_CabinLightmap + _Udon_CabinAmbient x AO), diffuse part (1 - 0.96 metallic)."""
    return np.asarray(albedo) * (1 - 0.96 * metallic) * (np.asarray(lm_rgb) * lm_on + np.asarray(ambient) * ao)


def bleach_albedo(albedo, bleach, ambient):
    amb = np.maximum(np.asarray(ambient, float), 0)
    la = luma(amb)
    tint = amb / la if la > 1e-5 else np.ones(3)
    tint = np.minimum(tint, 1.6)
    target = luma(albedo) * 0.9 * tint
    return np.asarray(albedo) + (target - np.asarray(albedo)) * np.clip(bleach, 0, 1)


# ---------------------------------------------------------------------------------------------------
# FBM (the shader's LanbaiHash13 + quintic value noise, float32 like the GPU)
def hash13(p):
    p = np.asarray(p, np.float32)
    p = (p * np.float32(0.1031)) % np.float32(1.0)
    pzyx = p[..., ::-1]
    d = np.sum(p * (pzyx + np.float32(31.32)), -1, keepdims=True).astype(np.float32)
    p = p + d
    return ((p[..., 0] + p[..., 1]) * p[..., 2]) % np.float32(1.0)


def vnoise3(p):
    i = np.floor(p)
    f = p - i
    u = f * f * f * (f * (f * 6 - 15) + 10)
    n = {}
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                n[(dx, dy, dz)] = hash13(i + np.array([dx, dy, dz], np.float32))
    x00 = n[0, 0, 0] + (n[1, 0, 0] - n[0, 0, 0]) * u[..., 0]
    x10 = n[0, 1, 0] + (n[1, 1, 0] - n[0, 1, 0]) * u[..., 0]
    x01 = n[0, 0, 1] + (n[1, 0, 1] - n[0, 0, 1]) * u[..., 0]
    x11 = n[0, 1, 1] + (n[1, 1, 1] - n[0, 1, 1]) * u[..., 0]
    y0 = x00 + (x10 - x00) * u[..., 1]
    y1 = x01 + (x11 - x01) * u[..., 1]
    return y0 + (y1 - y0) * u[..., 2]


def fbm(pos, patch=ERODE_NOISE[0]):
    p = np.asarray(pos, np.float32) / np.float32(max(patch, 0.05)) + np.array([17.3, 5.1, 9.7], np.float32)
    s, a = 0.0, 0.5
    for _ in range(4):
        s = s + a * vnoise3(p)
        p = p * np.float32(2.03) + np.array([3.1, 7.7, 1.3], np.float32)
        a *= 0.5
    return s / 0.9375


def rect_sd(p, c, h, r):
    q = np.abs(p - c) - (np.asarray(h) - r)
    return np.linalg.norm(np.maximum(q, 0), axis=-1) + np.minimum(np.max(q, -1), 0) - r


def sky_dist(pos):
    q = np.abs(pos[..., [0, 2]] - np.array([SKY_RECT[0], SKY_RECT[2]])) - SKY_RECT[3]
    dxz = np.linalg.norm(np.maximum(q, 0), axis=-1)
    return np.hypot(dxz, pos[..., 1] - SKY_RECT[1])


def erode_field(pos, fade, form=0, resist=0.0, hole_open=0.0, coef=ERODE_COEF, noise_range=NOISE_RANGE, door_bias=0.0):
    """s = noise - tau (< 0 removed). Mirrors LanbaiCabinErodeField."""
    pos = np.asarray(pos, float)
    hN = np.clip((pos[..., 1] - CABIN_BOX[0]) / (CABIN_BOX[1] - CABIN_BOX[0]), 0, 1)
    fN = np.clip((pos[..., 2] - CABIN_BOX[2]) / (CABIN_BOX[3] - CABIN_BOX[2]), 0, 1)
    e = np.exp(-sky_dist(pos) / coef[3])
    front = fN if form else 1 - fN
    sky = e if form else 1 - e
    tau = fade - coef[0] * (1 - hN) - coef[1] * front - coef[2] * sky - resist
    if fade <= 0:
        tau = np.full_like(tau, -10.0)
    seat_rel = np.clip((fade - 0.97) / 0.03, 0, 1)
    dS = np.linalg.norm(pos - np.array(SEAT_SPHERE[:3]), axis=-1)
    in_sphere = 1 - smoothstep(SEAT_SPHERE[3] - 0.05, SEAT_SPHERE[3], dS)
    patch_rel = np.clip((fade - 0.65) / 0.027, 0, 1)
    pc = np.array([(FLOOR_PATCH[0] + FLOOR_PATCH[1]) / 2, (FLOOR_PATCH[2] + FLOOR_PATCH[3]) / 2])
    ph = np.array([(FLOOR_PATCH[1] - FLOOR_PATCH[0]) / 2, (FLOOR_PATCH[3] - FLOOR_PATCH[2]) / 2])
    in_patch = ((rect_sd(pos[..., [0, 2]], pc, ph, 0.02) < 0) & (pos[..., 1] < CABIN_BOX[0] + 0.08)).astype(float)
    prot = np.maximum(in_sphere * (1 - seat_rel), in_patch * (1 - patch_rel))
    tau_raw = tau
    tau = tau + (-10.0 - tau) * prot
    if fade > 0 and door_bias > 0:                  # D-33 #7a, after the protections (as the shader)
        dq = np.maximum(np.array(DOOR_BOX_MIN[:3]) - pos, pos - np.array(DOOR_BOX_MAX))
        in_door = 1 - smoothstep(0.0, DOOR_BOX_MIN[3], np.max(dq, -1))
        tau = tau + ((tau_raw + 1.0 + resist) - tau) * np.clip(door_bias, 0, 1) * in_door
    n = fbm(pos)
    nu = np.clip((n - ERODE_NOISE[1]) / (ERODE_NOISE[2] - ERODE_NOISE[1]), 0, 1)
    s = noise_range[0] + (noise_range[1] - noise_range[0]) * nu - tau
    o = np.clip(hole_open, 0, 1)
    if o > 0:
        g = min(o * 2, 1.0)
        k = np.clip(o * 2 - 1, 0, 1)
        c = np.array(HOLE_MIN[:2]) + (np.array(HOLE_FULL[:2]) - np.array(HOLE_MIN[:2])) * k
        h = np.array(HOLE_MIN[2:]) * g + (np.array(HOLE_FULL[2:]) - np.array(HOLE_MIN[2:]) * g) * k
        h = np.maximum(h, 0.001)
        sd = rect_sd(pos[..., [0, 2]], c, h, min(HOLE_SHAPE[0], h.min())) + (nu - 0.5) * 2 * HOLE_SHAPE[1]
        s = np.where(pos[..., 1] < HOLE_SHAPE[2], np.minimum(s, sd), s)
    return s


# ---------------------------------------------------------------------------------------------------
# the driver's curves (= LanbaiCabinDriver.cs; labels from FromLocal/cues.json / bible v2.1 §2.1)
L = dict(U4h=99.50, U5=107.50, U6=133.80, U9=179.55, U12=248.64, F0=251.64, F1=281.86, F2h=363.26, F5=644.96,
         F8b=877.96, EXIT=922.36, F10=942.26, F10e=956.36, F10l=961.06, RISE=962.26, F12=987.06, W11=1178.46,
         F16=1149.31)
MIRRORS = [1032.41, 1034.91, 1037.98, 1041.74, 1045.82, 1052.3, 1058.95, 1067.46, 1077.21, 1089.91, 1106.41, 1125.55]


def ss(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def tubes(t):
    if t < L['U4h']:
        return 1.0
    if t < L['U5']:
        return 2 ** (-(t - L['U4h']) / (L['U5'] - L['U4h']))
    if t < L['U6']:
        return 0.5
    if t < L['U9']:
        return 0.5 + (0.3125 - 0.5) * ss((t - L['U6']) / 30)
    if t < L['U9'] + 0.2:
        return 0.3125 * 1.5
    if t < L['U9'] + 0.45:
        return 0.3125 * 1.5 * (1 - (t - L['U9'] - 0.2) / 0.25)
    if t < L['W11']:
        return 0.0
    return 1.0


def mirror_steps(t):
    return sum(ss((t - c) / 1.2) for c in MIRRORS)


def bleach(t):
    if t >= L['W11']:
        return 0.0
    if t < L['F0']:
        return 0.0
    if t < L['F1']:
        return 0.10 * (t - L['F0']) / (L['F1'] - L['F0'])
    if t < L['F2h']:
        return 0.10
    if t < L['F5']:
        return 0.10 + 0.15 * (t - L['F2h']) / (L['F5'] - L['F2h'])
    if t < L['EXIT']:
        return 0.25
    if t < L['RISE']:
        return 0.25 + 0.25 * ss((t - L['EXIT']) / (L['RISE'] - L['EXIT']))
    b = 0.5 + 0.3 * mirror_steps(t) / 12
    return b + (1 - b) * ss((t - L['F16']) / 1.2)


def fade(t):
    if t >= L['W11'] or t < L['F2h']:
        return 0.0
    if t < L['F5']:
        return 0.25 * np.sqrt((t - L['F2h']) / (L['F5'] - L['F2h']))
    if t < L['EXIT']:
        return 0.25
    if t < L['RISE']:
        return 0.25 + 0.40 * ss((t - L['EXIT']) / (L['RISE'] - L['EXIT']))
    f = 0.65 + 0.027 * mirror_steps(t)
    return f + (1 - f) * ss((t - L['F16']) / 1.2)


def door_bias(t, start=957.40, end=965.40):
    """LanbaiCabinDriver.DoorBias (D-33 #7a)."""
    if t < start or t >= L['W11']:
        return 0.0
    return float(ss((t - start) / (end - start)))


def hole(t):
    if t < L['F8b'] or t >= L['W11']:
        return 0.0
    if t < L['F8b'] + 6:
        return 0.5 * ss((t - L['F8b']) / 6)
    return 0.5 + 0.5 * ss((t - L['F8b'] - 6) / (897.96 - L['F8b'] - 6))


# ---------------------------------------------------------------------------------------------------
SURFACES = [  # name, albedo sRGB (bible 4.2)
    ('seat vinyl', '#5A2126'), ('seat worn', '#6A3434'), ('frame', '#3C3E3D'), ('floor', '#323634'),
    ('lower wall', '#D9D4C5'), ('ceiling', '#E2DDCF'), ('tube off', '#D8DBD6'), ('dash', '#353637'),
    ('curtain', '#A9BCCB'), ('steel', '#C0C3C4')]


def save(img, name):
    os.makedirs(DOCS, exist_ok=True)
    img.save(os.path.join(DOCS, name))


def swatch_d08():
    raw = srgb2lin('#B9B6D6') * 0.8                 # GateLayout_v2 lights.tear E 0.8
    lim = wound_light_limit(raw)
    W, H = 110, 70
    img = Image.new('RGB', (W * len(SURFACES), H * 2 + 40), (20, 20, 24))
    d = ImageDraw.Draw(img)
    rows = []
    for i, (n, h) in enumerate(SURFACES):
        a = srgb2lin(h)
        c0 = a * raw                                 # lit by the raw wound light (N.L = 1)
        c1 = purple_band(a * lim)                    # limited light + band guard (what the shader returns)
        for j, c in enumerate((c0, c1)):
            col = tuple(int(round(v * 255)) for v in lin2srgb(c))
            d.rectangle([i * W, j * H, i * W + W - 2, j * H + H - 2], fill=col)
        Lc, Cc, hc = lch(c1)
        d.text((i * W + 3, 2 * H + 2), n[:14], fill=(220, 220, 220))
        d.text((i * W + 3, 2 * H + 18), 'C%.1f h%.0f' % (Cc, hc), fill=(220, 220, 220))
        rows.append((n, lch(c0), lch(c1)))
    save(img, 'swatch_d08_limiter.png')
    return raw, lim, rows


def swatch_bleach():
    amb = srgb2lin('#828BAA') * 0.45
    levels = [0, 0.10, 0.25, 0.5, 0.8, 1.0]
    W, H = 80, 40
    img = Image.new('RGB', (W * len(levels), H * len(SURFACES)), (0, 0, 0))
    d = ImageDraw.Draw(img)
    for i, (n, h) in enumerate(SURFACES):
        for j, b in enumerate(levels):
            a = bleach_albedo(srgb2lin(h), b, amb)
            d.rectangle([j * W, i * H, j * W + W - 2, i * H + H - 2], fill=tuple(int(v * 255) for v in lin2srgb(a)))
    save(img, 'swatch_bleach.png')


def curves():
    ts = np.arange(-5, 1260, 0.25)
    W, H = 1260, 360
    img = Image.new('RGB', (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)
    for k, (fn, col) in enumerate([(tubes, (40, 120, 200)), (bleach, (200, 150, 40)), (fade, (190, 40, 40)), (hole, (40, 150, 70))]):
        pts = [(int((t + 5) / 1265 * W), int(H - 20 - fn(t) / 1.5 * (H - 40))) for t in ts]
        d.line(pts, fill=col, width=2)
        d.text((10, 10 + 14 * k), ['tubes', 'bleach', 'fade', 'D-26 hole'][k], fill=col)
    for n in ('U9', 'F0', 'F2h', 'F5', 'EXIT', 'F16', 'W11'):
        x = int((L[n] + 5) / 1265 * W)
        d.line([(x, 0), (x, H)], fill=(200, 200, 200))
        d.text((x + 2, H - 16), n, fill=(90, 90, 90))
    save(img, 'curve_cabin_timeline.png')


ZONES = {  # name: (x range, y range, z range) sample boxes inside the cabin (bus_spec numbers)
    'skylight rim 0-0.3 m': ((0.05, 1.05), (2.55, 2.62), (2.30, 3.30)),
    'front roof z>1.5': ((-1.0, 1.0), (2.55, 2.62), (1.5, 3.4)),
    'rear roof z<-1': ((-1.0, 1.0), (2.55, 2.62), (-3.5, -1.0)),
    'upper walls y 1.9-2.4': ((0.95, 1.0), (1.9, 2.4), (-3.4, 3.2)),
    'seats y 0.9-1.3': ((-1.3, -0.45), (0.9, 1.3), (-3.0, 1.5)),
    'stanchion (resist 0.3)': ((-0.40, -0.38), (0.7, 2.5), (-3.0, 2.5)),
    'floor aisle': ((-0.4, 0.3), (0.62, 0.62), (-3.4, 0.8)),
}


def zone_fraction(zone, f, form, resist=0.0, n=4000, seed=1):
    rng = np.random.default_rng(seed)
    (x0, x1), (y0, y1), (z0, z1) = ZONES[zone]
    pos = np.stack([rng.uniform(x0, x1, n), rng.uniform(y0, y1, n), rng.uniform(z0, z1, n)], -1)
    r = 0.3 if 'resist' in zone else resist
    return float(np.mean(erode_field(pos, f, form, r) < 0))


def erosion_zones():
    fades = [0.072, 0.25, 0.45, 0.65, 0.80, 0.97]
    table = {}
    W, H = 900, 380
    img = Image.new('RGB', (W, H), (250, 250, 248))
    d = ImageDraw.Draw(img)
    cols = [(200, 40, 40), (230, 120, 30), (120, 120, 20), (40, 140, 60), (40, 100, 200), (120, 60, 180), (80, 80, 80)]
    for form in (0, 1):
        for zi, z in enumerate(ZONES):
            v = [zone_fraction(z, f, form) for f in fades]
            table[(form, z)] = v
            x0 = 40 + form * 440
            pts = [(x0 + int(i / (len(fades) - 1) * 380), int(H - 40 - v[i] * (H - 80))) for i in range(len(fades))]
            d.line(pts, fill=cols[zi], width=2)
            if form == 0:
                d.text((40, 20 + 13 * zi), z, fill=cols[zi])
        d.text((40 + form * 440, H - 30), ['PROSE (default)', 'LITERAL'][form] + '  fade 0.07 .. 0.97', fill=(0, 0, 0))
    save(img, 'erosion_zones.png')
    return fades, table


def floor_plan():
    xs = np.linspace(-1.35, 1.04, 240)
    zs = np.linspace(-0.5, 3.5, 400)
    X, Z = np.meshgrid(xs, zs)
    pos = np.stack([X, np.full_like(X, 0.62), Z], -1)
    s = erode_field(pos, fade(897.96), 0, 0, hole(897.96))
    img = np.where((s < 0)[..., None], np.array([46, 60, 102]), np.array([60, 62, 60])).astype(np.uint8)[::-1]
    im = Image.fromarray(img).resize((480, 800), Image.NEAREST)
    d = ImageDraw.Draw(im)
    d.text((6, 6), 'floor plan t=897.96 (rear at bottom, right wall at right); blue = open', fill=(255, 255, 255))
    save(im, 'erosion_floor_d26.png')
    return float(np.mean(s < 0))


def selftest():
    # 1. Lab round trip
    c = np.array([0.3, 0.2, 0.6])
    assert np.allclose(lab2lin(lin2lab(c)), c, atol=1e-3)
    # 2. D-08: the limited wound light is a cold white C* <= 12, h 230-290
    raw, lim, rows = swatch_d08()
    Ll, Cl, hl = lch(lim)
    assert Cl <= 12.05 and 229 <= hl <= 290.5, (Cl, hl)
    # 3. D-21 band: nothing lit by the limited light is in h 290-330 with C* > 8 and L* > 40
    for n, _, (L_, C_, h_) in rows:
        assert not (290 < h_ < 330 and C_ > 8.05 and L_ > 40), (n, L_, C_, h_)
    # 4. palette colours are untouched by the band guard when L* <= 40 (D-21 indigo) and outside the band
    for h in ('#3D4A80', '#5A2126', '#E2DDCF'):
        a = srgb2lin(h)
        assert np.allclose(purple_band(a), a, atol=2e-3), h
    # 5. erosion: fade 0 removes nothing; protected sphere survives 0.9; hole opens at 897.96
    pos = np.random.default_rng(0).uniform([-1.3, 0.62, -3.6], [1.0, 2.62, 3.4], (5000, 3))
    assert np.all(erode_field(pos, 0.0) > 0)
    sp = np.array(SEAT_SPHERE[:3]) + np.random.default_rng(1).normal(0, 0.25, (2000, 3))
    sp = sp[np.linalg.norm(sp - SEAT_SPHERE[:3], axis=1) < 0.8]
    assert np.all(erode_field(sp, 0.96) > 0)
    hc = np.array([[HOLE_FULL[0], 0.62, HOLE_FULL[1]]])
    assert erode_field(hc, fade(897.96), 0, 0, hole(897.96))[0] < 0
    # 6. curves hit the bible §4.8 table
    assert abs(fade(L['F5']) - 0.25) < 1e-6 and abs(fade(1137.58) - (0.65 + 0.027 * 12)) < 0.01
    assert abs(bleach(L['F1']) - 0.10) < 1e-6 and abs(bleach(L['RISE']) - 0.5) < 1e-6
    assert tubes(L['U9'] + 0.1) == 0.3125 * 1.5 and tubes(L['U9'] + 0.5) == 0.0 and tubes(1200) == 1.0
    swatch_bleach()
    curves()
    fades, table = erosion_zones()
    open_frac = floor_plan()
    # FBM distribution (for _ErodeNoise.y / .z)
    n = fbm(pos)
    print('FBM mean %.3f std %.3f p2 %.3f p98 %.3f' % (n.mean(), n.std(), np.percentile(n, 2), np.percentile(n, 98)))
    print('wound light raw  L %.1f C %.1f h %.1f' % lch(raw))
    print('wound light lim  L %.1f C %.1f h %.1f   linear %s' % (Ll, Cl, hl, np.round(lim, 4)))
    for nme, (L0, C0, h0), (L1, C1, h1) in rows:
        print('  %-11s raw L%5.1f C%5.1f h%5.1f  ->  L%5.1f C%5.1f h%5.1f' % (nme, L0, C0, h0, L1, C1, h1))
    print('eroded fraction per zone (fade %s)' % fades)
    for form in (0, 1):
        print(['PROSE (default)', 'LITERAL'][form])
        for z in ZONES:
            print('  %-24s %s' % (z, ' '.join('%4.0f%%' % (100 * v) for v in table[(form, z)])))
    print('floor plan at 897.96: %.1f %% of the sampled floor open' % (100 * open_frac))
    print('OK  (PNGs in %s)' % DOCS)


if __name__ == '__main__':
    sys.exit(selftest())
