# -*- coding: utf-8 -*-
"""总导演 10-26：左阙方案的俯视对比（现在 vs (c)）——阙的阙基和两层檐的外轮廓、两列灯、神道铺石和中线、崖口。
用法：python3 plan_compare.py <旧约定.json> <新约定.json> <out.png>"""
import json
import sys

from PIL import Image, ImageDraw, ImageFont

OLD_EAVE, NEW_EAVE = (5.77, 7.77), (5.47, 7.47)       # 腰檐 / 上檐里较宽的那一层的外扩（含檐板、串珠），x 半宽 / z 半深
BASE = (3.95, 5.95)
X0, X1, Z0, Z1, S = -52.0, 2.0, 18.0, 112.0, 14       # 画的范围（宫殿坐标，米）和每米像素


def panel(frame, eave, title):
    W, H = int((X1 - X0) * S), int((Z1 - Z0) * S)
    im = Image.new('RGB', (W, H + 60), (12, 20, 28))
    d = ImageDraw.Draw(im)
    tx = lambda x: (x - X0) * S
    tz = lambda z: H - (z - Z0) * S + 60
    try:
        f = ImageFont.truetype('/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc', 17)
    except OSError:
        f = ImageFont.load_default()
    e = frame['terrace']['edge_x']
    d.rectangle([tx(e), 60, W, H + 60], fill=(4, 8, 14))                                   # 崖口外（深渊）
    d.line([tx(e), 60, tx(e), H + 60], fill=(120, 120, 120), width=2)
    pv = frame['avenue']['paving']
    d.rectangle([tx(pv['x'][0]), tz(min(pv['z'][1], Z1)), tx(pv['x'][1]), tz(max(pv['z'][0], Z0))], fill=(40, 46, 50))
    ax = frame['avenue']['axis_x']
    for z in range(int(Z0), int(Z1), 4):
        d.line([tx(ax), tz(z), tx(ax), tz(z + 2)], fill=(200, 200, 200), width=2)
    gaps = []
    xs = []
    for q in frame['que']:
        cx, _, cz = q['pos']
        d.rectangle([tx(cx - eave[0]), tz(cz + eave[1]), tx(cx + eave[0]), tz(cz - eave[1])], outline=(150, 110, 150), width=3)
        d.rectangle([tx(cx - BASE[0]), tz(cz + BASE[1]), tx(cx + BASE[0]), tz(cz - BASE[1])], fill=(90, 50, 85))
        xs.append(cx)
    xs.sort()
    gap = (xs[1] - eave[0]) - (xs[0] + eave[0])
    for l in frame['lamps']:
        x, _, z = l['pos']
        if Z0 <= z <= Z1:
            d.ellipse([tx(x) - 6, tz(z) - 6, tx(x) + 6, tz(z) + 6], fill=(255, 170, 60))
    d.text((12, 12), '%s   神道中线 x %.2f，阙中距 %.1f m，两檐净距 %.2f m，灯列 x %s' % (
        title, ax, xs[1] - xs[0], gap, ' / '.join('%.2f' % c for c in frame['avenue']['columns_x'])), fill=(230, 230, 230), font=f)
    return im


if __name__ == '__main__':
    a = panel(json.load(open(sys.argv[1], encoding='utf-8')), OLD_EAVE, '现在')
    b = panel(json.load(open(sys.argv[2], encoding='utf-8')), NEW_EAVE, '(c)')
    im = Image.new('RGB', (a.width + b.width + 20, max(a.height, b.height)), (0, 0, 0))
    im.paste(a, (0, 0))
    im.paste(b, (a.width + 20, 0))
    im.save(sys.argv[3])
    print('wrote', sys.argv[3])
