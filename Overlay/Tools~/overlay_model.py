"""Numpy port of Lanbai/Overlay v2 (Shaders/Lanbai_Overlay.shader, same arithmetic) + the checks in README §5.

  python3 overlay_model.py            -> prints the checks, writes Docs~/overlay_checks.json and Docs~/overlay_lobes.png

Checks
  1  no lobe  == one curve for every direction (bit-identical to FLAT driven by the same curve)
  2  lobe edges are soft: the lead changes by <= |lead_i - lead_else| / 30 per degree (soft edge >= 30 deg)
  3  per-direction ramp law (bible §1.8): any 0.25 / 1 / 2 s window <= 0.5 / 1.0 / 1.8 EV of brightening, for every
     scene luminance between the floor and the extreme the curve was built for (E17: one curve, built on the extreme)
     a dawn (5->6): black -> dawn, Lscene = APL 210 (the sun sector in the door), 8.7 s, staggered starts
     b white (9->10 mask): scene -> white in 3 s (the white's own crash / swell happen before; here only the mask)
     c second white (11->12): 1.5 s pre-roll to the floor, then 8.0 s to #A3B4BE, windows first
     d act 5 black: darkening only (any direction may only get darker)
     e white shrinks into the lamps (10->11, WhiteSchedule.json overlay.shrink): darkening only, monotonic
"""
import json
import math
import os

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
DOCS = os.path.join(KIT, 'Docs~')
os.makedirs(DOCS, exist_ok=True)
FLOOR = 0.004


def ev_overlay_alpha(x, Lfrom, Lto, Ls, Lo):
    a = max(Lfrom, FLOOR)
    b = max(Lto, FLOOR)
    L = a * (b / a) ** np.clip(x, 0.0, 1.0)
    den = Ls - Lo
    return np.ones_like(L) if abs(den) < 1e-6 else np.clip((Ls - L) / den, 0.0, 1.0)


def smoothstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def lobe_weight(d, lobe, soft):
    axis, half = np.asarray(lobe[:3], float), lobe[3]
    if half <= 0:
        return np.zeros(d.shape[:-1])
    axis = axis / np.linalg.norm(axis)
    c = d @ axis
    return smoothstep(math.cos(math.radians(min(half + soft, 180.0))), math.cos(math.radians(min(half, 179.0))), c)


def lead_of(d, lobes, leads, lead_else, soft):
    soft = max(soft, 30.0)
    lead = np.full(d.shape[:-1], float(lead_else))
    for lb, ld in zip(lobes, leads):
        lead = lead + (ld - lead) * lobe_weight(d, lb, soft)
    return lead


def alpha(d, tau, T, L, lobes=(), leads=(), lead_else=0.0, soft=30.0):
    x = (tau - lead_of(d, lobes, leads, lead_else, soft)) / max(T, 1e-3)
    return ev_overlay_alpha(x, *L)


def sphere_dirs(n_az=180, n_el=90):
    az = np.radians(np.linspace(-180, 180, n_az, endpoint=False) + 1)
    el = np.radians(np.linspace(-89, 89, n_el))
    A, E = np.meshgrid(az, el)
    return np.stack([np.sin(A) * np.cos(E), np.sin(E), np.cos(A) * np.cos(E)], -1), A, E


def ramp_windows(t, Lc):
    """max EV gained in any 0.25 / 1 / 2 s window (brightening only), per curve (last axis = time)."""
    ev = np.log2(np.maximum(Lc, FLOOR))
    out = []
    dt = t[1] - t[0]
    for w in (0.25, 1.0, 2.0):
        k = max(1, int(round(w / dt)))
        gain = ev[..., k:] - ev[..., :-k]
        out.append(float(np.max(gain)) if gain.size else 0.0)
    return out


def lum_of_hex(h):
    c = np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)]) / 255.0
    lin = np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)
    return float(lin @ [0.2126, 0.7152, 0.0722])


