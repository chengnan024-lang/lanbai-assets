# -*- coding: utf-8 -*-
"""总导演终审 r2：证明“往下滑”读得出来。965.4 → 987.4 每 2 s 一帧正前（+3 m/s 匀速上升），并排成一张条带图（左半边：近层、中层的卡），
再给出近层卡（1.4–1.9 km）的仰角随时间：每秒 0.09–0.12°，22 s 里滑 2–2.7°。写 Docs~/iterations/05_rise_strip.png 和 Docs~/rise_strip.json。"""
import os
import sys
import json
import math
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import act08_ref as R  # noqa: E402
import act08_layout as AL  # noqa: E402

R.POEM_ON = False


def main():
    ts = np.arange(965.4, 987.41, 2.0)
    tiles = []
    for t in ts:
        codes, m, lin = R.render(float(t), 'hero', 960, 'bible_v2')
        tile = Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).crop((0, 60, 480, 420))
        d = ImageDraw.Draw(tile)
        d.line([(0, 210), (480, 210)], fill=(255, 255, 255), width=1)          # a fixed reference line
        d.text((6, 6), '%.1f s' % t, fill=(255, 255, 255))
        tiles.append(tile)
    W, H = tiles[0].size
    sheet = Image.new('RGB', (W * 6, H * 2), (20, 20, 20))
    for i, tl in enumerate(tiles):
        sheet.paste(tl, ((i % 6) * W, (i // 6) * H))
    sheet.save(os.path.join(KIT, 'Docs~', 'iterations', '05_rise_strip.png'))
    near = [c for c in R.LAYOUT['cards'] if c.get('layer') in ('near', 'near-right', 'mid')]
    out = {}
    for c in near:
        els = [round(math.degrees(math.atan((c['position_local'][1] + AL.motion(float(t))[0] - AL.EYE[1]) / c['dist'])), 2) for t in ts]
        out[c['id']] = dict(dist=c['dist'], layer=c['layer'], el=els, deg_per_s=round((els[0] - els[-1]) / (ts[-1] - ts[0]), 3))
        print(c['id'], out[c['id']]['deg_per_s'], 'deg/s', els[0], '->', els[-1])
    json.dump(dict(t=[round(float(t), 1) for t in ts], cards=out), open(os.path.join(KIT, 'Docs~', 'rise_strip.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
