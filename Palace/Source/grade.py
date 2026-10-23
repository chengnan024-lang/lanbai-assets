# -*- coding: utf-8 -*-
"""S7b 的 PPv2 模拟（引擎版参数 Grading/Tools~/inputs/grades_engine.json + 圣经的 bloom），以及屏幕目标 → 填值的反解。
输入一律是场景线性（Unity 的 HDR 相机缓冲）。"""
import copy
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Grading', 'Tools~', 'engine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'lens_cine'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'bible_work'))
import ppv2_engine as E  # noqa: E402
import ppv2 as LD  # noqa: E402
from lutlib_core import patch_ppv2  # noqa: E402
patch_ppv2(LD)

_G = json.load(open(os.path.join(REPO, 'Grading', 'Tools~', 'inputs', 'grades_engine.json')))


def profile(sid='S7b'):
    p = copy.deepcopy(_G['profiles'][sid]['ppv2'])
    p['colorFilter'] = _G['common']['colorFilter']
    p['hueShift'] = _G['common']['hueShift']
    return p


P7B = profile('S7b')
_LUT = None


def lut():
    global _LUT
    if _LUT is None:
        _LUT = E.bake_lut(P7B)
    return _LUT


def bloom(img, p=P7B):
    pb = LD.full({'bloom': dict(p['bloom'], clamp=4.24)})
    return LD.bloom_layer(img.astype(np.float64), pb)


def grade(img, p=P7B, with_bloom=True):
    """场景线性 (H, W, 3) → 显示码 0..255（float）。"""
    x = img.astype(np.float64)
    if with_bloom:
        x = x + bloom(x, p)
    return E.codes(x, p, lut() if p is P7B else None)


def srgb_to_lin(h):
    h = h.lstrip('#')
    c = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def screen_of_lin(lin, p=P7B):
    return E.codes(np.asarray(lin, float).reshape(1, 1, 3), p)[0, 0]


def solve_fill(screen_hex, p=P7B, iters=60):
    """要在屏幕上读到 screen_hex，场景线性要填多少（逐通道迭代反解）。"""
    tgt = srgb_to_lin(screen_hex) * 255.0
    tgt_codes = np.array([int(screen_hex.lstrip('#')[i:i + 2], 16) for i in (0, 2, 4)], float)
    x = srgb_to_lin(screen_hex).copy() + 1e-4
    for _ in range(iters):
        c = screen_of_lin(x, p)
        x = np.maximum(x * np.clip(((tgt_codes + 0.5) / (c + 0.5)) ** 1.6, 0.5, 2.0), 1e-6)
    return x, screen_of_lin(x, p)


def lin_to_hex(lin):
    c = np.clip(np.asarray(lin, float), 0, 1)
    s = np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
    return '#%02X%02X%02X' % tuple(int(round(v * 255)) for v in s)


if __name__ == '__main__':
    for h in ['#04121E', '#02070F', '#06202C', '#010407', '#26496C', '#B52A1E', '#FFC46A', '#2A557B', '#7A4A6E', '#D8CFE0']:
        x, c = solve_fill(h)
        print(h, '-> fill lin', np.round(x, 5), lin_to_hex(x), 'reads', np.round(c, 1))
