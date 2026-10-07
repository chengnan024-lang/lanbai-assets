"""Hero drops (bible §3.3, §4.6, §5.4, §6·12).

PendantDrop_Flip4x4_512   skylight-corner / lamp-arm / case-roof drip: 16 side-view frames of a Young-Laplace
                          pendant drop on a 1.5 mm lip: 0-11 growth (stable branch up to V_max = 4.9e-8 m3),
                          12-14 necking + pinch-off, 15 recoiling remnant. Frame = 10 x 10 mm, lip at top centre.
OneDrop_Head_Flip4x4_512  'that one raindrop' (4 mm on the hero window): frame 0 = at rest (gravity sag),
                          frame 15 = sliding (advancing front steep, receding tail drawn out). Frame = 12 x 12 mm;
                          anchor (head position) at (0.5, 0.40) of the frame.
OneDrop_Trail_128x1024    its 80 mm path on a 12 x 96 mm decal: start 8 mm below the top, pause at 20 mm,
                          end (rubber seal) at 88 mm below the top.
StepWet_Decal_256         wet spot on the door step under the skylight drip (0.12 m square).
RGBA encodings (linear, sRGB OFF):
  Pendant / Head : R,G = tangent normal xy (0.5 bias, +X right, +Y up, +Z toward viewer), B = thickness / 5 mm,
                   A = coverage
  Trail          : R = path centre-line offset for this row (0.5 + dx / 4 mm), constant across the row
                   G = residue-pearl height / 0.25 mm, B = wet-track film mask, A = 1
  StepWet        : R = film wetness, G = bead height / 1 mm, B = splash-ring darkening, A = overall mask
"""
import json, os, sys
import numpy as np
from PIL import Image
from scipy import ndimage
from pendant import family, LC

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rainpaths as RP
OUT = sys.argv[1] if len(sys.argv) > 1 else RP.out_dir()
rng = np.random.default_rng(1234)


def enc(v):
    return np.clip(np.round(v * 255), 0, 255).astype(np.uint8)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


# ------------------------------------------------------------------ pendant drop
def revolve_frame(rz_fn, z_top, npx=128, size=0.010, ss=4):
    """rz_fn(y) -> radius (m) at height y (m, measured down from the lip, 0 = lip). side view, lip at the top."""
    n = npx * ss; px = size / n
    x = (np.arange(n) + 0.5) * px - size / 2
    y = (np.arange(n) + 0.5) * px                         # distance below the lip (row 0 = lip)
    r = rz_fn(y)                                          # (n,)
    dr = np.gradient(r, px)                               # dr/dy(down)
    Xg, Rg = np.meshgrid(x, r); _, DRg = np.meshgrid(x, dr)
    inside = np.abs(Xg) < Rg
    q = np.where(inside, Xg / np.maximum(Rg, 1e-9), 0)
    nz = np.sqrt(np.clip(1 - q * q, 0, 1))
    # surface of revolution: n ~ (x/r, dr/dy_down, sqrt(1-(x/r)^2))  (+Y up in tangent space: dr/dy_down > 0 means the
    # silhouette widens downward -> the surface faces up there)
    n_ = np.stack([q, DRg * nz, nz], -1)
    n_ /= np.maximum(np.linalg.norm(n_, axis=-1, keepdims=True), 1e-9)
    thick = np.where(inside, 2 * np.sqrt(np.clip(Rg ** 2 - Xg ** 2, 0, None)), 0) / 0.005
    ds = lambda a: a.reshape(npx, ss, npx, ss, *a.shape[2:]).mean((1, 3))
    cov = ds(inside.astype(float)); nn = ds(n_ * inside[..., None]); th = ds(thick)
    nxy = nn[..., :2] / np.maximum(cov[..., None], 1e-6)
    return np.dstack([0.5 + 0.5 * nxy[..., 0], 0.5 + 0.5 * nxy[..., 1], np.clip(th, 0, 1), cov])


