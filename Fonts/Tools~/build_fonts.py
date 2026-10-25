# -*- coding: utf-8 -*-
"""Build everything in the Fonts kit from lanbai_strings.py:
   strings_all.json, Charsets/charset_*.txt, Subset/*.otf|ttf (fontTools), and Docs~/reports.
Usage:  python3 build_fonts.py            (run from anywhere; paths are relative to this file)
Needs:  fontTools >= 4.40  (pip install fonttools)
Originals are expected in ../Originals~/ (downloaded by fetch_fonts.sh).
"""
import os, sys, json, math, datetime, collections, io
from fontTools.ttLib import TTFont, newTable
from fontTools import subset as ftsubset
from fontTools.varLib import instancer
from fontTools.pens.boundsPen import BoundsPen

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import lanbai_strings as L

ORIG = os.path.join(KIT, 'Originals~')
SUB = os.path.join(KIT, 'Subset')
CS = os.path.join(KIT, 'Charsets')
DOCS = os.path.join(KIT, 'Docs~')
for d in (SUB, CS, DOCS):
    os.makedirs(d, exist_ok=True)

# ------------------------------------------------------------------------------------------ collect
by_font = collections.OrderedDict((k, collections.OrderedDict()) for k in L.FONTS)   # font -> {string: [ids]}

def add(font, text, ident):
    if text is None:
        return
    by_font[font].setdefault(text, [])
    if ident not in by_font[font][text]:
        by_font[font][text].append(ident)

def join_lines(segs, key):
    out = []
    for s in segs:
        if key in s:
            out += s[key]
    return out

# v5 (D-45): the poems are subtitles (lanbai_subtitles.py). World text is left only for the Han characters of Tianwen in
# the sky (everyone) and the Zhuangzi column (D-45 #15.4: zh / en / de read the simplified column, zht / ja the
# traditional one). Tianwen's v4 sub-lines stay in its frozen layout (SHA check) but nobody shows them any more.
import lanbai_subtitles as LS
WORLD_TEXT = {'P09_Tianwen': ('main',), 'P08b_Zhuangzi_Xiaoyao': ('main', 'zht')}
COLUMN_OF_KEY = {'zh': 'zh', 'en': 'zh', 'de': 'zh', 'zht': 'zht', 'ja': 'zht'}
SUBS, SUB_STRINGS = LS.build()
poems_out = []
for p in L.POEMS:
    keep = WORLD_TEXT.get(p['id'], ())
    for fk, ln, ident in L.shown_strings(p):
        k_ = 'main' if ident == p['id'] else ident.split('/', 1)[1]
        if k_ in keep:
            add(fk, ln, ident)
    main_lines = join_lines(p['segments'], 'main')
    q = {k: v for k, v in p.items() if k not in ('segments', 'translations')}
    q['original'] = dict(p['original'], lines=main_lines, tmp_text='\n'.join(main_lines))
    q['segments'] = p['segments']
    q['translations'] = {}
    for lang, tr in p['translations'].items():
        lines = join_lines(p['segments'], lang)
        q['translations'][lang] = dict(font=(L.SUB_FONT if p.get('picture') else L.TR_FONT)[lang], lines=lines, tmp_text='\n'.join(lines))
    q['display_by_player_language'] = {}
    for pl in ('zh', 'zht', 'ja', 'en', 'de'):
        q['display_by_player_language'][pl] = dict(shown='main' if p.get('picture') else L.shown_lang(p, pl),
                                                   sub_line=L.translation_for(p, pl))
    poems_out.append(q)

# credits (bible full text)
C = L.CREDITS
add(C['title']['font'], C['title']['text'], 'CREDITS/title')
add(C['title_cjk']['font'], C['title_cjk']['text'], 'CREDITS/title_cjk')
for ln in C['epigraph']['lines']:
    add(C['epigraph']['font'], ln, 'CREDITS/epigraph')
add(C['attribution']['font'], C['attribution']['text'], 'CREDITS/attribution')
for row in C['rows']:
    add(C['role_font'], row['role'], 'CREDITS/role')
    for n in row['names']:
        if not n.get('placeholder'):          # placeholders are notes for the user, not display text
            add(n['font'], n['text'], 'CREDITS/name')
for font, lines in L.CREDITS_SIGNKIT_VARIANT.items():
    for ln in lines:
        add(font, ln, 'CREDITS_SIGNKIT')
# Coleridge
K = L.COLERIDGE
add(K['head']['font'], K['head']['text'], 'COLERIDGE/head')
add(K['prose']['font'], K['prose']['text'], 'COLERIDGE/prose')
for ln in K['verse']['lines']:
    add(K['verse']['font'], ln, 'COLERIDGE/verse')
# destination roll, UI
add(L.DESTINATION_ROLL['font'], L.DESTINATION_ROLL['text'], 'DEST_ROLL')
for u in L.UI:
    add(u['font'], u['text'], u['id'])
for fk, ln, ident in SUB_STRINGS:                      # v5 subtitles and the board's settings card
    add(fk, ln, ident)
RETIRED = [k for k in L.FONTS if not by_font[k]]       # v5: JP Medium (it only had Tianwen's Japanese sub-line)
for k in RETIRED:
    del by_font[k]
FONTS_V5 = collections.OrderedDict((k, v) for k, v in L.FONTS.items() if k not in RETIRED)

# --------------------------------------------------------------------------------------- charsets
def charset_of(strings):
    cs = set()
    for s in strings:
        for ch in s:
            if ch not in '\n\r\t':
                cs.add(ch)
    return ''.join(sorted(cs, key=ord))

charsets = collections.OrderedDict()
for k in FONTS_V5:
    charsets[k] = charset_of(by_font[k].keys())

def write_charset(name, chars):
    p = os.path.join(CS, name)
    with open(p, 'w', encoding='utf-8', newline='') as f:
        f.write(chars)            # no trailing newline: TMP would try to add U+000A
    return p

charset_files = {}
for k, chars in charsets.items():
    charset_files[k] = 'Charsets/' + os.path.basename(write_charset('charset_%s.txt' % k, chars))
    if not L.FONTS[k]['cjk']:
        plus = ''.join(sorted(set(chars) | set(L.ASCII), key=ord))
        write_charset('charset_%s+ascii.txt' % k, plus)
# union files for convenience
write_charset('charset_ALL_CJK.txt', ''.join(sorted(set(''.join(v for k, v in charsets.items() if L.FONTS[k]['cjk'])), key=ord)))

# ---------------------------------------------------------------------------------------- subsets
LATIN_EXTRA = [*range(0x20, 0x7F), *range(0xA0, 0x100), *range(0x2010, 0x2028), *range(0x2030, 0x203B), 0x2044, 0x20AC, 0x2122]
CJK_EXTRA = [*range(0x20, 0x7F), *range(0x3000, 0x3020), *range(0xFF01, 0xFF5F), 0x00B7, 0x2014, 0x2015, 0x2018, 0x2019, 0x201C, 0x201D, 0x2026, 0x2500, 0x2E3A]


