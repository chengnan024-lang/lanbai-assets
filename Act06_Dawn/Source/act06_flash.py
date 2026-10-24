# -*- coding: utf-8 -*-
"""剪 1 的黑 → 晨（252.64 → 266.4）的爬升律 / 闪烁核查（圣经 §1.8、E2 / E17；D-09）。
每个机位：先渲 266.34 的晨（act06_ref，静态：这 14 秒里车只下降 ~50 m，画面几乎不变），再按 Lanbai_Overlay v2 的数学
（Overlay/Tools~/overlay_model.py：一条按最亮视向建的 EvOverlayAlpha 曲线、按方向错开起点）逐帧盖上遮罩，填色 = S6 行
#090200，按 S6 调色（含 bloom）写成 60 fps 的 PNG 序列，再跑圣经的 lens_tech/flashcheck.py。
另外直接算每个视向的全画面 EV 爬升（0.25 / 1 / 2 秒窗，限 0.5 / 1.0 / 1.8 EV）。
用法：~/bpy/bin/python act06_flash.py [--w 320] [--views hero door_d12 hero_skylight vr_door_d12]"""
import os
import sys
import json
import math
import argparse
import subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'Overlay', 'Tools~'))
import act06_ref as R  # noqa: E402
import lb_common as C  # noqa: E402
import overlay_model as OM  # noqa: E402

LAYOUT = R.LAYOUT
B = LAYOUT['beats']
FILL = C.hex_lin('#090200')
L_BLACK, L_DAWN = 0.0013, (210 / 255.0) ** 2.2
SUN = np.array(LAYOUT['sun']['dir'])
LOBES = [(0.0, 1.0, 0.0, 40.0), (0.0, -1.0, 0.0, 60.0), (SUN[0], 0.0, SUN[2], 30.0)]
LEADS = [0.0, 2.2, 3.3]
LEAD_ELSE, SOFT, T_CURVE = 2.0, 30.0, 8.65


def overlay_alpha(V, t):
    t_pre, t_dawn = B['preroll_t0'], B['dawn_t0']
    if t < t_pre:
        return np.ones(len(V))
    a0 = float(OM.ev_overlay_alpha(np.array(0.0), L_BLACK, L_DAWN, L_DAWN, L_BLACK))
    if t < t_dawn:
        x = (t - t_pre) / (t_dawn - t_pre)
        return np.full(len(V), 1.0 + (a0 - 1.0) * x)
    return OM.alpha(V, t - t_dawn, T_CURVE, (L_BLACK, L_DAWN, L_DAWN, L_BLACK), LOBES, LEADS, LEAD_ELSE, SOFT)


def law(ts, Lmean):
    ev = np.log2(np.maximum(Lmean, 0.004))
    out = {}
    fps = 1.0 / (ts[1] - ts[0])
    for win, lim in ((0.25, 0.5), (1.0, 1.0), (2.0, 1.8)):
        n = int(round(win * fps))
        d = ev[n:] - ev[:-n]
        out['%.2fs' % win] = [round(float(d.max()), 3), lim]
    out['pass'] = all(v[0] <= v[1] for k, v in out.items() if k != 'pass')
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--w', type=int, default=320)
    ap.add_argument('--views', nargs='+', default=['hero', 'door_d12', 'hero_skylight', 'vr_door_d12'])
    ap.add_argument('--fps', type=float, default=60.0)
    ap.add_argument('--out', default='/tmp/lb/flash')
    ap.add_argument('--flashcheck', action='store_true')
    a = ap.parse_args()
    res = {}
    for view in a.views:
        codes0, m0, lin = R.render(266.34, view, a.w, 'd12')
        h, w, _ = lin.shape
        V, _, _ = R.rays(dict(R.CAMS[view]), a.w)
        ts = np.arange(B['preroll_t0'] - 0.5, B['dawn_t1'] + 1.0, 1.0 / a.fps)
        Lm = []
        fdir = os.path.join(a.out, view)
        os.makedirs(fdir, exist_ok=True)
        for i, t in enumerate(ts):
            al = overlay_alpha(V, t).reshape(h, w, 1)
            img = lin * (1 - al) + FILL * al
            codes = C.grade(img, 'S6', bloom=True)
            Lm.append(float(C.srgb_dec(np.clip(codes, 0, 255) / 255.0).mean(axis=(0, 1)) @ C.LUMA))
            if a.flashcheck:
                Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(os.path.join(fdir, 'f%05d.png' % i))
        r = dict(law=law(ts, np.array(Lm)), apl_end=m0['APL'])
        if a.flashcheck:
            fc = os.path.join(REPO, 'Art', 'tools', 'lens_tech', 'flashcheck.py')
            p = subprocess.run([sys.executable, fc, fdir, '--fps', str(a.fps), '--hfov', str(R.CAMS[view]['hfov_deg']),
                                '--out', os.path.join(a.out, view + '_report')], capture_output=True, text=True)
            r['flashcheck_tail'] = (p.stdout + p.stderr).strip().splitlines()[-6:]
        res[view] = r
        print(view, json.dumps(r, ensure_ascii=False))
    os.makedirs(os.path.join(KIT, 'Docs~'), exist_ok=True)
    json.dump(res, open(os.path.join(KIT, 'Docs~', 'flash_dawn.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
