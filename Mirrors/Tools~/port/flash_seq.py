"""光敏与爬升律：用 numpy 移植逐帧渲出序列，过 Art/tools/lens_tech/flashcheck.py（库调用）。

    python flash_seq.py <case> [fps] [w h]
case: m1   第 1 面穿越 1029.4 → 1035.4（正前方偏下）
      m10  第 10 面 1112.4 → 1118.4（正前方偏下：加速的尾，最密的脉冲）
      m11  第 11 面 1122.5 → 1128.5
      wf   白：1137.0 → 1149.31 正前方（+6°）
      wd   白：1137.0 → 1149.31 向下看（−60°，整个视野是第 13 面）
白的遮罩（1146.31 → F16）在场景线性里合成（遮罩在 PPv2 之前画：rgb = 填值 × 2^−ΔEV，alpha = EvOverlayAlpha），
调色用 S9b + ΔEV + WHITE_SAT / WHITE_BLOOM（按权重混进 PPv2 参数，r3 C3）；星点按通量守恒（r3 C2）。
-> Mirrors/Docs~/flashcheck/<case>.json
"""
import json, math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_port as MP
sys.path.insert(0, os.path.join(MP.REPO, 'Art', 'tools', 'lens_tech'))
import flashcheck as FC

CASES = dict(m1=(1029.4, 1035.4, 0, -12), m10=(1112.4, 1118.4, 0, -12), m11=(1122.5, 1128.5, 0, -12),
             wf=(1137.0, 1150.0, 0, 6), wd=(1137.0, 1150.0, 0, -60), wu=(1137.0, 1150.0, 0, 60), wsu=(1137.0, 1150.0, 90, 30), m13in=(1058.0, 1065.0, 0, -45))
for _k, _m in enumerate(MP.SCH['mirrors'][:12]):          # C6: every crossing, forward-low / up / down
    _tc = _m['t_cross']
    CASES.setdefault('m%d' % (_k + 1), (_tc - 3.0, _tc + 3.0, 0, -12))
    CASES['m%du' % (_k + 1)] = (_tc - 3.0, _tc + 3.0, 0, 60)
    CASES['m%dd' % (_k + 1)] = (_tc - 3.0, _tc + 3.0, 0, -60)
W = MP.WHITE
FILL = np.array(W['overlay']['fills']['S9b_WHITESAT']['desktop']['linear_rgb'])
LW = float(MP.G.hexlin('#E8F1F5') @ np.array([0.2126, 0.7152, 0.0722]))
LSCENE = float(sys.argv[5]) if len(sys.argv) > 5 else 0.06   # = LanbaiWhiteDriver.lSceneMask (darkest view; C1 = B)
MASK = W['overlay']['mask_in']                                # C1 = B: 1144.81, 4.5 s, a forward lobe 0.46 s behind
T_MASK0, T_MASK = MASK['t'][0], MASK['T_s']


def mask_lead(d):
    """Overlay v2 LeadAt: leadElse, then lerp toward each lobe's lead by its smoothstep weight (soft edge >= 30 deg)."""
    lead = np.full(d.shape[:-1], MASK['lead_else_s'])
    soft = max(MASK['soft_edge_deg'], 30.0)
    for lb in MASK['lobes']:
        v = np.array(lb['dir'], float); v /= np.linalg.norm(v)
        c = d @ v
        cin = math.cos(math.radians(lb['half_angle_deg'])); cout = math.cos(math.radians(min(lb['half_angle_deg'] + soft, 180.0)))
        m = np.clip((c - cout) / (cin - cout), 0, 1); m = m * m * (3 - 2 * m)
        lead = lead + (lb['lead_s'] - lead) * m
    return lead


def ev_alpha(x, lf, lt, ls, lo):
    a = max(lf, 0.004); b = max(lt, 0.004)
    L = a * (b / a) ** min(max(x, 0), 1)
    return min(max((ls - L) / (ls - lo), 0), 1)


