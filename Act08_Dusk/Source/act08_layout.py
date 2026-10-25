# -*- coding: utf-8 -*-
"""第 8 幕（暮 8-i → 8-ii → 8b 蓝时，922.36 → 1001.21；主光到 1149.31）的布局与时间：唯一的数据源 Act08_Dusk/Act08_Layout.json。
   ~/bpy/bin/python act08_layout.py            -> 写 JSON，打印检查（运动、日盘露出、云卡的角速度和禁区）

坐标：Unity 世界，米，车在原点、车头 +Z，眼 (0.55, 1.70, 2.05)。R_Dusk（第 8 幕的根）只做竖直平移：R_Dusk.y = h(t) =
车在出海平面下的深度（车往下掉 = 世界往上升）。R_Dusk 局部：出海平面（= 海之天花）在 y = 1.70（出海那一刻眼睛就在平面上）。
依据：圣经 v2.1 §6·8、§6·8b、§6.x #25–31、§2.2；裁决 D-00、D-09、D-17 #1、D-18、D-21、D-22、D-25、D-28 #5、D-33 #4 #6 #7a；
Engineering/README_集成.md §8（main）；Sea/README_Sea接口.md §2.4、§2.6、§4、§5；Sky/SkyPresets.json、FogPresets.json。
"""
import os
import sys
import json
import math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
CUES = json.load(open(os.path.join(REPO, 'FromLocal', 'cues.json')))
T = {k: v['t'] for k, v in CUES['F'].items()}
T.update({k: v['t'] for k, v in CUES['F_sub'].items()})
# v2.1 sub-labels not yet merged into cues.json (Engineering/cues_v21_patch.json; same values as fallbacks)
try:
    PATCH = json.load(open(os.path.join(REPO, 'Engineering', 'cues_v21_patch.json')))
    for k, v in PATCH.get('F_sub', {}).items():
        T.setdefault(k, v['t'])
except FileNotFoundError:
    pass
for k, v in (('F9s', 921.86), ('F9t', 937.26), ('F10e', 956.36), ('F10l', 961.06)):
    T.setdefault(k, v)
EXIT = round(T['F9s'] + 0.5, 2)                 # 922.36 出海
END8 = 1001.21                                   # 第 9 幕起点：t >= 1001.21 第 8 幕不再 Apply / ApplyBlend
END_LIGHT = T['F16']                             # 1149.31：主光到这里归第 8 幕（集成 §8.2；第 9 幕不写）
EYE = [0.55, 1.70, 2.05]

# ---------------------------------------------------------------- sun (bible §6·8: az 0, el +0.5; D-18 disc 0.53 deg)
SUN_AZ, SUN_EL, DISC_R = 0.0, 0.5, 0.265


def dir_az_el(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)])


SUN = dir_az_el(SUN_AZ, SUN_EL)

# ---------------------------------------------------------------- motion (bible §6·8 运动; dusk_motion_final.json is not in the repo:
# rebuilt from the bible's numbers, matches every beat of its table within 1 m)
V0 = -1.5                                        # vertical velocity of the bus at the exit (m/s, + = up)
SEGS = [(EXIT, 13.0, -1.5, -12.0),               # falls 1.5 -> 12 m/s (922.36 -> 935.36, peak 1.21 m/s^2)
        (T['F10'], 20.0, -12.0, 3.0),            # F10 the wings: -12 -> +3 (942.26 -> 962.26, peak 1.13; 0 at 956.52)
        (T['F12'], 8.0, 3.0, 0.0)]               # F12: the rise stops (987.06 -> 995.06, peak 0.56)


def _ss_int(x):
    return x ** 3 - 0.5 * x ** 4


