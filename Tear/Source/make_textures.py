"""Tear kit v2 textures (numpy + PIL). Colour values are the bible's FILLS (scene-linear, what the shader outputs
before PPv2), so what we render is what Unity gets.

Tear_Emission_2048x512.png / Tear_Rip_1024x128.png:  RGB = sRGB-encoded (linear fill / EMISSION_SCALE 4), A = how much
   of the sky behind is covered (premultiplied blend: out = rgb*4 + (1-A)*dst). Core A = 1, fibres partial, glow 0.
Tear_Fibres_1024.png:  8 fibre strands (128 x 1024 each), RGB = A = strand intensity (additive; shader tints).
Tear_Flaps_1024.png:   4 bands (bottom->top L1, L2, R1, R2). R = distance inside the torn edge (m / 24),
   G = silk (0.5 = neutral), B = loose-thread mask beyond the edge, A = cloth coverage (alpha-to-coverage cutout).
Halo_512.png:          RGB = sRGB(halo fill #8275D0 x falloff), A = falloff.
Shaft_Gradient_256x1024.png: RGB = A = beam intensity (3 beams across; v 0 = tear end -> 1 = far end).
"""
import os, sys, math, json
import numpy as np
from PIL import Image, ImageDraw
from scipy.ndimage import gaussian_filter, zoom, distance_transform_edt

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import tear_def as T

LAN = os.path.dirname(os.path.dirname(HERE))
OUT = os.path.join(LAN, 'deliver', 'Tear', 'Textures')
os.makedirs(OUT, exist_ok=True)


def hexlin(h):
    h = h.lstrip('#')
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def fill(h, ev=0.0):
    return hexlin(h) * 2.0 ** ev


CORE = fill('#FFEDD1', 1.84)       # screen #F5F2EC
FIBRE = fill('#DFE6FF', 1.56)      # screen #E2E8F3
GLOW = fill('#C6B4FF', 1.04)       # screen #C0B9E4
PLY = fill('#DFCFFF', 1.96) * 0.80  # 4c first lip #E6E1F2, a touch dimmer: the second layer, seen from outside
HALO = fill('#8275D0')             # screen #5B57A1
THREAD = fill('#3E3C66') * 1.4     # indigo yarn silhouetted on the white


def lin_to_srgb(x):
    x = np.clip(x, 0, 1)
    return np.where(x <= 0.0031308, 12.92 * x, 1.055 * x ** (1 / 2.4) - 0.055)


def save_rgba(path, rgb_lin, a, scale=1.0, dither=True, seed=0):
    """rgb_lin (H,W,3) linear -> sRGB 8-bit of rgb_lin/scale, straight A."""
    rng = np.random.default_rng(seed)
    s = lin_to_srgb(rgb_lin / scale) * 255.0
    al = np.clip(a, 0, 1) * 255.0
    if dither:
        s = s + (rng.random(s.shape[:2]) - rng.random(s.shape[:2]))[..., None] * 0.5
        al = al + (rng.random(al.shape) - rng.random(al.shape)) * 0.5
    img = np.concatenate([np.clip(np.round(s), 0, 255), np.clip(np.round(al), 0, 255)[..., None]], 2).astype(np.uint8)
    Image.fromarray(img, 'RGBA').save(path)
    return img


