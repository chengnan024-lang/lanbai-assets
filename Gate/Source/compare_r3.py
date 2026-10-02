"""AD round 3: the before / after sheets (round 6 finals -> round 7 finals) with the measured numbers under each crop.

    python3 compare_r3.py      -> final/compare_r3_tear.png, compare_r3_arms.png, compare_r3_grade.png

BEFORE = final/_superseded/r4_final (byte-identical to gate/_r3/final, with its ID passes); AFTER = final/.
Numbers from accept_r5.py (definitions in its docstring)."""
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import accept_r5 as A  # noqa: E402

F_NEW = os.path.join(HERE, 'final')
F_OLD = os.path.join(HERE, 'final', '_superseded', 'r4_final')
BG = (10, 12, 18)
FG = (215, 220, 230)
DIM = (150, 156, 170)
try:
    FONT = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 22)
    FONT_B = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf', 30)
    FONT_S = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 19)
except Exception:      # noqa
    FONT = FONT_B = FONT_S = ImageFont.load_default()


def ld(F, name, shot):
    png = os.path.join(F, name + '.png')
    idn = os.path.join(F, name + '_id.npy')
    d = A.load(png, idn if os.path.exists(idn) else None, shot)
    d['img'] = Image.open(png).convert('RGB')
    return d


def bbox(mask, pad, W, H, aspect=None, min_wh=(64, 64)):
    ys, xs = np.where(mask)
    x0, x1, y0, y1 = xs.min() - pad, xs.max() + pad, ys.min() - pad, ys.max() + pad
    w, h = max(x1 - x0, min_wh[0]), max(y1 - y0, min_wh[1])
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    if aspect:
        if w / h < aspect:
            w = h * aspect
        else:
            h = w / aspect
    x0, y0 = int(max(0, cx - w / 2)), int(max(0, cy - h / 2))
    x1, y1 = int(min(W, x0 + w)), int(min(H, y0 + h))
    return x0, y0, x1, y1


def tile(img, box, scale):
    c = img.crop(box)
    return c.resize((int(c.width * scale), int(c.height * scale)), Image.LANCZOS)


def lines_h(lines, font=FONT_S):
    return 8 + len(lines) * (font.size + 6)


def sheet(title, rows, subtitle=None, W=None):
    """rows = list of lists of (PIL image, label, [caption lines])"""
    pad = 18
    W = W or max(sum(t[0].width for t in r) + pad * (len(r) + 1) for r in rows)
    H = 70 + (34 if subtitle else 0)
    for r in rows:
        H += max(t[0].height + 40 + lines_h(t[2]) for t in r) + pad
    out = Image.new('RGB', (W, H), BG)
    dr = ImageDraw.Draw(out)
    dr.text((pad, 16), title, fill=FG, font=FONT_B)
    y = 62
    if subtitle:
        dr.text((pad, y), subtitle, fill=DIM, font=FONT_S)
        y += 34
    for r in rows:
        x = pad
        rh = 0
        for im, lab, cap in r:
            dr.text((x, y), lab, fill=FG, font=FONT)
            out.paste(im, (x, y + 32))
            yy = y + 36 + im.height
            for ln in cap:
                dr.text((x, yy), ln, fill=DIM, font=FONT_S)
                yy += FONT_S.size + 6
            rh = max(rh, im.height + 40 + lines_h(cap))
            x += im.width + pad
        y += rh + pad
    return out


def tear_lines(m):
    if not m:
        return ['(no tear measured)']
    dsg = m['dark_segments_per_lip']
    return ['axis L* range %s [>=18]   hot-widest %s%% [+-8]' % (m['axis_L_range_central80'],
                                                              m['hot_row_minus_widest_row_pct_of_span']),
            'b* hot %s  lips %s  tip %s  [hot +2..4; lips,tip <=-2]' % (m['b_hot'], m['b_lips'], m['b_tip']),
            'glow 6px out: sd %s [>=10]  C* %s [<=18]' % (m['lipglow_6px_sd_L'], m['lipglow_6px_median_C']),
            'dark segments per lip: L %s  R %s  [>=3]' % (dsg.get('left'), dsg.get('right'))]


