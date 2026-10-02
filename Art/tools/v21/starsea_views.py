# -*- coding: utf-8 -*-
"""Star-sea test frames for ANY head direction (yaw, pitch), split into light sources, using bible_work/scenes_v2.starsea's own
recipe (same band, noise fields, star field seeds), so the per-view ramp checks use the bible's simulator."""
import os, sys, math, numpy as np
BW = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../bible_work"))
sys.path.insert(0, BW)
_cwd = os.getcwd(); os.chdir(BW)
import scenes_v2 as V
from scenes_proc import SL, W, H
os.chdir(_cwd)
from scipy.ndimage import gaussian_filter, map_coordinates
def starsea_parts(prof='S9a', pitch=6.0, yaw=0.0, climax=False):
    """returns dict(dark, lift, glow, stars) scene-linear (H, W, 3); full = dark + lift + glow + stars."""
    az, el = V.cam(pitch); az = az + yaw
    S = lambda h: SL(h, prof)
    base = S('#08112A'); dark = np.broadcast_to(S('#04060E'), (H, W, 3)).copy()
    ca, sa = math.cos(math.radians(35)), math.sin(math.radians(35))
    t = (az + 30) * ca + (el - 12) * sa
    n_ = -(az + 30) * sa + (el - 12) * ca
    band = np.exp(-(n_ / 5.0) ** 2) + 0.30 * np.exp(-(n_ / 12.0) ** 2)
    fld = gaussian_filter(np.random.default_rng(8).standard_normal((512, 512)), 2.0); fld /= fld.std()
    def along(ks, kn, off=0.0):
        return map_coordinates(fld, [(n_ * kn + 256 + off) % 512, (t * ks + 256) % 512], order=1, mode='wrap')
    lane = np.exp(-((n_ + 0.6 + 1.2 * along(0.8, 0.3)) / 0.9) ** 2) * np.clip(0.55 + 0.45 * along(1.5, 1.0, 97), 0, 1)
    lane += 0.5 * np.exp(-((n_ - 2.2 + 1.5 * along(0.6, 0.3, 33)) / 0.6) ** 2) * np.clip(along(2.0, 1.2, 55), 0, 1)
    fine = np.clip(1 + 0.35 * along(1.2, 0.8, 11) + 0.25 * along(3.0, 2.0, 71), 0.45, 1.6)
    core = np.exp(-((az + 30) / 10) ** 2 - ((el - 12) / 6) ** 2)
    gm = 1.8 if climax else 1.0
    glow = (band * fine * (1 - 0.85 * np.clip(lane, 0, 1)))[..., None] * (S('#6F82A0') - base).clip(0) * 0.6 * gm
    glow += (core * band * fine * (1 - 0.9 * np.clip(lane, 0, 1)))[..., None] * (S('#C8B79A') - base).clip(0) * 0.8 * gm
    r = np.random.default_rng(21)
    dens = 0.0016 + 0.006 * np.clip(band, 0, 1) * (1 - 0.7 * np.clip(lane, 0, 1))
    k = r.random((H, W)) < dens
    mag = np.zeros((H, W)); mag[k] = r.pareto(2.1, k.sum()) * 0.10 + 0.025
    st = gaussian_filter(mag, 0.55)
    tint = np.stack([np.ones((H, W)), 0.9 + 0.1 * r.random((H, W)), 0.8 + 0.25 * r.random((H, W))], -1)
    sg = 8.0 if climax else 4.0
    stars = (st[..., None] * tint) * (1.0 + (sg - 1) * (st > 0.05))[..., None] * S('#F2F6FF') / S('#F2F6FF').max()
    return dict(dark=dark, lift=np.broadcast_to(base - S('#04060E'), (H, W, 3)).copy(), glow=glow, stars=stars, band_frac=float((band > 0.5).mean()))
