"""Bible §6·4 + round-2 acceptance numbers on a gate frame (round 2: per-instance ID pass).

    python3 gate_metrics.py SHOT <display.png> <base>_id.npy [out.json]

ID pass (gate_scene.id_materials): R = (instance index + 1) / 128 (table in <base>_idmap.json), G = arc fraction t,
B = 0.25 tear lens / flaps, 0.5 cloud deck, 0.75 tide, 1.0 bus shell; sky = all 0.
Reports: APL (whole frame and through the glass), % luma < 12, % strong violet (C* > 30, h 290-325); per layer
(near, pillars, mid crowns t > 0.55, mid bodies, colossus crowns, Engel, background, haze behind) the median L*
AND the silhouette-edge L* (layer pixels within 2 px of sky); rim p99 L* in the 3-px band along each layer's
silhouette; ID area %; distinct silhouettes above the horizon; % pixels L* > 85 outside the wound / moon / pillar
rims; cloud pool / plain / moonward L* + C*; % C* > 12 at h 285-330 outside 25 deg of the wound."""
import json
import math
import os
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import binary_dilation, binary_erosion

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tear', 'v2'))
from metrics import lab  # noqa: E402
import gate_layout as G  # noqa: E402
from gate_plan import Cam  # noqa: E402
from gate_scene_shots import SHOTS  # noqa: E402


def stats(L, m, min_n=20):
    n = int(m.sum())
    if n < min_n:
        return None
    return dict(L_median=round(float(np.median(L[m])), 1), L_p10=round(float(np.percentile(L[m], 10)), 1),
                L_p90=round(float(np.percentile(L[m], 90)), 1), pixels=n)


