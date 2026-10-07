# -*- coding: utf-8 -*-
"""Lanbai / 蓝白 — poem and scrim colours: bible SCREEN TARGET -> what Unity must be FILLED with (verify round 2, B.1).

Bible law 1: every hex in §7.5 / §7.2 is a screen target (what a screenshot reads), not a value to type in.
A poem is unlit and is graded by the PPv2 grade live while it is on screen (Neutral tonemap, postExposure, white
balance, contrast, lift / gamma / gain, saturation), and TMP 3.0.6 applies no colour-space conversion to vertex
colours (TMP_SDF.shader: faceColor.rgb *= input.color.rgb). So:
  * TMP Vertex Color = WHITE, carrying only the alpha (0.90; scene 6d 1.00; scene 11 0.80; mirror 0.45; x the fade);
  * the colour goes on the poem's own material (preset) as the HDR _FaceColor = the scene-linear FILL solved here;
  * scrims: SpriteRenderer.color = (1, 1, 1, alpha); the colour is the Sprites/Default material's _Color = the fill.
The fill is solved with the bible's own look simulator (calib_final.solve; vendored in Tools~/colour_sim so the kit
works outside the art tree, verify r3 m2) under the grade that is LIVE while the poem is read. Two poems are read
during a PPv2 volume blend (bible §1.4: param = lerp(lower, higher, weight)):
  * 李白 I (71.80-86.80): S3 at weight ~0.3 over S2 (§6·3: 0 -> 0.3 over 39.10-79.10, smoothstep);
  * 里尔克 (137.30-150.30): S4 rising over S3 (§6·4 "3 -> 4": 0 -> 1 over 133.80-163.80, smoothstep);
they are solved at the blend weight of mid-hold, and the reading over the whole hold is reported.
    fill_hdr "#RRGGBB @ +n"  = Unity HDR colour picker: hex + Intensity n (linear x 2^n), like calib_final.md §B.
    fill_linear [r, g, b]    = the value the shader receives (Material.SetColor(name, linear.gamma) in a Linear project).
Engine cross-check: if the Grading kit (deliver2/Grading) is next to this kit, every fill is also run through its
engine-faithful PPv2 model with its engine-solved grades (Grading verify B1), and the code difference is reported.
"""
import os, sys, math, json, hashlib
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
ART = os.path.normpath(os.path.join(KIT, '..', '..', 'art'))
BIBLE_WORK = os.path.join(ART, 'bible_work')
GRADING = os.path.normpath(os.path.join(KIT, '..', 'Grading'))
sys.path.insert(0, os.path.join(HERE, 'colour_sim'))
import lanbai_sim as SIM          # noqa: E402

# poem -> the PPv2 grade live while it is read (bible §6, §2.2, appendix B). A str = one scene profile at weight 1;
# a dict = a volume blend: 'upper' rises over 'lower' with weight w_end * smoothstep((t - t0) / (t1 - t0)).
POEM_GRADE = {
    'P03_LiBai_Dream': dict(lower='S2', upper='S3', t0=39.10, t1=79.10, w_end=0.30),   # §6·3 调色
    'P04a_Rilke': dict(lower='S3', upper='S4', t0=133.80, t1=163.80, w_end=1.0),      # §6·4 "3 -> 4"
    'P04b_Urlicht': 'S4',             # 166.15: S4 reached 1 at 163.80
    'P06_Dream_Dawn': 'S6',           # 6d sea mirror: "S6 保持到入水"
    'P07_HeBo': 'S7b',                # 7b
    'P08a_Dream_Dusk': 'S7b',         # 7c: "S7b 恒定" (S7b -> S8 only at 922.36)
    'P08b_Zhuangzi_Xiaoyao': 'S8',    # 8-ii is S8 until F12 987.06 (S8 -> S8b while the lines leave)
    'P09_Tianwen': 'S9a',             # S8b -> S9a follows the darkening 1001.21 -> 1009.21: S9a at 1009.21
    'P11_Zhuangzi_Butterfly': 'S11',  # false awakening (= S2)
    'P12a_LiBai_Wake': 'S12',
    'P12b_Keats': 'S12',
}
SCRIM_GRADE = {'dark': 'S8', 'light': 'S6'}   # dark: only Zhuangzi (8-ii); light: only the dawn line (6d)
# The bible's scrim alpha (§7.2: #0E1A2F α0.30, #E8F1F5 α0.25) describes the LOOK of a veil on screen. Unity blends
# the sprite in scene-linear light BEFORE the grade's tonemap, so the same alpha reads differently there: the HDR
# light-scrim fill (x3.7 linear) at 0.25 lifts a mid-tone sea twice as much as a 25 % veil, and the dark scrim at 0.30
# darkens a bright sky less than a 30 % veil. Law 1 (targets are law, parameters chase them): the SpriteRenderer
# alpha is solved so that, over the representative background under the text, the Unity veil has the luma of the
# bible's veil. Representative backgrounds = the mean under the text in the proof sketches (Docs~/proof_report.json).
SCRIM_REP_BG = {'light': '#817B77',   # 6d: the calm sea mirror at -12° (gold-lit cloud deck reflected, water #1C3D63)
                'dark': '#C8B0A1'}    # 8-ii: the other sky / horizon band behind the Zhuangzi column

