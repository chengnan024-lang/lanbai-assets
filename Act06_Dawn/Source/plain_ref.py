# -*- coding: utf-8 -*-
"""Lanbai/CloudPlain（第 6 幕的云原 / 云峡 / 云唇 / 云盖）的 numpy 移植：参考渲染用它，和 Shaders/Lanbai_CloudPlain.shader
的 frag 逐段对应（段名相同）。思路来自门的 GateCloudDeck（GateClouds/Source/deck_ref.py：周期贴图的高度场、自适应步进、
烘好的日光路径与朝日 N·L），这里推广成一整块云：
    顶面 Htop(xz) = 云原顶 + 起伏（门的两张周期贴图，按日光重烘：Textures/Plain_*）× 尺度 K
    底面 B = 云盖底（平）
    区域：云原的边（朝日一侧 4.58 km，其余 ~8.2 km，软边）、峡谷（宽 1 km、沿方位 25°，F1 起 6 s 张开，谷底是 34 m 的薄雾层）、
          峡谷尽头的云唇（顶在 −729：太阳在车出云盖底时落到它后面，F1b1 从朝日的边下面回来）
    云 = { B < y < Htop }。每条视线（向下、向上都可以）在这块云的上下包络之间步进，找到第一次进云的点。
着色：朝日的面 = 日色 × N·L（顶面用烘好的 N·L，墙面用高度场的几何法线）× 前面的云投下的影（顶面：烘好的光路；
墙 / 谷 / 底面：朝太阳 16 步查云体）+ 天光 × AO（朝上）+ 地光（朝下：云盖底）+ 多次散射；然后 LanbaiFog。
颜色常数和云卡同一组（Clouds_v2/Textures/cards_v2.json colours.dawn），云原和云卡是同一种光。
"""
import os
import sys
import json
import math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
sys.path.insert(0, os.path.join(REPO, 'Clouds_v2', 'Source'))
import lb_common as C  # noqa: E402

LAYOUT = json.load(open(os.path.join(KIT, 'Act06_Layout.json')))
CARDS = json.load(open(os.path.join(REPO, 'Clouds_v2', 'Textures', 'cards_v2.json')))
COL = CARDS['colours']['dawn']

K_SCALE = 2.0             # the gate's tiles at 2x: heads up to ~90 m, 3.2 km detail period (seen from 470 m, not 40 m)
P = dict(
    Steps=96, StepC=0.9, Slope=0.35, KMin=0.004, KMax=0.06, DtMax=250.0, Bisect=4, MarchMax=16000.0,
    DetailMin=-12.0 * K_SCALE, DetailMax=56.0 * K_SCALE, MacroMin=-12.0 * K_SCALE, MacroMax=12.0 * K_SCALE,
    TauMaxD=160.0 * K_SCALE, TauMaxM=400.0 * K_SCALE, AmpMin=0.3, AmpMax=0.8, VarMin=0.85, VarMax=1.1,
    PeriodD=1600.0 * K_SCALE, PeriodM=6400.0 * K_SCALE, MicroScale=5.0, MicroAmp=4.0 * K_SCALE, MicroShade=0.6,
    SigmaL=0.012, SurfShadow=1.0, MsK=0.004, MsTau=0.25, SunGain=1.0, SkyGain=0.35, GroundGain=0.35,
    WallSlope=1.5, WallWrap=0.35, WallNormalPx=3.0, WallNormalMin=20.0, ShadowSteps=16, ShadowLen=6000.0, EdgeGlow=0.9, EdgeGlowLen=900.0,
    RimK=250.0, RimGain=0.8, RimDepth=60.0, UnderGround=0.25, UnderSky=0.04,
    TroughLod=3.5, TroughDepth=30.0, TroughK=0.35, FogDensity=0.00012, FogCap=1.0,
)
SUN = np.array(LAYOUT['sun']['dir'], float)
BODY = LAYOUT['body']
SUN_COL = np.array(COL['SunColor'])            # E x colour (linear), the cards' solve
SKY_COL = np.array(COL['SkyUpColor'])          # light from the upper dome (radiance; a white Lambert facing up sees it x 1)
GND_COL = np.array(COL['GroundColor'])


