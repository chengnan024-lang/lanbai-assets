# -*- coding: utf-8 -*-
"""v2.1 (final) ramp-law + flash checks on the MEASURED timeline (bible §1.8), per VIEW where a ramp is a single curve or a light source:
  any full-field rise <= 0.5 EV / 0.25 s, <= 1.0 EV / 1 s, <= 1.8 EV / 2 s; L = full-field mean relative luminance of the
  DISPLAYED frame (with bloom), EV = log2(max(L, 0.004)); darkening is free but counts as a flash; <= 2 flashes per 1 s.
Simulator and frames: the bible's own (bible_work/lutlib + scenes_v2 + the hue-mapped S3/S6/S8 mocks), corrected PPv2 maths
(EXPO_UP/DOWN w = dEV/(H - b)). Every event carries its timeline t from cues_v21.py. Writes v21/ramp_checks_v21.json."""
import os, sys, json, copy, math, time, numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
BW = os.path.abspath(os.path.join(HERE, '../../bible_work'))
sys.path.insert(0, HERE); sys.path.insert(0, BW)
from cues_v21 import T, D, MIRRORS, MIRROR_R1
os.chdir(BW)
from lutlib import ppv2, PROF, GF
import scenes_v2 as V, scenes_proc as SP
from scipy.ndimage import zoom, gaussian_filter
from PIL import Image
FLOOR = 0.004; LUMA = np.array([0.2126, 0.7152, 0.0722])
def relLpx(d): return ppv2.srgb_to_lin(np.clip(d, 0, 1)) @ LUMA
def relL(d): return float(relLpx(d).mean())
def apl(d): return float((np.clip(d, 0, 1) @ LUMA).mean() * 255)
def law(ts, L):
    ts = np.asarray(ts); ev = np.log2(np.maximum(np.asarray(L, float), FLOOR)); out = {}
    for win, lim in ((0.25, 0.5), (1.0, 1.0), (2.0, 1.8)):
        m = 0.0
        for i, t in enumerate(ts):
            j = np.searchsorted(ts, t + win, side='right') - 1
            m = max(m, float(ev[i:j + 1].max() - ev[i]))
        out['%.2fs' % win] = [round(m, 2), lim, 'PASS' if m <= lim + 1e-6 else 'FAIL']
    return out
def verdict(lw): return 'PASS' if all(v[2] == 'PASS' for v in lw.values()) else 'FAIL'
def lin_law(dEV, dur):
    """analytic: an EV-linear rise of dEV over dur seconds."""
    r = dEV / dur; out = {}
    for win, lim in ((0.25, 0.5), (1.0, 1.0), (2.0, 1.8)):
        m = min(dEV, r * win); out['%.2fs' % win] = [round(m, 2), lim, 'PASS' if m <= lim + 1e-6 else 'FAIL']
    return out
def lerp_prof(a, b, w):
    a, b = ppv2.full(a), ppv2.full(b); o = {}
    for k in a:
        if isinstance(a[k], dict): o[k] = {kk: (a[k][kk] + (b[k][kk] - a[k][kk]) * w if isinstance(a[k][kk], (int, float)) and not isinstance(a[k][kk], bool) else (b[k][kk] if w > 0.5 else a[k][kk])) for kk in a[k]}
        elif isinstance(a[k], (int, float)) and not isinstance(a[k], bool): o[k] = a[k] + (b[k] - a[k]) * w
        elif isinstance(a[k], (tuple, list)): o[k] = tuple(np.array(a[k]) + (np.array(b[k]) - np.array(a[k])) * w)
        else: o[k] = b[k] if w > 0.5 else a[k]
    return o
def with_dev(p, dEV):
    p = copy.deepcopy(ppv2.full(p)); b = p['postExposure']
    if dEV >= 0: w = dEV / (4 - b); p['postExposure'] = b + (4 - b) * w
    else: w = -dEV / (b + 4); p['postExposure'] = b + (-4 - b) * w
    return p, w
def chain_white(base, dEV, sat_w, bloom_w):
    p, w = with_dev(base, dEV)
    p['saturation'] = p['saturation'] + (GF['helpers']['WHITE_SAT']['ppv2']['saturation'] - p['saturation']) * sat_w
    WB = GF['helpers']['WHITE_BLOOM']['ppv2']['bloom']
    for k in ('intensity', 'threshold', 'softKnee', 'diffusion'): p['bloom'][k] = p['bloom'][k] + (WB[k] - p['bloom'][k]) * bloom_w
    return p, w
def sstep(x): x = np.clip(x, 0, 1); return x * x * (3 - 2 * x)
def small(img, f=0.5): return np.stack([zoom(img[..., c], f, order=1) for c in range(3)], -1)
FR = np.load('../lens_cine/mock/frames.npz')
def mock(key):
    a = FR[key]
    return np.stack([np.asarray(Image.fromarray(a[..., c].astype(np.float32), 'F').resize((SP.W, SP.H), Image.BILINEAR)) for c in range(3)], -1).astype(np.float64)
def gain_to_apl(scene, p, target):
    lo, hi = 0.05, 20.0
    for _ in range(40):
        g = math.sqrt(lo * hi)
        if apl(ppv2.render(scene * g, p, True)) < target: lo = g
        else: hi = g
    return scene * math.sqrt(lo * hi)
EV = []
def add(**kw):
    kw.setdefault('verdict', verdict(kw['law']) if 'law' in kw else 'PASS'); EV.append(kw)
    print('%-34s %-8s %s' % (kw['id'], kw['verdict'], kw.get('law', '')), flush=True)
t_start = time.time()
# ============================================================ 1. U4h touch the cloud: fog 0 -> 0.067, APL 34 -> 62 over 8 s EV-linear
d = 2.2 * math.log2(62 / 34.0)
add(id='U4h_touch_cloud', event='触云：雾 0 → 0.067，APL 34 → 62，EV 线性 8 s；天窗先白', anchor='U4h', t=[T['U4h'], T['U5']],
    method='analytic (EV-linear %.2f EV / 8 s)' % d, law=lin_law(d, 8.0))
