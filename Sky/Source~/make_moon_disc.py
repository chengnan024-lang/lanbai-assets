"""蓝白 · 月面圆盘（ART BIBLE §8.2：1024² 圆盘，去饱和 70%）。
Source: NASA Apollo 11 full-moon photograph (AS11-44-6667) as published in github.com/nasa/NASA-3D-Resources
('Images and Textures/Moon/Moon.jpg'; NASA media, no copyright). The NASA SVS CGI Moon Kit named in the bible is not
reachable from the cloud; this photograph is a real full moon, which is what a 1.2 deg disc needs.
Output Sky/Textures/Moon_Disc_1024.png: sRGB, the disc fills the square, alpha = disc (1.5 px anti-aliased edge),
colour 70 % desaturated, normalised so the brightest highlands are ~0.95 (Lanbai/Sky _MoonColor sets the level)."""
import os
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__))
im = np.asarray(Image.open(os.path.join(HERE, 'data', 'NASA_Apollo11_FullMoon_NASA-3D-Resources.jpg')).convert('RGB')).astype(np.float64) / 255
lin = np.where(im <= 0.04045, im / 12.92, ((im + 0.055) / 1.055) ** 2.4)
L = lin @ [0.2126, 0.7152, 0.0722]
mask = L > 0.02
ys, xs = np.nonzero(mask)
cy, cx = (ys.min() + ys.max()) / 2, (xs.min() + xs.max()) / 2
r = ((ys.max() - ys.min()) + (xs.max() - xs.min())) / 4
N = 1024
g = (np.arange(N) + 0.5) / N * 2 - 1
X, Y = np.meshgrid(g, g)
sx = cx + X * r; sy = cy + Y * r
from scipy import ndimage
out = np.stack([ndimage.map_coordinates(lin[..., c], [sy, sx], order=3, mode='nearest') for c in range(3)], -1)
lum = out @ [0.2126, 0.7152, 0.0722]
out = lum[..., None] + 0.3 * (out - lum[..., None])
rr = np.sqrt(X * X + Y * Y)
alpha = np.clip((1.0 - rr) * N / 2 / 1.5 + 0.5, 0, 1)
inside = rr < 0.97
out /= np.percentile((out @ [0.2126, 0.7152, 0.0722])[inside], 99.5) / 0.95
out = np.clip(out, 0, 1)
srgb = np.where(out <= 0.0031308, 12.92 * out, 1.055 * out ** (1 / 2.4) - 0.055)
rgba = np.concatenate([srgb, alpha[..., None]], -1)
os.makedirs(os.path.join(os.path.dirname(HERE), 'Textures'), exist_ok=True)
Image.fromarray((rgba * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(os.path.dirname(HERE), 'Textures', 'Moon_Disc_1024.png'))
print('disc centre', cx, cy, 'radius px', r)
