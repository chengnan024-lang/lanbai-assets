"""Preview-only ground textures (Poly Haven is not reachable from the cloud): an old rural asphalt and a wet
gravel/earth shoulder, 2 m tiles at 2048 px (~1 mm / px), tileable. Albedo (sRGB), Height (linear), Normal (GL).
Asphalt: oxidised binder + exposed aggregate (3-12 mm chips, a few quartz / basalt), sand, tar-sealed cracks.
Mean dry albedo ~ sRGB 80 (bible §6·1: dry reference 70-95)."""
import os, sys
import numpy as np
from PIL import Image
from scipy.spatial import cKDTree
from scipy import ndimage

OUT = sys.argv[1] if len(sys.argv) > 1 else (os.environ.get('RAIN_PREVIEW') or os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'preview_cache' if os.path.basename(os.path.dirname(os.path.abspath(__file__))) == 'preview' else 'preview'))
N = 2048; TILE = 2.0; PX = TILE / N
rng = np.random.default_rng(99)
yy, xx = np.mgrid[0:N, 0:N]
P = np.stack([(xx + 0.5) * PX, (yy + 0.5) * PX], -1).reshape(-1, 2)


def periodic_voronoi(spacing, jitter=0.9):
    n = int(TILE / spacing)
    g = (np.stack(np.meshgrid(np.arange(n), np.arange(n)), -1).reshape(-1, 2) + 0.5 + rng.uniform(-jitter / 2, jitter / 2, (n * n, 2))) * (TILE / n)
    tiles = [g + np.array([dx, dy]) * TILE for dx in (-1, 0, 1) for dy in (-1, 0, 1)]
    allp = np.concatenate(tiles)
    ids = np.tile(np.arange(len(g)), 9)
    tree = cKDTree(allp)
    d, i = tree.query(P, k=2)
    return d[:, 0].reshape(N, N), d[:, 1].reshape(N, N), ids[i[:, 0]].reshape(N, N), len(g)


def fbm(lmin, lmax, seed, beta=2.0):
    r = np.random.default_rng(seed)
    F = np.fft.rfft2(r.normal(size=(N, N)))
    ky = np.fft.fftfreq(N, PX)[:, None]; kx = np.fft.rfftfreq(N, PX)[None, :]
    k = np.hypot(kx, ky)
    amp = np.where((k >= 1 / lmax) & (k <= 1 / lmin), np.maximum(k, 1e-6) ** (-beta / 2), 0)
    f = np.fft.irfft2(F * amp, s=(N, N)); return f / f.std()


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)


def to_srgb(lin):
    lin = np.clip(lin, 0, 1)
    return np.where(lin <= 0.0031308, lin * 12.92, 1.055 * lin ** (1 / 2.4) - 0.055)


def lin_of(s):
    s = np.asarray(s, float) / 255.0
    return np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4)


def normal_from_height(h, strength=1.0):
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) / (2 * PX)
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) / (2 * PX)
    n = np.stack([-gx * strength, gy * strength, np.ones_like(h)], -1)     # PNG rows go down: +v = -row
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return (np.clip((n * 0.5 + 0.5), 0, 1) * 255).astype(np.uint8)


