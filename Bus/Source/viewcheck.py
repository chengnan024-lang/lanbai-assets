# -*- coding: utf-8 -*-
"""视窗验证：从眼位按 0.5° 网格打射线（和本地 s9_2_view_limits 的量法一样），记第一个碰到的是哪块玻璃 / 不透明件；
再对 15 个取景目标各打一束（中心 + 半径 0.9° 的 8 条），全部穿过玻璃或什么都不碰 = 看得见。

    ~/bpy/bin/python Bus/Source/viewcheck.py --out Bus/Docs~/viewcheck [--eye 0.55,1.70,2.05] [--name hero]
输出：<name>_map.png（方位 −180..180 × 仰角 −60..80 的视窗图）、<name>_targets.json、<name>_windows.json
"""
import argparse
import json
import math
import os
import sys

import bpy  # noqa: F401
import numpy as np
from mathutils import Vector
from mathutils.bvhtree import BVHTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import build_bus  # noqa: E402
import bus_spec as B  # noqa: E402

FONT = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Fonts', 'Originals~', 'SourceHanSerifCN-Medium.otf')


def scene_bvh():
    """one BVH over every mesh; a polygon -> object-name table so we know what was hit."""
    import bmesh
    dg = bpy.context.evaluated_depsgraph_get()
    verts, polys, owner = [], [], []
    for ob in bpy.data.objects:
        if ob.type != 'MESH':
            continue
        me = ob.evaluated_get(dg).to_mesh()
        M = ob.matrix_world
        base = len(verts)
        verts += [tuple(M @ v.co) for v in me.vertices]
        for p in me.polygons:
            polys.append([base + i for i in p.vertices])
            owner.append(ob.name)
        ob.evaluated_get(dg).to_mesh_clear()
    return BVHTree.FromPolygons(verts, polys, all_triangles=False), owner


def classify(name):
    if name.startswith('Glass_'):
        return name[6:]
    return None


def cast(bvh, owner, eye_b, d_b, maxd=40.0):
    """walk through glass; return (list of glass names passed, opaque hit name or None)."""
    passed = []
    o = Vector(eye_b)
    d = Vector(d_b)
    for _ in range(8):
        hit = bvh.ray_cast(o, d, maxd)
        if hit[0] is None:
            return passed, None
        nm = owner[hit[2]]
        g = classify(nm)
        if g is None:
            return passed, nm
        passed.append(g)
        o = hit[0] + d * 1e-4
    return passed, None


