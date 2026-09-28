"""Grade mock-ups: composite the delivered cloud cards (converted back to scene-linear) into
simple key frames, then push them through the PPv2 emulator with each scene's grade.
Usage: python3 mock.py            -> writes mock_*.png + grades contact sheet
"""
import json, os, sys, math
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter, map_coordinates
import ppv2

HERE = os.path.dirname(os.path.abspath(__file__))
LB = os.path.abspath(os.path.join(HERE, '..', '..'))
CARDS = os.path.join(LB, 'deliver', 'Clouds')
sys.path.insert(0, os.path.join(LB, 'clouds'))
GR = json.load(open(os.path.join(HERE, 'grades.json')))['profiles']

W, H = 1920, 804          # 2.39:1 trailer frame
HFOV = 80.0

PRE = {  # from make_clouds.PRESETS (sky + authoring exposure)
    'dawn': dict(sun_el=7.0, sun_az=84.0, zenith=(0.040, 0.120, 0.520), hz_sun=(1.00, 0.56, 0.34), hz_anti=(0.36, 0.30, 0.66),
                 ground=(0.22, 0.22, 0.30), glow=(1.00, 0.60, 0.34), glow_k=9.0, glow_E=1.4, sky_E=2.3, exposure=-1.1),
    'dusk': dict(sun_el=3.0, sun_az=72.0, zenith=(0.060, 0.050, 0.300), hz_sun=(1.00, 0.40, 0.30), hz_anti=(0.34, 0.18, 0.52),
                 ground=(0.16, 0.10, 0.20), glow=(1.00, 0.40, 0.28), glow_k=8.0, glow_E=1.6, sky_E=0.95, exposure=-1.1),
    'moon': dict(sun_el=26.0, sun_az=55.0, zenith=(0.006, 0.010, 0.032), hz_sun=(0.030, 0.042, 0.085), hz_anti=(0.016, 0.022, 0.050),
                 ground=(0.030, 0.040, 0.075), glow=(0.40, 0.52, 0.85), glow_k=14.0, glow_E=0.5, sky_E=0.9, exposure=-0.85),
}

def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def sun_dir(p, az_override=None):
    el = math.radians(p['sun_el']); az = math.radians(p['sun_az'] if az_override is None else az_override)
    return np.array([math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)])

def sky(p, dirs, az=None):
    sd = sun_dir(p, az)
    hs = np.array([sd[0], sd[1], 0.0]); hs /= np.linalg.norm(hs)
    d = dirs; up = d[..., 2:3]
    c = lambda k: np.array(p[k])
    horizon = c('hz_anti') + (c('hz_sun') - c('hz_anti')) * sstep(-0.9, 1.0, d @ hs)[..., None]
    s = horizon + (c('zenith') - horizon) * sstep(0.0, 0.55, up)
    lower = horizon + (c('ground') - horizon) * sstep(0.0, -0.35, up)
    col = lower + (s - lower) * sstep(-0.02, 0.02, up)
    col = col + c('glow') * p['glow_E'] * np.exp(p['glow_k'] * ((d @ sd)[..., None] - 1.0))
    return col * p['sky_E']

def cam_dirs(pitch_deg=0.0, hfov=HFOV, w=W, h=H):
    f = (w / 2) / math.tan(math.radians(hfov / 2))
    xs = np.arange(w) - w / 2 + 0.5
    ys = h / 2 - np.arange(h) - 0.5
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([X, np.full_like(X, f), Y], -1)
    pr = math.radians(pitch_deg)
    R = np.array([[1, 0, 0], [0, math.cos(pr), -math.sin(pr)], [0, math.sin(pr), math.cos(pr)]])
    d = d @ R.T
    return d / np.linalg.norm(d, axis=-1, keepdims=True), f

def inv_khronos(y):
    """inverse of Khronos PBR Neutral (display-linear -> pre-tonemap), desaturation term ignored."""
    y = np.clip(y, 0, 0.995)
    sc = 0.76; d = 0.24
    peak = y.max(-1, keepdims=True)
    big = peak >= sc
    pk = np.where(big, d * d / (1 - peak) - d + sc, peak)
    c = y * np.where(big, pk / np.maximum(peak, 1e-6), 1.0)
    ymin = c.min(-1, keepdims=True)
    x = np.where(ymin < 0.04, np.sqrt(np.maximum(ymin, 0) / 6.25), ymin + 0.04)
    off = np.where(x < 0.08, x - 6.25 * x * x, 0.04)
    return c + off

