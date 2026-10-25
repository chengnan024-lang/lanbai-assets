# -*- coding: utf-8 -*-
"""Lanbai / 蓝白 — Fonts kit v5 (D-45): the poems as Fins-style subtitles.

  python3 lanbai_subtitles.py      -> checks + Docs~/subtitle_report.md (needs the Subset fonts: run build_fonts.py once)
  build_fonts.py imports it: subtitle strings go into the charsets, subtitle_rig / subtitles into strings_all.json,
  the self-checks into the build (any FAIL stops the build).

Source of truth: lanbai_strings.SUBS (pages, B.8) and the rig parameters below (Art/字幕方案_D-45.md B–F, I.2), with
小楠's four decisions (裁决 D-45 #15): height and size "as Fins" (until 阿白's R1 measurement: last line at -21°, em
1.8°, 1.8° is the floor; both are DATA here), the desktop letterbox in three or four set pieces (data, desktop only),
Zhuangzi keeps the column (zh / zht) and adds subtitles for ja / en / de.

Self-checks (I.1; every one must pass):
  * same words, new breaks: every page's text, without spaces and punctuation, equals the v4 text of that key
  * every line <= 25° at the em size (the B-option whitelist allows 26°); <= 2 lines per page
  * every page shown >= 3.0 s; page changes >= 3 s apart; sync points identical in every key that has pages
  * every key of every poem has pages, except the ones declared empty (Tianwen zh / zht read the sky; Zhuangzi zh /
    zht read the column)
  * nothing shows inside a no-text zone (F13-F16 1018.21-1149.31 above all; dawn F0-F1; 8 s after leaving the sea;
    the dusk transformation; the white) and Tianwen's pages are gone by 1018.11
  * the screen target of every tier is <= luma 224 (the fill itself is solved and checked by build_fonts.py)
  * (build_fonts.py) the P09 layout's SHA-256 equals v4.1's; the charsets cover every subtitle and board string
Reading speed (D.4: zh 9 chars/s, ja 4 chars/s, en 17 characters/s) is reported; Tianwen and the sung Urlicht are
the bible's exceptions (listed, not failed).
"""
import json
import math
import os
import re
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import lanbai_strings as L  # noqa: E402

KEYS = ('zh', 'zht', 'ja', 'en', 'de')
P09_SHA_V41 = '4fc91ceae3d9c51b90b5a11a1ee81bddc74ad7d6fb652c986448fc70602a9a22'   # sha256 of v4.1's P09 layout (sorted keys, compact)

