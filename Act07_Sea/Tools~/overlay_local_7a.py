"""D-44 #5 per-cell check of the local captures (FromLocal/act07a_view/<run>/): draws WHERE each 7a object should be onto
阿白's screenshots, so every cell can be split into 'not drawn' / 'drawn but not in view' / 'behind the old roof'.

  ~/bpy/bin/python Act07_Sea/Tools~/overlay_local_7a.py <run dir> <out dir> [--layout <Act07_Layout.json>] [--eye x,y,z]

Camera = the capture's (LB_SeaViewAudit): 1600x900, vertical FOV 58.7155 deg (= horizontal 90), yaw 0, pitch 0 / +60,
from the eye in the bus frame (default 阿白's LB_Udon.HERO_EYE (0.70, 1.77, 0.20)). Use --layout with the layout the local
build actually ran (git show origin/main:Act07_Sea/Act07_Layout.json), not the working copy. Positions follow the same
laws as Docs~/lookdev/scene_7a.py (gather, last-shaft sweep, seeds' birth, trail pool age, warm point); only points the
water lets through (exp(-density d) > 0.1) are drawn. Marks:
  cyan line = forest shafts   yellow line = the last shaft   green dots = the ridge   red ring = sown light (born)
  magenta dot = hull glow (alive)   orange ring = warm point   white tick = Snell window edge (el 41.4) on the sea plane
Prints, per cell, how many of each land inside the image (whether glass or roof there is for the eye on the overlay)."""
import argparse
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import act07_motion as AM                                   # noqa: E402

W, H = 1600, 900
F = (H / 2) / math.tan(math.radians(58.7155) / 2)


def smooth(x):
    x = np.clip(x, 0.0, 1.0)
    return x * x * (3 - 2 * x)


def hash11(x):
    return np.modf(np.sin(x * 127.1 + 311.7) * 43758.5453)[0] % 1.0


def project(p, eye, pitch):
    """bus-frame points -> pixel (x, y) and a 'in front' mask; camera yaw 0, pitch + looks up"""
    v = np.atleast_2d(p) - eye
    cp, sp = math.cos(math.radians(pitch)), math.sin(math.radians(pitch))
    fwd = np.array([0.0, sp, cp]); up = np.array([0.0, cp, -sp]); right = np.array([1.0, 0.0, 0.0])
    z = v @ fwd
    ok = z > 0.05
    zz = np.where(ok, z, 1.0)
    return np.stack([W / 2 + F * (v @ right) / zz, H / 2 - F * (v @ up) / zz], -1), ok


def density(J, depth):
    W_ = J['water']['keys']
    ds = [k['depth'] for k in W_]
    if depth <= ds[0]:
        return W_[0]['density']
    for i in range(1, len(ds)):
        if depth < ds[i]:
            f = (depth - ds[i - 1]) / (ds[i] - ds[i - 1])
            return W_[i - 1]['density'] * (1 - f) + W_[i]['density'] * f
    return W_[-1]['density']


