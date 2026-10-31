# -*- coding: utf-8 -*-
"""河伯宫殿 · 布局（不依赖 bpy）。**宫殿坐标 = 海的约定 `Act07_Sea/PalaceFrame_约定.json`**（总导演 10-24：照它做）：
  米，Unity 轴（x 右、y 上、z = 车头方向）；x = 0 车路，y = 0 台地顶，z = 0 F5 时的车根。
  R_Palace.position = −busPos(t)；busPos 由海的 act07_motion 算（车停在台地顶上方 2.5 m）。
本文件只把海的数据读进来、给宫殿的建模 / 渲染用，再加上宫殿自己的东西（灯的高度细分、灯焰、门、相机）。"""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Act07_Sea', 'Tools~'))
import act07_motion as M  # noqa: E402

# 第 10 轮 (c)：海的新约定在 pkg/sea dcab186、还没合 main——先钉一份在 Source/ 里（合了以后删掉这份，回到 Act07_Sea 的那份）
_PINNED = os.path.join(HERE, 'PalaceFrame_约定_pkg_sea_f85c4b8.json')
FRAME = json.load(open(os.environ.get('PALACE_FRAME') or (_PINNED if os.path.exists(_PINNED) else os.path.join(REPO, 'Act07_Sea', 'PalaceFrame_约定.json')), encoding='utf-8'))
CUES = dict(FRAME['labels_used'])
T_QUE = 668.6
T_LAMPS = [l['abreast_t'] for l in FRAME['lamps'] if l['group'] == 'avenue'][::2]
T_HOT_END = CUES['F8'] + 40.0
EYE = np.array([0.55, 1.70, 2.05])
BUS_Y_STOP = FRAME['frame']['bus_origin_y_stop']

EDGE_X = FRAME['terrace']['edge_x']
LIP_Y = FRAME['terrace']['lip_bottom_y']

# 总导演 10-26：被崖口挡住多半的灯，车下沉时按几何遮挡在 >= 1 s 里淡掉（只往“藏”的方向；一盏灯要么读得出，要么不在）。
# 遮挡体按保守的近似：崖口顶边的斜坡（约定 terrace.edge_slope，坡宽、坡深取不带起伏的下限）+ 竖直石壁（外凸到 edge + 0.9）
# + 参差的下唇（最低处 lip − 1.2、往里收 0.6）。视线从坡上越过，或从下唇下面（下缘以下台地没有底面）穿过，才算看得见。
_ES = FRAME['terrace'].get('edge_slope')
_ESD = (_ES or {}).get('drop_m', 1.6)
CLIFF = dict(edge_x=FRAME['terrace']['edge_x'], lip_low=LIP_Y - 1.2, lip_x=FRAME['terrace']['edge_x'] - 0.6, wall_out=FRAME['terrace']['edge_x'] + 0.9,
             slope_w=(_ES['width_m'] if _ES else 0.8), slope_d=(min(_ESD) if isinstance(_ESD, list) else _ESD),
             slope_z=((_ES or {}).get('z', [48.0, 306.0]) + (_ES or {}).get('z_full', [54.0, 296.0])),
             bump=0.52, pad=0.08, fade_s=1.0, sink=1.5)


def cliff_vis(e, c, t=None):
    """眼 e、灯 c（宫殿坐标）之间的视线越过崖口 → 可见度 0..1（= Lanbai/PalaceFlame 的 LanbaiCliffVis）。
    复核 r10d #2：F8（835.16）起，一盏灯不会比 F8 开始那一刻更亮——那时被崖口藏着的灯，F8 里不再回来。"""
    v = cliff_margin(e, c)[2]
    if t is not None and t >= CUES['F8']:
        v = min(v, cliff_margin(cliff_eye_f8(), c)[2])
    return v


def cliff_eye_f8():
    """F8 那一刻主座位眼睛的宫殿坐标（带 F7 的 C 稿转角和横漂；shots._EYE_C）。Unity 里是常数 _CliffEyeF8。"""
    import shots
    return eye(CUES['F8']) + np.array([shots._EYE_C[0], 0.0, shots._EYE_C[1]])


def cliff_halo_r(e, c, R):
    """复核 r10d #1：晕的半径不超过视线越过崖口的余量（换到灯处 ÷ tL，再 × 0.6），晕不会碰到崖口的剪影，就不会被直线切。"""
    m, tL, _ = cliff_margin(e, c)
    if tL <= 0.0:
        return R
    g = min(1.0, max(0.0, -e[1] / 2.0))          # 只在眼睛低于台地顶（y < 0）以后收：在上面往下看时晕没被切（proc_l），不动
    return R + g * (min(R, max(m, 0.0) * 0.6 / tL) - R)


