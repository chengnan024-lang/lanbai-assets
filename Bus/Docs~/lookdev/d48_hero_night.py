# -*- coding: utf-8 -*-
"""D-48 主座位夜间图：第 2 幕（夜路、管灯亮），从主座位的眼 (0.55, 1.70, 2.05) 往下看自己的座垫和手、往前看；再量座垫在
调色以后还留不留得住中间调的纹理（没被压成一块黑）。

    ~/bpy/bin/python -B Bus/Docs~/lookdev/d48_hero_night.py [--samples 48] [--threads 4] [--grade S2|none] [--scale 1.0]
                                                           [--views hero_down,hero_fwd,hero_down_noproxy,ref_back]
                                                           [--blend /tmp/bus/bus_final_ext.blend] [--lightmap ...]
                                                           [--out Bus/Docs~/lookdev/d48]

场景：和 Bus/Docs~/slice/slice_final.py 的整车两张一样（直接 import 它的函数）：scene_acts.build() 第 2 幕，再让漫射只来自
光照图（Lanbai/Cabin 就是这样），光泽照常追；调色 --grade S2（默认，lbh/grade.py 的 PPv2 模拟，bloom 开，VR 不加镜头层），
none = Standard 直出。只读：--blend 先拷到临时文件夹再从拷贝里读，不存 .blend；光照图是 Bus/Textures/Cabin_TubeLM.exr
（--lightmap 换一份拷贝，测试时防重烘）；两样的前后 md5 都记进 json。

人（代理模型，平滑的低面数胶囊 / 椭球）：主座位上坐一个成年人，没有头（相机就是头）：胸以下的躯干、肩、上臂、前臂、手放在大腿上、
大腿压在座垫上、膝、小腿从座垫前沿垂下去、脚。主座位前面右半边是前轮罩（顶 y 1.00，到 z 2.49）和膝前护板（z 2.53–2.57），
右小腿放不下去，所以两条腿往过道那边偏一点，两只脚都踩在轮罩左边的地板上。手是中等肤色（线性约 0.4），衣服灰蓝（线性约
0.17）。车厢中段再坐四个人（头、颈、肩、上臂、躯干），SeatR2、SeatR3、SeatL2、SeatL3 靠过道的位子（头顶补光在 z 0，
前后各一排：R2、L2 的脸背着它，R3、L3 的脸对着它），当“车厢中段的头”的参照，取四个的平均。坐姿和座椅、靠背、护板、轮罩、
地板有没有穿插，脚本自己查（json 的 proxy_clearance）。

人的光：照 Unity 的逐顶点点光（UnityCG.cginc 的 Shade4PointLights）逐顶点算：三盏补光的
颜色（#E4F1F3 转线性）× 强度 × 管灯档位 × max(0, n·l) / (1 + d² × 25 / range²) 加起来，n 用平滑顶点法线。三盏：HeadFill_0/1
（每排管灯上方一盏，(x, 2.45, 0)，0.5，range 6），HeadFill_2（D-48，finish_bus.py 的 HERO_FILL，从源码读）。存成顶点色，人
画成 自发光 = 反照率 × 它；人身上没有别的光（第 2 幕环境光 0，人不吃光照图）。人对光泽光线隐身（Unity 的反射探针里没有人）、
不挡影子、不进漫射（车厢的漫射本来就只是光照图）。

机位（主座位的眼，水平 90°，960 × 720，--scale 缩放）：
  hero_down          偏航 0、俯 65°：往下看自己的胸、腿、手和大腿两边露出来的座垫
  hero_fwd           偏航 0、俯 10°：往前看（挡风、仪表台和收音机、发动机盖、门柱；司机座在 −67°，不在画面里）；
                     这个俯角下自己的膝和手（−58° 以下）在画面下沿以外
  hero_down_noproxy  = hero_down，不放人：单看座垫
  ref_back           偏航 180、俯 8°：往后看车厢中段那几个人（主座位自己的身体藏起来，当转过身去）。车厢中段在主座位
                     后面，往前看的图里看不到他们，所以另加这一张当参照；R3 正好在 R2 后面，被挡住

量：调色以后的 8 位图（存 PNG 以前的数组）上，Seat_SeatR0 的座垫顶面像素：按面挑（朝上、在座垫顶面那个高度、离四边 2 cm 以内
的滚边不要），另渲一张 ID 图（所有材质换成按面 / 按部位写的标记色），人身上的、边上混色的像素都去掉。sRGB 亮度（Rec.709 系数
乘码值）的中位、p10、p90、低于 16 级和 24 级的占比、纹理反差（亮度减去 σ 3 px 的高斯模糊（只在座垫像素里模糊），再在 σ 3 px
的窗里求均方根，取座垫像素（往里收 2 px）的中位，单位：级）。hero_down 和 hero_down_noproxy 各量一遍，另在两张共有的像素上
再比一遍。人：各部位逐顶点光的几种统计（按面积加权的平均、p90、对着眼睛那半边的平均、不管法线的点光值），车厢中段两个头的
同样几项，EV 差；再从图上量一次手和头（同一个肤色）的线性亮度比。座垫另在不调色（Standard）的同一批像素上量一遍，看调色
把它压暗、压平了多少。

出：<out>/hero_down.png、hero_fwd.png、hero_down_noproxy.png、ref_back.png（每张 < 400 KB，SF.save_capped）、
contact_sheet.png（带标签）、d48_hero_night.json（所有数、机位、用时、md5）、README.md。
没在 Unity 里编译、导入、运行过；这是 Blender 里的近似。
"""
import argparse
import ast
import json
import math
import os
import re
import shutil
import sys
import tempfile
import time

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.normpath(os.path.join(HERE, '..', '..', '..'))
sys.path.insert(0, os.path.join(ROOT, 'Bus', 'Docs~', 'slice'))
sys.path.insert(0, os.path.join(ROOT, 'Bus', 'Source'))

import slice_final as SF  # noqa: E402   (puts the harness / lookdev / parts paths on sys.path; bpy, lbh, scene_acts)
import bpy  # noqa: E402
import bmesh  # noqa: E402
import numpy as np  # noqa: E402
from mathutils.bvhtree import BVHTree  # noqa: E402
from PIL import Image, ImageDraw  # noqa: E402
from scipy import ndimage  # noqa: E402
from scipy.spatial import Delaunay  # noqa: E402

import bus_spec as B  # noqa: E402

S, G, SA = SF.S, SF.G, SF.SA

EYE = tuple(float(v) for v in B.EYE)
DEFAULT_LM = os.path.join(ROOT, 'Bus', 'Textures', 'Cabin_TubeLM.exr')
FINISH_BUS = os.path.join(ROOT, 'Bus', 'Source', 'finish_bus.py')
FILL_COLOUR = '#E4F1F3'
SKIN = (0.46, 0.36, 0.30)            # linear albedo, luminance ~0.38
CLOTH = (0.15, 0.17, 0.21)           # muted grey-blue, luminance ~0.17
SHOE = (0.05, 0.05, 0.055)
REC709 = np.array([0.2126, 0.7152, 0.0722])

VIEWS = {
    'hero_down': dict(eye=list(EYE), yaw_deg=0.0, pitch_deg=-65.0, hfov_deg=90.0, res=[960, 720], show=('hero', 'mid')),
    'hero_fwd': dict(eye=list(EYE), yaw_deg=0.0, pitch_deg=-10.0, hfov_deg=90.0, res=[960, 720], show=('hero', 'mid')),
    'hero_down_noproxy': dict(eye=list(EYE), yaw_deg=0.0, pitch_deg=-65.0, hfov_deg=90.0, res=[960, 720], show=()),
    'ref_back': dict(eye=list(EYE), yaw_deg=180.0, pitch_deg=-8.0, hfov_deg=90.0, res=[960, 720], show=('mid',)),
}
LOOK = {
    'hero_down': '往下看：自己的胸、大腿、两只手，大腿两边露出来的座垫；上面是地板、发动机盖（左）、前轮罩和护板（右）',
    'hero_fwd': '往前看：挡风、仪表台和收音机、发动机盖（左下）、轮罩上的扶手（右下）、门柱；自己的膝和手在画面以外',
    'hero_down_noproxy': '同 hero_down，不放人：整块座垫单看',
    'ref_back': '参照：往后看车厢中段的人的脸（主座位的身体藏起来；R3 在 R2 正后面，挡住了）',
}

