# -*- coding: utf-8 -*-
"""蓝白 · 共用体积云的参考光线步进（numpy）。是以后 `Lanbai/CloudVolume` shader 的数学（README_Volume §3），一幕一个“场景”：
一组水平的云层（底、顶、二维覆盖率、高度剖面、噪声尺度、风），可以再加几根云塔。每层的密度：
    cov  = 层的覆盖率(x, z, t)                     （二维，便宜；空的地方整段跳过）
    prof = 高度剖面(h, cov)                         （积云：底平、顶随覆盖率高低不一）
    base = remap(R(p / scale + 风 t) · prof, 1 − cov, 1)
    dens = remap(base, G(p / (scale / 4) + 风 t · 1.6) · 侵蚀, 1)  · σ
光：日光透过率（朝太阳 3 个样本）× 双瓣 HG + 天光（按层内高度在地光和天光之间）+ 一点多次散射的提亮；
雾按样本到眼的距离混进雾色（和 LanbaiFog 同一条：1 − exp(−k d)）。
起点：阿白的 VolumeCloudDeck（FromLocal/full_preview/20261025-0103/review_sources/，2026-10-25）：128³ 周期密度、
风跟时钟走、密度 × 层包络、朝光两个样本。这里拆成通用的层，往上看、往下看、在云里面都能用。"""
import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722])


