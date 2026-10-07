"""numpy port (float32) of LanbaiRain.cginc :: LanbaiRunners() - KEEP THE TWO IN SYNC, line for line.
Used to (a) look at / measure the motion (kymographs, headless-channel and pop counts), (b) build the height field
of the Blender glass preview.

Model (v2, after verification round 2):
  * each lane of each repeat of the 0.20 x 0.40 m lane lattice has its own identity (timing, size, speed);
  * a lane runs CYCLES: in cycle c a drop may start at phase fs0 (top half of the tile), slide down, and STOP at
    fs1 (<= 0.97, never at the tile edge). After fs1 the head is frozen: it relaxes into a round bead, holds, then
    evaporates before the cycle is dropped. Nothing ever moves without its head;
  * the channel behind the head refills by the TIME SINCE THE HEAD PASSED each point; the previous cycle is
    evaluated too, so its channel and its stopped bead carry across the wrap (no one-frame pops);
  * motion is driven by a DISTANCE clock D (metres slid by a reference drop, integrated by Udon), so speed changes
    never make the heads jump; stick-slip is POSITIONAL (pinning sites on the glass): dDw/dD = 1 + 0.9 ss cos(..) > 0;
  * 'density' fades lanes in and out over a 0.08 band, so a changing density never pops a head into existence.
"""
import numpy as np

TU, TV, W = np.float32(0.20), np.float32(0.40), np.float32(0.005)
TH = np.radians(55.0)
S2 = np.float32(np.sin(TH) ** 2); C = np.float32(np.cos(TH)); HK = np.float32((1 - np.cos(TH)) / np.sin(TH))
TILE_CUT = np.float32(0.07)     # the lane lattice is cut at u = 0.93, where no lane runs (meta/runners.json)
FS1_MAX = np.float32(0.97)      # a drop always stops >= 12 mm above its tile's lower edge


def f32(x):
    return np.asarray(x, np.float32)


def frac(x):
    return x - np.floor(x)


def sstep(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)


def hash11(p):
    p = frac(f32(p) * np.float32(0.1031))
    p = p * (p + np.float32(33.33))
    p = p * (p + p)
    return frac(p)


def hash21(px, py):
    """Dave Hoskins hash12 (= LanbaiHash21)"""
    px = f32(px); py = f32(py)
    p3x = frac(px * np.float32(0.1031)); p3y = frac(py * np.float32(0.1031)); p3z = frac(px * np.float32(0.1031))
    dd = p3x * (p3y + np.float32(33.33)) + p3y * (p3z + np.float32(33.33)) + p3z * (p3x + np.float32(33.33))
    p3x = p3x + dd; p3y = p3y + dd; p3z = p3z + dd
    return frac((p3x + p3y) * p3z)


def sample_bilinear(img, u, v):
    """img: float (H, W, C) with row 0 = TOP (PNG); u, v in tile units, repeat wrap, v up (Unity)."""
    H, Wd = img.shape[:2]
    x = frac(u) * Wd - 0.5; y = frac(1 - frac(v)) * H - 0.5      # PNG row from Unity v
    x0 = np.floor(x).astype(int); y0 = np.floor(y).astype(int)
    fx = (x - x0)[..., None]; fy = (y - y0)[..., None]
    x0 %= Wd; y0 %= H; x1 = (x0 + 1) % Wd; y1 = (y0 + 1) % H
    return (img[y0, x0] * (1 - fx) * (1 - fy) + img[y0, x1] * fx * (1 - fy) + img[y1, x0] * (1 - fx) * fy + img[y1, x1] * fx * fy)


def cap(across, along, a, af, at):
    """spherical cap (55 deg contact angle) stretched into a runner: returns h, d h / d across, d h / d along"""
    ad = np.where(along < 0, af, at)
    rho2 = (across / a) ** 2 + (along / ad) ** 2
    q = np.sqrt(np.maximum(1 - rho2 * S2, 1e-4))
    inside = (rho2 < 1).astype(np.float32)
    hmax = a * HK
    h = hmax * (q - C) / (1 - C) * inside
    dh = hmax * (-S2 / (2 * q)) / (1 - C) * inside                   # dh / d(rho2)
    return h, dh * 2 * across / (a * a), dh * 2 * along / (ad * ad), rho2


