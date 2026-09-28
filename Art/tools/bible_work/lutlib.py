import sys, json, numpy as np
sys.path.insert(0, '../lens_cine')
import ppv2
from lutlib_core import patch_ppv2, g2l, l2g
patch_ppv2(ppv2)
from PIL import Image

N = 32
GF = json.load(open('../grades_final.json'))
PROF = {k: v['ppv2'] for k, v in GF['profiles'].items()}

def look(s_rgb, p):
    """Neutral-relative display look: display sRGB (as PPv2 HDR+Neutral at default settings shows it) -> display sRGB under profile p."""
    y = ppv2.srgb_to_lin(np.clip(s_rgb, 0, 1))
    x = ppv2.neutral_inverse(np.minimum(y, 0.99999))
    pp = ppv2.full(p)
    return ppv2.lin_to_srgb(ppv2.grade_lut(x * 2 ** pp['postExposure'], pp))

def lut3d(p, n=N):
    g = np.arange(n) / (n - 1)
    B, G, R = np.meshgrid(g, g, g, indexing='ij')        # index [b][g][r]
    s = np.stack([R, G, B], -1)
    return look(s, p)                                    # shape (b, g, r, 3)

def write_strip(lut, path):
    n = lut.shape[0]
    img = np.zeros((n, n * n, 3))
    for b in range(n):
        img[:, b * n:(b + 1) * n, :] = lut[b]            # rows = g (0 = bottom in Unity), cols = r
    img = img[::-1]                                      # PNG row 0 = top -> green = max at top
    Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8), 'RGB').save(path)

def read_strip(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(np.float64) / 255
    a = a[::-1]                                          # back to Unity orientation (row 0 = green 0)
    n = a.shape[0]
    return np.stack([a[:, b * n:(b + 1) * n, :] for b in range(n)], 0)   # (b, g, r, 3)

def write_cube(lut, path, title, domain=(0.0, 1.0), comment=None):
    n = lut.shape[0]
    with open(path, 'w') as f:
        if comment:
            for line in comment:
                f.write('# %s\n' % line)
        f.write('TITLE "%s"\n' % title)
        f.write('LUT_3D_SIZE %d\n' % n)
        f.write('DOMAIN_MIN %.6f %.6f %.6f\n' % (domain[0],) * 3 if False else 'DOMAIN_MIN %.1f %.1f %.1f\n' % (domain[0], domain[0], domain[0]))
        f.write('DOMAIN_MAX %.1f %.1f %.1f\n' % (domain[1], domain[1], domain[1]))
        for b in range(n):
            for g in range(n):
                for r in range(n):
                    c = lut[b, g, r]
                    f.write('%.6f %.6f %.6f\n' % (c[0], c[1], c[2]))

def apply_lut(img_srgb, lut):
    """trilinear, as PPv2's 2D strip sampling (bilinear in-slice + lerp between blue slices)."""
    n = lut.shape[0]
    s = np.clip(img_srgb, 0, 1) * (n - 1)
    i0 = np.floor(s).astype(int); i0 = np.clip(i0, 0, n - 2); f = s - i0
    r0, g0, b0 = i0[..., 0], i0[..., 1], i0[..., 2]
    fr, fg, fb = f[..., 0:1], f[..., 1:2], f[..., 2:3]
    def L(db, dg, dr): return lut[b0 + db, g0 + dg, r0 + dr]
    c00 = L(0, 0, 0) * (1 - fr) + L(0, 0, 1) * fr
    c01 = L(0, 1, 0) * (1 - fr) + L(0, 1, 1) * fr
    c10 = L(1, 0, 0) * (1 - fr) + L(1, 0, 1) * fr
    c11 = L(1, 1, 0) * (1 - fr) + L(1, 1, 1) * fr
    c0 = c00 * (1 - fg) + c01 * fg
    c1 = c10 * (1 - fg) + c11 * fg
    return c0 * (1 - fb) + c1 * fb

# ALEXA LogC (PPv2 LUT_SPACE_ENCODE for HDR, non-precise path)
LOGC = dict(cut=0.011361, a=5.555556, b=0.047996, c=0.244161, d=0.386036, e=5.301883, f=0.092819)
def logc_decode(t):
    return (10 ** ((t - LOGC['d']) / LOGC['c']) - LOGC['b']) / LOGC['a']
def logc_encode(x):
    return LOGC['c'] * np.log10(LOGC['a'] * x + LOGC['b']) + LOGC['d']

def hdr_external(p, n=33):
    g = np.arange(n) / (n - 1)
    B, G, R = np.meshgrid(g, g, g, indexing='ij')
    x = np.maximum(logc_decode(np.stack([R, G, B], -1)), 0)
    pp = ppv2.full(p)
    return ppv2.grade_lut(x * 2 ** pp['postExposure'], pp)   # display-LINEAR output (PPv2 HDR path)
