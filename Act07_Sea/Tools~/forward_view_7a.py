"""D-44 #5: what can the main seat see FORWARD in act 7a, beat by beat? (before the local per-beat screenshots)

  ~/bpy/bin/python Act07_Sea/Tools~/forward_view_7a.py      -> Act07_Sea/Docs~/forward_view_7a.json (+ prints a table)
  ... [--eye 0.70,1.77,0.20] [--layout <json>] [--out <json>]   (阿白's old-bus HERO_EYE / the layout the local build ran)

The forward field (总导演 D-44 #5): azimuth -35..+35, elevation -10..+25 from the main eye (0.55, 1.70, 2.05), i.e. what
the windscreen shows (bus_shell bible_v2: az -50..25, el -15..22). Everything comes from Act07_Layout.json and the
driver's laws (the same gates / gains / fades as LanbaiAct07Driver.Evaluate); 'visible' also needs the water: the fog
transmittance exp(-density x distance) at that depth (README §2 water keys). Counts only -- whether the local build
DRAWS them is the screenshots' job (D-44 #5 step 1)."""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
PKG = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import act07_motion as AM                                   # noqa: E402

def _arg(name, default):
    return sys.argv[sys.argv.index(name) + 1] if name in sys.argv else default


J = json.load(open(_arg('--layout', os.path.join(PKG, 'Act07_Layout.json')), encoding='utf-8'))
U, P = J['unity'], J['particles']
EYE = np.array([float(v) for v in _arg('--eye', '0.55,1.70,2.05').split(',')])
AZ, EL = (-35.0, 35.0), (-10.0, 25.0)
BEATS = [(363.3, 'F2h 入水'), (367.2, 'F3 斯涅尔之窗'), (387.0, '车顶破洞见窗'), (446.0, 'F4 船体荧光'), (462.4, 'F4p 光柱汇聚'),
         (474.4, 'F3e 间奏'), (506.4, 'F3e1 最后一闪'), (532.4, 'F3e2 海脊'), (556.4, 'F3e3 蓝熄灭'), (559.0, 'F3i 播种开始'),
         (630.0, '播种最密'), (645.0, 'F5 暖点')]


