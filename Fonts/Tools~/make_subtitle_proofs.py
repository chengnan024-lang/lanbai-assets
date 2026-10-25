# -*- coding: utf-8 -*-
"""Proof sheets for the v5 subtitles (D-45): every page of every poem, per player key, as the main seat sees it looking
ahead, plus the desktop framing with the letterbox (D-45 #15.3).

  python3 make_subtitle_proofs.py          (after build_fonts.py: reads strings_all.json v5)
  -> Docs~/SubProof_zh.png  SubProof_zht.png  SubProof_ja.png  SubProof_en.png  SubProof_de.png
     Docs~/SubProof_Desktop.png   Docs~/subtitle_proof_report.json

What is drawn (Art/字幕方案_D-45.md B–E): the subset fonts laid out the way TMP does (advance + kern table + tracking
+0.10 em CJK), em 1.8° at the last line's elevation E (-21°, Tianwen -9.4°), pitch 1.5 / 1.35 em, bottom-aligned, CJK
line-final ？！— hung by half an em; the line halo (#0E1A2F, Hann window, width + 1.2 em, 1.8 em tall, the poem's alpha)
and the underlay (black, alpha 0.5, dilate 0.15 em, soft 0.30 em) at each page's full alpha; the text at its SCREEN
target (#D0DBDF / #B3BCC0), blended in display space (what the solved fill shows after the grade; the build checks the
fill). Backgrounds: the v4 art sketches (make_proofs.bg_scene: palette values, not renders) with the dashboard band
the main seat sees below -16° (bus seats_occlusion grid) drawn as a dark plate (#0B0D11). Not renders, not Unity.
Desktop: 16:9, em = 4.2 % of the height, last baseline 8 % above the bottom, letterbox 2.39:1 with 45° corner cuts.
"""
import os, sys, json, math
import numpy as np
from PIL import Image, ImageDraw
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import lanbai_strings as L
import make_proofs as MP

DOCS = os.path.join(KIT, 'Docs~')
PPD = 14.0                      # px per degree on the sheets (the acceptance density is 20 px/°: see the crop row)
EL_TOP, EL_BOT = 16.0, -30.0
HALF_AZ = 26.0
DASH_EL = -16.0                 # the main seat looking ahead: opaque dashboard below -16° (D-45 B.4 #2)
DASH = '#0B0D11'
SUPER = 3                       # supersampling of the text masks
REPORT = {'pages': 0, 'missing': [], 'panels': []}


def J():
    with open(os.path.join(KIT, 'strings_all.json'), encoding='utf-8') as f:
        return json.load(f)


