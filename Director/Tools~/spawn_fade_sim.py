"""Director v1.3 r2 (D-43, D-43 #7) numeric check: what a late joiner sees from the moment they spawn.

  python3 spawn_fade_sim.py            -> the table + ../Docs~/spawn_fade_sim.json / .md; exit 1 if any check fails
  python3 spawn_fade_sim.py --quick    -> the listed join times and the negative controls only (no dense scan)

A Python port, frame by frame, of the REAL code (same arithmetic, same order of calls):
  * LanbaiActDispatcher v1.3 r2   latch (_fadeEndT = t of the first dispatch after End), the hand-over state
                                  (_handState), the rewind rule, the 25 s timeout, the grade sum (gradeDEV), the window
                                  table, LanbaiOverlayHandoverAt, LanbaiSpawnBrightestL (<= 1), LanbaiSpawnFadeLength,
                                  LanbaiSpawnSeenL
  * LB_Journey's spawn            the state machine of README_Director §0 item 4 (black 3 s; hold + hand over, or its own
                                  fade that limits the SEEN brightness: scene x 2^dEV)
  * LanbaiInsideDriver            WriteBlack (catch-up), FlashFor (r2: from U12 - 0.75), LanbaiGrade, LanbaiBrightestL 0.2
  * LanbaiAct06Driver             the overlay part of Evaluate, Activate / HandBack, LanbaiOverlayWindow, LanbaiBrightestL
  * LanbaiWhiteDriver             pkg/mirrors 962567b, Act10_White/Runtime/LanbaiWhiteDriver.cs: LanbaiGrade (EXPO_UP 0 ->
                                  1 -> 2.4 EV, the +1 EV after the silence), DriveOverlay (mask curve with the forward
                                  lobe, flat white with the breath, shrink with three lobes, the late joiner's black ->
                                  white fill ramp, the toScene black -> act 11 ramp), LanbaiOverlayWindow, Release
  * LanbaiOverlay                 EvOverlayAlpha / SetFlat / SetCurve / lobes / Hide

What a view direction sees:  L = (1 - a) * Lscene * 2^dEV + a * Lfill   (the overlay is graded; its fill is compensated
by 2^-dEV, so the fill's luminance is what the driver asked for), dEV = the sum of the drivers' LanbaiGrade.
Scene luminances are the brightest non-white views the curves are built for: inside 0.2, the dawn 0.652, act 9 0.06
(after F13; 0.01 before), act 11 0.012; LB_Journey's own events are not modelled (none in these two stretches).

Checks, per direction, from the spawn until the joiner sees what someone who has been there all along sees:
  bible §1.8 windows: any 0.25 / 1 / 2 s <= 0.5 / 1.0 / 1.8 EV of brightening, EV = log2(max(L, 0.004));
  D-43 rate: any window w of 1 / 2 / 4 s <= 0.85 * w + 0.05 EV;  and the joiner must converge within 40 s.
Join times: the D-43 list, a dense scan every 0.1 s over 175-372 s and 1120-1200 s (30 fps), a 0.5 s hitch on the
hand-over frame, and a scrub back before the latch (DIR13-2). Negative controls (must FAIL): v1.2's LB_Journey + act 6
window; FLASH_TEAR not suppressed; the r1 FlashFor condition (U12 - 0.25); LB_Journey's fixed-T fade (r1, no seen limit);
the scrub without the rewind rule.
"""
import json
import math
import os
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
DOCS = os.path.join(os.path.dirname(HERE), 'Docs~')
FLOOR = 0.004
RATE = 0.85
DIRS = ['zenith', 'below', 'sun', 'else', 'fwd', 'side']


def clamp01(x):
    return min(1.0, max(0.0, x))


def ev_alpha(x, Lfrom, Lto, Ls, Lo):
    a, b = max(Lfrom, FLOOR), max(Lto, FLOOR)
    L = a * (b / a) ** clamp01(x)
    den = Ls - Lo
    return 1.0 if abs(den) < 1e-6 else clamp01((Ls - L) / den)


