# -*- coding: utf-8 -*-
"""v2 procedural scene-linear test frames for the scenes the critiques rebuilt (4, 4c, 7a, 7b, 9a, 9b, 6/8 hue-mapped mocks).
Every key colour is SOLVED so that under the scene's own v2 grade it lands on the bible's display target.
Geometry is angular: 960x402 (2.39:1), hFOV 90 deg, rectilinear, camera pitch given per frame."""
import math
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
from scenes_proc import SL, W, H, g2, blend, rng as _rng0
from lutlib import ppv2

F = (W / 2) / math.tan(math.radians(45.0))          # focal length in px (hFOV 90)
rng = np.random.default_rng(11)
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)

def cam(pitch):
    """per-pixel azimuth / elevation (deg) for a camera pitched up by `pitch` deg."""
    X = xx - W / 2 + 0.5; Y = H / 2 - yy - 0.5
    d = np.stack([X, np.full_like(X, F), Y], -1)
    p = math.radians(pitch)
    R = np.array([[1, 0, 0], [0, math.cos(p), -math.sin(p)], [0, math.sin(p), math.cos(p)]])
    d = d @ R.T; d /= np.linalg.norm(d, axis=-1, keepdims=True)
    az = np.degrees(np.arctan2(d[..., 0], d[..., 1])); el = np.degrees(np.arcsin(d[..., 2]))
    return az, el

def px(az, el, pitch):
    """angles -> pixel (x, y) for the same camera."""
    a, e, p = map(math.radians, (az, el, pitch))
    d = np.array([math.cos(e) * math.sin(a), math.cos(e) * math.cos(a), math.sin(e)])
    R = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])
    c = R @ d
    return W / 2 - 0.5 + F * c[0] / c[1], H / 2 - 0.5 - F * c[2] / c[1]

def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)

def lerpc(a, b, t):
    t = np.asarray(t)[..., None] if np.ndim(t) else t
    return a * (1 - t) + b * t

# ------------------------------------------------------------------ stroke rasteriser (tentacles, fibres, rips)
def stroke(pts, rad, shape=(H, W)):
    """pts: (N,2) pixel centreline, rad: (N,) radius px. Returns (cover 0..1, side -1..1, t 0..1 along)."""
    pts = np.asarray(pts, float); rad = np.asarray(rad, float)
    cover = np.zeros(shape); side = np.zeros(shape); along = np.zeros(shape); best = np.full(shape, 1e9)
    n = len(pts)
    for i in range(n - 1):
        p0, p1 = pts[i], pts[i + 1]; r0, r1 = rad[i], rad[i + 1]
        rmax = max(r0, r1) + 2
        x0 = int(max(min(p0[0], p1[0]) - rmax, 0)); x1 = int(min(max(p0[0], p1[0]) + rmax + 1, shape[1]))
        y0 = int(max(min(p0[1], p1[1]) - rmax, 0)); y1 = int(min(max(p0[1], p1[1]) + rmax + 1, shape[0]))
        if x1 <= x0 or y1 <= y0: continue
        Y, X = np.mgrid[y0:y1, x0:x1].astype(float)
        d = p1 - p0; L2 = max(d @ d, 1e-9)
        t = np.clip(((X - p0[0]) * d[0] + (Y - p0[1]) * d[1]) / L2, 0, 1)
        cx, cy = p0[0] + t * d[0], p0[1] + t * d[1]
        dist = np.hypot(X - cx, Y - cy)
        r = r0 + (r1 - r0) * t
        nd = dist / np.maximum(r, 0.35)
        sgn = np.sign((X - p0[0]) * d[1] - (Y - p0[1]) * d[0])
        sub = best[y0:y1, x0:x1]
        m = nd < sub
        sub[m] = nd[m]
        side[y0:y1, x0:x1][m] = (sgn * nd)[m]
        along[y0:y1, x0:x1][m] = ((i + t) / (n - 1))[m]
        cov = np.clip((r + 0.5 - dist), 0, 1)                 # 1-px antialias; thin strokes keep partial coverage
        cover[y0:y1, x0:x1] = np.maximum(cover[y0:y1, x0:x1], cov * np.minimum(r * 2, 1) ** 0.5)
    return cover, np.clip(side, -1, 1), along

def curve(p0, p1, bend, n=40, curl=0.0):
    """quadratic-ish curve from root p0 to tip p1 with lateral bend (px) and an optional hooked tip."""
    t = np.linspace(0, 1, n)
    p0 = np.array(p0, float); p1 = np.array(p1, float)
    d = p1 - p0; nrm = np.array([-d[1], d[0]]) / (np.linalg.norm(d) + 1e-9)
    pts = p0[None] + t[:, None] * d[None] + (np.sin(np.pi * t) * bend)[:, None] * nrm[None]
    if curl:
        k = t > 0.82
        a = (t[k] - 0.82) / 0.18
        pts[k] += (np.sin(a * np.pi * 0.9) * curl)[:, None] * nrm[None] * (1 - a[:, None] * 0.3)
    return pts