def runners(flow, p_m, t, dist, v_avg, density=0.05, size=0.0030, stretch=0.0, stickslip=1.0, trail_life=6.0,
            seed_off=0.0, bead_off=None):
    """flow: (H,W,4) float 0..1 ; p_m: (...,2) metres in runner space (drops move toward -v).
    dist: the distance clock D (m) = integral of this layer's reference speed; v_avg: recent mean of that speed (m/s,
    > 0), only used to turn distances into ages. bead_off: (...,2) runner-space metres from this pixel to the centre of
    the static bead under it (LanbaiBeadCentre): the CLEAR mask is evaluated there, so a runner takes a bead whole or
    leaves it whole - never slices it. Returns slope_u, slope_v, height_m, clear (all arrays)."""
    uv_u = p_m[..., 0] / TU; uv_v = p_m[..., 1] / TV
    f = sample_bilinear(flow, uv_u, uv_v).astype(np.float32)
    out_su = np.zeros(p_m.shape[:-1], np.float32); out_sv = np.zeros_like(out_su)
    out_h = np.zeros_like(out_su); out_c = np.zeros_like(out_su)
    fa = f[..., 3]
    dx = (f[..., 0] * 2 - 1) * W
    tx = np.floor(uv_u - dx / TU + TILE_CUT); ty = np.floor(uv_v)
    lane = f[..., 1] + np.float32(seed_off) + hash21(tx * 1.618 + seed_off * 3.7, ty * 2.414 + 0.5) * np.float32(9.0)
    h1 = hash11(lane * 113.7 + 0.1); h2 = hash11(lane * 71.3 + 0.7); h3 = hash11(lane * 37.9 + 0.3); h4 = hash11(lane * 53.1 + 0.9)
    lf = 0.55 + 0.9 * h1                                              # this lane's speed factor
    spd = np.maximum(lf * v_avg, 1e-4) / TV                           # tile units / s (for ages)
    lam = 0.012 + 0.028 * h2                                          # stick-slip: a pinning site every 1.2-4 cm
    w_ = 2 * np.pi / lam
    dw = dist + stickslip * 0.9 / w_ * np.sin(w_ * dist + 6.2832 * h3)
    inst = 1 + stickslip * 0.9 * np.cos(w_ * dist + 6.2832 * h3)      # instantaneous speed / mean
    s = h4 + lf * dw / TV
    cyc = np.floor(s); fs = s - cyc
    y = uv_v - ty                                                     # 0..1 inside this tile, 1 = top
    pth = f[..., 2] * 2 - 1
    ca = 1 / np.sqrt(1 + pth * pth)
    across = dx * ca
    bo_u = np.zeros_like(dx) if bead_off is None else bead_off[..., 0]
    bo_v = np.zeros_like(dx) if bead_off is None else bead_off[..., 1]
    across_c = (dx + bo_u - pth * bo_v) * ca                          # at the bead's centre (clear mask only)
    y_c = y + bo_v / TV
    tl = np.minimum(np.float32(trail_life) * 1.5, 0.75 / spd)         # channel refill time (s), < the bead's hold
    tp = np.minimum(np.float32(trail_life) * 3.0, 0.97 / spd)         # residue pearls last longer
    head_new_ph = None
    cyc_data = []
    for k in (0, 1):                                                  # pass 1: heads and channels of both cycles
        cc = cyc - k
        p = fs + k                                                    # phase within cycle cc (>= 1: it has ended)
        c1 = hash11(lane * 19.19 + cc * 0.6180339); c2 = hash11(lane * 7.77 + cc * 0.4142136); c3 = hash11(c1 * 3.1 + c2)
        act = np.clip((density - c1) / 0.08, 0, 1)
        fs0 = 0.02 + 0.48 * c2
        fs1 = np.minimum(FS1_MAX, fs0 + 0.45 + 0.5 * c3)
        ph = np.minimum(p, fs1)                                       # head phase (frozen after fs1)
        moving = (p < fs1).astype(np.float32)
        grow = sstep(fs0, fs0 + 0.06, p)
        tpost = np.maximum(p - fs1, 0) / spd                          # s since it stopped
        hold = 1 - sstep(0.75 / spd, 1.00 / spd, tpost)               # stopped bead holds, then evaporates
        merged = np.float32(1.0)
        if k == 1:                                                    # the new head swallows the old stopped bead
            merged = 1 - (head_new_ph >= fs1 - 0.01).astype(np.float32) * act_new
        vh = 1 - ph
        along = (y - vh) * TV                                         # + = behind (above) the head
        a = size * (0.8 + 0.4 * h3) * (0.6 + 0.4 * grow) * (1 - 0.35 * sstep(0, 1.5, tpost))
        a = np.maximum(a, 1e-5)
        af = a * 0.9
        at = a * (1.0 + moving * (0.25 + stretch + 0.35 * np.clip(inst, 0, 2)))
        hgt, gA, gL, rho2 = cap(across, along, a, af, at)
        life = grow * hold * act * merged * fa
        # channel: from the start (fs0) down to just behind the head, refilled by the time since the head passed
        fp = 1 - y                                                    # phase at which the head passed this row
        seen = sstep(fs0, fs0 + 0.01, fp)
        behind = sstep(at * 0.3, at, along) * seen * (fp <= ph).astype(np.float32)
        age = np.maximum(p - fp, 0) / spd
        fade = sstep(tl, 0.0, age)
        trail = behind * sstep(a * 1.05, a * 0.7, np.abs(across)) * fade * act * fa
        # the same channel and head, evaluated at the centre of the bead under this pixel (whole beads go)
        along_c = (y_c - vh) * TV
        fp_c = 1 - y_c
        behind_c = sstep(at * 0.3, at, along_c) * sstep(fs0, fs0 + 0.01, fp_c) * (fp_c <= ph).astype(np.float32)
        fade_c = sstep(tl, 0.0, np.maximum(p - fp_c, 0) / spd)
        trail_c = behind_c * sstep(a * 1.05, a * 0.7, np.abs(across_c)) * fade_c * act * fa
        rho2_c = (across_c / a) ** 2 + (along_c / np.where(along_c < 0, af, at)) ** 2
        cyc_data.append(dict(cc=cc, a=a, along=along, behind=behind, age=age, act=act, hgt=hgt * life, gA=gA * life,
                             gL=gL * life, rho2=rho2_c, life=life, trail=trail_c, head=(rho2 < 1.15).astype(np.float32) * life))
        if k == 0:
            head_new_ph = ph; act_new = act * (p >= fs0)
    no_head = 1 - np.clip(np.maximum(cyc_data[0]['head'], cyc_data[1]['head']), 0, 1)
    for d in cyc_data:                                                # pass 2: residue pearls, never inside a head
        a, along, cc = d['a'], d['along'], d['cc']
        DL = np.float32(0.0016)
        kk = np.floor(along / DL + 0.5)
        r1 = hash11(lane * 91.7 + kk * 0.7548777 + cc * 0.31); r2 = hash11(lane * 13.3 + kk * 0.5698403); r3 = hash11(r1 * 7.1 + r2)
        pcl = (kk + (r1 - 0.5) * 0.4) * DL
        pca = (r2 - 0.5) * 0.7 * a
        pr = 0.00010 + 0.00020 * r3 * r3
        pd2 = ((along - pcl) ** 2 + (across - pca) ** 2) / (pr * pr)
        pin = (pd2 < 1).astype(np.float32) * d['behind'] * (r3 > 0.25) * sstep(tp, 0.0, d['age']) * d['act'] * fa * no_head
        pq = np.sqrt(np.maximum(1 - pd2 * S2, 1e-4))
        ph_ = pr * HK * (pq - C) / (1 - C) * pin
        pdh = pr * HK * (-S2 / (2 * pq)) / (1 - C) * pin
        gA = d['gA'] + pdh * 2 * (across - pca) / (pr * pr)
        gL = d['gL'] + pdh * 2 * (along - pcl) / (pr * pr)
        out_su += gA * ca; out_sv += gL - gA * pth * ca
        out_h = np.maximum(out_h, np.maximum(d['hgt'], ph_))
        head_clear = np.clip((1.35 - d['rho2']) / 0.35, 0, 1) * d['life']
        out_c = np.maximum(out_c, np.maximum(np.clip(d['trail'] * 2.0, 0, 1), head_clear))
    out_su[fa < 0.002] = 0; out_sv[fa < 0.002] = 0; out_h[fa < 0.002] = 0; out_c[fa < 0.002] = 0
    return out_su, out_sv, out_h, out_c
