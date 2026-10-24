"""蓝白 · 白铜镜的 numpy 移植：驱动的逻辑（MirrorSchedule.json → 每面镜此刻的高度、可见度、凝聚、溶解）+
Lanbai/BronzeMirror、Lanbai/MirrorStars、Lanbai/MirrorDust 的数学（同名、同数），画在第 9 幕的天上
（天 = Act09_StarSea/Tools~/act09_renders.py 的同一套：Sky 的 CPU shader + 星表 + S9a/S9b 调色，总导演 10-24 第 1 条）。

    from mirror_port import frame
    codes, info = frame(t, yaw, pitch, w=960, h=540)       # sRGB 码值 (h, w, 3)，info = 量出的数

不是 Unity：没有车厢（标准台的车壳另合成）、镜面没有抛光纹和贴图、镜背只有剪影（它在星空前本来就是暗剪影）。
"""
import json, math, os, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.abspath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Act09_StarSea', 'Tools~'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
import act09_renders as A9                      # noqa: E402  (state(t), the sky material and globals)
import sky_cpu as S, grade as G, stars_cpu as SC   # noqa: E402
from shader_cpu import camera_dirs              # noqa: E402

SCH = json.load(open(os.path.join(REPO, 'Mirrors', 'MirrorSchedule.json'), encoding='utf-8'))
WHITE = json.load(open(os.path.join(REPO, 'Act10_White', 'WhiteSchedule.json'), encoding='utf-8'))
EYE = np.array(SCH['conventions']['eye'])
# spec §1 / LanbaiMirror.cginc
FACE_R, SAG, RHO = 0.48, 0.015, 7.6875
F0_FACE = G.hexlin('#D6CCB4'); F0_RIM = G.hexlin('#C9A873')
BACK_ALB = G.hexlin('#4F7A66'); AMB_GND = G.hexlin('#0E1830')
BACK_FILL = np.array([0.0105, 0.027, 0.0164])   # = _BackFill: the silhouette reads #16302A under S9a/S9b
EDGE = G.hexlin('#CDBF9C') * 0.8
BREAK_AMP, EDGE_W, APPEAR_S = 5.0, 0.3, 3.0
TONE = np.array([1.262, 0.974, 0.484])     # solved so that S9a / S9b show #CDBF9C (review r1 #5)
BRONZE_TONE = 1.0
RIM_SCHEME = 'A'          # mirror 13 study (mirror13_study.py)
RIM_SOFT_FROM = {'A': 0.80, 'C': 0.55, 'D': 0.55, 'E': 0.35, 'F': 0.25}


# ------------------------------------------------------------------------------------------------- driver logic
def herm(kn, t):
    kn = np.asarray(kn, float)
    x, y, m = kn[:, 0], kn[:, 1], kn[:, 2]
    t = min(max(t, x[0]), x[-1])
    i = min(max(np.searchsorted(x, t) - 1, 0), len(x) - 2)
    h = x[i + 1] - x[i]; s = (t - x[i]) / h
    return ((2 * s ** 3 - 3 * s ** 2 + 1) * y[i] + (s ** 3 - 2 * s ** 2 + s) * h * m[i] + (-2 * s ** 3 + 3 * s ** 2) * y[i + 1]
            + (s ** 3 - s ** 2) * h * m[i + 1])


def lin_knots(kn, t):
    kn = np.asarray(kn, float)
    return float(np.interp(t, kn[:, 0], kn[:, 1]))


