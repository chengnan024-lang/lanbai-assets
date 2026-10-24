# -*- coding: utf-8 -*-
"""参考渲染用的 Cycles 材质 —— 尽量就是 Lanbai/Palace shader 的数学：
  反照率 / 法线 / 掩码贴图（世界尺度 UV0），光滑度 → Blender 粗糙度 = 1 − s；
  淤泥：朝上的面（N.y > 0.55 开始，0.85 满）× 噪声，覆盖 40–70%，颜色 #5E6259、光滑度 0.10（圣经 §6·7b）；
  珍珠母：高光颜色 = 虹彩 f(N·V)：正面 #E7C9D5 → #C3E3D5 → 掠射 #B9C6EA；
  青铜：掩码 R = 金属（铜绿 / 暗化处为电介质，D-29）。"""
import os

import bpy

TEX = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'Textures'))


def s2l(h):
    h = h.lstrip('#')
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(x / 12.92 if x <= 0.04045 else ((x + 0.055) / 1.055) ** 2.4 for x in c)


class NB:
    def __init__(self, name):
        self.m = bpy.data.materials.get(name) or bpy.data.materials.new(name)
        self.m.use_nodes = True
        self.nt = self.m.node_tree
        for n in list(self.nt.nodes):
            self.nt.nodes.remove(n)
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')

    def n(self, t, **kw):
        node = self.nt.nodes.new(t)
        for k, v in kw.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def tex(self, fname, colour=True, uv='UVMap'):
        p = os.path.join(TEX, fname)
        img = bpy.data.images.get(fname) or bpy.data.images.load(p, check_existing=True)
        img.colorspace_settings.name = 'sRGB' if colour else 'Non-Color'
        t = self.n('ShaderNodeTexImage')
        t.image = img
        t.interpolation = 'Linear'
        uvn = self.n('ShaderNodeUVMap')
        uvn.uv_map = uv
        self.link(uvn.outputs[0], t.inputs[0])
        return t

    def math(self, op, a, b=None, clamp=False):
        m = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]


