# -*- coding: utf-8 -*-
"""蓝白 · 云（Clouds_v2 / Act06_Dawn / Act08_Dusk）共用的小工具：
.hdr 读取、方向 <-> 等距柱状、颜色换算（sRGB / Lab）、按 PPv2 引擎模型调色（含 bloom）。

坐标：Unity 世界，Y 上，车头 +Z，右 +X。方位 az 从 +Z 向 +X（向右）为正，仰角 el 向上为正。
调色：Grading/Tools~/engine/ppv2_engine.py（PPv2 Neutral 通路，按源码写的引擎模型）+ grades_engine.json；
bloom：Art/tools/lens_cine/ppv2.py 经 lutlib_core.patch_ppv2 修正的近似（与 Grading 的 compare_frames 相同做法）。
"""
import os
import sys
import json
import math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Grading', 'Tools~', 'engine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'lens_cine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'bible_work'))
import ppv2_engine as E  # noqa: E402
import ppv2 as LD  # noqa: E402
from lutlib_core import patch_ppv2  # noqa: E402
patch_ppv2(LD)

HDRI_DIR = os.path.join(REPO, 'FromLocal', 'hdri', 'hdr')
HDRI = dict(dawn=os.path.join(HDRI_DIR, 'syferfontein_6d_clear_puresky_1k.hdr'),
            dusk=os.path.join(HDRI_DIR, 'syferfontein_0d_clear_puresky_1k.hdr'))
LUMA = np.array([0.2126, 0.7152, 0.0722])


# ---------------------------------------------------------------- .hdr (Radiance RGBE, new-style RLE)
def read_hdr(path):
    with open(path, 'rb') as f:
        data = f.read()
    pos = 0
    while True:
        e = data.index(b'\n', pos)
        line = data[pos:e]
        pos = e + 1
        if line.startswith(b'-Y') or line.startswith(b'+Y'):
            parts = line.split()
            H, W = int(parts[1]), int(parts[3])
            break
    out = np.zeros((H, W, 4), np.uint8)
    buf = np.frombuffer(data, np.uint8)
    for y in range(H):
        if buf[pos] == 2 and buf[pos + 1] == 2 and (buf[pos + 2] << 8 | buf[pos + 3]) == W:
            pos += 4
            for c in range(4):
                x = 0
                while x < W:
                    n = int(buf[pos]); pos += 1
                    if n > 128:
                        n -= 128
                        out[y, x:x + n, c] = buf[pos]; pos += 1
                    else:
                        out[y, x:x + n, c] = buf[pos:pos + n]; pos += n
                    x += n
        else:                                  # flat
            out[y] = buf[pos:pos + 4 * W].reshape(W, 4); pos += 4 * W
    m = out[..., :3].astype(np.float32)
    ex = out[..., 3].astype(np.int32)
    s = np.where(ex > 0, np.ldexp(1.0, ex - 136), 0.0).astype(np.float32)
    return m * s[..., None]                    # (H, W, 3) linear, row 0 = top (zenith)


def write_hdr(path, img):
    """Flat (non-RLE) RGBE writer."""
    img = np.maximum(np.asarray(img, np.float64), 0)
    H, W, _ = img.shape
    mx = img.max(-1)
    m, e = np.frexp(mx)
    sc = np.where(mx > 1e-32, m * 256.0 / np.maximum(mx, 1e-32), 0)
    rgbe = np.zeros((H, W, 4), np.uint8)
    rgbe[..., :3] = np.clip(img * sc[..., None], 0, 255).astype(np.uint8)
    rgbe[..., 3] = np.where(mx > 1e-32, e + 128, 0).astype(np.uint8)
    with open(path, 'wb') as f:
        f.write(b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y %d +X %d\n' % (H, W))
        f.write(rgbe.tobytes())


# ---------------------------------------------------------------- directions
def dir_from_azel(az_deg, el_deg):
    az, el = np.radians(az_deg), np.radians(el_deg)
    return np.stack([np.cos(el) * np.sin(az), np.sin(el), np.cos(el) * np.cos(az)], -1)


def azel_from_dir(d):
    d = np.asarray(d, np.float64)
    return np.degrees(np.arctan2(d[..., 0], d[..., 2])), np.degrees(np.arcsin(np.clip(d[..., 1], -1, 1)))


def equirect_uv(d, yaw_deg=0.0):
    """Image coords (u right 0..1, v down 0..1) of unit directions; image column u = (az + yaw)/360 + 0.5."""
    az, el = azel_from_dir(d)
    u = ((az + yaw_deg) / 360.0 + 0.5) % 1.0
    v = (90.0 - el) / 180.0
    return u, v


def sample_equirect(img, d, yaw_deg=0.0):
    """Bilinear lookup of an equirect image along directions (..., 3)."""
    H, W, _ = img.shape
    u, v = equirect_uv(d, yaw_deg)
    x = u * W - 0.5
    y = np.clip(v * H - 0.5, 0, H - 1)
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    x0m, x1m = x0 % W, (x0 + 1) % W
    y1 = np.minimum(y0 + 1, H - 1)
    a = img[y0, x0m] * (1 - fx) + img[y0, x1m] * fx
    b = img[y1, x0m] * (1 - fx) + img[y1, x1m] * fx
    return a * (1 - fy) + b * fy


def equirect_dirs(H, W, yaw_deg=0.0):
    """Unit direction of every pixel centre of an (H, W) equirect with the given yaw (inverse of equirect_uv)."""
    u = (np.arange(W) + 0.5) / W
    v = (np.arange(H) + 0.5) / H
    az = (u - 0.5) * 360.0 - yaw_deg
    el = 90.0 - v * 180.0
    A, Ee = np.meshgrid(az, el)
    return dir_from_azel(A, Ee)


def solid_angle_rows(H, W):
    el = np.radians(90.0 - (np.arange(H) + 0.5) / H * 180.0)
    return (np.cos(el) * (np.pi / H) * (2 * np.pi / W))[:, None]


# ---------------------------------------------------------------- colour
def srgb_dec(v):
    v = np.asarray(v, np.float64)
    return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)