# ------------------------------------------------------------------ 4 the tentacle gate, U7 + 3 s (forward from the hero seat)
def gate(prof='S4'):
    pitch = 2.0
    az, el = cam(pitch)
    S = lambda h: SL(h, prof)
    tear_az, foot_el, top_el, mid_el = 0.0, -1.8, 21.2, 7.7
    h_eye = 52.0
    # --- sky: void; luminous haze band (#484D63 beside the tear -> #2A3041 at 50 deg az; 0-15 deg el; void beyond 60 deg / above +35 deg)
    void = S('#070A14'); band_n = S('#484D63'); band_f = S('#2A3041')
    daz = np.abs(az - tear_az)
    a_t = sstep(0, 50, daz) ** 0.6
    band_col = np.exp(np.log(band_n) * (1 - a_t)[..., None] + np.log(band_f) * a_t[..., None])
    e_w = np.where(el < 3, 1.0, np.interp(el, [3, 15, 35], [1.0, 0.55, 0.0]))
    w = ((1 - sstep(50, 60, daz)) * e_w)[..., None]
    img = np.exp(np.log(void) * (1 - w) + np.log(band_col) * w)
    st = np.zeros((H, W)); k = rng.random((H, W)) < 0.0012
    st[k] = rng.pareto(2.5, k.sum()) * 0.5 + 0.3
    img += S('#8C98B0') * 0.35 * (gaussian_filter(st, 0.6) * (1 - w[..., 0] * 0.8) * (el > 3))[..., None]
    # halo: dusk indigo-violet around the wound, mid-breath
    r_h = np.hypot(az - tear_az, (el - mid_el) / 2.4)
    halo = np.exp(-(r_h / 6.0) ** 2) * 0.9 + np.exp(-(r_h / 16.0) ** 2) * 0.25
    img += (S('#5B57A1') - band_n * 0.6).clip(0) * halo[..., None] * sstep(foot_el - 2, foot_el, el)[..., None]
    # --- far tide: 420 impostor arms at 5-12 km, 150-600 m, +-70 deg around the tear, fogged 80-92 %, leaning in
    for i in range(420):
        a = rng.uniform(-70, 70)
        if abs(a) < 4: continue
        dist = rng.uniform(5000, 12000); hgt = rng.uniform(150, 600)
        base_el = -math.degrees(math.atan(h_eye / dist)); tip_el = math.degrees(math.atan((hgt - h_eye) / dist))
        x0, y0 = px(a, base_el - 0.3, pitch); x1, y1 = px(a - a * 0.03 + rng.uniform(-0.4, 0.4), tip_el, pitch)
        pts = curve((x0, y0), (x1, y1), -np.sign(a) * rng.uniform(1, 4), n=10, curl=np.sign(a) * rng.uniform(0, 2))
        r = np.linspace(max(0.8, 22 / dist * F), 0.25, 10)
        cov, sd, t = stroke(pts, r)
        fog = rng.uniform(0.80, 0.92)
        img = img * (1 - cov[..., None]) + (band_col * fog + S('#0F1116') * (1 - fog)) * cov[..., None]
    # --- cloud sea: moonlit silver tops, #495270 pool under the tear, fogged toward the band
    sea = el < -0.12
    tex = gaussian_filter(rng.standard_normal((H, W)), (1.0, 3.5)) * 0.5 + gaussian_filter(rng.standard_normal((H, W)), (4, 16)) * 1.8
    tex = np.clip(0.55 + tex * 0.5, 0.08, 1.35)
    dd = np.clip(h_eye / np.tan(np.radians(np.maximum(-el, 0.05))), 1, 40000)
    pool = np.exp(-((az - tear_az) / 11.0) ** 2) * sstep(-9, -0.8, el)
    top_col = np.exp(np.log(S('#262F44')) * (1 - pool)[..., None] + np.log(S('#495270')) * pool[..., None])
    cs = top_col * tex[..., None]
    road = np.exp(-((az + 13.0) / (1.6 + 0.30 * np.maximum(-el, 0))) ** 2) * 0.65   # moon road, 60-75 % after the eclipse
    cs += S('#7A89A6') * (road * tex ** 1.5)[..., None]
    fogf = 1 - np.exp(-0.0006 * dd)
    cs = cs * (1 - fogf[..., None]) + band_col * fogf[..., None]
    img = np.where(sea[..., None], cs, img)
    # --- the tear: asymmetric lens, max width 26 % of height at 40 % height; interior = undyed white, fibrous lips
    def lens(s):
        p = math.log(0.5) / math.log(0.4)
        return np.sin(np.pi * np.clip(s, 0, 1) ** p)
    s_el = (el - foot_el) / (top_el - foot_el)
    lean = (el - foot_el) * 0.07
    x_rel = az - tear_az - lean
    wmax = math.degrees(math.atan(0.26 * 680 / 1620)) / 2
    fray = gaussian_filter(rng.standard_normal((H, W)), (5, 0.8)) * 0.22 + gaussian_filter(rng.standard_normal((H, W)), (1.2, 0.5)) * 0.14
    left = -wmax * 0.9 * lens(s_el) * (1 + fray)
    right = wmax * 1.1 * lens(s_el) * (1 - fray * 0.8)
    inside = (x_rel > left) & (x_rel < right) & (s_el > 0) & (s_el < 1)
    halfw = np.maximum((right - left) / 2, 1e-3); cen = (right + left) / 2
    u_in = np.clip(np.abs(x_rel - cen) / halfw, 0, 1)
    core, glow, fib = S('#F5F2EC'), S('#C0B9E4'), S('#E2E8F3')
    depth = 0.72 + 0.28 * lens(s_el)                                 # brightest at the widest part
    mist = gaussian_filter(rng.standard_normal((H, W)), (7, 2.5))
    interior = core * (depth * (0.93 + 0.07 * np.clip(mist * 3, -1, 1)))[..., None]
    interior = np.exp(np.log(interior) * (1 - u_in ** 4)[..., None] + np.log(fib * 0.95) * (u_in ** 4)[..., None])
    img = np.where(inside[..., None], interior, img)
    dl = np.minimum(np.abs(x_rel - left), np.abs(x_rel - right))
    img += glow * (0.45 * np.exp(-(dl / 0.45) ** 2) * (~inside) * sstep(0.0, 0.06, s_el) * (1 - sstep(0.94, 1.04, s_el)))[..., None]
    # lip fibres: short bright threads crossing the edge
    for _ in range(160):
        ss = rng.uniform(0.04, 0.96); sd_ = rng.choice([-1, 1])
        e = foot_el + ss * (top_el - foot_el)
        edge = (wmax * (0.9 if sd_ < 0 else 1.1) * float(lens(ss))) * sd_ + (e - foot_el) * 0.07
        x0, y0 = px(tear_az + edge, e, pitch)
        L = rng.uniform(3, 12)
        pts = curve((x0, y0), (x0 + sd_ * L, y0 + rng.uniform(-3, 5)), rng.uniform(-2, 2), n=6)
        cov, _, _ = stroke(pts, np.linspace(0.55, 0.2, 6))
        img = img * (1 - 0.8 * cov[..., None]) + fib * 0.8 * cov[..., None]
    # peeled flaps: indigo silk folded outward (thin), inner face takes the tear light, outer edge the moon rim
    for sgn, e0, e1, wdt in [(-1, 0.16, 0.58, 1.3), (1, 0.28, 0.74, 1.7), (-1, 0.64, 0.90, 0.9), (1, 0.80, 0.97, 0.6)]:
        ss = (s_el - e0) / (e1 - e0)
        prof_ = np.sin(np.pi * np.clip(ss, 0, 1)) ** 0.8 * wdt
        base = np.where(sgn < 0, left, right)
        rel = (x_rel - base) * sgn
        flap = (rel > 0.0) & (rel < prof_ * (1 + fray * 0.8)) & (ss > 0) & (ss < 1)
        fu = np.clip(rel / np.maximum(prof_, 1e-3), 0, 1)
        fc = np.exp(np.log(S('#3E3C66')) * (1 - fu)[..., None] + np.log(S('#12141F')) * fu[..., None])
        img = np.where(flap[..., None], fc, img)
        img = np.where((flap & (fu > 0.84))[..., None], img + S('#A9C2FF') * 0.45, img)
    # branch rips (U7): thin cracks from the upper end, 25-40 deg off the axis, still propagating
    for ang, ln in [(-33, 0.27), (38, 0.41)]:
        x0, y0 = px(tear_az + (top_el - foot_el) * 0.84 * 0.07, foot_el + (top_el - foot_el) * 0.84, pitch)
        L = ln * (top_el - foot_el) * F / 57.3
        x1 = x0 + math.sin(math.radians(ang)) * L; y1 = y0 - math.cos(math.radians(ang)) * L
        pts = curve((x0, y0), (x1, y1), rng.uniform(-5, 5), n=18) + rng.normal(0, 0.7, (18, 2))
        cov, _, _ = stroke(pts, np.linspace(1.6, 0.25, 18))
        img = img * (1 - cov[..., None]) + fib * 0.85 * cov[..., None]
        img += glow * 0.22 * gaussian_filter(cov, 2.0)[..., None]
    # --- shafts: dark violet beams from the wound, cut by the arms (drawn before them)
    sx, sy = px(tear_az, mid_el, pitch)
    ang_px = np.degrees(np.arctan2(yy - sy, xx - sx)); rr = np.hypot(xx - sx, yy - sy)
    shaft = np.zeros((H, W))
    for a0 in [22, 34, 57, 71, 83, 96, 108, 121, 147, 158]:
        shaft += np.exp(-((ang_px - a0) / rng.uniform(1.2, 2.8)) ** 2) * rng.uniform(0.5, 1.0)
    shaft *= sstep(25, 70, rr) * np.exp(-rr / 380) * (~inside)
    img += (S('#31335A') - band_n * 0.4).clip(0) * 0.6 * shaft[..., None]
    # the eaten moon: only a silver ring of glow shows around colossus 2's crown (az -13, el +8)
    rm = np.hypot(az + 13.0, el - 8.0)
    img += S('#5A6A88') * (0.55 * np.exp(-(rm / 3.0) ** 2) + 0.18 * np.exp(-(rm / 8.0) ** 2))[..., None] * (el > 0)[..., None]
    # --- arms
    def arm(root_az, dist, hgt, lean_to, bend, r_root, curl=0.0, rim=1.0, fog_cap=0.6):
        base_el = -math.degrees(math.atan(h_eye / dist)) - 0.8
        tip_el = math.degrees(math.atan((hgt - h_eye) / dist))
        x0, y0 = px(root_az, base_el, pitch); x1, y1 = px(root_az + lean_to, tip_el, pitch)
        n = 56
        pts = curve((x0, y0), (x1, y1), bend, n=n, curl=curl)
        tt = np.linspace(0, 1, n)
        r = r_root / dist * F * (1.08 - 0.08 * sstep(0, 0.08, tt)) * (1 - tt) ** 0.9 + 0.3
        cov, sd, t = stroke(pts, r)
        f_lin = 1 - math.exp(-0.0006 * dist)
        yrel = t * hgt
        fog = np.minimum(f_lin * np.exp(-np.maximum(0, yrel) / 500.0), fog_cap)
        fog = np.maximum(fog, f_lin * (1 - sstep(0.0, 0.2, t)))
        across = np.sqrt(np.clip(1 - sd ** 2, 0, 1))                     # pseudo-normal z: body roundness
        body = S('#0F1116') * (0.8 + 0.5 * across)[..., None]
        col = body * (1 - fog)[..., None] + band_col * fog[..., None]
        moon_side = sstep(0.70, 0.98, -sd)
        tear_side = sstep(0.74, 0.98, sd if root_az < tear_az else -sd)
        prox = math.exp(-abs(root_az - tear_az) / 22.0)
        col = col + S('#A9C2FF') * (rim * moon_side * (1 - fog * 0.8))[..., None]
        col = col + S('#A99DE1') * (0.55 * prox * tear_side * (1 - fog * 0.8))[..., None]
        streak = np.clip(gaussian_filter(rng.standard_normal((H, W)), (3.0, 0.7)) * 2.2 - 1.3, 0, 1)
        col = col + S('#5E6F94') * (0.45 * streak * sstep(-0.1, -0.75, sd) * (1 - fog))[..., None]
        return dist, cov, col
    L_ = []
    L_.append(arm(38.0, 1840, 440, -3.5, -30, 32, curl=14))                     # colossus 1 (behind Rilke earlier)
    L_.append(arm(-14.5, 1720, 470, 2.2, 26, 34, curl=-10, fog_cap=0.55))       # colossus 2 (ate the moon)
    L_.append(arm(15.0, 1050, 450, -12.5, -70, 32, curl=18, fog_cap=0.45))         # colossus 3 (reaching over the right lip)
    for i in range(7):
        a = rng.choice([-1, 1]) * rng.uniform(18, 50)
        L_.append(arm(a, rng.uniform(2400, 4000), rng.uniform(320, 450), -a * 0.12, rng.uniform(-30, 30), 30,
                      curl=rng.uniform(-12, 12), fog_cap=0.6))
    for i in range(18):
        a = rng.normal(0, 13)
        if abs(a) < 3.5: a = 3.5 * np.sign(a + 1e-3)
        d = rng.uniform(1100, 2100); hgt = rng.uniform(110, 250)
        L_.append(arm(a, d, hgt, -a * rng.uniform(0.12, 0.40), rng.uniform(-18, 18), hgt / 20.0,
                      curl=rng.uniform(-10, 10), rim=0.8, fog_cap=0.9))
    for dist, cov, col in sorted(L_, key=lambda l: -l[0]):
        img = img * (1 - cov[..., None]) + col * cov[..., None]
    # --- near arm, co-moving (12 m, lower left): inky, wet streaks, razor rim
    pts = curve((-60, H + 80), (W * 0.31, H * 0.33), 90, n=70, curl=30)
    tt = np.linspace(0, 1, 70)
    cov, sd, t = stroke(pts, 60 * (1 - tt) ** 0.85 + 0.4)
    across = np.sqrt(np.clip(1 - sd ** 2, 0, 1))
    body = S('#0F1116') * (0.7 + 0.6 * across)[..., None]
    streak = np.clip(gaussian_filter(rng.standard_normal((H, W)), (6.0, 1.0)) * 2.6 - 1.45, 0, 1)
    body = body + S('#8FA4CC') * (0.5 * streak * sstep(-0.05, -0.85, sd))[..., None]
    body = body + S('#A9C2FF') * (1.2 * sstep(0.88, 0.99, -sd))[..., None] + S('#A99DE1') * (0.55 * sstep(0.9, 0.99, sd))[..., None]
    img = img * (1 - cov[..., None]) + body * cov[..., None]
    # --- cabin: windscreen header (a straight edge at +18 deg), right A-pillar (+27..+31 deg), dash (< -15 deg)
    _, yh = px(0, 18.0, pitch); _, yd = px(0, -15.0, pitch)
    hdr = yy < yh - (xx - W / 2) * 0.012
    img = np.where(hdr[..., None], S('#16181E') * (1 + 0.3 * sstep(yh, 0, yy))[..., None], img)
    xp0, _ = px(27, 0, pitch); xp1, _ = px(31, 0, pitch)
    pil = (xx > xp0 + (yy - H / 2) * 0.10) & (xx < xp1 + (yy - H / 2) * 0.10)
    img = np.where(pil[..., None], S('#101216'), img)
    dash = yy > yd + ((xx - W / 2) / W) ** 2 * 30
    img = np.where(dash[..., None], S('#0E1013'), img)
    return img