def motion(t):
    """h = depth of the bus under the exit plane (m, >= 0), v = vertical velocity (+ up). Closed form."""
    t = float(t)
    if t <= EXIT:
        return 0.0, V0
    y = V0 * (t - EXIT)
    v = V0
    for t0, dur, v0, v1 in SEGS:
        if t <= t0:
            break
        x = min((t - t0) / dur, 1.0)
        y += (v1 - v0) * (dur * _ss_int(x) + max(t - t0 - dur, 0.0))
        v = v0 + (v1 - v0) * (3 * x * x - 2 * x ** 3)
    return -y, v


def accel(t, h=0.01):
    return (motion(t + h)[1] - motion(t - h)[1]) / (2 * h)


# ---------------------------------------------------------------- the sea ceiling (Sea/README_Sea接口 §2.4, §4 act 8)
CEIL = dict(y_local=EYE[1], inner_r=2300.0, centre=[0.0, 0.0], radius=2700.0, band=800.0,
            dissolve_t0=T['F10e'], dissolve_end=round(T['F10e'] + 9.0, 2), front_s=4.0, pixel_s=5.0,
            note='Sea_Ceiling.fbx under R_Dusk at local y = 1.70 (the exit plane). Inner -> M_08_SeaCeiling (opaque) until '
                 'F10e, then M_08_SeaCeilingFade; Edge -> M_08_SeaCeilingEdge. _DissolveTime = t - 956.36 on the three '
                 'materials (+ the palace points); renderers off from 965.36.')
SPECKS = dict(count=25, y_above=[40.0, 200.0], r_max=2000.0, flux=12.0, radius_m=2.0,
              colour_linear=[1.566, 0.616, 0.226], flicker=0.06, seed=8,
              note='PalaceSpecks: 20-30 golden palace points 40-200 m above the ceiling (Lanbai/SeaSpecks, _CeilingMode 1, '
                   'queue 2995; S8 gold #E0A860 = (1.566, 0.616, 0.226), flux x12, README_Sea接口 §2.6)')


def ceiling_alpha(d):
    """the edge material: 1 - smoothstep(r - band/2, r + band/2, d) (LanbaiSea.cginc)"""
    lo, hi = CEIL['radius'] - 0.5 * CEIL['band'], CEIL['radius'] + 0.5 * CEIL['band']
    x = np.clip((d - lo) / (hi - lo), 0, 1)
    return 1.0 - x * x * (3 - 2 * x)


def disc_reveal(t, n=24):
    """the visible fraction of the sun's disc under the ceiling's soft edge (area-weighted), before the dissolve. A ray at
    elevation e > 0 meets the ceiling plane (h above the eye) at horizontal distance h / tan(e): it is let through by
    1 - alpha(that distance)."""
    h = motion(t)[0]
    if t >= CEIL['dissolve_t0']:
        return 1.0
    xs = (np.arange(n) + 0.5) / n * 2 - 1
    X, Y = np.meshgrid(xs, xs)
    inside = X * X + Y * Y <= 1.0
    el = SUN_EL + DISC_R * Y[inside]
    with np.errstate(divide='ignore'):
        d = np.where(el > 0, h / np.tan(np.radians(np.maximum(el, 1e-6))), np.inf)
    trans = 1.0 - np.where(np.isfinite(d), ceiling_alpha(d), 0.0)
    return float(trans.mean())


def gap_deg(t):
    return math.degrees(math.atan(motion(t)[0] / CEIL['radius']))


