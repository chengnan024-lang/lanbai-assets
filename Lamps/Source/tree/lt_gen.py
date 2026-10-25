# -*- coding: utf-8 -*-
"""蓝白 · 样板树的生成器（纯 numpy；不用任何外部素材，所以整棵树是我们自己的，可以按 CC0 公开）。

骨架：空间殖民算法（Runions 2007）——在树冠包络里撒吸引点，枝从树干往点长，点被吃掉就停。
这样长出来的树冠有真的空隙和层次（法线贴图给不了的“轮廓和树冠空隙”，visual_feedback 03 的要点）。
半径：管道模型（da Vinci，r_parent^2.5 = Σ r_child^2.5）。
叶：每个末梢一簇叶片卡（cluster card），卡的朝向随机但偏向外侧和上方。

坐标：Z 上，树根在原点，米。
"""
import math

import numpy as np


class Species:
    def __init__(self, **kw):
        self.__dict__.update(kw)


# 三个候选形（参考板用）。都是东亚到欧洲乡道上常见的“无名”落叶阔叶树的形，不是某个具体树种的标本。
SPECIES = {
    # A：老的路边阔叶树（槐 / 榆一类的形）：短干，3–4 根斜伸的大枝，每根枝端一团叶云，团与团之间露天
    'A_old_broadleaf': Species(trunk_h=2.4, trunk_r=0.19, lean=(0.05, 0.01),
                               limbs=[(15, 30, 5.4, 1.0), (140, 38, 4.6, 0.85), (250, 48, 4.4, 0.8), (75, 62, 5.6, 0.95), (200, 70, 3.6, 0.7)],
                               clump=(1.7, 1.2), clumps_per_limb=2, n_pts=3600, step=0.24, infl=1.5, kill=0.40,
                               leaf_size=0.80, leaf_per_tip=2, droop=0.0, pendant=0.0, seed=4),
    # B：垂枝型（柳一类，水田边）：主干分成几根向上的大枝，枝端垂下 2–4 m 的细枝帘
    'B_weeping': Species(trunk_h=2.6, trunk_r=0.18, lean=(-0.05, 0.02),
                         limbs=[(0, 60, 5.0, 1.0), (125, 64, 4.6, 0.9), (245, 62, 4.8, 0.95), (300, 75, 4.0, 0.8)],
                         clump=(1.5, 1.0), clumps_per_limb=2, n_pts=2400, step=0.24, infl=1.4, kill=0.40,
                         leaf_size=0.60, leaf_per_tip=1, droop=0.0, pendant=3.2, seed=7),
    # C：柱形（杨树一类，但冠是碎的、有空隙）：本地杨树的形，改好的版本
    'C_columnar': Species(trunk_h=1.8, trunk_r=0.22, lean=(0.0, 0.0),
                          limbs=[(0, 84, 10.0, 1.0), (140, 70, 6.0, 0.7), (250, 72, 6.5, 0.7), (40, 76, 7.5, 0.7)],
                          clump=(1.2, 1.6), clumps_per_limb=4, n_pts=3200, step=0.22, infl=1.3, kill=0.38,
                          leaf_size=0.70, leaf_per_tip=2, droop=0.0, pendant=0.0, seed=11),
}


def limb_paths(sp, rng):
    """Major limbs from the fork (top of the trunk): gently curving polylines (azimuth, elevation, length)."""
    sp.trunk_h = sp.trunk_h0 * getattr(sp, 'scale', 1.0) ** 0.5 if hasattr(sp, 'trunk_h0') else sp.trunk_h
    top = np.array([sp.lean[0] * sp.trunk_h ** 2 / 2, sp.lean[1] * sp.trunk_h ** 2 / 2, sp.trunk_h])
    paths = []
    for az, el, L, w in sp.limbs:
        az = math.radians(az + rng.normal(0, 8)); el = math.radians(el + rng.normal(0, 4))
        pts = [top]
        L = L * getattr(sp, 'scale', 1.0)
        n = int(L / sp.step)
        d = np.array([math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])
        for k in range(n):
            d = d + np.array([0, 0, 0.04 if sp.droop == 0 else -0.02]) + rng.normal(0, 0.05, 3)
            d /= np.linalg.norm(d)
            pts.append(pts[-1] + d * sp.step)
        paths.append((np.array(pts), w))
    return top, paths


