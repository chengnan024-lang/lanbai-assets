# -*- coding: utf-8 -*-
"""总导演 10-25：主座位抬头时，天窗开口能看到多少天顶；387 s 起天窗边侵蚀以后，又能看到多少。

水下往上看是“斯涅尔窗”：水面以上的整个天空挤进天顶周围半角 48.6°（arcsin(1/1.333)）的一个圆里。所以量的是
主座位眼位往上、仰角 ≥ 41.4° 那一圈（按立体角加权，cos(仰角)）里有多少是通的：
  - 玻璃（天窗、斜面窗、侧窗）算通（那一块玻璃侵蚀走到之前也是透明的）；
  - 不透明件用 Cabin/Tools~/cabin_numpy.py 的 erode_field（和 LanbaiCabinCommon.cginc 1:1）在 fade(t) 下判断还在不在，
    不在就穿过去接着打（和 zhuangzi_check.py 一样）；立柱吃 _FadeResist 0.3。
分开报：经天窗玻璃看到的、经别的玻璃（斜面窗、侧窗）看到的、经侵蚀出来的洞看到的。
用的是现在这辆车（build_bus.build()），不是阿白截图里的旧车。
D-46（总导演 10-25）：侵蚀场加了“主座位正上方的顶棚先走”这一项（cabin_numpy.zenith_term）；--before 量没加之前的场。

    ~/bpy/bin/python Bus/Source/snell_check.py [--step 1] [--times 380,387,...]
"""
import argparse
import json
import math
import os
import sys

import bpy
import numpy as np
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'Cabin', 'Tools~'))
import bus_spec as B  # noqa: E402
import build_bus  # noqa: E402
import cabin_numpy as CN  # noqa: E402
from zhuangzi_check import scene_bvh  # noqa: E402

SNELL_EL = 90.0 - math.degrees(math.asin(1.0 / 1.333))      # 41.4 deg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--step', type=float, default=1.0)
    ap.add_argument('--times', default='370,375,380,384,387,395,410,430,446,460,500,506,550,600,644.96')
    ap.add_argument('--before', action='store_true', help='the field before D-46 (no zenith term), for comparison')
    a = ap.parse_args()
    build_bus.build()
    bvh, owner, mat = scene_bvh()
    eye = Vector((B.EYE[0], B.EYE[2], B.EYE[1]))
    els = np.arange(SNELL_EL + a.step / 2, 90.0, a.step)
    azs = np.arange(-180.0 + a.step / 2, 180.0, a.step)
    rows = []
    for t in [float(v) for v in a.times.split(',')]:
        fade, hole = CN.fade(t), CN.hole(t)
        tot = 0.0
        acc = dict(skylight=0.0, other_glass=0.0, eroded_hole=0.0, blocked=0.0)
        zen = dict(skylight=0.0, other_glass=0.0, eroded_hole=0.0, blocked=0.0)   # the inner 20 deg round the zenith
        tot_z = 0.0
        by = {}
        for el in els:
            w = math.cos(math.radians(el))
            for az in azs:
                d = B.dir_az_el(az, el)
                dv = Vector((d[0], d[2], d[1]))
                o = eye.copy()
                kind, through_hole, hit_name = None, False, None
                for _ in range(32):
                    h = bvh.ray_cast(o, dv, 60.0)
                    if h[0] is None:
                        break
                    nm, mn = owner[h[2]], mat[h[2]]
                    o = h[0] + dv * 1e-4
                    if nm.startswith('Glass_'):
                        if kind is None:
                            kind = 'skylight' if 'Sky' in nm else 'other_glass'
                        continue
                    p = np.array([h[0].x, h[0].z, h[0].y])
                    resist = 0.30 if 'Steel' in mn else 0.0
                    s = CN.erode_field(p[None], fade, resist=resist, hole_open=hole, zen=None if a.before else CN.ERODE_ZENITH)[0]
                    if s < 0:
                        through_hole = True
                        continue
                    hit_name = nm
                    break
                if hit_name:
                    k = 'blocked'
                    by[hit_name] = by.get(hit_name, 0.0) + w
                elif kind is not None and not through_hole:
                    k = kind
                elif through_hole:
                    k = 'eroded_hole'
                else:
                    k = 'other_glass'          # open air (the door gap) counts with the windows
                acc[k] += w
                tot += w
                if el >= 70.0:
                    zen[k] += w
                    tot_z += w
        frac = {k: round(v / tot, 4) for k, v in acc.items()}
        frac['visible'] = round(1.0 - frac['blocked'], 4)
        zf = {k: round(v / max(tot_z, 1e-9), 4) for k, v in zen.items()}
        zf['visible'] = round(1.0 - zf['blocked'], 4)
        top = sorted(by.items(), key=lambda kv: -kv[1])[:6]
        rows.append(dict(t=t, fade=round(float(fade), 4), snell_cone=frac, zenith_20deg=zf,
                         blocked_by={k: round(v / tot, 4) for k, v in top}))
        print('[snell] t %7.2f fade %.3f  cone visible %5.1f%% (skylight %4.1f, other glass %4.1f, eroded %4.1f)  '
              'zenith<=20deg visible %5.1f%%  blocked by %s'
              % (t, fade, 100 * frac['visible'], 100 * frac['skylight'], 100 * frac['other_glass'], 100 * frac['eroded_hole'],
                 100 * zf['visible'], ', '.join('%s %.1f%%' % (k, 100 * v / tot) for k, v in top[:4])))
    out = os.path.join(HERE, '..', 'Docs~', 'viewcheck', 'snell_hero%s.json' % ('_before_d46' if a.before else ''))
    json.dump(dict(_about='hero eye, the Snell window cone (elevation >= %.1f deg, solid-angle weighted), the current bus, '
                          'with the act erosion fade(t) (snell_check.py)%s' % (SNELL_EL, ', the field BEFORE D-46 (no zenith term)'
                                                                                if a.before else ', D-46 zenith term on'),
                   targets_d46={'387': 'cone >= 25 %', '446': 'cone >= 35 %', '506': 'cone >= 45 %, zenith 20 deg >= 30 %'},
                   eye=list(B.EYE), step_deg=a.step, rows=rows), open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    print('[snell] ->', os.path.normpath(out))


if __name__ == '__main__':
    main()
