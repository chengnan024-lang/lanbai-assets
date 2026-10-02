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
HALO = fill('#7A7B9C')             # v6 (awe r4 B1.8: C* <= 15 over the band); v5 #8275D0 (screen #5B57A1, C* 45)
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


def _lum(c):
    return float(np.asarray(c) @ np.array([0.2126, 0.7152, 0.0722]))


WARM = CORE / _lum(CORE)                    # #F5F2EC chroma at unit luminance
COOL = FIBRE / _lum(FIBRE)                  # #E2E8F3 chroma at unit luminance
THREAD5 = fill('#BDB7D6', 1.75)             # v5: bridging thread over the white (#BDB7D6, L* ~76; never black)
THIN_HOT = fill('#C8C6E4', 1.88)            # thin backlit cloth at the edge (v6 #C8C6E4, L* 80, C* ~15) ...
THIN_COLD = fill('#3E3D5E')                 # ... grading to #3E3D5E (L* 27)
FOLD_DARK = fill('#141726') * 1.0           # a fold turned toward the bus (L* ~7)


def _fill_solved(h):
    """the S4-solved fill of a screen hex (tear/fills.py convention)."""
    sys.path.insert(0, os.path.dirname(HERE))
    import grade as g
    return np.asarray(g.solve_fill(h), float)


def _polyline_dist(px_t, px_a, ct, ca, rad):
    """distance (m) from every pixel (t, a) to a dense polyline, and the polyline parameter of the nearest sample."""
    from scipy.spatial import cKDTree
    tree = cKDTree(np.stack([ct, ca], 1))
    d, i = tree.query(np.stack([px_t.ravel(), px_a.ravel()], 1), distance_upper_bound=rad)
    d = d.reshape(px_t.shape)
    i = i.reshape(px_t.shape)
    ok = np.isfinite(d)
    f = np.where(ok, np.linspace(0, 1, len(ct))[np.clip(i, 0, len(ct) - 1)], 1.0)
    return np.where(ok, d, 1e9), f


