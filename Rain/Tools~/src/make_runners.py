"""GlassRunners_Flow_512x1024: lane field for drops sliding on glass (bible §4.6 rain states).

Tile = 0.20 m (u) x 0.40 m (v). Drops run toward -v in texture space (the shader rotates the UV so that -v points
along the current flow direction). 12 lanes per tile; each lane is a periodic meandering path x_c(v) built from a
kinked random walk (drops jump sideways when they swallow a bead).
RGBA, linear (sRGB OFF), no compression artefacts allowed on R -> import uncompressed or BC7 high quality:
  R = 0.5 + 0.5 * dx / W          dx = x - x_c(v) (m), W = 5 mm band half-width; clamped outside the band
  G = lane id (0..1), constant over the lane's Voronoi cell
  B = 0.5 + 0.5 * clamp(dx_c/dv, -1, 1)   local path slope (head orientation)
  A = band mask (1 inside |dx| < 0.8 W, smooth to 0 at W; exactly 0 where two cells meet)
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter1d

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rainpaths as RP
OUT = sys.argv[1] if len(sys.argv) > 1 else RP.out_dir()
TU, TV = 0.20, 0.40
NU, NV = 512, 1024
K = 12
W = 0.005
rng = np.random.default_rng(4242)


def periodic_walk(n, step_sd, kink_p, kink_sd, smooth):
    x = np.cumsum(rng.normal(0, step_sd, n) + (rng.random(n) < kink_p) * rng.normal(0, kink_sd, n))
    x -= np.linspace(0, x[-1] - x[0], n)            # make periodic
    x -= x.mean()
    x = gaussian_filter1d(x, smooth, mode='wrap')
    return x


def build():
    v = (np.arange(NV) + 0.5) / NV * TV
    base = (np.arange(K) + 0.5 + rng.uniform(-0.28, 0.28, K)) * TU / K
    paths = []
    for k in range(K):
        p = periodic_walk(NV, 0.00006, 0.012, 0.0009, 5.0)
        p *= rng.uniform(0.6, 1.2) * 0.0035 / max(1e-9, np.abs(p).max())   # meander amplitude 2-4 mm
        paths.append(base[k] + p)
    paths = np.array(paths)                            # (K, NV)
    # keep neighbours >= 2W + 1.5 mm apart (periodic in u)
    for it in range(50):
        ok = True
        for k in range(K):
            j = (k + 1) % K
            gap = (paths[j] + (TU if j == 0 else 0)) - paths[k]
            if gap.min() < 2 * W + 0.0015:
                ok = False
                c = 0.5 * (paths[j].mean() + (TU if j == 0 else 0) + paths[k].mean())
                paths[k] = paths[k].mean() + (paths[k] - paths[k].mean()) * 0.85
                paths[j] = paths[j].mean() + (paths[j] - paths[j].mean()) * 0.85
        if ok:
            break
    slope = np.gradient(paths, TV / NV, axis=1)
    lane_id = (np.arange(K) + rng.uniform(0.1, 0.9, K)) / K
    lane_id = rng.permutation(lane_id)
    u = (np.arange(NU) + 0.5) / NU * TU
    R = np.zeros((NV, NU)); G = np.zeros((NV, NU)); B = np.zeros((NV, NU)); A = np.zeros((NV, NU))
    for iv in range(NV):
        # periodic signed distance to every lane at this row
        d = (u[None, :] - paths[:, iv:iv + 1] + TU / 2) % TU - TU / 2      # (K, NU)
        k = np.argmin(np.abs(d), 0)
        dx = d[k, np.arange(NU)]
        R[iv] = np.clip(0.5 + 0.5 * dx / W, 0, 1)
        G[iv] = lane_id[k]
        B[iv] = 0.5 + 0.5 * np.clip(slope[k, iv], -1, 1)
        t = np.clip((np.abs(dx) - 0.8 * W) / (0.2 * W), 0, 1)
        A[iv] = 1 - t * t * (3 - 2 * t)
    img = np.stack([R, G, B, A], -1)[::-1]               # v up
    Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'GlassRunners_Flow_512x1024.png'))
    json.dump(dict(TILE_U_M=TU, TILE_V_M=TV, LANES=K, BAND_HALF_WIDTH_M=W, lane_ids=lane_id.tolist(),
                   min_gap_mm=float(min(((paths[(k + 1) % K] + (TU if k == K - 1 else 0)) - paths[k]).min() for k in range(K)) * 1e3)),
              open(os.path.join(OUT, 'runners.json'), 'w'), indent=1)
    print('min gap mm', json.load(open(os.path.join(OUT, 'runners.json')))['min_gap_mm'])


if __name__ == '__main__':
    build()
