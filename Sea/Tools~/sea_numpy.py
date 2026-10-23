# -*- coding: utf-8 -*-
"""numpy port of Sea/Shaders/LanbaiSea.cginc (+ Lanbai_Sea.shader's frag), function by function, same names.
The reference renders call THIS, so what they show is what the shader computes (up to texture filtering: the
port does trilinear mip sampling with a footprint estimated from neighbouring pixels, like ddx/ddy).

Directions use the Unity frame: x right, y up, z forward. Environment 'cubes' are equirect float arrays in the
convention  lon = atan2(d.x, d.z) (azimuth, +x = +90 deg), lat = asin(d.y);  u = 0.5 + lon / 2pi,  v = 0.5 + lat / pi
(row 0 = v 0 = straight down)."""
import json
import math
import os

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
TEX = os.path.join(KIT, 'Textures')
META = json.load(open(os.path.join(TEX, 'sea_textures_meta.json')))
VAR_LARGE = META['SeaN_Large_1024']['rms_slope'] ** 2
VAR_SMALL = META['SeaN_Small_1024']['rms_slope'] ** 2


# ------------------------------------------------------------------------------------------------ helpers
def normalize(v):
    return v / np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-12)


def dot(a, b):
    return np.sum(a * b, axis=-1)


def smoothstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0.0, 1.0)
    return t * t * (3.0 - 2.0 * t)


def clamp_max_channel(c, m):
    """clamp the brightest channel to m keeping the hue (a per-channel min() turns a sun into a rainbow ring)"""
    mx = np.max(c, -1, keepdims=True)
    return np.where(mx > m, c * (m / np.maximum(mx, 1e-9)), c).astype(np.float32)


def saturate(x):
    return np.clip(x, 0.0, 1.0)


def read_hdr(path):
    """Radiance RGBE (.hdr) reader, new-style RLE. Returns float32 [H, W, 3], row 0 = top of the file."""
    data = open(path, 'rb').read()
    i = data.index(b'\n\n') + 2
    j = data.index(b'\n', i)
    dims = data[i:j].split()
    H, W = int(dims[1]), int(dims[3])
    p = j + 1
    out = np.zeros((H, W, 4), np.uint8)
    buf = np.frombuffer(data, np.uint8)
    for y in range(H):
        if buf[p] == 2 and buf[p + 1] == 2:
            p += 4
            for c in range(4):
                x = 0
                while x < W:
                    n = int(buf[p]); p += 1
                    if n > 128:
                        n -= 128
                        out[y, x:x + n, c] = buf[p]; p += 1
                    else:
                        out[y, x:x + n, c] = buf[p:p + n]; p += n
                    x += n
        else:
            out[y] = buf[p:p + 4 * W].reshape(W, 4); p += 4 * W
    e = out[..., 3].astype(np.int32)
    f = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0)
    return (out[..., :3].astype(np.float32) * f[..., None]).astype(np.float32)


def load_png_normal(name):
    a = np.asarray(Image.open(os.path.join(TEX, name)).convert('RGB'), np.float32) / 255.0
    a = np.flipud(a)                                             # row 0 = v 0 (Unity)
    n = a * 2.0 - 1.0
    # UnpackNormal on BC5/DXT5nm: xy from the texture, z rebuilt
    xy = n[..., :2]
    z = np.sqrt(saturate(1.0 - np.sum(xy * xy, -1)))
    return np.concatenate([xy, z[..., None]], -1)


class MipTex:
    """box-filtered mip chain + trilinear wrap sampling (what the GPU does for a tiling texture)"""

    def __init__(self, arr, wrap=True):
        self.levels = [np.asarray(arr, np.float32)]
        while self.levels[-1].shape[0] > 1:
            a = self.levels[-1]
            a = 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])
            self.levels.append(a)
        self.wrap = wrap

    def _bilinear(self, a, uv):
        h, w = a.shape[:2]
        x = uv[..., 0] * w - 0.5
        y = uv[..., 1] * h - 0.5
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
        fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
        x0 %= w; y0 %= h; x1 = (x0 + 1) % w; y1 = (y0 + 1) % h
        return (a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x1] * fx * (1 - fy) + a[y1, x0] * (1 - fx) * fy + a[y1, x1] * fx * fy)

    def sample(self, uv, lod):
        lod = np.clip(lod, 0, len(self.levels) - 1)
        l0 = np.floor(lod).astype(int)
        f = (lod - l0)[..., None]
        out = np.zeros(uv.shape[:-1] + (self.levels[0].shape[-1],), np.float32)
        for L in np.unique(l0):
            m = l0 == L
            a = self._bilinear(self.levels[L], uv[m])
            b = self._bilinear(self.levels[min(L + 1, len(self.levels) - 1)], uv[m])
            out[m] = a * (1 - f[m]) + b * f[m]
        return out


