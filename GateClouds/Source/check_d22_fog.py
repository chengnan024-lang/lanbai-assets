"""蓝白 / Lanbai · gate · D-22 check: do the arms' fog and the sky behind them agree through the U6 transition?

The gate driver blends the sky's moon_night globals into act4_gate over 133.8 -> 163.8 (smoothstep). Before v1.2 the
arms' fog colour was LanbaiGateSky's LanbaiBand (only the band colour, width and direction followed the blend; far,
void, elevation and below-horizon stayed the material's act-4 values) and their density ignored _Udon_Fog. v1.2 makes
LanbaiBand = LanbaiHorizon (the sky's own model) and the density = _Udon_Fog.x.

This script ports LanbaiHorizon (Common/Shaders/LanbaiSky.cginc, models A and B) and the old LanbaiBand to numpy,
evaluates both at t = 140 and 150.3 for an arm 1.5 km away (albedo-dark, linear 0.01), and writes a panorama:
rows = the sky / the arm with the OLD fog / the arm with the NEW fog, columns = azimuth from the tear -180..180,
elevation -10..40; graded with the S4 engine. Prints the arm-vs-sky EV per row band.

  python3 check_d22_fog.py --sky SkyPresets.json --fog FogPresets.json [--out d22.png]
"""
import json
import math
import os
import sys

import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import deck_ref as D  # noqa: E402

ss = lambda e0, e1, x: D.ss(e0, e1, x)  # noqa: E731


def smooth01(x):
    x = np.clip(x, 0, 1)
    return x * x * (3 - 2 * x)


def horizon(V, g, band_dir):
    """LanbaiHorizon (models A / B mixed by FogModel.x), no fog cube, no water"""
    el = np.degrees(np.arcsin(np.clip(V[..., 1], -1, 1)))
    th = band_dir[[0, 2]] / np.linalg.norm(band_dir[[0, 2]])
    vh = V[..., [0, 2]] / np.maximum(np.linalg.norm(V[..., [0, 2]], axis=-1, keepdims=True), 1e-6)
    az = np.degrees(np.arccos(np.clip(vh @ th, -1, 1)))
    nearC, farC, zenC = g['_Udon_FogBandColor'][:3], g['_Udon_HorizonColor'][:3], g['_Udon_ZenithColor'][:3]
    nadC = g['_Udon_NadirColor'][:3] if g['_Udon_NadirColor'][3] > 0 else farC
    bw = g['_Udon_FogBandWidth']
    bg = bw + 10.0
    shape, below = g['_Udon_FogShape'], g['_Udon_FogBelow']
    # A
    band = nearC + (farC - nearC) * ss(0, bw, az)[..., None]
    wel = np.clip(1 - ss(shape[0], max(shape[1], shape[0] + 0.1), el), 0, 1) ** (shape[2] if shape[2] > 0 else 1)
    w = (1 - ss(bw, max(bg, bw + 0.1), az)) * wel
    sky = zenC + (band - zenC) * w[..., None]
    sky = sky + farC * (shape[3] * ss(65, 120, az) * wel)[..., None]
    lum = sky @ np.array([0.2126, 0.7152, 0.0722])
    sky = sky + (lum[..., None] * np.array([0.92, 0.98, 1.12]) - sky) * (below[3] * ss(0, -4, el))[..., None]
    dark = below[2] + (1 - below[2]) * ss(below[0], max(below[1], below[0] + 0.1), el)
    A = sky * dark[..., None]
    # B
    hz = nearC + (farC - nearC) * ss(0, max(bw, 1), az)[..., None]
    up = np.clip(ss(shape[0], max(shape[1], shape[0] + 0.1), el), 0, 1) ** (shape[2] if shape[2] > 0 else 1)
    dn = np.clip(ss(below[1], min(below[0], below[1] - 0.1), el), 0, 1) ** (below[2] if below[2] > 0 else 1)
    c = hz + (zenC - hz) * up[..., None]
    B = c + (nadC - c) * dn[..., None]
    m = np.clip(g['_Udon_FogModel'][0], 0, 1)
    return A * (1 - m) + B * m


def old_band(V, g, band_dir):
    """LanbaiGateSky LanbaiBand v1 with the material defaults (HazeFar, Void, BandEl, BelowHorizon, BackBand 0.55)"""
    el = np.degrees(np.arcsin(np.clip(V[..., 1], -1, 1)))
    th = band_dir[[0, 2]] / np.linalg.norm(band_dir[[0, 2]])
    vh = V[..., [0, 2]] / np.maximum(np.linalg.norm(V[..., [0, 2]], axis=-1, keepdims=True), 1e-6)
    az = np.degrees(np.arccos(np.clip(vh @ th, -1, 1)))
    bw = g['_Udon_FogBandWidth']
    bg = bw + 10.0
    nearC = g['_Udon_FogBandColor'][:3]
    far, void = np.array([0.0436, 0.0504, 0.0726]), np.array([0.0021, 0.0030, 0.0070])
    band = nearC + (far - nearC) * ss(0, bw, az)[..., None]
    wel = np.clip(1 - ss(6, 22, el), 0, 1) ** 2
    w = (1 - ss(bw, bg, az)) * wel
    sky = void + (band - void) * w[..., None]
    sky = sky + far * (0.55 * ss(65, 120, az) * wel)[..., None]
    lum = sky @ np.array([0.2126, 0.7152, 0.0722])
    sky = sky + (lum[..., None] * np.array([0.92, 0.98, 1.12]) - sky) * (0.6 * ss(0, -4, el))[..., None]
    return sky * (0.55 + 0.45 * ss(-25, 0, el))[..., None]


