# -*- coding: utf-8 -*-
"""对照板 v2（D-40 #1 五栏、D-40a #4 三层状态、D-40a #6 / D-40b #2 细节看不看得出）：写 Bus/Docs~/detail/<part>/compare.png。

    python3 Bus/Source/parts/compare.py --part poles \
        --photos p1.jpg,p2.jpg \
        --neutral /tmp/bus/parts/poles_aisle_2m_neutral.png,... \
        --final /tmp/bus/parts/poles_aisle_2m_day.png,... \
        [--unity shot1.png,,shot3.png] [--headset note1.txt,,] \
        [--status blender=通过,unity=未测,vr=未测] [--details Bus/Docs~/detail/poles/details.json] \
        [--title "..."] [--out compare.png]

旧的用法照样能跑（--part --renders --photos --title）：--renders 进“Blender 定稿”那一栏。

每一行一个机位，五栏固定（D-40 #1）：真车照片 / Blender 中性光 / Blender 定稿 / Unity 截图 / 头显一句话。
各栏的文件按行对齐：逗号分开，第 i 个进第 i 行，空着（两个逗号之间什么都不写）就是那一行没有。
  - Unity 截图、头显一句话：没给文件就是一个写着“未测”的空框（后两栏空着 = 没验过，不是过了）。
    头显一句话可以是 .txt / .md（里面那一句话印在框里）或者一张图。
  - 每张照片下面一行署名（作者、授权），从照片所在文件夹往上找 sources.json（Bus/Docs~ 的参考板都有）；
    找不到就写“署名：没找到 sources.json”，要补。
三层状态表（D-40a #4）：Blender 离线 / Unity 桌面 / VR 头显，每层取 未测 / 通过 / 不通过 / 测不了。
  - 默认全是“未测”；Unity 桌面没给 --unity 文件、VR 头显没给 --headset 文件时，写了“通过”也记成“未测”
    （板上注明）。D-41 #4：Unity 层的“通过”要总导演看过图才记。
细节表（D-40a #6、D-40b #2）：读 details.json（默认 Bus/Docs~/detail/<part>/details.json），每处细节按
    角像素 = 尺寸 / 距离（弧度）× 180/π × ppd，在 20 px/° 和 14 px/° 下各算一次，≥ 2 px 记“看得出”。
    距离给的是一个范围时，近端、远端都算：两端都 ≥ 2 px“看得出”，只有近端够“近看得出”，都不够“看不出”。
    判定按 20 px/°（D-40a #6）；14 px/° 一栏只作参考，不判过不过（D-40b #2）。
字体 Fonts/Originals~/SourceHanSerifCN-Medium.otf。只用 PIL，系统的 python3 就能跑。
"""
import argparse
import json
import math
import os

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
DOCS = os.path.join(ROOT, 'Bus', 'Docs~')
FONT = os.path.join(ROOT, 'Fonts', 'Originals~', 'SourceHanSerifCN-Medium.otf')

COLS = ['真车照片', 'Blender 中性光', 'Blender 定稿', 'Unity 截图', '头显一句话']
LAYERS = [('blender', 'Blender 离线'), ('unity', 'Unity 桌面'), ('vr', 'VR 头显')]
STATES = ['未测', '通过', '不通过', '测不了']
KEY_ALIAS = {'blender': 'blender', 'blender离线': 'blender', 'unity': 'unity', 'unity桌面': 'unity', 'desktop': 'unity',
             'vr': 'vr', 'headset': 'vr', 'vr头显': 'vr', '头显': 'vr'}
PPD_JUDGE, PPD_PANEL, MIN_PX = 20.0, 14.0, 2.0

BG, PANEL, INK, DIM, LINE = (14, 14, 16), (28, 28, 32), (232, 232, 232), (150, 150, 156), (60, 60, 66)
STATE_COL = {'未测': (110, 110, 116), '通过': (70, 140, 90), '不通过': (170, 70, 60), '测不了': (120, 100, 60)}


def font(size):
    try:
        return ImageFont.truetype(FONT, size)
    except Exception:
        try:
            return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)
        except Exception:
            return ImageFont.load_default()


def split_list(s):
    """'a,,c' -> ['a', '', 'c'] (positions matter: one per row); trailing empties dropped."""
    if not s:
        return []
    out = [p.strip() for p in s.split(',')]
    while out and not out[-1]:
        out.pop()
    return out