# ---------------------------------------------------------------------------------------------- the rig (I.2)
RIG = {
    '_note': 'D-45: every number the driver uses, as data. em_deg / base_bottom_el_deg follow Fins once 阿白 measures R1 '
             '(D-45 #15.1, #15.2): until then -21° and 1.8° (1.8° is the floor); a result between -14° and -17° moves '
             'to the nearer side. option_b_* = the plan\'s B options, kept for a quick switch.',
    'em_deg': 1.8, 'em_floor_deg': 1.8, 'em_cjk_deg_optB': 2.0,
    'line_pitch_em': {'cjk': 1.5, 'latin': 1.35}, 'tracking_em': {'cjk': 0.10, 'latin': 0.0},
    'max_lines': 2, 'max_line_deg': 25.0, 'max_line_deg_optB': 26.0,
    'base_bottom_el_deg': -21.0, 'base_bottom_el_optB': -13.0, 'forbidden_el_band_deg': [-17.0, -14.0],
    'hang_em': 0.5, 'hang_chars': '？！—?!',
    'depth': {'main_forward_m': 1.0, 'clamp_m': [0.45, 1.0], 'near_factor': 0.92, 'max_rate_mps': 0.5,
              'fallback': {'main_within_30deg': 1.0, 'main_other': 0.6, 'other_seats': 0.45, 'unseated': 0.8}},
    'yaw': {'deadzone_min_deg': 12.0, 'deadzone_margin_deg': 3.0, 'stop_err_deg': 1.5, 'stop_vel_dps': 3.0,
            'omega': 4.5, 'max_speed_dps': 60.0, 'limit_deg': 120.0, 'limit_back_deg': 110.0, 'first_page_hold_s': 0.6},
    'pitch': {'up_enter_rel': 27.0, 'up_exit_rel': 23.0, 'hold_s': 0.4, 'up_cap_deg': 35.0,
              'low_band_rel': -12.0, 'low_above_deg': 12.0, 'low_floor_deg': -36.0, 'low_move_deg': 3.0, 'low_stop_deg': 1.0},
    'fast_turn': {'dps': 120.0, 'err_deg': 40.0, 'out_s': 0.15, 'settle_dps': 30.0, 'settle_s': 0.25, 'in_s': 0.30},
    'head_pos_tau_s': 0.5,
    'fade': {'in': 0.30, 'page_out': 0.25, 'page_gap': 0.10, 'page_in': 0.30, 'out_last': 0.50,
             'lyric_line_in': 0.20, 'lyric_lead': 0.05},
    'colour': dict(L.SUB_TIER_HEX), 'luma_max': 224.0,
    'underlay': {'colour': 'linear_black', 'alpha': 0.5, 'alpha_range': [0.4, 0.7], 'dilate': 0.15, 'softness': 0.30},
    'halo': {'colour': '#0E1A2F', 'texture': 'Textures/Lanbai_Scrim_Line.png', 'pad_w_em': 1.2, 'h_em': 1.8},
    'accept': {'ring_em': 0.15, 'min_ratio': 3.0},
    'face_dilate': {'vr': 0.10, 'desktop': 0.05}, 'sharpness': -0.1,
    'desktop': {'distance_m': 1.0, 'em_frac_h': 0.042, 'baseline_frac_h': 0.08, 'fov_fallback_deg': 60.0},
    # D-45 #15.3: the desktop letterbox "as Fins": now and then, desktop only, three or four set pieces (VR never)
    'letterbox': {'desktop_only': True, 'aspect': 2.39, 'corner_deg': 45.0, 'slide_s': 1.5, 'distance_m': 0.9,
                  'queue': 'Overlay+5',
                  'segments': [{'id': '3c_rilke', 't0': 134.0, 't1': 151.5}, {'id': '6d_dawn_line', 't0': 342.0, 't1': 359.0},
                               {'id': '9a_tianwen', 't0': 1005.0, 't1': 1018.21}],
                  'note': 'times are first values (the plan names the scenes, not the seconds): each covers the poem with '
                          '~3 s of lead; Tianwen ends at F13. Off when subtitles are off.'},
    'modes': ['follow', 'stay', 'off'],
    'render': {'subtitle_queue': 'Overlay+10', 'halo_queue': 'Overlay+9', 'ztest': 'Always', 'zwrite': 'Off'},
}

# no-text zones (D.4; bible §7.5): (t0, t1, what). Act starts are not listed: the appear times are unchanged (§7.5
# checked them); the sung / per-page changes stay inside each poem's v4 span.
NO_TEXT = [(251.64, 281.86, 'dawn F0 -> F1'), (922.36, 930.36, '8 s after leaving the sea'),
           (956.36, 966.0, 'the dusk transformation'), (1018.21, 1149.31, 'F13 -> F16'), (1149.31, 1186.46, 'the white')]
SPEED = {'zh': 9.0, 'zht': 9.0, 'ja': 4.0, 'en': 17.0, 'de': 17.0}     # chars / s (en: characters)
SPEED_EXCEPT = {('P09_Tianwen', 'ja'), ('P09_Tianwen', 'en'), ('P09_Tianwen', 'de'), ('P04b_Urlicht', 'ja')}

_PUNCT = re.compile(r'[\s　，、。,.:;—\-–!！?？“”"‘’\']')


def norm(s):
    return _PUNCT.sub('', s)


# ------------------------------------------------------------------------------------------------- zht pages
def zht_map():
    """character map zh -> zht from every (zh text, ZHT text) pair of the v4 data (same length, position by position)"""
    m = {}
    for p in L.POEMS:
        for s in p['segments']:
            if 'zht' not in s:
                continue
            src = s['main'] if p['original']['lang'] == 'zh' else s.get('zh', [])
            for a, b in zip(src, s['zht']):
                for ca, cb in zip(a, b):
                    if ca != cb:
                        if m.get(ca, cb) != cb:
                            raise ValueError('zht map conflict: %s -> %s / %s' % (ca, m[ca], cb))
                        m[ca] = cb
    return m


def to_zht(text, m):
    return ''.join(m.get(c, c) for c in text)