class MipTex:
    def __init__(self, path):
        a = np.asarray(Image.open(path)).astype(np.float32) / 255.0
        self.levels = [a]
        while a.shape[0] > 1:
            a = 0.25 * (a[0::2, 0::2] + a[1::2, 0::2] + a[0::2, 1::2] + a[1::2, 1::2])
            self.levels.append(a)
        self.n = self.levels[0].shape[0]

    def _bil(self, lvl, u, v):
        A = self.levels[lvl]
        n = A.shape[0]
        x, y = u * n - 0.5, v * n - 0.5
        x0, y0 = np.floor(x).astype(np.int64), np.floor(y).astype(np.int64)
        fx, fy = (x - x0)[..., None], (y - y0)[..., None]
        x0 %= n; y0 %= n
        x1, y1 = (x0 + 1) % n, (y0 + 1) % n
        return A[y0, x0] * (1 - fx) * (1 - fy) + A[y0, x1] * fx * (1 - fy) + A[y1, x0] * (1 - fx) * fy + A[y1, x1] * fx * fy

    def sample(self, u, v, lod):
        lod = np.clip(lod, 0, len(self.levels) - 1)
        l0 = np.floor(lod).astype(np.int64)
        f = (lod - l0)[..., None]
        out = np.zeros(np.shape(u) + (4,), np.float32)
        for L in np.unique(l0):
            m = l0 == L
            a = self._bil(L, u[m], v[m])
            b = self._bil(min(L + 1, len(self.levels) - 1), u[m], v[m])
            out[m] = a * (1 - f[m]) + b * f[m]
        return out


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


def sig(x):
    return 1.0 / (1.0 + np.exp(np.clip(x, -60, 60)))


# ---- [Region] (shader: Region())
WALL_P, WALL_AMP = 700.0, 110.0      # the slot walls bulge: the detail tile over (along the axis, height), +-110 m


def region(x, z, slot_open, y=None, det=None, foot=None):
    S, E, Lp = BODY['slot'], BODY['edge'], BODY['lip']
    r = np.hypot(x, z)
    az = np.degrees(np.arctan2(x, z))
    da = ((az - LAYOUT['sun']['az_deg'] + 180) % 360) - 180
    R = E['r0'] + (E['r_sun'] - E['r0']) * np.exp(-(da / E['sun_lobe_deg']) ** 2)
    deck = sig((r - R) / (0.25 * E['soft']))
    a = math.radians(S['axis_az'])
    s = x * math.sin(a) + z * math.cos(a)
    q = x * math.cos(a) - z * math.sin(a) - S.get('center_q', 0.0)
    hw = S['half_width'] * slot_open
    aq = np.abs(q)
    if det is not None and y is not None:
        # [WallBulge] cauliflower walls: a 2-D sample of the detail tile at (along, height), mirrored per side
        lod = np.log2(np.maximum(foot, 1e-3) / (WALL_P / det.n))
        nz = det.sample(s / WALL_P + np.where(q > 0, 0.31, 0.0), y / WALL_P, lod)[:, 0]
        aq = aq + WALL_AMP * (nz - 0.5) * 2.0 * slot_open
    inw = sig((aq - hw) / (0.25 * S['soft'])) * (slot_open > 1e-3)
    slot = inw * sig((S['s0'] - s) / (0.25 * S['soft'])) * sig((s - S['s1']) / (0.25 * S['soft']))
    lip = inw * sig((S['s1'] - s) / (0.25 * Lp['soft']))
    return deck, slot, lip


_FOGSKY = {}


def fog_sky(sky_eq):
    """the sky low-passed (~6 deg) with the sun disc clamped away: LanbaiHorizon is a smooth gradient, it has no disc"""
    k = id(sky_eq)
    if k not in _FOGSKY:
        from scipy.ndimage import gaussian_filter
        s = np.minimum(sky_eq, np.percentile(sky_eq, 99.0, axis=(0, 1)))
        px = 6.0 / 360.0 * s.shape[1]
        _FOGSKY[k] = np.stack([gaussian_filter(s[..., i], px, mode='wrap') for i in range(3)], -1)
    return _FOGSKY[k]


FOGB = LAYOUT['fog']['model_b']           # the dawn preset (Sky/FogPresets.json) + act 6's own far / nadir (D-35 #3)
FOG_K = 1.0                               # the fog colour scale (under the cover: < 1; act06_ref sets it per frame)
FOG_USE_ACT = True                        # False: the preset as it is (for the comparison in the README)


