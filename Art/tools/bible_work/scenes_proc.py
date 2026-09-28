# -*- coding: utf-8 -*-
"""Procedural scene-linear test frames (for LUT previews of scenes that have no render yet).
Key colours are solved so that, under the scene's own grade, they land on the bible's display targets."""
import numpy as np
from PIL import Image
from functools import lru_cache
from lutlib import ppv2, PROF
from calib_final import solve

W, H = 960, 402
yy, xx = np.mgrid[0:H, 0:W].astype(np.float64)
u, v = xx / W, yy / H
rng = np.random.default_rng(3)

@lru_cache(maxsize=None)
def _sl(h, prof):
    return tuple(solve(h, prof)[0])
def SL(h, prof):
    return np.array(_sl(h, prof))

def vgrad(stops, prof, t=None):
    """stops = [(pos 0..1, hex)], interpolate in log scene-linear along t (default v)."""
    t = v if t is None else t
    pos = np.array([s[0] for s in stops]); cols = np.log(np.maximum(np.array([SL(s[1], prof) for s in stops]), 1e-6))
    out = np.zeros((H, W, 3))
    for c in range(3):
        out[..., c] = np.interp(t, pos, cols[:, c])
    return np.exp(out)

def g2(cx, cy, sx, sy):
    return np.exp(-0.5 * (((xx - cx * W) / (sx * W)) ** 2 + ((yy - cy * H) / (sy * H)) ** 2))

def blend(img, mask, col):
    m = mask[..., None]
    return img * (1 - m) + col * m

def lin_albedo(h):
    return ppv2.hex_to_lin(h)

