"""Act 4c geometry as numpy arrays (Unity space, metres): every mesh of the package, from inside_def + the solved layout.
inside_mesh.py (bpy) turns these into FBX; inside_render.py (numpy) ray-traces the same outlines.

Object frames: a lip object sits at InsideRoot-local (0, 0, s_k) (rotation 0, scale 1); its vertices carry the
opening's offset and roll. Sleeve plies sit at (0, 0, s_8 + dz_i).
Vertex channels (shader Lanbai/InsideLip):
  Sheet   uv0 = local xy / 100, uv1 = (metres to the torn edge, metres along the edge), colour R = gain
  Fringe  uv0 = (metres along the edge / 64, 0 at the cloth .. 1 at the tips), colour R = gain
  Thread  uv0 = (metres along / 64, 0..1 across), colour R = gain
"""
import json
import math
import os
import sys

import numpy as np
from scipy.spatial import cKDTree

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inside_def as D  # noqa: E402
import inside_layout as LY  # noqa: E402

R_FAR = 2200.0
FRINGE_TILE = 64.0


def curl_z(d_edge, u_edge, Hk, seed, perim):
    """torn cloth turns out of its plane at the lip: +z = away from the bus. Fades in ~1.5 % H from the edge.
    r04: three incommensurate wave counts (art review r03: one sinusoid read as a repeating silhouette)."""
    lam = 0.015 * Hk
    amp = 0.016 * Hk
    # r05: multi-scale wrapped noise along the edge (art review r03 / r04 and our own r05 side view: any sum of a few
    # sines still reads as a regular wave edge-on). Seamless round the loop (mode='wrap'), irregular, with kinks.
    from scipy.ndimage import gaussian_filter1d
    rng = np.random.default_rng(int(seed) * 7 + 3)
    m = max(int(perim / 0.5), 64)
    c = np.zeros(m)
    for sig_m, wgt in ((0.012 * Hk, 0.35), (0.04 * Hk, 0.6), (0.12 * Hk, 1.0)):
        nz = gaussian_filter1d(rng.normal(size=m), sig_m / 0.5, mode='wrap')
        c += wgt * nz / (nz.std() + 1e-9)
    c /= 1.25
    c = np.sign(c) * np.abs(c) ** 0.8                  # a little sharper at the turns
    xs = np.linspace(0, perim, m, endpoint=False)
    c = np.interp(np.mod(np.asarray(u_edge, float), perim), np.r_[xs, perim], np.r_[c, c[0]])
    return amp * c * np.exp(-np.asarray(d_edge) / lam)


def billow_z(xy, seed, amp, scale):
    """a slow 2-d sag of the whole sheet (r05: a perfectly flat ply seen edge-on in the sleeve is a ruled vertical line)."""
    rng = np.random.default_rng(int(seed) * 13 + 11)
    z = 0.0
    for j in range(6):
        a = rng.uniform(0, np.pi)
        k = 2 * np.pi / (scale * rng.uniform(0.5, 1.6))
        z = z + np.sin(k * (xy[:, 0] * np.cos(a) + xy[:, 1] * np.sin(a)) + rng.uniform(0, 6.283)) / (1.0 + 0.4 * j)
    return amp * z / 2.3