def make_emission(W=2048, Hh=512, SS=3):
    """v5 (gate round 4, AD round 3 item 1: 'a flat white plateau with a uniform neon-violet outline = a sticker').
    Looking INTO undyed white with depth, through torn indigo cloth that has thickness:
      * interior: hot spot #F5F2EC (linear ~3.0, L* 95) at the widest row, 10 % of the width toward the right lip; the
        body 1.4-2.2, the ends and a strip inside each lip ~0.9-1.0 and cooler (#E2E8F3 chroma at equal luminance);
        +-8 % very-low-frequency 'bright fog'; 4 soft torn VEILS crossing at 10-30 deg to the axis (a soft bright band
        with a darker side), never concentric. No noise above 1/20 of the width.
      * edge, varying along its length: a broken fibre cross-section band (1.6 % of the local width, #E2E8F3, ~70 %
        coverage); thin STRETCHED cloth glowing #C9C2EE -> #3E3C66 outside the lip only at the widest part and round the
        grips (x (1 - thickness noise)); 4 dark FOLDS per lip turned toward the bus (L* ~7, a faint lit crest) laid on
        the white; 4 clusters of frayed threads per lip (lit, curling outward). No drawn glow line: the halo is bloom.
      * 3 threads still bridging the gap + 1 snapped one hanging from the left lip, #BDB7D6 (L* ~76) over the white,
        glowing violet-white where they cross the lip. The v4 zipper, thickness band and notch fibres are gone."""
    Ws, Hs = W * SS, Hh * SS
    mt = (T.T_MAX - T.T_MIN) / Ws
    ma = (T.A_MAX - T.A_MIN) / Hs
    t = T.T_MIN + (np.arange(Ws) + 0.5) * mt
    a = T.A_MAX - (np.arange(Hs) + 0.5) * ma
    A = a[:, None]
    TT = np.broadcast_to(t[None, :], (Hs, Ws))
    AA = np.broadcast_to(A, (Hs, Ws))
    aL, aR = T.lips(t)
    wl = aR - aL
    cl = 0.5 * (aL + aR)
    inside = ((A > aL[None]) & (A < aR[None])).astype(np.float32)
    ib = inside > 0.5
    d_in = distance_transform_edt(ib, sampling=(ma, mt)).astype(np.float32)
    d_out = distance_transform_edt(~ib, sampling=(ma, mt)).astype(np.float32)
    # interior fields use a SMOOTHED width / centre (sigma 45 m along t): the lips' jogs must not leak into the white
    # as horizontal bands; the dimming toward the lips uses the true distance to the lip
    from scipy.ndimage import gaussian_filter1d
    wls = gaussian_filter1d(wl, 45.0 / mt, mode='nearest')
    cls_ = gaussian_filter1d(cl, 45.0 / mt, mode='nearest')
    u = np.clip((A - cls_[None]) / np.maximum(0.5 * wls[None], 0.5), -1.2, 1.2)
    au = np.abs(u)
    dl = d_in / np.maximum(0.5 * wls[None], 1.0)               # distance to the true lip / half width
    # ---------------------------------------------------------------- interior luminance
    t_foot = 0.0
    sn = np.where(t < T.T_HOT, (T.T_HOT - t) / (T.T_HOT - t_foot), (t - T.T_HOT) / (T.T_TOP - T.T_HOT))
    sn = np.clip(sn, 0.0, 1.0)
    Yb = (0.95 + 1.10 * (1.0 - sn ** 1.35))[None, :]
    w_hot = float(np.interp(T.T_HOT, t, wls))
    a_hot = float(np.interp(T.T_HOT, t, cls_)) + T.HOT_OFF * w_hot
    Yh = 1.05 * np.exp(-((TT - T.T_HOT) / 165.0) ** 2 - ((AA - a_hot) / (0.24 * w_hot)) ** 2)
    Y = Yb + Yh
    Y = Y * (1.0 - 0.22 * T.smoothstep(0.30, 1.0, au) - 0.25 * T.smoothstep(0.30, 0.04, dl))   # deeper in the middle
    fogf = field((Hs, Ws), (110.0 / ma, 170.0 / mt), 2, 1.0)
    Y = Y * (1.0 + 0.08 * np.clip(fogf, -2.5, 2.5) / 1.5)
    # veils v6 (gate round 8, awe r4 B1.7): soft torn SHEETS, each a soft step along a line tilted 15-35 deg off the
    # axis; the bright side decays away from the edge (a sheet of lit mist in front of the far white). No lobe, no streak.
    veil = np.zeros((Hs, Ws), np.float32)
    coolv = np.zeros((Hs, Ws), np.float32)
    msk = T.smoothstep(4.0, 22.0, d_in) * ib
    for (tc_, af, ang, ln, sgn, g, dec) in T.VEILS6:
        ac_ = float(np.interp(tc_, t, cls_)) + af * 0.5 * float(np.interp(tc_, t, wls))
        th_ = math.radians(ang)
        dt_, da_ = math.cos(th_), math.sin(th_)
        sA = (TT - tc_) * dt_ + (AA - ac_) * da_            # along the sheet edge
        qA = (-(TT - tc_) * da_ + (AA - ac_) * dt_) * sgn  # across it (+ = the bright side)
        step = T.smoothstep(-9.0, 9.0, qA) * np.exp(-np.maximum(qA, 0.0) / dec)
        win = T.smoothstep(0.5 * ln, 0.5 * ln - 70.0, np.abs(sA))
        veil += g * step * win * msk
        coolv += 0.5 * T.smoothstep(4.0, -14.0, qA) * np.exp(-np.maximum(-qA, 0.0) / 30.0) * win * msk
    veil = gaussian_filter(veil, (2.0 / ma, 2.0 / mt))
    Y = Y * (1.0 + veil)
    # the FAR LIP: just inside the right lip the white is the far wall of the hole seen in perspective, a little darker
    e_r = aR[None, :] - A
    fl0, fl1, fld = T.FAR_LIP
    farl = T.smoothstep(fl0 * wls[None], (fl0 + 0.015) * wls[None], e_r) * T.smoothstep(fl1 * wls[None], (fl1 - 0.02) * wls[None], e_r)
    farl = farl * T.smoothstep(40.0, 120.0, t)[None, :] * T.smoothstep(T.T_TOP * 0.85, T.T_TOP * 0.6, t)[None, :]
    Y = Y * (1.0 - fld * gaussian_filter(farl * ib, (1.5 / ma, 4.0 / mt)))
    Y = np.maximum(Y, 0.25)
    # ---------------------------------------------------------------- colour (equal luminance warm -> cool)
    k = 0.12 + 0.35 * T.smoothstep(0.35, 1.0, au) + 0.35 * T.smoothstep(0.35, 0.03, dl) + 0.45 * (sn ** 1.2)[None, :] \
        - 0.35 * (Yh / 1.05) + 0.35 * coolv
    k = np.clip(k, 0.0, 1.0)
    col = Y[..., None] * (WARM[None, None] * (1 - k[..., None]) + COOL[None, None] * k[..., None])
    rgb = col * inside[..., None]
    alpha = inside.copy()
    # ---------------------------------------------------------------- the fibre cross-section band (broken)
    bw = np.clip(0.016 * wl, 2.0, 6.0)[None, :]
    # v6 (tech r4 M4 / m14): BROKEN (<= ~50 % of the perimeter lit) and brighter / bluer (#E2E8F3: L* 92, b* -6)
    on_l = T.smoothstep(0.02, 0.22, T.fbm(t / 30.0, 611, 2) + 0.18 * T.fbm(t / 7.0, 612, 2))[None, :]
    on_r = T.smoothstep(0.02, 0.22, T.fbm(t / 30.0, 621, 2) + 0.18 * T.fbm(t / 7.0, 622, 2))[None, :]
    on = np.where(A < cl[None], on_l, on_r)
    fb = T.smoothstep(bw + 1.0, bw - 0.6, d_in) * ib * on * T.smoothstep(15.0, 60.0, t)[None, :]
    fibre_col = FIBRE * np.array([0.97, 0.99, 1.06]) * (0.86 + 0.26 * (1 - sn ** 1.5))[None, :, None]
    rgb = rgb * (1 - fb[..., None]) + fibre_col * fb[..., None]
    # ---------------------------------------------------------------- thin stretched cloth glowing outside the lip
    stretch = np.exp(-((t - T.STRETCH_T[0]) / T.STRETCH_T[1]) ** 2)
    st_l, st_r = stretch.copy(), stretch.copy()
    for k_ in range(len(T.GRIPS)):
        g_, _ = T.grip_kit(k_)
        tg, ag = T.to_ta(g_[0], g_[2])
        gg = np.exp(-((t - tg) / T.STRETCH_GRIP_SIGMA) ** 2)
        if T.GRIPS[k_][0] < 0:
            st_l = np.maximum(st_l, gg)
        else:
            st_r = np.maximum(st_r, gg)
    thick_l = 0.5 + 0.5 * T.fbm(t / 70.0, 631, 3)
    thick_r = 0.5 + 0.5 * T.fbm(t / 70.0, 641, 3)
    thin_l = st_l * T.smoothstep(0.62, 0.30, thick_l)
    thin_r = st_r * T.smoothstep(0.62, 0.30, thick_r)
    thin = np.where(A < cl[None], thin_l[None, :], thin_r[None, :])
    wg = 12.0 + 26.0 * np.where(A < cl[None], st_l[None, :], st_r[None, :])
    outside = 1.0 - inside
    prof = np.exp(-d_out / (0.38 * wg)) * outside
    gc = T.smoothstep(0.0, 0.55 * wg, d_out)[..., None]
    tc = THIN_HOT[None, None] * (1 - gc) + THIN_COLD[None, None] * gc
    rgb += tc * (prof * thin)[..., None] * 0.85
    alpha = np.maximum(alpha, 0.35 * prof * thin)          # the thin cloth still dims the sky behind a little
    # a whisper of edge light everywhere (anti-alias; NOT a drawn outline: ~L* +4 over the band at 2 m)
    rgb += GLOW[None, None] * (0.05 * np.exp(-d_out / 3.0) * outside)[..., None]
    # ---------------------------------------------------------------- dark folds turned toward the bus
    for (sd, tc_, ln, dfrac, skew) in T.EDGE_FOLDS:
        x = (t - tc_) / (0.5 * ln)
        xs = np.clip(x + skew * (1 - np.clip(x, -1, 1) ** 2) * 0.35, -1, 1)
        pr = (np.clip(1 - xs ** 2, 0, 1) ** 1.3) * (np.abs(x) < 1)            # pointed ends (a crescent, not a blob)
        dep = (dfrac * wls * pr)[None, :]
        e = (A - aL[None, :]) if sd < 0 else (aR[None, :] - A)        # inward distance from that lip
        m_in = T.smoothstep(dep + 0.7, dep - 0.5, e) * (dep > 0.3)
        # outside the lip the same roll continues as a darker shadow of the cloth (no isolated island)
        m_out = T.smoothstep(-2.2 * dep - 2.0, 0.0, e) * (e < 0) * (dep > 0.3) * 0.55
        m = np.maximum(m_in * (e >= -0.5), m_out)
        crest = np.exp(-((e - 0.40 * dep) / (0.16 * dep + 0.6)) ** 2) * m_in
        fc = FOLD_DARK[None, None] * (1 - 0.3 * crest[..., None]) + THIN_COLD[None, None] * (0.45 * crest)[..., None]
        rgb = rgb * (1 - m[..., None]) + fc * m[..., None]
        alpha = np.maximum(alpha, m)
    # ---------------------------------------------------------------- frayed thread clusters (lit, curling out)
    rng = np.random.default_rng(97)
    lay = Image.new('L', (Ws, Hs), 0)
    dr = ImageDraw.Draw(lay)
    tx = lambda tt: (tt - T.T_MIN) / mt
    ay = lambda aa: (T.A_MAX - aa) / ma
    # v6 (awe r4 B1.9): clusters from ONE root, every strand tapering FRAY_W[0] -> FRAY_W[1] m and drooping (no whiskers)
    for (sd, tc_, n, (l0, l1), spread) in T.FRAYS6:
        l, r = T.lips(np.array([tc_]))
        a_root = float(r[0] if sd > 0 else l[0])
        l2, r2 = T.lips(np.array([tc_ + 1.0]))
        slope = float(r2[0] if sd > 0 else l2[0]) - a_root
        nrm = math.atan2(sd * 1.0, -slope * sd)
        for j in range(n):
            tt = tc_ + rng.uniform(-4.0, 4.0)
            ang = nrm + math.radians((j - (n - 1) / 2) / max(n - 1, 1) * spread * 1.6 + rng.uniform(-4, 4))
            L = rng.uniform(l0, l1)
            pts, ttt, aaa = [], tt, a_root - sd * 1.5
            nseg = 22
            wav = rng.uniform(0, 6.28)
            for q in range(nseg + 1):
                pts.append((tx(ttt), ay(aaa)))
                f_ = q / nseg
                down = math.atan2(-1.0, 0.0)
                an = ang + (((down - ang + math.pi) % (2 * math.pi)) - math.pi) * 0.85 * f_ ** 1.3 + 0.18 * math.sin(wav + 4 * f_)
                ttt += math.cos(an) * L / nseg
                aaa += math.sin(an) * L / nseg
            v0 = rng.uniform(0.7, 1.0)
            for q in range(nseg):
                f_ = q / nseg
                wm = T.FRAY_W[0] + (T.FRAY_W[1] - T.FRAY_W[0]) * f_ ** 0.8
                dr.line([pts[q], pts[q + 1]], fill=int(255 * v0 * (1 - 0.45 * f_)), width=max(1, int(round(wm / ma))))
    fr = np.asarray(lay, np.float32) / 255.0 * outside
    frc = FIBRE[None, None] * 0.55 * (1 - T.smoothstep(0, 30, d_out))[..., None] + GLOW[None, None] * 0.45 * T.smoothstep(0, 30, d_out)[..., None]
    rgb += frc * fr[..., None]
    alpha = np.maximum(alpha, 0.5 * fr)
    # ---------------------------------------------------------------- threads bridging the gap
    # v6 (awe r4 B1.5): every thread hangs from ONE lip and is snapped; none spans the whole gap, none parallel
    for (kind, sd, t0_, ang, reach, sagf, wd, droop) in T.THREADS6:
        l0_, r0_ = T.lips(np.array([t0_]))
        a0 = float(r0_[0] if sd > 0 else l0_[0]) + sd * 3.0
        wloc = float(r0_[0] - l0_[0])
        if kind == 'reach':
            run = reach * wloc
            xs = np.linspace(0, 1, 360)
            th_ = math.radians(ang)
            ca = a0 - sd * run * xs
            ct = t0_ + run * math.tan(th_) * xs - sagf * run * 4 * xs * (1 - xs * 0.6)
            # the broken end droops: a short curl down (-t) toward the hanging side
            nd = max(int(droop / 1.5), 4)
            dd = np.linspace(0, 1, nd)[1:]
            ca = np.concatenate([ca, ca[-1] - sd * 0.25 * droop * np.sin(dd * 1.3)])
            ct = np.concatenate([ct, ct[-1] - droop * dd ** 1.2])
            ws = np.linspace(0, 1, len(ca))
            wdd = wd * (1.0 - 0.7 * ws)
        else:      # snapped: hangs from the lip, curling down toward the foot, tapering
            span = wloc
            xs = np.linspace(0, 1, 300)
            angs = np.radians(-8.0 - 75.0 * xs ** 1.3)
            ds = reach * span / 299
            ca = a0 - sd * np.concatenate([[0], np.cumsum(np.cos(angs[:-1]) * ds)])
            ct = t0_ + np.concatenate([[0], np.cumsum(np.sin(angs[:-1]) * ds)])
            wdd = wd * (1 - 0.65 * xs)
        sub = (TT > ct.min() - 20) & (TT < ct.max() + 20) & (AA > ca.min() - 20) & (AA < ca.max() + 20)
        ii = np.nonzero(sub.any(0))[0]
        jj = np.nonzero(sub.any(1))[0]
        if len(ii) == 0:
            continue
        sl = (slice(jj[0], jj[-1] + 1), slice(ii[0], ii[-1] + 1))
        d, f = _polyline_dist(TT[sl], AA[sl], ct, ca, 12.0)
        hw = 0.5 * np.interp(f, np.linspace(0, 1, len(wdd)), wdd)
        core = T.smoothstep(hw + 0.55, hw - 0.35, d)
        rimm = np.exp(-((d - hw - 0.6) / 0.7) ** 2) * (1 - core)
        ins = inside[sl]
        cur = rgb[sl]
        thr = THREAD5[None, None] * (0.85 + 0.15 * T.smoothstep(0, 1, f))[..., None]
        cur = cur * (1 - core[..., None] * ins[..., None]) + thr * (core * ins)[..., None]
        cur = cur + FIBRE[None, None] * (0.12 * rimm * ins)[..., None]
        glow_o = (core * (1 - ins))[..., None] * THIN_HOT[None, None] * 0.75
        rgb[sl] = cur + glow_o
        alpha[sl] = np.maximum(alpha[sl], core * np.maximum(ins, 0.6))
    # ---------------------------------------------------------------- borders
    lo, hi = lens_footprint(t)
    d_border = np.minimum(A - lo[None], hi[None] - A)
    d_border = np.minimum(d_border, np.minimum(t - (T.T_MIN + 4), (T.T_MAX - 4) - t)[None, :])
    edge_fade = T.smoothstep(0.0, 18.0, d_border)
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
    """v7 (gate round 9: the v6 crack was a smooth white cone, its +-1.25 m fbm jag only ~2 px in the key, so the visible
    root third read as a HORN / THORN). A rip in woven cloth:
      * it runs along the weave: the crack centre STAIR-STEPS (runs of 8-22 strip m, shifts 1.2-3.2 m, softened 0.5 m),
        the step size scaled down toward the thin end (a thin zigzag would read as lightning);
      * torn edges: fibrous jag 0.6-1.6 m at 2-6 m cells on each lip independently;
      * PINCHES at u 0.12 / 0.40 / 0.66 where the cloth still holds: the gap narrows to ~25 %, bridged by 2-3 DARK warp
        threads (dyed cloth in front of the white), one of them snapped with a white tuft;
      * a few more single bridging threads elsewhere, sagging and slanted, never a regular ladder;
      * edge fibres: short undyed white hairs (1.5-5 m) leaning out of both lips, irregular spacing;
      * interior mottled (x 0.78-1.0 at 25 m cells) and hotter where it is widest; root x 0.75 -> tip x 0.35 as v6;
      * dark torn lips either side (premultiplied A 0.45) follow the jagged edge. No lavender.
    strip space: u along (0 root -> 1 tip), v across (0..1, crack centre 0.5)."""
    r = T.RIPS[0]
    L = r['length']
    Ws, Hs = W * SS, Hh * SS
    u = (np.arange(Ws) + 0.5) / Ws
    v = (np.arange(Hs) + 0.5) / Hs
    M = 2 * T.RIP_MARGIN
    y = (0.5 - v)[:, None] * M                       # strip metres across (+ up)
    xm = u * L                                       # strip metres along
    rng = np.random.default_rng(707)
    w0 = r['width']
    half0 = 0.5 * w0 * np.clip(1.0 - u, 0, 1) ** 1.15 + 0.35
    # pinches: the cloth still holding
    PINCH = [(0.12, 0.020, 0.74), (0.40, 0.024, 0.70), (0.66, 0.028, 0.62)]
    pin = np.ones_like(u)
    for pc, pw, pd in PINCH:
        pin *= 1 - pd * np.exp(-((u - pc) / pw) ** 2)
    half = half0 * pin
    # weave stair-steps of the crack centre
    c = np.zeros_like(u)
    x = 0.0; off = 0.0
    edges = []
    while x < L:
        run = rng.uniform(8.0, 22.0)
        edges.append((x, off))
        x += run
        off = off + rng.choice([-1, 1]) * rng.uniform(1.2, 3.2)
        off = float(np.clip(off, -5.0, 5.0))
    for (x0, o), nxt in zip(edges, edges[1:] + [(L + 1, edges[-1][1])]):
        c[(xm >= x0) & (xm < nxt[0])] = o
    from scipy.ndimage import gaussian_filter1d
    c = gaussian_filter1d(c, 0.5 / (L / Ws))
    c *= np.clip(half0 / (0.5 * w0), 0.25, 1.0)      # small steps where it is thin (no lightning)
    jag1 = 0.9 * T.fbm(xm / 3.0, 711, 3) + 0.7 * T.fbm(xm / 9.0, 712, 2)
    jag2 = 0.9 * T.fbm(xm / 3.0, 713, 3) + 0.7 * T.fbm(xm / 9.0, 714, 2)
    k = np.clip(half / 3.0, 0.25, 1.0)
    lo = (c - half + jag1 * k)[None, :]
    hi = (c + half + jag2 * k)[None, :]
    lo, hi = np.minimum(lo, hi - 0.25), np.maximum(hi, lo + 0.25)
    inside = ((y > lo) & (y < hi)).astype(np.float32)
    d_out = np.maximum(lo - y, y - hi)
    d_in = np.minimum(y - lo, hi - y)
    Bu = (0.35 + 0.40 * (1 - u) ** 0.9)
    mott = 0.78 + 0.22 * (0.5 + 0.5 * T.fbm(xm / 25.0, 715, 3))
    wide = 0.86 + 0.14 * np.clip(half / (0.5 * w0 * 0.8), 0, 1)
    B = (Bu * mott * wide)[None, :]
    ez = np.exp(-np.maximum(d_in, 0) / 1.2)
    col = (CORE / max(_lum(CORE), 1e-6) * 0.5 + COOL * 0.5) * _lum(CORE) * 0.62
    rgb = col[None, None] * (B * (1 - 0.30 * ez))[..., None] * inside[..., None]
    alpha = inside.copy()
    lipw = 2.5 + 5.0 * np.clip(half / 6.0, 0, 1)[None, :]
    dark = np.exp(-np.maximum(d_out, 0) / lipw) * (1 - inside)
    alpha = np.maximum(alpha, 0.45 * dark)

    def to_px(xx, yy):
        return (xx / L * Ws, (0.5 - yy / M) * Hs)
    pxm = Hs / M                                      # px per strip metre across
    # edge fibres: undyed white hairs leaning out of both lips
    fib = Image.new('L', (Ws, Hs), 0)
    df = ImageDraw.Draw(fib)
    xx = rng.uniform(0.5, 2.0)
    while xx < L * 0.93:
        i = min(int(xx / L * Ws), Ws - 1)
        uu = xx / L
        hk = float(np.clip(half[i] / 3.5, 0.15, 1.0))     # fewer, shorter hairs where the crack is thin
        for side in (-1, 1):
            if rng.random() < 0.50 * hk:
                e = (hi[0, i] if side > 0 else lo[0, i])
                ln = rng.uniform(1.2, 4.2) * (0.35 + 0.65 * hk)
                ang = math.radians(rng.uniform(-35, 35) + (90 if side > 0 else -90))
                lean = rng.uniform(-0.6, 0.6)
                pts = []
                for q in range(6):
                    f = q / 5.0
                    pts.append(to_px(xx + math.cos(ang) * ln * f + lean * f * f * ln * 0.3,
                                     e + math.sin(ang) * ln * f - side * 0.15))
                df.line(pts, fill=int(rng.uniform(130, 230)), width=max(1, int(0.45 * pxm)))
        xx += rng.uniform(1.0, 3.2)
    fs = np.asarray(fib, np.float32) / 255.0 * (1 - inside)
    rgb += col[None, None] * (0.55 * B)[..., None] * fs[..., None]
    alpha = np.maximum(alpha, 0.85 * fs)
    # bridging threads: dark dyed warp threads across the gap (2-3 at each pinch + a few singles), one snapped
    thr = Image.new('L', (Ws, Hs), 0)
    dt = ImageDraw.Draw(thr)
    tuft = Image.new('L', (Ws, Hs), 0)
    dtu = ImageDraw.Draw(tuft)
    spots = []
    for pc, pw, pd in PINCH:                          # a tight cluster at the narrowest point (some cross)
        n = int(rng.integers(2, 4))
        for j in range(n):
            spots.append(pc + rng.uniform(-0.45, 0.45) * pw)
    spots += [0.045, 0.27, 0.53]
    for sidx, uu in enumerate(spots):
        i = min(int(uu * Ws), Ws - 1)
        a0, a1 = lo[0, i] - 0.8, hi[0, i] + 0.8
        slant = rng.uniform(-0.9, 0.9) * (a1 - a0)
        sag = rng.uniform(0.1, 0.35) * (a1 - a0) * rng.choice([-1, 1]) * 0.3
        snapped = (sidx == 1) or (sidx == len(spots) - 2)
        pts = []
        nq = 10
        stop = nq if not snapped else int(nq * rng.uniform(0.35, 0.6))
        for q in range(stop + 1):
            f = q / nq
            pts.append(to_px(uu * L + slant * f + sag * 4 * f * (1 - f) * 0.2, a0 + (a1 - a0) * f + sag * 4 * f * (1 - f)))
        dt.line(pts, fill=255, width=max(2, int(rng.uniform(0.55, 0.95) * pxm)))
        if snapped:                                   # a white tuft where it broke
            x_, y_ = pts[-1]
            for q in range(4):
                a_ = rng.uniform(0, 2 * math.pi)
                l_ = rng.uniform(0.8, 2.0) * pxm
                dtu.line([(x_, y_), (x_ + math.cos(a_) * l_ * 0.4, y_ + math.sin(a_) * l_)], fill=200,
                         width=max(1, int(0.35 * pxm)))
    ts = np.asarray(thr, np.float32) / 255.0
    rgb *= (1 - ts)[..., None]
    alpha = np.maximum(alpha, ts)
    tu = np.asarray(tuft, np.float32) / 255.0
    rgb += col[None, None] * (0.6 * B)[..., None] * tu[..., None]
    alpha = np.maximum(alpha, 0.8 * tu)
    # 2-3 fibre strands where the crack runs out (u 0.88-1)
    lay = Image.new('L', (Ws, Hs), 0)
    dr = ImageDraw.Draw(lay)
    for j in range(3):
        u0 = rng.uniform(0.86, 0.92)
        yy = rng.uniform(-1.0, 1.0)
        ang = rng.uniform(-0.10, 0.10)
        pts = []
        uu_, vv_ = u0, yy
        for q in range(12):
            pts.append((uu_ * Ws, (0.5 - vv_ / M) * Hs))
            uu_ += 0.009
            vv_ += ang * 0.009 * L + rng.normal(0, 0.25)
        dr.line(pts, fill=200, width=max(1, int(0.9 / M * Hs)))
    fs2 = np.asarray(lay, np.float32) / 255.0 * (1 - inside)
    rgb += col[None, None] * 0.30 * fs2[..., None]
    alpha = np.maximum(alpha, 0.5 * fs2)
    fade = (T.smoothstep(T.RIP_MARGIN, T.RIP_MARGIN * 0.75, np.abs(y)) * T.smoothstep(1.0, 0.97, u)[None, :])
    rgb *= fade[..., None]; alpha *= fade
    return box_down(rgb, SS), box_down(alpha, SS)


