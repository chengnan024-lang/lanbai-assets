"""Unity emulation of the v2 hero puddle (Lanbai/StencilWindow + Lanbai/MirrorCopy + Lanbai/PuddleOverlay): the door
puddle seen from the hero seat (bible §6·1 / §6·12: '静止的水洼；成双的「蓝白」站牌', '静水里的灯影 #DDE8EA').
Per pixel, exactly the shader rules: the mirrored copies (sign face = its albedo x _Lit, pole, lamp pole; the tube is
NOT a copy) behind the stencil, then the water: R(theta) = _MirrorReflectance + (1 - R0)(1 - cos)^5 of the copies,
the analytic tube (lamps_ref = LanbaiLamps.cginc v2) at the same reflectance with its core capped at _LampPeak, rings
breaking it (cells_ref = LanbaiRippleCells v2). Graded with the bible's PPv2 maths (S12 / S1, bloom on).
Panels: scene 12 still; scene 1 rain rings; the v1 shader (verification round 2, M1) for comparison.
usage: python3 still_puddle.py <out_png>"""
import json, os, sys
import numpy as np
from PIL import Image, ImageDraw, ImageFont
from matplotlib.path import Path

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
from lamps_ref import spec_one, nrm
import cells_ref as CR
import rainpaths as RP
LAN = RP.lanbai_root()
ART = os.path.join(LAN, 'art')
sys.path.insert(0, os.path.join(ART, 'lens_cine')); sys.path.insert(0, os.path.join(ART, 'bible_work'))
import ppv2
from lutlib_core import patch_ppv2
patch_ppv2(ppv2)
GF = json.load(open(os.path.join(ART, 'grades_final.json'))); PROF = {k: v['ppv2'] for k, v in GF['profiles'].items()}
LAY = json.load(open(RP.find('Stop_Layout.json')))
SIGNTEX = os.path.join(LAN, 'deliver2', 'Sign', 'Textures', 'Sign', 'Sign_Face_ZH_Albedo.png')


def lin(h):
    c = np.array([int(h[i:i + 2], 16) / 255 for i in (1, 3, 5)])
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


# ---- stage frame (x along the road, y = -X_u, z up); Unity lamp axis etc. from the README / layout
TUBE = np.array([2.44, -2.38, 3.90]); TAX = np.array([0.6, 0.8, 0.0]) * 0.6
TCOL = lin('#E4F1F3'); I_TUBE = 15.0
SIGN_POLE = np.array([3.40, -3.10]); SIGN_N = np.array([-0.8, 0.6, 0.0]); SIGN_R = 0.303
SIGN_C = np.array([*(SIGN_POLE + 0.0532 * SIGN_N[:2]), 2.25])    # the enamel face sits 53 mm in front of the pole axis
TT_C = np.array([*(SIGN_POLE + 0.048 * SIGN_N[:2]), 1.69]); TT_HW, TT_HH = 0.15, 0.21   # timetable plate (Sign kit)
TT_ALB = lin('#C4C6C2')
SIGN_RIGHT = np.cross(-SIGN_N, [0, 0, 1.0])                      # the face's +u as a viewer in front sees it
LIT = TCOL * 1.47                                                # _Lit = E x lamp colour (README: 静水镜像)
SKY = lin('#070B14')                                             # _MirrorSky
BOTTOM = np.full(3, 0.012)                                       # _BottomColour (sRGB 0.11 as picked)
R0, PEAK = 0.30, 1.45
EYE = np.array([-1.30, 0.85, 2.10])                              # hero seat eye (Sign stage SEAT_EYE)
sign_alb = np.asarray(Image.open(SIGNTEX).convert('RGB').resize((1024, 1024), Image.LANCZOS), np.float64) / 255
sign_alb = np.where(sign_alb <= 0.04045, sign_alb / 12.92, ((sign_alb + 0.055) / 1.055) ** 2.4)
door = np.array(LAY['hero_puddles']['door']['outline_stage_xy'])
door_path = Path(door)


def cyl_hit(o, d, c, r, z0, z1):
    """ray o + t d vs vertical cylinder at c (x, y) radius r, z0..z1 -> t (inf = miss)"""
    ox, oy = o[..., 0] - c[0], o[..., 1] - c[1]
    a = d[..., 0] ** 2 + d[..., 1] ** 2; b = 2 * (ox * d[..., 0] + oy * d[..., 1]); cc = ox ** 2 + oy ** 2 - r * r
    disc = b * b - 4 * a * cc
    t = (-b - np.sqrt(np.maximum(disc, 0))) / np.maximum(2 * a, 1e-12)
    z = o[..., 2] + t * d[..., 2]
    return np.where((disc > 0) & (t > 0) & (z > z0) & (z < z1), t, np.inf)


