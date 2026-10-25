#!/usr/bin/env python3
"""
蓝白 · 十三面白铜镜的时间表与运动（唯一的数据源 -> Mirrors/MirrorSchedule.json）

依据：圣经 v2.1 §6·9 9c 的表（定稿 E20，两段：第 1–10 面 r = 1.3083 加速到 F15 tragen!，尾声三声钟 1125.55 / 1137.58 / F16），
§6·9 → 10（白的冲击从第 12 面起；第 13 面的镜面自发光 +3 EV 只在膨胀与保持里升），§1.8（镜子脉冲只给第 1–11 面）。
不用 cues.json 里的 derived.mirror_r = 1.2265 与 mirror_crossings_*（E1、E20）。

时刻：从 FromLocal/cues.json 读 F13 / F14 / F15 / F16（标签一挪，这里重跑）；第 2–9 面按 Art/tools/v21/cues_v21.py 的
MIRRORS 与 F15 往回排的公比数列重解（吸附到 ±0.8 s 内的强拍，间隔不增、≥ 2.5 s），第 11、12 面是 cues.json 强拍表里的
尾声强拍（与圣经一致：1125.55、1137.58）。

运动（圣经只给了约束，具体曲线是这里定的，写进 JSON，驱动和天空都读 JSON）：
  * 镜面平面的高度 y(t)（世界 y，米）= 镜面在车（主座位眼位的 xz）正下方那一点的高度；穿越 = 这一点到达眼高 1.70。
  * 第 1–12 面：离车远时以“行进速度” v_a 上升，接近车时 smoothstep 减速到“穿越速度” v_c，最后 hold 秒保持 v_c；
    穿越后继续以 v_c 上升，2.0 s 内从镜缘向内溶解成星尘。v(τ) = v_c + (v_a − v_c)·S((τ − hold)/T_dec)，τ = t_c − t。
    积分有闭式（I(u) = u³ − u⁴/2），驱动里用同一公式；JSON 里同时给 Hermite 节点表（t, y, v），二者一致（下面核对）。
  * 第 13 面：F14 起在 6 km 下方，到 F16 − 10 s 慢慢升到 5 km（角直径增长 ≤ 0.5°/s）；最后 10 s 按镜缘俯角 φ(t)
    的单调 Hermite 升上来：1146.31（保持结束）时镜缘在 −2.2°（正前方下方 40% 是第 13 面，与 ramp_checks_v21 的仿真同一几何），
    F16 镜面到达眼睛。
  * 方位：每面镜“离车最近的镜缘”所在的方位（0° = 车头 +Z，负 = 左）；镜心在相反方向。最近镜缘距离 d_near 保证
    镜缘永远不碰车（车厢包围盒到镜缘 ≥ 10 m），并满足 §1.8 的 v ≤ 1.05 d。

用法：  ~/bpy/bin/python make_schedule.py         （写 MirrorSchedule.json、Docs~/schedule_check.txt、Docs~/schedule.png）
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
MIR = os.path.join(ROOT, 'Mirrors')
cues = json.load(open(os.path.join(ROOT, 'FromLocal', 'cues.json'), encoding='utf-8'))
F = {k: v['t'] for k, v in cues['F'].items()}
ACC = cues['F13_F16_accents_t']

# ------------------------------------------------------------------ crossings (bible §6·9, E20)
F13, F14, F15, F16 = F['F13'], F['F14'], F['F15'], F['F16']
T1 = round(F13 + 4.2 + 10.0, 2)                   # ignition 4.2 s + hold 10 s
N1 = 10
span = F15 - T1                                     # 82.95
def solve_r(span, d0=2.5, n=9):
    lo, hi = 1.0001, 2.0
    for _ in range(100):
        r = 0.5 * (lo + hi)
        s = d0 * (r ** n - 1) / (r - 1)
        lo, hi = (r, hi) if s < span else (lo, r)
    return r
R1 = solve_r(span)
gaps = [2.5 * R1 ** k for k in range(9)][::-1]     # first gap is the longest
raw = [T1]
for g in gaps:
    raw.append(raw[-1] + g)
raw[-1] = F15
# snap interior crossings (2..9) to the nearest accent within +-0.8 s, keeping gaps non-increasing and >= 2.5 s
cross = list(raw)
snap = [None] * 10
for i in range(1, 9):
    best = None
    for a in ACC:
        if abs(a - raw[i]) <= 0.8 and (best is None or abs(a - raw[i]) < abs(best - raw[i])):
            best = a
    if best is None:
        continue
    trial = list(cross); trial[i] = best
    g = np.diff(trial[:i + 2]) if i + 1 < 10 else np.diff(trial[:i + 1])
    ok = np.all(np.diff(np.diff(trial)) <= 1e-6) and np.all(np.diff(trial) >= 2.5 - 1e-6)
    if ok:
        cross = trial; snap[i] = round(best - raw[i], 2)
CODA = [1125.55, 1137.58]
for c in CODA:
    assert min(abs(a - c) for a in ACC) < 0.02, c
cross = [round(c, 2) for c in cross] + CODA + [F16]
BIBLE = [1032.41, 1054.29, 1070.62, 1082.67, 1092.39, 1099.71, 1105.42, 1109.46, 1112.86, 1115.36, 1125.55, 1137.58, 1149.31]
assert all(abs(a - b) < 0.011 for a, b in zip(cross, BIBLE)), (cross, BIBLE)

# ------------------------------------------------------------------ sizes and speeds
# mirror 13's last 10 s (总导演意见 #5): A = the first version; G = fast while the rim is soft, then <= 2.6 deg/s;
# H = a 17 km mirror that already fills the down view, rim <= 1.4 deg/s throughout (Docs~/iterations/m13_*). Pick with
# LANBAI_M13=A|G|H (the director's choice is recorded in the JSON as scheme13).
SCHEME13 = os.environ.get('LANBAI_M13', 'H')        # D-38: the director picked H
D13 = 17000.0 if SCHEME13 == 'H' else 2400.0
D = [40.0 * 1.2 ** k for k in range(10)] + [360.0, 620.0, D13]
EYE = np.array([0.55, 1.70, 2.05])             # Gate/GateLayout_v2.json cameras.U7 (CONTROL §3)
CAB = dict(x=(-1.40, 1.40), y=(0.0, 3.1), z=(-6.0, 5.0))   # conservative bus box (m, car space)
# nearest-rim azimuth (deg, 0 = +Z ahead, negative = left).  Front sector, alternating, tragen! dead ahead,
# the white's impact (12) front-right so the Milky Way core (-30 / +12) stays clear in the front-left.
AZ = [-62, 45, -45, 15, -60, 50, -10, 35, -35, 0, -25, 20, 0]   # 终审 M-1: mirrors 1, 2 turned so their knobs pass beside the bus
R_KNOB = 0.065          # knob base radius / D (make_mesh.py); it hangs 0.015 .. 0.065 D below the face edge
D_NEAR = [14.0, 13.0, 15.0, 17.0, 20.0, 23.0, 26.0, 29.0, 32.0, 35.0, 60.0, 100.0, None]
V_A = [3.0 * (40.0 / 3.0) ** (k / 9.0) for k in range(10)] + [18.0, 20.0]      # travel speed (m/s)
V_C = [1.7 * (10.0 / 1.7) ** (k / 9.0) for k in range(10)] + [6.0, 5.0]        # crossing speed (m/s)
HOLD = [0.6] * 10 + [1.0, 1.0]
T_DEC = [3.0] * 10 + [4.0, 4.0]
# far away every mirror waits in the column at a slow 'queue' speed and accelerates into its approach speed v_a only for the
# last few seconds, so a fast later mirror never overtakes a slower earlier one (the stack stays ordered)
V_Q = [min(v, 4.0) for v in V_A[:10]] + [18.0, 20.0]   # the coda mirrors wait deeper (they are the bells' 'stair' below)
T_APP = [6.0] * 10 + [8.0, 8.0]      # tau at which the queue -> approach acceleration ends
T_ACC = [4.0] * 12
PULSE = [0.35] * 11 + [0.0, 0.0]
EMIT_K = [round(0.2 + 0.08 * (k + 1), 4) for k in range(13)]
DISSOLVE = 2.0

def I(u):
    u = np.clip(u, 0.0, None)
    return np.where(u < 1.0, u ** 3 - 0.5 * u ** 4, 0.5 + (u - 1.0))

def y_of(k, t):
    """face height at the car (world y) for mirrors 1..12 (k 0-based).  depth(tau) = integral of v over [0, tau]."""
    tau = cross[k] - np.asarray(t, float)
    va, vc, vq, h, td, ta, tc = V_A[k], V_C[k], V_Q[k], HOLD[k], T_DEC[k], T_APP[k], T_ACC[k]
    below = vc * tau + (va - vc) * td * I((tau - h) / td) + (vq - va) * tc * I((tau - ta) / tc)
    return EYE[1] - np.where(tau >= 0, below, vc * tau)

def S(u):
    u = np.clip(u, 0, 1); return u * u * (3 - 2 * u)

def v_of(k, t):
    tau = cross[k] - np.asarray(t, float)
    v = V_C[k] + (V_A[k] - V_C[k]) * S((tau - HOLD[k]) / T_DEC[k]) + (V_Q[k] - V_A[k]) * S((tau - T_APP[k]) / T_ACC[k])
    return np.where(tau >= 0, v, V_C[k])

# ------------------------------------------------------------------ mirror 13
R13 = D[12] / 2
T_PLATEAU_END = 1146.31
def pchip_slopes(x, y):
    x = np.asarray(x, float); y = np.asarray(y, float)
    h = np.diff(x); d = np.diff(y) / h
    m = np.zeros_like(y)
    for i in range(1, len(y) - 1):
        if d[i - 1] * d[i] <= 0:
            m[i] = 0
        else:
            w1, w2 = 2 * h[i] + h[i - 1], h[i] + 2 * h[i - 1]
            m[i] = (w1 + w2) / (w1 / d[i - 1] + w2 / d[i])
    m[0] = d[0]; m[-1] = d[-1]
    return m
def herm(xk, yk, mk, x):
    x = np.asarray(x, float)
    i = np.clip(np.searchsorted(xk, x) - 1, 0, len(xk) - 2)
    h = xk[i + 1] - xk[i]; s = np.clip((x - xk[i]) / h, 0, 1)
    h00 = 2 * s ** 3 - 3 * s ** 2 + 1; h10 = s ** 3 - 2 * s ** 2 + s; h01 = -2 * s ** 3 + 3 * s ** 2; h11 = s ** 3 - s ** 2
    return h00 * yk[i] + h10 * h * mk[i] + h01 * yk[i + 1] + h11 * h * mk[i + 1]
# depth h (m below the eye) from F14 to F16-10, then rim depression phi (deg) for the last 10 s
T13A = F16 - 10.0
far_t = np.array([F14, T13A]); far_h = np.array([6000.0, 5000.0])
phi0 = math.degrees(math.atan(5000.0 / R13))
phi_t = np.array([T13A, 1142.3, 1144.78, T_PLATEAU_END, F16])
phi_k = np.array([phi0, 30.0, 9.0, 2.2, 0.0])
phi_m = pchip_slopes(phi_t, phi_k)
phi_m[0] = 0.0                                    # leaves the slow far approach with ~0 angular speed
far_m = np.array([0.0, (5000.0 - 6000.0) / (T13A - F14) * 1.5])
if SCHEME13 == 'G':
    phi_t = np.array([T13A, 1141.3, 1142.9, F16]); phi_k = np.array([phi0, 30.0, 11.5, 0.0]); phi_m = np.array([0.0, -24.0, -2.6, -0.3])
    RIM_SOFT = dict(sharpen_from=1142.9, seconds=1.0, inner_frac=0.25)
elif SCHEME13 == 'H':
    p6 = math.degrees(math.atan(6000.0 / R13))
    phi_t = np.array([F14, T13A, T_PLATEAU_END, F16]); phi_k = np.array([p6, 10.0, 2.2, 0.0]); phi_m = np.array([0.0, -0.44, -0.9, -0.3])
    RIM_SOFT = None                                # D-38: the rim is always clear (review r3 C4)
else:
    RIM_SOFT = dict(sharpen_from=T13A, seconds=4.0, inner_frac=0.80)


def depth13(t):
    t = np.asarray(t, float)
    if SCHEME13 == 'H':
        return R13 * np.tan(np.radians(herm(phi_t, phi_k, phi_m, np.clip(t, F14, F16))))
    d_far = 6000.0 - 1000.0 * (lambda u: u * u * (3 - 2 * u))(np.clip((t - F14) / (T13A - F14), 0, 1))
    phi = herm(phi_t, phi_k, phi_m, np.clip(t, T13A, F16))
    d_near = R13 * np.tan(np.radians(phi))
    return np.where(t < T13A, d_far, d_near)
def y13(t):
    return EYE[1] - depth13(t)

# ------------------------------------------------------------------ geometry per mirror
def centre(k):
    a = math.radians(AZ[k])
    u = np.array([math.sin(a), 0.0, math.cos(a)])
    if k == 12:
        return np.array([EYE[0], 0.0, EYE[2]]), u
    R = D[k] / 2
    c = np.array([EYE[0], 0.0, EYE[2]]) - u * (R - D_NEAR[k])   # nearest rim at distance d_near along u
    return c, u
def knob_clearance(k):
    """horizontal distance from the knob's outer edge to the cabin box (m); the knob passes through the cabin's height when
    the mirror crosses, so it must be beside the bus (终审 M-1: >= 1 m)."""
    c, _ = centre(k)
    dx = max(CAB['x'][0] - c[0], 0.0, c[0] - CAB['x'][1]); dz = max(CAB['z'][0] - c[2], 0.0, c[2] - CAB['z'][1])
    return math.hypot(dx, dz) - R_KNOB * D[k]
def cabin_rim_clearance(k):
    c, _ = centre(k); R = D[k] / 2
    xs = np.linspace(*CAB['x'], 8); zs = np.linspace(*CAB['z'], 23)
    X, Z = np.meshgrid(xs, zs)
    rr = np.hypot(X - c[0], Z - c[2])
    return float((R - rr).min())       # horizontal distance from the nearest cabin corner to the rim circle (inside)

# ------------------------------------------------------------------ checks
lines = []
def log(s=''):
    lines.append(s); print(s)
log('蓝白 · 十三面镜时间表核对（make_schedule.py 生成，不要手改）')
log('F13 %.2f  F14 %.2f  F15 %.2f  F16 %.2f   第一段公比 r = %.4f（9 个间隔之和 %.2f s）' % (F13, F14, F15, F16, R1, span))
log('')
log(' k   t_cross   gap    snap   D(m)    boss  az   d_near  rimClr  v_a    v_c   seen45(s)  vmax/d  pulse  emitK')
rows = []
tt = np.arange(F13 - 20, F16 + 5, 0.01)
ok_all = True
for k in range(13):
    c, u = centre(k)
    R = D[k] / 2
    if k < 12:
        y = y_of(k, tt)
        dn = D_NEAR[k]
        # galaxy 'seen' = face below the eye and within the near-rim distance (so it fills at least the lower 45 deg cone)
        seen = float(np.sum((EYE[1] - y <= dn) & (tt < cross[k]))) * 0.01
        w = (tt > cross[k] - 30) & (tt < cross[k] + DISSOLVE)
        sag = 0.015 * D[k]
        rim_y = y[w] - sag * (1 - ((R - dn) / R) ** 2)          # rim plane under the face point at the car
        dist = np.hypot(dn, rim_y - EYE[1])
        vd = float((v_of(k, tt[w]) / dist).max())
    else:
        y = y13(tt); dn = R13; seen = float(np.sum((EYE[1] - y <= R13) & (tt < F16))) * 0.01; vd = float('nan')
    clr = cabin_rim_clearance(k)
    need_seen = 2.0 if k < 10 else 4.0
    kclr = knob_clearance(k) if k < 12 else 99.0
    if k < 12 and kclr < 1.0:
        log('  !! 第 %d 面的钮离车厢包围盒只有 %.2f m（< 1 m）' % (k + 1, kclr))
    ok = clr >= 10.0 and kclr >= 1.0 and (seen >= need_seen or k == 12) and (k == 12 or vd <= 1.05)
    ok_all &= ok
    boss = int(round(math.pi * (D[k] - 0.02 * D[k]) / 1.5))
    log('%2d  %8.2f  %5s  %5s  %6.1f  %5d  %4d  %6.1f  %6.1f  %5.1f  %5.2f   %6.2f    %5.2f   %4.2f  %5.2f  %s' % (
        k + 1, cross[k], '%.2f' % (cross[k] - cross[k - 1]) if k else '—', ('%+.2f' % snap[k]) if (k < 10 and snap[k] is not None) else ('强拍' if k in (10, 11) else '—'),
        D[k], boss, AZ[k], dn, clr, V_A[k] if k < 12 else float('nan'), V_C[k] if k < 12 else float('nan'), seen, vd, PULSE[k], EMIT_K[k], 'OK' if ok else 'FAIL'))
    rows.append(dict(c=c, u=u))
# ordering: a later mirror is always below an earlier one while both exist (no interpenetration)
order_ok = True
for k in range(12):
    tend = cross[k] + DISSOLVE
    m = tt <= tend
    ya = y_of(k, tt[m])
    yb = y_of(k + 1, tt[m]) if k + 1 < 12 else y13(tt[m])
    if np.any(yb >= ya - 2.0):
        order_ok = False; log('  !! 第 %d 面与第 %d 面相交' % (k + 1, k + 2))
log('')
log('镜子之间不相交（后一面始终在前一面下方 ≥ 2 m，直到前一面溶解完）：%s' % ('OK' if order_ok else 'FAIL'))
# mirror 13: angular growth before the last 10 s, rim angular speed in the last 10 s
t13 = np.arange(F14, F16, 0.01)
th = np.degrees(np.arctan(R13 / np.maximum(depth13(t13), 1e-3)))
rate = np.gradient(th, t13)
pre = rate[t13 < T13A]
log('第 13 面（D = %.0f m，镜心在车下）：F14 时深 %.0f m（角半径 %.1f°），F16−10 = %.2f 时深 %.0f m（%.1f°）；之前角半径增长最快 %.3f°/s（≤ 0.45，D-38）' % (
    D[12], depth13(F14), th[0], T13A, depth13(T13A), np.degrees(np.arctan(R13 / depth13(T13A))), pre.max()))
phi = np.degrees(np.arctan(depth13(t13) / R13))
prate = -np.gradient(phi, t13)
last = t13 >= T13A
log('  最后 10 s：镜缘俯角 %.1f° → 0°，最快 %.1f°/s（在 %.2f），镜缘离眼 ≥ %.0f m；1144.78 时 %.2f°、1146.31 时 %.2f°（目标 2.2°）、F16 前 0.5 s 上升速度 %.1f m/s' % (
    phi0, prate[last].max(), t13[last][np.argmax(prate[last])], R13, float(np.degrees(np.arctan(depth13(1144.78) / R13))),
    float(np.degrees(np.arctan(depth13(1146.31) / R13))), float((depth13(F16 - 0.51) - depth13(F16 - 0.49)) / 0.02)))
ok13 = pre.max() <= 0.45 and (SCHEME13 != 'H' or prate[last].max() <= 1.4) and abs(float(np.degrees(np.arctan(depth13(1146.31) / R13))) - 2.2) < (0.05 if SCHEME13 != 'G' else 1.5)
ok_all &= ok13 and order_ok
# simultaneous dissolves
dis = [(cross[k], cross[k] + DISSOLVE) for k in range(12)]
mx = max(sum(1 for a, b in dis if a <= t < b) for t in tt)
log('同时溶解的镜子最多 %d 面（≤ 3，星尘 ≤ 750 颗）：%s' % (mx, 'OK' if mx <= 3 else 'FAIL'))
ok_all &= mx <= 3

# ------------------------------------------------------------------ visibility (column) and emission curves
def queue_vis(k):
    """face-emission visibility multiplier knots (t, value): 0 -> 0.3 when the mirror joins the visible column, -> 1 on approach."""
    if k == 0:
        # 终审 M-8: mirror 1 only starts condensing at 1024.41, so the galaxy's full ring under the feet (F13) is seen first
        a = round(cross[0] - 8.0, 2)
        return [[a, 0.0], [round(a + 3.0, 2), 0.3], [round(cross[0] - 2.0, 2), 1.0]]
    prev = cross[k - 1]
    if k < 12:
        # the visible column = the next three uncrossed mirrors, from F14 on (before F14 only the next one)
        if prev < F14:
            join = prev - 8.0          # appears (3 s condensing) while the previous mirror still covers most of it
        else:
            join = max(F14, cross[k - 3]) if k >= 3 else F14
        # the face emission reaches 1 AT the previous crossing (r4: ramping it 0.3 -> 1 after the crossing made the lower view
        # dip and climb back +1.3 EV in 1 s, flash sequence m10); a face at infinity-reflection is as bright far as near,
        # so the swap from the previous face to this one is then nearly luminance-neutral
        a = round(join, 2); b = round(min(a + 3.0, prev - 2.0), 2)
        c0 = round(prev - 2.0, 2); c1 = round(prev, 2)
        out = [[a, 0.0]] + ([[b, 0.3]] if b > a else []) + [[c0, 0.3], [c1, 1.0]]
        # strictly increasing times
        clean = []
        for p in out:
            if not clean or p[0] > clean[-1][0] + 1e-6:
                clean.append(p)
        return clean
    return [[round(F14, 2), 0.0], [round(F14 + 4.0, 2), 0.3], [round(cross[11] - 2.0, 2), 0.3], [round(cross[11], 2), 1.0]]   # done before the white's impact (no emission rises in the impact)

def hermite_knots(k, dt):
    if k < 12:
        t0 = queue_vis(k)[0][0] - 1.0
        t1 = cross[k] + DISSOLVE + 0.5
    else:
        t0, t1 = F14 - 1.0, F16 + 0.5
    ts = list(np.arange(t0, t1, dt)) + [t1]
    for extra in ([cross[k], cross[k] - HOLD[k], cross[k] - HOLD[k] - T_DEC[k]] if k < 12 else [T13A, 1142.3, 1144.78, T_PLATEAU_END, F16]):
        if t0 < extra < t1:
            ts.append(extra)
    ts = np.unique(np.round(np.array(ts), 3))
    if k < 12:
        ys = y_of(k, ts); vs = v_of(k, ts)
    else:
        ys = y13(ts); eps = 1e-3; vs = (y13(ts + eps) - y13(ts - eps)) / (2 * eps)
    return [[round(float(a), 3), round(float(b), 4), round(float(c), 4)] for a, b, c in zip(ts, ys, vs)]

def eval_knots(kn, t):
    kn = np.array(kn); x, y, m = kn[:, 0], kn[:, 1], kn[:, 2]
    return herm(x, y, m, t)

mirrors = []
max_err = 0.0
for k in range(13):
    c, u = centre(k)
    kn = hermite_knots(k, 0.25 if k < 12 else 0.04)
    # far part of mirror 13 does not need 0.1 s knots
    if k == 12:
        kn = [p for p in kn if p[0] >= T13A - 0.01 or abs((p[0] - F14) % 2.0) < 0.051 or p[0] <= F14]
    tchk = np.arange(kn[0][0], kn[-1][0], 0.01)
    ref = y_of(k, tchk) if k < 12 else y13(tchk)
    err = float(np.abs(eval_knots(kn, tchk) - ref).max())
    max_err = max(max_err, err)
    if err > (0.01 if k < 12 else 0.15): print('   knot error mirror', k + 1, round(err, 4))
    R = D[k] / 2
    m = dict(
        index=k + 1,
        t_cross=cross[k],
        gap=round(cross[k] - cross[k - 1], 2) if k else None,
        anchor=('F13 + 14.2（点燃 4.2 + 保持 10）' if k == 0 else 'F15 tragen!（加速的终点）' if k == 9 else
                '尾声第一声钟（强拍 1125.55）' if k == 10 else '尾声最响的一下：白的冲击从这一面开始' if k == 11 else
                'F16 终和弦：带走座位（剪 2）' if k == 12 else ('强拍吸附 %+.2f s' % snap[k] if snap[k] is not None else '公比数列')),
        phase=1 if k < 10 else 2,
        pulse_EV=PULSE[k],
        diameter_m=round(D[k], 2),
        radius_m=round(R, 2),
        rim_band_m=round(0.02 * D[k], 3),
        rim_boss_count=int(round(math.pi * (D[k] - 0.02 * D[k]) / 1.5)),
        tlv_tiles_across=round(D[k] / 40.0, 3),
        near_rim_azimuth_deg=AZ[k],
        near_rim_distance_m=round(D_NEAR[k], 2) if k < 12 else round(R, 1),
        centre_xz=[round(float(c[0]), 3), round(float(c[2]), 3)],
        cabin_rim_clearance_m=round(cabin_rim_clearance(k), 2),
        knob_cabin_clearance_m=round(knob_clearance(k), 2) if k < 12 else None,
        speed_travel_mps=round(V_A[k], 3) if k < 12 else None,
        speed_cross_mps=round(V_C[k], 3) if k < 12 else round(float((y13(F16) - y13(F16 - 0.05)) / 0.05), 3),
        decel=dict(hold_s=HOLD[k], T_dec_s=T_DEC[k]) if k < 12 else None,
        emission_k=EMIT_K[k],
        visibility_knots=queue_vis(k),
        dissolve=dict(start=cross[k], end=round(cross[k] + DISSOLVE, 2), dust=250, dust_slot=k % 3) if k < 12 else None,
        active=[round(queue_vis(k)[0][0] - 1.0, 2), round(cross[k] + DISSOLVE + 0.5, 2)] if k < 12 else [round(F14 - 1.0, 2), round(F16, 2)],
        motion=dict(kind='hermite', unit='world y of the face point under the eye (m)', knots=kn),
    )
    if k == 12:
        m['far_depth_m'] = {'F14': round(float(depth13(F14)), 1), 'F16-10': round(float(depth13(T13A)), 1)}
        m['rim_depression_knots_deg'] = [[round(float(a), 2), round(float(b), 3), round(float(c), 3)] for a, b, c in zip(phi_t, phi_k, phi_m)]
        m['scheme13'] = SCHEME13
        if RIM_SOFT is not None:
            m['rim_soft'] = RIM_SOFT
        m['face_emission_extra'] = dict(EV=2.7, t=[1138.78, T_PLATEAU_END], shape='EV-linear (0.36 EV/s; r3 C3: +3 -> +2.7); none during the 1.2-s impact',
                                        rule='保持时向下看 APL ≈ 220，不亮过 VR 的白 224（§6·9 → 10）')
        m['takes_seat_at'] = F16
    mirrors.append(m)
log('Hermite 节点表与闭式运动的最大误差 %.4f m（第 1–12 面 ≤ 0.01 m；第 13 面在 5 km 深处按相对误差 ≤ 1e-5）：%s' % (max_err, 'OK' if max_err <= (0.05 if SCHEME13 != 'H' else 0.15) else 'FAIL'))
ok_all &= max_err <= (0.05 if SCHEME13 != 'H' else 0.15)
log('')
log('全部核对：%s' % ('PASS' if ok_all else 'FAIL'))

out = dict(
    about='蓝白 · 十三面白铜镜的两段时间表（圣经 v2.1 §6·9 定稿 E20）。镜子套件的唯一数据源：车厢驱动、天空、第 9 幕组装、第 10 幕都读它。'
          '由 Mirrors/Tools~/schedule/make_schedule.py 从 FromLocal/cues.json 生成，不要手改。'
          '不要用 cues.json 的 derived.mirror_r = 1.2265 与 mirror_crossings_*（E1、E20）：本地 timeline_v1 的 starCross 请换成本文件的 t_cross。',
    version='1.0',
    generated_from=dict(cues='FromLocal/cues.json', bible='Art/ART_BIBLE.md v2.1 §6·9 9c、§6·9→10、§1.8、§4.8、§8.1 #11'),
    conventions=dict(
        coords='Unity 世界，米，Y 上；车固定在原点、车头 +Z；方位 0° = +Z，负 = 左（圣经：银心 −30°）',
        eye=[float(x) for x in EYE], eye_source='Gate/GateLayout_v2.json cameras.U7（CONTROL §3；本地若换眼位，改这里重跑）',
        crossing='镜面上位于眼睛正下方那一点到达眼高（y = 1.70）的时刻；车厢的扫光线、侵蚀、脉冲都从这一刻起',
        motion='motion.knots = [t, y, dy/dt] 的三次 Hermite 节点；在节点之间用标准 Hermite 基插值；节点范围之外取端点（镜子不活动）',
        face_height='y 是镜面在车正下方那一点的世界高度。镜面是凸的（镜心比镜缘高 sagitta），镜心位置 = centre_xz，镜缘平面 = y − sagitta·(1 − (r_car/R)²)',
        convexity=dict(sagitta_over_diameter=0.015, note='圣经 §6·9“凸 1.5%”：取 sagitta = 1.5% × 直径（反射的银河像鱼眼一样弯）'),
    ),
    labels=dict(F13=F13, F14=F14, F15=F15, F16=F16, ignition_full=round(F13 + 4.2, 2), first_mirror=T1),
    phase1=dict(r=round(R1, 4), first_gap=round(gaps[0], 2), last_gap=2.5, mirrors='1–10', rule='间隔 2.5 s × r^k 从 F15 往回排；内部吸附到 ±0.8 s 内最近的强拍，间隔不增、≥ 2.5 s'),
    phase2=dict(mirrors='11–13', rule='尾声的三声钟：1125.55、1137.58（尾声最响，白的冲击）、F16'),
    pulse=dict(EV=0.35, rise_s=0.08, fall_s=0.35, peak_at='t_cross', shape='EV 线性', helper='EXPO_UP（w = ΔEV / (4 − b)，b = S9a/S9b 的 +0.30 → w = 0.095）',
               mirrors=[1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11], none_for=[12, 13], note='第 12 面 = 白的冲击，第 13 面 = 剪 2'),
    ornament=dict(rim_band_frac_of_diameter=0.02, rim_boss_pitch_m=1.5, rim_boss_diameter_m=0.6, tlv_tile_m=40.0,
                  note='乳钉与 TLV 纹按绝对尺寸在 shader 里平铺：越大的镜子纹样越密，眼睛数得出来（§6·9）'),
    face=dict(albedo_metal='#D6CCB4', smoothness=0.94, polish_ripple='±0.02', emission='反射的天 × emission_k × visibility(t)',
              screen_target='#CDBF9C（白铜色调的银河）', column_emission=0.3, column_from='F14'),
    rim=dict(albedo_metal='#C9A873', smoothness=0.75),
    back=dict(albedo='#4F7A66', smoothness=0.35, metallic=0, screen_max='#1E3B34'),
    dissolve=dict(duration_s=DISSOLVE, direction='镜缘 → 镜心（FBM clip）', dust_per_mirror=250, max_simultaneous=3, dust_colour=['#CDBF9C', '#F2F6FF'],
                  dust_fade_s=4.0, dust_rise_mps='≤ 1.0', slots=3),
    cabin=dict(sweep_line=dict(thickness_m=0.02, screen='#DCE8FF', set='#8D95FF', set_EV=1.89, follows='镜面在车下那一点的高度 y(t)'),
               erosion_per_mirror=0.027, erosion_s=1.2, erosion_mirrors='1–12（0.65 → 0.97），第 13 面 0.97 → 1 并带走座位',
               rim_light=dict(kelvin=8000, peak_E=0.3, grey_card='#38414F', where='离车最近的镜缘点（near_rim_azimuth_deg / near_rim_distance_m，高度 = 镜缘平面）',
                              culling='Player + PlayerLocal（+ Bus）', window='穿越前 2 s → 穿越后 1 s')),
    white=dict(impact_from_mirror=12, file='Act10_White/WhiteSchedule.json'),
    mirrors=mirrors,
)
json.dump(out, open(os.path.join(MIR, 'MirrorSchedule.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
os.makedirs(os.path.join(MIR, 'Docs~'), exist_ok=True)
open(os.path.join(MIR, 'Docs~', 'schedule_check.txt'), 'w', encoding='utf-8').write('\n'.join(lines) + '\n')

# ------------------------------------------------------------------ figure
try:
    import matplotlib; matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    plt.rcParams['font.family'] = ['DejaVu Sans']
    fig, ax = plt.subplots(2, 1, figsize=(14, 8), dpi=110, gridspec_kw=dict(height_ratios=[3, 1]))
    tp = np.arange(1015, 1152, 0.02)
    for k in range(12):
        m = (tp >= mirrors[k]['active'][0]) & (tp <= mirrors[k]['active'][1])
        ax[0].plot(tp[m], -(y_of(k, tp[m]) - EYE[1]), lw=1.4, label='%d (D %.0f m)' % (k + 1, D[k]))
    m = tp >= F14
    ax[0].plot(tp[m], depth13(tp[m]), 'k', lw=2, label='13 (D 2400 m)')
    ax[0].set_yscale('symlog', linthresh=10); ax[0].invert_yaxis(); ax[0].set_ylim(7000, -30)
    for c in cross: ax[0].axvline(c, color='0.85', lw=0.6, zorder=0)
    for lab, tv in (('F13', F13), ('F14', F14), ('F15', F15), ('F16', F16)):
        ax[0].axvline(tv, color='C3', lw=0.8); ax[0].text(tv, -25, lab, color='C3')
    ax[0].set_ylabel('depth of face below the eye (m, symlog)'); ax[0].legend(ncol=7, fontsize=7, loc='lower left')
    ax[0].set_title('Lanbai · thirteen mirrors · two phases (r = %.4f to F15 tragen!, coda bells)' % R1)
    pul = np.zeros_like(tp)
    for k in range(11):
        x = tp - cross[k]
        pul = np.maximum(pul, np.where((x > -0.08) & (x <= 0), 0.35 * (x + 0.08) / 0.08, np.where((x > 0) & (x < 0.35), 0.35 * (1 - x / 0.35), 0)))
    ax[1].plot(tp, pul, 'C0'); ax[1].set_ylabel('pulse ΔEV'); ax[1].set_xlabel('timeline t (s)')
    for c in cross: ax[1].axvline(c, color='0.85', lw=0.6, zorder=0)
    fig.tight_layout(); fig.savefig(os.path.join(MIR, 'Docs~', 'schedule.png')); plt.close(fig)
except Exception as e:
    print('figure skipped:', e)
sys.exit(0 if ok_all else 1)
