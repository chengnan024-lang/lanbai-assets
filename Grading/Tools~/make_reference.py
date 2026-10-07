# -*- coding: utf-8 -*-
"""Reference images for the Unity side, drawn from the GENERATED C# (parsed back, not from the json):

  Docs~/TestCard_Reference.png  -- the 15 x 11 test-card targets (calib §C) as swatches + hex, to hold next to
                                   LanbaiReports/TestCard_AllProfiles.png from Unity
  Docs~/TestCard_Layout.png     -- front view of the Lanbai_TestCard rig with dimensions, and the volume stack
Fonts: Source Han Sans CN, Barlow Semi Condensed, IBM Plex Mono (all SIL OFL), looked up in FONT_DIR.
"""
import os
import sys

from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
sys.path.insert(0, HERE)
from verify_grade_data import parse_data_cs  # noqa: E402

FONT_DIR = os.environ.get('FONT_DIR', os.path.normpath(os.path.join(KIT, '..', '..', '..', 'fonts')))
SS = 2  # supersample


def font(name, px):
    for p in (os.path.join(FONT_DIR, name), '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'):
        if os.path.exists(p):
            return ImageFont.truetype(p, int(px * SS))
    return ImageFont.load_default()


CJK = lambda px: font('SourceHanSansCN-Regular.otf', px)
CJKM = lambda px: font('SourceHanSansCN-Medium.otf', px)
LAT = lambda px: font('BarlowSemiCondensed-Medium.ttf', px)
LATB = lambda px: font('BarlowSemiCondensed-SemiBold.ttf', px)
MONO = lambda px: font('IBMPlexMono-Regular.ttf', px)

# short scene labels as the bible's 1.7 table names them (display only)
LABEL = {'S1': '站牌', 'S2': '夜路', 'S3': '月海 · 基准 EV0', 'S4': '触手之门', 'S4c': '门内', 'S6': '晨', 'S7a': '海面之下',
         'S7b': '深海 · 河伯', 'S8': '暮', 'S8b': '蓝时', 'S9a': '星海', 'S9b': '星海高潮', 'S10': '白 · 中性',
         'S11': '假醒 (= S2)', 'S12': '醒'}

BG = (20, 21, 24)
INK = (226, 232, 236)
DIM = (140, 148, 156)
FAINT = (70, 75, 82)
LANBAI = (232, 241, 245)       # 藍白 #E8F1F5
INDIGO = (46, 79, 138)


def hex2rgb(h):
    return tuple(int(h[i:i + 2], 16) for i in (1, 3, 5))


def luma(c):
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def S(v):
    return int(round(v * SS))


def text(d, xy, s, f, fill=INK, anchor='la'):
    d.text((S(xy[0]), S(xy[1])), s, font=f, fill=fill, anchor=anchor)


def finish(img, path):
    img = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
    img.save(path, optimize=True)
    print('wrote', path, img.size)


# ------------------------------------------------------------------------------------------------
NIGHT = ['S1', 'S2', 'S3', 'S4', 'S4c', 'S7a', 'S7b', 'S8b', 'S9a', 'S9b', 'S11', 'S12']


def hexdiff(a, b):
    return max(abs(x - y) for x, y in zip(hex2rgb(a), hex2rgb(b)))