def main():
    case = sys.argv[1]
    if os.environ.get('MIRROR13'):
        import mirror13_study as M13S
        M13S.apply_scheme(os.environ['MIRROR13'])
    fps = float(sys.argv[2]) if len(sys.argv) > 2 else 30.0
    w = int(sys.argv[3]) if len(sys.argv) > 3 else 192
    h = int(sys.argv[4]) if len(sys.argv) > 4 else 108
    t0, t1, yaw, pitch = CASES[case]
    if os.environ.get('T0'):
        t0, t1 = float(os.environ['T0']), float(os.environ['T1'])
    ts = np.arange(t0, t1 + 1e-6, 1.0 / fps)
    frames = []
    LEAD = None
    for t in ts:
        c, info = MP.frame(float(t), yaw, pitch, w, h, dust=True)
        if case in ('wf', 'wd', 'wu', 'wsu') and t >= T_MASK0:
            # the overlay composited per pixel (the forward lobe leads by 0.46 s); at F16 the cut to the full white
            if LEAD is None:
                LEAD = mask_lead(MP.camera_dirs(w, h, 90, yaw, pitch).reshape(h, w, 3))
            if t >= W['labels']['F16_cut2']:
                a = np.ones((h, w))
            else:
                a = np.vectorize(lambda x: ev_alpha(x, LSCENE, LW, LSCENE, LW))((t - T_MASK0 - LEAD) / T_MASK)
            a = a[..., None]
            ev = MP.white_ev(float(t))
            lin = MP.G.hexlin  # noqa
            # approximate: blend in display-linear space of the graded frame toward the fill's screen colour
            disp = np.where(c / 255 <= 0.04045, c / 255 / 12.92, ((c / 255 + 0.055) / 1.055) ** 2.4)
            white = MP.G.hexlin('#E8F1F5')
            disp = disp * (1 - a) + white[None, None, :] * a
            c = np.where(disp <= 0.0031308, disp * 12.92, 1.055 * disp ** (1 / 2.4) - 0.055) * 255
        frames.append(np.clip(c, 0, 255).astype(np.uint8))
    rep, series = FC.analyze(frames, fps, hfov=90.0, label=case)
    apl = [float((np.clip(f, 0, 255) / 255.0) .mean()) for f in frames]
    L = [float(((np.clip(f, 0, 255) / 255.0) ** 2.2 @ np.array([0.2126, 0.7152, 0.0722])).mean()) for f in frames]
    rep['t_series'] = [round(float(t), 3) for t in ts]; rep['L_series'] = [round(x, 5) for x in L]
    rep['flashes_1s_series'] = [round(float(x), 2) for x in series['flashes_1s']]
    i = int(np.argmax(series['flashes_1s'])); rep['worst_flash_window_end_t'] = round(float(ts[i]), 3)
    out = os.path.join(MP.REPO, 'Mirrors', 'Docs~', 'flashcheck')
    os.makedirs(out, exist_ok=True)
    rep['case'] = case; rep['t'] = [t0, t1]; rep['fps'] = fps; rep['size'] = [w, h]; rep['view'] = [yaw, pitch]
    rep['note'] = 'numpy port of the mirror shaders on the act 9 sky (no cabin); the white mask blended in display-linear toward #E8F1F5 with EvOverlayAlpha (Lscene %.2f; C1 = B: from 1144.81, 4.5 s, forward lobe +0.46 s); WHITE_SAT/BLOOM blended into the PPv2 parameters; star flux conserved below 1.6 px (r3 C2)' % LSCENE
    json.dump(rep, open(os.path.join(out, case + (('_' + os.environ['MIRROR13']) if os.environ.get('MIRROR13') else '') + ('_%dpx' % w if w != 192 else '') + '.json'), 'w'), indent=1, default=float)
    print(json.dumps({k: rep[k] for k in rep if k not in ('series',)}, default=float)[:1500])


if __name__ == '__main__':
    main()