# ---------------------------------------------------------------- the cards (Clouds_v2 v2 cards, D-25 channel format)
# Elevations are given at the reference depth H_REF (mid 8-ii, t ~ 971); local y = D tan(el) - H_REF + eye y. Nearest
# >= 600 m (bible: <= 0.29 deg/s at 3 m/s). Keep-outs: the sun line (|az| < 15, |el| < 3), the Zhuangzi block and its
# mirror (az +18 .. +52, |el| < 8: D-33 #7a, text at +21.8 .. +48.2, +-6.4).
H_REF = 220.0
UPPER = [  # id, card, az, D, el_at_href, width, gain, from (8-i / 8-ii)
    ('U01', 'CloudV2_Cumulus_duskU', -38.0, 7000.0, 2.5, 900.0, 1.0, '8i'),
    ('U02', 'CloudV2_Bank_duskU', -75.0, 9000.0, 1.2, 2400.0, 1.0, '8i'),
    ('U03', 'CloudV2_Strato_duskU', -120.0, 8000.0, 3.5, 1800.0, 1.0, '8i'),
    ('U04', 'CloudV2_Cumulus_duskU', -160.0, 6000.0, 2.0, 800.0, 1.0, '8i'),
    ('U05', 'CloudV2_Bank_duskU', 160.0, 10000.0, 1.0, 2600.0, 1.0, '8i'),
    ('U06', 'CloudV2_Strato_duskU', 120.0, 7500.0, 4.5, 1600.0, 1.0, '8i'),
    ('U07', 'CloudV2_Cumulus_duskU', 75.0, 6500.0, 2.2, 850.0, 1.0, '8i'),
    ('U08', 'CloudV2_Cumulus_duskU', -20.0, 11000.0, 5.5, 900.0, 0.95, '8i'),
    ('U09', 'CloudV2_Strato_duskU', 60.0, 9000.0, 7.0, 1500.0, 1.0, '8i'),
    ('U10', 'CloudV2_Cumulus_duskU', -95.0, 900.0, 3.6, 350.0, 1.0, '8ii'),     # the near ones read the rise (r1: base stays above the horizon to 995)
    ('U11', 'CloudV2_Cumulus_duskU', 110.0, 1200.0, 3.0, 450.0, 1.0, '8ii'),
]
LOWER = [  # the other sky's clouds: other variants, 70 % of the count, x 0.82 + tint (0.92, 0.95, 1.05); 8-ii only
    ('L01', 'CloudV2_Congestus_duskD', -50.0, 8000.0, -3.0, 1400.0),
    ('L02', 'CloudV2_Cumulus_duskD', -100.0, 900.0, -4.0, 350.0),      # r1: its top stays under the horizon from 956
    ('L03', 'CloudV2_Puff_duskD', -140.0, 6000.0, -1.5, 500.0),
    ('L04', 'CloudV2_Strato_duskD', 150.0, 9000.0, -4.0, 1800.0),
    ('L05', 'CloudV2_Cumulus_duskD', 95.0, 1300.0, -3.0, 450.0),
    ('L06', 'CloudV2_Congestus_duskD', 70.0, 10000.0, -1.2, 1500.0),
    ('L07', 'CloudV2_Strato_duskD', -25.0, 12000.0, -6.0, 1600.0),
]
BLUE_FADE = (0.4, 0.55)        # (final review A5) gain at the end, and the wb where it gets there (act08_blue.py)
BLUE_DESAT = 1.0               # chroma of the blue-hour card light (act08_blue.py)


def _desat(c, k):
    m = sum(c) / 3.0
    return [round(m + (v - m) * k, 5) for v in c]


def _other_tint():
    """(final review A6) the tint of the other sky's clouds is the sky's own: dusk_8ii `_OtherTint` in Sky/SkyPresets.json
    (read, not copied). It belongs to the dusk other sky only: the driver bakes it into the dusk colours, the blue hour
    lerps to the untinted blue colours (it goes with wb)."""
    sp = json.load(open(os.path.join(REPO, 'Sky', 'SkyPresets.json')))
    for p in sp['presets']:
        if p.get('name') == 'dusk_8ii' or p.get('presetName') == 'dusk_8ii' or p.get('id') == 'dusk_8ii':
            for e in p.get('vectors', []):
                if e.get('k') == '_OtherTint':
                    return [round(float(v), 4) for v in e['v'][:3]]
    raise SystemExit('Sky/SkyPresets.json: dusk_8ii _OtherTint not found')


