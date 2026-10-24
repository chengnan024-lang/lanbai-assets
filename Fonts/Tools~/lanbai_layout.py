# -*- coding: utf-8 -*-
"""Lanbai / 蓝白 — the one place where every poem's TMP objects are laid out (art bible v2.1 §6·8, §7.2–7.5).

Both build_fonts.py (-> strings_all.json 'layout', build_report) and make_proofs.py (-> the proof sheets) call this,
so the numbers the Director reads and the pictures we looked at cannot disagree.

Model (what TMP 3.0 does for a world-space TextMeshPro, rich text off, no GSUB/GPOS, kern table only):
  * pen: advance + kern + tracking after every glyph; TMP subtracts the last glyph's tracking from the line's
    maxAdvance, so a centred line's box is [0, W] with W = sum(adv) + kern + tracking * (n - 1);
  * 1 em = 0.1 * fontSize world units at localScale 1  ->  fontSize = 10 * d * tan(size°);
  * every text object uses TextAlignmentOptions.Baseline (horizontal Center, first baseline on the transform).
Vertical em boxes: CJK = ideographic em box (BASE idtp 880 / ideo -120); Latin = ascender 0.72 / descender -0.26.
Elevations are degrees of visual angle, positive up; a parent at (az, el_anchor, d) faces the head and children sit
at local y = d * tan(el - el_anchor), local x = offset_em * em_m.
"""
import os, math
from fontTools.ttLib import TTFont
from fontTools.pens.boundsPen import BoundsPen

import lanbai_strings as L

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
SUB = os.path.join(KIT, 'Subset')

CJK_TOP, CJK_BOT = 0.88, -0.12
LAT_TOP, LAT_BOT = 0.72, -0.26
CJK_MID = (CJK_TOP + CJK_BOT) / 2            # 0.38 em above the baseline: optical centre of a Han character
OPT_MIN_EM = 0.06                            # optical offsets below this are not worth a transform
EL_MAX, EL_MIN = 10.0, -15.0                 # bible §7.3: a text's centre never above +10°, never below -15°
PLAYERS = ('zh', 'ja', 'en', 'de')        # v4 (D-30): client language -> player key, L.PLAYER_OF_CLIENT


def is_cjk(fk):
    return L.FONTS[fk]['cjk']

def pitch_em(fk):
    return 1.6 if is_cjk(fk) else 1.35          # bible §7.2

def track_em(fk):
    return 0.10 if is_cjk(fk) else 0.0          # bible §7.2

def top_em(fk):
    return CJK_TOP if is_cjk(fk) else LAT_TOP

def bot_em(fk):
    return CJK_BOT if is_cjk(fk) else LAT_BOT

def font_size(d, size_deg):
    return 10.0 * d * math.tan(math.radians(size_deg))

def em_m(d, size_deg):
    """em height in metres for a glyph of size_deg at distance d (bible §7.3: h = 0.0419 x d x size/2.4). For a few
    degrees d*tan(a) and 2*d*tan(a/2) agree to 0.04 %; the scrims (tens of degrees) use span_m below."""
    return d * math.tan(math.radians(size_deg))

def span_m(d, full_deg):
    """width in metres of a flat quad, facing the head at distance d, that subtends full_deg (verify r2 B.2:
    2*d*tan(a/2), NOT d*tan(a), which made the scrims 8-27 % too wide in Unity)."""
    return 2.0 * d * math.tan(math.radians(full_deg) / 2.0)

def span_deg(d, width_m):
    """inverse of span_m: the angle a quad of width_m at distance d really subtends."""
    return math.degrees(2.0 * math.atan(width_m / (2.0 * d)))


