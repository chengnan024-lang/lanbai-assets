"""The act 4c / 5 driver as pure functions of t: everything LanbaiInsideDriver.cs writes, computed the same way, so the
reference renders, the checks and the JSON for Unity agree. Fills are scene-linear values solved through the engine
grade (lb_grade.py, S4c) unless the bible gives them.

state(t) -> dict(fog=<LanbaiFog model-B parameter group>, fibre per lip, dot, dEV, overlay, cabin slice, dial, ...)
"""
import functools
import json
import math
import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import inside_def as D  # noqa: E402
import lb_grade as LG  # noqa: E402

OUT = os.path.join(D.HERE, 'out')
FOG_AHEAD_M = 100.0                     # the fog ahead is the next zone's colour, behind the previous one's
FOG_D0, FOG_D1 = 0.0006, D.FOG_DENSITY  # act 4's density -> the inside's, over U9 .. U9 + 2 s (smoothstep)
NADIR_K = 0.80                          # darker below (review r1 / art review r03)
SHEET_FOG_CAP, LIP8_HOLD_M, LIP8_RAMP_M = 0.25, 70.0, 60.0     # r09: cap 0.30 -> 0.25 (art review r08 B2-3; 0.28 lifted 200 by only 0.4 APL and the 197 near sheet to 41)
CROSSED_FADE_M = 300.0
SLEEVE_FOG_K = 0.72                                    # r07 / r09: the air inside the sleeve (forward APL; the side window barely depends on it)
SLEEVE_INNER_CLOTH_K = 1.35                            # r09: the inner plies' cut faces (226 side APL)
SLEEVE_LOOSE_K = 12.0                                  # r08: loose fibres pulled from the thick cloth, inside the sleeve
LOOSE_GAIN = 0.25                                      # the shader's _LooseGain (x the current fibre colour)


def sleeve_weight(t):
    """0 outside lip 8's sleeve, 1 inside (15 m in at the entry, 30 m out past the exit)."""
    s = float(D.dist(t))
    S8 = float(D.dist(D.LIP_T[7]))
    return float(D.ss((s - S8) / 15.0)) * (1.0 - float(D.ss((s - S8 - D.SLEEVE_DEPTH) / 30.0)))


def loose_gain(t):
    """r08 (art pre-review r0 #2: 228 forward had no structure; the 40 m clearance keeps every cloth edge out of the
    forward frame inside the sleeve): the loose fibres x 4 in the sleeve."""
    return 1.0 + (SLEEVE_LOOSE_K - 1.0) * sleeve_weight(t)


def clock(t):
    """the loose threads' clock: = t, easing to a stop over the last 4 s before STOP_T (LanbaiInsideDriver.Clock)."""
    t0 = D.STOP_T - 4.0
    if t <= t0:
        return float(t)
    x = min(max((t - t0) / 4.0, 0.0), 1.0)
    return t0 + 4.0 * (x - x ** 3 + 0.5 * x ** 4)
CODA_BW, CODA_SIDE_K, CODA_TOP_K = 40.0, 0.45, 0.38      # r06: the coda's radial gradient round the dot
AHEAD_K, BEHIND_K, ZENITH_K = 1.0, 0.72, 0.85        # r05: the gradient falls off sideways (bw 100) instead of brightening ahead


@functools.lru_cache(maxsize=None)
def fill_of(hex_target, sid='S4c'):
    lin, s, err = LG.solve_fill(hex_target, sid)
    return tuple(float(x) for x in lin)


def fill_hdr(h, n):
    return tuple(float(x) for x in LG.parse_fill(h, n))


@functools.lru_cache(maxsize=None)
def fibre_fill(k):
    """bible fills for lips 1, 4, 8; between them log-linear interpolation of those fills (keeps luma 200-235)."""
    keys = {kk: np.asarray(fill_hdr(*D.FIBRE_FILL_BIBLE[kk])) for kk in (1, 4, 8)}
    if k in keys:
        return tuple(keys[k])
    a, b = (1, 4) if k < 4 else (4, 8)
    f = (k - a) / (b - a)
    return tuple(np.exp(np.log(keys[a]) * (1 - f) + np.log(keys[b]) * f))


