"""Calibration tables for lens_cine.md, computed through the PPv2 emulator.
  - Kelvin -> light colour hex
  - grey-card display targets for each scene's light roles
  - inverse 'set' values: what to type into Unity so the screen shows the display target after the grade
Writes calib_out.md (tables) and calib.json.
"""
import json, os
import numpy as np
from scipy.optimize import least_squares
import ppv2

HERE = os.path.dirname(os.path.abspath(__file__))
G = json.load(open(os.path.join(HERE, 'grades.json')))
P = {k: v['ppv2'] for k, v in G['profiles'].items()}

KS = [2100, 2400, 3200, 4300, 5600, 6500, 7500, 9000]
KHEX = {K: ppv2.kelvin_hex(K) for K in KS}
TUBE = '#F6E7C0'            # 4300 K fluorescent with its green bump (old tubes)
TEAR = ppv2.lin_to_hex(np.array([0.62, 0.26, 1.00]))

def disp_hex(lin, prof):
    return ppv2.srgb_to_hex(ppv2.display_of(np.asarray(lin, float), P[prof]))

def solve(target_hex, prof):
    """robust inverse: coarse multi-start + Nelder-Mead in log space (the grade has clamp dead-zones)."""
    from scipy.optimize import minimize
    t_s = np.array([int(target_hex[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    t = ppv2.srgb_to_lin(t_s)
    def f(x):
        return (ppv2.display_of(np.exp(x), P[prof]) - t_s) * 255
    def cost(x):
        return float((f(x) ** 2).sum())
    starts = []
    grey = t.mean()
    for mix in (0.0, 0.3, 0.6):
        for sc in (0.5, 1.0, 2.0, 4.0):
            starts.append(np.log(np.maximum((t * (1 - mix) + grey * mix) * sc, 1e-5)))
    best = None
    for x0 in starts:
        c = cost(x0)
        if best is None or c < best[0]:
            best = (c, x0)
    r = minimize(cost, best[1], method='Nelder-Mead', options=dict(xatol=1e-5, fatol=1e-4, maxiter=4000))
    r2 = least_squares(f, np.clip(r.x, np.log(1e-7) + 1e-6, np.log(80) - 1e-6), bounds=(np.log(1e-7), np.log(80)))
    x = np.exp(r2.x)
    return x, np.abs(f(r2.x)).max()

def set_str(x):
    m = x.max()
    if m <= 1.0:
        return ppv2.lin_to_hex(x)
    ev = np.log2(m)
    return '%s @ +%.2f' % (ppv2.lin_to_hex(x / m), ev)

def insp(E):
    """Unity inspector intensity for linear irradiance E (Built-in default: intensity applied in gamma space)."""
    return E ** (1 / 2.2)

# ---------------- light roles: (scene, role, colour hex, E on a card facing the light) ----------------
LIGHTS = [
 ('S1', 'Key: stop lamp (LED 5600 K), card on the road at the pool centre', KHEX[5600], 1.30),
 ('S1', 'Fill: cabin spill through the open door (tube cream), card on the kerb', TUBE, 0.35),
 ('S1', 'Headlight pool on the road 10 m ahead (halogen 3200 K)', KHEX[3200], 0.90),
 ('S1', 'Ambient only (Trilight sky #1A2438), card facing up', '#1A2438', 1.0),
 ('S2', 'Key: cabin tubes, card on a seat cushion', TUBE, 0.55),
 ('S2', 'Streetlight sweep peak (sodium 2100 K), card on a seat', KHEX[2100], 0.90),
 ('S2', 'Headlight pool on the road 10 m ahead', KHEX[3200], 0.90),
 ('S3', 'Key: moon (9000 K) directional, intensity reference E = 1', KHEX[9000], 1.00),
 ('S3', 'Cabin tubes after the break-out (half of S2)', TUBE, 0.27),
 ('S4', 'Moon rim source (same moon), card facing the moon', KHEX[9000], 1.00),
 ('S4', 'Tear light (violet) directional from the tear, card facing the tear', TEAR, 0.80),
 ('S4', 'Cloud-sea bounce from below (#5A6488), card facing down', '#5A6488', 0.06 / ppv2.hex_to_lin('#5A6488').max()),
 ('S4', 'Cabin tubes base level before they die', TUBE, 0.25),
 ('S6', 'Key: dawn sun 3200 K, 6 deg elevation', KHEX[3200], 3.00),
 ('S6', 'Sky ambient only (Trilight sky #5A78B8), card facing up', '#5A78B8', 1.0),
 ('S7a', 'Key: sun through the surface (#A8DCEB), card facing up', '#A8DCEB', 1.60),
 ('S7a', 'Water ambient (Trilight equator #2B7FA8), card facing sideways', '#2B7FA8', 1.0),
 ('S7b', 'Palace glow from below (vermilion point light) at the bus', '#FF5A2E', 0.15),
 ('S7b', 'Deep ambient (Trilight sky #0E3050), card facing up', '#0E3050', 1.0),
 ('S8', 'Key/back: dusk sun 2400 K on the horizon, card facing the sun', KHEX[2400], 2.20),
 ('S8', 'Ground ambient: rose-violet cloud sea (#6A4A78), card facing down', '#6A4A78', 1.0),
 ('S8', 'Sky ambient: ocean ceiling (#1C3350), card facing up', '#1C3350', 1.0),
 ('S9a', 'Starlight ambient (Trilight sky #1A2A4A), card facing up', '#1A2A4A', 1.0),
 ('S9a', 'Mirror-crossing pulse light 8000 K (peak)', ppv2.kelvin_hex(8000), 0.30),
 ('S12', 'Key: stop lamp (same as S1)', KHEX[5600], 1.30),
 ('S12', 'Ambient only (clearing sky #121C2E), card facing up', '#121C2E', 1.0),
]
WHITE_CARD = [('S3', 'white card (albedo 0.80) under the moon: must match moonlit cloud-card tops', KHEX[9000], 1.0),
              ('S6', 'white card (0.80) in the dawn sun', KHEX[3200], 3.0),
              ('S8', 'white card (0.80) facing the dusk sun', KHEX[2400], 2.2)]

# ---------------- unlit / emissive / fog display targets ----------------
TARGETS = {
 'S1': [('Fog colour (Exp2)', '#101A2B'), ('Sky zenith (overcast night)', '#070B14'), ('Sky horizon', '#0E1628'),
        ('Horizon toward the town (sodium-lit cloud base)', '#231E24'), ('Town lights (soft sprites, fog-free)', '#D98A3E'),
        ('Rain streaks inside the lamp cone', '#9AA8B8'), ('Rain streaks elsewhere', '#1E2632'), ('Lamp cone (fake volumetric) core', '#3A4658')],
 'S2': [('Fog colour', '#0A0F18'), ('Sky', '#05080F'), ('Radio dial glow', '#F2A640'), ('Sodium lamp heads passing', '#FFC27A')],
 'S3': [('Sky zenith', '#08101F'), ('Sky horizon (away from the moon)', '#111B30'), ('Sky 10 deg around the moon', '#26344F'),
        ('Moon halo (disc of 6 deg)', '#5A6A88'), ('Fog colour above the clouds', '#111B30'), ('Town underglow patches on the cloud sea', '#6A4630'),
        ('Cloud-entry whiteout fog', '#4A5568')],
 'S4': [('Sky void', '#070A14'), ('Haze fog (far colossi dissolve into it)', '#1B2240'), ('Violet halo around the tear', '#6B45C8'),
        ('Violet light shafts (additive, where two overlap)', '#3A2A70'), ('Cloud sea under the tear (tinted)', '#4E4F7A'), ('Tear edge glow (just outside the core)', '#C9B2FF')],
 'S5': [('Black overlay', '#010207'), ('Falling motes', '#2A3550')],
 'S6': [('Zenith', '#3E64A6'), ('Earth-shadow band (anti-sun horizon)', '#8C98B8'), ('Belt of Venus (above the Earth shadow)', '#D9B3B9'),
        ('Sun-side horizon', '#F2C79A'), ('Fog colour (average forward horizon)', '#C4B8C0'), ('Sea far below (mirror, deep blue)', '#1C3D63')],
 'S7a': [('Snell window (the sky seen from below)', '#E6F3F8'), ('Water fog, shallow', '#2B7FA8'), ('God-ray cards (additive result)', '#7FC4DD'),
         ('Surface underside outside the window (total reflection)', '#0F3A5A')],
 'S7b': [('Water fog, 30-60 m', '#16507A'), ('Water fog, deep', '#061A30'), ('Abyss (looking down, before the palace)', '#02070F'),
         ('Plankton (bioluminescent points)', '#8FE8FF'), ('Palace glow, vermilion 朱', '#FF5A2E'), ('Palace glow, violet 紫贝', '#8A5CFF')],
 'S8': [('Ocean ceiling, straight overhead (deep water)', '#10263F'), ('Ocean ceiling near the horizon (mirror)', '#C98A7A'),
        ('Sky slot at the horizon', '#F2A56B'), ('Cloud-sea shadows below', '#4A3560'), ('Fog colour', '#B77F78')],
 'S8b': [('Blue-hour sky (the purest 蓝 of the piece)', '#2E4F8A'), ('Blue-hour horizon', '#6F86B0')],
 'S9a': [('Sky zenith 紺', '#0B1A33'), ('Sky horizon', '#16294A'), ('Milky Way, brightest diffuse', '#6F82A0'), ('Sea reflection (mirror, -0.3 EV)', '#0A1428')],
 'S10': [('The 藍白 overlay (full field)', '#E8F1F5')],
 'S11': [('Sea in the sky, underside', '#0F2438'), ('Amber light pools on the sea', '#B8763A'), ('Fog colour', '#0A0F18')],
 'S12': [('Sky zenith (breaking cloud)', '#070B14'), ('Pre-dawn 藍白 band, 0-4 deg above the horizon', '#8FA6BE'), ('Fog colour (thin)', '#111B2A'),
         ('Fireflies', '#D8F28A'), ('Town lights (now visible)', '#D98A3E')],
}

def main():
    out = []
    res = {'kelvin': KHEX, 'tube': TUBE, 'tear': TEAR, 'lights': [], 'targets': {}}
    out.append('### Kelvin to Unity light colour (D65-balanced, max channel 255)\n')
    out.append('| K | hex | K | hex |\n|---|---|---|---|')
    ks = list(KHEX.items())
    for i in range(0, len(ks), 2):
        a = ks[i]; b = ks[i + 1] if i + 1 < len(ks) else ('', '')
        out.append(f'| {a[0]} | `{a[1]}` | {b[0]} | `{b[1]}` |')
    out.append(f'\nOld fluorescent tube (4300 K + green bump): `{TUBE}`. Tear violet (preview rig TEAR_COLOR): `{TEAR}`.\n')
    out.append('### Grey-card targets (card = Standard shader, albedo #767676 = 0.18 linear, smoothness 0)\n')
    out.append('| Scene | Light role | Light colour | E (linear) | Unity intensity (directional, gamma rule) | Card reads (sRGB) |\n|---|---|---|---|---|---|')
    for sc, role, col, E in LIGHTS:
        lin = 0.18 * E * ppv2.hex_to_lin(col)
        d = disp_hex(lin, sc)
        out.append(f'| {sc} | {role} | `{col}` | {E:.2f} | {insp(E):.2f} | `{d}` |')
        res['lights'].append(dict(scene=sc, role=role, color=col, E=E, inspector=round(insp(E), 3), card=d))
    for sc, role, col, E in WHITE_CARD:
        lin = 0.80 * E * ppv2.hex_to_lin(col)
        d = disp_hex(lin, sc)
        out.append(f'| {sc} | {role} | `{col}` | {E:.2f} | {insp(E):.2f} | `{d}` |')
    out.append('\n### Unlit / emissive / fog: display target -> value to SET in Unity (under that scene\'s grade)\n')
    out.append('`#RRGGBB @ +n` means HDR colour: base hex with the HDR picker Intensity = +n (x 2^n). Values without @ are plain colour-picker hex (Unity converts sRGB->linear).\n')
    out.append('| Scene | Element | Screen must show | Set in Unity |\n|---|---|---|---|')
    for sc, items in TARGETS.items():
        prof = sc if sc in P else ('S4' if sc == 'S5' else sc)
        for name, hx in items:
            x, err = solve(hx, prof)
            s = set_str(x)
            ach = disp_hex(x, prof)
            shown = f'`{hx}`' if err <= 3 else f'`{ach}` (nearest reachable: this grade caps saturation)'
            out.append(f'| {sc} | {name} | {shown} | `{s}` |')
            res['targets'].setdefault(sc, []).append(dict(element=name, display=hx, set=s, lin=[round(float(v), 5) for v in x]))
    # grey ramp through each grade (for the in-Unity test card)
    out.append('\n### Grade test card: 11 unlit grey patches at 0.18 x 2^k (k = -6..+4); screenshot must match (+-3 codes)\n')
    ks = list(range(-6, 5))
    out.append('| Profile | ' + ' | '.join(f'{k:+d}' for k in ks) + ' |\n|' + '---|' * (len(ks) + 1))
    res['ramp'] = {}
    for prof in P:
        row = [disp_hex(np.array([0.18 * 2 ** k] * 3), prof) for k in ks]
        res['ramp'][prof] = row
        out.append(f'| {prof} | ' + ' | '.join(f'`{h}`' for h in row) + ' |')
    open(os.path.join(HERE, 'calib_out.md'), 'w').write('\n'.join(out) + '\n')
    json.dump(res, open(os.path.join(HERE, 'calib.json'), 'w'), indent=1, ensure_ascii=False)
    print('\n'.join(out))

if __name__ == '__main__':
    main()
