# -*- coding: utf-8 -*-
"""给 lbh_render 渲出来的目标图标字、判断每个目标看不看得见（投影到像素，看那里是不是目标盘子的亮橙色）。
  ~/bpy/bin/python annotate.py /tmp/busdec <out_dir>"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(os.path.dirname(HERE), 'render_harness'))
from lbh import sheets as SH  # noqa: E402
import importlib.util  # noqa: E402
spec = importlib.util.spec_from_file_location('ts', os.path.join(HERE, 'targets_scene.py'))
# targets_scene imports bpy at module level: read the table by text instead
src = open(os.path.join(HERE, 'targets_scene.py'), encoding='utf-8').read()
TARGETS = eval(src[src.index('TARGETS = [') + len('TARGETS = '):src.index(']\n\n\ndef build') + 1])


def project(cam, W, H, az, el):
    a, e = math.radians(az), math.radians(el)
    d = np.array([math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a)])
    y, p = math.radians(cam.get('yaw_deg', 0)), math.radians(cam.get('pitch_deg', 0))
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])
    c = (Ry @ Rx).T @ d
    if c[2] <= 0.05:
        return None
    fx = (W / 2.0) / math.tan(math.radians(cam['hfov_deg']) / 2)
    return (W / 2.0 + fx * c[0] / c[2], H / 2.0 - fx * c[1] / c[2])


def main(src_dir, out_dir):
    os.makedirs(out_dir, exist_ok=True)
    table = {}
    items = []
    for name in sorted(os.listdir(src_dir)):
        d = os.path.join(src_dir, name)
        if not os.path.exists(os.path.join(d, 'metrics.json')):
            continue
        m = json.load(open(os.path.join(d, 'metrics.json'), encoding='utf-8'))
        cam = m['cam']
        im = Image.open(os.path.join(d, 'graded.png')).convert('RGB')
        W, H = im.size
        arr = np.asarray(im).astype(float)
        dr = ImageDraw.Draw(im)
        f = SH.font(16)
        bus = name.rsplit('_', 1)[0]
        for tn, az, el in TARGETS:
            p = project(cam, W, H, az, el)
            if p is None or not (2 <= p[0] < W - 2 and 2 <= p[1] < H - 2):
                continue
            x, y = int(p[0]), int(p[1])
            patch = arr[max(0, y - 2):y + 3, max(0, x - 2):x + 3]
            vis = bool((patch.mean(-1) > 200).any())
            table.setdefault(bus, {})
            table[bus][tn] = table[bus].get(tn, False) or vis
            col = (120, 230, 140) if vis else (255, 90, 90)
            dr.ellipse([x - 9, y - 9, x + 9, y + 9], outline=col, width=2)
            dr.text((x + 11, y - 10), tn + ('' if vis else '（挡住）'), fill=col, font=f)
        p = os.path.join(out_dir, name + '.png')
        im.save(p)
        items.append((p, '%s  眼位 %s  看向 %+.0f° / %+.0f°  水平 %.0f°' % (name, cam['eye'], cam.get('yaw_deg', 0), cam.get('pitch_deg', 0), cam['hfov_deg'])))
    SH.contact_sheet(items, os.path.join(out_dir, 'sheet.png'), cols=3, cell_w=640,
                     title='车的决定（D-03）：圣经的取景目标在两种车里看不看得见（绿 = 看得见，红 = 被车挡住）')
    json.dump(table, open(os.path.join(out_dir, 'visibility.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    return table


if __name__ == '__main__':
    t = main(sys.argv[1], sys.argv[2])
    for bus, d in t.items():
        print(bus, sum(d.values()), '/', len(d), [k for k, v in d.items() if not v])