class Env:
    """equirect environment with a blurred pyramid standing in for the cube's GGX-prefiltered mips"""

    def __init__(self, arr):
        a = np.asarray(arr, np.float32)
        self.levels = [a]
        for k in range(7):
            a = self.levels[-1]
            if a.shape[0] < 8:
                break
            b = 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])
            self.levels.append(b)

    def lookup(self, d, lod=0.0):
        d = normalize(d)
        lon = np.arctan2(d[..., 0], d[..., 2])
        lat = np.arcsin(np.clip(d[..., 1], -1, 1))
        uv = np.stack([0.5 + lon / (2 * np.pi), 0.5 + lat / np.pi], -1)
        lod = np.broadcast_to(np.asarray(lod, np.float32), d.shape[:-1])
        out = np.zeros(d.shape, np.float32)
        l0 = np.clip(np.floor(lod).astype(int), 0, len(self.levels) - 1)
        f = np.clip(lod - l0, 0, 1)[..., None]
        for L in np.unique(l0):
            m = l0 == L
            A = self._samp(self.levels[L], uv[m])
            B = self._samp(self.levels[min(L + 1, len(self.levels) - 1)], uv[m])
            out[m] = A * (1 - f[m]) + B * f[m]
        return out

    @staticmethod
    def _samp(a, uv):
        h, w = a.shape[:2]
        x = uv[..., 0] * w - 0.5
        y = np.clip(uv[..., 1] * h - 0.5, 0, h - 1)
        x0 = np.floor(x).astype(np.int64); y0 = np.floor(y).astype(np.int64)
        fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
        x0 %= w; x1 = (x0 + 1) % w; y1 = np.minimum(y0 + 1, h - 1)
        return a[y0, x0] * (1 - fx) * (1 - fy) + a[y0, x1] * fx * (1 - fy) + a[y1, x0] * (1 - fx) * fy + a[y1, x1] * fx * fy


def equirect_from_hdr(hdr, sun_target_az_deg=None, tint=None):
    """file equirect (row 0 = zenith, column 0 = some azimuth) -> our convention (row 0 = nadir), optionally rotated so
    that the brightest pixel (the sun) sits at azimuth sun_target_az_deg."""
    a = np.flipud(hdr)
    H, W = a.shape[:2]
    if sun_target_az_deg is not None:
        y, x = np.unravel_index(np.argmax(a.sum(-1)), a.shape[:2])
        u_sun = (x + 0.5) / W
        u_t = 0.5 + math.radians(sun_target_az_deg) / (2 * math.pi)
        a = np.roll(a, int(round((u_t - u_sun) * W)), axis=1)
    if tint is not None:
        a = a * np.asarray(tint, np.float32)
    return a


