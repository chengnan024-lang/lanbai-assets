# -*- coding: utf-8 -*-
"""蓝白 · 共用体积云的密度体（128³，三个方向都周期）。起点是阿白本地的 generate_density_only.py（FromLocal/full_preview/
20261025-0103/review_sources/，2026-10-25，阿白写的 VolumeCloudDeck 用它）：四个八度的值噪声，R 主体、G 细节。
这里改了三处（README_Volume §2）：
  1. R 主体换成 Perlin-Worley（低频梯度噪声被反 Worley 重映射）：值噪声叠出来是棉花糖一样的软团，积云要的是一个个鼓起的头；
  2. G 细节换成三个八度的 Worley（边缘侵蚀用，越大越蓬）；B 是一个低频的 Worley（大团之间的空隙）；
  3. 轴序：Unity 的 Texture3D.SetPixelData 是 x 最快、再 y、再 z，numpy 要写成 [z, y, x] 再 tobytes。阿白的版本写成了
     [x, y, z]（x、z 对调）；因为三个轴都是同一种各向同性噪声，看不出来，这里改对，以后放各向异性的东西不会出错。
python vol_density.py <out_dir>  -> <out_dir>/CloudVolume128.bytes（RGBA8，128³，[z][y][x]）+ .npy（给参考渲染器）"""
import os
import sys
import numpy as np

N = 128
SEED = 20261025


def _grid(n):
    c = (np.arange(N, dtype=np.float32) + 0.5) * n / N
    return c


def perlin(n, rng):
    """periodic gradient noise, lattice n per side; [z, y, x]"""
    g = rng.normal(size=(n, n, n, 3)).astype(np.float32)
    g /= np.linalg.norm(g, axis=-1, keepdims=True)
    c = _grid(n)
    i = np.floor(c).astype(int)
    f = c - i
    w = f * f * f * (f * (f * 6 - 15) + 10)
    out = np.zeros((N, N, N), np.float32)
    for dz in (0, 1):
        for dy in (0, 1):
            for dx in (0, 1):
                gz = g[(i[:, None, None] + dz) % n, (i[None, :, None] + dy) % n, (i[None, None, :] + dx) % n]
                d = np.stack(np.broadcast_arrays(f[None, None, :] - dx, f[None, :, None] - dy, f[:, None, None] - dz), -1)
                dot = (gz[..., ::-1] * d).sum(-1)
                wz = w if dz else 1 - w
                wy = w if dy else 1 - w
                wx = w if dx else 1 - w
                out += dot * wz[:, None, None] * wy[None, :, None] * wx[None, None, :]
    return out


def worley(n, rng):
    """periodic Worley F1 (0 at the points .. ~1), one point per cell, lattice n; [z, y, x]"""
    pts = rng.random((n, n, n, 3)).astype(np.float32)
    c = _grid(n)
    i = np.floor(c).astype(int)
    f = c - i
    best = np.full((N, N, N), 9.0, np.float32)
    for dz in (-1, 0, 1):
        for dy in (-1, 0, 1):
            for dx in (-1, 0, 1):
                p = pts[(i[:, None, None] + dz) % n, (i[None, :, None] + dy) % n, (i[None, None, :] + dx) % n]
                ddx = dx + p[..., 0] - f[None, None, :]
                ddy = dy + p[..., 1] - f[None, :, None]
                ddz = dz + p[..., 2] - f[:, None, None]
                best = np.minimum(best, ddx * ddx + ddy * ddy + ddz * ddz)
    return np.clip(np.sqrt(best), 0, 1)


def remap(v, a, b, c, d):
    return c + (v - a) / (b - a) * (d - c)


def build():
    rng = np.random.default_rng(SEED)
    pf = perlin(4, rng) * 0.6 + perlin(8, rng) * 0.3 + perlin(16, rng) * 0.1
    pf = np.clip(pf * 1.1 + 0.5, 0, 1)
    w4, w8, w16, w32 = worley(4, rng), worley(8, rng), worley(16, rng), worley(32, rng)
    wb = 1 - (w4 * 0.625 + w8 * 0.25 + w16 * 0.125)                  # billows
    R = np.clip(remap(pf, wb - 1.0, 1.0, 0.0, 1.0), 0, 1)              # Perlin-Worley
    G = 1 - (w8 * 0.625 + w16 * 0.25 + w32 * 0.125)                    # detail erosion
    B = 1 - worley(2, rng)                                             # big gaps
    vol = np.stack([R, G, B, np.ones_like(R)], -1)
    return vol


def main():
    out = sys.argv[1] if len(sys.argv) > 1 else '/tmp/lb/vol'
    os.makedirs(out, exist_ok=True)
    vol = build()
    np.save(os.path.join(out, 'CloudVolume128.npy'), vol[..., :3].astype(np.float16))
    (np.clip(vol, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes()
    open(os.path.join(out, 'CloudVolume128.bytes'), 'wb').write((np.clip(vol, 0, 1) * 255 + 0.5).astype(np.uint8).tobytes())
    for k, ch in enumerate('RGB'):
        v = vol[..., k]
        print(ch, 'mean %.3f p10 %.3f p90 %.3f' % (v.mean(), np.percentile(v, 10), np.percentile(v, 90)))


if __name__ == '__main__':
    main()
