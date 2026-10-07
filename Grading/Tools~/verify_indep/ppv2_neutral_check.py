# -*- coding: utf-8 -*-
"""Adversarial check (verifier, not the builder): does PPv2 3.x really render the calib §C / §B targets
with the parameters in grades_final.json?

Model written from the PPv2 SOURCE (v2 branch 3.0.2 and Graphics/master 3.6.0 are identical here):
  Uber.shader  COLOR_GRADING_HDR_3D : color *= 2^postExposure; uvw = saturate(LinearToLogC(color)) (non-precise LogC)
  Lut3DBaker.compute, #else branch (Tonemapper.Neutral / None / Custom):
       LogGrade   : contrast in LogC around ACEScc_MIDGRAY 0.4135884
       LogCToLinear, LinearGrade in LINEAR REC.709 primaries: LMS white balance, colorFilter (SetVector, raw),
       channel mixer, LiftGammaGainHDR (lift*0.2, gain*0.8, gamma*0.8 via ColorUtilities), max 0,
       HSV hue, Saturation with Rec.709 luma, max 0, NeutralTonemap; 33^3 LUT stored ARGBHalf, trilinear.
The art simulator (art/lens_cine/ppv2.py grade_lut) instead runs the ACES-tonemapper branch's working spaces
(AP0 -> ACEScc contrast -> ACEScg WB/LGG/sat with AP1 luma -> sRGB -> Neutral).

Usage: python3 ppv2_neutral_check.py [--grades Tools~/inputs/grades_engine.json | grades_final.json] [--png out.png]
  Default (fix pass): the ENGINE numbers the kit ships (grades_engine.json), with the engine fills of
  calib_engine.json for section B. --grades .../grades_final.json reproduces the original finding (14/15 FAIL).
"""
import os, re, sys, glob, json, argparse
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(os.path.dirname(HERE))
ART = os.path.normpath(os.path.join(KIT, '..', '..', 'art'))
G = json.load(open(os.path.join(KIT, 'Tools~', 'inputs', 'grades_final.json'), encoding='utf-8'))
CAL = json.load(open(os.path.join(KIT, 'Tools~', 'inputs', 'calib_final.json'), encoding='utf-8'))

LC = dict(a=5.555556, b=0.047996, c=0.244161, d=0.386036)
def lin2logc(x): return LC['c'] * np.log10(LC['a'] * np.asarray(x) + LC['b']) + LC['d']
def logc2lin(x): return (10.0 ** ((np.asarray(x) - LC['d']) / LC['c']) - LC['b']) / LC['a']
L2LMS = np.array([[3.90405e-1, 5.49941e-1, 8.92632e-3], [7.08416e-2, 9.63172e-1, 1.35775e-3], [2.31082e-2, 1.28021e-1, 9.36245e-1]])
LMS2L = np.array([[2.85847e+0, -1.62879e+0, -2.48910e-2], [-2.10182e-1, 1.15820e+0, 3.24281e-4], [-4.18120e-2, -1.18169e-1, 1.06867e+0]])
def colour_balance(temp, tint):
    t1, t2 = temp / 60.0, tint / 60.0
    x = 0.31271 - t1 * (0.1 if t1 < 0 else 0.05)
    y = (2.87 * x - 3 * x * x - 0.27509507) + t2 * 0.05
    X, Y, Z = x / y, 1.0, (1 - x - y) / y
    L = 0.7328 * X + 0.4296 * Y - 0.1624 * Z; M = -0.7036 * X + 1.6975 * Y + 0.0061 * Z; S = 0.0030 * X + 0.0136 * Y + 0.9834 * Z
    return np.array([0.949237, 1.03542, 1.08728]) / np.array([L, M, S])
