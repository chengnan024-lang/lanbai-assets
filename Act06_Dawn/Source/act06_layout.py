# -*- coding: utf-8 -*-
"""第 6 幕（晨）的布局与时间：唯一的数据源 Act06_Dawn/Act06_Layout.json。
   ~/bpy/bin/python act06_layout.py            -> 写 JSON，打印检查（运动加速度、太阳遮挡时刻、各高度过窗的时刻）

坐标：Unity 世界，米，车在原点、车头 +Z。R_Dawn（第 6 幕的根）只做竖直平移：R_Dawn.y = d(t) = F0 起下降的距离
（世界往上升 = 车在下降）。R_Dawn 的局部坐标里：云原顶 −533、云盖底 −1134、海面按 F2h 交接对上（见 sea）。
依据：圣经 v2.1 §6·5→6、§6·6、§6.x；总导演裁决 D-09、D-12（晨日 +30° / +6°；天空预设用 HDRI 自己的 5.8°）、D-24、D-25（云唇）；
Engineering/README_集成.md §8；Act07_Sea/Act07_Layout.json handover（F2h 时水面在世界 y = 1.0）。
"""
import os
import json
import math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
CUES = json.load(open(os.path.join(REPO, 'FromLocal', 'cues.json')))
T = {k: v['t'] for k, v in CUES['F'].items()}
T.update({k: v['t'] for k, v in CUES['F_sub'].items()})
F_OFF = CUES['timeline']['F_offset']
for k, f in (('F0s', 26.0), ('F1c', 51.5), ('F1t', 61.0), ('F1b1', 78.0), ('F1b2', 88.0), ('F1z', 105.0)):
    T.setdefault(k, round(f + F_OFF, 2))          # bible §2.1 v2.1 sub-labels (file s + offset), not yet in cues.json
CUT1 = 248.64

# ---------------------------------------------------------------- sun (D-12; the sky preset's own elevation)
SUN_AZ, SUN_EL = 30.0, 5.8


def dir_az_el(az, el):
    a, e = math.radians(az), math.radians(el)
    return np.array([math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)])


SUN = dir_az_el(SUN_AZ, SUN_EL)

# ---------------------------------------------------------------- descent (bible §6·6 坠落速度)
# piecewise: constant, then smoothstep velocity segments (t0, duration, v0 -> v1)
V_START = 4.0
SEGS = [(257.64, T['F1'] - 257.64, 4.0, 25.0),           # 4 -> 25 m/s by F1 (peak 1.30 m/s^2)
        (T['F1'], 16.0, 25.0, 36.0),                      # 25 -> 36 (F1 -> F1 + 16)
        (327.26, T['F2h'] - 327.26, 36.0, 2.0)]           # 36 s brake to 2 m/s exactly at F2h (peak 1.42)


def _ss_int(x):
    """integral of smoothstep 3x^2 - 2x^3 from 0 to x"""
    return x ** 3 - 0.5 * x ** 4


def descent(t):
    """distance descended since F0 (m, > 0 = down) and the downward speed, closed form."""
    t = float(t)
    d = V_START * (t - T['F0'])
    v = V_START
    for t0, dur, v0, v1 in SEGS:
        if t <= t0:
            break
        x = min((t - t0) / dur, 1.0)
        d += (v1 - v0) * (dur * _ss_int(x) + max(t - t0 - dur, 0.0))
        v = v0 + (v1 - v0) * (3 * x * x - 2 * x ** 3)
    return d, v


def accel(t, h=0.01):
    return (descent(t + h)[1] - descent(t - h)[1]) / (2 * h)


# ---------------------------------------------------------------- the cloud body (R_Dawn local; one field: shader + numpy + sun table)
TOP, BOTTOM = -533.0, -1134.0                 # bible §6·6
SLOT = dict(axis_az=25.0, half_width=500.0, s0=-2200.0, s1=4000.0, soft=60.0,
            floor_top=-1100.0,                # the slot's thin misty floor (34 m): hides the sea until the bus exits at 305.4
            open_t0=T['F1'], open_t1=T['F1'] + 6.0)   # 峡口张开 at F1: the slot's top opens over 6 s (closed before F1)
EDGE = dict(r0=8200.0, r_sun=None, sun_lobe_deg=45.0, soft=180.0, wobble=350.0)   # r_sun solved below (F1b1)
LIP = dict(top=None, soft=40.0)               # solved below: the sun line from the slot floor at the slot's end