def mirror_state(m, t):
    """what LanbaiMirrorsDriver computes for mirror m at time t (None = renderer off)."""
    a0, a1 = m['active']
    if not (a0 <= t <= a1):
        return None
    D = m['diameter_m']; R = D / 2
    y_car = herm(m['motion']['knots'], t)
    cx, cz = m['centre_xz']
    r_car = math.hypot(EYE[0] - cx, EYE[2] - cz) / D             # object units
    f = lambda r: math.sqrt(RHO * RHO - r * r) - (RHO - SAG)
    y_edge = y_car - f(min(r_car, FACE_R)) * D                  # world y of the face edge (object y = 0)
    vis = lin_knots(m['visibility_knots'], t)
    join = m['visibility_knots'][0][0]
    appear = min(max((t - join) / APPEAR_S, 0), 1)
    dis = 0.0 if m['dissolve'] is None else min(max((t - m['t_cross']) / (m['dissolve']['end'] - m['t_cross']), 0), 1)
    extra = 0.0
    if m['index'] == 13:
        extra = lin_knots(WHITE['mirror13_face_extra']['EV_knots'], t)
    rimsoft = 0.0
    if m['index'] == 13:
        if RIM_SCHEME == 'F':      # E with the slow part at <= 2.6 deg/s and the soft rim held to 1143.6
            rimsoft = 1.0 - min(max((t - 1143.6) / 1.0, 0), 1)
        elif RIM_SCHEME == 'E':      # as D, the rim stays soft (wider feather) until the speed is under 3 deg/s
            rimsoft = 1.0 - min(max((t - 1143.3) / 1.0, 0), 1)
        elif RIM_SCHEME == 'D':      # fast rise only while soft (to 1142.9), then <= 3 deg/s and sharp
            rimsoft = 1.0 - min(max((t - 1142.9) / 1.0, 0), 1)
        elif RIM_SCHEME == 'C':      # keep the rim soft through the fast rise, sharpen only in the hush (rim then <= 1 deg/s)
            rimsoft = 1.0 - min(max((t - 1145.5) / 2.0, 0), 1)
        else:
            rimsoft = 1.0 - min(max((t - (m['t_cross'] - 10.0)) / 4.0, 0), 1)   # soft while far, sharp in the last 10 s
    return dict(D=D, R=R, c=np.array([cx, y_edge, cz]), y_car=y_car, vis=vis, appear=appear, dissolve=dis, extra=extra,
                k=m['emission_k'], index=m['index'], rimsoft=rimsoft)


def pulse_ev(t):
    ev = 0.0
    for m in SCH['mirrors']:
        if m['pulse_EV'] <= 0:
            continue
        x = t - m['t_cross']
        if -0.08 < x <= 0:
            ev = max(ev, 0.35 * (x + 0.08) / 0.08)
        elif 0 < x < 0.35:
            ev = max(ev, 0.35 * (1 - x / 0.35))
    return ev


def white_ev(t):
    return lin_knots(WHITE['exposure']['dEV_knots'], t) if t < WHITE['labels']['F16_cut2'] else 0.0


# ------------------------------------------------------------------------------------------------- shader maths
def _hash(p):
    p = np.mod(p * 0.1031, 1.0)
    p = p + np.sum(p * (p[..., [1, 2, 0]] + 33.33), -1, keepdims=True)
    return np.mod((p[..., 0] + p[..., 1]) * p[..., 2], 1.0)


def noise(x):
    i = np.floor(x); f = x - i; u = f * f * (3 - 2 * f)
    def h(o):
        return _hash(i + np.array(o, float))
    nx00 = h((0, 0, 0)) * (1 - u[..., 0]) + h((1, 0, 0)) * u[..., 0]
    nx10 = h((0, 1, 0)) * (1 - u[..., 0]) + h((1, 1, 0)) * u[..., 0]
    nx01 = h((0, 0, 1)) * (1 - u[..., 0]) + h((1, 0, 1)) * u[..., 0]
    nx11 = h((0, 1, 1)) * (1 - u[..., 0]) + h((1, 1, 1)) * u[..., 0]
    return (nx00 * (1 - u[..., 1]) + nx10 * u[..., 1]) * (1 - u[..., 2]) + (nx01 * (1 - u[..., 1]) + nx11 * u[..., 1]) * u[..., 2]


def fbm(pM):
    return (noise(pM / 8.0) * 0.55 + noise(pM / 2.7 + 17.1) * 0.30 + noise(pM / 0.9 + 41.7) * 0.15) * 2 - 1


def schlick(f0, c):
    m = 1 - np.clip(c, 0, 1)
    return f0 + (1 - f0) * (m ** 5)[..., None]


_GLOW = [False]


def sky(dirs, mat, gl):
    if not _GLOW[0]:
        S.renderer().tex.clear(); S.set_tex('_GlowTex', S.load_glow(1)); _GLOW[0] = True
    return S.render(dirs.reshape(-1, 3).astype(np.float32), mat, gl).reshape(dirs.shape)