def objects(J, t, eye):
    """{kind: list of polylines (Nx3) or points}, bus frame, already filtered by the water"""
    U, P = J['unity'], J['particles']
    depth = AM.depth(t); dens = density(J, depth)
    busw = np.array([0.0, -depth, AM.fwd(t)])
    seen = lambda q: np.exp(-dens * np.linalg.norm(q - eye, axis=-1)) > 0.1
    out = dict(shafts=[], last=[], ridge=None, seeds=None, trails=None, warm=None, window=None)
    under = t >= U['eye_under']
    # forest shafts
    g = 1 - min(max((depth - U['shaft_depth_full']) / (U['shaft_depth_gone'] - U['shaft_depth_full']), 0), 1)
    gather = float(smooth((t - U['gather_t0']) / (U['gather_t1'] - U['gather_t0'])))
    if t > U['gather_t0']:
        g = g + (1 - g) * gather
    if t > U['gather_t1']:
        g *= 1 - float(smooth((t - U['gather_t1']) / (U['shafts_gone_t'] - U['gather_t1'])))
    if under and g > 0.01:
        gp = np.asarray(U['gather_point_bus'])
        for i in range(len(U['shaft_half_width'])):
            c = np.asarray(U['shaft_centre'][3 * i:3 * i + 3]) - busw
            c = c + (gp + (c - gp) * 0.12 - c) * gather
            a = np.asarray(U['shaft_axis'][3 * i:3 * i + 3])
            q = c[None, :] + a[None, :] * (np.linspace(-0.5, 0.5, 25)[:, None] * U['shaft_length'][i])
            q = q[seen(q)]
            if len(q) > 1:
                out['shafts'].append(q)
    # the last shaft
    u = t - U['last_t0']; tot = U['last_in'] + U['last_sweep'] + U['last_out']
    if 0 < u < tot:
        sw = float(smooth((u - U['last_in'] * 0.5) / (U['last_sweep'] + U['last_in'])))
        c = np.asarray(U['last_from']) * (1 - sw) + np.asarray(U['last_to']) * sw
        foot = np.asarray(U['last_target']) * (1 - sw) + np.asarray(U['last_target_to']) * sw
        out['last'].append(np.stack([c, foot]))
    # the ridge (gain = the trails' from F4)
    if t >= U['F4']:
        R = J['ridge']; gr = R['grid']
        X = np.asarray(R['x']).reshape(gr['ny'], gr['nz'])
        ys = gr['y0'] + gr['dy'] * np.arange(gr['ny']); zs = gr['z0'] + gr['dz'] * np.arange(gr['nz'])
        Z, Y = np.meshgrid(zs, ys)
        yaw = math.radians(R.get('yaw_deg', 0.0))
        Xr = X * math.cos(yaw) + Z * math.sin(yaw); Zr = -X * math.sin(yaw) + Z * math.cos(yaw)
        q = np.stack([Xr, Y, Zr], -1)[::3, ::3].reshape(-1, 3) - busw
        out['ridge'] = q[seen(q)]
    # sown lights
    if t >= U['F3i'] - 0.1:
        Sd = P['seeds']
        q = np.asarray(Sd['positions']).reshape(-1, 3) - busw
        born = np.asarray(Sd['birth_t']) <= t
        out['seeds'] = q[born & seen(q)]
    # hull glow (pool positions moved by their age, as the shader)
    if t >= U['F4']:
        pts = []
        for key, fade in (('trails', None), ('trails_front', U.get('trails_front_fade'))):
            Tr = P.get(key)
            if Tr is None or (fade and t > fade[1]):
                continue
            period = Tr['pool'] / Tr['rate']
            ph = np.asarray(Tr['phase']); life = np.asarray(Tr['life']); seed = np.asarray(Tr['seed'])
            x = (t - Tr['T0']) / period - ph
            cyc = np.floor(x); age = (x - cyc) * period
            alive = (t >= Tr['T0'] + ph * period) & (age < life)
            h = hash11(seed * 91.7 + cyc * 1.31)
            jit = (np.stack([hash11(h * 13.1), hash11(h * 17.9), hash11(h * 23.3)], -1) - 0.5) * 0.25
            vel = np.array([0.0, -AM.SINK.v(t), AM.FWD.v(t) if t > AM.FWD.T0 else 0.0])
            q = np.asarray(Tr['positions']).reshape(-1, 3) + jit - vel[None, :] * age[:, None] + np.array([0.0, 0.02, 0.0]) * age[:, None]
            pts.append(q[alive])
        out['trails'] = np.concatenate(pts) if pts else None
    if t >= U['F5'] - 0.01:
        out['warm'] = (np.asarray(U['warm_position']) - busw)[None, :]
    # the Snell window's edge on the surface (a ring 41.4 deg above the horizon, around the eye)
    if under:
        th = np.radians(np.arange(0, 360, 3)); r = (depth + eye[1]) / math.tan(math.radians(41.4))
        out['window'] = np.stack([eye[0] + r * np.sin(th), np.full_like(th, depth), eye[2] + r * np.cos(th)], -1)
    return out


def inframe(xy, ok):
    return ok & (xy[:, 0] >= 0) & (xy[:, 0] < W) & (xy[:, 1] >= 0) & (xy[:, 1] < H)


def draw(img, obj, eye, pitch):
    d = ImageDraw.Draw(img)
    n = {}
    for kind, col in (('shafts', (0, 255, 255)), ('last', (255, 230, 0))):
        k = 0
        for q in obj[kind]:
            xy, ok = project(q, eye, pitch)
            if inframe(xy, ok).any():
                k += 1
            pts = [tuple(p) for p, o in zip(xy, ok) if o]
            if len(pts) > 1:
                d.line(pts, fill=col, width=3)
        n[kind] = k
    for kind, col, r, ring in (('ridge', (0, 255, 0), 2, False), ('trails', (255, 0, 255), 2, False), ('seeds', (255, 40, 40), 7, True),
                               ('warm', (255, 150, 0), 12, True), ('window', (255, 255, 255), 2, False)):
        q = obj[kind]
        if q is None or len(q) == 0:
            n[kind] = 0
            continue
        xy, ok = project(q, eye, pitch)
        m = inframe(xy, ok)
        n[kind] = int(m.sum())
        for x, y in xy[m]:
            if ring:
                d.ellipse([x - r, y - r, x + r, y + r], outline=col, width=2)
            else:
                d.ellipse([x - r, y - r, x + r, y + r], fill=col)
    return n


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('run'); ap.add_argument('out')
    ap.add_argument('--layout', default=os.path.join(HERE, '..', 'Act07_Layout.json'))
    ap.add_argument('--eye', default='0.70,1.77,0.20')
    a = ap.parse_args()
    J = json.load(open(a.layout, encoding='utf-8'))
    eye = np.array([float(v) for v in a.eye.split(',')])
    os.makedirs(a.out, exist_ok=True)
    rows = []
    for t in (363.3, 367.2, 387.0, 446.0, 462.4, 474.4, 506.4, 532.4, 556.4, 559.0, 630.0, 645.0):
        st = os.path.join(a.run, '%.1f_state.txt' % t)
        ta = float(open(st, encoding='utf-8').readline().split('actual=')[1].split()[0]) if os.path.exists(st) else t
        obj = objects(J, ta, eye)
        row = dict(t=t, actual=ta)
        for view, pitch in (('front', 0.0), ('up60', 60.0)):
            p = os.path.join(a.run, '%.1f_%s.png' % (t, view))
            img = Image.open(p).convert('RGB') if os.path.exists(p) else Image.new('RGB', (W, H))
            row[view] = draw(img, obj, eye, pitch)
            img.save(os.path.join(a.out, '%.1f_%s.png' % (t, view)))
        rows.append(row)
        print(json.dumps(row, ensure_ascii=False))
    json.dump(rows, open(os.path.join(a.out, 'overlay_counts.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


if __name__ == '__main__':
    main()
