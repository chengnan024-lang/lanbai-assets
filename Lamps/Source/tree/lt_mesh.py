# -*- coding: utf-8 -*-
"""Skeleton + leaf cards -> mesh arrays (numpy). Branches: a ring of `sides` vertices per node, quads to the parent
ring (shared rings along a branch, so the trunk is one smooth tube). Leaves: quads, UV in one of the 2x2 atlas cells.
Vertex colour (for the Unity wind): R = branch flexibility (0 trunk .. 1 twig tip), G = random phase, B = leaf flag."""
import math

import numpy as np


def branches(sk, sides=6, min_r=0.0, sides_by_r=None):
    N, par, r = sk['N'], sk['parent'], sk['r']
    n = len(N)
    children = sk['children']
    # direction at each node
    D = np.zeros((n, 3))
    for i in range(n):
        if par[i] >= 0:
            D[i] = N[i] - N[par[i]]
        elif children[i]:
            D[i] = N[children[i][0]] - N[i]
        D[i] /= np.linalg.norm(D[i]) + 1e-9
    V, F, UV, COL = [], [], [], []
    ring_of = {}
    rmax = r.max()
    rng = np.random.default_rng(1)
    phase = rng.uniform(0, 1, n)

    def ring(i, k):
        key = (i, k)
        if key in ring_of:
            return ring_of[key]
        d = D[i]
        a = np.cross(d, [0, 0, 1.0]) if abs(d[2]) < 0.95 else np.cross(d, [1.0, 0, 0])
        a /= np.linalg.norm(a); b = np.cross(d, a)
        ids = []
        flex = 1 - (r[i] / rmax) ** 0.5
        for s in range(k + 1):
            t = 2 * math.pi * s / k
            V.append(N[i] + r[i] * (math.cos(t) * a + math.sin(t) * b))
            UV.append((s / k * max(1, round(r[i] * 2 * math.pi / 0.6 * 2)) / 2, N[i][2] / 2.0))
            COL.append((flex, phase[i], 0.0))
            ids.append(len(V) - 1)
        ring_of[key] = ids
        return ids

    # simplify chains: keep roots, forks, tips and a node every `seglen(r)` metres of path; edges join kept nodes
    keep = np.zeros(n, bool); keep[0] = True
    acc = np.zeros(n)
    kept_parent = np.full(n, -1)
    for i in range(1, n):
        p = par[i]
        acc[i] = acc[p] + np.linalg.norm(N[i] - N[p])
        seglen = 0.3 if r[i] > 0.12 else (0.6 if r[i] > 0.04 else 1.1)
        last = p if keep[p] else kept_parent[p]
        kept_parent[i] = last
        if len(children[i]) != 1 or (acc[i] - acc[last]) >= seglen:
            keep[i] = True
    for i in range(1, n):
        if not keep[i] or r[i] < min_r:
            continue
        p = kept_parent[i]
        k = sides if sides_by_r is None else sides_by_r(r[i])
        a = ring(p, k); b = ring(i, k)
        for s in range(k):
            F.append((a[s], a[s + 1], b[s + 1], b[s]))
    return np.array(V), F, np.array(UV), np.array(COL)


def leaves(cards, rng=None, aspect=1.0):
    """cards = (centres, normals, ups, sizes[, atlas cells]). The card's bottom edge sits at the centre point and it
    extends `size` along `up` (so a card grows out of its twig)."""
    C, Nn, U, S = cards[:4]
    cells = cards[4] if len(cards) > 4 else None
    rng = rng or np.random.default_rng(2)
    V, F, UV, COL = [], [], [], []
    for j, (c, nrm, up, s) in enumerate(zip(C, Nn, U, S)):
        rt = np.cross(up, nrm)
        cell = int(cells[j]) if cells is not None else int(rng.integers(0, 4))
        u0, v0 = (cell % 2) * 0.5, 1 - (cell // 2 + 1) * 0.5
        flip = rng.uniform() < 0.5
        base = len(V)
        # the card's bottom edge (where the twig enters) sits near the branch: shift the card outward by half its size
        cc = c + up * s * 0.5
        for (sx, sy) in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
            V.append(cc + rt * sx * s * 0.5 * aspect + up * sy * s * 0.5)
            uu = (sx * (-1 if flip else 1) + 1) / 2
            UV.append((u0 + 0.5 * uu, v0 + 0.5 * (sy + 1) / 2))
            COL.append((1.0, rng.uniform(), 1.0))
        F.append((base, base + 1, base + 2, base + 3))
    return np.array(V), F, np.array(UV), np.array(COL)