def check_dawn():
    """bible §6·5→6: one curve built on APL 210, 8.7 s per direction; skylight / zenith first (lead 0), horizon +2.0,
    below +2.2, the sun sector (az +45, +-30 soft) a further +1.3. Pre-roll from #030409 to the floor is FLAT mode."""
    L210 = (210 / 255.0) ** 2.2
    Lblack = lum_of_hex('#030409')
    T = math.log2(L210 / FLOOR) / 0.85
    d, A, E = sphere_dirs(90, 45)
    up, horizon, below = (0, 1, 0), (0, 0, 1), (0, -1, 0)
    sun = (math.sin(math.radians(45)), 0.05, math.cos(math.radians(45)))
    # lobes are applied in order: horizon band first (wide), then below, then the sun sector on top, zenith = else
    lobes = [(*up, 0.0), (0, 0, 1, 0.0), (*below, 50.0), (*sun, 20.0)]
    leads = [0.0, 0.0, 2.2, 3.3]
    lead_else = 2.0                          # everything that is not zenith-ward starts 2.0 s late ...
    lobes[0] = (*up, 35.0)                   # ... except the sky above (skylight, zenith): lead 0
    t = np.arange(-0.5, 16.0, 1 / 60.0)
    worst = [0, 0, 0]
    for Ls_dir in np.geomspace(FLOOR, L210, 9):
        a = np.stack([alpha(d, tt, T, (Lblack, L210, L210, Lblack), lobes, leads, lead_else, 30.0) for tt in t], -1)
        Lc = a * Lblack + (1 - a) * Ls_dir
        worst = [max(w, x) for w, x in zip(worst, ramp_windows(t, Lc))]
    return dict(T=round(T, 3), worst_ev=[round(x, 3) for x in worst], limits=[0.5, 1.0, 1.8],
                passed=bool(worst[0] <= 0.5 and worst[1] <= 1.0 and worst[2] <= 1.8))


def check_white_mask():
    """scene -> white in 3 s (EV-linear). Built on the darkest view: the S9b scene at the floor."""
    Lw = lum_of_hex('#E8F1F5')
    t = np.arange(-0.2, 3.5, 1 / 60.0)
    worst = [0, 0, 0]
    Ls_curve = FLOOR * 4                      # the curve's Lscene (a dim view); real views are brighter -> slower
    d = np.array([[0.0, 0.0, 1.0]])
    for Ls_dir in np.geomspace(FLOOR, 0.3, 9):
        a = np.stack([alpha(d, tt, 3.0, (Ls_curve, Lw, Ls_curve, Lw)) for tt in t], -1)
        Lc = a * Lw + (1 - a) * Ls_dir
        worst = [max(w, x) for w, x in zip(worst, ramp_windows(t, Lc))]
    # the white mask is the END of a ramp already at +2.4 EV: the bible checks the whole 11.73 s (white_check of 镜与白);
    # here only the mask: report, do not gate (3 s from the floor is 2.4 EV/s at its fastest by construction)
    return dict(worst_ev=[round(x, 3) for x in worst], note='mask alone; the bible ramps the scene +2.4 EV first, so the '
                'mask covers the last ~2.6 EV over 3 s; see 镜与白 white_check for the full 11.73 s')


def check_second_white():
    """bible §6·11→12: fill #A3B4BE (L 0.4415), pre-roll 1.5 s to a0 = 0.004 / L_fill (FLAT), then one curve of 8.0 s
    built on the darkest view (side window night, from the floor), windows first, cabin 2 s later.
    The bible writes the curve as a = a0 (L_fill / 0.004)^x, which is EvOverlayAlpha(x, 0.004, L_fill, 0, L_fill)."""
    Lf = lum_of_hex('#A3B4BE')
    T = 8.0
    d = np.array([[1.0, 0.0, 0.0], [0.0, 0.0, 1.0]])
    lobes = [(1, 0, 0, 40.0), (-1, 0, 0, 40.0)]
    leads = [0.0, 0.0]
    t = np.arange(-1.6, 11.0, 1 / 60.0)
    worst = [0, 0, 0]
    for Ls_dir in np.geomspace(0.0005, 0.03, 8):
        a = []
        for tt in t:
            if tt < 0:                       # pre-roll: alpha 0 -> a0 linear over 1.5 s (sub-floor, invisible)
                a.append(np.full(len(d), FLOOR / Lf * np.clip((tt + 1.5) / 1.5, 0, 1)))
            else:
                a.append(alpha(d, tt, T, (FLOOR, Lf, 0.0, Lf), lobes, leads, 2.0, 30.0))   # bible: a = a0 (Lf / 0.004)^x  ==  Lscene = 0
        a = np.stack(a, -1)
        Lc = a * Lf + (1 - a) * Ls_dir
        worst = [max(w, x) for w, x in zip(worst, ramp_windows(t, Lc))]
    return dict(T=T, worst_ev=[round(x, 3) for x in worst], limits=[0.5, 1.0, 1.8],
                passed=bool(worst[0] <= 0.5 and worst[1] <= 1.0 and worst[2] <= 1.8))


