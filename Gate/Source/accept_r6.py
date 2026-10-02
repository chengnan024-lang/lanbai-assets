"""Round 8 (refine round 4): the GESTALT checks both r4 critiques asked for (critique_awe_r4 §6, critique_tech_r4 B1/B2/M1),
on top of accept_r5's numbers. Pure numpy on the 8-bit display PNGs + their ID passes (+ the scene-linear _lin.npy where
a pre-bloom number is useful).

    python3 accept_r6.py [final_dir] [out.json]        (default: final/ -> final/acceptance_r6.json)

  bright      L* > 80 outside the wound (dilated tear ID) and the moon disc: % of the frame; brightest 2000 px in the wound.
  silhouette  arm pixels within 6 px (x W/2560) of the white (tear ID & L* > 75): p10 / p50 / p90 L*, post-bloom (the PNG)
              and pre-bloom (the _lin.npy through the S4 grade without bloom).
  tear shape  per row extent of the white; width at 5 % of the visible height above the visible foot / max width;
              longest run of >= 20 consecutive columns whose bottom-most white pixel sits on ONE row (a ruler edge);
              bright components (L* > 75, >= 20 px) within 1.5 max widths of the white that are not connected to it.
  foot        the 0-60 px (x W/2560) band below the white's foot rows, +- 1 max width: sd and p95 of L*.
  cloth       the SKY pixels within 1.5 max widths of the white: sd of the high-pass (L* - gaussian(sigma 8 px)).
  multitude   per Mult_* member >= 30 px tall: interior range (p95 - p5 of L*, ID mask eroded 2 px); % >= 6 L*;
              free band: % of the columns in az -50..50 (el 0..12 deg) with no multitude pixel.
  lane        deck pixels within 4 deg of the foot azimuth, rows between the foot and the frame bottom: p95 / p5 of L*.
  deck far    deck rows whose plane distance (eye height / tan(depression)) is 1-3 km: median of the per-row L* sd.
  periodic    along the near / side whips (ID t > 0.80): the L* profile sampled along t, FFT peak / median (<= 8);
              run 9: + ring_band = the longest contiguous run, high-passed, periods 4-64 bins (the ring / bead test proper).
  rear        plain (deck pixels) p95; border: the frame's outer 4 % ring luma < 10 on >= 90 % of its pixels.
  U8a         specks: connected components of 2-30 px whose L* differs > 12 from their 9-px median, outside the white.
"""
import json
import math
import os
import sys

import numpy as np
from scipy.ndimage import binary_dilation, binary_erosion, gaussian_filter, label, median_filter

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import accept_r5 as A  # noqa: E402
import gate_layout as G  # noqa: E402
from gate_scene_shots import SHOTS  # noqa: E402

r1 = A.r1


def white_and_arms(d):
    wh = A.tear_white(d)
    arms = (d['inst'] > 0) if 'inst' in d else np.zeros_like(wh)
    return wh, arms


def bright_outside(d):
    if 'tear' not in d:
        return None
    L = d['L']
    wound = binary_dilation(d['tear'], iterations=max(2, int(0.02 * d['W'])))
    moon = np.zeros_like(wound)
    if 'D' in d:
        moon = np.degrees(np.arccos(np.clip(d['D'] @ G.L_MOON, -1, 1))) < 1.5
    out = (L > 80) & ~wound & ~moon
    yy, xx = np.unravel_index(np.argsort(d['luma'].ravel())[-2000:], d['luma'].shape)
    return dict(L_gt80_outside_wound_moon_pct=r1(out.mean() * 100, 3), L_gt80_outside_px=int(out.sum()),
                brightest2000_in_wound_pct=r1(wound[yy, xx].mean() * 100))


def silhouettes(d, lin_path=None):
    if 'inst' not in d:
        return None
    wh, arms = white_and_arms(d)
    near = binary_dilation(wh, iterations=A.px(d, 6))
    m = arms & near
    if m.sum() < 30:
        return dict(pixels=int(m.sum()))
    o = dict(pixels=int(m.sum()), post_bloom_p10_p50_p90=[r1(x) for x in np.percentile(d['L'][m], [10, 50, 90])])
    if lin_path and os.path.exists(lin_path):
        sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'tear', 'v2'))
        import s4
        from metrics import lab
        lin = np.load(lin_path).astype(np.float32)
        disp = s4.to_display(lin, bloom=False, vignette=True)
        Lp = lab(np.round(np.clip(disp, 0, 1) * 255))[0]
        if Lp.shape == m.shape:
            o['pre_bloom_p10_p50_p90'] = [r1(x) for x in np.percentile(Lp[m], [10, 50, 90])]
    return o


