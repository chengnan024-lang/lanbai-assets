# -*- coding: utf-8 -*-
"""D-42 #1：近层卡逆光那一面压到圣经暮的云影 #363D59（金边留着）。只动近层的天光 / 地光（NEAR_AMB，按组 upper / lower）。
在 971.4（8-ii 落定）的正前帧上量（含雾封顶 0.06、调色、bloom）：近层卡不透明（覆盖 > 0.97）的像素里去掉最亮的 20 %（金边），
取中位色，和 #363D59 比 Lab 距离；同时量近层卡边一圈的 D-21 紫，不许比 NEAR_AMB = 1 时多。写 Docs~/near_shadow.json。
用法：~/bpy/bin/python act08_shadow.py [--check 'u0,u1,u2;l0,l1,l2']（试值）"""
import os
import sys
import json
import numpy as np
from scipy.ndimage import binary_dilation

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import act08_ref as R  # noqa: E402
R.POEM_ON = False
import lb_common as C  # noqa: E402

T, CAM, W = 971.4, 'hero', 480
TARGET = '#363D59'


def lab(codes):
    return np.array(C.lab_of_codes(np.asarray(codes, float))).ravel()


def measure(amb_u, amb_l):
    R.AMB_OVERRIDE.clear()
    R.AMB_OVERRIDE.update(upper=list(amb_u), lower=list(amb_l))
    R.COVER.clear()
    codes, m, lin = R.render(T, CAM, W, 'bible_v2', None, '', None)
    hh, ww = codes.shape[:2]
    near = np.maximum(R.COVER.get('L:near', 0), R.COVER.get('L:near-right', 0)).reshape(hh, ww)
    grp_u = R.COVER.get('upper', np.zeros(hh * ww)).reshape(hh, ww)
    out = {}
    px = codes.reshape(hh, ww, 3).astype(float)
    for g, sel in (('upper', grp_u > 0.5), ('lower', grp_u <= 0.5)):
        body = (near > 0.97) & sel
        if body.sum() < 20:
            continue
        p = px[body]
        L = p @ C.LUMA
        p = p[L <= np.percentile(L, 80)]
        med = np.median(p, 0)
        out[g] = dict(hex=C.to_hex(med),
                      dE=float(np.linalg.norm(lab(med) - lab(C.hex_rgb(TARGET) * 255))), hC=[round(float(v), 1) for v in np.ravel(C.hue_chroma(med)[1:])])
    # D-21 around the near cards (body + soft edge + 3 px): purple pixels as a share of the whole frame
    zone = binary_dilation(near > 0.02, iterations=3)
    Lp, hp, cp = C.hue_chroma(px[zone])
    out['edge_purple'] = float(((hp >= 290) & (hp <= 330) & (cp > 8) & (Lp > 40)).sum()) / (hh * ww)
    out['frame_purple'] = m['purple_D21']
    out['APL'] = m['APL']
    return out


def main():
    if '--check' in sys.argv:
        u, l = [list(map(float, s.split(','))) for s in sys.argv[sys.argv.index('--check') + 1].split(';')]
        print(json.dumps(measure(u, l), ensure_ascii=False))
        return
    near = {c['group']: c['amb'] for c in R.LAYOUT['cards'] if c.get('amb')}
    res = dict(target=TARGET, t=T, cam=CAM, width=W, near_amb=near,
               fog_cap_near=[c['fog_cap'] for c in R.LAYOUT['cards'] if c.get('amb')][0],
               amb_1=measure([1, 1, 1], [1, 1, 1]), chosen=measure(near['upper'], near['lower']),
               before_r2=dict(note='fog cap 0.06, NEAR_AMB 1 (08afa9a)', upper='#6E4B5A', lower='#5A4051', frame_purple=0.0017),
               why=('the bloom (PPv2 engine, the sun line and the pink band) and the 6 % pink fog add a warm floor the sky light '
                    'cannot scale away: an even x0.6 goes RED (#653C44); a blue-only push goes PURPLE (#5F3A63). Fog cap 0 on the near '
                    'layer + a red-cut sky light lands on #363D59 (dE 4) with less D-21 purple than before'))
    print(json.dumps(res, ensure_ascii=False, indent=1))
    json.dump(res, open(os.path.join(KIT, 'Docs~', 'near_shadow.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