# ------------------------------------------------------------------------------------------------ credits
def credit(photo):
    """'author · licence' for a photo from the nearest sources.json above it (entries keyed by 'file', a path
    relative to that sources.json, or by its basename); None when there is none."""
    p = os.path.abspath(photo)
    d = os.path.dirname(p)
    stop = os.path.abspath(ROOT)
    while True:
        sj = os.path.join(d, 'sources.json')
        if os.path.exists(sj):
            try:
                data = json.load(open(sj, encoding='utf-8'))
            except Exception:
                data = []
            items = data if isinstance(data, list) else data.get('files', data.get('sources', []))
            if isinstance(items, dict):
                items = [dict(v, file=k) for k, v in items.items()]
            rel = os.path.relpath(p, d).replace(os.sep, '/')
            for e in items:
                f = str(e.get('file', '')).replace('\\', '/')
                if f == rel or os.path.basename(f) == os.path.basename(p):
                    who = e.get('author') or e.get('credit') or '作者不详'
                    lic = e.get('license') or e.get('licence') or '授权不详'
                    return '%s · %s' % (who, lic), e.get('page', '')
        if d == stop or os.path.dirname(d) == d:
            return None
        d = os.path.dirname(d)


# ------------------------------------------------------------------------------------------------ details
def angular_px(size_mm, dist_m, ppd):
    """angular size in pixels: size / distance (rad) x 180/pi x ppd (small angle)."""
    return (size_mm / 1000.0) / dist_m * 180.0 / math.pi * ppd


def visibility(size_mm, dist, ppd):
    """dist: a number or [near, far] (m) -> (label, px_near, px_far)."""
    near, far = (dist, dist) if isinstance(dist, (int, float)) else (min(dist), max(dist))
    pn, pf = angular_px(size_mm, near, ppd), angular_px(size_mm, far, ppd)
    if pf >= MIN_PX:
        return '看得出', pn, pf
    if pn >= MIN_PX:
        return '近看得出', pn, pf
    return '看不出', pn, pf


def detail_rows(path):
    d = json.load(open(path, encoding='utf-8'))
    rows = []
    for e in d.get('details', []):
        size = float(e['size_mm'])
        dist = e['distance_m']
        v20 = visibility(size, dist, PPD_JUDGE)
        v14 = visibility(size, dist, PPD_PANEL)
        rows.append(dict(name=e.get('name', e.get('id', '?')), size=size, what=e.get('size_of', ''), dist=dist,
                         v20=v20, v14=v14))
    return d, rows


# ------------------------------------------------------------------------------------------------ status
def parse_status(s, have_unity, have_vr):
    st = {k: '未测' for k, _ in LAYERS}
    notes = []
    for part in [p for p in (s or '').split(',') if p.strip()]:
        if '=' not in part:
            raise SystemExit('--status: write layer=state, e.g. blender=通过,unity=未测,vr=未测 (got %r)' % part)
        k, v = (x.strip() for x in part.split('=', 1))
        key = KEY_ALIAS.get(k.lower().replace(' ', ''))
        if key is None:
            raise SystemExit('--status: unknown layer %r (blender / unity / vr)' % k)
        if v not in STATES:
            raise SystemExit('--status: %s must be one of %s (got %r)' % (k, ' / '.join(STATES), v))
        st[key] = v
    if st['unity'] == '通过' and not have_unity:
        st['unity'] = '未测'
        notes.append('Unity 桌面写了“通过”，但没给 Unity 截图：记成“未测”。')
    if st['vr'] == '通过' and not have_vr:
        st['vr'] = '未测'
        notes.append('VR 头显写了“通过”，但没给头显那一句：记成“未测”。')
    return st, notes


# ------------------------------------------------------------------------------------------------ drawing
def wrap(d, text, f, width):
    """greedy wrap by measured width (CJK has no spaces)."""
    lines, cur = [], ''
    for ch in text:
        if ch == '\n':
            lines.append(cur)
            cur = ''
            continue
        if d.textlength(cur + ch, font=f) > width and cur:
            lines.append(cur)
            cur = ch
        else:
            cur += ch
    if cur:
        lines.append(cur)
    return lines