def run(shot, png, idnpy, out=None):
    im = np.asarray(Image.open(png).convert('RGB')).astype(float)
    H, W = im.shape[:2]
    luma = im @ np.array([0.2126, 0.7152, 0.0722])
    L, a, b = lab(im)
    C = np.hypot(a, b)
    h = np.degrees(np.arctan2(b, a)) % 360
    viol = (C > 30) & (h > 290) & (h < 325)
    ids = np.load(idnpy).astype(np.float32)
    if ids.shape[:2] != (H, W):
        raise SystemExit('id size mismatch')
    table = {int(k): v for k, v in json.load(open(idnpy.replace('_id.npy', '_idmap.json'))).items()}
    inst = np.round(ids[..., 0] * 128).astype(int)
    t = ids[..., 1]
    other = ids[..., 2]
    shell = (inst == 0) & (other > 0.9)
    tear = (inst == 0) & (np.abs(other - 0.25) < 0.05)
    deck = (inst == 0) & (np.abs(other - 0.5) < 0.05)
    tide = (inst == 0) & (np.abs(other - 0.75) < 0.05)
    sky = (inst == 0) & (other < 0.1)
    kind = np.full(inst.shape, '', object)
    for k, v in table.items():
        kind[inst == k] = v['kind']
    lay = {kn: (kind == kn) for kn in ('near', 'pillar', 'mid', 'colossus', 'hero', 'bg', 'rear', 'surge')}
    glass = ~shell
    sh = SHOTS[shot]
    SHOTS_HFOV[0] = sh['hfov']
    cam = Cam(G.eye_cf(sh['t'], sh['eye']), sh['yaw'], sh['pitch'], sh['hfov'], W, H)
    D = cam.rays()
    az, el = G.azel_of(D)
    o = dict(shot=shot, t=sh['t'])
    o['APL'] = round(float(luma.mean()), 1)
    o['APL_through_glass'] = round(float(luma[glass].mean()), 1) if glass.any() else None
    o['luma_lt12_pct'] = round(float((luma < 12).mean() * 100), 1)
    o['strong_violet_pct'] = round(float(viol.mean() * 100), 2)
    # --- layers
    o['near_body'] = stats(L, lay['near'])
    o['pillars'] = stats(L, lay['pillar'])
    o['mid_crowns'] = stats(L, lay['mid'] & (t > 0.55))
    o['mid_bodies'] = stats(L, lay['mid'] & (t <= 0.55))
    o['colossus_crowns'] = stats(L, (lay['colossus'] | lay['bg'] | lay['hero']) & (t > 0.55))
    o['engel'] = stats(L, lay['hero'])
    o['background_colossi'] = stats(L, lay['bg'])
    band = sky & (el > 0.5) & (el < 12) & (np.abs(az) > 4) & (np.abs(az) < 30) & (luma < 200)
    o['haze_behind'] = stats(L, band)
    # silhouette-edge L*: layer pixels within 2 px of sky
    near_sky = binary_dilation(sky, iterations=2)
    # the wound and its glow: silhouette pixels there are anti-aliased against L* 90+ white (not a rim)
    glow = binary_dilation(tear | (L > 80) & sky, iterations=int(0.012 * W) + 2)
    edge = {}
    for kn, m in lay.items():
        e = m & near_sky
        s = stats(L, binary_erosion(m, iterations=2) & binary_dilation(e, iterations=4) & ~e)   # just inside the rim
        edge[kn] = dict(rim_band=stats(L, e), body_inside_edge=s)
        if e.sum() > 20:
            edge[kn]['rim_p99'] = round(float(np.percentile(L[e], 99)), 1)
        e2 = e & ~glow
        if e2.sum() > 20:
            edge[kn]['rim_p99_away_from_wound'] = round(float(np.percentile(L[e2], 99)), 1)
    o['silhouette'] = edge
    steps = {}
    def med(x):
        return None if x is None else x['L_median']
    se = {kn: (edge[kn]['body_inside_edge'] or {}).get('L_median') for kn in lay}
    steps['pillar->mid (edge)'] = None if None in (se['pillar'], se['mid']) else round(se['mid'] - se['pillar'], 1)
    cc = med(o['colossus_crowns'])
    steps['mid crowns->colossus crowns'] = None if None in (med(o['mid_crowns']), cc) else round(cc - med(o['mid_crowns']), 1)
    steps['colossus crowns->haze'] = None if None in (cc, med(o['haze_behind'])) else round(med(o['haze_behind']) - cc, 1)
    steps['pillars->mid crowns'] = None if None in (med(o['pillars']), med(o['mid_crowns'])) else round(med(o['mid_crowns']) - med(o['pillars']), 1)
    o['layer_steps'] = steps
    # --- areas
    N = float(H * W)
    o['area_pct'] = dict(pillars=round(lay['pillar'].sum() / N * 100, 1), mid=round(lay['mid'].sum() / N * 100, 1),
                         engel=round(lay['hero'].sum() / N * 100, 1),
                         colossi=round((lay['colossus'] | lay['bg']).sum() / N * 100, 1),
                         near=round(lay['near'].sum() / N * 100, 1),
                         sky=round(sky.sum() / N * 100, 1), deck=round(deck.sum() / N * 100, 1),
                         tear=round(tear.sum() / N * 100, 2), shell=round(shell.sum() / N * 100, 1))
    above = el > 0.3
    n_sil = 0
    for k in table:
        if ((inst == k) & above).sum() > 0.0004 * N:
            n_sil += 1
    o['silhouettes_above_horizon'] = n_sil
    # --- one brightest point
    wound = binary_dilation(tear, iterations=int(0.02 * W))
    moon = np.degrees(np.arccos(np.clip(D @ G.L_MOON, -1, 1))) < 1.5
    pillar_rim = binary_dilation(lay['pillar'], iterations=3) & ~binary_erosion(lay['pillar'], iterations=3)
    bright = (L > 85) & ~wound & ~moon & ~pillar_rim
    o['L85_outside_wound_pct'] = round(float(bright.mean() * 100), 3)
    # --- cloud sea: plane z = 0 (the deck plane is at 12 m x k; close enough)
    e = cam.pos
    tpl = np.where(D[..., 2] < -1e-4, -(e[2] - 12.0) / np.minimum(D[..., 2], -1e-4), np.inf)
    P = e[None, None] + D * tpl[..., None]
    rf = np.hypot(P[..., 0], P[..., 1] - 0.0)
    pool = deck & (rf < 300.0)
    plain = deck & (rf > 1300.0) & (rf < 3000.0)
    moonward = deck & (az < -6) & (az > -24)
    o['cloud'] = dict(pool=stats(L, pool), plain=stats(L, plain),
                      moonward_p90_L=round(float(np.percentile(L[moonward], 90)), 1) if moonward.sum() > 50 else None,
                      moonward_C_median=round(float(np.median(C[moonward])), 1) if moonward.sum() > 50 else None,
                      plain_C_median=round(float(np.median(C[plain])), 1) if plain.sum() > 50 else None)
    # --- colour families
    core = G.tear_core_cf(sh['t'])
    tc = G.unit(core - e)
    ang_w = np.degrees(np.arccos(np.clip(D @ tc, -1, 1)))
    lav = (C > 12) & (h > 285) & (h < 330) & (ang_w > 25)
    o['lavender_outside_25deg_pct'] = round(float(lav.mean() * 100), 1)
    o['round3'] = round3(L, C, h, luma, inst, t, other, sky, deck, tide, tear, table, az, el, W, H)
    if out:
        json.dump(o, open(out, 'w'), indent=1)
    return o


def ring_contrast(L, m, sky, r0=4, r1=12):
    """critique_r2 ring method: median L* of the silhouette minus the median L* of the sky 4-12 px around it."""
    if m.sum() < 30:
        return None
    ring = binary_dilation(m, iterations=r1) & ~binary_dilation(m, iterations=r0) & sky
    if ring.sum() < 30:
        return None
    return round(float(np.median(L[m]) - np.median(L[ring])), 1)


