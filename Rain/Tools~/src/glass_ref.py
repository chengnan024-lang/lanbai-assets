"""numpy reference of LanbaiGlassRain() + LanbaiDropExit(): static beads + 2 runner layers (+ the wiper refill) ->
tangent-space slope field of the pane, and the two-interface refraction of a drop. Mirrors Shaders/LanbaiRain.cginc.
Pane coordinates in metres (x right, y up)."""
import os
import numpy as np
from PIL import Image
from runners_ref import runners, sample_bilinear
import rainpaths as RP

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.environ.get('RAIN_OUT', os.path.join(HERE, '..', 'out'))


def load(name):
    return np.asarray(Image.open(RP.find(name)), np.float32) / 255.0


def refract(I, N, eta):
    """HLSL refract(): I incident (unit), N facing against I (unit), eta = n1/n2. Zero vector on TIR."""
    c = -(I * N).sum(-1, keepdims=True)
    k = 1 - eta * eta * (1 - c * c)
    t = eta * I + (eta * c - np.sqrt(np.maximum(k, 0))) * N
    return np.where(k < 0, 0.0, t)


def drop_exit(I, Np, Nd):
    """LanbaiDropExit: cabin air -> water across the flat pane, then water -> air through the drop surface"""
    Iw = refract(I, -Np, 1.0 / 1.333)
    return refract(Iw, -Nd, 1.333)


class Glass:
    def __init__(self, variant='Vertical'):
        self.bn = load('RainBeads_%s_Normal_1024.png' % variant)
        self.bd = load('RainBeads_%s_Data_1024.png' % variant)
        self.flow = load('GlassRunners_Flow_512x1024.png')
        self.bead_tile = 0.20

    def slopes(self, P, t, amount=1.0, flow_dir=(0.0, -1.0), speed=0.03, density=0.05, size=0.0030, stretch=0.0,
               stickslip=1.0, trail_life=6.0, extra_clear=None, dist=None, v_avg=None, wipe_since=None, wipe_refill=3.0):
        """P: (...,2) pane metres. dist: distance clock (default speed * t), v_avg (default speed).
        extra_clear: an array (per pixel) or a callable f(P) -> 0..1, evaluated at each bead's CENTRE (whole beads go).
        returns su, sv (dh/dx, dh/dy), bead_thick_m, runner_h_m"""
        dist = speed * t if dist is None else dist
        v_avg = speed if v_avg is None else v_avg
        u = P[..., 0] / self.bead_tile; v = P[..., 1] / self.bead_tile
        n = sample_bilinear(self.bn, u, v) * 2 - 1
        d = sample_bilinear(self.bd, u, v)
        bsx = -n[..., 0] / np.maximum(n[..., 2], 0.2); bsy = -n[..., 1] / np.maximum(n[..., 2], 0.2)
        boff = bead_centre(bsx, bsy, d)                                # pane metres to the bead's centre
        ws = np.full(P.shape[:-1], 1e4, np.float32) if wipe_since is None else wipe_since
        refill = np.clip(ws / max(wipe_refill, 0.1), 0, 1)
        vis = np.clip((amount * refill - d[..., 1]) * 12.0, 0, 1)
        run_keep = np.clip((ws - 0.4) / 1.6, 0, 1)
        fd = np.asarray(flow_dir, np.float32); fd = fd / np.linalg.norm(fd)
        ax_v = -fd; ax_u = np.array([ax_v[1], -ax_v[0]], np.float32)
        Pr = np.stack([(P * ax_u).sum(-1), (P * ax_v).sum(-1)], -1)
        su_r = np.zeros(P.shape[:-1], np.float32); sv_r = np.zeros_like(su_r); hh = np.zeros_like(su_r); clr = np.zeros_like(su_r)
        for (sc, off, doff, seed) in [(1.0, (0.0, 0.0), 0.0, 0.0), (0.83, (0.071, 0.137), 7.3, 0.5)]:
            Q = (Pr / sc + np.array(off, np.float32)).astype(np.float32)
            bo_r = np.stack([(boff * ax_u).sum(-1), (boff * ax_v).sum(-1)], -1).astype(np.float32) / sc
            a, b, h, c = runners(self.flow, Q, t, dist / sc + doff, v_avg / sc, density=density, size=size / sc,
                                 stretch=stretch, stickslip=stickslip, trail_life=trail_life, seed_off=seed, bead_off=bo_r)
            su_r += a; sv_r += b; hh = np.maximum(hh, h * sc); clr = np.maximum(clr, c)
        rsx = su_r * ax_u[0] + sv_r * ax_v[0]
        rsy = su_r * ax_u[1] + sv_r * ax_v[1]
        big = np.clip((d[..., 3] - 0.10) / 0.05, 0, 1)
        ec = 0.0 if extra_clear is None else (extra_clear(P + boff) if callable(extra_clear) else extra_clear)
        keep = vis * (1 - np.maximum(clr * run_keep, ec) * big)
        ramt = amount * run_keep
        su = bsx * keep + rsx * ramt
        sv = bsy * keep + rsy * ramt
        return su, sv, d[..., 0] * 2.5e-3 * keep, hh * ramt


