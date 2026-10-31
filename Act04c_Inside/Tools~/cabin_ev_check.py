"""D-50 #1: the cabin's brightening against the bible §1.8 comfort limits (<= 0.5 EV / 0.25 s, <= 1.0 / 1 s, <= 1.8 / 2 s),
measured the way 阿白's Unity flicker probe measures it (frames.csv: mean log2 L of the whole frame).

  ~/bpy/bin/python cabin_ev_check.py            -> ../Docs~/flashcheck/cabin_ev_d50.json + cabin_ev_d50.png

1. Per cabin point (bus z -3.5 .. 3.5, window weight 0.35 / 1): the worst rise of log2 L, as-is (r15.2: smoothstep
   ambient over 8 s, band E fixed at the solved colours, 1.5 m front, 3.5 m tail) and now (D-50: inside_drive). The
   frame's log-mean cannot rise faster than its fastest pixel (before the tone curve), so the worst point bounds it.
2. 阿白's frames re-weighted: her measured as-is curve = c x (the cabin's log-mean) + (1 - c) x (the rest). c (the
   cabin's share of the frame) is fitted so the rest is as smooth as possible through the crossings; then the new
   curve = measured + c x (new cabin - as-is cabin). An estimate of what her probe will read, not a Unity run.
"""
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inside_def as D  # noqa: E402
import inside_drive as DR  # noqa: E402

LIMITS = {0.25: 0.5, 1.0: 1.0, 2.0: 1.8}
REPO = D.REPO
PROBES = {
    'fwd': ('FromLocal/flicker_probe/20261026-031149/probe/gate179/as_is/frames.csv', np.linspace(2.05, 3.5, 12)),
    'rear': ('FromLocal/flicker_probe/20261026-031222/probe/gate_back/as_is/frames.csv', np.linspace(-3.5, 2.05, 24)),
}
WINS = (0.35, 0.675, 1.0)
E_OLD = 0.2126 * 1.8665 + 0.7152 * 1.895 + 0.0722 * 2.4957   # luminance of the solved band colour (lip 1)


def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def light_old(z, t, win):
    """r15.2 as delivered (LanbaiInsideDriver before D-50)."""
    w = ss((t - 180.05) / 8.0)
    a = [g + (i - g) * w for g, i in zip(DR.CABIN_AMB_GATE, DR.CABIN_AMB_INSIDE)]
    y = 0.2126 * a[0] + 0.7152 * a[1] + 0.0722 * a[2]
    for k in range(8, 0, -1):
        t0, dur = D.BAND_START[k - 1], D.BAND_SWEEP[k - 1]
        if k < 8 and t0 <= t < t0 + dur + 1.2:
            d = z - (3.6 - 7.6 * (t - t0) / dur)
            edge = min(max(d / 1.5 + 0.5, 0.0), 1.0)
            return y + E_OLD * win * edge * math.exp(-max(d, 0.0) / 3.5)
        if k == 8 and t0 <= t < D.SLEEVE_BAND_END - 2.4:
            d = z - (3.6 - 7.6 * min((t - t0) / 2.4, 1.0))
            return y + E_OLD * win * min(max(d / 1.5 + 0.5, 0.0), 1.0)
    return y


def light_new(z, t, win):
    return DR.cabin_light(z, t, win)


def rises(t, y):
    out = {}
    for w in LIMITS:
        n = max(int(round(w / (t[1] - t[0]))), 1)
        best = (0.0, None)
        for i in range(len(y) - 1):
            seg = y[i + 1:i + n + 1]
            if len(seg):
                r = float(seg.max() - y[i])
                if r > best[0]:
                    best = (r, float(t[i]))
        out[w] = best
    return out


def cabin_logmean(fn, zs, t):
    return np.array([np.mean([math.log2(fn(z, tt, w)) for z in zs for w in WINS]) for tt in t])


