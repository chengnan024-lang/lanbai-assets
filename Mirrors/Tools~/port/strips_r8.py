"""总导演 10-26：三条对照条带（自查修正之后）。
  A 第 9 面过镜后的碎块：r7（块一帧没了，BREAKUP_SHRINK=0）对 现在（先缩向块心），正前方偏下 −12°（序列 m9 的视向），1113.06 → 1113.56 每 0.1 s
  B 第 13 面远 → 近的新时间 1131.31 → 1137.31，向下 −45°
  C 第 12 面的尘：增益 1 对 0.5，1138.67（冲击里），侧上方 yaw 90° +30°（序列 wsu）与向下 −60°
    BREAKUP_SHRINK=0 ~/bpy/bin/python strips_r8.py A0 ; ~/bpy/bin/python strips_r8.py A1 B C1 ; DUST_GAIN_IMPACT=1 ~/bpy/bin/python strips_r8.py C0 ; ~/bpy/bin/python strips_r8.py sheet
    -> Mirrors/Docs~/iterations/r8_*.png"""
import os, sys, json
import numpy as np
from PIL import Image, ImageDraw
import mirror_port as M

OUT = os.path.join(M.REPO, 'Mirrors', 'Docs~', 'iterations')
W, H = 640, 360
L = np.array([0.2126, 0.7152, 0.0722])
A_T = [1113.06, 1113.16, 1113.26, 1113.36, 1113.46, 1113.56]
B_T = [1129.31, 1131.31, 1132.81, 1134.31, 1135.81, 1137.31, 1138.31]
C_V = [(90, 30), (0, -60)]


def shot(name, t, yaw, pitch):
    c, info = M.frame(t, yaw, pitch, w=W, h=H)
    Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'r8_%s.png' % name))
    lin = (np.clip(c, 0, 255) / 255.0) ** 2.2 @ L
    rec = dict(t=t, view=[yaw, pitch], APL=info['APL'], L=round(float(lin.mean()), 5))
    o = info['owner']
    if (o == 131).any():
        lu = c @ L
        rec['m13_ring'] = round(float(lu[o == 131].mean()), 1); rec['m13_face'] = round(float(lu[o == 130].mean()), 1)
    print(name, rec, flush=True)
    json.dump(rec, open(os.path.join(OUT, 'r8_%s.json' % name), 'w'))


def sheet():
    log = json.load(open(os.path.join(OUT, 'r8.json'))) if os.path.exists(os.path.join(OUT, 'r8.json')) else {}
    rows = [('A0  mirror 9 chunks, r7: a chunk vanishes in one frame (1113.36: the back shows, L dips 0.034 -> 0.026)', ['A0_%.2f' % t for t in A_T]), ('A1  now: chunks shrink to their centre before they drop (L flat)', ['A1_%.2f' % t for t in A_T]),
            ('B   mirror 13 far -> near, 1131.31 -> 1137.31 (down -45 deg); mirror 12 covers the view from ~1134', ['B_%.2f' % t for t in B_T]),
            ('C   mirror 12 dust at 1138.67 (impact): gain 1 | 0.5 at side-up yaw 90 +30 (wsu), then gain 1 | 0.5 down -60', ['C0_90_30', 'C1_90_30', 'C0_0_-60', 'C1_0_-60'])]
    tw, th = 320, 180
    cols = max(len(r[1]) for r in rows)
    sh = Image.new('RGB', (tw * cols, (th + 34) * len(rows)), 'white')
    d = ImageDraw.Draw(sh)
    for ri, (title, names) in enumerate(rows):
        y = ri * (th + 34)
        d.text((4, y + 2), title, fill=(0, 0, 0))
        for ci, n in enumerate(names):
            im = Image.open(os.path.join(OUT, 'r8_%s.png' % n)).resize((tw, th))
            sh.paste(im, (ci * tw, y + 30))
            jp = os.path.join(OUT, 'r8_%s.json' % n)
            r = json.load(open(jp)) if os.path.exists(jp) else log[n]
            log[n] = r
            lab = 't %.2f  APL %.0f  L %.4f' % (r['t'], r['APL'], r['L']) + ('  ring %.0f face %.0f' % (r['m13_ring'], r['m13_face']) if 'm13_ring' in r else '')
            d.text((ci * tw + 4, y + 16), lab, fill=(60, 60, 60))
    sh.save(os.path.join(OUT, 'r8_sheet.png'))
    json.dump(log, open(os.path.join(OUT, 'r8.json'), 'w'), indent=1)
    for n in log:
        if os.path.exists(os.path.join(OUT, 'r8_%s.json' % n)):
            os.remove(os.path.join(OUT, 'r8_%s.json' % n))


if __name__ == '__main__':
    for a in sys.argv[1:]:
        if a in ('A0', 'A1'):
            for t in A_T:
                shot('%s_%.2f' % (a, t), t, 0, -12)
        elif a == 'B':
            for t in B_T:
                shot('B_%.2f' % t, t, 0, -45)
        elif a in ('C0', 'C1'):
            for yaw, p in C_V:
                shot('%s_%d_%d' % (a, yaw, p), 1138.67, yaw, p)
        elif a == 'sheet':
            sheet()