@functools.lru_cache(maxsize=None)
def zone_fill(k):
    if k == 1:
        return fill_hdr(D.FOG_FILL_BIBLE[D.FOG_SCREEN_FIRST], 0)
    if k == 8:
        return fill_hdr(D.FOG_FILL_BIBLE[D.FOG_SCREEN_LAST], 0)
    return fill_of(D.fog_screen(k))


def fog_colour_at_s(s):
    """F(s): zone k's fill from lip k's plane on, linear in fill space between consecutive planes."""
    S = np.asarray(D.S_LIP, float)
    if s <= S[0]:
        return np.asarray(zone_fill(1))
    if s >= S[-1]:
        return np.asarray(zone_fill(8))
    k = int(np.searchsorted(S, s))                  # S[k-1] <= s < S[k]
    f = (s - S[k - 1]) / (S[k] - S[k - 1])
    f = f * f * (3 - 2 * f)
    return np.asarray(zone_fill(k)) * (1 - f) + np.asarray(zone_fill(k + 1)) * f


def fog_params(t):
    s = float(D.dist(t))
    dens = FOG_D0 + (FOG_D1 - FOG_D0) * float(D.ss((t - D.U9) / 2.0))
    mid = fog_colour_at_s(s)
    # r04 (art review r03: the coda was a flat grey card): a little lighter ahead, darker behind and overhead / below.
    # r06 (art review r05 #6): after the sleeve the gradient turns toward the dot and narrows: the bible's #53606E stays
    # straight ahead (where it is measured), the frame's edges fall to ~luma 50, overhead / below ~40.
    c = float(D.ss((t - D.SLEEVE_EXIT_T) / 4.0))
    dd = D.dot_dir()
    bd = np.array([dd[0], 0.0, dd[2]]) * c + np.array([0.0, 0.0, 1.0]) * (1.0 - c)
    bd = bd / np.linalg.norm(bd)
    lerp = lambda a, b: a + (b - a) * c
    # r07 (art pre-review r0 #2: 228 forward was a grey card + a dot): inside the sleeve the air is darker (a tunnel in
    # thick cloth); it lifts at the exit over ~2 s (0.42 EV: within the ramp law) into the coda
    sk = 1.0 + (SLEEVE_FOG_K - 1.0) * sleeve_weight(t)
    return dict(model='B gradient', band_dir=tuple(bd), bw=lerp(100.0, CODA_BW),
                near=tuple(fog_colour_at_s(s + FOG_AHEAD_M) * AHEAD_K * sk),
                far=tuple(fog_colour_at_s(s - FOG_AHEAD_M) * lerp(BEHIND_K, CODA_SIDE_K) * sk),
                zenith=tuple(mid * lerp(ZENITH_K, CODA_TOP_K) * sk), nadir=tuple(mid * lerp(NADIR_K, CODA_TOP_K) * sk),
                shape=(lerp(25.0, 8.0), 90.0, 1.0, 0.0), below=(-90.0, lerp(-15.0, -6.0), 1.0, 0.0),
                density=dens, unity_fog_colour=tuple(mid))