# ============================================================ 2. U6k break-out: in-cloud APL floor + EXPO_UP +0.5 (0.6 s up, 3 s down), fog clears 2.5 s ease-out
S3 = gain_to_apl(small(mock('S3'), 0.5), PROF['S3'], 50.0)
def breakout(a_fog, rise):
    fog = gain_to_apl(np.ones_like(S3) * 0.2, PROF['S3'], a_fog)
    ts = np.arange(-0.5, 4.5, 0.05); L = []
    for t in ts:
        f = 1 - (1 - (1 - np.clip(t / 2.5, 0, 1)) ** 2) if t >= 0 else 1.0
        dv = 0.0 if t < 0 else (0.5 * min(t / rise, 1) if t < rise else 0.5 * max(0, 1 - (t - rise) / 3.0))
        p, w = with_dev(PROF['S3'], dv); L.append(relL(ppv2.render(f * fog + (1 - f) * S3, p, True)))
    return law(ts, L)
for a_fog, tag, role in ((58.0, 'U6k_breakout_cloudAPL58', 'spec (E13 floor)'), (62.0, 'U6k_breakout_cloudAPL62', 'spec (in-cloud 62)'),
                         (44.0, 'U6k_breakout_cloudAPL44_control', 'control: cloud allowed to go dark')):
    add(id=tag, event='破云：雾 2.5 s 散尽 + EXPO_UP +0.5 EV（0.6 s 升、3 s 降，w 0.102）；云中 APL %d' % a_fog, anchor='U6k', t=[T['U6k'], T['U6k'] + 3.6],
        method='sim (S3 mock @ APL 50, uniform cloud @ APL %d, PPv2 + bloom)' % a_fog, role=role, law=breakout(a_fog, 0.6),
        weight=round(with_dev(PROF['S3'], 0.5)[1], 3))
# ============================================================ 3. U6 moon road: 4 s wipe along the road, each pixel >= 2 s, area < 5%
add(id='U6_moon_road', event='月光之路铺开（沿路擦除 4 s，每像素 ≥ 2 s，面积 < 5%，比周围云顶亮 3–5 倍）', anchor='U6', t=[T['U6'], T['U6'] + 4.0],
    method='analytic upper bound: 5 pct of the frame going x5 in luminance -> full field <= log2(1 + 0.05*4) = %.2f EV total' % math.log2(1.2),
    law=lin_law(math.log2(1.2), 2.0))
# ============================================================ 4. U9 tube flash + LIP1 band (flash-count rule)
add(id='U9_tube_flash', event='管灯 150% 一闪（EXPO_UP +0.3 EV、0.2 s，w 0.062）→ 0.25 s 全灭；第 1 重光唇光带推迟到 180.15', anchor='U9',
    t=[T['U9'], T['U9'] + 0.45], method='analytic (+0.3 EV in 0.2 s) + flash count', law=lin_law(0.3, 0.2),
    weight=round(with_dev(PROF['S4'], 0.3)[1], 3), flashes_in_any_1s=2, flash_rule='<= 2 / s: tube blink (1) + LIP1 band at 180.15 (1) -> 2, at the limit; the 0.6 s delay keeps the band from riding the blink')
# ============================================================ 5. 4c: dial one step brighter, warm point growth
add(id='4c_dial_Lichtchen', event='表盘提亮一档（3 s 线性，屏幕 #E19867 → #F2B169，< 0.5% 画面）', anchor='ein Lichtchen', t=[196.1, 199.1],
    method='analytic local (full field < 0.02 EV)', law=lin_law(0.02, 3.0))
add(id='4c_warm_point', event='前方暖白点长大（U11 → 246.39，0.3° → 12°，自身遵守爬升律）', anchor='U11 → U12 − 2.25', t=[T['U11'], D['STILL']],
    method='analytic: APL 42 -> 55 over 44 s', law=lin_law(2.2 * math.log2(55 / 42.0), 44.0))
# ============================================================ 6. FLASH_TEAR, now ending on U12
fr = small(V.tear_inside('S4c'))
ts, L, ap = [], [], []
for t in np.arange(0, 0.51, 0.02):
    p, w = with_dev(PROF['S4c'], min(t / 0.4, 1.0) * 1.5); dd = ppv2.render(fr, p, True)
    ts.append(t); L.append(relL(dd)); ap.append(apl(dd))
add(id='U12_FLASH_TEAR', event='唯一授权闪光：+1.5 EV（0.4 s EV 线性 → 248.29，保持 0.1 s → 248.39，0.25 s 落入黑 → U12 248.64）', anchor='U12 − 0.75',
    t=[D['FLASH0'], T['U12']], method='sim (4c frame, S4c, bloom, no bloom override)', law=law(ts, L),
    verdict='AUTHORISED EXCEPTION', full_field_EV=round(math.log2(L[-1] / L[0]), 2), apl_before=round(ap[0]), apl_peak=round(ap[-1]),
    weight=round(with_dev(PROF['S4c'], 1.5)[1], 3), stillness=dict(from_t=D['STILL'], to_t=D['FLASH0'], seconds=round(D['FLASH0'] - D['STILL'], 2), rule='>= 1.5 s of no change before the flash', ok=D['FLASH0'] - D['STILL'] >= 1.5 - 1e-9),
    apl_peak_if_4c_ends_at_55=round(55 * ap[-1] / ap[0]), vr_peak_apl_ok=55 * ap[-1] / ap[0] <= 150)
# ============================================================ 7. black -> dawn: ONE EvOverlayAlpha curve, built for the BRIGHTEST view, rate-limited
# EvOverlayAlpha(x, Lfrom, Lto, Lscene, Lover) takes ONE scalar Lscene, so every direction runs the same alpha curve (only the start
# is staggered by direction). A view dimmer than the Lscene the curve was built for rises more slowly (L_v(t) = F + (L_v - F)(L_x - F)/(L_b - F),
# rate <= the built rate), so the curve is built for the brightest view and its duration follows from the rate:
# T = log2(L_extreme / 0.004) / 0.85 EV/s. Design extreme: the door / sun-sector view, APL 210 -> T_min 8.65 s; spec 8.7 s.
dawn = V.remapped_mock(mock('S6'), [(285, 330, 270, 0.62)]) * 0.6
Dd = ppv2.render(dawn, PROF['S6'], True); Lpx = relLpx(Dd); Lbar = float(Lpx.mean())
az, el = V.cam(0.0)
colL = Lpx.mean(0); az_sun = float(az[0, int(np.argmax(np.convolve(colL, np.ones(40) / 40, 'same')))])
RATE = 0.85
L_of = lambda a: (a / 255.0) ** 2.2
APL_EXT = 210.0; L_EXT = L_of(APL_EXT); T_DAWN_MIN = math.log2(L_EXT / FLOOR) / RATE; T_DAWN = 8.7
def overlay_alpha(x, Lb, L0=FLOOR):
    Lx = L0 * (Lb / L0) ** np.clip(x, 0, 1); return (Lb - Lx) / (Lb - L0)
