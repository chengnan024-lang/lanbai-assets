"""蓝白 / Lanbai · gate clouds kit · whole-frame preview: deck + cards + beams, the Unity way, graded with S4.

Composites what the three shaders draw (deck_ref.render_deck, then every card of GateClouds_Layout.json back to
front with Lanbai_GateCloudCard's maths and the deck's depth, then the shafts / wedges with Lanbai_GateBeam's), from
a GateLayout_v2.json camera, and grades it with the PPv2 S4 engine model. No arms, no tear (those are Unity's):
optionally pasted from a Unity screenshot where it shows sky or flat fog (--over).

  /tmp/claude-0/venv/bin/python preview_gate.py key --w 1280 [--over ../../FromLocal/gate_test/keyart_unity_t154.50.png]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.environ.get('GC_KIT', os.path.dirname(HERE))
sys.path.insert(0, HERE)
import deck_ref as D  # noqa: E402

LAY = json.load(open(os.path.join(KIT, 'GateClouds_Layout.json')))
SHAPES = {s['shape']: s for s in LAY['shapes']}
CARD = dict(FogCap=float(os.environ.get('FOGCAP', 1.0)), MoonE=0.146, SkyE=0.89, SkyColor=np.array([0.060, 0.064, 0.088]), Lining=(0.35, 7.0, 15.0),
            FogDensity=0.0006, FogScale=1.0, MoonAirFog=0.35)
BEAM = dict(Tint=np.array([0.0362, 0.0343, 0.0873]), Lobe=(2.6, 1.0, 0.04, 1.3), EdgeFadePow=3.0,
            NearFadeM=(60.0, 460.0), FogDensity=0.0006, FogScale=0.5)


def tear_H(t):
    ks = LAY_G['timeline']['tear_H_knots']
    ts = [k['t'] for k in ks]
    hs = [k['H'] for k in ks]
    return float(np.interp(t, ts, hs))


LAY_G = D.LAYOUT


def srgb_dec(x):
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def load_card(shape, cache={}):
    if shape not in cache:
        a = np.asarray(Image.open(os.path.join(KIT, 'Textures', SHAPES[shape]['texture']))).astype(np.float32) / 255
        cache[shape] = np.concatenate([srgb_dec(a[..., :3]), a[..., 3:]], -1)
    return cache[shape]


def bilinear(img, u, v):
    h, w = img.shape[:2]
    x = np.clip(u * w - 0.5, 0, w - 1)
    y = np.clip((1 - v) * h - 0.5, 0, h - 1)
    x0 = np.floor(x).astype(int)
    y0 = np.floor(y).astype(int)
    x1 = np.minimum(x0 + 1, w - 1)
    y1 = np.minimum(y0 + 1, h - 1)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) + img[y1, x0] * (1 - fx) * fy
            + img[y1, x1] * fx * fy)


def card_value(c, t):
    """tower sag / sink / alpha at t (LanbaiGateClouds.Key)"""
    def key(k, d):
        if not k:
            return d
        ts, vs = k[0::2], k[1::2]
        if t <= ts[0]:
            return vs[0]
        if t >= ts[-1]:
            return vs[-1]
        for i in range(len(ts) - 1):
            if ts[i] <= t <= ts[i + 1]:
                return vs[i] + (vs[i + 1] - vs[i]) * D.ss(0, 1, (t - ts[i]) / max(ts[i + 1] - ts[i], 1e-4))
        return vs[-1]
    return key(c['sag_keys'], 1.0), key(c['sink_keys'], 0.0), key(c['alpha_keys'], 1.0)


def main():
    a = sys.argv[1:]
    camname = a[0]
    w = int(a[a.index('--w') + 1]) if '--w' in a else 1280
    cam = LAY_G['cameras'][camname]
    t = float(a[a.index('--t') + 1]) if '--t' in a else cam['t']
    h = int(round(w / cam['aspect']))
    P = dict(D.DEFAULTS)
    col, alpha, dist = D.render_deck(cam, t, w, h, os.path.join(KIT, 'Textures'), P, pool=True)
    V, _ = D.camera_rays(cam, w, h)
    eye = np.array(cam['eye_bus_relative'], float)
    O = D.gate_origin(t)
    top = -D.h_bus(t)
    tear = O + np.array([20.0, 147.0, 0.0])
    moon = D.MOON_DIR
    # ---- cards, back to front -----------------------------------------------------------------------------------
    items = []
    for c in LAY['cards']:
        sag, sink, al = card_value(c, t)
        if al <= 0.001:
            continue
        piv = O + np.array(c['position']) + np.array([0.0, sink, 0.0])
        items.append((np.linalg.norm(piv - eye), c, piv, sag, al))
    items.sort(key=lambda x: -x[0])
    layers = np.zeros((h, w), np.int32)                # transparent overdraw (raster coverage, after the deck's depth)
    fse = dict(cards=0.0, shafts=0.0, wedges=0.0)
    for _, c, piv, sag, al in items:
        s = SHAPES[c['shape']]
        W, Hh = c['size'][0], c['size'][1] * sag
        f = piv[[0, 2]] - eye[[0, 2]]
        f = -f / np.linalg.norm(f)                               # pivot -> eye (horizontal)
        right = np.array([-f[1], 0.0, f[0]])            # the eye's right (tech r1 #3: was the left)
        n = np.array([f[0], 0.0, f[1]])
        den = V @ n
        tt = ((piv - eye) @ n) / np.where(np.abs(den) > 1e-6, den, 1e-6)
        P3 = eye + V * tt[..., None]
        lx = (P3 - piv) @ right / W
        ly = (P3[..., 1] - piv[1]) / Hh
        u = lx + s['pivot_uv'][0]
        v = ly + s['pivot_uv'][1]
        m = (tt > 0) & (u >= 0) & (u <= 1) & (v >= 0) & (v <= 1) & (tt < dist)
        bb = s['bbox_uv']
        uu_ = 1 - u if c['mirror'] > 0.5 else u
        mr = (tt > 0) & (uu_ >= bb[0]) & (uu_ <= bb[2]) & (v >= min(bb[1], s['pivot_uv'][1])) & (v <= bb[3]) & (tt < dist)
        layers += mr
        fse['cards'] += mr.mean()
        if not m.any():
            continue
        uu = 1 - u[m] if c['mirror'] > 0.5 else u[m]
        tx = bilinear(load_card(c['shape']), uu, v[m])
        Vm = V[m]
        los = (piv - eye)[[0, 2]]
        los /= np.linalg.norm(los)
        mh = moon[[0, 2]] / np.linalg.norm(moon[[0, 2]])
        rel = math.degrees(math.acos(np.clip(los @ mh, -1, 1)))
        wk = np.clip((rel - 35.0) / 35.0, 0, 1)
        sc = s['scale']
        moonC = tx[:, 0] * sc[0] * (1 - wk) + tx[:, 1] * sc[1] * wk
        am = np.degrees(np.arccos(np.clip(Vm @ moon, -1, 1)))
        edge = D.ss(0.02, 0.35, tx[:, 3]) * (1 - D.ss(0.55, 0.95, tx[:, 3]))
        lining = CARD['Lining'][0] * np.exp(-am / CARD['Lining'][1]) * (1 - D.ss(0.6 * CARD['Lining'][2], CARD['Lining'][2], am)) * edge
        cc = (CARD['MoonE'] * moonC * (1 + lining))[:, None] * D.MOON_COL + \
             (CARD['SkyE'] * tx[:, 2] * sc[2])[:, None] * CARD['SkyColor']
        cc *= c['gain']
        dd = tt[m]
        fogC = D.band(Vm, eye, tear) + D.moon_air(Vm) * CARD['MoonAirFog']
        fo = np.minimum(1 - np.exp(-CARD['FogDensity'] * CARD['FogScale'] * dd), c.get('fog_cap', 1.0) * CARD['FogCap'])
        cc = cc * (1 - fo)[:, None] + fogC * fo[:, None]
        wy = P3[..., 1][m]
        aa = tx[:, 3] * c['opacity'] * al * D.ss(top + c['melt'][0], top + c['melt'][0] + c['melt'][1], wy)
        col[m] = col[m] * (1 - aa)[:, None] + cc * aa[:, None]
    # ---- beams ----------------------------------------------------------------------------------------------------
    H = tear_H(t)
    S = H / 1000.0
    for b in LAY['beams']:
        if b['parent'] == 'Tear_Root':
            def to_w(p):
                p = np.asarray(p, float)
                return O + np.array([0.0, -150.0, 0.0]) + np.array([-p[0], p[1], -p[2]]) * S
            st = to_w(b['start'])
            ax = np.array([-b['axis'][0], b['axis'][1], -b['axis'][2]])
            ln, hw0 = b['length'] * S, b['half_width'] * S
        else:
            st = O + np.array(b['start'])
            ax = np.array(b['axis'], float)
            ln, hw0 = b['length'], b['half_width']
        ax = ax / np.linalg.norm(ax)
        mid = st + ax * 0.5 * ln
        side = np.cross(ax, eye - mid)
        side /= np.linalg.norm(side)
        n = np.cross(ax, side)
        den = V @ n
        tt = ((st - eye) @ n) / np.where(np.abs(den) > 1e-6, den, 1e-6)
        P3 = eye + V * tt[..., None]
        z = ((P3 - st) @ ax) / ln
        if b['mode'] > 0.5:                              # a wedge stops 300 m before the eye (shader: the same)
            zmax = max((np.dot(eye - st, ax) - 300.0) / ln, 0.0)
            z = np.where(z <= zmax, z, 9.0)
        hw = hw0 * (1 + (b['widen'] - 1) * np.clip(z, 0, 1)) * 0.85      # the strip trimmed to the lobe's 4 %
        x = ((P3 - st) @ side) / hw
        m = (tt > 0) & (z >= 0) & (z <= 1) & (np.abs(x) <= 1) & (tt < dist)
        # the shader collapses the whole strip when it is seen along its axis or lies entirely inside the near fade
        perp_m = np.linalg.norm(np.cross(ax, (eye - mid) / np.linalg.norm(eye - mid)))
        nearfar = max(np.linalg.norm(st - eye), np.linalg.norm(st + ax * ln - eye))
        whole = np.clip(perp_m * 1.4, 0, 1) ** BEAM['EdgeFadePow'] * D.ss(BEAM['NearFadeM'][0] if b['mode'] < 0.5 else 0.0,
                                                                         BEAM['NearFadeM'][1] if b['mode'] < 0.5 else 1.0, nearfar)
        cone = 1.0
        if b['mode'] > 0.5:                              # the wedges' view cone toward the wound (25..40 deg)
            ang = math.degrees(math.acos(np.clip(np.dot((mid - eye) / np.linalg.norm(mid - eye), (tear - eye) / np.linalg.norm(tear - eye)), -1, 1)))
            cone = 1 - float(D.ss(25.0, 40.0, ang))
            whole *= cone
        if whole < 0.003:
            continue
        layers += m
        fse['shafts' if b['mode'] < 0.5 else 'wedges'] += m.mean()
        if not m.any():
            continue
        xx, zz = x[m] * 0.85, z[m]
        lo = BEAM['Lobe']
        lobe = np.exp(-lo[0] * xx * xx) * np.clip(1 - xx * xx, 0, 1) ** lo[1]
        along = D.ss(0, lo[2], zz) * np.clip(1 - zz, 0, 1) ** lo[3]
        Vm = V[m]
        perp = np.linalg.norm(np.cross(ax, -Vm), axis=-1)
        dd = tt[m]
        nf = BEAM['NearFadeM'] if b['mode'] < 0.5 else (0.0, 1.0)
        fade = np.clip(perp * 1.4, 0, 1) ** BEAM['EdgeFadePow'] * D.ss(nf[0], nf[1], dd) \
            * np.exp(-BEAM['FogDensity'] * BEAM['FogScale'] * dd) * cone
        k = lobe * along * fade * b['intensity']
        if b['mode'] < 0.5:
            col[m] += BEAM['Tint'] * k[:, None]
        else:
            col[m] *= (1 - np.clip(k, 0, 1))[:, None]
    if '--fse' in a:
        out_j = dict(cam=camname, t=t, w=w, h=h, fse={k: round(v, 3) for k, v in fse.items()},
                     fse_total=round(sum(fse.values()), 3), max_layers=int(layers.max()),
                     px_over_8=float((layers > 8).mean()))
        print(json.dumps(out_j))
    img = D.grade(col)
    if '--over' in a:
        # paste the Unity screenshot where it is NOT its own sky / flat fog (the arms, the tear): compare it with what
        # that background must be (the same band + moon air, graded) and keep the pixels that differ by > 10 codes
        from scipy.ndimage import binary_dilation, gaussian_filter, median_filter, binary_opening
        ov = np.asarray(Image.open(a[a.index('--over') + 1]).convert('RGB').resize((w, h), Image.LANCZOS)).astype(float)
        bg = D.grade(D.band(V, eye, tear) + D.moon_air(V))
        diff = np.abs(median_filter(ov @ [0.2126, 0.7152, 0.0722], 3) - bg @ [0.2126, 0.7152, 0.0722])
        mk = binary_opening(diff > 10, iterations=1)
        mk = binary_dilation(mk, iterations=1).astype(float)
        mk = gaussian_filter(mk, 0.8)[..., None]
        img = img * (1 - mk) + ov * mk
    out = a[a.index('--out') + 1] if '--out' in a else '/tmp/claude-0/gc/prev_%s.png' % camname
    Image.fromarray(np.clip(img, 0, 255).astype(np.uint8)).save(out)
    print('wrote', out)


if __name__ == '__main__':
    main()
