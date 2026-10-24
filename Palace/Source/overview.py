# -*- coding: utf-8 -*-
"""迭代对照总览：Docs~/iterations/NN_*/ 每轮一行，固定几个机位一列，下面一句话（note.txt）。
~/bpy/bin/python overview.py"""
import glob
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
IT = os.path.join(HERE, '..', 'Docs~', 'iterations')
COLS = ['F5p', 'proc_l', 'F6', 'F7', 'F7pb']
FONT = '/home/user/lanbai-assets/Fonts'


def font(px):
    try:
        return ImageFont.truetype('/home/user/lanbai-assets/Fonts/Originals~/SourceHanSerifCN-Regular.otf', px)
    except Exception:
        pass
    for p in glob.glob(FONT + '/**/SourceHanSans*Regular*.otf', recursive=True) + glob.glob(FONT + '/**/*.otf', recursive=True):
        try:
            return ImageFont.truetype(p, px)
        except Exception:
            pass
    return ImageFont.load_default()


def main():
    rows = sorted(d for d in glob.glob(IT + '/[0-9][0-9]_*') if os.path.isdir(d))
    tw, th = 384, 216
    W = 40 + len(COLS) * (tw + 8)
    H = 60 + len(rows) * (th + 52)
    im = Image.new('RGB', (W, H), (14, 16, 20))
    d = ImageDraw.Draw(im)
    f1, f2 = font(22), font(15)
    d.text((20, 16), '河伯宫殿 · 迭代对照（PPv2 S7b 调色后）  列：' + ' / '.join(COLS), font=f1, fill=(230, 236, 240))
    y = 60
    for r in rows:
        x = 20
        for c in COLS:
            p = os.path.join(r, c + '.png')
            if os.path.exists(p):
                im.paste(Image.open(p).convert('RGB').resize((tw, th), Image.LANCZOS), (x, y))
            else:
                d.rectangle([x, y, x + tw, y + th], outline=(60, 60, 60))
            x += tw + 8
        note = open(os.path.join(r, 'note.txt')).read().strip() if os.path.exists(os.path.join(r, 'note.txt')) else ''
        d.text((20, y + th + 6), os.path.basename(r) + '  ' + note[:150], font=f2, fill=(170, 178, 188))
        y += th + 52
    out = os.path.join(HERE, '..', 'Docs~', 'iterations_overview.png')
    im.save(out, optimize=True)
    print('wrote', out, im.size)


if __name__ == '__main__':
    main()
