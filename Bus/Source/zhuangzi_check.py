# -*- coding: utf-8 -*-
"""D-33 #7a：第 8 幕庄子《逍遥游》（971.4 → 989.0）每种语言的字块被车挡掉多少，算上侵蚀。要 ≤ 10%。

从主座位眼位按 0.25° 网格对真车网格打射线；每次碰到东西：
  玻璃  -> 那块玻璃在这个 t 还在就算“看得见”（玻璃不挡），穿过去；
  不透明件 -> 用 Cabin/Tools~/cabin_numpy.py 的 erode_field（和 LanbaiCabinCommon.cginc 1:1，含 D-33 #7a 的门组偏置）
            算这个点在 fade(t)、door_bias(t) 下还在不在；不在就穿过去继续打，还在就算挡住。
立柱（Steel）吃 _FadeResist 0.3，和搭建菜单一致。双面都算（偏保守：Unity 里外壳从里面看是背面，会被剔掉）。
字块的方位 / 仰角读 Fonts/strings_all.json 的 block_table（P08b_Zhuangzi_Xiaoyao）。

    ~/bpy/bin/python Bus/Source/zhuangzi_check.py [--door-bias-off]
"""
import argparse
import json
import os
import sys

import bpy
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(ROOT, 'Cabin', 'Tools~'))
import bus_spec as B  # noqa: E402
import build_bus  # noqa: E402
import cabin_numpy as CN  # noqa: E402


def scene_bvh():
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, owner, mat = [], [], [], []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        me = ob.evaluated_get(dg).to_mesh()
        M = ob.matrix_world
        base = len(verts)
        verts += [tuple(M @ v.co) for v in me.vertices]
        names = [m.name if m else '' for m in me.materials]
        for p in me.polygons:
            polys.append([base + i for i in p.vertices])
            owner.append(ob.name)
            mat.append(names[p.material_index] if p.material_index < len(names) else '')
        ob.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, all_triangles=False), owner, mat


def pane_fade_at(c):
    """LanbaiCabinDriver.PaneThresholds at a unity-space pane centre."""
    x, y, z = c
    hN = min(max((y - 0.62) / 2.00, 0.0), 1.0)
    fN = min(max((z + 3.65) / 7.15, 0.0), 1.0)
    qx, qz = max(abs(x - 0.55) - 0.30, 0.0), max(abs(z - 2.80) - 0.30, 0.0)
    e = np.exp(-np.sqrt(qx * qx + qz * qz + (y - 2.62) ** 2) / 0.8)
    return 0.025 + 0.45 * (1 - hN) + 0.25 * (1 - fN) + 0.35 * (1 - e)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--step', type=float, default=0.25)
    ap.add_argument('--door-bias-off', action='store_true')
    ap.add_argument('--times', default='971.4,976.4,980.0,985.0,989.0')
    a = ap.parse_args()
    build_bus.build()
    bvh, owner, mat = scene_bvh()
    pane_c = {}
    for ob in bpy.data.objects:
        if ob.type == 'MESH' and ob.name.startswith('Glass_'):
            vs = [ob.matrix_world @ v.co for v in ob.data.vertices]
            c = sum(vs, Vector()) / max(len(vs), 1)
            pane_c[ob.name] = (c.x, c.z, c.y)
    S = json.load(open(os.path.join(ROOT, 'Fonts', 'strings_all.json'), encoding='utf-8'))
    blocks = {}
    for b in S['block_table']:
        if b['poem'].startswith('P08b') and b['shown'] not in blocks.values():
            blocks[b['player']] = b
    eye = Vector((B.EYE[0], B.EYE[2], B.EYE[1]))
    res = {}
    for t in [float(v) for v in a.times.split(',')]:
        fade, db = CN.fade(t), (0.0 if a.door_bias_off else CN.door_bias(t))
        for lang, b in blocks.items():
            azs = np.arange(b['az'][0] + a.step / 2, b['az'][1], a.step)
            els = np.arange(b['el'][0] + a.step / 2, b['el'][1], a.step)
            n = blocked = 0
            by = {}
            for el in els:
                for az in azs:
                    d = B.dir_az_el(az, el)
                    dv = Vector((d[0], d[2], d[1]))
                    o = eye.copy()
                    hit_name = None
                    for _ in range(24):
                        h = bvh.ray_cast(o, dv, 60.0)
                        if h[0] is None:
                            break
                        nm, mn = owner[h[2]], mat[h[2]]
                        o = h[0] + dv * 1e-4
                        if nm.startswith('Glass_'):
                            continue                           # glass never blocks (and fades out on its own)
                        p = np.array([h[0].x, h[0].z, h[0].y])
                        resist = 0.30 if 'Steel' in mn else 0.0
                        s = CN.erode_field(p[None], fade, resist=resist, hole_open=CN.hole(t), door_bias=db)[0]
                        if s < 0:
                            continue                           # eroded here: look further
                        hit_name = nm
                        break
                    n += 1
                    if hit_name:
                        blocked += 1
                        by[hit_name] = by.get(hit_name, 0) + 1
            frac = blocked / max(n, 1)
            top = sorted(by.items(), key=lambda kv: -kv[1])[:5]
            res.setdefault(lang, {})['%.1f' % t] = dict(blocked=round(frac, 4), by={k: round(v / n, 4) for k, v in top})
            print('[zhuangzi] t %.1f fade %.3f door %.2f  %-3s az %s el %s  blocked %.1f%%  %s'
                  % (t, fade, db, lang, b['az'], b['el'], 100 * frac, ', '.join('%s %.1f%%' % (k, 100 * v / n) for k, v in top)))
    out = os.path.join(HERE, '..', 'Docs~', 'viewcheck', 'zhuangzi_act8%s.json' % ('_nodoor' if a.door_bias_off else ''))
    json.dump(dict(_about='D-33 #7a: Zhuangzi block occlusion with the act-8 erosion (zhuangzi_check.py)', eye=list(B.EYE),
                   result=res), open(out, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
