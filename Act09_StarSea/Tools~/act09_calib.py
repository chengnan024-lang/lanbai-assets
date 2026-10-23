"""第 9 幕 · 星的亮度标定 + 银河点燃线 g(t)（圣经 v2.1 §6·9 9b、§1.8、E18）。
Renders the real Lanbai/Sky code (CPU) + the star splat with the Lanbai/StarPoints formula, grades with S9a
(engine + bloom), measures the frame's mean display-linear luminance L per view, then
  1. checks the F13 frame (all stars at once, glow 0) stays under the ramp floor 0.004 in every view (= +0.00 EV),
  2. builds g(t) over 4.2 s from the most extreme view so L is EV-linear from L(F13) to L(full), and checks the
     ramp law (0.25 s <= 0.5 EV, 1 s <= 1.0, 2 s <= 1.8) for every view under that same curve.
Usage: ~/bpy/bin/python -I act09_calib.py  -> Act09_StarSea/Data/ignition.json + Docs~/calib_*.png"""
import json, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
import sky_cpu as S, grade as G, stars_cpu as SC
from shader_cpu import camera_dirs
import make_presets as MP

W, H = 960, 540
FWHM = 1.6 * W / 1920.0          # the reference camera is 1920 wide; same angular star size at half resolution
VIEWS = {'front': (0, 0), 'up60': (0, 60), 'zenith85': (0, 85), 'galactic_centre': (-30, 12), 'down60': (0, -60)}
STAR = dict(scale=1.6, mag_ref=0.0, slope=0.5, bright_count=50.0, bright_boost=4.0)
T_IGN = 4.2


def load_glow():
    return S.load_glow(1)     # normalised; the preset material carries _GlowScale


def lum_display(codes):
    c = np.clip(codes / 255.0, 0, 1)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float((lin @ np.array([0.2126, 0.7152, 0.0722])).mean())


class Act9Frame:
    def __init__(self):
        S.renderer().tex.clear()
        S.set_tex('_GlowTex', load_glow())
        self.p = dict(MP.P['star_sea'])
        self.p['material'] = dict(self.p['material'], _GlowScale=S.glow_scale())   # the PNG glow is normalised (Sky v1.2)
        self.cat = SC.catalogue()
        self.dirs = {k: camera_dirs(W, H, 90, *v).astype(np.float32) for k, v in VIEWS.items()}
        self.base = {}

    def sky(self, view, g):
        # the sky is linear in the galaxy gain (night + g x (floor + glow), then a lerp): render g = 0 and g = 1 once,
        # 2 x 2 supersampled (the 8K glow has 0.044 deg texels, a 960 px pixel is 0.094 deg), and interpolate
        if view not in self.base:
            yaw, pitch = VIEWS[view]
            d2 = camera_dirs(W * 2, H * 2, 90, yaw, pitch).astype(np.float32)
            ends = []
            for gg in (0.0, 1.0):
                gl = dict(self.p['globals']); gl['_Udon_GalaxyGain'] = [gg, 0, 0, 1]
                ends.append(S.render(d2, self.p['material'], gl).reshape(H, 2, W, 2, 3).mean(axis=(1, 3)))
            self.base[view] = ends
        a, b = self.base[view]
        return a + (b - a) * g

    def frame(self, view, g, star_gain, boost=4.0, count=50.0, profile='S9a', glow_mult=1.0):
        img = self.sky(view, g * glow_mult)
        if star_gain > 0:
            c = self.cat
            pk = SC.flux(c['mag'], c['rank'], STAR['scale'], STAR['mag_ref'], STAR['slope'], count, boost) * star_gain
            SC.splat(img, W, H, 90, *VIEWS[view], c['dir'], pk, c['col'], FWHM)
        return img, np.clip(G.grade(img, profile), 0, 255)


def main():
    A = Act9Frame()
    res = {'views': {}, 'star_params': STAR, 'resolution': [W, H], 'fwhm_px_at_1920': 1.6}
    gs = np.linspace(0, 1, 11)
    curves = {}
    for v in VIEWS:
        L0 = lum_display(A.frame(v, 0.0, 0.0)[1])
        L = [lum_display(A.frame(v, g, 1.0)[1]) for g in gs]
        curves[v] = L
        res['views'][v] = dict(L_floor=L0, L_F13=L[0], L_full=L[-1], ev_full_over_F13=float(np.log2(max(L[-1], 0.004) / max(L[0], 0.004))),
                               F13_under_floor=bool(L[0] < 0.004), APL_full=round(G.apl(A.frame(v, 1.0, 1.0)[1]), 1),
                               APL_F13=round(G.apl(A.frame(v, 0.0, 1.0)[1]), 1))
        print(v, json.dumps(res['views'][v]))
    # the extreme view = the largest EV span (it needs the slowest curve); bible: front
    ext = max(VIEWS, key=lambda v: res['views'][v]['ev_full_over_F13'])
    Lc, Lg = max(curves[ext][0], 0.004), curves[ext][-1]
    # speed-limited, not duration-limited (bible §1.8 E17 principle): T = EV span of the extreme view / 0.85 EV/s,
    # never shorter than the bible's 4.2 s
    T = max(T_IGN, np.ceil(np.log2(Lg / Lc) / 0.85 / 0.05) * 0.05)
    res['ignition_s'] = float(T)
    ts = np.round(np.arange(0, T + 1e-6, 0.05), 2)
    target = Lc * (Lg / Lc) ** (ts / T)
    gtab = np.interp(target, curves[ext], gs)
    gtab[0] = 0.0; gtab[-1] = 1.0
    res['extreme_view'] = ext
    res['g_table'] = {'t_from_F13_s': ts.tolist(), 'g': [round(float(x), 4) for x in gtab],
                      'how': 'L(t) = L(F13) x (L(full) / L(F13))^(t / T) in the extreme view, L floored at 0.004, T = its EV span / 0.85; g = the glow gain giving L(t)'}
    # ramp law per view under this curve (finer: interpolate L(g) per view)
    fine_t = np.arange(0, T + 2.0001, 0.05)
    g_f = np.interp(np.minimum(fine_t, T), ts, gtab)
    law = {}
    for v in VIEWS:
        Lv = np.interp(g_f, gs, curves[v])
        ev = np.log2(np.maximum(Lv, 0.004))
        def worst(win):
            n = int(round(win / 0.05)); return float(max(ev[i + n] - ev[i] for i in range(len(ev) - n)))
        law[v] = dict(w025=round(worst(0.25), 3), w1=round(worst(1.0), 3), w2=round(worst(2.0), 3))
        law[v]['PASS'] = law[v]['w025'] <= 0.5 and law[v]['w1'] <= 1.0 and law[v]['w2'] <= 1.8
        print('ramp', v, law[v])
    res['ramp_law'] = law
    os.makedirs(os.path.join(REPO, 'Act09_StarSea', 'Data'), exist_ok=True)
    json.dump(res, open(os.path.join(REPO, 'Act09_StarSea', 'Data', 'ignition.json'), 'w'), indent=1)
    print('extreme view', ext)


if __name__ == '__main__':
    main()
