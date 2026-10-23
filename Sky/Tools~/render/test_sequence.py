"""Sequence test for the sky presets (chief engineer r2 #2): Sky/SkyPresets.json replayed in film order the way
LanbaiSkyPreset.Apply() / ApplyBlend() write the globals (this file mirrors their rules; keep them in step).

  1. every preset lists the same global names (so Apply() overwrites everything the previous act wrote);
  2. after each Apply() the global state equals that preset exactly (no residue from any earlier act);
  3. the visible fades (dusk_8i -> dusk_8ii, dusk_8ii -> blue_hour, act 6 cut excluded) blended with the runtime
     rules at t = 0.25 / 0.5 / 0.75 render finite, with no black hole where a cube is unbound, and the cube parameters
     of the side that has the cube are kept (no spinning HDRI).
Exit 1 on a failure."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky_cpu as S
from shader_cpu import camera_dirs, REPO

ORDER = ['overcast_rain_night_town', 'overcast_rain_night', 'moon_night', 'dawn', 'dusk_8i', 'dusk_8ii', 'blue_hour', 'star_sea',
         'overcast_rain_night']
FADES = [('dusk_8i', 'dusk_8ii'), ('dusk_8ii', 'blue_hour')]
HDRI = os.path.join(REPO, 'FromLocal', 'hdri', 'hdr')


def load():
    d = json.load(open(os.path.join(REPO, 'Sky', 'SkyPresets.json')))
    out = {}
    for p in d['presets']:
        g = {kv['k']: list(kv['v']) for kv in p['globalVectors']}
        g.update({kv['k']: kv['v'] for kv in p['globalFloats']})
        out[p['name']] = dict(p, g=g)
    return out


def group(n):   # LanbaiSkyPreset.CacheIds()
    if n == '_Udon_SkyGlobals':
        return 3
    if n.startswith('_Udon_Sky_') and n.endswith('A'):
        return 1
    if n.startswith('_Udon_Sky_') and n.endswith('B') and n != '_Udon_Sky_OtherFromB':
        return 2
    return 0


def blend(a, b, t):   # LanbaiSkyPreset.ApplyBlend()
    fa, fb = a['g']['_Udon_SkyGlobals'], b['g']['_Udon_SkyGlobals']
    out = {}
    for n, va in a['g'].items():
        vb = b['g'].get(n, 0.0 if np.ndim(va) == 0 else [0.0] * 4)
        if np.ndim(va) == 0:
            out[n] = va + (vb - va) * t
            continue
        va, vb = np.array(va, float), np.array(vb, float)
        gr = group(n)
        if gr == 3: v = np.maximum(va, vb)
        elif gr == 1 and fb[1] < 0.5 <= fa[1]: v = va
        elif gr == 1 and fa[1] < 0.5 <= fb[1]: v = vb
        elif gr == 2 and fb[2] < 0.5 <= fa[2]: v = va
        elif gr == 2 and fa[2] < 0.5 <= fb[2]: v = vb
        else: v = va + (vb - va) * t
        out[n] = v.tolist()
    return out


def main():
    P = load()
    fails = []
    names = None
    for n, p in P.items():
        s = set(p['g'])
        if names is None:
            names = s
        elif s != names:
            fails.append('%s: names differ (%s)' % (n, sorted(s ^ names)[:6]))
    state = {}
    for n in ORDER:
        state.update(P[n]['g'])
        if any(state[k] != v for k, v in P[n]['g'].items()) or set(state) != set(P[n]['g']):
            fails.append('after %s: state != preset' % n)
    print('1-2: %d presets, %d globals each, %d applies in film order: %s' % (len(P), len(names), len(ORDER), 'OK' if not fails else 'FAIL'))
    d = np.concatenate([camera_dirs(64, 36, 90, yaw, pitch) for yaw, pitch in ((0, 5), (90, 30), (180, 60), (0, 88))]).astype(np.float32)
    for a, b in FADES:
        pa, pb = P[a], P[b]
        S.renderer().tex.clear()
        cube = pa['cubeA'] or pb['cubeA']
        if cube:
            S.set_cube('_CubeA', S.load_hdr(os.path.join(HDRI, cube + '_1k.hdr')))
        S.set_tex('_GlowTex', S.load_glow(4))
        ends = [S.render(d, {}, pa['g']), S.render(d, {}, pb['g'])]
        lum = lambda c: c @ np.array([0.2126, 0.7152, 0.0722])
        lo = np.minimum(lum(ends[0]), lum(ends[1]))
        for t in (0.25, 0.5, 0.75):
            g = blend(pa, pb, t)
            c = S.render(d, {}, g)
            ok = np.isfinite(c).all() and (lum(c) >= 0.5 * lo - 1e-4).all()
            rot_ok = all(g['_Udon_Sky_RotationA'][0] == x['g']['_Udon_Sky_RotationA'][0] for x in (pa, pb) if x['g']['_Udon_SkyGlobals'][1] >= 0.5)
            print('3: %s -> %s  t %.2f  finite / no hole: %s  cube rotation kept: %s' % (a, b, t, ok, rot_ok))
            if not (ok and rot_ok):
                fails.append('%s -> %s t %.2f' % (a, b, t))
    print('FAIL: ' + '; '.join(fails) if fails else 'SEQUENCE TEST OK')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