def dawn_sim(S_el, S_sun, Dur, Lcurve, dt=0.02):
    t0 = S_el * np.clip((90 - el) / 90, 0, 1.1) + S_sun * np.exp(-((az - az_sun) / 30.0) ** 2)
    ts = np.arange(0, t0.max() + Dur + 0.5, dt); L = []
    for t in ts:
        a = overlay_alpha((t - t0) / Dur, Lcurve); L.append(float((Lpx * (1 - a) + FLOOR * a).mean()))
    return ts, L, float(t0.max() + Dur)
def view_rise(Lv, Lcurve, Dur, dt=0.01):
    ts = np.arange(-0.2, Dur + 0.5, dt); a = overlay_alpha(np.clip(ts / Dur, 0, 1), Lcurve); a = np.where(ts < 0, 1.0, a)
    return ts, Lv * (1 - a) + FLOOR * a
ts, L, tot = dawn_sim(2.0, 1.3, T_DAWN, L_EXT)
add(id='F0_dawn_forward', event='黑 → 晨：一条 EvOverlayAlpha 曲线按最亮的视向（车门 / 太阳扇区，APL %d）建，每方向 %.1f s（最少 %.2f s = log2(L/0.004)/0.85）；天窗 / 天顶先，地平线 +2.0 s，下方 +2.2 s，太阳扇区再 +1.3 s；总 %.1f s，落在 F0s' % (APL_EXT, T_DAWN, T_DAWN_MIN, tot),
    anchor='F0 + 2.5', t=[D['DAWN0'], round(D['DAWN0'] + tot, 2)], method='sim (S6 hue-mapped mock @ APL %d = the forward view, per-pixel overlay, curve built for APL %d)' % (round(apl(Dd)), APL_EXT),
    role='spec', law=law(ts, L), apl_end=round(apl(Dd)), total_s=round(tot, 2), T_per_direction=T_DAWN, T_min=round(T_DAWN_MIN, 2))
per = {}
for a_v in (110, 130, 150, 174, 200, 210):
    ts, L = view_rise(L_of(a_v), L_EXT, T_DAWN); per['APL %d' % a_v] = law(ts, L)
add(id='F0_dawn_per_view', event='晨：同一条曲线在每个视向（正前方 APL 110 → 车门 / 日侧云 APL 210）', anchor='F0 + 2.5', t=[D['DAWN0'], D['DAWN1']],
    method='sim (uniform view of the given APL under the spec curve)', role='spec', per_view=per,
    law={w: [max(per[k][w][0] for k in per), per['APL 110'][w][1], 'PASS' if all(per[k][w][2] == 'PASS' for k in per) else 'FAIL'] for w in per['APL 110']})
per = {}
for a_v in (110, 150, 174, 200):
    ts, L = view_rise(L_of(a_v), Lbar, 7.5); per['APL %d' % a_v] = law(ts, L)
add(id='F0_dawn_draft_curve_from_forward_mean_control', event='对照：v2.1 草稿（曲线按正前方平均亮度建、每方向 7.5 s），车门 / 日侧云视向', anchor='(draft)', t=None,
    method='sim (uniform views)', role='control (consistency B1)', per_view=per,
    law={w: [max(per[k][w][0] for k in per), per['APL 110'][w][1], 'PASS' if all(per[k][w][2] == 'PASS' for k in per) else 'FAIL'] for w in per['APL 110']})
ts, L, tot = dawn_sim(3.0, 1.0, 3.0, Lbar)
add(id='F0_dawn_v2_literal_control', event='对照：v2 写法（7 s 总长、每像素 ≥ 2 s）', anchor='(v2)', t=None, method='sim', role='control (E2)', law=law(ts, L))
add(id='F0_preroll', event='预滚：黑 #030409（L≈0.0013）→ 地板 0.004（1.5 s，低于地板，不计入；屏幕 luma ≈4 → ≈13）', anchor='F0 + 1.0', t=[T['F0'] + 1.0, D['DAWN0']], method='below the 0.004 floor by definition',
    law=lin_law(0.0, 1.5))
# ============================================================ 8. dawn -> sea-mirror local events
add(id='F0s_cloud_towers', event='云塔应答：三根云塔的冠 +0.7 EV（各 4 s，错开 1.5 s；每根 < 3% 画面）', anchor='F0s', t=[T['F0s'], 273.36],
    method='analytic: 3 x 3 pct of the frame x (2^0.7 - 1) -> full field <= %.2f EV' % math.log2(1 + 0.09 * (2 ** 0.7 - 1)), law=lin_law(math.log2(1 + 0.09 * (2 ** 0.7 - 1)), 4.0))
add(id='305.4_under_the_deck', event='出云盖：太阳被挡，APL 96 → 74（变暗，免费）', anchor='305.4（几何）', t=[305.4, 306.4], method='darkening is free', law=lin_law(0.0, 1.0))
d = 2.2 * math.log2(92 / 74.0)
add(id='F1b1_sun_returns', event='太阳从云盖远边下面重新出来：日盘 2.2 s 露全，APL 74 → 92；座椅上的金光带局部约 +3.3 EV（录像窗口 (a) 99–368 s 覆盖，前方 / 过道座椅 / 车门三个视向）', anchor='F1b1', t=[T['F1b1'], T['F1b1'] + 2.2],
    method='analytic (EV-linear %.2f EV / 2.2 s, disc emergence is ~linear in luminance -> bound by the mean rate x1.3); must be confirmed by the recording' % d, law=lin_law(d * 1.3, 2.2))
# ============================================================ 9. water entry at F2h
add(id='F2h_water_entry', event='入水：EXPO_DOWN −0.5 EV（0.3 s 降，w 0.156）→ 1 s 回；S6 → S7a 1.5 s（水线遮挡）', anchor='F2h', t=[T['F2h'], T['F2h'] + 1.3],
    method='analytic (recovery +0.5 EV in 1.0 s)', law=lin_law(0.5, 1.0), weight=round(-(-0.5) / (PROF['S7a']['postExposure'] + 4), 3))
