# -*- coding: utf-8 -*-
"""D-36 对照板：近景渲染（左两列）+ 真车照片（右列），写 Bus/Docs~/detail/<part>/compare.png。

    python3 Bus/Source/parts/compare.py --part seat --renders a.png,b.png,... --photos p1.jpg,p2.jpg --title "..."
"""
import argparse
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--part', required=True)
    ap.add_argument('--renders', required=True)
    ap.add_argument('--photos', required=True)
    ap.add_argument('--title', default='')
    a = ap.parse_args()
    R = [p for p in a.renders.split(',') if p]
    P = [p for p in a.photos.split(',') if p]
    W, H = 640, 360
    rows = max((len(R) + 1) // 2, len(P))
    sheet = Image.new('RGB', (W * 3, 28 + (H + 22) * rows), (14, 14, 16))
    d = ImageDraw.Draw(sheet)
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 15)
        cjk = os.path.join(ROOT, 'Fonts', 'Originals~', 'SourceHanSerifCN-Medium.otf')
        fc = ImageFont.truetype(cjk, 16) if os.path.exists(cjk) else f
    except Exception:
        f = fc = ImageFont.load_default()
    d.text((8, 5), a.title, fill=(230, 230, 230), font=fc)

    def put(path, x, y, label):
        im = Image.open(path).convert('RGB')
        im.thumbnail((W, H))
        sheet.paste(im, (x + (W - im.width) // 2, y + 22 + (H - im.height) // 2))
        d.text((x + 6, y + 3), label, fill=(200, 200, 200), font=fc)

    for i, p in enumerate(R):
        put(p, (i % 2) * W, 28 + (i // 2) * (H + 22), '渲染 · ' + os.path.splitext(os.path.basename(p))[0])
    for i, p in enumerate(P):
        put(p, 2 * W, 28 + i * (H + 22), '照片 · ' + os.path.splitext(os.path.basename(p))[0])
    out = os.path.join(ROOT, 'Bus', 'Docs~', 'detail', a.part)
    os.makedirs(out, exist_ok=True)
    sheet.save(os.path.join(out, 'compare.png'))
    print('[compare]', os.path.join(out, 'compare.png'), sheet.size)


if __name__ == '__main__':
    main()
