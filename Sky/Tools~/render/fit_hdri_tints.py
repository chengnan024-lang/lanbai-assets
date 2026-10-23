"""Fit Lanbai/Sky's three tints (+ the tint elevations) so the act's HDRI shows the bible's screen targets under the
act's grade; the regions the HDRI cannot reach by tints (earth shadow, Venus belt, ...) are left to the horizon
bands. Every evaluation runs the real LanbaiSkyLayers.cginc on the CPU. Usage: fit_hdri_tints.py dawn|dusk"""
import json, sys, os
import numpy as np
from scipy.optimize import least_squares
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky_cpu as S, grade as G

CFG = {
    'dawn': dict(hdri='syferfontein_6d_clear_puresky_1k.hdr', sid='S6', rot=-80.7, sun_az=45.0,
                 targets={  # region: (az0, az1 relative to the sun, el0, el1), screen target (bible §6·6 / calib)
                     'zenith': ((-180, 180), (84, 89.5), '#3E64A6'),
                     'anti45': ((165, 195), (40, 50), '#AFC4E0'),
                     'sunhor': ((-25, 25), (0.5, 6), '#F2C79A'),
                     'sun30': ((-30, 30), (25, 35), '#B4C6D8'),   # no bible number: pale blue over the sun (no mauve), keeps 'white with blue and gold'
                     'antihor': ((160, 200), (5, 8), '#AEB8CC'),  # between the earth shadow #8C98B8 and the pearl belt
                     'sun12': ((-30, 30), (10, 16), '#E2D9CC'),   # no bible number: warm pearl-white above the gold (no mauve)
                     'side15': ((80, 100), (10, 20), '#B8C6D8'),  # no bible number: pale blue at the side windows
                 }),
    'dusk': dict(hdri='syferfontein_0d_clear_puresky_1k.hdr', sid='S8', rot=None, sun_az=0.0,
                 targets={
                     'zenith': ((-180, 180), (80, 89.5), '#3D4A80'),
                     'midsky': ((-60, 60), (35, 55), '#808AB2'),
                     'midback': ((120, 240), (25, 45), '#808AB2'),
                     'midside': ((70, 110), (20, 40), '#808AB2'),
                     'lowback': ((140, 220), (10, 20), '#7E88AE'),   # no bible number: indigo-grey above the rose band (h < 285)
                     'lowside': ((70, 110), (6, 16), '#9C8FA6'),     # no bible number: the warm -> indigo turn at the side, kept grey
                     'sunhor': ((-20, 20), (0.5, 6), '#FFB070'),
                 }),
}


def dirs(az0, az1, el0, el1, sun_az, n=20):
    a = np.radians(np.linspace(az0, az1, n) + sun_az); e = np.radians(np.linspace(el0, el1, n))
    A, E = np.meshgrid(a, e)
    return np.stack([np.sin(A) * np.cos(E), np.sin(E), np.cos(A) * np.cos(E)], -1).reshape(-1, 3).astype(np.float32)


def inv_screen(hexs, sid):
    """fill (linear) whose screen colour under sid is hexs (Gauss-Newton on the engine)."""
    t = np.array([int(hexs[i:i + 2], 16) for i in (1, 3, 5)], np.float64)
    x = G.hexlin(hexs) * 1.3
    for _ in range(30):
        s = G.screen_of_fill(x, sid)
        J = np.zeros((3, 3))
        for k in range(3):
            d = np.zeros(3); d[k] = x[k] * 0.01 + 1e-5
            J[:, k] = (G.screen_of_fill(x + d, sid) - s) / d[k]
        x = np.maximum(x + np.linalg.lstsq(J, t - s, rcond=None)[0], 1e-5)
    return x