# ============================================================ 10. 7c rose pre-payment (real start and end fog values)
deep = small(V.deep('S7b'))
def c7_frame(fill_hex): return deep * (1 - 0.55) + ppv2.hex_to_lin(fill_hex) * 0.55
APL_F8b = 20.0
A7_start = apl(ppv2.render(c7_frame('#3E2C2B'), PROF['S7b'], True))     # fog #2E2228 (fill #3E2C2B), window settled 897.96
A7_end = apl(ppv2.render(c7_frame('#4B312C'), PROF['S7b'], True))       # fog #3A2629 (fill #4B312C), 921.4
seg1 = 2.2 * math.log2(A7_start / APL_F8b) / 20.0; seg2 = 2.2 * math.log2(A7_end / A7_start) / (921.4 - 897.96)
add(id='7c_rose_prepay', event='7c 玫瑰预付：F8b 起雾 #04121E → #2E2228（20 s，897.96），F8c 起 → #3A2629（921.4）；APL %d → %d → %d' % (APL_F8b, round(A7_start), round(A7_end)),
    anchor='F8b → F9s', t=[T['F8b'], D['EXIT']], method='sim APLs (7b deep frame + rose fog fill at 55 pct, S7b) + EV-linear bound per segment',
    law=lin_law(max(seg1, seg2) * 2.0, 2.0), apl_897_96=round(A7_start, 1), apl_921_4=round(A7_end, 1), ev_per_s=[round(seg1, 3), round(seg2, 3)])
# ============================================================ 11. SEA EXIT: EXPO_DOWN pin, one EV-linear release cresting +0.5 EV on F9, 4 s decay
dusk = small(V.remapped_mock(mock('S8'), [(288, 335, 283, 0.62)]))
D8 = ppv2.render(dusk, PROF['S8'], True); L8 = relL(D8)
R = T['F9'] - D['EXIT']          # 6.75 s
for rose_hex, fillnote, role in (('#4B312C', '7c end #3A2629 (option a: the dark trough is kept)', 'spec'),
                                 ('#6C4643', 'draft 7c end #5A3A3E (option b, not adopted)', 'reference'),
                                 ('#392735', 'v2 fog #2A1E30', 'reference')):
    c7 = c7_frame(rose_hex)
    D7 = ppv2.render(c7, PROF['S7b'], True); L7 = relL(D7); dEV = math.log2(L8 / L7)
    ts = np.arange(-2.0, R + 4.0 + 1.0, 0.1); L = []; W = []; Hh = D8.shape[0]
    for t in ts:
        if t < 0: L.append(L7); W.append(0.0); continue
        dv = -dEV + (dEV + 0.5) * (t / R) if t <= R else 0.5 * max(0.0, 1 - (t - R) / 4.0)
        p, w = with_dev(lerp_prof(PROF['S7b'], PROF['S8'], float(sstep(t / 8.0))), dv); W.append(w)
        l = relLpx(ppv2.render(dusk, p, True))
        if t < 0.8: k = int(Hh * (1 - t / 0.8)); l = np.concatenate([relLpx(D7)[:k], l[k:]], 0)
        L.append(float(l.mean()))
    add(id='EXIT_F9s+0.5_%s' % rose_hex.strip('#'), event='出海 922.36：水线 0.8 s；EXPO_DOWN 钉住 %.2f EV → 一条 EV 线性的线 %.2f s 放开到 F9 上 +0.5 EV → 4 s 回 0（933.11）；S7b → S8 8 s smoothstep' % (dEV, R),
        anchor='F9s + 0.5 → F9', t=[D['EXIT'], round(T['F9'] + 4.0, 2)], method='sim (7b deep frame + rose fog %s -> S8 dusk mock, PPv2 + bloom, 0.8 s bottom-up waterline)' % rose_hex,
        role=role + ' · ' + fillnote, law=law(ts, L), apl_7c_end=round(apl(D7)), apl_dusk=round(apl(D8)), pin_EV=round(dEV, 2), w_pin=round(max(W[:25]), 3),
        w_crest=round(with_dev(PROF['S8'], 0.5)[1], 3), crest_on='F9 %.2f' % T['F9'],
        director_rule='dEV(t) = target(t) - scene(t): the line is TOTAL luminance; the sun disc (lower limb ~923.9, half at F9, full ~932.0) is inside it, never added on top')
# v2 as written (control): S7b -> S8 weight over 6 s, no pin
ts = np.arange(-1, 8, 0.1); L = []
c7 = c7_frame('#392735'); D7 = ppv2.render(c7, PROF['S7b'], True)
for t in ts:
    if t < 0: L.append(relL(D7)); continue
    l = relLpx(ppv2.render(dusk, lerp_prof(PROF['S7b'], PROF['S8'], min(t / 6, 1)), True))
    if t < 0.8: k = int(l.shape[0] * (1 - t / 0.8)); l = np.concatenate([relLpx(D7)[:k], l[k:]], 0)
    L.append(float(l.mean()))
add(id='EXIT_v2_as_written_control', event='对照：v2 写法（S7b → S8 weight 6 s，无钉住；亮度跳变来自 0.8 s 水线）', anchor='(v2)', t=None, method='sim', role='control (E3)', law=law(ts, L))
# ============================================================ 12. dusk: ceiling dissolve (per-pixel T = dEV_px / 0.85 >= 5 s, front 4 s)
pp = 2.2 * math.log2(138 / 36.0)
add(id='F10e_ceiling_dissolve', event='头顶的海溶化：前沿 4 s（956.36 → 960.36），每像素 EV 线性、时长 T = ΔEV_px / 0.85 = %.2f / 0.85 → 5.0 s（shader 两态都知道，真正逐像素）；天顶 ≈965.4 散尽；_OtherSky 0 → 1 8 s' % pp, anchor='F10e',
    t=[T['F10e'], 965.4], method='analytic: every pixel obeys the law -> the full field (a luminance-weighted mean of pixel rates, bounded by the fastest pixel) does too', law=lin_law(pp, 5.0))