# ------------------------------------------------------------------ 1 / 12 the stop
def stop(prof='S1', wake=False):
    hz = 0.56
    img = vgrad([(0, '#070B14'), (hz * 0.85, '#0D1320'), (hz, '#121A28'), (1, '#121A28')], prof)
    # town glow on the cloud base, far left
    img += (SL('#241E22', prof) - SL('#121A28', prof)).clip(0) * (g2(0.12, hz, 0.10, 0.06) * (v < hz))[..., None]
    # far tree line / hills: fogged silhouettes
    ridge = hz - 0.02 - 0.025 * np.sin(u * 9 + 1) * np.sin(u * 23) - 0.03 * np.exp(-((u - 0.35) / 0.08) ** 2)
    img = blend(img, ((v > ridge) & (v < hz + 0.01)).astype(float) * 0.85, SL('#0C121C', prof))
    if wake:  # the aijiro band, opposite the town (right), 0-4 deg
        band = np.exp(-((v - (ridge - 0.012)) / 0.03) ** 2) * np.clip(1 - np.abs(u - 0.78) / 0.30, 0, 1) * (v < ridge)
        img = blend(img, band * 0.9, SL('#33465B', prof))
        for _ in range(26):   # a few stars in the gaps
            sx, sy = rng.uniform(0.55, 0.98), rng.uniform(0.03, 0.25)
            img += SL('#8A96A8', prof) * 4 * g2(sx, sy, 0.0012, 0.0028)[..., None]
    # town lights (points)
    for _ in range(70):
        sx, sy = rng.normal(0.13, 0.05), hz - rng.uniform(0.0, 0.02)
        img += SL('#DC8F51', prof) * 2.0 * g2(sx, sy, 0.0011, 0.0024)[..., None]
    # ground: wet road + field
    gnd = (v >= hz)
    img[gnd] = (SL('#0A0E14', prof))
    field = gnd & (u > 0.72 + (v - hz) * 0.6)
    img[field] = SL('#070A10', prof)
    # the pole + lamp
    px = 0.60
    pole = (np.abs(u - px) < 0.0045) & (v > 0.10) & (v < 0.70)
    img = blend(img, pole.astype(float), SL('#232830', prof))
    arm = (u > px - 0.07) & (u < px) & (np.abs(v - 0.105) < 0.004)
    img = blend(img, arm.astype(float), SL('#1A1E24', prof))
    tube_c = SL('#EEF5F7', prof)
    tube = (u > px - 0.066) & (u < px - 0.012) & (np.abs(v - 0.118) < 0.0045)
    img = blend(img, tube.astype(float), tube_c)
    img += SL('#C9DCE0', prof) * (0.35 * g2(px - 0.04, 0.13, 0.05, 0.08) + 0.15 * g2(px - 0.04, 0.2, 0.12, 0.22))[..., None]
    # lamp pool + streak on the wet road
    pool = g2(px - 0.035, 0.66, 0.075, 0.07) * gnd
    img += SL('#262D33', prof) * pool[..., None]
    streak = np.exp(-((u - (px - 0.04)) / 0.009) ** 2) * np.clip((v - 0.60) / 0.40, 0, 1) ** 0.6 * gnd
    ripple = 0.75 + 0.25 * np.sin(v * 180 + np.sin(u * 40) * 2) if not wake else 1.0
    img += tube_c * 0.45 * (streak * ripple)[..., None] * (0.35 if not wake else 0.55)
    # the sign (albedo mock lit by the tube, E 1.3)
    sg = np.asarray(Image.open('../work/sign_zh_albedo_mock.png').convert('RGB').resize((80, 80), Image.LANCZOS)).astype(float) / 255
    alb = ppv2.srgb_to_lin(sg)
    lit = alb * ppv2.hex_to_lin('#E4F1F3') * 1.3
    cx, cy, r = int(px * W) + 1, int(0.30 * H), 40
    Y, X = np.mgrid[0:80, 0:80]; m = (np.hypot(X - 39.5, Y - 39.5) < 39.5).astype(float)[..., None]
    region = img[cy - r:cy + r, cx - r:cx + r]
    img[cy - r:cy + r, cx - r:cx + r] = region * (1 - m) + lit * m
    if wake:  # crisp mirror of the sign + tube in the still puddle
        py0 = int(0.74 * H)
        refl = lit[::-1] * 0.55
        region = img[py0:py0 + 80, cx - r:cx + r]
        img[py0:py0 + 80, cx - r:cx + r] = region * (1 - m[::-1] * 0.9) + refl * m[::-1] * 0.9
    # the bus (left): two-tone body (cream upper / faded indigo lower), rounded roof, lit windows
    roof = 0.30 + 0.02 * (np.abs(u - 0.255) / 0.205) ** 6
    bus = (u > 0.05) & (u < 0.46) & (v > roof) & (v < 0.66)
    img = blend(img, bus.astype(float), SL('#1C2026', prof))
    lower = bus & (v > 0.50)
    img = blend(img, lower.astype(float), SL('#0E141E', prof))
    img += SL('#3A4450', prof) * 0.5 * (bus * np.exp(-((u - 0.46) / 0.03) ** 2))[..., None]   # tube catches the rear-right edge
    for i in range(6):
        wx0 = 0.085 + i * 0.061
        win = (u > wx0) & (u < wx0 + 0.050) & (v > 0.345) & (v < 0.465)
        grad = 1.0 - 0.35 * (v - 0.345) / 0.12
        img = blend(img, win.astype(float), SL('#C9DCE0', prof) * grad[..., None])
    img = blend(img, ((u > 0.05) & (u < 0.46) & (np.abs(v - 0.495) < 0.004)).astype(float), SL('#3A3F45', prof))
    for tx in (0.065, 0.435):
        img += SL('#B2252C', prof) * 3.0 * g2(tx, 0.58, 0.004, 0.009)[..., None]
        refl = np.exp(-((u - tx) / 0.004) ** 2) * np.clip((v - 0.66) / 0.3, 0, 1) ** 0.5 * np.exp(-(v - 0.66) / 0.18) * gnd
        img += SL('#B2252C', prof) * 0.9 * refl[..., None]
    # door light on the shoulder
    door = g2(0.47, 0.70, 0.03, 0.03) * gnd
    img += SL('#C9DCE0', prof) * 0.25 * door[..., None]
    if not wake:  # rain only where lit (the lamp cone)
        for _ in range(900):
            rx, ry = rng.normal(px - 0.04, 0.06), rng.uniform(0.14, 0.72)
            L = rng.uniform(0.02, 0.05)
            seg = (np.abs(u - (rx + (v - ry) * 0.08)) < 0.0006) & (v > ry) & (v < ry + L)
            w = np.exp(-((rx - (px - 0.04)) / 0.07) ** 2) * np.exp(-((ry - 0.35) / 0.35) ** 2)
            img += SL('#9AA8B4', prof) * 0.35 * w * seg[..., None]
    else:     # 46 field fireflies (#DEEA88) over the paddy, doubled in the water; the one Lichtchen close, warm white (#FCF5DA)
        for _ in range(18):
            fx, fy = rng.uniform(0.74, 0.99), rng.uniform(hz + 0.02, 0.8)
            img += SL('#DEEA88', prof) * 2.0 * g2(fx, fy, 0.0011, 0.0026)[..., None]
            img += SL('#DEEA88', prof) * 0.6 * g2(fx, 2 * hz + 0.06 - fy + 0.1, 0.0015, 0.0036)[..., None] * (field[..., None])
        lx, ly = 0.515, 0.47     # 1.0 m from the eye, 0.3 m right: seen through the open door
        img += SL('#FCF5DA', prof) * 4.0 * g2(lx, ly, 0.0035, 0.0085)[..., None]
        img += SL('#EBECA6', prof) * 0.30 * g2(lx, ly, 0.022, 0.05)[..., None]
    return img