# ------------------------------------------------------------------ 4c inside the tear: dark grace, irregular lips, the dye thins
def _cabin_frame(img, S, pitch, col='#0C0E14', dial=None):
    _, yh = px(0, 17.5, pitch); _, yd = px(0, -13.0, pitch)
    img = np.where((yy < yh - (xx - W / 2) * 0.012)[..., None], S(col), img)
    xp0, _ = px(27, 0, pitch); xp1, _ = px(31, 0, pitch)
    img = np.where(((xx > xp0 + (yy - H / 2) * 0.10) & (xx < xp1 + (yy - H / 2) * 0.10))[..., None], S(col), img)
    img = np.where((yy > yd + ((xx - W / 2) / W) ** 2 * 30)[..., None], S(col), img)
    if dial:
        dx, dy = px(-20, -15.5, pitch)
        img = np.where(((np.abs(xx - dx) < 20) & (np.abs(yy - dy) < 5))[..., None], S(dial), img)
        img += S(dial) * 0.10 * np.exp(-(((xx - dx) / 34) ** 2 + ((yy - dy) / 14) ** 2))[..., None]
    return img

def tear_inside(prof='S4c'):
    """frame at lip 5 of 8 (between U10 and U11): three lips visible through each other, offset and rotated, never concentric."""
    pitch = 1.0
    az, el = cam(pitch)
    S = lambda h: SL(h, prof)
    vfib = gaussian_filter(rng.standard_normal((H, W)), (12, 0.6))
    wall = S('#1A2030') * (1 + 0.18 * np.clip(vfib * 3, -1, 1))[..., None]        # the inner face of the torn indigo cloth
    img = wall.copy()
    # (centre az, centre el, half-height, half-width, rotation, fibre colour, mist seen THROUGH it, kind)
    lips = [(-6.0, 3.0, 27.0, 13.0, -24, '#D9DFEE', '#2E3647', 'rip'),
            (6.5, 1.0, 13.0, 6.0, 17, '#CDDBE8', '#3F4A5A', 'fork'),
            (4.4, 3.0, 7.5, 1.7, 34, '#C2D8E2', '#53606E', 'rip')]
    opening = np.ones((H, W), bool)
    for (ca, ce, hh, hw, rot, fcol, mist, kind) in lips:
        r = math.radians(rot)
        xr = (az - ca) * math.cos(r) + (el - ce) * math.sin(r)
        yr = -(az - ca) * math.sin(r) + (el - ce) * math.cos(r)
        s = yr / hh
        fray = gaussian_filter(rng.standard_normal((H, W)), (4, 0.7)) * 0.20 + gaussian_filter(rng.standard_normal((H, W)), (1, 0.4)) * 0.10
        if kind == 'hole':   # a ragged hole: low-frequency lobes, not an ellipse
            fray = fray + np.clip(gaussian_filter(rng.standard_normal((H, W)), 9) * 9, -0.5, 0.6)
        prof_ = np.clip(1 - s ** 2, 0, 1) ** (0.8 if kind != 'hole' else 0.45)
        asym = np.where(xr < 0, 0.85, 1.15)
        half = hw * prof_ * asym * (1 + fray)
        ins = (np.abs(xr) < half) & (np.abs(s) < 1)
        if kind == 'fork':   # a second tongue splitting off the upper end
            xr2 = xr - 0.8 * hw * np.clip(s - 0.15, 0, 1) * 2.4
            ins |= (np.abs(xr2) < hw * 0.55 * np.clip(1 - ((s - 0.6) / 0.4) ** 2, 0, 1) * (1 + fray)) & (s > 0.2) & (s < 1)
        ins &= opening
        # through the opening: the next, thinner mist, brighter toward its centre (depth)
        m = S(mist) * (0.85 + 0.25 * np.exp(-((xr / (hw + 1e-3)) ** 2 + s ** 2) * 1.5))[..., None]
        m = m * (1 + 0.10 * np.clip(vfib * 3, -1, 1))[..., None]
        img = np.where(ins[..., None], m, img)
        # the lip: a band of backlit fibres along the torn edge (outside face dark, the edge line bright)
        dedge = np.abs(np.abs(xr) - half)
        band = np.exp(-(dedge / 0.35) ** 2) * (np.abs(s) < 1) * opening
        strands = 0.45 + 0.55 * np.clip(gaussian_filter(rng.standard_normal((H, W)), (3, 0.3)) * 3 + 0.4, 0, 1)
        img += S(fcol) * (0.75 * band * strands)[..., None]
        halo_ = np.exp(-(dedge / 1.4) ** 2) * (np.abs(s) < 1) * opening
        img += S(fcol) * (0.06 * halo_)[..., None]
        for _ in range(40):   # threads hanging off the edge into the opening
            ss = rng.uniform(-0.85, 0.85); side = rng.choice([-1, 1])
            hx = float(hw * max(1 - ss ** 2, 0) ** 0.8 * (0.85 if side < 0 else 1.15)) * side
            ax_ = ca + hx * math.cos(r) - ss * hh * math.sin(r); ay_ = ce + hx * math.sin(r) + ss * hh * math.cos(r)
            x0, y0 = px(ax_, ay_, pitch)
            L = rng.uniform(4, 16) * hh / 27
            pts = curve((x0, y0), (x0 - side * rng.uniform(1, 4), y0 + L), rng.uniform(-2, 2), n=8)
            cov, _, _ = stroke(pts, np.linspace(0.5, 0.2, 8))
            img = img * (1 - cov[..., None] * 0.7) + S(fcol) * 0.6 * cov[..., None] * opening[..., None]
        opening = ins
    # the warm point ahead, inside the innermost opening (U10-U11: 0.3 deg core, 4 deg glow)
    wx, wy = px(5.6, 1.6, pitch)
    rr = np.hypot(xx - wx, yy - wy) / F * 57.3
    img += S('#FFF1DC') * (2.2 * np.exp(-(rr / 0.16) ** 2) + 0.10 * np.exp(-(rr / 2.0) ** 2))[..., None]
    for _ in range(14):   # a few loose threads drifting toward the centre
        tx, ty = rng.uniform(0, W), rng.uniform(H * 0.1, H * 0.7)
        pts = curve((tx, ty), (tx + (W / 2 - tx) * 0.03, ty + rng.uniform(10, 22)), 1.0, n=6)
        cov, _, _ = stroke(pts, np.full(6, 0.3))
        img += S('#D9DFEE') * 0.18 * cov[..., None]
    return _cabin_frame(img, S, pitch, dial='#F2B169')