def horizon_b(V, F=None):
    """LanbaiHorizon model B (Common/Shaders/LanbaiSky.cginc LanbaiHorizonGradient), line for line"""
    F = F or FOGB
    near, zen = np.array(F['near']), np.array(F['zenith'])
    far = np.array(F['far_act06'] if FOG_USE_ACT else F['far'])
    nad = np.array(F['nadir_act06'] if FOG_USE_ACT else F['nadir'])
    el = np.degrees(np.arcsin(np.clip(V[:, 1], -1, 1)))
    T = np.array(F['band_dir'][:3])
    th = T[[0, 2]] + np.array([1e-5, 0.0]); th /= np.linalg.norm(th)
    vh = V[:, [0, 2]] + np.array([1e-5, 0.0]); vh /= np.linalg.norm(vh, axis=-1, keepdims=True)
    az = np.degrees(np.arccos(np.clip(vh @ th, -1, 1)))
    wd = F['width_act06'] if FOG_USE_ACT else F['width']
    hz = near[None] + (far - near)[None] * ss(0.0, max(wd, 1.0), az)[:, None]
    sh, be = F['shape'], F['below']
    lo, hi = sh[0], min(max(sh[1], sh[0] + 0.1), 90.0)
    x = np.clip((el - lo) / max(hi - lo, 1e-4), 0, 1)
    up = (x * x * (3 - 2 * x)) ** (sh[2] if sh[2] > 0 else 1.0)
    dn = ss(be[1], min(be[0], be[1] - 0.1), el) ** (be[2] if be[2] > 0 else 1.0)
    fl = 1e-3 * np.maximum(hz.max(-1, keepdims=True), zen.max()) + 1e-7
    c = np.exp2(np.log2(np.maximum(hz, fl)) * (1 - up)[:, None] + np.log2(np.maximum(zen[None], fl)) * up[:, None])
    return (c * (1 - dn)[:, None] + nad[None] * dn[:, None]) * FOG_K


def fog_colour(sky_eq, V):
    """r3: LanbaiHorizon model B exactly as Unity computes it (the dawn preset's numbers, with act 6's far / nadir)"""
    return horizon_b(V)


MIST = BODY.get('mist')


def mist_cum(y):
    """integral of the mist density from the cover bottom up to y (the tent profile), per metre of height"""
    M = MIST
    yb, yp, yt, sg = M['y_bot'], M['y_peak'], M['y_top'], M['sigma']
    y = np.clip(y, yb, yt)
    lo = np.minimum(y, yp) - yb
    a = 0.5 * sg * lo * lo / (yp - yb)
    hi = np.maximum(y - yp, 0.0)
    b = sg * hi - 0.5 * sg * hi * hi / (yt - yp)
    return a + b


def mist_sigma(y):
    M = MIST
    up = M['sigma'] * (M['y_top'] - y) / (M['y_top'] - M['y_peak'])
    dn = M['sigma'] * (y - M['y_bot']) / (M['y_peak'] - M['y_bot'])
    return np.clip(np.where(y > M['y_peak'], up, dn), 0.0, None) * ((y < M['y_top']) & (y > M['y_bot']))


_MIST_TEX = {}


def _mist_noise(x, z, period, drift_m, off, lod=3.0):
    """the detail tile's height (R), low-passed (lod 3), at (xz - axis * drift) / period"""
    if 'det' not in _MIST_TEX:
        _MIST_TEX['det'] = MipTex(os.path.join(KIT, 'Textures', 'Plain_Detail_1024.png'))
    a = math.radians(BODY['slot']['axis_az'])
    u = (x - math.sin(a) * drift_m) / period + off
    v = (z - math.cos(a) * drift_m) / period + off * 0.7
    n = _MIST_TEX['det'].sample(u, v, np.broadcast_to(lod, np.shape(u)).astype(np.float64))[..., 0]
    return np.clip((n - 0.1) / 0.45, 0.0, 1.0)            # the tile's R spans ~0.06 .. 0.59 at lod 3: to 0 .. 1


def mist_wedge(x, z):
    """the clear wedge toward the sun (from the bus): 1 = clear (D-35 #1)"""
    r = np.hypot(x, z)
    sx, sz = SUN[0], SUN[2]
    c = (x * sx + z * sz) / np.maximum(r * math.hypot(sx, sz), 1e-6)
    c0, c1 = math.cos(math.radians(MIST['wedge_zero_deg'])), math.cos(math.radians(MIST['wedge_full_deg']))
    return ss(c0, c1, c) * (r >= 1.0)


