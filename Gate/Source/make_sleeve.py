"""Gate_RootSleeve_512.png (round 3, critique B6.1): the cloud an arm drags up where it leaves the sea.
A camera-facing card centred on the root: RGB = billow luminance (straight, sRGB), A = coverage. Across: a soft
column ~1.2-1.8 x the arm's diameter wide at the bottom, narrowing upward; up: dense at the deck, thinning into a
RAGGED top that streams DOWN (vertical streaks), gone by the top of the card (card height = 60-150 m). Edges are soft
everywhere (>= 6 px at 1 km); the bottom is buried under the deck."""
import os
import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

HERE = os.path.dirname(os.path.abspath(__file__))


def field(shape, sig, seed):
    r = np.random.default_rng(seed).standard_normal(shape)
    f = gaussian_filter(r, sig, mode='wrap')
    return f / (f.std() + 1e-9)


def make(N=512, seed=3):
    y = (np.arange(N) + 0.5)[:, None] / N            # 0 = bottom (we flip at the end)
    x = (np.arange(N) + 0.5)[None, :] / N
    ax = np.abs(x - 0.5) * 2
    # streaks running down: noise stretched vertically
    st = field((N, N), (70, 26), seed) * 0.8 + field((N, N), (30, 14), seed + 1) * 0.2     # resume: no thin streaks (a barcode at 0.5 km)
    billow = field((N, N), (26, 22), seed + 2) * 0.7 + field((N, N), (10, 9), seed + 3) * 0.3
    # the top edge: ragged, and higher in the middle (the arm drags it up)
    top = 0.55 + 0.30 * (1 - ax ** 1.6) + 0.07 * field((1, N), (1, 30), seed + 4)[0][None, :]
    h = y / np.clip(top, 0.2, 1.0)
    dens = np.clip(1.0 - h ** 1.6 + 0.16 * st * np.clip(h, 0, 1), 0, 1)
    width = 1.0 - 0.45 * np.clip(y, 0, 1)            # narrows upward
    col = np.clip(1 - ((ax / width) ** 2.2), 0, 1)
    a = dens * col * (0.85 + 0.15 * billow)
    a = np.maximum(a, np.clip(1.0 - y / 0.18, 0, 1) * np.clip(1 - ((ax / 0.92) ** 4), 0, 1))     # solid at the deck
    a = np.clip(gaussian_filter(a, 4.0), 0, 1)
    lum = np.clip(0.62 + 0.10 * billow + 0.20 * y - 0.06 * st, 0, 1)      # brighter toward the lit top
    rgb = np.repeat(lum[..., None], 3, -1)
    img = np.concatenate([(rgb * 255 + 0.5), (a[..., None] * 255 + 0.5)], -1).clip(0, 255).astype(np.uint8)
    return img[::-1]


if __name__ == '__main__':
    out = os.path.join(HERE, 'Textures', 'Gate_RootSleeve_512.png')
    Image.fromarray(make(), 'RGBA').save(out)
    print(out)