# ------------------------------------------------------------------------------------------------ material
DEFAULTS = dict(LargeTile=64.0, SmallTile=9.0, LargeScroll=(0.9, 0.35), SmallScroll=(-0.4, 0.7), NormalStrength=1.0, WaveRotate=(0.0, 0.0),
                WaveAmp=1.0, MacroTile=1500.0, CalmStrength=0.15, CalmAll=0.0, CalmPatch=(0, 0, 0, 0), IOR=1.333,
                Smoothness=0.97, ReflGain=1.0, ReflClamp=2.4, WaterColor=(0.0156, 0.0484, 0.0954), DiscCenter=(0, 0, 0, 0),
                SunColor=(0, 0, 0), SunDir=(0.4973, 0.1045, 0.8613), SunGlitterRough=0.12, SunReflPeakEV=1.3, SunDiscDeg=0.53,
                AirSide=1.0, WindowGain=1.0, WindowTint=(1, 1, 1, 0), Dispersion=(1.331, 1.337), TIRColor=(0.0222, 0.0685, 0.1651),
                TIRCubeGain=0.0, WindowEdgeSoft=0.6, WindowRadial=(1.0, 2.0), WindowSunDir=(0.0, -0.0087, 1.0, 1.2), WindowSunSpread=14.0, WindowSunColor=(0, 0, 0), WindowSunFloor=0.35, WindowSunGain=1.0, WindowCore=(0.0, 0.5, 2.0, 0.0), DissolveTime=-1.0, DissolveFront=4.0, DissolvePixel=5.0,
                FogMode=1, ReflExposure=1.0, MirrorTint=(1.0, 1.0, 1.0), PurpleGuard=(1.0,), PurpleMask=(1, 1, 1, 1), PurpleCeiling='main',
                GerstnerLength=(60, 37, 23, 0.08), GerstnerAmp=(0, 0, 0), GerstnerDir=(0.94, 0.34, 0.5, 0.866), LampGlints=0.0, Lamps=())

_TEX = {}


def textures():
    if not _TEX:
        _TEX['L'] = MipTex(load_png_normal('SeaN_Large_1024.png'))
        _TEX['S'] = MipTex(load_png_normal('SeaN_Small_1024.png'))
        mac = np.flipud(np.asarray(Image.open(os.path.join(TEX, 'SeaMacro_512.png')).convert('RGB'), np.float32) / 255.0)
        _TEX['M'] = MipTex(mac)
    return _TEX


def lod_of(uv, N=1024.0):
    """footprint from neighbouring pixels (= ddx / ddy)"""
    dx = np.zeros_like(uv); dy = np.zeros_like(uv)
    dx[:, :-1] = uv[:, 1:] - uv[:, :-1]; dx[:, -1] = dx[:, -2]
    dy[:-1] = uv[1:] - uv[:-1]; dy[-1] = dy[-2]
    dx *= N; dy *= N
    return np.maximum(0.0, 0.5 * np.log2(np.maximum(np.maximum(np.sum(dx * dx, -1), np.sum(dy * dy, -1)), 1e-12)))


def unresolved(lod):
    return saturate(lod / 7.6) ** 1.15


