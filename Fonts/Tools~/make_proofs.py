# -*- coding: utf-8 -*-
"""Proof sheets for the Lanbai poems (v4 of this kit: D-30, one language per player; art bible v2.1).

Every line is drawn from lanbai_layout.py — the SAME objects, baselines, optical offsets and mirror transforms that
strings_all.json hands to the Director — using the SUBSET fonts the way TMP lays them out (advance + kern table +
tracking, no ligatures, no GPOS), at the bible's angular sizes (§7.3), colours / opacity / scrims (§7.2, §7.5),
blended in linear light (Unity Linear project).

  Docs~/Proof_zh.png  Proof_ja.png  Proof_en.png  Proof_de.png   what a player of that language sees, scene by scene
  Docs~/Proof_Trilingual_Zhuangzi.png   the key frame of the world (§6·8): full view + zh / ja / en + time strip
  Docs~/Proof_Credits.png                every credits / Coleridge string (glyph specimen for the TMP fallback path)
  Docs~/proof_report.json                glyphs drawn, missing glyphs (= tofu), purple share per panel (§1.3.4)

Backgrounds are ART SKETCHES from palette values, not renders. Scene 8 uses sky_dusk.py (no purple, §1.3.4 / §6·8);
6d is the calm sea mirror (physical Fresnel, n = 1.333) under the gold-lit cloud deck; 7c is the dark rose water above
the inverted Snell's window. Every panel also carries the Unity-model reading of the text (scene-linear alpha-over of
the solved fills, then the grade) and a bloom check (the bible's PPv2 bloom model on the text at 1080p / 90°).
"""
import os, sys, math, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy import ndimage as ndi

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.normpath(os.path.join(HERE, '..'))
sys.path.insert(0, HERE)
import lanbai_strings as L
import lanbai_layout as LY
import lanbai_color as LC
import sky_dusk as SKY

SUB = os.path.join(KIT, 'Subset')
ORIG = os.path.join(KIT, 'Originals~')
DOCS = os.path.join(KIT, 'Docs~')
os.makedirs(DOCS, exist_ok=True)

SS = 2                     # supersampling of the text masks
RNG = np.random.default_rng(7)
REPORT = {'glyphs_drawn': 0, 'missing': [], 'lines': [], 'purple': [], 'composite': []}

# ------------------------------------------------------------------------------------------- colour
def hx(h):
    h = h.lstrip('#')
    return np.array([int(h[i:i + 2], 16) / 255.0 for i in (0, 2, 4)])

def s2l(c):
    c = np.asarray(c, dtype=np.float64)
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)

def l2s(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)

def luma709(srgb):
    return float(np.dot(np.asarray(srgb) * 255, [0.2126, 0.7152, 0.0722]))

# ------------------------------------------------------------------------------------------- fonts
_pil = {}
def pil_font(fk, px):
    k = (fk, px)
    if k not in _pil:
        _pil[k] = ImageFont.truetype(os.path.join(SUB, L.FONTS[fk]['subset']), px, layout_engine=ImageFont.Layout.BASIC)
    return _pil[k]

CAP_SERIF = os.path.join(ORIG, 'SourceHanSerifCN-Regular.otf')     # captions of the sheets only (full font)
CAP_LATIN = os.path.join(ORIG, 'EBGaramond-Italic.ttf')
_capf = {}
def capfont(px, latin=False):
    k = (px, latin)
    if k not in _capf:
        _capf[k] = ImageFont.truetype(CAP_LATIN if latin else CAP_SERIF, px)
    return _capf[k]

# ----------------------------------------------------------------------------------- noise helpers
def fbm(h, w, scales, seed):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for s in scales:
        n = ndi.gaussian_filter(r.standard_normal((h, w)), s, mode='wrap')
        n /= n.std() + 1e-9
        acc += amp * n
        tot += amp
        amp *= 0.55
    return acc / tot

def fbm_aniso(h, w, scales, seed, aspect=3.0):
    r = np.random.default_rng(seed)
    acc = np.zeros((h, w))
    amp, tot = 1.0, 0.0
    for sc in scales:
        n = ndi.gaussian_filter(r.standard_normal((h, w)), (sc, sc * aspect), mode='wrap')
        n /= n.std() + 1e-9
        acc += amp * n
        tot += amp
        amp *= 0.5
    return acc / tot

def smooth(a, b, x):
    t = np.clip((x - a) / (b - a), 0, 1)
    return t * t * (3 - 2 * t)

def vgrad(h, w, el_top, deg_per_px, stops):
    els = el_top - (np.arange(h) + 0.5) * deg_per_px
    e = np.array([s[0] for s in stops], float)
    cols = np.array([s2l(hx(s[1])) for s in stops])
    out = np.stack([np.interp(els, e, cols[:, i]) for i in range(3)], -1)
    return np.repeat(out[:, None, :], w, 1), els

def add_glow_points(img, pts, color, radius_px, strength):
    h, w, _ = img.shape
    lay = np.zeros((h, w))
    for (x, y, a) in pts:
        xi, yi = int(x), int(y)
        if 0 <= xi < w and 0 <= yi < h:
            lay[yi, xi] += a
    core = ndi.gaussian_filter(lay, max(0.6, radius_px * 0.25))
    halo = ndi.gaussian_filter(lay, radius_px * 2.5)
    img += (core * strength * 18 + halo * strength * 60)[..., None] * s2l(hx(color))
    return img

def horizon_band(img, els, width_deg, hexc, strength):
    t = np.exp(-(els / width_deg) ** 2)
    img += (t * strength)[:, None, None] * s2l(hx(hexc))
    return img