def cjk_dash(font):
    """Chinese 破折号 = two full-width dashes on the Han mid-line that join into one 2 em rule. TMP applies no GSUB,
    and Source Han's default U+2014 is the proportional Latin dash (890-901 wide, ink at 242-299, i.e. low, and two of
    them leave a gap). In our renamed subsets U+2014 therefore points at the full-bleed rule of U+2500
    (advance 1000, ink 0-1000 x 360-400: the Han mid-line, same stroke as the font's own 'fwid' dash)."""
    n = 0
    for t in font['cmap'].tables:
        if t.isUnicode() and 0x2500 in t.cmap and 0x2014 in t.cmap:
            t.cmap[0x2014] = t.cmap[0x2500]
            n += 1
    return n


def load_original(k):
    info = L.FONTS[k]
    f = TTFont(os.path.join(ORIG, info['original']))
    if info.get('instance'):
        f = instancer.instantiateVariableFont(f, info['instance'], updateFontNames=True)
        fix_static_names(f, k)
        static_name = k + '.ttf'                     # EBGaramond-Regular.ttf / EBGaramond-Italic.ttf (full, static)
        sp = os.path.join(ORIG, static_name)
        f.save(sp)
        f = TTFont(sp)
    return f


def fix_static_names(f, k):
    """instancer names the italic instance 'EBGaramondItalic-Italic'; give both instances clean names."""
    fam = 'EB Garamond'
    sty = 'Italic' if k.endswith('Italic') else 'Regular'
    ps = 'EBGaramond-' + sty
    name = f['name']
    for rec in list(name.names):
        if rec.nameID == 1:
            rec.string = fam
        elif rec.nameID == 2:
            rec.string = sty
        elif rec.nameID == 4:
            rec.string = fam + ' ' + sty
        elif rec.nameID == 6:
            rec.string = ps
        elif rec.nameID == 3:
            rec.string = rec.toUnicode().replace('EBGaramondItalic-Italic', ps)
    name.removeNames(nameID=16)
    name.removeNames(nameID=17)
    name.removeNames(nameID=25)


def gpos_kern_pairs(font, glyphs):
    """Evaluate the GPOS 'kern' feature (latn, else DFLT; default LangSys) for every ordered pair of `glyphs`.
    Returns {(left, right): xAdvanceAdjust} (font units, non-zero only). Lookup type 2 (and 9 -> 2) only."""
    if 'GPOS' not in font:
        return {}, 0
    t = font['GPOS'].table
    scripts = {sr.ScriptTag: sr.Script for sr in t.ScriptList.ScriptRecord}
    sc = scripts.get('latn') or scripts.get('DFLT')
    if sc is None or sc.DefaultLangSys is None:
        return {}, 0
    lookups = []
    for fi in sc.DefaultLangSys.FeatureIndex:
        fr = t.FeatureList.FeatureRecord[fi]
        if fr.FeatureTag == 'kern':
            lookups += list(fr.Feature.LookupListIndex)
    lookups = sorted(set(lookups))
    gset = set(glyphs)
    total = collections.defaultdict(int)
    n_placement = 0
    for li in lookups:
        lk = t.LookupList.Lookup[li]
        subs = lk.SubTable
        typ = lk.LookupType
        if typ == 9:
            typ = subs[0].ExtensionLookupType
            subs = [s.ExtSubTable for s in subs]
        if typ != 2:
            continue
        done = set()                                   # pairs already matched by an earlier subtable of this lookup
        for st in subs:
            cov = st.Coverage.glyphs
            if st.Format == 1:
                for i, g1 in enumerate(cov):
                    if g1 not in gset:
                        continue
                    for rec in st.PairSet[i].PairValueRecord:
                        g2 = rec.SecondGlyph
                        if g2 not in gset or (g1, g2) in done:
                            continue
                        done.add((g1, g2))
                        v1 = getattr(rec, 'Value1', None)
                        v2 = getattr(rec, 'Value2', None)
                        dx = (getattr(v1, 'XAdvance', 0) or 0) if v1 is not None else 0
                        if v2 is not None and (getattr(v2, 'XPlacement', 0) or 0):
                            n_placement += 1
                        if dx:
                            total[(g1, g2)] += dx
            elif st.Format == 2:
                cd1 = st.ClassDef1.classDefs if st.ClassDef1 else {}
                cd2 = st.ClassDef2.classDefs if st.ClassDef2 else {}
                for g1 in cov:
                    if g1 not in gset:
                        continue
                    c1 = cd1.get(g1, 0)
                    row = st.Class1Record[c1].Class2Record
                    for g2 in gset:
                        if (g1, g2) in done:
                            continue
                        done.add((g1, g2))              # format 2 matches every second glyph once g1 is covered
                        v1 = row[cd2.get(g2, 0)].Value1
                        dx = (getattr(v1, 'XAdvance', 0) or 0) if v1 is not None else 0
                        if dx:
                            total[(g1, g2)] += dx
    return {k: v for k, v in total.items() if v}, n_placement


def add_kern_table(font, pairs):
    from fontTools.ttLib.tables._k_e_r_n import KernTable_format_0
    kern = newTable('kern')
    kern.version = 0
    st = KernTable_format_0()
    st.version = 0
    st.coverage = 1                    # horizontal
    st.format = 0
    st.tupleIndex = None
    st.kernTable = dict(pairs)
    kern.kernTables = [st]
    font['kern'] = kern


def rename_rfn(font, info):
    """OFL §3: a modified font must not use a Reserved Font Name. Source Han: 'Source' (Adobe). IM FELL: name ID 0 of
    both originals says 'With Reserved Font Name IM FELL English Roman / SC' (verify r3 m1; upstream OFL.txt lists no
    RFN, so we follow the stricter statement in the font). Rename family / full / PostScript names everywhere."""
    fam = info['new_family']
    sty = info['style']
    ps = (fam.replace(' ', '') + '-' + sty)
    full = fam + ' ' + sty
    name = font['name']
    orig_full = (name.getDebugName(4) or info['original'])
    for rec in list(name.names):
        nid = rec.nameID
        if nid == 1:
            rec.string = fam if sty == 'Regular' else fam + ' ' + sty
        elif nid == 16:
            rec.string = fam
        elif nid == 17:
            rec.string = sty
        elif nid == 3:
            rec.string = ps + ';Lanbai subset;' + datetime.date.today().isoformat()
        elif nid in (4, 18):
            rec.string = full
        elif nid in (6, 20):
            rec.string = ps
        elif nid == 5:
            rec.string = rec.toUnicode() + '; Lanbai subset (fontTools)'
    # keep copyright (0), trademark (7), manufacturer, designer, licence (13, 14) untouched.
    name.setName('Subset of %s (%s) for the VRChat world Lanbai, renamed %s per SIL OFL 1.1 §3 (Reserved Font Name).'
                 % (orig_full, info['original'], ps), 10, 3, 1, 0x409)
    if 'CFF ' in font:
        cff = font['CFF '].cff
        cff.fontNames = [ps]
        td = cff.topDictIndex[0]
        for attr, val in (('FullName', full), ('FamilyName', fam)):
            if hasattr(td, attr):
                setattr(td, attr, val)
        if hasattr(td, 'CIDFontName'):
            td.CIDFontName = ps
        if hasattr(td, 'FDArray'):                 # per-FD names (not user-visible, but no RFN left anywhere)
            old_ps = os.path.splitext(info['original'])[0]
            for fd in td.FDArray:
                if hasattr(fd, 'FontName') and fd.FontName:
                    fd.FontName = fd.FontName.replace(old_ps, ps)
    # sanity: no reserved name left in any name except copyright/trademark/description/licence strings
    toks = info.get('rfn_names', ('Source',))
    hit = lambda t: any(k.lower() in (t or '').lower() for k in toks)
    bad = [(r.nameID, r.toUnicode()) for r in name.names if hit(r.toUnicode()) and r.nameID not in (0, 7, 10, 13, 14)]
    if 'CFF ' in font:
        td = font['CFF '].cff.topDictIndex[0]
        bad += [('FDArray', fd.FontName) for fd in getattr(td, 'FDArray', []) if hit(getattr(fd, 'FontName', ''))]
        bad += [('CFF', n) for n in font['CFF '].cff.fontNames if hit(n)]
    return bad


