"""第 13 面最后 10 秒的对照（总导演意见第 5 条）：1137.58 → 1149.31 每 0.5 s 一帧，正前方 + 向下看；量镜缘对背景的
对比（显示级差，镜缘两侧 3 px 的 luma 中位差）和镜缘的角速度（俯角对时间的导数，°/s）。规则：对比 > 4 级时角速度 ≤ 3°/s。

    python mirror13_study.py <scheme> [w h]      scheme: A（现在的：清楚的镜缘） | C（快的那一段镜缘柔化，被白吃掉）
-> Mirrors/Docs~/iterations/m13_<scheme>_sheet.png + m13_<scheme>.json
"""
import json, math, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from scipy.ndimage import binary_dilation
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import mirror_port as MP

OUT = os.path.join(MP.REPO, 'Mirrors', 'Docs~', 'iterations')
M13 = MP.SCH['mirrors'][12]
R13 = M13['radius_m']


def depression(t):
    return math.degrees(math.atan(max(MP.EYE[1] - MP.herm(M13['motion']['knots'], t), 0) / R13))


def rim_speed(t, dt=0.05):
    return abs(depression(t + dt) - depression(t - dt)) / (2 * dt)


def contrast(codes, owner):
    luma = codes @ np.array([0.2126, 0.7152, 0.0722])
    m13 = (owner // 10 == 13)
    sky = owner < 0
    if m13.sum() < 50 or sky.sum() < 50:
        return None
    edge_in = m13 & binary_dilation(sky, iterations=3)
    edge_out = sky & binary_dilation(m13, iterations=3)
    if edge_in.sum() < 20 or edge_out.sum() < 20:
        return None
    return round(float(abs(np.median(luma[edge_in]) - np.median(luma[edge_out]))), 1)


def main():
    scheme = sys.argv[1] if len(sys.argv) > 1 else 'A'
    w = int(sys.argv[2]) if len(sys.argv) > 2 else 480
    h = int(sys.argv[3]) if len(sys.argv) > 3 else 270
    MP.RIM_SCHEME = scheme
    if scheme == 'D':
        # rim depression: fast while the rim is soft (1139.31 -> 1142.9), then <= 3 deg/s (1142.9 -> F16)
        import importlib.util, io, contextlib
        spec = importlib.util.spec_from_file_location('ms', os.path.join(HERE, '..', 'schedule', 'make_schedule.py'))
        ms = importlib.util.module_from_spec(spec)
        with contextlib.redirect_stdout(io.StringIO()):
            try:
                spec.loader.exec_module(ms)
            except SystemExit:
                pass
        kt = np.array([ms.T13A, 1141.3, 1142.9, 1144.6, 1146.31, ms.F16]); kp = np.array([ms.phi0, 30, 11.5, 6.4, 2.2, 0])
        km = np.array([0, -22, -2.9, -2.9, -1.6, -0.4])
        far = [k for k in M13['motion']['knots'] if k[0] < ms.T13A]
        tt = np.arange(ms.T13A, ms.F16 + 1e-6, 0.04)
        dep = R13 * np.tan(np.radians(ms.herm(kt, kp, km, tt)))
        y = MP.EYE[1] - dep
        v = np.gradient(y, tt)
        M13['motion']['knots'] = far + [[float(a), float(b), float(c)] for a, b, c in zip(tt, y, v)]
    ts = [round(1137.58 + 0.5 * i, 2) for i in range(24)] + [1149.30]
    if len(sys.argv) > 4:
        ts = [t for t in ts if float(sys.argv[4]) <= t <= float(sys.argv[5])]
    rows = []
    frames = []
    for t in ts:
        row = dict(t=t, depression_deg=round(depression(t), 2), rim_deg_per_s=round(rim_speed(t), 2))
        for vn, yaw, pitch in (('fwd', 0, 6), ('down', 0, -60)):
            c, info = MP.frame(t, yaw, pitch, w, h, dust=False)
            row[vn + '_contrast'] = contrast(c, info['owner'])
            row[vn + '_APL'] = info['APL']
            frames.append((t, vn, np.clip(c, 0, 255).astype(np.uint8)))
        lim = row['rim_deg_per_s'] <= 3.0 or all((row[k] is None or row[k] <= 4.0) for k in ('fwd_contrast', 'down_contrast'))
        row['rule_ok'] = bool(lim)
        rows.append(row)
        print(json.dumps(row), flush=True)
    json.dump(rows, open(os.path.join(OUT, 'm13_%s.json' % scheme), 'w'), indent=1)
    tw, th = 240, 135
    cols = 10
    sh = Image.new('RGB', (cols * tw, ((len(frames) + cols - 1) // cols) * (th + 30)), (14, 14, 18))
    d = ImageDraw.Draw(sh)
    fnt = ImageFont.truetype(os.path.join(MP.REPO, 'Fonts', 'Originals~', 'SourceHanSerifCN-Regular.otf'), 12)
    byt = {r['t']: r for r in rows}
    for i, (t, vn, im) in enumerate(frames):
        x, y = (i % cols) * tw, (i // cols) * (th + 30)
        sh.paste(Image.fromarray(im).resize((tw, th), Image.LANCZOS), (x, y + 30))
        r = byt[t]
        d.text((x + 3, y + 2), '%.2f %s 俯角 %.1f° %.1f°/s' % (t, vn, r['depression_deg'], r['rim_deg_per_s']), fill=(220, 220, 220), font=fnt)
        d.text((x + 3, y + 15), '对比 %s 级 APL %s %s' % (r[vn + '_contrast'], r[vn + '_APL'], '' if r['rule_ok'] else '✗'), fill=(220, 180, 160) if not r['rule_ok'] else (170, 200, 170), font=fnt)
    sh.save(os.path.join(OUT, 'm13_%s_sheet.png' % scheme))


if __name__ == '__main__':
    main()
