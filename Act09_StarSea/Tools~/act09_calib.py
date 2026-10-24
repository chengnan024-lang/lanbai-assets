"""第 9 幕 · 星的亮度标定 + 银河点燃线 g(t)（圣经 v2.1 §6·9 9b、§1.8、E18）。
Renders the real Lanbai/Sky code (CPU) + the star splat with the Lanbai/StarPoints formula, grades with S9a
(engine + bloom), measures the frame's mean display-linear luminance L per view, then
  1. checks the F13 frame (all stars at once, glow 0) stays under the ramp floor 0.004 in every view (= +0.00 EV),
  2. builds g(t) over 4.2 s from the most extreme view (final review r1 #1: one breath, no pop and stall):
       0 .. T_EASE  : g eases from 0 to the g where that view's L crosses the ramp floor 0.004 (a cubic that starts
                      flat and joins the next part with the same slope: no step, no stall);
       T_EASE .. T  : L EV-linear from the floor to L(full);
  3. the core leads (LanbaiGalaxyGainAt, Common/Shaders/LanbaiSky.cginc): the arms run g(t), the core runs the same
     curve `lead` seconds ahead: its below-floor ease is `lead` shorter (it starts at F13 too, never before), then the
     arms' EV-linear part shifted by `lead` (the same EV rate: a time shift, not a faster curve, so no view climbs
     faster than the arms do), full `lead` seconds early. lead = the largest of 0.3 / 0.2 / 0.1 / 0 that
     passes the ramp law (0.25 s <= 0.5 EV, 1 s <= 1.0, 2 s <= 1.8) and stays monotone in every view, measured on the
     frames as rendered (per-pixel gain), not on a uniform-gain model.
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
T_EASE = 0.7
LEADS = (0.3, 0.2, 0.1, 0.0)   # <= 0.3: the core's own ease stays >= 0.4 s (0.5 would leave it 0.2 s, a pop again)
GC = np.array([-0.489074, 0.207912, 0.847101]); NGP = np.array([0.866025, 0.0, 0.5])   # = LanbaiGalaxyCoreWeight


def load_glow():
    return S.load_glow(1)     # normalised; the preset material carries _GlowScale


def lum_display(codes):
    c = np.clip(codes / 255.0, 0, 1)
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float((lin @ np.array([0.2126, 0.7152, 0.0722])).mean())


def core_weight(d):
    """= LanbaiGalaxyCoreWeight (Common/Shaders/LanbaiSky.cginc)."""
    p = d - (d @ NGP)[:, None] * NGP[None, :]
    c = (p @ GC) / np.sqrt(np.maximum((p * p).sum(1), 1e-8))
    l = np.degrees(np.arccos(np.clip(c, -1, 1)))
    t = np.clip((l - 15.0) / 45.0, 0, 1)
    return 1 - t * t * (3 - 2 * t)


class Act9Frame:
    def __init__(self):
        S.renderer().tex.clear()
        S.set_tex('_GlowTex', load_glow())
        self.p = dict(MP.P['star_sea'])
        self.p['material'] = dict(self.p['material'], _GlowScale=S.glow_scale())   # the PNG glow is normalised (Sky v1.2)
        self.cat = SC.catalogue()
        self.base = {}

    def sky(self, view, g, gc=None):
        # the sky is linear in the galaxy gain per pixel (night + gain x (floor + glow), then a lerp): render gain 0 and 1
        # once, 2 x 2 supersampled (the 8K glow has 0.044 deg texels, a 960 px pixel is 0.094 deg), and keep
        # a = sky(0), b - a, and mean((b - a) x core weight), so the arms at g and the core at gc are exact:
        # sky = a + (b - a) g + ((b - a) w) (gc - g)
        if view not in self.base:
            yaw, pitch = VIEWS[view]
            d2 = camera_dirs(W * 2, H * 2, 90, yaw, pitch).astype(np.float32)
            ends = []
            for gg in (0.0, 1.0):
                gl = dict(self.p['globals']); gl['_Udon_GalaxyGain'] = [gg, 0, 0, 1]
                ends.append(S.render(d2, self.p['material'], gl).reshape(H * 2, W * 2, 3))
            w = core_weight(d2.astype(np.float64)).reshape(H * 2, W * 2, 1)
            red = lambda x: x.reshape(H, 2, W, 2, 3).mean(axis=(1, 3))
            self.base[view] = (red(ends[0]), red(ends[1] - ends[0]), red((ends[1] - ends[0]) * w))
        a, ba, baw = self.base[view]
        return a + ba * g + (0.0 if gc is None else baw * (gc - g))

    def frame(self, view, g, star_gain, boost=4.0, count=50.0, profile='S9a', glow_mult=1.0, gc=None):
        img = self.sky(view, g * glow_mult, None if gc is None else gc * glow_mult)
        if star_gain > 0:   # the stars add linearly: splat once per view and setting
            key = ('stars', view, star_gain, boost, count)
            if key not in self.base:
                c = self.cat
                pk = SC.flux(c['mag'], c['rank'], STAR['scale'], STAR['mag_ref'], STAR['slope'], count, boost) * star_gain
                self.base[key] = SC.splat(np.zeros((H, W, 3)), W, H, 90, *VIEWS[view], c['dir'], pk, c['col'], FWHM)
            img = img + self.base[key]
        return img, np.clip(G.grade(img, profile), 0, 255)


def ease_table(ts, curve, gs, T, te, shift=0.0):
    """g(t): a cubic from (0, 0, slope 0) to (te - shift, g_floor, the EV-linear part's slope), then L EV-linear to
    L(full), that part taken `shift` seconds ahead (shift = 0: the arms; shift = lead: the core); 1 after it ends."""
    Lf, Lg = 0.004, curve[-1]
    lin = lambda t: np.interp(Lf * (Lg / Lf) ** ((np.clip(t, te, T) - te) / (T - te)), curve, gs)
    gf = float(lin(te)); s1 = float((lin(te + 0.01) - gf) / 0.01)
    e = te - shift
    s1 = min(s1, 3 * gf / e)                      # keeps the cubic monotone
    u = np.clip(ts / e, 0, 1)
    cub = gf * (3 * u ** 2 - 2 * u ** 3) + s1 * e * (u ** 3 - u ** 2)
    g = np.where(ts < e, cub, lin(ts + shift))
    g[0] = 0.0; g[ts >= T - shift - 1e-9] = 1.0
    return g, gf


def g_at(ts, gtab, s):
    return np.interp(np.clip(s, 0, ts[-1]), ts, gtab)


def ramp(ev):
    def worst(win):
        n = int(round(win / 0.05)); return float(max(ev[i + n] - ev[i] for i in range(len(ev) - n)))
    r = dict(w025=round(worst(0.25), 3), w1=round(worst(1.0), 3), w2=round(worst(2.0), 3))
    r['PASS'] = r['w025'] <= 0.5 and r['w1'] <= 1.0 and r['w2'] <= 1.8
    return r


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
    T = T_IGN
    res['ignition_s'] = float(T)
    ts = np.round(np.arange(0, T + 1e-6, 0.05), 2)
    gtab, gf = ease_table(ts, curves[ext], gs, T, T_EASE)
    res['extreme_view'] = ext
    res['g_table'] = {'t_from_F13_s': ts.tolist(), 'g': [round(float(x), 4) for x in gtab], 'ease_s': T_EASE, 'g_floor': round(gf, 4),
                      'how': 'the arms: 0 .. %.1f s a cubic from g 0 (flat start) to the g where the extreme view crosses the floor 0.004, '
                             'then L EV-linear to L(full) at %.1f s; the core (g_core): the same, its ease `lead` shorter and the '
                             'EV-linear part `lead` seconds ahead' % (T_EASE, T)}
    # ramp law per view on the rendered frames (arms g(t), core g(t T / (T - lead)), stars from F13), 0.05 s steps
    fine_t = np.round(np.arange(0, T + 2.0001, 0.05), 2)
    chosen = None
    for lead in LEADS:
        ctab = ease_table(ts, curves[ext], gs, T, T_EASE, lead)[0] if lead > 0 else gtab
        law, Ls = {}, {}
        for v in VIEWS:
            Lv = np.array([lum_display(A.frame(v, g_at(ts, gtab, t), 1.0, gc=g_at(ts, ctab, t))[1]) for t in fine_t])
            Ls[v] = Lv
            law[v] = ramp(np.log2(np.maximum(Lv, 0.004)))
            law[v]['monotone'] = bool(np.all(np.diff(Lv) >= -1e-6))
        ok = all(law[v]['PASS'] and law[v]['monotone'] for v in VIEWS)
        print('lead %.1f s' % lead, 'PASS' if ok else 'FAIL', json.dumps(law))
        if ok:
            chosen = lead; res['ramp_law'] = law
            res['g_table']['g_core'] = [round(float(x), 4) for x in ctab]
            res['L_t'] = {v: [round(float(x), 6) for x in Ls[v]] for v in VIEWS}
            break
    res['core_lead_s'] = chosen
    res['core_weight'] = 'LanbaiGalaxyCoreWeight: 1 within 15 deg of galactic longitude of the centre, 0 beyond 60 deg (smoothstep)'
    os.makedirs(os.path.join(REPO, 'Act09_StarSea', 'Data'), exist_ok=True)
    json.dump(res, open(os.path.join(REPO, 'Act09_StarSea', 'Data', 'ignition.json'), 'w'), indent=1)
    print('extreme view', ext, 'core lead', chosen)


if __name__ == '__main__':
    main()
