"""Director v1.3 (D-43) numeric check: what a late joiner sees from the moment they spawn.

  python3 spawn_fade_sim.py          -> prints the table, writes ../Docs~/spawn_fade_sim.json and ../Docs~/spawn_fade_sim.md

A Python port (same arithmetic, frame by frame at 90 Hz) of:
  * LanbaiActDispatcher v1.3      fade latch (_fadeEndT = t of the first dispatch after End), since, the window tables,
                                  LanbaiOverlayHandoverAt, LanbaiSpawnBrightestL, LanbaiSpawnFadeLength
  * LB_Journey's spawn            README_Director §0 (v1.3): 3 s black, then either hold the black and hand over at
                                  LanbaiOverlayHandoverAt(blackEnd, blackEnd + T), or its own EV-linear fade of T s
  * LanbaiInsideDriver            WriteBlack (catch-up, FlashFor) and LanbaiGrade, 177.55 .. 252.64
  * LanbaiAct06Driver             the overlay part of Evaluate (pre-roll, lobed dawn curve, catch-up, Hide), Activate,
                                  HandBack, LanbaiOverlayWindow (252.64 .. window end - one rise)
  * the white of act 10           NOT on main (pkg/mirrors). A STAND-IN written to the same rule (D-43 #1: from the moment
                                  it writes the overlay to its window end minus one rise; brings a joiner up from black at
                                  0.85 EV/s). It checks LB_Journey's side against that rule, not the mirrors' code.
  * LanbaiOverlay                 EvOverlayAlpha / SetFlat / SetCurve / lobes / Hide (Overlay/Tools~/overlay_model.py)

What is measured, per view direction (the act 6 lobes: zenith, below, the sun's sector, everything else):
  the viewer's luminance  L = (1 - a) * Lscene * 2^dEV + a * Lfill   (the fill is compensated by 2^-dEV, so Lfill fixed)
  from the spawn until the joiner's view equals the view of someone who has been in the world all along (the reference
  viewer, since = 1e6); the ramp law of bible §1.8 / E17 on that stretch: any 0.25 / 1 / 2 s window <= 0.5 / 1.0 / 1.8 EV
  of brightening, EV = log2(max(L, 0.004)) (the overlay's floor, as overlay_model.py), and the largest one-frame rise.
Scene luminances are the extremes the curves are built for (the brightest case): inside 0.2, the dawn 0.652 from 252.64,
the white 0.84 (drawn by the overlay; the night under it 0.05), elsewhere 0.5. Timeline t = real time (no hitch), plus one case with a 0.5 s hitch on the hand-over frame.
"""
import json
import math
import os

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), 'Docs~')
FLOOR = 0.004
DT = 1.0 / 90.0
RATE = 0.85


def clamp01(x):
    return min(1.0, max(0.0, x))


def ev_alpha(x, Lfrom, Lto, Ls, Lo):
    a, b = max(Lfrom, FLOOR), max(Lto, FLOOR)
    L = a * (b / a) ** clamp01(x)
    den = Ls - Lo
    return 1.0 if abs(den) < 1e-6 else clamp01((Ls - L) / den)


DIRS = ['zenith', 'below', 'sun', 'else']


class Overlay:
    """LanbaiOverlay: per-direction alpha (the four act 6 directions get their lobe's lead exactly)."""

    def __init__(self):
        self.mode = 'hidden'
        self.leads = {d: 0.0 for d in DIRS}
        self.flat = 0.0
        self.curve = None
        self.fillL = 0.0013

    def SetFlat(self, fillL, a):
        self.mode, self.flat, self.fillL = 'flat', clamp01(a), fillL

    def SetCurve(self, fillL, tau, T, Lfrom, Lto, Ls, Lo):
        self.mode, self.curve, self.fillL = 'curve', (tau, max(T, 1e-3), Lfrom, Lto, Ls, Lo), fillL

    def SetLobes(self, leads):
        self.leads = dict(leads)

    def ClearLobes(self):
        self.leads = {d: 0.0 for d in DIRS}

    def Hide(self):
        self.ClearLobes()
        self.mode = 'hidden'

    def alpha(self, d):
        if self.mode == 'hidden':
            return 0.0
        if self.mode == 'flat':
            return self.flat
        tau, T, Lf, Lt, Ls, Lo = self.curve
        return ev_alpha((tau - self.leads[d]) / T, Lf, Lt, Ls, Lo)


