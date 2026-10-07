"""Radial ripple LUTs (u = radius, v = age), for shader-evaluated rings.

  RippleRing_LUT_256x128.png  : one median drizzle drop (D 0.95 mm) on a puddle; r 0..0.25 m, age 0..1.25 s.
                                Used by the procedural hero-puddle path (random cells) - bible rate 3-5 /m^2/s.
  DripRipple_LUT_512x256.png  : one 4.5 mm drip falling 2-4 m (lamp arm, sign edge, notice case, bible §5.4/§5.5);
                                r 0..0.5 m, age 0..2.5 s; main ring 0.4 m at 1.6 s, disturbance tau ~0.7 s, 0 at 2.5 s.
Encoding (linear PNG, sRGB OFF):
  R = 0.5 + 0.5 * s / gain(age)        s = d(eta)/dr, physical radial slope (dimensionless, + = surface rising outward)
  G = (log2(gain) + 12) / 14           gain(age) = exp2(G * 14 - 12)  (row constant)
  B, A = the same slope LOW-PASSED for a 4 mm pixel footprint (Gaussian exp(-(k/600)^2) on the wavenumber spectrum),
         same encoding (B = 0.5 + 0.5 s_low / gain_low, A = (log2(gain_low) + 12) / 14). v2: the shader blends R,G ->
         B,A by the pixel's footprint, so a fresh impact (slope up to 7 at 2 mm) no longer aliases into a moire disc.
Texel centres: u = (r / R_MAX) * (W - 1) / W + 0.5 / W ;  v = (age / T_MAX) * (H - 1) / H + 0.5 / H ; v = 0 at the
BOTTOM of the image (Unity convention), i.e. PNG row H-1 is age 0.
"""
import json, os, sys
import numpy as np
from PIL import Image
from ripple_physics import RadialSolver

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rainpaths as RP
OUT = sys.argv[1] if len(sys.argv) > 1 else RP.out_dir()


def smooth_win(x, a, b):
    t = np.clip((x - a) / (b - a), 0, 1)
    return 1 - t * t * (3 - 2 * t)


def build(name, W, H, R_MAX, T_MAX, a, jet, slope_ref, t_ref, depth, extra_tau, age_fade, r_fade, k_max, amp_scale=1.0):
    S = RadialSolver(r_max=R_MAX, n_r=W * 4, k_max=k_max, n_k=1400, depth=depth)
    _, s_ref = S.profile(a, 1.0, t_ref, jet)
    K = slope_ref / np.abs(s_ref).max()
    ages = np.linspace(0, T_MAX, H)
    R = np.zeros((H, W)); G = np.zeros((H, W)); B = np.zeros((H, W)); A = np.zeros((H, W))
    rs = np.linspace(0, R_MAX, W)
    rows = []
    for i, t in enumerate(ages):
        h, s = S.profile(a, K * amp_scale, t, jet)
        _, sl = S.profile(a, K * amp_scale, t, jet, kc=600.0)
        env = np.exp(-t / extra_tau) if extra_tau else 1.0
        env *= smooth_win(t, *age_fade)
        rw = smooth_win(S.r, *r_fade)
        s = np.interp(rs, S.r, s * rw) * env
        sl = np.interp(rs, S.r, sl * rw) * env
        g = max(np.abs(s).max(), 2 ** -12); gl = max(np.abs(sl).max(), 2 ** -12)
        R[i] = 0.5 + 0.5 * s / g; G[i] = (np.log2(g) + 12) / 14
        B[i] = 0.5 + 0.5 * sl / gl; A[i] = (np.log2(gl) + 12) / 14
        rows.append((float(t), float(g), float(gl)))
    img = np.stack([R, G, B, A], -1)[::-1]                      # age 0 at the bottom
    Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, name))
    return dict(file=name, W=W, H=H, R_MAX_M=R_MAX, T_MAX_S=T_MAX, crater_m=a, jet=jet, slope_ref=slope_ref, t_ref=t_ref,
                depth_m=depth, extra_tau_s=extra_tau, age_fade=age_fade, r_fade=r_fade, K=float(K),
                peak_slope_by_age=[(round(t, 3), round(g, 5), round(gl, 5)) for t, g, gl in rows[::max(1, H // 16)]],
                columns='age s, peak slope full band, peak slope 4 mm band-limited')


if __name__ == '__main__':
    meta = {}
    meta['ring'] = build('RippleRing_LUT_256x128.png', 256, 128, 0.25, 1.25, 2.4e-3 * 0.95, (0.11, 0.6 * 2.4e-3 * 0.95, 0.35),
                         0.28, 0.15, 0.012, None, (0.90, 1.25), (0.20, 0.25), 2600.0)
    meta['drip'] = build('DripRipple_LUT_512x256.png', 512, 256, 0.5, 2.5, 0.009, (0.19, 0.005, 0.5),
                         0.35, 0.20, 0.015, 2.3, (1.9, 2.5), (0.42, 0.5), 1500.0)
    json.dump(meta, open(os.path.join(OUT, 'ripple_luts.json'), 'w'), indent=1)
    print(json.dumps({k: (v['K'], v['peak_slope_by_age'][:6]) for k, v in meta.items()}, indent=0))