def mirror_world(P, R):
    """what the mirrored copies show along the reflected ray R from the water point P (full brightness)"""
    col = np.broadcast_to(SKY, P.shape).copy()
    best = np.full(P.shape[:-1], np.inf)
    # sign face (disc)
    den = (R * SIGN_N).sum(-1)
    t = ((SIGN_C - P) * SIGN_N).sum(-1) / np.where(np.abs(den) < 1e-9, 1e-9, den)
    H = P + t[..., None] * R
    q = H - SIGN_C
    u = (q * SIGN_RIGHT).sum(-1); v = q[..., 2]
    on = (t > 0) & (u * u + v * v < SIGN_R ** 2) & (den < 0)
    iu = np.clip(((u / SIGN_R) * 0.5 + 0.5) * 1023, 0, 1023).astype(int); iv = np.clip((0.5 - (v / SIGN_R) * 0.5) * 1023, 0, 1023).astype(int)
    sc = sign_alb[iv, iu] * LIT
    col = np.where(on[..., None], sc, col); best = np.where(on, t, best)
    # the timetable plate below it (same plane, near-blank faded print)
    t2 = ((TT_C - P) * SIGN_N).sum(-1) / np.where(np.abs(den) < 1e-9, 1e-9, den)
    q2 = P + t2[..., None] * R - TT_C
    on2 = (t2 > 0) & (np.abs((q2 * SIGN_RIGHT).sum(-1)) < TT_HW) & (np.abs(q2[..., 2]) < TT_HH) & (den < 0) & (t2 < best)
    col = np.where(on2[..., None], TT_ALB * LIT, col); best = np.where(on2, t2, best)
    # sign pole (galvanised, lit ~0.6 from the tube) and the concrete lamp pole (screen 60-80 under the lamp)
    for c, r, z0, z1, alb, E in ((tuple(SIGN_POLE), 0.030, 0.0, 2.6, 0.30, 0.9), ((1.72, -3.34), 0.12, 0.0, 9.0, 0.09, 1.2)):
        th = cyl_hit(P, R, c, r, z0, z1)
        m = th < best
        zh = P[..., 2] + th * R[..., 2]
        shade = np.where(zh < 3.9, E, 0.08)                      # above the trough the pole is unlit
        col = np.where(m[..., None], (alb * shade)[..., None] * TCOL, col); best = np.where(m, th, best)
    return col


def render(mode, W=900, Hh=600, t_rain=37.3):
    look = np.array([0.36, -0.58, 0.0])
    fwd = nrm(look - EYE); right = nrm(np.cross(fwd, [0, 0, 1.0])); up = np.cross(right, fwd)
    th = np.tan(np.radians(23.0) / 2)
    xs = ((np.arange(W) + 0.5) / W * 2 - 1) * th * W / Hh; ys = (1 - (np.arange(Hh) + 0.5) / Hh * 2) * th
    X, Y = np.meshgrid(xs, ys)
    D = nrm(fwd[None, None] + X[..., None] * right[None, None] + Y[..., None] * up[None, None])
    t = -EYE[2] / D[..., 2]
    P = EYE + t[..., None] * D
    V = -D
    inside = door_path.contains_points(P[..., :2].reshape(-1, 2)).reshape(P.shape[:2])
    # ---- the road outside: wet film, diffuse from the baked tube + its long GGX band (WetSurface)
    toL = TUBE - P; d2 = (toL ** 2).sum(-1)
    E = I_TUBE / d2 * np.clip(toL[..., 2] / np.sqrt(d2), 0, 1)
    Nup = np.zeros_like(P); Nup[..., 2] = 1
    road = (0.08 * 0.5 * E)[..., None] * TCOL + spec_one(TUBE, I_TUBE, TCOL, 0.013, TAX, (0, 0, -1), 0.05, P, Nup, V, (1 - 0.79) ** 2, 0.04)
    # ---- the puddle surface
    fp = t * (2 * th / Hh) / np.maximum(V[..., 2], 0.2)
    bl = CR.ring_band(fp)
    Xu, Zu = -P[..., 1], P[..., 0]
    if mode == 'rain':
        sX, sZ = CR.cells(Xu, Zu, t_rain, 4.0, bl)
        s = np.stack([sZ, -sX], -1)                              # stage slopes (dh/dx_b, dh/dy_b)
    else:
        s = np.zeros(P.shape[:-1] + (2,))
    N = nrm(np.stack([-s[..., 0], -s[..., 1], np.ones(P.shape[:-1])], -1))
    cosV = np.clip(V[..., 2], 0, 1); cosR = np.clip((N * V).sum(-1), 0, 1)
    fC = (1 - cosV) ** 5; fR = (1 - cosR) ** 5
    if mode == 'v1':
        Rcalm = 0.02 + 0.98 * fC; Rrip = 0.02 + 0.98 * fR
    else:
        Rcalm = R0 + (1 - R0) * fC; Rrip = R0 + (1 - R0) * fR
    brk = np.clip(np.hypot(s[..., 0], s[..., 1]) / 0.04, 0, 1)
    keep = Rcalm * (1 - brk)
    Rc = V * 0; Rc = 2 * cosV[..., None] * Nup - V                # calm mirror direction
    mir = mirror_world(P, Rc)
    if mode == 'v1':
        lamp = 0.0 * mir                                         # v1 GGX epsilon: the tube's image was ~0.005
    else:
        lc = spec_one(TUBE, I_TUBE, TCOL, 0.013, TAX, (0, 0, -1), 0.05, P, Nup, V, 0.002, 0.02, boost=Rcalm / (0.02 + 0.98 * fC), peak=PEAK)
        lr = spec_one(TUBE, I_TUBE, TCOL, 0.013, TAX, (0, 0, -1), 0.05, P, N, V, 0.002, 0.02, boost=Rrip / (0.02 + 0.98 * fR), peak=PEAK)
        lamp = lc * (1 - brk[..., None]) + lr * brk[..., None]
    Rr = 2 * cosR[..., None] * N - V
    broken = mirror_world(P, Rr) * 0 + SKY * (Rrip * 0.8 * brk)[..., None]
    water = mir * keep[..., None] + broken + lamp + BOTTOM * (1 - (Rcalm * (1 - brk) + Rrip * brk))[..., None]
    img = np.where(inside[..., None], water, road)
    prof = 'S1' if mode == 'rain' else 'S12'
    disp = ppv2.render(img, PROF[prof], with_bloom=True)
    return disp, img, inside, lc if mode != 'v1' else None


