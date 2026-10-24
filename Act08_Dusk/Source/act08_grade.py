# -*- coding: utf-8 -*-
"""第 8 幕出海的曝光线（圣经 §6·8「7 → 8」、附录 B、§6.x #26）：驱动报 ΔEV，`LanbaiGrade(t)` = {dEV, 0, 0, 1}。
这条线写的是“场景 + 曝光”的总亮度（Director：ΔEV(t) = 目标线(t) − 场景(t)）：
  1. 922.36 钉住在 7c 末的亮度：APL 34（圣经；7c 末 `#3A2629`）。参考帧里求出要多少 ΔEV 才把出海那一帧压到 APL 34。
  2. EV 线性放开，6.75 s 后在 F9（929.11）顶到“场景 + 0.5 EV”。
  3. 4 s 线性回到 0（→ 933.11）。
场景(t) = 正前方（hero）在 ΔEV = 0 时的 log2 平均线性亮度（S7b → S8 调色、含 bloom），在关键帧上量；每个关键帧上的 ΔEV 用二分
求到正好落在目标线上（调色不是线性的）。写 Act08_Dusk/Act08_Grade.json，act08_layout.py 把它并进 Act08_Layout.json。
实机：圣经要“用 7c 末（921）与 8 开头（923）两张正前方截图标定”：README §5。"""
import os
import sys
import json
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import act08_ref as R  # noqa: E402
import lb_common as C  # noqa: E402

W = 320
APL_PIN = 34.0
KEYS = [922.36, 923.0, 924.0, 925.0, 926.0, 927.0, 928.0, 929.11, 930.0, 931.0, 932.0, 933.11]


def measure(t, dev):
    codes, m, lin = R.render(t, 'hero', W, 'bible_v2', None, '', dev)
    L = float(C.srgb_dec(np.clip(codes, 0, 255) / 255.0).mean(axis=(0, 1)) @ C.LUMA)
    return np.log2(max(L, 1e-5)), m['APL']


def solve(t, target, key='ev', lo=-6.0, hi=3.0):
    for _ in range(18):
        mid = 0.5 * (lo + hi)
        ev, apl = measure(t, mid)
        v = ev if key == 'ev' else apl
        if v > target:
            hi = mid
        else:
            lo = mid
    return 0.5 * (lo + hi)


def main():
    t9, t_end = R.B['F9'], 933.11
    scene = {t: measure(t, 0.0)[0] for t in KEYS}
    dev_pin = solve(KEYS[0], APL_PIN, key='apl')
    ev0 = measure(KEYS[0], dev_pin)[0]
    ev9 = scene[t9] + 0.5
    out_t, out_d, line = [], [], []
    for t in KEYS:
        if t <= t9:
            tgt = ev0 + (ev9 - ev0) * (t - KEYS[0]) / (t9 - KEYS[0])
        else:
            tgt = ev9 + (scene[t_end] - ev9) * (t - t9) / (t_end - t9)
        d = dev_pin if t == KEYS[0] else (0.0 if t == t_end else solve(t, tgt))
        out_t.append(t); out_d.append(round(d, 3)); line.append(round(tgt, 3))
        print('t %.2f scene EV %.3f target %.3f dEV %.3f' % (t, scene[t], tgt, d), flush=True)
    out_t.append(t_end + 0.01); out_d.append(0.0)
    g = dict(t=out_t, dev=out_d, target_ev=line, scene_ev=[round(scene[t], 3) for t in KEYS], apl_pin=APL_PIN,
             pin_dev=round(dev_pin, 3), width=W, cam='hero', shell='bible_v2',
             note='LanbaiGrade(t) = {dEV(t), 0, 0, 1}, linear between the keys; 0 outside 922.36 .. 933.11. Calibrate on the '
                  'real bus: README §5 (7c end 921 and 8 start 923 front screenshots)')
    json.dump(g, open(os.path.join(KIT, 'Act08_Grade.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