# ------------------------------------------------------------------ 2 / 11 the night road through the windscreen
def road(prof='S2', false=False):
    hz = 0.47
    img = vgrad([(0, '#05080F'), (hz, '#0A0F18'), (1, '#0A0F18')], prof)
    gnd = v >= hz
    img[gnd] = SL('#07090D', prof)
    # road trapezoid to the vanishing point
    half = (v - hz) * 1.25
    rd = gnd & (np.abs(u - 0.5) < half)
    img[rd] = SL('#0A0D12', prof)
    dash = rd & (np.abs(u - 0.5) < 0.004 + (v - hz) * 0.012) & (np.sin(1 / np.maximum(v - hz, 1e-3) * 3.0) > 0.3)
    img = blend(img, dash.astype(float) * 0.5, SL('#5A5A56', prof))
    # headlight pool
    img += SL('#C8A878', prof) * 0.30 * (g2(0.5, 0.70, 0.07, 0.06) * rd)[..., None]
    img += SL('#C8A878', prof) * 0.06 * (g2(0.5, 0.62, 0.20, 0.10) * rd)[..., None]
    # sodium lamp passing, upper left, with its streak on the road
    sod = SL('#F2B070', prof)
    if false:   # the sea overhead, lamps hang from it
        sea = v < 0.20 + 0.01 * np.sin(u * 20)
        img = blend(img, sea.astype(float), SL('#0F2438', prof))
        for i in range(40):
            gx, gy = rng.uniform(0, 1), rng.uniform(0.02, 0.18)
            img += SL('#D08A59', prof) * 1.4 * g2(gx, gy, 0.012, 0.0025)[..., None] * np.exp(-((gx - 0.25) / 0.25) ** 2)
        pole = (np.abs(u - 0.22) < 0.003) & (v < 0.22) & (v > 0.0)
        img = blend(img, pole.astype(float), SL('#15181D', prof))
        img += sod * 3 * g2(0.22, 0.225, 0.012, 0.008)[..., None]
        img += sod * 0.25 * g2(0.22, 0.2, 0.06, 0.05)[..., None]
    else:
        pole = (np.abs(u - 0.18) < 0.004) & (v > 0.06) & (v < 0.52)
        img = blend(img, pole.astype(float), SL('#15181D', prof))
        img += sod * 3 * g2(0.205, 0.07, 0.014, 0.008)[..., None]
        img += sod * 0.22 * g2(0.205, 0.10, 0.07, 0.08)[..., None]
        streak = np.exp(-((u - (0.205 + (v - hz) * 0.6)) / 0.01) ** 2) * gnd * np.clip((v - hz) / 0.5, 0, 1)
        img += sod * 0.35 * streak[..., None]
    # roadside tree silhouettes
    for tx in (0.03, 0.08, 0.86, 0.93, 0.98):
        tr = g2(tx, hz - 0.06, 0.035, 0.09) > 0.4
        img = blend(img, tr.astype(float), SL('#06080C', prof))
    # windscreen frame + dash + radio dial
    frame = (u < 0.025) | (u > 0.975) | (v < 0.02)
    img = blend(img, frame.astype(float), SL('#0C0E11', prof))
    dash = v > 0.84 - 0.03 * np.cos((u - 0.5) * 3)
    img = blend(img, dash.astype(float), SL('#16191C', prof))
    img += SL('#C4CACA', prof) * 0.05 * (np.exp(-((v - (0.84 - 0.03 * np.cos((u - 0.5) * 3))) / 0.006) ** 2))[..., None]
    dial = (np.abs(u - 0.30) < 0.035) & (np.abs(v - 0.9) < 0.012)
    img = blend(img, dial.astype(float), SL('#E19867', prof) * (0.35 if false else 1.0))
    img += SL('#E19867', prof) * 0.12 * g2(0.30, 0.9, 0.05, 0.03)[..., None] * (0.3 if false else 1)
    wheel = np.abs(np.hypot((u - 0.16) / 0.9, (v - 1.02) * 2.4 / 2.4) - 0.16) < 0.008
    img = blend(img, (wheel & (v < 1)).astype(float), SL('#0A0B0D', prof))
    if not false:  # raindrops holding tiny lamps
        for _ in range(70):
            dx, dy = rng.uniform(0.03, 0.97), rng.uniform(0.03, 0.8)
            k = np.exp(-((dx - 0.2) / 0.25) ** 2 - ((dy - 0.15) / 0.4) ** 2)
            img += sod * 0.35 * k * g2(dx, dy, 0.0010, 0.0024)[..., None]
    return img

