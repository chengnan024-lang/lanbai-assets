"""Fast composition planner (numpy + PIL, no Cycles): silhouettes of every layer from a camera at time t,
aerial perspective approximated with the bible fog, S4 display. For iterating the layout in seconds.

usage: python3 gate_plan.py SHOT [W] [out.png]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

import gate_layout as G

TEAR_V2 = os.path.join(G.LAN, 'tear', 'v2')
sys.path.insert(0, TEAR_V2)
import s4  # noqa: E402

FILL = json.load(open(os.path.join(G.LAN, 'tear', 'tear_fills.json')))
F = {k: np.array(v['linear']) for k, v in FILL.items()}


def band(az, el):
    az = np.abs(az)
    t = G.ss(az / 50.0)[..., None]
    c = F['HazeNear'] * (1 - t) + F['HazeFar'] * t
    w = ((1 - G.ss((az - 50) / 10)) * G.band_el(el))[..., None]
    sky = F['Void'] * (1 - w) + c * w
    below = (0.55 + 0.45 * G.ss((el + 25) / 25))[..., None]
    return sky * below


from gate_scene_shots import SHOTS as _S  # noqa: E402
SHOTS = {k: (v['t'], v['eye'], v['yaw'], v['pitch'], v['hfov'], v['aspect']) for k, v in _S.items()}


class Cam:
    def __init__(self, pos, yaw, pitch, hfov, W, H):
        self.pos = np.asarray(pos, float)
        y, p = math.radians(yaw), math.radians(pitch)
        self.fwd = np.array([math.sin(y) * math.cos(p), math.cos(y) * math.cos(p), math.sin(p)])
        self.right = np.array([math.cos(y), -math.sin(y), 0.0])
        self.up = np.cross(self.right, self.fwd)
        self.W, self.H = W, H
        self.f = (W / 2) / math.tan(math.radians(hfov) / 2)

    def proj(self, P):
        d = np.asarray(P, float) - self.pos
        z = d @ self.fwd
        x = d @ self.right
        y = d @ self.up
        zz = np.maximum(z, 1e-3)
        return np.stack([self.W / 2 + self.f * x / zz, self.H / 2 - self.f * y / zz, z], -1)

    def rays(self):
        xs = (np.arange(self.W) + 0.5 - self.W / 2) / self.f
        ys = -(np.arange(self.H) + 0.5 - self.H / 2) / self.f
        X, Y = np.meshgrid(xs, ys)
        D = self.fwd[None, None] + X[..., None] * self.right[None, None] + Y[..., None] * self.up[None, None]
        return D / np.linalg.norm(D, axis=-1, keepdims=True)


def fog_amount(d, h, far_cap=True, cap=0.6, cap_h=500.0):
    rho = 0.0006 * (1 + 0.5 * np.exp(-np.maximum(h, 0) / 60.0))
    f = 1 - np.exp(-d * rho)
    if far_cap:
        fc = np.minimum(f, cap) * (np.exp(-np.maximum(h, 0) / cap_h) if cap_h else 1.0)
        w = G.ss((d - 1300) / 400)
        f = f * (1 - w) + fc * w
    return f


def plan(shot, W=960, out=None, layout=None, tide=None, extra=None):
    t, eye, yaw, pitch, hfov, asp = SHOTS[shot]
    H = int(round(W / asp))
    ss_ = 2
    cam = Cam(G.eye_cf(t, eye), yaw, pitch, hfov, W * ss_, H * ss_)
    D = cam.rays()
    az, el = G.azel_of(D)
    img = band(az, el)
    # moon + halo
    cosm = np.clip(D @ G.L_MOON, -1, 1)
    ang = np.degrees(np.arccos(cosm))
    img = img + (np.exp(-1.2 * ang) * 0.10 + np.exp(-0.3 * ang) * 0.035)[..., None] * np.array([0.27, 0.35, 0.58])
    disc = (ang < 0.6)[..., None]
    img = np.where(disc, F['MoonDisc'], img)
    # cloud floor below the horizon (flat at z = 0): dark silver, fogged
    down = D[..., 2] < -1e-4
    dist = np.where(down, -cam.pos[2] / np.minimum(D[..., 2], -1e-4), 1e9)
    fl = fog_amount(dist, 0.0, far_cap=False)
    floor = np.array([0.05, 0.055, 0.075]) * (1 - fl[..., None]) + band(az, np.full_like(el, 0.0)) * fl[..., None]
    img = np.where(down[..., None], floor, img)
    # tear glow (halo approx)
    core = G.tear_core_cf(t) + np.array([0, G.gate_z(0) * 0, 0])
    tc = core - cam.pos
    tcn = tc / np.linalg.norm(tc)
    at = np.degrees(np.arccos(np.clip(D @ tcn, -1, 1)))
    Hdeg = math.degrees(math.atan(G.tear_H(t) / np.linalg.norm(tc)))
    img = img + F['Halo'][None, None] * (0.8 / (1 + (at / (0.35 * Hdeg)) ** 2))[..., None]
    lin = img.astype(np.float64)
    pil = Image.fromarray(np.zeros((cam.H, cam.W), np.uint8))

    # --- tear lens polygon
    S = G.tear_H(t) / G.TD.H
    w = G.TD.width_mul(G.tear_open(t))
    tt = np.linspace(G.TD.T_BOT, G.TD.T_TOP, 200)
    aL, aR = G.TD.lips(tt)
    PL = G.TD.P(tt, aL * w) * S
    PR = G.TD.P(tt, aR * w) * S
    poly = np.concatenate([PL, PR[::-1]])
    poly = poly[poly[:, 2] > -5]
    sp = cam.proj(poly)
    m = Image.new('L', (cam.W, cam.H), 0)
    if (sp[:, 2] > 1).all():
        ImageDraw.Draw(m).polygon([tuple(p[:2]) for p in sp], fill=255)
    a = np.asarray(m, np.float64)[..., None] / 255
    lin = lin * (1 - a) + F['Core'][None, None] * a

    # --- tide (atlas cells blitted, fogged, cap 0.92)
    if tide:
        atl = {}
        for td in sorted(tide, key=lambda d: -np.linalg.norm(d['root'] - cam.pos)):
            r = G.tide_root_at(td, t)
            c = td['cell']
            if c['atlas'] not in atl:
                atl[c['atlas']] = np.asarray(Image.open(os.path.join(G.LAN, 'deliver', 'Tentacles', 'Textures',
                                                                   c['atlas'] + '.png')).convert('RGBA'), np.float64) / 255
            A = atl[c['atlas']]
            u0, v0, u1, v1 = c['uv_rect']
            h_, w_ = A.shape[:2]
            cell = A[int((1 - v1) * h_):int((1 - v0) * h_), int(u0 * w_):int(u1 * w_)]
            Hq = c['cell_height_in_lengths'] * td['size']
            Wq = Hq * 0.5
            p0 = cam.proj(r)
            if p0[2] < 10:
                continue
            ph = cam.f * Hq / p0[2]
            pw = ph * 0.5
            if ph < 2:
                continue
            mirror = r[0] > 0
            ru = c['root_u']
            x0 = p0[0] - ((1 - ru) * pw if mirror else ru * pw)
            y0 = p0[1] - ph
            ci = Image.fromarray((cell * 255).astype(np.uint8), 'RGBA')
            if mirror:
                ci = ci.transpose(Image.FLIP_LEFT_RIGHT)
            ci = ci.resize((max(int(pw), 1), max(int(ph), 1)), Image.BILINEAR)
            ca = np.asarray(ci, np.float64) / 255
            X0, Y0 = int(round(x0)), int(round(y0))
            hh, ww = ca.shape[:2]
            xa, ya = max(X0, 0), max(Y0, 0)
            xb, yb = min(X0 + ww, cam.W), min(Y0 + hh, cam.H)
            if xa >= xb or ya >= yb:
                continue
            sub = ca[ya - Y0:yb - Y0, xa - X0:xb - X0].copy()
            ycl = cam.proj(np.array([r[0], r[1], 0.0]))[1]          # the cloud top at the root: hide what is below
            rows = np.arange(ya, yb)[:, None]
            sub[..., 3] *= (rows < ycl)
            d = np.linalg.norm(r - cam.pos)
            az0, el0 = G.azel_of(r - cam.pos)
            fg = min(fog_amount(d, 0.0, far_cap=False), 0.92)
            col = (sub[..., :3] ** 2.2) * (1 - fg) + band(np.array(az0), np.array(el0 + 2.0)) * fg
            al = sub[..., 3:4]
            lin[ya:yb, xa:xb] = lin[ya:yb, xa:xb] * (1 - al) + col * al

    # --- tentacles, far to near, per-segment fog
    layout = layout or []
    order = sorted(layout, key=lambda it: -np.linalg.norm(G.pose_at(it, t)[0] - cam.pos))
    for it in order:
        root, R = G.pose_at(it, t)
        lod = 1 if it['layer'] in ('mid', 'near', 'colossus', 'rear') else 2
        for (C, r, u) in G.parts(it['variant'], lod):
            Wc = root + it['scale'] * (C @ R.T)
            rr = it['scale'] * r * G.form_mult(u, it.get('girth', 1.0), it['variant'])
            sp = cam.proj(Wc)
            if (sp[:, 2] < 2).all():
                continue
            rho = cam.f * rr / np.maximum(sp[:, 2], 1)
            rho = np.maximum(rho, 0.6)
            m = Image.new('L', (cam.W, cam.H), 0)
            dr = ImageDraw.Draw(m)
            for i in range(len(sp) - 1):
                if sp[i, 2] < 2 or sp[i + 1, 2] < 2:
                    continue
                if Wc[i, 2] < 0 or Wc[i + 1, 2] < 0:
                    continue
                d2 = sp[i + 1, :2] - sp[i, :2]
                n = np.array([-d2[1], d2[0]])
                n = n / (np.linalg.norm(n) + 1e-9)
                q = [sp[i, :2] + n * rho[i], sp[i + 1, :2] + n * rho[i + 1], sp[i + 1, :2] - n * rho[i + 1],
                     sp[i, :2] - n * rho[i]]
                if np.abs(np.array(q)).max() > 1e5:
                    continue
                dr.polygon([tuple(x) for x in q], fill=255)
                dr.ellipse([sp[i, 0] - rho[i], sp[i, 1] - rho[i], sp[i, 0] + rho[i], sp[i, 1] + rho[i]], fill=255)
            a = np.asarray(m, np.float64) / 255
            ys, xs = np.nonzero(a > 0)
            if len(ys) == 0:
                continue
            # per-pixel fog: distance / height from the nearest centre sample (approx.)
            y0, y1, x0, x1 = ys.min(), ys.max() + 1, xs.min(), xs.max() + 1
            sub = a[y0:y1, x0:x1]
            gy, gx = np.mgrid[y0:y1, x0:x1]
            from scipy.spatial import cKDTree
            okp = (sp[:, 2] > 2) & (Wc[:, 2] > -5)
            idx = np.nonzero(okp)[0] if okp.any() else np.arange(len(sp))
            _, kk = cKDTree(sp[idx, :2]).query(np.stack([gx.ravel(), gy.ravel()], -1))
            k = idx[kk].reshape(gx.shape)
            dd = sp[k, 2]
            hh = np.maximum(Wc[k, 2], 0)
            cap = 0.6
            dens = G.fog_scale_at(it, t)
            fgv = fog_amount(dd * dens, hh, far_cap=it['layer'] in ('colossus_bg',) or it.get('role') in ('moon', 'rilke'), cap=cap)
            fgv = np.where(Wc[k, 2] < 0, np.maximum(fgv, 0.9), fgv)
            azp, elp = G.azel_of(D[y0:y1, x0:x1])
            body = np.array([0.006, 0.0062, 0.0075])
            col = body * (1 - fgv[..., None]) + band(azp, elp) * fgv[..., None]
            lin[y0:y1, x0:x1] = lin[y0:y1, x0:x1] * (1 - sub[..., None]) + col * sub[..., None]
    lin = lin.reshape(cam.H // ss_, ss_, cam.W // ss_, ss_, 3).mean((1, 3))
    disp = s4.to_display(lin, bloom=False, vignette=False)
    im = Image.fromarray((disp * 255 + 0.5).astype(np.uint8))
    if os.environ.get('PLAN_LABELS'):
        dr = ImageDraw.Draw(im)
        for it in layout:
            W_, u_ = G.world_centreline(it, t, 6)
            sp = cam.proj(W_)
            ok = (sp[:, 2] > 1) & (W_[:, 2] > 0)
            if not ok.any():
                dr.text((5, 5 + 10 * (hash(it['id']) % 30)), it['id'] + ' (hidden)', fill=(255, 80, 80))
                continue
            k = np.argmin(np.where(ok, sp[:, 1], 1e9))
            x, y = sp[k, 0] / ss_, sp[k, 1] / ss_
            col = {'mid': (120, 200, 255), 'colossus': (255, 200, 80), 'colossus_bg': (255, 140, 60),
                   'rear': (200, 120, 255), 'near': (255, 255, 255)}.get(it['layer'], (255, 255, 255))
            dr.text((x + 2, y - 10), it['id'].replace('Colossus_', 'C').replace('Mid_', 'M'), fill=col)
    if extra:
        extra(im, cam, ss_)
    out = out or os.path.join(G.WIP, 'plan_%s.png' % shot)
    im.save(out)
    return out


def guides(im, cam, ss_):
    """draw the windscreen (az -50..+25, el -15..+22) and skylight outlines + the Rilke text box."""
    dr = ImageDraw.Draw(im)

    def p(az, el):
        v = G.dir_azel(az, el)
        d = v @ cam.fwd
        if d <= 0.05:
            return None
        return (cam.W / 2 + cam.f * (v @ cam.right) / d) / ss_, (cam.H / 2 - cam.f * (v @ cam.up) / d) / ss_
    for poly, col in (([(-50, -15), (25, -15), (25, 22), (-50, 22)], (255, 200, 80)),
                      ([(-5, 40), (23, 40), (23, 68), (-5, 68)], (120, 255, 160)),
                      ([(13, 1), (27, 1), (27, 5), (13, 5)], (255, 120, 200))):
        pts = [p(a, e) for a, e in poly]
        if all(q is not None for q in pts):
            dr.line(pts + [pts[0]], fill=col, width=1)


if __name__ == '__main__':
    shot = sys.argv[1]
    W = int(sys.argv[2]) if len(sys.argv) > 2 else 960
    lay = G.build_layout()
    cells = json.load(open(os.path.join(G.LAN, 'deliver', 'Tentacles', 'Textures', 'TentacleTide_Atlas.json')))['cells']
    tide = G.build_tide(cells)
    print(plan(shot, W, layout=lay, tide=tide, extra=guides if shot != 'key' else None))