def subset_font(k):
    info = L.FONTS[k]
    font = load_original(k)
    orig_cmap = font.getBestCmap()
    extra = CJK_EXTRA if info['cjk'] else LATIN_EXTRA
    uni = set(ord(c) for c in charsets[k]) | set(extra)
    uni = {u for u in uni if u in orig_cmap}
    opt = ftsubset.Options()
    opt.layout_features = ['kern']      # TMP 3.0 uses cmap glyphs only; keep GPOS kern for newer TMP
    opt.name_IDs = ['*']
    opt.name_languages = ['*']
    opt.name_legacy = True
    opt.notdef_outline = True
    opt.recalc_bounds = True
    opt.legacy_kern = True
    opt.hinting = True
    opt.glyph_names = False
    sub = ftsubset.Subsetter(opt)
    sub.populate(unicodes=sorted(uni))
    sub.subset(font)
    notes = []
    if info.get('rfn'):
        bad = rename_rfn(font, info)
        notes.append('renamed %s (RFN %s)' % (info['new_family'], '/'.join(info.get('rfn_names', ('Source',)))))
        if bad:
            notes.append('WARNING names still contain a reserved name: %r' % bad)
    if k.startswith('SourceHanSerif'):
        if cjk_dash(font):
            notes.append('U+2014 -> full-width mid-line rule (glyph of U+2500)')
    if info.get('kern_from_gpos'):
        cmap = font.getBestCmap()
        gl = sorted(set(cmap.values()))
        pairs, nplace = gpos_kern_pairs(font, gl)
        add_kern_table(font, pairs)
        notes.append('kern table injected from GPOS: %d pairs over %d glyphs (Value2.XPlacement pairs ignored: %d)'
                     % (len(pairs), len(gl), nplace))
    out = os.path.join(SUB, info['subset'])
    font.save(out)
    # read back check
    f2 = TTFont(out)
    cm2 = f2.getBestCmap()
    missing = [c for c in charsets[k] if ord(c) not in cm2]
    return out, notes, missing, f2


# ------------------------------------------------------------------------------------- run subsets
report = []
subset_info = {}
for k, info in FONTS_V5.items():
    out, notes, missing, f2 = subset_font(k)
    o_path = os.path.join(ORIG, info['original'])
    subset_info[k] = dict(original=info['original'], original_bytes=os.path.getsize(o_path),
                          subset=os.path.basename(out), subset_bytes=os.path.getsize(out),
                          subset_glyphs=len(f2.getGlyphOrder()), notes=notes, missing=missing)
    if info.get('instance'):
        subset_info[k]['static_instance'] = k + '.ttf'
    report.append('%-30s %-32s %10d B -> %-40s %8d B  (%5.2f%%)  glyphs %d  %s%s' % (
        k, info['original'], os.path.getsize(o_path), os.path.basename(out), os.path.getsize(out),
        100.0 * os.path.getsize(out) / os.path.getsize(o_path), len(f2.getGlyphOrder()),
        '; '.join(notes), ('  MISSING ' + ''.join(missing)) if missing else ''))

# ------------------------------------------------------------------------------ coverage check (every string)
cov_lines = []
ok_all = True
fonts_loaded = {k: TTFont(os.path.join(SUB, L.FONTS[k]['subset'])) for k in FONTS_V5}
for k, d in by_font.items():
    cm = fonts_loaded[k].getBestCmap()
    cmo = TTFont(os.path.join(ORIG, L.FONTS[k]['original']), lazy=True).getBestCmap()
    for s in d:
        miss = [c for c in s if c not in '\n' and ord(c) not in cm]
        misso = [c for c in s if c not in '\n' and ord(c) not in cmo]
        if miss or misso:
            ok_all = False
            cov_lines.append('MISSING  %-28s %r  subset:%r original:%r' % (k, s, ''.join(miss), ''.join(misso)))
cov_lines.insert(0, 'coverage: %s — every character of every string is in its font (subset AND original)'
                 % ('PASS' if ok_all else 'FAIL'))

# ----------------------------------------------------------------------------- metrics, widths, atlas fit
def glyph_metrics(font):
    cmap = font.getBestCmap()
    gs = font.getGlyphSet()
    hmtx = font['hmtx']
    upm = font['head'].unitsPerEm
    kern = {}
    if 'kern' in font:
        for st in font['kern'].kernTables:
            kern.update(st.kernTable)
    return cmap, gs, hmtx, upm, kern

MET = {k: glyph_metrics(f) for k, f in fonts_loaded.items()}

def line_width_em(k, s, tracking_em):
    cmap, gs, hmtx, upm, kern = MET[k]
    w = 0.0
    prev = None
    n = 0
    for ch in s:
        g = cmap[ord(ch)]
        w += hmtx[g][0]
        if prev is not None:
            w += kern.get((prev, g), 0)
        prev = g
        n += 1
    return w / upm + tracking_em * max(0, n - 1)

TRACK = lambda k: 0.10 if L.FONTS[k]['cjk'] else 0.0


def glyph_boxes(k, chars, px, pad):
    font = fonts_loaded[k]
    cmap, gs, hmtx, upm, kern = MET[k]
    boxes = []
    for ch in chars:
        g = cmap.get(ord(ch))
        if g is None:
            continue
        bp = BoundsPen(gs)
        gs[g].draw(bp)
        if bp.bounds is None:          # space
            continue
        x0, y0, x1, y1 = bp.bounds
        w = math.ceil((x1 - x0) * px / upm) + 1 + 2 * pad
        h = math.ceil((y1 - y0) * px / upm) + 1 + 2 * pad
        boxes.append((w, h, ch))
    return boxes


def shelf_pack(boxes, W, H):
    """Simple shelf packer (worse than TMP's MaxRects, so a fit here is a fit in TMP)."""
    boxes = sorted(boxes, key=lambda b: (-b[1], -b[0]))
    x = y = shelf_h = 0
    for w, h, _ in boxes:
        if w > W:
            return False, 0
        if x + w > W:
            y += shelf_h
            x = 0
            shelf_h = 0
        if y + h > H:
            return False, 0
        x += w
        shelf_h = max(shelf_h, h)
    return True, y + shelf_h


