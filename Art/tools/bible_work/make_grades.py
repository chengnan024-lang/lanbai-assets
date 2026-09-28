"""Resolved PPv2 profiles for the ART BIBLE v2.
Start: lens_cine/grades.json -> v1 changes -> v2 changes (critique_awe + critique_feasibility). Writes ../grades_final.json.
Bloom thresholds are SOLVED, not typed: for every scene profile the knee start T0 = GammaToLinearSpaceExact(threshold) * (1 - softKnee)
(scene-linear, BEFORE postExposure, which is how PPv2 Bloom.cs + Uber.shader work) is placed where a neutral grey displays at luma 228.
So nothing that displays <= luma ~225 (skies, clouds, text, lit surfaces) ever blooms; only emitters and speculars do."""
import json, copy, sys
import numpy as np
sys.path.insert(0, '../lens_cine')
import ppv2
from lutlib_core import patch_ppv2, g2l, l2g
patch_ppv2(ppv2)

G = json.load(open('../lens_cine/grades.json'))
F = copy.deepcopy(G)
F['_about'] = ("Lanbai ART BIBLE v2 resolved grade set. Colour Grading mode = High Definition Range, Tonemapper = Neutral in EVERY "
               "profile. Trackballs = PPv2 Vector4 (x,y,z wheel colour, max channel 1; w = offset). Every scene profile overrides the "
               "SAME full parameter set. Scene crossfade: incoming (higher priority) 0->1 while outgoing stays 1, then outgoing -> 0. "
               "PPv2 OVERRIDES ARE ABSOLUTE: param = lerp(current, override, weight). Helpers therefore carry FAR targets and the "
               "Director solves their weight every frame (see helpers._how).")
LIFT_NIGHT = [0.9875, 0.9905, 1, 0.008]
DISPLAY_T0 = 228          # luma at which bloom starts (neutral grey), every scene profile
CLAMP_GAMMA = 4.24        # PPv2 converts clamp with GammaToLinearSpace: 4.24 -> 24.0 linear

F['common']['bloom']['fastMode'] = True
F['common']['bloom']['clamp'] = CLAMP_GAMMA
F['common']['bloom']['_clamp_note'] = "clamp is gamma-space in PPv2: 4.24 = 24 scene-linear (v1 wrote 24 = 1,088 linear)"
P = F['profiles']
# ---- v1 changes (kept)
for k in ('S1', 'S2', 'S11', 'S12'):
    P[k]['ppv2']['temperature'] = -4
P['S11']['name'] = '假醒 false awakening (= S2 exactly: normality is the lie)'
new = {}
for k, v in P.items():
    new[k] = v
    if k == 'S4':
        new['S4c'] = {"priority": 5, "name": "门内 inside the tear (dark grace; the dye thins)",
                      "ppv2": {"postExposure": -0.9, "temperature": -3, "tint": 2, "saturation": -14, "contrast": 6,
                               "lift": [0.99, 0.99, 1, 0.004], "gamma": [0.985, 0.98, 1, 0], "gain": [1, 0.99, 1, 0],
                               "bloom": {"intensity": 6, "threshold": 1.0, "softKnee": 0.7, "diffusion": 9, "color": "#F2F3F6"}}}
F['profiles'] = P = new
P['S8']['ppv2']['saturation'] = 5
P['S8']['ppv2']['gain'] = [1, 0.965, 0.9, 0]
# ---- v2 changes
def upd(k, **kw):
    for a, b in kw.items():
        if a == 'bloom':
            P[k]['ppv2']['bloom'].update(b)
        else:
            P[k]['ppv2'][a] = b
upd('S4', postExposure=-0.85, temperature=-6, tint=2, saturation=-10, contrast=16, lift=[0.99, 0.99, 1, 0.006],
    gamma=[0.98, 0.98, 1, 0], gain=[1, 1, 1, 0], bloom=dict(color='#F0F0F6', intensity=5))