def mist_sigma_top(y, yt):
    """the tent with a moving top yt (per sample)"""
    M = MIST
    up = M['sigma'] * (yt - y) / np.maximum(yt - M['y_peak'], 1.0)
    dn = M['sigma'] * (y - M['y_bot']) / (M['y_peak'] - M['y_bot'])
    return np.clip(np.where(y > M['y_peak'], up, dn), 0.0, None) * ((y < yt) & (y > M['y_bot']))


def mist(eye_world, V, d_root, t_end, slot_open=1.0, clock=0.0):
    """[Mist] r3 (D-35 #1 / #4): the slot's lower mist + drifting wisps, a 16-sample march over the part of the segment
    eye -> eye + V t_end inside the mist's height band. Density: the tent in y x the slot x (1 - the clear wedge toward
    the sun) x a slow low-contrast undulation; wisps: a thin layer above it, cut by a drifting noise. Colour: the shadow
    blue-grey, darker downward, brighter toward the sun. Returns transmittance (N,) and premultiplied colour (N, 3)."""
    M = MIST
    ro = np.array(eye_world, float) - np.array([0.0, d_root, 0.0])
    n = len(V)
    vy = V[:, 1]
    te = np.minimum(t_end, P['MarchMax'])
    ylo, yhi = M['y_bot'], max(M['y_top'] + M['roll_amp'], M['wisp_hi'])
    with np.errstate(divide='ignore', invalid='ignore'):
        ta = (ylo - ro[1]) / vy
        tb = (yhi - ro[1]) / vy
    flat = np.abs(vy) < 1e-6
    inband = (ro[1] > ylo) & (ro[1] < yhi)
    t_in = np.where(flat, 0.0, np.maximum(np.minimum(ta, tb), 0.0))
    t_out = np.where(flat, np.where(inband, te, 0.0), np.maximum(ta, tb))
    t_out = np.minimum(np.minimum(t_out, te), t_in + M['max_len'])
    L = np.maximum(t_out - t_in, 0.0)
    T = np.ones(n)
    col = np.zeros((n, 3))
    live = L > 0
    if not live.any():
        return T, col
    base = np.array(M['color_linear'])
    k0, k1, k2 = M['phase']
    ph = (k0 + k1 * np.exp((V @ SUN - 1.0) * k2))[live]
    Vl, tin, Ll = V[live], t_in[live], L[live]
    Tl = np.ones(len(Vl)); Cl = np.zeros((len(Vl), 3))
    gate_v = ss(M['wedge_vy'][0], M['wedge_vy'][1], Vl[:, 1])      # the clear lane only for rays at / above the horizon
    gate_v = gate_v * ss(M['y_bot'] - 30.0, M['y_bot'], ro[1])     # and only while the eye is above the cover bottom
    N = int(M['steps'])
    for i in range(N):
        # quadratic spacing: fine where the mist starts (what is seen), coarse deep inside it
        u = (i + 0.5) / N
        t = tin + Ll * u * u
        ds = Ll * 2.0 * u / N
        # the noise is filtered to the sample spacing (no aliasing streaks on long, flat segments)
        lod_u = np.maximum(4.0, np.log2(np.maximum(ds, 1e-3) / (M['und_period'] / 1024.0)))
        lod_w = np.maximum(3.0, np.log2(np.maximum(ds, 1e-3) / (M['wisp_period'] / 1024.0)))
        p = ro[None, :] + Vl * t[:, None]
        y = p[:, 1]
        w = region(p[:, 0], p[:, 2], slot_open)[1] * (1.0 - mist_wedge(p[:, 0], p[:, 2]) * gate_v)
        und = 1.0 + M['und_amp'] * (2.0 * _mist_noise(p[:, 0], p[:, 2], M['und_period'], M['und_drift'] * clock, 0.13, lod_u) - 1.0)
        # a rolling top (+-roll_amp m, slow): mounds above the mean top are lit, hollows below it are darker
        roll = M['roll_amp'] * (2.0 * _mist_noise(p[:, 0], p[:, 2], M['roll_period'], M['und_drift'] * clock, 0.71,
                                                 np.maximum(3.0, np.log2(np.maximum(ds, 1e-3) / (M['roll_period'] / 1024.0)))) - 1.0)
        sg = mist_sigma_top(y, M['y_top'] + roll) * und
        wn = ss(M['wisp_cut'][0], M['wisp_cut'][1], _mist_noise(p[:, 0], p[:, 2], M['wisp_period'], M['wisp_drift'] * clock, 0.41, lod_w))
        wt = np.clip(np.where(y < M['wisp_mid'], (y - M['wisp_lo']) / (M['wisp_mid'] - M['wisp_lo']),
                              (M['wisp_hi'] - y) / (M['wisp_hi'] - M['wisp_mid'])), 0, 1)
        sw = M['wisp_sigma'] * wt * wn
        sig = (sg + sw) * w
        a = 1.0 - np.exp(-sig * ds)
        f = np.clip((M['y_top'] + M['roll_amp'] - y) / M['shade_depth'], 0, 1)
        shade = 1.0 - M['shade_dark'] * f ** M['shade_pow']
        cm = shade * (1.0 + M['und_col'] * (und - 1.0) / M['und_amp'])
        c = (cm * sg + 1.12 * sw) / np.maximum(sg + sw, 1e-9)            # wisps a little lighter
        Cl += (Tl * a * c * ph)[:, None] * base[None, :]
        Tl *= 1.0 - a
    T[live] = Tl
    col[live] = Cl
    return T, col