# ----------------------------------------------------------------------------------- backgrounds
def bg_scene(scene, w, h, el_top, dpp, az_c=0.0, line_half=10.0):
    """Linear-light background sketch for a scene, from bible palette hexes. dpp = degrees per pixel."""
    if scene == '3':
        # lift-off: over the sea of lights (towns in clusters, warm haze thickening toward the horizon). Palette 03.
        img, els = vgrad(h, w, el_top, dpp, [(-40, '#05080F'), (-12, '#080D18'), (-3, '#0E1526'), (0, '#111B30'), (4, '#111B30'), (25, '#08101F'), (60, '#08101F')])
        clus = fbm_aniso(h, w, [55, 22, 9], 13, aspect=2.2)
        dens = smooth(0.1, 1.4, clus) * np.exp(np.clip(els, -60, 0) / 7.0)[:, None]
        pts = []
        cand = RNG.uniform(0, 1, (int(w * h * 0.03), 3))
        for u, v, r in cand:
            x, y = u * w, v * h
            if r < dens[int(y), int(x)] * 0.35:
                e = el_top - y * dpp
                pts.append((x, y, RNG.uniform(0.25, 1.0) * (0.55 + 0.45 * math.exp(e / 10.0))))
        img = add_glow_points(img, pts, '#E8A050', 0.9, 0.022)
        haze = ndi.gaussian_filter(dens, 18) * 0.9
        img += haze[..., None] * s2l(hx('#E8A050')) * 0.035
        img = horizon_band(img, els + 1.0, 3.0, '#E8A050', 0.020)
    elif scene == '4a':
        img, els = vgrad(h, w, el_top, dpp, [(-40, '#1E2233'), (-4, '#3B4157'), (0, '#484D63'), (3, '#40465B'), (14, '#23283A'), (40, '#070A14')])
        # colossus 1 rising behind the words (§6·4: 4° right of the poem centre); head clear, foot in the mist band
        xs = np.arange(w)[None, :]
        rise = np.clip(el_top - els, 0, None)[:, None]
        cx = w / 2 + 4.0 / dpp + (1.2 / dpp) * np.sin(rise / 9.0) + 0.02 * rise / dpp
        half = (0.55 + 0.045 * rise) / dpp
        m = smooth(1.0, -1.0, (np.abs(xs - cx) - half) / (0.35 / dpp))
        m *= smooth(-6, 1.5, els)[:, None] * 0.35 + 0.65
        body = s2l(hx('#0F1116'))
        img = img * (1 - m[..., None] * 0.9) + m[..., None] * 0.9 * body
        rim = m * smooth(0.0, 1.0, (cx - half * 0.55 - xs) / (0.25 / dpp))
        img += rim[..., None] * s2l(hx('#A9C2FF')) * 0.06
        mist = smooth(6, -4, els)[:, None]
        img = img * (1 - 0.35 * mist[..., None]) + 0.35 * mist[..., None] * s2l(hx('#484D63'))
    elif scene == '4b':
        img, els = vgrad(h, w, el_top, dpp, [(-40, '#262E45'), (-8, '#3A4460'), (0, '#495270'), (2, '#484D63'), (18, '#2A3041'), (40, '#070A14')])
        n = fbm_aniso(h, w, [40, 16, 6], 3, aspect=3.5)
        cl = smooth(-0.2, 1.3, n) * smooth(0.5, -2.0, els)[:, None]
        img = img * (1 - 0.30 * cl[..., None]) + 0.30 * cl[..., None] * s2l(hx('#5E6784'))
    elif scene == '6':
        # dawn, looking down (-12°) at sunlit cloud tops: peach-gold tops, blue-grey shadows (never lavender, §6·6)
        img, els = vgrad(h, w, el_top, dpp, [(-40, '#8593AA'), (-6, '#B4B8C2'), (-0.5, '#F2DCC8'), (0, '#D2BCAE'), (4, '#8C9AB8'), (20, '#3E64A6'), (60, '#3E64A6')])
        n = fbm_aniso(h, w, [70, 30, 12, 5], 11, aspect=2.4)
        tops = smooth(-0.9, 0.9, n)
        cloud = s2l(hx('#F6DCC4')) * tops[..., None] + s2l(hx('#8593AA')) * (1 - tops[..., None])
        sea = smooth(-1.25, -1.9, n)
        cloud = cloud * (1 - 0.45 * sea[..., None]) + 0.45 * sea[..., None] * s2l(hx('#1C3D63'))
        below = smooth(-0.3, -2.0, els)[:, None, None]
        img = img * (1 - 0.75 * below) + 0.75 * below * cloud
    elif scene == '6d':
        # §6·6 6d sea mirror, looking down (-12°, az -15°): the calm sea reflects what is above it at +|el| -- the
        # underside of the cloud deck, lit gold by the low sun from its far edge, and below the deck edge (~+8.5° at
        # az -15°) a strip of pale dawn sky (the 'cloud gap'). Water body = the far sea #1C3D63. Physical Fresnel.
        img, els = vgrad(h, w, el_top, dpp, [(-60, '#1C3D63'), (60, '#1C3D63')])
        e2 = np.clip(-els, 0.05, 89.0)                           # reflected elevation
        # gold = the yellow gold of the bible's dawn light (#E8B878 / #F2C79A family), never peach: mixed with the blue
        # water a peach turns mauve, a yellow gold turns a clean grey-green-blue (§6·6: 白上的藍与金, no lavender)
        refl_stops = [(0.0, '#F2E6CF'), (3.0, '#ECE0C8'), (7.6, '#E6D8BC'), (8.5, '#EECB8C'), (10.0, '#E0BE86'),
                      (14.0, '#B9B398'), (20.0, '#98A4AE'), (40.0, '#8593AA')]
        e = np.array([q[0] for q in refl_stops])
        cols = np.array([s2l(hx(q[1])) for q in refl_stops])
        refl = np.stack([np.interp(e2, e, cols[:, i]) for i in range(3)], -1)
        th = np.radians(90.0 - e2)                               # incidence angle
        n = 1.333
        ct = np.sqrt(np.clip(1 - (np.sin(th) / n) ** 2, 0, 1))
        rs = ((np.cos(th) - n * ct) / (np.cos(th) + n * ct)) ** 2
        rp = ((ct - n * np.cos(th)) / (ct + n * np.cos(th))) ** 2
        R = 0.5 * (rs + rp)
        water = s2l(hx('#1C3D63'))
        row = water[None, :] * (1 - R[:, None]) + refl * R[:, None]
        img = np.repeat(row[:, None, :], w, 1)
        # calm surface: long low swells stretch the reflection a little (no waves, §6·6 'only a little surface texture')
        sw = fbm_aniso(h, w, [6, 2.5], 61, aspect=9.0)
        img *= (1 + 0.035 * sw)[..., None]
        above = smooth(-0.4, 0.4, els)[:, None, None]             # (horizon never in this panel; kept for safety)
        img = img * (1 - above) + above * s2l(hx('#E6D3BF'))
    elif scene == '7c':
        # §6·7c at 903.0: dark rose water (fog #2E2228 -> #3A2629), the inverted Snell's window far below (edge at
        # -41.5°); outside it total internal reflection mirrors the dark water and the palace lamps, now steady points.
        img, els = vgrad(h, w, el_top, dpp, [(-60, '#3A2A2D'), (-25, '#33252A'), (-8, '#2E2228'), (10, '#2A2026'), (40, '#241C22')])
        win = smooth(-30.0, -41.5, els)[:, None]
        img = img * (1 - 0.6 * win[..., None]) + 0.6 * win[..., None] * s2l(hx('#B0705A'))
        pts = []
        for _ in range(26):
            y = RNG.uniform(0, h)
            e_ = el_top - y * dpp
            if e_ > -3.0:
                continue
            pts.append((RNG.uniform(0, w), y, RNG.uniform(0.25, 0.8) * min(1.0, (-e_) / 12.0)))
        img = add_glow_points(img, pts, '#FFC46A', 1.0, 0.012)
        n = fbm(h, w, [60, 20], 23)
        img *= (1 + 0.05 * n)[..., None]
    elif scene == '7':
        # §6·7b v2.1 at 714.0: the lit, empty gate is LEFT of the words (az -7°), on the axis of the hall whose dark
        # front fills the left of the frame; the words float over the abyss-side dark water to the right. The gate is
        # 'a lit vertical opening seen from outside in the dark, its light laid on a wet surface in front' (§6·7b).
        img, els = vgrad(h, w, el_top, dpp, [(-40, '#02070F'), (-10, '#040E1C'), (0, '#061A30'), (12, '#0A2440'), (40, '#061A30')])
        az = (az_c - w * dpp / 2) + (np.arange(w) + 0.5) * dpp
        AZ, EL = np.meshgrid(az, els)
        G = -7.0
        eave = 7.2 + 0.9 * smooth(-6.0, -1.2, AZ) * smooth(-1.0, -1.6, AZ)     # the eave lifts at the corner (az ~ -1.5°)
        front = smooth(-0.6, -2.2, AZ) * smooth(0.25, -0.25, EL - eave) * smooth(-7.5, -6.5, EL)
        roof = smooth(-0.6, -2.6, AZ) * smooth(-0.2, 0.2, EL - eave) * smooth(0.3, -0.3, EL - (eave + 3.2 + 0.08 * (AZ - G)))
        img = img * (1 - 0.8 * front[..., None]) + 0.8 * front[..., None] * s2l(hx('#03070D'))
        img = img * (1 - 0.7 * roof[..., None]) + 0.7 * roof[..., None] * s2l(hx('#020509'))
        for k in range(-6, 3):                                            # pillars, faintly vermilion near the gate
            pa = G + k * 3.0
            col = np.exp(-((AZ - pa) / 0.32) ** 2) * front * np.exp(-((pa - G) / 7.0) ** 2)
            img = img + col[..., None] * s2l(hx('#4A140D')) * 0.12
        door = smooth(0.25, -0.15, np.abs(AZ - G) - 1.15) * smooth(0.15, -0.15, EL - 2.4) * smooth(-5.2, -4.8, EL)
        grad = 0.30 + 0.25 * smooth(2.4, -5.0, EL)
        img = img * (1 - door[..., None]) + door[..., None] * s2l(hx('#FFC46A')) * grad[..., None]
        glow = np.exp(-((AZ - G) / 2.2) ** 2) * np.exp(-((EL + 1.2) / 3.4) ** 2) * (1 - door)
        img = img + glow[..., None] * s2l(hx('#B5772E')) * 0.05
        spill = np.exp(-((AZ - G) / (1.3 + 0.25 * np.clip(-EL - 5.0, 0, None))) ** 2) * smooth(-5.0, -5.6, EL) * np.exp(np.clip(EL + 5.0, None, 0) / 4.0)
        img = img + spill[..., None] * s2l(hx('#FFB25C')) * 0.12
        pts = []
        for k in range(1, 10):
            for side in (-1, 1):
                a_ = G + side * (1.6 + 7.5 / k)
                e_ = -5.2 - 7.0 / k
                pts.append(((a_ - (az_c - w * dpp / 2)) / dpp, (el_top - e_) / dpp, 1.25 / (0.7 + 0.2 * k)))
        img = add_glow_points(img, pts, '#B52A1E', 4.0, 0.016)
        img = add_glow_points(img, pts, '#FFC46A', 0.9, 0.028)
        n = fbm(h, w, [70, 25], 5)
        img += np.clip(n, 0, None)[..., None] * 0.010 * s2l(hx('#26496C'))
    elif scene in ('8', '8-ii'):
        # §6·8 with the v2 colour law: amber -> sand -> warm grey -> indigo-grey; no rose on the sun side; no purple
        dpp_ = dpp
        img, az, el = SKY.dusk_view(w, h, az_c - w * dpp_ / 2, el_top, dpp_, mode='8-i' if scene == '8' else '8-ii',
                                    line_half=line_half)
        els = el[:, 0]
    elif scene == '9a':
        img, els = vgrad(h, w, el_top, dpp, [(-40, '#04060E'), (0, '#04060E'), (40, '#04060E')])
    elif scene == '11':
        # false awakening: the sea hangs overhead just above the words; sodium glints; lamp heads hang from it
        img, els = vgrad(h, w, el_top, dpp, [(-30, '#05080F'), (4, '#07090F'), (12.0, '#0A1020'), (13.0, '#0F2438'), (40, '#0F2438')])
        n = fbm_aniso(h, w, [3, 1.5], 41, aspect=4.0)
        gl = smooth(2.2, 3.2, n) * smooth(12.8, 14.0, els)[:, None]
        img += gl[..., None] * s2l(hx('#D08A59')) * 0.45
        pts = [(w / 2 + k * 11 / dpp, (el_top - 12.4) / dpp, 1.0) for k in (-3, -2, -1, 1, 2, 3)]
        img = add_glow_points(img, pts, '#F2B070', 1.2, 0.010)
    elif scene == '12':
        img, els = vgrad(h, w, el_top, dpp, [(-40, '#04060B'), (-1, '#070B12'), (0, '#1B2431'), (2.5, '#101722'), (12, '#070B14'), (60, '#070B14')])
        pts = []
        for _ in range(46):
            y = RNG.uniform(0, h)
            if el_top - y * dpp > -1.5:
                continue
            pts.append((RNG.uniform(0, w), y, RNG.uniform(0.3, 1.0)))
        img = add_glow_points(img, pts, '#DEEA88', 1.6, 0.012)
    else:
        img, els = vgrad(h, w, el_top, dpp, [(-90, '#101010'), (90, '#101010')])
    return img, els