if __name__ == '__main__':
    out = sys.argv[1]
    FONTS = os.path.join(LAN, 'deliver2', 'Sign', 'Fonts')
    F = lambda s: ImageFont.truetype(os.path.join(FONTS, 'SourceHanSerifCN-Regular.otf'), s)
    FB = lambda s: ImageFont.truetype(os.path.join(FONTS, 'SourceHanSerifCN-Medium.otf'), s)
    panels = []
    notes = []
    for mode in ('still', 'rain', 'v1'):
        disp, lin_img, inside, lc = render(mode)
        panels.append(disp)
        if lc is not None:
            m = lc.max(-1); j = np.unravel_index(np.argmax(m), m.shape)
            core = (np.clip(disp[j], 0, 1) * 255).round().astype(int)
            notes.append('#%02X%02X%02X' % tuple(core))
        else:
            notes.append('—')
    W, Hh = panels[0].shape[1], panels[0].shape[0]
    im = Image.new('RGB', (W * 3 + 80, Hh + 330), (14, 17, 24)); d = ImageDraw.Draw(im)
    d.text((40, 24), '主角水洼：静水里的灯影与成双的站牌（Unity 模拟）', font=FB(34), fill=(222, 230, 234))
    d.text((40, 70), "Hero puddle 'door' from the hero seat: Lanbai/StencilWindow + MirrorCopy + PuddleOverlay v2, per-pixel kit maths, PPv2 grade with bloom",
           font=F(19), fill=(140, 150, 160))
    caps = ['第 12 幕 · 静水（S12）\n灯管 = 解析灯，核心钉在圣经目标（实测 %s，圣经 #DDE8EA）；\n站牌镜像副本 × 静水反射率 R(θ)=0.30→1（Schlick）：成双的「蓝白」' % notes[0],
            '第 1 幕 · 雨纹（S1，程序化环 4 个/m²/s）\n被打碎的倒影：每个碎面都被同一个上限钳住——\n涟漪只会让倒影变暗、变散，永远不会更亮',
            'v1（验收第 2 轮 M1）：静水只保留 2% 的镜像，\n解析灯的 GGX ε 让灯管倒影几乎为 0\n→ 全片最后一个画面是一块暗斑']
    for k, p in enumerate(panels):
        im.paste(Image.fromarray((np.clip(p, 0, 1) * 255).astype(np.uint8)), (40 + k * (W + 0), 120))
        for i, line in enumerate(caps[k].split('\n')):
            d.text((48 + k * W, 140 + Hh + i * 30), line, font=F(19), fill=(222, 230, 234) if i == 0 else (140, 150, 160))
    d.text((48, 140 + Hh + 3 * 30 + 26), '怎么读这张图：从主座位透过开着的车门往下看 door 水洼（俯角约 51°，长焦放大）。深色的不规则形状就是水洼的轮廓——里面是镜子'
           '（镜像副本 + 夜空 #070B14 × R(θ)），外面是灯下的湿路；镜子里上下颠倒：时刻表板在站牌上面，灯管在站牌下面。',
           font=F(19), fill=(140, 150, 160))
    im.save(out)
    print('tube image core', notes)
