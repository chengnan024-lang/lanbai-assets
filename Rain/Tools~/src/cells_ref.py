"""numpy port of LanbaiRain.cginc :: LanbaiRippleCells / LanbaiRingLUT / LanbaiDripOne / LanbaiRingBand (v2, with the
footprint band-limit). Used by make_docs.py (Sheet_PuddleCells) and the stop preview (ripple normals of the puddles).
Coordinates: p = (X_u, Z_u) metres in R_Stop-local Unity space (the shader's P.xz). Returns slopes (dh/dX, dh/dZ)."""
import os
import numpy as np
from PIL import Image
import rainpaths as RP

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('RAIN_OUT', os.path.join(HERE, '..', 'out'))
fr = lambda x: x - np.floor(x)


def h21(x, y):
    p3 = np.stack([fr(x * .1031), fr(y * .1031), fr(x * .1031)])
    d = p3[0] * (p3[1] + 33.33) + p3[1] * (p3[2] + 33.33) + p3[2] * (p3[0] + 33.33)
    p3 = p3 + d
    return fr((p3[0] + p3[1]) * p3[2])


def h22(x, y):
    p3 = np.stack([fr(x * .1031), fr(y * .1030), fr(x * .0973)])
    d = p3[0] * (p3[1] + 33.33) + p3[1] * (p3[2] + 33.33) + p3[2] * (p3[0] + 33.33)
    p3 = p3 + d
    return fr((p3[0] + p3[1]) * p3[2]), fr((p3[0] + p3[2]) * p3[1])     # frac((p3.xx + p3.yz) * p3.zy)


def h11(p):
    p = fr(p * .1031); p = p * (p + 33.33); p = p * (p + p); return fr(p)


class LUT:
    def __init__(self, name, rmax, tmax):
        self.L = np.asarray(Image.open(RP.find(name)), np.float64) / 255.0     # row 0 = top = v 1
        self.H, self.W = self.L.shape[:2]; self.rmax, self.tmax = rmax, tmax

    def __call__(self, r, age, amp, bl):
        ok = (r < self.rmax) & (age > 0) & (age < self.tmax)
        u = np.clip(r / self.rmax, 0, 1) * (self.W - 1) / self.W + 0.5 / self.W
        v = np.clip(age / self.tmax, 0, 1) * (self.H - 1) / self.H + 0.5 / self.H
        x = u * self.W - 0.5; y = (1 - v) * self.H - 0.5
        x0 = np.clip(np.floor(x).astype(int), 0, self.W - 1); y0 = np.clip(np.floor(y).astype(int), 0, self.H - 1)
        x1 = np.minimum(x0 + 1, self.W - 1); y1 = np.minimum(y0 + 1, self.H - 1); fx = x - np.floor(x); fy = y - np.floor(y)
        s = lambda c: (self.L[y0, x0, c] * (1 - fx) * (1 - fy) + self.L[y0, x1, c] * fx * (1 - fy)
                       + self.L[y1, x0, c] * (1 - fx) * fy + self.L[y1, x1, c] * fx * fy)
        full = (s(0) * 2 - 1) * np.exp2(s(1) * 14 - 12)
        low = (s(2) * 2 - 1) * np.exp2(s(3) * 14 - 12)
        return np.where(ok, (full * (1 - bl) + low * bl) * amp, 0.0)


_ring = None


def ring_band(footprint):
    return np.clip((footprint - 0.0008) / 0.0010, 0, 1)


def cells(px, pz, t, dens, bl=0.0):
    global _ring
    if _ring is None:
        _ring = LUT('RippleRing_LUT_256x128.png', 0.25, 1.25)
    sx = np.zeros_like(px, dtype=np.float64); sz = np.zeros_like(sx)
    pF = min(1.0, dens * 0.6 * 0.6 * 1.25 * 0.5)
    for layer in range(2):
        qx = px / 0.6 + 0.5 * layer; qy = pz / 0.6 + 0.5 * layer
        bx = np.floor(qx - 0.5); by = np.floor(qy - 0.5)
        for j in range(2):
            for i in range(2):
                cx = bx + i; cy = by + j; ix = cx + layer * 97.0; iy = cy + layer * 97.0
                ph = h21(ix * 0.713 + 5.1, iy * 0.713 + 5.1)
                tt = t / 1.25 + ph; n = np.floor(tt); age = fr(tt) * 1.25
                fire = (h21(ix * 1.371 + n * 0.6180339, iy * 1.371 + n * 0.6180339) <= pF).astype(float)
                ox, oy = h22(ix + n * 0.7548777, iy + n * 0.7548777)
                sz_ = 0.8 + 0.4 * h11((ix * 0.37 + iy * 0.61) + n)
                dx = (qx - (cx + ox)) * 0.6 / sz_; dy = (qy - (cy + oy)) * 0.6 / sz_
                r = np.hypot(dx, dy)
                s = fire * _ring(r, age, sz_ ** 1.5, bl)
                sx += s * dx / np.maximum(r, 1e-5); sz += s * dy / np.maximum(r, 1e-5)
    return sx, sz


_drip = None


def drip(px, pz, cx, cz, age, bl=0.0):
    global _drip
    if _drip is None:
        _drip = LUT('DripRipple_LUT_512x256.png', 0.5, 2.5)
    dx = px - cx; dz = pz - cz; r = np.hypot(dx, dz)
    s = _drip(r, np.full_like(r, age), 1.0, bl)
    return s * dx / np.maximum(r, 1e-5), s * dz / np.maximum(r, 1e-5)
