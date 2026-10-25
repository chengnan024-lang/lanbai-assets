# -*- coding: utf-8 -*-
"""Lanbai/CloudCard 的数学（numpy 移植，和 Shaders/Lanbai_CloudCard.shader 的 frag 逐行对应）。
参考图、求解器、量具都用它，所以 Unity 里看到的颜色就是这里算出来的颜色（雾、软边、底部融化在 shader 里另乘，
这里的 shade() 只到“卡自己的颜色 + alpha”；fog_mix() 给参考渲染用）。

  rel   = 太阳与视线（中眼 → 卡的枢轴）的水平夹角，0..180°（0 = 太阳在云正后方）
  K(rel)= 三个太阳通道按 rel 分段线性插值（15° → R，80° → G，150° → B，两端钳住）
  c     = SunColor · K(rel) + SkyUpColor · S.r + GroundColor · S.g          （都是线性；SunColor 已含 E）
  c    *= Gain；  a = coverage · Alpha
  太阳在视线左边时 uv.x 镜像（_Mirror：0 关、1 开、2 自动 = 按太阳在哪一边）。
"""
import numpy as np

KEY_ANGLES = (15.0, 80.0, 150.0)


def key_weights(rel):
    a0, a1, a2 = KEY_ANGLES
    w1 = np.clip((rel - a0) / (a1 - a0), 0, 1)          # k0 -> k1
    w2 = np.clip((rel - a1) / (a2 - a1), 0, 1)          # k1 -> k2
    return (1 - w1), w1 * (1 - w2), w2                  # weights of k0, k1, k2 (sum 1)


def rel_angle(los_xz, sun_xz):
    """los, sun: horizontal (x, z) vectors. Returns (rel deg 0..180, sun_on_left bool)."""
    l = np.asarray(los_xz, np.float64) + np.array([1e-5, 0.0])
    s = np.asarray(sun_xz, np.float64) + np.array([1e-5, 0.0])
    l = l / np.linalg.norm(l)
    s = s / np.linalg.norm(s)
    rel = np.degrees(np.arccos(np.clip(l @ s, -1, 1)))
    right = l[1] * s[0] - l[0] * s[1]                  # Unity: x right, z forward; > 0 = sun on the right
    return rel, right < 0


def shade(K, S, a, rel, sun_col, sky_col, gnd_col, gain=1.0, alpha=1.0, mirror=False, tex_per_px=1.0, rim_tame=0.6):
    """K (h,w,3) linear key channels (already x KScale), S (h,w,2) linear (x SScale), a (h,w) coverage.
    tex_per_px: texels per screen pixel (the shader's fwidth footprint); > 1 calms the backlit channel's thin rims."""
    if mirror:
        K, S, a = K[:, ::-1], S[:, ::-1], a[:, ::-1]
    w0, w1, w2 = key_weights(rel)
    k = K[..., 0] * w0 + K[..., 1] * w1 + K[..., 2] * w2
    k = k * (1 - rim_tame * w0 * (1 - a) * np.clip(tex_per_px - 1.0, 0, 1))
    c = (k[..., None] * np.asarray(sun_col) + S[..., 0:1] * np.asarray(sky_col) + S[..., 1:2] * np.asarray(gnd_col))
    return c * gain, a * alpha


def melt(a, v, base_v, melt=(-0.02, 0.10)):
    """Base melt, UV mode (w = 0): v = texture v (0 at the bottom) per pixel."""
    t = np.clip((v - base_v - melt[0]) / max(melt[1], 1e-4), 0, 1)
    return a * t * t * (3 - 2 * t)


def load_card(npz):
    z = np.load(npz)
    return z['K'].astype(np.float64), z['S'].astype(np.float64), z['a'].astype(np.float64)


def fog_mix(c, a, fog_col, fog_amount):
    """LanbaiApplyFog on a straight-alpha card: colour -> fog colour, alpha unchanged."""
    return c * (1 - fog_amount) + np.asarray(fog_col) * fog_amount, a
