"""蓝白 / Lanbai · TentacleTide atlas v3 (gate round 3, run 6).

Why: the v2 atlas cells were thin, beaded, kinked blades (leaf / grass silhouettes). Seen 5-12 km away in a row along
the horizon they read as GRASS - the v1 'sprouts' failure again. v3 cells are drawn from the gate's v4 arm form
(arms4.RAD4: a muscular root, a swan-neck taper from t 0.45 into a thread) with the v4 gestures (lean 20-45 deg toward
the wound, crest at 55-70 % of the length, the top third curling over and DOWN, one soft hook / half curl / straight
whip), and half the cells are CLUSTERS (2-4 arms from one root area, different heights, overlapping) so the far tide
reads as massed waves of arms, not single stalks with sky between them.

Same contract as v2 (README_Tentacles / Lanbai_TentacleTide_v2.shader): 2 atlases x 8 cells (2 columns x 4 rows,
index = row * 2 + col, row 0 at the top), 256 x 512 px cells, every silhouette leans RIGHT, the root sits at
(root_u, 0) of its cell, a quad of height cell_height_in_lengths x size shows the (largest) arm at its true length.
RGB = body colour (sRGB 14-18, blue-black) with a faint moon edge on the upper-left (the shader scales it by the
far-rim falloff); alpha = coverage, feathered over the bottom 7 % (the base dissolves; no straight cut).

    python3 tide_atlas_v3.py      -> gate/Textures/TentacleTide_v3_Atlas_A.png, _B.png, TentacleTide_v3_Atlas.json
"""
import json
import math
import os

import numpy as np
from PIL import Image, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
OUTD = os.path.join(HERE, 'Textures')
CW, CH = 256, 512
SS = 4                       # supersampling
RAD4 = [(0.00, 1.00), (0.05, 1.05), (0.15, 1.03), (0.30, 0.95), (0.45, 0.83), (0.55, 0.69), (0.65, 0.53),
        (0.75, 0.37), (0.84, 0.235), (0.91, 0.135), (0.955, 0.075), (0.985, 0.040), (1.00, 0.022)]


def rad(u):
    a = np.array(RAD4)
    return np.interp(u, a[:, 0], a[:, 1])


def arm_path(rng, lean, crest, droop, hook, wiggle, n=700):
    """2D centreline (x right, y up, length 1): a long neck rising `lean` deg right of vertical with a gentle S
    (`wiggle`), then the top third curls over toward the wound: the tangent turns ~horizontal at `crest` (0.72-0.86 of
    the length) and points down by `droop` after it; the last ~6 % hooks by `hook` deg. Integrated from a curvature
    profile -> always smooth, never kinked."""
    s = np.linspace(0, 1, n)
    ds = 1.0 / (n - 1)
    th0 = math.radians(lean)                     # angle from vertical, + = right
    turn_crest = math.pi / 2 - th0
    turn_end = turn_crest + math.atan(droop * 4.0)
    k = np.zeros(n)
    g1 = np.exp(-((s - (crest - 0.14)) / 0.17) ** 2)
    g2 = np.exp(-((s - min(0.95, crest + 0.06)) / 0.09) ** 2)
    k += g1 / (g1.sum() * ds) * turn_crest
    k += g2 / (g2.sum() * ds) * (turn_end - turn_crest)
    k += wiggle * np.sin(2 * math.pi * (s * 1.1) + rng.uniform(0, 6)) * np.clip(1.2 - s / crest, 0, 1) * 2.4
    gh = np.exp(-((s - 0.97) / 0.025) ** 2)
    k += gh / (gh.sum() * ds) * math.radians(hook)
    th = th0 + np.cumsum(k) * ds
    x = np.cumsum(np.sin(th)) * ds
    y = np.cumsum(np.cos(th)) * ds
    return np.stack([x - x[0], y - y[0]], -1), s


