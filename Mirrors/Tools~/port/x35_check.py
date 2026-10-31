"""D-50 #1：阿白的 Unity 全片 sweep x35（第 12 面的白冲击，1137.587 → 1138.579 全画面 1 s 升 1.0024 EV，限 1.0）在移植里重算。
量法同 sweep：正前方、全画面平均对数亮度（mean log2 L），每 0.1 s；比较圣经原来的冲击（+1.0 EV、bloom 0.5）和 D-50 的（+0.8 EV、bloom 0.4）。
移植没有车厢、没有 Unity 的 bloom 实现，所以看两者的差；预计 Unity = 1.0024 − (旧 − 新)。
    ~/bpy/bin/python x35_check.py  ->  Mirrors/Docs~/flashcheck/x35_d50.json + Mirrors/Docs~/iterations/x35_d50_strip.png"""
import copy, json, os
import numpy as np
from PIL import Image, ImageDraw
import mirror_port as M

OUT_J = os.path.join(M.REPO, 'Mirrors', 'Docs~', 'flashcheck', 'x35_d50.json')
OUT_S = os.path.join(M.REPO, 'Mirrors', 'Docs~', 'iterations', 'x35_d50_strip.png')
W, H = 320, 180
TS = [round(1136.5 + 0.1 * i, 2) for i in range(32)]
STRIP_T = [1137.38, 1137.58, 1137.78, 1137.98, 1138.18, 1138.38, 1138.58, 1138.78]
LW = np.array([0.2126, 0.7152, 0.0722])
NEW = copy.deepcopy(M.WHITE)
OLD = copy.deepcopy(M.WHITE)
OLD['exposure']['dEV_knots'][1][1] = 1.0
OLD['white_bloom']['knots'][1][1] = 0.5


def run(sched):
    M.WHITE = sched
    logs, frames = [], {}
    for t in TS:
        c, _ = M.frame(t, 0.0, 0.0, w=W, h=H)
        L = (np.clip(c, 0, 255) / 255.0) ** 2.2 @ LW
        logs.append(float(np.log2(np.maximum(L, 1e-4)).mean()))
        if any(abs(t - s) < 1e-6 for s in STRIP_T):
            frames[t] = np.clip(c, 0, 255).astype(np.uint8)
    lg = np.array(logs)
    r1 = max(lg[i + 10] - lg[i] for i in range(len(lg) - 10))
    r025 = max(max(lg[i + k] - lg[i] for k in (1, 2)) for i in range(len(lg) - 2))
    return dict(t=TS, mean_log2_L=[round(x, 4) for x in logs], rise_1s=round(float(r1), 3), rise_02s=round(float(r025), 3)), frames


if __name__ == '__main__':
    o, fo = run(OLD)
    n, fn = run(NEW)
    rep = dict(note=__doc__, unity_x35_rise_1s_old=1.0024, port_old=o, port_new=n,
               predicted_unity_new=round(1.0024 - (o['rise_1s'] - n['rise_1s']), 3))
    json.dump(rep, open(OUT_J, 'w'), ensure_ascii=False, indent=1)
    sh = Image.new('RGB', (W * len(STRIP_T), (H + 20) * 2), 'white')
    d = ImageDraw.Draw(sh)
    for ri, (lab, fr) in enumerate((('bible impact +1.0 EV, bloom 0.5', fo), ('D-50: +0.8 EV, bloom 0.4', fn))):
        for ci, t in enumerate(STRIP_T):
            sh.paste(Image.fromarray(fr[t]), (ci * W, ri * (H + 20) + 20))
            d.text((ci * W + 4, ri * (H + 20) + 4), '%s  t %.2f' % (lab if ci == 0 else '', t), fill=(0, 0, 0))
    sh.save(OUT_S)
    print('port rise 1 s: old %.3f new %.3f -> Unity predicted %.3f' % (o['rise_1s'], n['rise_1s'], rep['predicted_unity_new']))