# person part codes in the ID pass (G channel = code / 10); passengers: B = 1 head, 0.5 body
HERO_CODES = dict(hands=1, thighs=2, chest=3, abdomen=4, pelvis=5, upper_arms=6, forearms=7, shins=8, feet=9)
SEEN_PARTS = ('hands', 'lap', 'chest', 'head')         # the four the finish_bus comment names


# ------------------------------------------------------------------------------------------------ lights
def hero_fill_from_source():
    """HERO_FILL and the EV numbers of its comment, read from finish_bus.py (no import: it pulls the whole build in)."""
    src = open(FINISH_BUS, encoding='utf-8').read()
    fill = None
    for node in ast.parse(src).body:
        if isinstance(node, ast.Assign) and any(getattr(t, 'id', None) == 'HERO_FILL' for t in node.targets):
            fill = ast.literal_eval(node.value)
    if fill is None:
        raise RuntimeError('HERO_FILL not found in ' + FINISH_BUS)
    i = src.find('HERO_FILL =')
    doc = {}
    for k, v in re.findall(r'(hands|lap|chest|head) (-?\d+\.\d+)', src[max(0, i - 600):i]):
        doc.setdefault(k, float(v))
    return fill, doc


def head_fills(level):
    """the three head fills as finish_bus.layout() writes them into BusLayout.json (HeadFill_0/1 = one per tube row,
    0.5 / range 6 = LanbaiBusBuild's defaults; HeadFill_2 = HERO_FILL). 'level' = the tube level the lights follow
    (LB_Journey.cabinLights x _Udon_CabinLightmap)."""
    (pos, inten, rng), _ = hero_fill_from_source()
    L = [dict(name='HeadFill_%d' % i, pos=[float(x), 2.45, 0.0], intensity=0.5, range=6.0) for i, x in enumerate(B.TUBE_X)]
    L.append(dict(name='HeadFill_2', pos=[float(v) for v in pos], intensity=float(inten), range=float(rng)))
    for li in L:
        li.update(colour=FILL_COLOUR, colour_linear=[round(float(c), 5) for c in G.hex_lin(FILL_COLOUR)], level=float(level),
                  render_mode='Not Important (per vertex)', culling='Player + PlayerLocal')
    return L


def layout_check(lights):
    """the three lights against Bus/Models/BusLayout.json's head_fill_lights (what LanbaiBusBuild reads; read-only).
    A missing intensity / range there = LanbaiBusBuild's defaults 0.5 / 6."""
    p = os.path.join(ROOT, 'Bus', 'Models', 'BusLayout.json')
    try:
        H = json.load(open(p, encoding='utf-8')).get('head_fill_lights') or []
    except Exception as e:  # noqa: BLE001
        return dict(path=shown(p), error=str(e), match=False)
    rows = []
    for i, li in enumerate(lights):
        if i >= len(H):
            rows.append(dict(name=li['name'], in_layout=False))
            continue
        h = H[i]
        rows.append(dict(name=li['name'], in_layout=True,
                         pos=bool(np.allclose(h.get('pos', [9, 9, 9]), li['pos'], atol=1e-4)),
                         intensity=bool(abs((h.get('intensity') or 0.5) - li['intensity']) < 1e-6),
                         range=bool(abs((h.get('range') or 6.0) - li['range']) < 1e-6),
                         colour=h.get('colour', FILL_COLOUR).upper() == li['colour'].upper()))
    ok = len(H) == len(lights) and all(r.get('in_layout') and r['pos'] and r['intensity'] and r['range'] and r['colour']
                                       for r in rows)
    return dict(path=shown(p), lights_in_layout=len(H), rows=rows, match=ok)


def shade4(P, N, lights):
    """UnityCG Shade4PointLights per vertex: sum colour_lin x intensity x max(0, n.l) / (1 + d^2 x 25 / range^2)."""
    E = np.zeros((len(P), 3))
    for li in lights:
        d = np.asarray(li['pos'], float)[None] - P
        d2 = np.maximum((d * d).sum(1), 1e-6)
        ndl = np.maximum((N * d).sum(1) / np.sqrt(d2), 0.0)
        att = 1.0 / (1.0 + d2 * 25.0 / li['range'] ** 2)
        E += (np.asarray(li['colour_linear']) * li['intensity'] * li['level'])[None] * (ndl * att)[:, None]
    return E


def omni(p, lights):
    """the same sum at one point with n.l = 1 for every light (a point model that ignores the normal)."""
    p = np.asarray(p, float)
    e = 0.0
    for li in lights:
        d2 = max(float(((np.asarray(li['pos']) - p) ** 2).sum()), 1e-6)
        e += float(np.dot(li['colour_linear'], REC709)) * li['intensity'] * li['level'] / (1.0 + d2 * 25.0 / li['range'] ** 2)
    return e


# ------------------------------------------------------------------------------------------------ proxy geometry (unity)
def _loft(rings, U, V, seg):
    """rings [(centre, rho)] -> verts, faces; rho 0 = a pole (one vertex)."""
    verts, faces, idx = [], [], []
    for c, rho in rings:
        if rho < 1e-9:
            idx.append([len(verts)])
            verts.append(np.asarray(c, float))
            continue
        ring = []
        for j in range(seg):
            ph = 2 * math.pi * j / seg
            ring.append(len(verts))
            verts.append(c + rho * (math.cos(ph) * U + math.sin(ph) * V))
        idx.append(ring)
    for a, b in zip(idx[:-1], idx[1:]):
        if len(a) == 1 and len(b) == 1:
            continue
        if len(a) == 1:
            faces += [(a[0], b[j], b[(j + 1) % seg]) for j in range(seg)]
        elif len(b) == 1:
            faces += [(a[j], a[(j + 1) % seg], b[0]) for j in range(seg)]
        else:
            faces += [(a[j], a[(j + 1) % seg], b[(j + 1) % seg], b[j]) for j in range(seg)]
    return np.array(verts), faces


def capsule(p0, p1, r0, r1, flat=1.0, up=(0.0, 1.0, 0.0), seg=24, rings=7):
    """tapered capsule p0 -> p1, radii r0 / r1; the cross-section squashed to 'flat' along 'up' (thighs, hands)."""
    p0, p1 = np.asarray(p0, float), np.asarray(p1, float)
    a = (p1 - p0) / np.linalg.norm(p1 - p0)
    u = np.asarray(up, float) - np.dot(up, a) * a
    u /= np.linalg.norm(u)
    v = np.cross(a, u)
    rl = [(p0 + a * r0 * math.sin(-math.pi / 2 + math.pi / 2 * k / rings), r0 * math.cos(-math.pi / 2 + math.pi / 2 * k / rings))
          for k in range(rings + 1)]
    rl += [(p1 + a * r1 * math.sin(math.pi / 2 * k / rings), r1 * math.cos(math.pi / 2 * k / rings)) for k in range(rings + 1)]
    return _loft(rl, u * flat, v, seg)


def ellipsoid(c, radii, tilt_deg=0.0, seg=28, rings=14):
    """ellipsoid at c with radii (x, y, z); tilt_deg about x, + = the top leans back (to -z)."""
    rx, ry, rz = radii
    rl = [(np.array([0.0, ry * math.sin(-math.pi / 2 + math.pi * k / rings), 0.0]), math.cos(-math.pi / 2 + math.pi * k / rings))
          for k in range(rings + 1)]
    v, f = _loft(rl, np.array([rx, 0.0, 0.0]), np.array([0.0, 0.0, rz]), seg)
    t = math.radians(tilt_deg)
    R = np.array([[1, 0, 0], [0, math.cos(t), math.sin(t)], [0, -math.sin(t), math.cos(t)]])
    return v @ R.T + np.asarray(c, float), f


def torso_parts(cx, cy, bz):
    """pelvis, abdomen, chest, shoulder bar for someone sitting on a cushion top cy with the back of the seat at bz
    (the backrest's front face is ~bz + 0.054 at the cushion, ~bz - 0.01 at shoulder height: 10 deg recline)."""
    return [
        ('pelvis', ellipsoid((cx, cy + 0.097, bz + 0.170), (0.165, 0.090, 0.115)), 'cloth'),
        ('abdomen', ellipsoid((cx, cy + 0.215, bz + 0.162), (0.150, 0.105, 0.105), 5.0), 'cloth'),
        ('chest', ellipsoid((cx, cy + 0.370, bz + 0.127), (0.165, 0.130, 0.110), 8.0), 'cloth'),
        ('chest', capsule((cx - 0.15, cy + 0.445, bz + 0.105), (cx + 0.15, cy + 0.445, bz + 0.105), 0.058, 0.058,
                          flat=0.85, up=(0, 1, 0)), 'cloth'),
    ]


