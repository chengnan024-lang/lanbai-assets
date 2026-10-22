# -*- coding: utf-8 -*-
"""Contact sheets, the iteration overview, the stranger-test thumbnail (PIL only)."""
import hashlib
import json
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

from . import paths


def font(size):
    try:
        return ImageFont.truetype(paths.FONT, size)
    except OSError:
        return ImageFont.load_default()


def _fit(im, w):
    r = w / float(im.width)
    return im.resize((w, max(1, int(round(im.height * r)))), Image.LANCZOS)


def contact_sheet(items, out, cols=3, cell_w=640, title=None, bg=(18, 20, 26)):
    """items: [(png path or PIL image, caption str (may have \\n)), ...] -> one PNG."""
    ims = [(Image.open(p).convert('RGB') if isinstance(p, str) else p.convert('RGB'), cap) for p, cap in items]
    ims = [(_fit(im, cell_w), cap) for im, cap in ims]
    f = font(18)
    cap_h = max([18 + 24 * (cap.count('\n') + 1) for _, cap in ims] + [30])
    cell_h = max(im.height for im, _ in ims) + cap_h
    rows = (len(ims) + cols - 1) // cols
    top = 50 if title else 0
    sheet = Image.new('RGB', (cols * (cell_w + 12) + 12, top + rows * (cell_h + 12) + 12), bg)
    d = ImageDraw.Draw(sheet)
    if title:
        d.text((14, 12), title, fill=(230, 236, 240), font=font(24))
    for i, (im, cap) in enumerate(ims):
        x = 12 + (i % cols) * (cell_w + 12)
        y = top + 12 + (i // cols) * (cell_h + 12)
        sheet.paste(im, (x, y))
        d.multiline_text((x + 2, y + im.height + 6), cap, fill=(210, 216, 222), font=f, spacing=4)
    os.makedirs(os.path.dirname(os.path.abspath(out)), exist_ok=True)
    sheet.save(out)
    return out


def metrics_caption(m, target=None):
    s = 'APL %.1f' % m['APL']
    if target:
        s += '（目标 %.0f · %s）' % (target['APL'], target['phase'])
    s += '  紫 %.2f%%' % m['purple_pct']
    if 'top25_Lstar' in m:
        s += '  上25%% L* %.1f' % m['top25_Lstar']['mean']
    b = m['brightest']
    s += '\n最亮 2000 px：(%d,%d) 团 %d' % (b['centroid'][0], b['centroid'][1], b['clusters_ge5pct'])
    if 'centroid_az_el' in b:
        s += '  方位 %.1f° 仰 %.1f°' % tuple(b['centroid_az_el'])
    if 'palette' in m and 'pixel_to_nearest_dE_median' in m['palette']:
        s += '  色板 ΔE 中位 %.1f' % m['palette']['pixel_to_nearest_dE_median']
    return s


def iteration_overview(iter_dir, out, cols=4, cell_w=480):
    """iter_dir/NN_<slug>/ each holding graded.png, metrics.json (optional) and note.txt (one line).
    Sorted by NN. Caption = NN + note + key numbers; the deliverable 'iteration comparison overview'."""
    rows = []
    for name in sorted(os.listdir(iter_dir)):
        p = os.path.join(iter_dir, name)
        if not os.path.isdir(p):
            continue
        img = None
        for cand in ('graded.png', 'frame.png'):
            if os.path.exists(os.path.join(p, cand)):
                img = os.path.join(p, cand)
                break
        if img is None:
            pngs = sorted(x for x in os.listdir(p) if x.endswith('.png'))
            if not pngs:
                continue
            img = os.path.join(p, pngs[0])
        note = open(os.path.join(p, 'note.txt'), encoding='utf-8').read().strip() if os.path.exists(os.path.join(p, 'note.txt')) else ''
        cap = name + ('  ' + note if note else '')
        mp = os.path.join(p, 'metrics.json')
        if os.path.exists(mp):
            m = json.load(open(mp, encoding='utf-8'))
            cap += '\n' + metrics_caption(m.get('metrics', m), m.get('target'))
        rows.append((img, _wrap(cap, 34)))
    if not rows:
        raise SystemExit('no iterations under %s' % iter_dir)
    return contact_sheet(rows, out, cols=cols, cell_w=cell_w, title='迭代对照 · ' + os.path.basename(os.path.abspath(iter_dir)))


def _wrap(s, n):
    out = []
    for line in s.split('\n'):
        while len(line) > n:
            out.append(line[:n])
            line = line[n:]
        out.append(line)
    return '\n'.join(out)


def stranger_thumb(png, out_dir):
    """640 px wide, no caption, anonymous file name (the name must not leak the intent)."""
    im = _fit(Image.open(png).convert('RGB'), 640)
    h = hashlib.sha1(open(png, 'rb').read()).hexdigest()[:10]
    os.makedirs(out_dir, exist_ok=True)
    out = os.path.join(out_dir, 'img_%s.png' % h)
    im.save(out)
    prompt = ('你会看到一张图（%s）。不要猜它来自什么项目，也不要找任何别的资料。'
              '只用一句话说你看到了什么（是什么东西、在哪里、给人什么感觉）。然后用一句话说你的眼睛最先落在哪里。' % out)
    open(os.path.join(out_dir, 'img_%s.prompt.txt' % h), 'w', encoding='utf-8').write(prompt + '\n')
    return out, prompt


def side_by_side(a_png, b_png, out, labels=('A', 'B'), w=960):
    a = _fit(Image.open(a_png).convert('RGB'), w)
    b = _fit(Image.open(b_png).convert('RGB'), w)
    H = max(a.height, b.height) + 40
    s = Image.new('RGB', (2 * w + 30, H), (18, 20, 26))
    s.paste(a, (10, 36))
    s.paste(b, (w + 20, 36))
    d = ImageDraw.Draw(s)
    d.text((12, 6), labels[0], fill=(230, 236, 240), font=font(22))
    d.text((w + 22, 6), labels[1], fill=(230, 236, 240), font=font(22))
    s.save(out)
    return out


def diff_heat(a_png, b_png, out):
    """|luma(a) - luma(b)| as a heat map (for Unity vs reference)."""
    A = np.asarray(Image.open(a_png).convert('RGB'), float)
    B = np.asarray(Image.open(b_png).convert('RGB').resize((A.shape[1], A.shape[0]), Image.LANCZOS), float)
    d = np.abs(A @ [0.2126, 0.7152, 0.0722] - B @ [0.2126, 0.7152, 0.0722])
    v = np.clip(d / 40.0, 0, 1)
    rgb = np.stack([v, v ** 2, 0.2 * (1 - v)], -1) * 255
    Image.fromarray(rgb.astype(np.uint8)).save(out)
    return dict(mean_abs_luma_diff=round(float(d.mean()), 2), p95=round(float(np.percentile(d, 95)), 2))
