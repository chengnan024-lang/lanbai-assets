# -*- coding: utf-8 -*-
"""第 8 幕变形（956.36 → 964.36）里的日线：每 0.5 s 用天空会话的 CPU 版 Lanbai/Sky（真的 cginc）渲一小块（方位 ±15°、仰角 ±3°，
0.05°/像素），参数按驱动写的：dusk_8i → dusk_8ii 的 ApplyBlend（参数空间，smoothstep 8 s）、`_Udon_SunDir`（+0.5° → 0°，3 s）、
`_Udon_SunDisc.z`（959.36 起 5 s 长到 10°）。每帧在方位 min(+5°, 线半长的一半) 那一列沿仰角找亮线的个数（中间要掉到峰值的 60 % 以下才算两条）。
评审 r1 B1：之前日线和下沉同一条 8 s 曲线，957.5 → 961.5 是两条平行线。
用法：~/bpy/bin/python sun_strip.py  -> Act08_Dusk/Docs~/iterations/02_sun_line_strip.png + Docs~/sun_strip.json"""
import os
import sys
import json
import math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(KIT, 'Source'))
import sky_equirect as SE  # noqa: E402
import lb_common as C  # noqa: E402
import act08_layout as AL  # noqa: E402

LAY = json.load(open(os.path.join(KIT, 'Act08_Layout.json')))
B = LAY['beats']


def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def params(t):
    sk = B['sun_sink']
    el = sk['el'][0] + (sk['el'][1] - sk['el'][0]) * ss((t - sk['t'][0]) / (sk['t'][1] - sk['t'][0]))
    gr = B['sun_line']['grow']
    z = gr[2] * ss((t - gr[0]) / (gr[1] - gr[0]))
    w = ss((t - B['F10e']) / 8.0)
    return w, el, z


def patch(t, W=600, H=120):
    w, el, z = params(t)
    cwd = os.getcwd()
    os.chdir(os.path.join(REPO, 'Sky', 'Tools~', 'render'))
    try:
        import make_presets as MP
        import sky_cpu as S
    finally:
        os.chdir(cwd)
    pa, pb = MP.P['dusk_8i'], MP.P['dusk_8ii']
    S.renderer().tex.clear()
    S.set_cube('_CubeA', S.load_hdr(pa['hdri_file']))
    ga, gb = dict(pa['globals']), dict(pb['globals'])
    if pa.get('fog_from_sky'):
        ga.update(MP.fog_group(pa))
    if pb.get('fog_from_sky'):
        gb.update(MP.fog_group(pb))
    ga.setdefault('_Udon_SkyBlend', [0.0, 0.0, 0.0, 1.0])
    globs = SE._lerp_dict(ga, gb, w)
    e = math.radians(el)
    globs['_Udon_SunDir'] = [0.0, math.sin(e), math.cos(e), 1.0]
    globs['_Udon_SunDisc'] = [1.0, 0.265, z, 1.0]
    mat = SE._lerp_dict(pa['material'], pb['material'], w)
    az = (np.arange(W) + 0.5) / W * 30.0 - 15.0
    elv = 3.0 - (np.arange(H) + 0.5) / H * 6.0
    A, E = np.meshgrid(np.radians(az), np.radians(elv))
    d = np.stack([np.cos(E) * np.sin(A), np.sin(E), np.cos(E) * np.cos(A)], -1).reshape(-1, 3).astype(np.float32)
    img = np.asarray(S.render(d, mat, globs)).reshape(H, W, 3)
    return img, (w, el, z), az, elv


def count_lines(lin, az, elv, at=5.0):
    col = int(np.argmin(np.abs(az - at)))
    Y = lin[:, col] @ C.LUMA
    pk = Y.max()
    if pk <= 0:
        return 0
    above = Y > 0.6 * pk
    runs = int(np.sum(above[1:] & ~above[:-1]) + (1 if above[0] else 0))
    return runs


def main():
    ts = np.arange(956.5, 964.51, 0.5)
    rows, res = [], {}
    for t in ts:
        lin, (w, el, z), az, elv = patch(float(t))
        codes = np.clip(C.grade(lin, 'S8', bloom=False), 0, 255).astype(np.uint8)
        n = count_lines(lin, az, elv, at=min(5.0, 0.5 * z)) if z > 0.3 else None
        res['%.1f' % t] = dict(w_other=round(w, 3), sun_el=round(el, 3), line_half_len=round(z, 2), lines_at_az5=n)
        print('%.1f' % t, res['%.1f' % t], flush=True)
        rows.append(codes)
    sheet = np.concatenate([np.concatenate([r, np.full((4, r.shape[1], 3), 20, np.uint8)], 0) for r in rows], 0)
    os.makedirs(os.path.join(KIT, 'Docs~', 'iterations'), exist_ok=True)
    Image.fromarray(sheet).save(os.path.join(KIT, 'Docs~', 'iterations', '02_sun_line_strip.png'))
    json.dump(dict(note='each row = one frame (az -15..15, el +3..-3); lines counted at az min(5, half the line) (None = no line yet)', frames=res),
              open(os.path.join(KIT, 'Docs~', 'sun_strip.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