def pendant_flipbook():
    fam = family(0.0015, 160)
    vols = np.array([v for _, v, _, _ in fam]); imax = int(np.argmax(vols))
    stable = fam[:imax + 1]
    targets = np.linspace(vols[0] * 1.5, vols[imax], 12) ** 1.0
    frames = []
    def rz_from(xs, zs, lip=0.0015):
        ztop = zs[-1]
        yy = ztop - zs                                    # distance below the lip
        order = np.argsort(yy)
        def f(y):
            return np.where(y <= yy.max(), np.interp(y, yy[order], xs[order]), 0.0)
        return f
    for tv in targets:
        k = int(np.argmin(np.abs(vols[:imax + 1] - tv)))
        _, _, xs, zs = stable[k]
        frames.append(revolve_frame(rz_from(xs, zs), zs[-1]))
    # pinch-off (Eggers): 12 hourglass neck; 13 thread, bulb rounding and sagging; 14 bulb gone (it is now the falling
    # drop particle), conical remnant retracting + satellite droplet; 15 remnant cap recoiling
    _, _, xs, zs = stable[-1]
    base = rz_from(xs, zs); H = zs[-1]
    yn = 0.45 * H
    def f12(y):
        return base(y) * (1 - 0.45 * np.exp(-((y - yn) / (0.16 * H)) ** 2))
    def f13(y):
        top = base(y) * (1 - 0.85 * np.exp(-((y - yn) / (0.20 * H)) ** 2))
        # lower bulb: sphere of the detaching volume, centred 0.5 mm lower than before
        Rb = 0.95 * base(np.array([0.72 * H]))[0]; cb = 0.74 * H + 0.0005
        bulb = np.sqrt(np.clip(Rb ** 2 - (y - cb) ** 2, 0, None))
        thread = np.where((y > yn) & (y < cb - Rb * 0.9), 0.00012, 0.0)
        return np.where(y < yn, top, np.maximum(bulb, thread))
    def f14(y):
        t = np.clip((y - 0.10 * H) / (yn + 0.0014 - 0.10 * H), 0, 1)
        cone = base(np.minimum(y, yn)) * (1 - t * t * (3 - 2 * t)) ** 0.75
        rs = 0.00032; cs = yn + 0.0022                      # satellite droplet
        sat = np.sqrt(np.clip(rs ** 2 - (y - cs) ** 2, 0, None))
        return np.maximum(cone, sat)
    for f in (f12, f13, f14):
        frames.append(revolve_frame(f, H))
    # remnant: small cap with a little upward recoil bulge
    _, _, xs2, zs2 = stable[max(2, len(stable) // 5)]
    frames.append(revolve_frame(rz_from(xs2, zs2 * 0.9), zs2[-1]))
    atlas = np.zeros((512, 512, 4))
    for i, f in enumerate(frames[:16]):
        r, c = divmod(i, 4)
        atlas[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128] = f
    Image.fromarray(enc(atlas), 'RGBA').save(os.path.join(OUT, 'PendantDrop_Flip4x4_512.png'))
    return dict(V_max_m3=float(vols[imax]), D_eq_mm=float((6 * vols[imax] / np.pi) ** (1 / 3) * 1e3), lip_radius_mm=1.5,
                frames='0-11 growth, 12-14 pinch-off, 15 remnant', frame_mm=10)


# ------------------------------------------------------------------ sessile hero drop (dome inside an outline)
def dome(inside, iters=900, guess=None):
    phi = inside.astype(float) * 0.5 if guess is None else np.where(inside, guess, 0.0)
    for _ in range(iters):
        nb = np.roll(phi, 1, 0) + np.roll(phi, -1, 0) + np.roll(phi, 1, 1) + np.roll(phi, -1, 1)
        phi = np.where(inside, (nb + 1.0) * 0.25, 0.0)
    return phi / max(phi.max(), 1e-9)


def head_frame(m, npx=128, size=0.012, ss=3):
    n = npx * ss; px = size / n
    x = (np.arange(n) + 0.5) * px - size / 2
    y = (np.arange(n) + 0.5) * px - 0.40 * size             # y up, anchor at 40 % height
    X, Y = np.meshgrid(x, y)
    a = 0.0020
    Lf = a * (1.0 - 0.06 * m); Lt = a * (1.05 + 0.85 * m); Wd = a * (1.0 - 0.10 * m)
    yc = -0.12 * a * (1 - m)                                  # at rest the mass sags downward
    Yr = Y - yc
    L = np.where(Yr < 0, Lf, Lt)
    # teardrop: narrow toward the tail
    wmod = Wd * (1 - 0.35 * m * np.clip(Yr / Lt, 0, 1) ** 1.5)
    rr = (X / wmod) ** 2 + (Yr / L) ** 2
    inside = rr < 1
    # Jacobi from the ellipse paraboloid (the exact answer for an ellipse), scaled to the Poisson units (lap = -4 / r_px^2 ~ -1)
    rpx = min(Wd, Lf) / px
    phi = dome(inside, 2500, guess=np.clip(1.0 - rr, 0, 1) * rpx * rpx / 4.0)
    rho2 = np.clip(1 - phi, 0, 1)
    # contact angle: front (bottom) advancing 62 deg, tail receding 62 -> 32 deg with motion; rest 55 deg
    front = np.clip(-Yr / Lf, 0, 1); back = np.clip(Yr / Lt, 0, 1)
    th = np.radians(55 + 7 * m * front - (23 * m + 4) * back)
    s2 = np.sin(th) ** 2
    f = (np.sqrt(np.clip(1 - rho2 * s2, 0, 1)) - np.cos(th)) / (1 - np.cos(th))
    hmax = a * (1 - np.cos(np.radians(55))) / np.sin(np.radians(55))
    sagw = np.clip(-Yr / Lf, 0, 1); sagw = sagw * sagw * (3 - 2 * sagw)
    h = np.where(inside, hmax * f * (1 + 0.10 * (1 - m) * sagw), 0)
    gy, gx = np.gradient(h, px)
    nn = np.stack([-gx, -gy, np.ones_like(h)], -1); nn /= np.linalg.norm(nn, axis=-1, keepdims=True)
    ds = lambda q: q.reshape(npx, ss, npx, ss, *q.shape[2:]).mean((1, 3))
    cov = ds(inside.astype(float)); nd = ds(nn * inside[..., None]); th_ = ds(h) / 0.005 * 2
    nxy = nd[..., :2] / np.maximum(cov[..., None], 1e-6)
    img = np.dstack([0.5 + 0.5 * nxy[..., 0], 0.5 + 0.5 * nxy[..., 1], np.clip(th_, 0, 1), cov])
    return img[::-1]                                           # PNG row 0 = top


def onedrop_head():
    atlas = np.zeros((512, 512, 4))
    for i in range(16):
        m = (i / 15) ** 1.2
        r, c = divmod(i, 4)
        atlas[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128] = head_frame(m)
        print('head frame', i, flush=True)
    Image.fromarray(enc(atlas), 'RGBA').save(os.path.join(OUT, 'OneDrop_Head_Flip4x4_512.png'))


def onedrop_trail():
    W, H = 128, 1024; size_u, size_v = 0.012, 0.096
    pxu = size_u / W; pxv = size_v / H
    top = 0.008; L = 0.080
    s = np.clip((np.arange(H) + 0.5) * pxv - top, 0, L)       # path distance for each PNG row (row 0 = top)
    # centre line: gentle meander, a kink where it paused (20 mm) and where it hit a pinning site (52 mm)
    cl = 0.00035 * np.sin(2 * np.pi * s / 0.041 + 0.7) + 0.00018 * np.sin(2 * np.pi * s / 0.013 + 2.1)
    cl += 0.00030 * sstep(0.020, 0.023, s) - 0.00045 * sstep(0.052, 0.055, s)
    cl -= cl[np.argmin(np.abs(s - 0.0))]
    R = np.tile((0.5 + 0.5 * cl / 0.004)[:, None], (1, W))
    u = (np.arange(W) + 0.5) * pxu - size_u / 2
    U, S = np.meshgrid(u, s)
    dx = U - np.interp(S, s, cl)
    width = 0.0011 + 0.00025 * np.sin(2 * np.pi * S / 0.017)
    film = sstep(width, width * 0.55, np.abs(dx)) * (S > 0.0005) * (S < L - 0.0005)
    Gp = np.zeros((H, W))
    # residue pearls every ~1.3 mm, 0.08-0.28 mm radius, more where it moved slowly (after the pause, near the end)
    pos = 0.0008
    while pos < L - 0.002:
        r = rng.uniform(0.00008, 0.00028)
        if abs(pos - 0.020) < 0.0015:
            r = 0.00045                                         # the remnant where the drop rested for 20 minutes
        c_u = np.interp(pos, s, cl) + rng.normal(0, 0.00035)
        d2 = ((U - c_u) ** 2 + (S - pos) ** 2) / r ** 2
        Gp = np.maximum(Gp, np.where(d2 < 1, np.sqrt(np.clip(1 - d2 * 0.55, 0, 1)) - np.sqrt(0.45), 0) / (1 - np.sqrt(0.45)) * r / 0.00025)
        pos += rng.uniform(0.0008, 0.0019)
    img = np.dstack([R, np.clip(Gp, 0, 1), film, np.ones_like(R)])
    Image.fromarray(enc(img), 'RGBA').save(os.path.join(OUT, 'OneDrop_Trail_128x1024.png'))
    return dict(decal_mm=[12, 96], path_start_from_top_mm=8, pause_mm=20, path_length_mm=80, seal_from_top_mm=88,
                centreline_mm=[round(float(v) * 1e3, 3) for v in np.interp(np.linspace(0, L, 41), s, cl)])


def step_wet():
    N = 256; size = 0.12; px = size / N
    x = (np.arange(N) + 0.5) * px - size / 2
    X, Y = np.meshgrid(x, x)
    r = np.hypot(X, Y); ang = np.arctan2(Y, X)
    from scipy.ndimage import gaussian_filter
    nz = gaussian_filter(rng.normal(size=(N, N)), 9, mode='wrap'); nz /= nz.std()
    lobes = 1 + 0.07 * np.sin(2 * ang + 1.0) + 0.04 * np.sin(5 * ang + 2.0) + 0.025 * np.sin(11 * ang) + 0.05 * nz
    film = sstep(0.034 * lobes, 0.022 * lobes, r)
    ring = np.exp(-((r - 0.030 * lobes) / 0.004) ** 2) * 0.6           # the edge where the film thickens (coffee ring)
    beads = np.zeros_like(r)
    for k in range(140):
        rad = abs(rng.normal(0.034, 0.012)); a_ = rng.uniform(0, 2 * np.pi)
        cx, cy = rad * np.cos(a_), rad * np.sin(a_)
        br = rng.uniform(0.0003, 0.0012) * (1.3 if rad > 0.03 else 0.8)
        d2 = ((X - cx) ** 2 + (Y - cy) ** 2) / br ** 2
        beads = np.maximum(beads, np.where(d2 < 1, (1 - d2) * br / 0.0012, 0))
    mask = np.clip(np.maximum(film, beads * 1.5) + ring * 0.5, 0, 1)
    img = np.dstack([film, np.clip(beads, 0, 1), ring, mask])
    Image.fromarray(enc(img), 'RGBA').save(os.path.join(OUT, 'StepWet_Decal_256.png'))


if __name__ == '__main__':
    meta = {}
    meta['pendant'] = pendant_flipbook(); print('pendant', meta['pendant'], flush=True)
    if '--all' in sys.argv: onedrop_head()
    meta['trail'] = onedrop_trail()
    step_wet()
    json.dump(meta, open(os.path.join(OUT, 'drops.json'), 'w'), indent=1)