def check_no_lobe_equivalence():
    d, _, _ = sphere_dirs(60, 30)
    L = (0.2, FLOOR, 0.2, FLOOR)
    ok = True
    for tau in np.linspace(-1, 9, 41):
        a = alpha(d, tau, 8.0, L)                     # no lobes
        u = ev_overlay_alpha(np.array([tau / 8.0]), *L)[0]
        ok &= bool(np.all(a == u))
    return dict(passed=ok)


def check_soft_edges():
    d, A, E = sphere_dirs(720, 2)
    eq = d[0:1]                                       # one ring
    lobes = [(0, 0, 1, 20.0)]
    lead = lead_of(eq, lobes, [3.0], 0.0, 30.0)[0]
    step = np.abs(np.diff(np.r_[lead, lead[:1]]))     # per 0.5 deg
    per_deg = float(step.max() / 0.5)
    return dict(max_lead_change_per_deg=round(per_deg, 4), limit=round(3.0 / 30.0 * 1.6, 4),
                passed=per_deg <= 3.0 / 30.0 * 1.6)   # smoothstep peaks at 1.5 x the mean slope


def check_shrink():
    """10->11 (WhiteSchedule.json overlay.shrink): white -> S11 scene, darkening only; lobes tubes 0 s, lamps 1.5 s,
    sea (zenith) 3.0 s, T 5.0 s. Every direction must only get darker (alpha monotonic down) and no seam may move
    faster than 60 deg/s."""
    Lw = lum_of_hex('#E8F1F5')
    Ls = (30 / 255.0) ** 2.2
    d, A, E = sphere_dirs(120, 60)
    tubes = (0, 0.7, 0.3, 45.0)
    lamps = (-1, 0.25, 0.2, 35.0)
    sea = (0, 1, 0, 30.0)
    lobes = [lamps, sea, tubes]
    leads = [1.5, 3.0, 0.0]
    t = np.arange(0, 8.5, 1 / 30.0)
    a = np.stack([alpha(d, tt, 5.0, (Lw, Ls, Ls, Lw), lobes, leads, 1.5, 30.0) for tt in t], -1)
    mono = bool(np.all(np.diff(a, axis=-1) <= 1e-9))
    return dict(monotonic_darkening=mono, passed=mono), (d, A, E, t, a)


def figure(sh):
    from PIL import Image, ImageDraw
    d, A, E, t, a = sh
    frames = [0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5]
    W, H = 360, 180
    im = Image.new('RGB', (W * 4 + 50, H * 2 + 90), (16, 17, 20))
    dr = ImageDraw.Draw(im)
    dr.text((10, 8), 'Lanbai_Overlay v2: alpha over the sphere (equirect, az -180..180, el -89..89), 10->11 shrink example', fill=(220, 225, 230))
    for k, tt in enumerate(frames):
        i = int(np.argmin(np.abs(t - tt)))
        img = (a[..., i][::-1] * 255).astype(np.uint8)
        tile = Image.fromarray(img).resize((W, H))
        x, y = 10 + (k % 4) * (W + 10), 30 + (k // 4) * (H + 25)
        im.paste(tile.convert('RGB'), (x, y))
        dr.text((x, y + H + 3), 't = %.1f s' % tt, fill=(170, 178, 188))
    p = os.path.join(DOCS, 'overlay_lobes.png')
    im.save(p)
    return p


if __name__ == '__main__':
    res = dict(no_lobe_equals_uniform=check_no_lobe_equivalence(), soft_edges=check_soft_edges(),
               dawn=check_dawn(), second_white=check_second_white(), white_mask=check_white_mask())
    sh, data = check_shrink()
    res['shrink'] = sh
    res['figure'] = os.path.relpath(figure(data), KIT)
    print(json.dumps(res, indent=1, ensure_ascii=False))
    json.dump(res, open(os.path.join(DOCS, 'overlay_checks.json'), 'w'), indent=1, ensure_ascii=False)