class Metrics:
    """Advance / kern / ink of a SUBSET font (the file TMP is built from)."""
    _cache = {}

    def __new__(cls, fk):
        if fk not in cls._cache:
            o = super().__new__(cls)
            o._init(fk)
            cls._cache[fk] = o
        return cls._cache[fk]

    def _init(self, fk):
        self.fk = fk
        self.path = os.path.join(SUB, L.FONTS[fk]['subset'])
        tt = TTFont(self.path)
        self.cmap = tt.getBestCmap()
        self.hmtx = tt['hmtx']
        self.upm = tt['head'].unitsPerEm
        self.gs = tt.getGlyphSet()
        self.kern = {}
        if 'kern' in tt:
            for st in tt['kern'].kernTables:
                self.kern.update(st.kernTable)
        hh = tt['hhea']
        self.line_height_em = (hh.ascent - hh.descent + hh.lineGap) / self.upm
        self._ink = {}

    def ink(self, g):
        if g not in self._ink:
            bp = BoundsPen(self.gs)
            self.gs[g].draw(bp)
            b = bp.bounds
            self._ink[g] = None if b is None else (b[0] / self.upm, b[1] / self.upm, b[2] / self.upm, b[3] / self.upm)
        return self._ink[g]

    def line(self, text, tracking_em=None):
        """TMP pen positions in em. Returns dict(width, ink_l, ink_r, pens=[(ch, x, adv, inkbox|None, glyph|None)])."""
        tr = track_em(self.fk) if tracking_em is None else tracking_em
        x, prev, pens = 0.0, None, []
        for ch in text:
            g = self.cmap.get(ord(ch))
            if g is None:
                pens.append((ch, x, 1.0, None, None))
                x += 1.0 + tr
                prev = None
                continue
            if prev is not None:
                x += self.kern.get((prev, g), 0) / self.upm
            adv = self.hmtx[g][0] / self.upm
            pens.append((ch, x, adv, self.ink(g), g))
            x += adv + tr
            prev = g
        width = x - (tr if pens else 0.0)
        inks = [(px + ib[0], px + ib[2]) for (_, px, _, ib, _) in pens if ib is not None]
        il = min(a for a, _ in inks) if inks else 0.0
        ir = max(b for _, b in inks) if inks else width
        return dict(width=width, ink_l=il, ink_r=ir, pens=pens)

    def optical_offset(self, text, tracking_em=None):
        """em to move a centred line right so its INK is centred (a line-final ？！ in a Chinese font leaves
        half an em of blank on the right; bible §7.2's reason for dropping line-final punctuation)."""
        ln = self.line(text, tracking_em)
        d = ln['width'] / 2.0 - (ln['ink_l'] + ln['ink_r']) / 2.0
        return round(d, 3) if abs(d) >= OPT_MIN_EM else 0.0

    def tmp_line_spacing(self, target_pitch_em):
        return round((target_pitch_em - self.line_height_em) * 100.0, 1)


def rich(lines, offsets):
    """Same text with a leading <space> tag on lines that need an optical shift (TMP: a leading space of s moves a
    centred line by s/2). Needs Rich Text ON on that object; plain tmp_text stays the default."""
    out = []
    for t, o in zip(lines, offsets):
        out.append(('<space=%.3gem>' % (2 * o) if o else '') + t)
    return '\n'.join(out)


def _obj(role, lang, fk, size, lines, d, anchor_el, first_bl, extra=None):
    m = Metrics(fk)
    pitch = pitch_em(fk) * size
    bls = [first_bl - i * pitch for i in range(len(lines))]
    top = bls[0] + top_em(fk) * size
    bot = bls[-1] + bot_em(fk) * size
    offs = [m.optical_offset(t) for t in lines]
    widths = [m.line(t)['width'] * size for t in lines]
    o = dict(role=role, lang=lang, font=fk, tmp_asset=L.FONTS[fk]['tmp_asset'], size_deg=size,
             font_size=round(font_size(d, size), 2), character_spacing=round(track_em(fk) * 100, 1),
             line_spacing=m.tmp_line_spacing(pitch_em(fk)), alignment='Baseline',
             lines=list(lines), tmp_text='\n'.join(lines), optical_offsets_em=offs,
             tmp_text_rich=rich(lines, offs) if any(offs) else None,
             first_baseline_el=round(first_bl, 3), line_baselines_el=[round(b, 3) for b in bls],
             top_el=round(top, 3), bottom_el=round(bot, 3), center_el=round((top + bot) / 2, 3),
             width_deg=[round(w, 2) for w in widths],
             local_y_m=round(d * math.tan(math.radians(first_bl - anchor_el)), 4),
             line_local_x_m=[round(o_ * em_m(d, size), 4) for o_ in offs],
             scale_y=1)
    if extra:
        o.update(extra)
    return o