def make_tear(old, new):
    rows = []
    r = []
    for tag, d, in (('round 6', old['key']), ('round 7', new['key'])):
        wh = A.tear_white(d)
        box = bbox(wh, int(0.03 * d['W']), d['W'], d['H'], aspect=0.62)
        sc = 1050.0 / (box[3] - box[1])
        m = A.tear_metrics(d)
        r.append((tile(d['img'], box, sc), 'KEY tear x%.1f  (%s)' % (sc, tag), tear_lines(m)))
    for tag, d in (('round 6', old['U6']), ('round 7', new['U6'])):
        wh = A.tear_white(d)
        box = bbox(wh, int(0.02 * d['W']), d['W'], d['H'], aspect=0.62)
        sc = 1050.0 / (box[3] - box[1])
        m = A.tear_metrics(d)
        r.append((tile(d['img'], box, sc), 'U6 tear x%.1f  (%s)' % (sc, tag), tear_lines(m)[:3]))
    rows.append(r)
    r = []
    for tag, d in (('round 6', old['U8fwd']), ('round 7', new['U8fwd'])):
        W, H = d['W'], d['H']
        wh = A.tear_white(d)
        cx = int(np.mean(np.where(wh)[1]))
        box = (max(0, cx - 560), 60, min(W, cx + 560), 60 + 760)
        m = A.tear_metrics(d)
        r.append((tile(d['img'], box, 1.0), 'U8 forward, centre x1  (%s)' % tag, tear_lines(m)))
    rows.append(r)
    return sheet('compare_r3_tear  -  AD round 3 item 1: the tear (kit v4.1 -> v5)', rows,
                 'pairs: round 6 (gate/_r3) | round 7. Depth, veils, hot off-centre core, varying edge, folds, backlit threads, '
                 'hanging flaps, luminous foot. Numbers: accept_r5.py on the shipped PNG + ID pass; [brackets] = critique_awe_r3 §5.')


def hand_box(d, prefix, pad, aspect):
    m = np.zeros((d['H'], d['W']), bool)
    for k, v in d['table'].items():
        if v['id'].startswith(prefix):
            m |= d['inst'] == k
    return bbox(m, pad, d['W'], d['H'], aspect=aspect)


def arm_lines(arms, ids):
    out = []
    for i in ids:
        a = (arms or {}).get(i)
        if a:
            out.append('%s: section range %s (p25 %s), tear-side flank %s, body %s' % (
                i, a['cross_section_range_L_median'], a['cross_section_range_L_p25'], a['tear_side_flank_L_median'],
                a['body_L_median']))
    return out or ['(not in frame)']


def make_arms(old, new):
    rows = []
    for prefix, ids, nm in (('Hand_L', ('Hand_L0', 'Hand_L1', 'Hand_L2'), 'LEFT hand'),
                            ('Hand_R', ('Hand_R0', 'Hand_R1', 'Hand_R2'), 'RIGHT hand')):
        r = []
        b0 = hand_box(old['key'], prefix, int(0.02 * old['key']['W']), 1.25)
        b1 = hand_box(new['key'], prefix, int(0.02 * new['key']['W']), 1.25)
        box = (min(b0[0], b1[0]), min(b0[1], b1[1]), max(b0[2], b1[2]), max(b0[3], b1[3]))     # same crop both sides
        for tag, d in (('round 6', old['key']), ('round 7', new['key'])):
            sc = min(2.0, 1100.0 / max(box[2] - box[0], 1))
            arms = A.arm_metrics(d)
            r.append((tile(d['img'], box, sc), 'KEY %s x%.1f  (%s)' % (nm, sc, tag), arm_lines(arms, ids)))
        rows.append(r)
    r = []
    b0 = hand_box(old['key'], 'Colossus_3', int(0.01 * old['key']['W']), 1.25)
    b1 = hand_box(new['key'], 'Colossus_3', int(0.01 * new['key']['W']), 1.25)
    box = (min(b0[0], b1[0]), min(b0[1], b1[1]), max(b0[2], b1[2]), max(b0[3], b1[3]))
    for tag, d in (('round 6', old['key']), ('round 7', new['key'])):
        sc = min(1.0, 1100.0 / max(box[2] - box[0], 1))
        arms = A.arm_metrics(d)
        r.append((tile(d['img'], box, sc), 'KEY Engel x%.2f  (%s)' % (sc, tag), arm_lines(arms, ('Colossus_3',))))
    rows.append(r)
    r = []
    for tag, d in (('round 6', old['U8fwd']), ('round 7', new['U8fwd'])):
        W = d['W']
        box = (int(0.18 * W), 40, int(0.82 * W), int(0.62 * d['H']))
        arms = A.arm_metrics(d)
        r.append((tile(d['img'], box, 0.9), 'U8 forward: the whips (%s)' % tag, arm_lines(arms, ('Hand_L1', 'Hand_R1'))))
    rows.append(r)
    return sheet('compare_r3_arms  -  AD round 3 item 2: wound rim + moon rim + translucency; coil grips, not claws',
                 rows, 'section range = p95 - p5 of L* across the arm (ID arc-fraction bands)  [>= 12];  '
                       'tear-side flank = the quarter of each section nearest the wound  [28-45 within 500 m of a lip]')