P['S4']['name'] = '触手之门 the tentacle gate (dusk-violet wound, indigo haze band)'
upd('S6', postExposure=-0.75, temperature=-4, tint=0, saturation=2, contrast=6, gain=[1, 0.98, 0.94, 0])
P['S6']['name'] = '天空 I 晨 dawn (藍 and gold on white)'
upd('S7a', tint=1, lift=[0.99, 0.995, 1, 0.008], gamma=[0.975, 0.985, 1, 0], gain=[0.985, 0.995, 1, 0])
P['S7a']['name'] = '海面之下 under the surface (open-ocean ultramarine, never teal)'
upd('S9b', postExposure=0.3, contrast=16, lift=LIFT_NIGHT, bloom=dict(intensity=8))
P['S9b']['name'] = '星海高潮 star-sea climax (black stays black; light comes from sources)'
for k, v in P.items():
    b = v['ppv2']['bloom']; b['diffusion'] = min(b['diffusion'], 9)
# S10 carries S11's bloom shape at intensity 0, so the 10->11 crossfade never passes through a low threshold
P['S10']['ppv2']['bloom'] = dict(intensity=0, threshold=1.0, softKnee=0.6, diffusion=7.5, color='#FFFFFF')

def pre_for_display(d, p):
    t = d / 255.0; lo, hi = 1e-5, 500.0
    for _ in range(90):
        m = (lo * hi) ** 0.5
        y = ppv2.display_of(np.array([m, m, m]), p)[1]
        lo, hi = (m, hi) if y < t else (lo, m)
    return m
T0 = {}
for k, v in P.items():
    p = v['ppv2']; b = p['bloom']
    L = pre_for_display(DISPLAY_T0, p if k != 'S10' else P['S11']['ppv2'])
    b['threshold'] = round(l2g(L / (1 - b['softKnee'])), 2)
    T0[k] = g2l(b['threshold']) * (1 - b['softKnee'])
    v['bloom_T0_scene_linear'] = round(T0[k], 3)
    v['bloom_T0_note'] = 'bloom starts at scene-linear %.3f (pre-exposure) = neutral grey displayed at luma %d' % (T0[k], DISPLAY_T0)

F['_changes_v1'] = [
 "bloom.fastMode = true in every profile (lens_tech: VR cost)",
 "S1/S2/S11/S12 temperature -6 -> -4 (cool 藍白 tubes turned cyan at -6)",
 "NEW S4c 门内 inside the tear",
 "S8 saturation +8 -> +5, gain (1,0.955,0.87) -> (1,0.965,0.90) (corrected AP1->sRGB matrix)"]
F['_changes_v2'] = [
 "bloom threshold re-solved per profile: knee start T0 at luma %d (v1 thresholds 0.7-1.1 made everything above luma 100-166 bloom)" % DISPLAY_T0,
 "bloom clamp 24 -> 4.24 (gamma; = 24 linear)",
 "S4 -0.85 / -6 / +2 / sat -10 / contrast +16, gamma (0.98,0.98,1,0), gain neutral, bloom #F0F0F6 (critique_awe B2)",
 "S4c -0.9 / -3 / +2 / sat -14, bloom 6 #F2F3F6 (critique_awe B3: dark grace, APL 30->55)",
 "S6 temp -4, tint 0, sat +2, contrast +6, gain (1,0.98,0.94), postExposure retuned to APL 110 with bloom on the v2-hue dawn frame (critique_awe M4)",
 "S7a tint +1, lift (0.99,0.995,1,0.008), gamma (0.975,0.985,1,0), gain (0.985,0.995,1,0): red never crushed to 0 (critique_awe M6)",
 "S9b postExposure +0.8 -> +0.3, contrast +16, night lift, bloom 10 -> 8: black stays black; the climb comes from emitters (critique_awe M8)",
 "helpers rebuilt: PPv2 lerps to ABSOLUTE override values, so exposure helpers are EXPO_UP (+4) / EXPO_DOWN (-4) driven by w = dEV/(H-b); "
 "bloom and saturation helpers split off; FLASH_TEAR has no bloom override (critique_feasibility B-1, B-2)"]

