# -*- coding: utf-8 -*-
"""The static fallback cookie for the 7a sun (final review #9): Lanbai/SeaCausticsCookie frozen at clock 0, 256 x 256,
the same floor (0.25) and gain (0.3) on the same two-layer min of Caustics_8x8_2048 (numpy copy of the shader).
Grey RGB + the same value in ALPHA (a built-in directional cookie reads alpha).
  ~/bpy/bin/python Sea/Tools~/make_cookie.py   ->  Sea/Textures/CausticsCookie_Static_256.png"""
import os

import numpy as np
from PIL import Image

KIT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
N, GRID, FRAMES, MIN_NORM = 256, 8, 64, 2.45
FLOOR, GAIN = 0.25, 0.3


def main():
    atlas = np.asarray(Image.open(os.path.join(KIT, 'Textures', 'Caustics_8x8_2048.png')).convert('L'), np.float64) / 255.0
    fp = atlas.shape[0] // GRID

    def frame(uv, f):
        f = int(f) % FRAMES
        col, row = f % GRID, f // GRID                                   # image rows top-down: row r = v from the top
        u = (uv[..., 0] % 1.0) * fp; v = (1.0 - (uv[..., 1] % 1.0)) * fp
        x = (np.floor(u).astype(int) % fp) + col * fp; y = (np.floor(v).astype(int) % fp) + row * fp
        s = np.minimum(atlas[y, x], 0.999)
        return 2.0 * np.log((1 + s) / (1 - s))

    def layer(uv, ph):
        f = ph * FRAMES; f0 = np.floor(f)
        return frame(uv, f0) * (1 - (f - f0)) + frame(uv, f0 + 1) * (f - f0)

    g = (np.arange(N) + 0.5) / N
    U, V = np.meshgrid(g, g[::-1])
    uv = np.stack([U, V], -1)
    A = layer(uv * 2.0, 0.0)
    B = layer(uv + np.array([0.31, 0.57]), 0.37)
    c = np.clip(FLOOR + GAIN * np.minimum(A, B) * MIN_NORM, 0, 1)
    c8 = np.round(c * 255).astype(np.uint8)
    Image.fromarray(np.stack([c8, c8, c8, c8], -1), 'RGBA').save(os.path.join(KIT, 'Textures', 'CausticsCookie_Static_256.png'))
    print('cookie mean %.3f min %.3f max %.3f' % (c.mean(), c.min(), c.max()))


if __name__ == '__main__':
    main()