# ------------------------------------------------------------------ 7a under the surface (ultramarine ladder)
def undersea(prof='S7a'):
    pitch = 30.0
    az, el = cam(pitch)
    S = lambda h: SL(h, prof)
    # water column: bright shallow blue up, the ladder down
    t = sstep(-20, 40, el)
    img = np.exp(np.log(S('#1A4163')) * (1 - t)[..., None] + np.log(S('#507DA6')) * t[..., None])
    # Snell's window: 48.6 deg half-angle cone around the zenith; frame shows its lower rim
    zen = 90 - el
    ripple = 1 + 0.035 * np.sin(az * 0.9 + np.sin(el * 0.6) * 2) * np.sin(el * 0.8)
    win = 1 - sstep(46.5, 48.6, zen * ripple)
    tir = sstep(48.6, 50.5, zen * ripple) * sstep(-5, 25, el)
    sky = np.exp(np.log(S('#94CAE9')) * sstep(30, 47, zen)[..., None] + np.log(S('#E6F3F8')) * (1 - sstep(30, 47, zen))[..., None])
    img = img * (1 - win[..., None]) + sky * win[..., None]
    img = img * (1 - tir[..., None] * 0.7) + S('#11395E') * (tir * 0.7)[..., None]
    img += S('#ACD4ED') * 0.35 * np.exp(-((zen - 48.6) / 0.6) ** 2)[..., None]             # chromatic rim
    # god rays leaning with the refracted sun
    for k in range(11):
        a0 = rng.uniform(-40, 40)
        ray = np.exp(-((az - (a0 + (el - 30) * 0.35)) / rng.uniform(0.5, 1.6)) ** 2) * sstep(-18, 30, el) * (1 - win)
        img += S('#90BFE9') * 0.16 * ray[..., None]
    for _ in range(420):  # marine snow
        sx, sy = rng.uniform(0, W), rng.uniform(0, H)
        img += S('#697987') * rng.uniform(0.4, 1.0) * np.exp(-(((xx - sx) / 0.9) ** 2 + ((yy - sy) / 1.6) ** 2))[..., None]
    for _ in range(14):   # bioluminescent sparks (F4)
        sx, sy = rng.uniform(0, W), rng.uniform(H * 0.5, H)
        img += S('#8AC6FF') * 1.6 * np.exp(-(((xx - sx) / 0.9) ** 2 + ((yy - sy) / 0.9) ** 2))[..., None]
    # cabin: windscreen header edge just entering the top-left (the roof is still there at F3; erosion starts at the hatch)
    _, yh = px(0, 18.0, pitch)
    return img

