# -*- coding: utf-8 -*-
"""第 6 幕云海重做（D-44 #2）的设计板渲染：体积云（Clouds_v2/Volume，共用；起点是阿白的 VolumeCloudDeck）。
只是设计板（总导演看过再动手）：几何、六个时刻从主座位看出去的样子、哪里有空隙。数值都是设计值，不是 shader 的输出。

坐标：Unity 世界、以 F0 时主座位所在的竖线为原点（x 右、z 前），y 以 F0 的眼高为 0；云层不动，车往下走 d(t)
（act06_layout.descent）；太阳方位 +30°、仰角 5.8°（D-12）。
层（README 设计板 §2）：
  A 上层云原：底 −1134、顶最高 −533；覆盖率高（看下去是连成一片的、有起伏的云原，不是一块板）；
    · 朝太阳的谷（取代原来 1 500 m 宽的长方形云峡）：中线在车的竖线旁边 300 m，宽 1.0–1.6 km、边是一团一团的，
      从车后 1.4 km 一直通到朝日 4.3 km，F1 → F1 + 6 s 里谷里的云团散开（不是墙升起来）；谷里留着稀的云团随风漂，
      车会穿进一两团再出来；
    · 朝日一侧（±40°）的边在 4.58 km（318.36 太阳从这条边下面出来）；别的方向一直铺到地平线（远处同一层、便宜的步进）。
  B 下层碎积云：底 −1950、顶 −1700（离海 655–905 m），覆盖率约 0.6，到 12 km 以外连成地平线；
    305 → 325 车下面那一块和朝日一侧散开，空隙一直开到海面。
  T 三座云塔：方位 −25°（7.5 km）、+75°（9 km）、+120°（10 km），从 A 层底长到眼高以上 1.2–1.5 km。
海面 −2604.59（F2h 落到 y = 1.0，见 Act06_Layout.sea）。"""
import os
import sys
import json
import math
import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
REPO = os.path.normpath(os.path.join(KIT, '..'))
sys.path.insert(0, HERE)
sys.path.insert(0, os.path.join(REPO, 'Clouds_v2', 'Volume', 'Source'))
import act06_ref as A6  # noqa: E402
import vol_ref as VR  # noqa: E402

C = A6.C
AL = A6.AL
PR = A6.PR
LAYOUT = A6.LAYOUT
VOL_NPY = os.environ.get('LB_VOL', '/tmp/lb/vol/CloudVolume128.npy')
SKY_HDR = os.environ.get('LB_SKY_DAWN', '/tmp/lb/sky2/sky_dawn_2048.hdr')

SUN_AZ, SUN_EL = 30.0, 5.8
S_AX = np.array([math.sin(math.radians(SUN_AZ)), math.cos(math.radians(SUN_AZ))])      # (x, z) toward the sun
C_AX = np.array([S_AX[1], -S_AX[0]])                                                     # across
SEA_Y = LAYOUT['sea']['level_local']
F1 = LAYOUT['labels']['F1']

# clearings are irregular "lakes" along the sun axis (a) with a meandering, domain-warped across coordinate (q): no straight
# edge, no rectangle, no pie slice (review of the board's first plan). The along-axis ends stay exact near the sun line
# (the sun's timing: hidden behind the valley's end wall from ~300.6, back under the bay's edge at 318.36).
GEO = dict(
    A=dict(y0=-1134.0, y1=-533.0, base=0.66,
           valley=dict(a=(-1400.0, 4200.0), hw=(650.0, 800.0), c_off=-300.0, warp=320.0, soft=260.0, inside=0.14, end_warp=220.0,
                       open=[F1, F1 + 6.0]),
           bay=dict(a=(4580.0, 23000.0), hw=(700.0, 6500.0), c_off=0.0, warp=800.0, soft=300.0)),
    B=dict(y0=-1950.0, y1=-1700.0, base=0.88, far_r=12000.0, open=[305.4, 325.0],
           column=dict(a=(-1300.0, 1300.0), hw=(1100.0, 1100.0), c_off=0.0, warp=380.0, soft=300.0, end_warp=500.0),
           bay=dict(a=(1500.0, 12500.0), hw=(900.0, 3600.0), c_off=0.0, warp=650.0, soft=350.0, end_warp=900.0)),
    T=[dict(az=-25.0, r=7500.0, rad=1300.0, top=1500.0), dict(az=75.0, r=9000.0, rad=1100.0, top=1200.0),
       dict(az=120.0, r=10000.0, rad=1000.0, top=1300.0)],
)


def ss(e0, e1, x):
    return VR.ss(e0, e1, x)


