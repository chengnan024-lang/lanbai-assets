"""蓝白 / Lanbai · gate · the data LanbaiGateDriver needs at runtime, flattened from GateLayout_v2.json.

Udon cannot afford to walk a 27 000-line JSON every frame, so everything the driver evaluates per frame is baked here
into flat arrays (Gate/GateDriver_Bake.json); the editor builder (Gate/Editor/LanbaiGateDriverBuilder.cs) reads that
file with JsonUtility and fills the driver's serialized fields. Re-run after any change to GateLayout_v2.json:

  python3 gate_driver_bake.py

What is baked (README_GateLayout §2 / §2.1 / §2.2 / §4.1, the same evaluation as FromLocal/gate_test LB_GateTest_Run):
  cues, v_g; tear_H_knots with their monotone PCHIP slopes (Fritsch-Carlson = scipy PchipInterpolator); the moon;
  the moon disc gain keys; the multitude's two reveal groups; the tide reveal; the tear's sky-fold keys and overrides;
  per instance: id, frame, final pose, the reveal (keys, or the multitude group) and the anims rise / lean / track /
  close / drift (at most one of each per instance; evaluated in that order, which is the JSON order for every instance).
"""
import json
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
GATE = os.path.dirname(HERE)
J = json.load(open(os.path.join(GATE, 'GateLayout_v2.json')))
PROFILES = {'ss': 0, 'trap': 1, 'beta': 2}


def pchip_slopes(x, y):
    x = np.asarray(x, float)
    y = np.asarray(y, float)
    h = np.diff(x)
    dl = np.diff(y) / h
    n = len(x)
    d = np.zeros(n)
    for k in range(1, n - 1):
        if dl[k - 1] * dl[k] <= 0:
            d[k] = 0.0
        else:
            w1, w2 = 2 * h[k] + h[k - 1], h[k] + 2 * h[k - 1]
            d[k] = (w1 + w2) / (w1 / dl[k - 1] + w2 / dl[k])

    def edge(h0, h1, m0, m1):
        dv = ((2 * h0 + h1) * m0 - h0 * m1) / (h0 + h1)
        if np.sign(dv) != np.sign(m0):
            dv = 0.0
        elif np.sign(m0) != np.sign(m1) and abs(dv) > abs(3 * m0):
            dv = 3 * m0
        return dv
    d[0] = edge(h[0], h[1], dl[0], dl[1])
    d[-1] = edge(h[-1], h[-2], dl[-1], dl[-2])
    return d


def keys(ks, value='value'):
    return [float(k['t']) for k in ks], [float(k[value]) for k in ks]


def ease(a):
    return dict(t0=float(a.get('t0', 0.0)), t1=float(a.get('t1', 0.0)), profile=PROFILES.get(a.get('profile', 'ss'), 0),
                e=float(a.get('ease_e', 0.25)), b=float(a.get('beta_b', 3.5)))


def main():
    tl = J['timeline']
    cues = tl['cues']
    kt = [float(k['t']) for k in tl['tear_H_knots']]
    kh = [float(k['H']) for k in tl['tear_H_knots']]
    mt, mg = keys(J['moon']['disc_gain_keys'], 'gain')
    g0t, g0v = keys(J['multitude']['reveal_groups']['group0']['keys'])
    g1t, g1v = keys(J['multitude']['reveal_groups']['group1']['keys'])
    tt, tv = keys(J['tide']['reveal']['keys'])
    fd = J['tear']['fades']
    ft, fv = keys(fd['skyfolds_intensity_keys'], 'x')
    ov = J['tear']['gate_overrides']
    eye = J['cameras']['U7']['eye_bus_relative']
    out = dict(
        about='蓝白 gate driver bake (Gate/Source/gate_driver_bake.py from GateLayout_v2.json); read by '
              'Gate/Editor/LanbaiGateDriverBuilder.cs. Do not edit by hand.',
        U6=cues['U6'], U7=cues['U7'], U7b=cues['U7b'], U8=cues['U8'], U9=cues['U9'],
        vg=float(tl['v_g_m_per_s']),
        h_t=kt, h_H=kh, h_d=[float(v) for v in pchip_slopes(kt, kh)],
        moon_dir=[float(v) for v in J['lights']['moon']['direction_to_light_unity']],
        disc_t=mt, disc_g=mg,
        g0_t=g0t, g0_v=g0v, g1_t=g1t, g1_v=g1v,
        tide_t=tt, tide_v=tv,
        folds_t=ft, folds_v=fv, folds_gain=float(ov.get('skyfolds', 1.0)), halo_gain=float(ov.get('halo_intensity', 1.0)),
        tear_foot_os=[0.5, 0.0, -30.0], tear_top_os=[-59.14, 920.36, -30.0],
        eye_fallback=[float(v) for v in eye],
        inst=[],
    )
    for it in J['instances']:
        d = dict(id=it['id'], bus=1 if it.get('frame') == 'bus' else 0,
                 pos=[float(v) for v in it['position']], rot=[float(v) for v in it['rotation_xyzw']],
                 reveal_kind=0, group=0, rev_t=[], rev_v=[],
                 rise=0, rise_ease=ease({}), rise_start=[0.0, 0.0, 0.0],
                 lean=0, lean_ease=ease({}), lean_start=[0.0, 0.0, 0.0, 1.0],
                 track_t=[], track_q=[],
                 close=0, close_ease=ease({}), close_end=[0.0, 0.0, 0.0, 1.0],
                 drift_v=0.0, drift_tref=0.0,
                 # the per-renderer block values LB_GateTest writes (the builder snapshots the multitude's variant dims
                 # and occlusion maps from the scene; these two come from here)
                 phase=float(it['phase']) if 'phase' in it else float(it['material'].get('_Phase', 0.0)),
                 fog_cap=float(it['_FogCapI']) if '_FogCapI' in it else -1.0)
        rv = it.get('reveal') or {}
        if it.get('layer') == 'surge':
            d['reveal_kind'] = 2
            d['group'] = int(rv.get('group', 0))
        elif rv.get('keys'):
            d['reveal_kind'] = 1
            d['rev_t'], d['rev_v'] = keys(rv['keys'])
        seen = []
        for a in it.get('anim') or []:
            ty = a['type']
            seen.append(ty)
            if ty == 'rise':
                d['rise'] = 1
                d['rise_ease'] = ease(a)
                d['rise_start'] = [float(v) for v in a['position_start']]
            elif ty == 'lean':
                d['lean'] = 1
                d['lean_ease'] = ease(a)
                d['lean_start'] = [float(v) for v in a['rotation_start_xyzw']]
            elif ty == 'track':
                for k in a['keys']:
                    d['track_t'].append(float(k['t']))
                    d['track_q'] += [float(v) for v in k['rotation_xyzw']]
            elif ty == 'close':
                d['close'] = 1
                d['close_ease'] = ease(a)
                d['close_end'] = [float(v) for v in a['rotation_end_xyzw']]
            elif ty == 'drift':
                d['drift_v'] = float(a['v_rel_m_per_s'])
                d['drift_tref'] = float(a['t_ref'])
        order = [t for t in seen if t != 'drift']
        assert order == sorted(order, key=['rise', 'lean', 'track', 'close'].index), (it['id'], seen)
        out['inst'].append(d)
    path = os.path.join(GATE, 'GateDriver_Bake.json')
    json.dump(out, open(path, 'w'), indent=1, ensure_ascii=False)
    print('wrote', path, len(out['inst']), 'instances,', sum(len(i['track_t']) for i in out['inst']), 'track keys')


if __name__ == '__main__':
    main()