def seg_lines(s_, key):
    """lines of one segment in one language; '<key>_v4' = that language re-broken for the v4 size (D-30 #2: <= 28°)."""
    return s_.get(key + '_v4', s_.get(key, []))


def shown_text(p, player):
    """v4 (D-30): (key, lang, font, size) of the ONE text this player sees. key = 'main' (the original) or a language."""
    k = 'main' if p.get('picture') else L.shown_lang(p, player)
    if k == 'main':
        fk, lang = p['original']['font'], p['original']['lang']
    else:
        fk, lang = L.TR_FONT[k], k
    return k, lang, fk, L.size_for(p, fk, lang)


def block_box(objs, az):
    """the block a poem occupies for one player: width = widest line box, height = top of the first em box to the
    bottom of the last (degrees of visual angle); the table the act packages and the bus's D-13 check use."""
    w = max(max(o['width_deg']) for o in objs)
    top = max(o['top_el'] for o in objs)
    bot = min(o['bottom_el'] for o in objs)
    return dict(width_deg=round(w, 2), height_deg=round(top - bot, 2), az=[round(az - w / 2, 2), round(az + w / 2, 2)],
                el=[round(bot, 2), round(top, 2)], center=[az, round((top + bot) / 2, 2)])


def block_layout(p, player, segs=None):
    """v4 (D-30): a poem shown as ONE single-language block at the main-line size (the original if it is in the player's
    language, else the translation into it). Exception Tianwen (picture): Han characters for everyone + the player's
    language beneath at 1.8° (§7.3 secondary). Block centre = the bible elevation (§7.5); if an object's centre would
    leave [-15°, +10°] (§7.3, 'never'), the whole block is shifted by the minimum amount and the shift is reported."""
    segs = p['segments'] if segs is None else segs
    d = p['place'][2]
    el = p['place'][1]
    key, lang, fm, sm = shown_text(p, player)
    tr = L.translation_for(p, player)
    main = [t for s in segs for t in seg_lines(s, key)]
    trl = [t for s in segs for t in seg_lines(s, tr)] if tr else []
    # relative layout (first main baseline at 0)
    mb_last = -(len(main) - 1) * pitch_em(fm) * sm
    top = top_em(fm) * sm
    bot = mb_last + bot_em(fm) * sm
    t_first = None
    if trl:
        ft, st = p['translations'][tr]['font'], p['size_tr']
        t_first = mb_last - (pitch_em(ft) * st + 0.35 * sm)
        bot = t_first - (len(trl) - 1) * pitch_em(ft) * st + bot_em(ft) * st
    shift = el - (top + bot) / 2.0
    if p.get('picture'):
        # Tianwen: the Han characters ARE the picture (act 9 lights a star on each one at the zh layout's positions),
        # so they sit exactly where the zh player sees them; the player's line simply hangs beneath
        shift = el - (top_em(fm) * sm + mb_last + bot_em(fm) * sm) / 2.0

    def build(sh):
        objs = [_obj('main', lang, fm, sm, main, d, el, 0.0 + sh, dict(shown=key))]
        if trl:
            objs.append(_obj('translation', tr, p['translations'][tr]['font'], p['size_tr'], trl, d, el, t_first + sh))
        return objs

    objs = build(shift)
    adj = 0.0
    hi = max(o['center_el'] for o in objs)
    lo = min(o['center_el'] for o in objs)
    if hi > EL_MAX:
        adj = EL_MAX - hi
    elif lo < EL_MIN:
        adj = EL_MIN - lo
    if adj and p.get('picture'):
        raise ValueError('%s/%s: the picture would have to move (%.2f°)' % (p['id'], player, adj))
    if adj:
        objs = build(shift + adj)
    if p['id'] == 'P09_Tianwen':                      # §6·9: at F13 every Han character becomes a star
        o = objs[0]
        m = Metrics(fm)
        emm = em_m(d, sm)
        pts, chars = [], []
        k = 0          # stagger slot: one per Han character; a punctuation mark focuses with the character before it,
                       # so the 16 characters settle at 15 x 0.12 + 0.6 = 2.4 s = 1011.61 (bible v2.1 §7.5 #8 "≈1011.6 就位")
        for li, t in enumerate(main):
            ln = m.line(t)
            off = o['optical_offsets_em'][li]
            bl = o['line_baselines_el'][li]
            for ch, px, adv, ib, g in ln['pens']:
                x_em = round(px + adv / 2 - ln['width'] / 2 + off, 3)
                star = '一' <= ch <= '鿿'
                if star:
                    pts.append(dict(char=ch, line=li, x_em=x_em, y_em_above_baseline=CJK_MID))
                # verify r2 m5: the per-character focus (§7.4-4, softness 0.9 -> 0 in 0.6 s, 120 ms apart) needs one
                # TMP object (and one material instance) per character: _OutlineSoftness is a material property.
                # A single character with Baseline alignment is centred on its own advance, so this reproduces the
                # line object exactly (kern and tracking are already in the pen positions).
                slot = k if star else max(k - 1, 0)
                chars.append(dict(char=ch, line=li, star=star, focus_delay_s=round(0.12 * slot, 2), focus_s=0.6,
                                  local_x_m=round(x_em * emm, 4),
                                  local_y_m=round(d * math.tan(math.radians(bl - el)), 4),
                                  baseline_el=bl))
                if star:
                    k += 1
        o['star_points'] = pts
        o['char_objects'] = chars
    return add_scrims(dict(player=player, shown=key, shown_lang=lang, translation=tr, anchor=[p['place'][0], el, d],
                           block_center_el=round(el + adj, 3), shift_deg=round(adj, 3), objects=objs,
                           block=block_box(objs, p['place'][0])), p)