def lin(xs, ys, t):
    if t <= xs[0]:
        return ys[0]
    for i in range(len(xs) - 1):
        if t <= xs[i + 1]:
            return ys[i] + (ys[i + 1] - ys[i]) * (t - xs[i]) / max(xs[i + 1] - xs[i], 1e-6)
    return ys[-1]


class Overlay:
    def __init__(self):
        self.mode = 'hidden'
        self.leads = dict.fromkeys(DIRS, 0.0)
        self.flat = 0.0
        self.fillL = 0.0
        self.curve = None

    def SetFlat(self, fillL, a):
        self.mode, self.flat, self.fillL = 'flat', clamp01(a), fillL

    def SetCurve(self, fillL, tau, T, Lf, Lt, Ls, Lo):
        self.mode, self.fillL, self.curve = 'curve', fillL, (tau, max(T, 1e-3), Lf, Lt, Ls, Lo)

    def SetLeads(self, leads):
        self.leads = dict(leads)

    def ClearLobes(self):
        self.leads = dict.fromkeys(DIRS, 0.0)

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


# ------------------------------------------------------------------------------------------------------------ drivers
class Inside:
    tU9, tU12, flashEV = 179.55, 248.64, 1.5
    Ls, Lb = 0.2, 0.00129
    flash_from = 0.75          # r2 (DIR13-3); r1 was 0.25
    suppress = True
    r1 = False                 # negative control: r1 also suppressed while the spawn fade runs (since < 0)

    def __init__(self, ov):
        self.ov, self.since = ov, 1e6

    def window(self):
        return (self.tU9 - 2.0, self.tU12 + 4.0)

    def overlay_window(self):
        return (self.tU12 - 0.25, self.tU12 + 4.0)

    def brightest(self, t):
        return 0.2

    def delta_ev(self, t):
        t0 = self.tU12 - 0.75
        if t < t0: return 0.0
        if t < t0 + 0.4: return self.flashEV * (t - t0) / 0.4
        if t < t0 + 0.5: return self.flashEV
        if t < self.tU12: return self.flashEV * (1 - (t - t0 - 0.5) / 0.25)
        return 0.0

    def flash_for(self, t):
        if not self.suppress:
            return self.delta_ev(t)
        if self.r1 and self.since < 0: return 0.0
        if 0 <= self.since < 1e5:
            te = t - self.since
            rng = math.log2(0.2 / 0.004)
            if self.tU12 - self.flash_from <= te < self.tU12 + 4.0 and self.since * 0.85 < rng: return 0.0
        return self.delta_ev(t)

    def grade(self, t):
        return self.flash_for(t)

    def activate(self, on):
        pass

    def tick(self, t):
        if t < self.tU9 or self.since < 0:
            return
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
    LEADS = {'zenith': 0.0, 'below': 2.2, 'sun': 3.3, 'else': 2.0, 'fwd': 2.0, 'side': 2.0}
    v12 = False

    def __init__(self, ov):
        self.ov, self.since = ov, 1e6
        self.held = self.hidden = self.lobes = False
        self.lastT = -1.0

    def window(self):
        return (self.windowStart, self.windowEnd)

    def rise(self):
        return math.log2(max(self.lDawn, FLOOR) / max(self.lBlack, FLOOR)) / 0.85 + 3.3

    def hand_end(self):
        return self.tOverlayOff if self.v12 else max(self.tOverlayOff, self.windowEnd - self.rise() - 0.5)

    def overlay_window(self):
        return (self.tPreroll0, self.hand_end())

    def brightest(self, t):
        return self.lDawn

    def grade(self, t):
        return 0.0

    def activate(self, on):
        if not on and not self.hidden and self.lastT >= self.tPreroll0 and self.since >= 0:
            self.ov.Hide(); self.hidden = True
        if on:
            self.hidden = self.lobes = False; self.lastT = -1.0

    def tick(self, t):
        if t < self.lastT - 0.5: self.hidden = self.lobes = False
        elif t < self.lastT and t < self.tOverlayOff: self.hidden = self.lobes = False
        self.lastT = t
        held = self.since < 0
        if held: self.held = True
        elif self.held:
            self.held = False; self.lobes = False
            if t - self.since < self.hand_end(): self.hidden = False
        catch = (not held) and self.since < 1e5 and self.tPreroll0 <= t - self.since < self.hand_end()
        rng = math.log2(max(self.lDawn, FLOOR) / max(self.lBlack, FLOOR))
        tauC = self.since * 0.85 * self.dawnT / max(rng, 1e-3) if catch else 1e6
        if (not held) and (not self.hidden) and t >= self.tPreroll0:
            if t < self.tDawn0:
                a0 = ev_alpha(0.0, self.lBlack, self.lDawn, self.lDawn, self.lBlack)
                x = (t - self.tPreroll0) / (self.tDawn0 - self.tPreroll0)
                aCur = 1 + (a0 - 1) * clamp01(x)
                if catch: aCur = max(aCur, ev_alpha(tauC / self.dawnT, self.lBlack, self.lDawn, self.lDawn, self.lBlack))
                self.ov.SetFlat(self.lBlack, aCur)
            elif t < self.tOverlayOff or (catch and tauC < self.dawnT + 3.3):
                if not self.lobes: self.ov.SetLeads(self.LEADS); self.lobes = True
                self.ov.SetCurve(self.lBlack, min(t - self.tDawn0, tauC), self.dawnT, self.lBlack, self.lDawn, self.lDawn, self.lBlack)
            else:
                self.ov.Hide(); self.hidden = True