OTHER = dict(gain=0.82, tint=_other_tint(), tint_source='Sky/SkyPresets.json dusk_8ii _OtherTint')
# r2 (director final review: "技术对、但不好看"): the FRONT, in three overlapping layers in the free spaces (outside the sun line
# and the Zhuangzi block), bigger toward the eye and smaller toward the horizon; a mass up-right and a different one down-right
# (weight balanced, not mirrored); a high thin layer catching the pink; near / upper cards keep their body and gold edge
# (_FogCap 0 near (D-42 #1; was 0.06) / 0.12 mid / 0.2 high: at 0.5-0.6 the 1.5-km fog (31 %) already reads pink; Docs~/iterations/03_fog_cap.png),
# only the far layer eats the fog. Opaque angular widths -> card widths (cards_v2 opaque_bbox_uv).
# (D-42 #1) the near layer's backlit body reads deep indigo (bible dusk cloud shadow #363D59): its sky / ground light
# (_SkyUpColor, _GroundColor; dusk part only, the blue hour lerps as before) x NEAR_AMB per group. Solved on the 971.4
# front frame with bloom (act08_shadow.py; Docs~/near_shadow.json); the sun term (the gold rims) and the mid / far layers
# untouched. The near layer's _FogCap goes 0.06 -> 0: 6 % of the bright pink fog on a body this dark was half the mauve
NEAR_AMB = dict(upper=[0.3, 0.7, 1.0], lower=[0.45, 0.8, 1.0])
FRONT = [  # id, card, az, D, el_at_href, opaque deg, group, show_from, fog_cap, layer
    ('F_N1', 'CloudV2_Cumulus_duskU', -30.0, 1500.0, 4.5, 16.0, 'upper', '8ii', 0.0, 'near'),
    ('F_N2', 'CloudV2_Bank_duskU', -22.0, 1900.0, 12.5, 14.0, 'upper', '8ii', 0.0, 'near'),   # final review A3: was az -9 (rel 9: aubergine h 312-323 over the line)
    ('F_N3', 'CloudV2_Cumulus_duskD', -24.0, 1400.0, -5.5, 13.0, 'lower', '8ii', 0.0, 'near'),
    ('F_M1', 'CloudV2_Cumulus_duskU', -42.0, 4000.0, 2.0, 9.0, 'upper', '8ii', 0.12, 'mid'),
    ('F_M2', 'CloudV2_Strato_duskU', 8.0, 4500.0, 4.0, 10.0, 'upper', '8ii', 0.12, 'mid'),
    ('F_M3', 'CloudV2_Puff_duskD', -12.0, 3500.0, -4.0, 6.0, 'lower', '8ii', 0.12, 'mid'),
    ('F_M4', 'CloudV2_Strato_duskD', 6.0, 4200.0, -4.5, 9.0, 'lower', '8ii', 0.12, 'mid'),
    ('F_R1', 'CloudV2_Bank_duskU', 32.0, 2500.0, 10.5, 14.0, 'upper', '8ii', 0.0, 'near-right'),
    ('F_R2', 'CloudV2_Congestus_duskD', 36.0, 2800.0, -11.0, 12.0, 'lower', '8ii', 0.0, 'near-right'),
    ('F_H1', 'CloudV2_Strato_duskU', -18.0, 6000.0, 10.0, 30.0, 'upper', '8ii', 0.2, 'high'),
    ('F_H2', 'CloudV2_Wisp_duskU', 18.0, 7000.0, 12.5, 22.0, 'upper', '8ii', 0.2, 'high'),
]
FRONT_MELT = [-0.04, 0.18, 0.0, 0.0]          # softer bases (the review: "ruler-straight bottoms")
CARDS_JSON = json.load(open(os.path.join(REPO, 'Clouds_v2', 'Textures', 'cards_v2.json')))['cards']


def width_for(card, D, deg):
    ob = CARDS_JSON[card]['opaque_bbox_uv']
    return round(2.0 * D * math.tan(math.radians(deg) / 2.0) / max(ob[2] - ob[0], 0.2), 1)