class Plain:
    def __init__(self, tex_dir=os.path.join(KIT, 'Textures')):
        self.det = MipTex(os.path.join(tex_dir, 'Plain_Detail_1024.png'))
        self.mac = MipTex(os.path.join(tex_dir, 'Plain_Macro_512.png'))
        self.texel_d = P['PeriodD'] / self.det.n
        self.texel_m = P['PeriodM'] / self.mac.n

    # ---- [Field] (shader: Field()): top surface, bottom, margin (> 0 inside cloud) at local points
    def field(self, p, foot, slot_open):
        x, y, z = p[:, 0], p[:, 1], p[:, 2]
        dd = self.det.sample(x / P['PeriodD'], z / P['PeriodD'], np.log2(np.maximum(foot, 1e-3) / self.texel_d))
        mm = self.mac.sample(x / P['PeriodM'], z / P['PeriodM'], np.log2(np.maximum(foot, 1e-3) / self.texel_m))
        hd = P['DetailMin'] + dd[:, 0] * (P['DetailMax'] - P['DetailMin'])
        hm = P['MacroMin'] + mm[:, 0] * (P['MacroMax'] - P['MacroMin'])
        amp = P['AmpMin'] + mm[:, 2] * (P['AmpMax'] - P['AmpMin'])
        lod_u = np.log2(np.maximum(foot, 1e-3) * P['MicroScale'] / self.texel_d)
        mu = np.full(len(x), 0.45)
        near = lod_u < 3.5
        if near.any():
            mu[near] = self.det.sample(x[near] * P['MicroScale'] / P['PeriodD'] + 0.37,
                                       z[near] * P['MicroScale'] / P['PeriodD'] + 0.61, np.maximum(lod_u[near], 0))[:, 0]
        fade = 1 - ss(1.0, 3.5, lod_u)
        micro = P['MicroAmp'] * ((mu - 0.45) * fade + 0.35 * (1 - fade))
        rel = hm + amp * (hd + micro)
        deck, slot, lip = region(x, z, slot_open, y, self.det, foot)
        top = BODY['top'] + rel
        top = top + (BODY['lip']['top'] + 0.3 * rel - top) * lip
        top = top + (BODY['slot']['floor_top'] - 50.0 - top) * slot      # r2: no floor (50 m under the bottom: open)
        bot = np.full(len(x), BODY['bottom'])
        top = bot + (top - bot) * ss(0.2, 0.8, deck)
        m = np.minimum(top - y, y - bot)
        return m, top, bot, dd, mm, amp, deck, slot, lip

    def tau(self, dd, mm, amp):
        return P['SigmaL'] * (amp * dd[:, 1] * P['TauMaxD'] + mm[:, 1] * P['TauMaxM'])

    def sun_shadow(self, p, slot_open):
        """coarse: fraction of the sun line (16 steps, exponential) clear of the MEAN body (no relief)"""
        vis = np.ones(len(p))
        s = 120.0                                   # beyond the wall bulges (WALL_AMP): no self-speckle
        for _ in range(P['ShadowSteps']):
            q = p + SUN[None, :] * s
            deck, slot, lip = region(q[:, 0], q[:, 2], slot_open)
            top = BODY['top'] + (BODY['lip']['top'] - BODY['top']) * lip
            top = top + (BODY['slot']['floor_top'] - top) * slot
            inside = (q[:, 1] < top) & (q[:, 1] > BODY['bottom']) & (deck > 0.5)
            vis = vis * np.where(inside, 0.55, 1.0)  # soft: each occupied sample takes 45 % (transmittance-like)
            s *= (P['ShadowLen'] / 120.0) ** (1.0 / P['ShadowSteps'])
        return vis

    def render(self, eye_world, V, pix_ang, d_root, sky_eq, slot_open=1.0):
        """eye_world (3,), V (N,3) unit rays, pix_ang (rad per pixel), d_root = R_Dawn.y.
        Returns colour (N,3) linear, hit (N,) bool, distance (N,)."""
        ro = np.array(eye_world, float) - np.array([0.0, d_root, 0.0])          # local
        n = len(V)
        vy = V[:, 1]
        y_hi = BODY['top'] + P['MacroMax'] + P['DetailMax'] * P['AmpMax'] + 10
        y_lo = BODY['bottom'] - 1.0
        # slab [y_lo, y_hi] along each ray
        with np.errstate(divide='ignore', invalid='ignore'):
            ta = (y_hi - ro[1]) / vy
            tb = (y_lo - ro[1]) / vy
        t0 = np.where(np.abs(vy) > 1e-6, np.maximum(np.minimum(ta, tb), 0.0), 0.0)
        t1 = np.where(np.abs(vy) > 1e-6, np.maximum(ta, tb), P['MarchMax'])
        inside_slab = (ro[1] < y_hi) & (ro[1] > y_lo)
        t0 = np.where(inside_slab, 0.5, t0)
        t1 = np.minimum(t1, P['MarchMax'])
        live = t1 > t0
        col = np.zeros((n, 3))
        hit = np.zeros(n, bool)
        dist = np.full(n, np.inf)
        tcur = t0 + 0.5
        tprev = t0.copy()
        mprev = np.full(n, -1e9)
        idx_all = np.arange(n)
        for it in range(P['Steps']):
            act = live & ~hit & (tprev < t1)
            if not act.any():
                break
            idx = idx_all[act]
            tm = np.minimum(tcur[idx], t1[idx])
            p = ro + V[idx] * tm[:, None]
            foot = np.maximum(tm * pix_ang, 1e-3) / np.maximum(np.abs(vy[idx]), 0.05) ** 0.5
            m = self.field(p, foot, slot_open)[0]
            entered = m > 0
            if entered.any():
                hi_i = idx[entered]
                lo, hi_ = tprev[hi_i], tm[entered]
                for _ in range(P['Bisect']):
                    mid = 0.5 * (lo + hi_)
                    pm = ro + V[hi_i] * mid[:, None]
                    mmid = self.field(pm, np.maximum(mid * pix_ang, 1e-3), slot_open)[0]
                    inn = mmid > 0
                    hi_ = np.where(inn, mid, hi_)
                    lo = np.where(inn, lo, mid)
                dist[hi_i] = 0.5 * (lo + hi_)
                hit[hi_i] = True
            tprev[idx] = tm
            dt = np.clip(P['StepC'] * np.abs(m) / (np.abs(vy[idx]) + P['Slope']), P['KMin'] * tm, np.minimum(P['KMax'] * tm + 5.0, P['DtMax']))
            tcur[idx] = tm + dt
        gi = idx_all[hit]
        if len(gi) == 0:
            return col, hit, dist
        # ---- [Shade] at the hit
        th = dist[gi]
        p = ro + V[gi] * th[:, None]
        foot = np.maximum(th * pix_ang, 1e-3)
        m, top, bot, dd, mm, amp, deck, slot, lip = self.field(p, foot, slot_open)
        # which surface: crossed the top (from above or through a wall) or the bottom (from below)
        # r2 (review r1 S2): the underside by height above the bottom, soft (was a hard nearest-surface test: it flipped
        # pixel by pixel where the bisection landed)
        under_w = ss(40.0, 5.0, p[:, 1] - bot) * (V[gi, 1] > 0)
        under = under_w > 0.0
        # geometric normal of the top surface (finite differences of Htop)
        h = np.maximum(foot * 2.0, 4.0)
        tx = self.field(p + np.c_[h, np.zeros(len(h)), np.zeros(len(h))], foot, slot_open)[1]
        tz = self.field(p + np.c_[np.zeros(len(h)), np.zeros(len(h)), h], foot, slot_open)[1]
        gx, gz = (tx - top) / h, (tz - top) / h
        nrm = np.stack([-gx, np.ones(len(h)), -gz], -1)
        nrm /= np.linalg.norm(nrm, axis=-1, keepdims=True)
        slope = np.hypot(gx, gz)
        wall = ss(P['WallSlope'] * 0.5, P['WallSlope'], slope)
        # r2 (review r1 B2): on the walls, the normal of the body's margin in 3-D (the bulges vary with height too),
        # over >= 20 m / 3 px (no sub-pixel glints), and a wrapped N.L (a cauliflower wall scatters light round its heads)
        wi = wall > 0.05
        if wi.any():
            e = np.maximum(foot[wi] * P['WallNormalPx'], P['WallNormalMin'])
            pw = p[wi]
            m0 = self.field(pw, e, slot_open)[0]
            ez = np.zeros(len(e))
            gm = np.stack([self.field(pw + np.c_[e, ez, ez], e, slot_open)[0] - m0,
                           self.field(pw + np.c_[ez, e, ez], e, slot_open)[0] - m0,
                           self.field(pw + np.c_[ez, ez, e], e, slot_open)[0] - m0], -1)
            nw = -gm / np.maximum(np.linalg.norm(gm, axis=-1, keepdims=True), 1e-6)
            nb = nrm[wi] * (1 - wall[wi])[:, None] + nw * wall[wi][:, None]
            nrm[wi] = nb / np.maximum(np.linalg.norm(nb, axis=-1, keepdims=True), 1e-6)
        lam_geo = np.clip((nrm @ SUN + P['WallWrap']) / (1 + P['WallWrap']), 0, 1)
        lam = dd[:, 3] * (1 - wall) + lam_geo * wall
        tau = self.tau(dd, mm, amp)
        shadow_baked = np.exp(-tau * P['SurfShadow'])
        # walls, the slot floor, the lip: the baked path does not know them: test the mean body toward the sun
        need = (wall > 0.05) | (slot > 0.05) | (lip > 0.05) | under
        sh = shadow_baked.copy()
        if need.any():
            vis = self.sun_shadow(p[need] + nrm[need] * 2.0, slot_open)
            sh[need] = np.minimum(sh[need], vis)
        ms = P['MsK'] * np.exp(-tau * P['MsTau'])
        ao = dd[:, 2] * (1 - wall) + 0.75 * wall
        up = np.clip(nrm[:, 1], 0, 1)
        var = P['VarMin'] + mm[:, 3] * (P['VarMax'] - P['VarMin'])
        sunL = (P['SunGain'] * (lam * sh + ms))[:, None] * SUN_COL
        skyL = (P['SkyGain'] * ao * (0.55 + 0.45 * up))[:, None] * SKY_COL + (P['GroundGain'] * 0.25 * (1 - up))[:, None] * GND_COL
        surf = (sunL + skyL) * var[:, None]
        # the underside (cloud-cover bottom, seen from below): ground light + a glow toward the sunward edge
        if under.any():
            pu = p[under]
            r = np.hypot(pu[:, 0], pu[:, 2])
            az = np.degrees(np.arctan2(pu[:, 0], pu[:, 2]))
            da = ((az - LAYOUT['sun']['az_deg'] + 180) % 360) - 180
            E = BODY['edge']
            R = E['r0'] + (E['r_sun'] - E['r0']) * np.exp(-(da / E['sun_lobe_deg']) ** 2)
            to_edge = np.maximum(R - r, 0.0)
            glow = P['EdgeGlow'] * np.exp(-to_edge / P['EdgeGlowLen']) * np.clip(np.cos(np.radians(da)), 0, 1)
            # r3 (D-35 #2): ground k 0.35 -> UnderGround, sky k 0.06 -> UnderSky (the cover's underside darker at 312)
            su = (P['GroundGain'] * P['UnderGround'] * var[under])[:, None] * GND_COL + (glow * var[under])[:, None] * SUN_COL * 0.35 \
                + (P['UnderSky'] * var[under])[:, None] * SKY_COL
            wu = under_w[under][:, None]
            surf[under] = surf[under] * (1 - wu) + su * wu
        # troughs toward the haze (tops only)
        fogC = fog_colour(sky_eq, V[gi])
        lod_t = np.log2(np.maximum(foot, 1e-3) / self.texel_d) + P['TroughLod']
        dm = self.det.sample(p[:, 0] / P['PeriodD'], p[:, 2] / P['PeriodD'], np.maximum(lod_t, P['TroughLod']))
        hmean = BODY['top'] + P['MacroMin'] + mm[:, 0] * (P['MacroMax'] - P['MacroMin']) + amp * (
            P['DetailMin'] + dm[:, 0] * (P['DetailMax'] - P['DetailMin']))
        # r3 (D-35 #2): not on the underside (it switched with the relief's slope there: the streaks at 312)
        trough = np.clip((hmean - p[:, 1]) / P['TroughDepth'], 0, 1) * P['TroughK'] * (1 - wall) * (1 - slot) * (1 - under_w)
        # (dawn) troughs go toward the deep sky light, not the horizon haze: shadows stay blue (bible 1.3 rule 2)
        surf = surf * (1 - trough)[:, None] + (P['SkyGain'] * 0.6) * SKY_COL[None, :] * trough[:, None]
        # r3 (D-35 #1): the lip's top edge against the sun: a bright rim (forward scattering through the thin edge)
        rim = lip * ss(P['RimDepth'], 0.0, top - p[:, 1]) * np.exp((V[gi] @ SUN - 1.0) * P['RimK']) * P['RimGain']
        surf = surf + rim[:, None] * SUN_COL[None, :]
        # ---- [Fog] LanbaiApplyFog: exp density, colour = the sky in that direction (the dawn preset's horizon model)
        f = np.minimum(1 - np.exp(-P['FogDensity'] * th), P['FogCap'])
        col[gi] = surf * (1 - f)[:, None] + fogC * f[:, None]
        return col, hit, dist