# ------------------------------------------------------------------------------------------------- the frame
def frame(t, yaw=0.0, pitch=0.0, w=960, h=540, ss=1, cabin=None, dust=True, extra_ev=None):
    gl, mat, star, first, prof = A9.state(t)
    W, H = w * ss, h * ss
    d = camera_dirs(W, H, 90, yaw, pitch).reshape(H, W, 3).astype(np.float64)
    img = sky(d, mat, gl)
    depth = np.full((H, W), np.inf)
    owner = np.full((H, W), -1)
    face_mask = {}
    info = dict(t=t, mirrors=[])
    states = [(m, mirror_state(m, t)) for m in SCH['mirrors']]
    for m, st in states:
        if st is None:
            continue
        D, R, c = st['D'], st['R'], st['c']
        Cs = c + np.array([0, (SAG - RHO) * D, 0])               # face sphere centre
        rho = RHO * D
        # ray / sphere (from the eye)
        oc = EYE - Cs
        b = (d * oc).sum(-1); cc = (oc * oc).sum() - rho * rho
        disc = b * b - cc
        sq = np.sqrt(np.maximum(disc, 0))
        tn = -b - sq
        under = tn <= 0                                          # the eye is inside the face sphere: the face is seen from below
        tt = np.where(under, -b + sq, tn)
        hit = (disc > 0) & (tt > 0) & ~under                     # Cull Back: inside the slab the eye sees through it
        P = EYE + d * tt[..., None]
        rr = np.hypot(P[..., 0] - c[0], P[..., 2] - c[2])
        face = hit & (rr <= FACE_R * D) & (P[..., 1] >= c[1] - 1e-6)
        # rim band (annulus plane at the band top) and the back (plane at the field, seen from below)
        yb = c[1] + 0.002 * D
        tb = (yb - EYE[1]) / np.where(np.abs(d[..., 1]) > 1e-9, d[..., 1], 1e-9)
        Pb = EYE + d * tb[..., None]; rb = np.hypot(Pb[..., 0] - c[0], Pb[..., 2] - c[2])
        band = (tb > 0) & (rb >= FACE_R * D) & (rb <= 0.5 * D) & (EYE[1] > yb)
        yk = c[1] - 0.015 * D
        tk = (yk - EYE[1]) / np.where(np.abs(d[..., 1]) > 1e-9, d[..., 1], 1e-9)
        Pk = EYE + d * tk[..., None]; rk = np.hypot(Pk[..., 0] - c[0], Pk[..., 2] - c[2])
        back = (tk > 0) & (rk <= 0.5 * D) & (EYE[1] < yk)       # only from below (Cull Back)
        # dissolve / appear front (object-anchored noise, metres)
        def keep(Pw, rM):
            pM = (Pw - c)                                       # object space x D (uniform scale, no rotation)
            n1 = fbm(pM); n2 = fbm(pM + 71.3)
            sdD = (R + BREAK_AMP - st['dissolve'] * (R + 2 * BREAK_AMP)) - (rM + BREAK_AMP * n1)
            sdA = (-BREAK_AMP + st['appear'] * (R + 2 * BREAK_AMP)) - (rM + BREAK_AMP * n2)
            sd = np.minimum(sdD, sdA)
            act = float(st['dissolve'] > 0.0005 or st['appear'] < 0.9995)
            return sd > 0, np.clip(1 - sd / EDGE_W, 0, 1) * act
        for kind, mask, Pw, rM, tdist in (('face', face, P, rr, tt), ('band', band, Pb, rb, tb), ('back', back, Pk, rk, tk)):
            if not mask.any():
                continue
            ok, edge = keep(Pw[mask], rM[mask])
            sel = np.zeros_like(mask); sel[mask] = ok
            nearer = sel & (tdist < depth)
            if not nearer.any():
                continue
            idx = nearer[mask]
            Pn = Pw[nearer]; dn = d[nearer]
            if kind == 'face' and under.any() and under[nearer].all():
                col = np.broadcast_to(BACK_FILL + BACK_ALB * AMB_GND, dn.shape).copy()
            elif kind == 'face':
                n = Pn - Cs; n /= np.linalg.norm(n, axis=-1, keepdims=True)
                rdir = dn - 2 * (dn * n).sum(-1, keepdims=True) * n
                sk = sky(rdir, mat, gl)
                F = schlick(F0_FACE, -(dn * n).sum(-1))
                col = sk * F + sk * (st['k'] * st['vis'] * 2 ** st['extra'])
                lum = col @ np.array([0.2126, 0.7152, 0.0722])
                col = lum[:, None] * (1 - BRONZE_TONE + BRONZE_TONE * TONE[None, :])   # white-bronze tone (#CDBF9C), chroma from the tone only (r3: a blue/warm mix went lavender)
            elif kind == 'band':
                n = np.array([0, 1.0, 0])
                rdir = dn * np.array([1, -1, 1])
                col = sky(rdir, mat, gl) * schlick(F0_RIM, np.abs(dn[:, 1]))
            else:
                col = np.broadcast_to(BACK_FILL + BACK_ALB * AMB_GND, dn.shape).copy()
                if st['dissolve'] > 0:                           # breaking into light: the back goes 60 % -> 100 % toward the sky behind it
                    bl = min(0.6 + 0.4 * st['dissolve'], 1.0)
                    col = col * (1 - bl) + img[nearer] * bl
            near = np.clip((tdist[nearer] - 5.0) / 20.0, 0, 1)
            col = col + EDGE * (edge[idx] * near)[:, None]
            if st['rimsoft'] > 0:
                s0 = RIM_SOFT_FROM.get(RIM_SCHEME, 0.80)
                soft = np.clip((rM[nearer] / (0.5 * D) - s0) / (1.0 - s0), 0, 1)
                soft = soft * soft * (3 - 2 * soft) * st['rimsoft']
                col = col * (1 - soft[:, None]) + img[nearer] * soft[:, None]
            img[nearer] = col
            depth[nearer] = tdist[nearer]
            owner[nearer] = st['index'] * 10 + {'face': 0, 'band': 1, 'back': 2}[kind]
        face_mask[st['index']] = (st, Cs, rho)
        info['mirrors'].append(dict(index=st['index'], y_car=round(st['y_car'], 2), vis=round(st['vis'], 3),
                                    appear=round(st['appear'], 3), dissolve=round(st['dissolve'], 3), extra_EV=round(st['extra'], 3)))
    # stars: the sky's own stars where the sky is visible, and their convex-mirror images inside each face (MirrorStars)
    cat = SC.catalogue()
    fw = A9.FWHM * w / 960 * ss
    if star['gain'] > 0:
        pk = SC.flux(cat['mag'], cat['rank'], 1.6, 0.0, 0.5, star['count'], star['boost']) * star['gain']
        sky_layer = np.zeros_like(img)
        SC.splat(sky_layer, W, H, 90, yaw, pitch, cat['dir'], pk, cat['col'], fw)
        img += sky_layer * (owner < 0)[..., None]
        for idx, (st, Cs, rho) in face_mask.items():
            dd = cat['dir']
            # convex-mirror image (same as Lanbai/MirrorStars): start from the flat mirror, then refine with the normal at
            # the hit point: v = reflect(d, n) is the look direction, P = ray(E, v) on the face sphere, n = normal at P
            n = np.broadcast_to(np.array([0, 1.0, 0]), dd.shape).copy()
            oc = EYE - Cs
            cc = (oc * oc).sum() - rho * rho
            for k in range(7):
                v = dd - 2 * (dd * n).sum(-1, keepdims=True) * n
                b = (v * oc).sum(-1)
                tq = -b - np.sqrt(np.maximum(b * b - cc, 0))
                P = EYE + v * tq[:, None]
                if k < 6:                                        # damped (the plain iteration oscillates near grazing)
                    n = 0.5 * n + 0.5 * (P - Cs) / rho
                    n /= np.linalg.norm(n, axis=-1, keepdims=True)
            n = (P - Cs) / rho; toE = EYE - P; toE /= np.linalg.norm(toE, axis=-1, keepdims=True)
            rr_ = -toE - 2 * ((-toE) * n).sum(-1, keepdims=True) * n
            ok = ((dd * n).sum(-1) > 0) & ((toE * n).sum(-1) > 0) & ((rr_ * dd).sum(-1) > math.cos(math.radians(0.5)))
            F = schlick(F0_FACE, (n * toE).sum(-1))
            gain = (F + st['k'] * st['vis'] * 2 ** st['extra'])
            gain = (gain @ np.array([0.2126, 0.7152, 0.0722]))[:, None] * (1 - BRONZE_TONE + BRONZE_TONE * TONE[None, :])
            appd = -toE                                          # the image's direction from the eye
            layer = np.zeros_like(img)
            SC.splat(layer, W, H, 90, yaw, pitch, appd[ok], pk[ok], cat['col'][ok] * gain[ok], fw)
            img += layer * (owner == idx * 10)[..., None]
    # dust (Lanbai/MirrorDust, closed form)
    if dust:
        for m in SCH['mirrors'][:12]:
            x = t - m['t_cross']
            if not (0 <= x <= m['dissolve']['end'] - m['t_cross'] + 4.0):
                continue
            D = m['diameter_m']; R = D / 2; cx, cz = m['centre_xz']
            rng = np.random.default_rng(1000 + m['dissolve']['dust_slot'])
            u1, u2, u3, u4 = rng.random((4, 250))
            a = 2 * np.pi * u2
            car = np.array([EYE[0] - cx, EYE[2] - cz])
            nearP = car[None, :] + np.stack([np.cos(a), np.sin(a)], -1) * (np.sqrt(u1) * min(40.0, R))[:, None]
            anyP = np.stack([np.cos(a), np.sin(a)], -1) * (np.sqrt(u1) * R)[:, None]
            p = np.where((u3 < 0.7)[:, None], nearP, anyP)
            l = np.linalg.norm(p, axis=-1); p = np.where((l > 0.985 * R)[:, None], p * (0.985 * R / np.maximum(l, 1e-6))[:, None], p)
            q = np.linalg.norm(p, axis=-1) / R
            tb = m['t_cross'] + 2.0 * (1 - q); age = t - tb
            alive = (age >= 0) & (age <= 4.0)
            vrise = m['speed_cross_mps']
            yb = EYE[1] + vrise * np.maximum(tb - m['t_cross'], 0)
            pos = np.stack([cx + p[:, 0], yb + 0.6 * (0.6 + 0.4 * u4) * age, cz + p[:, 1]], -1)
            xx = np.clip(age / 4.0, 0, 1)
            br = np.clip(age / 0.25, 0, 1) * (1 - xx) ** 2
            col = G.hexlin('#CDBF9C')[None, :] * (1 - xx[:, None]) + G.hexlin('#F2F6FF')[None, :] * xx[:, None]
            dirs = pos - EYE; dist = np.linalg.norm(dirs, axis=-1); dirs /= dist[:, None]
            pxang = math.radians(90) / W
            rmin = 1.4 / 1.4133 * pxang * dist
            peak = 6.0 * np.minimum(0.05 / rmin, 1) ** 2 * br * alive * np.clip((dist - 0.3) / 0.7, 0, 1)
            layer = np.zeros_like(img)
            SC.splat(layer, W, H, 90, yaw, pitch, dirs, peak, col, fw)
            img += layer
    if cabin is not None:
        img = cabin(img, d, yaw, pitch)
    if ss > 1:
        img = img.reshape(h, ss, w, ss, 3).mean((1, 3))
    ev = (pulse_ev(t) + white_ev(t)) if extra_ev is None else extra_ev
    a, b, wgt = prof
    ca = np.clip(G.grade(img, a, ev=ev), 0, 255)
    cb = ca if b == a else np.clip(G.grade(img, b, ev=ev), 0, 255)
    codes = ca * (1 - wgt) + cb * wgt
    info['APL'] = round(G.apl(codes), 1)
    info['EV'] = round(ev, 3)
    info['owner'] = owner if ss == 1 else owner[::ss, ::ss]
    return codes, info


if __name__ == '__main__':
    from PIL import Image
    t = float(sys.argv[1]) if len(sys.argv) > 1 else 1030.4
    yaw = float(sys.argv[2]) if len(sys.argv) > 2 else 0.0
    pitch = float(sys.argv[3]) if len(sys.argv) > 3 else 0.0
    c, info = frame(t, yaw, pitch)
    out = sys.argv[4] if len(sys.argv) > 4 else '/tmp/mirror_%.2f.png' % t
    Image.fromarray(np.clip(c, 0, 255).astype(np.uint8)).save(out)
    print(out, info['APL'], info['mirrors'])
