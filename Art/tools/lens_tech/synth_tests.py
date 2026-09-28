#!/usr/bin/env python3
"""
Synthetic self-tests for flashcheck.py: a crude 320x180 "seat view" (hFOV 90) of the gate with ten big
ceiling tubes, the tear, the plunge and the dawn, plus the white transitions. Compares the flicker/flash/ramp
specs in lens_cine.md and lens_lookdev.md with the Lanbai tech rules in lens_tech.md.
Everything is in display-linear relative luminance (what the screen shows), which is what the rules are about.
"""
import json, math, os
import numpy as np
import flashcheck as fc
import flicker_schedule as fs

W, H, FPS = 320, 180, 60
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "out")
yy, xx = np.mgrid[0:H, 0:W].astype(np.float32)
u, v = xx / W, yy / H


def lin_to_u8(rgb):
    rgb = np.clip(rgb, 0, 1)
    s = np.where(rgb <= 0.0031308, rgb * 12.92, 1.055 * rgb ** (1 / 2.4) - 0.055)
    return (s * 255 + 0.5).astype(np.uint8)


# ---------------- layers (linear RGB) ----------------
SKY = np.array([0.0020, 0.0030, 0.0068])                       # ~#070B14 void
TEAR_C = np.array([0.80, 0.70, 1.00])
d_tear = ((u - 0.5) / 0.035) ** 2 + ((v - 0.42) / 0.30) ** 2
tear = np.exp(-d_tear * 1.2)[..., None] * TEAR_C * 0.9 + np.exp(-np.sqrt(d_tear) * 0.9)[..., None] * np.array([0.10, 0.04, 0.22])
cabin_mask = ((v < 0.28) | (u < 0.10) | (u > 0.90) | (v > 0.80)).astype(np.float32)
CABIN_C = np.array([0.0125, 0.0115, 0.0105])                   # tube-lit cabin at the gate (grey #1E1C1D)
tubes = []
for row, (y0, h, w) in enumerate([(0.03, 0.07, 0.15), (0.16, 0.04, 0.10)]):
    for col in range(5):
        cx = 0.10 + col * 0.20
        m = ((np.abs(u - cx) < w / 2) & (np.abs(v - y0 - h / 2) < h / 2)).astype(np.float32)
        tubes.append(m)
TUBE_C = np.array([0.86, 0.83, 0.70])                          # cream diffuser ~#F0EBD6
exterior = (1 - cabin_mask)[..., None] * (SKY + tear)
DAWN = (1 - cabin_mask)[..., None] * (np.array([0.25, 0.30, 0.42]) * (1.0 - 0.5 * v)[..., None]) + cabin_mask[..., None] * np.array([0.018, 0.016, 0.016])
BLACK = np.array([0.0006, 0.0006, 0.0012])


def gate_frame(levels, exposure_ev=0.0, black=0.0):
    img = exterior + cabin_mask[..., None] * (CABIN_C * levels.mean() + 0.0015)
    for m, lv in zip(tubes, levels):
        img = img * (1 - m[..., None]) + m[..., None] * TUBE_C * lv
    img = img * 2.0 ** exposure_ev
    return img * (1 - black) + BLACK * black


def shimmer(t, i):
    # sub-threshold continuous wobble: +-6 %, < 2 Hz, per tube
    return 1.0 + 0.06 * math.sin(2 * math.pi * (0.7 + 0.11 * i) * t + i * 1.7) * math.sin(2 * math.pi * 0.23 * t + i)


# ---------------- scenarios ----------------
def seq_lanbai_gate(t0=-40.0, t1=10.0):
    ev = fs.make()
    for k in range(int((t1 - t0) * FPS)):
        t = t0 + k / FPS
        lv = fs.level_at(ev, t) * np.array([shimmer(t, i) for i in range(10)])
        e, blk = 0.0, 0.0
        if -0.4 <= t < 0.0:          # entry flash: +1.5 EV over 0.4 s, EV-linear
            e = 1.5 * (t + 0.4) / 0.4
            lv = lv * (1 + 0.5 * (t + 0.4) / 0.4)
        elif 0.0 <= t < 0.1:
            e, lv = 1.5, lv * 1.5
        elif 0.1 <= t < 0.35:         # fall to black over 0.25 s
            x = (t - 0.1) / 0.25
            e, lv, blk = 1.5 * (1 - x), lv * 1.5 * (1 - x), x
        if t >= 0.35 and t < 3.35:
            yield BLACK[None, None, :] * np.ones((H, W, 1))
            continue
        if t >= 3.35:                 # dawn, EV-linear from the mesopic floor (0.004) over 7 s
            x = min((t - 3.35) / 7.0, 1.0)
            Lb, Lf, Ld = 0.0008, 0.004, float((DAWN @ fc.LUMA).mean())
            L = Lf * (Ld / Lf) ** x
            a = (L - Lb) / (Ld - Lb)
            yield DAWN * a + BLACK * (1 - a)
            continue
        yield gate_frame(lv, e, blk)


