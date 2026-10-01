"""Solve every tear-kit colour as a Unity fill under S4 (bible screen target -> linear value the shader gets).
Writes tear_fills.json. Bible-given fills are used as given (and re-checked); the rest are solved."""
import json, numpy as np
import grade as g

GIVEN = {   # name: (screen target, bible fill hex, EV)
    'Core':      ('#F5F2EC', '#FFEDD1', 1.84),
    'Fibre':     ('#E2E8F3', '#DFE6FF', 1.56),
    'Glow':      ('#C0B9E4', '#C6B4FF', 1.04),
    'Halo':      ('#5B57A1', '#8275D0', 0.0),
    'ShaftPair': ('#31335A', '#4C4A74', 0.0),
    'CloudGlow': ('#495270', '#696F8D', 0.0),
    'HazeNear':  ('#484D63', '#67697D', 0.0),
    'HazeFar':   ('#2A3041', '#424755', 0.0),
    'Void':      ('#070A14', '#0E1217', 0.0),
    'FogGlobal': ('#353B4F', '#505466', 0.0),
    'FarTearLine': ('#D2CEE4', '#E6D8FF', 1.08),
}
SOLVE = {   # name: screen target (solved here under S4)
    'FlapInner': '#3E3C66',
    'FlapOuterNear': '#141726',
    'FlapOuterFar': '#0C0E18',
    'MoonRim': '#A9C2FF',
    'MoonDisc': '#EAEEF4',
    'MoonHalo': '#5A6A88',
    'Cloth': '#0C0E18',
}
out = {}
for k, (scr, hx, ev) in GIVEN.items():
    x = g.fill(hx, ev)
    out[k] = dict(screen=scr, fill_hex=hx, fill_ev=round(ev, 2), linear=[round(float(v), 4) for v in x],
                  check=g.hexs(g.screen_of(x)), xT0=round(float(x.max() / g.T0_S4), 2), source='bible')
for k, scr in SOLVE.items():
    x = g.solve_fill(scr)
    hx, ev = g.fill_as_hdr(x)
    out[k] = dict(screen=scr, fill_hex=hx, fill_ev=round(ev, 2), linear=[round(float(v), 4) for v in x],
                  check=g.hexs(g.screen_of(x)), xT0=round(float(x.max() / g.T0_S4), 2), source='solved (S4, no bloom)')
# a single shaft beam: half of the two-beam overlap
out['ShaftBeam'] = dict(out['ShaftPair']); out['ShaftBeam']['linear'] = [round(v * 0.5, 4) for v in out['ShaftPair']['linear']]
out['ShaftBeam']['source'] = 'half of ShaftPair (two beams overlap = the bible target)'
out['ShaftBeam']['check'] = g.hexs(g.screen_of(np.array(out['ShaftBeam']['linear'])))
json.dump(out, open('tear_fills.json', 'w'), indent=1)
for k, v in out.items():
    print(f"{k:14s} screen {v['screen']}  fill {v['fill_hex']} @ +{v['fill_ev']:.2f}  lin {v['linear']}  -> {v['check']}  xT0 {v['xT0']}")