def v4_text(p, key):
    """the v4 text a player of `key` read (for 'same words, new breaks')"""
    k = L.shown_lang(p, key)
    if p.get('picture') and key not in ('zh', 'zht'):
        k = L.translation_for(p, key) or k
    return ''.join(ln for s in p['segments'] for ln in s.get(k, []))


def font_of(sub, key):
    if key in sub.get('italic', ()):
        return 'EBGaramond-Italic'
    return L.SUB_FONT_V5[key]


def pages_for(sub, key, zmap):
    k = sub['keys']
    if key in k:
        return list(k[key])
    if key == 'zht' and 'zh' in k:
        return [(t, [to_zht(x, zmap) for x in lines]) for t, lines in k['zh']]
    if key == 'de' and 'en' in k:
        return list(k['en'])
    return []


def build():
    """-> (subtitles list for strings_all.json, strings [(font, text, ident)] for the charsets)"""
    zmap = zht_map()
    fade = RIG['fade']
    out, strings = [], []
    for sub in L.SUBS:
        p = next(q for q in L.POEMS if q['id'] == sub['poem'])
        out_last = sub.get('out_last', fade['out_last'])
        rec = dict(poem=sub['poem'], scene=p['scene'], t_in=sub['t_in'], t_end=sub['t_end'], out_last=out_last,
                   tier=sub['tier'], target=L.SUB_TIER_HEX[sub['tier']], halo_alpha=sub['halo'],
                   base_bottom_el=sub.get('base_bottom_el', RIG['base_bottom_el_deg']), sync=list(sub['sync']),
                   empty_keys={}, keys={})
        if sub.get('line_t'):
            rec['line_t'] = list(sub['line_t'])
            rec['line_in'] = sub['line_in']
        for key in KEYS:
            if key in sub.get('sky_keys', ()):
                rec['empty_keys'][key] = 'reads the Han characters in the sky (D-30 #4, D-45 G.1)'
                rec['keys'][key] = []
                continue
            if key in sub.get('column_keys', ()):
                rec['empty_keys'][key] = 'reads the Zhuangzi column (D-45 #15.4)'
                rec['keys'][key] = []
                continue
            pg = pages_for(sub, key, zmap)
            fk = font_of(sub, key)
            pages = []
            for i, (t, lines) in enumerate(pg):
                t_next = pg[i + 1][0] if i + 1 < len(pg) else None
                pages.append(dict(t=t, font=fk, lines=list(lines),
                                  t_out=round((t_next - fade['page_out'] - fade['page_gap']) if t_next else sub['t_end'] - out_last, 3),
                                  t_gone=round((t_next - fade['page_gap']) if t_next else sub['t_end'], 3)))
                for ln in lines:
                    strings.append((fk, ln, '%s/sub/%s' % (sub['poem'], key)))
            rec['keys'][key] = pages
        out.append(rec)
    for uid, by in L.UI_V5:
        for key, text in by.items():
            strings.append((L.UI_LANG[key], text, uid + '/' + key))
    for uid, key, text in L.UI_LANG_NAMES:
        strings.append(('EBGaramond-Italic' if uid.endswith('de_note') else L.UI_LANG[key], text, uid))
    return out, strings


def ui_rows():
    rows = [dict(id=uid, lang=key, font=L.UI_LANG[key], text=text) for uid, by in L.UI_V5 for key, text in by.items()]
    rows += [dict(id=uid, lang=key, font=('EBGaramond-Italic' if uid.endswith('de_note') else L.UI_LANG[key]), text=text,
                  note='每个语言名用它自己的文字，所有玩家看到的都一样' if not uid.endswith('de_note') else '只给德语客户端（English 旁边的小字）')
             for uid, key, text in L.UI_LANG_NAMES]
    return rows


