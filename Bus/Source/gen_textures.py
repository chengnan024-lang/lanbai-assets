# -*- coding: utf-8 -*-
"""车厢的平铺细节贴图（numpy 生成，可重跑）。法线 = 切线空间、OpenGL（+Y 上，Unity 的约定）。
平铺尺寸写在文件名里；材质的 _DetailTiling = 1 / 平铺米数（uv0 是米制盒投影）。

    ~/bpy/bin/python Bus/Source/gen_textures.py --out Bus/Textures
"""
import argparse
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFont


def height_to_normal(h, metres_per_px, strength=1.0):
    gy, gx = np.gradient(h, metres_per_px)
    n = np.stack([-gx * strength, gy * strength, np.ones_like(h)], -1)     # image rows go down -> +gy flips
    n /= np.linalg.norm(n, axis=-1, keepdims=True)
    return ((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8)


def tile_noise(n, octaves, seed, base=4):
    rng = np.random.default_rng(seed)
    out = np.zeros((n, n))
    amp = 1.0
    for o in range(octaves):
        f = base * 2 ** o
        F = np.zeros((n, n), complex)
        k = rng.standard_normal((f * 2 + 1, f * 2 + 1)) + 1j * rng.standard_normal((f * 2 + 1, f * 2 + 1))
        F[:f + 1, :f + 1] = k[:f + 1, :f + 1]
        F[-f:, :f + 1] = k[f + 1:, :f + 1]
        F[:f + 1, -f:] = k[:f + 1, f + 1:]
        F[-f:, -f:] = k[f + 1:, f + 1:]
        layer = np.real(np.fft.ifft2(F))
        out += amp * layer / (np.abs(layer).max() + 1e-9)
        amp *= 0.5
    return (out - out.min()) / (out.max() - out.min())


def ceiling(out, n=1024):
    """perforated hardboard: Ø3 mm holes on a 12 mm grid (bible 4.2). Tile 0.12 m = 10 x 10 holes."""
    tile = 0.12
    mpp = tile / n
    y, x = (np.mgrid[0:n, 0:n] + 0.5) * mpp
    gx, gy = np.mod(x, 0.012) - 0.006, np.mod(y, 0.012) - 0.006
    r = np.sqrt(gx ** 2 + gy ** 2)
    hole = np.clip((0.0015 + mpp - r) / (2 * mpp), 0, 1)           # anti-aliased disc
    rim = np.clip(1 - np.abs(r - 0.0017) / 0.0004, 0, 1) * 0.3      # a slight pressed lip
    grain = tile_noise(n, 5, 11, base=6) * 0.15
    h = -hole * 0.0015 + rim * 0.0002 + grain * 0.00008
    Image.fromarray(height_to_normal(h, mpp, 1.0)).save(os.path.join(out, 'Cabin_CeilingPerf_N_0.12m.png'))
    # mask: R = hole (dark, 0.15 albedo inside), G = board fibre (albedo variation)
    m = np.stack([hole, 0.5 + 0.5 * (grain / 0.15 - 0.5), np.zeros_like(hole)], -1)
    Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, 'Cabin_CeilingPerf_M_0.12m.png'))


def floor(out, n=1024):
    """studded rubber: Ø25 mm studs, 50 mm pitch, 1.5 mm high (bible 4.2). Tile 0.20 m = 4 x 4 studs."""
    tile = 0.20
    mpp = tile / n
    y, x = (np.mgrid[0:n, 0:n] + 0.5) * mpp
    gx, gy = np.mod(x, 0.05) - 0.025, np.mod(y, 0.05) - 0.025
    r = np.sqrt(gx ** 2 + gy ** 2)
    stud = np.clip((0.0125 - r) / 0.0012, 0, 1)                     # a flat-topped stud with a 1.2 mm shoulder
    rough = tile_noise(n, 6, 3, base=8)
    h = stud * 0.0015 + rough * 0.00006
    Image.fromarray(height_to_normal(h, mpp, 1.0)).save(os.path.join(out, 'Cabin_FloorStud_N_0.20m.png'))
    # mask: R = stud top (worn shiny), G = dirt in the valleys (ring round each stud), B = rubber mottling
    dirt = np.clip(1 - np.abs(r - 0.0135) / 0.0025, 0, 1) * (1 - stud)
    m = np.stack([stud, dirt, rough], -1)
    Image.fromarray((np.clip(m, 0, 1) * 255).astype(np.uint8)).save(os.path.join(out, 'Cabin_FloorStud_M_0.20m.png'))