WISPS = [  # id, az, D, local y, drift m/s (tangential, + = toward +az)
    ('W01', -95.0, 450.0, -40.0, 5.0),
    ('W02', -70.0, 520.0, -110.0, 4.0),
    ('W03', 100.0, 480.0, -70.0, -5.0),
    ('W04', 125.0, 560.0, -150.0, -4.0),
]
WISP_CARD = 'CloudV2_Wisp_duskU'
WISP_FADE = [950.36, T['F10e']]                  # bible: no wisp passes once the transform begins


def keepout(az, el):
    a = ((az + 180) % 360) - 180
    if abs(a) < 15 and abs(el) < 3:
        return 'sun line'
    if 18 <= a <= 52 and abs(el) < 8:
        return 'Zhuangzi block (D-33 #7a)'
    return None


def card_entries():
    out = []
    for cid, card, az, D, el, w, g, frm in UPPER:
        a = math.radians(az)
        y = D * math.tan(math.radians(el)) - H_REF + EYE[1]
        out.append(dict(id=cid, card=card, group='upper', position_local=[round(D * math.sin(a), 1), round(y, 1), round(D * math.cos(a), 1)],
                        width_m=w, gain=g, show_from=frm, el_at_href=el, az=az, dist=D, keepout=keepout(az, el)))
    for cid, card, az, D, el, w in LOWER:
        a = math.radians(az)
        # the card's TOP sits at el (it is seen from above): pivot (cloud base) one card height below
        y = D * math.tan(math.radians(el)) - H_REF + EYE[1]
        out.append(dict(id=cid, card=card, group='lower', position_local=[round(D * math.sin(a), 1), round(y, 1), round(D * math.cos(a), 1)],
                        width_m=w, gain=OTHER['gain'], tint=OTHER['tint'], show_from='8ii', el_at_href=el, az=az, dist=D,
                        keepout=keepout(az, el), pivot='top'))
    for cid, card, az, D, el, deg, grp, frm, cap, layer in FRONT:
        a = math.radians(az)
        y = D * math.tan(math.radians(el)) - H_REF + EYE[1]
        e = dict(id=cid, card=card, group=grp, position_local=[round(D * math.sin(a), 1), round(y, 1), round(D * math.cos(a), 1)],
                 width_m=width_for(card, D, deg), gain=(OTHER['gain'] if grp == 'lower' else 1.0), show_from=frm, el_at_href=el,
                 az=az, dist=D, keepout=keepout(az, el), fog_cap=cap, melt=FRONT_MELT, layer=layer, opaque_deg=deg)
        if grp == 'lower':
            e.update(tint=OTHER['tint'], pivot='top')
        if layer.startswith('near'):
            e['amb'] = NEAR_AMB[grp]
        out.append(e)
    for e in out:
        # the card's top (local y): 8-i cards show only while it is under the gap's lower edge (review r2: not cut by the
        # ceiling's opaque depth), then come in with the dissolve
        cj = CARDS_JSON.get(e['card'])
        if cj:
            aspect = cj['size'][1] / cj['size'][0]
            hgt = (cj['opaque_bbox_uv'][3] - cj['cloud_base_v']) * aspect * e['width_m']
            e['top_y_local'] = round(e['position_local'][1] + (0.0 if e['group'] == 'lower' else hgt), 1)
        e.setdefault('fog_cap', 1.0)
        e.setdefault('melt', [-0.02, 0.10, 0.0, 0.0])
        e.setdefault('layer', 'far')
    return out


def wisp_entries():
    out = []
    for wid, az, D, y, v in WISPS:
        a = math.radians(az)
        out.append(dict(id=wid, card=WISP_CARD, group='wisp', position_local=[round(D * math.sin(a), 1), y, round(D * math.cos(a), 1)],
                        tangent=[round(math.cos(a), 4), 0.0, round(-math.sin(a), 4)], drift=v, width_m=260.0, gain=0.9))
    return out


