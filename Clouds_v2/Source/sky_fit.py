# -*- coding: utf-8 -*-
"""把选定的 HDRI 拉到圣经的屏幕目标（§6·6 晨、§6·8 暮），得到“场景线性的目标天”：
   sky(d) = HDRI(d) × T(el, Δaz)，T 是“按仰角分带”的乘色：日侧（Δaz 0）、侧面（90）、背日（180）三条随仰角变化的
   log 乘色曲线（单调三次插值），方位之间按 cos 平滑过渡；控制点 = 圣经给的每个屏幕目标（按 S6 / S8 引擎模型反解成
   场景线性）。真实的天就是按仰角分带的，所以只在带上调，不会出现色块。太阳像素先抠掉（太阳由平行光 + 程序化日盘负责）。下半球按圣经换成
   “地平线色 → 天底色”的雾渐变（晨 #6F8FA8；暮的下半球在 8-i 是天花之下的暮天、8-ii 是另一片天，见 Act08）。
输出 sky/<preset>_target_1k.hdr（1024×512，yaw 已转好：太阳在圣经方位），sky/<preset>_fit.json（控制点、残差），
sky/<preset>_preview.png（按调色显示的全景 + 控制点）。
这是“云卡被什么天照亮”和参考渲染用的天；正式的 Lanbai/Sky 归天空会话（见 Clouds_v2/给总控.md）。
"""
import os
import sys
import json
import numpy as np
from PIL import Image, ImageDraw

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import lb_common as C  # noqa: E402

OUT = os.path.join(HERE, 'sky')

PRESETS = {
    # profiles: Δaz from the sun -> list of (el, screen target). Bible targets + 设计值 (design values, listed in
    # DESIGN below) where the bible gives none, so every azimuth has a full vertical profile (no interpolation holes).
    'dawn': dict(sid='S6', sun_az=45.0, sun_el=6.0, nadir='#6F8FA8', zenith='#3E64A6',
                 prof={0: [(1.5, '#F2C79A'), (6.0, '#F6DDB8'), (15.0, '#E3D6C4'), (30.0, '#B3C2D6'), (60.0, '#6A8CC0')],
                       90: [(1.5, '#D6CFC6'), (8.0, '#C8CCD4'), (25.0, '#9DB3D6'), (45.0, '#8EA9D4')],
                       180: [(1.5, '#8C98B8'), (7.0, '#CFB7B7'), (25.0, '#9DB5DA'), (45.0, '#AFC4E0')]},
                 notes={'#9DB5DA': '背日 25°（圣经：20–40° 调色后 ≥ #6F8FC0，h 255–275）'}),
    'dusk': dict(sid='S8', sun_az=0.0, sun_el=0.5, nadir='#2E3C66', zenith='#3D4A80',
                 prof={0: [(0.5, '#F2A56B'), (2.0, '#FFB070'), (6.0, '#F6B98A'), (14.0, '#E0AE93'), (28.0, '#A8A2B0'),
                           (50.0, '#7E87B0')],
                       90: [(1.0, '#D9A0A0'), (6.0, '#C9A1A6'), (18.0, '#A8A2B0'), (40.0, '#808AB2')],
                       180: [(1.0, '#B98E99'), (5.0, '#E7A0A0'), (16.0, '#A8A2B0'), (40.0, '#808AB2')]},
                 notes={}),
}
BIBLE = {'dawn': {'#3E64A6', '#F2C79A', '#8C98B8', '#CFB7B7', '#AFC4E0'},
         'dusk': {'#3D4A80', '#F2A56B', '#FFB070', '#E7A0A0', '#808AB2'}}
NAMES = {('dawn', 0, 1.5): '日侧地平线 sun-side horizon', ('dawn', 180, 1.5): '地影带 earth shadow',
         ('dawn', 180, 7.0): '金星带 belt of Venus', ('dawn', 180, 25.0): '背日 25°', ('dawn', 180, 45.0): '背日 45°',
         ('dusk', 0, 0.5): '天缝 sky slot', ('dusk', 0, 2.0): '日带 sun band', ('dusk', 90, 40.0): '中天（侧）mid-sky',
         ('dusk', 180, 5.0): '玫瑰带 rose band', ('dusk', 180, 40.0): '中天 mid-sky'}


