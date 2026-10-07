# -*- coding: utf-8 -*-
"""Lanbai / 蓝白 -- PPv2 grade data generator.

Two layers of grade numbers exist (verify.md B1, bible law 1 "屏幕目标值是法律，参数只是起点"):
  * LOOK DEFINITION  art/grades_final.json (bible appendix B1). Every screen target in calib_final was made from these
                     numbers with the art simulator, which models the ACES working spaces. They are kept as the record.
  * ENGINE NUMBERS   Tools~/inputs/grades_engine.json, written by Tools~/engine/solve_engine_grades.py: the numbers
                     PPv2 3.x really needs (Neutral path: LogC contrast, linear-709 WB / LGG / saturation) to SHOW the
                     same screen targets. postExposure, bloom, helpers: identical to the look definition.
This generator reads the ENGINE numbers (+ the look definition for traceability), calib_final.json (section C rows)
and Tools~/inputs/calib_engine.json (fills re-solved for the engine), and writes:

  1. Editor/LanbaiGradeData.cs          -- every scene profile + every helper as static C# data
                                           (no runtime JSON parsing; nothing hand-copied), plus the engine model's own
                                           prediction of every test-card patch and of the black point
  2. Runtime/LanbaiExposure.cs          -- only the region between the <lanbai:generated> markers
                                           (scene order, postExposure table, EXPO targets, volume
                                           fields for UdonSharp, which cannot use static data)
  3. README_Grading.md                  -- only the generated tables (engine numbers, look definition, re-solved fills)

Usage (from anywhere):
    python3 gen_grade_data.py [--grades inputs/grades_engine.json] [--lookdef art/grades_final.json]
                              [--calib art/calib_final.json] [--calib-engine inputs/calib_engine.json]
Stops with an error when the engine solve is stale (its recorded sha256 of grades_final / calib_final differs):
re-run Tools~/engine/solve_engine_grades.py and Tools~/engine/engine_calib.py first.
The inputs actually used are copied into ./inputs/ so the kit stays reproducible.
Run verify_grade_data.py afterwards (it parses the C# back, diffs it against the json, and gates the result through
two independent PPv2 engine models).
"""
import argparse
import hashlib
import json
import os
import re
import shutil
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.dirname(HERE)
ART = os.path.normpath(os.path.join(KIT, '..', '..', 'art'))
sys.path.insert(0, os.path.join(HERE, 'engine'))
import ppv2_engine as E  # noqa: E402  (PPv2 3.x Neutral path, written from the package source)

# --------------------------------------------------------------------------------------------
# the rules the bible states in prose (section 1.4 / appendix B) that the json encodes implicitly
# --------------------------------------------------------------------------------------------
SCENE_GROUP, HELPER_GROUP, LENS_GROUP = 'Scenes', 'Helpers', 'Lens_DesktopOnly'
# short scene labels exactly as the bible's 1.7 table names the acts (display only: logs, README, debug window)
SCENE_SHORT = {'S1': '站牌', 'S2': '夜路', 'S3': '月海 · 基准 EV0', 'S4': '触手之门', 'S4c': '门内', 'S6': '晨',
               'S7a': '海面之下', 'S7b': '深海 · 河伯', 'S8': '暮', 'S8b': '蓝时', 'S9a': '星海', 'S9b': '星海高潮',
               'S10': '白 · 中性', 'S11': '假醒 (= S2)', 'S12': '醒'}
# human labels for the helpers (the json only has ids); unknown helpers fall back to their id
HELPER_NAMES = {
    'EXPO_UP': '曝光助手 +4 EV 远目标 (w = dEV/(4-b))',
    'EXPO_DOWN': '曝光助手 -4 EV 远目标 (w = -dEV/(b+4))',
    'WHITE_SAT': '白光 饱和 -30',
    'WHITE_BLOOM': '白光 bloom 12 / 0.8 / 0.8 / 9',
    'LENS_CLEAN': '桌面镜头层 干净 (暗角 0.20 + 颗粒 0.06)',
    'LENS_ARCHIVE': '桌面镜头层 档案 1951 (暗角 0.26 + 颗粒 0.20)',
}
# PPv2 effect types no Lanbai profile may carry (json "common": "... off")
FORBIDDEN = [('autoExposure', 'AutoExposure'), ('motionBlur', 'MotionBlur'), ('depthOfField', 'DepthOfField'),
             ('chromaticAberration', 'ChromaticAberration'), ('lensDistortion', 'LensDistortion'),
             ('ambientOcclusion', 'AmbientOcclusion'), ('screenSpaceReflections', 'ScreenSpaceReflections')]
# helpers.<ppv2 key> -> entry field
PPV2_KEYS = {'postExposure': 'postExposure', 'temperature': 'temperature', 'tint': 'tint', 'saturation': 'saturation',
             'contrast': 'contrast', 'hueShift': 'hueShift', 'colorFilter': 'colorFilter',
             'lift': 'lift', 'gamma': 'gamma', 'gain': 'gain'}
BLOOM_KEYS = {'intensity': 'bloomIntensity', 'threshold': 'bloomThreshold', 'softKnee': 'bloomSoftKnee',
              'clamp': 'bloomClamp', 'diffusion': 'bloomDiffusion', 'anamorphicRatio': 'bloomAnamorphicRatio',
              'color': 'bloomColor', 'fastMode': 'bloomFastMode'}
VIGNETTE_KEYS = {'mode': 'vignetteMode', 'color': 'vignetteColor', 'center': 'vignetteCenter',
                 'intensity': 'vignetteIntensity', 'smoothness': 'vignetteSmoothness',
                 'roundness': 'vignetteRoundness', 'rounded': 'vignetteRounded'}
GRAIN_KEYS = {'colored': 'grainColored', 'intensity': 'grainIntensity', 'size': 'grainSize',
              'lumContrib': 'grainLumContrib', 'luminanceContribution': 'grainLumContrib'}

