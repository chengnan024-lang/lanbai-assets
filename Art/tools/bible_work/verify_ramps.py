"""v2 ramp-law checks with the corrected helper maths (EXPO_UP w = dEV/(4-b)) and real bloom.
Law: any full-field rise <= 0.5 EV / 0.25 s, <= 1.0 EV / 1 s, <= 1.8 EV / 2 s. VR peak APL <= 150 (whites excepted)."""
import copy, json, numpy as np
from lutlib import ppv2, PROF, GF
import scenes_v2 as V
from scipy.ndimage import zoom
def small(img, f=0.5): return np.stack([zoom(img[..., c], f, order=1) for c in range(3)], -1)
def relL(disp): return float((ppv2.srgb_to_lin(np.clip(disp, 0, 1)) @ [0.2126, 0.7152, 0.0722]).mean())
def apl(disp): return float((np.clip(disp, 0, 1) @ [0.2126, 0.7152, 0.0722]).mean() * 255)
def lerp(a, b, w): return a + (b - a) * w
def chain(base, dEV=0.0, sat_w=0.0, bloom_w=0.0):
    p = copy.deepcopy(ppv2.full(base))
    b = p['postExposure']; H = 4.0 if dEV >= 0 else -4.0
    w = dEV / (H - b) if dEV != 0 else 0.0
    p['postExposure'] = lerp(b, H, w)                      # PPv2 lerp to the absolute far target
    WS = GF['helpers']['WHITE_SAT']['ppv2']['saturation']
    p['saturation'] = lerp(p['saturation'], WS, sat_w)
    WB = GF['helpers']['WHITE_BLOOM']['ppv2']['bloom']
    for k in ('intensity', 'threshold', 'softKnee', 'diffusion'):
        p['bloom'][k] = lerp(p['bloom'][k], WB[k], bloom_w)
    return p, w
def law(ts, evs):
    ts, evs = np.array(ts), np.array(evs); out = {}
    for win, lim in ((0.25, 0.5), (1.0, 1.0), (2.0, 1.8)):
        m = 0
        for i, t in enumerate(ts):
            j = np.searchsorted(ts, t + win, side='right') - 1
            m = max(m, evs[i:j + 1].max() - evs[i])
        out['%.2fs' % win] = (round(m, 2), lim, 'PASS' if m <= lim + 1e-6 else 'FAIL')
    return out
res = {}
# ---- 1. the white: crash (1.2 s, +1.0 EV) + swell (6 s, to +2.4 EV) on the S9b climax frame, WHITE_SAT/WHITE_BLOOM with it
fr = small(V.starsea('S9b', climax=True))
ts, evs, apls = [], [], []
for t in np.arange(0, 7.21, 0.05):
    dEV = min(t / 1.2, 1.0) * 1.0 if t <= 1.2 else 1.0 + (t - 1.2) / 6.0 * 1.4
    f = dEV / 2.4
    bw = 0.5 * min(t / 1.2, 1) if t <= 1.2 else 0.5 + 0.5 * (t - 1.2) / 6.0
    p, w = chain(PROF['S9b'], dEV, f, bw)
    d = ppv2.render(fr, p, with_bloom=True)
    ts.append(t); evs.append(np.log2(max(relL(d), 0.004))); apls.append(apl(d))
# 3 s overlay EV-linear to the white (#E8F1F5 desktop); WHITE_BLOOM fades 1 -> 0 with it, so the overlay never blooms
Lw = float(ppv2.srgb_to_lin(np.array([0xE8, 0xF1, 0xF5]) / 255) @ [0.2126, 0.7152, 0.0722])
e0 = evs[-1]
for t in np.arange(0.05, 3.01, 0.05):
    ts.append(7.2 + t); evs.append(e0 + (np.log2(Lw) - e0) * t / 3.0)
res['white_9b_to_10'] = dict(law=law(ts, evs), ev_start=round(evs[0], 2), ev_swell_end=round(e0, 2), ev_white=round(np.log2(Lw), 2),
                             apl_start=round(apls[0]), apl_swell_end=round(apls[-1]),
                             weights=dict(crash_end=round(chain(PROF['S9b'], 1.0)[1], 3), swell_end=round(chain(PROF['S9b'], 2.4)[1], 3)))
# ---- 2. FLASH_TEAR at U12 on the 4c frame (lip 8): +1.5 EV in 0.4 s EV-linear, hold 0.1 s; no bloom override
fr = small(V.tear_inside('S4c'))
ts, evs, ap = [], [], []
for t in np.arange(0, 0.51, 0.02):
    dEV = min(t / 0.4, 1.0) * 1.5
    p, w = chain(PROF['S4c'], dEV)
    d = ppv2.render(fr, p, with_bloom=True)
    ts.append(t); evs.append(np.log2(max(relL(d), 0.004))); ap.append(apl(d))
res['flash_tear'] = dict(law=law(ts, evs), full_field_EV=round(evs[-1] - evs[0], 2), apl_before=round(ap[0]), apl_peak=round(ap[-1]),
                         weight=round(chain(PROF['S4c'], 1.5)[1], 3), note='the only authorised flash: exempt from the 0.25 s law by design; must stay <= +1.5 EV and APL <= 150 in VR')
# ---- 3. mirror pulse inside the x^2.5 ramp (mirror 9, b ~ S9b): +0.35 EV in 0.08 s
fr = small(V.starsea('S9b', climax=True))
base = ppv2.render(fr, PROF['S9b'], True)
p, w = chain(PROF['S9b'], 0.35); pk = ppv2.render(fr, p, True)
res['mirror_pulse'] = dict(weight=round(w, 3), full_field_EV=round(np.log2(relL(pk) / relL(base)), 2))
# ---- 4. break-out BEAT (S3, +0.5 EV in 0.4 s) and dusk-exit BEAT (S8, +0.8 EV at the end of the >= 6 s ramp)
for name, prof, ev, rise in (('beat_breakout_U6', 'S3', 0.5, 0.4), ('beat_dusk_exit', 'S8', 0.8, 2.0), ('beat_U9_tube', 'S4', 0.3, 0.2)):
    p, w = chain(PROF[prof], ev)
    res[name] = dict(weight=round(w, 3), ev=ev, rise_s=rise, ev_per_025s=round(ev * min(0.25 / rise, 1), 2))
p, w = chain(PROF['S7a'], -0.5); res['beat_down_water'] = dict(weight=round(w, 3))
json.dump(res, open('../ramp_checks_v2.json', 'w'), ensure_ascii=False, indent=1)
print(json.dumps(res, ensure_ascii=False, indent=1))