# ------------------------------------------------------------------ 7b the palace: cinnabar + indigo, two rows of lamps converging
def deep(prof='S7b'):
    pitch = -8.0
    az, el = cam(pitch)
    S = lambda h: SL(h, prof)
    t = sstep(-30, 20, el)
    img = np.exp(np.log(S('#02070F')) * (1 - t)[..., None] + np.log(S('#061A30')) * t[..., None])
    img = img * (1 + 0.10 * gaussian_filter(rng.standard_normal((H, W)), 20)[..., None])
    hz = -6.0
    # processional axis: two rows of 12 lamps, 18 m pitch, converging to the hall door (flames _FogMode 2, _Atten 0.004)
    for side in (-1, 1):
        for i in range(12):
            dist = 14 + 18 * i
            a = math.degrees(math.atan(side * 9.0 / dist)); e = math.degrees(math.atan(-4.0 / dist)) - 1
            x, y = px(a, e, pitch)
            fall = math.exp(-0.004 * dist)
            sz = max(1.1, 5.5 * 14 / dist)
            img += S('#FFC46A') * 1.2 * fall * np.exp(-(((xx - x) / (sz * 0.55)) ** 2 + ((yy - y) / sz) ** 2))[..., None]
            img += S('#2A557B') * 0.35 * fall * np.exp(-(((xx - x) / (sz * 7)) ** 2 + ((yy - y) / (sz * 6)) ** 2))[..., None]
            img += S('#FFC46A') * 0.15 * fall * np.exp(-(((xx - x) / (sz * 2.2)) ** 2 + ((yy - y) / (sz * 2.2)) ** 2))[..., None]
    # the hall at the end of the axis (60 m wide, 30 m tall on a 6 m terrace, 230 m away): heavy straight Han roof
    dist = 230.0
    hw = math.degrees(math.atan(30 / dist)); top = math.degrees(math.atan(26 / dist)); bot = math.degrees(math.atan(-10 / dist))
    hall = (np.abs(az) < hw) & (el > bot) & (el < top)
    img = np.where(hall[..., None], S('#040A12'), img)
    roof = (el > top - 1.2) & (el < top + 2.2) & (np.abs(az) < hw * 1.35 - (el - (top - 1.2)) * 2.0)
    img = np.where(roof[..., None], S('#03070C'), img)
    door = (np.abs(az) < 1.2) & (el > bot) & (el < bot + 3.2)
    img = np.where(door[..., None], S('#FFC46A') * 0.7, img)
    img += S('#FFC46A') * 0.25 * np.exp(-((az / 2.0) ** 2 + ((el - bot - 0.2) / 0.5) ** 2))[..., None]
    for cx in (-1.8, 1.8):   # vermilion columns at the door, lit by its glow
        col = (np.abs(az - cx) < 0.25) & (el > bot) & (el < bot + 3.6)
        img = np.where(col[..., None], S('#B52A1E'), img)
    # cowrie gate towers (small, lit only near their lamps)
    for gx in (-7.5, 7.5):
        tw = (np.abs(az - gx) < 0.9) & (el > bot) & (el < top + 1.0)
        img = np.where(tw[..., None], S('#04080E'), img)
        img += S('#7A4A6E') * 0.5 * (tw * np.exp(-((el - bot - 1.0) / 1.2) ** 2))[..., None]
    # the terrace and the paving between the rows: indigo falloff of the lamps, cinnabar only near flames
    ground = el < hz - 2 + 0 * az
    g = S('#050B12') + S('#26496C') * 0.25 * np.exp(-(az / 25) ** 2)[..., None]
    img = np.where(ground[..., None] & ~hall[..., None], g * (1 + 0.3 * gaussian_filter(rng.standard_normal((H, W)), 2)[..., None]), img)
    # silver fish ring (catching lamp light), nacre glints on the fish-scale roofs
    for _ in range(140):   # the silver fish ring (radius 35 m around the hall), flashing where it passes the lamps
        th = rng.uniform(0, 2 * math.pi); rad_ = 35 + rng.normal(0, 3)
        fx_, fz_ = rad_ * math.cos(th), 230 + rad_ * math.sin(th); fy_ = rng.uniform(4, 22)
        a = math.degrees(math.atan2(fx_, fz_)); e = math.degrees(math.atan2(fy_ - 10, fz_))
        x, y = px(a, e, pitch)
        img += S('#D8CFE0') * rng.uniform(0.05, 0.5) * np.exp(-(((xx - x) / 1.0) ** 2 + ((yy - y) / 0.5) ** 2))[..., None]
    for _ in range(22):
        sx, sy = rng.uniform(0, W), rng.uniform(0, H)
        img += S('#8AC6FF') * rng.uniform(0.2, 0.6) * np.exp(-(((xx - sx) / 0.8) ** 2 + ((yy - sy) / 0.8) ** 2))[..., None]
    return img