def round3(L, C, h, luma, inst, t, other, sky, deck, tide, tear, table, az, el, W, H):
    """round-3 acceptance (critique_awe_r2 section 7)."""
    from scipy.ndimage import uniform_filter, label
    r = {}
    per = {}
    for k, v in table.items():
        m = inst == k
        if m.sum() < 30:
            continue
        d = dict(kind=v['kind'], role=v.get('role'), dL_ring=ring_contrast(L, m, sky), area_pct=round(float(m.mean() * 100), 2))
        if v.get('role') == 'engel':
            tip = m & (t > 0.80)
            d['hand_dL_ring'] = ring_contrast(L, tip, sky | tear)
            d['body_dL_ring'] = ring_contrast(L, m & (t < 0.6), sky)
        per[v['id']] = d
    r['per_instance'] = per
    def grp(kinds, roles=None):
        vals = [d['dL_ring'] for d in per.values() if d['dL_ring'] is not None and d['kind'] in kinds and
                (roles is None or d['role'] in roles)]
        return None if not vals else dict(median=round(float(np.median(vals)), 1), min=round(float(min(vals)), 1),
                                          max=round(float(max(vals)), 1), n=len(vals))
    r['dL_ring'] = dict(pillars=grp(('pillar',)), hands=grp(('mid',), ('hand',)), engel=grp(('hero',)),
                        colossi=grp(('colossus', 'bg')), surge=grp(('surge',)), near=grp(('near',)), rear=grp(('rear',)))
    # tide: connected blades, contrast against the sky ring
    lab_, n = label(tide)
    sizes = np.bincount(lab_.ravel())[1:] if n else np.array([])
    r['tide'] = dict(blades=int((sizes >= 6).sum()), pixels_pct=round(float(tide.mean() * 100), 3),
                     dL_ring=ring_contrast(L, tide, sky, 2, 6),
                     brighter_than_sky_pct=None)
    # top of frame (sky only)
    for frac in (0.10, 0.25):
        rr = int(H * frac)
        m = sky[:rr]
        r['top%d_sky_L' % int(frac * 100)] = round(float(np.median(L[:rr][m])), 1) if m.sum() > 50 else None
    r['frac_L15_40_pct'] = round(float(((L > 15) & (L < 40)).mean() * 100), 1)
    # mirror IoU of the dark silhouettes about the wound axis (column of the tear centroid)
    ys, xs = np.nonzero(tear)
    if len(xs):
        cx = int(np.round(xs.mean()))
        dark = (inst > 0) & (L < 20)
        half = min(cx, W - cx)
        lft = dark[:, cx - half:cx]
        rgt = dark[:, cx:cx + half][:, ::-1]
        inter = (lft & rgt).sum()
        uni = (lft | rgt).sum()
        r['mirror_IoU'] = round(float(inter / max(uni, 1)), 2)
        r['tear_centroid_x_pct'] = round(cx / W * 100, 1)
    # silhouettes taller than 10 % of the frame height above the horizon (a bundle counts once)
    seen = set()
    above = el > 0.3
    for k, v in table.items():
        m = (inst == k) & above
        if not m.any():
            continue
        rows = np.nonzero(m.any(1))[0]
        if rows.max() - rows.min() > 0.10 * H:
            seen.add(v['id'].rstrip('0123456789') if v.get('role') == 'hand' else v['id'])
    r['silhouettes_gt10pct_above_horizon'] = len(seen)
    # deck local contrast (31 px at 2560)
    win = max(5, int(31 * W / 2560))
    mu = uniform_filter(L, win)
    sd = np.sqrt(np.maximum(uniform_filter(L * L, win) - mu * mu, 0.0))
    dk = binary_erosion(deck, iterations=win)
    near_rows = dk & (el < -6.0)
    mid_rows = dk & (el >= -6.0) & (el < -1.5)
    r['deck_sigma_L'] = dict(near=round(float(np.median(sd[near_rows])), 2) if near_rows.sum() > 50 else None,
                             mid=round(float(np.median(sd[mid_rows])), 2) if mid_rows.sum() > 50 else None)
    r['near_deck_L'] = round(float(np.median(L[deck & (el < -6.0)])), 1) if (deck & (el < -6.0)).sum() > 50 else None
    # the halo's chroma 1-3 deg from the lips
    if tear.any():
        px_deg = W / float(SHOTS_HFOV[0])
        rim1 = binary_dilation(tear, iterations=max(1, int(1 * px_deg))) & ~tear
        rim3 = binary_dilation(tear, iterations=max(2, int(3 * px_deg))) & ~binary_dilation(tear, iterations=max(1, int(1 * px_deg)))
        r['halo_C_0_1deg'] = round(float(np.median(C[rim1 & sky])), 1) if (rim1 & sky).sum() > 30 else None
        r['halo_C_1_3deg'] = round(float(np.median(C[rim3 & sky])), 1) if (rim3 & sky).sum() > 30 else None
        r['halo_L_1_3deg'] = round(float(np.median(L[rim3 & sky])), 1) if (rim3 & sky).sum() > 30 else None
    return r


SHOTS_HFOV = [90.0]


if __name__ == '__main__':
    a = sys.argv[1:]
    r = run(a[0], a[1], a[2], a[3] if len(a) > 3 else None)
    print(json.dumps(r, indent=1))
