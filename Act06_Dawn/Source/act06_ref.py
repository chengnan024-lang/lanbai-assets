# -*- coding: utf-8 -*-
"""第 6 幕参考帧（numpy）：天空会话的 dawn 预设（CPU 版 Lanbai/Sky 渲成的等距柱状图）+ Lanbai/CloudPlain（plain_ref）+
云卡（Lanbai/CloudCard 的 numpy 移植 cardshade：公告板、雾、底部融化、软边）+ 海（ABOVE 的简化替身，见 README §6）+
车壳（渲染标准台 bible_v2 的角度窗；--door d12 = D-12 的真车门 +22…+37°）。按 PPv2 引擎模型 S6 调色（含 bloom）。
量：APL（Rec.709 luma 均值）、最亮 0.1 % 的位置、紫 / 薰衣草占比（第 6 幕：h 285–330 且 C* > 12，§1.3.4）。
用法：~/bpy/bin/python act06_ref.py --t 266.34 --cam hero [--w 960] [--door d12] [--out DIR]
"""
import os
import sys
import json
import math
import argparse
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'Clouds_v2', 'Source'))
import lb_common as C  # noqa: E402
import cardshade as CS  # noqa: E402
import act06_layout as AL  # noqa: E402
import plain_ref as PR  # noqa: E402

AL.solve_edges()
LAYOUT = json.load(open(os.path.join(KIT, 'Act06_Layout.json')))
CARDJ = json.load(open(os.path.join(REPO, 'Clouds_v2', 'Textures', 'cards_v2.json')))
COL = CARDJ['colours']['dawn']
HARNESS = os.path.join(REPO, 'Engineering', 'render_harness')
CAMS = json.load(open(os.path.join(HARNESS, 'cameras.json')))
CAMS = CAMS.get('cameras', CAMS)
CAMS['door_d12'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=30.0, pitch_deg=0.0, hfov_deg=90.0, res=[1920, 1080],
                        note='D-12: the real door +22..+37 deg, the sun framed in it')
CAMS['vr_door_d12'] = dict(eye=[0.55, 1.7, 2.05], yaw_deg=30.0, pitch_deg=0.0, hfov_deg=97.3, res=[1832, 1920],
                           note='D-09: VR single eye looking at the door (D-12)')
SHELL = json.load(open(os.path.join(HARNESS, 'bus_shell.json')))['presets']['bible_v2']
WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')
EYE = np.array([0.55, 1.70, 2.05])
FOG_D = LAYOUT['fog']['density']


def rays(cam, w):
    hf = math.radians(cam['hfov_deg'])
    rw, rh = cam['res']
    h = int(round(w * rh / rw))
    tx = math.tan(hf / 2)
    ty = tx * h / w
    xs = ((np.arange(w) + 0.5) / w * 2 - 1) * tx
    ys = (1 - (np.arange(h) + 0.5) / h * 2) * ty
    X, Y = np.meshgrid(xs, ys)
    d = np.stack([X, Y, np.ones_like(X)], -1)
    p, y = math.radians(cam['pitch_deg']), math.radians(cam['yaw_deg'])
    Rx = np.array([[1, 0, 0], [0, math.cos(p), math.sin(p)], [0, -math.sin(p), math.cos(p)]])
    Ry = np.array([[math.cos(y), 0, math.sin(y)], [0, 1, 0], [-math.sin(y), 0, math.cos(y)]])
    d = d @ Rx.T @ Ry.T
    d /= np.linalg.norm(d, axis=-1, keepdims=True)
    return d.reshape(-1, 3), h, 2 * tx / w


def window_mask(V, door='bible_v2'):
    az, el = C.azel_from_dir(V)
    m = np.zeros(len(V), bool)
    for wdw in SHELL['windows']:
        a0, a1 = wdw['az']
        if door == 'd12' and wdw['name'] == 'door_glass':
            a0, a1 = 22.0, 37.0
        azz = az if a1 <= 180 else np.where(az < 0, az + 360, az)
        m |= (azz >= a0) & (azz <= a1) & (el >= wdw['el'][0]) & (el <= wdw['el'][1])
    for mu in SHELL.get('mullions', []):
        m &= ~((np.abs(az - mu['az']) < mu['width_deg'] / 2) & (el >= mu['el'][0]) & (el <= mu['el'][1]))
    return m


_CARD = {}


def card_tex(name):
    if name not in _CARD:
        cj = CARDJ['cards'][name]
        k = np.asarray(Image.open(os.path.join(REPO, 'Clouds_v2', 'Textures', name + '_K.png')).convert('RGBA')).astype(np.float32) / 255
        s = np.asarray(Image.open(os.path.join(REPO, 'Clouds_v2', 'Textures', name + '_S.png')).convert('RGB')).astype(np.float32) / 255
        _CARD[name] = (C.srgb_dec(k[..., :3]) * cj['kscale'], C.srgb_dec(s[..., :2]) * cj['sscale'], k[..., 3], cj)
    return _CARD[name]


