#!/usr/bin/env python3
"""
Lanbai / 蓝白 : photosensitivity + luminance-ramp checker for captured frames.

Run it on a DESKTOP capture of the world (1920x1080, the VRChat desktop view, hFOV ~90 deg, seated, looking
where a rider looks) of every risky passage: the gate (scene 4, last 60 s + entry), the plunge -> dawn,
the sea entry, the 9b -> 10 white, 10 -> 11 and 11 -> 12. Unity Recorder / OBS -> PNG sequence.

    python flashcheck.py <frames_dir> --fps 60 [--hfov 90] [--start 0] [--every 1] [--out report]
    python flashcheck.py --selftest             (synthetic pass/fail cases)

What it measures (per WCAG 2.2 SC 2.3.1 "three flashes or below threshold", adapted to VR):
  * general flash: a pair of opposing changes in relative luminance >= 0.10 (of max 1.0) where the darker
    state is < 0.80, evaluated on tiles the size of 25 % of a 10 deg visual field (4.43 deg square);
    FAIL if > 3 flashes in any 1 s; Lanbai's own limit is <= 2 (VR fills the field, so we keep a margin);
  * red flash: the same on the saturated-red metric max(0, R-G-B)*320 for pixels with R/(R+G+B) >= 0.8
    (linear RGB), threshold 20;
  * the Lanbai ramp law on full-field mean relative luminance (APL): max EV rise in any 0.25 s / 1 s / 2 s,
    max EV fall in any 0.25 s, peak APL (display luma).
Frames must be what the screen showed (sRGB, after post).  Output: <out>.json and <out>.png.
"""
import argparse, glob, json, math, os, sys
import numpy as np

LUMA = np.array([0.2126, 0.7152, 0.0722], np.float32)
FLASH_T = 0.10
DARK_LIMIT = 0.80
RED_T = 20.0
LAW = {  # Lanbai ramp law (see lens_tech.md, section 3)
    "rise_ev_per_0.25s": 0.5, "rise_ev_per_1s": 1.0, "rise_ev_per_2s": 1.8,
    "max_flashes_per_1s": 2.0, "wcag_max_flashes_per_1s": 3.0,
    "apl_floor": 0.004,   # relative luminance ~ display luma 20 (~0.4 nit on a 100-nit headset): below this, EV is not counted
}


def srgb_to_lin(u8):
    x = u8.astype(np.float32) / 255.0
    return np.where(x <= 0.04045, x / 12.92, ((x + 0.055) / 1.055) ** 2.4)


def tile_means(img, tile, stride):
    """Mean of img (H,W) over square tiles of side `tile` px, stride `stride` px (box filter via integral image)."""
    H, W = img.shape
    ii = np.zeros((H + 1, W + 1), np.float64)
    ii[1:, 1:] = img.cumsum(0).cumsum(1)
    ys = np.arange(0, max(H - tile, 0) + 1, stride)
    xs = np.arange(0, max(W - tile, 0) + 1, stride)
    y0, x0 = np.meshgrid(ys, xs, indexing="ij")
    y1, x1 = np.minimum(y0 + tile, H), np.minimum(x0 + tile, W)
    s = ii[y1, x1] - ii[y0, x1] - ii[y1, x0] + ii[y0, x0]
    return (s / ((y1 - y0) * (x1 - x0))).ravel()


class TransitionCounter:
    """Per-tile peak/trough tracker. A transition is a move of >= thr from the running extreme since the
    last transition, in the direction opposite to the previous transition, with the darker end < dark."""

    def __init__(self, n, thr, dark=None):
        self.thr, self.dark = thr, dark
        self.hi = None
        self.lo = None
        self.dir = np.zeros(n, np.int8)  # +1 last transition was a rise, -1 a fall, 0 none

    def step(self, y):
        if self.hi is None:
            self.hi, self.lo = y.copy(), y.copy()
            return np.zeros_like(y, bool)
        self.hi = np.maximum(self.hi, y)
        self.lo = np.minimum(self.lo, y)
        dark_ok_fall = np.ones_like(y, bool) if self.dark is None else (y < self.dark)
        dark_ok_rise = np.ones_like(y, bool) if self.dark is None else (self.lo < self.dark)
        fall = (self.hi - y >= self.thr) & (self.dir >= 0) & dark_ok_fall
        rise = (y - self.lo >= self.thr) & (self.dir <= 0) & dark_ok_rise & ~fall
        ev = fall | rise
        self.dir[fall] = -1
        self.dir[rise] = 1
        self.hi[ev] = y[ev]
        self.lo[ev] = y[ev]
        return ev


