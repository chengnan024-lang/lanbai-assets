# -*- coding: utf-8 -*-
"""D-13：里尔克诗块的候选位置，主座位 t = 140。
真车（build_bus）+ 一个按门的时间表算出来的伤口透镜（Gate/GateLayout_v2.json：gate_z、h_bus、tear_H；圣经 §6·4 的形状：
最宽处在 40% 高度、左 45% / 右 55%、轴斜 4°；核心 #F5F2EC）+ 月（−12°/+8°，1.2°）+ 云海顶 + 诗块（真字体、真字高）。
不是门的画面（门的包有自己的渲染），只为看诗块和伤口、月、A 柱、中柱的关系。
    --set poem=az,el  [--set em=2.2]
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'Source'))
import build_bus  # noqa: E402
import bus_spec as B  # noqa: E402

V_G, U6, U9, U6E = 59.0164, 133.8, 179.55, 160.50
H_KNOTS = [(133.8, 565.0), (150.3, 616.0), (155.1, 640.0), (160.5, 715.0), (166.15, 799.0), (179.55, 1000.0)]


def lin(h):
    return build_bus.srgb2lin(h)


def ss(x):
    x = min(1.0, max(0.0, x))
    return x * x * (3 - 2 * x)


def h_bus(t):
    return 40 + 20 * ss((t - U6) / (U6E - U6)) if t <= U6E else 60 + 90 * ss((t - U6E) / (U9 - U6E))


def tear_H(t):
    from scipy.interpolate import PchipInterpolator
    k = np.array(H_KNOTS)
    return float(PchipInterpolator(k[:, 0], k[:, 1])(t))


def emis(name, rgb, k):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs[0].default_value = (*rgb, 1)
    e.inputs[1].default_value = k
    o = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(e.outputs[0], o.inputs[0])
    return m


def lens(S, t, eye):
    D = V_G * (U9 - t)                 # gate z (bus at origin)
    h = h_bus(t)
    H = tear_H(t)
    wfrac = 0.18 + (0.22 - 0.18) * min(1.0, max(0.0, (t - 133.8) / (150.3 - 133.8)))
    y0, y1 = -h - 90.0, -h + H
    tilt = math.radians(4.0)
    V = []
    n = 48
    for k in range(n + 1):
        u = k / n
        y = y0 + (y1 - y0) * u
        # lens profile: widest at 40 %, pointed ends
        w = wfrac * H * (math.sin(math.pi * min(1.0, u / 0.8)) ** 0.8 if u < 0.4 else math.sin(math.pi * (0.5 + 0.5 * (u - 0.4) / 0.6)) ** 0.9)
        xc = (y - y0) * math.tan(tilt)
        V.append(((xc - 0.45 * w, y, D), (xc + 0.55 * w, y, D)))
    verts, faces = [], []
    for k, (a, b) in enumerate(V):
        verts += [a, b]
        if k:
            i = 2 * k
            faces.append((i - 2, i - 1, i + 1, i))
    core = emis('TearCore', lin('#FFEDD1'), 2 ** 1.84)
    S.mesh_object('TearCore', verts, faces, core)
    halo = emis('TearHalo', lin('#C6B4FF'), 2 ** 1.04 * 0.35)
    vh = [(x * 1.6, y, z + 5) for (x, y, z) in verts]
    S.mesh_object('TearHalo', vh, faces, halo)
    # the cloud-sea top (moonlit, dark)
    sea = emis('CloudTop', lin('#2A3248'), 0.35)
    S.mesh_object('CloudTop', [(-6000, -h, 0), (6000, -h, 0), (6000, -h, 9000), (-6000, -h, 9000)], [(0, 1, 2, 3)], sea)
    return dict(D=D, h=h, H=H, top_el=math.degrees(math.atan2(y1 - eye[1], D - eye[2])))


def disc(S, name, az, el, diam_deg, mat, r=900.0, eye=B.EYE):
    d = B.dir_az_el(az, el)
    c = [eye[k] + r * d[k] for k in range(3)]
    R = r * math.tan(math.radians(diam_deg / 2))
    up = (0, 1, 0)
    rx = np.cross(up, d)
    rx /= np.linalg.norm(rx)
    ry = np.cross(d, rx)
    V = [c] + [list(np.array(c) + R * (math.cos(a) * rx + math.sin(a) * ry)) for a in np.linspace(0, 2 * math.pi, 33)[:-1]]
    S.mesh_object(name, V, [(0, 1 + k, 1 + (k + 1) % 32) for k in range(32)], mat)


def poem_texture(path, em):
    """the block as Unity will set it: German italic (em deg) in two lines, Chinese translation 1.8 deg below."""
    from PIL import Image, ImageDraw, ImageFont
    ppd = 60
    fde = ImageFont.truetype(os.path.join(ROOT, 'Fonts', 'Originals~', 'EBGaramond-Italic.ttf'), int(em * ppd))
    fzh = ImageFont.truetype(os.path.join(ROOT, 'Fonts', 'Originals~', 'SourceHanSerifCN-Medium.otf'), int(1.8 * ppd))
    de = ['Denn das Schöne ist nichts', 'als des Schrecklichen Anfang']
    zh = ['因为美无非是', '恐怖的开端']
    W = int(max(fde.getlength(s) for s in de) + 2 * ppd)
    lh_de, lh_zh = int(em * ppd * 1.2), int(1.8 * ppd * 1.3)
    Hh = 2 * lh_de + int(0.8 * ppd) + 2 * lh_zh + ppd
    im = Image.new('L', (W, Hh), 0)
    d = ImageDraw.Draw(im)
    y = ppd // 2
    for s in de:
        d.text(((W - fde.getlength(s)) / 2, y), s, font=fde, fill=255)
        y += lh_de
    y += int(0.8 * ppd)
    for s in zh:
        d.text(((W - fzh.getlength(s)) / 2, y), s, font=fzh, fill=255)
        y += lh_zh
    im.save(path)
    return W / ppd, Hh / ppd, max(fde.getlength(s) for s in de) / ppd


def poem(S, az, el, em, eye):
    path = '/tmp/bus/poem_%.1f.png' % em
    wdeg, hdeg, text_w = poem_texture(path, em)
    r = 60.0
    d = np.array(B.dir_az_el(az, el))
    c = np.array(eye) + r * d
    rx = np.cross((0, 1, 0), d)
    rx /= np.linalg.norm(rx)
    ry = np.cross(d, rx)
    hw, hh = r * math.tan(math.radians(wdeg / 2)), r * math.tan(math.radians(hdeg / 2))
    V = [list(c - hw * rx - hh * ry), list(c + hw * rx - hh * ry), list(c + hw * rx + hh * ry), list(c - hw * rx + hh * ry)]
    ob = S.mesh_object('Poem', V, [(0, 1, 2, 3)], None)
    me = ob.data
    uvl = me.uv_layers.new(name='UVMap')
    for li, uv in zip(range(4), [(0, 0), (1, 0), (1, 1), (0, 1)]):
        uvl.data[li].uv = uv
    m = bpy.data.materials.new('PoemMat')
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    tex = nt.nodes.new('ShaderNodeTexImage')
    tex.image = bpy.data.images.load(path)
    tex.image.colorspace_settings.name = 'Non-Color'
    e = nt.nodes.new('ShaderNodeEmission')
    e.inputs[0].default_value = (*lin('#D8DDE6'), 1)
    e.inputs[1].default_value = 0.55
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mix = nt.nodes.new('ShaderNodeMixShader')
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    nt.links.new(tex.outputs['Color'], mix.inputs[0])
    nt.links.new(tr.outputs[0], mix.inputs[1])
    nt.links.new(e.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])
    me.materials.append(m)
    return dict(block_w_deg=round(text_w, 1), block_h_deg=round(hdeg, 1))


def build(ctx):
    S = ctx['lbh_scene']
    a = ctx['args']
    t = float(ctx['t'] if ctx['t'] is not None else 140.0)
    eye = ctx['eye']
    build_bus.build(open_door=True, reset=False)
    sys.path.insert(0, HERE)
    import scene_bus as SB
    # act 4, t = 140: the tubes dying from 0.5 to 0.31 (bible 4.8: U6 -> 163.80); cabin ambient = moon #232A3A x 0.3
    tubes = 0.5 + (0.31 - 0.5) * min(1.0, max(0.0, (t - U6) / (163.80 - U6)))
    SB.tube_lights(S, scale=tubes, watts=7.0)
    S.unity_ambient_flat(tuple(0.3 * c for c in lin('#232A3A')))
    info = lens(S, t, eye)
    disc(S, 'Moon', -12, 8, 1.2, emis('MoonMat', lin('#E8EEF8'), 6.0))
    em = float(a.get('em', 2.2))
    if 'poem' in a:
        az, el = (float(v) for v in a['poem'].split(','))
        info.update(poem(S, az, el, em, eye), poem_az=az, poem_el=el, em=em)
    return dict(what='D-13 Rilke candidate t=%.1f' % t, **{k: (round(v, 2) if isinstance(v, float) else v) for k, v in info.items()})