def asphalt():
    H = np.zeros((N, N)); A = np.zeros((N, N, 3))
    binder = lin_of(62) * (1 + 0.10 * fbm(0.02, 0.4, 1)) * (1 + 0.05 * fbm(0.003, 0.02, 2))
    A[:] = (binder * np.array([1.0, 0.985, 0.96]))[..., None] if np.ndim(binder) == 0 else binder[..., None] * np.array([1.0, 0.985, 0.96])
    H += 0.00015 * fbm(0.002, 0.01, 3)                                   # sand / binder texture
    for spacing, gap, hmax, cover in ((0.0095, 0.0011, 0.0016, 0.72), (0.0048, 0.0006, 0.0009, 0.55), (0.0026, 0.00035, 0.0005, 0.45)):
        f1, f2, cid, n = periodic_voronoi(spacing)
        edge = f2 - f1
        rnd = np.random.default_rng(int(spacing * 1e5))
        present = rnd.random(n) < cover
        size_h = rnd.uniform(0.4, 1.0, n) * hmax
        kind = rnd.random(n)
        grey = rnd.uniform(78, 128, n)
        grey = np.where(kind < 0.08, rnd.uniform(135, 165, n), grey)     # quartz / limestone
        grey = np.where(kind > 0.92, rnd.uniform(46, 58, n), grey)       # basalt
        hue = np.stack([np.ones(n), rnd.uniform(0.97, 1.01, n), rnd.uniform(0.90, 1.0, n)], -1)
        col = lin_of(grey)[:, None] * hue
        m = present[cid] * sstep(gap * 0.5, gap * 1.8, edge)
        dome = np.sqrt(np.clip(edge / (spacing * 0.6), 0, 1)) * size_h[cid]
        # chips half-buried in binder; worn (flattened) tops
        dome = np.minimum(dome, size_h[cid] * 0.75)
        H = np.maximum(H, dome * m)
        film = 0.35 + 0.25 * fbm(0.01, 0.2, int(spacing * 1e6))           # binder film still on the chip
        cc = col[cid] * (1 - np.clip(film, 0, 0.8))[..., None] + binder[..., None] * np.clip(film, 0, 0.8)[..., None]
        A = A * (1 - m[..., None]) + cc * m[..., None]
    # tar-sealed cracks (random walks, periodic)
    crack = np.zeros((N, N))
    for c in range(9):
        x, y = rng.uniform(0, N, 2); ang = rng.uniform(0, 2 * np.pi); L = rng.integers(300, 1400)
        for s in range(L):
            ang += rng.normal(0, 0.12)
            x = (x + np.cos(ang) * 1.3) % N; y = (y + np.sin(ang) * 1.3) % N
            crack[int(y), int(x)] = 1
    crack = ndimage.gaussian_filter(np.maximum(crack, np.roll(crack, 1, 0)), 1.2, mode='wrap')
    crack = np.clip(crack / max(crack.max(), 1e-6) * 3, 0, 1)
    A = A * (1 - 0.55 * crack[..., None])
    H = H - 0.0008 * crack
    # low-frequency staining / oil
    stain = 1 + 0.10 * fbm(0.15, 1.5, 7) - 0.12 * np.clip(fbm(0.2, 1.0, 8) - 1.2, 0, None)
    A = A * stain[..., None]
    alb = (to_srgb(A) * 255).astype(np.uint8)
    Image.fromarray(alb).save(os.path.join(OUT, 'Pv_Asphalt_Albedo.png'))
    Image.fromarray((np.clip((H - H.min()) / (H.max() - H.min()), 0, 1) * 65535).astype(np.uint16)).save(os.path.join(OUT, 'Pv_Asphalt_Height.png'))
    Image.fromarray(normal_from_height(H)).save(os.path.join(OUT, 'Pv_Asphalt_Normal.png'))
    print('asphalt mean sRGB', alb.reshape(-1, 3).mean(0), 'height range mm', (H.max() - H.min()) * 1e3)


def gravel():
    H = np.zeros((N, N))
    soil = lin_of(66) * (1 + 0.18 * fbm(0.05, 0.8, 11))
    A = soil[..., None] * np.array([1.0, 0.93, 0.80])
    H += 0.0015 * fbm(0.05, 0.6, 12)
    for spacing, gap, hmax, cover in ((0.022, 0.004, 0.006, 0.45), (0.011, 0.002, 0.003, 0.5), (0.005, 0.001, 0.0015, 0.5)):
        f1, f2, cid, n = periodic_voronoi(spacing)
        edge = f2 - f1
        rnd = np.random.default_rng(int(spacing * 1e5) + 5)
        present = rnd.random(n) < cover
        size_h = rnd.uniform(0.4, 1.0, n) * hmax
        grey = rnd.uniform(70, 135, n)
        hue = np.stack([np.ones(n), rnd.uniform(0.95, 1.0, n), rnd.uniform(0.85, 0.98, n)], -1)
        col = lin_of(grey)[:, None] * hue
        m = present[cid] * sstep(gap * 0.4, gap * 1.6, edge)
        dome = np.sqrt(np.clip(edge / (spacing * 0.55), 0, 1)) * size_h[cid]
        H = np.maximum(H, dome * m)
        mud = np.clip(0.3 + 0.3 * fbm(0.02, 0.3, int(spacing * 1e6) + 3), 0, 0.85)
        cc = col[cid] * (1 - mud)[..., None] + soil[..., None] * np.array([1.0, 0.93, 0.80]) * mud[..., None]
        A = A * (1 - m[..., None]) + cc * m[..., None]
    alb = (to_srgb(A) * 255).astype(np.uint8)
    Image.fromarray(alb).save(os.path.join(OUT, 'Pv_Gravel_Albedo.png'))
    Image.fromarray((np.clip((H - H.min()) / (H.max() - H.min()), 0, 1) * 65535).astype(np.uint16)).save(os.path.join(OUT, 'Pv_Gravel_Height.png'))
    Image.fromarray(normal_from_height(H)).save(os.path.join(OUT, 'Pv_Gravel_Normal.png'))
    print('gravel mean sRGB', alb.reshape(-1, 3).mean(0))


if __name__ == '__main__':
    os.makedirs(OUT, exist_ok=True)
    asphalt(); gravel()