def load_card(name, preset):
    im = np.asarray(Image.open(os.path.join(CARDS, f'{name}_{preset}.png')).convert('RGBA')).astype(np.float64) / 255
    rgb = ppv2.srgb_to_lin(im[..., :3])
    rad = inv_khronos(rgb)          # authored pre-tonemap level (= what the InverseNeutral card shader feeds PPv2)
    return rad, im[..., 3]

def paste(canvas, rad, a, cx, base_y, width, haze_col=None, haze=0.0, flip=False, base_v=0.15):
    """place card with its cloud base (v from bottom) at pixel row base_y, centred at cx, width px."""
    h0, w0 = a.shape
    s = width / w0
    nh = max(2, int(h0 * s)); nw = max(2, int(width))
    rim = Image.fromarray(np.uint8(np.clip(a, 0, 1) * 255)).resize((nw, nh), Image.LANCZOS)
    aa = np.asarray(rim).astype(np.float64) / 255
    rr = np.stack([np.asarray(Image.fromarray(np.float32(rad[..., k]), 'F').resize((nw, nh), Image.LANCZOS)) for k in range(3)], -1).astype(np.float64)
    if flip:
        aa = aa[:, ::-1]; rr = rr[:, ::-1]
    if haze_col is not None and haze > 0:
        rr = rr * (1 - haze) + np.asarray(haze_col) * haze
    top = int(base_y - nh * (1 - base_v)); left = int(cx - nw / 2)
    y0, y1 = max(top, 0), min(top + nh, canvas.shape[0]); x0, x1 = max(left, 0), min(left + nw, canvas.shape[1])
    if y1 <= y0 or x1 <= x0:
        return
    sub_a = aa[y0 - top:y1 - top, x0 - left:x1 - left, None]
    sub_r = rr[y0 - top:y1 - top, x0 - left:x1 - left]
    canvas[y0:y1, x0:x1] = canvas[y0:y1, x0:x1] * (1 - sub_a) + sub_r * sub_a

def horizon_row(pitch):
    f = (W / 2) / math.tan(math.radians(HFOV / 2))
    return H / 2 + f * math.tan(math.radians(pitch))

def base_frame(preset, pitch=3.0, sun_az=None, strips=True, clouds=()):
    d, f = cam_dirs(pitch)
    img = sky(PRE[preset], d, sun_az) * 2 ** PRE[preset]['exposure']
    hz = horizon_row(pitch)
    if strips:
        for i, (nm, flip) in enumerate([('CloudSea_1', False), ('CloudSea_2', True), ('CloudSea_1', True)]):
            rad, a = load_card(nm, preset)
            # strip top (horizon) ~ opaque bbox top v=0.70; put it slightly below the horizon line
            nw = W * 0.62
            nh = a.shape[0] * nw / a.shape[1]
            base_y = hz + nh * (0.70 - 0.15) - 2
            paste(img, rad, a, W * (0.18 + 0.32 * i), base_y + nh * 0.0, nw, flip=flip)
        # foreground: a bigger, closer strip to fill the lower frame
        rad, a = load_card('CloudSea_2', preset)
        nw = W * 1.25; nh = a.shape[0] * nw / a.shape[1]
        paste(img, rad, a, W * 0.5, hz + nh * 0.55 + H * 0.05, nw)
    for (nm, cx, dist_w, haze, flip) in clouds:
        rad, a = load_card(nm, preset)
        hc = sky(PRE[preset], np.array([[0, 1.0, 0.02]]) / np.linalg.norm([0, 1, 0.02]), sun_az)[0] * 2 ** PRE[preset]['exposure']
        paste(img, rad, a, cx, hz + 4, dist_w, hc, haze, flip)
    return img, hz

def fill_below(img, hz, col):
    img[int(hz) + 1:] = np.where(img[int(hz) + 1:].sum(-1, keepdims=True) > 0, img[int(hz) + 1:], col)
    return img