def solve_edges():
    """r_sun: the sun passes under the sunward edge exactly at F1b1; lip top: the sun line from the canyon bottom (the
    moment the bus leaves the deck) grazes the lip, so the sun sets behind it as the bus exits the deck."""
    d_b1 = descent(T['F1b1'])[0]
    drop = BOTTOM - (1.70 - d_b1)                     # how far the EYE is under the deck bottom at F1b1 (> 0)
    tan_el = math.tan(math.radians(SUN_EL))
    EDGE['r_sun'] = round(drop / tan_el, 1)
    LIP['top'] = round(BOTTOM + SLOT['s1'] * math.cos(math.radians(SUN_AZ - SLOT['axis_az'])) * tan_el, 1)
    return d_b1, drop


def _sig(x):
    """1 / (1 + exp(x)), overflow-safe"""
    return 1.0 / (1.0 + math.exp(max(min(x, 60.0), -60.0)))


def region(x, z):
    """(in_deck 0..1, in_slot 0..1, in_lip 0..1) at local xz (soft)."""
    r = math.hypot(x, z)
    az = math.degrees(math.atan2(x, z))
    da = ((az - SUN_AZ + 180) % 360) - 180
    w = math.exp(-(da / EDGE['sun_lobe_deg']) ** 2)
    R = EDGE['r0'] + (EDGE['r_sun'] - EDGE['r0']) * w
    deck = _sig((r - R) / (0.25 * EDGE['soft']))
    a = math.radians(SLOT['axis_az'])
    s = x * math.sin(a) + z * math.cos(a)             # along the axis
    q = x * math.cos(a) - z * math.sin(a)             # across (+ = right of the axis)
    inw = _sig((abs(q) - SLOT['half_width']) / (0.25 * SLOT['soft']))
    inl = _sig((SLOT['s0'] - s) / (0.25 * SLOT['soft']))
    slot = inw * inl * _sig((s - SLOT['s1']) / (0.25 * SLOT['soft']))
    lip = inw * _sig((SLOT['s1'] - s) / (0.25 * LIP['soft']))
    return deck, slot, lip


def occupied(p):
    """Is the local point inside cloud (open slot, smooth macro relief ignored: the sun table works on the mean body)?"""
    deck, slot, lip = region(p[0], p[2])
    if deck < 0.5:
        return False
    top = TOP
    if lip > 0.5:
        top = LIP['top']
    if slot > 0.5:
        top = SLOT['floor_top']
    return BOTTOM < p[1] < top


def sun_visible(t, step=10.0):
    """1 = the sun line from the eye is clear of the cloud body, 0 = blocked (mean body, no relief)."""
    d = descent(t)[0]
    eye = np.array([0.55, 1.70 - d, 2.05])            # in R_Dawn local
    s = 0.0
    while s < 30000.0:
        p = eye + SUN * s
        if p[1] > TOP + 50:
            return 1.0
        if occupied(p):
            return 0.0
        s += step
    return 1.0


# ---------------------------------------------------------------- cards (Clouds_v2 v2 cards; billboards about the cloud base)
CARD_SETS = [
    # (id, card, az deg, dist m, width m, base y local, gain, role)
    ('Tower_A', 'CloudV2_Congestus_dawn', -25.0, 7500.0, 2200.0, TOP + 40.0, 1.0, 'tower'),      # the big one (bible)
    ('Tower_B', 'CloudV2_Congestus_dawn', 75.0, 9000.0, 1700.0, TOP + 40.0, 0.95, 'tower'),
    ('Tower_C', 'CloudV2_Congestus_dawn', 120.0, 10500.0, 1800.0, TOP + 40.0, 0.92, 'tower'),
    ('Tower_D', 'CloudV2_Bank_dawn', -70.0, 9500.0, 2600.0, TOP + 30.0, 0.9, 'tower'),
    ('Tower_E', 'CloudV2_Congestus_dawn', 200.0, 11000.0, 1500.0, TOP + 40.0, 0.9, 'tower'),
    ('Head_01', 'CloudV2_Cumulus_dawn', -40.0, 3200.0, 520.0, TOP + 10.0, 1.0, 'head'),
    ('Head_02', 'CloudV2_Puff_dawn', -5.0, 2600.0, 300.0, TOP + 8.0, 1.0, 'head'),
    ('Head_03', 'CloudV2_Cumulus_dawn', 60.0, 3600.0, 560.0, TOP + 10.0, 1.0, 'head'),
    ('Head_04', 'CloudV2_Bank_dawn', 100.0, 4200.0, 1100.0, TOP + 8.0, 1.0, 'head'),
    ('Head_05', 'CloudV2_Puff_dawn', 150.0, 3000.0, 320.0, TOP + 8.0, 1.0, 'head'),
    ('Head_06', 'CloudV2_Cumulus_dawn', 185.0, 3800.0, 600.0, TOP + 10.0, 1.0, 'head'),
    ('Head_07', 'CloudV2_Strato_dawn', 230.0, 3400.0, 900.0, TOP + 5.0, 1.0, 'head'),
    ('Head_08', 'CloudV2_Puff_dawn', 270.0, 2800.0, 280.0, TOP + 8.0, 1.0, 'head'),
    ('Head_09', 'CloudV2_Cumulus_dawn', 310.0, 3500.0, 540.0, TOP + 10.0, 1.0, 'head'),
    ('Head_10', 'CloudV2_Bank_dawn', -100.0, 5200.0, 1300.0, TOP + 8.0, 1.0, 'head'),
]
RING = dict(card='CloudSeaV2_1_dawn', alt_card='CloudSeaV2_2_dawn', count=10, radius=13000.0, width=9000.0,
            top_el_deg=-0.4, gain=0.95)        # the horizon ring beyond the deck: the deck's far continuation, hides the far sea