atlas_lines = ['TMP atlas fit at Sampling Point Size 90, Padding 10 (bible §7.2), shelf-packer check (conservative).']
atlas_info = {}
for k, info in FONTS_V5.items():
    if not info.get('tmp_asset'):
        continue
    for variant, chars in (('exact', charsets[k]),) + ((('+ascii', ''.join(sorted(set(charsets[k]) | set(L.ASCII), key=ord))),) if not info['cjk'] else ()):
        boxes = glyph_boxes(k, chars, 90, 10)
        area = sum(w * h for w, h, _ in boxes)
        rec = None
        for W, H in ((512, 512), (1024, 512), (1024, 1024), (2048, 1024), (2048, 2048), (4096, 4096)):
            fit, used_h = shelf_pack(boxes, W, H)
            if fit:
                rec = (W, H, used_h)
                break
        W0, H0 = info['atlas']
        fit0, used0 = shelf_pack(boxes, W0, H0)
        atlas_info.setdefault(k, {})[variant] = dict(glyphs=len(boxes), bible_atlas='%dx%d' % (W0, H0), fits_bible_atlas=fit0,
                                                     fill_bible_atlas=round(area / (W0 * H0), 3),
                                                     smallest_fit='%dx%d' % (rec[0], rec[1]) if rec else None)
        atlas_lines.append('%-30s %-6s %4d glyphs  bible atlas %dx%d: %s, area fill %4.1f%%   smallest shelf fit: %s' % (
            k, variant, len(boxes), W0, H0, 'FITS' if fit0 else 'DOES NOT FIT', 100 * area / (W0 * H0),
            '%dx%d' % (rec[0], rec[1]) if rec else 'none'))

# TMP line spacing that gives the bible's leading
lead_lines = ['TMP Line Spacing (units of 1/100 em, added to the font line height) to get the bible leading (§7.2):']
lead_info = {}
for k, f in fonts_loaded.items():
    hh = f['hhea']
    upm = f['head'].unitsPerEm
    lh = (hh.ascent - hh.descent + hh.lineGap) / upm
    target = 1.6 if L.FONTS[k]['cjk'] else 1.35
    if k.startswith('IMFell'):
        target = 1.22
    ls = (target - lh) * 100
    lead_info[k] = dict(font_line_height_em=round(lh, 4), target_pitch_em=target, tmp_line_spacing=round(ls, 1))
    lead_lines.append('%-30s font line height %.3f em -> target %.2f em -> TMP Line Spacing %+.1f' % (k, lh, target, ls))