# order of fields in the C# initialiser (also the order verify_grade_data.py prints)
FIELDS = [
    ('id', 'string'), ('shortName', 'string'), ('displayName', 'string'), ('kind', 'kind'), ('group', 'string'), ('priority', 'float'),
    ('initialWeight', 'float'), ('desktopOnly', 'bool'), ('weightRule', 'string'),
    ('hdrNeutral', 'bool?'), ('postExposure', 'float?'), ('temperature', 'float?'), ('tint', 'float?'),
    ('colorFilter', 'string'), ('hueShift', 'float?'), ('saturation', 'float?'), ('contrast', 'float?'),
    ('lift', 'float[]'), ('gamma', 'float[]'), ('gain', 'float[]'), ('channelMixer', 'float[]'),
    ('bloomIntensity', 'float?'), ('bloomThreshold', 'float?'), ('bloomSoftKnee', 'float?'), ('bloomClamp', 'float?'),
    ('bloomDiffusion', 'float?'), ('bloomAnamorphicRatio', 'float?'), ('bloomColor', 'string'), ('bloomFastMode', 'bool?'),
    ('bloomColorCompensated', 'float[]'),
    ('vignetteMode', 'string'), ('vignetteColor', 'string'), ('vignetteCenter', 'float[]'), ('vignetteIntensity', 'float?'),
    ('vignetteSmoothness', 'float?'), ('vignetteRoundness', 'float?'), ('vignetteRounded', 'bool?'),
    ('grainColored', 'bool?'), ('grainIntensity', 'float?'), ('grainSize', 'float?'), ('grainLumContrib', 'float?'),
    ('bloomT0', 'float?'), ('expectedTestCard', 'string[]'), ('predictedTestCard', 'string[]'),
    ('expectedColourPatches', 'string[]'), ('predictedColourPatches', 'string[]'),
    ('expectedBlack', 'string'), ('predictedBlack', 'string'), ('lookDefinition', 'string'), ('routeCLut', 'string'),
]
# the PPv2 parameters an entry can override (bloomColorCompensated is another spelling of bloomColor, not a parameter)
PARAM_FIELDS = [n for n, _ in FIELDS[FIELDS.index(('hdrNeutral', 'bool?')):FIELDS.index(('grainLumContrib', 'float?')) + 1]
                if n != 'bloomColorCompensated']
COLOUR_KEYS = ('temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain')


def sha256(path):
    return hashlib.sha256(open(path, 'rb').read()).hexdigest()


def cs_float(x):
    x = float(x)
    if x != x or x in (float('inf'), float('-inf')):
        raise ValueError('non-finite float %r' % x)
    s = repr(x)
    if s.endswith('.0'):
        s = s[:-2]
    if s == '-0':
        s = '0'
    return s + 'f'


def cs_string(s):
    out = ['"']
    for ch in s:
        if ch == '\\':
            out.append('\\\\')
        elif ch == '"':
            out.append('\\"')
        elif ch == '\n':
            out.append('\\n')
        elif ord(ch) < 32:
            out.append('\\u%04x' % ord(ch))
        else:
            out.append(ch)
    out.append('"')
    return ''.join(out)


def cs_value(v, typ):
    if v is None:
        return None
    if typ == 'string':
        return cs_string(v)
    if typ in ('float', 'float?'):
        return cs_float(v)
    if typ in ('bool', 'bool?'):
        return 'true' if v else 'false'
    if typ == 'kind':
        return 'LanbaiGradeKind.' + v
    if typ == 'float[]':
        return 'new float[] { ' + ', '.join(cs_float(x) for x in v) + ' }'
    if typ == 'string[]':
        return 'new string[] { ' + ', '.join(cs_string(x) for x in v) + ' }'
    raise ValueError(typ)


def hexcheck(h, where):
    if not re.fullmatch(r'#[0-9A-Fa-f]{6}', h or ''):
        raise ValueError('%s: bad hex colour %r' % (where, h))
    return h.upper()


def srgb_encode1(v):
    v = min(max(float(v), 0.0), 1.0)
    return 12.92 * v if v <= 0.0031308 else 1.055 * v ** (1 / 2.4) - 0.055


def bloom_compensated(hexcol):
    """PPv2 Bloom: uberSheet.properties.SetColor(Bloom_Color, settings.color.value.linear). Color.linear decodes sRGB once,
    and MaterialPropertyBlock.SetColor decodes again in a Linear project, so the shader gets srgb_decode(srgb_decode(c)).
    The bible means a linear tint of srgb_decode(hex) (the art simulator decodes once). The raw Color c that gives exactly
    that under double decoding is c = srgb_encode(hex / 255) (6 decimals; no 8-bit rounding)."""
    h = hexcol.lstrip('#')
    return [round(srgb_encode1(int(h[i:i + 2], 16) / 255.0), 6) for i in (0, 2, 4)]


COLOUR_PATCHES = {}      # filled from calib_engine.json: names, scene-linear rgb, the look's hex per profile


def engine_prediction(p, common):
    """(11 test-card hex, black hex, colour-row hex) that the engine model predicts for these engine numbers
    (33^3 half LUT, trilinear)."""
    import numpy as np
    q = {k: p[k] for k in ('postExposure',) + COLOUR_KEYS}
    q['mixer'] = p.get('mixer', E.MIXER_IDENTITY)
    q.update(colorFilter=common['colorFilter'], hueShift=common['hueShift'])
    L = E.bake_lut(q)
    P = np.stack([np.full(3, 0.18 * 2.0 ** k) for k in range(-6, 5)] + [np.zeros(3)] +
                 [np.asarray(c, np.float64) for c in COLOUR_PATCHES['linear']])
    c = E.codes(P, q, L)
    hx = [E.to_hex(v) for v in c]
    return hx[:11], hx[11], hx[12:]


def fmt_v4(v):
    return '(%s)' % ', '.join(('%g' % x) for x in v)


def lookdef_text(ld):
    return ('look definition (bible B1, art simulator): temperature %+g, tint %+g, saturation %+g, contrast %+g, '
            'lift %s, gamma %s, gain %s' % (ld['temperature'], ld['tint'], ld['saturation'], ld['contrast'],
                                           fmt_v4(ld['lift']), fmt_v4(ld['gamma']), fmt_v4(ld['gain'])))