_STATE = {}


def _md5(path):
    return hashlib.md5(open(path, 'rb').read()).hexdigest()


def sim_info():
    """Which grades the solver uses; refreshes the vendored PROF from art/grades_final.json when the art tree is here."""
    if 'info' in _STATE:
        return _STATE['info']
    info = dict(vendored=SIM.GRADES_PATH, vendored_md5=_md5(SIM.GRADES_PATH), art_grades=None, used='vendored')
    art_g = os.path.join(ART, 'grades_final.json')
    if os.path.isfile(art_g):
        info['art_grades'] = art_g
        info['art_md5'] = _md5(art_g)
        if info['art_md5'] != info['vendored_md5']:
            print('lanbai_color: WARNING art/grades_final.json differs from Tools~/colour_sim/grades_final.json; '
                  'using the art copy (the bible is the source of truth) — copy it into colour_sim/ and rebuild')
            SIM.PROF.clear()
            SIM.PROF.update({k: v['ppv2'] for k, v in json.load(open(art_g, encoding='utf-8'))['profiles'].items()})
            info['used'] = 'art'
        else:
            info['used'] = 'vendored (identical to art/grades_final.json)'
    else:
        print('lanbai_color: art/ not found next to the kit; solving with the vendored simulator '
              '(Tools~/colour_sim, grades md5 %s)' % info['vendored_md5'])
    _STATE['info'] = info
    return info


def smoothstep(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def grade_at(pid, t=None):
    """grade spec for a poem at timeline second t (None = mid-hold, the solving point)."""
    g = POEM_GRADE[pid]
    if isinstance(g, str):
        return g
    if t is None:
        raise ValueError('blend grade needs t')
    w = g['w_end'] * smoothstep((t - g['t0']) / (g['t1'] - g['t0']))
    return (g['lower'], g['upper'], round(w, 3))


def params(spec):
    sim_info()
    return SIM.params_of(spec)


def hex_rgb(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])


