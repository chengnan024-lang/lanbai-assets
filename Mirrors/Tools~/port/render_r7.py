"""总导演终审（10-25）美术项的重渲：M-1 钮、M-2 镜背的天、M-3 溶解碎片、M-4 第 13 面的远处圆盘。
    ~/bpy/bin/python render_r7.py [shot ...]   -> Mirrors/Docs~/iterations/r7_*.png + r7_sheet.png + r7.json"""
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw
import mirror_port as M
import render_r6 as R6

OUT = os.path.join(M.REPO, 'Mirrors', 'Docs~', 'iterations')
W, H, SS = 960, 540, 2
m1, m10, m13 = M.SCH['mirrors'][0], M.SCH['mirrors'][9], M.SCH['mirrors'][12]
SHOTS = []
y1, _ = R6.toward_centre(m1, 0)
SHOTS.append(('M1_knob_m1_+0.9s', dict(t=m1['t_cross'] + 0.9, yaw=y1, pitch=35), 'M-1：第 1 面过镜后 0.9 s，朝镜心抬头 35°：钮在车旁边'))
SHOTS.append(('M1_knob_m1_+1.4s', dict(t=m1['t_cross'] + 1.4, yaw=y1, pitch=20), 'M-1：+1.4 s，朝镜心抬头 20°'))
SHOTS.append(('M2_m1_back_+0.8s', dict(t=m1['t_cross'] + 0.8, yaw=0, pitch=75), 'M-2：第 1 面镜背 +0.8 s，抬头 75°（无极点的天）'))
SHOTS.append(('M2_m1_back_+1.0s', dict(t=m1['t_cross'] + 1.0, yaw=0, pitch=75), 'M-2：+1.0 s，抬头 75°'))
for m, tag in ((m1, 'm1'), (m10, 'm10')):
    yc, _ = R6.toward_centre(m, 0)
    for dt in (0.5, 1.0, 1.5):
        SHOTS.append(('M3_%s_+%.1fs' % (tag, dt), dict(t=m['t_cross'] + dt, yaw=yc, pitch=28), 'M-3：%s 溶解 +%.1f s，朝镜心抬头 28°' % (tag, dt)))
for t in (1065.0, 1076.0, 1095.0):
    for p in (-45, -60, -80):
        SHOTS.append(('M4_%d_%d' % (t, -p), dict(t=t, yaw=0, pitch=p), 'M-4：%.0f s 向下 %d°（第 13 面远处的模糊圆盘）' % (t, p)))


def rim_luma(codes, info):
    """mirror 13 face pixels in the outer quarter of its disc (owner 130) -> mean luma (8-bit code)."""
    o = info['owner']
    m = o == 130
    if not m.any():
        return None
    luma = codes @ np.array([0.2126, 0.7152, 0.0722])
    return round(float(luma[m].mean()), 1)


if __name__ == '__main__':
    only = sys.argv[1:]
    log = {}
    lp = os.path.join(OUT, 'r7.json')
    if os.path.exists(lp):
        log = json.load(open(lp, encoding='utf-8'))
    for name, kw, cap in SHOTS:
        if only and name not in only:
            continue
        codes, info = M.frame(kw['t'], kw['yaw'], kw['pitch'], w=W, h=H, ss=SS, eye=kw.get('eye'), fov=kw.get('fov', 90.0))
        Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'r7_%s.png' % name))
        log[name] = dict(t=round(kw['t'], 3), caption=cap, APL=info['APL'], m13_face_luma=rim_luma(codes, info))
        print(name, log[name], flush=True)
        json.dump(log, open(lp, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    if not only:
        tiles = []
        for name, kw, cap in SHOTS:
            im = Image.open(os.path.join(OUT, 'r7_%s.png' % name)).resize((480, 270))
            c = Image.new('RGB', (480, 290), 'white'); c.paste(im, (0, 20))
            extra = '' if log[name].get('m13_face_luma') is None else '  m13 luma %.0f' % log[name]['m13_face_luma']
            ImageDraw.Draw(c).text((4, 4), '%s  APL %.0f%s' % (name, log[name]['APL'], extra), fill=(0, 0, 0))
            tiles.append(c)
        cols = 3
        sheet = Image.new('RGB', (480 * cols, 290 * ((len(tiles) + cols - 1) // cols)), 'white')
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % cols) * 480, (i // cols) * 290))
        sheet.save(os.path.join(OUT, 'r7_sheet.png'))