def route_c_luts():
    """Scene id -> Texture3D name that PPv2's CubeLutAssetImporter makes from art/luts/hdr_external/<name>.cube."""
    import glob
    out = {}
    for f in sorted(glob.glob(os.path.join(ART, 'luts', 'hdr_external', 'Lanbai_*_HDRext33.cube'))):
        n = os.path.splitext(os.path.basename(f))[0]
        m = re.match(r'Lanbai_(S\d+[a-z]?)_', n)
        if m:
            out[m.group(1)] = n
    return out


# --------------------------------------------------------------------------------------------
ROUTE_C = {}


def build_entries(G, C):
    """json -> ordered list of entry dicts (keys = FIELDS names). Raises on anything unknown."""
    warnings = []
    if '_engine' not in G:
        raise ValueError('--grades must be the ENGINE grade set (Tools~/inputs/grades_engine.json), not the look definition')
    common = G['common']
    for key, cls in FORBIDDEN:
        if common.get(key) != 'off':
            raise ValueError('common.%s is %r, expected "off"' % (key, common.get(key)))
    if common.get('mixer') != 'identity' or common.get('curves') != 'default':
        raise ValueError('common.mixer/curves changed: the builder only supports identity/default')
    if common['bloom'].get('dirt') is not None:
        raise ValueError('common.bloom.dirt is set: the bible forbids bloom dirt')

    entries = []
    scenes = sorted(G['profiles'].items(), key=lambda kv: kv[1]['priority'])
    first_scene = scenes[0][0]
    for sid, prof in scenes:
        p, b = prof['ppv2'], prof['ppv2']['bloom']
        unknown = set(p) - {'postExposure', 'temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain', 'mixer', 'bloom'}
        unknown |= set(b) - {'intensity', 'threshold', 'softKnee', 'diffusion', 'color'}
        if unknown:
            raise ValueError('profile %s: unknown keys %s (teach the generator first)' % (sid, sorted(unknown)))
        ramp = C['ramp'].get(sid)
        if ramp is None or len(ramp) != 11:
            raise ValueError('calib_final.json ramp for %s missing or not 11 patches' % sid)
        ld = prof.get('ppv2_lookdef')
        if ld is None or set(ld) != set(COLOUR_KEYS):
            raise ValueError('profile %s: ppv2_lookdef missing or incomplete: is this grades_engine.json '
                             '(Tools~/engine/solve_engine_grades.py)?' % sid)
        pred, pblack, pcol = engine_prediction(p, common)
        if pcol != COLOUR_PATCHES['engine'][sid]:
            raise ValueError('%s: colour-row prediction differs from calib_engine.json: re-run engine_calib.py' % sid)
        rep = G['_engine']['report'][sid]
        e = dict(
            id=sid, shortName=SCENE_SHORT.get(sid, prof['name'].split(' ')[0]), displayName=prof['name'], kind='Scene', group=SCENE_GROUP, priority=prof['priority'],
            initialWeight=1.0 if sid == first_scene else 0.0, desktopOnly=False,
            weightRule=('first scene: weight 1 at load' if sid == first_scene else
                        'scene crossfade: incoming 0->1 while outgoing stays 1, then outgoing -> 0 (bible 1.4)'),
            hdrNeutral=True,
            postExposure=p['postExposure'], temperature=p['temperature'], tint=p['tint'],
            colorFilter=hexcheck(common['colorFilter'], sid + '.colorFilter'), hueShift=common['hueShift'],
            saturation=p['saturation'], contrast=p['contrast'],
            lift=list(p['lift']), gamma=list(p['gamma']), gain=list(p['gain']),
            channelMixer=[float(v) for v in p.get('mixer', [100, 0, 0, 0, 100, 0, 0, 0, 100])],
            bloomIntensity=b['intensity'], bloomThreshold=b['threshold'], bloomSoftKnee=b['softKnee'],
            bloomClamp=common['bloom']['clamp'], bloomDiffusion=b['diffusion'],
            bloomAnamorphicRatio=common['bloom']['anamorphicRatio'], bloomColor=hexcheck(b['color'], sid + '.bloom.color'),
            bloomFastMode=bool(common['bloom']['fastMode']),
            vignetteIntensity=common['vignette']['intensity'], grainIntensity=common['grain']['intensity'],
            bloomColorCompensated=bloom_compensated(hexcheck(b['color'], sid + '.bloom.color')),
            bloomT0=prof['bloom_T0_scene_linear'], expectedTestCard=[hexcheck(h, sid + '.ramp') for h in ramp],
            predictedTestCard=pred, expectedBlack=hexcheck(rep['black']['target'], sid + '.black'), predictedBlack=pblack,
            expectedColourPatches=list(COLOUR_PATCHES['look'][sid]), predictedColourPatches=pcol,
            lookDefinition=lookdef_text(ld), routeCLut=ROUTE_C.get(sid),
        )
        for k in ('lift', 'gamma', 'gain'):
            if len(e[k]) != 4:
                raise ValueError('%s.%s must be a Vector4' % (sid, k))
        if len(e['channelMixer']) != 9 or any(abs(v) > 200 for v in e['channelMixer']):
            raise ValueError('%s.mixer must be 9 percentages in [-200, 200]' % sid)
        entries.append(e)

    v1 = G.get('lens_desktop_only', {})
    helpers = [(k, v) for k, v in G['helpers'].items() if not k.startswith('_')]
    helpers.sort(key=lambda kv: (kv[1]['priority'], kv[0]))
    for hid, h in helpers:
        known = {'priority', 'ppv2', 'weight', 'events', 'desktop_only', 'vignette', 'grain'}
        if set(h) - known:
            raise ValueError('helper %s: unknown keys %s' % (hid, sorted(set(h) - known)))
        lens = bool(h.get('desktop_only'))
        e = dict(id=hid, shortName=hid, displayName=HELPER_NAMES.get(hid, hid), kind='Lens' if lens else 'Helper', group=LENS_GROUP if lens else HELPER_GROUP,
                 priority=h['priority'], desktopOnly=lens, weightRule=h['weight'],
                 # bible 1.4: LENS_CLEAN "在桌面上始终为 1，包括第 1 幕"; everything else starts at 0
                 initialWeight=1.0 if hid == 'LENS_CLEAN' else 0.0)
        for k, v in h.get('ppv2', {}).items():
            if k == 'bloom':
                for bk, bv in v.items():
                    if bk not in BLOOM_KEYS:
                        raise ValueError('helper %s bloom.%s unknown' % (hid, bk))
                    e[BLOOM_KEYS[bk]] = hexcheck(bv, hid) if bk == 'color' else bv
                    if bk == 'color':
                        e['bloomColorCompensated'] = bloom_compensated(e['bloomColor'])
            elif k in PPV2_KEYS:
                e[PPV2_KEYS[k]] = hexcheck(v, hid) if k == 'colorFilter' else v
            else:
                raise ValueError('helper %s ppv2.%s unknown' % (hid, k))
        # lens layers: v2 values from helpers.*; the v1 block lens_desktop_only only contributes the
        # vignette SHAPE fields that v2 does not state (they equal the PPv2 defaults). Conflicts are
        # reported and resolved in favour of v2 (bible 1.4 / B2: LENS_CLEAN 199, LENS_ARCHIVE 200).
        old = v1.get(hid, {})
        for sect, keys, prefix in (('vignette', VIGNETTE_KEYS, 'vignette'), ('grain', GRAIN_KEYS, 'grain')):
            if sect not in h:
                continue
            for k, v in h[sect].items():
                if k not in keys:
                    raise ValueError('helper %s %s.%s unknown' % (hid, sect, k))
                e[keys[k]] = hexcheck(v, hid) if k == 'color' else v
            for k, v in old.get(sect, {}).items():
                if k not in keys:
                    raise ValueError('lens_desktop_only %s %s.%s unknown' % (hid, sect, k))
                f = keys[k]
                if f in e:
                    if (hexcheck(v, hid) if k == 'color' else v) != e[f]:
                        warnings.append('%s.%s: v1 block lens_desktop_only says %r, v2 helpers says %r -> using v2 %r'
                                        % (hid, f, v, e[f], e[f]))
                else:
                    e[f] = list(v) if isinstance(v, list) else v
        if old and old.get('priority') != h['priority']:
            warnings.append('%s.priority: v1 block lens_desktop_only says %r, v2 helpers says %r -> using v2 %r '
                            '(bible 1.4: LENS_CLEAN 199 / LENS_ARCHIVE 200, archive sits above clean)'
                            % (hid, old.get('priority'), h['priority'], h['priority']))
        if e.get('vignetteMode') not in (None, 'Classic'):
            raise ValueError('only Classic vignette is supported')
        entries.append(e)

    ids = [e['id'] for e in entries]
    if len(set(ids)) != len(ids):
        raise ValueError('duplicate ids %s' % ids)
    for e in entries:
        for name, _ in FIELDS:
            e.setdefault(name, None)
        if set(e) - {n for n, _ in FIELDS}:
            raise ValueError('internal: stray keys %s' % (set(e) - {n for n, _ in FIELDS}))
    return entries, warnings