def globals_at(t, A, B, fade):
    x = float(smooth01((t - fade[0]) / (fade[1] - fade[0])))
    return {k: A[k] + (B[k] - A[k]) * x for k in A}, x


def main():
    a = sys.argv[1:]
    sp = json.load(open(a[a.index('--sky') + 1]))
    fp = json.load(open(a[a.index('--fog') + 1]))
    out = a[a.index('--out') + 1] if '--out' in a else 'd22_check.png'
    moon = [p for p in sp['presets'] if p['name'] == 'moon_night'][0]
    gate = [p for p in fp['acts'] if p['preset'] == 'act4_gate'][0]
    fade = [t for t in fp['transitions'] if t['label'] == 'U6'][0]['t']
    A = {kv['k']: np.array(kv['v'], float) for kv in moon['globalVectors']}
    A['_Udon_FogBandWidth'] = float([kv['v'] for kv in moon['globalFloats'] if kv['k'] == '_Udon_FogBandWidth'][0])
    B = dict(A)
    B.update({'_Udon_FogModel': np.array([gate['model'], 0, 0, 1.0]), '_Udon_FogBandColor': np.array(gate['near'] + [1.0]),
              '_Udon_HorizonColor': np.array(gate['far'] + [1.0]), '_Udon_ZenithColor': np.array(gate['zenith'] + [1.0]),
              '_Udon_FogShape': np.array(gate['shape'], float), '_Udon_FogBelow': np.array(gate['below'], float),
              '_Udon_Fog': np.array([gate['density'], 0, 0, 1.0]), '_Udon_FogBandWidth': float(gate['width'])})
    eye = np.array([0.55, 1.7, 2.05])
    az = np.radians(np.linspace(-180, 180, 720))
    el = np.radians(np.linspace(40, -10, 100))
    rows = []
    for t in (140.0, 150.3):
        g, x = globals_at(t, A, B, fade)
        gp = D.gate_origin(t)
        tear = gp + np.array([0.0, -150.0 + 0.4 * 600.0, 0.0])
        dir_tear = tear - eye
        dir_tear[1] = 0
        dir_tear /= np.linalg.norm(dir_tear)
        bd = A['_Udon_FogBandDir'][:3] + (dir_tear - A['_Udon_FogBandDir'][:3]) * x
        bd[1] = 0
        bd /= np.linalg.norm(bd)
        # directions in azimuth from the tear (as the bus looks)
        base = math.atan2(dir_tear[0], dir_tear[2])
        AZ, EL = np.meshgrid(az + base, el)
        V = np.stack([np.cos(EL) * np.sin(AZ), np.sin(EL), np.cos(EL) * np.cos(AZ)], -1)
        sky = horizon(V, g, bd)
        arm = np.full(V.shape, 0.01)
        d = 1500.0
        f_old = 1 - np.exp(-0.0006 * d)                       # material density (the arms ignored _Udon_Fog)
        f_new = 1 - np.exp(-g['_Udon_Fog'][0] * d)
        arm_old = arm * (1 - f_old) + old_band(V, g, bd) * f_old
        arm_new = arm * (1 - f_new) + horizon(V, g, bd) * f_new
        L = lambda c: c @ np.array([0.2126, 0.7152, 0.0722])  # noqa: E731
        for name, img in (('old', arm_old), ('new', arm_new)):
            ev = np.log2(np.maximum(L(img), 1e-6) / np.maximum(L(sky), 1e-6))
            back = np.abs(np.degrees(az)) > 120
            print('t %.1f (x = %.2f) arm %s: arm / sky EV median %+.2f, toward the back (|az| > 120) %+.2f, high (el > 20) %+.2f'
                  % (t, x, name, np.median(ev), np.median(ev[:, back]), np.median(ev[np.degrees(el) > 20])))
        for lab, img in (('t %.1f  sky (LanbaiHorizon)' % t, sky), ('arm 1.5 km, OLD fog', arm_old), ('arm 1.5 km, NEW fog', arm_new)):
            im = Image.fromarray(D.grade(img).astype(np.uint8))
            ImageDraw.Draw(im).text((4, 2), lab, fill=(255, 255, 255))
            rows.append(im)
    W, H = rows[0].size
    sheet = Image.new('RGB', (W, (H + 2) * len(rows)), (255, 0, 0))
    for i, r in enumerate(rows):
        sheet.paste(r, (0, i * (H + 2)))
    sheet.save(out)
    print('wrote', out, '(columns: azimuth from the tear -180..180, rows el 40..-10)')


if __name__ == '__main__':
    main()