def silt_mask(b, coverage=0.55):
    geo = b.n('ShaderNodeNewGeometry')
    sep = b.n('ShaderNodeSeparateXYZ')
    b.link(geo.outputs['Normal'], sep.inputs[0])
    up = b.math('MULTIPLY', b.math('SUBTRACT', sep.outputs['Z'], 0.55), 1 / 0.30, clamp=True)
    nz = b.n('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 0.35
    nz.inputs['Detail'].default_value = 6.0
    tc = b.n('ShaderNodeTexCoord')
    b.link(tc.outputs['Object'], nz.inputs['Vector'])
    noisy = b.math('MULTIPLY', b.math('SUBTRACT', nz.outputs['Fac'], 0.5 - (coverage - 0.5) * 0.5), 5.0, clamp=True)
    return b.math('MULTIPLY', up, noisy, clamp=True)


def standard(name, base, normal=None, mask=None, smooth=0.5, metallic=0.0, silt=0.0, nstr=1.0, irid=False, tint=None):
    b = NB(name)
    bs = b.n('ShaderNodeBsdfPrincipled')
    alb = b.tex(base) if base.endswith('.png') else None
    col = alb.outputs['Color'] if alb else None
    if tint is not None and col is not None:
        mix = b.n('ShaderNodeMix', data_type='RGBA', blend_type='MULTIPLY')
        mix.inputs[0].default_value = 1.0
        b.link(col, mix.inputs[6])
        mix.inputs[7].default_value = (*tint, 1)
        col = mix.outputs[2]
    if col is None:
        bs.inputs['Base Color'].default_value = (*s2l(base), 1)
    rough = None
    if mask:
        mk = b.tex(mask, colour=False)
        sepm = b.n('ShaderNodeSeparateColor')
        b.link(mk.outputs['Color'], sepm.inputs[0])
        rough = b.math('SUBTRACT', 1.0, mk.outputs['Alpha'])
        if metallic == 'mask':
            b.link(sepm.outputs['Red'], bs.inputs['Metallic'])
    else:
        bs.inputs['Roughness'].default_value = 1 - smooth
    if metallic != 'mask':
        bs.inputs['Metallic'].default_value = metallic
    if normal:
        nt = b.tex(normal, colour=False)
        nm = b.n('ShaderNodeNormalMap')
        nm.inputs['Strength'].default_value = nstr
        b.link(nt.outputs['Color'], nm.inputs['Color'])
        b.link(nm.outputs[0], bs.inputs['Normal'])
    if silt > 0 and col is not None:
        s = silt_mask(b, silt)
        mix = b.n('ShaderNodeMix', data_type='RGBA')
        b.link(s, mix.inputs[0])
        b.link(col, mix.inputs[6])
        mix.inputs[7].default_value = (*s2l('#5E6259'), 1)
        col = mix.outputs[2]
        if rough is not None:
            rough = b.math('ADD', b.math('MULTIPLY', rough, b.math('SUBTRACT', 1.0, s)), b.math('MULTIPLY', s, 0.90))
        else:
            rough = b.math('ADD', b.math('MULTIPLY', 1 - smooth, b.math('SUBTRACT', 1.0, s)), b.math('MULTIPLY', s, 0.90))
    if col is not None:
        b.link(col, bs.inputs['Base Color'])
    if rough is not None:
        b.link(rough, bs.inputs['Roughness'])
    if irid:
        lw = b.n('ShaderNodeLayerWeight')
        lw.inputs['Blend'].default_value = 0.5
        ramp = b.n('ShaderNodeValToRGB')
        cr = ramp.color_ramp
        cr.elements[0].color = (*s2l('#E7C9D5'), 1)
        cr.elements[1].color = (*s2l('#B9C6EA'), 1)
        e = cr.elements.new(0.5)
        e.color = (*s2l('#C3E3D5'), 1)
        b.link(lw.outputs['Facing'], ramp.inputs[0])
        b.link(ramp.outputs[0], bs.inputs['Specular Tint'])
        bs.inputs['Specular IOR Level'].default_value = 0.9
        bs.inputs['Coat Weight'].default_value = 0.4
        b.link(ramp.outputs[0], bs.inputs['Coat Tint'])
    b.link(bs.outputs[0], b.out.inputs['Surface'])
    return b.m


def emission(name, rgb_lin, strength=1.0):
    b = NB(name)
    e = b.n('ShaderNodeEmission')
    e.inputs['Color'].default_value = (*rgb_lin, 1)
    e.inputs['Strength'].default_value = strength
    b.link(e.outputs[0], b.out.inputs['Surface'])
    b.m.cycles.emission_sampling = 'NONE'
    return b.m


def build_all():
    T = lambda s: 'T_07b_%s.png' % s
    M = {}
    M['Lacquer'] = standard('M_07b_Lacquer', T('Lacquer_Albedo'), T('Lacquer_Normal'), T('Lacquer_Mask'), silt=0.55)
    M['LacquerBlack'] = standard('M_07b_LacquerBlack', '#282426', smooth=0.75, silt=0.4)
    M['LacquerBand'] = standard('M_07b_LacquerBand', T('LacquerBand_Albedo'), None, T('LacquerBand_Mask'), silt=0.3)
    M['Gilt'] = standard('M_07b_Gilt', '#C9A56A', smooth=0.60, metallic=1.0)
    M['Bronze'] = standard('M_07b_Bronze', T('Bronze_Albedo'), T('Bronze_Normal'), T('Bronze_Mask'), metallic='mask')
    M['Verdigris'] = standard('M_07b_Verdigris', '#3E7A68', smooth=0.32)
    M['Stone'] = standard('M_07b_Stone', T('Stone_Albedo'), T('Stone_Normal'), T('Stone_Mask'), silt=0.6)
    M['StoneDark'] = standard('M_07b_StoneDark', T('Stone_Albedo'), T('Stone_Normal'), T('Stone_Mask'), silt=0.4, tint=(0.8, 0.8, 0.8))
    M['FishScale'] = standard('M_07b_FishScale', T('FishScale_Albedo'), T('FishScale_Normal'), T('FishScale_Mask'), silt=0.25, irid=True)
    M['Cowrie'] = standard('M_07b_Cowrie', T('Cowrie_Albedo'), T('Cowrie_Normal'), T('Cowrie_Mask'), silt=0.2, nstr=1.5)
    M['Tile'] = standard('M_07b_Tile', T('Stone_Albedo'), T('Stone_Normal'), None, smooth=0.35, silt=0.7, tint=(0.95, 0.98, 1.0))
    M['Wood'] = standard('M_07b_Wood', '#2C2522', smooth=0.35)
    M['Rock'] = standard('M_07b_Rock', '#33362F', smooth=0.22, silt=0.0)
    M['Weed'] = standard('M_07b_Weed', '#2E3A26', smooth=0.55)
    M['Fish'] = standard('M_07b_Fish', '#8A949A', smooth=0.85)
    M['DoorGlow'] = emission('M_07b_DoorGlow', tuple(3.0 * c for c in s2l('#FFB74D')))
    return M