class Act06Scene:
    def __init__(self):
        self.vol = VR.Volume(VOL_NPY)
        g = GEO

        def n2(x, z, period, ch=2, off=0.0):
            k = self.vol.n / period
            th = (period * 0.0137 + off * 0.71) % (2 * math.pi)      # each octave rotated differently: no shared tiling grid
            xr, zr = x * math.cos(th) - z * math.sin(th), x * math.sin(th) + z * math.cos(th)
            p = np.stack([xr * k + off, np.full_like(x, 17.0 + off), zr * k], -1)
            lo, hi = NORM[ch]
            return np.clip((self.vol.sample(p, ch) - lo) / (hi - lo), 0, 1)     # each channel to ~0..1 (p10 .. p90)

        def lake(x, z, L, seed):
            """0..1 inside an irregular clearing: along a in L['a'], half width hw(a) (linear, x 0.7..1.3 noise), across q
            meandering and domain-warped"""
            a = x * S_AX[0] + z * S_AX[1]
            q = x * C_AX[0] + z * C_AX[1]
            a0, a1 = L['a']
            u = np.clip((a - a0) / (a1 - a0), 0, 1)
            hw = (L['hw'][0] + (L['hw'][1] - L['hw'][0]) * u) * (0.7 + 0.6 * n2(a, np.full_like(a, 7.0 * seed), 3000.0, 2, seed))
            mid = L['c_off'] + 0.5 * L['warp'] * 2 * (n2(a, np.full_like(a, 3.0 * seed), 6000.0, 0, seed + 5.0) - 0.5)
            qw = q + L['warp'] * 2 * (n2(x, z, 1400.0, 0, seed + 11.0) - 0.5)
            aw = a + L.get('end_warp', 0.0) * 2 * (n2(x, z, 2000.0, 2, seed + 17.0) - 0.5)
            ends = ss(a0 - L['soft'], a0, aw) * ss(a1, a1 - L['soft'] * 3, aw)
            return ss(hw, hw - L['soft'], np.abs(qw - mid)) * ends

        def covA(x, z, t):
            A = g['A']
            c = A['base'] + 0.36 * (n2(x, z, 9300.0, 0, 1.0) - 0.5) + 0.2 * (n2(x, z, 2270.0, 0, 3.0) - 0.6)
            v = A['valley']
            inside = lake(x, z, v, 1.0)
            op = float(ss(v['open'][0], v['open'][1], t))
            puffs = v['inside'] + 0.22 * (n2(x, z, 900.0, 0, 33.0) - 0.45)
            c = c * (1 - inside * op) + np.clip(puffs, 0, 1) * inside * op
            c = c * (1 - lake(x, z, A['bay'], 2.0))
            return np.clip(c, 0, 1)

        def covB(x, z, t):
            B = g['B']
            c = B['base'] + 0.5 * (n2(x, z, 2630.0, 0, 51.0) - 0.62) + 0.25 * (n2(x, z, 8700.0, 0, 61.0) - 0.5)
            op = float(ss(B['open'][0], B['open'][1], t))
            c = np.maximum(c, 0.97 * (1 - op))       # closed until 305.4: the sea first shows at 305.4 (bible §6·6)
            c = c * (1 - 0.92 * op * np.maximum(lake(x, z, B['column'], 3.0), lake(x, z, B['bay'], 4.0)))
            return np.clip(c, 0, 1)

        towers = []
        for tw in g['T']:
            a = math.radians(tw['az'])
            towers.append((tw['r'] * math.sin(a), tw['r'] * math.cos(a), tw['rad']))

        def covT(x, z, t):
            c = np.zeros_like(x)
            for (tx, tz, rad) in towers:
                d = np.hypot(x - tx, z - tz)
                c = np.maximum(c, ss(rad, rad * 0.35, d + 350.0 * (n2(x, z, 1200.0, 0, 81.0) - 0.5)))
            return c * 0.8              # never solid: the noise carves the heads (cauliflower, not a dome)

        top_t = max(tw['top'] for tw in g['T'])
        self.layers = [
            VR.Layer('A', g['A']['y0'], g['A']['y1'], covA, scale=1700.0, wind=(4.0, 0.0, 1.5), sigma=0.05, erode=0.5),
            VR.Layer('B', g['B']['y0'], g['B']['y1'], covB, scale=1800.0, wind=(3.0, 0.0, 2.5), sigma=0.04, kind='cumulus',
                     erode=0.42, base_soft=0.1),
            VR.Layer('T', g['A']['y0'], top_t, covT, scale=1500.0, wind=(2.0, 0.0, 1.0), sigma=0.05, erode=0.5,
                     base_soft=0.02),
        ]
        sun = np.array([S_AX[0] * math.cos(math.radians(SUN_EL)), math.sin(math.radians(SUN_EL)), S_AX[1] * math.cos(math.radians(SUN_EL))])
        col = A6.COL
        self.sky = C.read_hdr(SKY_HDR).astype(np.float64)
        self.fsky = PR.fog_sky(self.sky)
        self.scene = VR.Scene(self.vol, self.layers, sun, np.array(col['SunColor']) * SUN_K,
                              np.array(col['SkyUpColor']) * AMB_K, np.array(col['GroundColor']) * AMB_K * 1.6,
                              fog_fn=self.fog, amb_k=1.0, ms=0.3)

    def fog(self, V, dist):
        fc = PR.fog_colour(self.sky, V)
        fa = 1 - np.exp(-A6.FOG_D * dist)
        return fc, fa


