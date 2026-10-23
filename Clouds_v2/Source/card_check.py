# -*- coding: utf-8 -*-
"""量一张 v2 云卡：叠在它自己的天上（卡片所朝方向、仰角 0–25° 的目标天）按该幕调色显示，量
阴影体（alpha > 0.95 的像素里亮度 10–30 百分位的中位）、受光顶（98 百分位）、紫 / 薰衣草占比、线性最大值。
用法：python card_check.py <name> [...]   （读 $LB_WORK/<name>_lin.npz 与 Textures/<name>.json 或 --dir）"""
import os
import sys
import json
import argparse
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lb_common as C  # noqa: E402

WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')
TARGET = {'dawn': dict(shadow='#8593AA', top='#F6DCC4', grade='S6', sun_az=45.0),
          'dusk': dict(shadow='#363D59', top='#F0A878', grade='S8', sun_az=0.0)}


def sky_backdrop(preset, view_az, h, w, el_top=24.0, el_bot=-6.0, hfov=60.0):
    sky = C.read_hdr(os.path.join(HERE, 'sky', f'{preset}_target_1k.hdr'))
    el = np.linspace(el_top, el_bot, h)
    az = view_az + np.linspace(-hfov / 2, hfov / 2, w)
    A, E_ = np.meshgrid(az, el)
    return C.sample_equirect(sky, C.dir_from_azel(A, E_), 0.0)


def check(name, info_dir, out_png=None):
    z = np.load(os.path.join(WORK, f'{name}_lin.npz'))
    lin, a = z['lin'].astype(np.float64), z['a'].astype(np.float64)
    info = json.load(open(os.path.join(info_dir, name + '.json')))
    T = TARGET[info['preset']]
    h, w = a.shape
    bg = sky_backdrop(info['preset'], T['sun_az'] - info['sun_rel_az'], h, w)
    comp = lin * a[..., None] + bg * (1 - a[..., None])
    codes = C.grade(comp, T['grade'], bloom=True)
    body = a > 0.95
    lum = (lin @ C.LUMA)
    r = dict(name=name)
    if body.sum() > 50:
        lb = lum[body]
        lo, hi = np.percentile(lb, [10, 30])
        sel = body & (lum >= lo) & (lum <= hi)
        sh = np.median(codes[sel], 0)
        top_sel = body & (lum >= np.percentile(lb, 98))
        tp = np.median(codes[top_sel], 0)
        Ls, hs, cs = C.hue_chroma(sh)
        Lt, ht, ct = C.hue_chroma(tp)
        Lall, hall, call = C.hue_chroma(codes[a > 0.5])
        purple = float(((hall >= 285) & (hall <= 330) & (call > 12)).mean())
        r.update(shadow=C.to_hex(sh), shadow_hC=[round(float(hs)), round(float(cs), 1)], shadow_target=T['shadow'],
                 shadow_err=float(np.abs(sh - C.hex_rgb(T['shadow']) * 255).max()),
                 top=C.to_hex(tp), top_hC=[round(float(ht)), round(float(ct), 1)], top_target=T['top'],
                 lavender_frac_cloud=round(purple, 4), lin_max=float(lin[a > 0.5].max()),
                 lin_p999=float(np.percentile(lin[a > 0.5].max(-1), 99.9)),
                 clipped_frac=float((lin[a > 0.05].max(-1) >= 2.0 ** 2.5 * 0.999).mean()))
    if out_png:
        Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(out_png)
    return r


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('names', nargs='+')
    ap.add_argument('--dir', default=os.path.join(HERE, '..', 'Textures'))
    ap.add_argument('--png', default=None)
    a = ap.parse_args()
    for n in a.names:
        r = check(n, a.dir, (os.path.join(a.png, n + '_graded.png') if a.png else None))
        print(json.dumps(r, ensure_ascii=False))
