"""蓝白 / Lanbai · gate clouds kit · round 10 on the VOLUME deck (总导演 10-26: the gate's cloud is Lanbai/GateVolumeDeck).

The gate's cameras (GateLayout_v2.json: key, U7, U8fwd, U8side, ...) rendered like seam_ref.py: arms from Cycles (posed by
the driver's maths, TentacleSway v2.8 stand-in shading), the volume deck as a numpy port, and the TEAR pasted from the
pixel-aligned Unity screenshot (FromLocal/gate_clouds_test/20261025-0009/shots: same camera, same t; the lens and its lips
where they are brighter than the scene, above the foot). No cloud cards, no bus. Prints the APL (display codes, whole
frame, as metrics_unity_vs_render.json) and region percentiles.

  python3 vol_ref.py <view> [--w 960] [--set k=v,...] [--out dir]     view = U8fwd | key | U7 | U8side
  --set: TEARL keys (E, R0, G, Tap, Pool) for the AFTER column
"""
import json
import os
import sys

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deck_ref as D  # noqa: E402
import seam_ref as S  # noqa: E402

SHOTS = os.path.join(D.REPO, 'FromLocal', 'gate_clouds_test', '20261025-0009', 'shots')
CAMS = S.json.load(open(os.path.join(D.REPO, 'Gate', 'GateLayout_v2.json')))['cameras']
# the tear in each screenshot: columns, the row under which it is the deck (the lit foot), the lens threshold
TEARCUT = {'U8fwd': ('U8fwd_unity_t169.65.png', (560, 1360), 640),
           'key': ('key_unity_t154.50.png', (980, 1380), 760),
           'U7': ('U7_unity_t155.10.png', (840, 1120), 560),
           'U8side': ('U8side_unity_t166.45.png', (0, 0), 0)}
# the after column's tear light (Lanbai/GateVolumeDeck defaults; keep in sync)
AFTER = dict(on=True, E=0.5, R0=120.0, G=0.6, Tap=30.0, Pool=0.0, Lift=60.0, HashJitter=1.0)


def cam_of(view):
    c = CAMS[view]
    return dict(t=c['t'], pos=c['eye_bus_relative'], look_yaw_deg=c['look_yaw_deg'], look_pitch_deg=c['look_pitch_deg'],
                hfov_deg=c['hfov_deg'])


def project(cam, w, h, P):
    """world point -> pixel (x, y) for deck_ref.camera_rays' camera"""
    import math
    yaw, pitch = math.radians(cam['look_yaw_deg']), math.radians(cam['look_pitch_deg'])
    cp, sp, cy, sy = math.cos(pitch), math.sin(pitch), math.cos(yaw), math.sin(yaw)
    Rx = np.array([[1, 0, 0], [0, cp, sp], [0, -sp, cp]])
    Ry = np.array([[cy, 0, sy], [0, 1, 0], [-sy, 0, cy]])
    d = (np.asarray(P, float) - np.asarray(cam['pos'], float)) @ Ry @ Rx       # inverse of d @ Rx.T @ Ry.T
    tx = math.tan(math.radians(cam['hfov_deg']) / 2)
    ty = tx * h / w
    return (d[0] / d[2] / tx + 1) / 2 * w, (1 - d[1] / d[2] / ty) / 2 * h