SUN_K, AMB_K = 0.8, 0.3          # calibrated on the 282 frame: lit tops ~#F3D2B0, shade ~#8593AA (S6)
_SC = None
NORM = {0: (0.549, 0.791), 1: (0.331, 0.635), 2: (0.251, 0.711)}    # vol_density.py p10 / p90 per channel


def scene():
    global _SC
    if _SC is None:
        _SC = Act06Scene()
    return _SC


def render(t, cam_name='hero', w=640, out=None, tag='', look=None):
    S = scene()
    cam = dict(A6.CAMS[cam_name])
    if look:
        cam.update(look)
    V, hh, pix = A6.rays(cam, w)
    d, _ = AL.descent(t)
    A6.FOG_D = A6.fog_at(t)
    PR.FOG_K = A6.fog_colour_k(t)
    eye = np.array([A6.EYE[0], A6.EYE[1] - d, A6.EYE[2]])
    img = C.sample_equirect(S.sky, V, 0.0)
    # the sun disc (procedural, not fogged): visible only where the clouds let it through (T below)
    sun = S.scene.sun
    cs = V @ sun
    disc = cs > math.cos(math.radians(0.45))
    # the sea
    depth = np.full(len(V), np.inf)
    with np.errstate(divide='ignore', invalid='ignore'):
        ts = (SEA_Y - eye[1]) / V[:, 1]
    sea = (V[:, 1] < -1e-4) & (ts > 0)
    if sea.any():
        Vh = V[sea]
        R = Vh * np.array([1, -1, 1])
        cosi = np.clip(-Vh[:, 1], 0, 1)
        F = 0.02 + 0.98 * (1 - cosi) ** 5
        calm = A6.smooth01((t - LAYOUT['beats']['sea_calm_all']['t0']) / LAYOUT['beats']['sea_calm_all']['dur'])
        refl = C.sample_equirect(S.fsky, R, 0.0)
        P0 = eye[None] + Vh * ts[sea][:, None]
        Lr, Tr, _ = S.scene.march(P0[0] * 0 + np.array([0.0, SEA_Y + 2.0, 0.0]), R, t, max_d=25000.0, steps_max=90)
        refl = refl * Tr[:, None] + Lr
        water = np.array([0.0156, 0.0484, 0.0954])
        c = water[None] * (1 - F)[:, None] + refl * F[:, None] * (0.6 + 0.4 * calm)
        fc, fa = S.fog(Vh, ts[sea])
        img[sea] = c * (1 - fa)[:, None] + fc * fa[:, None]
        depth[sea] = ts[sea]
    Lc, Tc, first = S.scene.march(eye, V, t, max_d=60000.0, depth=depth)
    img = img * Tc[:, None] + Lc
    sun_vis = float(Tc[disc].mean()) if disc.any() else 0.0
    win = A6.window_mask(V)
    interior = C.hex_lin('#2A2C30') * (C.hex_lin('#98A4B8') * 0.5 + 0.6)
    img[~win] = interior * (0.35 + 0.65 * sun_vis)
    lin = img.reshape(hh, w, 3)
    codes = C.grade(lin, 'S6', bloom=True)
    L, hue, cc = C.hue_chroma(codes.reshape(-1, 3))
    m = dict(t=t, cam=cam_name, d=round(float(d), 1), eye_y=round(float(eye[1]), 1), APL=round(float((codes @ C.LUMA).mean()), 1),
             sun_visible=round(sun_vis, 3), purple_D21=round(float(((hue >= 285) & (hue <= 330) & (cc > 12)).mean()), 4),
             cloud_cover_px=round(float(((1 - Tc) > 0.5).mean()), 3), sea_px=round(float(((sea) & (Tc > 0.5) & win).mean()), 3))
    if out:
        os.makedirs(out, exist_ok=True)
        Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(os.path.join(out, f'{tag}{cam_name}_t{t:.1f}.png'))
        json.dump(m, open(os.path.join(out, f'{tag}{cam_name}_t{t:.1f}.json'), 'w'), indent=1)
    return codes, m


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument('--t', type=float, nargs='+', default=[282.0])
    ap.add_argument('--cam', nargs='+', default=['hero'])
    ap.add_argument('--w', type=int, default=640)
    ap.add_argument('--out', default='/tmp/lb/a6vol')
    a = ap.parse_args()
    for t in a.t:
        for c in a.cam:
            _, m = render(t, c, a.w, a.out)
            print(json.dumps(m), flush=True)
