# -*- coding: utf-8 -*-
"""Act 7 (F2h -> F9s + 0.5) motion of the bus relative to the sea world, bible v2.1 §6·7a / §6·7b / §6·7c.
The bus never moves (treadmill): these are the bus's displacements in the SEA frame; the driver moves R_Sea by the
negative. Every segment is 'velocity = v0 + dv * smoothstep((t - t0) / dur)', so position is the exact integral.

Labels come from FromLocal/cues.json when present; the v2.1 sub-labels that cues.json does not have yet fall back to
the bible §2.1 seconds (BIBLE_SUBLABELS). The C# driver carries the same table (LanbaiAct07Driver.cs) - keep in sync.
"""
import json
import os

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))

# bible v2.1 §2.1 (t, timeline seconds) for every label act 7 uses; cues.json wins where it has the label
BIBLE_LABELS = {
    'F2': 352.06, 'F2h': 363.26, 'F3': 367.21, 'F4': 446.01, 'F4p': 462.36, 'F3e': 474.36, 'F3e1': 506.36,
    'F3e2': 532.36, 'F3e3': 556.36, 'F3i': 558.86, 'F5': 644.96, 'F5p': 655.86, 'F5q': 675.36, 'F5r': 708.86,
    'F6': 735.56, 'F7': 748.26, 'F7e': 777.36, 'F7s': 796.86, 'F7p': 812.36, 'F8': 835.16, 'F8a': 848.86,
    'F8b': 877.96, 'F8c': 902.16, 'F8r': 921.66, 'F9s': 921.86, 'F9': 929.11,
}


def load_labels():
    lab = dict(BIBLE_LABELS)
    src = {k: 'bible' for k in lab}
    p = os.path.join(REPO, 'FromLocal', 'cues.json')
    if os.path.exists(p):
        d = json.load(open(p, encoding='utf-8'))
        for grp in ('F', 'F_sub'):
            for k, v in d.get(grp, {}).items():
                if k in lab:
                    lab[k] = float(v['t'])
                    src[k] = 'cues.json'
    return lab, src


L, LSRC = load_labels()
EXIT = L['F9s'] + 0.5          # 922.36 出海


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3.0 - 2.0 * x)


def ss_int(x):
    """integral of smoothstep from 0 to x (x in [0,1]) = x^3 - x^4/2; for x > 1: 0.5 + (x - 1)."""
    if x <= 0.0:
        return 0.0
    if x >= 1.0:
        return 0.5 + (x - 1.0)
    return x ** 3 - 0.5 * x ** 4


class Profile:
    """velocity(t) = v0 + sum dv_i * smoothstep((t - t0_i)/dur_i)  for t >= T0; position(T0) = 0."""

    def __init__(self, T0, v0, segs):
        self.T0, self.v0, self.segs = T0, v0, segs   # segs: (t0, dur, dv)

    def v(self, t):
        return self.v0 + sum(dv * smoothstep((t - t0) / dur) for t0, dur, dv in self.segs)

    def x(self, t):
        if t <= self.T0:
            return self.v0 * (t - self.T0)
        s = self.v0 * (t - self.T0)
        for t0, dur, dv in self.segs:
            s += dv * dur * ss_int((t - t0) / dur)
        return s

    def peak_acc(self):
        return max(1.5 * abs(dv) / dur for _, dur, dv in self.segs)


# ---- depth below the sea surface (m, positive down) of the BUS ORIGIN (road level, floor + 0.62 above it) ----------
# 7a §6·7a: 2 -> 0.15 m/s (10 s) at F2h; 0.15 -> 1.5 (10 s) at F3e; 1.5 -> 1.0 (12 s) at F3i;
# 7b §6·7b: 1.0 -> 0 over F5 -> 668.6; 7b-iv: 0 -> 1.5 (8 s) at F7s; 7c keeps 1.5 m/s to the exit.
SINK = Profile(L['F2h'], 2.0, [
    (L['F2h'], 10.0, -1.85),
    (L['F3e'], 10.0, +1.35),
    (L['F3i'], 12.0, -0.50),
    (L['F5'], 668.6 - L['F5'], -1.00),
    (L['F7s'], 8.0, +1.50),
])
# forward (bus heading +Z): 7b 0 -> 3.5 m/s over F5 -> F5 + 23; brake 3.5 -> 0 over F6 + 4.7 -> F7 (8 s)
FWD = Profile(L['F5'], 0.0, [
    (L['F5'], 23.0, +3.5),
    (L['F6'] + 4.7, L['F7'] - (L['F6'] + 4.7), -3.5),
])

