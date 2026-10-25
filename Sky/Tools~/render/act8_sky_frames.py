"""第 8 幕的天（只有天，没有车厢 / 云卡 / 海）：按「云」的驱动（pkg/clouds Act08_Dusk/Runtime/LanbaiAct08Driver.cs）的时间表写全局量，
在 CPU 上跑真的 Lanbai/Sky，按 S8 / S8b + 第 8 幕的蓝时 ΔEV（Act08_Grade.json：993.06 → 1001.21 到 −1.5）调色。
看四件事（第 8 幕终审，天空这边）：日线的形状和收缩、暮 HDRI 太阳右边的台阶、蓝时的地平线缝 / 日侧、F12 前后的过渡带。
-> Sky/Docs~/act8/act8_sky_frames.png（正前方 90°）+ act8_sun_line.png（日线小块：方位 ±16°、仰角 ±4°）
+ act8_fade_986_994.png（F12 的淡变，每 0.25 s 一张：上面三行正前方，下面三行抬头 35°）"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw, ImageFont
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import sky_cpu as S, grade as G, make_presets as MP, test_sequence as TS
from shader_cpu import camera_dirs, REPO

F10e, F12 = 956.36, 987.06
OUT = os.path.join(REPO, 'Sky', 'Docs~', 'act8')


def ss(x):
    x = min(max(x, 0.0), 1.0)
    return x * x * (3 - 2 * x)


def dev(t):
    return float(np.interp(t, [993.06, 1001.21, 1009.21], [0.0, -1.502, 0.0]))


def state(t, P):
    """= LanbaiAct08Driver.Sky() + its sun line / sun direction (the presets from Sky/SkyPresets.json)"""
    if t < F10e:
        g = TS.globs_of(P['dusk_8i'])
    elif t < F10e + 8:
        g = TS.blend(P['dusk_8i'], P['dusk_8ii'], ss((t - F10e) / 8))[0]
    elif t < F12:
        g = TS.globs_of(P['dusk_8ii'])
    elif t < F12 + 6:
        g = TS.blend(P['dusk_8ii'], P['blue_hour'], ss((t - F12) / 6))[0]
    else:
        g = TS.globs_of(P['blue_hour'])
    g = dict(g)
    k = 1 - ss((t - F12) / 6.0)
    line = 10.0 * ss((t - 959.36) / 5.0) * k
    g['_Udon_SunDisc'] = [k, 0.265, line, 1.0]
    if t >= F10e:
        el = np.radians(0.5 * (1 - ss((t - F10e) / 3.0)))
        g['_Udon_SunDir'] = [0.0, float(np.sin(el)), float(np.cos(el)), 1.0]
    wb = ss((t - F12) / 6.0)
    return g, wb


def grade(lin, wb, t):
    a = np.clip(G.grade(lin, 'S8', ev=dev(t)), 0, 255)
    if wb <= 0:
        return a
    b = np.clip(G.grade(lin, 'S8b', ev=dev(t)), 0, 255)
    return a * (1 - wb) + b * wb


def font(px):
    return ImageFont.truetype(os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf'), px)


def main():
    P, _ = TS.load()
    S.renderer().tex.clear()
    S.set_cube('_CubeA', S.load_hdr(MP.P['dusk_8i']['hdri_file']))
    S.set_tex('_GlowTex', S.load_glow(4))
    os.makedirs(OUT, exist_ok=True)
    W, H = 640, 360
    d = camera_dirs(W, H, 90, 0, 0).astype(np.float32)
    times = [(940.36, '940.36 论点之帧（8-i）：太阳右边不再有台阶'), (964.4, '964.4 日线长满（±10°）'), (971.4, '971.4 日线'),
             (987.06, 'F12 987.06'), (988.5, '988.5 日线开始烧尽'), (990.0, '990 烧到一半；蓝从天顶往下来'),
             (991.5, '991.5'), (993.06, '993.06 蓝时（ΔEV 0）'), (1001.21, '1001.21 蓝时末（ΔEV −1.5）')]
    rows = []
    meas = []
    for t, label in times:
        g, wb = state(t, P)
        c = grade(S.render(d, {}, g).reshape(H, W, 3), wb, t)
        im = Image.fromarray(c.astype(np.uint8))
        ImageDraw.Draw(im).text((8, 6), label, fill=(255, 255, 255), font=font(16))
        rows.append(np.asarray(im))
        L, A, B = G.lab(c); C = np.hypot(A, B); h = np.degrees(np.arctan2(B, A)) % 360
        meas.append(dict(t=t, APL=round(G.apl(c), 1), red_clip_pct=round(100 * float((c[..., 0] >= 254).mean()), 2),
                         lavender_pct=round(100 * float(((h >= 290) & (h <= 330) & (C > 8) & (L > 40)).mean()), 3)))
        print(json.dumps(meas[-1]))
    sheet = np.concatenate([np.concatenate(rows[i:i + 3], 1) for i in range(0, 9, 3)], 0)
    Image.fromarray(sheet).save(os.path.join(OUT, 'act8_sky_frames.png'))
    # the sun line, 0.04 deg / px
    Ws, Hs = 800, 200
    az = np.radians(np.linspace(-16, 16, Ws)); el = np.radians(np.linspace(4, -4, Hs))
    A_, E_ = np.meshgrid(az, el)
    ds = np.stack([np.sin(A_) * np.cos(E_), np.sin(E_), np.cos(A_) * np.cos(E_)], -1).reshape(-1, 3).astype(np.float32)
    strip = []
    for t in (961.0, 962.5, 964.4, 971.4, 987.06, 988.5, 990.0, 991.5, 992.5):
        g, wb = state(t, P)
        c = grade(S.render(ds, {}, g).reshape(Hs, Ws, 3), wb, t)
        im = Image.fromarray(c.astype(np.uint8)); ImageDraw.Draw(im).text((6, 4), '%.2f' % t, fill=(255, 255, 255), font=font(14))
        strip.append(np.asarray(im))
    Image.fromarray(np.concatenate(strip, 0)).save(os.path.join(OUT, 'act8_sun_line.png'))
    # the F12 fade, every 0.25 s (act 8 final review A1: no hard edge, no sudden cut), front and up 35 deg
    fade = []
    for pitch in (0, 35):
        dd = camera_dirs(240, 135, 90, 0, pitch).astype(np.float32)
        row = []
        for t in np.arange(986.0, 994.01, 0.25):
            g, wb = state(t, P)
            im = Image.fromarray(grade(S.render(dd, {}, g).reshape(135, 240, 3), wb, t).astype(np.uint8))
            ImageDraw.Draw(im).text((4, 2), '%.2f' % t, fill=(255, 255, 255), font=font(11))
            row.append(np.asarray(im))
        fade.append(np.concatenate([np.concatenate(row[i:i + 11], 1) for i in range(0, 33, 11)], 0))
    Image.fromarray(np.concatenate(fade, 0)).save(os.path.join(OUT, 'act8_fade_986_994.png'))
    json.dump(meas, open(os.path.join(OUT, 'act8_sky_frames.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