def tear_shape(d):
    wh = A.tear_white(d)
    H, W = wh.shape
    rows = np.where(wh.sum(1) >= 2)[0]
    if len(rows) < 20:
        return None
    # round 8b: the white is CUT by the arms crossing it (the whips' X): pieces of the white separated only by arm pixels
    # belong to the main shape (they were counted as 'detached shapes' before)
    conn = wh.copy()
    if 'inst' in d:
        conn |= (d['inst'] > 0) & binary_dilation(wh, iterations=A.px(d, 6))
    lab_, n = label(binary_dilation(conn, iterations=1))
    sizes = np.bincount(lab_.ravel(), weights=wh.ravel().astype(float))
    sizes[0] = 0
    main = (lab_ == int(np.argmax(sizes))) & wh
    rows = np.where((wh & main).sum(1) >= 2)[0]
    top, foot = rows.min(), rows.max()
    span = foot - top
    width = np.array([(wh & main)[r].sum() for r in range(H)])
    wmax = width.max()
    r5 = int(round(foot - 0.05 * span))
    w5 = width[max(r5 - 1, 0):r5 + 2].mean() / max(wmax, 1)
    # the ruler: bottom-most white row per column
    cols = np.where((wh & main).any(0))[0]
    bot = np.array([np.where((wh & main)[:, c])[0].max() for c in cols])
    def longest(cols, bot):
        best = run = 1
        for i in range(1, len(bot)):
            if abs(int(bot[i]) - int(bot[i - 1])) <= 0 and cols[i] == cols[i - 1] + 1:
                run += 1
                best = max(best, run)
            else:
                run = 1
        return best
    best = longest(cols, bot)
    best_id = None
    if 'tear' in d:                 # the tech critic's definition: the tear-ID mask's bottom edge
        tm = d['tear'] & binary_dilation(main, iterations=int(0.3 * wmax) + 2)
        c2 = np.where(tm.any(0))[0]
        if len(c2) > 5:
            b2 = np.array([np.where(tm[:, c])[0].max() for c in c2])
            best_id = longest(c2, b2)
    # detached bright shapes near the white
    bright = d['L'] > 75
    lb, nb = label(bright)
    zone = binary_dilation(main, iterations=int(1.5 * wmax))
    det = 0
    for k in range(1, nb + 1):
        mk = lb == k
        if mk.sum() < A.px(d, 20) or (mk & binary_dilation(lab_ == int(np.argmax(sizes)), iterations=2)).any():
            continue
        if (mk & zone).any():
            det += 1
    # the foot band
    xs = np.where((wh & main)[foot - max(2, int(0.03 * span)):foot + 1].any(0))[0]
    cx = int(xs.mean()) if len(xs) else W // 2
    b0, b1 = foot + 1, min(H, foot + 1 + A.px(d, 60))
    x0, x1 = max(0, cx - int(wmax)), min(W, cx + int(wmax))
    band = d['L'][b0:b1, x0:x1]
    # cloth: sky high-pass within 1.5 widths
    hp = d['L'] - gaussian_filter(d['L'], 8.0 * d['s'] * 2.0)
    ring = zone & ~binary_dilation(main, iterations=A.px(d, 4))
    if 'sky' in d:
        ring &= d['sky']
    return dict(visible_rows=int(span), max_width_px=int(wmax), width_at_5pct_from_foot_over_max=r1(w5, 2),
                longest_ruler_run_cols=int(best), longest_ruler_run_cols_tearID=best_id, detached_bright_shapes=det,
                foot_band_sd_L=r1(band.std()) if band.size else None, foot_band_p95_L=r1(np.percentile(band, 95)) if band.size else None,
                sky_highpass_sd_within_1p5_widths=r1(hp[ring].std()) if ring.sum() > 100 else None)