# ------------------------------------------------------------------ 6 / 8: v1 mock frames hue-mapped to the v2 cloud-card targets
def _lch_remap(disp, lo, hi, target, cscale, feather=28):
    Wn = np.array([0.95047, 1, 1.08883])
    M = np.array([[0.4124, 0.3576, 0.1805], [0.2126, 0.7152, 0.0722], [0.0193, 0.1192, 0.9505]]); Mi = np.linalg.inv(M)
    f = lambda t: np.where(t > 0.008856, np.cbrt(t), 7.787 * t + 16 / 116)
    fi = lambda t: np.where(t > 0.2069, t ** 3, (t - 16 / 116) / 7.787)
    X = ppv2.srgb_to_lin(disp) @ M.T / Wn
    fx, fy, fz = f(X[..., 0]), f(X[..., 1]), f(X[..., 2])
    L = 116 * fy - 16; A = 500 * (fx - fy); B = 200 * (fy - fz)
    C = np.hypot(A, B); Hh = np.degrees(np.arctan2(B, A)) % 360
    w = np.clip(np.minimum(Hh - (lo - feather), (hi + feather) - Hh) / feather, 0, 1)
    Hn = Hh + w * (target - Hh); Cn = C * (1 - w * (1 - cscale))
    A = Cn * np.cos(np.radians(Hn)); B = Cn * np.sin(np.radians(Hn)); fy = (L + 16) / 116
    Xn = np.stack([fi(fy + A / 500), fi(fy), fi(fy - B / 200)], -1) * Wn
    return np.clip(ppv2.lin_to_srgb(Xn @ Mi.T), 0, 1)