# ------------------------------------------------------------------ 4c inside the tear
def tear_inside(prof='S4c'):
    """nested lens-shaped torn rims receding ahead; dark torn-indigo cloth around them."""
    from scipy.ndimage import gaussian_filter
    noise = gaussian_filter(rng.standard_normal((H, W)), (1.5, 6))           # horizontal fibres
    streak = gaussian_filter(rng.standard_normal((H, W)), (14, 0.8))         # vertical fibres
    cx, cy = 0.5, 0.47
    img = vgrad([(0, '#0E0C18'), (0.5, '#1A1530'), (1, '#0E0C18')], prof)
    wall = np.exp(-(((u - cx) / 0.42) ** 2)) * (0.6 + 0.4 * np.clip(streak * 3, -1, 1))
    img = blend(img, np.clip(wall, 0, 1) * 0.8, SL('#3B2E66', prof))
    for k in range(8):            # k = 0 outermost (rim 1) ... 7 innermost (rim 8)
        s = 0.80 ** k
        hh, ww = 0.60 * s, 0.17 * s
        yy_ = (v - cy) / hh
        half = ww * np.clip(1 - yy_ ** 2, 0, 1) ** 0.85 * (1 + 0.10 * noise)  # vesica with a torn edge
        dd = np.abs(u - cx) / np.maximum(half, 1e-4)
        inside = (dd < 1) & (np.abs(yy_) < 1)
        t = k / 7.0
        haze = np.exp((1 - t) * np.log(SL('#6E6690', prof)) + t * np.log(SL('#BDB4D8', prof)))
        img = blend(img, inside.astype(float) * (0.55 + 0.05 * k), haze)
        lip = np.exp(-((dd - 1) / (0.05 + 0.02 * np.abs(streak))) ** 2) * (np.abs(yy_) < 1) * np.clip(1 - np.abs(yy_) ** 4, 0, 1)
        lip *= 0.6 + 0.4 * np.clip(streak * 2 + 0.5, 0, 1)
        img += SL('#F1EAFF', prof) * (0.30 + 0.05 * k) * lip[..., None]
    img += SL('#FFF1DC', prof) * 2.5 * g2(cx, cy, 0.003, 0.007)[..., None] + SL('#FFF1DC', prof) * 0.30 * g2(cx, cy, 0.025, 0.06)[..., None]
    for _ in range(90):  # loose threads drifting toward the centre
        tx, ty = rng.uniform(0.1, 0.9), rng.uniform(0.1, 0.85)
        img += SL('#F1EAFF', prof) * 0.12 * g2(tx, ty, 0.0009, 0.02)[..., None]
    # dark cabin silhouette: windscreen frame, pillar, dash with the Lichtchen dial
    frame = (u < 0.05) | (u > 0.95) | (v < 0.04) | (v > 0.80 - 0.04 * np.cos((u - 0.5) * 3))
    img = blend(img, frame.astype(float), SL('#0E0C16', prof))
    img += SL('#FFB65A', prof) * 1.0 * ((np.abs(u - 0.30) < 0.035) & (np.abs(v - 0.88) < 0.012))[..., None]
    img += SL('#FFB65A', prof) * 0.12 * g2(0.30, 0.88, 0.06, 0.03)[..., None]
    return img