def attraction_points(sp, rng, paths):
    """Points in a union of ellipsoidal leaf clumps placed along / beyond each limb (a clumpy crown with sky between)."""
    clumps = []
    for P, w in paths:
        for k in range(sp.clumps_per_limb):
            t = 0.45 + 0.55 * (k + 1) / sp.clumps_per_limb
            c = P[min(len(P) - 1, int(t * (len(P) - 1)))] + rng.normal(0, 0.5, 3)
            if k == sp.clumps_per_limb - 1:
                c = P[-1] + (P[-1] - P[-2]) / sp.step * sp.clump[0] * 0.5
            r = np.array([sp.clump[0], sp.clump[0], sp.clump[1]]) * w * rng.uniform(0.75, 1.15) * getattr(sp, 'scale', 1.0)
            clumps.append((c, r))
    pts = []
    tries = 0
    while len(pts) < sp.n_pts and tries < sp.n_pts * 60:
        tries += 1
        c, r = clumps[rng.integers(len(clumps))]
        p = rng.uniform(-1, 1, 3)
        if (p ** 2).sum() > 1:
            continue
        q = c + p * r
        if q[2] < sp.trunk_h + 0.4:
            continue
        pts.append(q)
    return np.array(pts), clumps


def grow(sp):
    rng = np.random.default_rng(sp.seed)
    top, paths = limb_paths(sp, rng)
    A, clumps = attraction_points(sp, rng, paths)
    alive = np.ones(len(A), bool)
    # trunk: straight-ish nodes up to trunk_h with the lean
    nodes = [np.zeros(3)]
    parent = [-1]
    n_tr = int(sp.trunk_h / sp.step)
    for i in range(1, n_tr + 1):
        z = i * sp.step
        p = np.array([sp.lean[0] * z * z / 2 + rng.normal(0, 0.01), sp.lean[1] * z * z / 2 + rng.normal(0, 0.01), z])
        nodes.append(p); parent.append(i - 1)
    fork = len(nodes) - 1
    for P, w in paths:
        prev = fork
        for p in P[1:]:
            nodes.append(p); parent.append(prev); prev = len(nodes) - 1
    N = np.array(nodes)
    for it in range(400):
        if alive.sum() == 0:
            break
        P = A[alive]
        d = np.linalg.norm(P[:, None] - N[None], axis=-1)        # (points, nodes)
        nearest = d.argmin(1)
        dmin = d.min(1)
        infl = dmin < sp.infl
        grew = False
        new = []
        for ni in np.unique(nearest[infl]):
            sel = infl & (nearest == ni)
            v = (P[sel] - N[ni])
            v = (v / np.linalg.norm(v, axis=1, keepdims=True)).sum(0)
            v = v / (np.linalg.norm(v) + 1e-9)
            v = v + np.array([0, 0, 0.15]) + rng.normal(0, 0.12, 3)          # tropism up + wobble
            v /= np.linalg.norm(v)
            new.append((N[ni] + v * sp.step, ni))
        if not new:
            # no node within reach: extend the trunk top toward the crown centre
            top = len(N) - 1 if it == 0 else int(np.argmax(N[:, 2]))
            v = np.array([0, 0, 1.0])
            new.append((N[top] + v * sp.step, top))
        for p, pi in new:
            nodes.append(p); parent.append(pi)
            grew = True
        N = np.array(nodes)
        # kill reached points
        d2 = np.linalg.norm(A[:, None] - N[None, -len(new):], axis=-1).min(1)
        alive &= d2 > sp.kill
        if not grew:
            break
    parent = np.array(parent)
    # radii by pipe model from the tips down
    n = len(N)
    children = [[] for _ in range(n)]
    for i in range(1, n):
        children[parent[i]].append(i)
    r = np.zeros(n)
    tip_r = 0.007
    order = np.argsort(-np.arange(n))         # nodes were appended in growth order: children after parents
    for i in order:
        if not children[i]:
            r[i] = tip_r
        else:
            r[i] = sum(r[c] ** 2.5 for c in children[i]) ** (1 / 2.5)
    r *= sp.trunk_r / max(r[0], 1e-6)
    r = np.maximum(r, tip_r)
    # droop (weeping): bend the outer, thin parts down by a sag that grows with distance from the branch base
    if sp.droop > 0:
        depth = np.zeros(n)
        for i in range(1, n):
            depth[i] = depth[parent[i]] + 1
        thin = np.clip(1 - r / (sp.trunk_r * 0.25), 0, 1)
        sag = np.zeros(n)
        for i in range(1, n):
            sag[i] = sag[parent[i]] + sp.droop * 0.11 * sp.step * thin[i] * max(depth[i] - n_tr, 0) ** 0.75
        N = N.copy(); N[:, 2] -= sag
    if getattr(sp, 'pendant', 0) > 0:
        # weeping: from every tip hang a strand that arcs out a little and then falls (catenary-ish), 2-4 m
        nodes_l = list(N); par_l = list(parent); r_l = list(r)
        for t in [i for i in range(n) if not children[i]]:
            L = sp.pendant * rng.uniform(0.6, 1.25)
            d0 = N[t] - N[parent[t]]; d0[2] = 0; d0 /= np.linalg.norm(d0) + 1e-9
            prev = t; p = N[t].copy(); v = d0 * 0.5 + np.array([0, 0, 0.3])
            for k in range(int(L / 0.25)):
                v = v + np.array([0, 0, -0.35]) + rng.normal(0, 0.05, 3)
                v /= np.linalg.norm(v)
                p = p + v * 0.25
                nodes_l.append(p.copy()); par_l.append(prev); r_l.append(0.006); prev = len(nodes_l) - 1
        N = np.array(nodes_l); parent = np.array(par_l); r = np.array(r_l); n = len(N)
        children = [[] for _ in range(n)]
        for i in range(1, n):
            children[parent[i]].append(i)
    tips = np.array([i for i in range(n) if not children[i]])
    return dict(N=N, parent=parent, r=r, tips=tips, children=children, clumps=clumps)


