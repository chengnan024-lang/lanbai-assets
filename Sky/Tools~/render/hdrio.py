"""Radiance .hdr (RGBE, new-style RLE) reader / writer: no extra dependencies."""
import numpy as np


def read_hdr(path):
    with open(path, 'rb') as f:
        data = f.read()
    pos = 0
    while True:
        end = data.index(b'\n', pos)
        line = data[pos:end]; pos = end + 1
        if line.startswith(b'-Y') or line.startswith(b'+Y'):
            parts = line.split(); H = int(parts[1]); W = int(parts[3]); break
    out = np.zeros((H, W, 4), np.uint8)
    buf = np.frombuffer(data, np.uint8)
    for y in range(H):
        if buf[pos] == 2 and buf[pos + 1] == 2 and W >= 8 and W < 32768:
            pos += 4
            for c in range(4):
                x = 0
                while x < W:
                    n = int(buf[pos]); pos += 1
                    if n > 128:
                        n -= 128; out[y, x:x + n, c] = buf[pos]; pos += 1
                    else:
                        out[y, x:x + n, c] = buf[pos:pos + n]; pos += n
                    x += n
        else:
            out[y] = buf[pos:pos + 4 * W].reshape(W, 4); pos += 4 * W
    e = out[..., 3].astype(np.int32)
    scale = np.where(e > 0, np.ldexp(1.0, e - 136), 0.0)
    img = out[..., :3].astype(np.float64) * scale[..., None]
    if line.startswith(b'+Y'):
        img = img[::-1]
    return img.astype(np.float32)


def write_hdr(path, img):
    img = np.asarray(img, np.float64)
    H, W, _ = img.shape
    m = img.max(axis=2)
    e = np.where(m > 1e-32, np.ceil(np.log2(np.maximum(m, 1e-32)) + 1e-9), -128).astype(np.int32)
    sc = np.where(m > 1e-32, 256.0 / np.ldexp(1.0, e), 0)
    rgb = np.clip(img * sc[..., None], 0, 255).astype(np.uint8)
    ee = np.where(m > 1e-32, e + 128, 0).astype(np.uint8)
    with open(path, 'wb') as f:
        f.write(b'#?RADIANCE\nFORMAT=32-bit_rle_rgbe\n\n-Y %d +X %d\n' % (H, W))
        f.write(np.concatenate([rgb, ee[..., None]], 2).tobytes())