if __name__ == '__main__':
    import time
    sys.path.insert(0, HERE)
    sky = C.read_hdr(os.environ.get('LB_SKY', '/tmp/lb/clouds/sky_dawn_1024.hdr')).astype(np.float64)
    w, h = 480, 270
    yaw, pitch = float(sys.argv[1]) if len(sys.argv) > 1 else 0.0, float(sys.argv[2]) if len(sys.argv) > 2 else -10.0
    t = float(sys.argv[3]) if len(sys.argv) > 3 else 266.34
    sys.path.insert(0, HERE)
    import act06_layout as AL
    AL.solve_edges()
    d = AL.descent(t)[0]
    tx = math.tan(math.radians(45))
    xs = ((np.arange(w) + 0.5) / w * 2 - 1) * tx
    ys = (1 - (np.arange(h) + 0.5) / h * 2) * tx * h / w
    X, Y = np.meshgrid(xs, ys)
    dv = np.stack([X, Y, np.ones_like(X)], -1)
    cp, sp, cy, sy = math.cos(math.radians(pitch)), math.sin(math.radians(pitch)), math.cos(math.radians(yaw)), math.sin(math.radians(yaw))
    Rx = np.array([[1, 0, 0], [0, cp, sp], [0, -sp, cp]]); Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    dv = dv @ Rx.T @ Ry.T
    dv /= np.linalg.norm(dv, axis=-1, keepdims=True)
    V = dv.reshape(-1, 3)
    t0 = time.time()
    so = float(np.clip((t - BODY['slot']['open_t0']) / (BODY['slot']['open_t1'] - BODY['slot']['open_t0']), 0, 1))
    c, hit, dist = Plain().render([0.55, 1.70, 2.05], V, 2 * tx / w, d, sky, slot_open=so)
    img = C.sample_equirect(sky, V, 0.0)
    img[hit] = c[hit]
    codes = C.grade(img.reshape(h, w, 3), 'S6', bloom=True)
    out = '/tmp/lb/plain_%g_%g_%g.png' % (yaw, pitch, t)
    Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(out)
    print(out, '%.1fs' % (time.time() - t0), 'hit %.2f' % hit.mean())