# ---------------------------------------------------------------------------------------------------------- drivers
class Inside:
    tU9, tU12, flashEV = 179.55, 248.64, 1.5
    Ls, Lb = 0.2, 0.00129

    def __init__(self, ov):
        self.ov, self.since = ov, 1e6

    def window(self):
        return (self.tU9 - 2.0, self.tU12 + 4.0)

    def overlay_window(self):
        return (self.tU12 - 0.25, self.tU12 + 4.0)

    def brightest(self, t):
        return self.Ls

    def delta_ev(self, t):
        t0 = self.tU12 - 0.75
        if t < t0: return 0.0
        if t < t0 + 0.4: return self.flashEV * (t - t0) / 0.4
        if t < t0 + 0.5: return self.flashEV
        if t < self.tU12: return self.flashEV * (1 - (t - t0 - 0.5) / 0.25)
        return 0.0

    def flash_for(self, t):
        if self.since < 0: return 0.0
        if self.since < 1e5:
            te = t - self.since
            rng = math.log2(0.2 / 0.004)
            if self.tU12 - 0.25 <= te < self.tU12 + 4.0 and self.since * 0.85 < rng: return 0.0
        return self.delta_ev(t)

    def grade(self, t):
        return self.flash_for(t)

    def activate(self, on):
        pass

    def tick(self, t):
        if t < self.tU9: return
        self.write_black(t)

    def write_black(self, t):
        if self.since < 0: return
        tb = self.tU12 - 0.25
        te = t - self.since
        catch = self.since < 1e5 and tb <= te < self.tU12 + 4.0
        aC = 0.0
        if catch:
            rng = math.log2(self.Ls / max(self.Lb, 0.004))
            aC = ev_alpha(self.since * 0.85 / max(rng, 1e-3), self.Lb, self.Ls, self.Ls, self.Lb)
        if t < tb:
            if catch and aC > 0: self.ov.SetFlat(self.Lb, aC)
            return
        if t < self.tU12:
            a = ev_alpha((t - tb) / 0.25, self.Ls, self.Lb, self.Ls, self.Lb)
            self.ov.SetFlat(self.Lb, max(a, aC))
        elif t < self.tU12 + 4.0:
            self.ov.SetFlat(self.Lb, 1.0)


class Act06:
    windowStart, windowEnd = 248.64, 363.62
    tPreroll0, tDawn0, dawnT, tOverlayOff = 252.64, 254.14, 8.65, 266.4
    lBlack, lDawn = 0.0013, 0.652
    LEADS = {'zenith': 0.0, 'below': 2.2, 'sun': 3.3, 'else': 2.0}

    def __init__(self, ov):
        self.ov = ov
        self.since = 1e6
        self.held = False
        self.hidden = False
        self.lobes = False
        self.lastT = -1.0

    def window(self):
        return (self.windowStart, self.windowEnd)

    def rise(self):
        rng = math.log2(max(self.lDawn, FLOOR) / max(self.lBlack, FLOOR))
        return rng / 0.85 + max(self.LEADS.values())

    def hand_end(self):
        return max(self.tOverlayOff, self.windowEnd - self.rise() - 0.5)

    def overlay_window(self):
        return (self.tPreroll0, self.hand_end())

    def brightest(self, t):
        return self.lDawn

    def grade(self, t):
        return 0.0

    def activate(self, on):
        if not on: self.hand_back()
        if on: self.hidden, self.lobes, self.lastT = False, False, -1.0

    def hand_back(self):
        if not self.hidden and self.lastT >= self.tPreroll0 and self.since >= 0:
            self.ov.Hide()
            self.hidden = True

    def tick(self, t):
        if t < self.lastT - 0.5: self.hidden = False; self.lobes = False
        elif t < self.lastT and t < self.tOverlayOff: self.hidden = False; self.lobes = False
        self.lastT = t
        held = self.since < 0
        if held: self.held = True
        elif self.held:
            self.held = False
            self.lobes = False
            if t - self.since < self.hand_end(): self.hidden = False
        catch = (not held) and self.since < 1e5 and self.tPreroll0 <= t - self.since < self.hand_end()
        rng = math.log2(max(self.lDawn, FLOOR) / max(self.lBlack, FLOOR))
        tauC = self.since * 0.85 * self.dawnT / max(rng, 1e-3) if catch else 1e6
        maxLead = max(self.LEADS.values())
        if (not held) and (not self.hidden) and t >= self.tPreroll0:
            if t < self.tDawn0:
                a0 = self.ev_alpha(0.0)
                x = (t - self.tPreroll0) / (self.tDawn0 - self.tPreroll0)
                aCur = 1 + (a0 - 1) * clamp01(x)
                if catch: aCur = max(aCur, self.ev_alpha(tauC / self.dawnT))
                self.ov.SetFlat(self.lBlack, aCur)
            elif t < self.tOverlayOff or (catch and tauC < self.dawnT + maxLead):
                if not self.lobes:
                    self.ov.SetLobes(self.LEADS)
                    self.lobes = True
                self.ov.SetCurve(self.lBlack, min(t - self.tDawn0, tauC), self.dawnT, self.lBlack, self.lDawn, self.lDawn, self.lBlack)
            else:
                self.ov.Hide()
                self.hidden = True

    def ev_alpha(self, x):
        return ev_alpha(x, self.lBlack, self.lDawn, self.lDawn, self.lBlack)