# ------------------------------------------------------------------------------- layout (lanbai_layout.py)
import lanbai_layout as LY
import lanbai_color as LC
# v5: only the world text keeps a layout. P09 exactly as v4.1 (every player; the sky stars of act 9 were placed from it),
# the Zhuangzi column as two sets (COLUMN_OF_KEY says who reads which).
import hashlib
_P = {p['id']: p for p in L.POEMS}
LAYOUTS = collections.OrderedDict()
LAYOUTS['P08b_Zhuangzi_Xiaoyao'] = {k: LY.poem_layout(_P['P08b_Zhuangzi_Xiaoyao'], k) for k in ('zh', 'zht')}
LAYOUTS['P09_Tianwen'] = {pl: LY.poem_layout(_P['P09_Tianwen'], pl) for pl in LY.PLAYERS}
P09_SHA = hashlib.sha256(json.dumps(LAYOUTS['P09_Tianwen'], sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')).hexdigest()
P09_SHA_OK = P09_SHA == LS.P09_SHA_V41
print('P09 layout sha256 %s -> %s' % (P09_SHA, 'PASS (= v4.1)' if P09_SHA_OK else 'FAIL (v4.1 is %s)' % LS.P09_SHA_V41))
for q in poems_out:
    if q['id'] in LAYOUTS:
        q['layout'] = LAYOUTS[q['id']]
    if q['id'] == 'P08b_Zhuangzi_Xiaoyao':
        q['column_of_key'] = dict(COLUMN_OF_KEY)
    if q['id'] == 'P09_Tianwen':
        q['layout_sha256'] = P09_SHA
        q['layout_note'] = ('v5: frozen = v4.1 byte for byte (sha256 above). Only the "main" objects (the Han characters in the '
                            'sky) are shown; the "translation" objects are v4 and retired: the subtitles carry them now.')
v_ok, v_rows = LY.vertical_check(LAYOUTS)

# line widths (v4: every line some player sees, at the size it is shown; limit 28°, bible §7.3 / D-30 #2)
width_lines = ['Line widths in degrees of visual angle at the v4 sizes (limit 28°, bible §7.3, D-30 #2). CJK tracking +0.10 em, Latin 0; kerning = injected kern table.']
worst = 0
seen_w = set()
for pid, per in LAYOUTS.items():
    width_lines.append('')
    width_lines.append(pid)
    for pl, lay in per.items():
        for o in lay['objects']:
            for ln, w in zip(o['lines'], o['width_deg']):
                key = (pid, o['font'], o['size_deg'], ln)
                if key in seen_w:
                    continue
                seen_w.add(key)
                worst = max(worst, w)
                width_lines.append('  %5.1f°%s  %-4s %-11s %-5s %s' % (w, ' OVER' if w > 28.0 else '     ', o['lang'], o['role'], str(o['size_deg']) + '°', ln))
width_lines.insert(1, 'widest line: %.1f° -> %s' % (worst, 'PASS' if worst <= 28.0 else 'FAIL'))

# D-33 #5: placement constraints, then every block against the REAL bus (pkg/bus build_bus + viewcheck rays)
place_bad = LY.placement_check(LAYOUTS)
for r in place_bad:
    print('PLACEMENT FAIL %s/%s: %s' % (r['poem'], r['player'], '; '.join(r['problems'])))
import block_viewcheck as BV
VIEW_LAYOUTS = {'P08b_Zhuangzi_Xiaoyao': LAYOUTS['P08b_Zhuangzi_Xiaoyao']}    # v5: only the Zhuangzi column (D-45 #15.4)
import subprocess, tempfile
BUS_DIR = os.environ.get('LANBAI_BUS_DIR')
BUS_REF = os.environ.get('LANBAI_BUS_REF', 'origin/pkg/bus')
if not BUS_DIR:
    # the bus's geometry is pkg/bus's latest (D-33 #5): export Bus/ from that ref of this repository
    BUS_DIR = tempfile.mkdtemp(prefix='lanbai_bus_')
    repo = os.path.normpath(os.path.join(KIT, '..'))
    arch = subprocess.run(['git', '-C', repo, 'archive', BUS_REF, 'Bus'], capture_output=True)
    if arch.returncode != 0:
        sys.exit('VIEWCHECK: cannot read %s (git fetch origin pkg/bus, or set LANBAI_BUS_DIR): %s' % (BUS_REF, arch.stderr.decode()[:200]))
    subprocess.run(['tar', '-x', '-C', BUS_DIR], input=arch.stdout, check=True)
    BUS_SRC = '%s (%s)' % (BUS_REF, subprocess.run(['git', '-C', repo, 'rev-parse', '--short', BUS_REF], capture_output=True, text=True).stdout.strip())
else:
    BUS_SRC = BUS_DIR
if BV.lookup_available(BUS_DIR) and os.environ.get('LANBAI_VIEWCHECK') != 'rays':
    VIEW = BV.run_lookup(VIEW_LAYOUTS, BUS_DIR)
    how = 'the bus\'s occlusion table Bus/Docs~/viewcheck/hero_occlusion.npz via Bus/Source/occlusion_lookup.py (0.25° grid)'
else:
    VIEW = BV.run(VIEW_LAYOUTS, BUS_DIR)
    how = 'rays cast here: Bus/Source/build_bus.py + viewcheck.cast, every %.1f°' % BV.STEP
view_lines = ['Every block of every player against the real bus (%s; %s; clearance ring %.2f° steps up to %.1f°). '
              'FAIL = some of the block is behind an opaque part (glass does not count).' % (BUS_SRC, how, BV.RING, BV.MAX_CLEAR), '']
view_fail = []
for pid, per in VIEW.items():
    P_ = next(p for p in L.POEMS if p['id'] == pid)
    ex = P_.get('viewcheck_exempt')
    for pl, r in per.items():
        r['exempt'] = ex if (ex and not r['ok']) else None
        st = 'ok' if r['ok'] else ('EXEMPT' if ex else 'FAIL')
        if st == 'FAIL':
            view_fail.append('%s/%s' % (pid, pl))
        view_lines.append('%-24s %-3s %-6s hits %-40s clearance %s%s' % (pid, pl, st, ','.join(r['hits'][:5]) or '-', r['clearance_deg'],
                                                                      (' (%s)' % r['clear_hit']) if r['clear_hit'] else ''))
view_ok = not view_fail
view_lines.insert(1, 'viewcheck: %s%s' % ('PASS' if view_ok else 'FAIL', '' if view_ok else ' — ' + ', '.join(view_fail)))

# D-45 C.2: the subtitle depth table is written by the bus package at Bus/Docs~/viewcheck/subtitle_depth.json (Unity
# ignores ~ folders, so the bake cannot read it there): copied into Fonts/subtitle_depth.json when it is there and has the
# agreed shape ({"seats", "yaw_cells": 24, "pitch_cells": 9, "depth_m": [seat][24][9]}); otherwise the driver's fallbacks
DEPTH_SRC = os.path.join(BUS_DIR, 'Bus', 'Docs~', 'viewcheck', 'subtitle_depth.json')
DEPTH_DST = os.path.join(KIT, 'subtitle_depth.json')
if os.path.exists(DEPTH_SRC):
    with open(DEPTH_SRC, encoding='utf-8') as f_:
        dj = json.load(f_)
    dm = dj.get('depth_m', [])
    shape_ok = (dj.get('yaw_cells') == 24 and dj.get('pitch_cells') == 9 and len(dm) > 0
                and all(len(sy) == 24 and all(len(c) == 9 for c in sy) for sy in dm))
    if not shape_ok:
        sys.exit('DEPTH TABLE: %s does not have the agreed shape (seats x 24 yaw x 9 pitch)' % DEPTH_SRC)
    with open(DEPTH_DST, 'w', encoding='utf-8') as f_:
        json.dump(dj, f_, ensure_ascii=False, separators=(',', ':'))
    depth_note = 'subtitle depth table: %d seats from %s -> Fonts/subtitle_depth.json' % (len(dm), BUS_SRC)
else:
    depth_note = 'subtitle depth table: not in %s yet -> the driver uses the fallbacks (C.2)' % BUS_SRC
print(depth_note)

# D-37 seat table: retired in v5 (D-45 I.1; seat_table.py and seat_positions.json stay, unused)
SEATS = None
seat_lines = ['retired in v5 (D-45): the subtitles follow the head; the Zhuangzi column keeps the main seat\'s D-33 placement']

# block table (D-30: each act package places the poem with it; the bus re-checks Rilke's D-13 position with it)
block_rows = []
for q in poems_out:
    for pl, lay in q.get('layout', {}).items():
        b = lay['block']
        block_rows.append(dict(poem=q['id'], player=pl, shown=lay['shown'], shown_lang=lay['shown_lang'], sub_line=lay['translation'],
                               size_deg=lay['objects'][0]['size_deg'], lines=sum(len(o['lines']) for o in lay['objects'] if o['role'] != 'mirror'),
                               viewcheck=VIEW.get(q['id'], {}).get(pl), **b))

# ------------------------------------------------------------------ colour: screen target -> fill (verify r2 B.1)
SIMINFO = LC.sim_info()
materials = collections.OrderedDict()
col_lines = ['Bible law 1: §7.5 / §7.2 hexes are SCREEN targets. Each is solved with the bible look simulator',
             '(calib_final.solve, vendored in Tools~/colour_sim; grades: %s) under the grade LIVE while the poem is read' % SIMINFO['used'],
             '(two poems are read during a PPv2 volume blend: solved at mid-hold, reading over the hold listed below).',
             'TMP: Vertex Color = white (alpha only); fill -> the poem material preset\'s HDR _FaceColor (one instance per object).',
             'Scrims: SpriteRenderer.color = (1,1,1,alpha); fill -> the Sprites/Default material\'s _Color.',
             'x_T0 = fill max channel / the grade\'s bloom start T0; bloom share = fraction entering the bloom prefilter',
             '(PPv2 QuadraticThreshold) for the opaque fill and at the object\'s alpha over black. naive = round-1 README (hex as vertex colour).',
             '']
col_ok = True
pure_targets = []
engine_items = []
for q in poems_out:
    if 'layout' not in q:
        continue
    fr = LC.poem_fill_record(q)
    prof = fr['profile']
    q['grade'] = fr['grade']
    q['profile'] = prof
    q['face_color'] = fr
    ok = fr['screen_of_fill'] == fr['target'] and fr['screen_luma'] <= 224.5
    col_ok = bool(col_ok and ok)
    if '→' not in fr['grade']:
        pure_targets.append((fr['target'], fr['grade']))
    engine_items.append((q['id'], fr['fill_linear'], LC.poem_solve_spec(q), fr['target']))
    col_lines.append('%-24s %-14s target %s (luma %5.1f) -> fill %-18s -> screen %s  x_T0 %.3f  bloom share %.5f / %.5f@a%.2f  %s   [naive: %s luma %.0f]' % (
        q['id'], fr['grade'], fr['target'], LC.luma(fr['target']), fr['fill_hdr'], fr['screen_of_fill'], fr['x_T0'],
        fr['bloom_share_opaque'], fr['bloom_share_at_alpha'], q['opacity'], 'ok' if ok else 'CHECK',
        fr['naive_vertex_colour_screen'], fr['naive_vertex_colour_luma']))
    for r in fr.get('screen_over_hold', []):
        col_lines.append('%-24s     %-18s t %7.2f  %-16s -> screen %s (luma %5.1f, %d code%s off the target)' % (
            '', r['moment'], r['t'], r['grade'], r['screen'], r['luma'], r['diff_codes'], '' if r['diff_codes'] == 1 else 's'))
    if fr.get('single_profile_fill_would_be'):
        sp_ = fr['single_profile_fill_would_be']
        col_lines.append('%-24s     (a fill solved under %s alone, %s, would show %s here)' % ('', sp_['profile'], sp_['fill_hdr'], sp_['screen_live']))
    names = collections.OrderedDict()
    for pl, lay in q['layout'].items():
        for card in (lay if isinstance(lay, list) else [lay]):
            for o in card['objects']:
                if o['role'] in ('main', 'mirror'):          # v5: Tianwen's "translation" objects are retired
                    names[o['material']] = o['tmp_asset']
    for mname, asset in names.items():
        materials[mname] = dict(name=mname, kind='tmp_face', tmp_asset=asset, poem=q['id'], profile=fr['grade'],
                                target=fr['target'], fill_hdr=fr['fill_hdr'], fill_linear=fr['fill_linear'])
    if q.get('scrim'):
        col, a = L.SCRIM_DARK if q['scrim'] == 'dark' else L.SCRIM_LIGHT
        sp = LC.SCRIM_GRADE[q['scrim']]
        assert sp == fr['grade'], (q['id'], sp, fr['grade'])
        sf = LC.fill_record(col, sp, a)
        q['scrim_fill'] = sf
        pure_targets.append((col, sp))
        engine_items.append((LY.SCRIM_MATERIAL[q['scrim']], sf['fill_linear'], sp, col))
        mname = LY.SCRIM_MATERIAL[q['scrim']]
        materials[mname] = dict(name=mname, kind='scrim', shader='Sprites/Default', render_queue=3009, profile=sp,
                                target=sf['target'], alpha=a, fill_hdr=sf['fill_hdr'], fill_linear=sf['fill_linear'])
        col_lines.append('%-24s %-14s scrim %s a%.2f -> fill %-18s -> screen %s  x_T0 %.3f  bloom share %.5f opaque / %.5f@a%.2f' % (
            '', sp, sf['target'], a, sf['fill_hdr'], sf['screen_of_fill'], sf['x_T0'], sf['bloom_share_opaque'],
            sf['bloom_share_at_alpha'], a))
col_lines.insert(7, 'colour: %s (every fill displays exactly its target; every poem target <= luma 224.5)' % ('PASS' if col_ok else 'FAIL'))
col_lines.append('')
col_lines.append('materials (Editor/LanbaiPoemMaterials.cs builds them): %d' % len(materials))
for m_ in materials.values():
    col_lines.append('  %-58s %-9s %-14s %s -> %s' % (m_['name'], m_['kind'], m_['profile'], m_['target'], m_['fill_hdr']))
# cross-checks (reports only; they never change a fill)
b_status, b_worst, b_rows = LC.bible_crosscheck(sorted(set(pure_targets)))
e_status, e_worst, e_rows = LC.engine_crosscheck(engine_items)
col_lines.append('')
col_lines.append('cross-check 1 — the same fills from art/bible_work/calib_final.solve: %s%s' % (
    b_status, '' if b_worst is None else ' (max %d code%s)' % (b_worst, '' if b_worst == 1 else 's')))
for r in b_rows:
    col_lines.append('  %s %-4s bible %-18s kit %-18s  %d codes' % (r['target'], r['profile'], r['bible_fill'], r['kit_fill'], r['screen_diff_codes']))
col_lines.append('cross-check 2 — every fill through the Grading kit\'s ENGINE model (real PPv2 Neutral path) with its engine-solved')
col_lines.append('  grades (Grading verify B1): %s%s' % (e_status, '' if e_worst is None else '; worst %d code%s from the target' % (e_worst, '' if e_worst == 1 else 's')))
for r in e_rows:
    col_lines.append('  %-30s %-16s target %s -> engine %s  %d' % (r['name'], r['grade'], r['target'], r['engine_screen'], r['diff_codes']))

# ------------------------------------------------------------------ v5 subtitles (D-45): fills, checks, report
_Q = {q['id']: q for q in poems_out}
sub_extra = []
for rec in SUBS:
    q2 = dict(_Q[rec['poem']], color_target=rec['target'], opacity=1.0)
    fr = LC.poem_fill_record(q2)
    rec['grade'] = fr['grade']
    rec['fill_hdr'], rec['fill_linear'], rec['screen_of_fill'] = fr['fill_hdr'], fr['fill_linear'], fr['screen_of_fill']
    rec['fill_ok'] = bool(fr['screen_of_fill'] == fr['target'] and LC.luma(fr['screen_of_fill']) <= LS.RIG['luma_max'])
    if fr.get('screen_over_hold'):
        rec['screen_over_hold'] = fr['screen_over_hold']
    sub_extra.append('fill %-24s %-6s %-14s target %s -> fill %-18s -> screen %s (luma %5.1f) %s' % (
        rec['poem'], rec['tier'], fr['grade'], rec['target'], fr['fill_hdr'], fr['screen_of_fill'], LC.luma(fr['screen_of_fill']),
        'ok' if rec['fill_ok'] else 'FAIL'))
    if rec['halo_alpha'] > 0:
        hf = LC.fill_record(LS.RIG['halo']['colour'], LC.poem_solve_spec(q2), rec['halo_alpha'])
        rec['halo_fill_hdr'], rec['halo_fill_linear'] = hf['fill_hdr'], hf['fill_linear']
        sub_extra.append('halo %-24s a%.2f %s -> fill %s -> screen %s' % (rec['poem'], rec['halo_alpha'], hf['target'], hf['fill_hdr'], hf['screen_of_fill']))
sub_ok, sub_rows = LS.check(SUBS, LS.Metrics())
for rec in SUBS:
    if not rec['fill_ok']:
        sub_ok = False
        sub_rows.append(('FAIL', '%s fill does not show its target %s within luma %.0f' % (rec['poem'], rec['target'], LS.RIG['luma_max']), ''))
    # time on screen: never longer than v4's (so every act's text share stays the §7.5 one, <= 40 %), never earlier
    # than v4's appear time minus the sung lead
    q = _Q[rec['poem']]
    lead = LS.RIG['fade']['lyric_lead'] if rec.get('line_t') else 0.0
    span_ok = (rec['t_in'] >= q['t_appear'] - lead - 1e-6 and rec['t_end'] <= q['t_gone'] + 1e-6)
    sub_rows.append(('ok' if span_ok else 'FAIL', '%s on screen %.2f-%.2f inside v4 %.2f-%.2f (act share <= 40 %% unchanged)' % (
        rec['poem'], rec['t_in'], rec['t_end'], q['t_appear'], q['t_gone']), ''))
    sub_ok = sub_ok and span_ok
sub_rows.append(('ok' if P09_SHA_OK else 'FAIL', 'P09 layout sha256 = v4.1', P09_SHA))
sub_ok = sub_ok and P09_SHA_OK
sub_rows.append(('ok' if ok_all else 'FAIL', 'charsets cover every subtitle and board string (coverage above)', ''))
sub_ok = sub_ok and ok_all
with open(os.path.join(DOCS, 'subtitle_report.md'), 'w', encoding='utf-8') as f:
    f.write(LS.report_md(SUBS, sub_rows, ['```'] + sub_extra + ['```']))

# timing (bible v2.1 §7.4-3 / §7.5)
time_lines = ['Bible v2.1 §7.5 timeline (t = s after departure; the Director binds each to its cue label). hold formula = §7.4-3 x 1.3.', '']
for q in poems_out:
    hf = q.get('hold_formula_s')
    time_lines.append('%-24s cue %-28s appear %8.2f  hold %-5s (formula %s)  exit %-8s gone %8.2f  %s' % (
        q['id'], q.get('cue'), q['t_appear'], q.get('hold_s'), hf, q.get('t_exit'), q['t_gone'], q.get('hold_note', '')))

# scrim geometry (verify r2 B.2): metres from 2 d tan(a/2); report the angle Unity will really show
scr_lines = ['Scrim quads: width_m = 2 d tan(width_deg / 2) (was d tan(width_deg): 8-27 %% too wide). Unity angle = 2 atan(width_m / 2d).',
             'Zhuangzi: outer edge >= %.0f° + %.0f° from the sun (az 0) so no scrim reaches the ±%.0f° sun line (§6·8).' % (
                 LY.SUN_LINE_HALF_DEG, LY.SUN_CLEAR_DEG, LY.SUN_LINE_HALF_DEG), '']
scr_ok = True
seen_s = set()
for q in poems_out:
    for pl, lay in q.get('layout', {}).items():
        for card in (lay if isinstance(lay, list) else [lay]):
            d_ = card['anchor'][2]
            for sc in card['scrims']:
                ua = LY.span_deg(d_, sc['width_m'])
                uh = LY.span_deg(d_, sc['height_m'])
                good = abs(ua - sc['width_deg']) < 0.02 and abs(uh - sc['height_deg']) < 0.02
                if q.get('mirror'):
                    good &= sc['azimuth_span_deg'][0] >= LY.SUN_LINE_HALF_DEG + LY.SUN_CLEAR_DEG - 1e-6
                scr_ok = bool(scr_ok and good)
                key = (q['id'], sc['for_object'], sc['width_m'])
                if key in seen_s:
                    continue
                seen_s.add(key)
                scr_lines.append('%-24s %-6s %-6s design %6.2f° x %5.2f°  ->  %7.3f m x %6.3f m  ->  Unity %6.2f° x %5.2f°  az %s  %s%s' % (
                    q['id'], pl, sc['for_object'], sc['width_deg'], sc['height_deg'], sc['width_m'], sc['height_m'], ua, uh,
                    sc.get('azimuth_span_deg'), 'ok' if good else 'FAIL', ('  [' + sc['note'] + ']') if sc.get('note') else ''))
scr_lines.insert(2, 'scrim geometry: %s' % ('PASS' if scr_ok else 'FAIL'))

# scrim textures (§7.2): RGB white, alpha = the profile lanbai_layout.scrim_alpha describes (proofs use the same)
import numpy as _np
from PIL import Image as _Image
TEX = os.path.join(KIT, 'Textures')
os.makedirs(TEX, exist_ok=True)
for style, info in LY.SCRIM_TEX.items():
    W_, H_ = info['px']
    u = (_np.arange(W_) + 0.5) / W_
    v = (_np.arange(H_) + 0.5) / H_
    a_ = LY.scrim_alpha(u[None, :], v[:, None], style)
    rgba = _np.zeros((H_, W_, 4), _np.uint8)
    rgba[..., :3] = 255
    rgba[..., 3] = _np.clip(_np.round(a_ * 255), 0, 255).astype(_np.uint8)
    _Image.fromarray(rgba, 'RGBA').save(os.path.join(KIT, info['file']))
vert_lines = ['Every text object\'s centre elevation (bible §7.3: never above +10°, never below -15°). '
              'Blocks sit at the §7.5 elevation unless that would push an object out of range; then shifted (shift column).',
              'vertical: %s' % ('PASS' if v_ok else 'FAIL')]
last = None
for r in v_rows:
    key = (r['poem'], r['player'], r['card'])
    if r['poem'] != (last or ('',))[0]:
        vert_lines.append('')
        vert_lines.append(r['poem'])
    vert_lines.append('  %-5s %-6s %-12s centre %+7.2f°   top %+7.2f°   bottom %+7.2f°   shift %+5.2f°  %s' % (
        r['player'], ('card%d' % r['card']) if r['card'] else '', r['obj'], r['center_el'], r['top_el'], r['bottom_el'],
        r['shift_deg'], 'ok' if r['ok'] else 'OUT OF RANGE'))
    last = key
shifted = sorted({(r['poem'], r['player'], r['shift_deg']) for r in v_rows if r['shift_deg']})
vert_lines.insert(2, 'blocks shifted to respect the range: ' + (', '.join('%s/%s %+.2f°' % t for t in shifted) or 'none'))

opt_lines = ['Optical offsets (em, move the line RIGHT) where the ink centre is off the TMP box centre by >= %.2f em '
             '(line-final ？！ in Chinese fonts sit in the left half of their em box). Applied in the proofs; in Unity '
             'use tmp_text_rich (<space> tag, Rich Text on) or per-line local x = line_local_x_m.' % LY.OPT_MIN_EM]
seen = set()
for pid, per in LAYOUTS.items():
    for pl, lay in per.items():
        for card in (lay if isinstance(lay, list) else [lay]):
            for o in card['objects']:
                for t, off in zip(o['lines'], o['optical_offsets_em']):
                    if off and (o['font'], t) not in seen:
                        seen.add((o['font'], t))
                        opt_lines.append('  %+.3f em  %-26s %s' % (off, o['font'], t))

# ------------------------------------------------------------------------------------------- JSON
def fontinfo(k):
    i = dict(L.FONTS[k])
    i['subset_file'] = 'Subset/' + i['subset']
    i['original_file'] = 'Originals~/' + i['original']
    i['charset_file'] = charset_files[k]
    i['charset_count'] = len(charsets[k])
    i['atlas'] = '%dx%d' % i['atlas'] if i.get('atlas') else None
    i.update({'tmp_line_spacing': lead_info[k]['tmp_line_spacing']})
    return i

out = collections.OrderedDict()
out['_about'] = ('Every string the Lanbai world displays (art bible v2.1 §4.7, §5.5, §6, §7; lens_story §4.2, §6). '
                 'Generated by Tools~/build_fonts.py from Tools~/lanbai_strings.py — edit that file, not this one. '
                 'Lines are pre-broken (TMP word wrap OFF). Sizes are em heights in degrees of visual angle; '
                 'place = [azimuth°, elevation°, distance m] in bus space.')
out['generated'] = datetime.datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')
out['version'] = 5
out['display_rule_v5'] = ('v5 (D-45, 2026-10-25; overrides v4 below and bible §7 presentation): the poems are subtitles in the lower '
                          'part of the view, Fins-style, lazily following the head (subtitle_rig, subtitles; Tools~/lanbai_subtitles.py). '
                          'Player key from the client language as before (player_of_client_language; zh-Hant / zh-HK / zh-TW -> zht), '
                          'overridable on the board. Same words as v4, new breaks. World text is left in two places only: the Han '
                          'characters of Tianwen in the sky (everyone; P09 layout frozen = v4.1, layout_sha256) and the Zhuangzi column '
                          '(zh / en / de read the simplified column, zht / ja the traditional one: column_of_key); ja / en / de also get '
                          'Zhuangzi subtitles, zh / zht do not, and nobody gets Tianwen subtitles in zh / zht.')
out['retired_in_v5'] = dict(fonts=RETIRED, block_layouts='every poem but P09 and the Zhuangzi column', seat_table='seat_table.py / seat_positions.json',
                            viewcheck='only the Zhuangzi column', textures=['Textures/Lanbai_Scrim_Block.png'])
out['display_rule'] = ('v4 (D-30, 2026-10-24; overrides bible §7.4-7): every player sees ONE language. Player key from the '
                       'VRChat client language: zh* -> zh, ja -> ja, de -> de, anything else -> en. The original is shown when it '
                       'is in the player\'s language (a de player reads the German originals, English otherwise); otherwise the '
                       'translation into it (Chinese poems for ja = 書き下し). One block at the main-line size (CJK 2.2–2.4°, Latin '
                       '2.0–2.2° em; size_cjk / size_lat per poem), lines <= 28° (a language re-breaks its own lines: <key>_v4). '
                       'Exception (D-30 #4): Tianwen is a picture in the sky: everyone sees the Han characters, a non-zh player also '
                       'gets one 1.8° line of their language beneath (sub_line). Timing unchanged (§7.5, x1.3 kept). Zhuangzi: the '
                       'shown language is mirrored, no caption. layout[player] per poem; block_table lists every block\'s size.')
out['player_of_client_language'] = [dict(client_prefix=a, player=b) for a, b in L.PLAYER_OF_CLIENT]
out['fonts'] = collections.OrderedDict((k, fontinfo(k)) for k in FONTS_V5)
out['by_font'] = collections.OrderedDict((k, [{'text': t, 'used_by': ids} for t, ids in d.items()]) for k, d in by_font.items())
out['poems'] = poems_out
out['credits'] = L.CREDITS
out['credits_signkit_variant'] = L.CREDITS_SIGNKIT_VARIANT
out['coleridge_slip'] = L.COLERIDGE
out['destination_roll'] = L.DESTINATION_ROLL
out['ui'] = L.UI
out['ui_v5'] = LS.ui_rows()
out['subtitle_rig'] = LS.RIG
out['subtitles'] = SUBS
out['subtitle_check'] = dict(passed=bool(sub_ok), rows=[dict(status=a_, what=b_, detail=c_) for a_, b_, c_ in sub_rows if a_ != 'ok'])
out['ui_note'] = L.UI_NOTE
out['layout_model'] = LY.__doc__.strip()
out['zhuangzi_rule'] = LY.zhuangzi_layout.__doc__.strip()
out['charsets'] = charsets
out['block_table'] = block_rows
out['seat_check'] = SEATS['summary'] if SEATS else None   # D-37 (the positions themselves: seat_positions.json)
out['materials'] = list(materials.values())
import gen_poem_materials as GPM
print('wrote', GPM.write(out['materials']))
out['colour_rule'] = LC.__doc__.strip()
with open(os.path.join(KIT, 'strings_all.json'), 'w', encoding='utf-8') as f:
    json.dump(out, f, ensure_ascii=False, indent=1)

with open(os.path.join(DOCS, 'build_report.txt'), 'w', encoding='utf-8') as f:
    f.write('Lanbai Fonts kit build report  %s\n\n' % out['generated'])
    f.write('== SUBSETS (original -> subset) ==\n' + '\n'.join(report) + '\n\n')
    tot_o = sum(v['original_bytes'] for v in subset_info.values())
    tot_s = sum(v['subset_bytes'] for v in subset_info.values())
    f.write('total %d B -> %d B (%.2f%%, saved %.1f MB)\n\n' % (tot_o, tot_s, 100.0 * tot_s / tot_o, (tot_o - tot_s) / 1e6))
    f.write('== COVERAGE ==\n' + '\n'.join(cov_lines) + '\n\n')
    f.write('== CHARSETS ==\n' + '\n'.join('%-30s %4d chars  %s' % (k, len(v), charset_files[k]) for k, v in charsets.items()) + '\n\n')
    f.write('== ATLAS ==\n' + '\n'.join(atlas_lines) + '\n\n')
    f.write('== LEADING ==\n' + '\n'.join(lead_lines) + '\n\n')
    f.write('== OPTICAL OFFSETS ==\n' + '\n'.join(opt_lines) + '\n\n')
    f.write('== COLOUR (screen target -> fill) ==\n' + '\n'.join(col_lines) + '\n\n')
    f.write('== TIMING (bible v2.1 §7.5) ==\n' + '\n'.join(time_lines) + '\n\n')
    f.write('== SCRIM GEOMETRY ==\n' + '\n'.join(scr_lines) + '\n\n')
    f.write('== VERTICAL PLACEMENT ==\n' + '\n'.join(vert_lines) + '\n\n')
    f.write('== VIEWCHECK (D-33 #5) ==\n' + '\n'.join(view_lines) + '\n\n')
    f.write('== SUBTITLES (v5, D-45) ==\n' + ('PASS' if sub_ok else 'FAIL') + ' — Docs~/subtitle_report.md\n' + depth_note + '\n' + '\n'.join(sub_extra) + '\n\n')
    f.write('== SEATS (D-37) ==\n' + '\n'.join(seat_lines) + '\n\n')
    f.write('== PLACEMENT (D-33) ==\n' + ('PASS' if not place_bad else '\n'.join('FAIL %s/%s: %s' % (r['poem'], r['player'], '; '.join(r['problems'])) for r in place_bad)) + '\n\n')
    f.write('== LINE WIDTHS ==\n' + '\n'.join(width_lines) + '\n\n')
    f.write('== BLOCKS (v4: width x height per poem and player) ==\n' + '\n'.join(
        '%-24s %-3s %-5s %4.2f°  %2d lines  %6.2f° x %5.2f°  az %s  el %s' % (r['poem'], r['player'], r['shown'], r['size_deg'], r['lines'],
                                                                         r['width_deg'], r['height_deg'], r['az'], r['el']) for r in block_rows) + '\n')
with open(os.path.join(DOCS, 'build_report.json'), 'w', encoding='utf-8') as f:
    json.dump(dict(subsets=subset_info, atlas=atlas_info, leading=lead_info, coverage_pass=ok_all, widest_line_deg=round(worst, 2),
                   vertical_pass=v_ok, vertical=v_rows, colour_pass=col_ok, scrim_geometry_pass=scr_ok,
                   colour={q['id']: dict(face=q['face_color'], scrim=q.get('scrim_fill')) for q in poems_out if 'face_color' in q},
                   subtitle_pass=bool(sub_ok),
                   colour_solver=SIMINFO, bible_crosscheck=dict(status=b_status, worst_codes=b_worst, rows=b_rows),
                   engine_crosscheck=dict(status=e_status, worst_codes=e_worst, rows=e_rows),
                   materials=list(materials.values())),
              f, ensure_ascii=False, indent=1)

print('\n'.join(report))
print('\n'.join(cov_lines[:20]))
print('\n'.join(atlas_lines))
print('\n'.join(lead_lines))
print(width_lines[1])
print('\n'.join(vert_lines[:3]))
print('\n'.join(opt_lines))
print('\n'.join(col_lines))
print('\n'.join(time_lines))
print('\n'.join(scr_lines))
print('\n'.join(view_lines))
print('\n'.join(seat_lines[:3]))
for r in sub_rows:
    if r[0] != 'ok':
        print('SUBTITLE', *r)
print('subtitles: %s (Docs~/subtitle_report.md)' % ('PASS' if sub_ok else 'FAIL'))
if place_bad or not view_ok or not sub_ok:
    sys.exit('BUILD FAILED: %d placement problem(s), viewcheck %s, subtitles %s (strings_all.json and the reports are written so you can look)' % (
        len(place_bad), 'PASS' if view_ok else 'FAIL: ' + ', '.join(view_fail), 'PASS' if sub_ok else 'FAIL'))
