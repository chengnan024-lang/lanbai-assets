"""Splat the star points exactly as Lanbai/StarPoints draws them (Gaussian of FWHM px, same flux formula), into a
scene-linear frame from camera_dirs(). Used for the act 9 calibration and reference renders."""
import os
import numpy as np

REPO = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', '..'))
_cat = None


def catalogue():
    global _cat
    if _cat is None:
        a = np.genfromtxt(os.path.join(REPO, 'Sky', 'Data', 'StarPoints_BSC5.csv'), delimiter=',', skip_header=2)
        _cat = dict(hr=a[:, 0].astype(int), dir=a[:, 1:4], mag=a[:, 4], col=a[:, 6:9], rank=a[:, 9])
    return _cat


def flux(mag, rank, scale=1.0, mag_ref=0.0, slope=0.62, bright_count=50.0, bright_boost=4.0, mag_floor=6.5):
    f = scale * np.exp2(-1.3287712 * slope * (mag - mag_ref))
    f *= 1.0 + (bright_boost - 1.0) * np.clip((bright_count - rank) / 20.0, 0, 1)
    return np.where(mag <= mag_floor, f, 0.0)


def splat(img, w, h, hfov, yaw, pitch, dirs, peaks, cols, fwhm=1.6):
    """img (h, w, 3) += Gaussians. dirs (N, 3) Unity world; peaks (N,) linear peak; cols (N, 3) luminance-1 colour."""
    t = np.tan(np.radians(hfov) / 2)
    p, yw = np.radians(pitch), np.radians(yaw)
    Rx = np.array([[1, 0, 0], [0, np.cos(p), np.sin(p)], [0, -np.sin(p), np.cos(p)]])
    Ry = np.array([[np.cos(yw), 0, np.sin(yw)], [0, 1, 0], [-np.sin(yw), 0, np.cos(yw)]])
    cam = dirs @ (Rx.T @ Ry.T)          # world -> camera (inverse of camera->world = transpose)
    vis = cam[:, 2] > 1e-3
    x = cam[vis, 0] / cam[vis, 2] / t; y = cam[vis, 1] / cam[vis, 2] / (t * h / w)
    px = (x + 1) / 2 * w - 0.5; py = (1 - y) / 2 * h - 0.5
    pk = peaks[vis]; cl = cols[vis]
    r = int(np.ceil(2 * fwhm))
    k = -4 * np.log(2) / fwhm ** 2
    for i in np.nonzero((px > -r) & (px < w + r) & (py > -r) & (py < h + r) & (pk > 0))[0]:
        x0, y0 = int(np.floor(px[i])), int(np.floor(py[i]))
        xs = np.arange(x0 - r, x0 + r + 2); ys = np.arange(y0 - r, y0 + r + 2)
        xs = xs[(xs >= 0) & (xs < w)]; ys = ys[(ys >= 0) & (ys < h)]
        if len(xs) == 0 or len(ys) == 0:
            continue
        g = np.exp(k * ((xs[None, :] - px[i]) ** 2 + (ys[:, None] - py[i]) ** 2))
        img[ys[:, None], xs[None, :], :] += g[..., None] * (pk[i] * cl[i])[None, None, :]
    return img
