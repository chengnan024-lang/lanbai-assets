# -*- coding: utf-8 -*-
"""Verification of the generated grade data -- and a gate on what PPv2 will really SHOW.

  A. parses Editor/LanbaiGradeData.cs back (the C# text, not the generator's memory) and diffs every field
     against expectations built INDEPENDENTLY from grades_engine.json / grades_final.json / calib_final.json
     (no generator code reused);
  B. parses the generated region of Runtime/LanbaiExposure.cs (scene order, postExposure table, EXPO targets);
  C. optional --dump: JSON printed by the COMPILED C# (csc + .NET run of LanbaiGradeData / LanbaiExposure),
     compared field by field in float32;
  D. ENGINE GATE (verify.md B1 / M1). The numbers parsed from the C# go through TWO independent models of PPv2 3.x's
     Neutral path, both written from the package source (LogC contrast, linear-709 white balance / lift-gamma-gain /
     saturation, 33^3 half LUT, trilinear):
        Tools~/verify_indep/ppv2_neutral_check.py  (the verifier's, used as the gate)
        Tools~/engine/ppv2_engine.py                (the solver's; must agree with the verifier's)
     and must show: every calib section C patch within +-3 codes, the black point the bible asks for at input 0
     (night profiles never crush red to 0), every section A reading, section B fill and section D overlay fill
     within +-3 codes (with the engine fills of calib_engine.json where it re-solved one), and the C#'s own
     predictedTestCard / predictedBlack. The art simulator is NOT used here (that was the circular check).
     D0 (informational only): the look-definition numbers still reproduce section C in the art simulator.
  E. cross-checks ART_BIBLE.md appendix B: table B1 against the look-definition record, B2 against the helpers,
     and recomputes table B3's (v2.1) weights with the U# formula;
  F. checks every sha256 chain: C# header -> grades_engine.json / grades_final.json / calib_final.json,
     grades_engine.json -> the look definition it was solved from, calib_engine.json -> both;
  G. regenerates the kit in a temporary copy and compares the generated files byte for byte.
Exit code 0 = everything passes.
"""
import argparse
import glob
import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ART = os.path.normpath(os.path.join(KIT, '..', '..', 'art'))

problems, notes = [], []
NIGHT = {'S1', 'S2', 'S3', 'S4', 'S4c', 'S7a', 'S7b', 'S8b', 'S9a', 'S9b', 'S11', 'S12'}   # bible 1.3.5: never crush red to 0
TOL = 3


def bad(msg):
    problems.append(msg)


def ok(msg):
    notes.append(msg)


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


# ------------------------------------------------------------------------------------------ C# parsing
TOKEN = re.compile(r'\s*(?:(?P<str>"(?:[^"\\]|\\.)*")|(?P<num>-?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?f)|(?P<kw>true|false|null)'
                   r'|(?P<enum>LanbaiGradeKind\.\w+)|(?P<arr>new (?:float|string)\[\]\s*\{)|(?P<close>\})|(?P<comma>,))')


def parse_value(s, i):
    m = TOKEN.match(s, i)
    if not m:
        raise ValueError('cannot parse value at: %r' % s[i:i + 60])
    if m.group('str'):
        return json.loads(m.group('str')), m.end()
    if m.group('num'):
        return float(m.group('num')[:-1]), m.end()
    if m.group('kw'):
        return {'true': True, 'false': False, 'null': None}[m.group('kw')], m.end()
    if m.group('enum'):
        return m.group('enum').split('.')[1], m.end()
    if m.group('arr'):
        out, j = [], m.end()
        while True:
            m2 = TOKEN.match(s, j)
            if m2 and m2.group('close'):
                return out, m2.end()
            v, j = parse_value(s, j)
            out.append(v)
            m3 = TOKEN.match(s, j)
            if m3 and m3.group('comma'):
                j = m3.end()
    raise ValueError('unexpected token %r' % m.group(0))


def parse_data_cs(path):
    text = open(path, encoding='utf-8-sig').read()
    entries = []
    for m in re.finditer(r'new LanbaiGradeEntry\s*\{', text):
        i, e = m.end(), {}
        while True:
            m2 = re.compile(r'\s*\}\s*,').match(text, i)
            if m2:
                break
            m3 = re.compile(r'\s*(\w+)\s*=\s*').match(text, i)
            if not m3:
                raise ValueError('bad initialiser near %r' % text[i:i + 80])
            v, i = parse_value(text, m3.end())
            e[m3.group(1)] = v
            m4 = re.compile(r'\s*,').match(text, i)
            if m4:
                i = m4.end()
        entries.append(e)
    header = {k: re.search(r'%s = "([0-9a-f]{64})"' % k, text).group(1) for k in ('GradesSha256', 'LookDefSha256', 'CalibSha256')}
    header['ColourPatchNames'] = [json.loads(x) for x in re.findall(r'"[^"]*"', re.search(r'ColourPatchNames = new string\[\] \{ (.*?) \};', text).group(1))]
    header['ColourPatchLinear'] = [float(x) for x in re.findall(r'(-?[\d.]+)f', re.search(r'ColourPatchLinear = new float\[\] \{ (.*?) \};', text).group(1))]
    forb = re.search(r'ForbiddenEffects = new string\[\] \{ (.*?) \};', text).group(1)
    return entries, header, [json.loads(x) for x in re.findall(r'"[^"]*"', forb)]