def make_rip_v6(W=1024, Hh=128, SS=3):
    """v6 (gate round 8, awe r4 B1.6: the branch read as 'a detached lavender spindle, a leaf'): a stress crack that
    RUNS ON from the main lip: widest at its root (joined to the lip, the strip's u = 0 overlaps it by ~6 m), tapering
    monotonically to a hairline, jagged (fbm), the undyed white x 0.75 at the root -> x 0.35 at the tip, NO lavender
    fill or glow; dark torn lips either side (premultiplied A 0.45, no colour); 2-3 fibre strands at the tip.
    strip space: u along (0 root -> 1 tip), v across (0..1, crack centre 0.5)."""
    r = T.RIPS[0]
    L = r['length']
    Ws, Hs = W * SS, Hh * SS
    u = (np.arange(Ws) + 0.5) / Ws
    v = (np.arange(Hs) + 0.5) / Hs
    y = (0.5 - v)[:, None] * 2 * T.RIP_MARGIN
    w0 = r['width']
    half = (0.5 * w0 * np.clip(1.0 - u, 0, 1) ** 1.35 + 0.35)[None, :]            # monotone: widest at the root
    jag1 = (0.35 * T.fbm(u * L / 9.0, 401, 2) + 0.9 * T.fbm(u * L / 40.0, 402, 2))[None, :]
    jag2 = (0.35 * T.fbm(u * L / 9.0, 403, 2) + 0.9 * T.fbm(u * L / 40.0, 404, 2))[None, :]
    k = np.minimum(1, half / 2.5)
    lo, hi = -half + jag1 * k, half + jag2 * k
    inside = ((y > lo) & (y < hi)).astype(np.float32)
    d_out = np.maximum(lo - y, y - hi)
    d_in = np.minimum(y - lo, hi - y)
    Bu = (0.35 + 0.40 * (1 - u) ** 0.9)[None, :]                                  # x 0.75 at the root -> 0.35
    ez = np.exp(-np.maximum(d_in, 0) / 1.5)
    col = (CORE / max(_lum(CORE), 1e-6) * 0.5 + COOL * 0.5) * _lum(CORE) * 0.62
    rgb = col[None, None] * (Bu * (1 - 0.30 * ez))[..., None] * inside[..., None]
    alpha = inside.copy()
    lipw = 3.0 + 6.0 * np.clip(half / 6.0, 0, 1)
    dark = np.exp(-np.maximum(d_out, 0) / lipw) * (1 - inside)
    alpha = np.maximum(alpha, 0.45 * dark)
    # 2-3 fibre strands where the crack runs out (u 0.88-1): thin lines continuing on, the white x 0.3
    rng = np.random.default_rng(405)
    lay = Image.new('L', (Ws, Hs), 0)
    dr = ImageDraw.Draw(lay)
    for j in range(3):
        u0 = rng.uniform(0.86, 0.92)
        yy = rng.uniform(-1.0, 1.0)
        ang = rng.uniform(-0.10, 0.10)
        pts = []
        uu_, vv_ = u0, yy
        for q in range(12):
            pts.append((uu_ * Ws, (0.5 - vv_ / (2 * T.RIP_MARGIN)) * Hs))
            uu_ += 0.009
            vv_ += ang * 0.009 * L + rng.normal(0, 0.25)
        dr.line(pts, fill=200, width=max(1, int(0.9 / (2 * T.RIP_MARGIN) * Hs)))
    fs = np.asarray(lay, np.float32) / 255.0 * (1 - inside)
    rgb += col[None, None] * 0.30 * fs[..., None]
    alpha = np.maximum(alpha, 0.5 * fs)
    fade = (T.smoothstep(T.RIP_MARGIN, T.RIP_MARGIN * 0.75, np.abs(y)) * T.smoothstep(1.0, 0.97, u)[None, :])
    rgb *= fade[..., None]; alpha *= fade
    return box_down(rgb, SS), box_down(alpha, SS)