class WhiteStandIn:
    """NOT the mirrors' driver: the D-43 rule applied to the white (1146.31 mask .. 1186.46 shrink end)."""
    t0, t1, Lw, Lb = 1146.31, 1186.46, 0.84, 0.0013

    def __init__(self, ov):
        self.ov, self.since = ov, 1e6

    def window(self):
        return (self.t0 - 1.0, self.t1 + 1.0)

    def rise(self):
        return math.log2(self.Lw / FLOOR) / 0.85

    def overlay_window(self):
        return (self.t0, self.t1 - self.rise() - 0.5)

    def brightest(self, t):
        return self.Lw

    def grade(self, t):
        return 0.0

    def activate(self, on):
        if not on and self.since >= 0: self.ov.Hide()     # the same rule as act 6's HandBack: not under the spawn fade

    def tick(self, t):
        if self.since < 0: return
        te = t - self.since
        catch = self.since < 1e5 and self.overlay_window()[0] <= te < self.overlay_window()[1]
        # the film itself (simplified): white over everything 1146.31 .. 1186.46 (the scene under it is irrelevant here)
        if t < self.t0: return
        if t >= self.t1: self.ov.Hide(); return
        if catch:
            L = min(self.Lw, FLOOR * 2 ** (RATE * self.since))      # EV-linear from the floor to the white
            if L < self.Lw:
                self.ov.SetFlat(L, 1.0)
                return
        self.ov.SetFlat(self.Lw, 1.0)


def scene_L(t):
    if t < 248.64: return Inside.Ls
    if t < 252.64: return Inside.Ls                    # under the act 5 black (the overlay is 1 there)
    if t < 363.62: return Act06.lDawn
    if 1100 <= t < 1300: return 0.05                  # the night under / after the white (the white itself is the overlay)
    return 0.5


# ---------------------------------------------------------------------------------------------------------- director
class Dispatcher:
    def __init__(self, drivers):
        self.drivers = sorted(drivers, key=lambda d: type(d).__name__)
        self.on = {id(d): False for d in self.drivers}
        self.ovw = sorted(d.overlay_window() for d in self.drivers)
        self.reported = self.ask = self.ended = False
        self.fadeEndT = -1.0
        self.begin = -1.0
        self.gradeDEV = 0.0

    def handover_at(self, t0, t1):
        best = -1.0
        for w0, w1 in self.ovw:
            if w0 < t1 and w1 > t0:
                h = max(t0, w0)
                if best < 0 or h < best: best = h
        return best

    def covers(self, t):
        return any(w0 <= t < w1 for w0, w1 in self.ovw)

    def brightest(self, t):
        L = -1.0
        for d in self.drivers:
            w0, w1 = d.window()
            if w0 <= t < w1: L = max(L, d.brightest(t))
        return L if L > 0 else 1.0

    def fade_length(self, t, lBlack):
        ev = math.log2(max(self.brightest(t), 0.004) / max(lBlack, 0.004))
        return min(max(ev / RATE, 0.0), 9.0)

    def fade_begin(self, real):
        self.reported, self.ask, self.ended, self.fadeEndT, self.begin = True, False, False, -1.0, real

    def fade_end(self):
        if self.reported and not self.ended and not self.ask: self.ask = True

    def dispatch(self, t, real):
        if self.reported and not self.ended and (self.ask or real - self.begin > 15.0):
            self.ended, self.fadeEndT = True, t
        since = 1e6 if not self.reported else (-1.0 if not self.ended else max(0.0, t - self.fadeEndT))
        self.gradeDEV = 0.0
        for d in self.drivers:
            w0, w1 = d.window()
            inside = w0 <= t < w1
            if inside != self.on[id(d)]:
                d.activate(inside)
                self.on[id(d)] = inside
            if inside:
                d.since = since
                d.tick(t)
                self.gradeDEV += d.grade(t)
        return since


