"""D-06 star check (acts 3 and 4: the same star set, the same gain across the 3 -> 4 seam).

Rules (Art/总导演裁决.md D-06, bible §6·4): only the bright stars under the moon (magnitude < 3, _Udon_StarShape.x),
no galaxy, one EV darker inside the act-4 haze band (_Udon_StarShape.y = -1), every star >= 1.5 px FWHM at 1080p,
L* <= 12. Read as: the brightest star stands at most 12 CIE L* above its own sky in the graded 1080p frame (desktop,
90 deg). (An absolute L* <= 12 cannot hold: the moonlit horizon sky alone is above L* 12, so no star could be there.)
Moon disc +-3 deg excluded.

Usage: check_stars.py [--solve]   --solve: the largest _Udon_StarGain.x that passes both acts (binary search);
without it: checks the gain written in make_presets.py (moon_night) and exits 1 on a failure."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import make_presets as MP, sky_cpu as S, grade as G, stars_cpu as SC
from shader_cpu import camera_dirs

W, H, HFOV = 1920, 1080, 90.0
FWHM_PX = 1.6                       # Lanbai/StarPoints _FWHM (Range 1.5 .. 4)
MAG_FLOOR = 3.0                     # bible §6·4 at U6: 'only the stars brighter than magnitude 3'
BAND_EV = -1.0
VIEWS = [('up60', 0, 60), ('zenith', 30, 88), ('back', 180, 35), ('front', 0, 20)]
L_MAX = 12.0


def act_globals(act):
    p = MP.P['moon_night']
    g = dict(p['globals'])
    if p.get('fog_from_sky'):
        g.update(MP.fog_group(p))
    if act == 4:   # the gate's sky (model A = LanbaiGateSky's band, FogPresets act4_gate), the tear straight ahead
        a = MP.GATE_ACT4
        g.update(_Udon_FogModel=[0.0, 0, 0, 1], _Udon_FogBandColor=[*a['near'], 1.0], _Udon_HorizonColor=[*a['far'], 1.0],
                 _Udon_ZenithColor=[*a['zenith'], 1.0], _Udon_FogShape=list(a['shape']), _Udon_FogBelow=list(a['below']),
                 _Udon_FogBandWidth=a['width'], _Udon_FogBandDir=[*MP.dir_az_el(0.0, 0.0), 1.0])
        g.pop('_Udon_HorizonColor_model', None)
    return p, g


def band_weight(dirs, width):
    az = np.degrees(np.abs(np.arctan2(dirs[:, 0], dirs[:, 2])))
    el = np.degrees(np.arcsin(np.clip(dirs[:, 1], -1, 1)))
    s = lambda e0, e1, x: np.clip((x - e0) / (e1 - e0), 0, 1) ** 2 * (3 - 2 * np.clip((x - e0) / (e1 - e0), 0, 1))
    return (1 - s(width, width + 10, az)) * (1 - s(10, 25, el))


def max_star_L(act, gain, cache={}):
    p, g = act_globals(act)
    prof = 'S3' if act == 3 else 'S4'
    cat = SC.catalogue()
    keep = cat['mag'] <= MAG_FLOOR
    pk = SC.flux(cat['mag'], cat['rank'], 1.6, 0.0, 0.5, 1.0, 1.0) * gain
    if act == 4:
        pk = pk * np.exp2(BAND_EV * band_weight(cat['dir'], MP.GATE_ACT4['width']))
    pk = np.where(keep, pk, 0.0)
    moon = np.array(g['_Udon_MoonDir'][:3], float); moon /= np.linalg.norm(moon)
    worst = 0.0
    for name, yaw, pitch in VIEWS:
        key = (act, name)
        if key not in cache:
            S.renderer().tex.clear()
            d = camera_dirs(W, H, HFOV, yaw, pitch).astype(np.float32)
            cache[key] = (d, S.render(d, p['material'], g).reshape(H, W, 3))
        d, sky = cache[key]
        img = SC.splat(sky.copy(), W, H, HFOV, yaw, pitch, cat['dir'], pk, cat['col'], FWHM_PX, snap=True)   # worst case (tech r2 #5)
        add = (img - sky).max(axis=2)
        away = np.degrees(np.arccos(np.clip(d.reshape(H, W, 3) @ moon, -1, 1))) > 3.0
        m = (add > 1e-5) & away
        if not m.any():
            continue
        if ('L', key) not in cache:
            cache[('L', key)] = G.lab(np.clip(G.grade(sky, prof), 0, 255))[0]
        L = G.lab(np.clip(G.grade(img, prof), 0, 255))[0]
        worst = max(worst, float((L - cache[('L', key)])[m].max()))
    return worst


def moon_gain():
    return float(MP.P['moon_night']['globals']['_Udon_StarGain'][0])


def main():
    if '--solve' in sys.argv:
        lo, hi = 0.0, 1.0
        for _ in range(12):
            mid = 0.5 * (lo + hi)
            ok = max(max_star_L(3, mid), max_star_L(4, mid)) <= L_MAX
            lo, hi = (mid, hi) if ok else (lo, mid)
        print('largest passing _Udon_StarGain.x = %.3f' % lo)
        return
    gain = moon_gain()
    res = {a: round(max_star_L(a, gain), 2) for a in (3, 4)}
    ok = all(v <= L_MAX for v in res.values()) and FWHM_PX >= 1.5
    out = dict(rule='D-06', gain=gain, mag_floor=MAG_FLOOR, band_ev=BAND_EV, fwhm_px=FWHM_PX, max_star_dLstar=res, L_max=L_MAX, ok=ok)
    print(json.dumps(out, ensure_ascii=False))
    json.dump(out, open(os.path.join(MP.REPO, 'Sky', 'Data', 'stars_D06.json'), 'w'), indent=1, ensure_ascii=False)
    sys.exit(0 if ok else 1)


if __name__ == '__main__':
    main()
