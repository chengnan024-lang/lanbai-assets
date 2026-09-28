# -*- coding: utf-8 -*-
"""v2 before/after previews. BEFORE = the frame through PPv2 HDR + Neutral at default settings (profile S10, no bloom).
AFTER = the full v2 profile INCLUDING bloom (corrected PPv2 threshold/knee/clamp semantics, 1080p pyramid).
The LUT file reproduces AFTER minus bloom; its agreement with the parametric path is printed per profile."""
import os, sys, json, numpy as np
from PIL import Image, ImageDraw, ImageFont
from lutlib import ppv2, PROF, read_strip, apply_lut, GF
import scenes_proc as SP
import scenes_v2 as V
from scene_data import SCENES

OUT = '../previews'; os.makedirs(OUT, exist_ok=True)
CJK = '/usr/share/fonts/truetype/wqy/wqy-zenhei.ttc'; MONO = '/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf'
SANS = '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
BG = (12, 14, 19); INK = (232, 241, 245); MUTED = (128, 146, 164)
F = lambda p, s: ImageFont.truetype(p, s)
NAMES = {'S1': '01_stop', 'S2': '02_nightroad', 'S3': '03_liftoff_moon', 'S4': '04_gate', 'S4c': '04c_inside_tear', 'S6': '06_dawn',
         'S7a': '07a_undersea', 'S7b': '07b_deep_palace', 'S8': '08_dusk', 'S8b': '08b_bluehour', 'S9a': '09a_starsea',
         'S9b': '09b_starsea_climax', 'S10': '10_white', 'S11': '11_false_wake', 'S12': '12_wake'}
FR = np.load('../lens_cine/mock/frames.npz')

def mock(key):
    a = FR[key]
    im = Image.fromarray(np.clip(a / 8.0, 0, 1).astype(np.float32).mean(-1))  # dummy to get size
    out = np.stack([np.asarray(Image.fromarray(a[..., c].astype(np.float32), 'F').resize((SP.W, SP.H), Image.BILINEAR)) for c in range(3)], -1)
    return out.astype(np.float64)

def s9b_frame():
    """star field above; a white-bronze mirror face below carrying the reflected Milky Way; its rising edge = the mirror line."""
    f = mock('S9').copy()
    hz = 0.60
    top = f[:int(hz * SP.H)]
    refl = top[::-1][:SP.H - int(hz * SP.H)]
    refl = np.pad(refl, ((0, max(0, SP.H - int(hz * SP.H) - refl.shape[0])), (0, 0), (0, 0)), mode='edge')
    bronze = np.array([0.92, 0.84, 0.66]) * 1.35
    f[int(hz * SP.H):] = refl * bronze + np.array([0.020, 0.017, 0.012])
    line = np.exp(-((SP.v - hz) / 0.0035) ** 2)
    f += np.array([0.95, 0.98, 1.1]) * 2.2 * line[..., None]
    f += np.array([0.35, 0.33, 0.30]) * 0.10 * np.exp(-((SP.v - hz) / 0.05) ** 2)[..., None]
    return f