L709 = np.array([0.2126, 0.7152, 0.0722])
def lift_v(c): c = np.array(c, float) * 0.2; return c[:3] - c[:3] @ L709 + c[3]
def gain_v(c): c = np.array(c, float) * 0.8; return c[:3] - c[:3] @ L709 + c[3] + 1.0
def invgamma_v(c): c = np.array(c, float) * 0.8; return 1.0 / np.maximum(c[:3] - c[:3] @ L709 + c[3] + 1.0, 1e-3)
def hex_raw(h): return np.array([int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])
def hex8(h): return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)])
def s2l(v): v = np.asarray(v, float); return np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
def rgb2hsv(c):
    r, g, b = c[..., 0], c[..., 1], c[..., 2]; o = np.ones_like(r)
    p = np.where((g >= b)[..., None], np.stack([g, b, 0 * o, -o / 3], -1), np.stack([b, g, -o, 2 * o / 3], -1))
    q = np.where((r >= p[..., 0])[..., None], np.stack([r, p[..., 1], p[..., 2], p[..., 0]], -1), np.stack([p[..., 0], p[..., 1], p[..., 3], r], -1))
    d = q[..., 0] - np.minimum(q[..., 3], q[..., 1]); e = 1e-4
    return np.stack([np.abs(q[..., 2] + (q[..., 3] - q[..., 1]) / (6 * d + e)), d / (q[..., 0] + e), q[..., 0]], -1)
def hsv2rgb(c):
    K = np.array([1.0, 2 / 3, 1 / 3, 3.0]); p = np.abs(np.modf(c[..., 0:1] + K[:3])[0] * 6 - K[3])
    return c[..., 2:3] * (K[0] + (np.clip(p - K[0], 0, 1) - K[0]) * c[..., 1:2])
def neutral(x):
    a, b, c, d, e, f = 0.2, 0.29, 0.24, 0.272, 0.02, 0.3
    NC = lambda x: ((x * (a * x + c * b) + d * e) / (x * (a * x + b) + d * f)) - e / f
    ws = 1.0 / NC(5.3); return NC(x * ws) * ws
def grade(logc, p):
    x = (logc - 0.4135884) * (p['contrast'] / 100 + 1) + 0.4135884
    x = logc2lin(x)
    x = (LMS2L @ ((L2LMS @ x.T).T * colour_balance(p['temperature'], p['tint'])).T).T
    x = x * hex_raw(p.get('colorFilter', '#FFFFFF'))
    mx = np.array(p.get('mixer', (100, 0, 0, 0, 100, 0, 0, 0, 100)), float) / 100.0   # ChannelMixer: rows R, G, B (fix pass)
    x = np.stack([x @ mx[0:3], x @ mx[3:6], x @ mx[6:9]], -1)
    x = x * gain_v(p['gain']) + lift_v(p['lift'])
    x = np.sign(x) * np.abs(x) ** invgamma_v(p['gamma'])
    x = np.maximum(x, 0)
    hsv = rgb2hsv(x); h = hsv[..., 0] + p.get('hueShift', 0) / 360.0
    hsv[..., 0] = np.where(h < 0, h + 1, np.where(h > 1, h - 1, h)); x = hsv2rgb(hsv)
    lu = x @ np.array([0.2126729, 0.7151522, 0.0721750]); x = lu[..., None] + (p['saturation'] / 100 + 1) * (x - lu[..., None])
    return neutral(np.maximum(x, 0))
def srgb8(v):
    v = np.clip(v, 0, 1); return np.round(np.where(v <= 0.0031308, 12.92 * v, 1.055 * np.power(v, 1 / 2.4) - 0.055) * 255).astype(int)
N = 33; g1 = np.arange(N) / (N - 1)
GRID = np.stack(np.meshgrid(g1, g1, g1, indexing='ij'), -1).reshape(-1, 3)
def lut3d(p): return grade(GRID, p).astype(np.float16).astype(np.float64).reshape(N, N, N, 3)
def sample3d(L, uvw):
    t = np.clip(uvw, 0, 1) * (N - 1); i0 = np.minimum(np.floor(t).astype(int), N - 2); fr = t - i0; out = 0
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                w = (fr[..., 0] if dx else 1 - fr[..., 0]) * (fr[..., 1] if dy else 1 - fr[..., 1]) * (fr[..., 2] if dz else 1 - fr[..., 2])
                out = out + w[..., None] * L[i0[..., 0] + dx, i0[..., 1] + dy, i0[..., 2] + dz]
    return out
