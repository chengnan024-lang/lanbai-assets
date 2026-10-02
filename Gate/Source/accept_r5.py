"""Round 4 (refine round 3): the acceptance numbers both r3 critiques asked for, measured on the shipped PNGs and
their ID passes (critique_awe_r3 §5, critique_tech_r3 §2 / m9).

    python3 accept_r5.py [final_dir] [out.json]        (default: final/ -> final/acceptance_r5.json)

Also imported by compare_r3.py (the before / after sheets).  Pure numpy on the 8-bit display PNGs (sRGB -> CIELAB D65).
Definitions (all distances in px are scaled by W / 2560 so the key and the 1920 frames are comparable):
  tear      white = tear-ID pixels with L* > 75. Per row: the white's extent [x0, x1], centre c; axis L* = median L* of
            the white within 12 % of the width round c.  Central 80 % of the visible rows: range (max - min of the
            axis profile, smoothed 1 % of the span), hot row (centroid of rows within 1 L* of the max), widest row;
            offset = (hot - widest) / span.  b*: lips = white 1-5 px inside its sky edge; tip = top 12 % of rows;
            hot = white within 3 % of the span round (hot row, c).
  lip glow  pixels 6 px outside the white (not on arms): sd L*, median C*; dark segments per lip = runs >= 3 px
            (scaled) where the 6-px-outside L* falls 10 below its 41-row running median.
  arms      cross-sections = ID pixels in a narrow band of the arc fraction t (orientation-free): per band
            p95 - p5 of L*; tear-side flank = the quarter of each band nearest the white's centroid.
  sea       deck pixels at az -45 .. -4 (moonward of the wound): p5 / p95 L*, local sd (31 px), moon path = median L*
            within 3 deg of the moon azimuth minus 8-15 deg away.
  multitude Mult_* IDs: members with a visible height >= 30 px; area; lean = crown (t > 0.6) leans from the root
            (t < 0.25) toward the wound's x.
  m9        'never brighter than the sky' with SAME-ROW sky samples 6-40 px either side (tech m9).
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter1d, median_filter, uniform_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tear', 'v2'))
from metrics import lab  # noqa: E402
import gate_layout as G  # noqa: E402
from gate_plan import Cam  # noqa: E402
from gate_scene_shots import SHOTS  # noqa: E402


def r1(x, n=1):
    return None if x is None or (isinstance(x, float) and not np.isfinite(x)) else round(float(x), n)


def load(png, idnpy=None, shot=None):
    im = np.asarray(Image.open(png).convert('RGB')).astype(float)
    H, W = im.shape[:2]
    L, a, b = lab(im)
    d = dict(L=L, a=a, b=b, C=np.hypot(a, b), luma=im @ np.array([0.2126, 0.7152, 0.0722]), H=H, W=W, s=W / 2560.0)
    if idnpy and os.path.exists(idnpy):
        ids = np.load(idnpy).astype(np.float32)
        table = {int(k): v for k, v in json.load(open(idnpy.replace('_id.npy', '_idmap.json'))).items()}
        inst = np.round(ids[..., 0] * 128).astype(int)
        other = ids[..., 2]
        d.update(inst=inst, t=ids[..., 1], other=other, table=table,
                 tear=(inst == 0) & (np.abs(other - 0.25) < 0.05), deck=(inst == 0) & (np.abs(other - 0.5) < 0.05),
                 shell=(inst == 0) & (other > 0.9), sky=(inst == 0) & (other < 0.1))
    if shot:
        sh = SHOTS[shot]
        cam = Cam(G.eye_cf(sh['t'], sh['eye']), sh['yaw'], sh['pitch'], sh['hfov'], W, H)
        D = cam.rays()
        az, el = G.azel_of(D)
        d.update(D=D, az=az, el=el)
    return d


def px(d, n):
    return max(1, int(round(n * d['s'])))


# ------------------------------------------------------------------------------------------------------------ tear
def tear_white(d):
    if 'tear' in d:
        return d['tear'] & (d['L'] > 75)
    # no ID pass: the TALLEST connected component of L* > 75 (as with IDs; not the moon, not lit shell edges)
    from scipy.ndimage import label, find_objects
    lab_, n = label(binary_dilation(d['L'] > 75, iterations=2))
    if n == 0:
        return d['L'] > 75
    sl = find_objects(lab_)
    k = int(np.argmax([s_[0].stop - s_[0].start for s_ in sl])) + 1
    return (lab_ == k) & (d['L'] > 75)


def tear_metrics(d):
    L, b, C = d['L'], d['b'], d['C']
    wh = tear_white(d)
    H, W = wh.shape
    rows = np.where(wh.sum(1) >= 3)[0]
    if len(rows) < 20:
        return None
    r_top, r_bot = rows.min(), rows.max()
    span = float(r_bot - r_top)
    prof = np.full(H, np.nan)
    width = np.zeros(H)
    cen = np.full(H, np.nan)
    x0s = np.full(H, -1)
    x1s = np.full(H, -1)
    for r in rows:
        xs = np.where(wh[r])[0]
        x0, x1 = xs.min(), xs.max()
        w = x1 - x0 + 1
        c = 0.5 * (x0 + x1)
        k = max(1, int(0.12 * w))
        sel = xs[np.abs(xs - c) <= k]
        if len(sel) == 0:
            continue
        prof[r] = np.median(L[r, sel])
        width[r] = w
        cen[r] = c
        x0s[r], x1s[r] = x0, x1
    lo, hi = int(r_top + 0.1 * span), int(r_bot - 0.1 * span)
    rr = np.arange(lo, hi + 1)
    p = prof[rr]
    ok = np.isfinite(p)
    if ok.sum() < 10:
        return None
    p = np.interp(rr, rr[ok], p[ok])
    ps = gaussian_filter1d(p, max(1.0, 0.01 * span))
    ws = gaussian_filter1d(width[rr], max(1.0, 0.02 * span))
    hot = float(np.mean(rr[ps >= ps.max() - 1.0]))
    widest = float(rr[np.argmax(ws)])
    o = dict(visible_rows=int(span), axis_L_range_central80=r1(ps.max() - ps.min()), axis_L_max=r1(ps.max()),
             axis_L_min=r1(ps.min()), axis_L_at_tip_end=r1(ps[0]), axis_L_at_foot_end=r1(ps[-1]),
             hot_row_minus_widest_row_pct_of_span=r1((hot - widest) / span * 100.0))
    # b*: lips (white 1-5 px inside its sky edge, away from arms), tip rows, hot spot
    arms = binary_dilation(d['inst'] > 0, iterations=px(d, 4)) if 'inst' in d else np.zeros_like(wh)
    lipz = binary_erosion(wh, iterations=1) & ~binary_erosion(wh, iterations=px(d, 5)) & ~arms
    tipz = wh & (np.arange(H)[:, None] < r_top + 0.12 * span)
    yy, xx = np.mgrid[0:H, 0:W]
    hc = cen[int(round(hot))] if np.isfinite(cen[int(round(hot))]) else np.nanmedian(cen)
    hotz = wh & (np.hypot(yy - hot, xx - hc) < 0.03 * span)
    o['b_lips'] = r1(np.median(b[lipz])) if lipz.sum() > 20 else None
    o['b_tip'] = r1(np.median(b[tipz])) if tipz.sum() > 20 else None
    o['b_hot'] = r1(np.median(b[hotz])) if hotz.sum() > 5 else None
    # lip glow 6 px outside the white
    n = px(d, 6)
    ring = binary_dilation(wh, iterations=n) & ~binary_dilation(wh, iterations=n - 1) & ~arms
    if 'tear' in d:
        ring &= ~(d['tear'] & (L > 75))
    o['lipglow_6px_sd_L'] = r1(np.std(L[ring])) if ring.sum() > 50 else None
    o['lipglow_6px_median_C'] = r1(np.median(C[ring])) if ring.sum() > 50 else None
    o['lipglow_6px_median_L'] = r1(np.median(L[ring])) if ring.sum() > 50 else None
    # dark segments along each lip
    segs = {}
    for side, xe in (('left', x0s), ('right', x1s)):
        vals = np.full(len(rr), np.nan)
        for i, r in enumerate(rr):
            if xe[r] < 0:
                continue
            x = int(xe[r] - n) if side == 'left' else int(xe[r] + n)
            if 0 <= x < W and not arms[r, x]:
                vals[i] = L[r, x]
        okv = np.isfinite(vals)
        if okv.sum() < 20:
            segs[side] = None
            continue
        v = np.interp(np.arange(len(rr)), np.where(okv)[0], vals[okv])
        base = median_filter(v, size=41, mode='nearest')
        dark = (v < base - 10.0) & okv
        cnt, run = 0, 0
        for x_ in dark:
            run = run + 1 if x_ else 0
            if run == px(d, 3):
                cnt += 1
        segs[side] = cnt
    o['dark_segments_per_lip'] = segs
    o['white_centroid_x_pct'] = r1(np.mean(np.where(wh)[1]) / W * 100)
    return o


# ------------------------------------------------------------------------------------------------------------ arms
def arm_metrics(d, which=('hand', 'engel')):
    if 'inst' not in d:
        return None
    L = d['L']
    wh = tear_white(d)
    if wh.sum() < 10:
        return None
    ty, tx = np.mean(np.where(wh), axis=1)
    out = {}
    for k, v in d['table'].items():
        if v.get('role') not in which:
            continue
        m = d['inst'] == k
        if m.sum() < 200:
            continue
        tv = d['t'][m]
        ys, xs = np.where(m)
        Lm = L[m]
        rng, flank, nb = [], [], 0
        for tb in np.linspace(0.06, 0.96, 60):
            s = np.abs(tv - tb) < 0.005
            if s.sum() < px(d, 8):
                continue
            nb += 1
            vals = Lm[s]
            rng.append(np.percentile(vals, 95) - np.percentile(vals, 5))
            dd = np.hypot(ys[s] - ty, xs[s] - tx)
            near = dd <= np.percentile(dd, 25)
            flank.append(np.median(vals[near]))
        if nb < 3:
            continue
        out[v['id']] = dict(sections=nb, cross_section_range_L_median=r1(np.median(rng)),
                            cross_section_range_L_p25=r1(np.percentile(rng, 25)),
                            tear_side_flank_L_median=r1(np.median(flank)), body_L_median=r1(np.median(Lm)),
                            pixels=int(m.sum()))
    return out


def same_row_contrast(d, roles=('engel', 'background', 'colossus', 'moon', 'rilke', 'pillar')):
    """tech m9: arm vs sky 6-40 px away IN THE SAME ROW, per instance (median over rows), sky pixels only."""
    if 'inst' not in d:
        return None
    L, sky = d['L'], d['sky']
    a, bb = px(d, 6), px(d, 40)
    out = {}
    for k, v in d['table'].items():
        if v.get('role') not in roles and v.get('layer') not in ('colossus', 'colossus_bg'):
            continue
        m = d['inst'] == k
        if m.sum() < 200:
            continue
        diffs = []
        for r in np.unique(np.where(m)[0])[::2]:
            xs = np.where(m[r])[0]
            arm = np.median(L[r, xs])
            cand = []
            for x in (np.arange(xs.min() - bb, xs.min() - a), np.arange(xs.max() + a, xs.max() + bb)):
                x = x[(x >= 0) & (x < d['W'])]
                x = x[sky[r, x]]
                cand.extend(L[r, x].tolist())
            if len(cand) >= 4:
                diffs.append(arm - np.median(cand))
        if len(diffs) >= 5:
            out[v['id']] = dict(dL_same_row_median=r1(np.median(diffs)), rows=len(diffs),
                                brighter_rows_pct=r1(np.mean(np.array(diffs) > 0) * 100))
    return out


# ------------------------------------------------------------------------------------------------------- multitude
def multitude_metrics(d):
    if 'inst' not in d:
        return None
    wh = tear_white(d)
    tx = np.mean(np.where(wh)[1]) if wh.sum() else d['W'] / 2
    N = float(d['H'] * d['W'])
    n_vis = n30 = n_lean = n_lean_tested = 0
    area = 0
    for k, v in d['table'].items():
        if not v['id'].startswith('Mult_'):
            continue
        m = d['inst'] == k
        if m.sum() == 0:
            continue
        n_vis += 1
        area += m.sum()
        ys, xs = np.where(m)
        if ys.max() - ys.min() + 1 >= 30:
            n30 += 1
        tv = d['t'][m]
        cr, rt = tv > 0.6, tv < 0.25
        if cr.sum() > 5 and rt.sum() > 5:
            n_lean_tested += 1
            rx, cx = xs[rt].mean(), xs[cr].mean()
            if np.sign(cx - rx) == np.sign(tx - rx) or abs(cx - tx) < abs(rx - tx):
                n_lean += 1
    return dict(members_visible=n_vis, members_ge30px_tall=n30, area_pct=r1(area / N * 100, 2),
                lean_toward_wound=f'{n_lean}/{n_lean_tested}')


# ------------------------------------------------------------------------------------------------------- grade
def tone_metrics(d):
    L, luma, H = d['L'], d['luma'], d['H']
    o = dict(APL=r1(luma.mean()), luma_lt12_pct=r1((luma < 12).mean() * 100))
    if 'shell' in d and d['shell'].any():
        o['APL_through_glass'] = r1(luma[~d['shell']].mean())
    top = L[: int(0.18 * H)]
    if 'sky' in d:
        o['top18_sky_L_p90'] = r1(np.percentile(top[d['sky'][: int(0.18 * H)]], 90)) if d['sky'][: int(0.18 * H)].sum() > 100 else None
    o['top18_all_L_p90'] = r1(np.percentile(top, 90))
    if 'az' in d and 'sky' in d:
        az, el = d['az'], d['el']
        bins = []
        for a0 in range(3, 45, 5):
            s = d['sky'] & (el > 0.5) & (el < 8) & (np.abs(az) >= a0) & (np.abs(az) < a0 + 5) & (L < 85)
            if s.sum() > 100:
                bins.append((a0, float(np.median(L[s]))))
        o['band_L_by_az'] = {f'{a}-{a + 5}': r1(v) for a, v in bins}
        o['band_peak_L'] = r1(max(v for _, v in bins)) if bins else None
        moon = np.degrees(np.arccos(np.clip(d['D'] @ G.L_MOON, -1, 1))) < 1.2
        if moon.any():
            Lm = median_filter(L, size=3)
            o['moon_L_max'] = r1(Lm[moon].max())
        if 'tear' in d:
            wound = binary_dilation(d['tear'], iterations=max(2, int(0.02 * d['W'])))
            o['L_gt90_outside_wound_pct'] = r1(((L > 90) & ~wound).mean() * 100, 3)
    yy, xx = np.unravel_index(np.argsort(luma.ravel())[-2000:], luma.shape)
    o['brightest2000_centroid'] = [r1(xx.mean() / d['W'], 3), r1(yy.mean() / H, 3)]
    if 'tear' in d:
        o['brightest2000_in_wound_pct'] = r1(binary_dilation(d['tear'], iterations=3)[yy, xx].mean() * 100)
    return o


def sea_metrics(d):
    if 'deck' not in d or 'az' not in d:
        return None
    L, az = d['L'], d['az']
    m = d['deck'] & (az > -45) & (az < -4)
    if m.sum() < 500:
        return None
    win = max(5, int(31 * d['s']))
    mu = uniform_filter(L, win)
    sd = np.sqrt(np.maximum(uniform_filter(L * L, win) - mu * mu, 0))
    core = binary_erosion(m, iterations=win // 2)
    path = d['deck'] & (np.abs(az - G.MOON_AZ) < 3)
    off = d['deck'] & (np.abs(az - G.MOON_AZ) > 8) & (np.abs(az - G.MOON_AZ) < 15) & (az < -4)
    return dict(moonward_p5_L=r1(np.percentile(L[m], 5)), moonward_p95_L=r1(np.percentile(L[m], 95)),
                moonward_local_sd_L=r1(np.median(sd[core])) if core.sum() > 100 else None,
                moon_path_minus_off_L=r1(np.median(L[path]) - np.median(L[off])) if path.sum() > 100 and off.sum() > 100 else None,
                deck_area_pct=r1(d['deck'].mean() * 100))


# ------------------------------------------------------------------------------------------------------- frames
def skylight_mask(d, shot='U8a'):
    """the skylight hole in the ceiling plane (gate_bus.SKY_C / SKY_HALF / CEIL_Y) seen from the shot's eye: the ID
    pass draws the clean-shell glass as shell, so the opening is found geometrically (it includes the well's inner
    sides: the visible glass is smaller)."""
    import gate_bus as GB
    sh = SHOTS[shot]
    W, H = d['W'], d['H']
    eye = np.asarray(sh['eye'], float)
    p, yw = math.radians(sh['pitch']), math.radians(sh['yaw'])
    tx = math.tan(math.radians(sh['hfov']) / 2)
    ty = tx * H / W
    fwd = np.array([math.sin(yw) * math.cos(p), math.sin(p), math.cos(yw) * math.cos(p)])
    right = np.array([math.cos(yw), 0.0, -math.sin(yw)])
    up = np.cross(fwd, right)
    xs = (2 * (np.arange(W) + 0.5) / W - 1) * tx
    ys = (1 - 2 * (np.arange(H) + 0.5) / H) * ty
    D = fwd[None, None] + xs[None, :, None] * right[None, None] + ys[:, None, None] * up[None, None]
    t = (GB.CEIL_Y - eye[1]) / np.where(np.abs(D[..., 1]) < 1e-6, 1e-6, D[..., 1])
    P = eye[None, None] + D * t[..., None]
    c = np.asarray(GB.SKY_C, float)
    return (t > 0) & (np.abs(P[..., 0] - c[0]) <= GB.SKY_HALF) & (np.abs(P[..., 2] - c[2]) <= GB.SKY_HALF)


def u8a_metrics(d):
    o = dict(APL=r1(d['luma'].mean()), luma_lt12_pct=r1((d['luma'] < 12).mean() * 100),
             white_L80_pct_of_frame=r1((d['L'] > 80).mean() * 100))
    sky = skylight_mask(d)
    o['skylight_hole_pct_of_frame'] = r1(sky.mean() * 100)
    o['white_L80_pct_of_hole'] = r1(((d['L'] > 80) & sky).sum() / max(sky.sum(), 1) * 100)
    yy, xx = np.unravel_index(np.argsort(d['luma'].ravel())[-2000:], d['luma'].shape)
    o['brightest2000_in_skylight_pct'] = r1(sky[yy, xx].mean() * 100)
    return o


def rear_metrics(d):
    o = dict(APL=r1(d['luma'].mean()), luma_lt12_pct=r1((d['luma'] < 12).mean() * 100))
    if 'inst' not in d:
        return o
    arms = {}
    masks = {}
    for k, v in d['table'].items():
        if not v['id'].startswith('Rear'):
            continue
        m = d['inst'] == k
        if m.sum() < 50:
            continue
        xs = np.where(m)[1]
        arms[v['id']] = dict(width_pct=r1((xs.max() - xs.min() + 1) / d['W'] * 100), area_pct=r1(m.mean() * 100, 2))
        masks[v['id']] = binary_dilation(m, iterations=2)
    ks = list(masks)
    o['arms'] = arms
    o['arms_ge6pct_width'] = sum(1 for v in arms.values() if v['width_pct'] >= 6)
    o['touching_pairs'] = [f'{a}+{b}' for i, a in enumerate(ks) for b in ks[i + 1:] if (masks[a] & masks[b]).any()]
    return o


def knees():
    """awe §5.4: minimum radius of curvature of every hand arm's centreline BODY (u <= 0.80, before the coil /
    whip tip) relative to its length."""
    try:
        lay = G.build_heroes()
    except Exception as e:      # noqa
        return dict(error=str(e))
    out = {}
    for it in lay:
        if not it['id'].startswith('Hand'):
            continue
        cl = G.BL._CLINE.get(it['variant'])
        if cl is None:
            continue
        u, k = np.asarray(cl['u']), np.asarray(cl['k'])
        s = (u > 0.03) & (u <= 0.80)
        rmin = 1.0 / max(float(k[s].max()), 1e-9)
        out[it['id']] = dict(length_m=r1(cl['L'], 0), min_radius_m=r1(rmin, 0), ratio=r1(rmin / cl['L'], 2),
                             at_u=r1(float(u[s][np.argmax(k[s])]), 2))
    return out


FRAMES = (('key', 'keyart_239'), ('U7', 'U7_engelein'), ('U8fwd', 'U8_forward'), ('U6', 'U6_approach'),
          ('U8a', 'U8a_ach_nein'), ('rear', 'rear_window'), ('U8b', 'U8b_spot'), ('U8side', 'U8_side'),
          ('U8near', 'U8_near'))


def run(F, with_knees=True):
    res = {}
    for shot, name in FRAMES:
        png = os.path.join(F, name + '.png')
        if not os.path.exists(png):
            continue
        idn = os.path.join(F, name + '_id.npy')
        # U8a: the ID pass draws the clean-shell skylight glass as shell (no tear / sky classes): image + geometry only
        d = load(png, idn if (os.path.exists(idn) and shot != 'U8a') else None, shot)
        o = dict(tones=tone_metrics(d))
        if shot in ('key', 'U7', 'U8fwd', 'U6'):
            o['tear'] = tear_metrics(d)
            o['arms'] = arm_metrics(d)
            o['multitude'] = multitude_metrics(d)
            o['sea'] = sea_metrics(d)
            o['same_row_contrast'] = same_row_contrast(d)
        if shot == 'U8a':
            o['u8a'] = u8a_metrics(d)
        if shot == 'rear':
            o['rear'] = rear_metrics(d)
        res[name] = o
    if with_knees:
        res['knees'] = knees()
    return res


if __name__ == '__main__':
    F = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'final')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(F, 'acceptance_r5.json')
    res = run(F)
    json.dump(res, open(out, 'w'), indent=1)
    print(json.dumps(res, indent=1)[:12000])