def reference_sheet(entries, path):
    scenes = [e for e in entries if e['kind'] == 'Scene']
    W, left, top = 2200, 330, 250
    sw, sh, gx, rowh = 132, 58, 10, 104
    H = top + rowh * len(scenes) + 190
    img = Image.new('RGB', (S(W), S(H)), BG)
    d = ImageDraw.Draw(img)

    text(d, (60, 52), 'LANBAI', LATB(40), LANBAI)
    text(d, (212, 50), '蓝白 · 调色测试卡目标值', CJKM(34), LANBAI)
    text(d, (60, 112), 'calib_final.md §C  ·  11 块无光照灰片，场景线性 0.18 × 2^k（k = −6 … +4）  ·  每个 profile 单独 weight 1  ·  '
         '测量模式：bloom / 暗角 / 颗粒 关  ·  截图读数允许 ±3 码', CJK(19), DIM)
    text(d, (60, 142), '色块 = 目标（法律）；色块下第二个数 = 套件写入的引擎参数在 PPv2 Neutral 通路里的预测与目标之差（码）。'
         '右列 = 黑底（输入 0）：目标 / 预测。和 LanbaiReports/TestCard_AllProfiles.png 并排看。', CJK(19), DIM)

    x0 = left
    for i, k in enumerate(range(-6, 5)):
        cx = x0 + i * (sw + gx) + sw / 2
        text(d, (cx, top - 62), ('k %+d' % k).replace('-', '−') if k else 'k 0', LATB(22), INK, 'ma')
        text(d, (cx, top - 34), ('%.4f' % (0.18 * 2 ** k)).rstrip('0').rstrip('.'), MONO(15), DIM, 'ma')
    xb = x0 + 11 * (sw + gx) + 24
    text(d, (xb + 80, top - 62), '黑 · 输入 0', CJKM(20), INK, 'ma')
    text(d, (xb + 80, top - 34), '目标 / 引擎预测', CJK(14), DIM, 'ma')
    d.line([S(60), S(top - 10), S(W - 60), S(top - 10)], fill=FAINT, width=S(1))

    worst = 0
    for r, e in enumerate(scenes):
        y = top + r * rowh + 8
        name = e.get('shortName') or LABEL.get(e['id'], e['id'])
        text(d, (60, y + 2), e['id'], LATB(30), LANBAI)
        text(d, (60 + 21 * len(e['id']) + 12, y + 8), name, CJKM(21), INK)
        pe = e['postExposure']
        text(d, (60, y + 44), 'postExp %+.2f   T0 %.2f' % (pe, e['bloomT0']), LAT(18), DIM)
        if e['id'] == 'S10':
            text(d, (60, y + 68), '中性 = 自检行：k 0 必须读 #767676', CJK(16), (190, 200, 150))
        for i, h in enumerate(e['expectedTestCard']):
            c = hex2rgb(h)
            x = x0 + i * (sw + gx)
            d.rectangle([S(x), S(y), S(x + sw), S(y + sh)], fill=c)
            if i == 6:
                d.rectangle([S(x - 3), S(y - 3), S(x + sw + 3), S(y + sh + 3)], outline=(90, 96, 104), width=S(1.5))
            dd = hexdiff(h, e['predictedTestCard'][i])
            worst = max(worst, dd)
            text(d, (x + 4, y + sh + 8), h, MONO(15), DIM)
            text(d, (x + sw - 2, y + sh + 8), 'Δ%d' % dd, LAT(16), (140, 200, 150) if dd <= 3 else (230, 120, 110), 'ra')
        # black point: target swatch (left half) and engine prediction (right half), both at true value
        bt, bp = e['expectedBlack'], e['predictedBlack']
        d.rectangle([S(xb), S(y), S(xb + 80), S(y + sh)], fill=hex2rgb(bt))
        d.rectangle([S(xb + 80), S(y), S(xb + 160), S(y + sh)], fill=hex2rgb(bp))
        d.rectangle([S(xb - 1), S(y - 1), S(xb + 161), S(y + sh + 1)], outline=(52, 56, 62), width=S(1))
        red = hex2rgb(bp)[0]
        col = (230, 120, 110) if (e['id'] in NIGHT and red < 1) or hexdiff(bt, bp) > 1 else DIM
        text(d, (xb, y + sh + 8), '%s / %s' % (bt, bp), MONO(14), col)
        d.line([S(60), S(y + rowh - 12), S(W - 60), S(y + rowh - 12)], fill=(34, 36, 40), width=S(1))

    yb = top + rowh * len(scenes) + 26
    night_ok = all(hex2rgb(e['predictedBlack'])[0] >= 1 for e in scenes if e['id'] in NIGHT)
    by = {e['id']: e for e in scenes}
    text(d, (60, yb), '按 PPv2 源码写的引擎模型预测：与 §C 目标最多差 %d 码%s。黑底（输入 0）：夜间 profile（%s）%s；' % (
        worst, '（全部 ≤ 3）' if worst <= 3 else '（有超过 3 的，见红字）', '、'.join(NIGHT),
        '全部抬到蓝黑、红通道 ≥ 1' if night_ok else '有红通道被压到 0 的（见红字）'), CJK(18), DIM)
    text(d, (60, yb + 30), '晨 S6 %s、暮 S8 %s 的黑按外观定义只抬蓝不抬红；S10 中性。S3 是全片曝光基准 EV0；k +3 / +4 在负曝光 profile 下进入 bloom 软膝，所以测量一律关 bloom。' % (
        by['S6']['predictedBlack'], by['S8']['predictedBlack']), CJK(18), DIM)
    text(d, (60, yb + 64), '由 Tools~/make_reference.py 从 Editor/LanbaiGradeData.cs 解析生成；预测与引擎门限核对见 Docs~/verify_report.txt（两个按 PPv2 源码独立写成的模型）。'
         '这是模型的预测，不是 Unity 的实测：实测看 MeasureAll 的报告。', CJK(16), FAINT)
    finish(img, path)


