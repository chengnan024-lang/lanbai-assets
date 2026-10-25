# -*- coding: utf-8 -*-
"""标准台自检：~/bpy/bin/python Engineering/render_harness/selftest.py [--render]
1 引擎：S10 下 0.18 灰 → #767676 / #777777（圣经 §1.4）；S4 的 bloom T0 = 2.124（grades_engine.json）
2 bloom：低于 T0 的画面加不了 bloom；单个亮点的 bloom 重心不偏（没有半像素错位）
3 量法：本地的 U7 Unity 截图 → APL 35.1、亮度<12 24.8%、L*>85 0.65%、最亮 2000 px 外框 (970,365)-(1003,461)
4 （--render）示例场景渲一张 480×270，整条链跑通"""
import os
import subprocess
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import numpy as np  # noqa: E402
from PIL import Image  # noqa: E402

from lbh import grade as G, measure as M, paths  # noqa: E402

ok = True


def check(name, cond, info=''):
    global ok
    ok &= bool(cond)
    print(('PASS ' if cond else 'FAIL ') + name + ('  ' + str(info) if info else ''))


hx = G.E.screen_hex([0.18] * 3, {})
check('engine S10 0.18 -> #767676/#777777', hx in ('#767676', '#777777'), hx)
st = G.state_for('S4')
T0 = G.gamma_to_linear_space(st['bloom']['threshold']) * (1 - st['bloom']['softKnee'])
check('S4 bloom T0 = 2.124', abs(T0 - 2.124) < 0.01, round(T0, 3))
img = np.full((270, 480, 3), 1.5)
b = G.bloom_pyramid(img, st['bloom'])
check('no bloom below T0', float(b.max()) == 0.0, float(b.max()))
img = np.zeros((270, 480, 3))
img[133:137, 238:242] = 500.0          # a 4x4 block centred on (135, 240) in pixel-centre coordinates (134.5+..)
b = G.bloom_pyramid(img, st['bloom'])[..., 1]
yy, xx = np.mgrid[0:b.shape[0], 0:b.shape[1]]
cy, cx = (b * yy).sum() / b.sum(), (b * xx).sum() / b.sum()
check('bloom of a block stays centred (<= 0.25 px)', abs(cy - 134.5) <= 0.25 and abs(cx - 239.5) <= 0.25, (round(cy, 2), round(cx, 2)))
u7 = os.path.join(paths.REPO, 'FromLocal', 'gate_test', 'U7_unity_t155.10.png')
if os.path.exists(u7):
    m = M.measure(np.asarray(Image.open(u7).convert('RGB')))
    check('U7 Unity APL 35.1', abs(m['APL'] - 35.1) < 0.06, m['APL'])
    check('U7 luma<12 24.8%', abs(m['luma_lt12_pct'] - 24.8) < 0.06, m['luma_lt12_pct'])
    check('U7 L*>85 0.65%', abs(m['Lstar_gt85_pct'] - 0.65) < 0.006, m['Lstar_gt85_pct'])
    check('U7 brightest bbox', m['brightest']['bbox'] == [970, 365, 1003, 461], m['brightest']['bbox'])
if '--render' in sys.argv:
    out = '/tmp/lbh_selftest'
    r = subprocess.run([sys.executable, os.path.join(HERE, 'lbh_render.py'), '--scene', os.path.join(HERE, 'examples', 'demo_moon_sea.py'),
                        '--cam', 'hero', '--grade', 'S3', '--act', '03', '--t', '140', '--res', '480x270', '--samples', '16', '--out', out],
                       capture_output=True, text=True)
    check('demo render chain', r.returncode == 0 and os.path.exists(os.path.join(out, 'metrics.json')), r.stderr[-300:])
print('ALL PASS' if ok else 'SOME FAILED')
sys.exit(0 if ok else 1)