def U2B(p):
    return (p[0], p[2], p[1])


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', required=True)
    ap.add_argument('--eye', default=','.join(str(v) for v in B.EYE))
    ap.add_argument('--name', default='hero')
    ap.add_argument('--step', type=float, default=0.5)
    ap.add_argument('--no-build', action='store_true')
    a = ap.parse_args()
    eye = tuple(float(v) for v in a.eye.split(','))
    if not a.no_build:
        build_bus.build()
    bvh, owner = scene_bvh()
    eb = U2B(eye)
    os.makedirs(a.out, exist_ok=True)
    # ---- the grid
    azs = np.arange(-180, 180 + 1e-6, a.step)
    els = np.arange(80, -60 - 1e-6, -a.step)
    labels = {}
    grid = np.zeros((len(els), len(azs)), np.int32)          # 0 = opaque, -1 = open air, k>0 = window k
    for i, el in enumerate(els):
        for j, az in enumerate(azs):
            d = B.dir_az_el(az, el)
            passed, opq = cast(bvh, owner, eb, U2B(d))
            if opq is not None:
                grid[i, j] = 0
            elif passed:
                k = labels.setdefault(passed[0], len(labels) + 1)
                grid[i, j] = k
            else:
                grid[i, j] = -1
    # window extents
    win = {}
    for nm, k in labels.items():
        ii, jj = np.nonzero(grid == k)
        win[nm] = dict(az=[float(azs[jj].min()), float(azs[jj].max())], el=[float(els[ii].min()), float(els[ii].max())],
                       solid_angle_cells=int(len(ii)))
    ii, jj = np.nonzero(grid == -1)
    if len(ii):
        win['(open: door / nothing)'] = dict(az=[float(azs[jj].min()), float(azs[jj].max())], el=[float(els[ii].min()), float(els[ii].max())], solid_angle_cells=int(len(ii)))
    json.dump(win, open(os.path.join(a.out, a.name + '_windows.json'), 'w'), ensure_ascii=False, indent=1)
    # ---- the targets
    res = {}
    for nm, az0, el0 in B.TARGETS:
        az0, el0 = B.TARGETS_MOVED.get(nm, (az0, el0))
        if nm == '收音机':
            # the radio is a thing in the cabin: visible = the ray toward (az, el) hits the radio itself, unobstructed
            passed, opq = cast(bvh, owner, eb, U2B(B.dir_az_el(az0, el0)))
            res[nm] = dict(az=az0, el=el0, visible=bool(opq and opq.startswith('Radio')), hit=opq)
            continue
        ok, hits = True, []
        for k in range(9):
            if k == 0:
                da, de = 0.0, 0.0
            else:
                t = 2 * math.pi * (k - 1) / 8
                da = B.TARGET_RADIUS_DEG * math.cos(t) / max(0.2, math.cos(math.radians(el0)))
                de = B.TARGET_RADIUS_DEG * math.sin(t)
            passed, opq = cast(bvh, owner, eb, U2B(B.dir_az_el(az0 + da, el0 + de)))
            if opq is not None:
                ok = False
                hits.append(opq)
            else:
                hits.append(passed[0] if passed else 'open')
        res[nm] = dict(az=az0, el=el0, visible=ok, through=sorted(set(hits)))
    json.dump(res, open(os.path.join(a.out, a.name + '_targets.json'), 'w'), ensure_ascii=False, indent=1)
    nvis = sum(1 for r in res.values() if r['visible'])
    print('[viewcheck] %s eye %s: %d / %d targets visible' % (a.name, eye, nvis, len(res)))
    for nm, r in res.items():
        print('   %-14s %+6.1f %+6.1f  %s  %s' % (nm, r['az'], r['el'], 'OK ' if r['visible'] else 'XX ', r.get('through', r.get('hit'))))
    for nm, w in sorted(win.items(), key=lambda kv: kv[1]['az'][0]):
        print('   window %-22s az %+7.1f..%+7.1f  el %+6.1f..%+6.1f' % (nm, w['az'][0], w['az'][1], w['el'][0], w['el'][1]))
    # ---- the picture
    from PIL import Image, ImageDraw, ImageFont
    sc = 4
    H, W = grid.shape
    img = np.zeros((H, W, 3), np.uint8)
    img[grid == 0] = (46, 46, 52)
    img[grid == -1] = (190, 205, 225)
    pal = [(120, 170, 220), (100, 150, 205), (140, 190, 230), (90, 140, 190), (160, 200, 235), (110, 160, 210)]
    for nm, k in labels.items():
        img[grid == k] = pal[k % len(pal)]
    im = Image.fromarray(img).resize((W * sc, H * sc), Image.NEAREST)
    dr = ImageDraw.Draw(im)
    try:
        f = ImageFont.truetype(FONT, 20)
        fs = ImageFont.truetype(FONT, 15)
    except Exception:
        f = fs = ImageFont.load_default()

    def px(az, el):
        return ((az + 180) / a.step * sc, (80 - el) / a.step * sc)
    for az in range(-180, 181, 30):
        x, _ = px(az, 0)
        dr.line([(x, 0), (x, H * sc)], fill=(70, 70, 80), width=1)
        dr.text((x + 3, H * sc - 22), '%+d°' % az, fill=(230, 230, 230), font=fs)
    for el in range(-60, 81, 20):
        _, y = px(0, el)
        dr.line([(0, y), (W * sc, y)], fill=(70, 70, 80), width=1)
        dr.text((3, y + 2), '%+d°' % el, fill=(230, 230, 230), font=fs)
    for nm, r in res.items():
        x, y = px(r['az'], r['el'])
        rr = B.TARGET_RADIUS_DEG / a.step * sc
        col = (60, 220, 90) if r['visible'] else (235, 60, 50)
        dr.ellipse([x - rr, y - rr, x + rr, y + rr], outline=col, width=3)
        dr.text((x + rr + 3, y - 10), nm, fill=col, font=fs)
    for nm, w in win.items():
        x, y = px((w['az'][0] + w['az'][1]) / 2, w['el'][1])
        dr.text((x - 30, y + 4), nm, fill=(20, 30, 50), font=fs)
    dr.text((10, 8), '%s · 眼位 (%.2f, %.2f, %.2f) · %d / %d 个目标看得见（绿）' % (a.name, *eye, nvis, len(res)), fill=(255, 255, 255), font=f)
    im.save(os.path.join(a.out, a.name + '_map.png'))


if __name__ == '__main__':
    main()
