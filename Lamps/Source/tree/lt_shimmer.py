# -*- coding: utf-8 -*-
"""Flicker proxy for the leaf cards (director note 2), deterministic:
coverage renders (white geometry / alpha-cut leaves on black, lt_render.py coverage=1) point-sampled
(filter 0.01 px, 1 sample) at 2x and 4x the target size; 2x2 box = '4x ordered supersampling' ~ MSAA 4x
alpha-to-coverage, 4x4 box = the reference. shimmer(pixel) = temporal std of (test - reference) in 0..255 over a
head micro-motion (+-2 cm, +-1 deg; lt_render.py sway). Same idea as the Unity test tool's `shimmer`.
usage: python lt_shimmer.py <Trees.blend> <shot> <W> <H> <frames> <outdir>"""
import json
import os
import subprocess
import sys

import numpy as np

blend, shot, W, H, nf, out = sys.argv[1], sys.argv[2], int(sys.argv[3]), int(sys.argv[4]), int(sys.argv[5]), sys.argv[6]
os.makedirs(out, exist_ok=True)
HERE = os.path.dirname(os.path.abspath(__file__))
PY = os.path.expanduser('~/bpy/bin/python')


def render(scale, f):
    p = os.path.join(out, '%s_s%d_f%02d.exr' % (shot, scale, f))
    if not os.path.exists(p.replace('.exr', '.npy')):
        subprocess.run([PY, os.path.join(HERE, 'lt_render.py'), blend, shot, p, str(W * scale), str(H * scale), '1',
                        'coverage=1', 'sway=%.4f' % (f / nf), 'pf=0.01'], check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    x = np.load(p.replace('.exr', '.npy'))[..., 0]
    return x.reshape(H, scale, W, scale).mean((1, 3))


diffs, tests = [], []
for f in range(nf):
    t = render(2, f); r = render(4, f)
    tests.append(t); diffs.append((t - r) * 255.0)
D = np.array(diffs)
sh = D.std(0)
T = np.array(tests) * 255.0
edge = (T.mean(0) > 2) & (T.mean(0) < 253)
res = dict(shot=shot, frames=nf, size=[W, H], shimmer_mean=float(sh.mean()), shimmer_p99=float(np.percentile(sh, 99)),
           shimmer_frac_gt4=float((sh > 4).mean()), edge_px_frac=float(edge.mean()),
           shimmer_mean_on_edges=float(sh[edge].mean()) if edge.any() else 0.0)
json.dump(res, open(os.path.join(out, '%s_shimmer.json' % shot), 'w'), indent=1)
from PIL import Image
hm = np.clip(sh / 16.0, 0, 1)
rgb = np.stack([hm ** 0.5, hm ** 1.5, hm ** 3], -1)
Image.fromarray((rgb * 255).astype(np.uint8)).save(os.path.join(out, '%s_shimmer_heat.png' % shot))
print(json.dumps(res, indent=1))


def weighted(shim_json, graded_png):
    """Coverage shimmer x the local contrast of the graded night frame (5x5 max - min of luma): what the flicker is in
    display codes, since a leaf edge only flickers by as much as the leaf differs from what is behind it."""
    from PIL import Image
    from scipy import ndimage
    s = json.load(open(shim_json))
    d = os.path.dirname(shim_json)
    nf = s['frames']; W, H = s['size']
    diffs = []
    for f in range(nf):
        t = np.load(os.path.join(d, 'hero_s2_f%02d.npy' % f))[..., 0].reshape(H, 2, W, 2).mean((1, 3))
        r = np.load(os.path.join(d, 'hero_s4_f%02d.npy' % f))[..., 0].reshape(H, 4, W, 4).mean((1, 3))
        diffs.append(t - r)
    sh = np.array(diffs).std(0)                         # coverage fraction
    g = np.asarray(Image.open(graded_png).convert('RGB'), float) @ np.array([0.2126, 0.7152, 0.0722])
    con = ndimage.maximum_filter(g, 5) - ndimage.minimum_filter(g, 5)
    w = sh * con
    s.update(night_shimmer_mean=float(w.mean()), night_shimmer_p99=float(np.percentile(w, 99)), night_shimmer_frac_gt4=float((w > 4).mean()),
             night_contrast_p50_on_edges=float(np.median(con[sh > 0.01])) if (sh > 0.01).any() else 0.0)
    json.dump(s, open(shim_json, 'w'), indent=1)
    return s
