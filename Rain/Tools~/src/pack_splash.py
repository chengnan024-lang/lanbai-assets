"""Pack the 16 Cycles splash frames (render_splash.py) into RainSplash_Flip4x4_512.png.
v2 (verification round 2): the late frames' spray reached the cell borders (alpha up to 0.30) -> cut on a straight line
and bled into the neighbours under bilinear / mips. Now each frame's outer 8 % fades out (the far spray thins away
instead of being cut) and the frame is scaled by SCALE about the impact point, leaving >= 6 px of empty border.
One cell now spans 48 / SCALE mm: Start Size of the splash particles x 1/SCALE (README §3), impact still at (0.5, 0.125)."""
import os, sys, json
import numpy as np
from PIL import Image
from exr import read_exr

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import rainpaths as RP
OUT = RP.out_dir()
SCALE = 0.84
frames = [read_exr(os.path.join(OUT, 'splash_frames', 'f%02d.exr' % k)) for k in range(16)]
lum = [0.2126 * f[..., 0] + 0.7152 * f[..., 1] + 0.0722 * f[..., 2] for f in frames]
wat = np.concatenate([l[f[..., 3] > 0.02].ravel() for l, f in zip(lum, frames)])      # WATER pixels only
ref = np.percentile(wat, 99.0); kmed = np.median(wat) * 0.6
N = frames[0].shape[0]
xs = (np.arange(N) + 0.5) / N
def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1); return t * t * (3 - 2 * t)
win = (sstep(0.0, 0.08, xs)[None, :] * sstep(1.0, 0.92, xs)[None, :] * sstep(0.0, 0.08, xs)[:, None])   # rows: 0 = top
atlas = np.zeros((512, 512, 4), np.float32)
for k, (f, l) in enumerate(zip(frames, lum)):
    L = np.clip(np.log1p(l / kmed) / np.log1p(ref / kmed), 0, 1)
    A = np.clip(f[..., 3] * 0.35 + L * 0.9, 0, 1) * (f[..., 3] > 0.001)
    tail = min(1.0, (15 - k) / 3.5 + 0.1)          # last frames fade: droplets never pop off
    L = L * tail * win; A = A * tail * win
    # scale about the impact point (u 0.5, v 0.125 from the bottom) into a 128 px cell
    n = int(round(128 * SCALE))
    Ls = np.array(Image.fromarray((L * 255).astype(np.uint8)).resize((n, n), Image.LANCZOS)) / 255.0
    As = np.array(Image.fromarray((A * 255).astype(np.uint8)).resize((n, n), Image.LANCZOS)) / 255.0
    cell_L = np.zeros((128, 128)); cell_A = np.zeros((128, 128))
    ox = int(round(64 - 0.5 * n)); oy = int(round((128 - 16) - (1 - 0.125) * n))   # impact row 112 stays at 112
    cell_L[oy:oy + n, ox:ox + n] = Ls; cell_A[oy:oy + n, ox:ox + n] = As
    r, c = divmod(k, 4)
    atlas[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128, :3] = cell_L[..., None]
    atlas[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128, 3] = cell_A
Image.fromarray(np.clip(np.round(atlas * 255), 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'RainSplash_Flip4x4_512.png'))
Image.fromarray((np.clip(atlas[..., :3], 0, 1) * 255).astype(np.uint8)).resize((1024, 1024), Image.LANCZOS).save(os.path.join(OUT, 'look_splash.png'))
border = []
for k in range(16):
    r, c = divmod(k, 4); a = atlas[r * 128:(r + 1) * 128, c * 128:(c + 1) * 128, 3]
    border.append(float(max(a[:6].max(), a[-6:].max(), a[:, :6].max(), a[:, -6:].max())))
print('ref', ref, 'max alpha within 6 px of any cell border: %.3f' % max(border))
