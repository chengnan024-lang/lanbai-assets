import numpy as np, os
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import zoom
import s4, tear_def as T
TEX = '../../deliver/Tear/Textures'
def load(n):
    return np.asarray(Image.open(os.path.join(TEX, n))).astype(np.float32) / 255.0
def s2l(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)
HAZE = np.array([0.1356, 0.1413, 0.2051]); VOID = np.array([0.0044, 0.006, 0.0086])
tiles = []
# emission, upright, true proportions, on the haze, graded
e = load('Tear_Emission_2048x512.png'); rgb = s2l(e[..., :3]) * 4; a = e[..., 3]
comp = rgb + (1 - a[..., None]) * HAZE
up = np.transpose(comp, (1, 0, 2))[::-1, ::-1]
mt = (T.T_MAX - T.T_MIN) / 2048; ma = (T.A_MAX - T.A_MIN) / 512
up = zoom(up, (0.5, 0.5 * ma / mt, 1), order=1)
tiles.append(('Tear_Emission_2048x512 (upright, on haze, S4)', s4.to_display(up, bloom=True, vignette=False)))
r = load('Tear_Rip_1024x128.png'); comp = s2l(r[..., :3]) * 4 + (1 - r[..., 3:]) * HAZE
tiles.append(('Tear_Rip_1024x128 (on haze, S4)', s4.to_display(zoom(comp, (1, 0.5, 1), order=1), bloom=True, vignette=False)))
f = load('Tear_Fibres_1024.png')[..., 3]
tiles.append(('Tear_Fibres_1024 (A)', np.repeat(zoom(f, 0.5, order=1)[..., None], 3, 2)))
fl = load('Tear_Flaps_1024.png')
show = np.stack([fl[..., 0], fl[..., 1] * fl[..., 3], fl[..., 2]], 2) * 0.8 + 0.1 * (1 - fl[..., 3:])
tiles.append(('Tear_Flaps_1024 (R dist, G silk x A, B threads)', zoom(show, (0.5, 0.5, 1), order=1)))
sf = load('Tear_SkyFolds_1024.png'); comp = s2l(sf[..., :3]) + (1 - sf[..., 3:]) * HAZE
tiles.append(('Tear_SkyFolds_1024 (on haze, S4)', s4.to_display(zoom(comp, (0.5, 0.5, 1), order=1), bloom=False, vignette=False)))
h = load('Halo_512.png'); comp = s2l(h[..., :3]) + VOID
tiles.append(('Halo_512 (on void, S4)', s4.to_display(comp, bloom=False, vignette=False)))
sh = load('Shaft_Gradient_256x1024.png')[..., 3]
tiles.append(('Shaft_Gradient_256x1024 (A)', np.repeat(zoom(sh, 0.5, order=1)[..., None], 3, 2)))
W = 1600; pad = 16; font = ImageFont.load_default()
rows = []; x = pad; y = pad; rowh = 0; placed = []
for name, img in tiles:
    hh, ww = img.shape[:2]
    if x + ww + pad > W:
        x = pad; y += rowh + 28; rowh = 0
    placed.append((name, img, x, y)); x += ww + pad; rowh = max(rowh, hh)
Hh = y + rowh + 28 + pad
sheet = Image.new('RGB', (W, Hh), (18, 20, 28)); d = ImageDraw.Draw(sheet)
for name, img, x, y in placed:
    sheet.paste(Image.fromarray((np.clip(img, 0, 1) * 255).astype(np.uint8)), (x, y + 18))
    d.text((x, y), name, fill=(210, 214, 225), font=font)
sheet.save('../../deliver/Tear/Renders/Tear_Textures_Sheet.png'); print(sheet.size)
