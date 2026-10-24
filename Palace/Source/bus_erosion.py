# -*- coding: utf-8 -*-
"""参考渲染用的车厢侵蚀（第 8 轮，评审 r5 新阻断 1）：照抄 pkg/bus 的 Bus/Docs~/lookdev/scene_acts.py 的 erosion_field
（= Lanbai/Cabin 的默认形式 _ErodeForm 0，同一组系数；噪声用 Blender 的 Noise 代替 shader 的哈希 FBM，统计上一样、图案不同）。
圣经 §6·7b：整个 7b 侵蚀 0.25（922.36 才往 0.65 走），车厢环境 #0F1E30 × 0.3、没有管灯。
坐标：车的本地坐标（Unity x, y, z），由跟车走的空物体 BusFrame 的 Object 坐标给（Blender (x, y, z) = Unity (x, z, y)，标准台的轴）。
常数取自 pkg/bus 的 Bus/Source/bus_spec.py。"""
import bpy

FLOOR_Y, CEIL_Y, Z_REAR, Z_FRONT = 0.62, 2.62, -3.65, 3.50
SKY_C, SKY_HALF = (0.55, 2.62, 2.80), 0.30
EYE = (0.55, 1.70, 2.05)
FADE_7B = 0.25


def _m(nt, op, a, b=None):
    n = nt.nodes.new('ShaderNodeMath')
    n.operation = op
    for k, v in enumerate((a, b)):
        if v is None:
            continue
        if isinstance(v, (int, float)):
            n.inputs[k].default_value = v
        else:
            nt.links.new(v, n.inputs[k])
    return n.outputs[0]


def erosion_field(nt, frame, fade, resist=0.0):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    tc.object = frame
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(tc.outputs['Object'], sep.inputs[0])
    x, zu, yu = sep.outputs[0], sep.outputs[1], sep.outputs[2]
    hN = _m(nt, 'MINIMUM', _m(nt, 'MAXIMUM', _m(nt, 'DIVIDE', _m(nt, 'SUBTRACT', yu, FLOOR_Y), CEIL_Y - FLOOR_Y), 0.0), 1.0)
    fN = _m(nt, 'MINIMUM', _m(nt, 'MAXIMUM', _m(nt, 'DIVIDE', _m(nt, 'SUBTRACT', zu, Z_REAR), Z_FRONT - Z_REAR), 0.0), 1.0)
    sx, sy, sz = SKY_C
    qx = _m(nt, 'MAXIMUM', _m(nt, 'SUBTRACT', _m(nt, 'ABSOLUTE', _m(nt, 'SUBTRACT', x, sx)), SKY_HALF), 0.0)
    qz = _m(nt, 'MAXIMUM', _m(nt, 'SUBTRACT', _m(nt, 'ABSOLUTE', _m(nt, 'SUBTRACT', zu, sz)), SKY_HALF), 0.0)
    dy = _m(nt, 'SUBTRACT', yu, sy)
    d = _m(nt, 'SQRT', _m(nt, 'ADD', _m(nt, 'ADD', _m(nt, 'MULTIPLY', qx, qx), _m(nt, 'MULTIPLY', qz, qz)), _m(nt, 'MULTIPLY', dy, dy)))
    e = _m(nt, 'EXPONENT', _m(nt, 'DIVIDE', d, -0.8))
    tau = _m(nt, 'SUBTRACT', fade, _m(nt, 'MULTIPLY', _m(nt, 'SUBTRACT', 1.0, hN), 0.45))
    tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', _m(nt, 'SUBTRACT', 1.0, fN), 0.25))
    tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', _m(nt, 'SUBTRACT', 1.0, e), 0.35))
    tau = _m(nt, 'SUBTRACT', tau, resist)
    ex, ey, ez = EYE
    ds = _m(nt, 'SQRT', _m(nt, 'ADD', _m(nt, 'ADD', _m(nt, 'POWER', _m(nt, 'SUBTRACT', x, ex), 2.0),
                                              _m(nt, 'POWER', _m(nt, 'SUBTRACT', yu, ey - 0.45), 2.0)), _m(nt, 'POWER', _m(nt, 'SUBTRACT', zu, ez), 2.0)))
    tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', _m(nt, 'LESS_THAN', ds, 0.9), 10.0))      # 座位球（到 0.97）
    low = _m(nt, 'LESS_THAN', yu, FLOOR_Y + 0.08)
    tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', low, 10.0))                                  # 地板（到 0.65）
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.0 / 0.55
    nz.inputs['Detail'].default_value = 3.0
    nt.links.new(tc.outputs['Object'], nz.inputs['Vector'])
    nu = _m(nt, 'MINIMUM', _m(nt, 'MAXIMUM', _m(nt, 'DIVIDE', _m(nt, 'SUBTRACT', nz.outputs['Fac'], 0.30), 0.40), 0.0), 1.0)
    nr = _m(nt, 'ADD', -0.20, _m(nt, 'MULTIPLY', nu, 0.45))
    return _m(nt, 'SUBTRACT', nr, tau)


def cabin_material(name, albedo_lin, ambient_lin, frame, fade=FADE_7B):
    """Lanbai/Cabin 的 7b 项：反照率 × 车厢环境（自发光，不吃宫殿的光），侵蚀边 3 cm 发环境 × 1.5，侵蚀掉的地方透明。"""
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    nt = m.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    out = nt.nodes.new('ShaderNodeOutputMaterial')
    em = nt.nodes.new('ShaderNodeEmission')
    em.inputs['Color'].default_value = (*[a * b for a, b in zip(albedo_lin, ambient_lin)], 1)
    s_ = erosion_field(nt, frame, fade)
    rim = nt.nodes.new('ShaderNodeEmission')
    rim.inputs['Color'].default_value = (*[1.5 * v for v in ambient_lin], 1)
    rw = _m(nt, 'MAXIMUM', _m(nt, 'SUBTRACT', 1.0, _m(nt, 'DIVIDE', s_, 0.02)), 0.0)
    isrim = _m(nt, 'MULTIPLY', _m(nt, 'MULTIPLY', rw, rw), 0.8)
    mr = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(isrim, mr.inputs[0])
    nt.links.new(em.outputs[0], mr.inputs[1])
    nt.links.new(rim.outputs[0], mr.inputs[2])
    keep = _m(nt, 'GREATER_THAN', s_, 0.0)
    tr = nt.nodes.new('ShaderNodeBsdfTransparent')
    mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(keep, mx.inputs[0])
    nt.links.new(tr.outputs[0], mx.inputs[1])
    nt.links.new(mr.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    return m