def tear_layer(view, w, h):
    """(rgb linear, alpha) of the tear from the screenshot, resized to w x h"""
    fn, (x0, x1), cut = TEARCUT[view]
    if cut <= 0:
        return None, None
    A = Image.open(os.path.join(SHOTS, fn)).convert('RGB')
    W0, H0 = A.size
    a = np.asarray(A).astype(np.float32) / 255.0
    L = a @ np.array([0.2126, 0.7152, 0.0722])
    alpha = D.ss(0.42, 0.84, L)
    m = np.zeros_like(L)
    m[:cut, x0:x1] = 1.0
    # only what belongs to the lens: the core (L > 0.84) grown by ~2 % of the width (its lips and glow), not the lit
    # cloud bits and arm highlights elsewhere in the box
    core = (L > 0.84) & (m > 0)
    from scipy import ndimage
    lab, n = ndimage.label(core)
    if n:
        sizes = np.asarray(ndimage.sum(core, lab, range(1, n + 1)))
        keep = 1 + np.nonzero(sizes >= 0.02 * sizes.max())[0]          # the lens, cut into pieces by the arms in front
        core = np.isin(lab, keep)
    grown = ndimage.binary_dilation(core, iterations=max(4, W0 // 50))
    alpha = alpha * m * grown
    # display -> linear through the inverse of the grade is not available: paste in display space after grading
    rgb = Image.fromarray((a * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
    al = Image.fromarray((alpha * 255).astype(np.uint8)).resize((w, h), Image.LANCZOS)
    return np.asarray(rgb).astype(np.float32), np.asarray(al).astype(np.float32)[..., None] / 255.0


def render(view, w, outdir, after):
    S.TEX = S.density_tex() if S.TEX is None else S.TEX
    cam = cam_of(view)
    t = cam['t']
    h = int(round(w * (1072 / 2560 if view == 'key' else 9 / 16)))
    eye = np.array(cam['pos'], float)
    tear = D.gate_origin(t) + np.array([0.0, -150.0 + 0.4 * 640.0, 19.0])
    V, PIX = D.camera_rays(cam, w, h)
    Vf = V.reshape(-1, 3)
    arms = S.arm_meshes(t, True)
    P, N, hit = S.render_arm_passes(arms, cam, w, h)
    trgb, ta = tear_layer(view, w, h)
    out = {}
    for name, tl in (('before', dict(on=False, E=0.0)), ('after', after)):
        S.TEARL.update(dict(on=False, E=0.0, R0=250.0, G=0.6, Tap=30.0, Pool=1.0))
        S.TEARL.update({k: v for k, v in tl.items() if k not in ('Lift', 'HashJitter')})
        S.VOL['Lift'] = float(tl.get('Lift', 0.0))
        S.VOL['HashJitter'] = float(tl.get('HashJitter', 0.0))
        c = S.Ctx(t, eye)
        c.pix = PIX
        c.skirts = S.skirts_runtime(t, arms, eye)
        col = D.band(Vf, eye, tear) + D.moon_air(Vf)
        scene_d = np.full(Vf.shape[0], np.inf)
        ia = np.nonzero(hit.reshape(-1))[0]
        acol, keep, dist = S.shade_arm(P.reshape(-1, 3)[ia], N.reshape(-1, 3)[ia], c, tear, True)
        col[ia[keep]] = acol[keep]
        scene_d[ia[keep]] = dist[keep]
        s, tr = S.march(Vf, c, scene_d, True, tear)
        img = D.grade((col * tr[:, None] + s).reshape(h, w, 3)).astype(np.float32)
        L0 = img @ np.array([0.2126, 0.7152, 0.0722])          # the cloud without the pasted tear (for the foot metric)
        if trgb is not None:
            img = img * (1 - ta) + trgb * ta
        img = np.clip(img, 0, 255).astype(np.uint8)
        out[name] = img
        os.makedirs(outdir, exist_ok=True)
        Image.fromarray(img).save(os.path.join(outdir, 'vol_%s_%s.png' % (view, name)))
        L = img.astype(np.float32) @ np.array([0.2126, 0.7152, 0.0722])
        low = L[int(0.6 * h):]
        print('%s %s: APL %.1f | lower 40%%: p5 %.0f p50 %.0f p95 %.0f' % (view, name, L.mean(), *np.percentile(low, [5, 50, 95])),
              flush=True)
        if view == 'key':
            # 'foot centre / moon path' (README §3.1: p95 in the band y 740-800 of the 2560 x 1072 keyart): boxes +-80 px
            # (2560 scale) at the projected tear foot's column and at the moon's column
            fx, fy = project(cam, w, h, S.tear_segment(t)[0])
            mx, _ = project(cam, w, h, eye + S.MOON * 1e5)
            k = w / 2560.0
            r0, r1 = int(740 * k), int(800 * k)
            fb = L0[r0:r1, max(int(fx - 80 * k), 0):int(fx + 80 * k)]
            mb = L0[r0:r1, max(int(mx - 80 * k), 0):int(mx + 80 * k)]
            print('   key foot / moon path p95: %.0f / %.0f = %.2f  (foot x %.0f y %.0f, moon x %.0f at w %d)'
                  % (np.percentile(fb, 95), np.percentile(mb, 95), np.percentile(fb, 95) / max(np.percentile(mb, 95), 1),
                     fx, fy, mx, w), flush=True)
    return out


def seq(view, n, w, outdir, after, fps=60.0):
    """n frames at fps from the view's t: before / after into outdir/before, outdir/after (f%03d.png, for measure_crawl)"""
    t0 = CAMS[view]['t']
    for f in range(n):
        CAMS[view] = dict(CAMS[view], t=t0 + f / fps)
        out = render(view, w, os.path.join(outdir, '_tmp'), after)
        for k in ('before', 'after'):
            os.makedirs(os.path.join(outdir, k), exist_ok=True)
            Image.fromarray(out[k]).save(os.path.join(outdir, k, 'f%03d.png' % f))
    CAMS[view] = dict(CAMS[view], t=t0)


if __name__ == '__main__':
    a = sys.argv[1:]
    w = int(a[a.index('--w') + 1]) if '--w' in a else 960
    outdir = a[a.index('--out') + 1] if '--out' in a else '/tmp/claude-0/vol'
    after = dict(AFTER)
    if '--set' in a:
        for k, v in (x.split('=') for x in a[a.index('--set') + 1].split(',')):
            after[k] = float(v)
    if '--seq' in a:
        seq(a[0], int(a[a.index('--seq') + 1]), w, outdir, after)
    else:
        render(a[0], w, outdir, after)