def box_down(x, f):
    h, w = x.shape[:2]
    return x.reshape(h // f, f, w // f, f, *x.shape[2:]).mean((1, 3))


def field(shape, sig, seed, amp=1.0):
    """smooth random field ~N(0,1)*amp with gaussian correlation sig=(sy, sx) in px."""
    rng = np.random.default_rng(seed)
    f = gaussian_filter(rng.standard_normal(shape), sig, mode='wrap')
    return f / (f.std() + 1e-9) * amp


# ======================================================================================== lens emission (v3)
L0 = fill('#DFCFFF', 1.96) * 0.47          # the outer layer of undyed cloth: the mist #E6E1F2 seen dimmer (L* ~83)
L1 = fill('#E4DAFF', 1.92) * 0.62          # the second layer (L* ~90)
LINE = FIBRE * 1.05                         # the torn fibre line on each layer's edge (#E2E8F3)


def lens_footprint(t):
    """the Tear_Lens mesh's across extent (kit_mesh.lens): the emission must reach 0 before it."""
    aL, aR = T.lips(t)
    pf = T.profile(t)
    lo = np.maximum(np.minimum(aL, T.path(t)) - 48.0 - 10 * pf, T.A_MIN + 2)
    hi = np.minimum(np.maximum(aR, T.path(t)) + 48.0 + 10 * pf, T.A_MAX - 2)
    return lo, hi


THICK_IN = fill('#3E3C66') * 1.7      # the torn cloth's reverse face seen edge-on (right edge), toward the lip
THICK_OUT = fill('#5B5A88') * 1.7     # ... toward the white
THREAD_ZIP = fill('#2A2C44') * 1.0    # the zipper's bridging threads (dark against the white)


def _veil_mask(kind, TT, AA, aL, aR, tc, ac_frac, st, sa_frac, tilt, seed):
    """(mask 0..1 of the veil sheet, edge distance m) for one inner veil (critique B4.1c): different torn shapes."""
    w_loc = np.interp(tc, TT[0], (aR - aL))
    mid = np.interp(tc, TT[0], 0.5 * (aL + aR))
    hw = 0.5 * w_loc
    ac = mid + ac_frac * hw
    th = math.radians(tilt)
    # local coords: x across (tilted), y along
    dx, dy = AA - ac, TT - tc
    xr = dx * math.cos(th) - dy * math.sin(th)
    yr = dx * math.sin(th) + dy * math.cos(th)
    ex = (xr / (sa_frac * w_loc)) ** 2 + (yr / (0.5 * st)) ** 2
    ell = T.smoothstep(1.0, 0.75, ex)
    jag = 3.0 * T.fbm(yr / 9.0, seed, 2) + 6.0 * T.fbm(yr / 41.0, seed + 1, 2)
    if kind == 'slant':           # a sheet hanging from one side, its torn edge a straight-ish diagonal
        d = xr - jag
        m = T.smoothstep(1.5, -1.5, d) * ell
    elif kind == 'hole':          # a sheet with an irregular hole off-centre
        hr = np.sqrt((xr / (0.42 * sa_frac * w_loc)) ** 2 + ((yr - 0.08 * st) / (0.30 * st)) ** 2)
        hr = hr + 0.10 * T.fbm(np.arctan2(yr, xr) * 3.0, seed + 2, 2)
        d = (hr - 1.0) * 0.42 * sa_frac * w_loc
        m = T.smoothstep(-1.5, 1.5, d) * ell
    elif kind == 'fork':          # a sheet split by a Y-shaped rip
        x1 = np.abs(xr - jag * 0.4 - 0.25 * np.maximum(yr, 0)) - (2.0 + 0.012 * np.maximum(-yr, 0))
        x2 = np.abs(xr - jag * 0.4 + 0.25 * np.maximum(yr, 0)) - (2.0 + 0.004 * np.maximum(yr, 0))
        d = np.where(yr > 0, np.minimum(x1, x2), x1)
        m = T.smoothstep(-1.5, 1.5, d) * ell
    else:                         # flag: a small torn piece hanging, ragged bottom
        d = -(yr + 0.35 * st + jag * 2.0)
        m = T.smoothstep(1.5, -1.5, d) * ell * T.smoothstep(0.6, 0.0, np.abs(xr) / (sa_frac * w_loc))
    return m, d


def make_emission(W=2048, Hh=512, SS=3):
    """v4 (gate round 3, critique B4): no nested lips. The undyed white with the bible's falloff (100 % at 40 % H ->
    70 % at the ends, no stripes); a cloth THICKNESS band inside the right edge; 4 soft inner VEILS of different torn
    shapes (slant / hole / fork / flag), dimmer, edged by a faint fibre line; the top 16 % closed by a ZIPPER of
    bridging threads (two snapped); the left edge clean, the right ragged; fibres only at the notches; a smooth
    #C0B9E4 lip glow that is 0 at the mesh border."""
    Ws, Hs = W * SS, Hh * SS
    mt = (T.T_MAX - T.T_MIN) / Ws
    ma = (T.A_MAX - T.A_MIN) / Hs
    t = T.T_MIN + (np.arange(Ws) + 0.5) * mt
    a = T.A_MAX - (np.arange(Hs) + 0.5) * ma
    A = a[:, None]
    TT = np.broadcast_to(t[None, :], (Hs, Ws))
    AA = np.broadcast_to(A, (Hs, Ws))
    aL, aR = T.lips(t)
    tx = lambda tt: (tt - T.T_MIN) / mt
    ay = lambda aa: (T.A_MAX - aa) / ma
    inside = ((A > aL[None]) & (A < aR[None])).astype(np.float32)
    ib = inside > 0.5
    d_in = distance_transform_edt(ib, sampling=(ma, mt)).astype(np.float32)
    d_out = distance_transform_edt(~ib, sampling=(ma, mt)).astype(np.float32)
    sn = np.where(t < T.T_W, (T.T_W - t) / (T.T_W - T.T_BOT), (t - T.T_W) / (T.T_TOP - T.T_W))
    Bt = (0.70 + 0.30 * (1 - np.clip(sn, 0, 1) ** 1.6))[None, :]
    slow = 1.0 + field((Hs, Ws), (90.0 / ma, 220.0 / mt), 2, 0.02)
    col = CORE[None, None] * (Bt * slow)[..., None] * np.ones((Hs, Ws, 1), np.float32)
    # (c) veils deep inside: dimmer sheets with a faint fibre line on their torn edge; never touching the lips
    for (kind, tc, acf, st, saf, tilt, seed) in T.VEILS:
        m, d = _veil_mask(kind, TT, AA, aL, aR, tc, acf, st, saf, tilt, seed)
        m = m * ib * T.smoothstep(4.0, 16.0, d_in)
        line = np.exp(-(d / 1.2) ** 2) * T.smoothstep(4.0, 16.0, d_in) * ib * (ell_ok := (m > -1))
        col = col * (1.0 - 0.13 * m[..., None]) + (LINE[None, None] * 0.92 - col) * (0.25 * line)[..., None]
    # (b) the thickness: the reverse face of the torn cloth along the RIGHT edge, outside the peel's span
    wloc = (aR - aL)[None, :]
    d_r = (aR[None, :] - A)                               # m inside the right lip
    thick_w = T.THICK_FRAC * wloc
    in_band = (d_r >= 0) & (d_r < thick_w) & ib
    peel = np.zeros_like(t)
    for fl in T.FLAPS:
        if fl['side'] > 0:
            peel = np.maximum(peel, T.smoothstep(fl['t0'] - 40, fl['t0'] + 10, t) * T.smoothstep(fl['t1'] + 40, fl['t1'] - 10, t))
    fx = np.clip(d_r / np.maximum(thick_w, 1e-3), 0, 1)
    thick = (THICK_IN[None, None] * (1 - fx[..., None]) + THICK_OUT[None, None] * fx[..., None])
    wt = (in_band * (1 - peel[None, :]) * T.smoothstep(0.0, 0.25, fx) ** 0 * T.smoothstep(1.0, 0.7, fx))[..., None]
    col = col * (1 - wt) + thick * wt
    # the left lip: a clean cool fibre line just inside the edge; the right: ragged (darker yarn ends)
    ez = np.exp(-(d_in / 1.4) ** 2) * ib
    left = (A < 0.5 * (aL + aR)[None, :])
    col = col * (1 - 0.5 * (ez * left)[..., None]) + LINE[None, None] * (0.5 * ez * left * Bt)[..., None]
    rgb = col * inside[..., None]
    alpha = inside.copy()
    # (d) the zipper: dark bridging threads across the top of the opening (2 snapped, ends curled back)
    zl = Image.new('L', (Ws, Hs), 0)
    dz = ImageDraw.Draw(zl)
    for (tl, tr, sag, wd, snapped) in T.zipper_threads():
        aL0, aR0 = T.lips(np.array([tl]))[0][0] - 3.0, T.lips(np.array([tr]))[1][0] + 3.0
        xs = np.linspace(0, 1, 40)
        tt_ = tl + (tr - tl) * xs - sag * 4 * xs * (1 - xs)
        aa_ = aL0 + (aR0 - aL0) * xs
        pts = [(tx(u), ay(v)) for u, v in zip(tt_, aa_)]
        wpx = max(2, int(round(wd / ma)))
        if not snapped:
            dz.line(pts, fill=255, width=wpx)
        else:      # snapped: two short stubs left on the lips, drooping toward the foot (no curls: they read as glyphs)
            n = len(pts)
            for half, sgn in ((pts[:n // 3], 1), (pts[-(n // 4):][::-1], -1)):
                droop = []
                for k, (x_, y_) in enumerate(half):
                    f_ = k / max(len(half) - 1, 1)
                    droop.append((x_ - (6.0 / mt) * f_ ** 2, y_))      # sags toward -t (column index down)
                dz.line(droop, fill=255, width=max(2, wpx - 1))
    zm = np.asarray(zl, np.float32) / 255.0
    zm = zm * (TT > T.ZIP_T0 * T.T_TOP - 20)
    rgb = rgb * (1 - zm[..., None]) + THREAD_ZIP[None, None] * zm[..., None]
    alpha = np.maximum(alpha, zm)

    # ------------------------------------------------------------ fibres at the notches only
    rng = np.random.default_rng(7)
    lay_out = Image.new('L', (Ws, Hs), 0)
    lay_in = Image.new('L', (Ws, Hs), 0)
    dO, dI = ImageDraw.Draw(lay_out), ImageDraw.Draw(lay_in)

    def draw_fibre(dr, t0, a0, ang, L, wid, val, bend, nseg=6):
        pts = []
        tt, aa = t0, a0
        for k in range(nseg + 1):
            pts.append((tx(tt), ay(aa)))
            ang2 = ang + bend * (k / nseg)
            tt += math.cos(ang2) * L / nseg
            aa += math.sin(ang2) * L / nseg
        for k in range(nseg):
            w = max(1, int(round(wid * (1 - 0.7 * k / nseg) / ma)))
            dr.line([pts[k], pts[k + 1]], fill=int(val * (1 - 0.55 * k / nseg)), width=w)

    for side in (-1, +1):
        ts = np.arange(80.0, T.T_TOP * T.ZIP_T0, 0.8)          # v4: no 'grass' at the foot, none in the zipper
        _, nk = T.notch_profile(ts, side)
        for tt, k in zip(ts, nk):
            if rng.random() > 0.55 * k:
                continue
            l, r = T.lips(np.array([tt]))
            a0 = float(r[0] if side > 0 else l[0])
            # perpendicular to the edge (the weft), 0.5-1.5 % of H
            eps = 1.0
            l2, r2 = T.lips(np.array([tt + eps]))
            slope = (float(r2[0] if side > 0 else l2[0]) - a0) / eps
            nrm = math.atan2(side * 1.0, -slope * side)          # outward normal angle in (t, a)
            L = rng.uniform(5.0, 15.0)
            if rng.random() < 0.7:
                draw_fibre(dO, tt, a0 - side * 0.8, nrm + rng.normal(0, 0.25), L, rng.uniform(0.5, 1.1),
                           int(rng.uniform(150, 255)), rng.normal(0, 0.3))
            else:
                draw_fibre(dI, tt, a0 + side * 0.5, nrm + math.pi + rng.normal(0, 0.25), L * 0.6, rng.uniform(0.4, 0.9),
                           int(rng.uniform(120, 220)), rng.normal(0, 0.3))
    fo = np.asarray(lay_out, np.float32) / 255.0
    fi = np.asarray(lay_in, np.float32) / 255.0
    rgb = rgb * (1 - 0.35 * (fi * inside)[..., None]) + FIBRE[None, None] * 0.25 * (fi * inside * Bt)[..., None]
    out_mask = fo * (1 - inside)
    rgb += FIBRE[None, None] * (out_mask * Bt * 0.9)[..., None]
    alpha = np.maximum(alpha, out_mask * 0.6)

    # ------------------------------------------------------------ lip glow outside (smooth; 0 at the mesh border)
    lo, hi = lens_footprint(t)
    d_border = np.minimum(A - lo[None], hi[None] - A)
    d_border = np.minimum(d_border, np.minimum(t - (T.T_MIN + 4), (T.T_MAX - 4) - t)[None, :])
    edge_fade = T.smoothstep(0.0, 18.0, d_border)
    along = 0.85 + 0.15 * np.clip(0.5 + 0.5 * T.fbm(t / 70.0, 5, 2), 0, 1)[None, :]
    g = (0.60 * np.exp(-d_out / 6.5) + 0.22 * np.exp(-d_out / 24.0)) * (1 - inside) * along * edge_fade
    rgb += GLOW[None, None] * (g * np.sqrt(Bt) * (1 - 0.4 * out_mask))[..., None]
    rgb *= edge_fade[..., None] ** 0.25
    alpha *= edge_fade ** 0.25
    rgb = box_down(rgb, SS)
    alpha = box_down(alpha, SS)
    bord = np.ones((Hh, W), np.float32)
    bord[:, :6] = 0; bord[:, -6:] = 0; bord[:6, :] = 0; bord[-6:, :] = 0
    bord = gaussian_filter(bord, 2.0)
    rgb *= bord[..., None]; alpha *= bord
    return rgb, alpha


# ======================================================================================== rip crack
def make_rip(W=1024, Hh=128, SS=3):
    """v3 (critique B4.6): the branch rips are cloth STRESS CRACKS, not lightning: a narrow torn slit (6-12 m at U7)
    showing the undyed white at ~0.4 x the core (screen L* 75-85), dark torn lips either side (the cloth there is
    pulled thin and casts no glow: premultiplied A 0.3 with no colour darkens the sky), a faint smooth glow, NO
    fibre fringe. strip space: u along (0 root -> 1 tip), v across (0..1, crack centre 0.5)."""
    r = T.RIPS[0]
    L = r['length']
    Ws, Hs = W * SS, Hh * SS
    u = (np.arange(Ws) + 0.5) / Ws
    v = (np.arange(Hs) + 0.5) / Hs
    y = (0.5 - v)[:, None] * 2 * T.RIP_MARGIN
    half = T.rip_width(r, u)[None, :] * 0.5
    jag1 = (0.25 * T.fbm(u * L / 9.0, 401, 2) + 0.8 * T.fbm(u * L / 40.0, 402, 2))[None, :]     # v4: a lens, not a bolt
    jag2 = (0.25 * T.fbm(u * L / 9.0, 403, 2) + 0.8 * T.fbm(u * L / 40.0, 404, 2))[None, :]
    lo, hi = -half + jag1 * np.minimum(1, half / 3), half + jag2 * np.minimum(1, half / 3)
    inside = ((y > lo) & (y < hi)).astype(np.float32)
    d_out = np.maximum(lo - y, y - hi)
    d_in = np.minimum(y - lo, hi - y)
    Bu = (0.75 + 0.25 * (1 - u) ** 0.7)[None, :]
    ez = np.exp(-np.maximum(d_in, 0) / 1.5)
    col = L0[None, None] * (0.62 * Bu * (1 - 0.35 * ez))[..., None]
    rgb = col * inside[..., None]
    alpha = inside.copy()
    # dark torn lips: the pulled-thin cloth either side (6-12 m), darker than the sky-cloth around
    lipw = 4.0 + 6.0 * np.clip(half / 8.0, 0, 1)
    dark = np.exp(-np.maximum(d_out, 0) / lipw) * (1 - inside)
    alpha = np.maximum(alpha, 0.45 * dark)                               # v4: darker torn lips
    g = 0.06 * np.exp(-np.maximum(d_out, 0) / 6.0) * (1 - inside)          # v4: glow <= 1.5 x the width
    rgb += GLOW[None, None] * (g * np.sqrt(Bu))[..., None]
    fade = (T.smoothstep(T.RIP_MARGIN, T.RIP_MARGIN * 0.75, np.abs(y)) * T.smoothstep(1.0, 0.97, u)[None, :])
    rgb *= fade[..., None]; alpha *= fade
    return box_down(rgb, SS), box_down(alpha, SS)


# ======================================================================================== fibre atlas
def make_fibres(W=1024, Hh=1024, SS=2, ncol=8):
    Ws, Hs = W * SS, Hh * SS
    cw = Ws // ncol
    lay = Image.new('L', (Ws, Hs), 0)
    dr = ImageDraw.Draw(lay)
    rng = np.random.default_rng(21)
    for c in range(ncol):
        x0 = c * cw + cw / 2
        nstr = [1, 2, 3, 1, 4, 2, 3, 5][c]
        for sidx in range(nstr):
            xr = x0 + rng.normal(0, cw * 0.06)
            amp = rng.uniform(0.02, 0.12) * cw
            freq = rng.uniform(0.6, 2.2)
            ph = rng.uniform(0, 6.28)
            lean = rng.normal(0, 0.08) * cw
            top = rng.uniform(0.72, 0.97)
            wid0 = rng.uniform(3.0, 7.0) * SS * (1.0 if nstr < 3 else 0.7)
            n = 60
            pts = []
            for k in range(n + 1):
                f = k / n * top
                x = xr + lean * f * 2 + amp * math.sin(ph + f * freq * 6.28) * f
                y = Hs - 1 - f * Hs
                pts.append((x, y))
            for k in range(n):
                f = k / n
                w = max(1, int(round(wid0 * (1 - 0.8 * f))))
                v = int(255 * (1.0 - 0.6 * f ** 1.3))
                dr.line([pts[k], pts[k + 1]], fill=v, width=w)
            # frayed tip: 2-4 filaments splitting off in the last 30 %
            k0 = int(n * rng.uniform(0.55, 0.75))
            for _ in range(int(rng.integers(2, 5))):
                x, y = pts[k0]
                ang = -math.pi / 2 + rng.normal(0, 0.35)
                Ls = (1 - k0 / n) * top * Hs * rng.uniform(0.6, 1.1)
                prev = (x, y)
                for m in range(10):
                    ang += rng.normal(0, 0.08)
                    nx = prev[0] + math.cos(ang) * Ls / 10
                    ny = prev[1] + math.sin(ang) * Ls / 10
                    nx = min(max(nx, c * cw + 3), (c + 1) * cw - 4)
                    dr.line([prev, (nx, ny)], fill=int(170 * (1 - m / 10) + 40), width=max(1, SS))
                    prev = (nx, ny)
    a = np.asarray(lay, np.float32) / 255.0
    a = box_down(a, SS)
    a[:, :] *= 1.0
    a[:2, :] = 0; a[-1:, :] = 0
    for c in range(ncol):                 # keep a clear gutter between cells (mip bleeding)
        a[:, c * (W // ncol):c * (W // ncol) + 2] = 0
        a[:, (c + 1) * (W // ncol) - 2:(c + 1) * (W // ncol)] = 0
    return a


# ======================================================================================== flap masks
def make_flaps(W=1024, Hh=1024, SS=2):
    band = Hh // 2
    Wb, Hb = W * SS, band * SS
    R = np.zeros((Hh, W), np.float32); G = np.zeros_like(R); B = np.zeros_like(R); A = np.zeros_like(R)
    order = ['Tear_Flap_L', 'Tear_Flap_R']      # v4: two flaps; band 0 = bottom
    for bi, name in enumerate(order):
        fl = [f for f in T.FLAPS if f['name'] == name][0]
        Lm = fl['length']
        s = (np.arange(Wb) + 0.5) / Wb
        vt = (np.arange(Hb) + 0.5) / Hb          # 0 at the band's bottom row (fold) .. 1 (top)
        r = (vt * 1.1)[:, None]                   # normalized r (0..1.1 of length)
        edge = T.flap_outline(fl, s)[None, :]
        # finer torn edge: small jag
        jag = (0.012 * T.fbm(s * 90, fl['seed'] + 3, 2) + 0.02 * T.fbm(s * 25, fl['seed'] + 4, 2))[None, :]
        e2 = edge + jag
        cov = (r < e2).astype(np.float32)
        dist = np.clip((e2 - r) * Lm, 0, None)    # metres inside the torn edge
        # holes near the torn edge (the silk is wearing through)
        hole = field((Hb, Wb), (1.4 / (1.1 * Lm) * Hb, 2.5 / (fl['t1'] - fl['t0']) * Wb), fl['seed'] + 20, 1.0)
        cov *= 1 - ((hole > 2.6) & (dist < 8)).astype(np.float32)          # v4: fewer holes (silk)
        # loose threads beyond the torn edge
        lay = Image.new('L', (Wb, Hb), 0)
        dr = ImageDraw.Draw(lay)
        rng = np.random.default_rng(fl['seed'])
        span = fl['t1'] - fl['t0']
        for ss in rng.uniform(0.04, 0.96, 140):
            j = int(ss * Wb)
            e0 = float(e2[0, j])
            if e0 < 0.03:
                continue
            Lt = float(np.clip(rng.lognormal(math.log(3.0), 0.5), 1.0, 9.0))
            ang = math.pi / 2 + rng.normal(0, 0.45)            # mostly continuing outward (+r)
            x0, y0 = j, Hb - 1 - (e0 - 0.003) / 1.1 * Hb
            pts = [(x0, y0)]
            for k in range(5):
                ang += rng.normal(0, 0.2)
                x0 += math.cos(ang) * Lt / 5 / span * Wb
                y0 -= math.sin(ang) * Lt / 5 / (1.1 * Lm) * Hb
                pts.append((x0, y0))
            wpx = max(1, int(rng.uniform(0.35, 0.9) / (1.1 * Lm) * Hb))
            for k in range(5):
                dr.line([pts[k], pts[k + 1]], fill=int(255 * (1 - 0.5 * k / 5)), width=wpx)
        thr = np.asarray(lay, np.float32)[::-1] / 255.0 * (1 - cov)     # flip: row 0 = fold
        # silk: tension wrinkles from the fold toward the torn edge, dye mottling, fine grain
        wr = 0.6 * field((Hb, Wb), (26.0 / (1.1 * Lm) * Hb, 4.0 / span * Wb), fl['seed'] + 30, 1.0) + \
            0.4 * field((Hb, Wb), (12.0 / (1.1 * Lm) * Hb, 1.6 / span * Wb), fl['seed'] + 33, 1.0) * \
            np.clip(field((Hb, Wb), (60.0 / (1.1 * Lm) * Hb, 30.0 / span * Wb), fl['seed'] + 34, 1.0), 0, None)
        mot = field((Hb, Wb), (40.0 / (1.1 * Lm) * Hb, 40.0 / span * Wb), fl['seed'] + 31, 1.0)
        grain = field((Hb, Wb), (0.6, 0.6), fl['seed'] + 32, 1.0)
        silk = 0.5 + 0.07 * wr + 0.05 * mot + 0.015 * grain                   # v4: smooth silk, no crumple
        a_b = np.maximum(cov, thr * 0.9)
        R_b = np.clip(dist / 24.0, 0, 1)
        blk = lambda x: box_down(x[::-1], SS)        # PNG rows top-down: flip so the fold is at the band bottom
        rows = slice(Hh - (bi + 1) * band, Hh - bi * band)
        R[rows] = blk(R_b); G[rows] = blk(np.clip(silk, 0, 1)); B[rows] = blk(thr); A[rows] = blk(a_b)
    return R, G, B, A


# ======================================================================================== sky-cloth folds
def _fold_strokes():
    """tension folds (critique B4.5): (anchor t, anchor a, start angle deg from +t toward +a, curvature deg/100 m,
    length m, root half-width m, relief sign). 6 from the top end, 5 from the bottom end, 4 from the right peel,
    2 from the left curl; curved, tapering, converging on their anchors; within ~1.5 H."""
    out = []
    rng = np.random.default_rng(91)
    top_t = T.T_TOP * 0.96
    top_a = float(T.path(np.array([top_t]))[0])
    for ang in (-62, -38, -16, 14, 36, 58):
        out.append((top_t, top_a, ang + rng.uniform(-5, 5), np.sign(ang) * rng.uniform(4, 9),
                    rng.uniform(0.6, 1.15) * T.H, rng.uniform(16, 30), 1))
    bot_t = 40.0
    bot_a = float(T.path(np.array([bot_t]))[0])
    for ang in (-118, -96, -76, 82, 104):
        out.append((bot_t, bot_a, ang + rng.uniform(-6, 6), -np.sign(ang) * rng.uniform(3, 7),
                    rng.uniform(0.5, 0.9) * T.H, rng.uniform(18, 34), 1))
    for k in (3, 4, 5):           # from the right peel's grips outward (the cloth pulled toward the hand)
        g, _ = T.grip_kit(k)
        tg, ag = T.to_ta(g[0], g[2])
        out.append((float(tg), float(ag), 70 + rng.uniform(-14, 14), rng.uniform(-6, 6), rng.uniform(0.45, 0.8) * T.H,
                    rng.uniform(14, 24), 1))
    fr = [f for f in T.FLAPS if f['side'] > 0][0]
    out.append((fr['t1'] + 20, float(T.lips(np.array([fr['t1']]))[1][0]), 40, 5, 0.6 * T.H, 18, 1))
    fl = [f for f in T.FLAPS if f['side'] < 0][0]
    for tt_, ang in ((fl['t0'] + 20, -100), (fl['t1'] - 10, -70)):
        out.append((tt_, float(T.lips(np.array([tt_]))[0][0]), ang, -4, 0.45 * T.H, 14, 1))
    return out


def make_skyfolds(N=1024, SS=2):
    """v4 (critique B4.5): the sky is cloth. Premultiplied card: RGB = the wound's light on the lit slope of each
    tension fold, A = the shade on the other slope (+-4-6 L*). No smoke, no halo layer."""
    n = N * SS
    t = T.FOLD_T0 + (np.arange(n) + 0.5) / n * (T.FOLD_T1 - T.FOLD_T0)
    a = T.FOLD_A0 + (np.arange(n) + 0.5) / n * (T.FOLD_A1 - T.FOLD_A0)
    TT, AA = np.meshgrid(t, a, indexing='ij')            # rows = t, cols = a
    aL, aR = T.lips(t)
    ins = (AA > aL[:, None]) & (AA < aR[:, None])
    mt = (T.FOLD_T1 - T.FOLD_T0) / n
    ma = (T.FOLD_A1 - T.FOLD_A0) / n
    d = distance_transform_edt(~ins, sampling=(mt, ma))
    h = np.zeros_like(TT)
    for (t0, a0, ang0, curv, L, w0, sg) in _fold_strokes():
        # the fold's centreline as a polyline in (t, a)
        m = 600                     # dense: a coarse polyline gave a beaded (dashed) relief
        ss_ = np.linspace(0, 1, m)
        angs = np.radians(ang0 + curv * ss_ * L / 100.0)
        dtt, daa = np.cos(angs) * L / (m - 1), np.sin(angs) * L / (m - 1)
        ct = t0 + np.concatenate([[0], np.cumsum(dtt[:-1])])
        ca = a0 + np.concatenate([[0], np.cumsum(daa[:-1])])
        # distance field to the polyline (coarse: nearest sample), along-fraction
        from scipy.spatial import cKDTree
        tree = cKDTree(np.stack([ct, ca], 1))
        dist, idx = tree.query(np.stack([TT.ravel(), AA.ravel()], 1), distance_upper_bound=w0 * 4 + 20)
        dist = dist.reshape(TT.shape)
        idx = idx.reshape(TT.shape)
        ok = np.isfinite(dist)
        f = np.where(ok, ss_[np.clip(idx, 0, m - 1)], 1.0)
        width = w0 * (1 - 0.85 * f)
        prof = np.where(ok, np.exp(-(np.where(ok, dist, 1e9) / np.maximum(width, 1.0)) ** 2), 0.0)
        h += sg * prof * T.smoothstep(0.0, 0.08, f) * T.smoothstep(1.0, 0.55, f)
    h *= T.smoothstep(4.0, 30.0, d)
    h = gaussian_filter(h, 1.0)
    gt, ga = np.gradient(h, mt, ma)
    k = 45.0
    nt_, na_, nz = -gt * k, -ga * k, np.ones_like(h)
    nn = np.sqrt(nt_ ** 2 + na_ ** 2 + nz ** 2)
    dt_, da_ = np.gradient(d, mt, ma)
    ln = np.sqrt(dt_ ** 2 + da_ ** 2) + 1e-6
    Lt, La, Lz = -dt_ / ln, -da_ / ln, 0.55
    Ln = np.sqrt(Lt ** 2 + La ** 2 + Lz ** 2)
    ndl = (nt_ * Lt + na_ * La + nz * Lz) / (nn * Ln) - Lz / Ln
    fall = np.exp(-d / 420.0) * 0.85 + 0.15
    fall *= T.smoothstep(0.0, 20.0, d) * T.smoothstep(1.6 * T.H, 0.9 * T.H, d)
    lit = np.clip(ndl, 0, None) * fall
    shade = np.clip(-ndl, 0, None) * fall
    light = hexlin('#A99DE1') / hexlin('#A99DE1').max()
    rgb = light[None, None, :] * (lit * 0.050)[..., None]
    alpha = np.clip(shade * 0.30, 0, 0.30)
    fu = T.smoothstep(0, 0.06, (np.arange(n) + 0.5) / n)
    fb = fu * fu[::-1]
    rgb *= (fb[:, None] * fb[None, :])[..., None]
    alpha *= fb[:, None] * fb[None, :]
    rgb = box_down(rgb, SS)
    alpha = box_down(alpha, SS)
    rgb = np.transpose(rgb, (1, 0, 2))[::-1]
    alpha = alpha.T[::-1]
    return rgb, alpha


# ======================================================================================== halo, shaft
def make_halo(N=512):
    y, x = np.mgrid[0:N, 0:N]
    x = (x + 0.5) / N * 2 - 1
    y = (y + 0.5) / N * 2 - 1
    r = np.sqrt(x * x + y * y)
    th = np.arctan2(y, x)
    # scattered light in haze: soft core + long tail, a little lumpy (not a perfect disc)
    lump = 1 + 0.07 * np.cos(3 * th + 0.7) + 0.05 * np.cos(5 * th + 2.1) + 0.04 * np.cos(2 * th)
    rr = r / lump
    f = 0.62 / (1 + (rr / 0.16) ** 2) ** 1.15 + 0.38 * np.exp(-(rr / 0.55) ** 2)
    f = f - f.min()
    f = f * T.smoothstep(1.0, 0.72, rr)
    f = f / f.max()
    return HALO[None, None, :] * f[..., None], f


def make_shaft(W=256, Hh=1024):
    """v4 (critique B7.1): ONE soft lobe across, no internal striation (finer than 1.5 deg read as a glory)."""
    u = (np.arange(W) + 0.5) / W
    v = (np.arange(Hh) + 0.5) / Hh            # 0 at the tear end
    across = np.clip(1 - np.abs(u - 0.5) * 2, 0, 1) ** 1.6
    along = T.smoothstep(0.0, 0.06, v) * (1 - v) ** 1.3
    img = np.clip(along[:, None] * across[None, :], 0, 1)
    return img[::-1]


def main():
    rgb, a = make_emission()
    save_rgba(os.path.join(OUT, 'Tear_Emission_2048x512.png'), rgb, a, scale=T.EMISSION_SCALE, seed=1)
    np.save(os.path.join(HERE, 'wip', 'emission_lin.npy'), np.concatenate([rgb, a[..., None]], 2).astype(np.float16))
    rgb, a = make_rip()
    save_rgba(os.path.join(OUT, 'Tear_Rip_1024x128.png'), rgb, a, scale=T.EMISSION_SCALE, seed=2)
    f = make_fibres()
    save_rgba(os.path.join(OUT, 'Tear_Fibres_1024.png'), np.repeat(f[..., None], 3, 2), f, scale=1.0, seed=3)
    R, G, B, A = make_flaps()
    img = np.stack([R, G, B, A], 2)
    Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8), 'RGBA').save(
        os.path.join(OUT, 'Tear_Flaps_1024.png'))
    rgb, a = make_skyfolds()
    save_rgba(os.path.join(OUT, 'Tear_SkyFolds_1024.png'), rgb, a, scale=1.0, seed=6)
    h, fa = make_halo()
    save_rgba(os.path.join(OUT, 'Halo_512.png'), h, fa, scale=1.0, seed=4)
    s = make_shaft()
    save_rgba(os.path.join(OUT, 'Shaft_Gradient_256x1024.png'), np.repeat(s[..., None], 3, 2), s, scale=1.0, seed=5)
    print('textures ->', OUT)


if __name__ == '__main__':
    main()