def multitude(d):
    if 'inst' not in d:
        return None
    L = d['L']
    rngs, n30 = [], 0
    for k, v in d['table'].items():
        if not v['id'].startswith('Mult_'):
            continue
        m = d['inst'] == k
        if m.sum() == 0:
            continue
        ys = np.where(m)[0]
        if ys.max() - ys.min() + 1 < 30 * d['s'] * 2:
            continue
        n30 += 1
        me = binary_erosion(m, iterations=2)
        if me.sum() < 30:
            continue
        v_ = L[me]
        rngs.append(np.percentile(v_, 95) - np.percentile(v_, 5))
    o = dict(members_ge30px=n30, measured=len(rngs))
    if rngs:
        o['interior_range_median'] = r1(np.median(rngs))
        o['pct_range_ge6'] = r1(np.mean(np.array(rngs) >= 6) * 100)
    if 'az' in d:
        az, el = d['az'], d['el']
        mult = np.zeros_like(L, bool)
        for k, v in d['table'].items():
            if v['id'].startswith('Mult_'):
                mult |= d['inst'] == k
        cols = (np.abs(az) <= 50) & (el > 0) & (el < 12)
        azc = np.round(az[cols]).astype(int)
        occ = {}
        for a_, mm in zip(azc, mult[cols]):
            occ[a_] = occ.get(a_, False) or bool(mm)
        seen = [a for a in occ]
        if seen:
            o['free_band_pct_of_visible_az'] = r1(100.0 * sum(1 for a in seen if not occ[a]) / len(seen))
            o['visible_az_range'] = [int(min(seen)), int(max(seen))]
    return o


def lane_and_deck(d, shot):
    if 'deck' not in d or 'az' not in d:
        return None
    sh = SHOTS[shot]
    t = sh['t']
    e = G.eye_cf(t, sh['eye'])
    S = G.tear_H(t) / G.TD.H
    xf = 0.5 * float(G.TD.path(np.array([0.0]))[0]) * S
    azf = math.degrees(math.atan2(xf - e[0], -e[1]))
    L, az, el = d['L'], d['az'], d['el']
    o = {}
    lane = d['deck'] & (np.abs(az - azf) < 4) & (el < -0.3)
    if lane.sum() > 200:
        o['lane_p95_L'] = r1(np.percentile(L[lane], 95))
        o['lane_p5_L'] = r1(np.percentile(L[lane], 5))
    dist = e[2] / np.tan(np.radians(np.clip(-el, 0.01, 89)))
    sds = []
    for r in range(d['H']):
        m = d['deck'][r] & (dist[r] > 1000) & (dist[r] < 3000)
        if m.sum() > 40:
            sds.append(L[r, m].std())
    o['deck_1_3km_row_sd_median'] = r1(np.median(sds)) if sds else None
    return o


def periodicity(d):
    """FFT peak / median of the L* profile along t of every thin whip part (t > 0.80) of near / mid / rear arms."""
    if 'inst' not in d:
        return None
    out = {}
    for k, v in d['table'].items():
        if v.get('layer') not in ('near', 'mid', 'rear', 'colossus'):
            continue
        m = (d['inst'] == k) & (d['t'] > 0.80) & (d['t'] < 0.985)
        if m.sum() < 200:
            continue
        tv, Lv = d['t'][m], d['L'][m]
        nb = 512
        bins = np.linspace(0.80, 0.985, nb + 1)
        idx = np.digitize(tv, bins) - 1
        prof = np.array([np.percentile(Lv[idx == i], 90) if (idx == i).sum() > 1 else np.nan for i in range(nb)])
        ok = np.isfinite(prof)
        if ok.sum() < 128:
            continue
        p = np.interp(np.arange(nb), np.where(ok)[0], prof[ok])
        p = p - gaussian_filter(p, 24)
        F = np.abs(np.fft.rfft(p))[2:]
        o = dict(all_bins=r1(F.max() / max(np.median(F), 1e-6), 1))
        # run 9: the whole-window number is dominated by the gross shape (occluded / out-of-frame stretches interpolated
        # flat, single highlights). The ring / bead test proper: the longest CONTIGUOUS run of measured bins, high-passed
        # (sigma 6 bins), periods 4..64 bins only.
        okf = ok.copy()                       # gaps of <= 3 bins (thin parts: < 2 px per bin) count as measured
        gi = np.where(~ok)[0]
        for g0 in gi:
            lo_, hi_ = g0, g0
            while lo_ - 1 >= 0 and not ok[lo_ - 1]:
                lo_ -= 1
            while hi_ + 1 < nb and not ok[hi_ + 1]:
                hi_ += 1
            if hi_ - lo_ + 1 <= 3 and lo_ > 0 and hi_ < nb - 1:
                okf[lo_:hi_ + 1] = True
        prof = np.where(ok, prof, np.interp(np.arange(nb), np.where(ok)[0], prof[ok]))
        ok = okf
        runs, st = [], None
        for i in range(nb + 1):
            if i < nb and ok[i]:
                st = i if st is None else st
            elif st is not None:
                runs.append((st, i)); st = None
        if runs:
            a0, a1 = max(runs, key=lambda r_: r_[1] - r_[0])
            if a1 - a0 >= 64:
                q = prof[a0:a1] - gaussian_filter(prof[a0:a1], 6)
                Fq = np.abs(np.fft.rfft(q * np.hanning(len(q))))
                fr = np.fft.rfftfreq(len(q))
                band = (fr >= 1 / 64.0) & (fr <= 1 / 4.0)
                if band.sum() > 8:
                    o['ring_band'] = r1(Fq[band].max() / max(np.median(Fq[band]), 1e-6), 1)
                    o['ring_band_bins'] = int(a1 - a0)
        out[v['id']] = o
    return out