def vinyl(out, n=1024):
    """fine leather-grain vinyl (detail normal 0.35, bible 4.2). Tile 0.25 m."""
    tile = 0.25
    mpp = tile / n
    a = tile_noise(n, 3, 21, base=40)
    cells = np.abs(np.sin(a * 40.0))                                # cracked-pebble grain
    h = (1 - cells) * 0.00012 + tile_noise(n, 4, 5, base=12) * 0.00004
    Image.fromarray(height_to_normal(h, mpp, 1.0)).save(os.path.join(out, 'Cabin_VinylGrain_N_0.25m.png'))


def weave(out, n=512):
    """curtain cotton-poly weave (normal 0.3, bible 4.5). Tile 0.05 m."""
    tile = 0.05
    mpp = tile / n
    y, x = (np.mgrid[0:n, 0:n] + 0.5) * mpp
    p = 0.0008
    h = 0.5 * (np.sin(2 * np.pi * x / p) * np.sign(np.sin(np.pi * y / p)) + np.sin(2 * np.pi * y / p) * np.sign(np.sin(np.pi * x / p)))
    h = h * 0.00008 + tile_noise(n, 4, 9, base=6) * 0.00003
    Image.fromarray(height_to_normal(h, mpp, 1.0)).save(os.path.join(out, 'Cabin_CurtainWeave_N_0.05m.png'))


def radio_dial(out, n=512):
    """the dial window: cream face #E8DFC8, tick marks only (no digits), red needle #C0392B. 512 x 256.
    A = backlight mask (the face glows, the ticks and needle do not)."""
    W, H = n, n // 2
    im = Image.new('RGBA', (W, H), (0xE8, 0xDF, 0xC8, 255))
    d = ImageDraw.Draw(im)
    for k in range(41):
        x = int(30 + (W - 60) * k / 40)
        L = 34 if k % 10 == 0 else (22 if k % 5 == 0 else 14)
        for yb in (40, H - 40):
            d.line([(x, yb), (x, yb + (L if yb == 40 else -L))], fill=(70, 62, 50, 255), width=3 if k % 5 == 0 else 2)
    d.line([(30, 40), (W - 30, 40)], fill=(70, 62, 50, 255), width=2)
    d.line([(30, H - 40), (W - 30, H - 40)], fill=(70, 62, 50, 255), width=2)
    nx = int(30 + (W - 60) * 0.62)
    d.line([(nx, 24), (nx, H - 24)], fill=(0xC0, 0x39, 0x2B, 255), width=5)
    a = np.array(im).astype(np.float32)
    lum = a[..., :3].mean(-1)
    a[..., 3] = np.clip((lum - 120) / 100, 0, 1) * 255
    Image.fromarray(a.astype(np.uint8), 'RGBA').save(os.path.join(out, 'Cabin_RadioDial_512x256.png'))


def dest_blind(out):
    """bible 4.7: black linen #262626, 「蓝白」 cut out (lit from behind by the tubes), Source Han Sans Heavy, 140 mm high,
    no route number. 1024 x 296 for the 0.76 x 0.22 m blind. R = A = letter mask (light), G = linen weave, B = 0.
    Reads correctly from OUTSIDE (uv u runs left -> right as seen from the front); from inside it is the back of the
    blind (D-08 era: blank, see Gate README 8.5). Act 11 swaps in the blank one."""
    W, H = 1024, 296
    px_m = W / 0.76
    font = os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'Fonts', 'Originals~', 'SourceHanSansCN-Heavy.otf')
    m = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(m)
    f = ImageFont.truetype(font, int(0.140 * px_m * 1.12))
    bb = d.textbbox((0, 0), '蓝白', font=f)
    d.text(((W - (bb[2] - bb[0])) / 2 - bb[0], (H - (bb[3] - bb[1])) / 2 - bb[1]), '蓝白', font=f, fill=255)
    weave = tile_noise(256, 3, 31, base=40)
    weave = np.tile(weave, (2, 4))[:H, :W]
    for name, mask in (('Bus_DestBlind_1024x296.png', np.asarray(m, np.float32) / 255.0), ('Bus_DestBlind_Blank_1024x296.png', np.zeros((H, W), np.float32))):
        # A = the letter mask too: Lanbai/Cabin's DestBlind emission mode reads the letters from A (_EmitTex.a)
        img = np.stack([mask, 0.75 + 0.25 * weave, np.zeros((H, W)), mask], -1)
        Image.fromarray((np.clip(img, 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(out, name))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--out', default=os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Textures'))
    a = ap.parse_args()
    os.makedirs(a.out, exist_ok=True)
    ceiling(a.out)
    floor(a.out)
    vinyl(a.out)
    weave(a.out)
    radio_dial(a.out)
    dest_blind(a.out)
    print('textures ->', a.out, sorted(os.listdir(a.out)))


if __name__ == '__main__':
    main()