# --------------------------------------------------------------------------------------------
HEADER = '''﻿// <auto-generated>
//   Lanbai / 蓝白 -- PPv2 grade data (ART BIBLE v2.1, section 1.4 / appendix B; screen targets: calib_final).
//   GENERATED by Tools~/gen_grade_data.py -- DO NOT HAND-EDIT.
//   Engine numbers : grades_engine.json  sha256 {gsha}
//   Look definition: grades_final.json   sha256 {lsha} (bible appendix B1; kept per entry in lookDefinition)
//   Test-card rows : calib_final.json    sha256 {csha} (section C)
//   To change a grade: art side edits art/bible_work/make_grades.py -> grades_final.json, then
//   Tools~/engine/solve_engine_grades.py -> engine_calib.py -> gen_grade_data.py -> verify_grade_data.py.
//
//   Why two sets of numbers (verify.md B1): the art simulator that defined the look runs the ACES working spaces;
//   PPv2 3.x with the Neutral tonemapper applies contrast in LogC and white balance / lift-gamma-gain / saturation
//   in linear Rec.709. The look-definition numbers crush night blacks to #000000 there. The numbers below are
//   solved so that PPv2's real Neutral path SHOWS the bible's screen targets (bible law 1: targets are law).
//   postExposure, bloom and every helper are identical to the look definition.
//
//   Semantics (read before touching LanbaiGradeBuilder):
//   * null / NaN-free: a null field means "this profile does NOT override that parameter".
//   * Colours are the hex the Unity colour picker shows (sRGB-coded Color, exactly like typing the hex).
//     colorFilter: PPv2 passes it RAW to the LUT baker (SetComputeVectorParam, no .linear). All Lanbai profiles use white.
//   * bloomColor = the bible's hex, meaning a linear tint of sRGB-decode(hex). PPv2's Bloom calls Color.linear and
//     then MaterialPropertyBlock.SetColor, which in a Linear project decodes AGAIN: the shader gets the tint decoded
//     twice (warm / cool tints come out too strong). bloomColorCompensated = the raw Color (r, g, b) that lands on the
//     intended tint after that double decode. The builder writes it unless the bloom-colour probe
//     (蓝白/Grades/Probe Bloom Colour) measured single decoding on this machine.
//   * lift / gamma / gain are the PPv2 trackball Vector4 (x, y, z = wheel colour, w = offset).
//   * channelMixer = PPv2 Channel Mixer, 9 percentages row-major: mixerRedOutRedIn, mixerRedOutGreenIn,
//     mixerRedOutBlueIn, mixerGreenOutRedIn, ..., mixerBlueOutBlueIn (identity 100/0/0, 0/100/0, 0/0/100). Within a few
//     points of identity: it lets the engine reproduce the look's ACES (AP1) working space on saturated colours.
//   * bloomThreshold and bloomClamp are GAMMA-space numbers, exactly as PPv2 wants them
//     (clamp 4.24 = 24 scene-linear). bloomT0 = scene-linear value where the soft knee starts
//     (informational: calib_final.md "xT0" column divides by it).
//   * expectedTestCard = calib_final.md section C: screen hex of the 11 unlit patches 0.18*2^k,
//     k = -6..+4, under this profile alone at weight 1, bloom off (tolerance +-3 codes).
//     predictedTestCard / predictedBlack = what the art side's model of PPv2's Neutral path predicts for the
//     numbers below (33^3 half LUT): if Unity reads the prediction but misses the target, the solve is off;
//     if Unity misses the prediction, the model of the engine is off. expectedBlack = the target at input 0.
//   * expectedColourPatches / predictedColourPatches = the test card's colour row (ColourPatchLinear, 8 saturated
//     colours) as the look shows it (art simulator) and as the engine model predicts it. Not bible targets: they
//     check that Unity handles saturated colours the way the model says (the channel mixer's job).
//   * routeCLut = name of the Texture3D PPv2 imports from art/luts/hdr_external/<name>.cube (Route C fallback, bible 1.7).
// </auto-generated>
{warn}
namespace Lanbai.Grading
{{
    public enum LanbaiGradeKind
    {{
        Scene = 0,   // one global volume per scene, crossfaded by weight
        Helper = 1,  // EXPO_UP / EXPO_DOWN / WHITE_SAT / WHITE_BLOOM: far targets, weight solved by the Director
        Lens = 2,    // desktop-only camera layers (vignette + grain); GameObjects disabled in VR
    }}

    public sealed class LanbaiGradeEntry
    {{
        public string id;
        public string shortName;        // the act's name as the bible's 1.7 table writes it
        public string displayName;
        public LanbaiGradeKind kind;
        public string group;            // child of the Lanbai_Grades root the volume lives under
        public float priority;
        public float initialWeight;     // weight written by the builder (runtime weights belong to the Director)
        public bool desktopOnly;
        public string weightRule;       // how the Director drives this volume (from the json)

        // ---- Color Grading (null = not overridden)
        public bool? hdrNeutral;        // true: gradingMode = HighDefinitionRange AND tonemapper = Neutral
        public float? postExposure;
        public float? temperature;
        public float? tint;
        public string colorFilter;
        public float? hueShift;
        public float? saturation;
        public float? contrast;
        public float[] lift;            // Vector4
        public float[] gamma;           // Vector4
        public float[] gain;            // Vector4
        public float[] channelMixer;    // 9 percentages, row-major (RR, RG, RB, GR, GG, GB, BR, BG, BB)

        // ---- Bloom
        public float? bloomIntensity;
        public float? bloomThreshold;   // gamma space
        public float? bloomSoftKnee;
        public float? bloomClamp;       // gamma space
        public float? bloomDiffusion;
        public float? bloomAnamorphicRatio;
        public string bloomColor;
        public bool? bloomFastMode;
        public float[] bloomColorCompensated;   // raw Color rgb for PPv2's double sRGB decode of the bloom tint (see header)

        // ---- Vignette
        public string vignetteMode;     // "Classic" only
        public string vignetteColor;
        public float[] vignetteCenter;  // Vector2
        public float? vignetteIntensity;
        public float? vignetteSmoothness;
        public float? vignetteRoundness;
        public bool? vignetteRounded;

        // ---- Grain
        public bool? grainColored;
        public float? grainIntensity;
        public float? grainSize;
        public float? grainLumContrib;

        // ---- information for tools
        public float? bloomT0;
        public string[] expectedTestCard;   // calib section C (the law)
        public string[] predictedTestCard;  // art-side engine model's prediction for these numbers
        public string[] expectedColourPatches;   // colour row as the LOOK shows it (art simulator)
        public string[] predictedColourPatches;  // colour row as the engine model predicts it
        public string expectedBlack;        // screen hex at input 0 the bible asks for
        public string predictedBlack;       // engine model's prediction at input 0
        public string lookDefinition;       // bible B1 numbers (art simulator), for the record
        public string routeCLut;            // Route C: Texture3D imported from art/luts/hdr_external/<routeCLut>.cube

        public bool HasColorGrading {{ get {{ return hdrNeutral.HasValue || postExposure.HasValue || temperature.HasValue || tint.HasValue || colorFilter != null || hueShift.HasValue || saturation.HasValue || contrast.HasValue || lift != null || gamma != null || gain != null || channelMixer != null; }} }}
        public bool HasBloom {{ get {{ return bloomIntensity.HasValue || bloomThreshold.HasValue || bloomSoftKnee.HasValue || bloomClamp.HasValue || bloomDiffusion.HasValue || bloomAnamorphicRatio.HasValue || bloomColor != null || bloomFastMode.HasValue; }} }}
        public bool HasVignette {{ get {{ return vignetteMode != null || vignetteColor != null || vignetteCenter != null || vignetteIntensity.HasValue || vignetteSmoothness.HasValue || vignetteRoundness.HasValue || vignetteRounded.HasValue; }} }}
        public bool HasGrain {{ get {{ return grainColored.HasValue || grainIntensity.HasValue || grainSize.HasValue || grainLumContrib.HasValue; }} }}
    }}

    public static class LanbaiGradeData
    {{
        public const string GradesSha256 = "{gsha}";        // grades_engine.json
        public const string LookDefSha256 = "{lsha}";       // grades_final.json (bible B1)
        public const string CalibSha256 = "{csha}";

        /// <summary>Test card colour row: names and scene-linear rgb (3 floats each), left to right.</summary>
        public static readonly string[] ColourPatchNames = new string[] {{ {cpnames} }};
        public static readonly float[] ColourPatchLinear = new float[] {{ {cplin} }};

        /// <summary>PPv2 effect types no Lanbai profile may carry (bible 1.4: "任何 profile 都不许开").</summary>
        public static readonly string[] ForbiddenEffects = new string[] {{ {forbidden} }};

        /// <summary>Every volume, scenes first (priority order), then helpers and lens layers (priority order).</summary>
        public static readonly LanbaiGradeEntry[] Entries = new LanbaiGradeEntry[]
        {{
{entries}
        }};

        public static LanbaiGradeEntry Find(string id)
        {{
            for (int i = 0; i < Entries.Length; i++)
                if (Entries[i].id == id) return Entries[i];
            return null;
        }}
    }}
}}
'''


