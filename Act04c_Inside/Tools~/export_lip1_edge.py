"""D-49 (looking back, A): the torn edge of lip 1 as the inside package actually builds it, for the gate's six hands
(their fingertips grip the real edge, curl included; 总导演 10-26: keep the edge's shape, do not flatten it).

  ~/bpy/bin/python export_lip1_edge.py   -> ../Docs~/lip1_torn_edge.json

Frame: InsideRoot local, metres (Unity axes). x = right, y = up, both in the lip frame = the Tear kit's (x, z - 150)
(tear_def.P: x across, z up; the entry point is at the bus origin, 150 m above the cloud top). z = out of lip 1's plane
(0 = the plane = _Udon_InsidePortal.x in world); +z = the bus's direction of travel (into the inside), -z = toward the
gate world where the hands are. InsideRoot.localPosition = (0, 0, -s(t)), lip 1 at local z = LipS[0] = 0.
Each point also carries the nearest Tear-kit parameter (t, side) so the gate can map it onto its own lens.
"""
import json
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inside_def as D  # noqa: E402
import inside_geom as GE  # noqa: E402


def main():
    rep, objs, meta = GE.build()
    C = np.asarray([L for L in meta['lips'] if L['k'] == 1][0]['contour'], float)
    sh = objs['Lip1_Sheet']
    V = np.asarray(sh['V'], float)[:len(C)]
    assert np.allclose(V[:, :2], C, atol=1e-3), 'sheet edge ring != contour'
    assert np.allclose(np.asarray(sh['uv1'], float)[:len(C), 0], 0.0, atol=1e-3), 'not the torn edge (uv1.x != 0)'
    sys.path.insert(0, os.path.join(D.REPO, 'Tear', 'Source'))
    import tear_def as TD
    t = np.linspace(TD.T_BOT + 0.5, TD.T_TOP - 0.5, 4000)
    aL, aR = TD.lips(t)
    kit = []
    for side, a in (('right', aR), ('left', aL)):
        P = TD.P(t, a)
        kit += [(float(tt), side, float(x), float(z) - 150.0) for tt, x, z in zip(t, P[:, 0], P[:, 2])]
    K = np.array([(k[2], k[3]) for k in kit])
    pts = []
    for x, y, z in V:
        j = int(np.argmin(np.sum((K - (x, y)) ** 2, 1)))
        pts.append(dict(x=round(float(x), 3), y=round(float(y), 3), z=round(float(z), 3),
                        kit_t=round(kit[j][0], 4), kit_side=kit[j][1], kit_dist_m=round(float(np.hypot(*(K[j] - (x, y)))), 3)))
    z = V[:, 2]
    out = dict(about=__doc__.strip().split('\n\n', 1)[1], lip=1, H_m=1000.0, n=len(pts), spacing_m=3.5,
               z_min_m=round(float(z.min()), 3), z_max_m=round(float(z.max()), 3), z_rms_m=round(float(np.sqrt(np.mean(z ** 2))), 3),
               curl='inside_geom.curl_z: amplitude 0.006 H, multi-scale noise along the edge, decays exp(-d / 0.015 H) away from it',
               points=pts)
    p = os.path.join(D.KIT, 'Docs~', 'lip1_torn_edge.json')
    json.dump(out, open(p, 'w'), ensure_ascii=False, indent=0)
    print(p, len(pts), 'points; z %.2f .. %.2f m (rms %.2f); max kit distance %.2f m' % (z.min(), z.max(), out['z_rms_m'], max(q['kit_dist_m'] for q in pts)))


if __name__ == '__main__':
    main()
