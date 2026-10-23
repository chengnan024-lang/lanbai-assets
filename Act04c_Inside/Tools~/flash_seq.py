"""Frame sequences for Art/tools/lens_tech/flashcheck.py, made the way the screen would show them.

  flash  : 245.9 -> 249.3 s at 60 fps from ONE linear render of the frozen scene (246.4 s; nothing changes after 246.39
           except the exposure and the overlay): x 2^dEV (FLASH_TEAR), the black overlay composited in linear BEFORE the
           grade (the overlay is graded; its fill x 2^-dEV), S4c -> S6 hard cut at U12, bloom on, desktop lens off.
  frames : grade every linear render in a directory (harness outputs <dir>/<run>/linear.npy) in time order, for the
           sequences rendered by the harness (seam, sleeve).
  ~/bpy/bin/python flash_seq.py flash <run dir with linear.npy> <out dir> [--vr]
"""
import argparse
import glob
import json
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inside_def as D  # noqa: E402
import inside_drive as DR  # noqa: E402
import lb_grade as LG  # noqa: E402


def down(img, w=480):
    h = int(round(img.shape[0] * w / img.shape[1]))
    k = img.shape[1] // w
    if k >= 2:
        img = img[:h * k, :w * k].reshape(h, k, w, k, 3).mean((1, 3))
    return img


def flash(run, out, vr=False):
    os.makedirs(out, exist_ok=True)
    img = down(np.load(os.path.join(run, 'linear.npy')).astype(np.float64))
    lum = img @ np.array([0.2126, 0.7152, 0.0722])
    rows = []
    for i, t in enumerate(np.arange(245.9, 249.3, 1 / 60.0)):
        dEV = DR.delta_ev(t)
        ov = DR.overlay(t, scene_L=float(lum.mean() * 2 ** (-0.9 + dEV)))
        sid = 'S6' if t >= D.U12 else 'S4c'
        x = img
        if ov is not None:
            fill = np.asarray(ov['fill']) * 2.0 ** (-ov['dEV'])
            x = ov['alpha'] * fill[None, None, :] + (1 - ov['alpha']) * img
        c = LG.grade(x, sid, dEV=dEV)
        Image.fromarray(np.clip(np.round(c), 0, 255).astype(np.uint8)).save(os.path.join(out, 'f%05d.png' % i))
        rows.append(dict(t=round(float(t), 4), dEV=round(dEV, 3), alpha=None if ov is None else round(ov['alpha'], 4), APL=round(LG.apl(c), 2)))
    json.dump(rows, open(os.path.join(out, 'sequence.json'), 'w'), indent=0)
    peak = max(rows, key=lambda r: r['APL'])
    print('flash sequence: %d frames, peak APL %.1f at t %.3f' % (len(rows), peak['APL'], peak['t']))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode')
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--vr', action='store_true')
    a = ap.parse_args()
    if a.mode == 'flash':
        flash(a.src, a.out, a.vr)