def prof(sid):
    p = dict(G['profiles'][sid]['ppv2']); p['colorFilter'] = G['common']['colorFilter']; p['hueShift'] = G['common']['hueShift']; return p
def render(sid, lin):  # engine prediction for scene-linear rgb rows (N,3), no bloom
    p = prof(sid); L = lut3d(p)
    return srgb8(sample3d(L, np.clip(lin2logc(np.asarray(lin) * 2.0 ** p['postExposure']), 0, 1)))

def main():
    global G
    ap = argparse.ArgumentParser(); ap.add_argument('--png')
    ap.add_argument('--grades', default=os.path.join(KIT, 'Tools~', 'inputs', 'grades_engine.json')); a = ap.parse_args()
    G = json.load(open(a.grades, encoding='utf-8'))
    engine_fills = {}
    if '_engine' in G:
        CE = json.load(open(os.path.join(KIT, 'Tools~', 'inputs', 'calib_engine.json'), encoding='utf-8'))
        engine_fills = {(r['scene'], r['element']): r['set_engine'] for r in CE['unlit'] if 'set_engine' in r}
    print('grades:', os.path.basename(a.grades), '(engine numbers + engine fills)' if engine_fills else '(look-definition numbers)')
    ks = np.arange(-6, 5); patch = 0.18 * 2.0 ** ks; P = np.stack([patch] * 3, -1)
    print('1. calib §C test card, PPv2-source Neutral path (33^3 LUT) vs target')
    fails = 0; rows = {}
    for sid in G['profiles']:
        pred = render(sid, P); tgt = np.array([hex8(h) for h in CAL['ramp'][sid]]); d = np.abs(pred - tgt).max(1)
        blk = render(sid, np.zeros((1, 3)))[0]; fails += (d > 3).any(); rows[sid] = (pred, tgt, blk)
        print('   %-4s max %2d codes  per patch %s   black(input 0) %s' % (sid, d.max(), ' '.join('%2d' % v for v in d), '#%02X%02X%02X' % tuple(blk)))
    print('   -> profiles that would FAIL MeasureAll (±3): %d / 15' % fails)
    print('2. calib §B non-blooming unlit targets (xT0 < 0.9)')
    tot = bad = 0; worst = []
    for e in CAL['unlit']:
        if e['xT0'] >= 0.9 or e['scene'] not in G['profiles']: continue
        m = re.match(r'#([0-9A-Fa-f]{6})(?: @ \+?(-?[\d.]+))?', engine_fills.get((e['scene'], e['element']), e['set']).strip())
        if not m: continue
        lin = s2l(hex_raw('#' + m.group(1))) * 2.0 ** float(m.group(2) or 0)
        pred = render(e['scene'], lin[None, :])[0]; d = int(np.abs(pred - hex8(e['display'])).max())
        tot += 1; bad += d > 3; worst.append((d, e['scene'], e['element'], e['display'], '#%02X%02X%02X' % tuple(pred)))
    worst.sort(reverse=True)
    print('   %d targets, %d off by > 3 codes; worst:' % (tot, bad))
    for w in worst[:8]: print('     %-4s %s: target %s -> engine %s (%d)' % (w[1], w[2], w[3], w[4], w[0]))
    print('3. Route C: art/luts/hdr_external/*_HDRext33.cube sampled the way PPv2 External mode does')
    wc = 0
    for sid in G['profiles']:
        fs = glob.glob(os.path.join(ART, 'luts', 'hdr_external', 'Lanbai_%s_*_HDRext33.cube' % sid))
        if not fs: print('   (no cube for %s)' % sid); continue
        v = np.array([[float(t) for t in l.split()] for l in open(fs[0]) if l[:1] in '0123456789-' and len(l.split()) == 3])
        L = v.reshape(N, N, N, 3).transpose(2, 1, 0, 3).astype(np.float16).astype(np.float64)
        pred = srgb8(sample3d(L, np.clip(lin2logc(P), 0, 1))); d = int(np.abs(pred - np.array([hex8(h) for h in CAL['ramp'][sid]])).max()); wc = max(wc, d)
    print('   worst |Route C - §C| over 15 x 11 patches = %d codes' % wc)
    if a.png:
        from PIL import Image, ImageDraw, ImageFont
        F = os.path.join(KIT, '..', '..', '..', 'fonts')
        def font(n, s):
            try: return ImageFont.truetype(os.path.join(F, n), s)
            except Exception: return ImageFont.load_default()
        fT, fS, fM, fL = font('SourceHanSansCN-Medium.otf', 30), font('SourceHanSansCN-Regular.otf', 19), font('IBMPlexMono-Regular.ttf', 14), font('BarlowSemiCondensed-SemiBold.ttf', 24)
        fD = font('SourceHanSansCN-Regular.otf', 15)
        im = Image.new('RGB', (1900, 1720), (18, 20, 24)); d = ImageDraw.Draw(im)
        fixed = bool(engine_fills)
        d.text((50, 34), '蓝白 · §C 目标 vs PPv2 真实 Neutral 通路（按源码独立推算）· ' + ('修正后：套件实际写入的引擎参数 grades_engine' if fixed else '修正前：外观定义参数 grades_final'),
               font=fT, fill=(232, 236, 240))
        d.text((50, 80), '每个 profile 上条 = calib §C 目标（美术模拟器：ACES 工作空间）；下条 = PPv2 3.x 源码的 Neutral 分支（LogC 对比 + 线性 709 的白平衡/LGG/饱和，33³ LUT）。右侧 = 最大误差 / 输入 0 的黑点。', font=fS, fill=(150, 156, 166))
        x0, sw, gap, y = 260, 120, 6, 150
        for sid, (pred, tgt, blk) in rows.items():
            d.text((50, y + 18), sid, font=fL, fill=(232, 236, 240))
            for i in range(11):
                xx = x0 + i * (sw + gap); dd = int(np.abs(pred[i] - tgt[i]).max()); col = (230, 120, 110) if dd > 3 else (120, 128, 138)
                d.rectangle([xx, y, xx + sw, y + 36], fill=tuple(int(v) for v in tgt[i])); d.rectangle([xx, y + 38, xx + sw, y + 74], fill=tuple(int(v) for v in pred[i]))
                d.text((xx + 2, y + 77), '#%02X%02X%02X' % tuple(pred[i]), font=fM, fill=col); d.text((xx + 78, y + 74), 'Δ%d' % dd, font=fD, fill=col)
            mx = int(np.abs(pred - tgt).max())
            d.text((x0 + 11 * (sw + gap) + 10, y + 10), 'max Δ %d' % mx, font=fS, fill=(230, 120, 110) if mx > 3 else (140, 200, 150))
            d.text((x0 + 11 * (sw + gap) + 10, y + 40), '黑点 %s' % ('#%02X%02X%02X' % tuple(blk)), font=fS, fill=(170, 176, 186)); y += 96
        d.text((50, y + 20), '上条 = 目标（圣经：夜间黑点 #02060C 蓝黑，永不压红到 0）；下条 = 引擎里实际会出现的' +
               ('（全部 ≤ 3 码；夜间黑点回到蓝黑，红通道 ≥ 1）。' if fixed else '（夜间黑点 ≈ #000000–#000002）。'), font=fS, fill=(170, 176, 186))
        im.save(a.png); print('wrote', a.png)

if __name__ == '__main__':
    main()
