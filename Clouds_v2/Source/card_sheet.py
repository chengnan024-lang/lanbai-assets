# -*- coding: utf-8 -*-
"""云卡 v2 的总览图与量数（通道格式）：每张卡按 cards_v2.json 解出的该组颜色、在 rel 15 / 80 / 150° 三个太阳角度下
着色（cardshade = shader 的 numpy 移植），叠在该幕的目标天上（卡所朝方向、仰角 −6…24°），按 PPv2 引擎模型调色（含 bloom）。
量：阴影体 / 受光顶的屏幕色、卡上的紫带占比（h 290–330、C* > 8、L* > 40，D-21；晨另按 h 285–330、C* > 12）、
通道是否裁顶。输出 Docs~/cards_<组>.png 与 Docs~/cards_<组>.json。
用法：python card_sheet.py dawn | dusk"""
import os
import sys
import json
import glob
import numpy as np
from PIL import Image, ImageDraw, ImageFont

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lb_common as C  # noqa: E402
import cardshade as CS  # noqa: E402
import card_solve as SV  # noqa: E402

KIT = os.path.normpath(os.path.join(HERE, '..'))
WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')
GROUPS = {'dawn': dict(sets=['dawn'], sky='dawn', sun_az=30.0, grade='S6', strict=True),
          'dusk': dict(sets=['duskU', 'duskD'], sky='dusk', sun_az=0.0, grade='S8', strict=False)}
RELS = (15.0, 80.0, 150.0)


def font(px):
    for p in (os.path.join(KIT, '..', 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf'), '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'):
        if os.path.exists(p):
            return ImageFont.truetype(p, px)
    return ImageFont.load_default()


def backdrop(sky, view_az, h, w, el_top, el_bot, hfov):
    el = np.linspace(el_top, el_bot, h)
    az = view_az + np.linspace(-hfov / 2, hfov / 2, w)
    A, E_ = np.meshgrid(az, el)
    return C.sample_equirect(sky, C.dir_from_azel(A, E_), 0.0)


def load_png_card(base):
    J = json.load(open(os.path.join(KIT, 'Textures', 'cards_v2.json')))['cards'][base]
    k = np.asarray(Image.open(os.path.join(KIT, 'Textures', base + '_K.png')).convert('RGBA')).astype(np.float64) / 255
    s = np.asarray(Image.open(os.path.join(KIT, 'Textures', base + '_S.png')).convert('RGB')).astype(np.float64) / 255
    return C.srgb_dec(k[..., :3]) * J['kscale'], C.srgb_dec(s[..., :2]) * J['sscale'], k[..., 3]


def purple(codes, mask, strict):
    L, h, c = C.hue_chroma(codes[mask])
    if strict:
        return float(((h >= 285) & (h <= 330) & (c > 12)).mean()) if len(h) else 0.0
    return float(((h >= 290) & (h <= 330) & (c > 8) & (L > 40)).mean()) if len(h) else 0.0


def main(group):
    G = GROUPS[group]
    J = json.load(open(os.path.join(KIT, 'Textures', 'cards_v2.json')))
    col = J['colours'][group]
    sun, skyc, gnd = np.array(col['SunColor']), np.array(col['SkyUpColor']), np.array(col['GroundColor'])
    sky = C.read_hdr(os.path.join(HERE, 'sky', f'{G["sky"]}_target_1k.hdr')).astype(np.float64)
    # the stored fit has the sun at the bible's +45 (dawn); D-12 puts it at +30: rotate the lookup
    sky_shift = {'dawn': 45.0 - G['sun_az'], 'dusk': 0.0}[G['sky']]
    cards = []
    for s in G['sets']:
        cards += sorted(glob.glob(os.path.join(WORK, f'Cloud*V2_*_{s}_ch.npz')))
    TW, TH = 360, 300
    rows, metrics = [], {}
    for npz in cards:
        base = os.path.basename(npz)[:-7]
        K, S, a = load_png_card(base)                  # review r1 S4: measure the shipped PNGs, not the float npz
        h, w = a.shape
        sc = min(TW / w, TH / h)
        tiles = []
        m = dict()
        sel = SV.selections(K, S, a) if (a > 0.97).sum() > 100 else None
        for rel in RELS:
            c, al = CS.shade(K, S, a, rel, sun, skyc, gnd)
            view_az = G['sun_az'] - rel + sky_shift
            bg = backdrop(sky, view_az, h, w, 20.0 if 'duskD' not in base else 0.0, -4.0 if 'duskD' not in base else -24.0, 60.0)
            comp = c * al[..., None] + bg * (1 - al[..., None])
            codes = C.grade(comp, G['grade'], bloom=True)
            mm = dict(purple_on_card=round(purple(codes, al > 0.5, G['strict']), 4))
            if sel is not None:
                sh, tp = sel
                mm['shadow'] = C.to_hex(np.median(codes[sh], 0))
                mm['top'] = C.to_hex(np.median(codes[tp], 0))
                mm['shadow_hC'] = [round(float(v), 1) for v in C.hue_chroma(np.median(codes[sh], 0))[1:]]
            mm['card_max_linear'] = round(float(c[al > 0.5].max()), 2) if (al > 0.5).any() else 0
            m[f'rel{int(rel)}'] = mm
            im = Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).resize((int(w * sc), int(h * sc)), Image.LANCZOS)
            tiles.append(im)
        info = json.load(open(os.path.join(KIT, 'Textures', base + '.json')))
        m['clipped_K'] = info.get('clipped_K'); m['clipped_S'] = info.get('clipped_S')
        metrics[base] = m
        rows.append((base, tiles))
    if not rows:
        print('no cards yet for', group)
        return
    f1, f2 = font(22), font(15)
    W = 40 + 3 * (TW + 20)
    H = 90 + len(rows) * (TH + 40)
    sheet = Image.new('RGB', (W, H), (18, 20, 24))
    d = ImageDraw.Draw(sheet)
    d.text((20, 16), f'云卡 v2 · {group} · 太阳在右侧 15° / 80° / 150°（逆光 / 侧光 / 顺光）· 按 {G["grade"]} 调色（含 bloom）', font=f1, fill=(232, 238, 244))
    d.text((20, 50), 'shader 的 numpy 移植着色，叠在该幕的目标天上；没有雾。颜色 = Textures/cards_v2.json colours.' + group, font=f2, fill=(150, 158, 168))
    y = 90
    for base, tiles in rows:
        d.text((20, y), base, font=f2, fill=(200, 206, 214))
        x = 20
        for t in tiles:
            sheet.paste(t, (x, y + 22))
            x += TW + 20
        y += TH + 40
    os.makedirs(os.path.join(KIT, 'Docs~'), exist_ok=True)
    sheet.save(os.path.join(KIT, 'Docs~', f'cards_{group}.png'))
    json.dump(metrics, open(os.path.join(KIT, 'Docs~', f'cards_{group}.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(metrics, ensure_ascii=False)[:3000])


if __name__ == '__main__':
    for g in sys.argv[1:] or ['dawn']:
        main(g)