def seq_cine_gate(t0=-40.0, t1=10.0, seed=1):
    """lens_cine 5.4/5.5: stutters 60-200 ms off, rising from 1 per 10 s to 3 per s (no refractory), FLASH_TEAR
    0->1 in 0.25 s ease-in (+2 EV), hold 0.15 s, snap to black in 0.10 s; dawn: black overlay 1->0 in 5 s ease-out cubic."""
    rng = np.random.default_rng(seed)
    dips, t = [], -105.0
    while t < -0.5:
        r = 0.1 * 30 ** ((t + 105) / 104.5)
        t += rng.exponential(1 / r)
        dips.append((t, rng.uniform(0.06, 0.2)))
    for k in range(int((t1 - t0) * FPS)):
        t = t0 + k / FPS
        lv = np.ones(10)
        for (a, d) in dips:
            if a <= t < a + d:
                lv[:] = 0.05
        e, blk = 0.0, 0.0
        if -0.5 <= t < -0.25:
            x = (t + 0.5) / 0.25
            e = 2.0 * x ** 2
        elif -0.25 <= t < -0.10:
            e = 2.0
        elif -0.10 <= t < 0.0:
            x = (t + 0.10) / 0.10
            e, blk = 2.0 * (1 - x), x
        if 0.0 <= t < 3.0:
            yield BLACK[None, None, :] * np.ones((H, W, 1))
            continue
        if t >= 3.0:
            x = min((t - 3.0) / 5.0, 1.0)
            a = 1 - (1 - x) ** 3
            yield DAWN * a + BLACK * (1 - a)
            continue
        yield gate_frame(lv, e, blk)


def seq_lookdev_gate(t0=-30.0, t1=0.0, seed=2):
    """lens_lookdev 3.2: each tube its own random sequence, dips to 5-40 % for 40-120 ms, rate 0.1 -> 3 per s, neighbours 30 %."""
    rng = np.random.default_rng(seed)
    per = []
    for i in range(10):
        t, L = -105.0, []
        while t < 0:
            r = 0.1 * 30 ** ((t + 105) / 105)
            t += rng.exponential(1 / r)
            L.append((t, rng.uniform(0.04, 0.12), rng.uniform(0.05, 0.4)))
        per.append(L)
    for k in range(int((t1 - t0) * FPS)):
        t = t0 + k / FPS
        lv = np.ones(10)
        for i in range(10):
            for (a, d, l) in per[i]:
                if a <= t < a + d:
                    lv[i] = min(lv[i], l)
                    for j in (i - 1, i + 1):
                        if 0 <= j < 10 and j // 5 == i // 5 and ((i * 7 + j * 3 + int(a * 10)) % 10) < 3:
                            lv[j] = min(lv[j], l)
        yield gate_frame(lv)


def seq_strobe(hz, secs=4.0):
    for k in range(int(secs * FPS)):
        t = k / FPS
        on = (t * hz) % 1.0 < 0.5
        yield (DAWN * (2.5 if on else 0.4))


def scene_img(apl_luma):
    """A frame with some structure whose mean display luma is about apl_luma."""
    base = DAWN / (DAWN @ fc.LUMA).mean()
    return base * (apl_luma / 255.0) ** 2.2


def overlay(img, col, a):
    return img * (1 - a) + np.array(col)[None, None, :] * a


def hex_lin(h):
    c = np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def seq_white_cine():
    """9b -> 10 per lens_cine: WHITE_RAMP postExposure 0 -> +3 EV, ease-in cubic over 5 s, then the overlay to #E8F1F5 in 1 s."""
    src = scene_img(80)
    W_ = hex_lin("#E8F1F5")
    for k in range(int(9 * FPS)):
        t = k / FPS - 1.0
        if t < 0:
            yield src
            continue
        if t < 5:
            yield src * 2 ** (3 * (t / 5) ** 3)
            continue
        a = min((t - 5) / 1.0, 1.0)
        yield overlay(src * 8, W_, a)


