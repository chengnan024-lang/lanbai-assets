# -*- coding: utf-8 -*-
"""Visual proof for the engine re-solve: the art pipeline's own preview test frames (art/bible_work/make_previews.SOURCES,
scene-linear) rendered three ways, bloom included (bloom happens before the grade and is unchanged):
    LOOK     = art simulator + grades_final.json            (what the bible's previews/ show = the target)
    BEFORE   = PPv2 Neutral path + grades_final.json        (what Unity would have shown with the v2 numbers)
    AFTER    = PPv2 Neutral path + grades_engine.json       (what Unity will show with this kit)
Writes Docs~/Engine_vs_Look_1.png, _2.png (profiles in two halves), Docs~/Engine_vs_Look_Shadows.png (the darkest part
of each night frame with display codes x5, and the input-0 black point as swatches) and prints per-profile code differences.
Usage: python3 compare_frames.py [--frames frames.npz]   (without --frames the frames are rebuilt from art/, ~1 min)
"""
import argparse
import copy
import json
import os
import sys

import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
TOOLS = os.path.dirname(HERE)
KIT = os.path.dirname(TOOLS)
ART = os.path.normpath(os.path.join(KIT, '..', '..', 'art'))
sys.path.insert(0, HERE)
import ppv2_engine as E  # noqa: E402
sys.path.insert(0, os.path.join(ART, 'lens_cine'))
sys.path.insert(0, os.path.join(ART, 'bible_work'))
import ppv2 as LD  # noqa: E402
from lutlib_core import patch_ppv2  # noqa: E402
patch_ppv2(LD)

FONT_DIR = os.environ.get('FONT_DIR', os.path.normpath(os.path.join(KIT, '..', '..', '..', 'fonts')))


def font(name, px):
    for p in (os.path.join(FONT_DIR, name), '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'):
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


LABEL = {'S1': '站牌', 'S2': '夜路', 'S3': '月海 · 基准', 'S4': '触手之门', 'S4c': '门内', 'S6': '晨', 'S7a': '海面之下',
         'S7b': '深海 · 河伯', 'S8': '暮', 'S8b': '蓝时', 'S9a': '星海', 'S9b': '星海高潮', 'S10': '白 · 中性',
         'S11': '假醒', 'S12': '醒'}


def load_frames(path):
    if path and os.path.exists(path):
        return dict(np.load(path))
    cwd = os.getcwd()
    os.chdir(os.path.join(ART, 'bible_work'))
    try:
        import make_previews as MP
        return {k: np.asarray(fn(), np.float32) for k, (_, fn) in MP.SOURCES.items()}
    finally:
        os.chdir(cwd)


def prof(G, sid):
    P = G['profiles'][sid]['ppv2']
    p = copy.deepcopy(P)
    p['colorFilter'] = G['common']['colorFilter']
    p['hueShift'] = G['common']['hueShift']
    return p


def render_look(img, p):
    return np.clip(LD.render(img, p, with_bloom=True), 0, 1) * 255.0


def render_engine(img, p_grade, p_bloom):
    x = img + LD.bloom_layer(img, LD.full(p_bloom))           # PPv2: bloom added to the scene-linear image, then the LUT
    return E.codes(x, p_grade)


def look_black(pl, sid, Ge):
    """The black the bible asks for at input 0 (the solver's target: look simulator, S7a from the bible text, red >= 1)."""
    t = Ge['_engine']['report'][sid]['black']['target']
    return E.hex8(t)


