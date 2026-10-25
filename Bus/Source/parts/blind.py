# -*- coding: utf-8 -*-
"""盲测图（D-40 #5 + D-40a #2）：真车照片的局部和我们的渲染局部混在一起、去掉标签，出一组手机竖屏能看的图，
让人（小楠，以后加志愿者）挑哪张是 CG。**它是找问题的工具，不是合格线**（D-40a #2）：挑出来的地方进下一轮的
修改清单，不判“过”或“不过”。

    python3 Bus/Source/parts/blind.py --set <名字> --photos a.jpg@0.6,0.45,0.9,b.jpg --renders r.png@0.5,0.5,1 [--seed 7]
    python3 Bus/Source/parts/blind.py --demo            # 用仓库里现成的文件出一组示例（Bus/Docs~/盲测/示例_车厢局部）

每个输入是 “路径” 或 “路径@cx,cy,h”：以 (cx, cy)（0–1，从左上算）为中心、高为图高 h 倍的 9:16 竖条裁下来
（碰到边就往里挪）；不写就是正中间、整个图高。
所有的图同一种处理，不让处理方式露馅：
  - 裁成 9:16，先缩到同一个工作尺寸（默认 540 × 960，LANCZOS），再放到 1080 × 1920（BICUBIC）：照片和渲染的
    清晰度拉到一个水平（渲染本来就比照片锐，这一点不该是认出 CG 的理由）；
  - 只要有一张照片是黑白的，就全部转灰（--gray auto；on / off 可以强制）；
  - 统一存 JPEG（质量 85、不带 EXIF、不带任何文字），文件名只是 01.jpg、02.jpg……，顺序按 --seed 洗过。
出 Bus/Docs~/盲测/<set>/NN.jpg；答案另存一个文件 Bus/Docs~/盲测/<set>/答案.json（每张是照片还是渲染、出处、裁的
位置、照片的作者和授权）。看图的人先别开答案。照片的署名从照片旁边往上找 sources.json（和 compare.py 一样）。
进仓库的照片只用 CC0 / 公有领域 / CC BY / CC BY-SA（D-41 #7）；ref_only/ 里的不拿来做盲测图。
只用 PIL，系统的 python3 就能跑。
"""
import argparse
import datetime
import json
import os
import random
import re

from PIL import Image, ImageChops, ImageOps, ImageStat

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
DOCS = os.path.join(ROOT, 'Bus', 'Docs~')
OUT_W, OUT_H = 1080, 1920

DEMO = dict(
    set='示例_车厢局部',
    photos=['实物参考_PAZ细节/flickr/F01_座椅背面_靠背顶整条软套_白背板_铆钉_31583330165.jpg@0.62,0.45,0.9',
            '实物参考_PAZ细节/flickr/F04_后轮罩_双人座侧面弯管框_单座_立柱横杆_31211178060.jpg@0.62,0.55,0.6',
            '实物参考_PAZ细节/flickr/F05_前门内侧_两扇折门_门口立柱_弯扶手_铭牌_31583333525.jpg@0.5,0.5,0.7',
            '实物参考_PAZ细节/flickr/F09_斜面窗内侧_拱形窗柱_衣钩_铝压条_31583316685.jpg@0.5,0.5,0.9'],
    renders=['parts/poles/r1_button_0.6m_day.png@0.5,0.5,1',
             'parts/window/r1_latch_0.4m_day.png@0.62,0.5,1',
             'parts/seat/r4_back_0.7m_day.png@0.22,0.5,1',
             'parts/window/r1_corner_0.5m_day.png@0.5,0.5,1'],
    seed=20261025,
    note='示例：仓库里现成的文件（renders = Bus/Docs~/parts/*/ 里 10-24 的近景渲染，白天光；photos = trolleway 那辆车，'
         '多半是 672、座椅重包过红色，颜色和 672M 不一样）。颜色本身就会露馅，这一组只是演示工具怎么用，不拿来下结论。',
)


def parse_item(s, base):
    """'path' or 'path@cx,cy,h' -> (abs path, (cx, cy, h))."""
    path, crop = (s.split('@', 1) + [''])[:2] if '@' in s else (s, '')
    p = path if os.path.isabs(path) or os.path.exists(path) else os.path.join(base, path)
    if not os.path.exists(p):
        raise SystemExit('[blind] missing file: %s' % path)
    c = (0.5, 0.5, 1.0)
    if crop:
        v = [float(x) for x in crop.split(',')]
        if len(v) != 3:
            raise SystemExit('[blind] crop must be cx,cy,h (got %s)' % crop)
        c = tuple(v)
    return os.path.abspath(p), c


def crop_box(W, H, cx, cy, h):
    """a 9:16 box centred at (cx, cy) (fractions), h x image height tall, pushed inside the image."""
    ch = min(H, max(16, round(h * H)))
    cw = round(ch * OUT_W / OUT_H)
    if cw > W:                                   # very narrow image: limit by the width instead
        cw = W
        ch = round(cw * OUT_H / OUT_W)
    x0 = min(max(0, round(cx * W - cw / 2)), W - cw)
    y0 = min(max(0, round(cy * H - ch / 2)), H - ch)
    return x0, y0, x0 + cw, y0 + ch


def is_bw(im, tol=3.0):
    """a photo is black-and-white when its channels hardly differ (mean |R-G| + |G-B| < tol on 0-255)."""
    r, g, b = im.convert('RGB').resize((128, 128)).split()
    d = ImageStat.Stat(ImageChops.difference(r, g)).mean[0] + ImageStat.Stat(ImageChops.difference(g, b)).mean[0]
    return d < tol