def grade_lines(d, tones, sea, mult):
    t = tones
    out = ['APL %s [32-36]   luma<12 %s %% [20-35]   top 18 %% sky L* p90 %s [<= 5]' % (t['APL'], t['luma_lt12_pct'], t.get('top18_sky_L_p90')),
           'band peak L* %s [26-28]   moon L* max %s [<= 82]   L*>90 outside the wound %s %%' % (
               t.get('band_peak_L'), t.get('moon_L_max'), t.get('L_gt90_outside_wound_pct')),
           'brightest 2000 px: centroid %s, in the wound %s %%' % (t.get('brightest2000_centroid'), t.get('brightest2000_in_wound_pct'))]
    if sea:
        out.append('moonward sea: p5 %s [<= 6]  p95 %s [>= 50]  local sd %s [>= 8]  moon path +%s L*' % (
            sea['moonward_p5_L'], sea['moonward_p95_L'], sea['moonward_local_sd_L'], sea['moon_path_minus_off_L']))
    if mult:
        out.append('multitude: %s members visible, %s >= 30 px tall [>= 60], %s %% of frame [>= 2], lean to wound %s' % (
            mult['members_visible'], mult['members_ge30px_tall'], mult['area_pct'], mult['lean_toward_wound']))
    return out


def make_grade(old, new):
    rows = []
    r = []
    for tag, d in (('round 6', old['key']), ('round 7', new['key'])):
        im = d['img'].resize((1240, int(1240 * d['H'] / d['W'])), Image.LANCZOS)
        r.append((im, 'KEY full frame (%s)' % tag, grade_lines(d, A.tone_metrics(d), A.sea_metrics(d), A.multitude_metrics(d))))
    rows.append(r)
    r = []
    for tag, d in (('round 6', old['key']), ('round 7', new['key'])):
        W, H = d['W'], d['H']
        box = (0, int(0.52 * H), int(0.5 * W), H)
        r.append((tile(d['img'], box, 1240 / (box[2] - box[0])), 'KEY moonward sea, lower left (%s)' % tag, []))
    rows.append(r)
    r = []
    for tag, d in (('round 6', old['U7']), ('round 7', new['U7'])):
        im = d['img'].resize((1240, int(1240 * d['H'] / d['W'])), Image.LANCZOS)
        t = A.tone_metrics(d)
        r.append((im, 'U7 (acceptance frame, generic shell) (%s)' % tag,
                  ['APL %s, through the glass %s [33-38]   luma<12 %s %%   band peak L* %s' % (
                      t['APL'], t.get('APL_through_glass'), t['luma_lt12_pct'], t.get('band_peak_L'))]))
    rows.append(r)
    return sheet('compare_r3_grade  -  AD round 3 item 3: key APL 32-36, void above, silver crests, one brightest point',
                 rows, 'left = round 6, right = round 7.  [brackets] = critique_awe_r3 §5 / AD targets.')


def main():
    old = {k: ld(F_OLD, n, k) for k, n in (('key', 'keyart_239'), ('U6', 'U6_approach'), ('U8fwd', 'U8_forward'),
                                            ('U7', 'U7_engelein'))}
    new = {k: ld(F_NEW, n, k) for k, n in (('key', 'keyart_239'), ('U6', 'U6_approach'), ('U8fwd', 'U8_forward'),
                                            ('U7', 'U7_engelein'))}
    for nm, fn in (('compare_r3_tear', make_tear), ('compare_r3_arms', make_arms), ('compare_r3_grade', make_grade)):
        im = fn(old, new)
        p = os.path.join(F_NEW, nm + '.png')
        im.save(p)
        print('wrote', p, im.size)


if __name__ == '__main__':
    main()