def lip_visibility(k, t):
    """r06 (art review r05 #3, bible "<= 3 lips visible at once"): the two nearest lips ahead are fully there, the third
    fades in (smoothstep) over the run from the last crossing to the next one, the rest are fogged out completely (their
    glow x 0 and their cloth's fog cap -> 1). Lips already crossed: 1 (behind you; the fog does the rest).
    Continuous at every crossing: the third lip reaches 1 exactly when the nearest is crossed and it becomes the second.
    r07 (art review r06 B1): lip 8's ring would sit inside lip 7's hole round the dot (a target): it also waits until
    lip 7 is 70 m away and fades in over 60 m (~4 s), so it is never drawn inside lip 7 round the dot."""
    s = float(D.dist(t))
    S = [float(D.dist(x)) for x in D.LIP_T]
    if s >= S[k - 1]:                                # 总导演终审 #4: crossed lips fade out behind (D-02 looking back)
        s_out = S[k - 1] + (D.SLEEVE_DEPTH if k == 8 else 0.0)      # lip 8: crossed once the sleeve's exit is
        return 1.0 if s < s_out else 1.0 - float(D.ss(np.clip((s - s_out) / CROSSED_FADE_M, 0.0, 1.0)))
    ahead = [i for i in range(8) if S[i] > s]
    rank = ahead.index(k - 1)
    if rank <= 1:
        v = 1.0
    elif rank >= 3:
        v = 0.0
    else:
        prev = max([x for x in S if x <= s] + [0.0])
        x = (s - prev) / max(S[ahead[0]] - prev, 1e-3)
        v = float(D.ss(np.clip(x, 0.0, 1.0)))
    if k == 8:
        v *= float(D.ss(np.clip((s - (S[6] - LIP8_HOLD_M)) / LIP8_RAMP_M, 0.0, 1.0)))
    return v


def lip_material(k, st=None):
    """r06 (art review r05 #1, #2): fibres x 3 in a narrower rim, the fringe x 2.6; the cloth's own fog capped at 0.30 so
    it stays 12-20 luma darker than the air in its opening; the weave streaks at ~20 % contrast; folds +-28 %, closer."""
    Hk = [1000.0, 790.0, 940.0, 525.0, 615.0, 345.0, 285.0, 195.0][k - 1]
    vis = 1.0 if st is None else lip_visibility(k, st['t'])
    return dict(cloth=fill_of(D.CLOTH_SCREEN), fibre=fibre_fill(k), roll=0.0, weave_scale=40.0, weave_amount=0.02,
                lip_glow=3.15 * vis, lip_w=max(0.5, 0.002 * Hk), band=(0.07 * vis, 0.04 * Hk), fringe_gain=2.75 * vis,
                thread_rim=0.6 * vis, folds=(0.08 * Hk, 0.5 * Hk, 0.0, 0.35 * Hk), fog_cap_cloth=SHEET_FOG_CAP, vis=vis)


FLASH_DOT_GLOW, FLASH_DOT_GAIN = 1.5, 1.0             # D-20: the dot's glow grows inside FLASH_TEAR's rise


def dot_flash(t):
    """(glow scale, gain scale) of the dot during FLASH_TEAR (D-20; LanbaiInsideDriver.WriteDot)."""
    k = min(max(delta_ev(t) / 1.5, 0.0), 1.0)
    return 1.0 + FLASH_DOT_GLOW * k, 1.0 + FLASH_DOT_GAIN * k


def delta_ev(t):
    """this act's exposure events: FLASH_TEAR only (the U9 tube flash belongs to the gate / timeline)."""
    if t < D.FLASH_T0:
        return 0.0
    if t < D.FLASH_T0 + 0.4:
        return 1.5 * (t - D.FLASH_T0) / 0.4
    if t < D.FLASH_T0 + 0.5:
        return 1.5
    if t < D.U12:
        return 1.5 * (1.0 - (t - D.FLASH_T0 - 0.5) / 0.25)
    return 0.0


