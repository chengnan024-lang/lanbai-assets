# -*- coding: utf-8 -*-
"""D-39 #1：8-ii 庄子靛墨字（#27304A，D-33 #4；S8 下的填值 #333C58，Fonts/README_Fonts）和它背后那片天的对比。
字块：方位 +21.8 … +48.2、仰角 −6.4 … +6.4（L1 正字在上、镜像在下；L3 反过来）。在车门机位的参考帧里取这块天的像素（不含车壳），
和字的屏幕色比：ΔL*（CIELAB）与 Weber 对比 (L_天 − L_字) / L_天（线性亮度）。写 Docs~/ink_contrast.json。"""
import os
import sys
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import act08_ref as R  # noqa: E402
R.POEM_ON = False
import lb_common as C  # noqa: E402

INK = '#27304A'
BLOCK_AZ, BLOCK_EL = (21.8, 48.2), (-6.4, 6.4)


def lum(codes):
    return C.srgb_dec(np.clip(codes, 0, 255) / 255.0) @ C.LUMA


def main():
    out = {}
    ink = C.hex_rgb(INK) * 255.0
    L_ink, _, _ = C.hue_chroma(ink[None])
    Y_ink = float(lum(ink[None])[0])
    for t in (971.4, 976.4, 985.0):
        codes, m, lin = R.render(t, 'door_d12', 960, 'bible_v2')
        V, hh, pix = R.rays(dict(R.CAMS['door_d12']), 960)
        az, el = C.azel_from_dir(V)
        win = R.window_mask(V, t)
        sel = (az >= BLOCK_AZ[0]) & (az <= BLOCK_AZ[1]) & (el >= BLOCK_EL[0]) & (el <= BLOCK_EL[1]) & win
        px = codes.reshape(-1, 3)[sel]
        for name, s in (('upper', el[sel] >= 0), ('lower', el[sel] < 0)):
            q = px[s]
            Ls, _, _ = C.hue_chroma(q)
            Ys = lum(q)
            out['%.1f_%s' % (t, name)] = dict(sky_L_med=round(float(np.median(Ls)), 1), sky_L_p10=round(float(np.percentile(Ls, 10)), 1),
                                              ink_L=round(float(L_ink[0]), 1), dL_med=round(float(np.median(Ls) - L_ink[0]), 1),
                                              dL_min=round(float(np.percentile(Ls, 10) - L_ink[0]), 1),
                                              weber_med=round(float((np.median(Ys) - Y_ink) / np.median(Ys)), 3),
                                              visible_share=round(float(sel.sum()) / float(((az >= BLOCK_AZ[0]) & (az <= BLOCK_AZ[1]) & (el >= BLOCK_EL[0]) & (el <= BLOCK_EL[1])).sum()), 3))
        print(t, {k: v for k, v in out.items() if k.startswith('%.1f' % t)}, flush=True)
    os.makedirs(os.path.join(KIT, 'Docs~'), exist_ok=True)
    json.dump(dict(ink=INK, block_az=BLOCK_AZ, block_el=BLOCK_EL, cam='door_d12', shell='bible_v2 (the door frame blocks part: visible_share)',
                   res=out), open(os.path.join(KIT, 'Docs~', 'ink_contrast.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