# ----------------------------------------------------------------------------------- compositing
def rounded_mask(shape, boxes):
    h, w = shape
    m = np.zeros((h, w))
    yy, xx = np.mgrid[0:h, 0:w]
    for x0, y0, x1, y1 in boxes:
        r = min((y1 - y0) / 2, (x1 - x0) / 2)
        cx = np.clip(xx, x0 + r, x1 - r)
        cy = np.clip(yy, y0 + r, y1 - r)
        m = np.maximum(m, (((xx - cx) ** 2 + (yy - cy) ** 2) <= r * r).astype(float))
    return m

def scrim(img, boxes, kind, ppd):
    """bible §7.2: one soft local scrim, 40 px feather at 1080p/90° (= 1.9°), scaled to this proof's px per degree."""
    col, alpha = {'dark': L.SCRIM_DARK, 'light': L.SCRIM_LIGHT}[kind]
    m = rounded_mask(img.shape[:2], boxes)
    m = ndi.gaussian_filter(m, 40.0 / (1920 / 90.0) * ppd / 2.0)
    a = (m * alpha)[..., None]
    return img * (1 - a) + a * s2l(hx(col))

def composite_mask(img, mask_arr, color, opacity):
    m = np.asarray(mask_arr, dtype=np.float64) / 255.0
    if SS > 1:
        m = m.reshape(m.shape[0] // SS, SS, m.shape[1] // SS, SS).mean(axis=(1, 3))
    a = (m * opacity)[..., None]
    return img * (1 - a) + a * s2l(hx(color))

def to_u8(lin):
    s = l2s(lin) * 255.0
    s += RNG.uniform(-0.5, 0.5, s.shape)                       # dither: no banding in the dark skies
    return np.clip(np.round(s), 0, 255).astype(np.uint8)

def ruler28(img, ppd, y_px, cx):
    """faint 28° bracket centred on the text axis (bible §7.3 line-length limit)"""
    x0, x1 = int(cx - 14 * ppd), int(cx + 14 * ppd)
    y = int(y_px)
    c = np.array([1.0, 1.0, 1.0]) * 0.5
    a = 0.22
    img[y:y + 2, x0:x1] = img[y:y + 2, x0:x1] * (1 - a) + a * c
    for x in (x0, x1 - 2):
        img[y - 8:y + 10, x:x + 2] = img[y - 8:y + 10, x:x + 2] * (1 - a) + a * c
    return img

# ------------------------------------------------------------------------------------ text drawing
def draw_object(mask, o, cx_px, el_top, ppd, upright_equivalent=False):
    """Draw one layout object into an 'L' mask (supersampled). Mirror objects (scale_y -1) are drawn at their
    UPRIGHT-equivalent position when upright_equivalent is True (the caller flips the mask about the horizon).
    Returns the widest line in degrees."""
    m = LY.Metrics(o['font'])
    px = int(round(o['size_deg'] * ppd * SS))
    pf = pil_font(o['font'], px)
    d = ImageDraw.Draw(mask)
    bls = o['line_baselines_el']
    if o['scale_y'] == -1 and upright_equivalent:
        bls = [-b for b in bls]
    widest = 0.0
    for text, bl, off in zip(o['lines'], bls, o['optical_offsets_em']):
        ln = m.line(text)
        x0 = cx_px * SS + (off - ln['width'] / 2.0) * px
        y = (el_top - bl) * ppd * SS
        for ch, x, adv, ib, g in ln['pens']:
            if g is None:                               # tofu marker: impossible to miss
                REPORT['missing'].append((o['font'], ch, text))
                d.rectangle([x0 + x * px + px * 0.1, y - px * 0.8, x0 + x * px + px * 0.9, y], outline=255, width=max(2, px // 12))
                continue
            if ib is None:
                continue
            d.text((round(x0 + x * px), round(y)), ch, font=pf, fill=255, anchor='ls')
            REPORT['glyphs_drawn'] += 1
        wdeg = ln['width'] * o['size_deg']
        widest = max(widest, wdeg)
        REPORT['lines'].append({'font': o['font'], 'text': text, 'em_deg': o['size_deg'], 'width_deg': round(wdeg, 2)})
    return widest

def obj_box_px(o, cx_px, el_top, ppd, pad_em=0.0):
    """box of an object in final px (from its em extents and widest line)."""
    m = LY.Metrics(o['font'])
    wdeg = max(m.line(t)['width'] for t in o['lines']) * o['size_deg']
    pad = pad_em * o['size_deg']
    x0 = cx_px - (wdeg / 2 + pad) * ppd
    x1 = cx_px + (wdeg / 2 + pad) * ppd
    y0 = (el_top - o['top_el'] - pad * 0.7) * ppd
    y1 = (el_top - o['bottom_el'] + pad * 0.7) * ppd
    return (x0, y0, x1, y1)

def ease_out(x):
    x = min(max(x, 0.0), 1.0)
    return 1 - (1 - x) ** 3

def obj_state(o, t):
    """(alpha multiplier, softness, drift in degrees) of an object at time t (s after its poem's first appearance):
    §7.4-4 focus-in 2.5 s ease-out, _OutlineSoftness 0.9 -> final (0; mirror 0.3); captions fade when replaced;
    the Zhuangzi exit (exit_at_s, exit_s): alpha -> 0 and a 0.2° drift up / down (the 'exit' field)."""
    final = o.get('outline_softness', 0.0)
    if t is None:
        return 1.0, final, 0.0
    k = ease_out((t - o.get('appear_s', 0.0)) / 2.5)
    a = k
    soft = final + (0.9 - final) * (1 - k)
    if o['role'] == 'caption' and 'fade_out_at_s' in o and t > o['fade_out_at_s']:
        a *= max(0.0, 1 - (t - o['fade_out_at_s']) / o.get('fade_out_s', 1.0))
    drift = 0.0
    if o.get('exit_at_s') is not None and t > o['exit_at_s']:
        x = min(1.0, (t - o['exit_at_s']) / o.get('exit_s', 3.0))
        a *= 1 - x
        drift = 0.2 * x * (1 if str(o.get('exit', '')).startswith('up') else -1)
    return a, soft, drift

def draw_scrims(img, scrims, objects, cx_px, el_top, ppd, t=None):
    """composite each scrim quad (alpha-over, in order), with the exact texture profile of lanbai_layout."""
    h, w, _ = img.shape
    ys = el_top - (np.arange(h) + 0.5) / ppd
    xs = (np.arange(w) + 0.5 - cx_px) / ppd
    byid = {o.get('id', o['role']): o for o in objects}
    for sc in scrims:
        o = byid.get(sc['for_object'])
        k = obj_state(o, t)[0] if o is not None else (1.0 if t is None else ease_out((t - sc['appear_s']) / 2.5))
        dy = obj_state(o, t)[2] if o is not None else 0.0
        if k <= 0.01:
            continue
        u = xs / sc['width_deg'] + 0.5
        v = (sc['center_el'] + dy - ys) / sc['height_deg'] + 0.5
        inside_u = (u >= 0) & (u <= 1)
        inside_v = (v >= 0) & (v <= 1)
        a = LY.scrim_alpha(np.clip(u, 0, 1)[None, :], np.clip(v, 0, 1)[:, None], sc['style'])
        a = a * inside_u[None, :] * inside_v[:, None] * sc['alpha'] * k
        img = img * (1 - a[..., None]) + a[..., None] * s2l(hx(sc['color_target']))
    return img

def render_objects(img, objects, cx_px, el_top, ppd, color, opacity, scrims=None, t=None, horizon_row=None):
    """Composite a list of layout objects (after their scrims). Mirror objects are rendered by flipping the
    upright-equivalent mask about the horizon row (exact reflection), softened (softness 0.3), at their own alpha."""
    h, w, _ = img.shape
    widest = 0.0
    if scrims:
        img = draw_scrims(img, scrims, objects, cx_px, el_top, ppd, t)
    for o in objects:
        a, soft, drift = obj_state(o, t)
        if a <= 0.01:
            continue
        mask = Image.new('L', (w * SS, h * SS), 0)
        mirror = o['scale_y'] == -1
        widest = max(widest, draw_object(mask, o, cx_px, el_top, ppd, upright_equivalent=mirror))
        arr = np.asarray(mask, dtype=np.float64)
        if mirror:
            yh = (horizon_row if horizon_row is not None else el_top * ppd) * SS
            ys = np.clip(np.round(2 * yh - 1 - np.arange(arr.shape[0])).astype(int), 0, arr.shape[0] - 1)
            arr = arr[ys]
        if drift:
            arr = ndi.shift(arr, (-drift * ppd * SS, 0), order=1, mode='constant')
        s_em = soft
        if s_em > 0:
            arr = ndi.gaussian_filter(arr, 0.12 * s_em * o['size_deg'] * ppd * SS)
        op = o.get('alpha', opacity) * a
        img = composite_mask(img, np.clip(arr, 0, 255), color, op)
    return img, widest

def elevation_scale(im, ppd, el_top, x_left=True, labels=True):
    """ticks every 5° at the frame edge; the §7.3 limits (+10°, -15°) as faint dashes across."""
    d = ImageDraw.Draw(im, 'RGBA')
    W, H = im.size
    f = capfont(16)
    for e in range(-30, 31, 5):
        y = (el_top - e) * ppd
        if y < 0 or y >= H:
            continue
        lim = e in (10, -15)
        L0 = 18 if e % 10 == 0 or lim else 10
        col = (255, 226, 176) if e == 0 else ((255, 255, 255) if lim else (230, 234, 240))
        for x0 in (0, W - L0):
            d.line([(x0, y), (x0 + L0, y)], fill=col, width=2)
        if lim:
            for x in list(range(20, int(W * 0.12), 26)) + list(range(int(W * 0.88), W - 20, 26)):
                d.line([(x, y), (x + 9, y)], fill=(255, 255, 255), width=1)
        if labels and (e % 10 == 0 or lim):
            t = ('%+d°' % e) if e else '0° 地平线'
            if lim:
                t += '  §7.3 限'
            bb = d.textbbox((24, y - 24), t, font=f)
            d.rounded_rectangle([bb[0] - 5, bb[1] - 3, bb[2] + 5, bb[3] + 3], radius=4, fill=(14, 16, 22, 150))
            d.text((24, y - 24), t, font=f, fill=col)
    return im


def purple_of(u8, scene):
    if scene.startswith('6'):
        v = SKY.purple_fraction(u8, 285, 330, 12)
        lim = 'h285–330 C*>12'
    else:
        v = SKY.purple_fraction(u8)
        lim = 'h290–325 C*>15'
    return v, lim

# ----------------------------------------------------------------------------------- captions
def wrap_text(text, font, max_w):
    """greedy wrap that breaks after spaces / CJK punctuation, or anywhere in CJK runs."""
    out, cur = [], ''
    for ch in text:
        if font.getlength(cur + ch) <= max_w:
            cur += ch
            continue
        cut = max(cur.rfind(' '), cur.rfind('，'), cur.rfind('；'), cur.rfind('·'), cur.rfind('、'), cur.rfind('：'))
        if cut > len(cur) * 0.6:
            out.append(cur[:cut + 1].rstrip())
            cur = cur[cut + 1:].lstrip() + ch
        else:
            out.append(cur)
            cur = ch
    if cur:
        out.append(cur)
    return out

def draw_wrapped(d, x, y, text, font, fill, max_w, lh):
    for ln in wrap_text(text, font, max_w):
        d.text((x, y), ln, font=font, fill=fill)
        y += lh
    return y

def caption_bar(width, lines):
    rows = []
    for i, t in enumerate(lines):
        f = capfont(22 if i == 0 else 19)
        for ln in wrap_text(t, f, width - 48):
            rows.append((ln, f, (214, 218, 224) if i == 0 else (150, 158, 170)))
    im = Image.new('RGB', (width, 26 + 30 * len(rows)), (18, 20, 26))
    d = ImageDraw.Draw(im)
    y = 12
    for ln, f, col in rows:
        d.text((24, y), ln, font=f, fill=col)
        y += 30
    return im

FONT_CN = {'SourceHanSerifSC-Regular': '思源宋体 SC Regular', 'SourceHanSerifSC-Medium': '思源宋体 SC Medium',
           'SourceHanSerifJP-Medium': '源ノ明朝 JP Medium', 'SourceHanSerifJP-Regular': '源ノ明朝 JP Regular', 'SourceHanSerifTW-Regular': '思源宋体 TC Regular', 'EBGaramond-Regular': 'EB Garamond Regular',
           'EBGaramond-Italic': 'EB Garamond Italic'}

def fmt_place(pl):
    a, e, d = pl
    return '%+g° / %+g° / %g m' % (a, e, d)

SCENE_BG = {'3': '3', '3c': '4a', '4': '4b', '6d': '6d', '7b': '7', '7c': '7c', '8-ii': '8-ii', '9a': '9a', '11': '11', '12': '12'}

# ----------------------------------------------------------------------------------- colour (verify r2 B.1)
def colour_line(p):
    """caption text: screen target, opacity, the fill the material carries, and the grade it was solved under."""
    fr = LC.poem_fill_record(p)
    g = fr['grade'].replace('→', ' → ').replace('@', ' @ w ')
    t = '屏幕目标 %s，不透明度 %d%%%s → %s 下 _FaceColor 填 %s（Vertex Color 白，只带 alpha）' % (
        fr['target'], round(p['opacity'] * 100), '（偏离 §7.2 的 90%，见 README §4.1）' if p['opacity'] == 1.0 else '',
        g, fr['fill_hdr'])
    if p.get('scrim'):
        col, a = L.SCRIM_DARK if p['scrim'] == 'dark' else L.SCRIM_LIGHT
        sf = LC.fill_record(col, LC.SCRIM_GRADE[p['scrim']], a)
        t += ' + %s %s α%.2f（_Color 填 %s，SpriteRenderer α %.3f）' % ('暗衬' if p['scrim'] == 'dark' else '亮衬', col, a, sf['fill_hdr'],
                                                                   LY.unity_alpha(p['scrim'])['alpha_unity'])
    elif p['id'] == 'P08a_Dream_Dusk':
        t += '；不加暗衬（§7.5 #6：写在暗水上）'
    return t


def timing_line(p):
    if p.get('mirror'):
        return 'L1 %.1f · L3 %.1f（%s）→ 一起保持到 %.1f → %.1f 退场完' % (
            p['t_appear'], float(p['segments'][1]['t']), p['cue'], p['t_appear'] + p['hold_s'], p['t_gone'])
    if p.get('hold_s') is None:
        return '出现 %.2f（%s，逐词与歌声同步）→ 约 %.1f 淡尽' % (p['t_appear'], p['cue'], p['t_gone'])
    return '出现 %.2f（%s）· 停留 %.1f s → %.2f → %.2f 退场完' % (p['t_appear'], p['cue'], p['hold_s'], p['t_exit'], p['t_gone'])


def unity_check(p, bg, objs, cx_px, el_top, ppd, label):
    """mean background under the text (display-linear, before scrims) -> LC.composite_check: what Unity shows
    (scene-linear alpha-over of the solved fills, then the grade) vs what this proof draws (display-linear mix)."""
    h, w, _ = bg.shape
    m = np.zeros((h, w), bool)
    for o in objs:
        x0, y0, x1, y1 = obj_box_px(o, cx_px, el_top, ppd)     # top_el / bottom_el of a mirror are already its own
        m[max(0, int(y0)):min(h, int(y1)), max(0, int(x0)):min(w, int(x1))] = True
    mean = bg[m].mean(axis=0) if m.any() else bg.reshape(-1, 3).mean(axis=0)
    bg_hex = '#%02X%02X%02X' % tuple(int(round(v * 255)) for v in l2s(mean))
    scr = None
    if p.get('scrim'):
        col, a_b = L.SCRIM_DARK if p['scrim'] == 'dark' else L.SCRIM_LIGHT
        scr = (col, a_b, LY.unity_alpha(p['scrim'])['alpha_unity'])
    spec = LC.poem_solve_spec(p)
    fr = LC.poem_fill_record(p)
    r = LC.composite_check(spec, bg_hex, p['color_target'], p['opacity'], scr, text_fill=fr['fill_linear'])
    r['panel'] = label
    r['poem'] = p['id']
    r['bloom'] = bloom_check(p, objs, spec, bg_hex, scr, fr['fill_linear'])
    REPORT['composite'].append(r)
    return r


def bloom_check(p, objs, spec, bg_hex, scr, fill):
    """The text's OWN bloom halo under the live grade, with the bible's PPv2 bloom model (lutlib_core.bloom_layer:
    quadratic threshold, clamp, pyramid depth for a 1920-px frame) at 1080p / 90° (21.3 px per degree), prefilter at
    half resolution as PPv2 does. Background = the mean under the text (uniform, below threshold). Returns the largest
    code the halo adds outside the glyphs and on them."""
    SIM = LC.SIM
    P = LC.params(spec)
    ppd_f = 1920.0 / 90.0
    ups = [o for o in objs if o['scale_y'] == 1]
    if not ups:
        return None
    top = max(o['top_el'] for o in ups) + 8.0
    bot = min(o['bottom_el'] for o in ups) - 8.0
    wdeg = max(max(LY.Metrics(o['font']).line(t)['width'] for t in o['lines']) * o['size_deg'] for o in ups) + 16.0
    H, W = int((top - bot) * ppd_f) // 2 * 2, int(wdeg * ppd_f) // 2 * 2
    mask = Image.new('L', (W * SS, H * SS), 0)
    for o in ups:
        draw_object(mask, o, W / 2, top, ppd_f)
    c = np.asarray(mask, np.float64) / 255.0
    c = c.reshape(H, SS, W, SS).mean(axis=(1, 3))
    bg_s, _ = LC.solve(bg_hex, spec)
    under = bg_s.copy()
    if scr:
        sc_s, _ = LC.solve(scr[0], spec)
        under = under * (1 - scr[2]) + sc_s * scr[2]
    a = (c * p['opacity'])[..., None]
    x = under[None, None, :] * (1 - a) + np.asarray(fill)[None, None, :] * a
    xh = x.reshape(H // 2, 2, W // 2, 2, 3).mean(axis=(1, 3))          # PPv2 prefilter runs at half resolution
    b = P['bloom']
    if b['intensity'] <= 0:
        return dict(halo_max_codes=0, on_text_max_codes=0)
    xc = np.minimum(xh, 24.0)
    thr = SIM.g2l(b['threshold'])
    knee = thr * b['softKnee'] + 1e-5
    br = xc.max(-1)
    rq = np.clip(br - (thr - knee), 0, 2 * knee)
    rq = (0.25 / knee) * rq * rq
    pre = xc * (np.maximum(rq, br - thr) / np.maximum(br, 1e-5))[..., None]
    if pre.max() <= 0:
        return dict(halo_max_codes=0, on_text_max_codes=0, prefilter_max=0.0)
    n = int(np.clip(np.floor(np.log2(1920 / 2) + min(b['diffusion'], 10) - 10), 1, 16))
    pad = int(3 * 2 ** n * 0.9 * 0.5) + 8
    big = np.pad(pre, ((pad, pad), (pad, pad), (0, 0)))
    F = np.fft.rfft2(big, axes=(0, 1))
    acc = np.zeros_like(big)
    for i in range(n):
        sg = 2.0 ** (i + 1) * 0.9 * 0.5                               # sigma in half-res px of a 1920-px frame
        acc += np.fft.irfft2(_fourier_gauss(F, sg, big.shape), s=big.shape[:2], axes=(0, 1))
    acc = acc[pad:-pad, pad:-pad]
    bl = acc * (2 ** (b['intensity'] / 10) - 1) * SIM.ppv2.hex_to_lin(b['color'])
    bl = np.repeat(np.repeat(bl, 2, 0), 2, 1)
    pe = 2.0 ** SIM.ppv2.full(P)['postExposure']
    d0 = SIM.ppv2.lin_to_srgb(SIM.ppv2.grade_lut(x * pe, SIM.ppv2.full(P)))
    d1 = SIM.ppv2.lin_to_srgb(SIM.ppv2.grade_lut((x + bl) * pe, SIM.ppv2.full(P)))
    dd = (d1 - d0).max(-1) * 255
    off = ndi.binary_dilation(c > 0.02, iterations=3)
    return dict(halo_max_codes=round(float(dd[~off].max()), 2), on_text_max_codes=round(float(dd[off].max()), 2),
                prefilter_max=round(float(pre.max()), 5))


def _fourier_gauss(F, sg, shape):
    """Gaussian blur in the frequency domain (rfft2 over axes 0, 1)."""
    ky = np.fft.fftfreq(shape[0])[:, None]
    kx = np.fft.rfftfreq(shape[1])[None, :]
    g = np.exp(-2 * (np.pi * sg) ** 2 * (kx ** 2 + ky ** 2))
    return F * g[..., None]


def check_text(r):
    t = 'Unity 模型（场景线性混合 → 调色）：字心 %s（luma %.0f，目标 luma %.0f，差 %d 码；本图画的是 %s）' % (
        r['text_unity'], r['text_luma_unity'], r['target_luma'], r['text_vs_target_codes'], r['text_proof'])
    if r['scrim']:
        t += '，衬底处 %s（本图 %s）' % (r['under_text_unity'], r['under_text_proof'])
    bm = r.get('bloom')
    if bm:
        t += '；bloom：字的光晕 ≤ %.1f 码' % bm['halo_max_codes']
    return t

# ----------------------------------------------------------------------------------- panels
def block_panel(p, player, ppd, width, lay, label_extra=''):
    objs = lay['objects']
    top = max(o['top_el'] for o in objs)
    bot = min(o['bottom_el'] for o in objs)
    ext = top - bot
    ph = int(max(15.0, ext + 7.0) * ppd)
    el_top = (top + bot) / 2 + ph / 2 / ppd
    scene = SCENE_BG[p['scene']]
    img, els = bg_scene(scene, width, ph, el_top, 1.0 / ppd, az_c=p['place'][0])
    chk = unity_check(p, img, objs, width / 2, el_top, ppd, '%s/%s' % (p['id'], player))
    img, widest = render_objects(img, objs, width / 2, el_top, ppd, p['color_target'], p['opacity'], lay.get('scrims'))
    img = ruler28(img, ppd, ph - 0.9 * ppd, width / 2)
    u8 = to_u8(img)
    pv, plim = purple_of(u8, p['scene'])
    REPORT['purple'].append({'panel': '%s/%s' % (p['id'], player), 'purple_share': round(pv, 4),
                             'rule': plim, 'limit': 'n/a (scene 4)' if p['scene'] == '4' else 0.02})
    out = Image.fromarray(u8)
    tr = lay['translation']
    m0 = objs[0]
    shown_txt = ('原文' if lay['shown'] == 'main' else {'zh': '中译', 'zht': '繁体', 'ja': '日文（書き下し / 和訳）', 'en': '英译'}[lay['shown']])
    tr_txt = ('+ 下面一行 ' + FONT_CN[p['translations'][tr]['font']] + ' %.1f°（天问的例外，D-30 #4）' % p['size_tr']) if tr else '（只这一份，D-30）'
    cents = '  '.join('%s %+.1f°' % ({'main': '字块', 'translation': '小字'}[o['role']], o['center_el']) for o in objs)
    blk = lay['block']
    offs = [(t, x) for o in objs for t, x in zip(o['lines'], o['optical_offsets_em']) if x]
    cap = caption_bar(width, [
        '第 %s 幕 · %s%s   ·   %s' % (p['scene'], p['source'], label_extra, timing_line(p)),
        '%s · %s %.2f°  %s   ·   %s   ·   最宽行 %.1f°   ·   字块 %.1f° × %.1f°' % (
            shown_txt, FONT_CN[m0['font']], m0['size_deg'], tr_txt, fmt_place(p['place']), widest, blk['width_deg'], blk['height_deg']),
        colour_line(p),
        check_text(chk),
        '物体中心仰角：%s%s   ·   紫 %.1f%%%s' % (
            cents, ('（整块上下移 %+.2f°，保 §7.3 范围）' % lay['shift_deg']) if lay['shift_deg'] else '',
            100 * pv, '' if p['scene'] != '4' else '（第 4 幕：裂口的紫允许）') +
        (('   ·   光学居中：' + '，'.join('「%s」%+.2f em' % (t[-3:], x) for t, x in offs)) if offs else ''),
    ])
    panel = Image.new('RGB', (width, out.height + cap.height))
    panel.paste(out, (0, 0))
    panel.paste(cap, (0, out.height))
    return panel

ZH_HALF_DEG = 17.0            # Zhuangzi views: horizon in the middle, ±17° (covers +9.9° .. -15.0°)
ZH_FINAL_T = 12.0             # s after L1: both lines (and their mirrors) fully focused
SUN_COLLAPSE = (987.06, 6.0)  # F12: the sun line shrinks from ±10° to a point in 6 s (§6·8b)


def sun_half_at(p, t):
    """half-width of the sun line (deg) at t s after L1 (linear collapse for the sketch)."""
    T = p['t_appear'] + (t or 0.0)
    x = (T - SUN_COLLAPSE[0]) / SUN_COLLAPSE[1]
    return 10.0 * (1.0 - min(max(x, 0.0), 1.0))


def annotate_sun(im, ppd, el_top, az_left, lay, half_now=10.0, labels=True):
    """verify r3 MAJOR 2: draw the 8-ii sun line (±10° at el 0, §6·8b) and the Unity outer edge of the dark scrims
    (azimuth_span_deg from strings_all.json, i.e. 2·atan(width_m / 2d)) so the clearance can be read off the proof."""
    d = ImageDraw.Draw(im, 'RGBA')
    W, H = im.size
    X = lambda az: (az - az_left) * ppd
    yh = el_top * ppd
    warm = (255, 226, 176, 210)
    y = yh + 1.15 * ppd                                              # bracket just under the horizon
    x0, x1 = X(-10.0), X(10.0)
    d.line([(x0, y), (x1, y)], fill=warm, width=2)
    for x in (x0, x1):
        d.line([(x, y - 0.45 * ppd), (x, y + 0.45 * ppd)], fill=warm, width=2)
    if half_now < 9.95:
        for x in (X(-half_now), X(half_now)):
            d.line([(x, y - 0.3 * ppd), (x, y + 0.3 * ppd)], fill=(255, 190, 120, 230), width=3)
    edges = sorted({sc['azimuth_span_deg'][0] for sc in lay['scrims'] if sc.get('azimuth_span_deg')})
    cool = (170, 205, 255, 200)
    for k, e in enumerate(edges[:1]):
        xe = X(e)
        for yy in range(int(yh - 9.0 * ppd), int(yh + 9.0 * ppd), 14):
            d.line([(xe, yy), (xe, yy + 7)], fill=cool, width=2)
        d.line([(x1, y), (xe, y)], fill=(255, 255, 255, 110), width=1)
    if labels:
        f = capfont(max(16, int(ppd * 0.62)))

        def tag(xy, text, col):
            bb = d.multiline_textbbox(xy, text, font=f, spacing=4)
            d.rounded_rectangle([bb[0] - 6, bb[1] - 4, bb[2] + 6, bb[3] + 4], radius=5, fill=(14, 16, 22, 170))
            d.multiline_text(xy, text, font=f, fill=col, spacing=4)
        tag((x0, y + 0.6 * ppd), '日线 ±10°（§6·8b；F12 起 6 s 收成一点）' if half_now >= 9.95 else
            '日线：F12 后 %.1f s，±%.1f°（线横着收拢）' % ((1 - half_now / 10.0) * 6.0, half_now), warm)
        if edges:
            tag((X(edges[0]) + 10, yh - 9.0 * ppd), '暗衬外缘 方位 %.1f°（Unity 实际张角 2·atan(w/2d)）\n离日线端 %.1f°' % (edges[0], edges[0] - 10.0), cool)
    return im


def zhuangzi_view(p, player, ppd, width, t=None, az_c=None, half=ZH_HALF_DEG, label=True, scale=True, annotate=False):
    lay = LY.zhuangzi_layout(p, player)
    objs = lay['objects']
    if t is not None:
        objs = [o for o in objs if obj_state(o, t)[0] > 0.01]
    H = int(round(2 * half * ppd))
    H += H % 2
    el_top = H / 2 / ppd
    az_c = p['place'][0] if az_c is None else az_c
    sh = sun_half_at(p, t)
    img, els = bg_scene('8-ii', width, H, el_top, 1.0 / ppd, az_c=az_c, line_half=sh)
    cx = width / 2 + (p['place'][0] - az_c) * ppd
    lay['_check'] = unity_check(p, img, objs, cx, el_top, ppd,
                                'P08b_Zhuangzi/%s/t=%s/w=%d' % (player, t, width))
    img, widest = render_objects(img, objs, cx, el_top, ppd, p['color_target'], p['opacity'], lay['scrims'],
                                 t=t, horizon_row=H / 2)
    u8 = to_u8(img)
    pv, plim = purple_of(u8, '8-ii')
    REPORT['purple'].append({'panel': 'P08b_Zhuangzi/%s/t=%s/w=%d' % (player, t, width), 'purple_share': round(pv, 4),
                             'rule': plim, 'limit': 0.02})
    im = Image.fromarray(u8)
    if scale:
        im = elevation_scale(im, ppd, el_top, labels=label)
    if annotate:
        im = annotate_sun(im, ppd, el_top, az_c - width / ppd / 2, lay, half_now=sh, labels=label)
    return im, lay, widest, pv


# ------------------------------------------------------------------------------------------ sheets
PLAYER_TITLE = {   # v4 (D-30): one language per player
    'zh': ('中文玩家', '只看中文：中文诗看原文，德 / 英诗看中译（思源宋体 SC Regular，主行字号）；天问照常'),
    'zht': ('繁體中文玩家（客戶端 zh-HK）', '只看中文（繁體）：中文詩看原文、德／英詩看中譯，思源宋體 TC Regular；天問照常（圖是同一幅）'),
    'ja': ('日本語のプレイヤー', '日本語だけ：漢詩は書き下し、独・英詩は和訳（源ノ明朝 JP Regular、主行の字号）。天問は漢字の下に一行（JP Medium 1.8°）'),
    'en': ('English-language players (and every other language)', 'English only: translations of the Chinese and German poems, Keats in the original (EB Garamond); Tianwen: the Han picture + one English line'),
    'de': ('Deutschsprachige Spieler', 'Rilke und Urlicht im Original, alles andere auf Englisch; Tianwen: das Bild in Han-Zeichen + eine englische Zeile'),
}

def header(width, title, sub):
    notes = ['字号 = 圣经 §7.3 视角（1° = %d px）；字距 CJK +0.10 em、拉丁 0；行距 1.6 / 1.35 em；按 TMP 的排法（advance + kern，无连字、无 GPOS）；'
             '每一行的位置、光学居中、衬底都取自 strings_all.json 的 layout。' % PPD,
             '底部细括号 = 28° 行长上限（§7.3）；背景是用各幕色板值画的示意，不是渲染；字与衬底按屏幕目标、不透明度与圣经的衬底强度在显示线性光里混合（这就是要在 Unity 里得到的样子）。',
             '第 4 版：每位玩家只看到一份（D-30）——原文是自己的语言就看原文，否则看译成自己语言的那一份；只剩一份就用主行字号（CJK 2.2–2.4°、拉丁 2.0–2.2° em），放不下 28° 的那种语言自己重新断行；时刻不变。',
             '每块说明栏：圣经 v2.1 §7.5 的时间 · 屏幕目标与填值（按诗句在屏幕上时实际起作用的调色求解）· Unity 模型读数（场景线性混合 → 调色，用交付的填值与衬底 α）· '
             'bloom 检查（圣经的 PPv2 bloom 模型，1080p）· 物体中心仰角（§7.3：+10° .. −15°）· 紫的面积（§1.3.4：第 4 幕以外 ≤ 2%）· 光学居中。']
    f = capfont(18)
    n = sum(len(wrap_text(t, f, width - 80)) for t in notes)
    im = Image.new('RGB', (width, 130 + 28 * n + 12), (12, 14, 19))
    d = ImageDraw.Draw(im)
    d.text((40, 28), '蓝白 / Lanbai · 诗句校样第 4 版（D-30：只显示自己的语言）· ' + title, font=capfont(40), fill=(226, 230, 236))
    d.text((40, 90), sub, font=capfont(20), fill=(170, 176, 188))
    y = 126
    for t in notes:
        y = draw_wrapped(d, 40, y, t, f, (130, 138, 150), width - 80, 28)
    return im

PPD = 26
WIDTH = 1500

def sheet(player):
    panels = []
    for p in L.POEMS:
        if p.get('mirror'):
            im, lay, widest, pv = zhuangzi_view(p, player, PPD, WIDTH, t=ZH_FINAL_T)
            m0 = lay['objects'][0]
            cents = '  '.join('%s %+.2f°' % (o['id'], o['center_el']) for o in lay['objects'])
            blk = lay['block']
            cap = caption_bar(WIDTH, [
                '第 8 幕 · 庄子《逍遥游》· 镜像处理（L1 + %.0f s：两行都在）   ·   %s' % (ZH_FINAL_T, timing_line(p)),
                '镜像的是这位玩家自己的语言（D-30）· %s %.2f°   ·   L2 不出（E25）   ·   每行一条暗衬带（Hann 拼成一整列）   ·   镜像字 α0.45（0.5 × 0.9）softness 0.3   ·   +35° / 0° / 60 m   ·   最宽行 %.1f°   ·   列 %.1f° × %.1f°' % (
                    FONT_CN[m0['font']], m0['size_deg'], widest, blk['width_deg'], blk['height_deg']),
                colour_line(p),
                check_text(lay['_check']),
                '物体中心仰角：%s   ·   紫 %.1f%%' % (cents, 100 * pv),
            ])
            pn = Image.new('RGB', (WIDTH, im.height + cap.height))
            pn.paste(im, (0, 0)); pn.paste(cap, (0, im.height))
            panels.append(pn)
        else:
            panels.append(block_panel(p, player, PPD, WIDTH, LY.block_layout(p, player)))
    t, sub = PLAYER_TITLE[player]
    hd = header(WIDTH, t, sub)
    gap = 14
    H = hd.height + sum(pn.height + gap for pn in panels) + 20
    sh = Image.new('RGB', (WIDTH, H), (12, 14, 19))
    sh.paste(hd, (0, 0))
    y = hd.height
    for pn in panels:
        sh.paste(pn, (0, y))
        y += pn.height + gap
    path = os.path.join(DOCS, 'Proof_%s.png' % player)
    sh.save(path, optimize=True)
    return path

def trilingual():
    p = [q for q in L.POEMS if q.get('mirror')][0]
    ppd = 30
    colw = 34 * ppd
    gap = 18
    W = 3 * colw + 4 * gap
    t_fin = ZH_FINAL_T
    # 1) the whole frame for an English-speaking player: sun dead ahead (az 0), the column at +35°; sun line and the
    #    Unity scrim edge marked (verify r3 MAJOR 2)
    pano_w = W - 2 * gap
    pano, lay_p, _, pv_pano = zhuangzi_view(p, 'en', ppd, pano_w, t=t_fin, az_c=pano_w / ppd / 2 - 18.0, half=15.5,
                                            label=True, annotate=True)
    # 2) zh / ja / en, settled
    finals = [zhuangzi_view(p, pl, ppd, colw, t=t_fin) for pl in ('zh', 'ja', 'en')]
    # 3) time strip (en), 2 x 2, each frame az -14° .. +60° so the sun line and the scrim edge are in every frame
    fw = (W - 3 * gap) // 2
    span = 74.0
    fppd = fw / span
    times = (1.5, 5.5, t_fin, 19.6)
    strip = [zhuangzi_view(p, 'en', fppd, fw, t=tt, az_c=-14.0 + span / 2, half=15.5, label=True, annotate=True)
             for tt in times]
    top = 230
    H = (top + pano.height + 70 + finals[0][0].height + 70 + 2 * (strip[0][0].height + 66) + 150)
    sh = Image.new('RGB', (W, H), (12, 14, 19))
    d = ImageDraw.Draw(sh)
    d.text((gap + 10, 30), '蓝白 · 全世界的论点之帧：庄子《逍遥游》在暮色的另一片天里（圣经 v2.1 §6·8、§7.3、§7.4-7、§7.5 #7）',
           font=capfont(44), fill=(226, 230, 236))
    y_ = 100
    pmax = 100 * max(f[3] for f in finals + strip + [(0, 0, 0, pv_pano)])
    for t in ['v2.1：只出 L1「天之苍苍，其正色邪？」（971.4）与 L3「其视下也，亦若是则已矣」（976.4，正字在地平线下，低头读）；L2 不出。'
              '第 4 版（D-30）：镜像的是每位玩家自己的语言（中文玩家原文、日文玩家書き下し、其余英文）；一列等距，地平线在正中那道缝里——上：L1、L3′（倒）；下：L3、L1′。排版恰好在“往下看与往上看一样”这一行上翻转。'
              '不再有译文字幕位。两行一起保持到 989.0，989.0 → 993.0 与 F12 的日线收缩同步退场：线横着收拢，字竖着分开。',
              '暖色细括号 = 日线 ±10°（§6·8b）；蓝色虚线 = 暗衬在 Unity 里的实际外缘（strings_all.json 的 azimuth_span_deg = 2·atan(width_m / 2d)），'
              '英语玩家的外缘在方位 %.1f°，离日线端 %.1f°（三种语言里最近的是 %.1f°，规定 ≥ 2°）：没有任何衬底压到日线上（§6·8“永远不压在日线上”）。背景按 §1.3.4 去紫（全图最大紫 %.2f%%，上限 2%%）。' % (
                  min(sc['azimuth_span_deg'][0] for sc in lay_p['scrims']), min(sc['azimuth_span_deg'][0] for sc in lay_p['scrims']) - 10.0,
                  min(sc['azimuth_span_deg'][0] - 10.0 for f in finals for sc in f[1]['scrims']), pmax)]:
        y_ = draw_wrapped(d, gap + 10, y_, t, capfont(22), (160, 168, 180), W - 2 * gap - 20, 34)
    y = top
    sh.paste(pano, (gap, y))
    d.text((gap + 6, y + pano.height + 14), 'English-speaking player, L1 + %.0f s, the whole frame: sun dead ahead in the windscreen (az 0°), '
                                             'the column on the horizon at az +35°, 60 m   ·   英语玩家的整个画面（方位 −18° .. +85°）' % t_fin,
           font=capfont(22), fill=(200, 206, 214))
    y += pano.height + 70
    labels = ['中文玩家 · 原文', '日本語 · 書き下しだけ（源ノ明朝 JP Regular 2.08°）',
              'English and others · English only (EB Garamond 2.0°)']
    for i, (im, lay, widest, pv) in enumerate(finals):
        x = gap + i * (colw + gap)
        sh.paste(im, (x, y))
        d.text((x + 6, y + im.height + 14), labels[i] + '   ·   L1 + %.0f s' % t_fin, font=capfont(22), fill=(200, 206, 214))
    y += finals[0][0].height + 70
    tl = ['971.4 + %.1f s · L1 与它的镜像对焦中' % times[0],
          '971.4 + %.1f s · L3 在地平线下对焦（低头读）、L3′ 在地平线上' % times[1],
          '971.4 + %.0f s · 四块都就位；最静的画面' % times[2],
          '991.0（退场第 2 s）· 日线收到 ±%.1f°：线横着收拢，字竖着分开（地平线上的向上、下的向下）' % sun_half_at(p, times[3])]
    for i, (im, lay, widest, pv) in enumerate(strip):
        x = gap + (i % 2) * (fw + gap)
        yy = y + (i // 2) * (strip[0][0].height + 66)
        sh.paste(im, (x, yy))
        d.text((x + 6, yy + im.height + 14), 'English · ' + tl[i], font=capfont(22), fill=(200, 206, 214))
    lay = LY.zhuangzi_layout(p, 'en')
    y += 2 * (strip[0][0].height + 66) + 10
    d.text((gap + 10, y), '中心仰角（英语玩家）：' + '   '.join('%s %+.2f°' % (o['id'], o['center_el']) for o in lay['objects'] if o['id'] in ('L1', 'L3′', 'L3', 'L1′'))
           + '   ·   字号：英文 2.0° em（fontSize %.2f @ 60 m）' % lay['objects'][0]['font_size'], font=capfont(22), fill=(150, 158, 170))
    d.text((gap + 10, y + 40), '时间条每格方位 −14° .. +60°（1° = %.1f px），上方大图与三栏 1° = %d px。' % (fppd, ppd), font=capfont(22), fill=(150, 158, 170))
    path = os.path.join(DOCS, 'Proof_Trilingual_Zhuangzi.png')
    sh.save(path, optimize=True)
    return path


# ---------------------------------------------------------------------------------------- credits
class _Face:
    """small adaptor for the credits specimen (layout in em via lanbai_layout.Metrics)."""
    def __init__(self, fk):
        self.fk = fk
        self.m = LY.Metrics(fk)
    def width_em(self, text, track):
        return self.m.line(text, track)['width']

def credits_proof():
    """Every credits / Coleridge string in its bible font at the §5.5 minimum sizes, on the bible's paper colours.
    GLYPH SPECIMEN for the TMP fallback path, NOT the board layout (the Sign kit's baked Notice_Credits texture is
    the real sheet, in its condensed wording)."""
    mm = 1.2
    Wmm = 900.0
    margin = 72.0
    C = L.CREDITS
    y = margin + 40
    rows = []

    def em_for(fk, cap_mm=None, em_mm=None):
        if em_mm:
            return em_mm
        from fontTools.ttLib import TTFont
        tt = TTFont(os.path.join(SUB, L.FONTS[fk]['subset']), lazy=True)
        return cap_mm / (tt['OS/2'].sCapHeight / tt['head'].unitsPerEm)

    def wrap(text, fk, em, track, measure):
        f = _Face(fk)
        if f.width_em(text, track) * em <= measure:
            return [text]
        parts, lines, cur = text.split(' '), [], ''
        for w_ in parts:
            t = (cur + ' ' + w_).strip()
            if cur and f.width_em(t, track) * em > measure:
                lines.append(cur)
                cur = w_
            else:
                cur = t
        lines.append(cur)
        return lines

    def add(text, fk, em, x, track=None, lead=1.35, after=0.0):
        nonlocal y
        track = (0.0 if '——' in text else LY.track_em(fk)) if track is None else track
        for ln in wrap(text, fk, em, track, Wmm - margin - x):
            rows.append((ln, fk, em, x, track, y))
            y += em * lead
        y += after

    add(C['title']['text'], C['title']['font'], em_for(C['title']['font'], cap_mm=56), margin, track=0.30, lead=1.0, after=10)
    add(C['title_cjk']['text'], C['title_cjk']['font'], 40, margin, lead=1.0, after=60)
    for ln in C['epigraph']['lines']:
        add(ln, C['epigraph']['font'], 34, margin + 60, lead=1.6)
    add(C['attribution']['text'], C['attribution']['font'], 30, margin + 400, track=0.0, lead=1.6, after=60)
    for row in C['rows']:
        add(row['role'], C['role_font'], em_for(C['role_font'], cap_mm=24), margin, lead=1.45)
        names = [n for n in row['names'] if not n.get('placeholder')] or [{'text': '〔　　　　〕', 'font': 'SourceHanSerifSC-Regular'}]
        for n in names:
            em = 34 if LY.is_cjk(n['font']) else em_for(n['font'], cap_mm=24)
            add(n['text'], n['font'], em, margin + 60, lead=1.45)
        y += 40
    # strings that only the Sign kit's condensed sheet uses
    y += 30
    label_y = y                                  # a sheet label, drawn later in the caption font (not a world string)
    y += 22 * 2.0
    sk = L.CREDITS_SIGNKIT_VARIANT
    for fk in ('EBGaramond-Italic', 'EBGaramond-Regular', 'SourceHanSerifSC-Regular', 'SourceHanSerifSC-Medium'):
        full = set()
        for r in C['rows']:
            full.add(r['role'])
            full.update(n['text'] for n in r['names'])
        full.update(C['epigraph']['lines'] + [C['attribution']['text'], C['title_cjk']['text']])
        for t in sk[fk]:
            if t not in full:
                em = 34 if LY.is_cjk(fk) else em_for(fk, cap_mm=24)
                add(t, fk, em, margin + 60, lead=1.45)
    Hmm_ = y + margin
    W, H = int(Wmm * mm), int(Hmm_ * mm)
    paper = np.ones((H, W, 3)) * s2l(hx(L.PAPER))
    mask = Image.new('L', (W * SS, H * SS), 0)
    d = ImageDraw.Draw(mask)
    for text, fk, em, x, track, yy in rows:
        m = LY.Metrics(fk)
        px = int(round(em * mm * SS))
        ln = m.line(text, track)
        pf = pil_font(fk, px)
        for ch, gx, adv, ib, g in ln['pens']:
            X = x * mm * SS + gx * px
            if g is None:
                REPORT['missing'].append((fk, ch, text))
                d.rectangle([X, yy * mm * SS - px * 0.8, X + px * 0.8, yy * mm * SS], outline=255, width=4)
                continue
            if ib is None:
                continue
            d.text((round(X), round(yy * mm * SS)), ch, font=pf, fill=255, anchor='ls')
            REPORT['glyphs_drawn'] += 1
    board = Image.fromarray(to_u8(composite_mask(paper, mask, L.INK_CREDITS, 1.0)))
    ImageDraw.Draw(board).text((margin * mm, label_y * mm), '—— 以下：站牌套件精简版独有的字符串（校样标注，不是世界里的字）——',
                               font=capfont(int(18 * mm)), fill=(120, 110, 96), anchor='ls')

    # Coleridge slip: IM FELL English 7 mm body, leading 1.22; sized to the text the way the Sign kit does
    smm = 6.0
    K = L.COLERIDGE
    em = 7.0
    lead = em * 1.22
    ml, mr, mt = 11.0, 9.0, 12.0
    vind = 9.0
    fr, fsc = LY.Metrics('IMFellEnglish-Roman'), LY.Metrics('IMFellEnglishSC')
    longest = max(fr.line(t, 0)['width'] * em for t in K['verse']['lines'])
    measure = vind + longest + 1.0
    words = K['prose']['text'].split(' ')
    prose, cur = [], ''
    for wd in words:
        t = (cur + ' ' + wd).strip()
        if cur and fr.line(t, 0)['width'] * em > measure:
            prose.append(cur)
            cur = wd
        else:
            cur = t
    prose.append(cur)
    SWmm = ml + measure + mr
    SHmm = mt + lead * (1.6 + len(prose) + 0.5 + len(K['verse']['lines'])) + 10
    SW, SH = int(SWmm * smm), int(SHmm * smm)
    slip = np.ones((SH, SW, 3)) * s2l(hx(L.SLIP_PAPER))
    m2 = Image.new('L', (SW * SS, SH * SS), 0)
    d2 = ImageDraw.Draw(m2)

    def put2(text, fk, emmm, xmm, ymm):
        mm_ = LY.Metrics(fk)
        px = int(round(emmm * smm * SS))
        ln = mm_.line(text, 0.0)
        pf = pil_font(fk, px)
        for ch, gx, adv, ib, g in ln['pens']:
            X = xmm * smm * SS + gx * px
            if g is None:
                REPORT['missing'].append((fk, ch, text))
                d2.rectangle([X, ymm * smm * SS - px * 0.8, X + px * 0.8, ymm * smm * SS], outline=255, width=4)
                continue
            if ib is None:
                continue
            d2.text((round(X), round(ymm * smm * SS)), ch, font=pf, fill=255, anchor='ls')
            REPORT['glyphs_drawn'] += 1

    yy = mt
    hw = fsc.line(K['head']['text'], 0)['width'] * em * 0.86
    put2(K['head']['text'], 'IMFellEnglishSC', em * 0.86, (SWmm - hw) / 2, yy)
    yy += lead * 1.6
    for ln in prose:
        put2(ln, 'IMFellEnglish-Roman', em, ml, yy)
        yy += lead
    yy += lead * 0.5
    for i, ln in enumerate(K['verse']['lines']):
        put2(ln, 'IMFellEnglish-Roman', em, ml + vind + (22 if i == 0 else 0), yy)
        yy += lead
    slip_img = Image.fromarray(to_u8(composite_mask(slip, m2, '#2B2723', 1.0)))

    out = Image.new('RGB', (board.width + slip_img.width + 120, max(board.height, slip_img.height) + 300), (12, 14, 19))
    d = ImageDraw.Draw(out)
    d.text((40, 26), '蓝白 · 片尾与 Coleridge 纸条的全部字符串 — TMP 备用路径的字形校样（不是版式；正式版是站牌套件烘好的贴图）', font=capfont(32), fill=(226, 230, 236))
    y_ = 80
    for t in ['左：圣经 / lens_story §6 全文版 + 站牌套件精简版独有的字符串，按 §5.5 下限字号（拉丁大写 24 mm、中文 30–34 mm、标题大写 56 mm）排在 900 mm 宽的纸上，1 mm = %.1f px。' % mm,
              '全文版在这个字号下要 %.0f mm 长，圣经允许的纸最长 1 400 mm（箱体 1 000 × 1 500）→ 全文版在规格上放不下，公告板只能用站牌套件的精简版（两栏）。'
              '「——梦中得句」：子集里 U+2014 = 全宽、汉字中线上的横线，这一行字距 0，两条连成一条 2 em 的线。' % (Hmm_,),
              '右：纸条，IM FELL English（子集已改名 Lanbai Slip，OFL 保留字名）7 mm，行距 1.22，1 mm = %d px。尺寸 %.1f × %.1f mm 是按站牌套件的做法“纸随 7 mm 的字”排出的，不是圣经 §5.5 的 120 × 170 mm。'
              '算法：宽 = 左边距 %.0f + 诗行缩进 %.0f + 最长诗行 %.1f + 余量 1 + 右边距 %.0f mm；高 = 上边距 %.0f + 行距 × (标题 1.6 + 散文 %d 行 + 0.5 + 诗 %d 行) + 10 mm。'
              '120 mm 宽的纸放不下 7 mm 的字：要么接受这个尺寸，要么把字降到 7 × (120 − %.0f) / %.1f = %.1f mm。'
              % (smm, SWmm, SHmm, ml, vind, longest, mr, mt, len(prose), len(K['verse']['lines']), ml + mr + vind, longest,
                 7.0 * (120 - ml - mr - vind) / longest)]:
        y_ = draw_wrapped(d, 40, y_, t, capfont(19), (150, 158, 170), out.width - 80, 28)
    out.paste(board, (40, 250))
    out.paste(slip_img, (board.width + 80, 250))
    path = os.path.join(DOCS, 'Proof_Credits.png')
    out.save(path, optimize=True)
    REPORT['credits_full_version_length_mm'] = round(Hmm_, 1)
    REPORT['coleridge_slip_mm'] = [round(SWmm, 1), round(SHmm, 1)]
    REPORT['coleridge_longest_verse_mm'] = round(longest, 1)
    return path


if __name__ == '__main__':
    which = sys.argv[1:] or ['zh', 'zht', 'ja', 'en', 'de', 'tri', 'credits']
    made = []
    for w in which:
        if w in ('zh', 'zht', 'ja', 'en', 'de'):
            made.append(sheet(w))
        elif w == 'tri':
            made.append(trilingual())
        elif w == 'credits':
            made.append(credits_proof())
    REPORT['missing_count'] = len(REPORT['missing'])
    REPORT['verdict'] = 'PASS: no missing glyph (no tofu)' if not REPORT['missing'] else 'FAIL: tofu'
    bad = [r for r in REPORT['purple'] if isinstance(r['limit'], float) and r['purple_share'] > r['limit']]
    REPORT['purple_verdict'] = ('PASS: every panel outside scene 4 has <= 2 %% purple (max %.2f %%)' %
                                (100 * max([r['purple_share'] for r in REPORT['purple'] if isinstance(r['limit'], float)] or [0]))
                                if not bad else 'FAIL: ' + ', '.join(r['panel'] for r in bad))
    with open(os.path.join(DOCS, 'proof_report.json'), 'w', encoding='utf-8') as f:
        json.dump({k: v for k, v in REPORT.items() if k != 'lines'} | {'n_lines': len(REPORT['lines'])}, f, ensure_ascii=False, indent=1)
    print('\n'.join(made))
    print(REPORT['verdict'], REPORT['glyphs_drawn'], 'glyphs')
    print(REPORT['purple_verdict'])