def remapped_mock(frame, maps):
    """scene-linear mock -> neutral display -> Lab hue remap (v1 card hues -> v2 targets) -> back to scene-linear."""
    disp = ppv2.render(frame, {}, with_bloom=False)
    for lo, hi, t, cs in maps:
        disp = _lch_remap(disp, lo, hi, t, cs)
    lin = ppv2.srgb_to_lin(disp)
    inv = ppv2.neutral_inverse(np.minimum(lin, 0.9995))
    return np.where(frame.max(-1, keepdims=True) > 4.5, frame, inv)

# ------------------------------------------------------------------ 9a / 9b the star sea
def _stars(seed, density, h=H, w=W):
    r = np.random.default_rng(seed)
    img = np.zeros((h, w, 3))
    n = int(h * w * density)
    ys = r.integers(0, h, n); xs = r.integers(0, w, n)
    mag = r.pareto(2.0, n) * 0.10 + 0.03
    tint = r.choice([[1, 1, 1], [0.8, 0.88, 1.0], [1.0, 0.9, 0.75], [0.75, 0.85, 1.0]], n)
    img[ys, xs] += tint * mag[:, None]
    return gaussian_filter(img, (0.55, 0.55, 0)), ys, xs, mag

def pxv(az, el, pitch):
    a, e, p = np.radians(az), np.radians(el), math.radians(pitch)
    d = np.stack([np.cos(e) * np.sin(a), np.cos(e) * np.cos(a), np.sin(e)], -1)
    R = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])
    c = d @ R.T
    return W / 2 - 0.5 + F * c[..., 0] / c[..., 1], H / 2 - 0.5 - F * c[..., 2] / c[..., 1]

# stroke counts of 遂古之初谁传道之上下未形何由考之 (simplified forms) -> star brightness
TIANWEN_STROKES = [12, 5, 3, 7, 10, 6, 12, 3, 3, 3, 5, 7, 7, 5, 6, 3]