# ------------------------------------------------------------------------------ Zhuangzi (§6·8)
ZH_GAP_EM = 0.30        # v3 constant (CJK): v4 derives the gap from the shown language's pitch (same 0.30 em for CJK)


def zhuangzi_times(p):
    """seconds after L1 (971.4) for each segment, the shared exit start and the exit length (bible v2.1 §6·8)."""
    t0 = float(p['segments'][0]['t'])
    seg_t = [round(float(s['t']) - t0, 3) for s in p['segments']]
    return seg_t, round(p['t_appear'] + p['hold_s'] - t0, 3), p.get('exit_s', 4.0)


def zhuangzi_layout(p, player, t_now=None):
    """§6·8 mirror treatment, v4 of this kit (D-30: each player sees ONE language; bible v2.1: only L1 and L3):
       * the player's text is mirrored (the original for zh players, 書き下し for ja, English for everyone else).
         Column (from the top): L1, L3', | horizon |, L3, L1'. The line whose upright copy is BELOW the horizon
         (L3, read looking down) sits next to the horizon, so the typesetting flips exactly at "其视下也，亦若是则已矣";
         L1 and its mirror frame the column. A segment may have several lines (ja / en); the column keeps the
         language's own pitch (1.6 em CJK, 1.35 em Latin) everywhere, the horizon in the middle of the central gap:
         one evenly spaced block that reflects onto itself;
       * no caption slot any more (v3 put the translation under the column);
       * everything leaves together at 989.0 for 4 s, in step with the F12 sun-line collapse: objects above the
         horizon drift up, objects below drift down (each upright / mirror pair separates, the reflection stays exact).
    t_now (s after L1): if given, only objects visible at that moment are returned (for the time strip)."""
    az, el0, d = p['place']
    key, lang, fm, sm = shown_text(p, player)
    segs = p['segments']
    times, t_exit, exit_s = zhuangzi_times(p)
    objs = []
    pitch = pitch_em(fm)
    box = top_em(fm) - bot_em(fm)
    gap_between = pitch - box                  # em between the em boxes of neighbouring lines
    gap0 = gap_between / 2.0                   # horizon -> nearest em box (CJK: 0.30 em, as in v3)
    lines_of = [seg_lines(s_, key) for s_ in segs]
    # the line flipped to read below the horizon goes next to it; the others stack outward in reading order
    flipped = [i for i, s_ in enumerate(segs) if s_.get('upright') == 'below']
    normal = [i for i, s_ in enumerate(segs) if s_.get('upright') != 'below']
    order = flipped + list(reversed(normal))   # slot 1, 2, ... outward from the horizon
    off = {}
    acc = gap0
    for i in order:
        off[i] = acc                           # em from the horizon to the near edge of this slot's em boxes
        acc += (len(lines_of[i]) - 1) * pitch + box + gap_between
    lid = lambda i: s_id(segs[i], i)
    for i, s_ in enumerate(segs):
        text = lines_of[i]
        n = len(text)
        if s_.get('upright') == 'below':
            up_bl = (-off[i] - top_em(fm)) * sm                           # first line's em box touches -off
        else:
            up_bl = (off[i] - bot_em(fm) + (n - 1) * pitch) * sm          # last line's em box touches +off
        up_exit = 'up 0.2°' if up_bl > 0 else 'down 0.2°'
        mi_exit = 'down 0.2°' if up_bl > 0 else 'up 0.2°'
        common = dict(appear_s=times[i], appear_t=round(p['t_appear'] + times[i], 2), exit_at_s=t_exit,
                      exit_t=round(p['t_appear'] + t_exit, 2), exit_s=exit_s, shown=key)
        o = _obj('main', lang, fm, sm, text, d, el0, up_bl,
                 dict(id=lid(i), exit=up_exit, alpha=p['opacity'], **common))
        objs.append(o)
        # mirror: same object, transform at -baseline, localScale.y = -1 (exact reflection about the horizon plane)
        mo = _obj('mirror', lang, fm, sm, text, d, el0, up_bl,
                  dict(id=lid(i) + '′', exit=mi_exit, alpha=round(p['opacity'] * 0.5, 3), outline_softness=0.3, **common))
        mo['scale_y'] = -1
        mo['first_baseline_el'] = round(-up_bl, 3)
        mo['line_baselines_el'] = [round(-b, 3) for b in o['line_baselines_el']]
        mo['top_el'], mo['bottom_el'] = round(-o['bottom_el'], 3), round(-o['top_el'], 3)
        mo['center_el'] = round(-o['center_el'], 3)
        mo['local_y_m'] = round(-o['local_y_m'], 4)
        objs.append(mo)
    lay = add_scrims(dict(anchor=[az, el0, d], objects=objs), p)
    scr = lay['scrims']
    blk = block_box(objs, az)
    if t_now is not None:
        objs = [o for o in objs if o['appear_s'] <= t_now]
    return dict(player=player, shown=key, shown_lang=lang, translation=None, anchor=[az, el0, d], block_center_el=0.0,
                shift_deg=0.0, objects=objs, scrims=scr, block=blk,
                rule='column: %s | horizon | %s (the player\'s own language, mirrored; no caption in v4)' % (
                         ', '.join(o['id'] for o in sorted([o for o in objs if o['center_el'] > 0], key=lambda o: -o['center_el'])),
                         ', '.join(o['id'] for o in sorted([o for o in objs if o['center_el'] < 0], key=lambda o: -o['center_el']))))


