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


def _compose(img, t):
    lum = img @ np.array([0.2126, 0.7152, 0.0722])
    dEV = DR.delta_ev(t)
    ov = DR.overlay(t, scene_L=float(lum.mean() * 2 ** (-0.9 + dEV)))
    sid = 'S6' if t >= D.U12 else 'S4c'
    x = img
    if ov is not None:
        fill = np.asarray(ov['fill']) * 2.0 ** (-ov['dEV'])
        x = ov['alpha'] * fill[None, None, :] + (1 - ov['alpha']) * img
    return LG.grade(x, sid, dEV=dEV), dEV, ov


def flashdyn(frozen, rundir, out):
    """D-20: the dot's glow grows inside the flash, so the frames 247.88 .. 248.65 come from their own linear renders
    (<rundir>/f_<t>/linear.npy, t to 3 decimals); the rest from the frozen frame."""
    os.makedirs(out, exist_ok=True)
    base = down(np.load(os.path.join(frozen, 'linear.npy')).astype(np.float64))
    rows = []
    for i, t in enumerate(np.arange(245.9, 249.3, 1 / 60.0)):
        p = os.path.join(rundir, 'f_%.3f' % t, 'linear.npy')
        img = down(np.load(p).astype(np.float64)) if os.path.exists(p) else base
        c, dEV, ov = _compose(img, t)
        Image.fromarray(np.clip(np.round(c), 0, 255).astype(np.uint8)).save(os.path.join(out, 'f%05d.png' % i))
        rows.append(dict(t=round(float(t), 4), dEV=round(dEV, 3), own=os.path.exists(p), APL=round(LG.apl(c), 2)))
    json.dump(rows, open(os.path.join(out, 'sequence.json'), 'w'), indent=0)
    peak = max(rows, key=lambda r: r['APL'])
    print('flash (dynamic dot) sequence: %d frames (%d own renders), peak APL %.1f at t %.3f' % (len(rows), sum(r['own'] for r in rows), peak['APL'], peak['t']))


def stills(rundir, out):
    """the four act-5 stills at full resolution (D-20): <rundir>/<t>/linear.npy composed like the sequence."""
    os.makedirs(out, exist_ok=True)
    for t in (247.9, 248.29, 248.5, 248.64):
        img = np.load(os.path.join(rundir, '%.2f' % t, 'linear.npy')).astype(np.float64)
        c, dEV, ov = _compose(img, t)
        Image.fromarray(np.clip(np.round(c), 0, 255).astype(np.uint8)).save(os.path.join(out, '%.2f_hero.png' % t))
        print('%.2f dEV %.2f overlay %s APL %.1f' % (t, dEV, None if ov is None else round(ov['alpha'], 3), LG.apl(c)))


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('mode')
    ap.add_argument('src')
    ap.add_argument('out')
    ap.add_argument('--vr', action='store_true')
    a = ap.parse_args()
    if a.mode == 'flash':
        flash(a.src, a.out, a.vr)
    elif a.mode == 'flashdyn':
        frozen, rundir = a.src.split(',')
        flashdyn(frozen, rundir, a.out)
    elif a.mode == 'stills':
        stills(a.src, a.out)
