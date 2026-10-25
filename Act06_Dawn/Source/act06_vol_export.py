# -*- coding: utf-8 -*-
"""第 6 幕体积云的数据（给搭建器和驱动）：act06_vol.py 的场景 -> Act06_Dawn/Act06_Volume.json（单一来源，别手改）。
  material：Lanbai/CloudVolume 的各项（层 A / B、颜色、相函数、阴影）
  towers / blobs：云塔的球（搭建器用 Material.SetVectorArray 写进 _TowerBox / _Blobs）
  puffs：漂过车的三团（_Puff / _PuffWind）
  open：谷（A）和下层（B）散开的时间（驱动写 _CovOpen）
  sun_table：从主座位沿太阳方向在体积里步进出的透过率，每 0.25 s（驱动按它写主光，再平滑 2.2 s；取代旧云原的 sun_table）
  coverage：Textures/Act06_CloudCoverage.png 的范围（act06_cov_bake.py）"""
import os
import sys
import json
import math
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import act06_vol as AV  # noqa: E402


def r(v, n=4):
    return [round(float(x), n) for x in v]


def main():
    S = AV.scene()
    sc = S.scene
    A = [l for l in S.layers if l.name == 'A'][0]
    B = [l for l in S.layers if l.name == 'B'][0]
    g = AV.GEO
    mat = dict(
        _A_Y=[A.y0, A.y1, A.sigma, A.scale], _A_Shape=[A.erode, A.hvar, A.soft_pow, A.base_soft], _A_Wind=r(A.wind) + [0],
        _B_Y=[B.y0, B.y1, B.sigma, B.scale], _B_Shape=[B.erode, B.hvar, B.soft_pow, B.base_soft], _B_Wind=r(B.wind) + [0],
        _B_Strato=1.0 if B.kind == 'strato' else 0.0,
        _SunColor=r(sc.sun_col) + [0], _SkyColor=r(sc.sky_col) + [0], _GndColor=r(sc.gnd_col) + [0],
        _Phase=list(sc.phase) + [sc.ms], _Shadow=[sc.cast_k, sc.ao_k, 150.0, 0.0],
        _SunDirFallback=r(sc.sun) + [0], _SeaY=float(AV.SEA_Y), _CovExtent=24000.0,
        _NoiseLo=r(sc.vol.lo) + [0], _NoiseHi=r(sc.vol.hi) + [1],
        _MaxSteps=96.0, _StepK=0.015, _MaxDist=60000.0, _NearClear=[2.0, 18.0, 0.0, 0.0])
    # towers: the blob lists act06_vol built (rebuilt here the same way: deterministic seeds)
    towers, blobs = [], []
    for k_t, tw in enumerate(g['T']):
        a = math.radians(tw['az'])
        tx, tz = tw['r'] * math.sin(a), tw['r'] * math.cos(a)
        towers.append([round(tx, 1), round(tz, 1), round(tw['rad'] * 1.4, 1), g['A']['y0']])
    for (tx, tz, R, sph) in S.tower_blobs:
        lst = [r(s_, 1) for s_ in sph][:40]
        lst += [[0, 0, 0, 0]] * (40 - len(lst))
        blobs += lst
    puffs, pw = [], []
    for (t_c, wind, rad, thick) in g['P']:
        d_c, _ = AV.AL.descent(t_c)
        puffs.append([t_c, round(AV.A6.EYE[1] - d_c, 1), rad, thick])
        pw.append(list(wind) + [0.0])
    # the sun from the main seat through the volume, every 0.25 s (the driver smooths it over 2.2 s)
    sc.step_k = 0.01
    t0, dt = 248.64, 0.25
    ts = np.arange(t0, 363.62 + 1e-6, dt)
    tab = []
    for t in ts:
        dd, _ = AV.AL.descent(float(t))
        eye = np.array([AV.A6.EYE[0], AV.A6.EYE[1] - dd, AV.A6.EYE[2]])
        _, T, _ = sc.march(eye, sc.sun[None], float(t), max_d=40000.0, steps_max=600)
        tab.append(round(float(T[0]), 3))
    out = dict(
        about='第 6 幕体积云（D-44 #2）：Source/act06_vol_export.py 生成，别手改。层的高度是 layout 坐标（F0 的眼高 = 0，R_Dawn 上移 d(t)）',
        material=mat, towers=towers, blobs=blobs, puffs=puffs, puff_wind=pw,
        open=dict(A=g['A']['valley']['open'], B=g['B']['open']),
        under_fog_k=AV.UNDER_FOG_K, fog_under_density=LAYOUT_FOG_BASE(),
        tower_answer=[[266.36, 4.0, 0.7], [267.86, 4.0, 0.7], [269.36, 4.0, 0.7]],
        sun_table=dict(t0=t0, dt=dt, v=tab, note='transmittance from the main seat along the sun (act06_vol march)'),
        coverage=dict(png='Textures/Act06_CloudCoverage.png', extent_m=24000.0),
        density=dict(bytes='Clouds_v2/Volume/Textures/CloudVolume128.bytes', size=128, order='[z][y][x] RGBA8'))
    json.dump(out, open(os.path.join(AV.KIT, 'Act06_Volume.json'), 'w'), indent=1, ensure_ascii=False)
    hidden = [float(t) for t, v in zip(ts, tab) if v < 0.5]
    print('ok; sun hidden from %.2f to %.2f' % (min(hidden), max(hidden)) if hidden else 'ok; never hidden')


def LAYOUT_FOG_BASE():
    return AV.LAYOUT['beats']['fog_under_cover']['base']


if __name__ == '__main__':
    main()
