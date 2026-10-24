"""Numerical proof that LanbaiHorizon (Common/Shaders/LanbaiSky.cginc) equals the gate's LanbaiBand
(Gate/Shaders/LanbaiGateSky.cginc) in act 4. Both files are compiled by slang for the CPU (the files as they are in
the repo; only the material uniforms become constants = Lanbai_GateAirSky v3 defaults) and evaluated on 20 000
directions x 4 eye positions x 2 cases: (a) the gate defaults (only the band-colour flag set), (b) the gate driver's
band globals set. Usage: ~/bpy/bin/python -I check_gate_equivalence.py"""
import re, sys
import os
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from slang_cpu import run, read, stub, strip_includes

gate = read('Gate/Shaders/LanbaiGateSky.cginc')
DEF = {'_HazeNear': '(0.1085, 0.1130, 0.1641, 1)', '_HazeFar': '(0.0436, 0.0504, 0.0726, 1)', '_Void': '(0.0021, 0.0030, 0.0070, 1)',
       '_BandAz': '(50, 60, 0, 0)', '_BandEl': '(6, 22, 2, 0)', '_BelowHorizon': '(-25, 0, 0.55, 0)', '_TearPos': '(0, 297, 1800, 0)'}
for k, v in DEF.items():
    gate = re.sub(r'float4\s+%s;' % k, 'static const float4 %s = float4%s;' % (k, v), gate)
gate = gate.replace('half   _BelowDesat;', 'static const half _BelowDesat = 0.6;').replace('half   _BackBand;', 'static const half _BackBand = 0.55;')
for g in ('_Udon_FogBandDir', '_Udon_FogBandColor', '_Udon_TearPos', '_Udon_TearH', '_Udon_MoonDir', '_Udon_MoonDisc'):
    gate = re.sub(r'float4\s+%s;' % g, 'static float4 %s = float4(0, 0, 0, 0);' % g, gate)
gate = re.sub(r'float\s+_Udon_FogBandWidth;', 'static float _Udon_FogBandWidth = 0;', gate)
prelude = stub() + strip_includes(read('Common/Shaders/LanbaiVR.cginc')) + gate + strip_includes(read('Common/Shaders/LanbaiSky.cginc'))
body = r'''
 _WorldSpaceCameraPos = CAM[id]; _Udon_FogBandDir = BDIR[id]; _Udon_FogBandColor = BCOL[id]; _Udon_FogBandWidth = BW[id];
 GATE[id] = LanbaiBand(V[id]);
 if (_Udon_FogBandColor.a <= 0.0) _Udon_FogBandColor = float4(0.1085, 0.1130, 0.1641, 1.0);   // the act-4 flag
 HOR[id] = LanbaiHorizon(V[id]);
'''
rng = np.random.default_rng(1)
N = 20000
V = rng.normal(size=(N, 3)); V /= np.linalg.norm(V, axis=1, keepdims=True)
V[:5000, 1] = rng.uniform(-0.2, 0.45, 5000); V[:5000] /= np.linalg.norm(V[:5000], axis=1, keepdims=True)   # dense near the horizon
worst = 0.0
for cam in ([0.55, 1.70, 2.05], [0.0, 92.0, -1440.0], [3, 1.2, 9], [-2, 1.7, 0.2]):
    for bdir, bcol, bw in (((0, 0, 0, 0), (0, 0, 0, 0), 0.0), ((0.2, 0.0, 1.0, 0), (0.12, 0.11, 0.17, 1), 42.0)):
        ins = {'V': V, 'CAM': np.tile(cam, (N, 1)), 'BDIR': np.tile(bdir, (N, 1)), 'BCOL': np.tile(bcol, (N, 1)), 'BW': np.full((N, 1), bw)}
        r = run(prelude, body, N, {k: np.asarray(v, np.float32) for k, v in ins.items()}, {'GATE': 3, 'HOR': 3}, 'equiv')
        a, b = r['GATE'], r['HOR']
        d = np.abs(a - b).max()
        worst = max(worst, d)
        print('eye %-22s band globals %-24s max |diff| %.2e  (colour %.4f..%.4f)' % (cam, 'set' if bcol[3] else 'unset (defaults)', d, a.min(), a.max()))
print('WORST %.2e -> %s' % (worst, 'EQUAL (float rounding only)' if worst < 1e-6 else 'DIFFERENT'))
sys.exit(0 if worst < 1e-6 else 1)