def mirror_ceiling(img, hz, tint=(0.35, 0.55, 0.75), deep=(0.010, 0.030, 0.060), slot=0):
    """S8 thesis frame: the ocean hangs overhead as a rippled mirror of the lower world."""
    h = img.shape[0]
    out = img.copy()
    hzi = int(hz)
    yy, xx = np.mgrid[0:hzi, 0:img.shape[1]].astype(np.float64)
    src_y = 2 * hz - yy
    rng = np.random.default_rng(3)
    n = gaussian_filter(rng.standard_normal((hzi, img.shape[1])), (3, 14))
    n = n / (np.abs(n).max() + 1e-9)
    dist = (hz - yy) / hz          # 0 at horizon, 1 at top
    src_y = src_y + n * 18 * (0.2 + dist)
    src_x = xx + n * 10
    src_y = np.clip(src_y, hz, h - 1)
    refl = np.stack([map_coordinates(img[..., k], [src_y, src_x], order=1, mode='nearest') for k in range(3)], -1)
    # Fresnel: bright mirror near the horizon, see-through dark water straight overhead
    fres = 0.02 + 0.98 * (1 - np.clip(dist * 1.25, 0, 1)) ** 5
    fres = fres[..., None]
    water = np.array(deep) * (1 - dist[..., None]) + np.array(deep) * 0.4 * dist[..., None]
    ceil = refl * fres * np.array(tint) * 1.6 + water * (1 - fres)
    if slot:
        # the ceiling ends a few km out and dissolves in mist: a thin band of real dusk sky at eye level
        edge = hz - slot
        m = sstep(edge - 22, edge + 6, yy)[..., None]      # 0 = ceiling, 1 = open sky
        ceil = ceil * (1 - m) + img[:hzi] * m
    out[:hzi] = ceil
    return out

def stars(h, w, seed=7, density=0.0018, mw=True):
    rng = np.random.default_rng(seed)
    img = np.zeros((h, w, 3))
    n = int(h * w * density)
    ys = rng.integers(0, h, n); xs = rng.integers(0, w, n)
    mag = rng.pareto(2.2, n) * 0.08 + 0.02
    tint = rng.choice([[1, 1, 1], [0.8, 0.88, 1.0], [1.0, 0.9, 0.75], [0.75, 0.85, 1.0]], n)
    img[ys, xs] += tint * mag[:, None]
    img = gaussian_filter(img, (0.6, 0.6, 0))
    if mw:
        yy, xx = np.mgrid[0:h, 0:w].astype(np.float64)
        # diagonal band rising from lower-left to upper-right
        t = (xx / w) * 0.9 + (yy / h) * 0.55 - 0.72
        band = np.exp(-(t / 0.11) ** 2)
        noise = gaussian_filter(rng.standard_normal((h, w)), 6) * 3 + gaussian_filter(rng.standard_normal((h, w)), 22) * 6
        dust = np.clip(1 - 1.8 * np.exp(-(t / 0.035) ** 2) * (0.5 + gaussian_filter(rng.standard_normal((h, w)), 10) * 4), 0.1, 1)
        core = np.exp(-((xx / w - 0.28) / 0.12) ** 2 - ((yy / h - 0.62) / 0.25) ** 2)
        glow = band * (0.022 + 0.018 * np.clip(noise, -1, 1)) * dust
        img += glow[..., None] * np.array([0.78, 0.84, 1.0]) + (core * band * 0.05 * dust)[..., None] * np.array([1.0, 0.86, 0.66])
        dense = rng.random((h, w)) < band * 0.012
        img[dense] += 0.05
    return img

def save(arr_srgb, path):
    Image.fromarray(np.uint8(np.clip(arr_srgb, 0, 1) * 255 + 0.5)).save(path)

def grade(img, key, bloom=True):
    return ppv2.render(img, GR[{'S9': 'S9a'}.get(key, key)]['ppv2'], with_bloom=bloom)