def colour_sheet(entries, names, path):
    """The test card's colour row: what the LOOK shows (target of the solve, not a bible law value) per profile."""
    scenes = [e for e in entries if e['kind'] == 'Scene']
    n = len(names)
    W, left, top = 2000, 330, 250
    sw, sh, gx, rowh = 170, 50, 12, 92
    H = top + rowh * len(scenes) + 150
    img = Image.new('RGB', (S(W), S(H)), BG)
    d = ImageDraw.Draw(img)
    text(d, (60, 52), 'LANBAI', LATB(40), LANBAI)
    text(d, (212, 50), '蓝白 · 测试卡第二行：饱和色', CJKM(34), LANBAI)
    text(d, (60, 112), '8 块无光照色片（场景线性，SetVector 写入，不经颜色转换）。色块 = 外观（美术模拟器 + 圣经 B1）在该 profile 下的样子；'
         '数 = 引擎预测与它之差（码）。', CJK(19), DIM)
    text(d, (60, 142), '不是圣经的法律值：它检查 Unity 里的 PPv2 处理饱和色是否和我们的模型一致（Channel Mixer 的活）。MeasureAll 报告里有实测。', CJK(19), DIM)
    for i, nm in enumerate(names):
        cx = left + i * (sw + gx) + sw / 2
        text(d, (cx, top - 46), nm, CJK(16), INK, 'ma')
    d.line([S(60), S(top - 12), S(W - 60), S(top - 12)], fill=FAINT, width=S(1))
    worst = 0
    for r, e in enumerate(scenes):
        y = top + r * rowh + 6
        text(d, (60, y + 4), e['id'], LATB(28), LANBAI)
        text(d, (60 + 21 * len(e['id']) + 12, y + 10), e.get('shortName') or e['id'], CJKM(19), INK)
        for i, h in enumerate(e['expectedColourPatches']):
            x = left + i * (sw + gx)
            d.rectangle([S(x), S(y), S(x + sw), S(y + sh)], fill=hex2rgb(h))
            dd = hexdiff(h, e['predictedColourPatches'][i])
            worst = max(worst, dd)
            text(d, (x + 4, y + sh + 6), h, MONO(14), DIM)
            text(d, (x + sw - 2, y + sh + 6), 'Δ%d' % dd, LAT(16), (140, 200, 150) if dd <= 3 else (230, 120, 110), 'ra')
    # how big the differences are to the eye: CIE76 Delta E of every cell that differs by more than 3 codes
    big, de_blue, de_warm = 0, 0.0, 0.0
    for e in scenes:
        for h, q in zip(e['expectedColourPatches'], e['predictedColourPatches']):
            if hexdiff(h, q) <= 3:
                continue
            big += 1
            de = delta_e76(hex2rgb(h), hex2rgb(q))
            if hex2rgb(h)[2] > hex2rgb(h)[0]:
                de_blue = max(de_blue, de)
            else:
                de_warm = max(de_warm, de)
    yb = top + rowh * len(scenes) + 24
    text(d, (60, yb), '引擎预测与外观最多差 %d 码；差 > 3 码的 %d 格，换成色差：偏蓝的色最大 ΔE76 %.1f（差几乎都在接近 0 的红通道，看不出来），'
         '暖色最大 ΔE76 %.1f（引擎略红一点）。' % (worst, big, de_blue, de_warm), CJK(17), DIM)
    text(d, (60, yb + 28), '每一幕真正出现的颜色另由 calib §B 填值（引擎下 ≤ 3 码）和预览测试帧（Docs~/Engine_vs_Look_*.png）把关；这一行的颜色放进每一个 profile，'
         '所以有不在那一幕出现的组合（例如 S9b 的钠灯、S3 的尾灯）。', CJK(17), DIM)
    text(d, (60, yb + 58), '由 Tools~/make_reference.py 从 LanbaiGradeData.cs 生成；Unity 实测见 MeasureAll 报告的 “Colour row” 一节（与模型比，±3）。', CJK(15), FAINT)
    finish(img, path)


