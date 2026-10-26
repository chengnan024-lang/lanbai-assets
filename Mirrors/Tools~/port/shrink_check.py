"""总导演终审 r3 C7：10 → 11 “白收缩进灯里”的光敏 / 爬升检查（合成场景）。
第 11 幕的场景不在本包：用均匀的 L11 = 0.012（APL 30）代替，加上 1178.46 起 +1 EV、4 s 衰减的曝光；遮罩 = LanbaiWhiteDriver 的
收缩：SetCurve(白, dEV, t − 1178.46, 5 s, Lw, L11, L11, Lw)，方向领先照驱动的 lobe（管灯 0 s、路灯 1.5 s、头顶 3 s、其余 3 s，软边 30°），
和 Overlay v2 shader 的 LeadAt / LobeWeight 同一个式子。白的填色补偿 2^−dEV 由遮罩组件做，所以白恒为 Lw。
    ~/bpy/bin/python shrink_check.py   -> Mirrors/Docs~/flashcheck/shrink_<view>.json"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'lens_tech'))
from shader_cpu import camera_dirs              # noqa: E402
import flashcheck as FC                         # noqa: E402

T_SE, T_END, SHRINK, DECAY = 1178.46, 1186.46, 5.0, 4.0
L11 = 0.012
LOBES = [((0, 0.6, 0.8), 30.0, 0.0), ((1, 0.15, 0), 40.0, 1.5), ((0, 1, 0), 35.0, 3.0)]
LEAD_ELSE, SOFT = 3.0, 30.0


def ev_alpha(x, lf, lt, ls, lo):
    a = max(lf, 0.004); b = max(lt, 0.004)
    L = a * (b / a) ** np.clip(x, 0, 1)
    return np.clip((ls - L) / (ls - lo), 0, 1)


def lead_at(d):
    lead = np.full(d.shape[:-1], LEAD_ELSE)
    for v, half, ld in LOBES:
        v = np.array(v, float); v /= np.linalg.norm(v)
        c = d @ v
        cin, cout = math.cos(math.radians(half)), math.cos(math.radians(min(half + SOFT, 180)))
        m = np.clip((c - cout) / (cin - cout), 0, 1); m = m * m * (3 - 2 * m)
        lead = lead + (ld - lead) * m
    return lead


def run(name, yaw, pitch, lw, fps=30.0, w=192, h=108):
    d = camera_dirs(w, h, 90, yaw, pitch).reshape(h, w, 3)
    lead = lead_at(d)
    frames = []
    ts = np.arange(T_SE - 1.0, T_END + 1.0, 1 / fps)
    for t in ts:
        dev = max(0.0, 1.0 - (t - T_SE) / DECAY) if t >= T_SE else 0.0
        a = np.ones((h, w)) if t < T_SE else ev_alpha((t - T_SE - lead) / SHRINK, lw, L11, L11, lw)
        D = (1 - a) * L11 * 2 ** dev + a * lw
        code = np.where(D <= 0.0031308, D * 12.92, 1.055 * D ** (1 / 2.4) - 0.055) * 255
        frames.append(np.repeat(np.clip(code, 0, 255).astype(np.uint8)[..., None], 3, -1))
    rep, series = FC.analyze(frames, fps, hfov=90.0, label=name)
    rep.update(case=name, view=[yaw, pitch], Lwhite=lw, L11=L11, t=[float(ts[0]), float(ts[-1])],
               note='synthetic act 11 (uniform L 0.012) under the driver shrink lobes; Overlay v2 LeadAt maths')
    out = os.path.join(REPO, 'Mirrors', 'Docs~', 'flashcheck')
    json.dump(rep, open(os.path.join(out, 'shrink_%s.json' % name), 'w'), indent=1, default=float)
    keys = [k for k in rep if 'flash' in k or 'rise' in k or 'rule' in k]
    print(name, {k: rep[k] for k in keys})


if __name__ == '__main__':
    for lw, tag in ((0.86, 'desk'), (0.74, 'vr')):
        for name, yaw, pitch in (('fwd', 0, 0), ('tubes', 0, 37), ('street', 90, 8), ('up', 0, 80), ('down', 0, -60), ('back', 180, 0)):
            run(name + '_' + tag, yaw, pitch, lw)