def s_id(seg_, i):
    """L1 / L3: the bible numbers the lines of the passage (L2 exists in the text but is not shown)."""
    return seg_.get('label') or 'L%d' % (i + 1)


# ------------------------------------------------------------------------------ scrims (§7.2)
# One soft card behind the text, #0E1A2F α0.30 (8-ii Zhuangzi) or #E8F1F5 α0.25 (6d dawn line), never an outline or
# shadow. Bible v2.1: the dusk line (now 7c, on dark water) has NO scrim.
# Built as a SpriteRenderer with one of two alpha textures (RGB white) and a Sprites/Default material (unlit,
# alpha-blended, depth-tested) whose _Color (Tint) is the scene-linear FILL of the scrim's screen target
# (lanbai_color; verify r2 B.1). SpriteRenderer.color = (1, 1, 1, alpha): white RGB is the same number in gamma and
# linear, so there is no colour-space question, and Udon fades the scrim with SpriteRenderer.color.a.
#   Lanbai_Scrim_Line.png  512x128: horizontal flat core 55 % + raised-cosine tapers; vertical = pure Hann window.
#       Quad height = (n_lines + 1) x pitch, so in the evenly spaced Zhuangzi column the bands of neighbouring lines
#       overlap by half; alpha-over gives 0.30 at a line centre and 1 - 0.85^2 = 0.2775 between lines (7.5 % lighter
#       between lines, never a dark stripe), and a lone line tapers over one pitch.
#   Lanbai_Scrim_Block.png 512x256 (v3): a SUPERELLIPSE veil, r = (|2u-1|^4 + |2v-1|^4)^(1/4), flat to r = 0.5, then
#       a raised cosine to 0 at r = 1: no straight edges, so the 6d veil reads as light on the sea mirror, not as a
#       card. Quad = the padded text box x (1.8, 1.7); the end of every line sits at alpha >= 0.88 of the core.
# The feather is wider than §7.2's 40 px (1.9°) minimum on purpose: the card must melt into the sky, not read as a box.
# Size in metres = 2 d tan(angle / 2) (verify r2 B.2), so Unity shows exactly the angles the proofs draw.
SCRIM_TEX = {
    'line': dict(file='Textures/Lanbai_Scrim_Line.png', px=(512, 128), core=(0.55, 0.0)),
    'block': dict(file='Textures/Lanbai_Scrim_Block.png', px=(512, 256), core=(0.50, 0.50), shape='superellipse', p=4.0,
                  quad_scale=(1.8, 1.7)),
}
SPRITE_PPU = 100.0
SCRIM_MATERIAL = {'dark': 'Lanbai_Scrim_Dark_S8', 'light': 'Lanbai_Scrim_Light_S6'}   # dark: Zhuangzi only; light: 6d only
# §6·8: the Zhuangzi column "永远不压在日线上"; the sun line spans azimuth ±10° at the horizon (§6·8b). No scrim of the
# mirrored column may reach closer than SUN_CLEAR_DEG to it (room for the line's glow): outer edge >= 12°.
SUN_LINE_HALF_DEG = 10.0
SUN_CLEAR_DEG = 2.0


