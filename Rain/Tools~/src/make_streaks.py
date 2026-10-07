"""RainStreak_Atlas8x1_512: 8 motion-blurred raindrop streaks, each cell 64 x 512 (u across, v along the fall).

Physics (Garg & Nayar 2006): a falling drop is a ~165 deg fish-eye; under one lamp it shows a reflection glint and a
refraction glint whose brightness is modulated by the drop's shape oscillation (Rayleigh n=2 mode,
f = sqrt(8 sigma / (rho R^3)) / 2pi ~ 120 Hz for R = 1 mm). Over a 1/30 s persistence the streak therefore carries
3-6 soft 'beads'. The two glints sit on opposite sides of the drop and separate into a faint twin line when the lamp
is to the side.  Values are LUMINANCE (grey RGB) and ALPHA; the colour and the lamp-dependent brightness are applied
by Shaders/Lanbai_RainParticles.shader (only lit where lit).
Cell layout: 8 x 1, cell 0 at the left. v = 0 (bottom of the PNG) = the TAIL (older end, where the drop was),
v = 1 (top) = the HEAD (where the drop is now) - matches a Unity Stretched Billboard (texture v runs along velocity).
Core width: ~1/5 of the cell (the quad is wider than the visible line so VR MSAA never sees a 1-px sliver).
"""
import json, os, sys
import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import rainpaths as RP
OUT = sys.argv[1] if len(sys.argv) > 1 else RP.out_dir()
CW, CH, NCELL = 64, 512, 8
rng = np.random.default_rng(77)


def gauss(x, s):
    return np.exp(-0.5 * (x / s) ** 2)


def streak(kind, seed):
    r = np.random.default_rng(seed)
    y = (np.arange(CH) + 0.5) / CH            # 0 = tail (PNG bottom) .. 1 = head (PNG top)
    x = (np.arange(CW) + 0.5) / CW - 0.5
    X, Y = np.meshgrid(x, y)
    # envelope along the streak: soft at both ends, brighter toward the head (the eye weights the latest position)
    env = np.clip(Y / 0.12, 0, 1) ** 1.5 * np.clip((1 - Y) / 0.05, 0, 1) ** 0.8 * (0.7 + 0.3 * Y)
    # shape oscillation beads
    n_beads = {'plain': 0, 'beaded': r.uniform(3.0, 4.5), 'beaded_fine': r.uniform(5, 6.5), 'twin': r.uniform(2.5, 4),
               'faint': 0, 'wobble': r.uniform(3, 4), 'bright_head': r.uniform(3, 4), 'twin_beaded': r.uniform(4, 5.5)}[kind]
    depth = {'plain': 0.0, 'beaded': 0.55, 'beaded_fine': 0.45, 'twin': 0.35, 'faint': 0.0, 'wobble': 0.4, 'bright_head': 0.5, 'twin_beaded': 0.6}[kind]
    ph = r.uniform(0, 2 * np.pi)
    osc = 1 - depth * 0.5 * (1 - np.cos(2 * np.pi * n_beads * Y + ph)) if n_beads else 1.0
    # lateral position: slight sway for 'wobble' (wind gust within the exposure)
    cx = 0.0 + (0.035 * np.sin(2 * np.pi * (Y * r.uniform(0.6, 1.1)) + ph) if kind == 'wobble' else 0.0)
    w = {'faint': 0.050, 'plain': 0.042}.get(kind, 0.045)
    core = gauss(X - cx, w) * osc
    halo = 0.18 * gauss(X - cx, w * 2.6)               # the drop's refracted halo / defocus
    L = core + halo
    if kind in ('twin', 'twin_beaded'):
        sep = r.uniform(0.11, 0.15)
        osc2 = 1 - depth * 0.5 * (1 - np.cos(2 * np.pi * n_beads * Y + ph + np.pi * 0.8))
        L = gauss(X - cx + sep / 2, w * 0.85) * osc + 0.45 * gauss(X - cx - sep / 2, w * 0.8) * osc2 + halo
    if kind == 'bright_head':
        L = L + 1.4 * gauss(X - cx, w * 1.1) * gauss(Y - 0.93, 0.03)
    L = L * env
    if kind == 'faint':
        L *= 0.45
    L = L / max(1e-6, np.percentile(L, 99.9)) * (0.45 if kind == 'faint' else 1.0)
    L = np.clip(L, 0, 1)
    alpha = np.clip(L * 1.15, 0, 1)
    return L, alpha


kinds = ['plain', 'beaded', 'beaded_fine', 'twin', 'faint', 'wobble', 'bright_head', 'twin_beaded']
atlas = np.zeros((CH, CW * NCELL, 4))
for i, k in enumerate(kinds):
    L, A = streak(k, 100 + i)
    L = L[::-1]; A = A[::-1]                              # PNG row 0 = top = head
    atlas[:, i * CW:(i + 1) * CW, 0:3] = L[..., None]
    atlas[:, i * CW:(i + 1) * CW, 3] = A
Image.fromarray(np.clip(np.round(atlas * 255), 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'RainStreak_Atlas8x1_512.png'))
json.dump(dict(cells=kinds, cell_px=[CW, CH], layout='8x1, cell 0 left', v='0 = tail (bottom) .. 1 = head (top)',
               core_fraction_of_width=0.2), open(os.path.join(OUT, 'streaks.json'), 'w'), indent=1)
# view: enlarge horizontally, on dark
v = (atlas[..., :3] * atlas[..., 3:4])
Image.fromarray((np.clip(v, 0, 1) * 255).astype(np.uint8)).resize((1024, 512), Image.LANCZOS).save(os.path.join(OUT, 'look_streaks.png'))