def leaf_cards(sk, sp, rng=None):
    """Return (centres, normals, ups, sizes) of the leaf-cluster cards: a few per tip + some along thin twigs."""
    rng = rng or np.random.default_rng(sp.seed + 99)
    N, par, r = sk['N'], sk['parent'], sk['r']
    C, Nn, U, S = [], [], [], []
    if getattr(sp, 'pendant', 0) > 0:
        cand = [i for i in range(len(N)) if r[i] <= 0.0061 and rng.uniform() < 0.5]
    else:
        cand = list(sk['tips']) + [i for i in range(len(N)) if r[i] < 0.03 and rng.uniform() < 0.15]
    ctr = np.mean([c for c, r in sk['clumps']], axis=0) - np.array([0, 0, 1.0])
    for i in cand:
        base = N[i]
        out = base - ctr; out[2] *= 0.5; out /= np.linalg.norm(out) + 1e-9
        for k in range(sp.leaf_per_tip):
            c = base + rng.normal(0, sp.leaf_size * 0.35, 3)
            nrm = out + np.array([0, 0, 0.6]) + rng.normal(0, 0.6, 3); nrm /= np.linalg.norm(nrm)
            up = np.cross(nrm, rng.normal(0, 1, 3)); up /= np.linalg.norm(up)
            if getattr(sp, 'pendant', 0) > 0:              # weeping: the card hangs from its twig
                d = np.array([0, 0, -1.0]) + rng.normal(0, 0.25, 3)
                up = d - np.dot(d, nrm) * nrm; up /= np.linalg.norm(up) + 1e-9
            C.append(c); Nn.append(nrm); U.append(up); S.append(sp.leaf_size * rng.uniform(0.75, 1.25))
    return np.array(C), np.array(Nn), np.array(U), np.array(S)


# ---------------------------------------------------------------------------------------------- the sample tree (D-44 #6)
import copy as _copy