DAWN_K = 0.6   # the v1 dawn mock is 0.74 EV too bright: scaled so its zenith lands on the #3E64A6 luma under S6
SOURCES = {
 'S1': ('雨中的站牌（程序化测试帧）', lambda: SP.stop('S1')),
 'S2': ('挡风玻璃外的夜路（程序化测试帧）', lambda: SP.road('S2')),
 'S3': ('月下云海（v1 云卡合成）', lambda: mock('S3')),
 'S4': ('U7+3 秒：透镜形裂口、光雾带、远潮、巨像（程序化测试帧，v2 几何）', lambda: V.gate('S4')),
 'S4c': ('门内第 5 重：三重错开的撕口、暗的恩典（程序化测试帧）', lambda: V.tear_inside('S4c')),
 'S6': ('晨（v1 云卡合成，色相按 v2 目标重映射，曝光按天顶目标校）', lambda: V.remapped_mock(mock('S6'), [(285, 330, 270, 0.62)]) * DAWN_K),
 'S7a': ('海面之下：斯涅尔之窗与光柱（程序化测试帧）', lambda: V.undersea('S7a')),
 'S7b': ('河伯：两列 12 盏灯汇向开着的门（程序化测试帧）', lambda: V.deep('S7b')),
 'S8': ('暮 8-i：海之天花与 3° 天缝（v1 云卡合成，阴影色相按 v2 目标重映射）', lambda: V.remapped_mock(mock('S8'), [(288, 335, 283, 0.62)])),
 'S8b': ('蓝时（程序化测试帧）', lambda: SP.bluehour('S8b')),
 'S9a': ('星海：银河一整圈点燃之后（程序化测试帧）', lambda: V.starsea('S9a')),
 'S9b': ('星海高潮：第 12 面镜、上一面的星尘、天问的 16 颗星（程序化测试帧）', lambda: V.starsea('S9b', climax=True)),
 'S10': ('白：S10 是中性（校验用；白由藍白遮罩球承担）', lambda: V.remapped_mock(mock('S6'), [(285, 330, 270, 0.62)]) * DAWN_K),
 'S11': ('假醒：头顶的海、倒挂的灯（程序化测试帧）', lambda: SP.road('S11', false=True)),
 'S12': ('醒：雨停、静水、萤火虫、那一只 Lichtchen（程序化测试帧）', lambda: SP.stop('S12', wake=True)),
}
# universal reference patches: (label, scene-linear)
REF = [('中灰 18%', np.full(3, 0.18)), ('肤色 浅', ppv2.hex_to_lin('#C8967A') * 0.9), ('肤色 深', ppv2.hex_to_lin('#6B4634') * 0.9),
       ('植物', ppv2.hex_to_lin('#3F5A2A') * 0.9), ('牛血红座椅', ppv2.hex_to_lin('#5A2126') * 0.9), ('藍白珐琅', ppv2.hex_to_lin('#DDE9EA') * 0.9),
       ('靛蓝', ppv2.hex_to_lin('#1D3E66') * 0.9), ('钠灯', ppv2.hex_to_lin('#FF941D') * 1.6), ('天蓝', ppv2.hex_to_lin('#6E8FC8')), ('高光 ×4', np.full(3, 0.72))]

def neutral_disp(lin):
    return ppv2.render(lin, {}, with_bloom=False)

def to_img(a):
    return Image.fromarray(np.clip(np.round(a * 255), 0, 255).astype(np.uint8), 'RGB')

def chart(prof, lut, pal):
    ramp = [np.full(3, 0.18 * 2.0 ** k) for k in range(-6, 5)]
    pw = 1.0
    cols = [(('%+d' % k), c) for k, c in zip(range(-6, 5), ramp)] + REF
    lin = np.array([c for _, c in cols])[None]
    before = neutral_disp(lin)[0]
    after = apply_lut(before[None], lut)[0]
    return cols, before, after