def smooth(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def water_density(depth):
    W = J['water']['keys']
    ds = [k['depth'] for k in W]
    if depth <= ds[0]:
        return W[0]['density']
    for i in range(1, len(ds)):
        if depth < ds[i]:
            f = (depth - ds[i - 1]) / (ds[i] - ds[i - 1])
            return W[i - 1]['density'] * (1 - f) + W[i]['density'] * f
    return W[-1]['density']


def azel(v):
    d = np.linalg.norm(v, axis=-1)
    az = np.degrees(np.arctan2(v[..., 0], v[..., 2]))
    el = np.degrees(np.arcsin(np.clip(v[..., 1] / np.maximum(d, 1e-9), -1, 1)))
    return az, el, d


def inside(az, el):
    return (az >= AZ[0]) & (az <= AZ[1]) & (el >= EL[0]) & (el <= EL[1])


def shafts_at(t, depth, dens):
    """the 16 water-fixed shafts: segments, sampled; in the forward field if any visible part is; gain = the driver's"""
    g = 1 - min(max((depth - U['shaft_depth_full']) / (U['shaft_depth_gone'] - U['shaft_depth_full']), 0), 1)
    gather = smooth((t - U['gather_t0']) / (U['gather_t1'] - U['gather_t0']))
    if t > U['gather_t0']:
        g = g + (1 - g) * gather
    if t > U['gather_t1']:
        g *= 1 - smooth((t - U['gather_t1']) / (U['shafts_gone_t'] - U['gather_t1']))
    if g < 0.01:
        return dict(gain=round(g, 3), in_view=0, note='off')
    busw = np.array([0.0, -depth, AM.fwd(t)])
    n = len(U['shaft_half_width'])
    C = np.asarray(U['shaft_centre']).reshape(-1, 3); A = np.asarray(U['shaft_axis']).reshape(-1, 3)
    gp = np.asarray(U['gather_point_bus'])
    hits, best = 0, 0.0
    for i in range(n):
        c = C[i] - busw
        c = c + (gp + (c - gp) * 0.12 - c) * gather                     # the vertex shader's gather (bus frame)
        s = np.linspace(-0.5, 0.5, 41)[:, None] * U['shaft_length'][i]
        pts = c[None, :] + A[i][None, :] * s
        az, el, d = azel(pts - EYE)
        tr = np.exp(-dens * d)
        vis = inside(az, el) & (tr > 0.15)
        if vis.any():
            hits += 1
            best = max(best, float(tr[vis].max()))
    return dict(gain=round(g, 3), in_view=hits, best_transmittance=round(best, 2))


def particles_at(t, depth, dens):
    busw = np.array([0.0, -depth, AM.fwd(t)])
    out = {}
    # snow (the shader's wrap box, sphere fade)
    Sn = P['snow']
    pw = np.asarray(Sn['positions']).reshape(-1, 3) - np.array([0.0, P['snow_sink'] * t, 0.0])
    rel = (np.modf((pw - busw) / U['snow_box'] + 0.5)[0] % 1.0 - 0.5) * U['snow_box']
    az, el, d = azel(rel - EYE)
    vis = inside(az, el) & (np.linalg.norm(rel, axis=1) < U['snow_sphere'])
    out['snow'] = dict(in_view=int(vis.sum()), within_5m=int((vis & (d < 5)).sum()))
    # sown lights (fixed in the water, born from F3i)
    Sd = P['seeds']
    pos = np.asarray(Sd['positions']).reshape(-1, 3) - busw
    born = np.asarray(Sd['birth_t']) <= t
    az, el, d = azel(pos - EYE)
    tr = np.exp(-dens * d)
    vis = born & inside(az, el) & (tr > 0.1)
    out['seeds'] = dict(born=int(born.sum()), in_view=int(vis.sum()), births_last_10s_in_view=int((vis & (np.asarray(Sd['birth_t']) > t - 10)).sum()))
    # hull trails (bus frame; F4 on): positions near the hull
    if t >= U['F4']:
        Tr = P['trails']
        az, el, d = azel(np.asarray(Tr['positions']).reshape(-1, 3) - EYE)
        out['trails'] = dict(pool_in_view=int(inside(az, el).sum()), of=Tr['count'],
                             note='the hull points are beside / under the bus: through the windscreen only the ones ahead of the eye')
        TF = P.get('trails_front')
        if TF is not None:
            f0, f1 = U['trails_front_fade']
            g = 1.0 - smooth((t - f0) / (f1 - f0))
            # they flow up the windscreen: count the pool that is in the field while rising 0..3 m
            q = np.asarray(TF['positions']).reshape(-1, 3)
            n_in = 0
            for rise in (0.0, 1.0, 2.0, 3.0):
                az, el, d = azel(q + np.array([0.0, rise, 0.0]) - EYE)
                n_in = max(n_in, int(inside(az, el).sum()))
            out['trails_front'] = dict(pool_in_view=n_in if g > 0.01 else 0, of=TF['count'], gain=round(g, 2))
    else:
        out['trails'] = dict(pool_in_view=0, note='before F4')
    return out


def ridge_at(t, depth, dens):
    R = J['ridge']; g = R['grid']
    X = np.asarray(R['x']).reshape(g['ny'], g['nz'])
    busw = np.array([0.0, -depth, AM.fwd(t)])
    ys = g['y0'] + g['dy'] * np.arange(g['ny']); zs = g['z0'] + g['dz'] * np.arange(g['nz'])
    Z, Y = np.meshgrid(zs, ys)
    yaw = math.radians(R.get('yaw_deg', 0.0))
    Xr = X * math.cos(yaw) + Z * math.sin(yaw); Zr = -X * math.sin(yaw) + Z * math.cos(yaw)     # the mesh's turn (D-44 #5 P3)
    pts = np.stack([Xr, Y, Zr], -1).reshape(-1, 3) - busw
    az, el, d = azel(pts - EYE)
    tr = np.exp(-dens * d)
    vis = inside(az, el) & (tr > 0.1)
    allv = (tr > 0.1) & (el > -40) & (el < 40)
    return dict(in_view_pct=round(100.0 * vis.mean(), 2), visible_any_dir=bool(allv.any()),
                az_range_visible=[round(float(az[allv].min()), 1), round(float(az[allv].max()), 1)] if allv.any() else None)


def warm_at(t, depth):
    if t < U['F5']:
        return dict(on=False)
    busw = np.array([0.0, -depth, AM.fwd(t)])
    az, el, d = azel(np.asarray(U['warm_position']) - busw - EYE)
    return dict(on=True, az=round(float(az), 1), el=round(float(el), 1), dist=round(float(d), 1), in_view=bool(inside(az, el)))


def window_at(t):
    """Snell's window: elevation >= 41.4 deg (overhead); the forward field tops out at +25: never in it"""
    return dict(in_view=False, el_min=41.4, roof='whole' if t < 387 else 'eroding from the skylight edge')


def main():
    rows = []
    for t, name in BEATS:
        depth = AM.depth(t); dens = water_density(depth)
        r = dict(t=t, beat=name, depth=round(depth, 1), fog_per_m=round(dens, 4), see_10m=round(math.exp(-dens * 10), 2),
                 see_30m=round(math.exp(-dens * 30), 2), shafts=shafts_at(t, depth, dens), window=window_at(t),
                 ridge=ridge_at(t, depth, dens), warm=warm_at(t, depth), **particles_at(t, depth, dens))
        last = t - U['last_t0']
        r['last_shaft'] = 'sweeping overhead (bus frame from (3,14,-2) to (-1.5,14,4.5)): above the windscreen' if 0 < last < 8 else 'off'
        rows.append(r)
    out = _arg('--out', os.path.join(PKG, 'Docs~', 'forward_view_7a.json'))
    json.dump(dict(field=dict(az=AZ, el=EL, eye=EYE.tolist()), beats=rows), open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    for r in rows:
        print(r['t'], r['beat'], '| shafts', r['shafts'].get('in_view'), '| snow', r['snow']['in_view'], '| seeds', r['seeds'],
              '| trails', r['trails'].get('pool_in_view'), '| front', r.get('trails_front', {}).get('pool_in_view'), '| ridge', r['ridge']['in_view_pct'], '| last', r['last_shaft'][:8], '| warm', r['warm'])
    print('wrote', out)


if __name__ == '__main__':
    main()
