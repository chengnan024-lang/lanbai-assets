# -*- coding: utf-8 -*-
"""第 6 幕体积云的二维覆盖率图（给 shader，`Lanbai/CloudVolume`）。act06_vol.py 的覆盖率函数在 shader 里逐样本算太贵，烘成一张：
  R = 上层 A 合着（F1 之前）    G = 上层 A 谷散开以后（F1 + 6 s 起）   shader 按 _CovOpen.x 在两张之间插（A 对开谷是线性的）
  B = 下层 B 的底子覆盖率 c0    A = 下层 B 的空隙（车下那块、朝日那个湾，取大）
      shader：c = max(c0, 0.97 (1 − op)) · (1 − op · gap)，op = _CovOpen.y（305.4 → 311 smoothstep），和 act06_vol.covB 一样
范围 ±24 km（`EXTENT`），1024²（47 m / 像素），镜像平铺（远处一直铺到地平线，不见接缝），线性 sRGB 关（数据）。
-> Act06_Dawn/Textures/Act06_CloudCoverage.png + .json（范围、对应的时刻）"""
import os
import sys
import json
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import act06_vol as AV  # noqa: E402

EXTENT = 24000.0
N = 1024


def main():
    S = AV.scene()
    xs = (np.arange(N) + 0.5) / N * 2 * EXTENT - EXTENT
    X, Z = np.meshgrid(xs, xs[::-1])            # row 0 = +z (far forward): texture v = 1 at the top
    x, z = X.ravel().astype(np.float32), Z.ravel().astype(np.float32)
    A = [l for l in S.layers if l.name == 'A'][0]
    B = [l for l in S.layers if l.name == 'B'][0]
    g = AV.GEO
    a_closed = A.cov(x, z, g['A']['valley']['open'][0] - 1.0)
    a_open = A.cov(x, z, g['A']['valley']['open'][1] + 1.0)
    # B's pieces, taken apart the way the shader puts them together
    b_open_t = g['B']['open'][1] + 1.0
    c_full = B.cov(x, z, g['B']['open'][0] - 1.0)               # closed: max(c0, 0.97)
    # c0 and gap from the open state and the gap masks themselves
    gap = np.maximum(S.lake_of(x, z, g['B']['column'], 3.0), S.lake_of(x, z, g['B']['bay'], 4.0))
    c0 = np.clip(S.covB_raw(x, z), 0, 1)
    img = np.stack([a_closed, a_open, np.clip(c0, 0, 1), gap], -1).reshape(N, N, 4)
    out = os.path.join(AV.KIT, 'Textures')
    os.makedirs(out, exist_ok=True)
    Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(out, 'Act06_CloudCoverage.png'))
    json.dump(dict(extent_m=EXTENT, size=N, wrap='mirror', srgb=False,
                   channels=dict(R='A closed (t < %.2f)' % g['A']['valley']['open'][0], G='A open (t > %.2f)' % g['A']['valley']['open'][1],
                                 B='B c0', A='B gap (column, sun bay)'),
                   a_open=g['A']['valley']['open'], b_open=g['B']['open'], check_closed_B_max_err=float(np.abs(np.maximum(c0, 0.97) - c_full).max())),
              open(os.path.join(out, 'Act06_CloudCoverage.json'), 'w'), indent=1)
    print('ok', img.shape, 'B closed check', float(np.abs(np.maximum(c0, 0.97) - c_full).max()))


if __name__ == '__main__':
    main()