# ---------------------------------------------------------------------------------------------- widths
class Metrics:
    def __init__(self):
        from fontTools.ttLib import TTFont
        self.f = {}
        self.TTFont = TTFont

    def width_em(self, fk, s):
        if fk not in self.f:
            ft = self.TTFont(os.path.join(KIT, 'Subset', L.FONTS[fk]['subset']))
            kern = {}
            if 'kern' in ft:
                for st in ft['kern'].kernTables:
                    kern.update(st.kernTable)
            self.f[fk] = (ft.getBestCmap(), ft['hmtx'], ft['head'].unitsPerEm, kern)
        cmap, hmtx, upm, kern = self.f[fk]
        track = RIG['tracking_em']['cjk' if L.FONTS[fk]['cjk'] else 'latin']
        w, prev, n = 0.0, None, 0
        for ch in s:
            g = cmap.get(ord(ch))
            if g is None:
                raise KeyError('%s has no glyph for %r (%s)' % (fk, ch, s))
            w += hmtx[g][0]
            if prev is not None:
                w += kern.get((prev, g), 0)
            prev = g
            n += 1
        return w / upm + track * max(0, n - 1)


def deg_of_em(w_em, em_deg):
    """width in degrees of a line w_em ems wide, the em being em_deg at any distance (the rig scales with depth)"""
    em_m = 2 * math.tan(math.radians(em_deg / 2))
    return math.degrees(2 * math.atan(w_em * em_m / 2))


# ---------------------------------------------------------------------------------------------- checks
def check(subs, metrics=None):
    """-> (ok, rows of (status, what, detail)), per I.1"""
    rows = []
    ok = True

    def add(st, what, detail=''):
        nonlocal ok
        if st == 'FAIL':
            ok = False
        rows.append((st, what, detail))

    for rec in subs:
        p = next(q for q in L.POEMS if q['id'] == rec['poem'])
        pid = rec['poem']
        # every key has pages, unless declared empty
        for key in KEYS:
            pages = rec['keys'].get(key, [])
            if not pages and key not in rec['empty_keys']:
                add('FAIL', '%s/%s has no pages' % (pid, key))
        for key, pages in rec['keys'].items():
            if not pages:
                continue
            # same words, new breaks
            got = norm(''.join(ln for pg in pages for ln in pg['lines']))
            want = norm(v4_text(p, key))
            if key == 'zht':
                want = norm(v4_text(p, 'zht'))
            if got != want:
                add('FAIL', '%s/%s: the words changed' % (pid, key), 'v4 %r / v5 %r' % (want, got))
            for i, pg in enumerate(pages):
                if not (1 <= len(pg['lines']) <= RIG['max_lines']):
                    add('FAIL', '%s/%s page %d has %d lines' % (pid, key, i + 1, len(pg['lines'])))
                t_next = pages[i + 1]['t'] if i + 1 < len(pages) else rec['t_end']
                if t_next - pg['t'] < 3.0 - 1e-6:
                    add('FAIL', '%s/%s page %d shown %.2f s (< 3.0 s)' % (pid, key, i + 1, t_next - pg['t']))
                if i and pg['t'] - pages[i - 1]['t'] < 3.0 - 1e-6:
                    add('FAIL', '%s/%s page changes %.2f s apart (< 3 s)' % (pid, key, pg['t'] - pages[i - 1]['t']))
            if pages[0]['t'] != rec['t_in']:
                add('FAIL', '%s/%s first page at %.2f, not at t_in %.2f' % (pid, key, pages[0]['t'], rec['t_in']))
            # sync points: every key with pages changes page there
            for s in rec['sync']:
                if not any(abs(pg['t'] - s) < 1e-6 for pg in pages):
                    add('FAIL', '%s/%s has no page change at the sync point %.2f' % (pid, key, s))
            # widths
            if metrics is not None:
                for pg in pages:
                    for ln in pg['lines']:
                        w = deg_of_em(metrics.width_em(pg['font'], ln), RIG['em_deg'])
                        pg.setdefault('width_deg', []).append(round(w, 2))
                        if w > RIG['max_line_deg'] + 1e-6:
                            add('FAIL', '%s/%s line %.1f° > %.0f°' % (pid, key, w, RIG['max_line_deg']), ln)
            # reading speed (report)
            for i, pg in enumerate(pages):
                t_next = pages[i + 1]['t'] if i + 1 < len(pages) else rec['t_end']
                txt = ''.join(pg['lines'])
                n = len(norm(txt)) if key in ('zh', 'zht', 'ja') else len(' '.join(pg['lines']))
                rate = n / max(t_next - pg['t'], 1e-3)
                pg['rate'] = round(rate, 2)
                if rate > SPEED[key] + 1e-6:
                    add('EXCEPT' if (pid, key) in SPEED_EXCEPT else 'WARN', '%s/%s page %d reads %.1f /s (limit %.0f)' % (pid, key, i + 1, rate, SPEED[key]))
        # no-text zones and the Tianwen deadline
        t0 = rec['t_in']
        t1 = rec['t_end']
        for z0, z1, what in NO_TEXT:
            if t0 < z1 and t1 > z0:
                add('FAIL', '%s shows %.2f-%.2f inside a no-text zone (%s %.2f-%.2f)' % (pid, t0, t1, what, z0, z1))
        if pid == 'P09_Tianwen' and t1 > 1018.11 + 1e-6:
            add('FAIL', 'Tianwen subtitles must be gone by 1018.11 (they end %.2f)' % t1)
        if rec['halo_alpha'] < 0 or rec['halo_alpha'] > 1:
            add('FAIL', '%s halo alpha %.2f' % (pid, rec['halo_alpha']))
    for tier, hx in L.SUB_TIER_HEX.items():
        r, g, b = (int(hx[i:i + 2], 16) for i in (1, 3, 5))
        luma = 0.2126 * r + 0.7152 * g + 0.0722 * b
        add('ok' if luma <= RIG['luma_max'] else 'FAIL', 'tier %s %s luma %.1f (<= %.0f)' % (tier, hx, luma, RIG['luma_max']))
    # E outside the forbidden band (D-45 #15.1)
    lo, hi = RIG['forbidden_el_band_deg']
    for e in sorted({r_['base_bottom_el'] for r_ in subs} | {RIG['base_bottom_el_deg']}):
        add('ok' if not (lo < e < hi) else 'FAIL', 'last-line elevation %.1f° outside (%.0f°, %.0f°)' % (e, lo, hi))
    add('ok' if RIG['em_deg'] >= RIG['em_floor_deg'] else 'FAIL', 'em %.2f° >= the floor %.2f°' % (RIG['em_deg'], RIG['em_floor_deg']))
    return ok, rows