def shadow_sheet(rows, out):
    """Darkest 45 % band of every night frame, display codes x5 (so a 1-code black lift is visible), + black swatches."""
    fT, fS, fL, fM = font('SourceHanSansCN-Medium.otf', 30), font('SourceHanSansCN-Regular.otf', 17), \
        font('BarlowSemiCondensed-SemiBold.ttf', 26), font('IBMPlexMono-Regular.ttf', 15)
    sel = [r for r in rows if r[0] in ('S1', 'S2', 'S3', 'S4', 'S7a', 'S7b', 'S8b', 'S9a', 'S9b', 'S11', 'S12')]
    tw, th, sw = 470, 150, 96
    W = 150 + 3 * (tw + sw + 30) + 20
    H = 170 + len(sel) * (th + 34) + 50
    im = Image.new('RGB', (W, H), (16, 17, 20))
    d = ImageDraw.Draw(im)
    d.text((40, 28), '蓝白 · 暗部放大 ×5：夜的黑在引擎里去了哪里', font=fT, fill=(232, 241, 245))
    d.text((40, 74), '每个 profile 取测试帧里最暗的一段，显示码 ×5（1 码的抬黑也看得见）；右边色块 = 输入 0 的黑点（×5 显示，下面是真实 hex）。'
                     '圣经 §1.3.5：夜间调色把输入 0 抬到约 #02060C 的蓝黑，永不压红到 0。', font=fS, fill=(150, 158, 168))
    heads = ['目标（圣经）', '修正前（PPv2 + 旧参数）', '修正后（PPv2 + grades_engine）']
    for i, h in enumerate(heads):
        d.text((150 + i * (tw + sw + 30), 124), h, font=fS, fill=(190, 198, 208))
    y = 160
    for sid, look, before, after, d0, d1, img, blk in sel:
        lum = img @ E.LUMA709_UTIL
        rowm = lum.mean(1)
        n = int(0.45 * len(rowm))
        best = min(range(0, len(rowm) - n + 1, 4), key=lambda a: rowm[a:a + n].mean())
        d.text((40, y + 10), sid, font=fL, fill=(232, 241, 245))
        for i, (arr, b) in enumerate(((look, blk[0]), (before, blk[1]), (after, blk[2]))):
            crop = np.clip(np.round(arr[best:best + n]) * 5.0, 0, 255).astype(np.uint8)
            t = Image.fromarray(crop).resize((tw, th), Image.LANCZOS)
            x = 150 + i * (tw + sw + 30)
            im.paste(t, (x, y))
            bb = np.clip(np.round(b), 0, 255)
            d.rectangle([x + tw + 10, y, x + tw + 10 + sw, y + th - 30], fill=tuple(int(v) for v in np.clip(bb * 5, 0, 255)))
            col = (230, 120, 110) if bb[0] < 1 and sid != 'S7a' or (i > 0 and np.abs(bb - np.round(blk[0])).max() > 2) else (170, 178, 188)
            d.text((x + tw + 10, y + th - 24), E.to_hex(bb), font=fM, fill=col)
        y += th + 34
    d.text((40, H - 40), '红字 = 黑点红通道被压到 0，或与目标差 > 2 码。修正前夜景的黑是 #000000–#000002（verify.md B1）；修正后回到蓝黑。', font=fS, fill=(120, 128, 138))
    im.save(out, optimize=True)
    print('wrote', out, im.size)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--frames', default=None)
    a = ap.parse_args()
    Gl = json.load(open(os.path.join(TOOLS, 'inputs', 'grades_final.json'), encoding='utf-8'))
    Ge = json.load(open(os.path.join(TOOLS, 'inputs', 'grades_engine.json'), encoding='utf-8'))
    F = load_frames(a.frames)
    ids = sorted(Gl['profiles'], key=lambda s: Gl['profiles'][s]['priority'])
    rows = []
    for sid in ids:
        img = np.maximum(np.asarray(F[sid], np.float64), 0)
        pl, pe = prof(Gl, sid), prof(Ge, sid)
        look = render_look(img, pl)
        before = render_engine(img, pl, pl)
        after = render_engine(img, pe, pe)
        d0 = np.abs(np.round(before) - np.round(look)).max(-1)
        d1 = np.abs(np.round(after) - np.round(look)).max(-1)
        blk = [look_black(pl, sid, Ge), E.codes(np.zeros((1, 3)), pl)[0], E.codes(np.zeros((1, 3)), pe)[0]]
        rows.append((sid, look, before, after, d0, d1, img, blk))
        print('%-4s BEFORE vs LOOK: mean %.2f p99 %2.0f max %3.0f  |  AFTER vs LOOK: mean %.2f p99 %2.0f max %3.0f  (codes, per pixel max channel)'
              % (sid, d0.mean(), np.percentile(d0, 99), d0.max(), d1.mean(), np.percentile(d1, 99), d1.max()), flush=True)

    fT, fS, fL, fM = font('SourceHanSansCN-Medium.otf', 30), font('SourceHanSansCN-Regular.otf', 17), \
        font('BarlowSemiCondensed-SemiBold.ttf', 26), font('IBMPlexMono-Regular.ttf', 14)
    tw, th = 540, 226
    for part, sel in ((1, rows[:8]), (2, rows[8:])):
        W = 170 + 3 * (tw + 14) + 20
        H = 150 + len(sel) * (th + 40) + 60
        im = Image.new('RGB', (W, H), (16, 17, 20))
        d = ImageDraw.Draw(im)
        d.text((40, 30), '蓝白 · 引擎里的调色 vs 圣经的目标（%d/2）' % part, font=fT, fill=(232, 241, 245))
        heads = ['目标（圣经预览：美术模拟器 + grades_final）', '修正前：PPv2 真实 Neutral 通路 + 旧参数', '修正后：PPv2 真实 Neutral 通路 + grades_engine']
        for i, h in enumerate(heads):
            d.text((170 + i * (tw + 14), 100), h, font=fS, fill=(170, 178, 188))
        y = 140
        for sid, look, before, after, d0, d1, _, _ in sel:
            d.text((40, y + 6), sid, font=fL, fill=(232, 241, 245))
            d.text((40, y + 40), LABEL.get(sid, ''), font=fS, fill=(170, 178, 188))
            for i, (arr, dd) in enumerate(((look, None), (before, d0), (after, d1))):
                t = Image.fromarray(np.clip(np.round(arr), 0, 255).astype(np.uint8)).resize((tw, th), Image.LANCZOS)
                x = 170 + i * (tw + 14)
                im.paste(t, (x, y))
                if dd is not None:
                    col = (230, 120, 110) if np.percentile(dd, 99) > 3 else (140, 200, 150)
                    d.text((x, y + th + 6), '与目标差（码）：均 %.2f · p99 %.0f · 最大 %.0f' % (dd.mean(), np.percentile(dd, 99), dd.max()), font=fS, fill=col)
            y += th + 40
        d.text((40, H - 44), '含 bloom（bloom 在调色之前、参数没变）。修正后的差来自：高饱和的亮发光体（calib §B 已为它们重解填值，这里仍用旧填值）与 LUT 量化。',
               font=fS, fill=(120, 128, 138))
        out = os.path.join(KIT, 'Docs~', 'Engine_vs_Look_%d.png' % part)
        im.save(out, optimize=True)
        print('wrote', out, im.size)
    shadow_sheet(rows, os.path.join(KIT, 'Docs~', 'Engine_vs_Look_Shadows.png'))


if __name__ == '__main__':
    main()