def cabin_slice(t):
    """the crossing light band: (front z in bus coordinates, front soft m, tail m, cover, colour key k, level 0..1).
    Bus z runs -3.5 (rear) .. +3.5 (front). Lip 8: sweeps in front -> back over 2.4 s and stays (cover 1), then from
    229.6 retreats from the REAR toward the front over 2.4 s (so the front rows stay lit ~6 s; review r1)."""
    for k in range(1, 9):
        t0, dur = D.BAND_START[k - 1], D.BAND_SWEEP[k - 1]
        if k < 8:
            if t0 <= t < t0 + dur + 1.2:
                x = (t - t0) / dur
                return dict(k=k, front=3.6 - 7.6 * x, soft=1.5, tail=3.5, cover=0.0, level=1.0)
        else:
            out0 = D.SLEEVE_BAND_END - 2.4
            if t0 <= t < out0:
                x = min((t - t0) / 2.4, 1.0)
                return dict(k=8, front=3.6 - 7.6 * x, soft=1.5, tail=3.5, cover=1.0, level=1.0)
            if out0 <= t < D.SLEEVE_BAND_END:
                x = (t - out0) / 2.4
                return dict(k=8, front=-4.0 + 7.6 * x, soft=1.5, tail=0.0, cover=-1.0, level=1.0)   # -1: lit AHEAD of the edge
    return None


def dial(t):
    """the radio dial (bible fill #FF7B00 @ +2.13 on 'ein Lichtchen', 3 s linear), out with the black mask."""
    base = np.asarray(fill_hdr('#FF7703', 0.71))                 # act 2's dial fill (bible §6·2)
    bright = np.asarray(fill_hdr('#FF7B00', 2.13))
    x = np.clip((t - D.LICHT_DIAL_T) / 3.0, 0, 1)
    c = base * (1 - x) + bright * x
    if t >= D.FLASH_T0 + 0.5:
        c = c * max(0.0, 1.0 - (t - D.FLASH_T0 - 0.5) / 0.25)
    return tuple(c)


def overlay(t, scene_L=None):
    """act 5 black: 248.39 -> 248.64 EvOverlayAlpha from the frame's luminance to #030409 (S4c fill #030400 x 2^-dEV),
    then at U12 the same frame S6's fill #090200 (cut 1)."""
    t0 = D.FLASH_T0 + 0.5
    if t < t0:
        return None
    Lb = 0.00129
    if t < D.U12:
        Ls = scene_L if scene_L is not None else (90 / 255.0) ** 2.2
        x = (t - t0) / 0.25
        a = max(Lb, 0.004) * (Lb / max(Lb, 0.004)) ** x
        L = Ls * (Lb / Ls) ** x
        alpha = float(np.clip((Ls - L) / (Ls - Lb), 0, 1))
        return dict(fill=fill_hdr('#030400', 0), alpha=alpha, dEV=delta_ev(t), grade='S4c')
    return dict(fill=fill_hdr('#090200', 0), alpha=1.0, dEV=0.0, grade='S6')


def state(t):
    fp = fog_params(t)
    k, f = D.fog_zone_weights(t)
    core, glow, gain = D.dot_size(t)
    return dict(t=t, s=float(D.dist(t)), v=float(D.speed(t)), fog=fp, fog_zone_hex=D.to_hex(LG.display(np.asarray(fp['zenith']), 'S4c') / 255.0),
                dot_core=fill_hdr(*D.DOT_FILL), dot=(core, glow, gain), dEV=delta_ev(t), slice=cabin_slice(t), dial=dial(t),
                overlay=overlay(t), ambient=(tuple(np.asarray(fill_hdr(D.CABIN_AMBIENT[0], 0)) * D.CABIN_AMBIENT[1]) if t >= D.U9 else None))


if __name__ == '__main__':
    for t in (179.6, 181, 185, 193.9, 197, 205, 218.75, 226, 232, 240, 246.4, 248.0, 248.5, 248.64):
        st = state(t)
        print('%.2f s %.0f v %.1f zone %s dens %.4f dEV %.2f slice %s dot %s' % (t, st['s'], st['v'], st['fog_zone_hex'], st['fog']['density'],
              st['dEV'], st['slice'] and (st['slice']['k'], round(st['slice']['front'], 2)), tuple(round(x, 2) for x in st['dot'])))