class Journey:
    """LB_Journey's spawn, README_Director §0 v1.3 (the black is L 0.0013, the fill of the spawn overlay)."""
    BLACK, LBLACK = 3.0, 0.0013

    def __init__(self, disp, ov, ts, joiner=True):
        self.d, self.ov, self.ts = disp, ov, ts
        self.state = 'black' if joiner else 'done'
        self.T = 0.0
        self.handAt = -1.0
        self.L = 1.0
        if joiner:
            disp.fade_begin(0.0)
            ov.SetFlat(self.LBLACK, 1.0)

    def step(self, t):
        if self.state == 'black':
            self.ov.SetFlat(self.LBLACK, 1.0)
            if t >= self.ts + self.BLACK:
                self.T = self.d.fade_length(t, self.LBLACK)
                self.L = self.d.brightest(t)
                self.handAt = self.d.handover_at(t, t + self.T)
                self.t0 = t
                self.state = 'hold' if self.handAt >= 0 else 'fade'
        if self.state == 'hold':
            self.ov.SetFlat(self.LBLACK, 1.0)
            if t >= self.handAt and self.d.covers(t):
                self.d.fade_end()
                self.state = 'done'
            elif t > self.handAt + 1.0:                     # the window went away (a seek): own fade from here
                self.T = self.d.fade_length(t, self.LBLACK); self.L = self.d.brightest(t); self.t0 = t; self.state = 'fade'
        if self.state == 'fade':
            self.ov.ClearLobes()
            tau = t - self.t0
            self.ov.SetCurve(self.LBLACK, tau, self.T, self.LBLACK, self.L, self.L, self.LBLACK)
            if tau >= self.T:
                self.ov.Hide()
                self.d.fade_end()
                self.state = 'done'


class Act06v12(Act06):
    """negative control: act 6 as in v1.2 (overlay window and catch-up only to 266.4)"""

    def hand_end(self):
        return self.tOverlayOff


class JourneyV12(Journey):
    """negative control: LB_Journey as README_Director v1.2 (point check at spawn and spawn + 3 s, 3 s fade)"""

    def __init__(self, disp, ov, ts, joiner=True):
        Journey.__init__(self, disp, ov, ts, joiner)
        self.covered = joiner and (disp.covers(ts) or disp.covers(ts + 3.0))

    def step(self, t):
        if self.state == 'black':
            self.ov.SetFlat(self.LBLACK, 1.0)
            if t >= self.ts + self.BLACK:
                if self.covered:
                    self.d.fade_end(); self.state = 'done'
                else:
                    self.T, self.L, self.t0, self.state = 3.0, self.d.brightest(t), t, 'fade'
        if self.state == 'fade':
            tau = t - self.t0
            self.ov.SetCurve(self.LBLACK, tau, self.T, self.LBLACK, self.L, self.L, self.LBLACK)
            if tau >= self.T:
                self.ov.Hide(); self.d.fade_end(); self.state = 'done'


def run(ts, joiner, t_end, hitch_at_handover=False, v12=False):
    ov = Overlay()
    drivers = [Inside(ov), (Act06v12 if v12 else Act06)(ov), WhiteStandIn(ov)]
    d = Dispatcher(drivers)
    j = (JourneyV12 if v12 else Journey)(d, ov, ts, joiner)
    out = []
    t, real = ts, 0.0
    hitched = False
    while t <= t_end:
        j.step(t)
        d.dispatch(t, real)
        dev = d.gradeDEV
        Ls = scene_L(t)
        out.append((t, {k: (1 - ov.alpha(k)) * Ls * 2 ** dev + ov.alpha(k) * ov.fillL for k in DIRS}, j.state))
        step = DT
        if hitch_at_handover and not hitched and j.state == 'done' and joiner:
            step, hitched = 0.5, True
        t += step
        real += step
    return out