# ------------------------------------------------------------------ 7a under the surface (looking forward and up)
def undersea(prof='S7a'):
    img = vgrad([(0, '#0F3A5A'), (0.35, '#2A8497'), (0.7, '#1B5E7E'), (1, '#0F4263')], prof)
    ripple = 1 + 0.06 * np.sin(u * 60 + np.sin(v * 30) * 2) * np.sin(v * 40)
    d = ((u - 0.5) / 0.30) ** 2 + ((v + 0.05) / 0.26) ** 2
    win = np.clip((1.0 - d * ripple) / 0.15, 0, 1)
    img = blend(img, win, SL('#E6F3F8', prof))
    img += SL('#B4D6E3', prof) * 0.25 * np.exp(-((np.sqrt(d) - 1) / 0.08) ** 2)[..., None]
    for k in range(9):  # god rays leaning with the sun
        x0 = 0.2 + k * 0.08 + rng.uniform(-0.02, 0.02)
        ray = np.exp(-((u - (x0 + (v * 0.25))) / rng.uniform(0.008, 0.02)) ** 2) * np.clip(1 - v / 0.9, 0, 1)
        img += SL('#7FC4DD', prof) * 0.22 * ray[..., None]
    for _ in range(380):  # marine snow
        sx, sy = rng.uniform(0, 1), rng.uniform(0.2, 1)
        img += SL('#5E7C86', prof) * 0.8 * g2(sx, sy, 0.0012, 0.0028)[..., None]
    return img

# ------------------------------------------------------------------ 7b the deep, the palace
def deep(prof='S7b'):
    img = vgrad([(0, '#061A30'), (0.55, '#04121E'), (1, '#02070F')], prof)
    base = 0.72
    # terrace and hall silhouettes (Han: heavy straight roofs)
    terr = (v > base) & (u > 0.12) & (u < 0.9)
    img = blend(img, terr.astype(float), SL('#050B12', prof))
    hall = (v > 0.42) & (v < base) & (u > 0.32) & (u < 0.68)
    img = blend(img, hall.astype(float), SL('#04090F', prof))
    roof = (v > 0.33) & (v < 0.43) & (np.abs(u - 0.5) < 0.24 - (0.43 - v) * 0.9)
    img = blend(img, roof.astype(float), SL('#03070C', prof))
    for gx in (0.18, 0.82):  # 阙 towers
        tw = (np.abs(u - gx) < 0.035) & (v > 0.30) & (v < base)
        img = blend(img, tw.astype(float), SL('#04080E', prof))
        img += SL('#7A4A6E', prof) * 0.35 * (tw * g2(gx, 0.55, 0.05, 0.2))[..., None]
    # the open doors: warm light and its spill on the terrace
    door = (np.abs(u - 0.5) < 0.035) & (v > 0.52) & (v < base)
    img = blend(img, door.astype(float), SL('#FFC46A', prof) * 0.55)
    img += SL('#FFC46A', prof) * 0.35 * (g2(0.5, base + 0.04, 0.08, 0.03) * (v > base))[..., None]
    # vermilion columns beside the door, lit near the flames
    for cx in (0.43, 0.57):
        col = (np.abs(u - cx) < 0.008) & (v > 0.45) & (v < base)
        img = blend(img, col.astype(float), SL('#B52A1E', prof))
    # bronze lamps: warm core -> teal falloff
    for lx in (0.26, 0.38, 0.62, 0.74):
        img += SL('#FFC46A', prof) * 3.0 * g2(lx, base - 0.06, 0.003, 0.008)[..., None]
        img += SL('#FFC46A', prof) * 0.25 * g2(lx, base - 0.06, 0.02, 0.04)[..., None]
        img += SL('#1E5F66', prof) * 0.5 * g2(lx, base - 0.04, 0.08, 0.12)[..., None]
    for _ in range(70):  # plankton / bio sparks
        sx, sy = rng.uniform(0, 1), rng.uniform(0, 1)
        img += SL('#5CD6F5', prof) * rng.uniform(0.3, 1.0) * g2(sx, sy, 0.0009, 0.0021)[..., None]
    return img

# ------------------------------------------------------------------ 8b the blue hour (mirror-symmetric)
def bluehour(prof='S8b'):
    t = np.abs(v - 0.5) * 2  # 0 at horizon -> 1 at top/bottom
    up = vgrad([(0, '#6F86B0'), (0.35, '#2E4F8A'), (1, '#16223F')], prof, t=t)
    img = np.where((v > 0.5)[..., None], up * 0.82 * np.array([0.92, 0.95, 1.05]), up)
    img += SL('#C98A7A', prof) * 0.35 * g2(0.5, 0.5, 0.15, 0.012)[..., None]
    for _ in range(40):
        sx, sy = rng.uniform(0, 1), rng.uniform(0.02, 0.3)
        img += SL('#E8EEF8', prof) * rng.uniform(0.5, 2.0) * g2(sx, sy, 0.0011, 0.0026)[..., None]
    return img
