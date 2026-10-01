"""S4 grade for tear kit v2 renders: scene-linear (fill space) -> display sRGB, via the bible's PPv2 simulator."""
import os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import grade as g  # tear/grade.py (bible simulator wrapper)

LENS_CLEAN = dict(intensity=0.20, smoothness=0.40, roundness=1.0, color='#02040A')


def to_display(lin, bloom=True, vignette=True):
    p = dict(g.S4)
    if vignette:
        p['vignette'] = LENS_CLEAN
    p = g.ppv2.full(p)
    x = np.maximum(np.asarray(lin, np.float64), 0)
    if bloom:
        x = x + g.ppv2.bloom_layer(x, p)
    if vignette:
        x = g.ppv2.vignette(x, p)
    x = x * 2 ** p['postExposure']
    return np.clip(g.ppv2.lin_to_srgb(g.ppv2.grade_lut(x, p)), 0, 1)


def save(disp, path, seed=0):
    rng = np.random.default_rng(seed)
    n = (rng.random(disp.shape[:2]) + rng.random(disp.shape[:2]) - 1.0)[..., None] / 255.0
    Image.fromarray(np.round(np.clip(disp + n, 0, 1) * 255).astype(np.uint8)).save(path)