def line_mask(fk, text, em_px, track_em):
    """(mask float HxW in [0,1], baseline y, width px) for one line: glyph by glyph, TMP-style advances."""
    S = SUPER
    font = MP.pil_font(fk, int(round(em_px * S)))
    for ch in text:
        if not font.getmask(ch).size and ch not in ' 　':
            REPORT['missing'].append((fk, ch))
    adv = [font.getlength(ch) for ch in text]
    w = sum(adv) + track_em * em_px * S * max(0, len(text) - 1)
    asc, desc = font.getmetrics()
    W, H = int(w + 4 * S * em_px), int((asc + desc) + 2 * S * em_px)
    im = Image.new('L', (W, H), 0)
    d = ImageDraw.Draw(im)
    x = 2 * S * em_px
    base = S * em_px + asc
    for ch, a in zip(text, adv):
        d.text((x, base), ch, font=font, fill=255, anchor='ls')
        x += a + track_em * em_px * S
    m = np.asarray(im, np.float64) / 255.0
    m = m.reshape(H // S, S, W // S, S).mean(axis=(1, 3)) if H % S == 0 and W % S == 0 else \
        np.asarray(im.resize((W // S, H // S), Image.LANCZOS), np.float64) / 255.0
    return m, (S * em_px + asc) / S, w / S, 2 * em_px


def paste_mask(canvas_shape, m, x0, y0):
    out = np.zeros(canvas_shape)
    h, w = m.shape
    X0, Y0 = int(round(x0)), int(round(y0))
    xs, ys = max(0, X0), max(0, Y0)
    xe, ye = min(canvas_shape[1], X0 + w), min(canvas_shape[0], Y0 + h)
    if xe > xs and ye > ys:
        out[ys:ye, xs:xe] = m[ys - Y0:ye - Y0, xs - X0:xe - X0]
    return out


def halo_mask(shape, cx, cy, w_px, h_px):
    yy, xx = np.mgrid[0:shape[0], 0:shape[1]]
    v = np.clip((yy - cy) / h_px + 0.5, 0, 1)
    hann = np.sin(np.pi * v) ** 2
    u = np.abs(xx - cx) / (w_px / 2)
    ends = np.clip((1.15 - u) / 0.45, 0, 1)                      # long feathered ends, no straight edge
    ends = ends * ends * (3 - 2 * ends)
    return hann * ends


def over(img_s, mask, colour_hex, alpha):
    """display-space alpha-over (the proofs' model: the targets are screen colours)"""
    a = np.clip(mask * alpha, 0, 1)[..., None]
    return img_s * (1 - a) + a * MP.hx(colour_hex)


def draw_page(img_s, rig, rec, pg, cx, el_to_y, em_px, desktop=False):
    """draw one page (both lines at full alpha) onto a display-space float image"""
    fk = pg['font']
    cjk = L.FONTS[fk]['cjk']
    cls = 'cjk' if cjk else 'latin'
    pitch = rig['line_pitch_em'][cls]
    c = rig['em_centre_above_baseline_em'][cls]
    track = rig['tracking_em'][cls]
    lines = pg['lines']
    n = len(lines)
    base_el = rec['base_bottom_el']
    for i, ln in enumerate(lines):
        k_up = n - 1 - i                                       # 0 = the last line
        m, base_y_local, w_px, pad = line_mask(fk, ln, em_px, track)
        x_off = pg['x_em'][i] * em_px
        centre_y = el_to_y(base_el) - k_up * pitch * em_px      # the line's em centre
        base_y = centre_y + c * em_px
        x0 = cx - w_px / 2 + x_off - pad
        y0 = base_y - base_y_local
        mask = paste_mask(img_s.shape[:2], m, x0, y0)
        if rec['halo_alpha'] > 0:
            hm = halo_mask(img_s.shape[:2], cx + x_off, centre_y, w_px + rig['halo']['pad_w_em'] * em_px, rig['halo']['h_em'] * em_px)
            img_s = over(img_s, hm, rig['halo']['colour'], rec['halo_alpha'])
        u = rig['underlay']
        dil = ndi.maximum_filter(mask, size=max(1, int(round(u['dilate'] * em_px))))
        soft = ndi.gaussian_filter(dil, max(0.5, u['softness'] * em_px / 2))
        img_s = over(img_s, soft, '#000000', u['alpha'])
        img_s = over(img_s, mask, rec['target'], 1.0)
        REPORT['pages'] += 0
    return img_s


def scene_bg(scene, w, h, el_top, ppd, dash=True):
    lin, els = MP.bg_scene(MP.SCENE_BG.get(scene, scene), w, h, el_top, 1.0 / ppd, az_c=0.0)
    img = MP.l2s(lin)
    if dash:
        y0 = int((el_top - DASH_EL) * ppd)
        if 0 <= y0 < h:
            ramp = np.clip((np.arange(h) - y0) / (0.4 * ppd), 0, 1)[:, None, None]
            img = img * (1 - ramp) + ramp * MP.hx(DASH)
    return img


def caption(width, lines):
    return MP.caption_bar(width, lines)


def header(width, title, sub):
    rows = [(title, MP.capfont(30), (226, 230, 236), 46)] + [(t, MP.capfont(18), (150, 158, 170), 28) for t in sub]
    im = Image.new('RGB', (width, 60 + 60 * len(rows)), (12, 14, 18))
    d = ImageDraw.Draw(im)
    y = 20
    for t, f, c, lh in rows:
        y = MP.draw_wrapped(d, 24, y, t, f, c, width - 48, lh)
    return im.crop((0, 0, width, y + 12))


def panel(rig, rec, key, i, pg, pages):
    W = int(2 * HALF_AZ * PPD)
    H = int((EL_TOP - EL_BOT) * PPD)
    img = scene_bg(rec['scene'], W, H, EL_TOP, PPD)
    el_to_y = lambda el: (EL_TOP - el) * PPD
    em_px = rig['em_deg'] * PPD
    img = draw_page(img, rig, rec, pg, W / 2, el_to_y, em_px)
    # guides: E and the dashboard edge
    u8 = np.clip(np.round(img * 255), 0, 255).astype(np.uint8)
    out = Image.fromarray(u8)
    d = ImageDraw.Draw(out)
    for el, col, lab in ((DASH_EL, (90, 96, 110), '−16° 仪表台上沿'), (rec['base_bottom_el'], (70, 110, 150), 'E %+.1f°' % rec['base_bottom_el'])):
        y = el_to_y(el)
        d.line([(0, y), (14, y)], fill=col, width=1)
        d.text((18, y - 9), lab, font=MP.capfont(13), fill=col)
    t_next = pages[i + 1]['t'] if i + 1 < len(pages) else rec['t_end']
    ws = ' / '.join('%.1f°' % w for w in pg['width_deg'])
    cap = caption(W, ['%s · %s · 第 %d/%d 页 · %.2f → %.2f s（淡出 %.2f）' % (rec['poem'], key, i + 1, len(pages), pg['t'], pg['t_gone'], pg['t_out']),
                      '%s · %s · 行宽 %s · 晕 %.2f · %s %s' % (MP.FONT_CN.get(pg['font'], pg['font']), '两行' if len(pg['lines']) > 1 else '一行',
                                                       ws, rec['halo_alpha'], rec['tier'], rec['target'])])
    p = Image.new('RGB', (W, out.height + cap.height))
    p.paste(out, (0, 0))
    p.paste(cap, (0, out.height))
    REPORT['pages'] += 1
    return p


def empty_panel(rec, key, why):
    W = int(2 * HALF_AZ * PPD)
    H = int((EL_TOP - EL_BOT) * PPD)
    img = scene_bg(rec['scene'], W, H, EL_TOP, PPD)
    out = Image.fromarray(np.clip(np.round(img * 255), 0, 255).astype(np.uint8))
    cap = caption(W, ['%s · %s · 没有字幕' % (rec['poem'], key), why])
    p = Image.new('RGB', (W, out.height + cap.height))
    p.paste(out, (0, 0))
    p.paste(cap, (0, out.height))
    return p


def sheet(key):
    D = J()
    rig = D['subtitle_rig']
    panels = []
    for rec in D['subtitles']:
        pages = rec['keys'].get(key, [])
        if not pages:
            panels.append(empty_panel(rec, key, rec['empty_keys'].get(key, '')))
            continue
        for i, pg in enumerate(pages):
            panels.append(panel(rig, rec, key, i, pg, pages))
    cols = 3
    pw = max(p.width for p in panels)
    ph = max(p.height for p in panels)
    rows = (len(panels) + cols - 1) // cols
    head = header(cols * pw + (cols + 1) * 16, '蓝白 · 字幕校样（第 5 版，D-45）· 玩家键 %s' % key,
                     ['主座位往前看，方位 ±%.0f°、仰角 %+.0f°…%+.0f°，%.0f px/°。背景是 v4 的美术示意（色板值，不是渲染）加主座位看到的仪表台暗带（−16° 以下）。'
                     '字是屏幕目标色，暗晕、行晕按每首的值，字号 em %.1f°。不是 Unity 截图；验收在头显里。' % (HALF_AZ, EL_TOP, EL_BOT, PPD, rig['em_deg']),
                      '每页画的是全亮的一刻（淡入淡出不画）。行宽上限 25°；左边的细线标出仪表台上沿（−16°）和末行仰角 E。'])
    out = Image.new('RGB', (cols * pw + (cols + 1) * 16, head.height + rows * (ph + 16) + 16), (12, 14, 18))
    out.paste(head, (0, 0))
    for n, p in enumerate(panels):
        r, c = divmod(n, cols)
        out.paste(p, (16 + c * (pw + 16), head.height + 16 + r * (ph + 16)))
    path = os.path.join(DOCS, 'SubProof_%s.png' % key)
    out.save(path, optimize=True)
    REPORT['panels'].append({'key': key, 'panels': len(panels)})
    return path


def bar_frac(w, h, aspect, e):
    return max(0.0, 0.5 * (1 - (w / h) / aspect)) * e


def letterbox_mask(w, h, aspect, tan_c, corner_frac, e=1.0):
    """as Lanbai/Letterbox: bars of bar_frac x h, inner corners cut at 45°, corner_frac of the bar deep"""
    bar = bar_frac(w, h, aspect, e)
    yy, xx = np.mgrid[0:h, 0:w]
    y = (np.minimum(yy, h - 1 - yy) + 0.5) / h
    xs = (np.minimum(xx, w - 1 - xx) + 0.5) / h
    cut = np.maximum(0.0, corner_frac * bar - xs * tan_c)
    return (y < bar - cut).astype(np.float64)


def desktop():
    D = J()
    rig = D['subtitle_rig']
    lb = rig['letterbox']
    W, H = 1280, 720
    fov = rig['desktop']['fov_fallback_deg']
    ppd_v = H / fov
    el_top = fov / 2
    # (poem, key, label, slide e): e = 1 bars fully in, 0.5 half way through the 1.5 s slide, 0 no bars
    picks = [('P04a_Rilke', 'en', '3c 里尔克（黑边）', 1.0), ('P06_Dream_Dawn', 'zh', '6d 晨句（黑边）', 1.0),
             ('P09_Tianwen', 'en', '9a 天问（黑边，1018.11 前滑出）', 1.0), ('P09_Tianwen', 'ja', '9a 天问 滑出到一半（约 1017.4）', 0.5),
             ('P04a_Rilke', 'de', '3c 里尔克 滑入到一半（约 134.75）', 0.5), ('P07_HeBo', 'ja', '7b 河伯（没有黑边）', 0.0)]
    panels = []
    for pid, key, lab, e in picks:
        rec = next(r for r in D['subtitles'] if r['poem'] == pid)
        pg = rec['keys'][key][0]
        img = scene_bg(rec['scene'], W, H, el_top, ppd_v)
        em_px = rig['desktop']['em_frac_h'] * H
        cls = 'cjk' if L.FONTS[pg['font']]['cjk'] else 'latin'
        base_y = H - rig['desktop']['baseline_frac_h'] * H
        centre_y = base_y - rig['em_centre_above_baseline_em'][cls] * em_px
        if e > 0:                                               # the bars (Overlay+5) under the text (Overlay+10)
            m = letterbox_mask(W, H, lb['aspect'], math.tan(math.radians(lb['corner_deg'])), lb['corner_frac'], e)
            img = img * (1 - m[..., None])
            # as the driver: the block centred in the bottom bar, moving with the slide (smoothstep e already applied)
            bar_px = bar_frac(W, H, lb['aspect'], e) * H
            block_mid = 0.5 * rig['line_pitch_em'][cls] * em_px if len(pg['lines']) > 1 else 0.0
            y_bar = H - 0.5 * bar_px + block_mid
            centre_y = centre_y + (y_bar - centre_y) * e
        rec2 = dict(rec, base_bottom_el=0.0)
        img = draw_page(img, rig, rec2, pg, W / 2, lambda el: centre_y, em_px, desktop=True)
        u8 = np.clip(np.round(img * 255), 0, 255).astype(np.uint8)
        out = Image.fromarray(u8)
        cap = caption(W, ['桌面 16:9 · %s · %s · em = 屏高 %.1f%%，末行基线在底边上方 %.0f%%' % (lab, key, 100 * rig['desktop']['em_frac_h'], 100 * rig['desktop']['baseline_frac_h']),
                          '黑边 %.2f:1，内角 %.0f° 切角、深为黑边高度的 %.0f%%，%.1f 秒滑入滑出；字幕在黑边里竖直居中；时段 %s' % (
                              lb['aspect'], lb['corner_deg'], 100 * lb['corner_frac'], lb['slide_s'], '、'.join('%s %.1f–%.2f' % (s['id'], s['t0'], s['t1']) for s in lb['segments']))])
        p = Image.new('RGB', (W, out.height + cap.height))
        p.paste(out, (0, 0))
        p.paste(cap, (0, out.height))
        panels.append(p)
    head = header(2 * W + 48, '蓝白 · 字幕校样（第 5 版）· 桌面', ['字贴在屏幕下部（C.8）；黑边只在桌面、只在三段（D-45 #15.3），VR 里没有。黑边在的时候字幕整块放进下面那条黑边里、竖直居中，滑入滑出时跟着挪（D-45 #15 r2）。背景是示意，不是渲染。'])
    out = Image.new('RGB', (2 * W + 48, head.height + 3 * (panels[0].height + 16) + 16), (12, 14, 18))
    out.paste(head, (0, 0))
    for n, p in enumerate(panels):
        r, c = divmod(n, 2)
        out.paste(p, (16 + c * (W + 16), head.height + 16 + r * (p.height + 16)))
    path = os.path.join(DOCS, 'SubProof_Desktop.png')
    out.save(path, optimize=True)
    return path


if __name__ == '__main__':
    which = sys.argv[1:] or ['zh', 'zht', 'ja', 'en', 'de', 'desktop']
    made = [desktop() if w == 'desktop' else sheet(w) for w in which]
    REPORT['missing'] = sorted(set(REPORT['missing']))
    REPORT['verdict'] = 'PASS: no missing glyph' if not REPORT['missing'] else 'FAIL: missing glyphs'
    with open(os.path.join(DOCS, 'subtitle_proof_report.json'), 'w', encoding='utf-8') as f:
        json.dump(REPORT, f, ensure_ascii=False, indent=1)
    print('\n'.join(made))
    print(REPORT['verdict'], REPORT['pages'], 'pages')