def sheet(contour, Hk, seed, gain=1.0, r_far=R_FAR, centre=(0.0, 0.0), billow=0.0):
    import triangle
    from shapely.geometry import Polygon
    C = np.asarray(contour, float)
    n = len(C)
    seg = np.linalg.norm(np.roll(C, -1, 0) - C, axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])[:-1]
    perim = float(seg.sum())
    ds = float(np.median(seg))
    nrm = D.normals(C, smooth=6)
    pg = Polygon(C)
    tree = cKDTree(C)
    pts = [C]
    rings = [0.6, 1.6, 3.5, 7.0, 13.0, 24.0, 42.0, 75.0, 130.0, 220.0, 380.0, 640.0, 1050.0, 1600.0]
    for d in rings:
        step = max(1, int(round(d / (ds * 2.2))))
        P = C[::step] + nrm[::step] * d
        P = P[np.linalg.norm(P - np.asarray(centre), axis=1) < r_far * 0.97]
        if len(P) == 0:
            continue
        dd, _ = tree.query(P)
        keep = dd > 0.55 * d
        import shapely
        keep &= ~shapely.contains_xy(pg, P[:, 0], P[:, 1])
        pts.append(P[keep])
    m = 128
    a = np.linspace(0, 2 * np.pi, m, endpoint=False)
    outer = np.stack([np.cos(a), np.sin(a)], -1) * r_far + np.asarray(centre)
    V2 = np.concatenate(pts + [outer], 0)
    segs = np.concatenate([np.stack([np.arange(n), (np.arange(n) + 1) % n], -1),
                           np.stack([np.arange(m), (np.arange(m) + 1) % m], -1) + len(V2) - m], 0)
    hole = np.array(pg.representative_point().coords[0])
    T = triangle.triangulate(dict(vertices=V2, segments=segs, holes=[hole]), 'pQ')
    V2, F = T['vertices'], T['triangles']
    dd, idx = tree.query(V2)
    # inside the opening the nearest-point distance is not "into the cloth": the triangulation has no such vertices
    # r12 (art review r11 S4): the nearest edge point jumps across the medial axis and the folds (a function of u) broke
    # into zigzag seams there: u = the inverse-distance circular mean of the 4 nearest edge points (wrap-aware)
    dk, ik = tree.query(V2, k=4)
    wk = 1.0 / np.maximum(dk, 1e-3) ** 2
    ang = arc[ik] / perim * 2.0 * np.pi
    u = (np.angle((wk * np.exp(1j * ang)).sum(1)) % (2.0 * np.pi)) / (2.0 * np.pi) * perim
    z = curl_z(dd, u, Hk, seed, perim)
    if billow > 0:
        z = z + billow_z(V2, seed, billow, 45.0) * (1.0 - np.exp(-dd / 6.0))   # the edge keeps its curl, the cloth sags
    V = np.stack([V2[:, 0], V2[:, 1], z], -1)
    uv0 = V2 / 100.0
    uv1 = np.stack([dd, u], -1)
    col = np.tile([gain, 0, 0, 1], (len(V), 1))
    return dict(V=V, F=F, uv0=uv0, uv1=uv1, col=col, perim=perim)


def fringe(contour, Hk, seed, L, gain=1.0, roll=0.0):
    """r04 (art review r03: radial bristles read as fur): a torn weave frays along its warp or weft, so each fibre points
    along whichever of the two (rotated with the lip's roll) runs more into the opening; most are short."""
    C = np.asarray(contour, float)
    seg = np.linalg.norm(np.roll(C, -1, 0) - C, axis=1)
    arc = np.concatenate([[0], np.cumsum(seg)])[:-1]
    perim = float(seg.sum())
    nrm = D.normals(C, smooth=2)
    rng = np.random.default_rng(seed + 5)
    zb = curl_z(np.zeros(len(C)), arc, Hk, seed, perim)
    base = C + nrm * 0.4
    a = np.radians(roll)
    warp = np.array([-np.sin(a), np.cos(a)])
    weft = np.array([np.cos(a), np.sin(a)])
    inward = -nrm
    dw, df = inward @ warp, inward @ weft
    dirs = np.where((np.abs(dw) >= np.abs(df))[:, None], np.sign(dw)[:, None] * warp[None], np.sign(df)[:, None] * weft[None])
    from scipy.ndimage import gaussian_filter1d
    dirs = np.stack([gaussian_filter1d(dirs[:, 0], 2, mode='wrap'), gaussian_filter1d(dirs[:, 1], 2, mode='wrap')], -1)
    dirs /= np.linalg.norm(dirs, axis=1, keepdims=True) + 1e-9
    tip = C + dirs * L
    zt = zb + L * (0.35 * D.fbm(arc / 37.0, seed + 6, 2))       # fibres stick out of the plane a little
    n = len(C)
    V = np.concatenate([np.c_[base, zb], np.c_[tip, zt]], 0)
    u = arc / FRINGE_TILE
    # close the loop seamlessly: duplicate the first column with u = perimeter / tile
    V = np.concatenate([V[:n], V[:1], V[n:], V[n:n + 1]], 0)
    u = np.r_[u, perim / FRINGE_TILE]
    m = n + 1
    uv0 = np.concatenate([np.c_[u, np.zeros(m)], np.c_[u, np.ones(m)]], 0)
    F = []
    for i in range(n):
        F.append((i, i + 1, m + i + 1))
        F.append((i, m + i + 1, m + i))
    col = np.tile([gain, 0, 0, 1], (len(V), 1))
    return dict(V=V, F=np.array(F), uv0=uv0, col=col, rngstate=rng.random())