def parse_expo_cs(path):
    t = open(path, encoding='utf-8-sig').read()
    a, b = t.index('// <lanbai:generated'), t.index('// </lanbai:generated>')
    r = t[a:b]
    out = {'SceneCount': int(re.search(r'SceneCount = (\d+);', r).group(1)),
           'up': float(re.search(r'ExpoUpTarget = (-?[\d.]+)f;', r).group(1)),
           'down': float(re.search(r'ExpoDownTarget = (-?[\d.]+)f;', r).group(1)),
           'sha': re.search(r'sha256="([0-9a-f]{64})"', r).group(1),
           'source': re.search(r'source="([^"]+)"', r).group(1)}
    ids = re.search(r'string SceneId\(int i\).*?switch \(i\)\s*\{(.*?)\}', r, re.S).group(1)
    out['ids'] = [(int(i), s) for i, s in re.findall(r'case (\d+): return "([^"]+)";', ids)]
    idx = re.search(r'int SceneIndex\(string id\)(.*?)return -1;', r, re.S).group(1)
    out['index'] = [(s, int(i)) for s, i in re.findall(r'if \(id == "([^"]+)"\) return (\d+);', idx)]
    pe = re.search(r'float ScenePostExposure\(int i\).*?switch \(i\)\s*\{(.*?)\}', r, re.S).group(1)
    out['pe'] = [(int(i), float(v)) for i, v in re.findall(r'case (\d+): return (-?[\d.]+)f;', pe)]
    out['fields_normal'] = re.findall(r'private PostProcessVolume _scene(\d+);', r)
    out['fields_fallback'] = re.findall(r'private Animator _scene(\d+);', r)
    return out


# ------------------------------------------------------------------------------------------ expectations
def srgb_enc(v):
    v = min(max(v, 0.0), 1.0)
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def expected_from_json(G, C, CP=None):
    """Independent restatement of bible 1.4 / appendix B in terms of the json (NOT the generator's code)."""
    com = G['common']
    exp = {}
    scenes = sorted(G['profiles'], key=lambda k: G['profiles'][k]['priority'])
    luts = {}
    for f in glob.glob(os.path.join(ART, 'luts', 'hdr_external', '*_HDRext33.cube')):
        n = os.path.basename(f)[:-5]
        luts[n.split('_')[1]] = n

    def comp(h):     # double sRGB decode of the bloom tint: raw colour = sRGB-encode(hex / 255)
        return [round(srgb_enc(int(h[i:i + 2], 16) / 255.0), 6) for i in (1, 3, 5)]
    for sid in scenes:
        P = G['profiles'][sid]
        p, b = P['ppv2'], P['ppv2']['bloom']
        exp[sid] = {
            'kind': 'Scene', 'group': 'Scenes', 'priority': P['priority'], 'displayName': P['name'],
            'initialWeight': 1.0 if sid == scenes[0] else 0.0, 'desktopOnly': False,
            'hdrNeutral': True, 'postExposure': p['postExposure'], 'temperature': p['temperature'], 'tint': p['tint'],
            'colorFilter': com['colorFilter'], 'hueShift': com['hueShift'], 'saturation': p['saturation'],
            'contrast': p['contrast'], 'lift': p['lift'], 'gamma': p['gamma'], 'gain': p['gain'], 'channelMixer': p['mixer'],
            'bloomIntensity': b['intensity'], 'bloomThreshold': b['threshold'], 'bloomSoftKnee': b['softKnee'],
            'bloomClamp': com['bloom']['clamp'], 'bloomDiffusion': b['diffusion'],
            'bloomAnamorphicRatio': com['bloom']['anamorphicRatio'], 'bloomColor': b['color'],
            'bloomColorCompensated': comp(b['color']),
            'bloomFastMode': com['bloom']['fastMode'], 'vignetteIntensity': com['vignette']['intensity'],
            'grainIntensity': com['grain']['intensity'], 'bloomT0': P['bloom_T0_scene_linear'],
            'expectedTestCard': C['ramp'][sid], 'expectedBlack': G['_engine']['report'][sid]['black']['target']}
        if CP:
            exp[sid]['expectedColourPatches'] = CP['look'][sid]
        if luts:
            exp[sid]['routeCLut'] = luts.get(sid)
    H = G['helpers']
    exp['EXPO_UP'] = {'kind': 'Helper', 'group': 'Helpers', 'priority': H['EXPO_UP']['priority'], 'initialWeight': 0.0,
                      'postExposure': H['EXPO_UP']['ppv2']['postExposure']}
    exp['EXPO_DOWN'] = {'kind': 'Helper', 'group': 'Helpers', 'priority': H['EXPO_DOWN']['priority'], 'initialWeight': 0.0,
                        'postExposure': H['EXPO_DOWN']['ppv2']['postExposure']}
    exp['WHITE_SAT'] = {'kind': 'Helper', 'group': 'Helpers', 'priority': H['WHITE_SAT']['priority'], 'initialWeight': 0.0,
                        'saturation': H['WHITE_SAT']['ppv2']['saturation']}
    wb = H['WHITE_BLOOM']['ppv2']['bloom']
    exp['WHITE_BLOOM'] = {'kind': 'Helper', 'group': 'Helpers', 'priority': H['WHITE_BLOOM']['priority'], 'initialWeight': 0.0,
                          'bloomIntensity': wb['intensity'], 'bloomThreshold': wb['threshold'], 'bloomSoftKnee': wb['softKnee'],
                          'bloomDiffusion': wb['diffusion'], 'bloomColor': wb['color'], 'bloomColorCompensated': comp(wb['color'])}
    for lid, w0 in (('LENS_CLEAN', 1.0), ('LENS_ARCHIVE', 0.0)):
        L = H[lid]
        exp[lid] = {'kind': 'Lens', 'group': 'Lens_DesktopOnly', 'priority': L['priority'], 'initialWeight': w0, 'desktopOnly': True,
                    'vignetteIntensity': L['vignette']['intensity'], 'vignetteSmoothness': L['vignette']['smoothness'],
                    'vignetteColor': L['vignette']['color'], 'grainIntensity': L['grain']['intensity'],
                    'grainSize': L['grain']['size'], 'grainLumContrib': L['grain']['lumContrib'],
                    'grainColored': L['grain']['colored'],
                    # shape fields only in the v1 block (== PPv2 defaults)
                    'vignetteMode': 'Classic', 'vignetteCenter': [0.5, 0.5], 'vignetteRoundness': 1, 'vignetteRounded': False}
    extra = set(k for k in H if not k.startswith('_')) - set(exp)
    if extra:
        bad('json has helpers this verifier does not know: %s' % sorted(extra))
    return exp, scenes


