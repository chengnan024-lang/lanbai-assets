"""终审 M-2：镜背“身后的天”的来源，没有极点。
这一幕的天（银河增益 1 时的全部：夜底 + 星空底 + 银河辉光，不含星点）的亮度，按球面上的高斯（σ 0.2 rad ≈ 27° 的反射瓣）
模糊，存成 64 px 的立方图（横十字 256 × 192，单通道，sqrt 编码：值 = sqrt(L / scale)）。shader：
    Lsky = max(lum(星空底), 银河增益(V) × scale × cube(V)²)     （点燃前星空底为主，点燃后就是模糊的天）
    ~/bpy/bin/python bake_back_sky.py   -> Mirrors/Textures/T_MirrorBackSky_Cube.png，scale 打印出来（= _BackSkyScale）"""
import json, math, os, sys
import numpy as np
from PIL import Image
import mirror_port as MP

N = 64
SIGMA = 0.2
OUT = os.path.join(MP.REPO, 'Mirrors', 'Textures', 'T_MirrorBackSky_Cube.png')
LUMA = np.array([0.2126, 0.7152, 0.0722])


def face_dirs(face, n=N):
    """Unity / D3D cube face convention: +X, -X, +Y, -Y, +Z, -Z; (u, v) in [-1, 1], v down the image."""
    a = (np.arange(n) + 0.5) / n * 2 - 1
    u, v = np.meshgrid(a, a)
    one = np.ones_like(u)
    d = {0: (one, -v, -u), 1: (-one, -v, u), 2: (u, one, v), 3: (u, -one, -v), 4: (u, -v, one), 5: (-u, -v, -one)}[face]
    d = np.stack(d, -1)
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def main():
    gl, mat, star, first, prof = MP.A9.state(1045.0)
    g1 = dict(gl); g1['_Udon_GalaxyGain'] = [1.0, 0, 0, 1]
    g0 = dict(gl); g0['_Udon_GalaxyGain'] = [0.0, 0, 0, 1]
    # the glow on a dense sphere sample (equirect 512 x 256, supersampled 2 x 2), weighted by solid angle
    W, H = 512, 256
    lon = (np.arange(W * 2) + 0.5) / (W * 2) * 2 * np.pi - np.pi
    lat = np.pi / 2 - (np.arange(H * 2) + 0.5) / (H * 2) * np.pi
    LO, LA = np.meshgrid(lon, lat)
    d = np.stack([np.cos(LA) * np.sin(LO), np.sin(LA), np.cos(LA) * np.cos(LO)], -1).reshape(-1, 3)
    glow = MP.sky(d, mat, g1) @ LUMA
    glow = glow.reshape(H, 2, W, 2).mean((1, 3))
    d = d.reshape(H, 2, W, 2, 3).mean((1, 3)); d /= np.linalg.norm(d, axis=-1, keepdims=True)
    wsa = np.cos(np.pi / 2 - (np.arange(H) + 0.5) / H * np.pi)[:, None] * np.ones((1, W))
    D = d.reshape(-1, 3); G = (glow * wsa).reshape(-1); Wt = wsa.reshape(-1)
    faces = []
    for f in range(6):
        fd = face_dirs(f).reshape(-1, 3)
        acc = np.zeros(len(fd)); wac = np.zeros(len(fd))
        for i in range(0, len(D), 8192):
            c = fd @ D[i:i + 8192].T
            k = np.exp((c - 1.0) / (SIGMA * SIGMA))             # ~ exp(-theta^2 / (2 sigma^2)) near the axis
            acc += k @ G[i:i + 8192]; wac += k @ Wt[i:i + 8192]
        faces.append((acc / np.maximum(wac, 1e-12)).reshape(N, N))
    scale = float(max(f.max() for f in faces)) * 1.02
    enc = [np.sqrt(np.clip(f / scale, 0, 1)) for f in faces]
    # horizontal cross: row 1 = -X +Z +X -Z ; +Y above +Z ; -Y below +Z
    cross = np.zeros((3 * N, 4 * N))
    pos = {0: (1, 2), 1: (1, 0), 2: (0, 1), 3: (2, 1), 4: (1, 1), 5: (1, 3)}
    for f, (r, c) in pos.items():
        cross[r * N:(r + 1) * N, c * N:(c + 1) * N] = enc[f]
    Image.fromarray((cross * 255 + 0.5).astype(np.uint8)).save(OUT, optimize=True)
    print('wrote', OUT, 'scale (_BackSkyScale) = %.6f' % scale)
    json.dump(dict(scale=scale, sigma_rad=SIGMA, t_ref=1045.0, encoding='sqrt(L / scale)', layout='horizontal cross, Unity face order'),
              open(os.path.join(MP.REPO, 'Mirrors', 'Docs~', 'T_MirrorBackSky_Cube.json'), 'w'), indent=1)


if __name__ == '__main__':
    main()