def threads(contour_unrolled_H, Hk, roll, off, seed, z_at, bus_clear):
    """2-5 unbroken dark weft threads across the narrow ends of a slit / fork (none for holes); one or two broken."""
    from shapely.geometry import Polygon, LineString, box
    rng = np.random.default_rng(seed + 77)
    pg = Polygon(contour_unrolled_H)
    cands = []
    for v in np.linspace(-0.48, 0.48, 400):
        ln = LineString([(-1, v), (1, v)])
        it = pg.intersection(ln)
        if it.geom_type != 'LineString' or it.is_empty:
            continue
        x0, x1 = sorted([it.coords[0][0], it.coords[-1][0]])
        w = x1 - x0
        if 0.025 < w < 0.10:
            cands.append((v, x0, x1, w))
    if not cands:
        return None
    rng.shuffle(cands)
    chosen = []
    for c in cands:
        if all(abs(c[0] - q[0]) > 0.05 for q in chosen):
            chosen.append(c)
        if len(chosen) >= int(rng.integers(3, 6)):
            break
    R = D.lip_roll_matrix(roll)
    bus = box(-D.BUS_HALF_W, D.BUS_Y0, D.BUS_HALF_W, D.BUS_Y1)
    Vs, Fs, UVs = [], [], []
    width = max(0.0035 * Hk, 1.2)
    out = []
    for j, (v, x0, x1, w) in enumerate(sorted(chosen)):
        broken = j in (1, 3)
        npt = 14
        f = np.linspace(0, 1, npt)
        if broken:
            ln = rng.uniform(0.45, 0.75)
            f = f * ln
            sag = -0.5 * w * ln * (f / ln) ** 1.8                      # the loose end hangs
        else:
            sag = -0.035 * w * 4 * f * (1 - f)
        if broken and rng.random() < 0.5:
            xs, from_right = x1 - f * w, True
        else:
            xs, from_right = x0 - 0.01 + f * (w + 0.02), False
        ys = v + sag
        P = (R @ (np.stack([xs, ys], -1) * Hk).T).T + np.asarray(off)
        line = LineString(P)
        if line.distance(bus) < bus_clear:
            continue
        tg = np.gradient(P, axis=0)
        tg /= np.linalg.norm(tg, axis=1, keepdims=True) + 1e-9
        nn = np.stack([-tg[:, 1], tg[:, 0]], -1) * width * 0.5
        z = z_at(P)
        k0 = sum(len(q) for q in Vs)
        Vs.append(np.concatenate([np.c_[P - nn, z], np.c_[P + nn, z]], 0))
        arc = np.concatenate([[0], np.cumsum(np.linalg.norm(np.diff(P, axis=0), axis=1))])
        UVs.append(np.concatenate([np.c_[arc / FRINGE_TILE, np.zeros(npt)], np.c_[arc / FRINGE_TILE, np.ones(npt)]], 0))
        for i in range(npt - 1):
            Fs.append((k0 + i, k0 + i + 1, k0 + npt + i + 1))
            Fs.append((k0 + i, k0 + npt + i + 1, k0 + npt + i))
        out.append(dict(v=float(v), broken=bool(broken), from_right=bool(from_right), span_m=float(w * Hk)))
    if not Vs:
        return None
    V = np.concatenate(Vs, 0)
    return dict(V=V, F=np.array(Fs), uv0=np.concatenate(UVs, 0), col=np.tile([1.0, 0, 0, 1], (len(V), 1)), info=out)


def dome(r=2400.0, nu=48, nv=24):
    th = np.linspace(0, np.pi, nv + 1)
    ph = np.linspace(0, 2 * np.pi, nu + 1)
    T, P = np.meshgrid(th, ph, indexing='ij')
    V = np.stack([np.sin(T) * np.cos(P), np.cos(T), np.sin(T) * np.sin(P)], -1).reshape(-1, 3) * r
    F = []
    for i in range(nv):
        for j in range(nu):
            a = i * (nu + 1) + j
            b, c, d = a + 1, a + nu + 1, a + nu + 2
            F += [(a, c, b), (b, c, d)]                 # inward-facing (Cull Off in the material anyway)
    return dict(V=V, F=np.array(F), uv0=np.zeros((len(V), 2)), col=np.tile([1.0, 0, 0, 1], (len(V), 1)))


def dot_quad():
    V = np.zeros((4, 3))
    uv0 = np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]])
    return dict(V=V, F=np.array([(0, 1, 2), (0, 2, 3)]), uv0=uv0, col=np.tile([1.0, 0, 0, 1], (4, 1)))