def find_sun(im):
    H, W, _ = im.shape
    lum = im @ C.LUMA
    from scipy.ndimage import gaussian_filter
    y, x = np.unravel_index(np.argmax(gaussian_filter(lum, 1.0)), lum.shape)
    return (x + 0.5) / W, 90.0 - (y + 0.5) / H * 180.0


def remove_sun(im, sun_dir, yaw, radius=2.5):
    """Replace the disc + its hottest glow with the azimuthal ring just outside it (sun = lamp + program disc)."""
    H, W, _ = im.shape
    d = C.equirect_dirs(H, W, yaw)
    ang = np.degrees(np.arccos(np.clip(d @ sun_dir, -1, 1)))
    out = im.copy()
    ring = (ang > radius) & (ang < radius + 1.5)
    rv = np.median(im[ring], 0)
    inside = ang <= radius
    # soft: keep the smooth aureole below the ring level
    out[inside] = np.minimum(im[inside], rv * (1 + 0.6 * (1 - ang[inside] / radius))[:, None])
    removed = ((im - out) * C.solid_angle_rows(H, W)[..., None]).reshape(-1, 3).sum(0)
    return out, removed


def _pchip(xk, yk, x):
    from scipy.interpolate import PchipInterpolator
    if len(xk) == 1:
        return np.broadcast_to(yk[0], x.shape + yk.shape[1:]).copy()
    return PchipInterpolator(xk, yk, axis=0, extrapolate=False)(np.clip(x, xk[0], xk[-1]))


