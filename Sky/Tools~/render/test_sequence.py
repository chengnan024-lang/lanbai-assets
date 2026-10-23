"""Sequence test for the sky presets (chief engineer r2 #2, #6): Sky/SkyPresets.json replayed in the film's real order
(README_Sky §3.1: the LanbaiSkyDriver tables in SkyPresets.json 'drivers' + the clouds' fades) the way
LanbaiSkyPreset.Apply() / ApplyBlend() write the globals. blend() below mirrors ApplyBlend line for line (the groups
come from the JSON, as in the runtime); keep the two in step.

  1. every preset lists the same names in the same order (ApplyBlend's map is the identity);
  2. replaying the applies in film order, every global after Apply(p) equals p (and nothing else is left);
  3. every visible fade, at t = 0.25 / 0.5 / 0.75: finite, no hole (>= half the darker end), the cube never turns
     (a cube's rotation in use is always one of the two ends' rotations);
  4. continuity: the frame at t = 0.999 and the frame after Apply(b) differ by < 1 display code (8 bit, graded);
  5. at t = 0.5 the zenith (pitch 89 / 90) passes the gradient self-check (no cap with a rim).
Exit 1 on a failure."""
import os, sys, json
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky_cpu as S, grade as G
import make_presets as MP
from shader_cpu import camera_dirs, REPO

CLOUD_FADES = [('dusk_8i', 'dusk_8ii', 'S8'), ('dusk_8ii', 'blue_hour', 'S8b')]     # README §3.1, the clouds' driver
CLOUD_APPLIES = ['dawn', 'dusk_8i']                                                    # under occlusion


def load():
    d = json.load(open(os.path.join(REPO, 'Sky', 'SkyPresets.json')))
    P = {}
    for p in d['presets']:
        P[p['name']] = dict(p, names=[kv['k'] for kv in p['globalVectors']], vals=[np.array(kv['v'], float) for kv in p['globalVectors']],
                            fnames=[kv['k'] for kv in p['globalFloats']], fvals=[kv['v'] for kv in p['globalFloats']])
    return P, d['drivers']


def globs_of(p, vals=None, fvals=None):
    g = {n: list(v) for n, v in zip(p['names'], vals if vals is not None else p['vals'])}
    g.update({n: v for n, v in zip(p['fnames'], fvals if fvals is not None else p['fvals'])})
    return g


def rot_a(p):
    return p['vals'][p['names'].index('_Udon_Sky_RotationA')][0]


def blend(a, b, t):
    """= LanbaiSkyPreset.ApplyBlend (same names, same order). Returns (globals, cube A preset, cube B preset or None)."""
    fa = a['vals'][a['names'].index('_Udon_SkyGlobals')]; fb = b['vals'][b['names'].index('_Udon_SkyGlobals')]
    hasA, hasB = fa[1] >= 0.5, fb[1] >= 0.5
    cross = hasA and hasB and (a['cubeA'] != b['cubeA'] or abs(rot_a(a) - rot_a(b)) > 0.01)
    anyA, anyB = fa[1] >= 0.5 or fa[2] >= 0.5, fb[1] >= 0.5 or fb[2] >= 0.5
    skip = set(a.get('blendSkip') or [])
    out = []
    for i, n in enumerate(a['names']):
        va, vb = a['vals'][i], b['vals'][i]
        g = a['vecGroups'][i]
        if n in skip:   # not written by ApplyBlend: the other writer (the clouds' sun line) runs the same span; stand-in = lerp
            out.append(va + (vb - va) * t); continue
        if g == 3:
            v = np.maximum(va, vb)
            if cross: v = v.copy(); v[2] = 1.0
        elif g == 1:
            v = va if cross else (va if (hasA and not hasB) else (vb if (hasB and not hasA) else va + (vb - va) * t))
        elif g == 2:
            if cross:
                v = b['vals'][a['vecPartner'][i]]
            else:
                v = va if (fa[2] >= 0.5 > fb[2]) else (vb if (fb[2] >= 0.5 > fa[2]) else va + (vb - va) * t)
        elif g == 4:
            v = va if (anyA and not anyB) else (vb if (anyB and not anyA) else va + (vb - va) * t)
        elif g == 5:
            da, db = va[:3], vb[:3]
            if np.dot(db, db) < 1e-8: v = va
            elif np.dot(da, da) < 1e-8: v = vb
            else:
                d = da + (db - da) * t; d = d / np.linalg.norm(d)
                v = np.r_[d, va[3] + (vb[3] - va[3]) * t]
        else:
            v = va + (vb - va) * t
        if cross and n == '_Udon_SkyBlend':
            v = v.copy(); v[0] = t
        out.append(np.asarray(v, float))
    fv = [x + (y - x) * t for x, y in zip(a['fvals'], b['fvals'])]
    return globs_of(a, out, fv), (a if hasA else b), (b if cross else None), cross


