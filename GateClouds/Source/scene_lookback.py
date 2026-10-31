"""蓝白 / Lanbai · gate + inside, looking back past U9 (总导演 10-26: the hands in lip 1's opening read as silhouettes,
the lip's bright edge does not cut them). For the render harness:

  python3 Engineering/render_harness/lbh_render.py --scene GateClouds/Source/scene_lookback.py --cam hero --yaw 180 \
      --t 182.0 --grade S4c --act 04c --lens clean --bus none --res 960x540 --out ...

The inside (lips, fringe, threads, dome, loose threads) = Act04c_Inside/Docs~/lookdev/scene_4c.py build(ctx), unchanged.
Added: the six hands kept past U9 (seam_ref.arm_meshes: the driver's pose, TentacleSway v2.9 curl), in the same
bus-relative frame (the gate origin's z = -s(t) = inside_def.dist), as TentacleSway past U9: _Silhouette 1 (black
surface), the inside's fog (model B colour, its density), capped at _FogHold (0.7, let go over 184.0 -> 184.5) and the
reveal (184.0 -> 184.5). ctx['args']: cap=<x> (1 = no cap).
"""
import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, HERE)
_spec = importlib.util.spec_from_file_location('scene_4c', os.path.join(REPO, 'Act04c_Inside', 'Docs~', 'lookdev', 'scene_4c.py'))
S4 = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(S4)
import bpy  # noqa: E402
import seam_ref as SR  # noqa: E402

U9 = 179.55


def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def mat_hand(fp, hold, rv):
    m = bpy.data.materials.new('Gate_KeptHand')
    N = S4.NT(m)
    f = N.math('MINIMUM', N.fog_amount(fp['density']), float(hold))
    f = N.math('SUBTRACT', 1.0, N.math('MULTIPLY', N.math('SUBTRACT', 1.0, f), float(rv)))
    N.done(N.emission(N.mix(N.rgb((0.0, 0.0, 0.0)), N.horizon(fp), f)))
    return m


def build(ctx):
    res = S4.build(ctx)
    t = float(ctx['t'])
    a = ctx.get('args', {}) or {}
    cap = float(a.get('cap', 0.7))
    fp = S4.DR.state(t)['fog']
    sil = ss((t - (U9 - 0.05)) / 0.3)
    hold = (1.0 - sil) + cap * sil
    hold = hold + (1.0 - hold) * ss((t - 184.0) / 0.5)
    rv = 1.0 - min(max((t - 184.0) / 0.5, 0.0), 1.0)
    mat = mat_hand(fp, hold, rv)
    n = 0
    for name, V, F, p, R, sc in SR.arm_meshes(t, True):
        if not SR.LAY[name].get('curl'):
            continue
        S4.mesh(None, 'Gate_' + name, dict(V=V, F=F), 0.0, mat)
        n += 1
    res['what'] += ' + gate hands %d (cap %.2f, hold %.2f, reveal %.2f)' % (n, cap, hold, rv)
    return res
