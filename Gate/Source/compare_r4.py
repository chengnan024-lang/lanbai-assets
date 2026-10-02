"""Round 8 (refine round 4): the three before / after sheets the awe r4 critique asked for (§5 'Required comparisons'),
with the measured numbers under each crop (accept_r6.py definitions).

    python3 compare_r4.py      -> final/compare_r4_tear.png, compare_r4_light.png, compare_r4_multitude.png

BEFORE = gate/_r4/final (the round-7 finals the r4 critiques reviewed, with their ID passes); AFTER = final/."""
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import accept_r5 as A  # noqa: E402
import accept_r6 as R  # noqa: E402
from compare_r3 import bbox, sheet, tile  # noqa: E402

F_NEW = os.path.join(HERE, 'final')
F_OLD = os.path.join(HERE, '_r4', 'final')


def ld(F, name, shot):
    png = os.path.join(F, name + '.png')
    idn = os.path.join(F, name + '_id.npy')
    d = A.load(png, idn if os.path.exists(idn) else None, shot)
    d['img'] = Image.open(png).convert('RGB')
    d['lin'] = os.path.join(F, name + '_lin.npy')
    return d


def f(x, n=1):
    return '-' if x is None else (('%.' + str(n) + 'f') % x if isinstance(x, (float, np.floating)) else str(x))


def tear_caption(d):
    ts = R.tear_shape(d) or {}
    tr = A.tear_metrics(d) or {}
    return ['width at 5 %% from foot / max %s [<=0.35]' % f(ts.get('width_at_5pct_from_foot_over_max'), 2),
            'ruler run (cols, same bottom row) %s / tear-ID %s [<=20 px]' % (ts.get('longest_ruler_run_cols'),
                                                                          ts.get('longest_ruler_run_cols_tearID')),
            'foot band 0-60 px: sd %s  p95 %s [sd>=8, p95>=70]' % (f(ts.get('foot_band_sd_L')), f(ts.get('foot_band_p95_L'))),
            'sky high-pass sd (1.5 widths) %s [>=6]   detached %s [0]' % (f(ts.get('sky_highpass_sd_within_1p5_widths')),
                                                                         ts.get('detached_bright_shapes')),
            'lip glow 6 px out: C* %s [<=18]' % f(tr.get('lipglow_6px_median_C'))]


def tear_box(d, scale_pad=0.35, aspect=None):
    wh = A.tear_white(d)
    ys, xs = np.where(wh)
    h = ys.max() - ys.min()
    return bbox(wh, int(scale_pad * h), d['W'], d['H'], aspect=aspect)


