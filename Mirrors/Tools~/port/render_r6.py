"""总导演终审 r3 #6：用真贴图 + shader 逻辑（back_port.py）渲镜背、新铭文、镜缘串珠与过镜那几帧。
    ~/bpy/bin/python render_r6.py      -> Mirrors/Docs~/iterations/r6_*.png + r6_sheet.png"""
import math, os, sys, json
import numpy as np
from PIL import Image, ImageDraw
import mirror_port as M

OUT = os.path.join(M.REPO, 'Mirrors', 'Docs~', 'iterations')
W, H, SS = 960, 540, 2
m1, m10 = M.SCH['mirrors'][0], M.SCH['mirrors'][9]


def t_at(m, dy):
    """t where the face point under the eye is at EYE.y + dy (bisection on the driver's motion)."""
    a, b = m['t_cross'] - 3.0, m['t_cross'] + 3.0
    for _ in range(60):
        c = 0.5 * (a + b)
        if M.mirror_state(m, c)['y_car'] - M.EYE[1] < dy: a = c
        else: b = c
    return 0.5 * (a + b)


def rim_eye(m, t, dist=14.0, up=2.0):
    st = M.mirror_state(m, t)
    c = st['c']; R = st['R']
    u = np.array([1.0, 0.0, 0.0])                       # look at the rim's east point from outside
    tgt = c + u * (0.49 * st['D']) + np.array([0, 0.002 * st['D'], 0])
    eye = tgt + u * dist + np.array([0, up, 0])
    v = tgt - eye; v /= np.linalg.norm(v)
    yaw = math.degrees(math.atan2(v[0], v[2])); pitch = math.degrees(math.asin(v[1]))
    return eye, yaw, pitch


def toward_centre(m, pitch):
    cx, cz = m['centre_xz']
    return math.degrees(math.atan2(cx - M.EYE[0], cz - M.EYE[2])), pitch


SHOTS = []
# in the ride (the eye at the bus seat)
SHOTS.append(('m1_back_+0.3s', dict(t=m1['t_cross'] + 0.3, yaw=0, pitch=75), '第 1 面过镜后 0.3 s：眼还在 1.2 m 厚的板里（镜背 0.68 s 才过眼），薄平面：看穿'))
SHOTS.append(('m1_back_+0.8s', dict(t=m1['t_cross'] + 0.8, yaw=0, pitch=75), '第 1 面镜背，过镜后 0.8 s（镜背在头顶 0.2 m），抬头 75°'))
y, p = toward_centre(m1, 25)
SHOTS.append(('m1_back_+1.0s', dict(t=m1['t_cross'] + 1.0, yaw=y, pitch=p), '第 1 面镜背，过镜后 1.0 s（溶解中），朝镜心抬头 25°'))
y, p = toward_centre(m10, 20)
SHOTS.append(('m10_back_+0.5s', dict(t=m10['t_cross'] + 0.5, yaw=y, pitch=p), '第 10 面镜背，过镜后 0.5 s，朝镜心抬头 20°'))
SHOTS.append(('m10_back_+1.0s', dict(t=m10['t_cross'] + 1.0, yaw=y, pitch=35), '第 10 面镜背，过镜后 1.0 s（溶解中），朝镜心抬头 35°'))
e, y, p = rim_eye(m1, 1028.0, dist=14.0, up=6.0)
SHOTS.append(('m1_rim_14m', dict(t=1028.0, yaw=y, pitch=p, eye=e, fov=30), '第 1 面镜缘正前方 14 m、高 6 m，30° 视角：连珠乳钉一行'))
SHOTS.append(('m1_cross_-0.2m', dict(t=t_at(m1, -0.2), yaw=0, pitch=-30), '过镜：镜面在眼下 0.2 m，向下 30°'))
SHOTS.append(('m1_cross_+0.2m', dict(t=t_at(m1, +0.2), yaw=0, pitch=30), '过镜：镜面在眼上 0.2 m（眼在板里：薄平面，看穿，暖色是银河核心）'))
# lookdev (not in the ride): the whole back of mirror 1, dissolve frozen at 0, from 22 m below its centre
st = M.mirror_state(m1, m1['t_cross'] + 1.0)
LD_EYE = [m1['centre_xz'][0], st['c'][1] - 0.6 - 22.0, m1['centre_xz'][1]]
SHOTS.append(('lookdev_m1_back', dict(t=m1['t_cross'] + 1.0, yaw=0, pitch=89.9, eye=LD_EYE, fov=90, ovr={1: dict(dissolve=0.0, appear=1.0)}),
              '镜背 lookdev（不是旅程里的画面）：第 1 面整个镜背，溶解冻结，从镜心下方 22 m 仰视'))
SHOTS.append(('lookdev_m1_band', dict(t=m1['t_cross'] + 1.0, yaw=0, pitch=60, eye=[LD_EYE[0], LD_EYE[1] + 14.0, LD_EYE[2] + 6.0], fov=40, ovr={1: dict(dissolve=0.0, appear=1.0)}),
              '镜背 lookdev：铭文带、栉齿、锯齿、流云带（溶解冻结，40° 视角）'))

if __name__ == '__main__':
    only = sys.argv[1:]
    log = {}
    for name, kw, cap in SHOTS:
        if only and name not in only:
            continue
        M.OVERRIDE.clear(); M.OVERRIDE.update(kw.get('ovr', {}))
        codes, info = M.frame(kw['t'], kw['yaw'], kw['pitch'], w=W, h=H, ss=SS, eye=kw.get('eye'), fov=kw.get('fov', 90.0))
        p = os.path.join(OUT, 'r6_%s.png' % name)
        Image.fromarray(np.clip(codes, 0, 255).astype(np.uint8)).save(p)
        log[name] = dict(t=round(kw['t'], 3), caption=cap, APL=info['APL'], EV=info['EV'])
        print(name, log[name], flush=True)
    if not only:
        tiles = []
        for name, kw, cap in SHOTS:
            im = Image.open(os.path.join(OUT, 'r6_%s.png' % name)).resize((640, 360))
            canvas = Image.new('RGB', (640, 384), 'white'); canvas.paste(im, (0, 24))
            ImageDraw.Draw(canvas).text((6, 5), '%s  t=%.2f  APL %.0f' % (name, kw['t'], log[name]['APL']), fill=(0, 0, 0))
            tiles.append(canvas)
        sheet = Image.new('RGB', (1280, 384 * ((len(tiles) + 1) // 2)), 'white')
        for i, t in enumerate(tiles):
            sheet.paste(t, ((i % 2) * 640, (i // 2) * 384))
        sheet.save(os.path.join(OUT, 'r6_sheet.png'))
        json.dump(log, open(os.path.join(OUT, 'r6.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
