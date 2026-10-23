"""InsideLayout.json (the one data source for Unity) + Editor/InsideLayoutData.cs (the same numbers as C# constants for
the build menu, so nothing is hand-copied). Run after inside_layout.py.  ~/bpy/bin/python build_json.py
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inside_def as D  # noqa: E402
import inside_drive as DR  # noqa: E402
import lb_grade as LG  # noqa: E402

KIT = D.KIT


def r(x, n=4):
    if isinstance(x, np.ndarray) and x.ndim == 0:
        x = float(x)
    if isinstance(x, (list, tuple, np.ndarray)):
        return [r(v, n) for v in x]
    return round(float(x), n)


def band_colour(k):
    """linear E x colour of the crossing band so a grey card (0.18) facing it reads luma 120 under S4c (seats, darker
    than grey, stay below 120): solved on the grey card's display luma."""
    fib = np.asarray(DR.fibre_fill(k))
    c = fib / max(fib.max(), 1e-6)
    lo, hi = 0.0, 50.0
    for _ in range(60):
        m = 0.5 * (lo + hi)
        codes = LG.display(0.18 * c * m, 'S4c')
        luma = float(codes @ [0.2126, 0.7152, 0.0722])
        lo, hi = (m, hi) if luma < 120 else (lo, m)
    return tuple(c * lo)