def hero_parts(cx, cy, bz):
    """the hero, no head. Legs lean to the aisle: the front wheel box (top y 1.00, x >= ~0.56, to z 2.49) and the knee
    guard (z 2.53-2.57) take the right half of the leg room in front of the cushion."""
    P = torso_parts(cx, cy, bz)
    for s in (-1, 1):                        # -1 = left (aisle), +1 = right (window)
        # elbows by the hips, hands on the front half of the thighs: the cushion beside the thighs stays in view
        sh = (cx + s * 0.185, cy + 0.435, bz + 0.105)
        el = (cx + s * 0.195, cy + 0.172, bz + 0.155)
        wr = (0.432, cy + 0.164, 2.165) if s < 0 else (0.602, cy + 0.164, 2.165)       # on the thigh, fingers in ~15 deg
        tip = (0.468, cy + 0.146, 2.325) if s < 0 else (0.558, cy + 0.146, 2.325)
        hip = (cx + s * 0.085, cy + 0.083, bz + 0.170)
        knee = (0.425, cy + 0.068, 2.415) if s < 0 else (0.530, cy + 0.068, 2.415)
        ank = (0.370, B.FLOOR_Y + 0.080, 2.455) if s < 0 else (0.455, B.FLOOR_Y + 0.080, 2.465)
        toe = (ank[0] - 0.018, B.FLOOR_Y + 0.036, ank[2] + 0.190)
        hd = np.subtract(tip, wr) / np.linalg.norm(np.subtract(tip, wr))
        P += [
            ('upper_arms', capsule(sh, el, 0.047, 0.040), 'cloth'),
            ('forearms', capsule(el, wr, 0.038, 0.029, flat=0.85), 'cloth'),
            ('hands', capsule(np.add(wr, hd * 0.040), np.subtract(tip, hd * 0.038), 0.042, 0.038, flat=0.38), 'skin'),
            ('thighs', capsule(hip, knee, 0.080, 0.057, flat=0.82), 'cloth'),
            ('shins', capsule(knee, ank, 0.050, 0.036), 'cloth'),
            ('feet', capsule((ank[0], B.FLOOR_Y + 0.045, ank[2] - 0.030), toe, 0.042, 0.040, flat=0.62), 'shoe'),
        ]
    return P


def passenger_parts(cx, cy, bz):
    """a mid-cabin passenger: head, neck, shoulders, upper arms, torso (the lap is behind the seat in front)."""
    P = torso_parts(cx, cy, bz)
    P += [('neck', capsule((cx, cy + 0.470, bz + 0.100), (cx, cy + 0.585, bz + 0.135), 0.050, 0.047), 'skin'),
          ('head', ellipsoid((cx, cy + 0.665, bz + 0.155), (0.075, 0.108, 0.095)), 'skin')]
    for s in (-1, 1):
        P.append(('upper_arms', capsule((cx + s * 0.185, cy + 0.435, bz + 0.105), (cx + s * 0.195, cy + 0.195, bz + 0.205),
                                        0.047, 0.040), 'cloth'))
    return P


def hero_head_virtual(cx, bz):
    """the hero's own head: not rendered (the camera is in it), numbers only; the eye sits at its front."""
    return ellipsoid((cx, EYE[1] - 0.035, EYE[2] - 0.075), (0.075, 0.108, 0.095))


def make_person(name, parts, mats, id_of):
    """one object from the parts: unity -> blender verts, outward normals, smooth; returns (object, info) with the
    per-vertex unity positions / normals / areas / part names."""
    V, F, fpart, fmat, vpart, vshell = [], [], [], [], [], []
    slots = list(mats)
    for k, (pname, (v, f), mk) in enumerate(parts):
        off = sum(len(x) for x in V)
        V.append(v)
        F += [tuple(i + off for i in fc) for fc in f]
        fpart += [pname] * len(f)
        fmat += [slots.index(mk)] * len(f)
        vpart += [pname] * len(v)
        vshell += [k] * len(v)
    V = np.concatenate(V)
    me = bpy.data.meshes.new(name)
    me.from_pydata([(float(x), float(z), float(y)) for x, y, z in V], [], F)
    me.update()
    bm = bmesh.new()
    bm.from_mesh(me)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    bm.to_mesh(me)
    bm.free()
    me.polygons.foreach_set('material_index', fmat)
    me.shade_smooth()
    me.update()
    for mk in slots:
        me.materials.append(mats[mk])
    nb = np.empty(len(me.vertices) * 3)
    me.vertex_normals.foreach_get('vector', nb)
    N = nb.reshape(-1, 3)[:, [0, 2, 1]]
    N /= np.linalg.norm(N, axis=1, keepdims=True)
    vpart, vshell = np.array(vpart), np.array(vshell)
    for k in range(len(parts)):                            # every closed shell must face outward
        s = vshell == k
        assert (np.einsum('ij,ij->i', N[s], V[s] - V[s].mean(0)) > 0).mean() > 0.9, (name, parts[k][0])
    area = np.zeros(len(V))
    for fc in F:                                           # vertex area = 1/n of each touching face (fan triangles)
        p = V[list(fc)]
        a = sum(0.5 * np.linalg.norm(np.cross(p[k] - p[0], p[k + 1] - p[0])) for k in range(1, len(fc) - 1))
        area[list(fc)] += a / len(fc)
    idc = np.array([id_of(p) for p in fpart], float)
    at = me.attributes.new('d48_id', 'FLOAT_COLOR', 'FACE')
    at.data.foreach_set('color', np.concatenate([idc, np.ones((len(idc), 1))], 1).ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.visible_glossy = False              # Unity's reflection probes have no avatars
    ob.visible_shadow = False              # no shadow on anything (the cabin's diffuse is the lightmap anyway)
    ob.visible_diffuse = False
    ob.visible_volume_scatter = False
    ob.visible_transmission = True         # seen through glass like any opaque avatar
    return ob, dict(V=V, N=N, area=area, part=vpart, parts=parts)


def set_vertex_light(ob, E):
    me = ob.data
    a = me.attributes.get('d48_vl') or me.attributes.new('d48_vl', 'FLOAT_COLOR', 'POINT')
    a.data.foreach_set('color', np.concatenate([E, np.ones((len(E), 1))], 1).astype(np.float32).ravel())


def proxy_material(name, albedo):
    """emission = albedo x the per-vertex light (Unity vertex lights land in the diffuse term: albedo x E)."""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_type = 'GEOMETRY'
    at.attribute_name = 'd48_vl'
    mul = nt.nodes.new('ShaderNodeMix')
    mul.data_type = 'RGBA'
    mul.blend_type = 'MULTIPLY'
    mul.inputs[0].default_value = 1.0
    nt.links.new(at.outputs['Color'], mul.inputs[6])
    mul.inputs[7].default_value = (*albedo, 1.0)
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Strength'].default_value = 1.0
    nt.links.new(mul.outputs[2], em.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs[0])
    m.cycles.emission_sampling = 'NONE'
    return m


# ------------------------------------------------------------------------------------------------ cabin probes
def world_mesh(ob):
    """(unity verts, faces, blender verts) of an object in world space."""
    me = ob.data
    co = np.empty(len(me.vertices) * 3)
    me.vertices.foreach_get('co', co)
    M = np.array(ob.matrix_world)
    vb = co.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3]
    return vb[:, [0, 2, 1]], [tuple(p.vertices) for p in me.polygons], vb


