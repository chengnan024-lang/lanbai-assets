# -*- coding: utf-8 -*-
"""设计板附：“云上 → 穿云 → 云下”的连续对照（阿白要的，D-44 #2）。同一条路线、同几个时刻、主座位往前看：
左 = 现在交付的不透明云原（Lanbai_CloudPlain，act06_ref），右 = 体积云（act06_vol）。最后一行是“云自己在流”：
车停在 300 s 的位置不动，云按 290 / 300 / 310 的时钟各渲一张。-> Docs~/design_v3/strip_above_through_below.png、strip.json"""
import os
import sys
import json
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import act06_vol as AV  # noqa: E402
import act06_ref as A6  # noqa: E402

OUT = os.path.join(AV.KIT, 'Docs~', 'design_v3')
FONT = os.path.join(AV.REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf')
ROWS = [(270.0, '云上：云原在下方 300 m'), (285.0, '谷在散开，车快到云原顶'), (291.5, '穿进第一团（谷里，漂过来的）'),
        (296.0, '在谷里：两壁一团一团，透光'), (299.8, '穿进第二团'), (303.5, '谷底，太阳被谷尽头挡住'),
        (306.0, '出云底：上面是起伏的云底，下面 B 层在散开'), (312.0, '云下：云盖底、B 层、海'),
        (326.5, '穿过 B 层的一团'), (335.0, '云下：B 层之下，海镜')]
W = 480


def font(px):
    return ImageFont.truetype(FONT, px)


def label(im, text, sub=''):
    d = ImageDraw.Draw(im)
    d.rectangle([0, 0, im.width, 24], fill=(0, 0, 0))
    d.text((6, 2), text, fill=(255, 255, 255), font=font(15))
    if sub:
        d.text((6, im.height - 20), sub, fill=(255, 255, 210), font=font(13))
    return im


def main():
    AV.scene().scene.step_k = 0.006
    A6.SKY = AV.C.read_hdr('/tmp/lb/sky2/sky_dawn_1024.hdr').astype(np.float64)
    rows, meta = [], {}
    for t, cap in ROWS:
        c0, m0, _ = A6.render(t, 'hero', W)
        c1, m1 = AV.render(t, 'hero', W)
        a = label(Image.fromarray(np.clip(c0, 0, 255).astype(np.uint8)), f'{t:.1f} 现在（不透明云原）', f"APL {m0['APL']}")
        b = label(Image.fromarray(np.clip(c1, 0, 255).astype(np.uint8)), f'{t:.1f} 体积云：{cap}', f"APL {m1['APL']}  日光透过 {m1['sun_visible']}")
        rows.append((a, b))
        meta['%.1f' % t] = dict(plain=m0, volume=m1)
        print(t, m0['APL'], m1['APL'], flush=True)
    flow = []
    for tc in (290.0, 300.0, 310.0):
        c, m = AV.render(tc, 'hero', W, t_bus=300.0)
        flow.append(label(Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)), f'车停在 300 s 的位置，云的时钟 {tc:.0f}'))
        meta['flow_%.0f' % tc] = m
    w, h = rows[0][0].size
    head = 40
    sheet = Image.new('RGB', (w * 3, head + h * len(rows) + h), (16, 18, 22))
    ImageDraw.Draw(sheet).text((10, 8), '云上 → 穿云 → 云下（主座位往前看）。左：现在的不透明云原；中：体积云。最后一行：车不动、云自己流（风 2–5 m/s，20 秒）',
                               fill=(240, 240, 240), font=font(17))
    for i, (a, b) in enumerate(rows):
        sheet.paste(a, (0, head + i * h))
        sheet.paste(b, (w, head + i * h))
    for k, f in enumerate(flow):
        sheet.paste(f, (k * w, head + len(rows) * h))
    sheet.save(os.path.join(OUT, 'strip_above_through_below.png'))
    json.dump(meta, open(os.path.join(OUT, 'strip.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
