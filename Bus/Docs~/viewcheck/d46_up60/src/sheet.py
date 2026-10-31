# contact sheet of the up60 renders: row 1 before D-46, row 2 D-46, columns by t; labels with t, fade and the
# snell_check numbers (Bus/Docs~/viewcheck/snell_hero_before_d46.json / snell_hero.json); the 20-deg zenith circle as a
# thin outline (projected through the camera in render_up60.py -> up60_circle.json). Also image statistics -> up60_stats.json
#   ~/bpy/bin/python sheet.py
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = '/tmp/bus/d46'
REPO = '/home/user/lanbai-assets'
TIMES = [380, 387, 446, 506]
FONT = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
FONTB = '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'
CIRCLE = (255, 160, 30)


def snell(path):
    d = json.load(open(os.path.join(REPO, 'Bus', 'Docs~', 'viewcheck', path), encoding='utf-8'))
    return {round(r['t']): r for r in d['rows']}


def circle_mask(pts, W, H):
    """pixels inside the projected 20-deg circle (polygon of the in-front points, clipped by the frame)."""
    m = Image.new('L', (W, H), 0)
    poly = [p for p in pts if p is not None]
    ImageDraw.Draw(m).polygon(poly, fill=255)
    return np.array(m) > 0


def main():
    before, after = snell('snell_hero_before_d46.json'), snell('snell_hero.json')
    circ = json.load(open(os.path.join(OUT, 'up60_circle.json')))
    W, H = circ['res']
    pts = [tuple(p) if p is not None else None for p in circ['circle20_px']]
    cmask = circle_mask(pts, W, H)
    # image statistics: sky pixels (the Snell window's bright sky seen through glass or a hole), whole frame and inside
    # the in-frame part of the 20-deg circle. NOT the snell_check metric (that one is the whole cone, solid-angle weighted).
    stats = []
    tiles = {}
    for zen, tag in ((0, 'before'), (1, 'd46')):
        for t in TIMES:
            p = os.path.join(OUT, 'up60_%d_%s.png' % (t, tag))
            im = Image.open(p).convert('RGB')
            a = np.asarray(im).astype(int)
            sky = a.min(-1) >= 215
            stats.append(dict(t=t, zen_on=zen, png=p, sky_frame_pct=round(100 * float(sky.mean()), 2),
                              sky_in_circle20_pct=round(100 * float(sky[cmask].mean()), 2),
                              circle20_in_frame_px=int(cmask.sum())))
            tiles[(zen, t)] = im
    json.dump(dict(_about='image statistics of the up60 renders: sky = min(R, G, B) >= 215 (8-bit sRGB); circle20 = the '
                          'part of the 20-deg zenith circle inside the frame (the zenith itself is just above the top edge). '
                          'Not the snell_check metric.', rows=stats), open(os.path.join(OUT, 'up60_stats.json'), 'w'), indent=1)

    pad, head, rowhead = 14, 70, 44
    lab = 58
    SW = pad + len(TIMES) * (W + pad)
    SH = head + 2 * (rowhead + lab + H + pad)
    sh = Image.new('RGB', (SW, SH), (24, 26, 30))
    d = ImageDraw.Draw(sh)
    fT, fB, f, fs = ImageFont.truetype(FONTB, 30), ImageFont.truetype(FONTB, 24), ImageFont.truetype(FONT, 22), \
        ImageFont.truetype(FONT, 17)
    d.text((pad, 14), 'D-46  hero_up60 (eye 0.55 / 1.70 / 2.05, pitch +60, hfov 90)  -  erosion = erode.osl (Cycles OSL port of '
           'LanbaiCabinErodeField), glass clear, Snell window world', font=fT, fill=(235, 235, 235))
    rows = [(0, 'before D-46  (zen_on 0)   snell numbers: Bus/Docs~/viewcheck/snell_hero_before_d46.json', before),
            (1, 'D-46  (zen_on 1, LanbaiZenithTerm)   snell numbers: Bus/Docs~/viewcheck/snell_hero.json', after)]
    sstat = {(r['zen_on'], r['t']): r for r in stats}
    for ri, (zen, title, sn) in enumerate(rows):
        y0 = head + ri * (rowhead + lab + H + pad)
        d.text((pad, y0 + 8), title, font=fB, fill=(255, 210, 120) if zen else (190, 205, 225))
        for ci, t in enumerate(TIMES):
            x0 = pad + ci * (W + pad)
            r = sn[t]
            l1 = 't %d s   fade %.4f' % (t, r['fade'])
            l2 = 'Snell cone visible %.1f %%   zenith 20° visible %.1f %%' % (100 * r['snell_cone']['visible'],
                                                                        100 * r['zenith_20deg']['visible'])
            d.text((x0, y0 + rowhead), l1, font=f, fill=(235, 235, 235))
            d.text((x0, y0 + rowhead + 28), l2, font=f, fill=(235, 235, 235))
            ty = y0 + rowhead + lab
            tile = tiles[(zen, t)].copy()
            td = ImageDraw.Draw(tile)
            seg = []
            for p in pts + [None]:
                if p is None:
                    if len(seg) > 1:
                        td.line(seg, fill=CIRCLE, width=2)
                    seg = []
                else:
                    seg.append(p)
            st = sstat[(zen, t)]
            td.text((8, H - 26), 'frame: sky %.1f %% of pixels, inside the 20° circle %.1f %%'
                    % (st['sky_frame_pct'], st['sky_in_circle20_pct']), font=fs, fill=(255, 255, 255),
                    stroke_width=2, stroke_fill=(0, 0, 0))
            sh.paste(tile, (x0, ty))
    # circle legend on the first tile
    zx, zy = circ['zenith_px']
    vh = math.degrees(math.atan(math.tan(math.radians(circ['camera']['hfov_deg'] / 2)) * H / W))
    note = '— 20° round the zenith (the zenith is %.1f° above the top edge, 30° above the centre)' % (30.0 - vh)
    d.text((SW - pad - d.textlength(note, font=fs), 22 + 30), note, font=fs, fill=CIRCLE)
    p = os.path.join(OUT, 'up60_sheet.png')
    sh.save(p, optimize=True)
    print('sheet ->', p, sh.size)
    for s in stats:
        print(s)


if __name__ == '__main__':
    main()
