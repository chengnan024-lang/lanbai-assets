"""RainRipple flipbook (bible §1.6 / §6·1 puddles) + two radial LUTs for the procedural path and the drips.

Flipbook: 8x8 frames x 256 px, one frame = 0.5 m x 0.5 m of puddle, loop 2.0 s (32 fps), 10 drops per tile per loop.
Seamless in space (every ripple is summed over its 3x3 periodic images) and in time (age = (t - t0) mod LOOP and
every ripple is dead before LIFE < LOOP).
Unity tangent-space normal (+X = +u, +Y = +v = up in the PNG), linear.  Frame 0 = top-left, row-major.
"""
import json, os, sys
import numpy as np
from PIL import Image
from ripple_physics import RadialSolver

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rainpaths as RP
OUT = sys.argv[1] if len(sys.argv) > 1 else RP.out_dir()
os.makedirs(OUT, exist_ok=True)
rng = np.random.default_rng(20260930)

TILE = 0.5; LOOP = 2.0; NF = 64; NS = 8; FPX = 256; SS = 2
N_DROPS = 10
LIFE = 1.25; FADE0 = 0.90                  # age window (s)
R_TAPER = (0.22, 0.29)                     # radial window (m); profile solved to 0.30
SLOPE_REF = 0.28                           # physical max slope of a median drop at age 0.15 s
SLOPE_CLAMP = 1.2

S = RadialSolver(r_max=0.30, n_r=1500, k_max=2600.0, n_k=1400, depth=0.012)


def blue_noise_points(n, min_d, tries=5000):
    pts = []
    while len(pts) < n:
        for _ in range(tries):
            p = rng.random(2)
            ok = True
            for q in pts:
                d = np.abs(p - q); d = np.minimum(d, 1 - d)
                if np.hypot(*d) < min_d:
                    ok = False; break
            if ok:
                pts.append(p); break
        else:
            min_d *= 0.9
    return np.array(pts)


def make_drops(n, loop, min_d, d_med_mm=0.95, sig=0.30, jet_p=0.45):
    pos = blue_noise_points(n, min_d)
    order = rng.permutation(n)
    t0 = (order + rng.uniform(0.1, 0.9, n)) * loop / n            # stratified births: no bursts, no lulls
    D = np.clip(rng.lognormal(np.log(d_med_mm), sig, n), 0.5, 1.9)  # drizzle drop diameters (mm)
    drops = []
    for i in range(n):
        a = 2.4e-3 * D[i]                                          # crater ~2.4 D
        amp = (D[i] / d_med_mm) ** 1.5
        jet = None
        if D[i] > 0.9 and rng.random() < jet_p:                    # Worthington jet falls back at the centre
            jet = (float(rng.uniform(0.08, 0.14)), 0.6 * a, float(rng.uniform(0.25, 0.45)))
        drops.append(dict(u=float(pos[i, 0]), v=float(pos[i, 1]), t0=float(t0[i]), D_mm=float(D[i]), a=a, amp=amp, jet=jet))
    return drops


def calib():
    a = 2.4e-3 * 0.95
    _, s = S.profile(a, 1.0, 0.15)
    return SLOPE_REF / np.abs(s).max()


K = calib()


def age_window(age):
    x = np.clip((age - FADE0) / (LIFE - FADE0), 0, 1)
    return 1 - x * x * (3 - 2 * x)


r_win = 1 - np.clip((S.r - R_TAPER[0]) / (R_TAPER[1] - R_TAPER[0]), 0, 1) ** 2 * (3 - 2 * np.clip((S.r - R_TAPER[0]) / (R_TAPER[1] - R_TAPER[0]), 0, 1))


def frame_slopes(drops, t, npx, tile):
    """returns slope field (sx, sy) on an npx^2 grid, y up."""
    xs = (np.arange(npx) + 0.5) / npx * tile
    X, Y = np.meshgrid(xs, xs)                                     # Y[row] increases with row -> y up if we flip at write
    sx = np.zeros((npx, npx)); sy = np.zeros((npx, npx))
    for d in drops:
        age = (t - d['t0']) % LOOP
        if age >= LIFE:
            continue
        _, s = S.profile(d['a'], d['amp'] * K, age, d['jet'])
        s = s * r_win * age_window(age)
        cx, cy = d['u'] * tile, d['v'] * tile
        for ox in (-1, 0, 1):
            for oy in (-1, 0, 1):
                dx = X - (cx + ox * tile); dy = Y - (cy + oy * tile)
                r = np.hypot(dx, dy)
                m = r < S.r[-1]
                if not m.any():
                    continue
                sv = np.interp(r[m], S.r, s)
                rr = np.maximum(r[m], 1e-6)
                sx[m] += sv * dx[m] / rr
                sy[m] += sv * dy[m] / rr
    return sx, sy


def encode_normal(sx, sy):
    """slope field (y up, rows = +y) -> Unity normal-map RGB uint8 (PNG rows top = +v)."""
    mag = np.hypot(sx, sy)
    f = np.where(mag > 0, np.minimum(mag, SLOPE_CLAMP * np.tanh(mag / SLOPE_CLAMP)) / np.maximum(mag, 1e-9), 1)
    sx, sy = sx * f, sy * f
    n = np.stack([-sx, -sy, np.ones_like(sx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rgb = np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)
    return rgb[::-1]                                               # flip rows: row 0 of PNG = top = max y


def downsample(a, f):
    h, w = a.shape
    return a.reshape(h // f, f, w // f, f).mean((1, 3))


if __name__ == '__main__':
    drops = make_drops(N_DROPS, LOOP, min_d=0.16)
    atlas = np.zeros((NS * FPX, NS * FPX, 3), np.uint8)
    frames_s = []
    for f in range(NF):
        t = f * LOOP / NF
        sx, sy = frame_slopes(drops, t, FPX * SS, TILE)
        sx, sy = downsample(sx, SS), downsample(sy, SS)
        frames_s.append((sx, sy))
        rgb = encode_normal(sx, sy)
        r, c = divmod(f, NS)
        atlas[r * FPX:(r + 1) * FPX, c * FPX:(c + 1) * FPX] = rgb
        print('frame', f, 'max slope %.3f' % np.hypot(sx, sy).max(), flush=True)
    Image.fromarray(atlas).save(os.path.join(OUT, 'RainRipple_Flip8x8_2048.png'))
    np.save(os.path.join(OUT, 'ripple_slopes.npy'), np.array(frames_s, np.float32))
    json.dump(dict(TILE_M=TILE, LOOP_S=LOOP, FRAMES=NF, GRID='8x8', FRAME_PX=FPX, DROPS_PER_TILE_PER_LOOP=N_DROPS,
                   RATE_PER_M2_S=N_DROPS / (TILE * TILE * LOOP), LIFE_S=LIFE, SLOPE_REF=SLOPE_REF, SLOPE_CLAMP=SLOPE_CLAMP,
                   K=float(K), drops=drops), open(os.path.join(OUT, 'ripple_flipbook.json'), 'w'), indent=1)