def build(keys=('S3','S6','S8','S9')):
    frames = {}
    # S3 moonlit cloud sea (reference exposure)
    img, hz = base_frame('moon', pitch=4.0, sun_az=18.0, clouds=[('Cloud_Congestus', W * 0.80, 150, 0.55, False),
                                                                ('Cloud_Bank', W * 0.25, 260, 0.6, True)])
    d, _ = cam_dirs(4.0)
    md = sun_dir(PRE['moon'], 18.0)
    moon = np.clip((d @ md - math.cos(math.radians(0.55))) * 4000, 0, 1)[..., None] * np.array([6.0, 6.6, 7.5])
    img = img + moon
    # moon path on the cloud tops: brighten cloud pixels below the moon
    yy, xx = np.mgrid[0:H, 0:W]
    mx = W / 2 + ((W / 2) / math.tan(math.radians(HFOV / 2))) * math.tan(math.radians(18.0))
    path = np.exp(-((xx - mx) / (40 + (yy - hz).clip(0) * 0.9)) ** 2) * (yy > hz)
    img = img * (1 + 1.8 * path[..., None])
    frames['S3'] = img
    if 'S6' not in keys: pass
    # S6 dawn: sun ahead-right, scattered cumulus towers over the sea of cloud
    img, hz = base_frame('dawn', pitch=3.0, sun_az=62.0, clouds=[('Cloud_Congestus', W * 0.30, 330, 0.30, True),
                                                                ('Cloud_Cumulus', W * 0.63, 180, 0.45, False),
                                                                ('Cloud_Bank', W * 0.90, 300, 0.5, False)])
    d, _ = cam_dirs(3.0)
    sd = sun_dir(PRE['dawn'], 62.0)
    img = img + np.clip((d @ sd - math.cos(math.radians(0.6))) * 3000, 0, 1)[..., None] * np.array([40, 30, 20.0])
    frames['S6'] = img
    # S8 dusk thesis frame: horizon at eye level, cloud sea below, ocean ceiling above mirroring it
    img, hz = base_frame('dusk', pitch=0.0, sun_az=4.0, clouds=[('Cloud_Bank', W * 0.22, 280, 0.35, True),
                                                               ('Cloud_Cumulus', W * 0.80, 170, 0.45, False)])
    d, _ = cam_dirs(0.0)
    sd = sun_dir(PRE['dusk'], 4.0)
    img = img + np.clip((d @ sd - math.cos(math.radians(0.6))) * 3000, 0, 1)[..., None] * np.array([40, 22, 12.0])
    frames['S8'] = mirror_ceiling(img, hz, slot=38)
    # S9 star sea: sky of stars + Milky Way, mirror sea below
    hz = H * 0.56
    sk = stars(H, W) + np.array([0.004, 0.006, 0.014])
    top = sk[:int(hz)]
    below = top[::-1][:H - int(hz)] * 0.8 + np.array([0.002, 0.003, 0.007])
    img = np.concatenate([top, below], 0)
    # a rising mirror edge (the crossing line of light)
    edge_y = int(hz + 150)
    img[edge_y - 1:edge_y + 2] += np.array([1.2, 1.4, 1.7])
    frames['S9'] = img
    return frames

def tentacle_frame():
    im = np.asarray(Image.open(os.path.join(LB, 'tentacles', 'explore', 'skin', 'cluster.png')).convert('RGB')).astype(np.float64) / 255
    lin = ppv2.srgb_to_lin(im)
    lin = np.where(lin > 0.5, lin * (1 + (lin - 0.5) * 6), lin)  # crude un-AgX for the tear core
    im2 = Image.fromarray(np.uint8(np.clip(ppv2.lin_to_srgb(np.clip(lin, 0, 1)), 0, 1) * 255))
    # crop to 2.39:1
    w, h = im2.size
    ch = int(w / 2.39); y0 = (h - ch) // 2 + 20
    arr = lin[y0:y0 + ch]
    arr = np.stack([np.asarray(Image.fromarray(np.float32(arr[..., k]), 'F').resize((W, H), Image.LANCZOS)) for k in range(3)], -1)
    return arr.astype(np.float64)

if __name__ == '__main__':
    out = os.path.join(HERE, 'mock')
    os.makedirs(out, exist_ok=True)
    fz = os.path.join(out, 'frames.npz')
    if '--grade-only' in sys.argv and os.path.exists(fz):
        fr = dict(np.load(fz))
    elif '--rebuild' in sys.argv and os.path.exists(fz):
        fr = dict(np.load(fz))
        ks = [a for a in sys.argv[1:] if not a.startswith('--')]
        fr.update(build(tuple(ks)))
        np.savez_compressed(fz, **fr)
    else:
        fr = build()
        fr['S4'] = tentacle_frame()
        np.savez_compressed(fz, **fr)
    only = [a for a in sys.argv[1:] if not a.startswith('--')]
    if only:
        fr = {k: v for k, v in fr.items() if k in only}
    for k, img in fr.items():
        save(ppv2.render(img, {}, with_bloom=False), os.path.join(out, f'{k}_ungraded.png'))
        save(grade(img, k), os.path.join(out, f'{k}_graded.png'))
        print(k, 'done', 'APL', round(float((ppv2.lin_to_srgb(ppv2.srgb_to_lin(grade(img, k))) @ ppv2.LUMA709).mean() * 255), 1))
