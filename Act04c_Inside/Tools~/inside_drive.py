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
FOG_AHEAD_M = 250.0                     # the fog ahead is the next zone's colour, behind the previous one's
FOG_D0, FOG_D1 = 0.0006, D.FOG_DENSITY  # act 4's density -> the inside's, over U9 .. U9 + 2 s (smoothstep)
NADIR_K = 0.85                          # a little darker below (<= 6-8 L*, review r1)


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
    return dict(model='B gradient', band_dir=(0.0, 0.0, 1.0), bw=180.0,
                near=tuple(fog_colour_at_s(s + FOG_AHEAD_M)), far=tuple(fog_colour_at_s(s - FOG_AHEAD_M)),
                zenith=tuple(mid), nadir=tuple(mid * NADIR_K), shape=(25.0, 90.0, 1.0, 0.0), below=(-90.0, -15.0, 1.0, 0.0),
                density=dens, unity_fog_colour=tuple(mid))


def lip_material(k, st=None):
    Hk = [1000.0, 790.0, 940.0, 525.0, 615.0, 345.0, 285.0, 195.0][k - 1]
    return dict(cloth=fill_of(D.CLOTH_SCREEN), fibre=fibre_fill(k), roll=0.0, weave_scale=40.0, weave_amount=0.45,
                lip_glow=0.35, lip_w=max(1.5, 0.006 * Hk), band=(0.08, 0.08 * Hk), fringe_gain=0.65, thread_rim=0.6)


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