class White:
    """port of pkg/mirrors 962567b LanbaiWhiteDriver (desktop: isVR false)"""
    tMirror12, tF16, tSilenceEnd, tShrinkEnd, tMaskStart = 1137.58, 1149.31, 1178.46, 1186.46, 1144.11
    evT, evV = [1137.58, 1138.78, 1144.78, 1146.31, 1149.31], [0, 1, 2.4, 2.4, 2.4]
    lw, lSceneMask, maskSeconds, maskLobeLead, lScene11 = 0.86, 0.06, 5.2, 1.0, 0.012
    breathAmount, breathHz, shrinkSeconds, afterSilenceEV, afterSilenceDecay = 0.02, 0.1, 5.0, 1.0, 4.0
    joinFromL, joinMaxEVps, joinTail = 0.004, 0.8, 2.5
    MASK_LEADS = {'fwd': 1.0}
    SHRINK_LEADS = {'fwd': 0.0, 'side': 1.5, 'zenith': 3.0}
    SHRINK_ELSE = 3.0
    fixed = False              # the proposed fix (Engineering/给总导演.md): the toScene ramp starts at the hand-over, the
                               # overlay window ends one ramp (+0.5 s) before the driver's window ends (D-43 #7)

    def scene_ramp(self):
        return math.log2(max(self.lScene11, self.joinFromL * 1.01) / self.joinFromL) / self.joinMaxEVps

    def __init__(self, ov):
        self.ov, self.since = ov, 1e6
        self.owns = self.lobes = self.maskLobe = False

    def window(self):
        return (self.tMirror12 - 1.0, self.tShrinkEnd + self.joinTail)

    def overlay_window(self):
        if self.fixed:
            return (self.tMaskStart, self.tShrinkEnd + self.joinTail - self.scene_ramp() - 0.5)
        return (self.tMaskStart, self.tShrinkEnd + self.joinTail)

    def grade(self, t):
        if t < self.tMirror12 or t > self.tSilenceEnd + self.afterSilenceDecay:
            return 0.0
        if t < self.tF16:
            return lin(self.evT, self.evV, t)
        if t < self.tSilenceEnd:
            return 0.0
        return self.afterSilenceEV * clamp01(1 - (t - self.tSilenceEnd) / self.afterSilenceDecay)

    def activate(self, on):
        self.lobes = self.maskLobe = False
        if not on: self.release()

    def release(self):
        if not self.owns: return
        self.ov.ClearLobes(); self.ov.Hide()
        self.owns = self.lobes = self.maskLobe = False

    def breath(self, t):
        return 1 + self.breathAmount * math.sin(2 * math.pi * self.breathHz * (t - self.tF16))

    def tick(self, t):
        ov, lw = self.ov, self.lw
        tJoin = t - self.since
        joinedLate = tJoin >= self.tMaskStart
        rampT = math.log2(lw / self.joinFromL) / self.joinMaxEVps
        toScene = joinedLate and tJoin + rampT > self.tSilenceEnd
        sceneRampT = math.log2(max(self.lScene11, self.joinFromL * 1.01) / self.joinFromL) / self.joinMaxEVps
        rampEnd = (max(self.tShrinkEnd, tJoin) if self.fixed else self.tShrinkEnd) + sceneRampT
        if self.since < 0 or t < self.tMaskStart or (not toScene and t >= self.tShrinkEnd) or (toScene and t >= rampEnd):
            self.release(); return
        if toScene:
            self.owns = True
            if self.lobes: ov.ClearLobes(); self.lobes = False
            r0 = max(self.tShrinkEnd, tJoin) if self.fixed else self.tShrinkEnd
            if t < r0: ov.SetFlat(0.0, 1.0)
            else: ov.SetCurve(0.0, t - r0, sceneRampT, self.joinFromL, self.lScene11, self.lScene11, 0.0)
            return
        ramping = joinedLate and t < tJoin + rampT
        self.owns = True
        if t < self.tSilenceEnd and self.lobes: ov.ClearLobes(); self.lobes = self.maskLobe = False
        if (ramping or t >= self.tF16) and self.maskLobe: ov.ClearLobes(); self.maskLobe = False
        if ramping:
            x = clamp01((t - tJoin) / rampT)
            k = (self.joinFromL / lw) ** (1 - x)
            ov.SetFlat(lw * (self.breath(t) if t >= self.tF16 else 1.0) * k, 1.0)
        elif t < self.tF16:
            if not self.maskLobe:
                ov.ClearLobes(); ov.SetLeads(dict(dict.fromkeys(DIRS, 0.0), **self.MASK_LEADS)); self.maskLobe = True
            ov.SetCurve(lw, t - self.tMaskStart, self.maskSeconds, self.lSceneMask, lw, self.lSceneMask, lw)
        elif t < self.tSilenceEnd:
            ov.SetFlat(lw * self.breath(t), 1.0)
        else:
            if not self.lobes:
                self.maskLobe = False
                ov.ClearLobes(); ov.SetLeads(dict(dict.fromkeys(DIRS, self.SHRINK_ELSE), **self.SHRINK_LEADS)); self.lobes = True
            ov.SetCurve(lw, t - self.tSilenceEnd, self.shrinkSeconds, lw, self.lScene11, self.lScene11, lw)


