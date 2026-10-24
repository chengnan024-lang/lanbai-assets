# -*- coding: utf-8 -*-
"""第 8 幕的爬升律 / 闪烁核查（圣经 §1.8、E2 / E17；D-09）：直接逐帧渲 act08_ref（含驱动报的 ΔEV、S7b → S8 → S8b 调色），三段：
  exit     922.36 → 936.0（之前是第 7 幕的画面）  出海：钉住 → EV 线性放开 → F9 +0.5 EV → 4 s 回 0（圣经仿真 0.39 / 0.66 / 1.00 EV）
  dissolve 955.0 → 968.0   天花溶化（每像素 5 s EV 线性）、另一片天淡入
  f12      986.0 → 1002.0  日线收缩、蓝时（变暗免费）
每段量全画面 EV 的 0.25 / 1 / 2 秒窗最大爬升（限 0.5 / 1.0 / 1.8），再跑圣经的 lens_tech/flashcheck.py。
用法：~/bpy/bin/python act08_flash.py [--seg exit dissolve f12] [--w 160] [--fps 10] [--views hero door_d12 hero_up]"""
import os
import sys
import json
import argparse
import subprocess
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
sys.path.insert(0, HERE)
import act08_ref as R  # noqa: E402
import lb_common as C  # noqa: E402

SEGS = dict(exit=(922.36, 936.0), dissolve=(955.0, 968.0), f12=(986.0, 1002.0))


def law(ts, Lmean):
    ev = np.log2(np.maximum(Lmean, 0.004))
    out = {}
    fps = 1.0 / (ts[1] - ts[0])
    for win, lim in ((0.25, 0.5), (1.0, 1.0), (2.0, 1.8)):
        n = max(1, int(round(win * fps)))
        d = ev[n:] - ev[:-n]
        out['%.2fs' % win] = [round(float(d.max()), 3), lim]
    out['pass'] = all(v[0] <= v[1] for k, v in out.items() if k != 'pass')
    return out, ev


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--seg', nargs='+', default=list(SEGS))
    ap.add_argument('--w', type=int, default=160)
    ap.add_argument('--fps', type=float, default=10.0)
    ap.add_argument('--views', nargs='+', default=['hero', 'door_d12', 'hero_up'])
    ap.add_argument('--out', default='/tmp/lb/a8flash')
    a = ap.parse_args()
    path = os.path.join(KIT, 'Docs~', 'flash_act08.json')
    res = json.load(open(path)) if os.path.exists(path) else {}
    for seg in a.seg:
        t0, t1 = SEGS[seg]
        ts = np.arange(t0, t1 + 1e-6, 1.0 / a.fps)
        for view in a.views:
            fdir = os.path.join(a.out, f'{seg}_{view}')
            os.makedirs(fdir, exist_ok=True)
            Lm, apl = [], []
            for i, t in enumerate(ts):
                codes, m, lin = R.render(float(t), view, a.w, 'bible_v2')
                Lm.append(float(C.srgb_dec(np.clip(codes, 0, 255) / 255.0).mean(axis=(0, 1)) @ C.LUMA))
                apl.append(m['APL'])
                Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(os.path.join(fdir, 'f%05d.png' % i))
            lw, ev = law(ts, np.array(Lm))
            st = np.diff(ev)
            r = dict(law=lw, step_max_ev=round(float(np.abs(st).max()), 3), apl_range=[round(min(apl), 1), round(max(apl), 1)],
                     t0=t0, t1=t1, fps=a.fps, w=a.w, ev=[round(float(x), 3) for x in ev])
            fc = os.path.join(REPO, 'Art', 'tools', 'lens_tech', 'flashcheck.py')
            p = subprocess.run([sys.executable, fc, fdir, '--fps', str(a.fps), '--hfov', str(R.CAMS[view]['hfov_deg']),
                                '--out', os.path.join(a.out, f'{seg}_{view}_report')], capture_output=True, text=True)
            r['flashcheck_tail'] = (p.stdout + p.stderr).strip().splitlines()[-6:]
            res[f'{seg}/{view}'] = r
            print(seg, view, json.dumps({k: v for k, v in r.items() if k != 'ev'}, ensure_ascii=False), flush=True)
            os.makedirs(os.path.dirname(path), exist_ok=True)
            json.dump(res, open(path, 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
