"""蓝白 · 第 10 幕：迟到的人（D-43 #5）。照 LanbaiWhiteDriver.DriveOverlay 的逻辑逐帧算屏幕亮度，过 flashcheck。
进来的时刻 = 黑场结束、分发层调 LanbaiSpawnFade(0) 的那一刻（D-43 #4：遮罩窗口在黑场 + 淡入里开始的，保持黑、在 1146.31 交给本驱动）。
视向：被白盖住的部分屏幕亮度 = 白（桌面 0.86、VR 0.74）；第 11 幕 L 0.012（APL 30）× 2^dEV；遮罩那 3 s 的场景 L 用 C1 实测的三个。
    python3 join_check.py   -> Mirrors/Docs~/flashcheck/join_<t>.json"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Art', 'tools', 'lens_tech'))
import flashcheck as FC   # noqa: E402

W = json.load(open(os.path.join(REPO, 'Act10_White', 'WhiteSchedule.json'), encoding='utf-8'))
LB = W['labels']
MK = W['overlay']['mask_in']
T_MASK, T_F16, T_SE, T_END = MK['t'][0], LB['F16_cut2'], LB['silence_end'], LB['shrink_end']   # C1 = B: 1144.81
MASK_T = MK['T_s']
FLOOR, RATE, L11, SHRINK, DECAY = 0.004, 0.80, 0.012, 5.0, 4.0
LB11 = 1.0   # W2: the veil is built for act 11's brightest non-white view (1.0 until act 11 gives Lb)
LS_MASK = MK['Lscene']


def ev_alpha(x, lf, lt, ls, lo):
    a = max(lf, 0.004); b = max(lt, 0.004)
    L = a * (b / a) ** min(max(x, 0.0), 1.0)
    return min(max((ls - L) / (ls - lo), 0.0), 1.0)


def screen(t, tj, lw, lv_mask, lead, mlead=0.0):
    """the screen luminance of one view (its scene behind the mask = lv_mask, its shrink lead = lead)."""
    if t < tj:
        return FLOOR                                             # the spawn black (held by the dispatcher)
    ramp = math.log(lw / FLOOR, 2) / RATE
    to_scene = tj + ramp > T_SE
    scene_ramp = math.log(LB11 / FLOOR, 2) / RATE
    t0s = max(T_END, tj)                                         # W1: the rise starts at the hand-over
    dev = max(0.0, 1.0 - (t - T_SE) / DECAY) if t >= T_SE else 0.0
    l11 = L11 * 2 ** dev
    if to_scene:
        if t < t0s:
            return FLOOR
        x = min(max((t - t0s) / scene_ramp, 0), 1)
        a = ev_alpha(x, FLOOR, LB11, LB11, 0.0)
        return max((1 - a) * l11, FLOOR)
    if t < tj + ramp:
        return lw * (FLOOR / lw) ** (1 - (t - tj) / ramp)       # opaque, fill black -> white
    if t < T_F16:
        a = ev_alpha((t - T_MASK - mlead) / MASK_T, LS_MASK, lw, LS_MASK, lw)
        return (1 - a) * lv_mask + a * lw
    if t < T_SE:
        return lw
    a = 1 - ev_alpha((t - T_SE - lead) / SHRINK, lw, L11, lw, L11)
    return (1 - a) * l11 + a * lw


def run(tj, lw=0.86, fps=30.0):
    ts = np.arange(tj - 1.0, max(T_END, tj) + math.log(LB11 / FLOOR, 2) / RATE + 2.0, 1 / fps)
    worst = None
    for lv, lead, ml in ((0.48, 0.0, MK['lobes'][0]['lead_s']), (0.06, 3.0, 0.0), (0.74, 1.5, 0.0)):   # forward is in the mask's lobe
        L = np.array([screen(t, tj, lw, lv, lead, ml) for t in ts])
        code = np.where(L <= 0.0031308, L * 12.92, 1.055 * L ** (1 / 2.4) - 0.055) * 255
        frames = [np.full((54, 96, 3), c, np.uint8) for c in np.clip(code, 0, 255)]
        rep, _ = FC.analyze(frames, fps, hfov=90.0, label='join')
        r = (rep['max_rise_ev_0.25s'], rep['max_rise_ev_1s'], rep['max_rise_ev_2s'], rep['max_general_flashes_in_any_1s'], rep['lanbai_flash_rule'])
        ok = r[0] <= 0.5 and r[1] <= 1.0 and r[2] <= 1.8 and r[4] == 'PASS'
        if worst is None or not ok or r[1] > worst[1][1]:
            worst = (dict(view_Lmask=lv, lead=lead), r, ok)
    return worst


if __name__ == '__main__':
    out = {}
    # D-43 #5 times (black end; 1140 is handed over at the mask's start, rule 4) + the boundaries of this driver's paths
    for tj in (1144.11, 1144.81, 1146.31, 1150.0, 1160.0, 1168.5, 1169.5, 1175.0, 1178.46, 1180.0, 1186.0, 1186.3, 1186.46):   # after 1186.46 (the overlay window's end, D-43 #7) LB_Journey fades
        for lw, tag in ((0.86, 'desk'), (0.74, 'vr')):
            w = run(tj, lw)
            out['%.2f_%s' % (tj, tag)] = dict(view=w[0], rise_025_1_2=w[1][:3], flashes=w[1][3], rule=w[1][4], PASS=w[2])
            print('%.2f %s' % (tj, tag), w[1], 'PASS' if w[2] else 'FAIL')
    json.dump(out, open(os.path.join(REPO, 'Mirrors', 'Docs~', 'flashcheck', 'join_white.json'), 'w'), indent=1)
