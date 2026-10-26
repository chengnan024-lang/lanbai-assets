"""蓝白 / Lanbai · gate clouds kit · rim crawl in a scrolling PNG sequence (round 10).

Art/tools/lens_tech/flashcheck.py measures flashes on 4.4-degree tiles and the APL ramp; it cannot see a 1-2 px rim that
shimmers as the deck scrolls. Here, per pixel: frame-to-frame luma changes larger than 12 codes; a pixel CRAWLS when such
changes reverse sign at least twice within 10 frames (a contour passing by changes once; a shimmering one flips).
Reported over the lower half of the frame (the deck), by column thirds, plus a red map over a frame.

Also: per frame, the share of deck pixels changing by more than 4 codes (总导演 10-26: <= 0.2 %).

  python3 measure_crawl.py <frames_dir> [--frames 30] [--map out.png]
"""
import glob
import sys

import numpy as np
from PIL import Image


def crawl(frames, thr=12.0, win=10, step=5):
    A = np.stack([np.asarray(Image.open(f).convert('RGB')).astype(np.float32) @ [0.2126, 0.7152, 0.0722] for f in frames])
    d = np.diff(A, axis=0)
    sgn = np.sign(d) * (np.abs(d) > thr)
    worst = np.zeros(A.shape[1:], int)
    for s in range(0, max(d.shape[0] - win, 1), step):
        last = np.zeros(A.shape[1:])
        cnt = np.zeros(A.shape[1:], int)
        for k in range(min(win, d.shape[0] - s)):
            cur = sgn[s + k]
            cnt += (cur != 0) & (last != 0) & (cur != last)
            last = np.where(cur != 0, cur, last)
        worst = np.maximum(worst, cnt)
    return A, worst


if __name__ == '__main__':
    a = sys.argv[1:]
    n = int(a[a.index('--frames') + 1]) if '--frames' in a else None
    fs = sorted(glob.glob(a[0] + '/f*.png'))[:n]
    A, worst = crawl(fs)
    h, w = worst.shape
    deck = worst[h // 2:]
    print('%s (%d frames): deck pixels with >= 2 reversals in 10 frames %.3f %%, >= 3 %.3f %%  | thirds %.3f / %.3f / %.3f %%'
          % (a[0], len(fs), 100 * (deck >= 2).mean(), 100 * (deck >= 3).mean(),
             100 * (deck[:, :w // 3] >= 2).mean(), 100 * (deck[:, w // 3:2 * w // 3] >= 2).mean(),
             100 * (deck[:, 2 * w // 3:] >= 2).mean()))
    # 总导演 10-26 A: per frame, the share of deck pixels that change by more than 4 codes (mean and worst frame)
    dd = np.abs(np.diff(A[:, h // 2:], axis=0)) > 4.0
    per = 100 * dd.mean(axis=(1, 2))
    print('   per-frame deck pixels changing > 4 codes: mean %.3f %%, worst frame %.3f %%' % (per.mean(), per.max()))
    if '--map' in a:
        f = Image.open(fs[len(fs) // 2]).convert('RGB')
        m = Image.fromarray(((worst >= 2) * 255).astype(np.uint8))
        Image.blend(f, Image.merge('RGB', (m, Image.new('L', m.size, 0), Image.new('L', m.size, 0))), 0.45).save(a[a.index('--map') + 1])