def fit(name):
    P = PRESETS[name]
    im = C.read_hdr(C.HDRI[name]).astype(np.float64)
    H, W, _ = im.shape
    u, el_hdri = find_sun(im)
    yaw = (u - 0.5) * 360.0 - P['sun_az']
    sun_d = C.dir_from_azel(P['sun_az'], el_hdri)
    sky, Esun = remove_sun(im, sun_d, yaw)
    blur = sky.copy()
    from scipy.ndimage import gaussian_filter
    # knots are matched on an azimuth-averaged sky (±~20°): the sun's aureole keeps its own shape instead of being
    # flattened into a dark ring around a bright point
    base = sky.copy()
    dd = C.equirect_dirs(H, W, yaw)
    cone = np.degrees(np.arccos(np.clip(dd @ sun_d, -1, 1))) < 20.0
    for y in range(H):                       # aureole out of the baseline: bridge it across in azimuth, row by row
        cols = np.nonzero(cone[y])[0]
        if len(cols) == 0 or len(cols) > W // 2:
            continue
        l, r = (cols.min() - 1) % W, (cols.max() + 1) % W
        f = (cols - cols.min() + 1) / (len(cols) + 1.0)
        base[y, cols] = base[y, l] * (1 - f[:, None]) + base[y, r] * f[:, None]
    blur = np.stack([gaussian_filter(base[..., i], (1.5, 25), mode='wrap') for i in range(3)], -1)

    def lr(daz, el, hx):
        cd = C.dir_from_azel(P['sun_az'] + daz, el)
        t = C.ungrade_hex(hx, P['sid'])
        c = C.sample_equirect(blur, cd[None], yaw)[0]
        return np.log(t / np.maximum(c, 1e-6)), t, c
    rows = [('天顶 zenith', 0, 89.5, P['zenith'])]
    curves = {}
    for daz, knots in P['prof'].items():
        xs, ys = [], []
        for el, hx in knots:
            xs.append(el); ys.append(lr(daz, el, hx)[0]); rows.append((NAMES.get((name, daz, el), ''), daz, el, hx))
        xs.append(90.0); ys.append(lr(daz, 88.0, P['zenith'])[0])
        curves[daz] = (np.array(xs), np.array(ys))
    # side profile with no own knots below its first one: borrow the mean of sun / anti at those elevations
    def prof_eval(daz, el):
        xs, ys = curves[daz]
        v = _pchip(xs, ys, el)
        v[el < xs[0]] = ys[0]
        return v
    elv = 90.0 - (np.arange(H) + 0.5) / H * 180.0
    el_up = np.maximum(elv, 0.0)
    G = {k: prof_eval(k, el_up) for k in curves}            # (H, 3)
    d = C.equirect_dirs(H, W, yaw)
    az, _ = C.azel_from_dir(d)
    dz = np.abs(((az - P['sun_az']) + 180) % 360 - 180)      # 0..180
    # weights: sun 0, side 90, anti 180 with smooth (cosine) blending
    t = dz / 90.0
    w_sun = np.where(t < 1, 0.5 + 0.5 * np.cos(np.pi * t), 0)
    w_anti = np.where(t > 1, 0.5 - 0.5 * np.cos(np.pi * (t - 1)), 0)
    w_side = 1 - w_sun - w_anti
    LR = w_sun[..., None] * G[0][:, None] + w_side[..., None] * G[90][:, None] + w_anti[..., None] * G[180][:, None]
    out = sky * np.exp(LR)
    # lower hemisphere: horizon colour (same azimuth, just above) -> nadir, fog gradient
    hz_row = gaussian_filter(out[np.argmin(np.abs(elv - 0.6))], (12, 0), mode='wrap')
    nad = C.ungrade_hex(P['nadir'], P['sid'])
    for y in range(H):
        if elv[y] < 0:
            f = (min(-elv[y], 90.0) / 90.0) ** 0.45
            out[y] = hz_row * (1 - f) + nad * f
    os.makedirs(OUT, exist_ok=True)
    d0 = C.equirect_dirs(H, W, 0.0)
    store = C.sample_equirect(out, C.equirect_dirs(H, W, 0.0) @ np.eye(3), yaw) if False else None
    # resample to yaw 0 (column u = az/360 + 0.5): out is indexed in the HDRI's own columns (yaw)
    store = C.sample_equirect(out, d0, yaw)
    res = []
    sbase = store / np.maximum(C.sample_equirect(sky, d0, yaw), 1e-9) * C.sample_equirect(base, d0, yaw)
    sblur = np.stack([gaussian_filter(sbase[..., i], (1.5, 25), mode='wrap') for i in range(3)], -1)
    for lab, daz, el, hx in rows:
        got = C.sample_equirect(sblur, C.dir_from_azel(P['sun_az'] + daz, el)[None], 0.0)[0]
        code = C.grade(got[None, None], P['sid'], False)[0, 0]
        res.append(dict(source='bible' if hx in BIBLE[name] else '设计值 design', label=lab + (' · ' + P['notes'][hx] if hx in P['notes'] else ''), d_az_from_sun=daz, el=el,
                        target=hx, fill_linear=np.round(C.ungrade_hex(hx, P['sid']), 4).tolist(), result=C.to_hex(code),
                        err_codes=round(float(np.abs(code - C.hex_rgb(hx) * 255).max()), 1)))
    C.write_hdr(os.path.join(OUT, f'{name}_target_1k.hdr'), store)
    meta = dict(preset=name, hdri=os.path.basename(C.HDRI[name]), grade=P['sid'],
                sun_az_deg=P['sun_az'], sun_el_deg_in_hdri=round(float(el_hdri), 2), sun_el_deg_bible=P['sun_el'],
                hdri_yaw_deg=round(float(yaw), 2),
                mapping='equirect, column u = az/360 + 0.5 (az from +Z toward +X), row v = (90 - el)/180; Unity world',
                sun_removed_irradiance_rgb=np.round(Esun, 4).tolist(),
                tint_model='log tint = cosine-blend over Δaz of three pchip-over-elevation curves (sun 0 / side 90 / anti 180); zenith shared',
                tint_curves={str(k): dict(el=v[0].tolist(), log_rgb=np.round(v[1], 4).tolist()) for k, v in curves.items()},
                control_points=res, nadir=P['nadir'])
    with open(os.path.join(OUT, f'{name}_fit.json'), 'w') as f:
        json.dump(meta, f, indent=1, ensure_ascii=False)
    pv = C.grade(store[:int(H * 0.62)], P['sid'], bloom=False)
    img = Image.fromarray(np.clip(pv, 0, 255).astype(np.uint8))
    dr = ImageDraw.Draw(img)
    for r in res:
        uu = ((P['sun_az'] + r['d_az_from_sun']) / 360 + 0.5) % 1 * W
        vv = (90 - r['el']) / 180 * H
        dr.ellipse([uu - 4, vv - 4, uu + 4, vv + 4], outline=(255, 0, 0))
    img.save(os.path.join(OUT, f'{name}_preview.png'))
    print(name, 'yaw', round(yaw, 1), 'sun el', round(el_hdri, 2), 'removed sun irr', np.round(Esun, 3))
    for r in res:
        print('  %-28s target %s got %s err %.1f' % (r['label'][:26], r['target'], r['result'], r['err_codes']))
    return store, meta


if __name__ == '__main__':
    for n in (sys.argv[1:] or PRESETS):
        fit(n)