def main():
    report = {'limits': {str(k): v for k, v in LIMITS.items()}}
    # 1. per point, 177.55 .. 252.64 (the window the inside driver owns the cabin)
    t = np.arange(177.55, D.U12 - 0.02, 1.0 / 60.0)              # after U12 the cabin is under act 5's black
    pts = {}
    for name, fn in (('as_is', light_old), ('d50', light_new)):
        worst = {w: (0.0, None, None) for w in LIMITS}
        for z in np.linspace(-3.5, 3.5, 29):
            for win in (0.35, 1.0):
                y = np.log2([max(fn(z, tt, win), 1e-9) for tt in t])
                for w, (r, at) in rises(t, y).items():
                    if r > worst[w][0]:
                        worst[w] = (r, at, float(z))
        pts[name] = {str(w): dict(rise_ev=round(r, 3), at_t=at and round(at, 2), z=zz) for w, (r, at, zz) in worst.items()}
        print('per point %-6s' % name, '  '.join('%.2fs %+.2f@%.2f' % (w, r, at or 0) for w, (r, at, zz) in worst.items()))
    report['per_point'] = pts
    # 2. 阿白's frames re-weighted
    import csv
    probes = {}
    curves = {}
    for view, (rel, zs) in PROBES.items():
        rows = [r for r in csv.DictReader(open(os.path.join(REPO, rel)))]
        tm = np.array([float(r['t']) for r in rows])
        ym = np.array([float(r['mean_log2_L']) for r in rows])
        co = cabin_logmean(light_old, zs, tm)
        cn = cabin_logmean(light_new, zs, tm)
        sel = (tm > 179.8) & (tm < 187.5)
        best = None
        for c in np.linspace(0.0, 0.95, 96):
            rest = (ym - c * co) / (1.0 - c)
            score = rises(tm[sel], rest[sel])[0.25][0]
            if best is None or score < best[0] - 1e-6:
                best = (score, c)
        c = best[1]
        yn = ym + c * (cn - co)
        r_m, r_n = rises(tm, ym), rises(tm, yn)
        probes[view] = dict(frames=rel, cabin_share=round(float(c), 3),
                            measured={str(w): dict(rise_ev=round(r, 3), at_t=at and round(at, 2)) for w, (r, at) in r_m.items()},
                            estimated_d50={str(w): dict(rise_ev=round(r, 3), at_t=at and round(at, 2)) for w, (r, at) in r_n.items()},
                            passes=all(r_n[w][0] <= LIMITS[w] for w in LIMITS))
        curves[view] = (tm, ym, yn)
        print('%-4s c %.2f  measured' % (view, c), '  '.join('%.2fs %+.2f' % (w, r) for w, (r, at) in r_m.items()),
              ' | D-50 est.', '  '.join('%.2fs %+.2f' % (w, r) for w, (r, at) in r_n.items()))
    report['probes'] = probes
    out = os.path.join(D.KIT, 'Docs~', 'flashcheck', 'cabin_ev_d50.json')
    json.dump(report, open(out, 'w'), ensure_ascii=False, indent=1)
    try:
        import matplotlib
        matplotlib.use('Agg')
        import matplotlib.pyplot as plt
        fig, ax = plt.subplots(2, 1, figsize=(10, 6), sharex=True)
        for a, (view, (tm, ym, yn)) in zip(ax, curves.items()):
            a.plot(tm, ym, color='0.55', lw=1.2, label='measured in Unity (as-is, 10-26)')
            a.plot(tm, yn, color='C0', lw=1.6, label='D-50 estimate')
            a.set_ylabel('%s  mean log2 L' % view)
            a.grid(alpha=0.3)
            a.legend(loc='lower right', fontsize=8)
        ax[-1].set_xlabel('t (s)')
        plt.tight_layout()
        plt.savefig(out.replace('.json', '.png'), dpi=90)
    except Exception as e:  # noqa: BLE001
        print('no plot:', e)
    print(out)


if __name__ == '__main__':
    main()