def rear_extra(d):
    o = {}
    if 'deck' in d:
        o['plain_p95_L'] = r1(np.percentile(d['L'][d['deck']], 95)) if d['deck'].sum() > 100 else None
    H, W = d['luma'].shape
    b = int(0.04 * min(H, W))
    ring = np.zeros((H, W), bool)
    ring[:b] = ring[-b:] = True
    ring[:, :b] = ring[:, -b:] = True
    o['border_dark_pct'] = r1((d['luma'][ring] < 10).mean() * 100)
    return o


def specks(d):
    L = d['L']
    med = median_filter(L, size=9)
    diff = np.abs(L - med) > 12
    wh = d['L'] > 80
    lb, n = label(diff & ~binary_dilation(wh, iterations=2))
    sizes = np.bincount(lb.ravel())[1:]
    return dict(specks_outside_white=int(((sizes >= 2) & (sizes <= 30)).sum()))


FR = (('key', 'keyart_239'), ('U7', 'U7_engelein'), ('U8fwd', 'U8_forward'), ('U6', 'U6_approach'),
      ('U8a', 'U8a_ach_nein'), ('rear', 'rear_window'), ('U8b', 'U8b_spot'), ('U8side', 'U8_side'), ('U8near', 'U8_near'))


def run(F):
    res = {}
    for shot, name in FR:
        png = os.path.join(F, name + '.png')
        if not os.path.exists(png):
            continue
        idn = os.path.join(F, name + '_id.npy')
        d = A.load(png, idn if os.path.exists(idn) else None, shot)
        o = dict(tones=A.tone_metrics(d))
        if shot in ('key', 'U7', 'U8fwd', 'U6'):
            o['bright'] = bright_outside(d)
            o['silhouettes'] = silhouettes(d, os.path.join(F, name + '_lin.npy'))
            o['tear_shape'] = tear_shape(d)
            o['tear_r5'] = A.tear_metrics(d)
            o['multitude'] = multitude(d)
            o['lane_deck'] = lane_and_deck(d, shot)
            o['sea_r5'] = A.sea_metrics(d)
        if shot in ('U8near', 'U8side', 'rear', 'U8fwd'):
            o['periodicity_fft_peak_over_median'] = periodicity(d)
        if shot == 'rear':
            o['rear'] = A.rear_metrics(d)
            o['rear_extra'] = rear_extra(d)
        if shot == 'U8a':
            o['u8a'] = A.u8a_metrics(d)
            o['specks'] = specks(d)
        res[name] = o
        print(name, 'done')
    return res


if __name__ == '__main__':
    F = sys.argv[1] if len(sys.argv) > 1 else os.path.join(HERE, 'final')
    out = sys.argv[2] if len(sys.argv) > 2 else os.path.join(F, 'acceptance_r6.json')
    res = run(F)
    json.dump(res, open(out, 'w'), indent=1, default=lambda x: x.tolist() if hasattr(x, 'tolist') else str(x))
    print('wrote', out)