def loose_threads(n=90, seg=8, seed=901):
    rng = np.random.default_rng(seed)
    V, F, uv0, uv1, uv2, uv3, col = [], [], [], [], [], [], []
    for i in range(n):
        axis = rng.normal(0, 1, 3)
        axis[2] *= 0.5
        axis /= np.linalg.norm(axis)
        phase = rng.uniform(0, 14.0)
        speed = rng.uniform(0.2, 0.5)
        r0 = rng.uniform(9.0, 25.0)
        ang = rng.uniform(0, 2 * np.pi)
        z0 = rng.uniform(-22.0, 26.0)
        ln = rng.uniform(0.6, 3.0)
        br = rng.uniform(0.5, 1.0)
        k0 = len(V)
        for s in range(seg + 1):
            for side in (-1.0, 1.0):
                V.append((0, 0, 0))
                uv0.append((s / seg, side))
                uv1.append((phase, speed))
                uv2.append((r0, ang))
                uv3.append((z0, ln))
                col.append((*(axis * 0.5 + 0.5), br))
        for s in range(seg):
            a = k0 + 2 * s
            F += [(a, a + 2, a + 3), (a, a + 3, a + 1)]
    return dict(V=np.array(V, float), F=np.array(F), uv0=np.array(uv0), uv1=np.array(uv1), uv2=np.array(uv2),
                uv3=np.array(uv3), col=np.array(col), bounds=60.0)


def sleeve_wall(entry, exit_, dz, seed=313, n=90):
    """long dark strands of pulled warp running from the entry's torn edge to the exit's (the thick cloth's cut face):
    irregular spacing, widths 0.8-3 m, sagging, each slightly outside the opening (in the cloth), rim lit <= 15 %."""
    rng = np.random.default_rng(seed)
    E = np.asarray(entry)
    X = np.asarray(exit_)
    ce, cx = E.mean(0), X.mean(0)
    Vs, Fs, UVs = [], [], []
    angs = np.sort(rng.uniform(-np.pi, np.pi, n))
    for a in angs:
        def edge(P, c):
            d = P - c
            th = np.arctan2(d[:, 1], d[:, 0])
            i = int(np.argmin(np.abs(np.angle(np.exp(1j * (th - a))))))
            return P[i] + (P[i] - c) / (np.linalg.norm(P[i] - c) + 1e-9) * rng.uniform(0.5, 4.0)
        p0, p1 = edge(E, ce), edge(X, cx)
        w = rng.uniform(0.12, 0.45) * (2.5 if rng.random() < 0.1 else 1.0)    # r05: hairs, a few thicker (r04 read as cables)
        m = 24
        ln = rng.uniform(0.25, 0.6)                     # r06 (art review r05 #7): strands broken, 25-60 % of the depth
        f0 = rng.uniform(0.0, 1.0 - ln)
        f = f0 + ln * np.linspace(0, 1, m)
        P = p0[None] + (p1 - p0)[None] * f[:, None]
        sag = rng.uniform(1.5, 7.0) * 4 * f * (1 - f) + rng.uniform(1.0, 4.0) * ((f - f0) / ln) ** 2    # loose ends droop
        P[:, 1] -= sag
        side = np.array([-(p1 - p0)[1], (p1 - p0)[0]]) / (np.linalg.norm(p1 - p0) + 1e-9)
        P += side[None] * (rng.uniform(0.5, 2.5) * np.sin(f * np.pi * rng.uniform(1, 3) + rng.uniform(0, 6.28)))[:, None]
        zz = f * dz
        nrm = np.array([-(p1 - p0)[1], (p1 - p0)[0]])
        nrm = nrm / (np.linalg.norm(nrm) + 1e-9) * w * 0.5
        rad = (P - P.mean(0))
        k0 = sum(len(q) for q in Vs)
        Vs.append(np.concatenate([np.c_[P - nrm, zz], np.c_[P + nrm, zz]], 0))
        L = np.linalg.norm(p1 - p0) + dz
        UVs.append(np.concatenate([np.c_[f * L / FRINGE_TILE, np.zeros(m)], np.c_[f * L / FRINGE_TILE, np.ones(m)]], 0))
        for i in range(m - 1):
            Fs += [(k0 + i, k0 + i + 1, k0 + m + i + 1), (k0 + i, k0 + m + i + 1, k0 + m + i)]
    V = np.concatenate(Vs, 0)
    g = np.repeat(rng.uniform(0.03, 0.10, len(Vs)), [len(q) for q in Vs])     # r05: dim, uneven
    col = np.stack([g, np.ones_like(g), np.zeros_like(g), np.ones_like(g)], -1)
    return dict(V=V, F=np.array(Fs), uv0=np.concatenate(UVs, 0), col=col)