ALL_FIELDS = ['hdrNeutral', 'postExposure', 'temperature', 'tint', 'colorFilter', 'hueShift', 'saturation', 'contrast',
              'lift', 'gamma', 'gain', 'channelMixer', 'bloomIntensity', 'bloomThreshold', 'bloomSoftKnee', 'bloomClamp', 'bloomDiffusion',
              'bloomAnamorphicRatio', 'bloomColor', 'bloomFastMode', 'vignetteMode', 'vignetteColor', 'vignetteCenter',
              'vignetteIntensity', 'vignetteSmoothness', 'vignetteRoundness', 'vignetteRounded', 'grainColored',
              'grainIntensity', 'grainSize', 'grainLumContrib']
INFO_FIELDS = ['kind', 'group', 'priority', 'initialWeight', 'desktopOnly', 'displayName', 'bloomT0', 'expectedTestCard',
               'bloomColorCompensated', 'expectedBlack', 'routeCLut', 'expectedColourPatches']


def same(a, b, f32=False):
    if isinstance(a, list) or isinstance(b, list):
        return isinstance(a, list) and isinstance(b, list) and len(a) == len(b) and all(same(x, y, f32) for x, y in zip(a, b))
    if isinstance(a, bool) or isinstance(b, bool):
        return a is b or a == b and type(a) == type(b)
    if isinstance(a, (int, float)) and isinstance(b, (int, float)):
        if f32:
            return np.float32(a) == np.float32(b)
        return float(a) == float(b)
    if isinstance(a, str) and isinstance(b, str):
        return a.upper() == b.upper() if a.startswith('#') else a == b
    return a == b


def diff_entries(parsed, exp, label, f32=False):
    byid = {e['id']: e for e in parsed}
    if set(byid) != set(exp):
        bad('%s: id set differs: extra %s missing %s' % (label, sorted(set(byid) - set(exp)), sorted(set(exp) - set(byid))))
    n = 0
    for eid, want in exp.items():
        got = byid.get(eid)
        if got is None:
            continue
        for k in INFO_FIELDS + ALL_FIELDS:
            if k not in want:
                if k in ALL_FIELDS and got.get(k) is not None:
                    bad('%s %s.%s = %r but the json does not override it' % (label, eid, k, got.get(k)))
                continue
            n += 1
            if not same(got.get(k), want[k], f32):
                bad('%s %s.%s = %r, json says %r' % (label, eid, k, got.get(k), want[k]))
    return n


# ------------------------------------------------------------------------------------------ D. engine gate
def hex8(h):
    return np.array([int(h[i:i + 2], 16) for i in (1, 3, 5)])


def to_hex(c):
    return '#%02X%02X%02X' % tuple(int(x) for x in c)