def mark_cushion(ob):
    """the hero cushion's top (no welt): up-facing faces at the cushion's height, 2 cm in from its outline. Writes
    the FACE attribute 'd48_id' = (1, 0, 0) on them. Returns the selection numbers."""
    me = ob.data
    n = len(me.polygons)
    c = np.empty(n * 3)
    nn = np.empty(n * 3)
    ar = np.empty(n)
    me.polygons.foreach_get('center', c)
    me.polygons.foreach_get('normal', nn)
    me.polygons.foreach_get('area', ar)
    M = np.array(ob.matrix_world)
    cw = (c.reshape(-1, 3) @ M[:3, :3].T + M[:3, 3])[:, [0, 2, 1]]
    nw = nn.reshape(-1, 3) @ np.linalg.inv(M[:3, :3])
    nw = (nw / np.linalg.norm(nw, axis=1, keepdims=True))[:, [0, 2, 1]]
    x0, x1 = B.SEAT_R_X
    box = (nw[:, 1] > 0.5) & (cw[:, 0] > x0 - 0.01) & (cw[:, 0] < x1 + 0.01) & (cw[:, 2] > B.HERO_BACK_Z + 0.05) & \
          (cw[:, 2] < B.GUARD_Z) & (cw[:, 1] > 0.9) & (cw[:, 1] < 1.2)
    ytop = float(np.median(cw[box, 1]))
    top = box & (np.abs(cw[:, 1] - ytop) < 0.03)
    lo, hi = np.percentile(cw[top], 1, axis=0), np.percentile(cw[top], 99, axis=0)
    sel = top & (cw[:, 0] > lo[0] + 0.02) & (cw[:, 0] < hi[0] - 0.02) & (cw[:, 2] > lo[2] + 0.02) & (cw[:, 2] < hi[2] - 0.02)
    col = np.zeros((n, 4), np.float32)
    col[:, 3] = 1.0
    col[sel, 0] = 1.0
    at = me.attributes.get('d48_id') or me.attributes.new('d48_id', 'FLOAT_COLOR', 'FACE')
    at.data.foreach_set('color', col.ravel())
    return dict(faces=int(sel.sum()), area_m2=round(float(ar[sel].sum() * abs(np.linalg.det(M[:3, :3])) ** (2 / 3)), 4),
                top_y=round(ytop, 4), top_x=[round(float(lo[0]), 3), round(float(hi[0]), 3)],
                top_z=[round(float(lo[2]), 3), round(float(hi[2]), 3)], mesh_users=me.users,
                rule='up-facing (n.y > 0.5) faces within 3 cm of the cushion top height, 2 cm in from the top outline '
                     '(drops the welt and the rolled edges)')


def clearance(info, objs, names):
    """how the proxy sits against the cabin: per object, proxy vertices inside it (nearest face within 3 cm, behind
    it), the cabin's vertices inside a proxy part (convex hull test) and the smallest gap."""
    V, part = info['V'], info['part']
    lo, hi = V.min(0) - 0.05, V.max(0) + 0.05
    hulls = []
    for pn, (pv, _), _ in info['parts']:
        hulls.append((pn, Delaunay(pv), pv.min(0), pv.max(0)))
    out = {}
    for nm in names:
        ob = objs.get(nm)
        if ob is None or ob.type != 'MESH':
            continue
        vu, faces, vb = world_mesh(ob)
        if not ((vu >= lo) & (vu <= hi)).all(1).any():
            continue
        tree = BVHTree.FromPolygons([tuple(map(float, v)) for v in vb], faces)    # blender space: the winding's own side
        d_min, n_in, depth, where = 9.0, 0, 0.0, None
        for k, p in enumerate(V):
            pb = (float(p[0]), float(p[2]), float(p[1]))
            loc, nrm, _, dist = tree.find_nearest(pb, 0.10)
            if loc is None:
                continue
            d_min = min(d_min, dist)
            if dist < 0.03 and np.dot(np.subtract(pb, tuple(loc)), tuple(nrm)) < 0:
                n_in += 1
                if dist > depth:
                    depth, where = dist, (part[k], [round(float(x), 3) for x in p])
        cand = vu[((vu >= lo) & (vu <= hi)).all(1)]
        rev = {}
        for pn, hull, plo, phi in hulls:
            c2 = cand[((cand >= plo) & (cand <= phi)).all(1)]
            if len(c2):
                k = int((hull.find_simplex(c2) >= 0).sum())
                if k:
                    rev[pn] = rev.get(pn, 0) + k
        out[nm] = dict(min_gap_m=round(float(d_min), 4), proxy_verts_inside=n_in, max_depth_m=round(depth, 4),
                       deepest=where, cabin_verts_inside_proxy=rev)
    return out


# ------------------------------------------------------------------------------------------------ ID pass + measures
def id_material():
    m = bpy.data.materials.new('D48_ID')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    at = nt.nodes.new('ShaderNodeAttribute')
    at.attribute_type = 'GEOMETRY'
    at.attribute_name = 'd48_id'
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(at.outputs['Color'], em.inputs['Color'])
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(em.outputs[0], out.inputs[0])
    return m


def id_pass(path, mat, world):
    """every material -> the 'd48_id' face colour (R cushion top, G hero part / 10, B passenger head 1 / body 0.5),
    black world, no denoise: the same camera and pixel filter as the beauty render."""
    sc = bpy.context.scene
    vl = bpy.context.view_layer
    keep = (sc.cycles.samples, sc.cycles.use_denoising, sc.cycles.use_adaptive_sampling, sc.cycles.max_bounces, sc.world)
    vl.material_override = mat
    sc.world = world
    sc.cycles.samples, sc.cycles.use_denoising, sc.cycles.use_adaptive_sampling, sc.cycles.max_bounces = 16, False, False, 0
    try:
        return S.render_linear(path)
    finally:
        vl.material_override = None
        sc.cycles.samples, sc.cycles.use_denoising, sc.cycles.use_adaptive_sampling, sc.cycles.max_bounces, sc.world = keep


def decode_ids(idl):
    """clean labels: a pixel counts only if every channel is on a code and its 3 x 3 neighbourhood has the same codes
    (drops pixels mixed at edges)."""
    out = {}
    ok = np.ones(idl.shape[:2], bool)
    labs = []
    for ch, k in ((0, 1.0), (1, 10.0), (2, 2.0)):
        v = idl[..., ch] * k
        lab = np.rint(v)
        ok &= np.abs(v - lab) < 0.12
        ok &= ndimage.minimum_filter(lab, 3) == ndimage.maximum_filter(lab, 3)
        labs.append(lab.astype(int))
    r, g, b = labs
    out['cushion'] = ok & (r == 1) & (g == 0) & (b == 0)
    for pn, code in HERO_CODES.items():
        out['hero_' + pn] = ok & (r == 0) & (g == code) & (b == 0)
    out['mid_head'] = ok & (r == 0) & (g == 0) & (b == 2)
    out['mid_body'] = ok & (r == 0) & (g == 0) & (b == 1)
    out['any_proxy'] = (np.abs(idl[..., 1]) > 0.02) | (np.abs(idl[..., 2]) > 0.02)
    return out


def luma(px):
    return np.asarray(px, float)[..., :3] @ REC709          # sRGB luma on the 8-bit codes (Rec.709 weights)


def cushion_stats(px, mask, erode=2, sigma=3.0):
    """luma median / p10 / p90 / dark fractions on the mask; texture = local RMS (sigma window) of luma minus its
    sigma blur, both taken inside the mask only (normalised convolution), median over the mask eroded 'erode' px."""
    Y = luma(px)
    n = int(mask.sum())
    if n < 50:
        return dict(pixels=n)
    v = Y[mask]
    m = mask.astype(float)
    w = ndimage.gaussian_filter(m, sigma)
    blur = ndimage.gaussian_filter(Y * m, sigma) / np.maximum(w, 1e-6)
    hp = (Y - blur) * m
    rms = np.sqrt(ndimage.gaussian_filter(hp * hp, sigma) / np.maximum(w, 1e-6))
    core = ndimage.binary_erosion(mask, iterations=erode) if erode else mask
    if core.sum() < 50:
        core = mask
    return dict(pixels=n, luma_median=round(float(np.median(v)), 1), luma_p10=round(float(np.percentile(v, 10)), 1),
                luma_p90=round(float(np.percentile(v, 90)), 1), luma_mean=round(float(v.mean()), 1),
                frac_below_16=round(float((v < 16).mean()), 4), frac_below_24=round(float((v < 24).mean()), 4),
                texture_rms_median=round(float(np.median(rms[core])), 2), highpass_std=round(float(hp[core].std()), 2),
                texture_pixels=int(core.sum()))


def wstats(v, w):
    o = np.argsort(v)
    v, w = v[o], w[o]
    c = (np.cumsum(w) - 0.5 * w) / w.sum()
    return dict(mean=float((v * w).sum() / w.sum()), median=float(np.interp(0.5, c, v)), p90=float(np.interp(0.9, c, v)),
                max=float(v.max()))


def part_light(info, lights, eye, sel_parts):
    """per named part: area-weighted luminance stats of the vertex light, the side facing 'eye', and the point model."""
    V, N, A, part = info['V'], info['N'], info['area'], info['part']
    E = shade4(V, N, lights) @ REC709
    res = {}
    for key, names in sel_parts.items():
        s = np.isin(part, names)
        if not s.any():
            continue
        st = wstats(E[s], A[s])
        face = s & (np.einsum('ij,ij->i', N, np.asarray(eye)[None] - V) > 0)
        st['seen'] = float((E[face] * A[face]).sum() / A[face].sum()) if face.any() else None   # eye inside: None
        cen = (V[s] * A[s, None]).sum(0) / A[s].sum()
        st['point'] = omni(cen, lights)
        st['centroid'] = [round(float(x), 3) for x in cen]
        res[key] = st
    return res