def starsea(prof='S9a', climax=False):
    pitch = 6.0
    az, el = cam(pitch)
    S = lambda h: SL(h, prof)
    base = S('#08112A')
    img = np.broadcast_to(base, (H, W, 3)).copy()
    # the Milky Way ring: core at az -30 el +12, arching up and over; it continues below the horizon (full ring, not a reflection)
    ca, sa = math.cos(math.radians(35)), math.sin(math.radians(35))
    t = (az + 30) * ca + (el - 12) * sa
    n_ = -(az + 30) * sa + (el - 12) * ca
    band = np.exp(-(n_ / 5.0) ** 2) + 0.30 * np.exp(-(n_ / 12.0) ** 2)
    fld = gaussian_filter(np.random.default_rng(8).standard_normal((512, 512)), 2.0)
    fld /= fld.std()
    def along(ks, kn, off=0.0):   # noise stretched along the band (t) and tight across it (n_)
        return map_coordinates(fld, [(n_ * kn + 256 + off) % 512, (t * ks + 256) % 512], order=1, mode='wrap')
    lane = np.exp(-((n_ + 0.6 + 1.2 * along(0.8, 0.3)) / 0.9) ** 2) * np.clip(0.55 + 0.45 * along(1.5, 1.0, 97), 0, 1)
    lane += 0.5 * np.exp(-((n_ - 2.2 + 1.5 * along(0.6, 0.3, 33)) / 0.6) ** 2) * np.clip(along(2.0, 1.2, 55), 0, 1)
    fine = np.clip(1 + 0.35 * along(1.2, 0.8, 11) + 0.25 * along(3.0, 2.0, 71), 0.45, 1.6)
    core = np.exp(-((az + 30) / 10) ** 2 - ((el - 12) / 6) ** 2)
    gain_mw = 1.8 if climax else 1.0
    mw = (band * fine * (1 - 0.85 * np.clip(lane, 0, 1)))[..., None] * (S('#6F82A0') - base).clip(0) * 0.6 * gain_mw
    mw += (core * band * fine * (1 - 0.9 * np.clip(lane, 0, 1)))[..., None] * (S('#C8B79A') - base).clip(0) * 0.8 * gain_mw
    img += mw
    # stars: denser in the band; the sky below the horizon is different stars (space, not a mirror)
    r = np.random.default_rng(21)
    dens = 0.0016 + 0.006 * np.clip(band, 0, 1) * (1 - 0.7 * np.clip(lane, 0, 1))
    k = r.random((H, W)) < dens
    mag = np.zeros((H, W)); mag[k] = r.pareto(2.1, k.sum()) * 0.10 + 0.025
    st = gaussian_filter(mag, 0.55)
    tint = np.stack([np.ones((H, W)), 0.9 + 0.1 * r.random((H, W)), 0.8 + 0.25 * r.random((H, W))], -1)
    star_gain = 8.0 if climax else 4.0
    img += (st[..., None] * tint) * (1.0 + (star_gain - 1) * (st > 0.05))[..., None] * S('#F2F6FF') / S('#F2F6FF').max()
    if climax:
        # 16 stars where the question stood (az 0, el +8; two lines of 8 with the comma gap), brightness ~ stroke count
        jit = np.random.default_rng(5)
        for i, nst in enumerate(TIANWEN_STROKES):
            col = i % 8; row = i // 8
            a_ = -8.0 + col * 2.2 + (0.9 if col >= 4 else 0) + jit.uniform(-0.3, 0.3)
            e_ = 9.3 - row * 2.7 + jit.uniform(-0.3, 0.3)
            cx, cy = px(a_, e_, pitch)
            img += S('#F2F6FF') * (0.8 + 0.3 * nst) * np.exp(-(((xx - cx) / 0.8) ** 2 + ((yy - cy) / 0.8) ** 2))[..., None]
        # mirror 12, face up, rising under the bus: its far rim sits at el -2.2; the face reflects the sky in white bronze
        rim_el = -2.2
        face = el < rim_el
        sx, sy = pxv(az, -el, pitch)
        refl = np.stack([map_coordinates(img[..., c], [np.clip(sy, 0, H - 1), np.clip(sx, 0, W - 1)], order=1, mode='nearest') for c in range(3)], -1)
        k12 = 12
        bronze = np.array([0.93, 0.86, 0.70])
        img = np.where(face[..., None], refl * bronze * (1 + (0.2 + 0.08 * k12)), img)
        _, ly = px(0, rim_el, pitch)
        rimline = np.exp(-((yy - ly) / 1.1) ** 2)
        img += S('#CDBF9C') * (0.9 * rimline)[..., None]
        boss = (np.sin(xx * 1.1) > 0.9) * np.exp(-((yy - ly + 1.8) / 0.8) ** 2)       # rim bosses at a constant 1.5 m pitch
        img += S('#CDBF9C') * (0.7 * boss)[..., None]
        # the dust of mirror 11 still rising above (#CDBF9C -> #F2F6FF), <= 250 sprites per mirror
        for _ in range(250):
            dx, dy = rng.uniform(0, W), rng.uniform(H * 0.15, ly - 6)
            c = S('#CDBF9C') if rng.random() < 0.55 else S('#F2F6FF')
            img += c * rng.uniform(0.25, 1.0) * np.exp(-(((xx - dx) / 0.7) ** 2 + ((yy - dy) / 0.7) ** 2))[..., None]
    return img