def parse_set(s):
    m = re.match(r'\s*#([0-9A-Fa-f]{6})(?:\s*@\s*\+?(-?[\d.]+))?', s)
    v = np.array([int(m.group(1)[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])
    v = np.where(v <= 0.04045, v / 12.92, ((v + 0.055) / 1.055) ** 2.4)
    return v * 2.0 ** float(m.group(2) or 0.0)


def engine_gate(parsed, G, C, CE, header):
    sys.path.insert(0, os.path.join(HERE, 'verify_indep'))
    sys.path.insert(0, os.path.join(HERE, 'engine'))
    import ppv2_neutral_check as V     # the verifier's independent model (gate)
    import ppv2_engine as E            # the solver's model (must agree)

    def profile_from(e, saturation=None):
        p = {k: e[k] for k in ('postExposure', 'temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain', 'colorFilter', 'hueShift')}
        p['mixer'] = e['channelMixer']
        if saturation is not None:
            p['saturation'] = saturation
        return p

    cache = {}

    def show(key, p, lin):
        """8-bit screen codes of scene-linear rows through the VERIFIER's model (and the solver's, compared)."""
        if key not in cache:
            cache[key] = (V.lut3d(p), E.bake_lut(p))
        Lv, Le = cache[key]
        lin = np.atleast_2d(np.asarray(lin, np.float64))
        uvw = np.clip(V.lin2logc(np.maximum(lin, 0) * 2.0 ** p['postExposure']), 0, 1)
        a = V.srgb8(V.sample3d(Lv, uvw))
        b = np.round(E.codes(lin, p, Le)).astype(int)
        return a, int(np.abs(a - b).max())

    byid = {e['id']: e for e in parsed}
    scenes = [e for e in parsed if e['kind'] == 'Scene']
    P = np.stack([np.full(3, 0.18 * 2.0 ** k) for k in range(-6, 5)])
    worstC, worst_models, failing = 0, 0, []
    rows, colour_rows = [], []
    for e in scenes:
        p = profile_from(e)
        got, dm = show(e['id'], p, np.vstack([P, np.zeros((1, 3))]))
        worst_models = max(worst_models, dm)
        tgt = np.array([hex8(h) for h in e['expectedTestCard']])
        d = np.abs(got[:11] - tgt).max(1)
        worstC = max(worstC, int(d.max()))
        if d.max() > TOL:
            failing.append(e['id'])
            bad('ENGINE §C %s: patches %s off by %s codes (> %d)' % (e['id'], [k for k, x in zip(range(-6, 5), d) if x > TOL], d.max(), TOL))
        blk = got[11]
        db = int(np.abs(blk - hex8(e['expectedBlack'])).max())
        if db > 1:
            bad('ENGINE black %s: input 0 shows %s, the bible asks for %s' % (e['id'], to_hex(blk), e['expectedBlack']))
        if e['id'] in NIGHT and blk[0] < 1:
            bad('ENGINE black %s: red crushed to 0 (%s): bible 1.3.5 forbids it' % (e['id'], to_hex(blk)))
        pr = np.array([hex8(h) for h in e['predictedTestCard'] + [e['predictedBlack']]])
        dp = int(np.abs(pr - got).max())
        if dp > 1:
            bad('C# predictedTestCard/predictedBlack of %s differ from the verifier model by %d codes' % (e['id'], dp))
        rows.append((e['id'], int(d.max()), to_hex(blk), e['expectedBlack'], dp))
        # colour row (not bible targets): the C# prediction must be the verifier model's; report engine vs look
        lin = np.array(header['ColourPatchLinear']).reshape(-1, 3)
        gc, _ = show(e['id'], p, lin)
        pc = np.array([hex8(h) for h in e['predictedColourPatches']])
        if int(np.abs(pc - gc).max()) > 1:
            bad('C# predictedColourPatches of %s differ from the verifier model by %d codes' % (e['id'], int(np.abs(pc - gc).max())))
        colour_rows.append((e['id'], int(np.abs(gc - np.array([hex8(h) for h in e['expectedColourPatches']])).max())))
    ok('D. ENGINE GATE (PPv2 3.x Neutral path, two independent models from the package source; art simulator NOT used)')
    ok('   §C test card, 15 profiles x 11 patches through the engine: worst %d codes (tolerance %d)%s'
       % (worstC, TOL, '' if not failing else '  FAILING: %s' % failing))
    ok('   black point at input 0 (bible 1.3.5 / 1.4), engine vs bible:')
    for sid, dC, blk, want, dp in rows:
        ok('     %-4s §C max %d   black %s (bible %s)%s   C# prediction vs model: %d' % (
            sid, dC, blk, want, '' if sid not in NIGHT else '  red %s' % ('kept' if int(blk[1:3], 16) >= 1 else 'CRUSHED'), dp))
    ok('   the two engine models agree to %d code(s) on every patch' % worst_models)
    ok('   test-card colour row (8 saturated colours, not bible targets), engine vs look per profile: %s'
       % ', '.join('%s %d' % r for r in colour_rows))
    if worst_models > 1:
        bad('the verifier model and the solver model disagree by %d codes' % worst_models)

    # sections A / B / D of calib through the engine (fills: calib_engine.json set_engine where re-solved)
    def grade_of(name):
        m = re.match(r'(S\w+)(?:\s*\+\s*WHITE_SAT\(1\))?$', name.strip())
        sat = byid['WHITE_SAT']['saturation'] if 'WHITE_SAT' in name else None
        return m.group(1), profile_from(byid[m.group(1)], sat)
    worst = {'A': 0, 'B': 0, 'D': 0}
    n = {'A': 0, 'B': 0, 'D': 0}
    for L in C['lights']:
        p = profile_from(byid[L['scene']])
        alb = 0.80 if '白卡' in L['role'] else 0.18
        lin = alb * parse_set(L['colour']) * L['E']
        got, _ = show(L['scene'], p, lin)
        d = int(np.abs(got[0] - hex8(L['reads'])).max())
        worst['A'] = max(worst['A'], d)
        n['A'] += 1
        if d > TOL:
            bad('ENGINE §A %s %s: %s, target %s (%d)' % (L['scene'], L['role'], to_hex(got[0]), L['reads'], d))
    ce_unlit = {(r['scene'], r['element']): r for r in CE['unlit']}
    for U in C['unlit']:
        r = ce_unlit.get((U['scene'], U['element']))
        fill = r.get('set_engine', U['set']) if r else U['set']
        p = profile_from(byid[U['scene']])
        got, _ = show(U['scene'], p, parse_set(fill))
        d = int(np.abs(got[0] - hex8(U['display'])).max())
        worst['B'] = max(worst['B'], d)
        n['B'] += 1
        if d > TOL:
            bad('ENGINE §B %s %s: fill %s shows %s, target %s (%d)' % (U['scene'], U['element'], fill, to_hex(got[0]), U['display'], d))
    ce_ov = {(r['when'], r['role']): r for r in CE['overlay']}
    for O in C['overlay']:
        r = ce_ov.get((O['when'], O['role']))
        fill = r.get('set_engine', O['set']) if r else O['set']
        sid, p = grade_of(O['grade'])
        got, _ = show(O['grade'], p, parse_set(fill))
        d = int(np.abs(got[0] - hex8(O['display'])).max())
        worst['D'] = max(worst['D'], d)
        n['D'] += 1
        if d > TOL:
            bad('ENGINE §D %s %s: fill %s shows %s, target %s (%d)' % (O['when'], O['role'], fill, to_hex(got[0]), O['display'], d))
    ok('   calib through the engine: §A %d readings worst %d, §B %d fills worst %d (%d with the engine fill of calib_engine.json), '
       '§D %d overlay fills worst %d codes' % (n['A'], worst['A'], n['B'], worst['B'], sum('set_engine' in r for r in CE['unlit']),
                                              n['D'], worst['D']))
    return worstC


def lookdef_consistency(G, C):
    """D0, informational: the look-definition record still reproduces section C in the art simulator (it made §C)."""
    try:
        sys.path.insert(0, os.path.join(ART, 'lens_cine'))
        sys.path.insert(0, os.path.join(ART, 'bible_work'))
        import ppv2
        from lutlib_core import patch_ppv2
        patch_ppv2(ppv2)
    except Exception as ex:      # the art folder is not next to the kit: skip, it is informational
        return 'skipped (%s)' % ex
    worst = 0
    for sid, P in G['profiles'].items():
        q = dict(P['ppv2_lookdef'])
        q.update(postExposure=P['ppv2']['postExposure'], colorFilter=G['common']['colorFilter'], hueShift=G['common']['hueShift'])
        for i, k in enumerate(range(-6, 5)):
            s = ppv2.display_of(np.full(3, 0.18 * 2.0 ** k), q)
            got = np.clip(np.round(s * 255), 0, 255)
            worst = max(worst, int(np.abs(got - hex8(C['ramp'][sid][i])).max()))
    return '%d codes' % worst


# ------------------------------------------------------------------------------------------ E. bible appendix B
def bible_checks(bible_path, parsed, G):
    """B1 = the LOOK DEFINITION (art simulator numbers) -> compared with grades_engine.json's ppv2_lookdef record and with
    the C#'s lookDefinition text; postExposure / bloom / T0 are the same in both layers -> compared with the C# directly."""
    byid = {e['id']: e for e in parsed}
    t = open(bible_path, encoding='utf-8').read()
    b = t[t.index('## 附录 B'):t.index('## 附录 C')]
    night = [0.9875, 0.9905, 1, 0.008]
    n = 0
    seen = set()
    for line in b.splitlines():
        m = re.match(r'\|\s*\**(S\d+[a-c]?)\b', line)
        if not m or '|' not in line[2:]:
            continue
        sid = m.group(1)
        cells = [c.strip().replace('**', '').replace('`', '').replace('−', '-') for c in line.strip().strip('|').split('|')]
        if len(cells) < 12 or sid not in byid:
            continue
        seen.add(sid)
        e = byid[sid]
        ld = G['profiles'][sid]['ppv2_lookdef']

        def num(s):
            return float(s.replace('+', ''))

        def vec(s):
            return night if s == '夜间' else [float(x) for x in s.strip('()').split(',')]
        checks = [('priority', num(cells[1]), e['priority']), ('postExposure', num(cells[2]), e['postExposure']),
                  ('lookdef temperature', num(cells[3]), ld['temperature']), ('lookdef tint', num(cells[4]), ld['tint']),
                  ('lookdef saturation', num(cells[5]), ld['saturation']), ('lookdef contrast', num(cells[6]), ld['contrast']),
                  ('lookdef lift', vec(cells[7]), ld['lift']), ('lookdef gamma', vec(cells[8]), ld['gamma']),
                  ('lookdef gain', vec(cells[9]), ld['gain'])]
        bl = [x.strip() for x in cells[10].split('/')]
        checks += [('bloomIntensity', num(bl[0]), e['bloomIntensity']), ('bloomThreshold', num(bl[1]), e['bloomThreshold']),
                   ('bloomSoftKnee', num(bl[2]), e['bloomSoftKnee']), ('bloomDiffusion', num(bl[3]), e['bloomDiffusion']),
                   ('bloomColor', bl[4], e['bloomColor'])]
        if cells[11] not in ('—', '-'):
            checks.append(('bloomT0 (2 dp)', round(num(cells[11]), 2), round(e['bloomT0'], 2)))
        for k, want, got in checks:
            n += 1
            if not same(got, want):
                bad('bible B1 %s.%s: bible says %r, kit has %r' % (sid, k, want, got))
        # the C# record of the look definition must state the same numbers
        nums = [float(x) for x in re.findall(r'-?\d+(?:\.\d+)?', e['lookDefinition'].split(':', 1)[1])]
        want = [ld['temperature'], ld['tint'], ld['saturation'], ld['contrast']] + list(ld['lift']) + list(ld['gamma']) + list(ld['gain'])
        n += 1
        if len(nums) != len(want) or any(abs(x - y) > 1e-9 for x, y in zip(nums, want)):
            bad('C# lookDefinition of %s does not state the B1 numbers: %r' % (sid, e['lookDefinition']))
    if seen != {e['id'] for e in parsed if e['kind'] == 'Scene'}:
        bad('bible B1 rows found for %s only' % sorted(seen))
    # B2 (helpers): the numbers written in the table
    B2 = {'EXPO_UP': [('priority', 100), ('postExposure', 4.0)], 'EXPO_DOWN': [('priority', 99), ('postExposure', -4.0)],
          'WHITE_SAT': [('priority', 96), ('saturation', -30)],
          'WHITE_BLOOM': [('priority', 96), ('bloomIntensity', 12), ('bloomThreshold', 0.8), ('bloomSoftKnee', 0.8),
                          ('bloomDiffusion', 9), ('bloomColor', '#EEF4F8')],
          'LENS_CLEAN': [('priority', 199), ('vignetteIntensity', 0.20), ('vignetteSmoothness', 0.40), ('vignetteColor', '#02040A'),
                         ('grainIntensity', 0.06), ('grainSize', 0.8), ('grainColored', False)],
          'LENS_ARCHIVE': [('priority', 200), ('vignetteIntensity', 0.26), ('vignetteSmoothness', 0.45), ('grainIntensity', 0.20),
                           ('grainSize', 1.0), ('grainLumContrib', 0.85), ('grainColored', False)]}
    for hid, kv in B2.items():
        for k, want in kv:
            n += 1
            if not same(byid[hid].get(k), want):
                bad('bible B2 %s.%s: bible says %r, C# has %r' % (hid, k, want, byid[hid].get(k)))
    return n, b


B3 = [  # bible v2.1 table B3: (event, base b (profile id or number), dEV, listed weight, helper, decimals the bible prints)
    ('U6k break-out', 'S3', 0.5, 0.102, 'up', 3), ('U9 tube flash', 'S4', 0.3, 0.062, 'up', 3),
    ('FLASH_TEAR', 'S4c', 1.5, 0.306, 'up', 3),
    ('F2h water entry (S6 base)', 'S6', -0.5, 0.154, 'down', 3), ('F2h water entry (S7a base)', 'S7a', -0.5, 0.156, 'down', 3),
    ('exit to dusk: pin (7c end #3A2629, b = S7b)', 'S7b', -2.43, 0.68, 'down', 2),
    ('exit to dusk: release apex F9', 'S8', 0.5, 0.11, 'up', 2),
    ('mirror pulse (faces 1-11)', 'S9a', 0.35, 0.095, 'up', 3),
    ('white crash', 'S9b', 1.0, 0.270, 'up', 3), ('white swell', 'S9b', 2.4, 0.649, 'up', 3),
    ('after first white', 'S11', 1.0, 0.241, 'up', 3), ('after second white', 'S12', 0.8, 0.200, 'up', 3)]


def b3_checks(pe, up, down, bible_b, executed=None):
    rows = []
    for ev, sid, d, listed, h, dp in B3:
        b = pe[sid]
        w = d / (up - b) if h == 'up' else -d / (b - down)
        final = b + (w * (up - b) if h == 'up' else w * (down - b))
        if abs(w - listed) > 0.6 * 10 ** -dp:
            bad('B3 %s: formula gives w = %.4f, bible lists %s' % (ev, w, listed))
        if abs(final - (b + d)) > 1e-9:
            bad('B3 %s: final postExposure %.6f != b + dEV' % (ev, final))
        if ('%.*f' % (dp, listed)) not in bible_b:
            bad('B3 %s: the weight %.*f is not in the bible\'s appendix B any more (table changed?)' % (ev, dp, listed))
        rows.append((ev, sid, b, d, w, listed))
    if executed:
        for c in executed:
            d, b = c['dEV'], c['b']
            wu = min(max(d / (up - b), 0), 1) if d > 0 else 0.0
            wd = min(max(-d / (b - down), 0), 1) if d < 0 else 0.0
            if abs(c['wUp'] - wu) > 2e-6 or abs(c['wDown'] - wd) > 2e-6:
                bad('executed C# WeightUp/Down(%g, %g) = %g/%g, expected %g/%g' % (d, b, c['wUp'], c['wDown'], wu, wd))
            app = wu * (up - b) - wd * (b - down)
            if abs(c['applied'] - app) > 2e-5:
                bad('executed C# AppliedDeltaEV(%g, %g) = %g, expected %g' % (d, b, c['applied'], app))
            if abs(c['fill'] - 2 ** -app) > 2e-5:
                bad('executed C# OverlayFillScale = %g, expected %g' % (c['fill'], 2 ** -app))
    return rows


# ------------------------------------------------------------------------------------------ G. reproducibility
def regenerate_check():
    tmp = tempfile.mkdtemp(prefix='lanbai_regen_')
    try:
        dst = os.path.join(tmp, 'Grading')
        os.makedirs(dst)
        for d in ('Editor', 'Runtime'):
            shutil.copytree(os.path.join(KIT, d), os.path.join(dst, d))
        shutil.copy(os.path.join(KIT, 'README_Grading.md'), dst)
        os.makedirs(os.path.join(dst, 'Tools~'))
        shutil.copy(os.path.join(HERE, 'gen_grade_data.py'), os.path.join(dst, 'Tools~'))
        shutil.copytree(os.path.join(HERE, 'inputs'), os.path.join(dst, 'Tools~', 'inputs'))
        shutil.copytree(os.path.join(HERE, 'engine'), os.path.join(dst, 'Tools~', 'engine'),
                        ignore=shutil.ignore_patterns('__pycache__'))
        r = subprocess.run([sys.executable, os.path.join(dst, 'Tools~', 'gen_grade_data.py')], capture_output=True, text=True)
        if r.returncode != 0:
            bad('G. regeneration in a temporary copy failed: %s' % r.stderr.strip().splitlines()[-1:])
            return
        diffs = [f for f in ('Editor/LanbaiGradeData.cs', 'Runtime/LanbaiExposure.cs', 'README_Grading.md')
                 if open(os.path.join(dst, f), 'rb').read() != open(os.path.join(KIT, f), 'rb').read()]
        if diffs:
            bad('G. regenerating from Tools~/inputs changes %s: the shipped files are stale' % diffs)
        else:
            ok('G. regenerated in a temporary copy from Tools~/inputs: LanbaiGradeData.cs, the LanbaiExposure region and the README tables are byte-identical')
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


# ------------------------------------------------------------------------------------------
def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--grades', default=os.path.join(HERE, 'inputs', 'grades_engine.json'))
    ap.add_argument('--lookdef', default=os.path.join(ART, 'grades_final.json'))
    ap.add_argument('--calib', default=os.path.join(ART, 'calib_final.json'))
    ap.add_argument('--calib-engine', default=os.path.join(HERE, 'inputs', 'calib_engine.json'))
    ap.add_argument('--bible', default=os.path.join(ART, 'ART_BIBLE.md'))
    ap.add_argument('--dump', default=os.path.join(HERE, 'compile_check', 'dump.json'),
                    help='JSON printed by the compiled C# (Tools~/compile_check/run_check.sh)')
    ap.add_argument('--report', default=os.path.join(KIT, 'Docs~', 'verify_report.txt'))
    ap.add_argument('--no-regen', action='store_true')
    a = ap.parse_args()
    for p in ('lookdef', 'calib'):
        if not os.path.exists(getattr(a, p)):
            setattr(a, p, os.path.join(HERE, 'inputs', os.path.basename(getattr(a, p))))
    G = json.load(open(a.grades, encoding='utf-8'))
    LG = json.load(open(a.lookdef, encoding='utf-8'))
    C = json.load(open(a.calib, encoding='utf-8'))
    CE = json.load(open(a.calib_engine, encoding='utf-8'))

    parsed, header, forbidden = parse_data_cs(os.path.join(KIT, 'Editor', 'LanbaiGradeData.cs'))
    exp, scenes = expected_from_json(G, C, CE.get('colour_patches'))
    if [round(x, 6) for x in header['ColourPatchLinear']] != [round(v, 6) for c in CE['colour_patches']['linear'] for v in c] \
            or header['ColourPatchNames'] != CE['colour_patches']['names']:
        bad('ColourPatchNames / ColourPatchLinear in the C# differ from calib_engine.json')
    n = diff_entries(parsed, exp, 'C#')
    ok('A. parsed %d entries from LanbaiGradeData.cs, %d field comparisons against grades_engine.json / calib_final.json' % (len(parsed), n))
    if [e['id'] for e in parsed if e['kind'] == 'Scene'] != scenes:
        bad('scene order in C# is not priority order')
    for e in parsed:
        if e['kind'] == 'Scene':
            ov = [k for k in ALL_FIELDS if e.get(k) is not None]
            # PPv2 parameters: hdrNeutral stands for gradingMode + tonemapper, channelMixer for the 9 mixer entries
            npar = len(ov) + (1 if 'hdrNeutral' in ov else 0) + (8 if 'channelMixer' in ov else 0)
            if npar != 31 or len(e['channelMixer']) != 9:
                bad('%s overrides %d PPv2 parameters; every scene profile must override the same 31 (bible 1.4 22 + mixer 9)' % (e['id'], npar))
    ok('   every scene entry carries the same 31-parameter override set (bible 1.4\'s 22 + the 9 Channel Mixer entries)')
    for sid, P in LG['profiles'].items():          # the two layers may differ ONLY in the seven colour parameters
        for k in ('postExposure', 'bloom'):
            if G['profiles'][sid]['ppv2'][k] != P['ppv2'][k]:
                bad('%s.%s differs between the engine numbers and the look definition' % (sid, k))
        if G['profiles'][sid]['ppv2_lookdef'] != {k: P['ppv2'][k] for k in G['profiles'][sid]['ppv2_lookdef']}:
            bad('%s: the ppv2_lookdef record is not grades_final.json' % sid)
    if G['helpers'] != LG['helpers'] or G['common'] != LG['common']:
        bad('helpers / common differ between grades_engine.json and grades_final.json')
    ok('   engine numbers differ from the look definition only in temperature, tint, saturation, contrast, lift, gamma, gain '
       'and the channel mixer (identity in the look definition); postExposure, bloom, helpers, common: identical')
    want_forb = {'AutoExposure', 'MotionBlur', 'DepthOfField', 'ChromaticAberration', 'LensDistortion', 'AmbientOcclusion', 'ScreenSpaceReflections'}
    if set(forbidden) != want_forb:
        bad('ForbiddenEffects %s' % forbidden)

    gsha, lsha, csha, cesha = sha256(a.grades), sha256(a.lookdef), sha256(a.calib), sha256(a.calib_engine)
    chain = [('C# header GradesSha256 = grades_engine.json', header['GradesSha256'] == gsha),
             ('C# header LookDefSha256 = grades_final.json', header['LookDefSha256'] == lsha),
             ('C# header CalibSha256 = calib_final.json', header['CalibSha256'] == csha),
             ('grades_engine.json solved from this grades_final.json', G['_engine']['source_grades_sha256'] == lsha),
             ('grades_engine.json solved against this calib_final.json', G['_engine']['source_calib_sha256'] == csha),
             ('calib_engine.json made from this grades_engine.json', CE['source_grades_engine_sha256'] == gsha),
             ('calib_engine.json made from this calib_final.json', CE['source_calib_sha256'] == csha)]
    for what, good in chain:
        if not good:
            bad('F. sha256 chain broken: %s' % what)
    if all(g for _, g in chain):
        ok('F. sha256 chain intact: C# header -> grades_engine / grades_final / calib_final; engine solve and engine fills -> their sources')

    X = parse_expo_cs(os.path.join(KIT, 'Runtime', 'LanbaiExposure.cs'))
    pe = {e['id']: e['postExposure'] for e in parsed if e['kind'] == 'Scene'}
    if X['sha'] != gsha or X['source'] != 'grades_engine.json':
        bad('LanbaiExposure generated region is stale (sha256 / source)')
    if X['SceneCount'] != len(scenes) or [s for _, s in X['ids']] != scenes or [i for i, _ in X['ids']] != list(range(len(scenes))):
        bad('LanbaiExposure SceneId table %s != %s' % (X['ids'], scenes))
    if X['index'] != [(s, i) for i, s in enumerate(scenes)]:
        bad('LanbaiExposure SceneIndex table wrong')
    if [(i, v) for i, v in X['pe']] != [(i, float(G['profiles'][s]['ppv2']['postExposure'])) for i, s in enumerate(scenes)]:
        bad('LanbaiExposure ScenePostExposure table %s' % X['pe'])
    if X['up'] != G['helpers']['EXPO_UP']['ppv2']['postExposure'] or X['down'] != G['helpers']['EXPO_DOWN']['ppv2']['postExposure']:
        bad('LanbaiExposure EXPO targets %s / %s' % (X['up'], X['down']))
    if len(X['fields_normal']) != len(scenes) or len(X['fields_fallback']) != len(scenes):
        bad('LanbaiExposure volume fields: %d normal, %d fallback' % (len(X['fields_normal']), len(X['fields_fallback'])))
    ok('B. LanbaiExposure generated region: %d scenes in priority order, postExposure table, EXPO +%g / %g' % (X['SceneCount'], X['up'], X['down']))

    executed = None
    if a.dump and os.path.exists(a.dump):
        D = json.load(open(a.dump, encoding='utf-8'))
        n2 = diff_entries(D['entries'], exp, 'compiled C#', f32=True)
        byp = {e['id']: e for e in parsed}
        for e in D['entries']:
            for k in ('predictedTestCard', 'predictedBlack', 'lookDefinition'):
                if e.get(k) != byp[e['id']].get(k):
                    bad('compiled C# %s.%s differs from the parsed source' % (e['id'], k))
            hs = [e['HasColorGrading'], e['HasBloom'], e['HasVignette'], e['HasGrain']]
            want = [e['id'] in exp and any(k in exp[e['id']] for k in grp) for grp in (
                ALL_FIELDS[0:12], ALL_FIELDS[12:20], ALL_FIELDS[20:27], ALL_FIELDS[27:31])]
            if hs != want:
                bad('compiled C# %s Has* flags %s, expected %s' % (e['id'], hs, want))
        if D.get('colourPatchNames') != header['ColourPatchNames'] or \
                any(np.float32(a) != np.float32(b) for a, b in zip(D.get('colourPatchLinear') or [], header['ColourPatchLinear'])) or \
                len(D.get('colourPatchLinear') or []) != len(header['ColourPatchLinear']):
            bad('compiled C# ColourPatchNames / ColourPatchLinear differ from the source')
        for e in D['entries']:
            if e.get('predictedColourPatches') != byp[e['id']].get('predictedColourPatches'):
                bad('compiled C# %s.predictedColourPatches differs from the parsed source' % e['id'])
        ex = D['expo']
        if [s['id'] for s in ex['scenes']] != scenes or any(s['back'] != s['i'] for s in ex['scenes']):
            bad('executed LanbaiExposure.SceneId/SceneIndex mismatch')
        if any(np.float32(s['pe']) != np.float32(pe[s['id']]) for s in ex['scenes']):
            bad('executed LanbaiExposure.ScenePostExposure mismatch')
        blend = ex['blend']
        w_s2s3 = pe['S2'] + (pe['S3'] - pe['S2']) * 0.3
        w_9 = pe['S9a'] + (pe['S9b'] - pe['S9a']) * 0.5
        for got, want, what in ((blend[0], w_s2s3, 'BlendedBase S2=1,S3=0.3'), (blend[1], w_s2s3, 'CrossfadeBase'),
                                (blend[2], w_9, 'BlendedBase S9a=1,S9b=0.5'), (blend[3], pe['S1'], 'BlendedBase S1=1')):
            if abs(got - want) > 1e-6:
                bad('executed %s = %g, expected %g' % (what, got, want))
        rc = ex['routeC']
        for got, want in zip(rc, [0.0, (2 ** 0.5 - 1) / (2 - 1), 1.0, (2 ** -0.4 - 1) / (2 ** -0.8 - 1)]):
            if abs(got - want) > 1e-6:
                bad('executed RouteCCrossfadeWeight %g != %g' % (got, want))
        executed = ex['calls']
        ok('C. compiled + executed C# (%s): %d float32 field comparisons, LanbaiExposure static math run for %d cases'
           % (os.path.relpath(a.dump, KIT), n2, len(executed)))
    else:
        ok('C. (no compiled dump given: run Tools~/compile_check/run_check.sh first)')

    engine_gate(parsed, G, C, CE, header)
    ok('   D0 (informational, NOT an engine check): the look-definition record still reproduces §C in the art simulator: %s'
       % lookdef_consistency(G, C))
    nb, bible_b = bible_checks(a.bible, parsed, G)
    ok('E. ART_BIBLE appendix B: %d values compared (B1 against the look-definition record, B2 against the helpers)' % nb)
    rows = b3_checks(pe, X['up'], X['down'], bible_b, executed)
    ok('   table B3 (v2.1) weights recomputed with w = dEV/(4-b), -dEV/(b+4):')
    for ev, sid, b, d, w, listed in rows:
        ok('     %-44s b = %+.2f (%s)  dEV %+.2f  ->  w = %.4f   (bible %s)' % (ev, b, sid, d, w, listed))
    if not a.no_regen:
        regenerate_check()

    lines = ['Lanbai grade data verification', '=' * 32] + notes + ['']
    lines += (['PROBLEMS (%d):' % len(problems)] + ['  - ' + p for p in problems]) if problems else ['RESULT: PASS (no differences)']
    txt = '\n'.join(lines)
    print(txt)
    os.makedirs(os.path.dirname(a.report), exist_ok=True)
    open(a.report, 'w', encoding='utf-8').write(txt + '\n')
    sys.exit(1 if problems else 0)


if __name__ == '__main__':
    main()