def build(prof, sc):
    lut = read_strip('../luts/Lanbai_%s_%s_1024x32.png' % (prof, NAMES[prof]))
    label, fn = SOURCES[prof]
    lin = fn()
    before = neutral_disp(lin)
    lut_only = apply_lut(np.round(before * 255) / 255, lut)
    after = ppv2.render(lin, PROF[prof], with_bloom=True)
    nob = ppv2.render(lin, PROF[prof], with_bloom=False)
    e = np.abs(lut_only - nob) * 255
    build.lutcheck = (float(e.mean()), float(np.percentile(e, 99)))
    cols, cb, ca = chart(prof, lut, sc['pal'])
    Wp, Hp = SP.W, SP.H
    m, gap = 40, 24
    W = 2 * Wp + gap + 2 * m
    Hh = 118 + Hp + 50 + 250
    im = Image.new('RGB', (W, Hh), BG); d = ImageDraw.Draw(im)
    d.text((m, 26), '%s  %s' % (sc['id'], sc['zh']), font=F(CJK, 40), fill=INK)
    tw = d.textlength('%s  %s' % (sc['id'], sc['zh']), font=F(CJK, 40))
    d.text((m + tw + 20, 40), '%s  ·  LUT  Lanbai_%s_%s' % (sc['en'], prof, NAMES[prof]), font=F(SANS, 20), fill=MUTED)
    p = GF['profiles'][prof]['ppv2']
    apl = float((np.clip(after, 0, 1) @ [0.2126, 0.7152, 0.0722]).mean() * 255)
    info = 'postExposure %+.2f  temp %+d  tint %+d  sat %+d  contrast %+d  bloom %.0f / thr %.2f (T0 %.2f)  ·  APL %.0f（含 bloom）' % (
        p['postExposure'], p['temperature'], p['tint'], p['saturation'], p['contrast'], p['bloom']['intensity'], p['bloom']['threshold'],
        GF['profiles'][prof]['bloom_T0_scene_linear'], apl)
    d.text((m, 78), label + '     ' + info, font=F(CJK, 18), fill=MUTED)
    y0 = 118
    im.paste(to_img(before), (m, y0)); im.paste(to_img(after), (m + Wp + gap, y0))
    d.text((m, y0 + Hp + 10), '之前 · 中性（PPv2 HDR + Neutral，默认参数 = S10）', font=F(CJK, 19), fill=MUTED)
    d.text((m + Wp + gap, y0 + Hp + 10), '之后 · %s（完整 profile，含 bloom；LUT 与之差 = bloom）' % prof, font=F(CJK, 19), fill=INK)
    # chart
    cy = y0 + Hp + 56
    n = len(cols); cw = (W - 2 * m) / n
    for i, (lab, _) in enumerate(cols):
        x0 = m + i * cw
        d.rectangle([x0 + 2, cy, x0 + cw - 2, cy + 62], fill=tuple(int(round(c * 255)) for c in np.clip(cb[i], 0, 1)))
        d.rectangle([x0 + 2, cy + 66, x0 + cw - 2, cy + 128], fill=tuple(int(round(c * 255)) for c in np.clip(ca[i], 0, 1)))
        d.text((x0 + 4, cy + 134), lab, font=F(CJK, 14), fill=MUTED)
        d.text((x0 + 4, cy + 154), ppv2.srgb_to_hex(ca[i]), font=F(MONO, 12), fill=INK)
    d.text((m, cy + 184), '上排：中性    下排：%s 的 LUT    （灰阶 = 0.18×2^k 的无光照灰片，k = -6..+4；参考色 = 在白光 E=0.9 下的反照率）    v2' % prof, font=F(CJK, 15), fill=MUTED)
    path = '%s/Preview_%s_%s.png' % (OUT, prof, NAMES[prof])
    im.save(path)
    return path, before, after

if __name__ == '__main__':
    only = sys.argv[1:] or list(NAMES)
    bykey = {}
    for s in SCENES:
        bykey.setdefault(s['grade'], s)
    for prof in only:
        sc = bykey.get(prof) or dict(id='09', zh='星海 · 高潮', en='Star sea, climax', pal=[])
        path, b, a = build(prof, sc)
        L = (np.clip(a, 0, 1) @ [0.2126, 0.7152, 0.0722]) * 255
        print(path, 'APL before %.0f after(bloom) %.0f  <luma12 %.1f%%  LUT-vs-param mean %.2f p99 %.2f' % (
            np.mean(np.clip(b, 0, 1) @ [0.2126, 0.7152, 0.0722]) * 255, L.mean(), (L < 12).mean() * 100, *build.lutcheck))
        np.save('cache/after_%s.npy' % prof, a.astype(np.float32))
