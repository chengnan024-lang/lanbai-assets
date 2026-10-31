"""蓝白 / Lanbai · gate · D-05: how wide are the near arms where they pass the eye? (U8 side window, 1080p)

D-05 (Art/总导演裁决.md): when the U8 near arms sweep past the side window, the part at eye height must be >= 250 px wide at
1080p (the thick part up at window height, not the thin middle), keeping >= 8 m from the eye. This renders each near arm alone
(Cycles position pass, posed as LanbaiGateDriver, TentacleSway v2.8 vertex stretch, the instance girth) from the U8side
camera at times around 166.45 and prints, per arm: the width in pixels of its silhouette in the rows whose world height is
within +-1.5 m of the eye, and its nearest distance to the eye.

  python3 near_width.py [--t 166.45,167.75] [--girth Near_0=1.4,...] [--dy Near_0=12,...]
"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deck_ref as D  # noqa: E402
import seam_ref as S  # noqa: E402

CAMS = json.load(open(os.path.join(D.REPO, 'Gate', 'GateLayout_v2.json')))['cameras']


def measure(t, view='U8side', girth=None, dy=None, w=1920, h=1080, dx=None, gp=1.5):
    c = CAMS[view]
    cam = dict(t=t, pos=c['eye_bus_relative'], look_yaw_deg=c['look_yaw_deg'], look_pitch_deg=c['look_pitch_deg'],
               hfov_deg=c['hfov_deg'])
    eye = np.array(cam['pos'], float)
    arms = S.arm_meshes(t, True)
    out = {}
    for a in arms:
        name, V, F, p, R, sc = a
        if not name.startswith('Near_'):
            continue
        V = V.copy()
        if dy and name in dy:
            V[:, 1] += dy[name]
        if dx and name in dx:
            V[:, 0] += dx[name]
        if girth and name in girth and girth[name] != 1.0:
            # TentacleSway _Girth: inflate along the normal by (g - 1) (1 - t)^1.5 x B x R_root; here: push away from the
            # local centroid of each t ring (the same thing for a tube)
            T = S.ARMS[name + '_t']
            Vl = (V - p) @ R / sc                                   # back to object space
            g = girth[name]
            bins = np.round(T * 400).astype(int)
            for b in np.unique(bins):
                m = bins == b
                cen = Vl[m].mean(0)
                Vl[m] = cen + (Vl[m] - cen) * (1.0 + (g - 1.0) * (1.0 - T[m].mean()) ** gp)
            V = (Vl * sc) @ R.T + p
        P, N, hit = S.render_arm_passes([(name, V, F, p, R, sc)], cam, w, h)
        rows = []
        for y in range(h):
            m = hit[y]
            if not m.any():
                continue
            ys = P[y, m, 1]
            sel = np.abs(ys - eye[1]) < 1.5
            if sel.sum() > 0:
                xs = np.nonzero(m)[0][sel]
                rows.append(xs.max() - xs.min() + 1)
        dmin = float(np.min(np.linalg.norm(V - eye, axis=1)))
        out[name] = (max(rows) if rows else 0, int(np.median(rows)) if rows else 0, dmin)
    return out


if __name__ == '__main__':
    a = sys.argv[1:]
    ts = [float(x) for x in (a[a.index('--t') + 1].split(',') if '--t' in a else ['166.45'])]
    girth = dict((k, float(v)) for k, v in (x.split('=') for x in a[a.index('--girth') + 1].split(','))) if '--girth' in a else None
    dy = dict((k, float(v)) for k, v in (x.split('=') for x in a[a.index('--dy') + 1].split(','))) if '--dy' in a else None
    dx = dict((k, float(v)) for k, v in (x.split('=') for x in a[a.index('--dx') + 1].split(','))) if '--dx' in a else None
    view = a[a.index('--view') + 1] if '--view' in a else 'U8side'
    gp = float(a[a.index('--gp') + 1]) if '--gp' in a else 1.5
    for t in ts:
        for name, (wmax, wmed, dmin) in measure(t, view, girth, dy, dx=dx, gp=gp).items():
            print('t %.2f %s %s: width at eye height max %d px, median %d px; nearest %.1f m' % (t, view, name, wmax, wmed, dmin), flush=True)