def taper(t, core):
    """t = |2u - 1| in [0, 1]; flat up to core, then raised cosine to 0 at the edge."""
    import numpy as np
    t = np.clip(t, 0, 1)
    if core >= 1:
        return np.ones_like(t)
    s = np.clip((t - core) / (1 - core), 0, 1)
    return np.where(t <= core, 1.0, 0.5 * (1 + np.cos(np.pi * s)))


def scrim_alpha(u, v, style):
    """alpha profile of a scrim texture at normalised (u, v) in [0, 1]."""
    import numpy as np
    T = SCRIM_TEX[style]
    cw, ch = T['core']
    x, y = np.abs(2 * np.asarray(u) - 1), np.abs(2 * np.asarray(v) - 1)
    if T.get('shape') == 'superellipse':
        pe = T['p']
        r = (x ** pe + y ** pe) ** (1.0 / pe)
        return taper(r, cw)
    return taper(x, cw) * taper(y, ch)


_UA = {}


def unity_alpha(kind):
    if kind not in _UA:
        import lanbai_color as LC
        _UA[kind] = LC.scrim_unity_alpha(kind)
    return _UA[kind]


def _scrim(style, kind, center_el, w_deg, h_deg, d, anchor_el, of, appear=0.0, az=None, note=None):
    col, a = L.SCRIM_DARK if kind == 'dark' else L.SCRIM_LIGHT
    ua = unity_alpha(kind)['alpha_unity']
    tex = SCRIM_TEX[style]
    wm, hm = span_m(d, w_deg), span_m(d, h_deg)
    r = dict(style=style, texture=tex['file'], kind=kind, color_target=col, alpha=a, alpha_unity=ua,
             alpha_note='alpha = the bible veil (display-space look, what the proofs draw); sprite_color alpha = '
                        'alpha_unity, solved so the Unity scene-linear blend reads like that veil (lanbai_color.scrim_unity_alpha)',
             material=SCRIM_MATERIAL[kind], sprite_color=[1, 1, 1, ua],
             for_object=of, appear_s=appear,
             center_el=round(center_el, 3), width_deg=round(w_deg, 2), height_deg=round(h_deg, 2),
             width_m=round(wm, 3), height_m=round(hm, 3),
             local_y_m=round(d * math.tan(math.radians(center_el - anchor_el)), 4),
             sprite_scale=[round(wm / (tex['px'][0] / SPRITE_PPU), 4), round(hm / (tex['px'][1] / SPRITE_PPU), 4), 1],
             render_queue=3009)
    if az is not None:
        r['azimuth_span_deg'] = [round(az - span_deg(d, wm) / 2, 2), round(az + span_deg(d, wm) / 2, 2)]
    if note:
        r['note'] = note
    return r