def scene_L(t):
    if t < 248.64: return 0.2
    if t < 252.64: return 0.2            # behind the act 5 black
    if t < 363.62: return 0.652
    if t < 1018.21: return 0.01
    if t < 1149.31: return 0.06
    return 0.012


# ------------------------------------------------------------------------------------------------------------ director
class Dispatcher:
    rewind = True
    hands = True               # r2 hand-over state; False = r1 (since = t - fadeEndT for everyone)
    lookahead = True           # r2 fade length looks ahead at the drivers' grade; False = r1 formula

    def __init__(self, drivers):
        self.drivers = sorted(drivers, key=lambda d: type(d).__name__)
        self.on = {id(d): False for d in self.drivers}
        self.ovw = sorted(d.overlay_window() for d in self.drivers)
        self.reported = self.ask = self.ended = False
        self.fadeEndT = -1.0
        self.begin = 0.0
        self.hand = 0
        self.gradeDEV = 0.0

    def covers(self, t):
        return any(w0 <= t < w1 for w0, w1 in self.ovw)

    def handover_at(self, t0, t1):
        best = -1.0
        if t1 > t0:
            for w0, w1 in self.ovw:
                if w0 < t1 and w1 > t0:
                    h = max(t0, w0)
                    if best < 0 or h < best: best = h
        if self.reported and not self.ended: self.hand = 1 if best >= 0 else 2
        return best

    def brightest(self, t):
        L = -1.0
        for d in self.drivers:
            w0, w1 = d.window()
            if w0 <= t < w1 and hasattr(d, 'brightest'): L = max(L, d.brightest(t))
        return min(L if L > 0 else 1.0, 1.0)

    def grade_at(self, t):
        g = 0.0
        for d in self.drivers:
            w0, w1 = d.window()
            if w0 <= t < w1: g += d.grade(t)
        return g

    def fade_length(self, t, lBlack):
        if not self.lookahead:
            return min(max(math.log2(max(self.brightest(t), 0.004) / max(lBlack, 0.004)) / RATE, 0.0), 9.4)
        cap = max(9.4, 25.0 - 5.0)
        s = 0.0
        while s <= cap:
            if 0.004 * 2 ** (RATE * s) >= self.brightest(t + s) * 2 ** self.grade_at(t + s): return s
            s += 0.25
        return cap

    def seen(self, t, dEV):
        return self.brightest(t) * 2 ** dEV

    def fade_begin(self, real):
        self.reported, self.ask, self.ended, self.fadeEndT, self.begin, self.hand = True, False, False, -1.0, real, 0

    def fade_end(self):
        if self.reported and not self.ended and not self.ask: self.ask = True

    def fade_own(self):
        if self.reported and not self.ended: self.hand = 2

    def dispatch(self, t, real):
        if self.reported and not self.ended and (self.ask or real - self.begin > 25.0):
            self.ended, self.fadeEndT = True, t
            if self.hand == 0: self.hand = 1 if self.covers(t) else 2
        if self.rewind and self.ended and t < self.fadeEndT - 0.5: self.reported = False
        since = 1e6 if not self.reported else (-1.0 if not self.ended else (1e6 if (self.hand == 2 and self.hands) else max(0.0, t - self.fadeEndT)))
        self.gradeDEV = 0.0
        for d in self.drivers:
            w0, w1 = d.window()
            inside = w0 <= t < w1
            if inside != self.on[id(d)]:
                d.activate(inside); self.on[id(d)] = inside
            if inside:
                d.since = since
                d.tick(t)
                self.gradeDEV += d.grade(t)
        return since


