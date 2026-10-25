"""蓝白 · 白铜镜的镜背、镜缘带（连珠乳钉）、铭文 / 栉齿 / 锯齿 / 流云带的 numpy 移植（Lanbai_BronzeMirror.shader 的
BACK and KNOB / RIM BAND 分支 + LanbaiMirror.cginc 的 LanbaiMirrorBandCell / BandHeight / BeadNormalOS，同名、同数）。
贴图读的是 Mirrors/Textures/ 里真的那几张（双线性、平铺；没有 mip：渲染时用超采样代替）。"""
import math, os
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.abspath(os.path.join(HERE, '..', '..', 'Textures'))
LUMA = np.array([0.2126, 0.7152, 0.0722])
BACK_ALB = np.array([0.078, 0.195, 0.133])          # _BackAlbedo (#4F7A66)
RIM_F0 = np.array([0.584, 0.392, 0.184])            # _RimF0 (#C9A873)
BACK_RELIEF, BACK_LUMK, BACK_BUMP = 1.4, float(os.environ.get('BACK_LUMK', 1.0)), 1.0   # _BackRelief, _BackLumK, _BackBump
TLV_TILE, BOSS_PITCH, BOSS_RAD = 40.0, 1.5, 0.30
CLOUD_ASPECT = 5.246
_T = {}


def tex(name):
    if name not in _T:
        a = np.asarray(Image.open(os.path.join(TEX, name)), np.float32) / 255.0
        _T[name] = a if a.ndim == 3 else a[..., None]
    return _T[name]


def sample(name, u, v, wrap_u=True, wrap_v=True):
    """Unity convention: uv (0, 0) = bottom left; bilinear."""
    a = tex(name); H, W = a.shape[:2]
    x = u * W - 0.5; y = (1.0 - v) * H - 0.5
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int); fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    def idx(i, n, wrap):
        return np.mod(i, n) if wrap else np.clip(i, 0, n - 1)
    xa, xb = idx(x0, W, wrap_u), idx(x0 + 1, W, wrap_u)
    ya, yb = idx(y0, H, wrap_v), idx(y0 + 1, H, wrap_v)
    return (a[ya, xa] * (1 - fx) * (1 - fy) + a[ya, xb] * fx * (1 - fy) + a[yb, xa] * (1 - fx) * fy + a[yb, xb] * fx * fy)


def band_cell(rM, th, r0, r1, row_target, period, aspect, multiple):
    w = r1 - r0
    rows = max(math.floor(w / row_target), 1.0)
    rowH = w / rows
    y = (rM - r0) / rowH
    row = np.clip(np.floor(y), 0, rows - 1)
    v = np.clip(y - row, 0, 1)
    rRow = r0 + (row + 0.5) * rowH
    p = aspect * rowH if aspect > 0 else period
    n = multiple * np.maximum(np.round(2 * np.pi * rRow / p / multiple), 1.0)
    s = (th + np.pi) * (n / (2 * np.pi))
    return s, v, row, rows, rowH, n


def saw(x):
    return 1.0 - np.abs(np.mod(x, 1.0) * 2.0 - 1.0)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def band_height(rM, R, th, fp):
    q = rM / R
    h = np.zeros_like(rM)
    m = (q >= 0.80) & (q < 0.83)
    if m.any():
        s, v, row, rows, rowH, n = band_cell(rM[m], th[m], 0.80 * R, 0.83 * R, 1.0, 0.5, 0.0, 1.0)
        c = np.abs(np.mod(s + 0.5, 1.0) - 0.5) * 2.0
        gap = smoothstep(0.0, 0.08, v) * smoothstep(1.0, 0.92, v) if rows > 1 else 1.0
        h[m] = smoothstep(0.45, 0.25, c) * gap * np.clip(1.5 - fp[m] / 0.2, 0, 1)
    m = (q >= 0.855) & (q < 0.89)
    if m.any():
        s, v, row, rows, rowH, n = band_cell(rM[m], th[m], 0.855 * R, 0.89 * R, 1.1, 1.25, 0.0, 1.0)
        h[m] = (v <= saw(s) * 0.95) * np.clip(1.5 - fp[m] / 0.4, 0, 1)
    m = (q >= 0.895) & (q < 0.90)
    h[m] = 1.0
    m = (q >= 0.905) & (q < 0.975)
    if m.any():
        s, v, row, rows, rowH, n = band_cell(rM[m], th[m], 0.905 * R, 0.975 * R, 1.4, 0.0, CLOUD_ASPECT, 1.0)
        h[m] = sample('T_MirrorRimCloud_2048x256.png', np.mod(s, 1.0), v, True, False)[..., 0] * np.clip(1.5 - fp[m] / 0.3, 0, 1)
    m = (q >= 0.72) & (q < 0.80)
    if m.any():
        s, v, row, rows, rowH, n = band_cell(rM[m], th[m], 0.72 * R, 0.80 * R, 2.6, 0.0, 1.0, 35.0)
        idx = np.mod(np.floor(s) + row * 7.0, 35.0)
        gx = np.mod(idx, 8.0); gy = 7.0 - np.floor(idx / 8.0)
        gu = (gx + np.mod(s, 1.0) * 0.84 + 0.08) / 8.0; gv = (gy + v * 0.84 + 0.08) / 8.0
        g = sample('T_MirrorGlyphs_1024.png', gu, gv, False, False)[..., 0]
        h[m] = np.maximum(h[m], g * np.clip(1.5 - fp[m] / 0.4, 0, 1))
    return h