def s2l(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def luma(hexc):
    r, g, b = hex_rgb(hexc) * 255
    return float(0.2126 * r + 0.7152 * g + 0.0722 * b)


def disp(lin, spec):
    """display hex of a scene-linear colour through the grade (no bloom)."""
    return SIM.disp_hex(np.asarray(lin, float), params(spec))


def bloom_T0(spec):
    b = params(spec)['bloom']
    return SIM.g2l(b['threshold']) * (1 - b['softKnee'])


def bloom_share(lin, spec):
    """PPv2 prefilter (QuadraticThreshold on the max channel, before postExposure): the fraction of this pixel that
    enters the bloom pyramid (before intensity and blur). 0 = does not bloom at all."""
    b = params(spec)['bloom']
    th = SIM.g2l(b['threshold'])
    knee = th * b['softKnee']
    br = float(np.max(lin))
    rq = min(max(br - (th - knee), 0.0), 2 * knee)
    rq = 0.25 / knee * rq * rq if knee > 0 else 0.0
    return max(rq, br - th) / max(br, 1e-6)


_cache = {}


def solve(target_hex, spec):
    k = (target_hex.upper(), SIM.spec_name(spec))
    if k not in _cache:
        x, err = SIM.solve(target_hex.upper(), params(spec))
        _cache[k] = (np.asarray(x, float), float(err))
    return _cache[k]


def poem_solve_spec(p):
    """the grade a poem's fill is solved under: its profile, or the blend at mid-hold."""
    g = POEM_GRADE[p['id']]
    if isinstance(g, str):
        return g
    hold = p['hold_s'] if p.get('hold_s') else 6.0
    return grade_at(p['id'], p['t_appear'] + hold / 2.0)


def fill_record(target_hex, spec, alpha):
    """Everything the Director needs for one colour, plus the checks."""
    x, err = solve(target_hex, spec)
    shown = disp(x, spec)
    naive = disp(hex_rgb(target_hex), spec)                 # what the round-1 README produced (hex bytes as vertex colour)
    T0 = bloom_T0(spec)
    return dict(
        grade=SIM.spec_name(spec),
        profile=spec if isinstance(spec, str) else spec[1],
        target=target_hex.upper(),
        fill_hdr=SIM.set_str(x),
        fill_linear=[round(float(v), 4) for v in x],
        solve_error_codes=round(err, 3),
        screen_of_fill=shown, screen_luma=round(luma(shown), 1),
        x_T0=round(float(np.max(x)) / T0, 3),
        bloom_share_opaque=round(bloom_share(x, spec), 5),
        bloom_share_at_alpha=round(bloom_share(x * alpha, spec), 5),
        alpha=alpha,
        naive_vertex_colour_screen=naive, naive_vertex_colour_luma=round(luma(naive), 1),
    )


def poem_fill_record(p):
    spec = poem_solve_spec(p)
    fr = fill_record(p['color_target'], spec, p['opacity'])
    g = POEM_GRADE[p['id']]
    if not isinstance(g, str):
        x = np.asarray(fr['fill_linear'])
        rows = []
        t_end = p['t_appear'] + (p['hold_s'] or 6.0)
        for label, t in (('focus start', p['t_appear']), ('focused', p['t_appear'] + 2.5),
                         ('mid-hold (solved)', p['t_appear'] + (p['hold_s'] or 6.0) / 2), ('exit start', t_end)):
            sp = grade_at(p['id'], t)
            sh = disp(x, sp)
            rows.append(dict(moment=label, t=round(t, 2), grade=SIM.spec_name(sp), screen=sh, luma=round(luma(sh), 1),
                             diff_codes=int(round(np.abs(hex_rgb(sh) - hex_rgb(p['color_target'])).max() * 255))))
        fr['grade_note'] = ('read during a PPv2 volume blend: %s rises over %s (w_end %.2f, smoothstep %.2f -> %.2f s); '
                            'fill solved at mid-hold' % (g['upper'], g['lower'], g['w_end'], g['t0'], g['t1']))
        fr['screen_over_hold'] = rows
        fr['single_profile_fill_would_be'] = dict(
            profile=g['upper'], fill_hdr=SIM.set_str(solve(p['color_target'], g['upper'])[0]),
            screen_live=disp(solve(p['color_target'], g['upper'])[0], spec))
    return fr


def scrim_unity_alpha(kind, bg_hex=None):
    """SpriteRenderer alpha that gives, in Unity's scene-linear blend + grade, the screen luma of the bible's veil
    (display-linear alpha-over of the scrim target at the bible alpha) over the representative background."""
    from scipy.optimize import brentq
    col, a_b = ('#0E1A2F', 0.30) if kind == 'dark' else ('#E8F1F5', 0.25)
    spec = SCRIM_GRADE[kind]
    bg_hex = bg_hex or SCRIM_REP_BG[kind]
    bg_s, _ = solve(bg_hex, spec)
    sc_s, _ = solve(col, spec)
    W = np.array([0.2126, 0.7152, 0.0722])
    tgt = s2l(hex_rgb(bg_hex)) * (1 - a_b) + s2l(hex_rgb(col)) * a_b
    tl = float(tgt @ W)
    unity = lambda a: disp(bg_s * (1 - a) + sc_s * a, spec)
    f = lambda a: float(s2l(hex_rgb(unity(a))) @ W) - tl
    a_u = float(brentq(f, 1e-4, 0.999, xtol=1e-5))
    return dict(kind=kind, grade=spec, scrim=col, alpha_bible=a_b, alpha_unity=round(a_u, 3), background=bg_hex,
                veil_target=_l2hex(tgt), unity_at_bible_alpha=unity(a_b), unity_at_unity_alpha=unity(round(a_u, 3)))


def composite_check(spec, bg_display_hex, text_target, text_alpha, scrim=None, text_fill=None):
    """Unity model vs proof model for one representative background.
    Unity: scene-linear alpha-over (bg -> scrim fill at a_s -> text fill at a_t), then the grade.
    Proof: display-linear alpha-over of the targets (what the proof sheets draw).
    scrim = (target_hex, alpha) or (target_hex, display alpha, Unity sprite alpha) or None."""
    bg_s, _ = solve(bg_display_hex, spec)
    t_s = np.asarray(text_fill, float) if text_fill is not None else solve(text_target, spec)[0]
    x = bg_s.copy()
    y = s2l(hex_rgb(bg_display_hex))
    if scrim:
        sc_s, _ = solve(scrim[0], spec)
        a_u = scrim[2] if len(scrim) > 2 else scrim[1]
        x = x * (1 - a_u) + sc_s * a_u
        y = y * (1 - scrim[1]) + s2l(hex_rgb(scrim[0])) * scrim[1]
    under_unity, under_proof = disp(x, spec), _l2hex(y)
    x = x * (1 - text_alpha) + t_s * text_alpha
    y = y * (1 - text_alpha) + s2l(hex_rgb(text_target)) * text_alpha
    u, p = disp(x, spec), _l2hex(y)
    du = np.abs(hex_rgb(u) - hex_rgb(p)).max() * 255
    dund = np.abs(hex_rgb(under_unity) - hex_rgb(under_proof)).max() * 255
    dt = np.abs(hex_rgb(u) - hex_rgb(text_target)).max() * 255
    return dict(grade=SIM.spec_name(spec), background=bg_display_hex, scrim=scrim and list(scrim), text_alpha=text_alpha,
                under_text_unity=under_unity, under_text_proof=under_proof, under_text_diff_codes=int(round(dund)),
                text_unity=u, text_proof=p, text_diff_codes=int(round(du)), text_vs_target_codes=int(round(dt)),
                text_luma_unity=round(luma(u), 1), target_luma=round(luma(text_target), 1),
                bloom_share=round(bloom_share(x, spec), 5))


def _l2hex(lin):
    c = np.clip(lin, 0, 1)
    s = np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)
    return '#%02X%02X%02X' % tuple(int(round(v * 255)) for v in s)