def emit_entry(e):
    lines = ['            new LanbaiGradeEntry', '            {']
    for name, typ in FIELDS:
        v = cs_value(e[name], typ)
        if v is None:
            continue
        lines.append('                %s = %s,' % (name, v))
    lines.append('            },')
    return '\n'.join(lines)


def gen_data_cs(entries, warnings, gsha, lsha, csha):
    warn = ''
    if warnings:
        warn = '\n'.join(['// Resolved json conflicts (generator warnings):'] + ['//   ' + w for w in warnings]) + '\n'
    return HEADER.format(gsha=gsha, lsha=lsha, csha=csha, warn=warn,
                         cpnames=', '.join(cs_string(n) for n in COLOUR_PATCHES['names']),
                         cplin=', '.join(cs_float(v) for c in COLOUR_PATCHES['linear'] for v in c),
                         forbidden=', '.join(cs_string(c) for _, c in FORBIDDEN),
                         entries='\n'.join(emit_entry(e) for e in entries))


# --------------------------------------------------------------------------------------------
GEN_BEGIN = '// <lanbai:generated'
GEN_END = '// </lanbai:generated>'


def gen_exposure_region(entries, G, gsha):
    scenes = [e for e in entries if e['kind'] == 'Scene']
    up = G['helpers']['EXPO_UP']['ppv2']['postExposure']
    down = G['helpers']['EXPO_DOWN']['ppv2']['postExposure']
    if not (up > 0 > down):
        raise ValueError('EXPO_UP must be > 0 and EXPO_DOWN < 0')
    L = ['    %s source="grades_engine.json" sha256="%s">' % (GEN_BEGIN, gsha),
         '    // GENERATED by Tools~/gen_grade_data.py. Do not hand-edit between the markers.',
         '    // Udon cannot read static C# data, so the few numbers the Director needs live here as',
         '    // consts / switch tables (no allocation, callable from static methods).',
         '    public const int SceneCount = %d;' % len(scenes),
         '    public const float ExpoUpTarget = %s;   // EXPO_UP postExposure (priority %s)' % (cs_float(up), G['helpers']['EXPO_UP']['priority']),
         '    public const float ExpoDownTarget = %s; // EXPO_DOWN postExposure (priority %s)' % (cs_float(down), G['helpers']['EXPO_DOWN']['priority']),
         '',
         '    /// <summary>Scene index (0 = lowest priority) -> profile id. Volume GameObject = "PPV_" + id.</summary>',
         '    public static string SceneId(int i)',
         '    {',
         '        switch (i)',
         '        {']
    for i, e in enumerate(scenes):
        L.append('            case %d: return %s;' % (i, cs_string(e['id'])))
    L += ['        }', '        return "";', '    }', '',
          '    /// <summary>Profile id -> scene index, -1 if unknown.</summary>',
          '    public static int SceneIndex(string id)',
          '    {']
    for i, e in enumerate(scenes):
        L.append('        if (id == %s) return %d;' % (cs_string(e['id']), i))
    L += ['        return -1;', '    }', '',
          '    /// <summary>Scene index -> that profile\'s postExposure (EV). Used for the base b.</summary>',
          '    public static float ScenePostExposure(int i)',
          '    {',
          '        switch (i)',
          '        {']
    for i, e in enumerate(scenes):
        L.append('            case %d: return %s; // %s  priority %s' % (i, cs_float(e['postExposure']), e['id'], e['priority']))
    L += ['        }', '        return 0f;', '    }', '',
          '    // one field per scene volume: Udon-safe (no PostProcessVolume[] allocation at runtime)']

    def typed(T):
        out = []
        for i, e in enumerate(scenes):
            out.append('    private %s _scene%d; // %s' % (T, i, e['id']))
        out += ['', '    private %s GetSceneVolumeRaw(int i)' % T, '    {', '        switch (i)', '        {']
        for i, e in enumerate(scenes):
            out.append('            case %d: return _scene%d;' % (i, i))
        out += ['        }', '        return null;', '    }', '',
                '    private void SetSceneVolumeRaw(int i, %s v)' % T, '    {', '        switch (i)', '        {']
        for i, e in enumerate(scenes):
            out.append('            case %d: _scene%d = v; break;' % (i, i))
        out += ['        }', '    }']
        return out

    L += ['#if LANBAI_PPV_ANIMATOR_FALLBACK'] + typed('Animator') + ['#else'] + typed('PostProcessVolume') + ['#endif']
    L += ['    ' + GEN_END]
    return '\n'.join(L)


