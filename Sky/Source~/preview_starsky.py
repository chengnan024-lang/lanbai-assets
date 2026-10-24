"""Sky/Docs~/starsky_world_equirect.png from the shipped glow PNG + the star catalogue (no rebuild of the 8K map):
2048 x 1024 world-frame equirect, star floor added, stars as Gaussian sprites whose flux follows Lanbai/StarPoints
(_StarScale 1.6, _MagSlope 0.5, FWHM 1.6 px), so bright stars read bigger and faint ones fade (final review: the
old preview drew every star as the same dot)."""
import json, os, sys
import numpy as np
from PIL import Image
HERE = os.path.dirname(os.path.abspath(__file__)); SKY = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKY, 'Tools~', 'render'))
import sky_cpu as S, stars_cpu as SC
W, H = 2048, 1024
glow = S.load_glow(4) * S.glow_scale()                          # 8192 -> 2048 box, linear, real level
floor = np.array([0x0D, 0x0F, 0x23]) / 255.0
floor = np.where(floor <= 0.04045, floor / 12.92, ((floor + 0.055) / 1.055) ** 2.4)
img = glow + floor
cat = SC.catalogue()
d = cat['dir']; u = (0.5 + np.degrees(np.arctan2(d[:, 0], d[:, 2])) / 360.0) * W - 0.5
v = (0.5 - np.degrees(np.arcsin(np.clip(d[:, 1], -1, 1))) / 180.0) * H - 0.5
pk = SC.flux(cat['mag'], cat['rank'], 1.6, 0.0, 0.5, 50, 4)
k = -4 * np.log(2) / 1.6 ** 2
for i in np.argsort(pk):
    x0, y0 = int(np.floor(u[i])), int(np.floor(v[i]))
    xs = np.arange(x0 - 3, x0 + 5) % W; ys = np.clip(np.arange(y0 - 3, y0 + 5), 0, H - 1)
    gx = np.exp(k * ((np.arange(x0 - 3, x0 + 5) - u[i]) ** 2)); gy = np.exp(k * ((np.arange(y0 - 3, y0 + 5) - v[i]) ** 2))
    img[np.ix_(ys, xs)] += (gy[:, None] * gx[None, :])[..., None] * (pk[i] * cat['col'][i])[None, None, :]
c = np.clip(img, 0, None)
c = np.clip(np.where(c <= 0.0031308, 12.92 * c, 1.055 * c ** (1 / 2.4) - 0.055), 0, 1)
Image.fromarray((c * 255 + 0.5).astype(np.uint8)).save(os.path.join(SKY, 'Docs~', 'starsky_world_equirect.png'))
print('wrote Docs~/starsky_world_equirect.png')