def rot2(v, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return np.stack([v[..., 0] * c - v[..., 1] * s, v[..., 0] * s + v[..., 1] * c], -1)


def sea_normal(q, worldXZ, t, M):
    T = textures()
    rl, rsm = M['WaveRotate'][0], M['WaveRotate'][1]
    uvL = rot2(q + np.asarray(M['LargeScroll']) * t, -rl) / M['LargeTile']
    uvS = rot2(q + np.asarray(M['SmallScroll']) * t, -rsm) / M['SmallTile']
    lodL, lodS = lod_of(uvL), lod_of(uvS)
    nL = T['L'].sample(uvL, lodL).copy()
    nS = T['S'].sample(uvS, lodS).copy()
    nL[..., :2] = rot2(nL[..., :2], rl)
    nS[..., :2] = rot2(nS[..., :2], rsm)
    uvM = q / M['MacroTile']
    m = T['M'].sample(uvM, lod_of(uvM, 512.0))[..., 0]
    cp = M['CalmPatch']
    pd = np.linalg.norm(worldXZ - np.asarray(cp[:2]), axis=-1)
    m = m * (1.0 - cp[3] * (1.0 - smoothstep(0.6 * cp[2], max(cp[2], 1e-3), pd)))
    m = m * (1.0 - M['CalmAll'])
    k = M['NormalStrength'] * M['WaveAmp'] * (M['CalmStrength'] + (1 - M['CalmStrength']) * m)
    s = -(nL[..., :2] / np.maximum(nL[..., 2:3], 0.2) + nS[..., :2] / np.maximum(nS[..., 2:3], 0.2)) * k[..., None]
    if sum(M['GerstnerAmp']) > 0:
        s = s + gerstner_slope(q, t, M) * M['WaveAmp']
    var = (VAR_LARGE * unresolved(lodL) + VAR_SMALL * unresolved(lodS)) * k * k
    N = normalize(np.stack([-s[..., 0], np.ones_like(k), -s[..., 1]], -1))
    return N, var


def gerstner_slope(q, t, M):
    d1 = normalize(np.array(M['GerstnerDir'][:2], float) + [1e-5, 0]); d2 = normalize(np.array(M['GerstnerDir'][2:], float) + [0, 1e-5])
    b = normalize(d1 + d2 + 1e-5); d3 = np.array([-b[1], b[0]])
    Lw, A = M['GerstnerLength'], M['GerstnerAmp']
    w = 2 * np.pi * Lw[3]
    s = 0
    for d, lam, a, f in ((d1, Lw[0], A[0], 1.0), (d2, Lw[1], A[1], 1.27), (d3, Lw[2], A[2], 1.61)):
        k = 2 * np.pi / max(lam, 1.0)
        s = s + d * (k * a * np.cos(k * (q @ d) - w * t * f))[..., None]
    return s


def alpha_of(var, M):
    pr = 1.0 - M['Smoothness']
    return np.sqrt(pr ** 4 + var)


def fresnel(cosI, eta):
    cosI = saturate(cosI)
    sinT2 = eta * eta * (1.0 - cosI * cosI)
    tir = sinT2 >= 1.0
    cosT = np.sqrt(np.maximum(1.0 - sinT2, 0.0))
    rs = (eta * cosI - cosT) / np.maximum(eta * cosI + cosT, 1e-9)
    rp = (cosI - eta * cosT) / np.maximum(cosI + eta * cosT, 1e-9)
    return np.where(tir, 1.0, 0.5 * (rs * rs + rp * rp))


def cube(env, d, perceptual, M):
    lod = perceptual * (1.7 - 0.7 * perceptual) * 6.0
    rgb = env.lookup(d, lod) * M['ReflExposure']
    m = np.max(rgb, -1, keepdims=True)
    return np.where(m > M['ReflClamp'], rgb * (M['ReflClamp'] / np.maximum(m, 1e-9)), rgb)


def ggx_d(NdotH, a):
    a2 = a * a
    d = NdotH * NdotH * (a2 - 1.0) + 1.0
    return a2 / (np.pi * d * d + 1e-12)


def smith_vis(NdotL, NdotV, a):
    return 0.5 / (NdotL * (NdotV * (1.0 - a) + a) + NdotV * (NdotL * (1.0 - a) + a) + 1e-5)


def soft_cap(c, peak):
    m = np.max(c, -1, keepdims=True)
    return np.where(m > 1e-6, c * (peak * np.tanh(np.minimum(m / peak, 8.0)) / np.maximum(m, 1e-9)), c)


def disc_alpha(worldXZ, M):
    dc = M['DiscCenter']
    if dc[2] <= 0:
        return np.ones(worldXZ.shape[:-1])
    d = np.linalg.norm(worldXZ - np.asarray(dc[:2]), axis=-1)
    h = 0.5 * max(dc[3], 1.0)
    return 1.0 - smoothstep(dc[2] - h, dc[2] + h, d)


def above(N, V, var, env, M):
    a = alpha_of(var, M)
    NdotV = np.maximum(dot(N, V), 1e-4)
    R = 2 * dot(N, V)[..., None] * N - V
    R[..., 1] = np.abs(R[..., 1])
    F = fresnel(NdotV, 1.0 / M['IOR'])[..., None]
    refl = cube(env, R, np.sqrt(saturate(a)), M) * M['ReflGain']
    sunc = np.asarray(M['SunColor'], np.float32)
    sun = np.zeros_like(refl)
    L = normalize(np.asarray(M['SunDir'], np.float64))
    if sunc.max() > 0 and L[1] > -0.02:
        ag = np.sqrt(a * a + M['SunGlitterRough'] ** 2)
        H = normalize(L + V)
        NdotL = saturate(dot(N, L))
        NdotH = saturate(dot(N, H))
        omega = np.pi * math.radians(M.get('SunDiscRadius', 0.5 * M['SunDiscDeg'])) ** 2      # _Udon_SunDisc.y when set
        Fs = fresnel(saturate(dot(V, H)), 1.0 / M['IOR'])
        sun = sunc * (omega * ggx_d(NdotH, ag) * smith_vis(NdotL, NdotV, ag) * NdotL * Fs)[..., None]
        sun = soft_cap(sun, sunc.max() * 2.0 ** (-M['SunReflPeakEV']))
    body = np.asarray(M['WaterColor']) * (1 - F)
    return refl * F + sun + body


def refract_out(I, Na, n):
    c = dot(I, Na)
    s2 = n * n * (1.0 - c * c)
    ok = (s2 < 1.0).astype(np.float32)
    ct = np.sqrt(saturate(1.0 - s2))
    return normalize(n * I + (ct - n * c)[..., None] * Na), ok


def below(N, I, var, window_env, refl_env, M):
    side = 1.0 if M['AirSide'] >= 0 else -1.0
    Na = N.copy(); Na[..., 1] *= side
    bad = dot(I, Na) <= 1e-4
    Na[bad] = np.array([0.0, side, 0.0])
    cosI = dot(I, Na)
    F = fresnel(cosI, M['IOR'])
    Tg, okG = refract_out(I, Na, M['IOR'])
    Tr, okR = refract_out(I, Na, M['Dispersion'][0])
    Tb, okB = refract_out(I, Na, M['Dispersion'][1])
    def wc(d):
        rgb = window_env.lookup(d)
        m = np.max(rgb, -1, keepdims=True)
        return np.where(m > M['ReflClamp'], rgb * (M['ReflClamp'] / np.maximum(m, 1e-9)), rgb)
    win = np.stack([wc(Tr)[..., 0] * okR, wc(Tg)[..., 1] * okG, wc(Tb)[..., 2] * okB], -1)
    win = win * np.asarray(M['WindowTint'][:3]) * (M['WindowGain'] * M['IOR'] ** 2)
    crit = math.asin(1.0 / M['IOR'])
    th = np.arccos(saturate(cosI))
    thV = np.arccos(saturate(np.abs(I[..., 1])))
    if len(M['WindowTint']) > 3 and M['WindowTint'][3] > 0:
        wr = saturate(thV / crit)
        win = win + (luma(win)[..., None] - win) * (min(M['WindowTint'][3], 1.0) * (1.0 - wr * wr))[..., None]
    wc_ = M['WindowCore']
    if wc_[3] > 0:
        capL = wc_[0] * 2.0 ** (-wc_[1] * saturate(thV / crit) ** max(wc_[2], 0.01))
        lw = luma(win)
        win = win * np.where(lw > 1e-6, capL * np.tanh(np.minimum(lw / capL, 8.0)) / np.maximum(lw, 1e-9), 1.0)[..., None]
    edge = 1.0 - smoothstep(crit - math.radians(M['WindowEdgeSoft']), crit, th)
    wr = M['WindowRadial']
    edge = edge * (1.0 + (wr[0] - 1.0) * saturate(th / crit) ** max(wr[1], 0.01))
    wsun = 0.0
    wcover = 0.0
    if max(M['WindowSunColor']) > 0:
        Nf = np.broadcast_to(np.array([0.0, side, 0.0]), I.shape)
        Tf, okF = refract_out(I, Nf, M['IOR'])
        cosF = dot(I, Nf)
        Ff = fresnel(cosF, M['IOR'])
        thF = np.arccos(saturate(cosF))
        hor = normalize(I * np.array([1.0, 0.0, 1.0]) + np.array([0.0, side * 1e-3, 0.0]))
        Tr2 = np.where(okF[..., None] > 0.5, Tf, hor)
        sd = normalize(np.asarray(M['WindowSunDir'][:3], float))
        dEl = np.degrees(np.arcsin(np.clip(np.abs(Tr2[..., 1]), 0, 1)) - math.asin(min(abs(sd[1]), 1.0)))
        th2 = normalize(Tr2[..., [0, 2]] + np.array([1e-5, 0.0])); sh = normalize(sd[[0, 2]] + np.array([1e-5, 0.0]))
        dAz = np.degrees(np.arccos(np.clip(th2 @ sh, -1, 1)))
        re, ra = max(M['WindowSunDir'][3], 0.05), max(M['WindowSunSpread'], 0.05)
        rim = np.exp(-(np.degrees(thF - crit) / max(M['WindowEdgeSoft'] * 1.5, 0.3)) ** 2)
        e0 = math.degrees(math.asin(min(abs(sd[1]), 1.0))) / re
        arc = np.where(okF > 0.5, np.exp(-(dEl / re) ** 2), rim * math.exp(-e0 * e0)) \
            * (0.7 * np.exp(-(dAz / ra) ** 2) + 0.3 * np.exp(-(dAz / (0.12 * ra)) ** 2))
        wsun = np.asarray(M['WindowSunColor'])[None, None, :] * (arc * np.maximum(1 - Ff, M['WindowSunFloor']) * M['WindowSunGain'])[..., None]
        wcover = saturate(arc * 1.5)
    R = I - 2 * dot(I, Na)[..., None] * Na
    mirror = np.broadcast_to(np.asarray(M['TIRColor'], np.float32), win.shape).copy()
    if M['TIRCubeGain'] > 0 and refl_env is not None:
        mirror += cube(refl_env, R, np.sqrt(saturate(alpha_of(var, M))), M) * M['TIRCubeGain']
    return mirror * F[..., None] + win * ((1 - F) * edge * (1 - wcover))[..., None] + wsun


def lin_to_oklab(c):
    M1 = np.array([[0.4122214708, 0.5363325363, 0.0514459929], [0.2119034982, 0.6806995451, 0.1073969566], [0.0883024619, 0.2817188376, 0.6299787005]])
    M2 = np.array([[0.2104542553, 0.7936177850, -0.0040720468], [1.9779984951, -2.4285922050, 0.4505937099], [0.0259040371, 0.7827717662, -0.8086757660]])
    return np.cbrt(np.maximum(c @ M1.T, 0.0)) @ M2.T


def oklab_to_lin(L):
    M1 = np.array([[1.0, 0.3963377774, 0.2158037573], [1.0, -0.1055613458, -0.0638541728], [1.0, -0.0894841775, -1.2914855480]])
    M2 = np.array([[4.0767416621, -3.3077115913, 0.2309699292], [-1.2684380046, 2.6097574011, -0.3413193965], [-0.0041960863, -0.7034186147, 1.7076147010]])
    return np.maximum((L @ M1.T) ** 3 @ M2.T, 0.0)


_PC = {}


def purple_ceiling(which='main'):
    """Sea_PurpleCeiling.png (RGBA = S6, S7a, S7b, S8) or Sea_PurpleCeiling_S11.png; row 0 = L 0 of quarter lo1"""
    if which not in _PC:
        name = 'Sea_PurpleCeiling.png' if which == 'main' else 'Sea_PurpleCeiling_%s.png' % which
        _PC[which] = np.flipud(np.asarray(Image.open(os.path.join(TEX, name)).convert('RGBA'), np.float64)) / 255.0 * 0.8
    return _PC[which]


def purple_guard(c, M):
    """port of LanbaiPurpleGuard: a colour inside violet band 1 goes down to s = lo1, inside band 2 to s = lo2 (D-17 + D-21)"""
    M = dict(DEFAULTS, **M)
    if M['PurpleGuard'][0] <= 0:
        return c
    c = np.asarray(c, np.float64)
    o = lin_to_oklab(c)
    L = o[..., 0]
    C = np.hypot(o[..., 1], o[..., 2])
    t = purple_ceiling(M['PurpleCeiling'])
    Q = t.shape[0] // 4
    Wt = t.shape[1]
    col = np.floor((np.degrees(np.arctan2(o[..., 2], o[..., 1])) % 360.0) / 360.0 * Wt).astype(np.int64) % Wt
    row = np.clip(np.floor(L / 0.025 + 0.5).astype(np.int64), 0, Q - 1)      # POINT sampling (the importer sets Point)
    m = np.asarray(M['PurpleMask'], np.float64) > 0

    def quarter(q, empty, red):
        val = t[row + q * Q, col]
        return red(np.where(m, val, empty), -1)
    lo1, hi1 = quarter(0, 1e3, np.min), quarter(1, -1.0, np.max)
    lo2, hi2 = quarter(2, 1e3, np.min), quarter(3, -1.0, np.max)
    s = C / np.maximum(L, 1e-6)
    in1 = (s > lo1) & ((s <= hi1 + 1e-4) | (hi1 >= 0.799))
    in2 = (s > lo2) & ((s <= hi2 + 1e-4) | (hi2 >= 0.799))
    tg = np.where(in1, lo1, np.where(in2, lo2, s))
    k = np.where((L > 1e-5) & (C > 1e-6) & (tg < s), tg / np.maximum(s, 1e-9), 1.0)
    o[..., 1:] *= k[..., None]
    return np.where((k < 1.0)[..., None], oklab_to_lin(o), c)


def ceiling_progress(I, M):
    if M['DissolveTime'] < 0:
        return np.zeros(I.shape[:-1])
    el = np.degrees(np.arcsin(saturate(I[..., 1])))
    return saturate((M['DissolveTime'] - M['DissolveFront'] * el / 90.0) / max(M['DissolvePixel'], 0.01))


def luma(c):
    return c[..., 0] * 0.2126 + c[..., 1] * 0.7152 + c[..., 2] * 0.0722


def ev_linear_alpha(Lc, Ls, p):
    Lc = np.maximum(Lc, 1e-5); Ls = np.maximum(Ls, 1e-5)
    same = np.abs(Lc - Ls) < 1e-3
    Lp = 2.0 ** ((1 - p) * np.log2(Lc) + p * np.log2(Ls))
    return np.where(same, 1.0 - p, saturate((Lp - Ls) / np.where(same, 1.0, Lc - Ls)))


def ceiling_lamps(P, Nw, V, a, eta, M):
    """port of LanbaiCeilingLamps (Rain's convention: E * NdotL * Vis * pi * D * F; tubes; cones)"""
    out = np.zeros(P.shape)
    R = 2 * dot(Nw, V)[..., None] * Nw - V
    for lamp in M['Lamps']:                         # (xyz, intensity, linear rgb, radius[, axis xyz, dir xyzw])
        pos, I0, col, rad = lamp[:4]
        axis = np.asarray(lamp[4] if len(lamp) > 4 else (0.0, 0.0, 0.0), np.float64)
        dirw = np.asarray(lamp[5] if len(lamp) > 5 else (0.0, 0.0, 0.0, -1.0), np.float64)
        toC = np.asarray(pos) - P
        d2 = np.maximum(np.sum(toC * toC, -1), 1e-2)
        Lvec = toC
        seg = 2.0 * axis
        sl2 = float(seg @ seg)
        lineNorm = 1.0
        if sl2 > 1e-6:
            L0 = toC - axis
            RoS = R @ seg
            tt = saturate((dot(R, L0) * RoS - L0 @ seg) / np.maximum(sl2 - RoS * RoS, 1e-6))
            Lvec = L0 + seg * tt[..., None]
            lineNorm = a / saturate(a + 0.5 * math.sqrt(sl2) / (2.0 * np.sqrt(d2)))
        c2r = dot(Lvec, R)[..., None] * R - Lvec
        closest = Lvec + c2r * saturate(rad / np.maximum(np.linalg.norm(c2r, axis=-1), 1e-5))[..., None]
        L = normalize(closest)
        dL = np.maximum(np.linalg.norm(Lvec, axis=-1), 1e-3)
        aP = saturate(a + rad / (2 * dL))
        sphereNorm = (a / aP) ** 2
        NdotL = saturate(dot(Nw, L)); NdotV = np.maximum(dot(Nw, V), 1e-4)
        H = normalize(L + V)
        F = fresnel(saturate(dot(V, H)), eta)
        cone = 1.0 if dirw[3] <= -0.999 else smoothstep(dirw[3] - 0.08, dirw[3] + 0.08, normalize(-toC) @ dirw[:3])
        E = I0 / d2 * cone
        out += np.asarray(col) * (E * NdotL * smith_vis(NdotL, NdotV, a) * np.pi * sphereNorm * lineNorm * ggx_d(saturate(dot(Nw, H)), a) * F)[..., None]
    return out


def ceiling(N, I, var, worldXZ, refl_env, behind_env, M, P=None):
    Nw = N.copy(); Nw[..., 1] *= -1.0
    cosI = saturate(dot(-I, Nw))
    F = fresnel(cosI, 1.0 / M['IOR'])[..., None]
    R = I - 2 * dot(I, Nw)[..., None] * Nw
    R[..., 1] = -np.abs(R[..., 1])
    a = alpha_of(var, M)
    refl = cube(refl_env, R, np.sqrt(saturate(a)), M) * M['ReflGain'] * np.asarray(M['MirrorTint'])
    c = refl * F + np.asarray(M['WaterColor']) * (1 - F)
    if M['LampGlints'] > 0:
        c = c + ceiling_lamps(P, Nw, -I, a, 1.0 / M['IOR'], M) * M['LampGlints']
    alpha = disc_alpha(worldXZ, M)
    p = ceiling_progress(I, M)
    if np.any(p > 0):
        sky = behind_env.lookup(I)
        alpha = alpha * np.where(p > 0, ev_linear_alpha(luma(c), luma(sky), p), 1.0)
    return c, alpha


# ------------------------------------------------------------------------------------------------ fog (LanbaiFog port)
def fog(col, P, eye, density, horizon_fn):
    d = np.linalg.norm(P - eye, axis=-1)
    f = (1.0 - np.exp(-density * d))[..., None]
    return col * (1 - f) + horizon_fn(normalize(P - eye)) * f


def water_horizon(up, mid, down):
    up, mid, down = (np.asarray(x, np.float32) for x in (up, mid, down))

    def fn(d):
        y = d[..., 1:2]
        a = mid + (up - mid) * smoothstep(0.0, 1.0, np.maximum(y, 0))
        b = mid + (down - mid) * smoothstep(0.0, 1.0, np.maximum(-y, 0))
        return np.where(y >= 0, a, b)
    return fn


# ------------------------------------------------------------------------------------------------ camera
def camera_rays(W, H, hfov_deg, yaw_deg=0.0, pitch_deg=0.0):
    """unit view rays [H, W, 3], row 0 = top of the image. yaw: + turns right, pitch: + looks up."""
    tx = math.tan(math.radians(hfov_deg) / 2)
    ty = tx * H / W
    xs = (np.arange(W) + 0.5) / W * 2 - 1
    ys = 1 - (np.arange(H) + 0.5) / H * 2
    X, Y = np.meshgrid(xs * tx, ys * ty)
    d = normalize(np.stack([X, Y, np.ones_like(X)], -1))
    cp, sp = math.cos(math.radians(pitch_deg)), math.sin(math.radians(pitch_deg))
    d = np.stack([d[..., 0], d[..., 1] * cp + d[..., 2] * sp, -d[..., 1] * sp + d[..., 2] * cp], -1)
    cy, sy = math.cos(math.radians(yaw_deg)), math.sin(math.radians(yaw_deg))
    d = np.stack([d[..., 0] * cy + d[..., 2] * sy, d[..., 1], -d[..., 0] * sy + d[..., 2] * cy], -1)
    return d


def shade_plane(eye, rays, level, mode, t, M, env=None, window_env=None, behind_env=None, offset=(0.0, 0.0)):
    """intersect y = level; returns (rgb, alpha, hit mask, P). mode: 'above' | 'below' | 'ceiling'"""
    M = dict(DEFAULTS, **M)
    dy = rays[..., 1]
    s = (level - eye[1]) / np.where(np.abs(dy) < 1e-9, 1e-9, dy)
    hit = s > 0
    P = eye + rays * np.where(hit, s, 0.0)[..., None]
    q = P[..., [0, 2]] + np.asarray(offset)
    N, var = sea_normal(q, P[..., [0, 2]], t, M)
    I = rays
    if mode == 'above':
        rgb = above(N, -I, var, env, M)
        alpha = disc_alpha(P[..., [0, 2]], M)
    elif mode == 'below':
        rgb = below(N, I, var, window_env, env, M)
        alpha = np.ones(rgb.shape[:-1])
    else:
        rgb, alpha = ceiling(N, I, var, P[..., [0, 2]], env, behind_env, M, P)
    return rgb, alpha, hit, P
