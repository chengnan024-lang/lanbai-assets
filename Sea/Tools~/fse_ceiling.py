# -*- coding: utf-8 -*-
"""act-8 ceiling: the screen fraction each piece of Sea_Ceiling.fbx covers (hero eye, 1920x1080, 90 deg desktop), for the
FSE ledger. Inner disc r <= 2.3 km (opaque until 956.36), edge ring 2.3 .. 3.2 km (transparent throughout). The plane is
h m above the eye (exit 922.36: just over the eye; F9b 940.36: 148 m; F10e 956.36: 272 m).
  ~/bpy/bin/python Sea/Tools~/fse_ceiling.py  ->  Sea/Docs~/fse_ceiling.json"""
import json
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import sea_numpy as S  # noqa: E402

SEAM, OUTER = 2300.0, 3200.0


def main():
    out = dict(about=__doc__.split('\n')[0] + ' Inner opaque until 956.36 (no blend cost), then transparent for the 9 s dissolve; '
                                              'the edge ring is transparent throughout. Seam at 2.3 km (final review #3).', frames={})
    for name, h in (('exit 922.36', 0.5), ('F9b 940.36', 148.0), ('F10e 956.36', 272.0)):
        for pitch in (0, 35):
            rays = S.camera_rays(1920, 1080, 90.0, 0.0, float(pitch))
            up = rays[..., 1] > 1e-6
            s = np.where(up, h / np.maximum(rays[..., 1], 1e-6), np.inf)
            r = np.hypot(rays[..., 0] * s, rays[..., 2] * s)
            inner = up & (r <= SEAM)
            edge = up & (r > SEAM) & (r <= OUTER)
            out['frames']['%s pitch %d' % (name, pitch)] = dict(h_m=h, inner_FSE=round(float(inner.mean()), 3), edge_ring_FSE=round(float(edge.mean()), 3))
    json.dump(out, open(os.path.join(os.path.dirname(HERE), 'Docs~', 'fse_ceiling.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(out['frames']))


if __name__ == '__main__':
    main()
