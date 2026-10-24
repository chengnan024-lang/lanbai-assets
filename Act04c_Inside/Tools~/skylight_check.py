"""The skylight spot projection (bible §4.8, act 4 U8 -> U9) as the shader does it, checked against the gate's
GateLayout_v2.json skylight_spot.samples (corners_bus, 25 samples every 0.5 s).
core(t) = _Udon_TearPos + S * CORE_OFS,  S = H(t) / 1000  (the gate writes _Udon_TearPos = GateRoot + (0, -150 + 0.4 H, 0))
CORE_OFS = the tear kit's core point (tear_def: widest row, the path's across offset, 60 m behind the cloth) minus that
convention, in Unity axes. Prints the worst corner error and writes out/skylight_check.json."""
import json, os, sys
import numpy as np
from scipy.interpolate import PchipInterpolator
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Tear', 'Source'))
import tear_def as TD
G = json.load(open(os.path.join(REPO, 'Gate', 'GateLayout_v2.json')))
U6, U9 = 133.80, 179.55
VG = 2700.0 / (U9 - U6)
CLIMB = U9 - 19.05
kn = G['timeline']['tear_H_knots']
Hf = PchipInterpolator([k['t'] for k in kn], [k['H'] for k in kn])
ss = lambda x: np.clip(x, 0, 1) ** 2 * (3 - 2 * np.clip(x, 0, 1))
def h_bus(t):
    if t <= U6: return 40.0
    if t < CLIMB: return 40 + 20 * ss((t - U6) / (CLIMB - U6))
    return 60 + 90 * ss((t - CLIMB) / (U9 - CLIMB))
# kit core (x across +right, y depth +away, z up) at H = 1000
ck = TD.P(TD.T_W, float(TD.path(np.array([TD.T_W]))[0]), 60.0)[()]
CORE_OFS = np.array([ck[0], ck[2] - 400.0, ck[1]])          # Unity axes, relative to (0, 0.4 H, 0), x H/1000
SKY_C, SKY_HALF, CEIL_Y, FLOOR_Y = np.array([0.55, 2.45, 2.80]), 0.30, 2.45, 0.62
def corners(t):
    H = float(Hf(min(t, U9)))
    tearpos = np.array([0.0, 150.0 - h_bus(t) - 150.0 + 0.4 * H, VG * (U9 - t)])
    core = tearpos + CORE_OFS * H / 1000.0
    out = []
    for x, z in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
        p = np.array([SKY_C[0] + x * SKY_HALF, CEIL_Y + 0.1, SKY_C[2] + z * SKY_HALF])
        d = p - core
        d /= np.linalg.norm(d)
        k = (FLOOR_Y + 0.003 - p[1]) / d[1]
        out.append(p + d * k)
    return np.array(out)
worst = 0.0
rows = []
for s in G['skylight_spot']['samples']:
    c = corners(s['t'])
    e = float(np.abs(c - np.array(s['corners_bus'])).max())
    worst = max(worst, e)
    rows.append(dict(t=s['t'], err_m=round(e, 4)))
res = dict(core_offset_unity_per_1000=[round(float(v), 3) for v in CORE_OFS], worst_corner_error_m=round(worst, 4), samples=rows)
os.makedirs(os.path.join(HERE, 'out'), exist_ok=True)
json.dump(res, open(os.path.join(HERE, 'out', 'skylight_check.json'), 'w'), indent=1)
print('core offset', res['core_offset_unity_per_1000'], 'worst corner error %.4f m over %d samples' % (worst, len(rows)))
