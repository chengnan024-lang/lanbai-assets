"""终审 M-11：镜背与镜缘的每处细节，在约 21 px/°（1920 px / 90°）下看不看得出——按时间表真算：
* 镜背只在过镜后、从下面看得到，而且溶解从镜缘往里走：一条带只有在“镜背已经在眼上方”且“溶解前沿还没走到它”的那段时间里看得到；
  这段时间里取它离眼最近的那一刻。
* 掠射：沿半径方向的细节（字高、笔画、乳钉的径向）按仰角的 sin 缩短；沿圆周方向的周期（栉齿、锯齿、乳钉间距）不缩短。
角大小 = 尺寸 / 距离 × 57.3 × 21.3 px；shader 在约 2 px 以下淡掉：≥ 3 px 看得出，2–3 px 勉强，< 2 px 看不出；“没机会”= 那条带在看得到之前已经溶解。
    ~/bpy/bin/python visibility_21ppd.py -> Mirrors/Docs~/visibility_21ppd.md"""
import json, math, os
import numpy as np
import mirror_port as M

PPD = 1920 / 90.0
EYE = M.EYE


def px(size, dist):
    return size / max(dist, 1e-3) * 57.2958 * PPD


def verdict(p):
    return '看得出' if p >= 3 else ('勉强' if p >= 2 else '看不出')


def back_window(m, q):
    """best (nearest) moment the back at r/R = q is overhead and not yet dissolved: (distance, elevation sin) or None."""
    best = None
    for t in np.arange(m['t_cross'], m['t_cross'] + 2.6, 0.02):
        st = M.mirror_state(m, t)
        if st is None:
            continue
        D, R, c = st['D'], st['R'], st['c']
        yk = c[1] - 0.015 * D
        h = yk - EYE[1]
        if h <= 0.05:
            continue                                            # the back is not above the eye yet
        front = R * (1.0 - st['dissolve'])                      # the dissolve front (rim -> centre), metres from the centre
        r = q * R
        if r > front:
            continue                                            # already dissolved there
        rcar = math.hypot(EYE[0] - c[0], EYE[2] - c[2])
        dh = max(abs(r - rcar), 0.0)
        dist = math.hypot(dh, h)
        sin_el = h / dist
        if best is None or dist < best[0]:
            best = (dist, sin_el, round(float(t - m['t_cross']), 2))
    return best


rows = []
for k in (0, 4, 9, 11):
    m = M.SCH['mirrors'][k]; D = m['diameter_m']; R = D / 2
    cx, cz = m['centre_xz']; rcar = math.hypot(EYE[0] - cx, EYE[2] - cz)
    # the rim beads: 3 s before the crossing, seen from above at the nearest rim
    st = M.mirror_state(m, m['t_cross'] - 3.0)
    h = EYE[1] - (st['c'][1] + 0.002 * D)
    d_rim = math.hypot(R - rcar, h)
    rows.append((k + 1, D, '镜缘连珠乳钉（间距 1.5 m，圆周方向）', 1.5, '%.1f' % d_rim, px(1.5, d_rim), None, '过镜前 3 s，最近的镜缘'))
    rowH = (0.08 * R) / max(math.floor(0.08 * R / 2.6), 1)
    cloudU = 2.623 * (0.07 * R / max(math.floor(0.07 * R / 1.4), 1))
    bands = [
        ('镜背：博局格的线（约 0.25 m，任意方向）', 0.40, 0.25, True),
        ('镜背：铭文一字（字高 %.1f m，半径方向）' % rowH, 0.76, rowH, True),
        ('镜背：铭文笔画（%.2f m，半径方向）' % (0.06 * rowH), 0.76, 0.06 * rowH, True),
        ('镜背：栉齿（周期 0.5 m，圆周方向）', 0.815, 0.5, False),
        ('镜背：锯齿（齿距 1.25 m，圆周方向）', 0.87, 1.25, False),
        ('镜背：流云单元（%.1f m，圆周方向）' % cloudU, 0.94, cloudU, False),
        ('镜背：钮（直径 %.1f m）' % (0.13 * D), 0.0, 0.13 * D, False),
    ]
    for name, q, size, radial in bands:
        w = back_window(m, q)
        if w is None:
            rows.append((k + 1, D, name, size, '—', None, '没机会', '镜背到眼上方之前，这条带已经溶解'))
            continue
        dist, sin_el, dt = w
        p = px(size * (sin_el if radial else 1.0), dist)
        rows.append((k + 1, D, name, size, '%.1f' % dist, p, None, '过镜后 %.2f s 最近（仰角 %.0f°）' % (dt, math.degrees(math.asin(min(sin_el, 1))))))

out = ['# 镜背与镜缘的细节在 21 px/° 下看不看得出（终审 M-11）', '',
       '由 `Tools~/port/visibility_21ppd.py` 按时间表算（溶解的前沿、镜背什么时候在眼上方、掠射的缩短都算进去）。'
       '角大小 = 尺寸 / 距离 × 57.3 × 21.3 px（1920 px / 90°）；shader 在约 2 px 以下按屏幕足迹淡掉，≥ 3 px 才算看得出。'
       '配图：`Docs~/iterations/r7_key_*.png`（1920×1080）。', '',
       '| 镜 | D (m) | 细节 | 尺寸 (m) | 最近距离 (m) | px | 结论 | 什么时候 |', '|---|---|---|---|---|---|---|---|']
for (k, D, name, size, dist, p, v, when) in rows:
    out.append('| %d | %.0f | %s | %.2f | %s | %s | %s | %s |' % (k, D, name, size, dist, '—' if p is None else '%.1f' % p, v or verdict(p), when))
out += ['', '读法：“没机会”的那几条带（外圈的铭文、栉齿、锯齿、流云）在旅程里只有在溶解的前沿上一闪而过；它们的设计在 `r6_lookdev_*` 里看。']
open(os.path.join(M.REPO, 'Mirrors', 'Docs~', 'visibility_21ppd.md'), 'w', encoding='utf-8').write('\n'.join(out) + '\n')
print('\n'.join(out[5:]))
