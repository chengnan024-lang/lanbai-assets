# -*- coding: utf-8 -*-
"""河伯宫殿 · 布局的唯一数据源（不依赖 bpy）。

坐标：**PalaceRoot 局部 = Unity 轴**（x 右、y 上、z 前，米）。原点 = 车的根在 F7 停车时的位置。
世界里：车固定在原点、车头朝 +Z（跑步机），所以 PalaceRoot.position(t) = -car(t)（car 是车在宫殿坐标里的位置）。
车的运动按圣经 v2.1 §6·7b：
  前进 0 → 3.5 m/s（F5 → F5 + 23 s，smoothstep）；3.5 m/s 滑行；F6 + 4.7（740.26）起 8 s 刹停（smoothstep）；F7 停在门前。
  沉降 1.0 → 0（F5 → 668.6，smoothstep）；F7s 起 0 → 1.5 m/s（8 s，smoothstep），之后 1.5 m/s（7c 一直到出海）。
所有时刻用圣经 §2.1 的秒（cues.json 里还没有 v2.1 的子标签；本地加进 F_sub 以后按标签取）。
"""
import json
import math

import numpy as np

# ---------------------------------------------------------------- 时刻（圣经 v2.1 §2.1 / §6·7b，时间轴秒）
CUES = {
    'F5': 644.96, 'F5p': 655.86, 'F5q': 675.36, 'F5r': 708.86, 'F6': 735.56, 'F7': 748.26,
    'F7e': 777.36, 'F7s': 796.86, 'F7p': 812.36, 'F8': 835.16, 'F8a': 848.86, 'F8b': 877.96, 'F9s': 921.86,
}
T_ACC = (CUES['F5'], CUES['F5'] + 23.0)            # 前进 0 → 3.5
T_SETTLE = (CUES['F5'], 668.6)                      # 沉降 1.0 → 0
T_BRAKE = (CUES['F6'] + 4.7, CUES['F7'])            # 740.26 → 748.26
T_SINK = (CUES['F7s'], CUES['F7s'] + 8.0)           # 沉降 0 → 1.5
T_QUE = 668.6                                       # 右边那座紫贝阙在车左 9 m 经过
T_LAMPS = [672.0, 677.1, 682.3, 687.4, 692.6, 697.7, 702.8, 708.0, 713.1, 718.3, 723.4, 728.6]   # 12 对灯依次经过
T_POEM = (714.0, 727.5, 730.5)                      # 河伯诗：出现、开始退场、退场完（不归宫殿，用来留位置）
T_HOT_END = CUES['F8'] + 40.0                       # 宫殿热点一直到 7c 的前 40 秒
V_GLIDE = 3.5
V_SETTLE0 = 1.0
V_SINK = 1.5

EYE = np.array([0.55, 1.70, 2.05])                  # 主座位眼位（车相对，Unity）= Gate/GateLayout_v2.json cameras.U7
HFOV = 90.0
ASPECT = 16.0 / 9.0


def _ss_int(u):
    """∫0^u smoothstep = u^3 - u^4/2（smoothstep = 3u²−2u³）。"""
    u = np.clip(u, 0.0, 1.0)
    return u ** 3 - 0.5 * u ** 4


def _ramp_dist(t, t0, t1, v0, v1):
    """速度从 v0 到 v1 走 smoothstep（t0 → t1），返回 t0 起走过的距离（t < t0 为 0，t > t1 按 v1 继续）。"""
    T = t1 - t0
    u = np.clip((np.asarray(t, float) - t0) / T, 0.0, 1.0)
    d = v0 * u * T + (v1 - v0) * T * _ss_int(u)
    extra = np.maximum(np.asarray(t, float) - t1, 0.0) * v1
    return np.where(np.asarray(t, float) < t0, 0.0, d + extra)


def _z_raw(t):
    t = np.asarray(t, float)
    a = _ramp_dist(t, T_ACC[0], T_ACC[1], 0.0, V_GLIDE)                        # 0→3.5，之后 3.5 一直走
    b = _ramp_dist(t, T_BRAKE[0], T_BRAKE[1], 0.0, -V_GLIDE)                   # 刹车：减掉的那一部分
    return a + b


Z_STOP_RAW = float(_z_raw(CUES['F7']))


