# -*- coding: utf-8 -*-
"""鱼鳞屋预览：~/bpy/bin/python kit/preview_house.py [--w 10.2 --h 5.2 --d 7.5] [--seeds 0,1] [--lod 0]
渲到 /tmp/pal/kit_house/<seed>_<shot>_lod<n>.png（正面 / 3/4 / 低处仰看），灰模 + 槽位的大致颜色。"""
import argparse
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(HERE))
import bpy  # noqa: E402

import bl  # noqa: E402
from kit import house  # noqa: E402
from kit.common import UB  # noqa: E402
from kit.preview_que import look, materials, scene_setup  # noqa: E402


def shots(w, h, d):
    tgt = (0, h * 0.75, 0)
    return {
        'front': ((0, 1.7, -d / 2 - 13), 0, 6, 60),
        'q34': ((-w * 0.95, 3.2, -d / 2 - 9),) + look((-w * 0.95, 3.2, -d / 2 - 9), tgt) + (60,),
        'low': ((w * 0.45, 0.25, -d / 2 - 3.2),) + look((w * 0.45, 0.25, -d / 2 - 3.2), (0, h + 0.4, -d / 2 + 0.2)) + (78,),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--w', type=float, default=10.2)
    ap.add_argument('--h', type=float, default=5.2)
    ap.add_argument('--d', type=float, default=7.5)
    ap.add_argument('--seeds', default='0,1')
    ap.add_argument('--lod', type=int, default=0)
    ap.add_argument('--shots', default='front,q34,low')
    ap.add_argument('--res', type=int, default=480)
    ap.add_argument('--spp', type=int, default=16)
    ap.add_argument('--out', default='/tmp/pal/kit_house')
    a = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    os.makedirs(a.out, exist_ok=True)
    for seed in [int(s) for s in a.seeds.split(',')]:
        bl.reset()
        M = materials()
        scene_setup(a.res, a.spp)
        u = house.build(a.w, a.h, a.d, a.lod, seed)
        print('house seed%d lod%d tris %d' % (seed, a.lod, u.tris()))
        u.build('House', materials=M)
        g = UB()
        g.box((-60, -1, -60), (60, 0, 60), 'Rock')
        g.build('Ground', materials=M)
        S = shots(a.w, a.h, a.d)
        for s in a.shots.split(','):
            eye, yaw, pitch, hfov = S[s]
            bpy.context.scene.camera = bl.camera_unity('Cam_' + s, eye, yaw, pitch, hfov)
            bpy.context.scene.render.filepath = os.path.join(a.out, '%d_%s_lod%d.png' % (seed, s, a.lod))
            bpy.ops.render.render(write_still=True)


if __name__ == '__main__':
    main()