class Journey:
    """README_Director §0 item 4 (v1.3 r2). mode 'r1': the r1 fixed-T SetCurve fade (no seen limit); 'v12': v1.2."""
    BLACK, LB = 3.0, 0.0013

    def __init__(self, d, ov, ts, joiner=True, mode='r2'):
        self.d, self.ov, self.ts, self.mode = d, ov, ts, mode
        self.sp = 'black' if joiner else 'none'
        if joiner:
            d.fade_begin(0.0)
            if mode == 'v12': self.covered = d.covers(ts) or d.covers(ts + 3.0)

    def step(self, t, dEV):
        d, ov = self.d, self.ov
        if self.sp == 'none': return
        if self.sp == 'black':
            ov.SetFlat(self.LB, 1.0)
            if t < self.ts + self.BLACK: return
            if self.mode == 'v12':
                if self.covered: d.fade_end(); self.sp = 'none'; return
                self.T, self.L, self.f0, self.sp = 3.0, d.brightest(t), t, 'fadeT'
            else:
                T = d.fade_length(t, self.LB)
                self.handAt = d.handover_at(t, t + T + (0.5 if self.mode == 'r2' else 0.0))
                if self.handAt >= 0: self.sp = 'hold'
                else: self.sp, self.f0, self.T, self.L = ('fadeT' if self.mode == 'r1' else 'fade'), t, T, d.brightest(t)
        if self.sp == 'hold':
            ov.SetFlat(self.LB, 1.0)
            if t >= self.handAt and d.covers(t): d.fade_end(); self.sp = 'none'; return
            if t > self.handAt + 1.0: d.fade_own(); self.sp, self.f0 = 'fade', t
            else: return
        if self.sp == 'fade':
            seen = d.seen(t, dEV)
            ramp = 0.004 * 2 ** (RATE * (t - self.f0))     # from the floor (the black below it does not count)
            if ramp >= seen: ov.Hide(); d.fade_end(); self.sp = 'none'; return
            ov.ClearLobes(); ov.SetFlat(self.LB, clamp01((seen - ramp) / max(seen - self.LB, 1e-5)))
            return
        if self.sp == 'fadeT':
            tau = t - self.f0
            ov.ClearLobes(); ov.SetCurve(self.LB, tau, self.T, self.LB, self.L, self.L, self.LB)
            if tau >= self.T: ov.Hide(); d.fade_end(); self.sp = 'none'