# ------------------------------------------------------------------------------ cross-checks (reports only)
def bible_crosscheck(targets):
    """Same fills from art/bible_work/calib_final.solve (pure profiles only)? -> (status, max code diff, rows)."""
    if not os.path.isdir(BIBLE_WORK):
        return 'skipped (art/bible_work not found)', None, []
    cwd = os.getcwd()
    sys.path.insert(0, BIBLE_WORK)
    os.chdir(BIBLE_WORK)
    try:
        import calib_final as C
    finally:
        os.chdir(cwd)
    rows, worst = [], 0.0
    for tgt, prof in targets:
        xb, _ = C.solve(tgt.upper(), prof)
        xk, _ = solve(tgt, prof)
        d = float(np.max(np.abs(np.log2(np.asarray(xb) / xk))))
        sb, sk = C.disp_hex(xb, prof), disp(xk, prof)
        dc = int(round(np.abs(hex_rgb(sb) - hex_rgb(sk)).max() * 255))
        worst = max(worst, dc)
        rows.append(dict(target=tgt, profile=prof, bible_fill=C.set_str(np.asarray(xb)), kit_fill=SIM.set_str(xk),
                         max_log2_ratio=round(d, 5), screen_diff_codes=dc))
    return ('identical' if worst == 0 else 'DIFFERS'), worst, rows


def engine_crosscheck(items):
    """items: [(name, fill_linear, grade_spec, target_hex)]. Runs the Grading kit's engine model (ppv2_engine.py with
    grades_engine.json, its fix for Grading verify B1) when it is present; reports the code difference per fill."""
    eng_dir = os.path.join(GRADING, 'Tools~', 'engine')
    gpath = os.path.join(GRADING, 'Tools~', 'inputs', 'grades_engine.json')
    if not (os.path.isfile(os.path.join(eng_dir, 'ppv2_engine.py')) and os.path.isfile(gpath)):
        return 'skipped (Grading kit engine model not found)', None, []
    sys.path.insert(0, eng_dir)
    import ppv2_engine as E
    G = json.load(open(gpath, encoding='utf-8'))

    def eprof(sid):
        P = G['profiles'][sid]['ppv2']
        p = {k: P[k] for k in ('postExposure', 'temperature', 'tint', 'saturation', 'contrast', 'lift', 'gamma', 'gain')}
        p.update(colorFilter=G['common']['colorFilter'], hueShift=G['common']['hueShift'])
        return p

    rows, worst = [], 0
    for name, fill, spec, tgt in items:
        if isinstance(spec, str):
            p = eprof(spec)
        else:
            a, b, w = spec
            pa, pb = eprof(a), eprof(b)
            p = {k: (SIM._lerp(pa[k], pb[k], w) if k not in ('colorFilter',) else pa[k]) for k in pa}
        got = np.round(E.codes(np.asarray(fill, float)[None, :], p)[0])
        d = int(np.abs(got - E.hex8(tgt)).max())
        worst = max(worst, d)
        rows.append(dict(name=name, grade=SIM.spec_name(spec), target=tgt, engine_screen=E.to_hex(got), diff_codes=d))
    return 'ran (grades_engine.json md5 %s)' % _md5(gpath)[:12], worst, rows