add(id='F10e_ceiling_dissolve_4s_per_pixel_control', event='对照：若每像素只给 4 s', anchor='(control)', t=None, method='analytic bound', role='control', law=lin_law(pp, 4.0))
add(id='F12_sunline_collapse', event='日线 6 s 收成一点熄灭 → 蓝时 → 变暗（全是变暗，免费）', anchor='F12', t=[T['F12'], 1009.21], method='darkening is free', law=lin_law(0.0, 1.0))
# ============================================================ 13. F13 ignition: by SOURCE, not by exposure
# The frame goes from the 0.004 floor (#04060E sky, EV -7.97) to the lit star sea (EV -4.42): +3.55 EV full field (forward view).
# Point stars are ~1 pct of the full-frame light: switching ALL of them on in one frame (+ the 16 Tianwen stars) is +0.00 EV in every
# view (the dark sky plus every star is still under the 0.004 floor). The +3.55 EV is the diffuse Milky Way glow (_CubeB gain) and the
# sky base #04060E -> #08112A: those ride ONE source-gain line g(t) (0 -> 1), built for the extreme view so that view rises EV-linearly
# at 0.85 EV/s; every other view has more constant light per unit of glow and rises more slowly. No EXPO_DOWN pin (the draft's pin was
# solved on the forward view and left an up-view unpinned while the wave crossed it: consistency M1).
from starsea_views import starsea_parts
starsea = small(V.starsea('S9a')); dark = np.broadcast_to(SP.SL('#04060E', 'S9a'), starsea.shape).copy()
L_dark = relL(ppv2.render(dark, PROF['S9a'], True)); L_end = relL(ppv2.render(starsea, PROF['S9a'], True))
ts = np.arange(-0.5, 5.0, 0.02); L = []
for t in ts:
    g = 0.0 if t < 0 else (0.8 * t / 1.2 if t < 1.2 else min(1.0, 0.8 + 0.2 * (t - 1.2) / 3.0))
    L.append(relL(ppv2.render(dark * (1 - g) + starsea * g, PROF['S9a'], True)))
add(id='F13_galaxy_ignition_v2_wording_control', event='对照：v2 写法（银河 1.2 s 到 80%、再 3 s 补足，按亮度线性，不改曝光）', anchor='(v2)', t=None,
    method='sim (#04060E sky -> S9a star-sea frame, PPv2 + bloom)', role='control (v2 wording)', law=law(ts, L),
    ev_start=round(math.log2(max(L_dark, FLOOR)), 2), ev_end=round(math.log2(L_end), 2), dEV_full_field=round(math.log2(L_end / max(L_dark, FLOOR)), 2))
VIEWS9 = {'forward (pitch +6)': (6, 0), 'up (pitch +60)': (60, 0), 'overhead (pitch +85)': (85, 0), 'core (yaw -30, pitch +12)': (12, -30), 'down (pitch -60)': (-60, 0)}
PARTS9 = {}
for name, (pch, yw) in VIEWS9.items():
    c = starsea_parts('S9a', pch, yw); PARTS9[name] = {k: small(v) for k, v in c.items() if isinstance(v, np.ndarray)}
def Ld9(img): return relL(ppv2.render(img, PROF['S9a'], True))
# --- control: the draft's EXPO_DOWN pin, solved on the FORWARD view, seen by an UP view (waves from zenith / nadir, 1.2 s)
E0 = math.log2(max(L_dark, FLOOR)); E1 = math.log2(L_end)
def wave_cov(elv, t): return np.clip((t - (1.2 * np.clip(1 - np.abs(elv) / 90.0, 0, 1) - 0.3)) / 0.3, 0, 1)[..., None]
_, el_f = V.cam(6.0); el_f = zoom(el_f, 0.5, order=1); _, el_u = V.cam(60.0); el_u = zoom(el_u, 0.5, order=1)
cf = PARTS9['forward (pitch +6)']; cu = PARTS9['up (pitch +60)']
full_f = cf['dark'] + cf['lift'] + cf['glow'] + cf['stars']; full_u = cu['dark'] + cu['lift'] + cu['glow'] + cu['stars']
ts = np.arange(-0.3, 6.5, 0.05); Lu = []
for t in ts:
    if t < 0: Lu.append(Ld9(cu['dark'])); continue
    con_f = cf['dark'] * (1 - wave_cov(el_f, t)) + full_f * wave_cov(el_f, t); con_u = cu['dark'] * (1 - wave_cov(el_u, t)) + full_u * wave_cov(el_u, t)
    target = 2 ** (E0 + (E1 - E0) * np.clip((t - 1.2) / 4.2, 0, 1))
    if Ld9(con_f) <= target: dv = 0.0
    else:
        lo, hi = -4.29, 0.0
        for _ in range(14):
            m = (lo + hi) / 2
            if relL(ppv2.render(con_f, with_dev(PROF['S9a'], m)[0], True)) < target: lo = m
            else: hi = m
        dv = (lo + hi) / 2
    Lu.append(relL(ppv2.render(con_u, with_dev(PROF['S9a'], dv)[0], True)))
add(id='F13_draft_expo_pin_seen_looking_up_control', event='对照：草稿的做法（点燃波 1.2 s + EXPO_DOWN 按正前方截图钉住 → 4.2 s 放开）在抬头视向（pitch +60）看到的样子', anchor='(draft)', t=None,
    method='sim (wave-front content, Director pin solved on the forward view, applied to the up view; PPv2 + bloom)', role='control (consistency M1)', law=law(ts, Lu))
# --- spec: stars snap on at F13; glow + sky base on one source-gain line built for the extreme (forward) view, 4.2 s
T_IGN = 4.2
ce = PARTS9['forward (pitch +6)']; Ce = ce['dark'] + ce['stars']; Ge = ce['lift'] + ce['glow']
L0e = max(FLOOR, Ld9(Ce)); L1e = Ld9(Ce + Ge)
tg = np.arange(0, T_IGN + 0.001, 0.05); gcurve = []
for t in tg:
    tgt = L0e * (L1e / L0e) ** (t / T_IGN); lo, hi = 0.0, 1.0
    for _ in range(20):
        m = (lo + hi) / 2
        if Ld9(Ce + m * Ge) < tgt: lo = m
        else: hi = m
    gcurve.append((lo + hi) / 2)
gcurve = np.array(gcurve); per = {}
for name, c in PARTS9.items():
    ts = np.concatenate([np.arange(-0.5, 0, 0.05), tg, np.arange(T_IGN + 0.05, T_IGN + 1.0, 0.05)]); L = []
    for t in ts:
        if t < 0: L.append(Ld9(c['dark'])); continue
        L.append(Ld9(c['dark'] + c['stars'] + float(np.interp(t, tg, gcurve)) * (c['lift'] + c['glow'])))
    per[name] = law(ts, L)