# Entry (§6 -> 7): at F2h the water meets the window sills (~1.0 m above the bus origin) and the waterline climbs the
# glass; it passes the window tops (~2.3 m) at ~F2h + 0.65 = 363.9 (bible: '水线越过窗顶 ≈363.9'). So the bus ORIGIN is
# D0 = 1.0 m under the surface at F2h. The eye (origin + 1.70) goes under at ~F2h + 0.36.
D0 = 1.0


def depth(t):
    return D0 + SINK.x(t)


def fwd(t):
    return FWD.x(t)


# ---- 7b-ii F7 (D-34 #5 / D-49 #4, 总导演 10-26: option C, door centre -38 deg): the bus steers RIGHT into the stop.
# Heading (Unity yaw, + = clockwise from above) psi(t) = TURN_DEG * smoothstep((t - F6) / (F7 - F6)), held after F7
# (the bus only sinks from there). The bus moves along its heading, so in the palace frame it drifts: d(t) = integral
# of fwd'(t) * (sin psi, cos psi - 1) -- the displacement from the straight path. Only R_Palace follows this (the sea,
# the sun, the 7c mirror and rose lights do not). TURN_DEG is solved by Tools~/f7_door_options.py (palace contract 3.0:
# door x -21) for the door centre at -38 deg from the main eye at F7.
TURN_DEG = 4.08
TURN_T0, TURN_T1 = L['F6'], L['F7']
_TURN_DT = 0.01
_TURN_TAB = None


def heading(t):
    return TURN_DEG * smoothstep((t - TURN_T0) / (TURN_T1 - TURN_T0))


def _turn_table():
    global _TURN_TAB
    if _TURN_TAB is None:
        import math
        tab, x, z, t = [(TURN_T0, 0.0, 0.0)], 0.0, 0.0, TURN_T0
        while t < TURN_T1 - 1e-9:
            tm = t + _TURN_DT * 0.5
            ds = fwd(t + _TURN_DT) - fwd(t)
            a = math.radians(heading(tm))
            x += ds * math.sin(a); z += ds * (math.cos(a) - 1.0); t += _TURN_DT
            tab.append((t, x, z))
        _TURN_TAB = tab
    return _TURN_TAB


def drift(t):
    """(dx, dz) of the bus from the straight path, palace frame (0 before F6, held after F7)"""
    tab = _turn_table()
    if t <= TURN_T0:
        return 0.0, 0.0
    if t >= TURN_T1:
        return tab[-1][1], tab[-1][2]
    i = min(int((t - TURN_T0) / _TURN_DT), len(tab) - 2)
    f = (t - tab[i][0]) / _TURN_DT
    return tab[i][1] + (tab[i + 1][1] - tab[i][1]) * f, tab[i][2] + (tab[i + 1][2] - tab[i][2]) * f


def palace_to_bus(p, t, bus_y_stop=2.5):
    """palace-frame points (..., 3) -> the bus frame at t (PalaceFrame_约定: bus origin y = bus_y_stop + depth(F7) - depth(t)
    above the terrace top), with the F7 right turn: yaw(-heading) x (p - bus(t)), bus(t) on the drifted path"""
    import math
    import numpy as np
    dx, dz = drift(t)
    b = np.array([dx, bus_y_stop + (depth(L['F7']) - depth(t)), fwd(t) + dz])
    q = np.asarray(p, float) - b
    a = math.radians(-heading(t))
    c, s = math.cos(a), math.sin(a)
    return np.stack([q[..., 0] * c + q[..., 2] * s, q[..., 1], -q[..., 0] * s + q[..., 2] * c], -1)

if __name__ == '__main__':
    for k in ('F2h', 'F3', 'F4', 'F4p', 'F3e', 'F3e1', 'F3e2', 'F3e3', 'F3i', 'F5', 'F5p', 'F6', 'F7', 'F7s', 'F7p', 'F8',
              'F8a', 'F8b', 'F8c'):
        t = L[k]
        print('%-5s %7.2f  depth %7.2f m  v_sink %5.2f  fwd %7.2f m  v_fwd %4.2f  (%s)' % (
            k, t, depth(t), SINK.v(t), fwd(t), FWD.v(t), LSRC[k]))
    print('exit %.2f depth %.2f' % (EXIT, depth(EXIT)))
    print('peak acc sink %.3f fwd %.3f m/s^2' % (SINK.peak_acc(), FWD.peak_acc()))