def delta_e76(a, b):
    def lab(c):
        v = [x / 255.0 for x in c]
        v = [x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in v]
        X = (0.4124 * v[0] + 0.3576 * v[1] + 0.1805 * v[2]) / 0.9505
        Y = 0.2126 * v[0] + 0.7152 * v[1] + 0.0722 * v[2]
        Z = (0.0193 * v[0] + 0.1192 * v[1] + 0.9505 * v[2]) / 1.089
        f = [t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116 for t in (X, Y, Z)]
        return 116 * f[1] - 16, 500 * (f[0] - f[1]), 200 * (f[1] - f[2])
    la, lb = lab(a), lab(b)
    return sum((x - y) ** 2 for x, y in zip(la, lb)) ** 0.5


# ------------------------------------------------------------------------------------------------
def layout_sheet(entries, path):
    W, H = 2000, 1330
    img = Image.new('RGB', (S(W), S(H)), BG)
    d = ImageDraw.Draw(img)
    text(d, (60, 52), 'LANBAI', LATB(40), LANBAI)
    text(d, (212, 50), '蓝白 · 测试卡布局与 volume 叠放', CJKM(34), LANBAI)
    text(d, (60, 112), '正视图（从座位看过去）。rig 根物体 Lanbai_TestCard：tag EditorOnly（打包时整棵剥离）、层 LanbaiDebug、非 static、不投影。'
         '尺寸单位 m；可整体移动 / 旋转，保持正面朝向座位。', CJK(19), DIM)
    text(d, (60, 140), '自动测量分两趟：色片趟只渲染 LanbaiDebug 层（1.5 m，FOV 40，座椅 / 柱子永远挡不住色片）；卡片趟在两张卡前 0.7 m，'
         '另加卡片所在层（例如 Bus）。', CJK(19), DIM)

    # ---- front view, 1 m = 560 px, origin = patch row centre
    s = 560.0
    ox, oy = 640, 520
    P = lambda x, y: (S(ox + x * s), S(oy - y * s))
    s10 = [e for e in entries if e['id'] == 'S10'][0]['expectedTestCard']
    pitch, size = 0.115, 0.10
    bw = 10 * pitch + size + 0.06
    d.rectangle([*P(-bw / 2, 0.08), *P(bw / 2, -0.20)], fill=(6, 6, 7))
    # colour row
    cols = [e for e in entries if e['id'] == 'S10'][0]['expectedColourPatches']
    for i, h in enumerate(cols):
        x = (i - (len(cols) - 1) / 2) * pitch
        d.rectangle([*P(x - size / 2, -0.135 + size / 2), *P(x + size / 2, -0.135 - size / 2)], fill=hex2rgb(h))
    text(d, (ox + bw / 2 * s + 12, oy + 0.135 * s - 12), 'ColourPatches c1–c8', LAT(16), DIM)
    # black sample point (input 0) on the backing above the row: leader line in the gap above the patches
    bx, by_ = 0.0, 0.065
    d.rectangle([*P(bx - 0.008, by_ + 0.008), *P(bx + 0.008, by_ - 0.008)], outline=(230, 190, 90), width=S(2))
    d.line([*P(bx + 0.010, by_), *P(bw / 2 + 0.02, by_)], fill=(230, 190, 90), width=S(1))
    text(d, (ox + (bw / 2 + 0.03) * s, oy - by_ * s - 12), '黑点取样（输入 0）', CJK(15), (230, 190, 90))
    for i in range(11):
        x = (i - 5) * pitch
        d.rectangle([*P(x - size / 2, size / 2), *P(x + size / 2, -size / 2)], fill=hex2rgb(s10[i]))
        k = i - 6
        text(d, (ox + x * s, oy - 0.08 * s - 30), ('k%+d' % k).replace('-', '\u2212') if k else 'k0', LAT(17), DIM, 'ma')
    text(d, (ox + bw / 2 * s + 12, oy - 12), 'Patches k−6…k+4', LAT(16), DIM)
    # spheres
    sph = [('Grey18', (118, 118, 118)), ('White80', (231, 231, 231)), ('Chrome', (207, 209, 211)), ('Black30', (30, 30, 30))]
    for i, (n, c) in enumerate(sph):
        cx, cy, r = -0.3 + 0.2 * i, 0.25, 0.075
        d.ellipse([*P(cx - r, cy + r), *P(cx + r, cy - r)], fill=c, outline=(60, 64, 70), width=S(1))
        text(d, (ox + cx * s, oy - (cy + r) * s - 28), n, LAT(16), DIM, 'ma')
    text(d, (ox, oy - 0.36 * s - 58), 'CalibSpheres：Ø0.15 m，Standard；18% 灰 / 80% 白 smoothness 0.2，铬 metallic 1 smoothness 1，sRGB 30 黑', CJK(16), DIM, 'ma')
    # cards: exactly where the builder puts them (centre y -0.45, 0.5 m: top edge = the backing's bottom edge, -0.20)
    for cx, c, n in ((-0.30, (118, 118, 118), 'Grey #767676'), (0.30, (230, 230, 230), 'White #E6E6E6')):
        d.rectangle([*P(cx - 0.25, -0.20), *P(cx + 0.25, -0.70)], fill=c)
        text(d, (ox + cx * s, oy + 0.45 * s - 12), n, LATB(20), (22, 22, 22), 'ma')
        text(d, (ox + cx * s, oy + 0.45 * s + 16), '0.5 m · smoothness 0', LAT(16), (30, 30, 30), 'ma')
    yc = oy + 0.70 * s + 18
    for line in ('Patches：11 × 0.10 m 方片，间距 0.115 m，自发光 0.18 × 2^k；ColourPatches：8 块饱和色（SetVector 写线性 rgb）；',
                 '两行都用 Lanbai/Debug/TestPatch（不吃雾、不受光）。Backing：0.0 黑底 %.2f × 0.28 m（y +0.08 … −0.20），垫在两行后面。' % bw,
                 'CalibCards：Standard，关高光与反射（读 Lambert：calib §A = 反照率 × E）。卡片随灯移动；烘焙灯要读数时把卡设为 static 一起烘。'):
        text(d, (60, yc), line, CJK(16), DIM)
        yc += 28

    # ---- volume stack
    x0, y0 = 1330, 190
    text(d, (x0, y0), 'Volume 叠放（PPv2 按 priority 由低到高依次 lerp）', CJKM(22), INK)
    rows = [(1001, 'PPV_DEBUG_Measure', '测量：bloom/暗角/颗粒 = 0', 0, (120, 110, 70)),
            (1000, 'PPV_VERIFY_LDR', 'LDR + 中性 LUT 验证', 0, (120, 110, 70))]
    for e in reversed(entries):
        col = {'Scene': INDIGO, 'Helper': (96, 110, 140), 'Lens': (80, 80, 92)}[e['kind']]
        lab = (e.get('shortName') or e['id']) if e['kind'] == 'Scene' else e['displayName'].split(' (')[0]
        rows.append((e['priority'], 'PPV_' + e['id'], lab, e['initialWeight'], col))
    y = y0 + 48
    for pr, n, lab, w0, col in rows:
        d.rectangle([S(x0), S(y), S(x0 + 16), S(y + 26)], fill=col)
        text(d, (x0 + 28, y + 2), '%g' % pr, LATB(19), INK)
        text(d, (x0 + 92, y + 2), n, MONO(16), INK)
        text(d, (x0 + 300, y + 3), lab, CJK(15), DIM)
        if w0:
            text(d, (x0 + 612, y + 2), 'w 1', LATB(18), LANBAI, 'ra')
        y += 34
        if pr in (1000, 199, 96):
            d.line([S(x0), S(y - 4), S(x0 + 612), S(y - 4)], fill=FAINT, width=S(1))
    for i, line in enumerate(('初始 weight：S1 = 1、LENS_CLEAN = 1（桌面镜头层始终在），其余 0。',
                              '场景 profile 各覆盖同一套 31 个参数（圣经 §1.4 的 22 个 + Channel Mixer 9 个）。',
                              '交叉淡化：新的（更高 priority）0→1，旧的保持 1，之后旧的→0。',
                              'EXPO：w = ΔEV/(4−b) 或 −ΔEV/(b+4)，b = 场景 volume 混合后的 postExposure。',
                              'VR：Lens_DesktopOnly 整个 SetActive(false)。')):
        text(d, (x0, y + 14 + 26 * i), line, CJK(16), DIM)
    finish(img, path)


def main():
    import json
    import re
    cs = os.path.join(KIT, 'Editor', 'LanbaiGradeData.cs')
    entries, _, _ = parse_data_cs(cs)
    names = [json.loads(x) for x in re.findall(r'"[^"]*"', re.search(r'ColourPatchNames = new string\[\] \{ (.*?) \};', open(cs, encoding='utf-8-sig').read()).group(1))]
    out = os.path.join(KIT, 'Docs~')
    os.makedirs(out, exist_ok=True)
    reference_sheet(entries, os.path.join(out, 'TestCard_Reference.png'))
    colour_sheet(entries, names, os.path.join(out, 'TestCard_ColourRow.png'))
    layout_sheet(entries, os.path.join(out, 'TestCard_Layout.png'))


if __name__ == '__main__':
    main()