def variant(base, seed, scale, lean, rot_deg, n_pts=None):
    sp = _copy.deepcopy(SPECIES[base])
    sp.seed = seed; sp.scale = scale; sp.lean = lean
    sp.trunk_h0 = sp.trunk_h
    sp.trunk_r = sp.trunk_r * scale ** 0.8
    sp.limbs = [(az + rot_deg, el, L, w) for az, el, L, w in sp.limbs]
    if n_pts:
        sp.n_pts = n_pts
    sp.n_pts = int(sp.n_pts * scale ** 1.5)
    return sp


VARIANTS = {   # A main (3 variants, 10-13 m, different seeds / lean / crown bias), B accent (paddy side only)
    'Tree_A1': lambda: variant('A_old_broadleaf', 4, 1.30, (0.05, 0.01), 0),
    'Tree_A2': lambda: variant('A_old_broadleaf', 21, 1.45, (-0.03, 0.04), 115),
    'Tree_A3': lambda: variant('A_old_broadleaf', 37, 1.52, (0.02, -0.05), 230),
    'Tree_B1': lambda: variant('B_weeping', 7, 1.25, (-0.05, 0.02), 0),
}


def clump_cards(sk, sp, lod, rng=None):
    """Leaf-cluster cards placed by the crown clumps (not by every twig): the crown reads as masses with sky between,
    and the cards are big enough not to fizz at a distance (director note 2). Returns (centres, normals, ups, sizes, cell).
    LOD0: ~1.3 m cards, atlas cells 0-2; LOD1: ~2.6 m 'clump' cards, cell 3, about a fifth as many."""
    rng = rng or np.random.default_rng(sp.seed * 7 + lod)
    clumps = sk['clumps']
    sc = getattr(sp, 'scale', 1.0)
    size = (1.25 if lod == 0 else 2.5) * (0.9 + 0.1 * sc)
    dens = 1.0 / (0.50 if lod == 0 else 2.8)       # cards per m^3 of clump
    ctr_all = np.mean([c for c, r in clumps], axis=0) - np.array([0, 0, 1.5])
    C, Nn, U, S, cell = [], [], [], [], []
    weeping = getattr(sp, 'pendant', 0) > 0
    for c, r in clumps:
        vol = 4 / 3 * math.pi * r[0] * r[1] * r[2]
        n = max(3, int(vol * dens))
        for k in range(n):
            d = rng.normal(0, 1, 3); d /= np.linalg.norm(d)
            rad = rng.uniform(0, 1) ** 0.35                 # biased to the shell
            p = c + d * r * rad
            out = p - ctr_all; out[2] *= 0.6; out /= np.linalg.norm(out) + 1e-9
            nrm = out * 0.8 + d * 0.6 + np.array([0, 0, 0.5]) + rng.normal(0, 0.35, 3); nrm /= np.linalg.norm(nrm)
            up = np.cross(nrm, rng.normal(0, 1, 3)); up /= np.linalg.norm(up)
            C.append(p - up * size * 0.5); Nn.append(nrm); U.append(up); S.append(size * rng.uniform(0.8, 1.2))
            cell.append(3 if lod > 0 else int(rng.integers(0, 3)))
    if weeping:
        # the curtain: cards hanging along the pendant strands
        N, r = sk['N'], sk['r']
        idx = [i for i in range(len(N)) if r[i] <= 0.0061]
        step = 2 if lod == 0 else 9
        for i in idx[::step]:
            nrm = rng.normal(0, 1, 3); nrm[2] *= 0.2; nrm /= np.linalg.norm(nrm)
            dn = np.array([0, 0, -1.0]) + rng.normal(0, 0.2, 3)
            up = -(dn - np.dot(dn, nrm) * nrm); up /= np.linalg.norm(up)       # the card's up = toward the strand
            s = (0.8 if lod == 0 else 1.8)
            C.append(N[i] - up * s); Nn.append(nrm); U.append(up); S.append(s)          # top edge at the strand
            cell.append(2 if lod == 0 else 3)
    return np.array(C), np.array(Nn), np.array(U), np.array(S), np.array(cell)
