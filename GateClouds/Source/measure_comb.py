"""蓝白 / Lanbai · gate clouds kit · the art review's comb metric (美术审片意见 P1).

On contour pixels (vertical gradient > 12 codes), the fraction whose horizontal neighbour differences alternate in
sign with both magnitudes > 4 codes (a 1-px comb). Target <= 8 %; the Blender final's deck ~2 %.

  python3 measure_comb.py image.png [--rows 0.62 1.0] [--cols 0 1]
"""
import sys

import numpy as np
from PIL import Image


def comb_ratio(path, rows=(0.62, 1.0), cols=(0.0, 1.0)):
    a = np.asarray(Image.open(path).convert('RGB')).astype(float) @ [0.2126, 0.7152, 0.0722]
    h, w = a.shape
    a = a[int(rows[0] * h):int(rows[1] * h), int(cols[0] * w):int(cols[1] * w)]
    gy = np.abs(a[1:, 1:-1] - a[:-1, 1:-1])
    dl = a[1:, 1:-1] - a[1:, :-2]
    dr = a[1:, 2:] - a[1:, 1:-1]
    contour = gy > 12
    alt = (np.sign(dl) != np.sign(dr)) & (np.abs(dl) > 4) & (np.abs(dr) > 4)
    return float((alt & contour).sum() / max(contour.sum(), 1)), int(contour.sum())


if __name__ == '__main__':
    a = sys.argv[1:]
    rows = tuple(float(x) for x in a[a.index('--rows') + 1:a.index('--rows') + 3]) if '--rows' in a else (0.62, 1.0)
    cols = tuple(float(x) for x in a[a.index('--cols') + 1:a.index('--cols') + 3]) if '--cols' in a else (0.0, 1.0)
    r, n = comb_ratio(a[0], rows, cols)
    print('%s: comb %.1f %% of %d contour px' % (a[0], 100 * r, n))
