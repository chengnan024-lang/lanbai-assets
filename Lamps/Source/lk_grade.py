# -*- coding: utf-8 -*-
"""Grade a reference render (lk_scene.render output) for its act and print the metrics.
usage: python lk_grade.py <render.exr> <act> <out.png> [thumb.png]"""
import json
import sys

import numpy as np

import lk_post as P

ACTS = {   # profile, fog density, fog fill (Unity colour picker, sRGB) - bible §6·1, §6·2, §6·11, §6·12
    'act1': ('S1', 0.009, '#161B27'),
    'act2': ('S2', 0.008, '#0D0F15'),
    'act11': ('S11', 0.006, '#0D0F15'),
    'act12': ('S12', 0.005, '#151C27'),
}


def run(exr, act, out, thumb=None, regions=None):
    rgb = np.load(exr.replace('.exr', '.npy'))
    dep = np.load(exr.replace('.exr', '_depth.npy'))
    sid, dens, col = ACTS[act]
    sky = dep > 1e5
    codes, m = P.grade(rgb, dep, sid, fog=(dens, col), sky_mask=sky, out=out, regions=regions, thumb=thumb)
    m['profile'] = sid
    return codes, m


if __name__ == '__main__':
    exr, act, out = sys.argv[1:4]
    thumb = sys.argv[4] if len(sys.argv) > 4 else None
    _, m = run(exr, act, out, thumb)
    print(json.dumps(m, indent=1))