def back_color(Pl, D, fp, Lsky):
    """Pl: points on the back in mirror-local metres (x east, z north; y ignored), fp: metres per pixel,
    Lsky: luminance of the sky right behind each pixel (MirrorSky(V, 0.6)).  Returns linear RGB."""
    R = 0.5 * D
    x, z = Pl[:, 0], Pl[:, 2]
    rM = np.hypot(x, z); th = np.arctan2(z, x)
    cu = x / TLV_TILE + 0.5; cv = z / TLV_TILE + 0.5
    centre = (np.floor(cu) == 0) & (np.floor(cv) == 0)
    mA = sample('T_MirrorBack_Mask_2048.png', cu, cv); mC = sample('T_MirrorBack_Centre_Mask_2048.png', cu, cv)
    nA = sample('T_MirrorBack_Normal_2048.png', cu, cv); nC = sample('T_MirrorBack_Centre_Normal_2048.png', cu, cv)
    msk = np.where(centre[:, None], mC, mA); tn = np.where(centre[:, None], nC, nA)[:, :3] * 2 - 1
    nOS = np.stack([tn[:, 0], -tn[:, 2], tn[:, 1]], -1)
    nOS /= np.linalg.norm(nOS, axis=-1, keepdims=True)
    hb = band_height(rM, R, th, fp)
    # the screen-space bump: gradient of the band height at the pixel footprint
    e = np.maximum(fp, 1e-3)
    dhx = (band_height(np.hypot(x + e, z), R, np.arctan2(z, x + e), fp) - hb) / e
    dhz = (band_height(np.hypot(x, z + e), R, np.arctan2(z + e, x), fp) - hb) / e
    q = rM / R
    outer = q > 0.72
    msk = msk.copy()
    msk[outer, 1] = 1.0 + (0.75 - 1.0) * hb[outer]; msk[outer, 2] = hb[outer]
    nOS[outer] = np.array([0, -1.0, 0])
    fade = np.clip(1.5 - fp / 0.5, 0, 1)
    n = nOS - (BACK_BUMP * 0.02 * D * fade)[:, None] * np.stack([dhx, np.zeros_like(dhx), dhz], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    pat = BACK_ALB[None, :] * (np.array([0.85, 1.0, 1.05]) * (1 - msk[:, 3:4]) + np.array([1.15, 0.92, 0.8]) * msk[:, 3:4])
    t1 = pat / np.maximum(pat @ LUMA, 1e-4)[:, None]
    t2 = RIM_F0 / (RIM_F0 @ LUMA)
    tint = t1 + (t2[None, :] - t1) * (0.45 * msk[:, 2:3])
    key = np.array([-0.45, -0.75, -0.48]); key /= np.linalg.norm(key)
    # relief and AO only where the cell texture is not magnified (footprint >= 1 texel = 2 cm): a magnified patch is a few
    # metres of the relief filling the screen, whose own mean is not 1 (r6: a dark patch overhead read as a -1.3 EV dip)
    mag = np.clip(fp / (TLV_TILE / 2048.0), 0, 1)
    shade = np.maximum(1.0 + BACK_RELIEF * mag * (n @ key - np.array([0, -1.0, 0]) @ key), 0.15) * (1.0 + mag * (msk[:, 1] / 0.92 - 1.0))
    return (Lsky * BACK_LUMK * shade)[:, None] * tint


def bead_normal(Pl, D, fp):
    """LanbaiMirrorBeadNormalOS in mirror-local metres: returns world normal (no rotation) and cover."""
    x, z = Pl[:, 0], Pl[:, 2]
    r = np.hypot(x, z); th = np.arctan2(z, x)
    rc = 0.49 * D
    n = max(round(2 * np.pi * rc / BOSS_PITCH), 3.0)
    pitch = 2 * np.pi * rc / n
    s = th * rc
    du = (np.mod(s / pitch + 0.5, 1.0) - 0.5) * pitch
    dv = r - rc
    d2 = du * du + dv * dv
    a = BOSS_RAD
    inside = np.clip((a * a - d2) / (0.15 * a * a), 0, 1)
    h = np.sqrt(np.maximum(a * a - d2, 0))
    T = np.stack([-np.sin(th), np.zeros_like(th), np.cos(th)], -1)
    B = np.stack([np.cos(th), np.zeros_like(th), np.sin(th)], -1)
    nb = du[:, None] * T + dv[:, None] * B + np.maximum(h, 1e-4)[:, None] * np.array([0, 1.0, 0])
    nb /= np.linalg.norm(nb, axis=-1, keepdims=True)
    detail = np.clip(1.5 - fp / (0.5 * a), 0, 1)
    cover = inside * detail
    nn = np.array([0, 1.0, 0]) * (1 - cover[:, None]) + nb * cover[:, None]
    return nn / np.linalg.norm(nn, axis=-1, keepdims=True), cover