# ======================================================================================== fibre atlas
def make_fibres(W=1024, Hh=1024, SS=2, ncol=8):
    """v6 (gate round 8, awe r4 m2: the v5 atlas was vertical trunk-and-branch stems = birches / wheat): every cell
    holds 1-5 loose fibres that CURVE and CROSS each other, tapered at both ends, no common trunk, no branching."""
    Ws, Hs = W * SS, Hh * SS
    cw = Ws // ncol
    lay = Image.new('L', (Ws, Hs), 0)
    dr = ImageDraw.Draw(lay)
    rng = np.random.default_rng(23)
    for c in range(ncol):
        nstr = [1, 2, 3, 2, 4, 3, 5, 2][c]
        for sidx in range(nstr):
            x0 = c * cw + cw * rng.uniform(0.25, 0.75)
            y0 = Hs * rng.uniform(0.82, 0.98)
            ang = -math.pi / 2 + rng.normal(0, 0.45)
            curv = rng.normal(0, 1.6) / Hs
            L = Hs * rng.uniform(0.45, 0.85)
            n = 70
            wid0 = rng.uniform(2.5, 5.0) * SS
            pts = []
            x, y = x0, y0
            for k in range(n + 1):
                pts.append((x, y))
                ang += curv * L / n + rng.normal(0, 0.02)
                x = min(max(x + math.cos(ang) * L / n, c * cw + 4), (c + 1) * cw - 5)
                y += math.sin(ang) * L / n
            for k in range(n):
                f = k / n
                w = max(1, int(round(wid0 * math.sin(math.pi * min(max(f, 0.04), 0.96)) ** 0.6)))
                v = int(255 * (0.55 + 0.45 * math.sin(math.pi * f) ** 0.5))
                dr.line([pts[k], pts[k + 1]], fill=v, width=w)
    a = np.asarray(lay, np.float32) / 255.0
    a = box_down(a, SS)
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
        # v5: feathered torn edge (2.5 m), no 1-sample stair-step at 4x (Unity: Mip Maps Preserve Coverage)
        cov = T.smoothstep(0.0, 2.5 / (1.1 * Lm), e2 - r).astype(np.float32)
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
    """v6b (gate round 8, awe r4 B1.3 / tech M8): long DRAPED creases of the pulled sky-cloth, dominated by their SHADE
    (a lit crest only on the wound side): from every grip 3 creases leave the lip 15 m out, spread +-35 deg about the
    pull and SAG with gravity as they run out (curving down 5-10 deg / 100 m), 0.9-1.4 x the max width long, 30-46 m
    wide; 2 down-and-out from either side of the foot. Each: (anchor t, anchor a, start angle deg from +t toward +a,
    curvature deg / 100 m, length m, root half-width m, gain)."""
    out = []
    rng = np.random.default_rng(95)
    Wm = 300.0
    bot_t = 60.0
    for ang in (-128, -100, 100, 126):
        aL, aR = T.lips(np.array([bot_t]))
        sd = 1.0 if ang > 0 else -1.0
        a0 = float(aR[0] if ang > 0 else aL[0]) + sd * 15.0
        out.append((bot_t, a0, ang + rng.uniform(-6, 6), sd * rng.uniform(3, 6),
                    rng.uniform(0.7, 1.0) * Wm, rng.uniform(15, 20), 0.8))
    for k in range(len(T.GRIPS)):
        g, _ = T.grip_kit(k)
        tg, _ag = T.to_ta(g[0], g[2])
        sd = T.GRIPS[k][0]
        aL, aR = T.lips(np.array([float(tg)]))
        a0 = float(aR[0] if sd > 0 else aL[0]) + sd * 15.0
        base = 90.0 if sd > 0 else -90.0          # outward, along the pull
        # v6c: the creases of one side FAN gently and never cross: the angle follows the grip's height about the hot
        # spot (upper grips pull up-and-out, lower ones down-and-out); a second, shorter crease beside two grips
        fan = float(np.clip((tg - T.T_W) / T.T_W, -1, 1)) * 32.0
        angs = [fan] + ([fan + 13.0 * (1 if k % 2 else -1)] if k in (0, 4) else [])
        for j, dang in enumerate(angs):
            out.append((float(tg), a0, base - sd * (dang + rng.uniform(-3, 3)), sd * rng.uniform(4, 8),
                        rng.uniform(1.0, 1.4) * Wm * (1.0 if j == 0 else 0.7), rng.uniform(16, 22), 1.0))
    return out