def ev_table(parts, ref):
    def ev(x, r):
        return round(math.log2(x / r), 2) if x and r and x > 0 and r > 0 else None     # None: no value / no light
    return {p: {k: ev(parts[p][k], ref[k]) for k in ('mean', 'median', 'p90', 'seen', 'point')} for p in parts}


def rnd(d, n=4):
    if isinstance(d, dict):
        return {k: rnd(v, n) for k, v in d.items()}
    if isinstance(d, (list, tuple)):
        return [rnd(v, n) for v in d]
    if isinstance(d, float):
        return round(d, n)
    return d


# ------------------------------------------------------------------------------------------------ sheet + readme
def overlay(px, masks):
    """the graded frame darkened, the measured cushion pixels cyan, hand pixels yellow, mid-cabin heads magenta."""
    o = np.asarray(px, float) * 0.55
    for key, col in (('cushion', (0, 230, 255)), ('hero_hands', (255, 220, 0)), ('mid_head', (255, 60, 220))):
        m = masks.get(key)
        if m is not None and m.any():
            o[m] = 0.45 * o[m] / 0.55 + 0.55 * np.array(col)
    return Image.fromarray(np.clip(o, 0, 255).astype(np.uint8))


def contact_sheet(tiles, path, title, tw=480):
    """tiles: [(PIL image, title, line2)], 2 columns, a label band under each (slice_final's layout, own title)."""
    th = int(tw * 0.75)
    band, cols = 62, 2
    rows = (len(tiles) + cols - 1) // cols
    W, H = tw * cols + 6 * (cols + 1), (th + band) * rows + 6 * (rows + 1) + 30
    sheet = Image.new('RGB', (W, H), (18, 18, 20))
    dr = ImageDraw.Draw(sheet)
    f1, f2, f0 = SF.label_font(15), SF.label_font(12), SF.label_font(14)
    dr.text((8, 7), title, fill=(230, 230, 230), font=f0)
    for i, (img, t1, t2) in enumerate(tiles):
        x = 6 + (i % cols) * (tw + 6)
        y = 36 + (i // cols) * (th + band + 6)
        im = img.copy()
        im.thumbnail((tw, th), Image.Resampling.LANCZOS)
        sheet.paste(im, (x + (tw - im.width) // 2, y + (th - im.height) // 2))
        dr.text((x + 2, y + th + 4), t1, fill=(255, 255, 255), font=f1)
        for k, ln in enumerate(SF.wrap(dr, t2, f2, tw - 6)[:2]):
            dr.text((x + 2, y + th + 24 + 16 * k), ln, fill=(190, 190, 190), font=f2)
    return SF.save_capped(sheet, path)


def shown(path):
    """repo-relative for files in the repo, else as given."""
    ap = os.path.abspath(path)
    return os.path.relpath(ap, ROOT) if ap.startswith(ROOT + os.sep) else path


def fmt(v, f='%.2f'):
    return '—' if v is None else f % v


def write_readme(rec, path):
    L = []
    a = rec['args']
    L.append('# D-48 主座位夜间图（第 2 幕：夜路、管灯亮）\n')
    L.append('**没在 Unity 里编译、导入、运行过。这是 Blender 里的近似**：车厢照 `Lanbai/Cabin` 的几项拼（漫射只来自光照图），'
             '人是代理模型，身上的光照 Unity 逐顶点点光的公式在 Python 里算好再画上去。Unity 里是什么样，要等本地跑。\n')
    L.append('脚本：`Bus/Docs~/lookdev/d48_hero_night.py`（这一份：%d 采样、%d 线程、调色 %s、分辨率 × %g）。'
             '输入（只读，前后 md5 一样才算数）：`%s`（%s）、光照图 `%s`（%s）。\n'
             % (a['samples'], a['threads'], a['grade'], a['scale'], shown(a['blend']),
                '没动' if rec['inputs']['blend_untouched'] else '**md5 变了**', shown(a['lightmap']),
                '没动' if rec['inputs']['lightmap_untouched'] else '**md5 变了**'))
    if a.get('parts_dir'):
        L.append('座椅零件图集换成了 `%s` 里的（测试：旧的 .blend 配旧的图集）。\n' % shown(a['parts_dir']))
    L.append('## 图\n')
    L.append('| 图 | 机位（主座位的眼 (0.55, 1.70, 2.05)） | 是什么 | 渲染用时 |')
    L.append('|---|---|---|---|')
    for vid, v in rec['views'].items():
        L.append('| `%s` | 偏航 %g°、俯仰 %g°、水平 %g°、%d × %d | %s | %.0f s |'
                 % (v['png'], v['yaw_deg'], v['pitch_deg'], v['hfov_deg'], v['res'][0], v['res'][1], LOOK[vid],
                    v['seconds_render']))
    L.append('| `contact_sheet.png` | | 上面几张一页，加一张 hero_down 的“量了哪些像素”（青 = 座垫，黄 = 手） | |\n')
    cu = rec.get('cushion', {})
    if cu:
        L.append('## 座垫（`Seat_SeatR0` 顶面）调色以后\n')
        L.append('在调色以后的 8 位图上量（存 PNG 以前；PNG 超 400 KB 时会转 256 色，量的不是那一份）。亮度 = Rec.709 系数乘'
                 ' sRGB 码值，0–255。纹理反差 = 亮度减去 σ 3 px 的高斯模糊（只在座垫像素里模糊），σ 3 px 窗里的均方根，取中位。'
                 '挑面：%s，%d 个面、%.3f m²。\n' % ('朝上、座垫顶面那个高度、离四边 2 cm 以内（滚边）不要', cu['faces']['faces'],
                                                   cu['faces']['area_m2']))
        L.append('| 量在哪 | 像素 | 中位 | p10 | p90 | < 16 级 | < 24 级 | 纹理反差（级） |')
        L.append('|---|---|---|---|---|---|---|---|')
        for key, lab in (('hero_down', 'hero_down（人旁边露出来的）'),
                         ('hero_down_standard_view', 'hero_down，同一批像素不调色（Standard）'),
                         ('hero_down_noproxy', 'hero_down_noproxy（整块）'),
                         ('hero_down_noproxy_standard_view', 'hero_down_noproxy，不调色（Standard）'),
                         ('hero_down_noproxy_on_common', 'hero_down_noproxy，只取 hero_down 量的那些像素')):
            s = cu.get(key)
            if not s or 'luma_median' not in s:
                continue
            L.append('| %s | %d | %.1f | %.1f | %.1f | %.1f %% | %.1f %% | %.2f |'
                     % (lab, s['pixels'], s['luma_median'], s['luma_p10'], s['luma_p90'], 100 * s['frac_below_16'],
                        100 * s['frac_below_24'], s['texture_rms_median']))
        if 'diff_common' in cu:
            d = cu['diff_common']
            L.append('\n同一批像素上，放人和不放人差多少（亮度，级）：平均 %.2f、绝对值平均 %.2f、p99 %.1f。'
                     '人对光泽、影子、漫射都隐身，这里的差只是采样噪声和降噪。\n' % (d['mean'], d['mean_abs'], d['p99_abs']))
        crit = cu.get('crushed_rule')
        if crit:
            L.append('按这里定的口径（%s）：%s（调色以后的纹理反差是不调色的 %.2f 倍）。\n'
                     % (crit['rule'], '**压黑了或压平了**' if crit['crushed'] else '没有压成一块黑', crit['texture_ratio_graded_to_standard']))
    bad = ['%s / %s' % (who, ob) for who, d in rec.get('proxy_clearance', {}).items() for ob, c in d.items()
           if c['proxy_verts_inside'] or c['cabin_verts_inside_proxy']]
    gaps = [c['min_gap_m'] for d in rec.get('proxy_clearance', {}).values() for c in d.values()]
    L.append('## 人和车厢穿插没有\n')
    L.append(('**有穿插**：' + '、'.join(bad) + '（细节见 json 的 proxy_clearance）。\n') if bad else
             '没有：人身上没有顶点进到座椅、车厢里，车厢也没有顶点进到人身上；离得最近 %.1f cm（json 的 proxy_clearance）。\n'
             % (100 * min(gaps) if gaps else 0))
    lc = rec.get('lights_vs_layout')
    if lc:
        L.append('三盏灯和 `%s` 对过：%s。\n' % (lc['path'], '一样' if lc.get('match') else
                 '**不一样**（那里有 %s 盏；以 finish_bus.py 的 HERO_FILL 为准算的，重导出以后再跑一次）' % lc.get('lights_in_layout', '?')))
    vl = rec.get('vertex_light')
    if vl:
        L.append('## 人身上的逐顶点光（Unity 的 Shade4PointLights 照抄）\n')
        L.append('三盏补光：' + '；'.join('%s (%.2f, %.2f, %.2f) 强度 %.3g range %g' % (li['name'], *li['pos'], li['intensity'],
                                                                                    li['range']) for li in rec['lights'])
                 + '；颜色 %s（线性 %s），× 管灯档位 %g。E 是线性亮度（Rec.709），不乘反照率。\n'
                 % (FILL_COLOUR, ', '.join('%.3f' % c for c in rec['lights'][0]['colour_linear']), rec['lights'][0]['level']))
        L.append('几种取法：平均 = 这一部位全部表面按面积平均；p90 = 亮的那一侧；对眼 = 法线朝着主座位眼睛的那半边的平均；'
                 '点 = 部位中心一个点、不管法线（n·l 当 1），finish_bus 注释里的数像是这样算的。\n')
        L.append('| 部位 | E 平均 | E 对眼 | E 点 | EV 平均 | EV p90 | EV 对眼 | EV 点 | finish_bus 注释 | 补光以前 EV 点 |')
        L.append('|---|---|---|---|---|---|---|---|---|---|')
        for p in SEEN_PARTS:
            h = vl['hero'].get(p)
            if not h:
                continue
            e = vl['ev_vs_mid_heads'][p]
            eb = vl['ev_vs_mid_heads_before'][p]
            L.append('| %s | %s | %s | %s | %s | %s | %s | %s | %s | %s |'
                     % ({'hands': '手', 'lap': '大腿', 'chest': '胸', 'head': '头（不画，只算数）'}[p],
                        *[fmt(h[k], '%.3f') for k in ('mean', 'seen', 'point')], *[fmt(e[k], '%+.2f') for k in ('mean', 'p90', 'seen', 'point')],
                        fmt(vl['documented'].get(p), '%+.2f'), fmt(eb['point'], '%+.2f')))
        m = vl['mid_heads']
        L.append('| 车厢中段的头（%d 个的平均） | %.3f | %.3f | %.3f | 0 | 0 | 0 | 0 | | |\n'
                 % (len(m['seats']), m['mean'], m['seen'], m['point']))
        w2 = vl.get('point_model_ref_without_fill2')
        if w2:
            L.append('注释里的数怎么来的：点的取法、车厢中段的头只算 HeadFill_0/1（不算 HeadFill_2）时，这里得 '
                     + '、'.join('%s %+.2f' % ({'hands': '手', 'lap': '大腿', 'chest': '胸', 'head': '头'}[p], w2[p]) for p in SEEN_PARTS)
                     + ' EV。可 HeadFill_2 的 range 是 5，车厢中段的头离它不到 3 m，Unity 里它也照那些头（这里算是占它们的 %.0f %%，'
                       '点的取法），所以同一个点的取法下差距要再大约 %.2f EV。\n'
                     % (100 * vl['fill2_share_of_mid_heads']['point'],
                        float(np.mean([w2[p] - vl['ev_vs_mid_heads'][p]['point'] for p in SEEN_PARTS]))))
        L.append('车厢中段每个头：' + '；'.join('%s 平均 %.3f、p90 %.3f、对眼 %.3f、点 %.3f' % (k, v['mean'], v['p90'], v['seen'], v['point'])
                                           for k, v in vl['mid_heads_each'].items()) + '（头中心 z：'
                 + '、'.join('%s %.2f' % (k, v['centroid'][2]) for k, v in vl['mid_heads_each'].items())
                 + '；两盏排灯在 z 0）。\n')
    img = rec.get('image_ev')
    if img:
        L.append('从图上量（同一个肤色，线性亮度的中位，调色以前）：hero_down 里的手 %.4f、ref_back 里车厢中段的头 %.4f，'
                 '差 %+.2f EV；调色以后亮度中位：手 %.1f 级、头 %.1f 级。\n'
                 % (img['hands_lin_median'], img['mid_heads_lin_median'], img['ev'], img['hands_luma_median'],
                    img['mid_heads_luma_median']))
    L.append('## 哪些是近似\n')
    L.append('- **没在 Unity 里编译、导入、运行过。** 车厢是 Cycles 里照 `Lanbai/Cabin` 拼的（`scene_acts.build()` 第 2 幕 + 漫射只来自'
             '光照图，光泽照常追、代替车厢的反射探针），调色是渲染标准台的 PPv2 模拟（S2，bloom 开，VR 不加镜头层）。')
    L.append('- 人是代理模型（胶囊、椭球），不是哪个 VRChat 头像。坐姿是估的：靠着靠背，手放在大腿靠膝的地方；前轮罩占了座垫前面'
             '右半边的腿位，两条腿往过道偏。主座位的眼是合同里的点，人按它配：坐着眼高比座垫高 0.66 m，比一般成年人矮一点'
             '（像稍微窝着坐）。')
    L.append('- 人身上的光只有三盏补光的逐顶点项，照 `Shade4PointLights`：颜色线性 × 强度 × max(0, n·l) / (1 + 25 d² / range²)，'
             '顶点之间线性插值（Cycles 的属性插值 = Unity 的 Gouraud）。没算：Standard 的漫射项还要乘 (1 − 0.04)（介电的反射率，'
             '暗 0.06 EV，各部位一样，EV 差里抵掉）；光照探针 / 环境光（第 2 幕是 0）；头像自己的 shader（很多卡通 shader 对逐顶点光'
             '另有处理，有的不吃）。Unity 按物体包围盒挑灯，range 内才算，这里三盏都够得着。')
    L.append('- 人对光泽光线隐身、不挡影子、不进漫射：座垫上不会多出亮斑或第二个影子（和 Unity 一样：逐顶点光只照 Player 层，'
             '人不进光照图，反射探针里没有人）。')
    L.append('- 量座垫的像素靠另渲一张 ID 图（同一机位、同一像素滤镜，16 采样、不降噪），边上混色的像素扔掉。纹理反差和分辨率有关'
             '（σ 3 px），只和同分辨率的数比。')
    L.append('- 车厢中段在主座位后面：往前看的图里看不到那几个人，所以加了 `ref_back`（往后看）当参照；那张里主座位自己的身体'
             '藏起来了。')
    open(path, 'w', encoding='utf-8').write('\n'.join(L) + '\n')


# ------------------------------------------------------------------------------------------------ main
def main():
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    ap = argparse.ArgumentParser()
    ap.add_argument('--blend', default='/tmp/bus/bus_final_ext.blend')
    ap.add_argument('--lightmap', default=DEFAULT_LM, help='the _CabinTubeLM EXR (default Bus/Textures/Cabin_TubeLM.exr)')
    ap.add_argument('--parts-dir', default='', help='take the seat part atlases (Part_*.png) from this folder instead of '
                                                     'Bus/Textures/Parts (tests on an older .blend whose uv0 matches them)')
    ap.add_argument('--out', default=os.path.join(HERE, 'd48'))
    ap.add_argument('--samples', type=int, default=48)
    ap.add_argument('--threads', type=int, default=4)
    ap.add_argument('--grade', default='S2', help="harness grade key for act 2 (S2), or 'none' (Standard view)")
    ap.add_argument('--scale', type=float, default=1.0, help='resolution scale for tests (0.5 = 480 x 360)')
    ap.add_argument('--views', default=','.join(VIEWS), help='comma list of view ids')
    a = ap.parse_args(argv)
    views = [v for v in a.views.split(',') if v]
    for v in views:
        if v not in VIEWS:
            raise SystemExit('unknown view %r (%s)' % (v, ', '.join(VIEWS)))
    os.makedirs(a.out, exist_ok=True)
    T0 = time.time()
    md5_blend, md5_lm = SF.md5(a.blend), SF.md5(a.lightmap)
    tmp = tempfile.mkdtemp(prefix='d48_hero_night_')
    work = os.path.join(tmp, 'bus_final_ext_copy.blend')
    shutil.copyfile(a.blend, work)                         # read the copy, never the original

    # ---- the act-2 whole bus, exactly as slice_final's two hero-eye views
    S.new_scene(samples=a.samples, res=(960, 720), denoise=True, threads=a.threads)
    sc = bpy.context.scene
    ctx = dict(t=30.0, cam=S.camera_spec('hero'), eye=list(EYE), act='02', args={'act': '2', 'blend': work},
               U2B=S.U2B, lbh_scene=S, quality='final')
    info = SA.build(ctx)
    lm_used = []
    for im in bpy.data.images:                              # --lightmap: point the build's image at another copy
        if os.path.basename(im.filepath).startswith('Cabin_TubeLM'):
            if os.path.abspath(bpy.path.abspath(im.filepath)) != os.path.abspath(a.lightmap):
                im.filepath = a.lightmap
                im.reload()
            lm_used.append(os.path.abspath(bpy.path.abspath(im.filepath)))
        elif a.parts_dir and os.path.basename(im.filepath).startswith('Part_'):
            alt = os.path.join(a.parts_dir, os.path.basename(im.filepath))
            if os.path.exists(alt):
                im.filepath = alt
                im.reload()
    parts_used = sorted(os.path.abspath(bpy.path.abspath(im.filepath)) for im in bpy.data.images
                        if os.path.basename(im.filepath).startswith('Part_'))
    objs = {o.name: o for o in bpy.data.objects}
    SF.lanbai_cabin_only_lightmap(objs)
    base_hide = {o.name: o.hide_render for o in bpy.data.objects}
    SF.whole_bus(base_hide)
    bpy.context.view_layer.update()
    t_build = time.time() - T0

    # ---- the cushion top of the hero seat (ID pass) and the people
    cush = mark_cushion(objs['Seat_SeatR0'])
    cx, cy, bz = sum(B.SEAT_R_X) / 2, cush['top_y'], B.HERO_BACK_Z
    lights = head_fills(SA.ACTS['2']['tubes'])
    lights_before = [li for li in lights if li['name'] != 'HeadFill_2']
    mats = dict(skin=proxy_material('D48_Skin', SKIN), cloth=proxy_material('D48_Cloth', CLOTH),
                shoe=proxy_material('D48_Shoe', SHOE))
    hero_ob, hero = make_person('D48_Hero', hero_parts(cx, cy, bz), mats,
                                lambda p: (0.0, HERO_CODES.get(p, 3) / 10.0, 0.0))
    set_vertex_light(hero_ob, shade4(hero['V'], hero['N'], lights))
    mids = {}
    # mid cabin, both rows, one row each side of the head fills' z (0): the faces of the two ahead of it (R2, L2) see
    # those lamps only from above-behind, the two behind it (R3, L3) face them. x of the aisle place: BusLayout.json
    mid_seats = {'SeatR2': (sum(B.SEAT_R_X) / 2, B.FLOOR_Y + B.SEAT_H, B.RIGHT_ROWS[2]),
                 'SeatR3': (sum(B.SEAT_R_X) / 2, B.FLOOR_Y + B.SEAT_H, B.RIGHT_ROWS[3]),
                 'SeatL2a': (-0.66, B.FLOOR_Y + B.SEAT_H, B.LEFT_ROWS[2]),
                 'SeatL3a': (-0.66, B.FLOOR_Y + B.SEAT_H, B.LEFT_ROWS[3])}
    for sn, (mx, my, mz) in mid_seats.items():
        ob, inf = make_person('D48_Mid_' + sn, passenger_parts(mx, my, mz), mats,
                              lambda p: (0.0, 0.0, 1.0 if p == 'head' else 0.5))
        set_vertex_light(ob, shade4(inf['V'], inf['N'], lights))
        mids[sn] = (ob, inf, (mx, my, mz))
    # the hero's own head: numbers only (smooth normals + areas through the same code path, then dropped)
    tmp_ob, head_info = make_person('D48_HeroHeadVirtual', [('head', hero_head_virtual(cx, bz), 'skin')], mats,
                                    lambda p: (0.0, 0.0, 0.0))
    tmp_me = tmp_ob.data
    bpy.data.objects.remove(tmp_ob)
    bpy.data.meshes.remove(tmp_me)

    # ---- vertex-light numbers
    sel = dict(hands=['hands'], lap=['thighs'], chest=['chest'], forearms=['forearms'], upper_arms=['upper_arms'],
               abdomen=['abdomen'], shins=['shins'])
    vlr = {}
    for tag, L_ in (('', lights), ('_before', lights_before)):
        hp = part_light(hero, L_, EYE, sel)
        hp['head'] = part_light(head_info, L_, EYE, dict(head=['head']))['head']
        each = {sn: part_light(inf, L_, EYE, dict(head=['head']))['head'] for sn, (_, inf, _) in mids.items()}
        ref = {k: float(np.mean([e[k] for e in each.values()])) for k in ('mean', 'median', 'p90', 'seen', 'point', 'max')}
        ref['seats'] = list(each)
        vlr['hero' + tag] = hp
        vlr['mid_heads_each' + tag] = each
        vlr['mid_heads' + tag] = ref
        vlr['ev_vs_mid_heads' + tag] = ev_table(hp, ref)
        vlr['ev_vs_each_mid_head' + tag] = {sn: ev_table({p: hp[p] for p in SEEN_PARTS}, e) for sn, e in each.items()}
    _, documented = hero_fill_from_source()
    vlr['documented'] = documented
    # the finish_bus comment's numbers come back with the point model when the mid-cabin heads are lit by HeadFill_0/1
    # only; in Unity HeadFill_2 (range 5) reaches them too (Unity culls by range against the renderer bounds)
    ref_wo2 = float(np.mean([e['point'] for e in vlr['mid_heads_each_before'].values()]))
    vlr['point_model_ref_without_fill2'] = {p: math.log2(vlr['hero'][p]['point'] / ref_wo2) for p in SEEN_PARTS}
    vlr['fill2_share_of_mid_heads'] = {k: 1.0 - vlr['mid_heads_before'][k] / vlr['mid_heads'][k] for k in ('mean', 'seen', 'point')}
    vlr['statistics'] = ('E = Rec.709 luminance of the summed vertex light (linear, no albedo); per part, area-weighted '
                         'over its vertices: mean, median, p90, max; seen = mean over vertices whose normal faces the hero '
                         'eye; point = the sum at the part centroid with n.l = 1 (no normal)')
    vlr = rnd(vlr)

    # ---- how the people sit against the cabin
    near_hero = ['Seat_SeatR0', 'Cabin_Static', 'Pole_R0', 'Window_R1', 'Bus_Exterior_LOD0', 'Cabin_Curtains', 'Seat_SeatR1']
    clear = dict(hero=clearance(hero, objs, near_hero))
    for sn, (ob, inf, _) in mids.items():
        seat = 'Seat_' + sn.rstrip('a')
        ahead = seat[:-1] + str(int(seat[-1]) - 1)               # the seat in front (knees, back)
        clear[sn] = clearance(inf, objs, [seat, ahead, 'Cabin_Static', 'Cabin_Curtains'])

    # ---- renders
    idmat = id_material()
    idworld = bpy.data.worlds.new('D48_IDWorld')
    idworld.use_nodes = True
    idworld.node_tree.nodes['Background'].inputs[0].default_value = (0, 0, 0, 1)
    people = dict(hero=[hero_ob], mid=[m[0] for m in mids.values()])
    rec = dict(what='D-48 主座位夜间图：第 2 幕，主座位的眼往下看 / 往前看，人是代理模型，人身上是 Unity 逐顶点点光的近似',
               note='没在 Unity 里编译、导入、运行过；这是 Blender 里的近似（Cycles）。',
               command='~/bpy/bin/python -B Bus/Docs~/lookdev/d48_hero_night.py ' + ' '.join(argv),
               args=dict(vars(a)), scene=info, lights=lights, lightmap_images=lm_used, part_atlases=parts_used,
               shading='scene_acts.build(act 2) + slice_final.lanbai_cabin_only_lightmap + whole_bus (diffuse from the '
                       'lightmap only, glossy traced); people: emission = albedo x per-vertex Shade4PointLights sum, invisible '
                       'to glossy / shadow / diffuse rays',
               engine='Cycles CPU, OpenImageDenoise', grade=a.grade if a.grade == 'none' else
               '%s (lbh/grade.py, bloom on, no lens layer = VR)' % a.grade,
               proxies=dict(albedo=dict(skin=SKIN, cloth=CLOTH, shoe=SHOE),
                            hero=dict(seat='SeatR0', cushion_top_y=cy, back_z=bz, centre_x=cx,
                                      parts=sorted(set(hero['part'].tolist())), verts=len(hero['V'])),
                            mid={sn: dict(seat_xyz=list(v[2]), verts=len(v[1]['V'])) for sn, v in mids.items()},
                            note='hero: no head (the camera is the head); legs lean to the aisle (front wheel box + knee '
                                 'guard in front of the right half of the cushion)'),
               proxy_clearance=clear, lights_vs_layout=layout_check(lights), vertex_light=vlr, cushion=dict(faces=cush), views={}, timing=dict(build_s=round(t_build, 1)))
    frames = {}
    for vid in views:
        spec = VIEWS[vid]
        for k, obs in people.items():
            for o in obs:
                o.hide_render = k not in spec['show']
        res = [int(round(spec['res'][0] * a.scale)), int(round(spec['res'][1] * a.scale))]
        cam = S.add_camera(dict(eye=spec['eye'], yaw_deg=spec['yaw_deg'], pitch_deg=spec['pitch_deg'],
                                hfov_deg=spec['hfov_deg'], res=res), name='Cam_' + vid)
        t0 = time.time()
        lin = S.render_linear(os.path.join(tmp, vid + '.exr'))
        t1 = time.time()
        px = SF.to_png(lin, a.grade)
        t2 = time.time()
        p = os.path.join(a.out, vid + '.png')
        how = SF.save_capped(Image.fromarray(px), p)
        t3 = time.time()
        idl = id_pass(os.path.join(tmp, vid + '_id.exr'), idmat, idworld)
        t4 = time.time()
        masks = decode_ids(idl)
        frames[vid] = dict(px=px, lin=lin, masks=masks)
        vf = math.degrees(2 * math.atan(math.tan(math.radians(spec['hfov_deg'] / 2)) * res[1] / res[0]))
        rec['views'][vid] = dict(eye=spec['eye'], yaw_deg=spec['yaw_deg'], pitch_deg=spec['pitch_deg'],
                                 hfov_deg=spec['hfov_deg'], vfov_deg=round(vf, 2), res=res, people_shown=list(spec['show']),
                                 png=os.path.basename(p), png_kb=round(os.path.getsize(p) / 1024), png_mode=how,
                                 mean_srgb=round(float(px.mean()), 1), seconds_render=round(t1 - t0, 1),
                                 seconds_grade=round(t2 - t1, 1), seconds_id_pass=round(t4 - t3, 1),
                                 pixels={k: int(m.sum()) for k, m in masks.items()}, look_at=LOOK[vid])
        cam.hide_render = True
        print('[d48] %s render %.0f s, grade %.0f s, id %.0f s -> %s' % (vid, t1 - t0, t2 - t1, t4 - t3, p), flush=True)

    # ---- cushion numbers
    cu = rec['cushion']
    for vid in ('hero_down', 'hero_down_noproxy'):
        if vid in frames:
            f = frames[vid]
            cu[vid] = cushion_stats(f['px'], f['masks']['cushion'])
            # the same pixels without the grade (Standard view, linear -> sRGB): what the grade does to them
            cu[vid + '_standard_view'] = cushion_stats(SF.QA.lin_to_srgb8(f['lin']), f['masks']['cushion'])
            if rec['views'][vid]['png_mode'] != 'rgb':                      # what the saved (palette) PNG holds
                q = np.asarray(Image.open(os.path.join(a.out, rec['views'][vid]['png'])).convert('RGB'))
                if q.shape == f['px'].shape:
                    cu[vid + '_saved_png'] = cushion_stats(q, f['masks']['cushion'])
    if 'hero_down' in frames and 'hero_down_noproxy' in frames:
        common = frames['hero_down']['masks']['cushion'] & frames['hero_down_noproxy']['masks']['cushion']
        cu['hero_down_noproxy_on_common'] = cushion_stats(frames['hero_down_noproxy']['px'], common)
        cu['hero_down_on_common'] = cushion_stats(frames['hero_down']['px'], common)
        if common.sum():
            d = luma(frames['hero_down']['px'])[common] - luma(frames['hero_down_noproxy']['px'])[common]
            cu['diff_common'] = dict(pixels=int(common.sum()), mean=round(float(d.mean()), 2),
                                     mean_abs=round(float(np.abs(d).mean()), 2),
                                     p99_abs=round(float(np.percentile(np.abs(d), 99)), 1))
    s, s0 = cu.get('hero_down'), cu.get('hero_down_standard_view')
    if s and s0 and 'luma_p10' in s and 'luma_p10' in s0:
        ratio = s['texture_rms_median'] / max(s0['texture_rms_median'], 1e-6)
        cu['crushed_rule'] = dict(
            rule='中位 ≥ 32 级、p10 ≥ 16 级、低于 16 级的 < 5 %、调色以后的纹理反差 ≥ 不调色（Standard）的 0.8 倍',
            texture_ratio_graded_to_standard=round(ratio, 2),
            crushed=bool(s['luma_median'] < 32 or s['luma_p10'] < 16 or s['frac_below_16'] >= 0.05 or ratio < 0.8))

    # ---- hands vs mid-cabin heads, measured on the frames (same skin albedo)
    if 'hero_down' in frames and 'ref_back' in frames:
        hm, mm = frames['hero_down']['masks']['hero_hands'], frames['ref_back']['masks']['mid_head']
        if hm.sum() > 20 and mm.sum() > 20:
            lh = frames['hero_down']['lin'] @ REC709
            lm = frames['ref_back']['lin'] @ REC709
            a_, b_ = float(np.median(lh[hm])), float(np.median(lm[mm]))
            rec['image_ev'] = dict(hands_pixels=int(hm.sum()), mid_head_pixels=int(mm.sum()), hands_lin_median=round(a_, 5),
                                   mid_heads_lin_median=round(b_, 5), ev=round(math.log2(a_ / b_), 2),
                                   hands_luma_median=round(float(np.median(luma(frames['hero_down']['px'])[hm])), 1),
                                   mid_heads_luma_median=round(float(np.median(luma(frames['ref_back']['px'])[mm])), 1),
                                   note='scene-linear luminance before the grade (no bloom); both skin, same albedo')

    # ---- contact sheet
    tiles = []
    for vid in views:
        v = rec['views'][vid]
        tiles.append((Image.fromarray(frames[vid]['px']),
                      '%s · 偏航 %g° 俯仰 %g° · 水平 %g°' % (vid, v['yaw_deg'], v['pitch_deg'], v['hfov_deg']), '看：' + LOOK[vid]))
    if 'hero_down' in frames:
        s = cu.get('hero_down', {})
        tiles.append((overlay(frames['hero_down']['px'], frames['hero_down']['masks']), 'hero_down · 量了哪些像素',
                       '青 = 座垫（%d px，中位 %s 级，p10 %s，纹理 %s 级），黄 = 手'
                       % (s.get('pixels', 0), s.get('luma_median', '—'), s.get('luma_p10', '—'), s.get('texture_rms_median', '—'))))
    if tiles:
        sp = os.path.join(a.out, 'contact_sheet.png')
        rec['contact_sheet'] = dict(png='contact_sheet.png', mode=contact_sheet(
            tiles, sp, 'D-48 主座位夜间图 · 第 2 幕夜路、管灯亮 · Blender 近似（Cycles），不是 Unity 截图 · 人 = 代理模型'),
            kb=round(os.path.getsize(sp) / 1024))

    # ---- inputs untouched, json, readme
    rec['inputs'] = dict(blend=a.blend, blend_md5_before=md5_blend, blend_md5_after=SF.md5(a.blend),
                         lightmap=a.lightmap, lightmap_md5_before=md5_lm, lightmap_md5_after=SF.md5(a.lightmap))
    rec['inputs']['blend_untouched'] = rec['inputs']['blend_md5_after'] == md5_blend
    rec['inputs']['lightmap_untouched'] = rec['inputs']['lightmap_md5_after'] == md5_lm
    rec['timing']['total_s'] = round(time.time() - T0, 1)
    with open(os.path.join(a.out, 'd48_hero_night.json'), 'w', encoding='utf-8') as f:
        json.dump(rnd(rec), f, ensure_ascii=False, indent=1)
    write_readme(rnd(rec), os.path.join(a.out, 'README.md'))
    shutil.rmtree(tmp, ignore_errors=True)
    print('[d48] inputs untouched: blend %s, lightmap %s -> %s' % (rec['inputs']['blend_untouched'],
                                                                   rec['inputs']['lightmap_untouched'], a.out))


if __name__ == '__main__':
    main()