def make(t_start, joiner, mode='r2', v12=False):
    ov = Overlay()
    a6 = Act06(ov); a6.v12 = v12
    d = Dispatcher([Inside(ov), a6, White(ov)])
    j = Journey(d, ov, t_start, joiner, 'v12' if v12 else mode)
    return ov, d, j


def view(ov, t, dEV):
    Ls = scene_L(t)
    return [(1 - ov.alpha(k)) * Ls * 2 ** dEV + ov.alpha(k) * ov.fillL for k in DIRS]


def ev(L):
    return math.log2(max(L, FLOOR))


def run(ts, joiner, t_end, dt, mode='r2', v12=False, hitch=False, scrub=None):
    ov, d, j = make(ts, joiner, mode, v12)
    out = []
    t, real, hitched, scrubbed = ts, 0.0, False, False
    while t <= t_end + 1e-9:
        d.dispatch(t, real)
        dEV = d.gradeDEV
        j.step(t, dEV)
        out.append((t, [ev(x) for x in view(ov, t, dEV)], j.sp))
        step = dt
        if hitch and not hitched and joiner and j.sp == 'none' and d.ended:
            step, hitched = 0.5, True
        t += step; real += step
        if scrub and not scrubbed and t >= scrub[0]:
            t, scrubbed = scrub[1], True
    return out


REF = {}


def reference(t0, t1, dt):
    key = (round(t0, 3), round(t1, 3), round(dt, 5))
    if key not in REF:
        rows = run(t0, False, t1, dt)
        REF[key] = {round(t, 3): e for t, e, _ in rows}
    return REF[key]


def judge(rows, ref_of, horizon=40.0):
    """rows: the joiner; ref_of(t) -> the reference view at t (or None). Checks until convergence."""
    conv = None
    for t, e, sp in rows:
        r = ref_of(t)
        if sp == 'none' and r is not None and all(abs(a - b) < 0.02 for a, b in zip(e, r)):
            conv = t; break
    stop = conv if conv is not None else rows[-1][0]
    seg = [(t, e) for t, e, _ in rows if t <= stop + 1e-9]
    worst = {'w025': 0.0, 'w1': 0.0, 'w2': 0.0, 'rate': -9.0, 'frame': 0.0}
    ts = [t for t, _ in seg]
    for k in range(len(DIRS)):
        e = [x[k] for _, x in seg]
        for i in range(1, len(e)):
            worst['frame'] = max(worst['frame'], e[i] - e[i - 1])
        j0 = {0.25: 0, 1.0: 0, 2.0: 0, 4.0: 0}
        for i in range(len(e)):
            for w, key in ((0.25, 'w025'), (1.0, 'w1'), (2.0, 'w2'), (4.0, None)):
                j = j0[w]
                while ts[i] - ts[j] > w + 1e-9: j += 1
                j0[w] = j
                gain = e[i] - min(e[j:i + 1])
                if key: worst[key] = max(worst[key], gain)
                if w >= 1.0: worst['rate'] = max(worst['rate'], gain - (RATE * w + 0.05))
    ok = worst['w025'] <= 0.5 + 1e-6 and worst['w1'] <= 1.0 + 1e-6 and worst['w2'] <= 1.8 + 1e-6 and worst['rate'] <= 1e-6 and conv is not None
    return dict(converged_at=None if conv is None else round(conv, 2), ok=ok, **{k: round(v, 3) for k, v in worst.items()})