F['helpers'] = {
 "_how": ("PPv2 does param = lerp(current, override, weight). An exposure helper with a FAR target H (+4 or -4) gives exactly "
          "b + dEV when weight w = dEV / (H - b), where b = the postExposure already blended by the scene volumes below it "
          "(b = lerp(pe_old, pe_new, w_new) during a scene crossfade). The Director sums every exposure event active this frame "
          "(beat decay + flash + white ramp + mirror pulse) into ONE dEV(t) and sets EXPO_UP (dEV > 0) or EXPO_DOWN (dEV < 0). "
          "Route C (External LUT, profile postExposure = 0) is the same formula with b = 0."),
 "EXPO_UP": {"priority": 100, "ppv2": {"postExposure": 4.0}, "weight": "dEV / (4 - b)",
             "events": {"break-out U6": "+0.5 EV in 0.4 s, then 3 s linear decay (w_peak = 0.102 at b = -0.9)",
                        "U9 tube flash": "+0.3 EV in 0.2 s, 0.5 s decay (w_peak 0.062 at b = -0.85)",
                        "FLASH_TEAR U12": "desktop +1.5 EV in 0.4 s EV-linear, hold 0.1 s (w = 0.306 at b = -0.9); VR: min(+1.5, EV that brings APL to 150)",
                        "exit into dusk F9": "+0.8 EV at the end of the >= 6 s ramp, 4 s decay (w_peak 0.178 at b = -0.5)",
                        "white crash / swell": "crash 0 -> +1.0 EV in 1.2 s, swell -> +2.4 EV in 6 s (w = 0.270 / 0.649 at b = +0.3)",
                        "mirror pulse": "+0.35 EV, 0.08 s in / 0.35 s out, w = 0.35 / (4 - b(t)); suppressed for crossings inside the white ramp (mirrors 10-12)",
                        "after the first white": "+1.0 EV at weight solved against S11 (w = 0.241), 4 s decay, overlay fill compensated",
                        "after the second white": "+0.8 EV against S12 (w = 0.200), 5 s decay, overlay fill compensated"}},
 "EXPO_DOWN": {"priority": 99, "ppv2": {"postExposure": -4.0}, "weight": "-dEV / (b + 4)",
               "events": {"water entry F2": "-0.5 EV in 0.3 s, 1 s recovery (w_peak 0.156 at b = -0.8)"}},
 "WHITE_SAT": {"priority": 96, "ppv2": {"saturation": -30}, "weight": "= white-ramp fraction: 0 -> 0.42 (crash) -> 1.0 (swell); hard-cut to 0 under the full overlay"},
 "WHITE_BLOOM": {"priority": 96, "ppv2": {"bloom": {"intensity": 12, "threshold": 0.8, "softKnee": 0.8, "diffusion": 9, "color": "#EEF4F8"}},
                 "weight": "crash 0 -> 0.5, swell -> 1.0, then 1 -> 0 EV-linearly WITH the 3 s overlay (so the overlay itself never blooms)"},
 "LENS_ARCHIVE": {"priority": 200, "desktop_only": True,
                  "vignette": {"intensity": 0.26, "smoothness": 0.45, "color": "#02040A"},
                  "grain": {"intensity": 0.20, "size": 1.0, "lumContrib": 0.85, "colored": False},
                  "weight": "U0 0 -> 1 over 8 s (the record starts); U3 1 -> 0 over 8 s (the sound opens); 10->11 0 -> 1 under the white; 11->12 1 -> 0 under the second white"},
 "LENS_CLEAN": {"priority": 199, "desktop_only": True,
                "vignette": {"intensity": 0.20, "smoothness": 0.40, "color": "#02040A"},
                "grain": {"intensity": 0.06, "size": 0.8, "lumContrib": 0.8, "colored": False},
                "weight": "1 everywhere on desktop (scene 1 included); LENS_ARCHIVE sits above it"},
}
F['_route_c_crossfade'] = "External LUTs blend in display-linear light: for an exposure-changing crossfade drive w(t) = (2^(dEV*x) - 1)/(2^dEV - 1), x = 0..1"
json.dump(F, open('../grades_final.json', 'w'), ensure_ascii=False, indent=1)
for k, v in P.items():
    p = ppv2.full(v['ppv2'])
    print('%-4s pe %+5.2f temp %+3d tint %+3d sat %+3d con %+3d  bloom %4.1f thr %.2f knee %.1f  T0 %.3f' % (
        k, p['postExposure'], p['temperature'], p['tint'], p['saturation'], p['contrast'], p['bloom']['intensity'],
        p['bloom']['threshold'], p['bloom']['softKnee'], T0[k]))