# ---------------------------------------------------------------- the sky / fog / light schedule
def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def fog_density(t):
    """_Udon_Fog.x: water -> air (8 s smoothstep), 8-ii 0.00025 (F10e, 8 s), F12 -> 0 LINEAR, at 0 by 1001.21 (the bible's
    30 s fade would cross 1001.21, where act 9 writes 0 and blue_hour has 0: one writer, so it ends at 0 at 1001.21)"""
    if t < EXIT + 8.0:
        return 0.006 + (0.00015 - 0.006) * ss((t - EXIT) / 8.0)
    if t < T['F10e']:
        return 0.00015
    if t < T['F12']:
        return 0.00015 + (0.00025 - 0.00015) * ss((t - T['F10e']) / 8.0)
    return 0.00025 * max(0.0, 1.0 - (t - T['F12']) / (END8 - T['F12']))


def sun_line(t):
    """_Udon_SunDisc: (gain, radius, line half-length deg, 1). The line grows with the other sky (F10e, 8 s: the sun and its
    other self melt into one line), F12 collapses to a point and goes out in 6 s (bible §6·8b)."""
    z = 10.0 * ss((t - T['F10e'] - 3.0) / 5.0)
    k = 1.0 - ss((t - T['F12']) / 6.0)
    return [k, DISC_R, z * k, 1.0]


def light_E(t):
    return 2.2 * disc_reveal(t) * (1.0 - ss((t - T['F12']) / 6.0))