def report_md(subs, rows, extra=None):
    out = ['# 字幕自检（字体套件第 5 版，D-45；`Tools~/lanbai_subtitles.py` 生成）', '',
           '每一页：开始淡入的时刻、字体、行、每行宽（°，em %.1f°）、阅读速度。' % RIG['em_deg'], '']
    fails = [r for r in rows if r[0] == 'FAIL']
    out.append('**结果：%s**（%d 项不过；例外 %d 项；提醒 %d 项）' % ('全部通过' if not fails else '不过', len(fails),
                                                            sum(1 for r in rows if r[0] == 'EXCEPT'), sum(1 for r in rows if r[0] == 'WARN')))
    out.append('')
    for st, what, detail in rows:
        if st != 'ok':
            out.append('- %s %s%s' % (st, what, ('：' + detail) if detail else ''))
    if extra:
        out += [''] + extra
    out += ['', '| 诗 | 键 | 页 | t | 字体 | 行 | 宽 ° | 读速 |', '|---|---|---|---|---|---|---|---|']
    for rec in subs:
        for key in KEYS:
            pages = rec['keys'].get(key, [])
            if not pages:
                out.append('| %s | %s | — | — | — | %s | | |' % (rec['poem'], key, rec['empty_keys'].get(key, '（没有）')))
            for i, pg in enumerate(pages):
                out.append('| %s | %s | %d | %.2f | %s | %s | %s | %s |' % (
                    rec['poem'], key, i + 1, pg['t'], pg['font'].split('-')[0][-8:], ' / '.join(pg['lines']),
                    ' / '.join('%.1f' % w for w in pg.get('width_deg', [])), pg.get('rate', '')))
    return '\n'.join(out) + '\n'


def main():
    subs, _ = build()
    try:
        m = Metrics()
    except Exception as e:      # no fontTools
        print('no fontTools (%s): widths not checked' % e)
        m = None
    ok, rows = check(subs, m)
    os.makedirs(os.path.join(KIT, 'Docs~'), exist_ok=True)
    with open(os.path.join(KIT, 'Docs~', 'subtitle_report.md'), 'w', encoding='utf-8') as f:
        f.write(report_md(subs, rows))
    for r in rows:
        if r[0] != 'ok':
            print(*r)
    print('SUBTITLES', 'OK' if ok else 'FAIL')
    return 0 if ok else 1


if __name__ == '__main__':
    raise SystemExit(main())