def main(name):
    c = CFG[name]
    hdr = S.load_hdr(os.path.join(G.REPO, 'FromLocal', 'hdri', 'hdr', c['hdri']))
    S.set_cube('_CubeA', hdr)
    rot = c['rot']
    if rot is None:   # find the HDRI sun (brightest after a blur) and rotate it to sun_az
        lum = hdr @ np.array([0.2126, 0.7152, 0.0722])
        from scipy import ndimage
        lb = ndimage.gaussian_filter(lum, 2)
        y, x = np.unravel_index(np.argmax(lb[: hdr.shape[0] // 2]), lb.shape)
        phi = (0.5 - (x + 0.5) / hdr.shape[1]) * 2 * np.pi; th = (y + 0.5) / hdr.shape[0] * np.pi
        d = np.array([np.sin(th) * np.cos(phi), np.cos(th), np.sin(th) * np.sin(phi)])
        az_src = np.degrees(np.arctan2(d[0], d[2]))
        rot = c['sun_az'] - az_src
        print('HDRI sun az %.2f el %.2f -> rotation %.2f' % (az_src, 90 - np.degrees(th), rot))
    regions = {k: (dirs(*v[0], *v[1], c['sun_az']), inv_screen(v[2], c['sid'])) for k, v in c['targets'].items()}
    sun = np.array([np.sin(np.radians(c['sun_az'])), 0.1, np.cos(np.radians(c['sun_az']))])

    def params(p):
        return dict(_RotationA=rot, _SunGain=0, _ZenithTintA=(*np.exp(p[0:3]), 1), _HorizonTintA=(*np.exp(p[3:6]), 1),
                    _HorizonAntiTintA=(*np.exp(p[6:9]), 1), _MidTintA=(*np.exp(p[12:15]), 1),
                    _TintElevation=(p[9], p[10], zen_end(p), 1.0), _SunDir=(*sun, 0))

    def zen_end(p):   # the zenith zone always ends AT 90 (no cone, no flat cap with a ring): p[11] unused
        return 90.0

    def resid(p):
        r = []
        P = params(p)
        for k, (d, f) in regions.items():
            m = S.render(d, P).mean(0)
            r.extend(np.log(np.maximum(m, 1e-6) / f))
        r.extend(0.03 * (p[6:9] - p[3:6]))     # weak pull: anti-sun tint near the sunward one
        r.extend(0.03 * np.r_[p[0:9], p[12:15]])   # and every tint near 1
        return np.array(r)

    lo = np.r_[-np.ones(9) * 3, 1.0, 12.0, 0.0, -np.ones(3) * 3]   # mid -> zenith over >= 30 deg: no lid overhead
    hi = np.r_[np.ones(9) * 3, 10.0, 60.0, 1e-3, np.ones(3) * 3]   # mid <= 60: >= 30 deg to the zenith
    res = None
    for y0, f0 in ((30.0, 0.0), (20.0, 0.0), (45.0, 0.0), (55.0, 0.0)):   # a few starts: the elevations make it non-convex
        p0 = np.full(15, 0.01); p0[9] = 4.0; p0[10] = y0; p0[11] = f0
        r = least_squares(resid, p0, bounds=(lo, hi), diff_step=1e-2, x_scale=np.r_[np.ones(9), 2.0, 10.0, 0.3, np.ones(3)])
        print('start', y0, f0, 'cost %.5f' % r.cost)
        if res is None or r.cost < res.cost:
            res = r
    P = params(res.x)
    out = {'act': name, 'hdri': c['hdri'], 'rotation': round(float(rot), 2), 'profile': c['sid'], 'tints': {}}
    for k in ('_ZenithTintA', '_MidTintA', '_HorizonTintA', '_HorizonAntiTintA'):
        out['tints'][k] = [round(float(v), 4) for v in P[k][:3]]
    out['tints']['_TintElevation'] = [round(float(res.x[9]), 2), round(float(res.x[10]), 2), round(float(zen_end(res.x)), 2), 1.0]
    out['check'] = {}
    for k, (d, f) in regions.items():
        m = S.render(d, P).mean(0)
        out['check'][k] = {'target': c['targets'][k][2], 'got': G.to_hex(G.screen_of_fill(m, c['sid']))}
    print(json.dumps(out, indent=1))
    json.dump(out, open(os.path.join(G.REPO, 'Sky', 'Data', 'fit_%s.json' % name), 'w'), indent=1)


if __name__ == '__main__':
    main(sys.argv[1])
