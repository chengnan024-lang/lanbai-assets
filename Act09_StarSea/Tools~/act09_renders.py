"""第 9 幕参考帧：驱动的逻辑（LanbaiAct09Driver.LanbaiTick）在 Python 里复刻，天由 CPU 跑的 Lanbai/Sky 代码给，星按
Lanbai/StarPoints 的公式贴，调色 S8b / S9a / S9b（引擎 + bloom；交叉淡化的那几段按码值插值近似）。没有镜子、没有车厢、
没有天问的字（字由字体套件画）。-> Act09_StarSea/Docs~/act09_frames.png + Data/frames.json"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
sys.path.insert(0, HERE)
import sky_cpu as S, grade as G, stars_cpu as SC
from shader_cpu import camera_dirs
import make_presets as MP
from act09_calib import load_glow, lum_display

W, H = 960, 540
FWHM = 1.6 * W / 1920.0
A = json.load(open(os.path.join(REPO, 'Act09_StarSea', 'Act09_StarSea.json')))
L = A['labels']
VIEWS = [('正前方', 0, 0), ('抬头 +60°', 0, 60), ('银心 −30° / +12°', -30, 12)]
TIMES = [(L['act9_start'], '1001.21 蓝时末 · 第一批星'), (1005.21, '1005.21 变暗中（前方地平线带最后）'), (1008.6, '1008.6 天顶最后一颗星'),
         (L['F13'] - 0.02, 'F13 前一帧（天问时的黑）'), (L['F13'], 'F13 这一帧：所有星同时出现'), (L['F13'] + A['ignition']['seconds'] / 2, '点燃一半'),
         (L['ignition_full'], '点燃满（%.2f）' % L['ignition_full']), (1100.0, '1100 狂喜中段（x = 0.62）'), (1137.0, '1137 尾声（x = 0.91）')]


def ign(s):
    g = A['ignition']['g']; st = A['ignition']['table_step_s']
    if s <= 0: return 0.0
    f = s / st; i = int(f)
    return 1.0 if i >= len(g) - 1 else g[i] + (g[i + 1] - g[i]) * (f - i)


def state(t):
    p = MP.P['blue_hour']
    gl = dict(p['globals'])
    x = min(max((t - L['F13']) / (L['F16'] - L['F13']), 0), 1); x25 = x ** 2.5
    night = min(max((t - L['act9_start']) / (L['dark_end'] - L['act9_start']), 0), 1)
    g = ign(t - L['F13']) * (1 + 0.8 * x25)
    gl['_Udon_SkyBlend'] = [0, 1, night, 1]; gl['_Udon_SkyFx'] = [0, 0.85, 0, 1]; gl['_Udon_GalaxyGain'] = [g, 0, 0, 1]
    star = dict(gain=1.0 if t >= L['F13'] else 0.0, boost=4 + 4 * x25, count=50 + 150 * x25)
    fs = A['first_stars']
    a = np.clip((t - fs['appear'][0]) / (fs['appear'][1] - fs['appear'][0]), 0, 1); a = a * a * (3 - 2 * a)
    sweep = np.clip((t - (L['act9_start'] + 2.0)) / (L['dark_end'] - L['act9_start'] - 2.0), 0, 1)
    soft = 0.5 * fs['out_s'] / 6.0
    thr = -soft + (1 + 2 * soft) * sweep
    if x25 > 0:
        prof = ('S9a', 'S9b', x25)
    elif t < L['act9_start']:
        prof = ('S8b', 'S8b', 0)
    else:
        prof = ('S8b', 'S9a', night)
    return gl, p['material'], star, (a * fs['peak'], thr, soft), prof


def render(t, yaw, pitch):
    gl, mat, star, first, prof = state(t)
    d = camera_dirs(W, H, 90, yaw, pitch).astype(np.float32)
    img = S.render(d, mat, gl).reshape(H, W, 3)
    c = SC.catalogue()
    if star['gain'] > 0:
        pk = SC.flux(c['mag'], c['rank'], 1.6, 0.0, 0.5, star['count'], star['boost']) * star['gain']
        SC.splat(img, W, H, 90, yaw, pitch, c['dir'], pk, c['col'], FWHM)
        q = A['question_stars']['stars']
        SC.splat(img, W, H, 90, yaw, pitch, np.array([s['dir'] for s in q]), np.array([s['peak'] for s in q]), np.tile([0.96, 0.98, 1.06], (len(q), 1)), FWHM)
    gain, thr, soft = first
    if gain > 0 and t < L['dark_end'] + 0.8:
        fs = A['first_stars']['stars']
        o = np.array([s['order'] for s in fs]); vis = np.clip((o - (thr - soft)) / (2 * soft + 1e-6), 0, 1); vis = vis * vis * (3 - 2 * vis)
        pk = SC.flux(np.array([s['mag'] for s in fs]), np.full(len(fs), 9999.0), 1.6, 0.0, 0.5, 0, 1) * gain * vis
        SC.splat(img, W, H, 90, yaw, pitch, np.array([s['dir'] for s in fs]), pk, np.tile([0.94, 1.0, 1.10], (len(fs), 1)), FWHM)
    a, b, w = prof
    ca = np.clip(G.grade(img, a), 0, 255)
    cb = ca if b == a else np.clip(G.grade(img, b), 0, 255)
    return ca * (1 - w) + cb * w


def font(px):
    return ImageFont.truetype(os.path.join(REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf'), px)


def main():
    S.renderer().tex.clear(); S.set_tex('_GlowTex', load_glow())
    tw, th = 400, 225
    sheet = Image.new('RGB', (tw * len(VIEWS) + 300, th * len(TIMES)), (16, 16, 20))
    dr = ImageDraw.Draw(sheet)
    meas = []
    for r, (t, label) in enumerate(TIMES):
        row = {'t': t, 'label': label}
        for k, (vn, yaw, pitch) in enumerate(VIEWS):
            c = render(t, yaw, pitch)
            row[vn] = dict(APL=round(G.apl(c), 1), L=round(lum_display(c), 5))
            im = Image.fromarray(c.astype(np.uint8)).resize((tw, th), Image.LANCZOS)
            sheet.paste(im, (300 + k * tw, r * th))
            if r == 0:
                pass
            if t in (L['ignition_full'], L['F13']) and k == 0:
                Image.fromarray(c.astype(np.uint8)).save(os.path.join(REPO, 'Act09_StarSea', 'Docs~', 'frame_%s_front.png' % ('F13' if t == L['F13'] else 'full')))
        dr.text((10, r * th + 10), label, fill=(230, 230, 230), font=font(17))
        dr.text((10, r * th + 40), '  '.join('%s APL %.0f' % (vn[:2], row[vn]['APL']) for vn, _, _ in VIEWS), fill=(170, 170, 170), font=font(13))
        meas.append(row); print(json.dumps(row, ensure_ascii=False))
    for k, (vn, _, _) in enumerate(VIEWS):
        dr.text((300 + k * tw + 8, 6), vn, fill=(255, 255, 255), font=font(15))
    sheet.save(os.path.join(REPO, 'Act09_StarSea', 'Docs~', 'act09_frames.png'))
    json.dump(meas, open(os.path.join(REPO, 'Act09_StarSea', 'Data', 'frames.json'), 'w'), indent=1, ensure_ascii=False)


if __name__ == '__main__':
    main()
