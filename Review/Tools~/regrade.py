# -*- coding: utf-8 -*-
import sys; sys.dont_write_bytecode = True
"""调色复核：场景线性（调色前）图 → PPv2 引擎（Neutral 路径、33^3 LUT、grades_engine.json）+ bloom → sRGB 8 位，
和包交的 PNG 比较。这是 Unity 实际会显示的数学（Grading/verify.md）。
用法: python3 regrade.py SCENE.(exr|npy) --profile S6 [--compare pkg.png] [--out regraded.png]
EXR 需要 OpenEXR 或 imageio[freeimage]（pip install OpenEXR）；npy = float32 (H,W,3) 场景线性。"""
import argparse, json, os, sys, copy
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(ROOT, 'Grading/Tools~/engine'))
sys.path.insert(0, os.path.join(ROOT, 'Art/tools/lens_cine'))
sys.path.insert(0, os.path.join(ROOT, 'Art/tools/bible_work'))
import ppv2_engine as E
import ppv2 as LD
from lutlib_core import patch_ppv2
patch_ppv2(LD)


def load_lin(p):
    if p.endswith('.npy'):
        return np.load(p).astype(np.float64)[..., :3]
    try:
        import OpenEXR, Imath
        f = OpenEXR.InputFile(p)
        dw = f.header()['dataWindow']
        W, H = dw.max.x - dw.min.x + 1, dw.max.y - dw.min.y + 1
        ch = [np.frombuffer(f.channel(c, Imath.PixelType(Imath.PixelType.FLOAT)), np.float32).reshape(H, W) for c in 'RGB']
        return np.stack(ch, -1).astype(np.float64)
    except ImportError:
        import imageio.v3 as iio
        return np.asarray(iio.imread(p), np.float64)[..., :3]


def regrade(lin, sid):
    Gl = json.load(open(os.path.join(ROOT, 'Art/grades_final.json')))
    Ge = json.load(open(os.path.join(ROOT, 'Grading/Tools~/inputs/grades_engine.json')))
    def prof(G):
        p = copy.deepcopy(G['profiles'][sid]['ppv2'])
        p['colorFilter'] = G['common']['colorFilter']; p['hueShift'] = G['common']['hueShift']
        return p
    x = lin + LD.bloom_layer(lin, LD.full(prof(Gl)))
    return E.codes(x, prof(Ge))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('scene'); ap.add_argument('--profile', required=True)
    ap.add_argument('--compare'); ap.add_argument('--out')
    o = ap.parse_args()
    c = regrade(load_lin(o.scene), o.profile)
    img = np.clip(np.round(c), 0, 255).astype(np.uint8)
    if o.out: Image.fromarray(img).save(o.out)
    if o.compare:
        ref = np.asarray(Image.open(o.compare).convert('RGB')).astype(float)
        d = np.abs(ref - c)
        print(json.dumps({'mean_code_diff': round(float(d.mean()), 2), 'p99_code_diff': round(float(np.percentile(d, 99)), 2),
                          'max': round(float(d.max()), 1), 'mean_signed_rgb': [round(float(v), 2) for v in (ref - c).reshape(-1, 3).mean(0)]}, indent=1))