def seq_white_lanbai(vr=True):
    """9b -> 10 per lens_tech: crash +1 EV in 1.2 s, swell +1 -> +2.4 EV over 6 s (EV-linear), overlay EV-linear to the
    VR white #D7E3E8 over the last 3 s."""
    src = scene_img(80)
    W_ = hex_lin("#D7E3E8" if vr else "#E8F1F5")
    Lw = float(W_ @ fc.LUMA)
    for k in range(int(10 * FPS)):
        t = k / FPS - 1.0
        if t < 0:
            yield src
            continue
        if t < 1.2:
            yield src * 2 ** (1.0 * t / 1.2)
            continue
        e = 1.0 + 1.4 * min((t - 1.2) / 6.0, 1.0)
        img = src * 2 ** e
        if t >= 4.2:
            L0 = float((img @ fc.LUMA).mean())
            x = min((t - 4.2) / 3.0, 1.0)
            L = L0 * (Lw / L0) ** x
            a = (L - L0) / (Lw - L0) if Lw > L0 else x
            img = overlay(img, W_, a)
        yield img


def seq_second_white(cine=True):
    src = scene_img(30)
    if cine:   # overlay 0 -> 1 linear in 2.5 s to #E8F1F5, hold 1 s, 1 -> 0 in 4 s
        W_ = hex_lin("#E8F1F5")
        for k in range(int(9 * FPS)):
            t = k / FPS - 0.5
            a = 0 if t < 0 else (t / 2.5 if t < 2.5 else (1 if t < 3.5 else max(0, 1 - (t - 3.5) / 4)))
            yield overlay(src, W_, a)
    else:      # lens_tech: EV-linear to #A3B4BE over 6.5 s, hold 1.5 s, EV-linear back over 4 s
        W_ = hex_lin("#A3B4BE")
        Ls, Lw = float((src @ fc.LUMA).mean()), float(W_ @ fc.LUMA)
        for k in range(int(13 * FPS)):
            t = k / FPS - 0.5
            if t < 0:
                x = 0
            elif t < 6.5:
                x = t / 6.5
            elif t < 8.0:
                x = 1
            else:
                x = max(0.0, 1 - (t - 8.0) / 4)
            L = Ls * (Lw / Ls) ** x
            yield overlay(src, W_, (L - Ls) / (Lw - Ls))


def run():
    os.makedirs(OUT, exist_ok=True)
    cases = [
        ("A_lanbai_gate_plunge_dawn", seq_lanbai_gate),
        ("B_cine_gate_plunge_dawn", seq_cine_gate),
        ("C_lookdev_gate_flicker", seq_lookdev_gate),
        ("D1_strobe_4Hz_sanity", lambda: seq_strobe(4.0)),
        ("D2_strobe_2.5Hz_sanity", lambda: seq_strobe(2.5)),
        ("E1_cine_white_9b_to_10", seq_white_cine),
        ("E2_lanbai_white_9b_to_10_VR", seq_white_lanbai),
        ("F1_cine_second_white_11_to_12", lambda: seq_second_white(True)),
        ("F2_lanbai_second_white_11_to_12", lambda: seq_second_white(False)),
    ]
    reports = {}
    for name, gen in cases:
        frames = (lin_to_u8(f) for f in gen())
        rep, ser = fc.analyze(frames, FPS, 90.0, name)
        fc.plot(ser, rep, os.path.join(OUT, f"check_{name}.png"))
        reports[name] = rep
        print(f"{name:34s} flashes/1s={rep['max_general_flashes_in_any_1s']} WCAG={rep['wcag_2_3_1']:4s} "
              f"Lanbai={rep['lanbai_flash_rule']:4s} rise0.25={rep['max_rise_ev_0.25s']:5.2f} rise1={rep['max_rise_ev_1s']:5.2f} "
              f"rise2={rep['max_rise_ev_2s']:5.2f} fall0.25={rep['max_fall_ev_0.25s']:5.2f} peakAPL={rep['peak_apl_luma']}")
    with open(os.path.join(OUT, "selftest_reports.json"), "w") as fh:
        json.dump(reports, fh, indent=1)


if __name__ == "__main__":
    run()
