# -*- coding: utf-8 -*-
"""全片总览图：按时间轴把各幕的主机位排成一条，下面是 §2.2 的 APL 目标曲线和实测点、目标平均色和实测平均色。
看颜色和亮度的走向是不是圣经 §2 的“褪色”。来源在 Review/overview_sources.json。
用法: python3 Tools~/make_overview.py [out.png]   (默认 Review/全片总览.png)"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
REV = os.path.dirname(HERE)
ROOT = os.path.dirname(REV)
sys.path.insert(0, HERE)
import measure as M
FONT = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
f = lambda s: ImageFont.truetype(FONT, s)
T = json.load(open(os.path.join(REV, 'targets.json'), encoding='utf-8'))
SRC = json.load(open(os.path.join(REV, 'overview_sources.json'), encoding='utf-8'))['acts']
SEG = {s['key']: s for s in T['segments']}


def load_main(e):
    if e['kind'] == 'black':
        return Image.new('RGB', (1920, 1080), (3, 4, 9))
    if e['kind'] == 'white':
        return Image.new('RGB', (1920, 1080), (0xE8, 0xF1, 0xF5))
    if not e['img']:
        return None
    im = Image.open(os.path.join(ROOT, e['img'])).convert('RGB')
    if e['kind'] == 'bible':           # previews: crop the "after" panel
        W = im.width / 2024
        im = im.crop((int(1012 * W), int(117 * W), int(1960 * W), int(513 * W)))
    return im


TW, TH = 300, 169
acts = SRC
W = 60 + len(acts) * (TW + 12) + 40
H = 1080
out = Image.new('RGB', (W, H), (14, 15, 19))
d = ImageDraw.Draw(out)
d.text((40, 20), '蓝白 · 全片总览（美术审片）：各幕主机位按时间顺序；下面是 §2.2 的 APL 目标与实测、目标平均色与实测平均色', font=f(26), fill=(232, 241, 245))
d.text((40, 58), '标签：渲染 = 包的渲染；Unity = 本地截图；圣经 = 圣经测试帧（还没有真图，占位）；缺 = 还没有任何图', font=f(17), fill=(150, 158, 168))
y0 = 100
plot_y0, plot_h = 420, 330
d.text((40, plot_y0 - 30), 'APL（桌面正前方，含 bloom）：线 = §2.2 目标（±15% 带）；点 = 实测（主机位）', font=f(17), fill=(170, 178, 190))
ymax = 250
def py(v): return plot_y0 + plot_h - v / ymax * plot_h
for v in (0, 50, 100, 150, 200, 250):
    d.line((40, py(v), W - 30, py(v)), fill=(40, 44, 52))
    d.text((8, py(v) - 8), str(v), font=f(13), fill=(110, 118, 128))
rows = []
meas_pts = []
for i, e in enumerate(acts):
    x = 60 + i * (TW + 12)
    im = load_main(e)
    S = SEG[e['seg']]
    lbl = {'render': '渲染', 'unity': 'Unity', 'bible': '圣经', 'black': '黑', 'white': '白', 'missing': '缺'}[e['kind']]
    d.text((x, y0), f"{e['act']}  {S['name']}  t≈{e['t']}", font=f(18), fill=(220, 226, 232))
    d.text((x, y0 + 24), f"[{lbl}]  {S['profile']}", font=f(14), fill=(140, 150, 160) if e['kind'] != 'missing' else (220, 120, 90))
    meas = None
    if im is not None:
        th = im.resize((TW, TH), Image.LANCZOS)
        out.paste(th, (x, y0 + 46))
        tmp = '/tmp/_ov_%d.png' % i
        im.save(tmp)
        meas = M.measure(tmp, e['act'] if e['act'] in T['acts'] else '4', e['seg'])
    else:
        d.rectangle((x, y0 + 46, x + TW, y0 + 46 + TH), outline=(120, 60, 50))
        d.text((x + 20, y0 + 120), '还没有图', font=f(20), fill=(200, 110, 90))
    # target band
    a = S['APL']
    cx0, cx1 = x + 20, x + TW - 20
    pts = [(cx0 + (cx1 - cx0) * k / max(1, len(a) - 1), py(v)) for k, v in enumerate(a)] if len(a) > 1 else [(cx0, py(a[0])), (cx1, py(a[0]))]
    for (xa, ya), (xb, yb) in zip(pts, pts[1:]):
        d.line((xa, ya, xb, yb), fill=(140, 170, 210), width=3)
    lo, hi = min(a) * 0.85, max(a) * 1.15
    d.rectangle((cx0, py(hi), cx1, py(lo)), outline=(60, 80, 110))
    if meas:
        ok = meas['APL_target']['pass']
        mx = (cx0 + cx1) / 2
        col = (110, 210, 140) if ok else (240, 110, 90)
        d.ellipse((mx - 7, py(meas['APL']) - 7, mx + 7, py(meas['APL']) + 7), fill=col)
        d.text((mx + 10, py(meas['APL']) - 9), f"{meas['APL']}", font=f(14), fill=col)
        meas_pts.append((mx, py(meas['APL'])))
    # colour bars
    by = plot_y0 + plot_h + 30
    d.text((x, by), '目标平均色（§2.2 段色≈色板主色）', font=f(12), fill=(130, 138, 148))
    pal = T['acts'][e['act']].get('palette', []) if e['act'] in T['acts'] else []
    if pal:
        cols = [M.hex_rgb(p['hex']) for p in pal]
        n = len(cols)
        for k, c in enumerate(cols):
            d.rectangle((x + k * TW / n, by + 18, x + (k + 1) * TW / n, by + 58), fill=tuple(int(v * 255) for v in c))
    d.text((x, by + 66), '实测：画面平均色 · 紫块% · 最亮簇', font=f(12), fill=(130, 138, 148))
    if meas:
        c = M.hex_rgb(meas['mean_colour_hex'])
        d.rectangle((x, by + 84, x + TW, by + 124), fill=tuple(int(v * 255) for v in c))
        vt = meas['violet_h290_325_C15']['largest_region_pct']
        d.text((x, by + 130), f"{meas['mean_colour_hex']}  紫块 {vt}%  簇 {meas['brightest_2000']['clusters_ge5pct']}", font=f(13),
               fill=(240, 110, 90) if (vt > 2 and e['act'] not in ('4', '4c')) else (170, 178, 190))
    rows.append((e['act'], e['kind'], meas and meas['APL'], meas and meas['mean_colour_hex']))
for (xa, ya), (xb, yb) in zip(meas_pts, meas_pts[1:]):
    d.line((xa, ya, xb, yb), fill=(200, 200, 120), width=1)
d.text((40, H - 40), '生成：Review/Tools~/make_overview.py；来源表 Review/overview_sources.json。圣经测试帧是程序化帧，只看走向，不当实测。', font=f(15), fill=(110, 118, 128))
dst = sys.argv[1] if len(sys.argv) > 1 else os.path.join(REV, '全片总览.png')
out.save(dst)
for r in rows: print(r)
print('->', dst)
