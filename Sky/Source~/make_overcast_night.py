"""蓝白 · Sky_Overcast_Night（ART BIBLE §8.1 #8；第 1、2、11、12 幕的阴云夜空）。
Run: ~/bpy/bin/python -I make_overcast_night.py

A dim, low-contrast stratus deck seen from the ground at night, as a lat-long .hdr that Unity imports as a cubemap
(Texture Shape = Cube, Mapping = Latitude-Longitude; Unity's convention u = 0.5 - atan2(z, x) / 2pi, row 0 = zenith).
Values are FILL values under S1 (calib_engine.json): zenith #09080D (screen #070B14), horizon = the S1 fog colour
fill #161B27 (screen #121A28), so Lanbai/Sky with exposure 0 and tints 1 shows the bible's targets and the fog
(LanbaiHorizon / RenderSettings) meets the sky at the horizon. For S2 / S11 / S12 the act's exposure / tints scale it
(S2 sky #05080F fill #060405, fog #0A0F18 fill #0D0F15: x ~0.6).
Variant _TownGlow: + the sodium-lit cloud base toward the town (S1 #241E22, fill #2A1F1E) centred on azimuth 0 (+Z):
set Lanbai/Sky _RotationA = the town's azimuth.
The deck: fBm on a cloud plane 1.2 km up (so the texture foreshortens toward the horizon, as a real deck does),
+-7 % luminance, a slightly brighter ragged underside. No stars, no moon (bible: overcast).
"""
import math, os, sys
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
SKY = os.path.dirname(HERE)
sys.path.insert(0, os.path.join(SKY, 'Tools~', 'render'))
from hdrio import write_hdr   # noqa: E402

W, H = 2048, 1024


def lin(h):
    c = np.array([int(h[i:i + 2], 16) / 255.0 for i in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


ZEN, HOR, TOWN = lin('#09080D'), lin('#161B27'), lin('#2A1F1E')
rng = np.random.default_rng(7)
perm = rng.permutation(256)
perm = np.concatenate([perm, perm])
grad = rng.normal(size=(256, 2)); grad /= np.linalg.norm(grad, axis=1, keepdims=True)


def perlin(x, y):
    xi = np.floor(x).astype(int); yi = np.floor(y).astype(int)
    xf = x - xi; yf = y - yi
    def g(ix, iy, dx, dy):
        h = perm[(perm[ix & 255] + iy) & 255]
        return grad[h, 0] * dx + grad[h, 1] * dy
    u = xf * xf * xf * (xf * (xf * 6 - 15) + 10); v = yf * yf * yf * (yf * (yf * 6 - 15) + 10)
    n00 = g(xi, yi, xf, yf); n10 = g(xi + 1, yi, xf - 1, yf); n01 = g(xi, yi + 1, xf, yf - 1); n11 = g(xi + 1, yi + 1, xf - 1, yf - 1)
    return (n00 * (1 - u) + n10 * u) * (1 - v) + (n01 * (1 - u) + n11 * u) * v


def fbm(x, y, oct=6):
    s, a, f = 0.0, 0.5, 1.0
    for _ in range(oct):
        s = s + a * perlin(x * f, y * f); a *= 0.5; f *= 2.03
    return s


u = (np.arange(W) + 0.5) / W; v = (np.arange(H) + 0.5) / H
phi = (0.5 - u) * 2 * np.pi                       # = atan2(z, x)
theta = v * np.pi                                 # = acos(y), row 0 = zenith
PHI, TH = np.meshgrid(phi, theta)
dx, dy, dz = np.sin(TH) * np.cos(PHI), np.cos(TH), np.sin(TH) * np.sin(PHI)
el = np.degrees(np.arcsin(dy))
up = np.maximum(dy, 0.02)
px, pz = dx / up * 1.2, dz / up * 1.2             # km on the cloud plane
n = fbm(px * 0.9 + 3.1, pz * 0.9 - 7.7)            # large soft lumps
n2 = fbm(px * 4.0, pz * 4.0, 4)                   # fine ragged underside
fade = np.clip(dy / 0.08, 0, 1)                   # the texture melts into the horizon haze
deck = 1.0 + (0.11 * n + 0.04 * n2) * fade
t = np.clip(el / 50.0, 0, 1) ** 0.6               # horizon -> zenith
base = HOR[None, None, :] * (1 - t[..., None]) + ZEN[None, None, :] * t[..., None]
img = base * deck[..., None]
img[el < 0] = HOR                                  # Lanbai/Sky replaces the lower half anyway
os.makedirs(os.path.join(SKY, 'Textures'), exist_ok=True)
write_hdr(os.path.join(SKY, 'Textures', 'Sky_Overcast_Night_2048x1024.hdr'), img)
# town glow variant: azimuth 0 (+Z) = phi 90 deg
az = np.degrees(np.arctan2(dx, dz))
lobe = np.exp(-(az / 28.0) ** 2) * np.exp(-np.clip(el, 0, None) / 9.0) * (el >= -1)
town = img + (TOWN - HOR)[None, None, :] * lobe[..., None] * deck[..., None]
write_hdr(os.path.join(SKY, 'Textures', 'Sky_Overcast_Night_TownGlow_2048x1024.hdr'), np.maximum(town, 0))
print('zenith mean', img[:20].reshape(-1, 3).mean(0), 'horizon', img[H // 2 - 3].mean(0))
