# -*- coding: utf-8 -*-
"""灰卡校准（README §4）：在参考场景的灯下放 0.5 m 灰卡（albedo #767676 = 0.18，光滑度 0），只开宫殿的烘焙灯，
渲正对灰卡的小图，取中心的场景线性值，过 S7b 调色得到“截图应读到”的 hex。本地烘焙后在同样位置放同样的灰卡截图对照。"""
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402
import numpy as np  # noqa: E402

import bl  # noqa: E402
import palace_layout as L  # noqa: E402
import scene  # noqa: E402
from grade import grade  # noqa: E402

CARDS = {
    # 名字: (灰卡中心, 灰卡朝向（Unity，法线）, 说明)
    'lamp_2m': ((-9.0 + 2.0, 1.62, 54.39), (-1, 0, 0), '右列第 1 盏灯（Lamp_R01）的灯焰旁 2 m、同高、正对灯焰'),
    'lamp_8m': ((-9.0 + 8.0 * 0.0, 1.62 - 0.0, 54.39 + 8.0), (0, 0, -1), 'Lamp_R01 灯焰后方 8 m（+z）、同高、正对灯焰'),
    'avenue_floor': ((-18.0, 0.13, 63.3), (0, 1, 0), '第 1、2 对灯之间的神道正中（铺石面上，朝上）'),
    'door_floor': ((L.AXIS_X, 6.01, L.DOOR_Z - 3.0), (0, 1, 0), '殿门前 3 m 的台基面（朝上）'),
    'stair_foot': ((L.AXIS_X, 0.13, 323.0), (0, 1, 0), '台阶脚下 2 m 的地面（朝上）'),
}


def main():
    bl.reset()
    scene.setup_world()
    w = bpy.context.scene.world
    w.node_tree.nodes['Background'].inputs[1].default_value = 0.0      # 只量灯，不要环境
    scene.add_lights()
    M = bl.principled('grey', (0.18, 0.18, 0.18), 1.0)
    M.node_tree.nodes['Principled BSDF'].inputs['Specular IOR Level'].default_value = 0.0
    res = {}
    for name, (c, n, note) in CARDS.items():
        c, n = np.array(c, float), np.array(n, float) / np.linalg.norm(n)
        a = np.cross(n, [0, 1, 0] if abs(n[1]) < 0.9 else [1, 0, 0])
        a /= np.linalg.norm(a)
        b = np.cross(n, a)
        V = [c + 0.25 * (sa * a + sb * b) for sa, sb in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
        ob = bl.mesh_obj('Card_' + name, [bl.u2b(v) for v in V], [(0, 1, 2, 3)], M)
        cam = bl.camera_unity('C_' + name, c + n * 0.6, math.degrees(math.atan2(-n[0], -n[2])), math.degrees(math.asin(-n[1])), 20)
        sc = bpy.context.scene
        sc.camera = cam
        bl.render_setup(32, 18, 64)
        sc.cycles.use_denoising = False
        p = '/tmp/pal/cal_%s.exr' % name
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        import post
        e = post.read_exr(p)
        lin = e['Combined'][6:12, 12:20, :3].reshape(-1, 3).mean(0)
        code = grade(np.tile(lin, (8, 8, 1)), with_bloom=False)[0, 0]
        res[name] = dict(note=note, centre_unity=[round(float(x), 3) for x in c], normal=[float(x) for x in n],
                         scene_linear=[round(float(x), 5) for x in lin], screen='#%02X%02X%02X' % tuple(int(round(v)) for v in code))
        bpy.data.objects.remove(ob)
    import json
    json.dump(res, open(os.path.join(HERE, '..', 'Docs~', 'calib_cards.json'), 'w'), ensure_ascii=False, indent=1)
    for k, v in res.items():
        print(k, v['screen'], v['scene_linear'])


if __name__ == '__main__':
    main()
