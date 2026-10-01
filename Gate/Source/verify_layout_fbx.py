"""Check GateLayout_v2.fbx the way Unity reads it: parse the raw FBX (io_scene_fbx.parse_fbx), take each Model's
Lcl Translation / Lcl Rotation (XYZ Euler, R = Rz Ry Rx) / Lcl Scaling (+ PreRotation if present), apply Unity's
FBX axis conversion (the file is Y-up right-handed; Unity mirrors X: M_unity = S M_fbx S, S = diag(-1, 1, 1)) and
compare with GateLayout_v2.json (GateRoot-local position, rotation, uniform scale)."""
import json
import math
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bpy  # noqa: E402,F401
import addon_utils  # noqa: E402
addon_utils.enable('io_scene_fbx')
import io_scene_fbx.parse_fbx as pf  # noqa: E402


def rot_xyz(d):
    x, y, z = np.radians(d)
    Rx = np.array([[1, 0, 0], [0, math.cos(x), -math.sin(x)], [0, math.sin(x), math.cos(x)]])
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    Rz = np.array([[math.cos(z), -math.sin(z), 0], [math.sin(z), math.cos(z), 0], [0, 0, 1]])
    return Rz @ Ry @ Rx


def models(path):
    root, ver = pf.parse(path)
    objs = [e for e in root.elems if e.id == b'Objects'][0]
    out = {}
    for m in [e for e in objs.elems if e.id == b'Model']:
        name = m.props[1].split(b'\x00')[0].decode()
        P = dict(t=np.zeros(3), r=np.zeros(3), s=np.ones(3), pre=np.zeros(3))
        p70 = [e for e in m.elems if e.id == b'Properties70']
        for p in (p70[0].elems if p70 else []):
            k = p.props[0]
            if k == b'Lcl Translation':
                P['t'] = np.array(p.props[4:7], float)
            elif k == b'Lcl Rotation':
                P['r'] = np.array(p.props[4:7], float)
            elif k == b'Lcl Scaling':
                P['s'] = np.array(p.props[4:7], float)
            elif k == b'PreRotation':
                P['pre'] = np.array(p.props[4:7], float)
        out[name] = P
    gs = [e for e in root.elems if e.id == b'GlobalSettings'][0]
    axes = {p.props[0].decode(): p.props[-1] for p in [e for e in gs.elems if e.id == b'Properties70'][0].elems
            if p.props[0] in (b'UpAxis', b'UpAxisSign', b'FrontAxis', b'FrontAxisSign', b'CoordAxis', b'CoordAxisSign',
                              b'UnitScaleFactor')}
    return out, axes


def q2m(q):
    x, y, z, w = q
    return np.array([[1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w)],
                     [2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w)],
                     [2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)]])


def unity_of(P, unit=1.0):
    S = np.diag([-1.0, 1.0, 1.0])
    R = rot_xyz(P['pre']) @ rot_xyz(P['r'])
    return S @ (P['t'] * unit), S @ R @ S, P['s']


def check(fbx, js, verbose=True):
    M, axes = models(fbx)
    unit = float(axes.get('UnitScaleFactor', 100.0)) / 100.0
    doc = json.load(open(js))
    wp, wr, ws, n = 0.0, 0.0, 0.0, 0
    for it in doc['instances']:          # GateRoot children and the bus-relative near arms (under NearRoot)
        nm = [k for k in M if k == it['id'] or k.startswith(it['id'] + '__')][0]
        p, R, s = unity_of(M[nm], unit)
        wp = max(wp, float(np.abs(p - np.array(it['position'])).max()))
        wr = max(wr, float(np.abs(R - q2m(it['rotation_xyzw'])).max()))
        ws = max(ws, float(np.abs(s - it['scale']).max() / it['scale']))
        n += 1
    if verbose:
        print('FBX axes', axes)
        print('checked %d instances: max position error %.4f m, rotation-matrix error %.2e, scale rel error %.1e'
              % (n, wp, wr, ws))
    return wp, wr, ws


if __name__ == '__main__':
    check(os.path.join(HERE, 'GateLayout_v2.fbx'), os.path.join(HERE, 'GateLayout_v2.json'))
