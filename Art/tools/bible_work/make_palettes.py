# -*- coding: utf-8 -*-
import os
from PIL import Image, ImageDraw, ImageFont
from scene_data import SCENES
OUT = '../palettes'; os.makedirs(OUT, exist_ok=True)
CJK = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'
MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BG = (12, 14, 19); INK = (232, 241, 245); MUTED = (128, 146, 164); FAINT = (70, 80, 94)
def F(p, s): return ImageFont.truetype(p, s)
def rgb(h): h = h.lstrip('#'); return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))
def lum(c): return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]
def wrap(d, text, font, width):
    lines, cur = [], ''
    for ch in text:
        if d.textlength(cur + ch, font=font) > width and cur:
            lines.append(cur); cur = ch
        else:
            cur += ch
    if cur: lines.append(cur)
    return lines
def wrap_words(d, text, font, width):
    lines, cur = [], ''
    for w in text.split(' '):
        t = (cur + ' ' + w).strip()
        if d.textlength(t, font=font) > width and cur:
            lines.append(cur); cur = w
        else:
            cur = t
    if cur: lines.append(cur)
    return lines

def palette_png(s, path, W=1800, H=1000):
    im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
    m = 80
    d.text((m, 62), '%s  %s' % (s['id'], s['zh']), font=F(CJK, 58), fill=INK)
    tw = d.textlength('%s  %s' % (s['id'], s['zh']), font=F(CJK, 58))
    d.text((m + tw + 26, 84), s['en'], font=F(SANS, 30), fill=MUTED)
    d.text((m, 142), s['sub'], font=F(CJK, 26), fill=MUTED)
    tag = 'grade %s   ·   蓝白 / Lanbai 色板 v2 (display targets, 屏幕目标值)' % s['grade']
    d.text((W - m - d.textlength(tag, font=F(CJK, 20)), 92), tag, font=F(CJK, 20), fill=FAINT)
    n = len(s['pal']); gap = 16
    cw = (W - 2 * m - gap * (n - 1)) / n
    top, ch = 214, 500
    for i, (hx, zh, en) in enumerate(s['pal']):
        x0 = m + i * (cw + gap); x1 = x0 + cw
        c = rgb(hx)
        d.rounded_rectangle([x0, top, x1, top + ch], radius=12, fill=c, outline=(44, 52, 64) if lum(c) < 40 else None, width=2)
        d.text((x0 + 2, top + ch + 22), hx.upper(), font=F(MONO, 26), fill=INK)
        y = top + ch + 64
        for ln in wrap(d, zh, F(CJK, 23), cw - 4)[:3]:
            d.text((x0 + 2, y), ln, font=F(CJK, 23), fill=INK); y += 32
        y += 4
        for ln in wrap_words(d, en, F(SANS, 17), cw - 4)[:2]:
            d.text((x0 + 2, y), ln, font=F(SANS, 17), fill=MUTED); y += 24
    # continuous strip
    sy = H - 44
    for i, (hx, _, _) in enumerate(s['pal']):
        x0 = m + i * (W - 2 * m) / n
        d.rectangle([x0, sy, x0 + (W - 2 * m) / n + 1, sy + 14], fill=rgb(hx))
    im.save(path)

paths = []
for s in SCENES:
    p = '%s/Palette_%s_%s.png' % (OUT, s['id'], s['en'].lower().replace(' ', '_').replace(',', ''))
    palette_png(s, p); paths.append(p)
# overview sheet
W, rowh, m = 1800, 118, 60
H = 150 + rowh * len(SCENES) + 40
im = Image.new('RGB', (W, H), BG); d = ImageDraw.Draw(im)
d.text((m, 44), '蓝白 / Lanbai · 全片色板 v2（12 幕 + 门内 + 蓝时 + 星海；紫只在第 4 幕）', font=F(CJK, 40), fill=INK)
for r, s in enumerate(SCENES):
    y = 150 + r * rowh
    d.text((m, y + 26), s['id'], font=F(MONO, 26), fill=MUTED)
    d.text((m + 80, y + 22), s['zh'], font=F(CJK, 30), fill=INK)
    x = m + 330; n = len(s['pal']); cw = (W - x - m) / 10
    for i, (hx, zh, en) in enumerate(s['pal']):
        c = rgb(hx)
        d.rounded_rectangle([x + i * cw, y, x + (i + 1) * cw - 8, y + rowh - 26], radius=8, fill=c,
                            outline=(44, 52, 64) if lum(c) < 40 else None, width=2)
        d.text((x + i * cw + 8, y + rowh - 50), hx.upper(), font=F(MONO, 15), fill=(16, 18, 24) if lum(c) > 118 else (214, 222, 230))
im.save('%s/Palette_00_overview.png' % OUT)
print('\n'.join(paths))
