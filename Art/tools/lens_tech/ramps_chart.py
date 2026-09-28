#!/usr/bin/env python3
"""Figure for lens_tech.md: full-field luminance (EV) through the three big brightenings,
sibling-lens spec vs the lens_tech ramp law. Data = the synthetic sequences in synth_tests.py."""
import numpy as np, matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import synth_tests as st, flashcheck as fc

FLOOR = 0.004
BLUE, ORANGE = "#2a78d6", "#eb6834"          # categorical slots 1, 2 (validated reference palette)
INK, INK2, GRID, SURF = "#0b0b0b", "#52514e", "#e4e3df", "#fcfcfb"


def ev_series(gen, t0):
    y = [float((f @ fc.LUMA).mean()) for f in gen]
    t = t0 + np.arange(len(y)) / st.FPS
    return t, np.log2(np.maximum(np.array(y), FLOOR))


panels = [
    ("Gate entry → plunge → dawn", lambda: st.seq_cine_gate(-2.0, 11.0), -2.0, lambda: st.seq_lanbai_gate(-2.0, 12.0), -2.0,
     "lens_cine 5.5 (+2 EV flash, 5 s ease-out)", "lens_tech (+1.5 EV / 0.4 s, 7 s EV-linear)"),
    ("9b → 10, the white", st.seq_white_cine, -1.0, st.seq_white_lanbai, -1.0,
     "lens_cine 5.10 (5 s cubic + 1 s)", "lens_tech (crash + swell, VR white)"),
    ("11 → 12, white again", lambda: st.seq_second_white(True), -0.5, lambda: st.seq_second_white(False), -0.5,
     "lens_cine 6 (2.5 s linear alpha)", "lens_tech (6.5 s EV-linear, dimmer)"),
]
guide = {"Gate entry → plunge → dawn": (8.3, -8.0), "9b → 10, the white": (6.0, -8.0), "11 → 12, white again": None}
plt.rcParams.update({"font.size": 9, "axes.edgecolor": INK2, "axes.labelcolor": INK2, "xtick.color": INK2, "ytick.color": INK2})
fig, axs = plt.subplots(1, 3, figsize=(12.5, 3.9), sharey=True, facecolor=SURF)
for ax, (title, g1, t1, g2, t2, l1, l2) in zip(axs, panels):
    ax.set_facecolor(SURF)
    a, b = ev_series(g1(), t1)
    c, d = ev_series(g2(), t2)
    ax.plot(a, b, color=ORANGE, lw=2, label="sibling spec")
    ax.plot(c, d, color=BLUE, lw=2, label="lens_tech rule")
    ax.set_xlim(t1, t1 + 14.0)                       # equal time spans: slopes compare across panels
    if guide[title] is not None:                     # 1 EV/s slope guide, placed in empty space
        gx, gy = guide[title]
        ax.plot([gx, gx + 3], [gy, gy + 3], color=INK2, lw=1, ls=(0, (2, 2)))
        ax.text(gx + 3.15, gy + 3, "1 EV/s", color=INK2, fontsize=8, va="center")
    ax.set_title(title, loc="left", color=INK, fontsize=10)
    for k, (lab, col) in enumerate(((l1, ORANGE), (l2, BLUE))):
        yk = 0.965 - 0.075 * k
        ax.plot([0.02, 0.07], [yk, yk], color=col, lw=2, transform=ax.transAxes, solid_capstyle="butt")
        ax.text(0.085, yk, lab, transform=ax.transAxes, color=INK2, fontsize=7.5, va="center")
    ax.grid(axis="y", color=GRID, lw=0.8)
    ax.set_axisbelow(True)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlabel("time (s)")
axs[0].set_ylabel("full-field luminance (EV, 0 = white)")
axs[0].set_ylim(-8.3, 2.3)
axs[0].set_yticks(range(-8, 1))
h, lab = axs[0].get_legend_handles_labels()
fig.legend(h, lab, loc="upper right", frameon=False, ncol=2, fontsize=9)
fig.suptitle("Full-field brightening: sibling-lens specs vs the lens_tech ramp law (synthetic seat view, EV floor 0.004)", x=0.01, ha="left", fontsize=10.5, color=INK)
fig.tight_layout(rect=(0, 0, 1, 0.93))
fig.savefig("out/ramps_compare.png", dpi=120, facecolor=SURF)
print("ok")