def set_cubes(pa, pb):
    S.renderer().tex.clear()
    S.set_tex('_GlowTex', S.load_glow(4))
    if pa is not None and MP.P[pa['name']].get('hdri_file'):
        S.set_cube('_CubeA', S.load_hdr(MP.P[pa['name']]['hdri_file']))
    if pb is not None and MP.P[pb['name']].get('hdri_file'):
        S.set_cube('_CubeB', S.load_hdr(MP.P[pb['name']]['hdri_file']))


def main():
    P, drivers = load()
    fails = []
    names = next(iter(P.values()))['names']
    for n, p in P.items():
        if p['names'] != names or p['fnames'] != next(iter(P.values()))['fnames']:
            fails.append('%s: names / order differ' % n)
    order, fades = [], []
    for d in drivers:
        for i, e in enumerate(d['entries']):
            order.append(e['preset'])
            if e['fade'] > 0 and i > 0:
                fades.append((d['entries'][i - 1]['preset'], e['preset'], P[e['preset']]['profile']))
    order[3:3] = CLOUD_APPLIES + ['dusk_8ii', 'blue_hour']        # acts 6 .. 8b sit between the two driver windows
    fades += CLOUD_FADES
    state = {}
    for n in order:
        g = globs_of(P[n])
        state.update(g)
        if set(state) != set(g) or any(np.any(np.asarray(state[k]) != np.asarray(v)) for k, v in g.items()):
            fails.append('after Apply(%s): state != preset' % n)
    print('1-2: %d presets, %d vector + %d float globals, %d applies in film order (%s): %s'
          % (len(P), len(names), len(P[order[0]]['fnames']), len(order), ' -> '.join(order), 'OK' if not fails else 'FAIL'))
    d = np.concatenate([camera_dirs(96, 54, 90, yaw, pitch) for yaw, pitch in ((0, 3), (90, 30), (180, 60), (-70, 5))]).astype(np.float32)
    dz = [camera_dirs(96, 96, 90, 0, 90).astype(np.float32), camera_dirs(96, 96, 90, 37, 89).astype(np.float32)]
    ref = MP.grad_reference()
    lum = lambda c: c @ np.array([0.2126, 0.7152, 0.0722])
    for a, b, prof in fades:
        pa, pb = P[a], P[b]
        _, _, cb, cross = blend(pa, pb, 0.5)
        set_cubes(pa if pa['cubeA'] else pb, cb)
        ends = [S.render(d, {}, globs_of(pa)), None]
        if cross:   # Apply(b) puts b's cube back in slot A
            set_cubes(pb, None); ends[1] = S.render(d, {}, globs_of(pb)); set_cubes(pa, cb)
        else:
            ends[1] = S.render(d, {}, globs_of(pb))
        lo = np.minimum(lum(ends[0]), lum(ends[1]))
        rots = {round(rot_a(pa), 3), round(rot_a(pb), 3)}
        for t in (0.25, 0.5, 0.75):
            g, _, _, _ = blend(pa, pb, t)
            c = S.render(d, {}, g)
            ok = bool(np.isfinite(c).all() and (lum(c) >= 0.5 * lo - 1e-4).all())
            rot_ok = round(g['_Udon_Sky_RotationA'][0], 3) in rots and (not cross or round(g['_Udon_Sky_RotationB'][0], 3) in rots)
            zg = max(float(MP.grad_codes(np.clip(G.grade(S.render(z, {}, g).reshape(96, 96, 3), prof), 0, 255), z, []).max()) for z in dz) if t == 0.5 else 0.0
            z_ok = zg <= ref['max']
            print('3/5: %s -> %s%s t %.2f  finite/no hole %s  rotation kept %s%s'
                  % (a, b, ' (crossfade A -> B)' if cross else '', t, ok, rot_ok, ('  zenith max gradient %.2f codes/px %s' % (zg, 'OK' if z_ok else 'FAIL')) if t == 0.5 else ''))
            if not (ok and rot_ok and z_ok):
                fails.append('%s -> %s t %.2f' % (a, b, t))
        g, _, _, _ = blend(pa, pb, 0.999)
        c999 = np.clip(G.grade(S.render(d, {}, g)[None], prof, bloom=False), 0, 255)
        c1 = np.clip(G.grade(ends[1][None], prof, bloom=False), 0, 255)
        jump = float(np.abs(c999 - c1).max())
        if pa.get('blendSkip'):
            jump_note = ' (blendSkip %s: written by the other driver over the same span, modelled as a lerp)' % pa['blendSkip']
        else:
            jump_note = ''
        print('4: %s -> %s  t 0.999 vs Apply(%s): max %.2f codes %s%s' % (a, b, b, jump, 'OK' if jump < 1.0 else 'FAIL', jump_note))
        if jump >= 1.0:
            fails.append('%s -> %s: jump %.2f at t = 1' % (a, b, jump))
    print('FAIL: ' + '; '.join(fails) if fails else 'SEQUENCE TEST OK')
    sys.exit(1 if fails else 0)


if __name__ == '__main__':
    main()