def check(ts, dt=1 / 90, mode='r2', v12=False, hitch=False, label=''):
    rows = run(ts, True, ts + 40, dt, mode, v12, hitch)
    ref = run(ts, False, ts + 40, dt, mode, v12)
    refd = {round(t, 4): e for t, e, _ in ref}
    r = judge(rows, lambda t: refd.get(round(t, 4)))
    r.update(join=ts, case=label or ('hitch 0.5 s' if hitch else ''))
    return r


def check_scrub(rewind=True):
    """join at 270 (handed over to act 6, latched at 273), at 285 the timeline is dragged back to 255, run to 320.
    After the drag the joiner must see what the reference sees (no second rise from black, no jump)."""
    Dispatcher.rewind = rewind
    try:
        dt = 1 / 90
        rows = run(270, True, 320, dt, scrub=(285, 255))
        ref = run(255, False, 320, dt)
        refd = {round(t, 4): e for t, e, _ in ref}
        after = [(t, e) for t, e, _ in rows if t < 284.9 and False] or [(t, e) for (t, e, _), prev in zip(rows[1:], rows[:-1]) if t < prev[0]]
        # frames after the drag (time went backwards once): compare with the reference at the same t
        idx = next(i for i in range(1, len(rows)) if rows[i][0] < rows[i - 1][0])
        worst = 0.0
        for t, e, _ in rows[idx + 1:]:
            r = refd.get(round(t, 4))
            if r is None: continue
            worst = max(worst, max(abs(a - b) for a, b in zip(e, r)))
        return {'case': 'scrub 285 -> 255' + ('' if rewind else ' (no rewind rule)'), 'join': 270, 'max_dev_from_reference_ev': round(worst, 3), 'ok': worst <= 0.05}
    finally:
        Dispatcher.rewind = True


