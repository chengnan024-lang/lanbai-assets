# -*- coding: utf-8 -*-
"""设计板（D-44 #2）：六个时刻从主座位往前看 + 三张补充机位，拼成一张，带说明。
输入：act06_vol.py 渲好的帧（--src，默认 /tmp/lb/a6board）。-> Docs~/design_v3/frames/*.png、board.png、board.json"""
import os
import sys
import json
import shutil
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
OUT = os.path.join(KIT, 'Docs~', 'design_v3')
FONT = os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf')

MAIN = [
    ('hero', 251.6, '251.6 F0：黑里第一声号角（这一帧实际还是黑；画的是 266.3 天亮就位后同一位置的样子）。云原在下方 470 m，一直铺到地平线；云塔 −25°'),
    ('hero', 282.0, '282 F1：长笛鸟鸣。前下方朝太阳的谷开始散开（谷里的云团被风吹散，不是墙升起来）；谷外云原照旧'),
    ('hero', 305.4, '305.4 出云底：太阳被谷尽头的云墙挡住（303 起变暗、305 挡尽）；下层 B 开始散开，海第一次露出来'),
    ('hero', 318.4, '318.4 F1b1：太阳从上层朝日那个湾的边下面出来（318.0 → 318.8）；B 层朝日一侧已散开，海上铺出日光'),
    ('hero', 340.0, '340 海镜：在 B 层之下（离海 270 m），头顶是 B 层的底和它的空隙，太阳低低地从湾里照过来'),
    ('hero', 360.0, '360：离海 3 m，镜子填满下半个视野；B 层的底在 650 m 之上'),
]
EXTRA = [
    ('door_d12', 300.0, '补 300 车门：在谷里，朝太阳看，谷的两壁是一团一团的，谷里漂着稀的云团'),
    ('hero_up60', 310.0, '补 310 抬头 60°：上层的底从下面看，是起伏、有空隙的云底，不是长方形的布（截图 02 的问题）'),
    ('hero_down', 330.0, '补 330 往下：刚穿过 B 层，下面的空隙一直开到海面'),
]


def font(px):
    return ImageFont.truetype(FONT, px)


def tile(src, cam, t, caption, W=640):
    p = os.path.join(src, f'{cam}_t{t:.1f}.png')
    j = os.path.join(src, f'{cam}_t{t:.1f}.json')
    im = Image.open(p).convert('RGB')
    im = im.resize((W, int(im.height * W / im.width)))
    m = json.load(open(j))
    cap = Image.new('RGB', (W, 64), (24, 26, 30))
    d = ImageDraw.Draw(cap)
    words, line, lines = caption, '', []
    for ch in words:
        if d.textlength(line + ch, font=font(15)) > W - 16:
            lines.append(line)
            line = ''
        line += ch
    lines.append(line)
    for k, ln in enumerate(lines[:3]):
        d.text((8, 4 + 19 * k), ln, fill=(230, 230, 230), font=font(15))
    info = f"APL {m['APL']}  日光透过 {m['sun_visible']}  海 {m['sea_px'] * 100:.1f} %  紫 {m['purple_D21'] * 100:.2f} %"
    out = Image.new('RGB', (W, im.height + 64 + 22), (24, 26, 30))
    out.paste(im, (0, 0))
    out.paste(cap, (0, im.height))
    ImageDraw.Draw(out).text((8, im.height + 64), info, fill=(170, 190, 210), font=font(14))
    return out, m


def main():
    src = sys.argv[1] if len(sys.argv) > 1 else '/tmp/lb/a6board'
    os.makedirs(os.path.join(OUT, 'frames'), exist_ok=True)
    tiles, meta = [], {}
    for cam, t, cap in MAIN + EXTRA:
        tl, m = tile(src, cam, t, cap)
        tiles.append(tl)
        meta[f'{cam}_{t:.1f}'] = m
        shutil.copy(os.path.join(src, f'{cam}_t{t:.1f}.png'), os.path.join(OUT, 'frames', f'{cam}_t{t:.1f}.png'))
    W, H = tiles[0].size
    head = 56
    board = Image.new('RGB', (W * 3, head + H * 3), (16, 18, 22))
    ImageDraw.Draw(board).text((12, 10), '第 6 幕云海重做（D-44 #2）设计板：体积云，主座位 (0.55, 1.70, 2.05) 看出去。上两行 = 六个时刻（正前），'
                               '第三行 = 补充机位。numpy 参考渲染，不是 Unity。', fill=(240, 240, 240), font=font(19))
    for i, tl in enumerate(tiles):
        board.paste(tl, ((i % 3) * W, head + (i // 3) * H))
    board.save(os.path.join(OUT, 'board.png'))
    json.dump(meta, open(os.path.join(OUT, 'board.json'), 'w'), indent=1, ensure_ascii=False)
    print('ok', board.size)


if __name__ == '__main__':
    main()