def add_scrims(lay, p):
    if not p.get('scrim'):
        lay['scrims'] = []
        return lay
    d, el0 = lay['anchor'][2], lay['anchor'][1]
    az0 = lay['anchor'][0]
    sc = []
    objs = lay['objects']
    if p.get('mirror'):
        # widest scrim allowed by the sun line: outer edge >= SUN_LINE_HALF + SUN_CLEAR from azimuth 0
        w_sun = 2 * (abs(az0) - SUN_LINE_HALF_DEG - SUN_CLEAR_DEG)
        for o in objs:                       # every line, the mirrored ones too: the darkening stays symmetric
            if o['role'] == 'caption':       # the caption sits on the darker other sky, clear of the bright seam
                continue
            m = Metrics(o['font'])
            wdeg = max(m.line(t)['width'] for t in o['lines']) * o['size_deg']
            pitch = pitch_em(o['font']) * o['size_deg']
            w = (wdeg + 0.4 * o['size_deg']) / SCRIM_TEX['line']['core'][0]
            note = None
            if w > w_sun:
                note = ('width clamped %.2f° -> %.2f° so the outer edge stays %.0f° clear of the ±%.0f° sun line '
                        '(§6·8; verify r2 B.2); the text ends sit %.2f° into the taper (alpha x %.3f)' % (
                            w, w_sun, SUN_CLEAR_DEG, SUN_LINE_HALF_DEG,
                            max(0.0, wdeg / 2 - w_sun * SCRIM_TEX['line']['core'][0] / 2),
                            float(taper(min(1.0, wdeg / w_sun), SCRIM_TEX['line']['core'][0]))))
                w = w_sun
            h = (len(o['lines']) + 1) * pitch
            sc.append(_scrim('line', p['scrim'], o['center_el'], w, h, d, el0, o.get('id', o['role']), o.get('appear_s', 0.0),
                             az=az0, note=note))
    else:
        top = max(o['top_el'] for o in objs)
        bot = min(o['bottom_el'] for o in objs)
        wdeg = max(max(Metrics(o['font']).line(t)['width'] for t in o['lines']) * o['size_deg'] for o in objs)
        pad = 0.4 * p['size_main']
        kx, ky = SCRIM_TEX['block']['quad_scale']
        sc.append(_scrim('block', p['scrim'], (top + bot) / 2, (wdeg + pad) * kx, (top - bot + pad) * ky, d, el0, 'block',
                         az=az0))
    lay['scrims'] = sc
    return lay


