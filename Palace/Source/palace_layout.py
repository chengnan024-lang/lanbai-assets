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

FRAME = json.load(open(os.path.join(REPO, 'Act07_Sea', 'PalaceFrame_约定.json')))
CUES = dict(FRAME['labels_used'])
T_QUE = 668.6
T_LAMPS = [l['abreast_t'] for l in FRAME['lamps'] if l['group'] == 'avenue'][::2]
T_HOT_END = CUES['F8'] + 40.0
EYE = np.array([0.55, 1.70, 2.05])
BUS_Y_STOP = FRAME['frame']['bus_origin_y_stop']

EDGE_X = FRAME['terrace']['edge_x']
LIP_Y = FRAME['terrace']['lip_bottom_y']
AXIS_X = FRAME['avenue']['axis_x']
COL_R_X, COL_L_X = FRAME['avenue']['columns_x']
HALL = FRAME['hall']
PLAT = HALL['platform']
DOOR_Z = HALL['front_z']
QUE = FRAME['que']
LAMPS = FRAME['lamps']
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