def ss(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


class Volume:
    def __init__(self, path):
        v = np.load(path).astype(np.float32)          # [z, y, x, 3]
        self.v = v
        self.n = v.shape[0]

    def sample(self, p, ch):
        """trilinear, periodic; p (M, 3) in texels (x, y, z)"""
        n = self.n
        f = np.floor(p)
        i = f.astype(np.int64) % n
        w = (p - f).astype(np.float32)
        x0, y0, z0 = i[:, 0], i[:, 1], i[:, 2]
        x1, y1, z1 = (x0 + 1) % n, (y0 + 1) % n, (z0 + 1) % n
        V = self.v[..., ch]
        wx, wy, wz = w[:, 0], w[:, 1], w[:, 2]
        c00 = V[z0, y0, x0] * (1 - wx) + V[z0, y0, x1] * wx
        c01 = V[z0, y1, x0] * (1 - wx) + V[z0, y1, x1] * wx
        c10 = V[z1, y0, x0] * (1 - wx) + V[z1, y0, x1] * wx
        c11 = V[z1, y1, x0] * (1 - wx) + V[z1, y1, x1] * wx
        return (c00 * (1 - wy) + c01 * wy) * (1 - wz) + (c10 * (1 - wy) + c11 * wy) * wz


class Layer:
    """y0 base, y1 top (world m); cov(x, z, t) -> 0..1; scale = metres per volume period (R); kind 'cumulus' | 'strato'"""
    def __init__(self, name, y0, y1, cov, scale=2400.0, wind=(5.0, 0.0, 2.0), sigma=0.045, kind='cumulus', erode=0.35,
                 base_soft=0.06, soft_pow=1.0, hvar=0.0):
        self.soft_pow = soft_pow                       # > 1: density rounds off near the threshold (no flat-topped blocks)
        self.hvar = hvar                               # base / top heights wander (fraction of the layer): no ruler-straight
                                                       # base and top lines on a thin layer seen from the side
        self.name, self.y0, self.y1, self.cov, self.scale = name, y0, y1, cov, scale
        self.wind, self.sigma, self.kind, self.erode, self.base_soft = np.array(wind, float), sigma, kind, erode, base_soft

    def profile(self, h, c):
        if self.kind == 'strato':
            return ss(0.0, 0.25, h) * (1 - ss(0.6, 1.0, h))
        top = 0.35 + 0.65 * c                          # heads reach higher where the coverage is higher
        return ss(0.0, self.base_soft, h) * (1 - ss(top * 0.6, top, h))


class Scene:
    def __init__(self, vol, layers, sun_dir, sun_col, sky_col, gnd_col, fog_fn=None, phase=(0.6, -0.25, 0.7),
                 amb_k=1.0, ms=0.25):
        self.vol, self.layers = vol, layers
        self.sun = np.asarray(sun_dir, float) / np.linalg.norm(sun_dir)
        self.sun_col, self.sky_col, self.gnd_col = map(lambda a: np.asarray(a, float), (sun_col, sky_col, gnd_col))
        self.fog_fn, self.phase, self.amb_k, self.ms = fog_fn, phase, amb_k, ms
        self.step_k, self.step_min, self.step_max = 0.015, 10.0, 450.0
        self.ymin = min(l.y0 for l in layers)
        self.ymax = max(l.y1 for l in layers)

    def density(self, P, t, detail=True):
        """P (M, 3) world -> (sigma (M,), h01 (M,)) summed over the layers (h of the densest one)"""
        M = len(P)
        sig = np.zeros(M, np.float32)
        hh = np.zeros(M, np.float32)
        for L in self.layers:
            inside = (P[:, 1] >= L.y0) & (P[:, 1] <= L.y1)
            if not inside.any():
                continue
            idx = np.nonzero(inside)[0]
            Q = P[idx]
            c = L.cov(Q[:, 0], Q[:, 2], t)
            keep = c > 0.01
            if not keep.any():
                continue
            idx, Q, c = idx[keep], Q[keep], c[keep]
            h = (Q[:, 1] - L.y0) / (L.y1 - L.y0)
            k = self.vol.n / L.scale
            if L.hvar:
                pv = np.stack([Q[:, 0] * k * 0.35, np.full(len(Q), 40.0, np.float32), Q[:, 2] * k * 0.35], -1)
                h = h + L.hvar * 2 * (self.vol.sample(pv, 0) - 0.67) / 0.24
            prof = L.profile(np.clip(h, 0, 1), c) * ((h >= 0) & (h <= 1))
            q = (Q - L.wind[None] * t) * k
            n0 = self.vol.sample(q[:, [0, 1, 2]], 0)
            base = np.clip((n0 * prof - (1 - c)) / np.maximum(c, 1e-3), 0, 1)
            if detail:
                q2 = (Q - L.wind[None] * t * 1.6) * (k * 4.0)
                g = self.vol.sample(q2, 1)
                er = L.erode * (0.35 + 0.65 * (1 - h))          # wispy at the base, crisp at the heads
                base = np.clip((base - g * er) / np.maximum(1 - g * er, 1e-3), 0, 1)
            s = (base ** L.soft_pow if L.soft_pow != 1.0 else base) * L.sigma
            better = s > sig[idx]
            hh[idx[better]] = h[better]
            sig[idx] += s
        return sig, hh

    def sun_T(self, P, t):
        tau = np.zeros(len(P), np.float32)
        for dd, w in ((25.0, 25.0), (80.0, 60.0), (220.0, 160.0), (600.0, 450.0)):
            s, _ = self.density(P + self.sun[None] * dd, t, detail=False)
            tau += s * w
        return np.exp(-tau)

    def hg(self, cos, g):
        return (1 - g * g) / (4 * np.pi * (1 + g * g - 2 * g * cos) ** 1.5)

    def march(self, eye, V, t, max_d=60000.0, depth=None, near=0.5, steps_max=1400):
        """eye (3,), V (N, 3) unit. Returns (L premultiplied (N, 3), T (N,), first-hit distance (N,))"""
        N = len(V)
        eye = np.asarray(eye, float)
        vy = V[:, 1]
        with np.errstate(divide='ignore', invalid='ignore'):
            ta = (self.ymin - eye[1]) / vy
            tb = (self.ymax - eye[1]) / vy
        t0 = np.where(np.abs(vy) < 1e-6, np.where((eye[1] >= self.ymin) & (eye[1] <= self.ymax), 0.0, np.inf), np.minimum(ta, tb))
        t1 = np.where(np.abs(vy) < 1e-6, np.where((eye[1] >= self.ymin) & (eye[1] <= self.ymax), max_d, -np.inf), np.maximum(ta, tb))
        t0 = np.maximum(t0, near)
        t1 = np.minimum(t1, max_d)
        if depth is not None:
            t1 = np.minimum(t1, depth)
        Lo = np.zeros((N, 3), np.float64)
        T = np.ones(N, np.float64)
        first = np.full(N, np.inf)
        cur = t0.copy()
        rng = np.random.default_rng(7)
        cur += rng.random(N) * np.clip(cur * 0.01, 4, 60)
        act = np.nonzero(cur < t1)[0]
        cosv = V @ self.sun
        ph = self.phase[2] * self.hg(cosv, self.phase[0]) + (1 - self.phase[2]) * self.hg(cosv, self.phase[1])
        it = 0
        while len(act) and it < steps_max:
            it += 1
            d = cur[act]
            dt = np.clip(d * self.step_k, self.step_min, self.step_max)
            P = eye[None] + V[act] * (d + 0.5 * dt)[:, None]
            sig, h = self.density(P, t)
            hit = sig > 1e-5
            if hit.any():
                ia = act[hit]
                s = sig[hit].astype(np.float64)
                dts = dt[hit]
                Ph = P[hit]
                Ts = self.sun_T(Ph, t)
                amb = self.gnd_col[None] * (1 - h[hit])[:, None] + self.sky_col[None] * h[hit][:, None]
                ms = 1.0 + self.ms * (1 - np.exp(-s * 200.0))
                Lsrc = self.sun_col[None] * (Ts * ph[ia] * 4 * np.pi * ms)[:, None] * 0.25 + amb * self.amb_k
                if self.fog_fn is not None:
                    fc, fa = self.fog_fn(V[ia], d[hit])
                    Lsrc = Lsrc * (1 - fa)[:, None] + fc * fa[:, None]
                a = 1 - np.exp(-s * dts)
                Lo[ia] += (T[ia] * a)[:, None] * Lsrc
                T[ia] *= (1 - a)
                f = np.isinf(first[ia]) & (a > 0.02)
                first[ia[f]] = d[hit][f]
            cur[act] = d + dt
            act = act[(cur[act] < t1[act]) & (T[act] > 0.015)]
        return Lo, T, first