def main():
    L = json.load(open(os.path.join(D.HERE, 'out', 'layout_solved.json')))
    lips = []
    for p in L['lips']:
        k = p['k']
        m = DR.lip_material(k)
        lips.append(dict(k=k, cue='LIP%d' % k, t=p['t'], s=r(p['s'], 2), H=p['H'], mesh=p.get('mesh_kind', 'tear'), seed=p.get('seed'),
                         roll_deg=p['roll'] if k > 1 else -4.0, offset_m=p['offset'], clearance_m=p['clearance_m'],
                         clearance_need_m=r(p['clearance_need'], 1), fibre_screen=D.fibre_screen(k), fibre_fill_linear=r(m['fibre']),
                         fringe_len_m=4.0 if k == 1 else p.get('fringe_len_m'), lip_glow=m['lip_glow'], lip_glow_width_m=r(m['lip_w'], 2),
                         translucency_band=[m['band'][0], r(m['band'][1], 1)], band_colour_linear=r(band_colour(k)),
                         band_start=D.BAND_START[k - 1], band_sweep=D.BAND_SWEEP[k - 1]))
    zones = [dict(zone=k, screen=D.fog_screen(k) if 1 < k < 8 else (D.FOG_SCREEN_FIRST if k == 1 else D.FOG_SCREEN_LAST),
                  fill_linear=r(DR.zone_fill(k))) for k in range(1, 9)]
    out = dict(
        about='蓝白 · 第 4c 幕（门内）+ 第 5 幕（投入）的布局与时间曲线。唯一的数据源。由 Act04c_Inside/Tools~/build_json.py 生成，不要手改。'
              '坐标 = Unity 世界，米；车在原点、车头 +Z；InsideRoot 的世界位置 = (0, 0, -s(t))。',
        cues={k: D.CUE[k] for k in ('U6', 'U9', 'U10', 'U11', 'U12', 'U_voiceEnd', 'F0')} | {'LIP%d' % (i + 1): t for i, t in enumerate(D.LIP_T)},
        bible_vs_cues=dict(ein_Lichtchen_dial=dict(bible=196.10, cues_json_note=193.1, used=196.10)),
        hero_eye=dict(gate_cameras_U7=list(D.HERO_EYE), LB_Journey_heroEye=list(D.HERO_EYE_LBJ), used='gate_cameras_U7'),
        motion=dict(v_g=r(D.V_G, 4), v_end=D.V_END, decel_from='U9', decel_to='U_voiceEnd',
                    formula='s(t) = v_g tau + (v_end - v_g) T (x^3 - x^4/2), x = tau/T, tau = t - U9, T = U_voiceEnd - U9; '
                            'after T: s(T) + v_end (tau - T); before U9: v_g tau',
                    peak_accel=1.30, samples=[dict(t=t, s=r(D.dist(t), 2), v=r(D.speed(t), 3)) for t in np.arange(D.U9, D.U12 + 0.01, 0.5)]),
        lips=lips,
        sleeve=dict(L['sleeve'], wall_strands=46, note='entry + exit glow; 3 dark inner plies (gain 0.12, no fringe), two partial'),
        fog=dict(model='LanbaiFog v1 model B (gradient): _Udon_HorizonColor.a = 2', density_gate=DR.FOG_D0, density_inside=DR.FOG_D1,
                 density_ramp='U9 .. U9 + 2 s smoothstep', ahead_m=DR.FOG_AHEAD_M, nadir_k=DR.NADIR_K, band_dir=[0, 0, 1], band_width_deg=180,
                 shape=[25, 90, 1, 0], below=[-90, -15, 1, 0], zones=zones,
                 rule='zone colour F(s): zone k from lip k plane on, smoothstep between consecutive planes; ahead = F(s + 250), '
                      'behind = F(s - 250), zenith = F(s), nadir = 0.85 F(s); RenderSettings.fogColor = F(s)'),
        cloth=dict(screen=D.CLOTH_SCREEN, fill_linear=r(DR.fill_of(D.CLOTH_SCREEN)), weave_tile_m=40.0, weave_amount=0.45),
        dot=dict(az_deg=D.DOT_AZ_DEG, el_deg=D.DOT_EL_DEG, distance_m=D.DOT_DIST, screen=D.DOT_SCREEN, fill=list(D.DOT_FILL),
                 fill_linear=r(DR.fill_hdr(*D.DOT_FILL)), core_deg=list(D.DOT_CORE_DEG), glow_deg=list(D.DOT_GLOW_DEG),
                 appear=dict(t=D.DOT_APPEAR[0], dur=D.DOT_APPEAR[1], ev_from=-6), grow=dict(t0=D.DOT_GROW[0], t1=D.DOT_GROW[1], curve='smootherstep'),
                 halo_gain=0.22),
        cabin=dict(ambient_gate=['#232A3A', 0.3], ambient_inside=list(D.CABIN_AMBIENT), trilight_gate=['#0C1020', '#1E2234', '#262A40'],
                   trilight_inside=list(D.TRILIGHT), main_light=[1.0, 0.001], ramp='180.05 -> 188.05 smoothstep (with S4 -> S4c)',
                   band=dict(front_soft_m=1.5, tail_m=3.5, sweep='front (+3.6) -> rear (-4.0)', lip8='in 2.4 s, hold, from 228.6 retreat rear -> front 2.4 s'),
                   dial=dict(base=['#FF7703', 0.71], bright=['#FF7B00', 2.13], t=D.LICHT_DIAL_T, dur=3.0, out='with the black mask 248.39 -> 248.64')),
        act5=dict(stop=D.STOP_T, flash=dict(t0=D.FLASH_T0, rise=0.4, hold=0.1, fall=0.25, ev=1.5), black=dict(t0=D.FLASH_T0 + 0.5, t1=D.U12,
                  fill_S4c='#030400', fill_S6='#090200', screen='#030409', hold_to='F0 + 1.0 (act 6 takes the overlay)')),
        loose_threads=dict(count=90, radius_m=[9, 25], length_m=[0.6, 3.0], drift='forward 0.2-0.5 m/s, converge 25 %', gain=0.25,
                           clock='eased to a stop over 242.39 -> 246.39'),
        globals=['_Udon_InsidePortal', '_Udon_InsideDot', '_Udon_InsideFibre', '_Udon_InsideClock', '_Udon_InsideFog',
                 '_Udon_CabinSlice', '_Udon_CabinSliceColor', '_Udon_RadioDial', '_Udon_CabinAmbient',
                 'LanbaiFog: _Udon_FogDensity _Udon_FogBandDir _Udon_FogBandColor _Udon_FogBandWidth _Udon_HorizonColor _Udon_ZenithColor _Udon_NadirColor _Udon_FogShape _Udon_FogBelow'],
    )
    json.dump(out, open(os.path.join(KIT, 'InsideLayout.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    # ---- C# constants for the build menu
    def cs_floats(a):
        return 'new float[] { ' + ', '.join('%.6ff' % float(x) for x in a) + ' }'

    def cs_colors(cs):
        return 'new Color[] { ' + ', '.join('new Color(%.6ff, %.6ff, %.6ff, 1f)' % tuple(c[:3]) for c in cs) + ' }'
    cs = []
    cs.append('// GENERATED by Act04c_Inside/Tools~/build_json.py from InsideLayout.json. Do not edit by hand.')
    cs.append('#if UNITY_EDITOR\nusing UnityEngine;\nnamespace Lanbai.Inside.Editor\n{\n    public static class InsideLayoutData\n    {')
    cs.append('        public const float U6 = %.2ff, U9 = %.2ff, VoiceEnd = %.2ff, U12 = %.2ff, LichtDial = %.2ff, SleeveExit = %.2ff;' %
              (D.U6, D.U9, D.VOICE_END, D.U12, D.LICHT_DIAL_T, D.SLEEVE_EXIT_T))
    cs.append('        public static readonly float[] LipT = %s;' % cs_floats(D.LIP_T))
    cs.append('        public static readonly float[] LipS = %s;' % cs_floats([l['s'] for l in lips]))
    cs.append('        public static readonly float[] LipH = %s;' % cs_floats([l['H'] for l in lips]))
    cs.append('        public static readonly float[] LipRoll = %s;' % cs_floats([l['roll_deg'] for l in lips]))
    cs.append('        public static readonly float[] LipGlowWidth = %s;' % cs_floats([l['lip_glow_width_m'] for l in lips]))
    cs.append('        public static readonly float[] BandWidth = %s;' % cs_floats([l['translucency_band'][1] for l in lips]))
    cs.append('        public static readonly float[] BandStart = %s;' % cs_floats(D.BAND_START))
    cs.append('        public static readonly float[] BandSweep = %s;' % cs_floats(D.BAND_SWEEP))
    cs.append('        public static readonly Color[] FibreFill = %s;' % cs_colors([l['fibre_fill_linear'] for l in lips]))
    cs.append('        public static readonly Color[] BandColour = %s;' % cs_colors([l['band_colour_linear'] for l in lips]))
    cs.append('        public static readonly Color[] ZoneFill = %s;' % cs_colors([z['fill_linear'] for z in zones]))
    cs.append('        public static readonly Color ClothFill = new Color(%.6ff, %.6ff, %.6ff, 1f);' % tuple(DR.fill_of(D.CLOTH_SCREEN)))
    cs.append('        public static readonly Color DotFill = new Color(%.6ff, %.6ff, %.6ff, 1f);' % tuple(DR.fill_hdr(*D.DOT_FILL)))
    cs.append('        public static readonly float[] PlyDz = %s;' % cs_floats([p['dz'] for p in L['sleeve']['plies']]))
    cs.append('        public static readonly float[] PlyGain = %s;' % cs_floats([p['gain'] for p in L['sleeve']['plies']]))
    cs.append('        public static readonly float[] PlyRoll = %s;' % cs_floats([p['roll'] for p in L['sleeve']['plies']]))
    cs.append('        public const float DotAz = %.3ff, DotEl = %.3ff, DotDist = %.1ff;' % (D.DOT_AZ_DEG, D.DOT_EL_DEG, D.DOT_DIST))
    cs.append('        public static readonly Vector3 HeroEye = new Vector3(%.3ff, %.3ff, %.3ff);' % tuple(D.HERO_EYE))
    cs.append('    }\n}\n#endif')
    os.makedirs(os.path.join(KIT, 'Editor'), exist_ok=True)
    open(os.path.join(KIT, 'Editor', 'InsideLayoutData.cs'), 'w', encoding='utf-8').write('\n'.join(cs) + '\n')
    print('wrote InsideLayout.json + Editor/InsideLayoutData.cs; band colours', [l['band_colour_linear'] for l in lips][:2])


if __name__ == '__main__':
    main()