def replace_region(text, region, begin, end):
    a = text.find(begin)
    b = text.find(end)
    if a < 0 or b < 0 or b < a:
        raise ValueError('generated markers not found')
    a = text.rfind('\n', 0, a) + 1          # start of the line holding the begin marker
    b = b + len(end)
    return text[:a] + region + text[b:]


# --------------------------------------------------------------------------------------------
def fmt(x, nd=2, sign=True):
    return ('%+.*f' if sign else '%.*f') % (nd, x)


def v4(v):
    return '(%s)' % ', '.join(('%g' % x) for x in v)


def comp_hex(rgb):
    return '#%02X%02X%02X' % tuple(int(round(min(max(v, 0.0), 1.0) * 255)) for v in rgb)


def gen_readme_table(entries, warnings, G, CE):
    L = ['<!-- lanbai:generated:table (Tools~/gen_grade_data.py; do not hand-edit) -->', '',
         '**场景 profile · 引擎参数（真正写进 profile 的数；15 个；每个都覆盖同一整套 31 个参数；HDR + Neutral；colorFilter `#FFFFFF`、hueShift 0；'
         'bloom clamp 4.24（gamma）、anamorphicRatio 0、fastMode true；Vignette / Grain intensity 0）**', '',
         '| Volume | 优先级 | 初始 weight | postExp | 色温 | 色调 | 饱和 | 对比 | lift | gamma | gain | Channel Mixer（R / G / B 三行，%） | bloom 强度 / 阈值 / 软膝 / 扩散 / 颜色（写入值） | T0 |',
         '|---|---|---|---|---|---|---|---|---|---|---|---|---|---|']
    for e in entries:
        if e['kind'] != 'Scene':
            continue
        col = e['bloomColor']
        cc = comp_hex(e['bloomColorCompensated'])
        colcell = '`%s`' % col if cc == col else '`%s`（补偿后 ≈ `%s`）' % (col, cc)
        m = e['channelMixer']
        mix = ' / '.join('(%g, %g, %g)' % tuple(m[i:i + 3]) for i in (0, 3, 6))
        L.append('| `PPV_%s` %s | %g | %g | %s | %+.2f | %+.2f | %+.2f | %+.2f | %s | %s | %s | %s | %g / %g / %g / %g / %s | %.3f |' % (
            e['id'], e['shortName'], e['priority'], e['initialWeight'], fmt(e['postExposure']),
            e['temperature'], e['tint'], e['saturation'], e['contrast'], v4(e['lift']), v4(e['gamma']), v4(e['gain']), mix,
            e['bloomIntensity'], e['bloomThreshold'], e['bloomSoftKnee'], e['bloomDiffusion'], colcell, e['bloomT0']))
    L += ['', '**同一批 profile 的“外观定义”（圣经附录 B1 / `grades_final.json`；只在美术模拟器里成立，仅供对照，不要输进 Unity）与引擎预测**', '',
          '| Profile | 色温 | 色调 | 饱和 | 对比 | lift | gamma | gain | 黑点目标（输入 0） | 引擎预测黑点 | §C 引擎预测最大误差 |',
          '|---|---|---|---|---|---|---|---|---|---|---|']
    for e in entries:
        if e['kind'] != 'Scene':
            continue
        ld = G['profiles'][e['id']]['ppv2_lookdef']
        worst = max(max(abs(int(a[i:i + 2], 16) - int(b[i:i + 2], 16)) for i in (1, 3, 5))
                    for a, b in zip(e['expectedTestCard'], e['predictedTestCard']))
        L.append('| %s | %+g | %+g | %+g | %+g | %s | %s | %s | `%s` | `%s` | %d 码 |' % (
            e['id'], ld['temperature'], ld['tint'], ld['saturation'], ld['contrast'], v4(ld['lift']), v4(ld['gamma']), v4(ld['gain']),
            e['expectedBlack'], e['predictedBlack'], worst))
    L += ['', '**助手与镜头层（只覆盖列出的参数；与圣经表 B2 相同）**', '',
          '| Volume | 优先级 | 初始 weight | 覆盖的参数 | weight 怎么走 |', '|---|---|---|---|---|']
    for e in entries:
        if e['kind'] == 'Scene':
            continue
        parts = []
        for name in PARAM_FIELDS:
            v = e[name]
            if v is None:
                continue
            if isinstance(v, list):
                v = v4(v)
            elif isinstance(v, bool):
                v = 'true' if v else 'false'
            elif isinstance(v, float) or isinstance(v, int):
                v = '%g' % v
            if name == 'bloomColor' and e.get('bloomColorCompensated'):
                v = '%s（补偿后 ≈ %s）' % (v, comp_hex(e['bloomColorCompensated']))
            parts.append('%s %s' % (name, v))
        L.append('| `PPV_%s` | %g | %g | %s | %s |' % (e['id'], e['priority'], e['initialWeight'], '；'.join(parts),
                                                     e['weightRule'].replace('|', '/')))
    rows = [r for r in CE['unlit'] if 'set_engine' in r]
    ov = [r for r in CE['overlay'] if 'set_engine' in r]
    kept = [r for r in CE['unlit'] if 'kept' in r]
    L += ['', '**`calib_final.md` §B 里要改填的值（引擎版；其余 %d 项照 `calib_final.md` 原样填，引擎下误差 ≤ %d 码）**' % (
        len(CE['unlit']) - len(rows), max(r['codes'] for r in CE['unlit'] if 'set_engine' not in r)), '',
          '| 幕 | 元素 | 屏幕目标（不变） | `calib_final` 的填值 → 引擎显示 | **引擎版填值** → 引擎显示 |', '|---|---|---|---|---|']
    for r in rows:
        L.append('| %s | %s | `%s` | `%s` → `%s`（差 %d） | **`%s`** → `%s`（差 %d） |' % (
            r['scene'], r['element'], r['target'], r['set'], r['engine'], r['codes'], r['set_engine'], r['engine_after'], r['codes_after']))
    for r in ov:
        L.append('| %s（§D 遮罩） | %s %s | `%s` | `%s` → `%s`（差 %d） | **`%s`** → `%s`（差 %d） |' % (
            r['grade'], r['when'], r['role'], r['target'], r['set'], r['engine'], r['codes'], r['set_engine'], r['engine_after'], r['codes_after']))
    for r in kept:
        L.append('| %s | %s | `%s` | `%s` → `%s`（差 %d） | 不改：%s |' % (
            r['scene'], r['element'], r['target'], r['set'], r['engine'], r['codes'],
            '在 ±3 以内，重解会削掉它的 bloom（×T0 %s）' % r['kept'].split('xT0 ')[-1].rstrip(')')))
    L += ['', '§A 灰卡 / 白卡读数（%d 项）在引擎里最大差 %d 码；§D 遮罩填值（%d 项）最大差 %d 码，全部照 `calib_final.md` 原样用。' % (
        len(CE['lights']), max(r['codes'] for r in CE['lights']), len(CE['overlay']), max(r['codes'] for r in CE['overlay']))]
    if warnings:
        L += ['', 'json 里的冲突（生成器按 v2 解决）：', '']
        L += ['- ' + w for w in warnings]
    L += ['', '<!-- /lanbai:generated:table -->']
    return '\n'.join(L)