def put_image(sheet, path, x, y, w, h):
    im = Image.open(path).convert('RGB')
    im.thumbnail((w, h))
    sheet.paste(im, (x + (w - im.width) // 2, y + (h - im.height) // 2))


def empty_box(d, x, y, w, h, text, f, col=DIM):
    d.rectangle((x + 6, y + 6, x + w - 6, y + h - 6), outline=LINE, width=2)
    tw = d.textlength(text, font=f)
    d.text((x + (w - tw) / 2, y + h / 2 - f.size * 0.6), text, fill=col, font=f)


def main(argv=None):
    ap = argparse.ArgumentParser(description='D-40 #1 five-column compare board (v2)')
    ap.add_argument('--part', required=True)
    ap.add_argument('--photos', default='', help='真车照片, one per row')
    ap.add_argument('--renders', default='', help='old CLI: = --final')
    ap.add_argument('--neutral', default='', help='Blender 中性光 (qa.py --mode neutral), one per row')
    ap.add_argument('--final', default='', help='Blender 定稿 (preview.py), one per row')
    ap.add_argument('--unity', default='', help='Unity 截图, one per row; empty = 未测')
    ap.add_argument('--headset', default='', help='头显一句话: .txt/.md or an image, one per row; empty = 未测')
    ap.add_argument('--status', default='', help='blender=..,unity=..,vr=.. with 未测 / 通过 / 不通过 / 测不了')
    ap.add_argument('--details', default='', help='details.json (default Bus/Docs~/detail/<part>/details.json if there)')
    ap.add_argument('--no-details', action='store_true')
    ap.add_argument('--title', default='')
    ap.add_argument('--out', default='', help='default Bus/Docs~/detail/<part>/compare.png')
    a = ap.parse_args(argv)

    photos, neutral = split_list(a.photos), split_list(a.neutral)
    if a.final and a.renders:
        raise SystemExit('[compare] give --final or --renders (the old name of the same column), not both: '
                         'concatenating them would shift every row of the column')
    final = split_list(a.final) or split_list(a.renders)
    unity, headset = split_list(a.unity), split_list(a.headset)
    for lst in (photos, neutral, final, unity, headset):
        for p in lst:
            if p and not os.path.exists(p):
                raise SystemExit('[compare] missing file: %s' % p)
    cols = [photos, neutral, final, unity, headset]
    nrows = max([len(c) for c in cols] + [1])
    status, notes = parse_status(a.status, any(unity), any(headset))
    det_path = a.details or os.path.join(DOCS, 'detail', a.part, 'details.json')
    det = None
    if not a.no_details and os.path.exists(det_path):
        det = detail_rows(det_path)

    # ---- layout
    CW, CH, PAD = 480, 270, 10
    LBL, CRED = 30, 40                 # per row: a label strip above, a credit strip under the cells
    ft, fh, fb, fs = font(26), font(19), font(16), font(13)
    W = PAD * 2 + CW * 5
    title_h = 50
    status_h = 40 + 32 * 2 + (22 * len(notes)) + 30
    rows_h = 36 + nrows * (LBL + CH + CRED)
    det_h = 0
    if det:
        det_h = 80 + 26 * (len(det[1]) + 1) + 40
    H = title_h + status_h + rows_h + det_h + PAD * 2
    sheet = Image.new('RGB', (W, H), BG)
    d = ImageDraw.Draw(sheet)
    y = PAD
    d.text((PAD + 4, y), a.title or ('%s · 对照板（D-40 #1 五栏）' % a.part), fill=INK, font=ft)
    y += title_h

    # ---- three-layer status (D-40a #4)
    d.text((PAD + 4, y), '三层验收（D-40a #4，各记各的；一层通过不代表别的层通过；没在头显里看过的不写“已通过”）',
           fill=INK, font=fh)
    y += 34
    cw = 300
    for k, (key, name) in enumerate(LAYERS):
        x = PAD + 4 + k * (cw + 12)
        d.rectangle((x, y, x + cw, y + 56), fill=PANEL, outline=LINE)
        d.text((x + 10, y + 4), name, fill=DIM, font=fb)
        d.rectangle((x + 10, y + 26, x + 120, y + 50), fill=STATE_COL[status[key]])
        d.text((x + 18, y + 26), status[key], fill=(245, 245, 245), font=fh)
    d.text((PAD + 4 + 3 * (cw + 12), y + 4), '取值：未测 / 通过 / 不通过 / 测不了。Unity 桌面、VR 头显默认“未测”，',
           fill=DIM, font=fs)
    d.text((PAD + 4 + 3 * (cw + 12), y + 22), '没有截图 / 头显那一句就不记“通过”；Unity 的“通过”要总导演看过图（D-41 #4）。',
           fill=DIM, font=fs)
    y += 64
    for n_ in notes:
        d.text((PAD + 4, y), '注：' + n_, fill=(220, 160, 120), font=fs)
        y += 22
    y += 24

    # ---- the five columns
    for c, name in enumerate(COLS):
        x = PAD + c * CW
        d.rectangle((x, y, x + CW - 2, y + 30), fill=PANEL)
        d.text((x + 10, y + 3), name, fill=INK, font=fh)
    y += 36
    for r in range(nrows):
        get = [col[r] if r < len(col) else '' for col in cols]
        label = next((os.path.splitext(os.path.basename(p))[0] for p in (get[2], get[1]) if p), '')
        d.text((PAD + 4, y + 4), '第 %d 行%s' % (r + 1, ' · ' + label if label else ''), fill=DIM, font=fb)
        yc = y + LBL
        for c, p in enumerate(get):
            x = PAD + c * CW
            d.rectangle((x, yc, x + CW - 2, yc + CH), fill=PANEL)
            if c >= 3:
                if not p:
                    empty_box(d, x, yc, CW - 2, CH, '未测', ft)
                elif os.path.splitext(p)[1].lower() in ('.txt', '.md'):
                    txt = open(p, encoding='utf-8').read().strip()
                    for k, ln in enumerate(wrap(d, txt, fh, CW - 40)[:9]):
                        d.text((x + 18, yc + 16 + k * 26), ln, fill=INK, font=fh)
                else:
                    put_image(sheet, p, x, yc, CW - 2, CH)
            else:
                if p:
                    put_image(sheet, p, x, yc, CW - 2, CH)
                else:
                    empty_box(d, x, yc, CW - 2, CH, ('没有照片', '没有中性光图', '没有定稿图')[c], fh)
            # the line under the cell: photo credit / file name
            if p:
                if c == 0:
                    cr = credit(p)
                    line = ('照片：%s' % cr[0]) if cr else '署名：没找到 sources.json（要补）'
                    col_ = INK if cr else (220, 160, 120)
                else:
                    line, col_ = os.path.basename(p), DIM
                for k, ln in enumerate(wrap(d, line, fs, CW - 16)[:2]):
                    d.text((x + 6, yc + CH + 3 + k * 17), ln, fill=col_, font=fs)
        y += LBL + CH + CRED

    # ---- details (D-40a #6, D-40b #2)
    if det:
        meta, rows = det
        y += 10
        d.text((PAD + 4, y), '细节在目标视距下看不看得出（%s）' % os.path.relpath(det_path, ROOT), fill=INK, font=fh)
        y += 30
        d.text((PAD + 4, y), '角像素 = 尺寸 ÷ 距离（弧度）× 180/π × 像素密度；≥ %g px 记“看得出”。距离是范围时近端、远端都算。'
               '判定按 Index 约 20 px/°（D-40a #6）；14 px/° 那栏是显示面板的密度，只作参考，不判过不过（D-40b #2）。'
               % MIN_PX, fill=DIM, font=fs)
        y += 36
        xs = [PAD + 4, PAD + 640, PAD + 1040, PAD + 1200, PAD + 1640, PAD + 2080]
        heads = ['细节', '尺寸', '视距（m）', '20 px/°（判定）', '14 px/°（只作参考）', '']
        for x_, h_ in zip(xs, heads):
            d.text((x_, y), h_, fill=DIM, font=fb)
        y += 26
        for row in rows:
            dist = row['dist']
            ds = ('%.2f' % dist) if isinstance(dist, (int, float)) else '%.2f–%.2f' % (min(dist), max(dist))
            cells = [row['name'], '%g mm %s' % (row['size'], row['what']), ds]
            for k, (x_, t) in enumerate(zip(xs, cells)):
                lines = wrap(d, t, fb, xs[k + 1] - x_ - 16)
                d.text((x_, y), lines[0] + ('…' if len(lines) > 1 else ''), fill=INK, font=fb)
            for x_, v in ((xs[3], row['v20']), (xs[4], row['v14'])):
                lab, pn, pf = v
                colr = {'看得出': (120, 200, 140), '近看得出': (220, 190, 110), '看不出': (220, 120, 110)}[lab]
                rng = ('%.1f px' % pn) if abs(pn - pf) < 0.05 else ('%.1f–%.1f px' % (pf, pn))
                d.text((x_, y), '%s（%s）' % (lab, rng), fill=colr, font=fb)
            y += 26
    out = a.out or os.path.join(DOCS, 'detail', a.part, 'compare.png')
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sheet = sheet.crop((0, 0, W, min(H, y + PAD * 3)))
    sheet.save(out)
    print('[compare]', out, sheet.size, 'rows %d, status %s%s' % (nrows, status,
                                                               ', details %d' % len(det[1]) if det else ''))
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