def srgb_enc(v):
    v = np.clip(np.asarray(v, np.float64), 0, None)
    return np.where(v <= 0.0031308, v * 12.92, 1.055 * np.power(v, 1 / 2.4) - 0.055)


def hex_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float64) / 255.0


def hex_lin(h):
    return srgb_dec(hex_rgb(h))


def to_hex(codes):
    c = np.clip(np.round(np.asarray(codes, np.float64)), 0, 255).astype(int)
    return '#%02X%02X%02X' % tuple(c)


def lab_of_codes(codes):
    """CIE Lab (D65) of sRGB display codes 0..255 (..., 3)."""
    lin = srgb_dec(np.asarray(codes, np.float64) / 255.0)
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]])
    xyz = lin @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    L = 116 * f[..., 1] - 16
    a = 500 * (f[..., 0] - f[..., 1])
    b = 200 * (f[..., 1] - f[..., 2])
    return L, a, b


def hue_chroma(codes):
    L, a, b = lab_of_codes(codes)
    return L, (np.degrees(np.arctan2(b, a)) + 360) % 360, np.hypot(a, b)


def luma_of_codes(codes):
    """Rec.709 luma (as the bible's APL: weighted sum of display codes)."""
    return np.asarray(codes, np.float64) @ LUMA


# ---------------------------------------------------------------- grading (PPv2 engine model)
_G = None
_LUT = {}


def grades():
    global _G
    if _G is None:
        with open(os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_engine.json')) as f:
            _G = json.load(f)
    return _G


def profile(sid):
    G = grades()
    p = dict(G['profiles'][sid]['ppv2'])
    p['colorFilter'] = G['common']['colorFilter']
    p['hueShift'] = G['common']['hueShift']
    return p


def lerp_profile(a, b, w):
    """PPv2 volume blend (every overridden parameter interpolated)."""
    pa, pb = profile(a) if isinstance(a, str) else a, profile(b) if isinstance(b, str) else b
    out = {}
    for k, va in pa.items():
        vb = pb[k]
        if isinstance(va, dict):
            out[k] = {kk: (va[kk] + (vb[kk] - va[kk]) * w if isinstance(va[kk], (int, float)) else (vb[kk] if w > 0.5 else va[kk])) for kk in va}
        elif isinstance(va, (list, tuple)):
            out[k] = [x + (y - x) * w for x, y in zip(va, vb)]
        elif isinstance(va, (int, float)):
            out[k] = va + (vb - va) * w
        else:
            out[k] = vb if w > 0.5 else va
    return out


def grade(img_lin, sid, bloom=True, ev=0.0):
    """Scene-linear image (H, W, 3) -> display codes 0..255 float, as PPv2 shows it (bloom before the LUT).
    sid: profile id or a profile dict. ev: extra exposure (EXPO helpers), added to postExposure."""
    p = profile(sid) if isinstance(sid, str) else dict(sid)
    if ev:
        p['postExposure'] = p['postExposure'] + ev
    x = np.asarray(img_lin, np.float64)
    if bloom:
        x = x + LD.bloom_layer(x, LD.full(p))
    key = json.dumps({k: v for k, v in p.items() if k != 'bloom'}, sort_keys=True)
    if key not in _LUT:
        _LUT[key] = E.bake_lut(p)
    return E.codes(x, p, _LUT[key])


def ungrade_hex(target_hex, sid, lo=1e-4, hi=64.0):
    """Scene-linear colour that the profile shows as target_hex (no bloom), per channel by bisection on a grey axis,
    then a few Newton steps on the full colour (good to ~1 code)."""
    tgt = hex_rgb(target_hex) * 255.0
    x = srgb_dec(hex_rgb(target_hex))
    for _ in range(40):
        c = grade(x[None, None, :], sid, bloom=False)[0, 0]
        err = tgt - c
        if np.abs(err).max() < 0.3:
            break
        J = np.zeros((3, 3))
        for j in range(3):
            dx = np.zeros(3); dx[j] = max(x[j] * 0.02, 1e-5)
            J[:, j] = (grade((x + dx)[None, None, :], sid, bloom=False)[0, 0] - c) / dx[j]
        step = np.linalg.lstsq(J, err, rcond=None)[0]
        x = np.clip(x + step * 0.8, lo, hi)
    return x