def cut_partial(sh, centre, start_deg, span_deg, r_min):
    """keep only the triangles inside the angular sector (a torn flap that does not close the ring); near the opening
    (r < r_min) the ring is kept so the edge stays continuous where the flap is attached."""
    V, F = sh['V'], sh['F']
    c = V[F].mean(1)[:, :2] - np.asarray(centre)
    ang = (np.degrees(np.arctan2(c[:, 1], c[:, 0])) - start_deg) % 360.0
    r = np.hypot(c[:, 0], c[:, 1])
    keep = (ang <= span_deg) | (r < r_min)
    sh = dict(sh)
    sh['F'] = F[keep]
    return sh


def hanging(contour, Hk, seed, n=14, gain=1.0, need=40.0):
    """a few long loose threads hanging under gravity from the upper edges (art review r03), thin additive ribbons with
    the fringe texture's long-strand column (uv0.x fixed per thread)."""
    rng = np.random.default_rng(seed + 61)
    C = np.asarray(contour, float)
    cy = C[:, 1].mean()
    nrm = D.normals(C, smooth=4)
    cand = np.where((C[:, 1] > cy) & (nrm[:, 1] > 0.3))[0]
    if len(cand) == 0:
        return None
    V, F, uv = [], [], []
    for j in range(n):
        i = int(rng.choice(cand))
        p0 = C[i]
        L = rng.uniform(0.02, 0.05) * Hk
        from shapely.geometry import box, LineString
        bus = box(-D.BUS_HALF_W, D.BUS_Y0, D.BUS_HALF_W, D.BUS_Y1)
        while L > 1.0 and LineString([p0, (p0[0], p0[1] - L)]).distance(bus) < need:
            L *= 0.8                                       # the bus path keeps its clearance from every thread
        if L <= 1.0:
            continue
        w = max(0.0012 * Hk, 0.15)
        m = 10
        f = np.linspace(0, 1, m)
        drift = rng.normal(0, 0.12) * L
        P = np.stack([p0[0] + drift * f ** 1.5, p0[1] - L * f], -1)
        k = len(V)
        for q in range(m):
            V.append((P[q, 0] - w / 2, P[q, 1], 0.0))
            V.append((P[q, 0] + w / 2, P[q, 1], 0.0))
            col = rng.uniform(0.62, 0.9)
            uv += [(col, 0.08 + 0.85 * f[q]), (col + 0.0004, 0.08 + 0.85 * f[q])]
        for q in range(m - 1):
            a = k + 2 * q
            F += [(a, a + 2, a + 3), (a, a + 3, a + 1)]
    V = np.array(V, float)
    return dict(V=V, F=np.array(F), uv0=np.array(uv), col=np.tile([gain, 1.0, 0, 1], (len(V), 1)))


def fringe_gaps(fr, perim, seed):
    """bundles stop for 3-15 m now and then (review r1: one tiled comb everywhere reads as a printed border)."""
    rng = np.random.default_rng(seed + 31)
    n2 = len(fr['V']) // 2
    u = fr['uv0'][:n2, 0] * FRINGE_TILE
    keep = np.ones(n2)
    pos = 0.0
    while pos < perim:
        pos += rng.uniform(25, 90)
        w = rng.uniform(3, 15)
        keep *= 1 - np.clip(1 - np.abs(u - pos) / (w * 0.5), 0, 1) ** 0.5 * (np.abs(u - pos) < w * 0.5)
    g = np.r_[keep, keep]
    fr = dict(fr)
    col = fr['col'].copy()
    col[:, 1] = g
    fr['col'] = col
    fr['uv0'] = fr['uv0'] + np.array([rng.uniform(0, 1), 0])          # each lip starts its comb elsewhere
    return fr


def fringe_taper(fr, contour, need, Hk):
    """fringe length cut where the edge is near the bus (lip 1: the gate's own lens is only 61.6 m from the path)."""
    from shapely.geometry import box, Point
    bus = box(-D.BUS_HALF_W, D.BUS_Y0, D.BUS_HALF_W, D.BUS_Y1)
    n2 = len(fr['V']) // 2
    base, tip = fr['V'][:n2].copy(), fr['V'][n2:].copy()
    for i in range(n2):
        d = Point(base[i, 0], base[i, 1]).distance(bus)
        L = np.linalg.norm(tip[i, :2] - base[i, :2])
        allow = max(0.0, d - need)
        if L > allow and L > 1e-6:
            tip[i, :2] = base[i, :2] + (tip[i, :2] - base[i, :2]) * allow / L
    fr = dict(fr)
    fr['V'] = np.concatenate([base, tip], 0)
    return fr


