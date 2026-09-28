"""Corrections to lens_cine/ppv2.py used by every v2 script.
1. AP1->sRGB matrix rebuilt exactly as Unity ACES.hlsl (v1 fix).
2. GammaToLinearSpaceExact (UnityCG.cginc) for bloom threshold and clamp: sRGB curve below 1, pow 2.2 at/above 1.
3. Bloom: clamp applied in the prefilter (PPv2 Bloom.shader), pyramid depth computed for a 1920-px-wide screen
   (PPv2: iterations = floor(log2(screenW/2) + min(diffusion,10) - 10)), blur radii scaled to the image width,
   so a 960-px preview blooms like the 1080p desktop frame it stands for."""
import numpy as np

_AP1_2_XYZ = np.array([[0.6624541811, 0.1340042065, 0.1561876870],
                       [0.2722287168, 0.6740817658, 0.0536895174],
                       [-0.0055746495, 0.0040607335, 1.0103391003]])
_D60_2_D65 = np.array([[0.98722400, -0.00611327, 0.0159533],
                       [-0.00759836, 1.00186000, 0.0053302],
                       [0.00307257, -0.00509595, 1.0816800]])
_XYZ_2_709 = np.array([[3.2409699419, -1.5373831776, -0.4986107603],
                       [-0.9692436363, 1.8759675015, 0.0415550574],
                       [0.0556300797, -0.2039769589, 1.0569715142]])
REF_W = 1920
CLAMP_LIN = 24.0

def g2l(t):
    t = float(t)
    if t <= 0.04045: return t / 12.92
    if t < 1.0: return ((t + 0.055) / 1.055) ** 2.4
    return t ** 2.2

def l2g(x):
    x = float(x)
    if x >= 1.0: return x ** (1 / 2.2)
    lo, hi = 0.0, 1.0
    for _ in range(80):
        m = 0.5 * (lo + hi)
        if g2l(m) < x: lo = m
        else: hi = m
    return 0.5 * (lo + hi)

def patch_ppv2(ppv2):
    ppv2.AP1_2_sRGB = _XYZ_2_709 @ _D60_2_D65 @ _AP1_2_XYZ
    ppv2.gamma_to_lin_scalar = g2l

    def bloom_layer(img, p, levels=None):
        from scipy.ndimage import gaussian_filter
        b = p['bloom']
        if b['intensity'] <= 0:
            return np.zeros_like(img)
        x = np.minimum(img, CLAMP_LIN)
        thr = g2l(b['threshold'])
        knee = thr * b['softKnee'] + 1e-5
        br = x.max(-1)
        rq = np.clip(br - (thr - knee), 0, knee * 2)
        rq = (0.25 / knee) * rq * rq
        pre = x * (np.maximum(rq, br - thr) / np.maximum(br, 1e-5))[..., None]
        h, w = img.shape[:2]
        logs = np.log2(REF_W / 2) + min(b['diffusion'], 10) - 10
        n = int(np.clip(np.floor(logs), 1, 16)) if levels is None else levels
        sc = w / REF_W
        acc = np.zeros_like(img)
        for i in range(n):
            s = max(2.0 ** (i + 1) * 0.9 * sc, 0.5)
            acc += gaussian_filter(pre, sigma=(s, s, 0), mode='nearest')
        k = 2 ** (b['intensity'] / 10) - 1
        return acc * k * ppv2.hex_to_lin(b['color'])
    ppv2.bloom_layer = bloom_layer
    return ppv2