def bead_centre(bsx, bsy, d, sin_th=0.707):
    """LanbaiBeadCentre: from a static bead's slope and contact radius, the offset (pane metres) from this pixel to the
    bead's centre. For a spherical cap of contact radius a and contact angle th (sphere radius R = a / sin th):
    c - P = grad h * R / sqrt(1 + |grad h|^2). Zero off the beads; never further than a."""
    a = d[..., 3] * 0.003
    R = a / sin_th
    s2 = bsx * bsx + bsy * bsy
    k = R / np.sqrt(1 + s2)
    off = np.stack([bsx * k, bsy * k], -1)
    ln = np.linalg.norm(off, axis=-1, keepdims=True)
    off = off * np.minimum(1.0, a[..., None] / np.maximum(ln, 1e-9))
    return np.where((d[..., 2] > 0.5)[..., None], off, 0.0).astype(np.float32)


def wiper_since(P, pivot, rest_dir, sweep, r_min, r_max, t, t0, stroke=0.65, period=5.0, prev=True):
    """LanbaiWiperOne().since for a pane in its own 2D frame (P, pivot in metres, rest_dir unit 2D, sweep rad)."""
    v = P - np.asarray(pivot, np.float32)
    e1 = np.asarray(rest_dir, np.float32); e2 = np.array([-e1[1], e1[0]], np.float32)
    x = (v * e1).sum(-1); y = (v * e2).sum(-1)
    r = np.hypot(x, y); phi = np.arctan2(y, x)
    ok = (r >= r_min) & (r <= r_max) & (phi >= -0.03) & (phi <= sweep + 0.03)
    tau = t - t0
    u = np.clip(phi / sweep, 0, 1)
    t_out = stroke * np.arccos(1 - 2 * u) / np.pi; t_back = 2 * stroke - t_out
    since = np.where(tau >= t_back, tau - t_back, np.where(tau >= t_out, tau - t_out, (tau + period - t_back) if prev else 1e4))
    return np.where(ok, since, 1e4).astype(np.float32)


def shade(su, sv):
    n = np.stack([-su, -sv, np.ones_like(su)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
    L = np.array([-0.4, 0.5, 0.77]); s = np.clip((n * L).sum(-1), 0, 1)
    return s


if __name__ == '__main__':
    G = Glass()
    Wpx, Hpx = 400, 600; w, h = 0.10, 0.15
    xs = (np.arange(Wpx) + 0.5) / Wpx * w; ys = (np.arange(Hpx) + 0.5) / Hpx * h
    X, Y = np.meshgrid(xs, ys[::-1])
    P = np.stack([X, Y], -1).astype(np.float32)
    strip = [shade(*G.slopes(P, t, amount=1.0, speed=0.03, density=0.9)[:2]) for t in (0.0, 1.5, 3.0, 4.5, 6.0)]
    Image.fromarray((np.concatenate(strip, 1) * 255).astype(np.uint8)).save(os.path.join(OUT, 'look_runners_strip.png'))