def make_skyfolds(N=1024, SS=2):
    """v6: the sky is cloth pulled apart. Premultiplied card (just behind the lens): RGB = the wound's light on the
    flank of each crease that faces the wound (+7..+10 L* over the band near the lips), A = the shade on the far flank
    (-5..-8 L*). Strength falls off over ~600 m, nothing beyond 3 tear widths, nothing inside the hole."""
    from scipy.spatial import cKDTree
    n = N * SS
    t = T.FOLD_T0 + (np.arange(n) + 0.5) / n * (T.FOLD_T1 - T.FOLD_T0)
    a = T.FOLD_A0 + (np.arange(n) + 0.5) / n * (T.FOLD_A1 - T.FOLD_A0)
    TT, AA = np.meshgrid(t, a, indexing='ij')            # rows = t, cols = a
    aL, aR = T.lips(t)
    ins = (AA > aL[:, None]) & (AA < aR[:, None])
    mt = (T.FOLD_T1 - T.FOLD_T0) / n
    ma = (T.FOLD_A1 - T.FOLD_A0) / n
    d = distance_transform_edt(~ins, sampling=(mt, ma))
    lit = np.zeros_like(TT)
    shade = np.zeros_like(TT)
    for (t0, a0, ang0, curv, L, w0, gk) in _fold_strokes():
        m = 800
        ss_ = np.linspace(0, 1, m)
        angs = np.radians(ang0 + curv * ss_ * L / 100.0)
        ct = t0 + np.concatenate([[0], np.cumsum(np.cos(angs[:-1]) * L / (m - 1))])
        ca = a0 + np.concatenate([[0], np.cumsum(np.sin(angs[:-1]) * L / (m - 1))])
        tree = cKDTree(np.stack([ct, ca], 1))
        dist, idx = tree.query(np.stack([TT.ravel(), AA.ravel()], 1), distance_upper_bound=w0 * 4 + 10)
        dist = dist.reshape(TT.shape)
        idx = np.clip(idx.reshape(TT.shape), 0, m - 1)
        ok = np.isfinite(dist)
        f = np.where(ok, ss_[idx], 1.0)
        tx_, ta_ = np.cos(angs)[idx], np.sin(angs)[idx]
        nx_, na_ = -ta_, tx_
        cx_, ca_ = T.T_W - ct[idx], 0.0 - ca[idx]
        sgn = np.sign(nx_ * cx_ + na_ * ca_ + 1e-6)
        rel_t, rel_a = TT - ct[idx], AA - ca[idx]
        sd_ = (rel_t * nx_ + rel_a * na_) * sgn
        width = w0 * (1 - 0.75 * f)
        env = T.smoothstep(0.0, 0.18, f) * T.smoothstep(1.0, 0.40, f) * ok * gk
        lit += env * np.exp(-((sd_ - 0.35 * width) / np.maximum(width * 0.45, 1.0)) ** 2)
        shade += env * np.exp(-((sd_ + 0.55 * width) / np.maximum(width * 1.0, 1.0)) ** 2)
    # v6b: the creases live in the lit band round the wound (within ~1.6 widths), not out in the void
    fall = np.exp(-d / 420.0) * T.smoothstep(6.0, 30.0, d) * T.smoothstep(2.0 * 300.0, 1.1 * 300.0, d)
    lit = np.clip(lit, 0, 1.0) * fall
    shade = np.clip(shade, 0, 1.0) * fall
    light = hexlin('#A99DE1') / hexlin('#A99DE1').max()
    rgb = light[None, None, :] * (lit * 0.03)[..., None]
    alpha = np.clip(shade * 0.40, 0, 0.42)
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