def make_tear():
    rows = []
    for shot, name, sc, lab in (('key', 'keyart_239', 2.0, 'key, tear x2'), ('U6', 'U6_approach', 3.0, 'U6, tear x3')):
        r = []
        for tag, F in (('BEFORE (round 7)', F_OLD), ('AFTER (round 8)', F_NEW)):
            d = ld(F, name, shot)
            box = tear_box(d, 0.30, aspect=0.75)
            k = min(sc, 560.0 / max(box[3] - box[1], 1))
            r.append((tile(d['img'], box, k), '%s  %s' % (lab, tag), tear_caption(d)))
        rows.append(r)
    r = []
    for tag, F in (('BEFORE (round 7)', F_OLD), ('AFTER (round 8)', F_NEW)):
        d = ld(F, 'U8_forward', 'U8fwd')
        wh = A.tear_white(d)
        ys, xs = np.where(wh)
        cx, fy = int(xs.mean()), int(ys.max())
        w = int(0.45 * d['W'])
        box = (max(0, cx - w // 2), max(0, fy - int(0.30 * d['H'])), min(d['W'], cx + w // 2), min(d['H'], fy + int(0.16 * d['H'])))
        k = 760.0 / (box[2] - box[0])
        r.append((tile(d['img'], box, k), 'U8 forward, the foot  %s' % tag, tear_caption(d)))
    rows.append(r)
    out = sheet('compare_r4_tear: the wound (awe r4 B1 / B4, tech r4 B1 / M4)', rows,
                subtitle='left = round 7 finals (gate/_r4/final), right = round 8 finals (final/); numbers: accept_r6.py tear_shape, '
                         'accept_r5 lip glow; [target]')
    out.save(os.path.join(F_NEW, 'compare_r4_tear.png'))


def light_caption(d, shot):
    b = R.bright_outside(d) or {}
    s = R.silhouettes(d, d['lin']) or {}
    ld_ = R.lane_and_deck(d, shot) or {}
    t = A.tone_metrics(d) or {}
    pb = s.get('pre_bloom_p10_p50_p90')
    return ['L* > 80 outside wound + moon: %s %% (%s px) [0]   brightest 2000 in wound %s %% [100]'
            % (f(b.get('L_gt80_outside_wound_moon_pct'), 3), b.get('L_gt80_outside_px'), f(b.get('brightest2000_in_wound_pct'))),
            'arms by the white p10/p50/p90 post-bloom %s%s [p50<=15, p90>=60]'
            % (s.get('post_bloom_p10_p50_p90'), ('  pre-bloom %s' % pb) if pb else ''),
            'light lane: crest p95 %s  trough p5 %s [>=50, <=20]   deck 1-3 km row sd %s [>=7]'
            % (f(ld_.get('lane_p95_L')), f(ld_.get('lane_p5_L')), f(ld_.get('deck_1_3km_row_sd_median'))),
            'APL %s' % f(t.get('APL') if isinstance(t, dict) else None)]


def make_light():
    rows = []
    r = []
    for tag, F in (('BEFORE (round 7)', F_OLD), ('AFTER (round 8)', F_NEW)):
        d = ld(F, 'keyart_239', 'key')
        r.append((d['img'].resize((1100, int(1100 * d['H'] / d['W'])), Image.LANCZOS), 'key  %s' % tag, light_caption(d, 'key')))
    rows.append(r)
    r = []
    for tag, F in (('BEFORE', F_OLD), ('AFTER', F_NEW)):
        im = Image.open(os.path.join(F, 'keyart_239.png')).convert('RGB')
        r.append((im.resize((640, int(640 * im.height / im.width)), Image.LANCZOS), 'the 640-px read  %s' % tag, []))
    for tag, F in (('BEFORE', F_OLD), ('AFTER', F_NEW)):
        d = ld(F, 'U7_engelein', 'U7')
        r.append((d['img'].resize((480, 270), Image.LANCZOS), 'U7  %s' % tag, light_caption(d, 'U7')[:2]))
    rows.append(r)
    out = sheet('compare_r4_light: one brightest point, silhouettes over the white, the lane (awe r4 B3, tech r4 M1)', rows,
                subtitle='numbers: accept_r6.py (bright_outside, silhouettes, lane_and_deck); [target]')
    out.save(os.path.join(F_NEW, 'compare_r4_light.png'))


def mult_caption(d):
    m = R.multitude(d) or {}
    return ['members >= 30 px tall: %s   interior range median %s   %% >= 6 L*: %s [>=70]'
            % (m.get('members_ge30px'), f(m.get('interior_range_median')), f(m.get('pct_range_ge6'))),
            'band az -50..50 free of multitude: %s %% [>=35]' % f(m.get('free_band_pct_of_visible_az'))]


def make_mult():
    rows = []
    for name, shot, lab in (('keyart_239', 'key', 'key, left third'), ('keyart_239', 'key', 'key, right third')):
        r = []
        for tag, F in (('BEFORE (round 7)', F_OLD), ('AFTER (round 8)', F_NEW)):
            d = ld(F, name, shot)
            W, H = d['W'], d['H']
            box = (0, int(0.18 * H), W // 3, int(0.80 * H)) if 'left' in lab else (2 * W // 3, int(0.18 * H), W, int(0.80 * H))
            k = 760.0 / (box[2] - box[0])
            r.append((tile(d['img'], box, k), '%s  %s' % (lab, tag), mult_caption(d) if 'left' in lab else []))
        rows.append(r)
    out = sheet('compare_r4_multitude: fewer, bigger, layered; towers back (awe r4 B2, tech r4 M2)', rows,
                subtitle='r7: 150 members, one fog | r8: 36 in 5 clusters, fog tiers, rims, mirrored poses, real curls (accept_r6)')
    out.save(os.path.join(F_NEW, 'compare_r4_multitude.png'))


if __name__ == '__main__':
    make_tear()
    make_light()
    make_mult()
    print('wrote final/compare_r4_tear.png, compare_r4_light.png, compare_r4_multitude.png')