def cliff_margin(e, c):
    """返回（余量 m、视线在崖口处的参数 tL、可见度）。没有崖口挡的情况 m = 1e9、tL = 0。"""
    C = CLIFF
    ex, ey, ez = e
    cx, cy, cz = c
    if ex <= C['wall_out'] or cx >= C['edge_x']:
        return 1e9, 0.0, 1.0
    def at(x):
        t = (x - ex) / (cx - ex)
        return ey + (cy - ey) * t, ez + (cz - ez) * t, t
    def ss(a, b, x):
        u = min(1.0, max(0.0, (x - a) / (b - a)))
        return u * u * (3 - 2 * u)
    big = C['slope_w'] > 1.0
    m_over = 1e9
    for k in (0.0, 0.05, 0.1, 0.15, 0.2, 0.3, 0.4, 0.5, 0.65, 0.8, 1.0):
        y, z, _ = at(C['edge_x'])
        z0, z1, zf0, zf1 = C['slope_z']
        w = ss(z0, zf0, z) * (1.0 - ss(zf1, z1, z)) if big else 0.0
        W = 0.8 + w * (C['slope_w'] - 0.8)
        D = 1.6 + w * (C['slope_d'] - 1.6)
        x = C['edge_x'] - W * (1 - k)
        if big:
            kr = 0.15
            s = (k * k / (2 * kr) if k < kr else k - kr / 2) / (1 - kr / 2)
        else:
            s = k ** 1.5
        yr, _, _ = at(x)
        m_over = min(m_over, yr - (-D * s + C['bump'] * w * math.sin(math.pi * k)))   # 坡面起伏的上包络（terrace.py：≤ 0.51 m × sin πk）
    for j in (0.25, 0.5, 0.75, 1.0):                                 # 坡底往下 4.4 m 内石壁外凸从 0 长到最多 0.9 m（terrace.py）
        yw, _, _ = at(C['edge_x'] + 0.9 * j)
        m_over = min(m_over, yw - (-D - 4.4 * j))
    m_over -= C['pad']
    yl, _, te = at(C['lip_x'])
    m_under = C['lip_low'] - yl - C['pad']                            # 从下唇下面穿过
    m = max(m_over, m_under)
    width = max(0.1, C['fade_s'] * C['sink'] * (1.0 - te))          # 车下沉 1 s，视线在崖口处移动的米数
    return m, te, min(1.0, max(0.0, m / width))
AXIS_X = FRAME['avenue']['axis_x']
COL_R_X, COL_L_X = FRAME['avenue']['columns_x']
HALL = FRAME['hall']
PLAT = HALL['platform']
DOOR_Z = HALL['front_z']
QUE = FRAME['que']
LAMPS = list(FRAME['lamps'])
# 第 4 轮（美术评审 r3 阻断 6）：圣经“紫贝阙……宝贝壳贴面只在它的灯旁泛出 #7A4A6E”——每座阙前各一盏“它的灯”（宫殿加的，海的约定里没有）
# 第 8 轮（评审 r5 #6）：阙基高 3 m、比阙身宽 0.8 m，1.85 m 的灯焰在阙基顶面以下，整面宝贝贴面都在阙基的影子里；
# 阙前这两盏做成高 3.85 m 的立灯（灯焰 3.62 m，高过阙基 0.6 m），并恢复靛光：暖 + 靛照在 #5B2A4E 上才是 #7A4A6E
QUE_LAMP_H = 3.85
QUE_LAMP_INDIGO = 0.45        # 第 10 轮（终审 #2）：标准亮度；靛 ×0.6，暖 : 靛 让 #5B2A4E 的贝在灯旁读成 #7A4A6E 一带（h 330–340），不偏蓝紫
QUE_LAMP_GAIN = 1.0          # 第 10 轮（终审 #2）：回到标准亮度（第 8 轮的 ×4 读成霓虹广告牌）
QUE_LAMPS = [dict(id='Lamp_Q%d' % (k + 1), group='que', pos=[q['pos'][0], 0.0, round(q['pos'][2] - q['footprint'][1] / 2 - 1.6, 3)],
                  yaw_deg=0.0, height_m=QUE_LAMP_H, indigo_lift=0.0, indigo_range=5.0, gain=QUE_LAMP_GAIN, indigo_gain=QUE_LAMP_INDIGO, flame_pos=[q['pos'][0], QUE_LAMP_H - 0.23, round(q['pos'][2] - q['footprint'][1] / 2 - 1.6, 3)])
             for k, q in enumerate(FRAME['que'])]
LAMPS += QUE_LAMPS
HOUSES = FRAME['fish_houses']
WEEDS = FRAME['seaweed']
FISH = FRAME['fish']


def car(t):
    t = np.atleast_1d(np.asarray(t, float))
    out = np.array([[0.0, BUS_Y_STOP + (M.depth(CUES['F7']) - M.depth(tt)), M.fwd(tt)] for tt in t])
    return out[0] if out.shape[0] == 1 else out


def eye(t):
    return car(t) + EYE


def flame_points():
    return np.array([l['flame_pos'] for l in LAMPS], float)


def azimuth_of(p, t):
    e = eye(t)
    d = np.asarray(p, float) - e
    return (math.degrees(math.atan2(d[0], d[2])), math.degrees(math.atan2(d[1], math.hypot(d[0], d[2]))),
            float(np.linalg.norm(d)))


if __name__ == '__main__':
    door = (AXIS_X, PLAT['height_m'] + 3.75, DOOR_Z)
    for name, t in [('F5', CUES['F5']), ('F5p', CUES['F5p']), ('que', T_QUE), ('706', 706.0), ('714', 714.0),
                    ('730.5', 730.5), ('F6', CUES['F6']), ('F7', CUES['F7']), ('F7p', CUES['F7p']), ('hot', T_HOT_END)]:
        c = car(t)
        print('%-6s t %7.2f car y %7.2f z %7.2f  door az/el/d %7.2f %6.2f %6.1f' % ((name, t, c[1], c[2]) + azimuth_of(door, t)))