def analyze(frames, fps, hfov=90.0, label="capture"):
    """frames: iterable of uint8 sRGB (H,W,3). Returns a report dict and the time series."""
    lum_tc = red_tc = None
    trans_times = []      # per frame: max over tiles of transitions (general)
    red_times = []
    apl = []
    flash_tiles_frac = []
    tile = stride = None
    for i, fr in enumerate(frames):
        lin = srgb_to_lin(fr[..., :3])
        Y = lin @ LUMA
        if tile is None:
            H, W = Y.shape
            ppd = W / hfov
            tile = max(2, int(round(4.43 * ppd)))
            stride = max(1, tile // 2)
        s = lin.sum(-1) + 1e-6
        red = np.where(lin[..., 0] / s >= 0.8, np.maximum(0.0, lin[..., 0] - lin[..., 1] - lin[..., 2]) * 320.0, 0.0)
        ty = tile_means(Y, tile, stride)
        tr = tile_means(red, tile, stride)
        if lum_tc is None:
            lum_tc = TransitionCounter(ty.size, FLASH_T, DARK_LIMIT)
            red_tc = TransitionCounter(tr.size, RED_T, None)
        e1 = lum_tc.step(ty)
        e2 = red_tc.step(tr)
        trans_times.append(e1)
        red_times.append(e2)
        apl.append(float(Y.mean()))
    T = np.array(trans_times)        # (frames, tiles) bool
    R = np.array(red_times)
    n = T.shape[0]
    win = int(round(fps))
    # flashes in any 1 s window, per tile = floor(transitions / 2); take the worst tile
    cs = np.vstack([np.zeros((1, T.shape[1]), np.int32), np.cumsum(T, 0)])
    csr = np.vstack([np.zeros((1, R.shape[1]), np.int32), np.cumsum(R, 0)])
    flashes_1s = np.zeros(n)
    red_1s = np.zeros(n)
    for t in range(n):
        a, b = max(0, t - win + 1), t + 1
        flashes_1s[t] = ((cs[b] - cs[a]) / 2.0).max()     # a flash = a pair of opposing transitions
        red_1s[t] = ((csr[b] - csr[a]) / 2.0).max()
    apl = np.array(apl)
    ev = np.log2(np.maximum(apl, LAW["apl_floor"]))

    def max_delta(w_s, sign):
        w = max(1, int(round(w_s * fps)))
        if n <= w:
            return 0.0
        d = ev[w:] - ev[:-w]
        return float((d if sign > 0 else -d).max())

    rep = {
        "label": label, "frames": n, "fps": fps, "tile_px": tile,
        "max_general_flashes_in_any_1s": float(flashes_1s.max()),
        "max_red_flashes_in_any_1s": float(red_1s.max()),
        "wcag_2_3_1": "PASS" if flashes_1s.max() <= 3 and red_1s.max() <= 3 else "FAIL",
        "lanbai_flash_rule": "PASS" if flashes_1s.max() <= LAW["max_flashes_per_1s"] and red_1s.max() == 0 else "FAIL",
        "max_rise_ev_0.25s": round(max_delta(0.25, +1), 2),
        "max_rise_ev_1s": round(max_delta(1.0, +1), 2),
        "max_rise_ev_2s": round(max_delta(2.0, +1), 2),
        "max_fall_ev_0.25s": round(max_delta(0.25, -1), 2),   # reported only: darkening is limited by the flash rule
        "peak_apl_luma": int(round(255 * (apl.max() ** (1 / 2.2)))),
        "mean_apl_luma": int(round(255 * (apl.mean() ** (1 / 2.2)))),
    }
    ramp_ok = (rep["max_rise_ev_0.25s"] <= LAW["rise_ev_per_0.25s"] and rep["max_rise_ev_1s"] <= LAW["rise_ev_per_1s"]
               and rep["max_rise_ev_2s"] <= LAW["rise_ev_per_2s"])
    rep["lanbai_ramp_law"] = "PASS" if ramp_ok else "FAIL (unless this is the one authored tear flash)"
    series = {"t": np.arange(n) / fps, "apl": apl, "flashes_1s": flashes_1s, "red_1s": red_1s,
              "any_transition": T.any(1)}
    return rep, series


def plot(series, rep, path):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    t = series["t"]
    fig, ax = plt.subplots(2, 1, figsize=(10, 4.6), sharex=True, gridspec_kw={"height_ratios": [3, 1.3]})
    luma = 255 * series["apl"] ** (1 / 2.2)
    ax[0].plot(t, luma, color="#1F4E79", lw=1.4)
    ax[0].set_ylabel("APL (display luma)")
    ax[0].set_ylim(0, 255)
    tt = t[series["any_transition"]]
    ax[0].plot(tt, np.full_like(tt, 248), "|", color="#B0413E", ms=6, label="luminance transition (some tile)")
    ax[0].legend(loc="upper left", frameon=False, fontsize=8)
    ax[0].set_title(f"{rep['label']}: WCAG {rep['wcag_2_3_1']}, Lanbai flash {rep['lanbai_flash_rule']}, ramp {rep['lanbai_ramp_law'].split(' ')[0]}",
                    fontsize=10, loc="left")
    ax[1].step(t, series["flashes_1s"], where="post", color="#B0413E", lw=1.2)
    ax[1].axhline(3, color="#888", lw=0.8, ls="--")
    ax[1].axhline(2, color="#1F4E79", lw=0.8, ls=":")
    ax[1].set_ylabel("flashes / 1 s")
    ax[1].set_xlabel("time (s)")
    ax[1].set_ylim(0, max(4, series["flashes_1s"].max() + 1))
    for a in ax:
        a.spines[["top", "right"]].set_visible(False)
    fig.tight_layout()
    fig.savefig(path, dpi=110)
    plt.close(fig)


def load_frames(d, start=0, every=1):
    from PIL import Image
    files = sorted(glob.glob(os.path.join(d, "*.png")) + glob.glob(os.path.join(d, "*.jpg")))[start::every]
    for f in files:
        yield np.asarray(Image.open(f).convert("RGB"))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("frames", nargs="?")
    ap.add_argument("--fps", type=float, default=60)
    ap.add_argument("--hfov", type=float, default=90)
    ap.add_argument("--start", type=int, default=0)
    ap.add_argument("--every", type=int, default=1)
    ap.add_argument("--out", default="flashcheck_report")
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        import synth_tests
        synth_tests.run()
        return
    rep, ser = analyze(load_frames(a.frames, a.start, a.every), a.fps / a.every, a.hfov, os.path.basename(a.frames.rstrip("/")))
    with open(a.out + ".json", "w") as fh:
        json.dump(rep, fh, indent=1)
    plot(ser, rep, a.out + ".png")
    print(json.dumps(rep, indent=1))


if __name__ == "__main__":
    main()