# --------------------------------------------------------------------------------------------
def default_input(name):
    local = os.path.join(HERE, 'inputs', name)
    art = os.path.join(ART, name)
    return art if os.path.exists(art) else local


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument('--grades', default=os.path.join(HERE, 'inputs', 'grades_engine.json'),
                    help='ENGINE grade set written by Tools~/engine/solve_engine_grades.py')
    ap.add_argument('--lookdef', default=default_input('grades_final.json'), help='look definition (bible B1)')
    ap.add_argument('--calib', default=default_input('calib_final.json'))
    ap.add_argument('--calib-engine', default=os.path.join(HERE, 'inputs', 'calib_engine.json'),
                    help='fills re-solved for the engine (Tools~/engine/engine_calib.py)')
    a = ap.parse_args(argv)
    G = json.load(open(a.grades, encoding='utf-8'))
    C = json.load(open(a.calib, encoding='utf-8'))
    CE = json.load(open(a.calib_engine, encoding='utf-8'))
    gsha, lsha, csha = sha256(a.grades), sha256(a.lookdef), sha256(a.calib)
    # the engine solve must belong to exactly these look-definition files
    if G.get('_engine', {}).get('source_grades_sha256') != lsha:
        raise ValueError('grades_engine.json was solved from another grades_final.json (sha256 %s, now %s): '
                         're-run Tools~/engine/solve_engine_grades.py' % (G.get('_engine', {}).get('source_grades_sha256'), lsha))
    if G['_engine'].get('source_calib_sha256') != csha:
        raise ValueError('grades_engine.json was solved against another calib_final.json: re-run solve_engine_grades.py')
    if CE.get('source_grades_engine_sha256') != gsha or CE.get('source_calib_sha256') != csha:
        raise ValueError('calib_engine.json is stale: re-run Tools~/engine/engine_calib.py')
    LG = json.load(open(a.lookdef, encoding='utf-8'))
    for sid, P in LG['profiles'].items():          # the record in grades_engine must BE the look definition
        ld = G['profiles'][sid]['ppv2_lookdef']
        if any(ld[k] != P['ppv2'][k] for k in COLOUR_KEYS):
            raise ValueError('%s: ppv2_lookdef in grades_engine.json differs from grades_final.json' % sid)
        for k in ('postExposure', 'bloom'):
            if G['profiles'][sid]['ppv2'][k] != P['ppv2'][k]:
                raise ValueError('%s: %s differs between the engine set and the look definition (must be identical)' % (sid, k))
    if G['helpers'] != LG['helpers']:
        raise ValueError('helpers differ between grades_engine.json and grades_final.json (must be identical)')
    ROUTE_C.update(route_c_luts())
    COLOUR_PATCHES.update(CE['colour_patches'])
    if not ROUTE_C:
        old = os.path.join(KIT, 'Editor', 'LanbaiGradeData.cs')
        if os.path.exists(old):    # no art folder here: keep the names the last generation found
            for m in re.finditer(r'id = "(S\w+)",.*?routeCLut = "([^"]+)"', open(old, encoding='utf-8-sig').read(), re.S):
                ROUTE_C[m.group(1)] = m.group(2)
    entries, warnings = build_entries(G, C)

    # snapshot the inputs next to the generator
    os.makedirs(os.path.join(HERE, 'inputs'), exist_ok=True)
    for src, name in ((a.lookdef, 'grades_final.json'), (a.calib, 'calib_final.json')):
        dst = os.path.join(HERE, 'inputs', name)
        if os.path.abspath(src) != os.path.abspath(dst):
            shutil.copyfile(src, dst)

    data_cs = os.path.join(KIT, 'Editor', 'LanbaiGradeData.cs')
    with open(data_cs, 'w', encoding='utf-8', newline='\n') as f:
        f.write(gen_data_cs(entries, warnings, gsha, lsha, csha))

    expo_cs = os.path.join(KIT, 'Runtime', 'LanbaiExposure.cs')
    t = open(expo_cs, encoding='utf-8-sig').read()
    t = replace_region(t, gen_exposure_region(entries, G, gsha), GEN_BEGIN, GEN_END)
    with open(expo_cs, 'w', encoding='utf-8-sig', newline='\n') as f:
        f.write(t)

    readme = os.path.join(KIT, 'README_Grading.md')
    if os.path.exists(readme):
        r = open(readme, encoding='utf-8').read()
        r = replace_region(r, gen_readme_table(entries, warnings, G, CE), '<!-- lanbai:generated:table', '<!-- /lanbai:generated:table -->')
        with open(readme, 'w', encoding='utf-8', newline='\n') as f:
            f.write(r)

    print('entries: %d (%d scenes)' % (len(entries), sum(e['kind'] == 'Scene' for e in entries)))
    for e in entries:
        extra = ''
        if e['kind'] == 'Scene':
            worst = max(max(abs(int(x[i:i + 2], 16) - int(y[i:i + 2], 16)) for i in (1, 3, 5))
                        for x, y in zip(e['expectedTestCard'], e['predictedTestCard']))
            extra = '  §C predicted max %d codes  black %s (target %s)  Route C %s' % (worst, e['predictedBlack'], e['expectedBlack'], e['routeCLut'])
        print('  %-12s %-6s prio %6g  w0 %g%s' % (e['id'], e['kind'], e['priority'], e['initialWeight'], extra))
    for w in warnings:
        print('WARNING (resolved):', w)
    print('wrote', data_cs)
    print('updated', expo_cs, '(generated region)')
    if os.path.exists(readme):
        print('updated', readme, '(generated tables)')


if __name__ == '__main__':
    main()
