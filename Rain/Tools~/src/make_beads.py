"""RainBeads textures (static drops for glass / enamel / paint): Normal + Data, two variants.

  RainBeads_Vertical   : windows, windscreen, sign face, bus body where it beads; gravity sag, a_crit 2.1 mm
  RainBeads_Horizontal : skylight top, notice-case top rim, bench, bonnet; round, a_crit 3.4 mm
Tile 0.20 m = 1024 px (0.195 mm / px). Heights in metres internally.
Data RGBA (linear): R = thickness  h / 2.5 mm
                    G = persistence threshold: bead visible while rainAmount > G (big beads low G, mist high G)
                    B = footprint coverage (anti-aliased 0..1)
                    A = bead size  a / 3 mm (contact radius)
G and A are dilated into the gaps (nearest bead), so bilinear filtering never mixes two beads' values at an edge.
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from beads_sim import Beads, cap_volume

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rainpaths as RP
OUT = sys.argv[1] if len(sys.argv) > 1 else RP.out_dir()
TILE = 0.20; N = 1024; SS = 2


def simulate(variant, seed):
    rng = np.random.default_rng(seed)
    a_crit = 2.1e-3 if variant == 'Vertical' else 3.4e-3
    B = Beads(TILE, a_crit, rng)
    target = 0.36 if variant == 'Vertical' else 0.44          # vertical saturates ~0.38 (steady state: growth = run-off)
    n = 0; hist = []
    while True:
        # deposited volumes: drizzle drops break on impact into a parent bead + splash-back mist
        D = np.clip(rng.lognormal(np.log(0.75e-3), 0.45), 0.2e-3, 2.4e-3)
        V = np.pi / 6 * D ** 3 * rng.uniform(0.35, 0.8)
        x, y = rng.random(2) * TILE
        B.deposit(x, y, V)
        for _ in range(rng.poisson(2.0)):              # splash-back micro-droplets 60-250 um
            ang = rng.uniform(0, 2 * np.pi); rr = rng.uniform(1.5, 6) * D
            d = rng.uniform(60e-6, 250e-6)
            B.deposit(x + rr * np.cos(ang), y + rr * np.sin(ang), np.pi / 6 * d ** 3)
        n += 1
        if n % 2000 == 0:
            cov = B.coverage()
            print(variant, n, 'beads', len(B.b), 'coverage %.3f' % cov, 'runners', B.runners, flush=True)
            hist.append(cov)
            if cov >= target or n >= 90000 or (len(hist) > 6 and max(hist[-6:]) - min(hist[-6:]) < 0.006 and cov > 0.3):
                break
    # a last light mist so gaps are never glass-clean (fine sparkle between big beads)
    for _ in range(int(9000 * (TILE / 0.2) ** 2)):
        d = rng.uniform(50e-6, 160e-6)
        B.deposit(*(rng.random(2) * TILE), np.pi / 6 * d ** 3)
    return B, rng


def rasterize(B, rng, variant):
    M = N * SS; px = TILE / M
    H = np.zeros((M, M)); ID = np.full((M, M), -1, np.int32)
    beads = list(B.b.values())
    order = np.argsort([d['a'] for d in beads])
    # persistence: rank by size with noise (small first to vanish)
    size_noise = np.array([d['a'] * np.exp(rng.normal(0, 0.35)) for d in beads])
    rank = np.argsort(np.argsort(-size_noise)) / len(beads)          # 0 = most persistent
    gvals = np.clip(rank * 0.985 + rng.uniform(0, 0.015, len(beads)), 0, 0.999)
    sag = variant == 'Vertical'
    for idx in order:
        d = beads[idx]
        a, th = d['a'], d['th']
        R = int(np.ceil(a * 1.5 / px)) + 2
        cx, cy = d['x'] / px, d['y'] / px
        ix0, iy0 = int(cx) - R, int(cy) - R
        xs = np.arange(ix0, ix0 + 2 * R + 1); ys = np.arange(iy0, iy0 + 2 * R + 1)
        X, Y = np.meshgrid((xs + 0.5) - cx, (ys + 0.5) - cy)
        X *= px; Y *= px                                             # metres, y up (rows = +y, flipped at write)
        # footprint: stretched along the merge axis, low-order pinning wobble
        ca, sa = np.cos(d['axis']), np.sin(d['axis'])
        u = X * ca + Y * sa; v = -X * sa + Y * ca
        e = d['elong']
        u = u / (1 + e); v = v * (1 + e) ** 0.5
        phi = np.arctan2(v, u)
        wob = 1.0
        amp = 0.02 + 0.06 * min(1.0, d['merges'] / 4) + 0.02 * (a > 1e-3)
        for k in (2, 3, 4, 5):
            wob = wob + amp / k ** 0.8 * rng.normal() * np.cos(k * phi + rng.uniform(0, 2 * np.pi))
        rad = np.hypot(u, v) / (a * wob)
        if sag:                                                      # heavier bottom: footprint and apex sink (Bond ~ a^2)
            bo = min(0.6, 1000 * 9.81 * a * a / 0.06)
            rad = rad * (1 + 0.10 * bo * (Y / a))
        rho2 = np.clip(rad, 0, 1) ** 2
        if a / px > 4.0:                                             # constant-mean-curvature dome inside the pinned outline
            inside = rad < 1
            phi = np.where(inside, 1 - rho2, 0.0)
            for _ in range(260):                                     # Jacobi on lap(phi) = -4 (circle -> 1 - rho^2 exactly)
                nb = (np.roll(phi, 1, 0) + np.roll(phi, -1, 0) + np.roll(phi, 1, 1) + np.roll(phi, -1, 1))
                h_ = (a / px) ** 2
                phi = np.where(inside, (nb + 4.0 / h_ * 1.0) * 0.25, 0.0)
            phi = phi / max(phi.max(), 1e-9)
            rho2 = np.clip(1 - phi, 0, 1)
            rho2[~inside] = 1.0
        s2 = np.sin(th) ** 2
        f = (np.sqrt(np.maximum(1 - rho2 * s2, 0)) - np.cos(th)) / (1 - np.cos(th))
        hmax = a * (1 - np.cos(th)) / np.sin(th)
        h = hmax * f
        if sag:
            h = h * (1 - 0.35 * bo * np.clip(Y / a, -1, 1) * (1 - rho2))
        h[rad >= 1] = 0
        ys_w = ys % M; xs_w = xs % M
        sub = H[np.ix_(ys_w, xs_w)]; idsub = ID[np.ix_(ys_w, xs_w)]
        m = h > sub
        sub[m] = h[m]; idsub[m] = idx
        H[np.ix_(ys_w, xs_w)] = sub; ID[np.ix_(ys_w, xs_w)] = idsub
    return H, ID, np.array([d['a'] for d in beads]), gvals


def to_textures(H, ID, avals, gvals, name):
    M = H.shape[0]; px = TILE / M
    # periodic gradient
    gx = (np.roll(H, -1, 1) - np.roll(H, 1, 1)) / (2 * px)
    gy = (np.roll(H, -1, 0) - np.roll(H, 1, 0)) / (2 * px)
    ds = lambda a: a.reshape(N, SS, N, SS).mean((1, 3))
    gx, gy = ds(gx), ds(gy)
    n = np.stack([-gx, -gy, np.ones_like(gx)], -1)
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    rgb = np.clip(np.round((n * 0.5 + 0.5) * 255), 0, 255).astype(np.uint8)[::-1]
    Image.fromarray(rgb).save(os.path.join(OUT, name + '_Normal_1024.png'))
    # data
    cov = ds((H > 0).astype(float))
    thick = ds(H) / 2.5e-3
    # dilate ids into gaps (periodic) via distance transform on a 3x tiled copy
    big = np.tile(ID, (3, 3))
    _, (iy, ix) = ndimage.distance_transform_edt(big < 0, return_indices=True)
    fill = big[iy, ix][M:2 * M, M:2 * M]
    fill = fill[::SS, ::SS]
    G = gvals[fill]; A = np.clip(avals[fill] / 3e-3, 0, 1)
    from remap_bead_G import area_cdf_remap                          # rainAmount reads as bead AREA (verify r2)
    G = area_cdf_remap(np.round(G * 255) / 255, cov)
    data = np.stack([np.clip(thick, 0, 1), G, cov, A], -1)[::-1]
    Image.fromarray(np.clip(np.round(data * 255), 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, name + '_Data_1024.png'))
    np.save(os.path.join(OUT, name + '_height.npy'), ds(H).astype(np.float32))
    np.save(os.path.join(OUT, name + '_G.npy'), G.astype(np.float32))
    return dict(coverage=float(cov.mean()), max_h_mm=float(H.max() * 1e3))


if __name__ == '__main__':
    meta = {}
    for variant, seed in (('Vertical', 11), ('Horizontal', 12)):
        import pickle
        cache = os.path.join(OUT, 'beads_sim_%s.pkl' % variant)
        if os.path.exists(cache):
            B, rng = pickle.load(open(cache, 'rb'))
        else:
            B, rng = simulate(variant, seed)
            pickle.dump((B, rng), open(cache, 'wb'))
        H, ID, av, gv = rasterize(B, rng, variant)
        info = to_textures(H, ID, av, gv, 'RainBeads_' + variant)
        a = np.array([d['a'] for d in B.b.values()])
        info.update(n_beads=len(a), a_p50_mm=float(np.median(a) * 1e3), a_p99_mm=float(np.percentile(a, 99) * 1e3),
                    a_max_mm=float(a.max() * 1e3), runners=B.runners)
        meta[variant] = info
        print(variant, info, flush=True)
    json.dump(dict(TILE_M=TILE, PX=N, variants=meta, G_area_remap=True), open(os.path.join(OUT, 'beads.json'), 'w'), indent=1)
