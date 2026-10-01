"""S4 grade helper for the tear kit: fill <-> screen solving and the PPv2 S4 simulation (with bloom),
using the bible's own simulator (art/lens_cine/ppv2.py + art/bible_work/lutlib_core.py patches)."""
import sys, os, json
import numpy as np
LAN = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(LAN, 'art', 'lens_cine'))
sys.path.insert(0, os.path.join(LAN, 'art', 'bible_work'))
import ppv2  # noqa
from lutlib_core import patch_ppv2  # noqa
patch_ppv2(ppv2)
GF = json.load(open(os.path.join(LAN, 'art', 'grades_final.json')))
S4 = GF['profiles']['S4']['ppv2']
T0_S4 = GF['profiles']['S4']['bloom_T0_scene_linear']


def lin(h):
    return np.array(ppv2.hex_to_lin(h), np.float64)


def fill(h, ev=0.0):
    return lin(h) * 2.0 ** ev


def screen_of(fill_lin, prof=S4):
    return ppv2.display_of(np.asarray(fill_lin, np.float64), prof)


def hexs(srgb01):
    c = np.clip(np.round(np.asarray(srgb01) * 255), 0, 255).astype(int)
    return '#%02X%02X%02X' % tuple(c)


def solve_fill(target_hex, prof=S4, iters=60):
    """linear fill whose S4 display equals target_hex (no bloom)."""
    t = lin(target_hex)
    x = t.copy() + 1e-6
    for _ in range(iters):
        d = ppv2.srgb_to_lin(screen_of(x, prof))
        x = x * np.clip((t + 1e-6) / (d + 1e-6), 0.5, 2.0) ** 0.9
    return x


def fill_as_hdr(x):
    """express a linear fill as Unity HDR picker '#RRGGBB @ +n' (n >= 0 only if max channel > 1)."""
    m = float(np.max(x))
    ev = max(0.0, np.log2(m)) if m > 1 else 0.0
    base = x / 2 ** ev
    return hexs(ppv2.lin_to_srgb(np.clip(base, 0, 1))), ev


def grade(img_lin, prof=S4, bloom=True):
    """scene-linear HxWx3 (Unity fill space) -> display sRGB 0..1 under the profile (PPv2 sim)."""
    return np.clip(ppv2.render(img_lin, prof, with_bloom=bloom), 0, 1)