snap = {name: round(math.log2(max(Ld9(c['dark'] + c['stars']), FLOOR)) - math.log2(max(Ld9(c['dark']), FLOOR)), 3) for name, c in PARTS9.items()}
add(id='F13_ignition_source_gain', event='银河点燃（定稿）：F13 那一帧所有星点（最亮 50 颗 ×4、银心的星、天问 16 颗星）以满亮度同时出现（全画面 +0.00 EV）；银河漫射（_CubeB 增益）与星空底 #04060E → #08112A 走一条光源增益线，按极端视向（正前方）EV 线性 %.1f s 涨满（1018.21 → %.2f）；不用 EXPO_DOWN' % (T_IGN, T['F13'] + T_IGN),
    anchor='F13', t=[T['F13'], round(T['F13'] + T_IGN, 2)], role='spec',
    method='sim (star-sea split into sources for five head directions; g(t) solved on the forward view; PPv2 + bloom)', per_view=per, star_snap_EV=snap,
    law={w: [max(per[k][w][0] for k in per), per['forward (pitch +6)'][w][1], 'PASS' if all(per[k][w][2] == 'PASS' for k in per) else 'FAIL'] for w in per['forward (pitch +6)']},
    g_curve=dict(t=[round(float(x), 2) for x in tg[::6]], g=[round(float(x), 4) for x in gcurve[::6]]), dEV_forward=round(math.log2(L1e / L0e), 2),
    director_rule='play the precomputed g(t) (no per-frame solve); calibrate C and G from two forward screenshots at F13 (stars only) and 1022.41 (full)')
# ============================================================ 14. mirror pulses (crossings 1-11) and the band rhythm (two phases)
climax = small(V.starsea('S9b', climax=True))
base = ppv2.render(climax, PROF['S9b'], True); p, w = with_dev(PROF['S9b'], 0.35); pk = ppv2.render(climax, p, True)
gaps = np.diff(MIRRORS); g1 = gaps[:9]; g2 = gaps[9:]
add(id='9c_mirror_pulses_1_to_11', event='镜子脉冲 +0.35 EV（0.08 s 入 / 0.35 s 出），第 1–11 面：' + ' / '.join('%.2f' % m for m in MIRRORS[:11]) + '；第 12 面（白的冲击）与第 13 面（剪 2）不加',
    anchor='穿越（两段：加速到 F15 tragen!，r = 1.3083；尾声三声钟）', t=[MIRRORS[0], MIRRORS[10]], method='sim (S9b climax frame) + analytic', law=lin_law(float(np.log2(relL(pk) / relL(base))), 0.08),
    weight=round(w, 3), full_field_EV=round(float(np.log2(relL(pk) / relL(base))), 2), b_t='S9a and S9b both +0.30 -> w constant',
    gaps=[round(float(g), 2) for g in gaps], phase1_gaps_non_increasing=bool(np.all(np.diff(g1) <= 1e-9)), phase1_min_gap=round(float(g1.min()), 2),
    coda_gaps=[round(float(g), 2) for g in g2], min_gap=round(float(gaps.min()), 2), no_pulse=[MIRRORS[11], MIRRORS[12]], white_from=D['WHITE0'])
# ============================================================ 15. the white: impact on mirror 12 + swell + plateau + overlay, ending on F16,
#                                                               WITH mirror 13's face emission (+3 EV over the swell and plateau)
# timeline (s after 1137.58): impact 0 -> 1.2 (+1.0 EV), swell 1.2 -> 7.2 (+2.4 EV, = 1144.78, the hush), plateau 7.2 -> 8.73 (1146.31),
# mask 8.73 -> 11.73 (F16). Mirror 13 (>= 2 km, filling the lower hemisphere) raises its face emission EV-linearly by +3 EV over
# 1.2 -> 8.73 (0.40 EV/s), never during the 1.2-s impact: the down view then reaches APL ~220 at the plateau, just under the white itself.
from starsea_views import starsea_parts
fr = small(V.starsea('S9b', climax=True))
_, el9f = V.cam(6.0); face_f = (zoom(el9f, 0.5, order=1) < -2.2)[..., None].astype(float)
K13 = 0.2 + 0.08 * 13; K12 = 0.2 + 0.08 * 12
cu = starsea_parts('S9b', 60.0, 0.0, climax=True)
sky_up = small(cu['dark'] + cu['lift'] + cu['glow'] + cu['stars'])
bronze = np.array([0.93, 0.86, 0.70])
refl_down = sky_up[::-1] * bronze                                  # a camera pitched -60 sees the mirror reflect a camera pitched +60, flipped
t_imp, t_sw, t_pl, t_mask = 1.2, 7.2, D['WHITE_MASK0'] - D['WHITE0'], T['F16'] - D['WHITE0']
Lw = float(ppv2.srgb_to_lin(np.array([0xE8, 0xF1, 0xF5]) / 255) @ LUMA)
def white_run(frame_at, dt=0.05):
    ts = np.arange(0, t_pl + 1e-9, dt); L = []; A = []
    for t in ts:
        dv = min(t / t_imp, 1.0) if t <= t_imp else (1.0 + (min(t, t_sw) - t_imp) / (t_sw - t_imp) * 1.4)
        bw = 0.5 * min(t / t_imp, 1) if t <= t_imp else 0.5 + 0.5 * min(1.0, (t - t_imp) / (t_sw - t_imp))
        x = np.clip((t - t_imp) / (t_pl - t_imp), 0, 1); e = K13 * 8 ** x
        p, w = chain_white(PROF['S9b'], dv, dv / 2.4, bw); dd = ppv2.render(frame_at(e), p, True)
        L.append(relL(dd)); A.append(apl(dd))
    e0 = math.log2(L[-1]); ts = list(ts)
    for t in np.arange(dt, t_mask - t_pl + 1e-9, dt): ts.append(t_pl + t); L.append(2 ** (e0 + (math.log2(Lw) - e0) * t / (t_mask - t_pl)))
    return ts, L, A
fwd = lambda e: fr * (1 - face_f) + fr * face_f * (1 + e) / (1 + K12)
dwn = lambda e: refl_down * (1 + e)
res = {}
for name, fn in (('forward (pitch +6; lower 40 pct = mirror 13 face)', fwd), ('down (pitch -60; all mirror 13 face)', dwn)):
    ts, L, A = white_run(fn); res[name] = (law(ts, L), round(A[0]), round(A[-1]))
    print('   ', name, res[name], flush=True)