def car_z(t):
    """车根在宫殿坐标的 z（F7 = 0）。"""
    return _z_raw(t) - Z_STOP_RAW


def car_y(t):
    """车根在宫殿坐标的 y：F7 停车高度 = 0；F5 之前每秒沉 1.0，F5 → 668.6 减到 0；F7s 起往下沉。"""
    t = np.asarray(t, float)
    settle_total = V_SETTLE0 * (T_SETTLE[1] - T_SETTLE[0]) * 0.5
    y_settle = settle_total - _ramp_dist(t, T_SETTLE[0], T_SETTLE[1], V_SETTLE0, 0.0)
    y_before = settle_total + V_SETTLE0 * np.maximum(T_SETTLE[0] - t, 0.0)
    y = np.where(t < T_SETTLE[0], y_before, y_settle)
    return y - _ramp_dist(t, T_SINK[0], T_SINK[1], 0.0, V_SINK)


def car(t):
    t = np.asarray(t, float)
    return np.stack([np.zeros_like(t), car_y(t), car_z(t)], -1)


def eye(t):
    return car(t) + EYE


# ---------------------------------------------------------------- 场地（宫殿坐标，Unity 轴）
SHINDAO_Y = -6.0          # 神道（台地顶面）的高度：车在它上面 6 m 滑行，宫灯的光从下面来
EDGE_X = -8.0             # 台地边沿（崖口）的 x：右列灯在它里面 1 m；从眼睛到石壁 8.55 m（≥ 8）
LIP_DROP = 17.0           # 台地边沿的下缘：停车处下方 17 m 的眼睛高度（F7p 越过）
AXIS_X = -18.0            # 神道轴线（门在轴线上、车左 18 m）
COL_R_X = -9.0            # 右列灯（靠崖）
COL_L_X = -27.0           # 左列灯
LAMP_FLAME_H = 1.75       # 灯焰离地高度（长信宫灯式灯，总高 2.0 m）
PODIUM_H = 6.0            # 台基高
HALL_W, HALL_H = 60.0, 30.0
# 门：从 F7 的眼睛看在 −27°
DOOR_Z = EYE[2] + (EYE[0] - AXIS_X) / math.tan(math.radians(27.0))
PROMONTORY_Z = DOOR_Z - 14.5   # 大殿前的崖口：台地在这里向右伸出去托住大殿（停车处前 ~24 m）


def lamp_z():
    return [float(car_z(t) + EYE[2]) for t in T_LAMPS]


def que_z():
    return float(car_z(T_QUE) + EYE[2])


def azimuth_of(p, t):
    """从 t 时刻的眼睛看点 p 的方位（度，右正）与仰角。"""
    e = eye(t)
    d = np.asarray(p, float) - e
    az = math.degrees(math.atan2(d[0], d[2]))
    el = math.degrees(math.atan2(d[1], math.hypot(d[0], d[2])))
    return az, el, float(np.linalg.norm(d))


def summary():
    door = np.array([AXIS_X, SHINDAO_Y + PODIUM_H + 4.0, DOOR_Z])
    rows = []
    for name, t in [('F5', CUES['F5']), ('F5p', CUES['F5p']), ('que', T_QUE), ('706', 706.0), ('poem 714', 714.0),
                    ('poem out 730.5', 730.5), ('F6', CUES['F6']), ('brake', T_BRAKE[0]), ('F7', CUES['F7']),
                    ('F7s', CUES['F7s']), ('F7p', CUES['F7p']), ('F8', CUES['F8']), ('hot end', T_HOT_END)]:
        az, el, d = azimuth_of(door, t)
        c = car(t)
        rows.append((name, t, float(c[1]), float(c[2]), az, el, d))
    return rows


if __name__ == '__main__':
    print('Z_STOP_RAW %.2f  DOOR_Z %.2f  que_z %.2f' % (Z_STOP_RAW, DOOR_Z, que_z()))
    print('lamp z', ['%.1f' % z for z in lamp_z()])
    print('%-16s %8s %8s %9s %8s %7s %7s' % ('', 't', 'car y', 'car z', 'door az', 'el', 'dist'))
    for r in summary():
        print('%-16s %8.2f %8.2f %9.2f %8.2f %7.2f %7.1f' % r)