def fog_amount(dist):
    return 1 - np.exp(-FOG_D * dist)


def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def card_list(t, d):
    """every card (placed cards + the ring) with world pivot, width, gain, alpha at time t"""
    out = []
    B = LAYOUT['beats']
    for c in LAYOUT['cards']:
        if c['card'] not in CARDJ['cards']:
            continue
        g = c['gain']
        for ta in B['tower_answer']:
            if ta['id'] == c['id']:
                x = smooth01((t - ta['t0']) / ta['dur'])
                g *= 2 ** (ta['dev'] * x)     # the crown answers (+0.7 EV; the whole card here: an upper bound)
        p = np.array(c['position_local'], float) + np.array([0, d, 0])
        out.append(dict(c, pivot=p, gain_t=g, alpha_t=c['alpha']))
    ro = B['ring_off']
    a_ring = 1 - smooth01((t - ro['t0']) / (ro['t1'] - ro['t0']))
    for c in LAYOUT['ring']:
        name = c['card'] if c['card'] in CARDJ['cards'] else LAYOUT['ring'][0]['card']
        if name not in CARDJ['cards'] or a_ring <= 0:
            continue
        cj = CARDJ['cards'][name]
        aspect = cj['size'][1] / cj['size'][0]
        R = math.hypot(c['position_local'][0], c['position_local'][2])
        top_y = EYE[1] + R * math.tan(math.radians(c['top_el_deg']))
        v_top = cj['opaque_bbox_uv'][3]
        piv_y = top_y - (v_top - cj['cloud_base_v']) * aspect * c['width_m']
        p = np.array([c['position_local'][0], piv_y, c['position_local'][2]])   # world: the ring stays at the horizon
        out.append(dict(c, card=name, pivot=p, gain_t=c['gain'], alpha_t=c['alpha'] * a_ring))
    return out


def draw_cards(V, img, depth, t, d, pix):
    sun = np.array(LAYOUT['sun']['dir'])
    cards = card_list(t, d)
    cards.sort(key=lambda c: -np.linalg.norm(c['pivot'] - EYE))
    for c in cards:
        K, S, A, cj = card_tex(c['card'])
        hgt, wid = A.shape
        aspect = hgt / wid
        W = c['width_m']
        piv = c['pivot']
        f = EYE - piv
        fxz = f[[0, 2]] / max(np.linalg.norm(f[[0, 2]]), 1e-6)
        right = np.array([-fxz[1], 0.0, fxz[0]])
        nrm = np.array([fxz[0], 0.0, fxz[1]])
        denom = V @ nrm
        with np.errstate(divide='ignore', invalid='ignore'):
            tt = ((piv - EYE) @ nrm) / denom
        ok = (tt > 0) & np.isfinite(tt)
        P = EYE + V * np.where(ok, tt, 0)[:, None]
        u = ((P - piv) @ right) / W + 0.5
        v = (P[:, 1] - piv[1]) / (W * aspect) + cj['cloud_base_v']
        bb = cj.get('bbox_uv', [0, 0, 1, 1])
        ok &= (u >= bb[0]) & (u <= bb[2]) & (v >= bb[1]) & (v <= bb[3]) & (tt < depth + 40.0)
        if not ok.any():
            continue
        rel, left = CS.rel_angle(-f[[0, 2]], sun[[0, 2]])
        mir = c.get('mirror', 2)
        mirror = left if mir == 2 else bool(mir)
        uu = np.where(mirror, 1 - u[ok], u[ok])
        xi = np.clip((uu * wid).astype(int), 0, wid - 1)
        yi = np.clip(((1 - v[ok]) * hgt).astype(int), 0, hgt - 1)
        w0, w1, w2 = CS.key_weights(rel)
        k = K[yi, xi, 0] * w0 + K[yi, xi, 1] * w1 + K[yi, xi, 2] * w2
        a = A[yi, xi]
        col = k[:, None] * np.array(COL['SunColor']) + S[yi, xi, 0:1] * np.array(COL['SkyUpColor']) + S[yi, xi, 1:2] * np.array(COL['GroundColor'])
        col *= c['gain_t']
        a = a * c['alpha_t'] * CS.melt(np.ones_like(a), v[ok], cj['cloud_base_v'])
        # soft depth fade against the plain / sea (SOFTPARTICLES_ON, 40 m)
        a = a * np.clip((depth[ok] - tt[ok]) / 40.0, 0, 1)
        fa = fog_amount(tt[ok])
        fc = PR.fog_colour(SKY, V[ok])
        col = col * (1 - fa)[:, None] + fc * fa[:, None]
        idx = np.nonzero(ok)[0]
        img[idx] = img[idx] * (1 - a)[:, None] + col * a[:, None]


