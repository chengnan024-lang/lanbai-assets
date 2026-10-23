# -*- coding: utf-8 -*-
"""车的决定（总导演裁决 D-03）用：圣经里要框进窗的目标，按“从主座位看的方位 / 仰角”摆成发光的小盘子，
天是暗灰、地是更暗的灰（只为看清窗框）。和 lbh_render 的 --bus bible_v2 / local_v1 一起渲，看哪些目标在窗里。
目标表 = FromLocal/shots/s9_2_view_limits/README.md“圣经里的目标落在哪”那一节 + 天窗里的伤口（Gate cameras.U8a）。"""
import math

import bpy

TARGETS = [
    ('月', -12, 8), ('暮日', 0, 0.5), ('唱词 4b', 0, -6), ('天问 / 庄子 11', 0, 8), ('河伯', -25, 6), ('裂口顶 U7', 0, 18),
    ('银心', -30, 12), ('收音机', -20, -12), ('坠入深海', -15, -12), ('里尔克', 20, 3), ('晨日', 45, 6), ('庄子 8-ii', 35, 0),
    ('李白 3/12', 50, -9), ('济慈', 50, -14), ('天窗里的伤口 U8a', 0, 49)]


def build(ctx):
    S = ctx['lbh_scene']
    S.unity_ambient_flat((0.03, 0.032, 0.036))
    eye = ctx['eye']
    me = S.mat_emission('Target', (1.0, 0.55, 0.15), 6.0)
    for i, (name, az, el) in enumerate(TARGETS):
        a, e = math.radians(az), math.radians(el)
        d = (math.cos(e) * math.sin(a), math.sin(e), math.cos(e) * math.cos(a))
        r, R = 60.0, 60.0 * math.tan(math.radians(0.9))
        c = [eye[k] + r * d[k] for k in range(3)]
        # a small disc facing the eye
        up = (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (0.0, 0.0, 1.0)
        rx = (up[1] * d[2] - up[2] * d[1], up[2] * d[0] - up[0] * d[2], up[0] * d[1] - up[1] * d[0])
        n = math.sqrt(sum(x * x for x in rx)); rx = [x / n for x in rx]
        ry = (d[1] * rx[2] - d[2] * rx[1], d[2] * rx[0] - d[0] * rx[2], d[0] * rx[1] - d[1] * rx[0])
        V = [c]
        for k in range(16):
            t = 2 * math.pi * k / 16
            V.append([c[j] + R * (math.cos(t) * rx[j] + math.sin(t) * ry[j]) for j in range(3)])
        F = [(0, 1 + k, 1 + (k + 1) % 16) for k in range(16)]
        S.mesh_object('T_%02d' % i, V, F, me)
    # no ground: several targets are below the horizon (they are in the sky / over the sea in their acts)
    return dict(what='bus decision: framing targets', targets=TARGETS)