def material_name(p, o):
    """the per-poem TMP material preset that carries the solved _FaceColor (Editor/LanbaiPoemMaterials.cs makes it)."""
    return '%s - %s' % (o['tmp_asset'], p['id'])


def decorate(lay, p):
    """colour fields every object needs (verify r2 B.1): vertex colour white + alpha, colour on the material."""
    for card in (lay if isinstance(lay, list) else [lay]):
        for o in card['objects']:
            a = o.get('alpha', p['opacity'])
            o['alpha'] = a
            o['vertex_color'] = [1, 1, 1, a]
            o['material'] = material_name(p, o)
            # verify r3 m4: _OutlineSoftness / _FaceDilate are MATERIAL properties, and a main line and its mirror share
            # one preset but animate differently -> every text object renders with its OWN instance of the preset
            # (TMP: assign the preset to fontSharedMaterial once, then animate tmp.fontMaterial, which TMP instantiates
            # per object). The preset itself is never animated.
            final = o.get('outline_softness', 0.0)
            o['material_instance'] = 'own'
            o['outline_softness_anim'] = [0.9, final]          # §7.4-4 focus-in, 2.5 s ease-out (mirror settles at 0.3)
            o['face_dilate'] = dict(desktop=0.05, vr=0.10)     # §7.2, set once per instance from IsUserInVR()
    return lay


def timing(p):
    """bible v2.1 §7.5 timeline for the Director (seconds after departure; bind to the cue label, bible law 2)."""
    t = dict(cue=p.get('cue'), t_appear=p['t_appear'], focus_s=2.5, hold_s=p.get('hold_s'), t_exit=p.get('t_exit'),
             t_gone=p['t_gone'], exit=p['exit'], hold_formula_s=p.get('hold_formula_s'))
    if p.get('line_cues'):
        t['line_cues'] = p['line_cues']
    if p.get('hold_note'):
        t['note'] = p['hold_note']
    if p['id'] == 'P09_Tianwen':
        # §7.4-4 / §7.5 #8: per-character focus, 0.6 s each, 120 ms apart over the 16 Han characters (punctuation
        # rides with the character before it) -> the main line is settled 2.4 s after t_appear
        t['focus_s'] = round(15 * 0.12 + 0.6, 2)
        t['t_settled'] = round(p['t_appear'] + t['focus_s'], 2)
        t['focus_note'] = ('主行逐字对焦：16 个汉字各 0.6 s、120 ms 错开，标点与前一个字一起（char_objects）；'
                           '%.2f 就位（圣经 §7.5 #8 “≈1011.6 就位”）。译文物体照常 2.5 s 整块对焦' % t['t_settled'])
    return t


def poem_layout(p, player, segs=None):
    lay = zhuangzi_layout(p, player) if p.get('mirror') else block_layout(p, player, segs)
    lay['timing'] = timing(p)
    return decorate(lay, p)


def all_layouts():
    """{poem_id: {player: layout}} (bible v2.1: Urlicht is one card, "Ach nein! / Ich ließ mich nicht abweisen!")."""
    out = {}
    for p in L.POEMS:
        out[p['id']] = {pl: poem_layout(p, pl) for pl in PLAYERS}
    return out


def vertical_check(layouts):
    """Every text object's centre within [-15°, +10°] (bible §7.3). Returns (ok, rows)."""
    rows, ok = [], True
    for pid, per in layouts.items():
        for pl, lay in per.items():
            for card in (lay if isinstance(lay, list) else [lay]):
                for o in card['objects']:
                    c = o['center_el']
                    good = EL_MIN - 1e-6 <= c <= EL_MAX + 1e-6
                    ok &= good
                    rows.append(dict(poem=pid, player=pl, card=card.get('card'), obj=o.get('id', o['role']),
                                     center_el=c, top_el=o['top_el'], bottom_el=o['bottom_el'],
                                     shift_deg=card['shift_deg'], ok=good))
    return ok, rows