def ev(L):
    return math.log2(max(L, FLOOR))


def check(ts, hitch=False, v12=False):
    t_end = ts + 40.0
    jo = run(ts, True, t_end, hitch, v12)
    # the reference viewer: in the world all along (no spawn), same frames
    rv = run(ts, False, t_end, False, v12)
    conv = None
    for (t, L, st), (_, R, _) in zip(jo, rv):
        if st == 'done' and all(abs(ev(L[k]) - ev(R[k])) < 0.02 for k in DIRS):
            conv = t
            break
    stop = conv if conv is not None else t_end
    res = {'join': ts, 'converged_at': None if conv is None else round(conv, 2), 'hitch': hitch, 'v12': v12}
    worst = {'w025': 0.0, 'w1': 0.0, 'w2': 0.0, 'frame': 0.0}
    seg = [(t, L) for t, L, _ in jo if t <= stop + 1e-9]
    ts_ = [t for t, _ in seg]
    for k in DIRS:
        e = [ev(L[k]) for _, L in seg]
        for i in range(1, len(e)):
            worst['frame'] = max(worst['frame'], e[i] - e[i - 1])
        for key, w in (('w025', 0.25), ('w1', 1.0), ('w2', 2.0)):
            j = 0
            for i in range(len(e)):
                while ts_[i] - ts_[j] > w + 1e-9: j += 1
                lo = min(e[j:i + 1])
                worst[key] = max(worst[key], e[i] - lo)
    res.update({k: round(v, 3) for k, v in worst.items()})
    res['ok'] = worst['w025'] <= 0.5 + 1e-6 and worst['w1'] <= 1.0 + 1e-6 and worst['w2'] <= 1.8 + 1e-6 and conv is not None
    return res


def main():
    joins = [238, 244, 245.5, 249, 255, 260, 263.5, 266, 267, 270, 1140, 1150, 1180]
    rows = [check(ts) for ts in joins] + [check(263.5, True), check(270, True)]
    neg = [check(ts, v12=True) for ts in (263.5, 266, 1140)]     # negative control: v1.2 must fail here
    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, 'spawn_fade_sim.json'), 'w', encoding='utf-8') as f:
        json.dump({'v13': rows, 'negative_control_v12': neg}, f, indent=1)
    head = '| 进场 s | 卡顿 | 和一直在场的人一样的时刻 s | 0.25 s 内最多升 EV（≤ 0.5） | 1 s（≤ 1.0） | 2 s（≤ 1.8） | 一帧最多升 EV | 过 |\n|---|---|---|---|---|---|---|---|\n'
    body = ''.join('| {join} | {h} | {c} | {w025} | {w1} | {w2} | {frame} | {ok} |\n'.format(
        h='0.5 s' if r['hitch'] else '', c=r['converged_at'], ok='是' if r['ok'] else '**否**', **{k: r[k] for k in ('join', 'w025', 'w1', 'w2', 'frame')}) for r in rows)
    nbody = ''.join('| {join} | v1.2 | {c} | {w025} | {w1} | {w2} | {frame} | {ok} |\n'.format(
        c=r['converged_at'], ok='是' if r['ok'] else '否（应当不过）', **{k: r[k] for k in ('join', 'w025', 'w1', 'w2', 'frame')}) for r in neg)
    body += nbody
    with open(os.path.join(DOCS, 'spawn_fade_sim.md'), 'w', encoding='utf-8') as f:
        f.write('# 迟到的人进场：数值核对（`Director/Tools~/spawn_fade_sim.py` 生成，Python 移植，不是 Unity 里跑的）\n\n'
                '第 10 幕的白用的是按 D-43 写的替身，不是镜与白的代码。亮度按 0.004 的地板算 EV（和 `overlay_model.py` 一样）。'
                '“卡顿”= 交接那一帧时间轴跳 0.5 s。最后几行“v1.2”是负对照：用 v1.2 的做法，263.5 应当不过（D-43 说的 +7.35 EV）。\n\n' + head + body)
    print(head + body)
    neg_ok = not neg[0]['ok']                                  # 263.5 under v1.2 = the +7.35 EV jump D-43 is about
    print('negative control (v1.2 at 263.5 must fail):', 'reproduced' if neg_ok else 'NOT reproduced')
    return 0 if all(r['ok'] for r in rows) and neg_ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