def draw_cell(arms, seed):
    """arms: list of dict(path (n,2) in arm-length units, s, r0, ox, scale). Returns (rgba uint8, root_u, h_in_L)."""
    # fit: the bbox of all arms in units of the largest arm length
    pts = np.concatenate([a['path'] * a['scale'] + np.array([a['ox'], 0.0]) for a in arms])
    rmax = max(a['r0'] * a['scale'] for a in arms)
    x0, x1 = pts[:, 0].min() - rmax * 1.2, pts[:, 0].max() + rmax * 1.2
    y1 = pts[:, 1].max() + rmax * 1.2
    # cell aspect 0.5: height in L
    h = max(y1, (x1 - x0) * 2.0) * 1.04
    w = h * 0.5
    xc = (x0 + x1) / 2
    left = xc - w / 2
    root_u = (0.0 - left) / w
    W, H = CW * SS, CH * SS
    px = lambda p: ((p[..., 0] - left) / w * W, H - p[..., 1] / h * H)
    covs = []
    rim = Image.new('L', (W, H), 0)
    dr = ImageDraw.Draw(rim)
    for a in arms:
        cov_a = Image.new('L', (W, H), 0)
        dc = ImageDraw.Draw(cov_a)
        covs.append((cov_a, a.get('alpha', 1.0)))
        P = a['path'] * a['scale'] + np.array([a['ox'], 0.0])
        R = rad(a['s']) * a['r0'] * a['scale'] / h * H
        X, Y = px(P)
        # the moon is front-left and low: a faint edge on the upper-left of the body
        nrm = np.gradient(P, axis=0)
        nrm = np.stack([-nrm[:, 1], nrm[:, 0]], -1)
        nrm /= np.linalg.norm(nrm, axis=1, keepdims=True) + 1e-9
        for i in range(0, len(P)):
            r = max(R[i], 0.9)
            dc.ellipse([X[i] - r, Y[i] - r, X[i] + r, Y[i] + r], fill=255)
            side = nrm[i] if (nrm[i, 1] > 0 or nrm[i, 0] < 0) else -nrm[i]
            if side[1] * 0.7 - side[0] * 0.7 > 0.2 and a['s'][i] > 0.15:
                cx, cy = X[i] + side[0] * r * 0.55, Y[i] - side[1] * r * 0.55
                rr = r * 0.55
                dr.ellipse([cx - rr, cy - rr, cx + rr, cy + rr], fill=255)
    # composite back-to-front: the first arm is the front one (alpha 1); the others are behind it, partly in the air
    cov = np.zeros((CH, CW), np.float32)
    for cov_a, al in covs[::-1]:
        ca = np.array(cov_a.resize((CW, CH), Image.LANCZOS), np.float32) / 255.0 * al
        cov = ca + cov * (1 - ca)
    rimA = np.array(rim.resize((CW, CH), Image.LANCZOS), np.float32) / 255.0
    rimA = np.clip(rimA - np.array(Image.fromarray((cov * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(3)),
                                   np.float32) / 255.0 * 0.0, 0, 1)
    # rim only at the very edge: coverage between 0.15 and 0.85 of the eroded mask
    er = np.array(Image.fromarray((cov * 255).astype(np.uint8)).filter(ImageFilter.MinFilter(5)), np.float32) / 255.0
    edge = np.clip(cov - er, 0, 1) * rimA
    rng = np.random.default_rng(seed)
    body = np.array([15.0, 16.0, 21.0]) + rng.uniform(-1, 1)
    rimc = np.array([70.0, 80.0, 104.0])
    rgb = body[None, None, :] * (1 - edge[..., None]) + rimc[None, None, :] * edge[..., None]
    # base feather: bottom 7 % of the cell (in v: the cloud swallows the root)
    v = np.linspace(1, 0, CH)[:, None]
    cov = cov * np.clip(v / 0.07, 0, 1) ** 1.5
    out = np.dstack([rgb, cov * 255.0]).clip(0, 255).astype(np.uint8)
    return out, float(root_u), float(h)


def gestures():
    """16 cells: 8 single arms with different gestures, 8 clusters."""
    rng = np.random.default_rng(1307)
    singles = [
        dict(name='bow', lean=22, crest=0.80, droop=0.20, hook=40, wiggle=0.25, r0=0.065),
        dict(name='reach', lean=34, crest=0.90, droop=0.06, hook=12, wiggle=0.35, r0=0.060),
        dict(name='rear', lean=14, crest=0.76, droop=0.30, hook=70, wiggle=0.15, r0=0.070),
        dict(name='lash', lean=28, crest=0.84, droop=0.12, hook=-35, wiggle=0.55, r0=0.057),
        dict(name='hump', lean=38, crest=0.74, droop=0.24, hook=25, wiggle=0.3, r0=0.075),
        dict(name='whip', lean=24, crest=0.92, droop=0.04, hook=-10, wiggle=0.45, r0=0.052),
        dict(name='curl', lean=16, crest=0.78, droop=0.34, hook=110, wiggle=0.2, r0=0.065),
        dict(name='swan', lean=26, crest=0.82, droop=0.20, hook=20, wiggle=0.4, r0=0.062),
    ]
    cells = []
    for g in singles:
        P, s = arm_path(rng, g['lean'], g['crest'], g['droop'], g['hook'], g['wiggle'])
        cells.append(dict(kind='single', gesture=g['name'], arms=[dict(path=P, s=s, r0=g['r0'], ox=0.0, scale=1.0)]))
    for ci in range(8):
        n = [3, 4, 3, 5, 4, 3, 5, 4][ci]
        arms = []
        for j in range(n):
            g = singles[int(rng.integers(len(singles)))]
            # not a tuft: arms of similar size, spread along the row, some crossing / curling back
            lean = g['lean'] + rng.uniform(-14, 8) - (22 if (j % 3 == 2) else 0)
            P, s = arm_path(rng, lean, g['crest'] + rng.uniform(-0.06, 0.04), g['droop'] * rng.uniform(0.7, 1.4),
                            g['hook'] * rng.uniform(0.5, 1.3), g['wiggle'] * rng.uniform(0.8, 1.6), n=600)
            sc = 1.0 if j == 0 else rng.uniform(0.62, 0.95)
            ox = 0.0 if j == 0 else rng.uniform(0.10, 0.42) * (1 if j % 2 else -0.6)
            arms.append(dict(path=P, s=s, r0=g['r0'] * rng.uniform(1.0, 1.3), ox=ox, scale=sc,
                             alpha=1.0 if j == 0 else float(rng.uniform(0.70, 0.92))))
        cells.append(dict(kind='cluster%d' % n, gesture='cluster', arms=arms))
    return cells


def main():
    os.makedirs(OUTD, exist_ok=True)
    cells = gestures()
    meta = []
    for ai, an in enumerate('AB'):
        atl = np.zeros((CH * 4, CW * 2, 4), np.uint8)
        for idx in range(8):
            c = cells[ai * 8 + idx]
            img, ru, h = draw_cell(c['arms'], 31 * ai + idx)
            row, col = idx // 2, idx % 2
            atl[row * CH:(row + 1) * CH, col * CW:(col + 1) * CW] = img
            meta.append(dict(variant='v3_' + c['gesture'], kind=c['kind'], lean_deg=0, root_u=round(ru, 4),
                             cell_height_in_lengths=round(h, 4), atlas='TentacleTide_v3_Atlas_' + an, index=idx,
                             uv_rect=[col * 0.5, 1.0 - (row + 1) * 0.25, (col + 1) * 0.5, 1.0 - row * 0.25]))
        Image.fromarray(atl, 'RGBA').save(os.path.join(OUTD, 'TentacleTide_v3_Atlas_%s.png' % an))
    json.dump(dict(cell_px=[CW, CH], layout='2 columns x 4 rows per atlas, index = row * 2 + col, row 0 at the top',
                   note='v3 (gate run 6): v4 arm form (swan neck, crest 55-70 %, top third curls over and down), '
                        'half the cells are clusters of 2-4 arms; every silhouette leans RIGHT; root at (root_u, 0); '
                        'quad height = cell_height_in_lengths x size (size = the largest arm of the cell); alpha '
                        'feathered over the bottom 7 %; faint moon edge upper-left',
                   cells=meta), open(os.path.join(OUTD, 'TentacleTide_v3_Atlas.json'), 'w'), indent=1)
    # preview on band grey
    prev = []
    for an in 'AB':
        a = np.array(Image.open(os.path.join(OUTD, 'TentacleTide_v3_Atlas_%s.png' % an)), np.float32)
        al = a[..., 3:] / 255.0
        prev.append((a[..., :3] * al + 88 * (1 - al)).astype(np.uint8))
    Image.fromarray(np.concatenate(prev, 1)).resize((512, 1024)).save(os.path.join(HERE, 'wip', 'r4', 'atlas_v3.png'))
    print('ok', len(meta))


if __name__ == '__main__':
    main()