def build():
    rep = json.load(open(os.path.join(LY.OUT, 'layout_solved.json')))
    objs = {}
    meta = {'lips': [], 'plies': []}
    for L in rep['lips']:
        k = L['k']
        Hk = L['H']
        if k == 8:
            continue
        if k == 1:
            C = D.tear_outline_lip1()
            C, _ = D.resample(C, 3.5)
            seed = 101
        else:
            seed = L['seed']
            C = LY.lip_polygon(L['mesh_kind'], seed, Hk, L['roll'], L['offset'])
        sh = sheet(C, Hk, seed, 1.0)
        fl = 4.0 if k == 1 else LY.fringe_len(Hk)
        fr = fringe(C, Hk, seed, fl, 1.0, L['roll'] if k > 1 else -4.0)
        fr = fringe_taper(fr, C, L['clearance_need'], Hk)
        hg = hanging(C, Hk, seed, need=L['clearance_need'])
        if hg:
            objs['Lip%d_Hang' % k] = hg
        fr = fringe_gaps(fr, sh['perim'], seed)
        objs['Lip%d_Sheet' % k] = sh
        objs['Lip%d_Fringe' % k] = fr
        info = None
        if L['type'] in ('single', 'branched'):
            un = D.outline(L['mesh_kind'], seed)
            un, _ = D.torn_edge(un, Hk, seed)
            perim = sh['perim']
            Cc = np.asarray(C)
            segl = np.linalg.norm(np.roll(Cc, -1, 0) - Cc, axis=1)
            arc = np.concatenate([[0], np.cumsum(segl)])[:-1]
            tree = cKDTree(Cc)

            def z_at(P, tree=tree, arc=arc, Hk=Hk, seed=seed, perim=perim):
                dd, idx = tree.query(P)
                return curl_z(np.zeros(len(P)), arc[idx], Hk, seed, perim)
            th = threads(un, Hk, L['roll'], L['offset'], seed, z_at, L['clearance_need'])
            if th:
                info = th.pop('info')
                objs['Lip%d_Threads' % k] = th
        meta['lips'].append(dict(k=k, z=L['s'], H=Hk, roll=L['roll'], contour=np.asarray(C).tolist(), fringe_len=fl, threads=info))
    l8 = rep['lips'][7]
    contours = []
    for p in rep['sleeve']['plies']:
        i = p['i']
        C = LY.lip_polygon('hole', p['seed'], 195.0 * p['scale'], p['roll'], p['offset'],
                           jag_seed=None)
        contours.append(C)
        sh = sheet(C, 195.0, p['seed'] + 7 * i, max(p['gain'], 0.30), billow=2.5 if p['fringe'] else 5.0)   # r07: inner plies' rims lit (art review r06 S3)
        if p['partial']:
            sh = cut_partial(sh, np.asarray(C).mean(0), p['partial'][0], p['partial'][1], 18.0)
        objs['Lip8_Ply%d_Sheet' % i] = sh
        if p['fringe']:
            fr = fringe(C, 195.0, p['seed'] + 7 * i, LY.fringe_len(195.0), p['gain'], p['roll'])
            fr = fringe_taper(fr, C, 40.0, 195.0)
            objs['Lip8_Ply%d_Fringe' % i] = fringe_gaps(fr, sh['perim'], p['seed'] + i)
        meta['plies'].append(dict(i=i, z=l8['s'] + p['dz'], contour=np.asarray(C).tolist(), gain=p['gain'],
                                  fringe=p['fringe'], partial=p['partial']))
    objs['Lip8_Wall'] = sleeve_wall(contours[0], contours[-1], rep['sleeve']['depth'])
    objs['Inside_Dome'] = dome()
    objs['Inside_Dot'] = dot_quad()
    objs['Inside_Loose'] = loose_threads()
    return rep, objs, meta


if __name__ == '__main__':
    rep, objs, meta = build()
    tot = 0
    for k, o in objs.items():
        print('%-22s %7d v %7d t' % (k, len(o['V']), len(o['F'])))
        tot += len(o['F'])
    print('total triangles', tot)
    json.dump(meta, open(os.path.join(LY.OUT, 'geom_meta.json'), 'w'))