def credit(photo):
    """author / licence / page for a photo from the nearest sources.json above it (as compare.py does)."""
    d = os.path.dirname(photo)
    while True:
        sj = os.path.join(d, 'sources.json')
        if os.path.exists(sj):
            try:
                items = json.load(open(sj, encoding='utf-8'))
            except Exception:
                items = []
            if isinstance(items, dict):
                items = items.get('files', items.get('sources', []))
            rel = os.path.relpath(photo, d).replace(os.sep, '/')
            for e in items if isinstance(items, list) else []:
                f = str(e.get('file', '')).replace('\\', '/')
                if f == rel or os.path.basename(f) == os.path.basename(photo):
                    return dict(author=e.get('author', ''), license=e.get('license', ''), page=e.get('page', ''),
                                title=e.get('title', e.get('commons_title', '')))
        if os.path.abspath(d) == ROOT or os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


def main(argv=None):
    ap = argparse.ArgumentParser(description='D-40 #5 / D-40a #2 blind-test set (a problem-finding tool, not a pass line)')
    ap.add_argument('--set', default='')
    ap.add_argument('--photos', default='', help='comma list of path[@cx,cy,h] (relative to Bus/Docs~ or cwd)')
    ap.add_argument('--renders', default='', help='comma list of path[@cx,cy,h]')
    ap.add_argument('--seed', type=int, default=1)
    ap.add_argument('--gray', default='auto', choices=['auto', 'on', 'off'])
    ap.add_argument('--work', default='540x960', help='common working size before the 1080x1920 output')
    ap.add_argument('--quality', type=int, default=85)
    ap.add_argument('--out', default=os.path.join(DOCS, '盲测'))
    ap.add_argument('--demo', action='store_true', help='the demo set from files already in the repo')
    a = ap.parse_args(argv)
    note = ''
    if a.demo:
        a.set, a.seed, note = DEMO['set'], DEMO['seed'], DEMO['note']
        photos = [parse_item(s, DOCS) for s in DEMO['photos']]
        renders = [parse_item(s, DOCS) for s in DEMO['renders']]
    else:
        if not a.set:
            raise SystemExit('[blind] --set <name> (or --demo)')
        # items are 'path' or 'path@cx,cy,h': split on the commas that start a new path, not inside a crop
        photos = [parse_item(s, DOCS) for s in re.split(r',(?=[^\d.\-])', a.photos) if s.strip()]
        renders = [parse_item(s, DOCS) for s in re.split(r',(?=[^\d.\-])', a.renders) if s.strip()]
    if not photos or not renders:
        raise SystemExit('[blind] need at least one photo and one render')
    for p, _ in photos:
        if '/ref_only/' in p.replace(os.sep, '/'):
            raise SystemExit('[blind] %s is ref_only (not for reuse, D-41 #7)' % p)
    ww, wh = (int(v) for v in a.work.lower().split('x'))
    items = [('photo', p, c) for p, c in photos] + [('render', p, c) for p, c in renders]
    bw = [os.path.basename(p) for k, p, _ in items if k == 'photo' and is_bw(Image.open(p))]
    gray = a.gray == 'on' or (a.gray == 'auto' and bool(bw))
    rng = random.Random(a.seed)
    order = list(range(len(items)))
    rng.shuffle(order)
    out = os.path.join(a.out, a.set)
    os.makedirs(out, exist_ok=True)
    for f in os.listdir(out):                    # a re-run replaces the set (only our own NN.jpg files)
        if f.endswith('.jpg') and f[:-4].isdigit():
            os.remove(os.path.join(out, f))
    answers, credits = [], []
    for n, k in enumerate(order, 1):
        kind, path, (cx, cy, h) = items[k]
        im = ImageOps.exif_transpose(Image.open(path)).convert('RGB')
        box = crop_box(im.width, im.height, cx, cy, h)
        c = im.crop(box).resize((ww, wh), Image.LANCZOS).resize((OUT_W, OUT_H), Image.BICUBIC)
        if gray:
            c = ImageOps.grayscale(c).convert('RGB')
        name = '%02d.jpg' % n
        c.save(os.path.join(out, name), 'JPEG', quality=a.quality, optimize=True)
        rec = dict(file=name, kind=kind, kind_zh='照片' if kind == 'photo' else '渲染（CG）',
                   source=os.path.relpath(path, ROOT).replace(os.sep, '/'), crop_px=list(box),
                   crop_spec=dict(cx=cx, cy=cy, h=h))
        if kind == 'photo':
            cr = credit(path)
            rec['credit'] = cr or '没找到 sources.json（要补）'
            if cr and cr not in credits:
                credits.append(cr)
        answers.append(rec)
    js = os.path.join(out, '答案.json')
    json.dump(dict(
        set=a.set, made=datetime.date.today().isoformat(), seed=a.seed, count=len(items),
        photos=sum(1 for i in items if i[0] == 'photo'), renders=sum(1 for i in items if i[0] == 'render'),
        treatment=dict(crop='9:16 around (cx, cy), h x image height', work_size=[ww, wh], output=[OUT_W, OUT_H],
                       resample='LANCZOS down to the work size, BICUBIC up to the output', grayscale=gray,
                       grayscale_why=('B&W photos: ' + ', '.join(bw)) if bw else a.gray,
                       jpeg_quality=a.quality, labels=False, exif=False),
        rule='盲测是找问题的工具，不是合格线（D-40a #2）：挑出来的地方进下一轮的修改清单，不判过不过。照片和渲染尽量对齐机位和光照。',
        answers=answers,
        credits=[dict(c, changes='裁成 9:16 竖条、缩放%s、存 JPEG' % ('、转灰' if gray else '')) for c in credits],
        note=note), open(js, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[blind] %s: %d images (%d photos, %d renders), seed %d, gray %s -> %s' % (
        a.set, len(items), len(photos), len(renders), a.seed, gray, out))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