def main():
    quick = '--quick' in sys.argv
    joins = [238, 244, 245.5, 249, 255, 260, 263.5, 266, 267, 270, 1125.75, 1130, 1134.25, 1140, 1150, 1180]
    rows = [check(ts) for ts in joins] + [check(263.5, hitch=True), check(270, hitch=True)]
    scrub = check_scrub(True)
    neg = [check(263.5, v12=True, label='v1.2'), check(266, v12=True, label='v1.2'),
           dict(check_scrub(False))]
    Dispatcher.lookahead = False
    neg.append(check(1130, mode='r1', label='r1 fixed-T fade, no look-ahead (DIR13-4)'))
    Dispatcher.lookahead = True
    Inside.suppress = False; neg.append(check(245.5, label='FLASH_TEAR not suppressed')); Inside.suppress = True
    # r1 as a whole (dispatcher without the hand-over state, fade length without look-ahead, fixed-T fade, FlashFor from
    # U12 - 0.25 and suppressed under the spawn fade): a fade that ends at 248.0, inside FLASH_TEAR -> the flash pops up
    Inside.flash_from, Inside.r1, Dispatcher.hands, Dispatcher.lookahead = 0.25, True, False, False
    neg.append(check(248.0 - 3.0 - math.log2(0.2 / 0.004) / RATE, mode='r1', label='r1 whole (FlashFor U12 - 0.25)'))
    Inside.flash_from = 0.75
    rows.append(check(248.0 - 3.0 - math.log2(0.2 / 0.004) / RATE, mode='r1', label='r1 的其余部分 + 只改 FlashFor 到 U12 − 0.75（DIR13-3 单独够不够）'))
    Inside.r1, Dispatcher.hands, Dispatcher.lookahead = False, True, True
    dense = []
    if not quick:
        for a, b, wf in ((175.0, 372.0, False), (1120.0, 1200.0, False), (1120.0, 1200.0, True)):
            White.fixed = wf
            n = int(round((b - a) / 0.1))
            fails = []
            worst = {'w025': 0.0, 'w1': 0.0, 'w2': 0.0, 'rate': -9.0}
            for i in range(n + 1):
                ts = a + i * 0.1
                r = check(ts, dt=1 / 30)
                for k in worst: worst[k] = max(worst[k], r[k])
                if not r['ok']: fails.append(r)
            White.fixed = False
            dense.append({'white': 'pkg/mirrors 962567b + 建议的修改' if wf else ('pkg/mirrors 962567b' if a > 1000 else '—'), 'from': a, 'to': b, 'step': 0.1, 'fps': 30, 'joins': n + 1, 'fails': len(fails), 'worst': {k: round(v, 3) for k, v in worst.items()}, 'first_fails': fails[:10]})
    os.makedirs(DOCS, exist_ok=True)
    with open(os.path.join(DOCS, 'spawn_fade_sim.json'), 'w', encoding='utf-8') as f:
        json.dump({'joins': rows, 'scrub': scrub, 'dense': dense, 'negative_controls': neg}, f, indent=1, ensure_ascii=False)
    head = '| 进场 s | 情况 | 和一直在场的人一样的时刻 s | 0.25 s 升（≤ 0.5） | 1 s（≤ 1.0） | 2 s（≤ 1.8） | 超 0.85 EV/s 多少 | 一帧最多升 | 过 |\n|---|---|---|---|---|---|---|---|---|\n'
    fmt = lambda r, neg=False: '| {} | {} | {} | {} | {} | {} | {} | {} | {} |\n'.format(
        round(r['join'], 2), r.get('case', ''), r.get('converged_at'), r.get('w025', ''), r.get('w1', ''), r.get('w2', ''),
        max(0.0, r['rate']) if 'rate' in r else '', r.get('frame', ''), ('是' if r['ok'] else '**否**') if not neg else ('否（应当不过）' if not r['ok'] else '**是（负对照没复现）**'))
    body = ''.join(fmt(r) for r in rows)
    body += '| 270 | {} | — | — | — | — | — | 拖回以后和一直在场的人最多差 {} EV | {} |\n'.format(scrub['case'], scrub['max_dev_from_reference_ev'], '是' if scrub['ok'] else '**否**')
    dtxt = ''.join('- {from:.0f}–{to:.0f} s（白驱动：{white}），每 {step} s 一个进场、{fps} fps：{joins} 个，**{fails} 个不过**；最坏 0.25 / 1 / 2 s：{w025} / {w1} / {w2} EV，超 0.85 EV/s 最多 {rate} EV\n'.format(
        **{**dd, **dd['worst'], 'rate': max(0.0, dd['worst']['rate'])}) for dd in dense)
    nbody = ''.join(fmt(r, True) if 'w025' in r else '| {} | {} | — | — | — | — | — | 拖回以后最多差 {} EV | {} |\n'.format(
        r['join'], r['case'], r['max_dev_from_reference_ev'], '否（应当不过）' if not r['ok'] else '**是（负对照没复现）**') for r in neg)
    with open(os.path.join(DOCS, 'spawn_fade_sim.md'), 'w', encoding='utf-8') as f:
        f.write('# 迟到的人进场：数值核对（`Director/Tools~/spawn_fade_sim.py` 生成；Python 移植真代码，不是 Unity 里跑的）\n\n'
                '移植的是分发层 v1.3 r2、README_Director §0 第 4 条的出生状态机、门内、第 6 幕，和镜与白 `pkg/mirrors` 962567b 的真白驱动（含 LanbaiGrade）。'
                '看到的亮度 = (1 − a)·场景·2^ΣdEV + a·填色；EV 按 0.004 的地板算。从出生一直量到和一直在场的人看到的一样为止。\n\n'
                + head + body + '\n## 密扫\n\n' + (dtxt or '（--quick：没跑）\n') + '\n## 负对照（应当不过）\n\n' + head + nbody)
    print(head + body)
    print(dtxt)
    print('negative controls:')
    print(head + nbody)
    # the white stretch with the mirrors' current code is a FINDING for pkg/mirrors (reported, not ours to fix): judged
    # on the other stretches and on the proposed fix
    ok = all(r['ok'] for r in rows) and scrub['ok'] and all(dd['fails'] == 0 for dd in dense if dd['white'] != 'pkg/mirrors 962567b') and all(not r['ok'] for r in neg)
    print('ALL OK' if ok else 'SOMETHING FAILED')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