def main():
    ts = np.arange(EXIT, END_LIGHT + 0.01, 0.05)
    acc = np.array([accel(t) for t in ts if t < 1000])
    tab_t = np.arange(EXIT, T['F10e'] + 0.01, 0.1)
    reveal = [round(disc_reveal(t), 4) for t in tab_t]
    first = next(float(t) for t, r in zip(tab_t, reveal) if r > 0.01)
    half = next(float(t) for t, r in zip(tab_t, reveal) if r >= 0.5)
    full = next(float(t) for t, r in zip(tab_t, reveal) if r >= 0.99)
    cards = card_entries()
    # angular speed of each card at the +3 m/s rise and the peak fall (12 m/s), deg/s
    for c in cards:
        c['deg_per_s_rise'] = round(math.degrees(3.0 / c['dist']), 3)
    beats = dict(
        exit=EXIT, F9=T['F9'], F9t=T['F9t'], F9b=T['F9b'], F10=T['F10'], F10e=T['F10e'], F10l=T['F10l'], F11=T['F11'],
        F11b=T['F11b'], F12=T['F12'], blue=round(T['F12'] + 6.0, 2), end8=END8, end_light=END_LIGHT,
        sky=[dict(t0=EXIT, t1=T['F10e'], op='Apply', preset='dusk_8i'),
             dict(t0=T['F10e'], t1=T['F10e'] + 8.0, op='ApplyBlend', preset='dusk_8i', to='dusk_8ii', shape='smoothstep'),
             dict(t0=T['F10e'] + 8.0, t1=T['F12'], op='Apply', preset='dusk_8ii'),
             dict(t0=T['F12'], t1=T['F12'] + 6.0, op='ApplyBlend', preset='dusk_8ii', to='blue_hour', shape='smoothstep'),
             dict(t0=T['F12'] + 6.0, t1=END8, op='Apply', preset='blue_hour')],
        fog=dict(water=0.006, air=0.00015, ii=0.00025, note='see fog_density(): F12 -> 0 linear, 0 at 1001.21'),
        # review r1 B1: the line only grows once the two discs touch (the sun sinks first, 3 s), else 957.5 -> 961.5 shows
        # two parallel lines
        sun_line=dict(grow=[T['F10e'] + 3.0, T['F10e'] + 8.0, 10.0], collapse=[T['F12'], T['F12'] + 6.0]),
        # D-39 #2: ONE line: the sun sinks +0.5 -> 0 deg with the other sky (956.36 -> 964.36, 0.06 deg/s): it touches its
        # other self on the seam (the other sky samples (-x, -y, z): its sun is at -el), the two lines melt into one
        sun_sink=dict(t=[T['F10e'], T['F10e'] + 3.0], el=[SUN_EL, 0.0]),
        cards=dict(upper_8ii_in=[T['F10e'], T['F10e'] + 8.0], lower_in=[T['F10e'], T['F10e'] + 8.0],
                   blue=[T['F12'], T['F12'] + 6.0], dark=[END8, END8 + 8.0], wisp_out=WISP_FADE,
                   # (final review A5) F12: the cards dim as the light leaves and stay dim, no rebound: gain x lerp(1, g,
                   # smoothstep(0, w_end, wb)); the warm -> blue swing crosses the D-21 band under L* 40, and the blue-hour
                   # cards are no brighter than the sky at their elevation (act08_blue.py; Docs~/blue_cards.json)
                   blue_fade=list(BLUE_FADE)),
        light=dict(colour_srgb='#FFA642', E=2.2, floor=0.001, collapse=[T['F12'], T['F12'] + 6.0],
                   note='D-00: Inspector = E = 2.2 (the bible table 1.43 is the voided gamma value)'),
        trilight=dict(i=dict(sky='#1C3350', equator='#D08A70', ground='#4C5577'), ii_sky='#465582', ii=[T['F10e'], T['F10e'] + 8.0],
                      b=dict(sky='#26406E', equator='#4A5E8E', ground='#2A3050'), b_t=[T['F12'], T['F12'] + 8.0],
                      dark=[END8, END8 + 8.0, 0.03], note='9a: EV-linear to x 0.03 by 1009.21 (bible: 随变暗落到近零), held to 1149.31'),
        sea=dict(mode=3, ceiling_off=CEIL['dissolve_end'], refl_cube='Sea/Textures/Cube_DuskLower_256.exr (stand-in for ReflCube_DuskLower)'),
        poem=dict(L1=971.4, L3=976.4, out=[989.0, 993.0], az=35.0, block_az=[21.8, 48.2], block_el=[-6.4, 6.4],
                  note='the poem driver draws it; this act keeps the region clean (no cards / wisps / line crossing)'),
    )
    L = dict(
        about='蓝白 · 第 8 幕（暮 8-i → 8-ii → 8b 蓝时）布局与时间（Act08_Dusk/Source/act08_layout.py 生成，别手改）。Unity 世界、米；R_Dusk 只做竖直平移 y = h(t)。',
        version='v1 2026-10-24',
        labels={k: T[k] for k in ('F9s', 'F9', 'F9t', 'F9b', 'F10', 'F10e', 'F10l', 'F11', 'F11b', 'F12', 'F13', 'F16')},
        window=[EXIT, END_LIGHT], sky_window=[EXIT, END8], eye=EYE,
        sun=dict(az_deg=SUN_AZ, el_deg=SUN_EL, dir=[round(float(v), 6) for v in SUN], disc_radius_deg=DISC_R),
        motion=dict(v0=V0, segments=[dict(t0=a, dur=b, v0=c, v1=d) for a, b, c, d in SEGS],
                    h_at={k: round(motion(T[k] if k in T else v)[0], 1) for k, v in
                          (('F9', 0), ('F9t', 0), ('F9b', 0), ('F10', 0), ('F10e', 0), ('F11', 0), ('F12', 0), ('end8', END8))},
                    peak_accel=round(float(np.abs(acc).max()), 3), lowest=[956.52, round(motion(956.52)[0], 1)],
                    note='R_Dusk.y = h(t); closed form: y = v0 (t - exit) + sum (v1 - v0)(dur S(x) + max(t - t0 - dur, 0)), h = -y'),
        ceiling=CEIL, specks=SPECKS,
        reveal=dict(t0=float(tab_t[0]), dt=0.1, frac=reveal, first=round(first, 2), half=round(half, 2), full=round(full, 2),
                    note='the sun disc (0.53 deg, D-18) under the ceiling edge; the bible counted a 0.9 deg disc (923.9 -> 932.0)'),
        cards=cards, wisps=wisp_entries(), other=OTHER, beats=beats,
        # 8b: the sun is gone; the cards are lit by the blue-hour dome only (blue_hour zenith / nadir x 6, the same scale the
        # dusk solve lands on; D-25: colours per act, no re-bake)
        blue_colours=dict(SkyUpColor=_desat([0.0846, 0.1188, 0.306], BLUE_DESAT), GroundColor=_desat([0.0804, 0.1806, 0.594], BLUE_DESAT),
                          desat=BLUE_DESAT, note='blue_hour zenith / nadir x 6, chroma x desat (final review A5: C* <= the sky)'),
        tables=dict(t0=EXIT, dt=0.1,
                    h=[round(motion(t)[0], 2) for t in np.arange(EXIT, END8 + 0.05, 0.1)],
                    fog=[float('%.6g' % fog_density(t)) for t in np.arange(EXIT, END8 + 0.05, 0.1)]),
    )
    gp = os.path.join(KIT, 'Act08_Grade.json')            # act08_grade.py (the exit exposure line, measured on the references)
    if os.path.exists(gp):
        L['grade'] = json.load(open(gp))
    out = os.path.join(KIT, 'Act08_Layout.json')
    json.dump(L, open(out, 'w'), indent=1, ensure_ascii=False)
    print('h:', L['motion']['h_at'], 'lowest', L['motion']['lowest'], 'peak accel', L['motion']['peak_accel'])
    print('sun reveal first %.2f  half %.2f  full %.2f' % (first, half, full))
    print('gap at F9 %.2f  F9b %.2f  F10e %.2f deg' % (gap_deg(T['F9']), gap_deg(T['F9b']), gap_deg(T['F10e'])))
    bad = [(c['id'], c['keepout']) for c in cards if c['keepout']]
    # review r1: a card never crosses the horizon (the seam of the two skies) while it shows: the upper cards' base and the
    # lower cards' top (approx. top = base + 0.5 width for the cumulus shapes) over h(t) of their visible time
    cross = []
    for c in cards:
        t0 = T['F10e']                    # the seam exists from 8-ii (in 8-i the lower half is the mirrored dusk: far cards may rise through it)
        for t in np.arange(t0, END8, 0.5):
            h = motion(t)[0]
            y = c['position_local'][1] + h - EYE[1]
            if c['group'] == 'upper' and y < 0:
                cross.append((c['id'], round(float(t), 1))); break
            if c['group'] == 'lower' and y > 0:
                cross.append((c['id'], round(float(t), 1))); break
    print('cards crossing the horizon', cross)
    # the keep-outs over time (the cards slide with h(t)): sun line while it exists (to 993.06), the poem block 965.4 -> 993
    ko = []
    for c in cards:
        for t in np.arange(T['F10e'], 993.06, 0.5):
            h = motion(t)[0]
            el = math.degrees(math.atan((c['position_local'][1] + h - EYE[1]) / c['dist']))
            if c['group'] == 'lower':
                pass                               # el is the top for the lower cards (pivot moved by the builder)
            k = keepout(c['az'], el)
            if k == 'sun line' or (k and t >= 965.4):
                ko.append((c['id'], round(float(t), 1), k)); break
    print('keep-outs over time', ko)
    print('keep-out violations', bad, ' nearest card', min(c['dist'] for c in cards), 'm, fastest rise',
          max(c['deg_per_s_rise'] for c in cards), 'deg/s')


if __name__ == '__main__':
    main()
