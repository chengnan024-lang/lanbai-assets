# -*- coding: utf-8 -*-
"""透明叠绘估算（FSE = 透明片元数 / 屏幕像素数）：灯晕卡（每盏 3 m × 3 m 的公告板）+ 灯焰卡 + 门口 3 张光卡。
按 Unity 的画法算：公告板四边形在屏幕上的面积（裁到屏幕内、去掉被不透明物挡住的部分不算——Unity 里 ZTest 剔掉的片元
也要光栅化前的 early-Z，按“画了”算偏保守）。车厢玻璃 0.7 FSE 由账本统一加，不在这里。"""
import json
import math
import sys

import numpy as np

import palace_layout as L
from shots import SHOTS
from post import project, cam_basis

W, H = 1920, 1080


def quad_area(shot, centre, half_w, half_h, upright):
    t, yaw, pitch, hfov, _ = SHOTS[shot]
    e = L.eye(t)
    c = np.asarray(centre, float)
    f = e - c
    d = np.linalg.norm(f)
    f /= d
    right = np.cross([0, 1, 0], f)
    right /= np.linalg.norm(right) + 1e-9
    up = np.array([0, 1.0, 0]) if upright else np.cross(f, right)
    P = np.array([c + sx * half_w * right + sy * half_h * up for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
    px, py, zc, _ = project(shot, P, W, H)
    if (zc <= 0.05).any():
        return 0.0
    xs = np.clip(px, 0, W)
    ys = np.clip(py, 0, H)
    return 0.5 * abs(np.dot(xs, np.roll(ys, 1)) - np.dot(ys, np.roll(xs, 1)))


def fse(shot):
    tot = 0.0
    for p in L.flame_points():
        tot += quad_area(shot, p, 1.5, 1.5, False)
        tot += quad_area(shot, p, 0.09, 0.19, True)
    # 门口光卡：每张 20 m 长、宽 1.9 → 6.7 m 的梯形，近似成中线处的公告板面积（偏保守，加 30%）
    H_ = L.HALL
    for k in range(3):
        c = (H_['door_x'], L.PLAT['height_m'] - 1.0, L.DOOR_Z - 10.0)
        tot += 1.3 * quad_area(shot, c, 2.2, 10.0, True) / 3.0 * 3.0 / 3.0
    return tot / (W * H)


if __name__ == '__main__':
    out = {s: round(fse(s), 3) for s in SHOTS}
    print(json.dumps(out, indent=1))
    json.dump(dict(about='透明叠绘 FSE（灯晕 + 灯焰 + 门口光卡），1920×1080、水平 90°；车厢玻璃 0.7 另算', fse=out),
              open('../Docs~/fse.json', 'w'), indent=1, ensure_ascii=False)
