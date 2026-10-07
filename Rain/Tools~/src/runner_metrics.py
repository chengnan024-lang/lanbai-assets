"""Metrics of the runner model (runners_ref.py = LanbaiRunners v2): headless clear channels, one-frame pops, heads per
m^2 (after the verifier's phantom.py, round 2 M3), plus the kymograph Sheet_Glass shows (kymo_runners_stop.png).
usage: python3 runner_metrics.py [speed m/s = 0.03] [density = 0.05] [seconds = 120]"""
import numpy as np, sys, os
from PIL import Image
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import runners_ref as R
import rainpaths as RP
flow = np.array(Image.open(RP.find('GlassRunners_Flow_512x1024.png'))).astype(np.float32) / 255
H, W = flow.shape[:2]
mid = [28, 70, 100, 142, 193, 225, 274, 316, 356, 415, 446, 499]
cent = np.zeros((len(mid), H))
for li, c0 in enumerate(mid):
    c = c0
    for rr in list(range(512, H)) + list(range(511, -1, -1)):
        if rr == 511: c = c0
        win = np.arange(c - 6, c + 7) % W
        rv = flow[rr, win, 0]; av = flow[rr, win, 3]
        k = np.argmin(np.abs(rv - 0.5) + (av < 0.5) * 9)
        c = win[k]; cent[li, rr] = c
rows = np.arange(0, H, 5)
pts = []; ids = []
for tx in range(5):
    for ty in range(3):
        for li in range(len(mid)):
            u = (cent[li, rows] + 0.5) / W + tx
            v = (1 - (rows + 0.5) / H) + ty
            pts.append(np.stack([u * R.TU, v * R.TV], -1)); ids.append((tx, ty, li))
P = np.stack(pts).astype(np.float32)
speed = float(sys.argv[1]) if len(sys.argv) > 1 else 0.03
dens = float(sys.argv[2]) if len(sys.argv) > 2 else 0.05
TT = float(sys.argv[3]) if len(sys.argv) > 3 else 120
dt = 0.1; T = np.arange(0, TT, dt)
clearlen = np.zeros((len(T), P.shape[0])); head = np.zeros((len(T), P.shape[0])); hmov = np.zeros((len(T), P.shape[0]))
prevh = None
for i, t in enumerate(T):
    su, sv, h, clr = R.runners(flow, P, np.float32(t), np.float32(speed * t), speed, density=dens, size=0.003, trail_life=6.0)
    clearlen[i] = (clr > 0.5).sum(1) * 0.002
    head[i] = (h > 0.0003).sum(1)
    hp = np.argmax(h > 0.0003, 1)
    if prevh is not None:
        hmov[i] = (head[i] > 0) & (hp != prevh)
    prevh = hp
headless = (clearlen > 0.01) & (head == 0)
print('speed', speed, 'density', dens)
print('lane-tiles with any headless clear channel >1cm: %d of %d' % (headless.any(0).sum(), P.shape[0]))
print('mean simultaneous headless per m^2 (1 layer): %.2f' % (headless.sum(1).mean() / 1.2))
drops = -(np.diff(clearlen, axis=0))
pops = drops > 0.02
print('pops (>2 cm refilled in one 0.1 s step): %d -> %.2f per m^2 per minute; max drop %.1f cm' % (pops.sum(), pops.sum() / 1.2 / (TT / 60), drops.max() * 100))
hd = np.diff(head, axis=0)
print('head pixel-count jumps > 6 samples in one step: %d' % (np.abs(hd) > 6).sum())
print('heads present per m^2 (1 layer): %.2f ; moving heads per m^2 (1 layer): %.2f -> both layers ~ %.1f' % (
    (head > 0).sum(1).mean() / 1.2, hmov.sum(1).mean() / 1.2, hmov.sum(1).mean() / 1.2 * (1 + 1 / 0.83 ** 2)))
sel = np.argsort(-(head > 0).sum(0))[:5]
imgs = []
for j in sel:
    cols = []
    for i, t in enumerate(T[::2]):
        su, sv, h, clr = R.runners(flow, P[j:j + 1], np.float32(t), np.float32(speed * t), speed, density=dens, size=0.003, trail_life=6.0)
        col = np.stack([clr[0] * 200, clr[0] * 200, clr[0] * 200], -1)
        col[h[0] > 0.0003] = [255, 80, 40]
        cols.append(col)
    k = np.stack(cols, 1).astype(np.uint8)
    imgs.append(k); imgs.append(np.full((k.shape[0], 6, 3), 40, np.uint8))
im = np.concatenate(imgs, 1)
name = 'kymo_runners_stop.png' if (speed, dens) == (0.03, 0.05) else 'kymo_runners_%g_%g.png' % (speed, dens)
Image.fromarray(im).resize((im.shape[1] * 2, im.shape[0] * 2), Image.NEAREST).save(os.path.join(RP.out_dir(), name))
print('kymograph ->', os.path.join(RP.out_dir(), name))