def card_entries():
    out = []
    for cid, card, az, dist, width, base_y, gain, role in CARD_SETS:
        a = math.radians(az)
        rel = abs(((SUN_AZ - az + 180) % 360) - 180)
        out.append(dict(id=cid, card=card, role=role, position_local=[round(dist * math.sin(a), 1), round(base_y, 1),
                        round(dist * math.cos(a), 1)], width_m=width, gain=gain, alpha=1.0,
                        mirror=(1 if abs(rel) < 8 else 2), sun_rel_az_deg=round(rel, 1),
                        melt=[-0.02, 0.10, 0.0, 0.0]))
    return out


def ring_entries():
    out = []
    n = RING['count']
    for i in range(n):
        az = i * 360.0 / n
        a = math.radians(az)
        R = RING['radius']
        out.append(dict(id='Ring_%02d' % i, card=RING['card'] if i % 2 == 0 else RING['alt_card'], role='ring',
                        position_local=[round(R * math.sin(a), 1), None, round(R * math.cos(a), 1)],
                        width_m=RING['width'], gain=RING['gain'], alpha=1.0, mirror=2, top_el_deg=RING['top_el_deg']))
    return out


# ---------------------------------------------------------------- beats & curves (bible §6·6 节拍, §6.x #18–23)
def beats():
    return dict(
        apply_sky_t=CUT1, preroll_t0=T['F0'] + 1.0, dawn_t0=round(T['F0'] + 2.5, 2), dawn_t1=round(T['F0'] + 2.5 + 3.5 + 8.7, 2),
        dawn_per_dir_s=8.7, stagger=dict(skylight_zenith=0.0, horizon=2.0, below=2.2, sun_sector=3.5),
        sun_sector=dict(az=SUN_AZ, half_width_deg=30.0, soft_deg=30.0),
        main_light_t0=252.64, main_light_t1=363.615, render_settings_t0=252.64, render_settings_t1=362.26,
        tower_answer=[dict(id='Tower_A', t0=T['F0s'], dur=4.0, dev=0.7), dict(id='Tower_B', t0=round(T['F0s'] + 1.5, 2), dur=4.0, dev=0.7),
                      dict(id='Tower_C', t0=round(T['F0s'] + 3.0, 2), dur=4.0, dev=0.7)],
        cabin_bleach=dict(t0=T['F0'], t1=T['F1'], v0=0.0, v1=0.10),
        slot_open=[SLOT['open_t0'], SLOT['open_t1']],
        ring_off=dict(t0=T['F1'] + 4.0, t1=T['F1'] + 8.0, note='fades as the slot walls rise past the windows (occluded)'),
        sea_on=300.0,               # the sea renderer: on only from inside the canyon (occluded); bible: no sea before 305.4
        sea_calm_patch=dict(t0=T['F1b2'], dur=6.0, radius=300.0),
        sea_calm_all=dict(t0=337.0, dur=8.0, v1=0.85),
        entry=T['F2h'])