ts, L, A = white_run(lambda e: fr)
add(id='9_to_10_white_no_mirror_term_reference', event='参考：同一时间表、不含第 13 面的自发光（草稿里仿真过的那一项）', anchor='mirror 12', t=None, method='sim (S9b climax frame)', role='reference', law=law(ts, L))
add(id='9_to_10_white', event='白：冲击从第 12 面穿越（1137.58，尾声最响的一下）起 1.2 s（→ +1.0 EV）+ 膨胀 6 s（→ +2.4 EV，1144.78 = 吸气开始）+ 保持 1.53 s + 遮罩 3 s EV 线性到 #E8F1F5；第 13 面镜面自发光 +3 EV 在 1138.78 → 1146.31 EV 线性（冲击里不升；保持时向下看 ≈ luma 220，不亮过白）；F16 遮罩全满同帧硬切 S10（剪 2）',
    anchor='mirror 12 → F16', t=[D['WHITE0'], T['F16']], role='spec', method='sim (S9b climax frame forward + a down view whose field is mirror 13; EXPO_UP + WHITE_SAT + WHITE_BLOOM, then overlay)',
    per_view={k: v[0] for k, v in res.items()}, apl_start={k: v[1] for k, v in res.items()}, apl_plateau={k: v[2] for k, v in res.items()},
    law={w: [max(res[k][0][w][0] for k in res), 0 if False else list(res.values())[0][0][w][1], 'PASS' if all(res[k][0][w][2] == 'PASS' for k in res) else 'FAIL'] for w in list(res.values())[0][0]},
    weights=dict(impact_end=round(with_dev(PROF['S9b'], 1.0)[1], 3), swell_end=round(with_dev(PROF['S9b'], 2.4)[1], 3)),
    white_hold_s=D['WHITE_HOLD'], white_hold_rule='peak #D7E3E8 / #E8F1F5 held F16 -> silence end <= 30 s; the ramp and the shrink do not count', white_hold_ok=D['WHITE_HOLD'] <= 30.0)
e_flat = lambda e: 1.0
ts = []; L = []
for t in np.arange(0, 1.2 + 1e-9, 0.05):
    x = t / 1.2; p, w = chain_white(PROF['S9b'], x * 1.0, x / 2.4, 0.5 * x); ts.append(t); L.append(relL(ppv2.render(dwn(K13 * 8 ** x), p, True)))
add(id='9_to_10_white_mirror13_in_impact_control', event='对照：v2 / 草稿写法（最后一面镜的自发光放在 1.2 s 冲击里，这里取 +3 EV），向下看', anchor='(draft)', t=None,
    method='sim (down view)', role='control (consistency M3)', law=law(ts, L))
add(id='10_to_11_cut', event='10 → 11 硬切 S11 + 填值；EXPO_UP +1.0 EV（w 0.241）与遮罩填值 × 2^−1.0 同帧 → 屏幕一码不动；之后 4 s 衰减（变暗）', anchor='静默结束',
    t=[D['SILENCE_END'], D['SILENCE_END'] + 8.0], method='analytic (fill compensation is exact: postExposure multiplies before the LUT)', law=lin_law(0.0, 1.0),
    weight=round(with_dev(PROF['S11'], 1.0)[1], 3))
# ============================================================ 16. second white: pre-roll to the floor, then ONE curve built for the DARKEST view
# The fill #A3B4BE (L 0.4415) is 6.79 EV above the 0.004 floor, so any view that starts at the floor (a side window into the night)
# needs T >= 6.79 / 0.85 = 7.99 s. 1.5 s pre-roll a: 0 -> a0 = 0.004 / L_fill (lifts sub-floor pixels to the floor: free), then
# a = a0 (L_fill / 0.004)^x over 8.0 s; windows first, the cabin 2 s later. Brighter views rise more slowly under the same curve.
fr = SP.road('S11', false=True); D11 = ppv2.render(fr, PROF['S11'], True); P11 = relLpx(D11); L11 = float(P11.mean())
Lw2 = float(ppv2.srgb_to_lin(np.array([0xA3, 0xB4, 0xBE]) / 255) @ LUMA)
az, el = V.cam(0.0)
win = (((el > -15) & (el < 18) & (az > -50) & (az < 25)) | ((az > 30) & (el > -10) & (el < 25))).astype(float)
win = gaussian_filter(win, 6.0)
PRE, T_W2, STAG = 1.5, 8.0, 2.0
a0 = FLOOR / Lw2
def a_w2(t, t0):
    x = np.clip((t - PRE - t0) / T_W2, 0, 1)
    return np.where(t < PRE, a0 * np.clip(t / PRE, 0, 1), a0 * (Lw2 / FLOOR) ** x)
def w2_frame(dt=0.02):
    t0 = STAG * (1 - win); ts = np.arange(0, PRE + STAG + T_W2 + 0.5, dt); L = []
    for t in ts:
        a = a_w2(t, t0); L.append(float((P11 * (1 - a) + Lw2 * a).mean()))
    return ts, L
ts, L = w2_frame()
add(id='11_to_12_second_white_forward', event='第二次白：1.5 s 预滚到 a₀ = 0.004 / L_fill，然后一条按最暗视向建的曲线 a = a₀·(L_fill/0.004)^x，每方向 8.0 s 到 #A3B4BE，车窗先、车厢晚 2 s；%.2f 遮罩全满同帧硬切 S12（剪 3）+ EXPO_UP +0.8（w 0.200）' % D['CUT3'],
    anchor='第 11 幕 +62 s', t=[D['W2_0'], D['CUT3']], method='sim (S11 false-wake frame @ APL %d, per-pixel overlay)' % round(apl(D11)), role='spec', law=law(ts, L),
    dEV=round(math.log2(Lw2 / L11), 2), T_min=round(math.log2(Lw2 / FLOOR) / RATE, 2))
per = {}
for Lv in (0.0005, 0.004, 0.0077, 0.0182, 0.05):
    ts = np.arange(0, PRE + T_W2 + 0.5, 0.01); a = a_w2(ts, 0.0); per['L %.4f' % Lv] = law(ts, Lv * (1 - a) + Lw2 * a)
add(id='11_to_12_second_white_per_view', event='第二次白：同一条曲线在每个视向（侧窗外的夜 L ≤ 0.004 → 正前方 L 0.018）', anchor='第 11 幕 +62 s', t=[D['W2_0'], D['CUT3']],
    method='sim (uniform views)', role='spec', per_view=per,
    law={w: [max(per[k][w][0] for k in per), per['L 0.0182'][w][1], 'PASS' if all(per[k][w][2] == 'PASS' for k in per) else 'FAIL'] for w in per['L 0.0182']})
