"""蓝白 / Lanbai · gate clouds kit · round 4 measurements for the art review r2 numbers.

Deck region = the lowest 45 % of the frame. Rim pixels = brighter than their 15 px median by > 12 codes.
Prints p5 / p50 / p95 / p99.5 of the deck and p95 / p99.5 of the rim pixels (codes, Rec.709 luma of the graded PNG).
Art r2 targets: rim p99.5 <= 150, rim p95 >= 100, deck p5 ~ 20.

  /tmp/claude-0/venv/bin/python measure_rims.py image.png [...]
"""
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import median_filter


def stats(path):
    a = np.asarray(Image.open(path).convert('RGB')).astype(float) @ [0.2126, 0.7152, 0.0722]
    d = a[int(a.shape[0] * 0.55):]
    rim = d[(d - median_filter(d, size=15)) > 12]
    out = dict(p5=np.percentile(d, 5), p50=np.percentile(d, 50), p95=np.percentile(d, 95), p995=np.percentile(d, 99.5))
    out.update(rim_px=rim.size, rim_p95=np.percentile(rim, 95) if rim.size else 0.0,
               rim_p995=np.percentile(rim, 99.5) if rim.size else 0.0)
    return out


if __name__ == '__main__':
    for p in sys.argv[1:]:
        s = stats(p)
        print('%s: deck p5 %.0f p50 %.0f p95 %.0f p99.5 %.0f | rim px %d p95 %.0f p99.5 %.0f'
              % (p, s['p5'], s['p50'], s['p95'], s['p995'], s['rim_px'], s['rim_p95'], s['rim_p995']))
