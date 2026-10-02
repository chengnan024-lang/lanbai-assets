"""run 9: before / after sheet of the five things changed after the round-8 finals were rendered.
    python3 compare_r9.py   -> final/compare_r9_patch.png
before = final/_superseded/r6_pre_r9 (the round-8 finals), after = final/. Labels carry the measured numbers."""
import os
import sys
import json

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tear', 'v2'))
from metrics import lab  # noqa: E402

B = os.path.join(HERE, 'final', '_superseded', 'r6_pre_r9')
A = os.path.join(HERE, 'final')


def font(sz):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', '/usr/share/fonts/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, sz)
    return ImageFont.load_default()


def Lstar(img):
    return lab(np.asarray(img.convert('RGB')).astype(float))[0]


def bright_px(img, box):
    L = Lstar(img.crop(box))
    return int((L > 80).sum())


ROWS = [  # (title, file, crop box (x0, y0, x1, y1), zoom)
    ('1  rip branch: smooth white cone (a horn) -> ragged crack, pinches, bridging threads', 'keyart_239.png', (1120, 110, 1290, 330), 2.2),
    ('2  Engel at the top edge: grazing moon glint (L* 100) -> rim only (hero spec far 0.15 -> 0.01)', 'keyart_239.png', (1250, 0, 1500, 200), 1.6),
    ('3  multitude: LOD2 facets, no rims at 3-5 km -> LOD by screen height, tier A/B rim floor', 'keyart_239.png', (0, 380, 760, 760), 0.8),
    ('4  U8 forward foot: 40-px straight lens / cloud-plane line -> ends on a low backlit billow row', 'U8_forward.png', (860, 600, 1100, 720), 2.0),
    ('5  rear window: fingers = fangs / icicles -> varied tentacle tips in the picture plane', 'rear_window.png', (560, 120, 1500, 900), 0.5),
]


def main():
    f, fs = font(22), font(18)
    tiles = []
    for title, fn, box, z in ROWS:
        pb, pa = os.path.join(B, fn), os.path.join(A, fn)
        if not (os.path.exists(pb) and os.path.exists(pa)):
            print('skip', fn)
            continue
        ib, ia = Image.open(pb).convert('RGB'), Image.open(pa).convert('RGB')
        cb, ca = ib.crop(box), ia.crop(box)
        w, h = int(cb.size[0] * z), int(cb.size[1] * z)
        cb, ca = cb.resize((w, h), Image.LANCZOS), ca.resize((w, h), Image.LANCZOS)
        nb, na = bright_px(ib, box), bright_px(ia, box)
        tw = int(ImageDraw.Draw(Image.new('RGB', (8, 8))).textlength(title, font=f)) + 24
        t = Image.new('RGB', (max(2 * w + 30, tw), h + 70), (16, 18, 24))
        d = ImageDraw.Draw(t)
        d.text((10, 6), title, fill=(230, 230, 236), font=f)
        t.paste(cb, (10, 40))
        t.paste(ca, (20 + w, 40))
        for (x_, txt, colr) in ((14, 'round 8  (L*>80: %d px)' % nb, (255, 210, 120)), (24 + w, 'run 9  (L*>80: %d px)' % na, (140, 230, 160))):
            bb = d.textbbox((x_, 44), txt, font=fs)
            d.rectangle((bb[0] - 4, bb[1] - 3, bb[2] + 4, bb[3] + 3), fill=(10, 11, 16))
            d.text((x_, 44), txt, fill=colr, font=fs)
        tiles.append(t)
    if not tiles:
        return
    W = max(t.size[0] for t in tiles)
    H = sum(t.size[1] for t in tiles) + 10 * len(tiles)
    out = Image.new('RGB', (W, H), (8, 9, 12))
    y = 0
    for t in tiles:
        out.paste(t, (0, y))
        y += t.size[1] + 10
    sc = min(1.0, 1900.0 / W)
    out = out.resize((int(W * sc), int(H * sc)), Image.LANCZOS)
    p = os.path.join(A, 'compare_r9_patch.png')
    out.save(p)
    print('wrote', p, out.size)


if __name__ == '__main__':
    main()