per = {}
for Lv in (0.0005, 0.004, 0.0077, 0.0182):
    ts = np.arange(0, 7.0, 0.01); x = np.clip(ts / 6.5, 0, 1); Lx = L11 * (Lw2 / L11) ** x; a = (Lx - L11) / (Lw2 - L11)
    per['L %.4f' % Lv] = law(ts, Lv * (1 - a) + Lw2 * a)
add(id='11_to_12_draft_curve_from_forward_mean_control', event='对照：v2.1 草稿（曲线按正前方平均亮度建、每方向 6.5 s），侧窗视向', anchor='(draft)', t=None,
    method='sim (uniform views)', role='control (consistency B1)', per_view=per,
    law={w: [max(per[k][w][0] for k in per), per['L 0.0182'][w][1], 'PASS' if all(per[k][w][2] == 'PASS' for k in per) else 'FAIL'] for w in per['L 0.0182']})
add(id='12_shrink_into_tube', event='收缩进站台灯管 4 s，+0.8 EV 5 s 衰减（变暗）', anchor='%.2f' % D['S12_0'], t=[D['S12_0'], D['S12_0'] + 5.0], method='darkening is free', law=lin_law(0.0, 1.0))
add(id='12_notice_box_lamp', event='公告箱灯管 +95 s：一次“嗒”跌落 + 1.5 s 缓亮（箱内 170–190，< 2% 画面）', anchor='第 12 幕 +95 s', t=[round(D['S12_0'] + 95, 2), round(D['S12_0'] + 96.5, 2)],
    method='analytic local (one flash, full field < 0.05 EV)', law=lin_law(0.05, 1.5))
# ============================================================ 17. periodic light bands through the cabin (flash rule: <= 2 per second) + new local beats
lips = [T['LIP1'] + 0.6] + [T['LIP%d' % k] for k in range(2, 9)]
bands = dict(sodium_2=[25.0, 28.7, 31.9, 35.1, 38.3], lips_4c=[round(x, 2) for x in lips], shaft_7a=[T['F4p'], T['F3e1']],
             bronze_7b=[672.0, 677.1, 682.3, 687.4, 692.6, 697.7, 702.8, 708.0, 713.1, 718.3, 723.4, 728.6], mirrors_9c=MIRRORS)
mg = {k: round(float(np.diff(v).min()), 2) for k, v in bands.items()}
add(id='cabin_light_bands', event='穿过车厢的光带：钠灯 5 次、光唇 8 重（扫过 1.2 → 2.4 s；第 8 重是一段 85 m 的“袖”，光在整句长音里保持 6.25 s：一升一降相隔 6 s，不成闪烁对）、7a 两次光柱、铜灯 12 对、镜线 13 面', anchor='各自的乐句', t=[25.0, T['F16']],
    method='flash rule: every band >= 2.5 s apart (<= 0.4 per s, limit 2 per s)', law={'min_gap_s': [min(mg.values()), 2.5, 'PASS' if min(mg.values()) >= 2.5 else 'FAIL']},
    verdict='PASS' if min(mg.values()) >= 2.5 else 'FAIL', min_gaps=mg, times=bands)
add(id='F4p_shafts_converge', event='第一段合唱的女高音峰（462.36）：光柱在 ≈9 s 里汇成一束，从天窗的破洞落到座椅和手上（座椅 ≤ luma 120，≤ 6% 画面），F3e 前散尽', anchor='F4p',
    t=[453.4, T['F3e']], method='analytic local: 6 pct of the frame from luma 30 to 120 over 9 s', law=lin_law(math.log2(1 + 0.06 * ((120 / 30.0) ** 2.2 - 1)), 9.0))
add(id='F3e1_last_shaft', event='F3e1 斯涅尔之窗最后一闪：窗 8 s 缩暗成一枚暗币（变暗）；最后一道宽光柱 2 s 淡入、边走边扫过座椅（≤ luma 120，≤ 6% 画面）、2 s 淡出', anchor='F3e1',
    t=[T['F3e1'], T['F3e1'] + 8.0], method='analytic local: 6 pct of the frame from luma 30 to 120, fading in over 2 s', law=lin_law(math.log2(1 + 0.06 * ((120 / 30.0) ** 2.2 - 1)), 2.0))
add(id='F7p_palace_constellation', event='7b-iv 女高音峰（812.36）：车沉过台地边沿的下缘，30 盏宫灯同时出现在头顶（灯焰精灵，< 0.5% 画面）', anchor='F7p', t=[T['F7p'], T['F7p'] + 4.0],
    method='analytic local (full field < 0.05 EV)', law=lin_law(0.05, 4.0))
add(id='7a_sown_light', event='播种：每颗火花 0.2 s 诞生闪后留 12–15% 的恒定微光（≤ 3 cm、≥ 5 m、诞生闪任一 5° 锥内最多 1 个）；到 F5 约 200 个冷光点', anchor='F3i → F5', t=[T['F3i'], T['F5']],
    method='analytic local (each point < 0.001 pct of the frame)', law=lin_law(0.01, 1.0))
# ============================================================ summary
out = dict(about='蓝白 v2.1 · 爬升律与闪烁核查（实测时间轴）。t = 时间轴秒（cues.json）。law = [本事件任意窗口内的最大上升 EV, 上限, 结果]。control / fallback / reference 行不是规格，只作对照。',
           law='任意 0.25 s ≤ 0.5 EV、1 s ≤ 1.0 EV、2 s ≤ 1.8 EV（全画面平均相对亮度，含 bloom；EV = log2(max(L, 0.004))）',
           simulator='bible_work/lutlib + scenes_v2 + lens_cine/mock（与 ramp_checks_v2.json 同一模拟器）', runtime_s=round(time.time() - t_start, 1), events=EV)
spec = [e for e in EV if e.get('role', 'spec').startswith('spec') or 'role' not in e]
out['summary'] = dict(spec_events=len(spec), spec_pass=sum(e['verdict'] == 'PASS' for e in spec),
                      authorised_exception=[e['id'] for e in spec if e['verdict'] == 'AUTHORISED EXCEPTION'],
                      spec_fail=[e['id'] for e in spec if e['verdict'] == 'FAIL'],
                      controls_fail_as_expected=[e['id'] for e in EV if e.get('role', '').startswith('control') and e['verdict'] == 'FAIL'])
json.dump(out, open(os.path.join(HERE, '../ramp_checks_v21.json'), 'w'), ensure_ascii=False, indent=1)
print(json.dumps(out['summary'], ensure_ascii=False, indent=1))
