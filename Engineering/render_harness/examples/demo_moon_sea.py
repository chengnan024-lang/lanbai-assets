# -*- coding: utf-8 -*-
"""示例场景（也是标准台的自检）：月下云海的极简版。
  ~/bpy/bin/python lbh_render.py --scene examples/demo_moon_sea.py --cam hero --grade S3 --act 03 --t 140 --out /tmp/lbh_demo
天：世界节点做一个从地平线到天顶的渐变（线性值）；云海：y = −40 的大平面（月白漫反射）；月：平行光 E = 1（圣经 §1.5 的
照度基准，Inspector = E）+ 一个自发光的月盘；远处一个比 bloom 阈值亮的“灯点”验证 bloom。"""
import math

import bpy


def build(ctx):
    S = ctx['lbh_scene']
    w = bpy.context.scene.world
    nt = w.node_tree
    bg = nt.nodes['Background']
    tc = nt.nodes.new('ShaderNodeTexCoord')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    ramp = nt.nodes.new('ShaderNodeValToRGB')
    nt.links.new(tc.outputs['Generated'], sep.inputs[0])
    nt.links.new(sep.outputs['Z'], ramp.inputs['Fac'])
    ramp.color_ramp.elements[0].position = 0.5
    ramp.color_ramp.elements[0].color = (*S.hex_lin('#111B30'), 1)    # horizon (palette 03)
    ramp.color_ramp.elements[1].position = 0.85
    ramp.color_ramp.elements[1].color = (*S.hex_lin('#08101F'), 1)    # zenith
    nt.links.new(ramp.outputs['Color'], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = 0.35
    # cloud sea plane
    m = S.mat_principled('CloudSea', '#AEBFD2', roughness=1.0)
    S.mesh_object('CloudSea', [(-6000, -40, -6000), (6000, -40, -6000), (6000, -40, 6000), (-6000, -40, 6000)], [(0, 1, 2, 3)], m)
    # moon: Unity directional light E = 1 (bible 1.5 base; Inspector = E), az -12 el +8
    az, el = math.radians(-12), math.radians(8)
    du = (math.cos(el) * math.sin(az), math.sin(el), math.cos(el) * math.cos(az))
    S.unity_directional('Moon', 1.0, '#D6E4FF', du)
    d = S.U2B(du)
    # moon disc (emissive), 0.5 deg at 4 km
    r = 4000 * math.tan(math.radians(0.26))
    c = d * 4000
    cx, cy, cz = c.x, c.z, c.y   # back to unity order for mesh_object
    me = S.mat_emission('MoonDisc', S.hex_lin('#F2F6FF'), 6.0)
    S.mesh_object('MoonDisc', [(cx - r, cy - r, cz), (cx + r, cy - r, cz), (cx + r, cy + r, cz), (cx - r, cy + r, cz)], [(0, 1, 2, 3)], me)
    # a sodium point far below (bloom check)
    ml = S.mat_emission('Lamp', S.hex_lin('#E8A050'), 40.0)
    S.mesh_object('Lamp', [(18, -39.9, 300), (22, -39.9, 300), (22, -39.9, 304), (18, -39.9, 304)], [(0, 3, 2, 1)], ml)
    return dict(what='demo: moon over a flat cloud sea')