def sea(V, t, d):
    """ABOVE stand-in: water + Fresnel x the sky reflected (the calm sea is a mirror from 337.0), fog."""
    level = LAYOUT['sea']['level_local'] + d
    with np.errstate(divide='ignore', invalid='ignore'):
        ts = (level - EYE[1]) / V[:, 1]
    hit = (V[:, 1] < -1e-4) & (ts > 0)
    col = np.zeros((len(V), 3))
    if hit.any():
        Vh = V[hit]
        R = Vh * np.array([1, -1, 1])
        cosi = np.clip(-Vh[:, 1], 0, 1)
        F = 0.02 + 0.98 * (1 - cosi) ** 5
        calm = smooth01((t - LAYOUT['beats']['sea_calm_all']['t0']) / LAYOUT['beats']['sea_calm_all']['dur'])
        refl = C.sample_equirect(SKY, R, 0.0)
        refl = np.minimum(refl, 8.0)
        water = np.array([0.0156, 0.0484, 0.0954])
        c = water[None, :] * (1 - F)[:, None] + refl * F[:, None] * (0.6 + 0.4 * calm)
        fa = fog_amount(ts[hit])
        c = c * (1 - fa)[:, None] + PR.fog_colour(SKY, Vh) * fa[:, None]
        col[hit] = c
    return col, np.where(hit, ts, np.inf)


SKY = None


def render(t, cam_name, w=960, door='bible_v2', out_dir=None, tag=''):
    global SKY
    if SKY is None:
        SKY = C.read_hdr(os.path.join(WORK, 'sky_dawn_1024.hdr')).astype(np.float64)
    cam = dict(CAMS[cam_name])
    V, h, pix = rays(cam, w)
    d, vdown = AL.descent(t)
    img = C.sample_equirect(SKY, V, 0.0)
    depth = np.full(len(V), np.inf)
    sc, sd = sea(V, t, d)
    if t < LAYOUT['beats']['sea_on']:
        sd = np.full(len(V), np.inf)
    hs = np.isfinite(sd)
    img[hs] = sc[hs]
    depth = np.minimum(depth, sd)
    so = float(smooth01((t - LAYOUT['beats']['slot_open'][0]) / (LAYOUT['beats']['slot_open'][1] - LAYOUT['beats']['slot_open'][0])))
    pc, ph, pd = PR.Plain().render(EYE, V, pix, d, SKY, slot_open=so)
    front = ph & (pd < depth)
    img[front] = pc[front]
    depth = np.where(front, pd, depth)
    draw_cards(V, img, depth, t, d, pix)
    # the cabin (bible_v2 angular shell): the interior is dark, lit by the cabin ambient (#98A4B8 x 0.5) and the sky
    win = window_mask(V, door)
    interior = C.hex_lin('#2A2C30') * (C.hex_lin('#98A4B8') * 0.5 + 0.6)
    img[~win] = interior
    lin = img.reshape(h, w, 3)
    codes = C.grade(lin, 'S6', bloom=True)
    luma = codes @ C.LUMA
    L, hh, cc = C.hue_chroma(codes.reshape(-1, 3))
    lav = float(((hh >= 285) & (hh <= 330) & (cc > 12)).mean())
    thr = np.percentile(luma, 99.9)
    ys, xs = np.nonzero(luma >= thr)
    m = dict(t=t, cam=cam_name, door=door, d=round(d, 1), APL=round(float(luma.mean()), 1), lavender=round(lav, 4),
             brightest_px=[round(float(xs.mean() / w), 3), round(float(ys.mean() / h), 3)], width=w)
    if out_dir:
        os.makedirs(out_dir, exist_ok=True)
        base = os.path.join(out_dir, f'{tag}{cam_name}_t{t:.2f}')
        Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(base + '.png')
        json.dump(m, open(base + '.json', 'w'), indent=1)
    return codes, m, lin


if __name__ == '__main__':
    ap = argparse.ArgumentParser()
    ap.add_argument('--t', type=float, nargs='+', default=[266.34])
    ap.add_argument('--cam', nargs='+', default=['hero'])
    ap.add_argument('--w', type=int, default=960)
    ap.add_argument('--door', default='bible_v2')
    ap.add_argument('--out', default='/tmp/lb/act06')
    ap.add_argument('--tag', default='')
    a = ap.parse_args()
    for t in a.t:
        for c in a.cam:
            _, m, _ = render(t, c, a.w, a.door, a.out, a.tag)
            print(json.dumps(m))