def main():
    d_b1, drop = solve_edges()
    sea_entry_world_y = 1.0                       # Act07_Layout handover.plane_y_at_entry
    d_f2h = descent(T['F2h'])[0]
    sea_local = sea_entry_world_y - d_f2h
    ts = np.arange(CUT1, T['F2h'] + 0.36, 0.05)
    acc = np.array([accel(t) for t in ts])
    # key moments
    def t_at_depth(y_local):
        lo, hi = CUT1, T['F2h'] + 1
        for _ in range(60):
            m = 0.5 * (lo + hi)
            if 1.70 - descent(m)[0] > y_local:
                lo = m
            else:
                hi = m
        return round(0.5 * (lo + hi), 2)
    sun_tab_t = np.arange(CUT1, T['F2h'] + 0.4, 0.25)
    sun_tab = [sun_visible(t) for t in sun_tab_t]
    changes = [(round(float(sun_tab_t[i]), 2), sun_tab[i]) for i in range(1, len(sun_tab)) if sun_tab[i] != sun_tab[i - 1]]
    L = dict(
        about='蓝白 · 第 6 幕（晨）布局与时间（Act06_Dawn/Source/act06_layout.py 生成，别手改）。Unity 世界、米；R_Dawn 只做竖直平移 y = d(t)。',
        version='v1 2026-10-24',
        labels={k: T[k] for k in ('F0', 'F0s', 'F1', 'F1c', 'F1t', 'F1b1', 'F1b2', 'F1z', 'F2', 'F2h')}, cut1=CUT1,
        window=[CUT1, 363.62],
        eye=[0.55, 1.70, 2.05],
        sun=dict(az_deg=SUN_AZ, el_deg=SUN_EL, dir=[round(float(v), 5) for v in SUN],
                 color_srgb='#FFC47A', E=3.0, note='D-12 az +30; el 5.8 = the sky preset / HDRI sun (Sky/README_Sky §8 #5)'),
        motion=dict(v_start=V_START, segments=[dict(t0=a, dur=round(b, 3), v0=c, v1=e) for a, b, c, e in SEGS],
                    d_at=dict(F1=round(descent(T['F1'])[0], 2), F1b1=round(d_b1, 2), F2h=round(d_f2h, 2)),
                    peak_accel=round(float(np.abs(acc).max()), 3),
                    note='R_Dawn.y = d(t); closed form: d = v_start (t - F0) + sum (v1 - v0) (dur S(x) + max(t - t0 - dur, 0)), S(x) = x^3 - x^4 / 2'),
        body=dict(top=TOP, bottom=BOTTOM, slot=SLOT, lip=LIP, edge=EDGE,
                  note='one field: Lanbai/CloudPlain (shader), Source/plain_ref.py (numpy), sun_visible() here'),
        sea=dict(level_local=round(sea_local, 3), entry_world_y=sea_entry_world_y, first_seen_t=t_at_depth(BOTTOM),
                 note='Sea_Disc under R_Dawn at y = level_local: world y = 1.0 exactly at F2h (Act07 handover)'),
        moments=dict(enter_plain_top=t_at_depth(TOP), leave_deck_bottom=t_at_depth(BOTTOM), sun_changes=changes),
        sun_table=dict(t0=float(sun_tab_t[0]), dt=0.25, vis=sun_tab,
                       smoothing_s=2.2, note='driver: sun light x smoothstep over 2.2 s around each change (日盘约 2.2 秒露全)'),
        cards=card_entries(), ring=ring_entries(), beats=beats(),
        light=dict(trilight_srgb=dict(sky='#5A78B8', equator='#C8B4B8', ground='#8FA0BE'), cabin_ambient='#98A4B8',
                   cabin_ambient_k=0.5, sun_occluded_floor=0.1),
        fog=dict(density=0.00012, color_note='LanbaiFog from the dawn sky preset (Sky/FogPresets.json dawn)'),
    )
    out = os.path.join(KIT, 'Act06_Layout.json')
    json.dump(L, open(out, 'w'), indent=1, ensure_ascii=False)
    print('d(F1) %.1f  d(F1b1) %.1f  d(F2h) %.1f  peak accel %.3f' % (descent(T['F1'])[0], d_b1, d_f2h, np.abs(acc).max()))
    print('edge r_sun %.0f  lip top %.0f  sea local %.1f' % (EDGE['r_sun'], LIP['top'], sea_local))
    print('enter plain top %.2f  leave deck bottom %.2f' % (t_at_depth(TOP), t_at_depth(BOTTOM)))
    print('sun changes', changes)


if __name__ == '__main__':
    main()
