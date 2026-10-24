# -*- coding: utf-8 -*-
"""D-36 #3 材质：零件的“三十年的旧”，先在 Blender 里用程序节点调（快），对着照片调好以后烘成贴图给 Unity
（parts/texbake.py：法线、反照率、遮罩 R 金属 G 光滑 B 磨损 A AO）。

每个函数把 build_bus 的底色材质（MAT_TABLE）换成一份带细节的拷贝，返回新材质。数值全按圣经 §4.2：
  乙烯  #5A2126 / 0.45；坐亮处 #6A3434 / 0.62–0.70；靠窗晒褪 #7A4A48 / 0.40；接缝开裂 #8A6A60 / 0.20；细皮纹 0.35
  铬    #CFD1D3 / 0.85，坑点处 0.7
  座椅框 #3C3E3D / 0.35，磨处 0.5
节点里的“位置”一律是物体空间（零件自己的坐标），所以同一个零件放在车里哪里都长一样的旧；按座位变化的部分
（每座磨损遮罩）在烘焙时加。
"""
import os

import bpy

import build_bus as BB

HERE = os.path.dirname(os.path.abspath(__file__))
TEX = os.path.normpath(os.path.join(HERE, '..', '..', 'Textures'))


def lin(h):
    return BB.srgb2lin(h)


class N:
    """tiny node-graph helper."""

    def edges(self, radius=0.004):
        """convex-edge mask that does not depend on mesh density: the Bevel node's rounded normal vs the true one."""
        bv = self.new('ShaderNodeBevel', samples=8)
        bv.inputs['Radius'].default_value = radius
        geo = self.new('ShaderNodeNewGeometry')
        dp = self.new('ShaderNodeVectorMath', operation='DOT_PRODUCT')
        self.nt.links.new(bv.outputs['Normal'], dp.inputs[0])
        self.nt.links.new(geo.outputs['Normal'], dp.inputs[1])
        return self.ramp(self.math('SUBTRACT', 1.0, dp.outputs['Value']), 0.02, 0.12)

    def __init__(self, m):
        self.m = m
        self.nt = m.node_tree
        self.x = -1600

    def new(self, kind, **inputs):
        n = self.nt.nodes.new(kind)
        n.location = (self.x, 0)
        self.x += 40
        for k, v in inputs.items():
            if k in n.inputs:
                self.link_or_set(n.inputs[k], v)
            else:
                setattr(n, k, v)
        return n

    def link_or_set(self, sock, v):
        if hasattr(v, 'is_output') or (hasattr(v, 'links') and hasattr(v, 'node')):
            self.nt.links.new(v, sock)
        else:
            sock.default_value = v

    def math(self, op, a, b=0.0, clamp=False):
        n = self.new('ShaderNodeMath', operation=op, use_clamp=clamp)
        self.link_or_set(n.inputs[0], a)
        self.link_or_set(n.inputs[1], b)
        return n.outputs[0]

    def mix(self, fac, a, b):
        n = self.new('ShaderNodeMix', data_type='RGBA')
        fac_s = [s for s in n.inputs if s.name == 'Factor' and s.enabled][0]
        a_s = [s for s in n.inputs if s.name == 'A' and s.type == 'RGBA'][0]
        b_s = [s for s in n.inputs if s.name == 'B' and s.type == 'RGBA'][0]
        self.link_or_set(fac_s, fac)
        self.link_or_set(a_s, a)
        self.link_or_set(b_s, b)
        return [s for s in n.outputs if s.name == 'Result' and s.type == 'RGBA'][0]

    def ramp(self, v, lo, hi):
        """smoothstep-ish 0..1 of v between lo and hi."""
        n = self.new('ShaderNodeMapRange', interpolation_type='SMOOTHSTEP')
        self.link_or_set(n.inputs['Value'], v)
        n.inputs['From Min'].default_value = lo
        n.inputs['From Max'].default_value = hi
        return n.outputs['Result']

    def noise(self, vec, scale, detail=4.0, rough=0.55, distort=0.0, w=None):
        n = self.new('ShaderNodeTexNoise', noise_dimensions='3D' if w is None else '4D')
        self.link_or_set(n.inputs['Vector'], vec)
        n.inputs['Scale'].default_value = scale
        n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough
        n.inputs['Distortion'].default_value = distort
        if w is not None:
            n.inputs['W'].default_value = w
        return n

    def obj(self):
        return self.new('ShaderNodeTexCoord').outputs['Object']


def _fresh(base_name, new_name):
    src = BB.mat(base_name)
    m = src.copy()
    m.name = new_name
    nt = m.node_tree
    bs = nt.nodes.get('Principled BSDF')
    return m, nt, bs


def _grain(g, scale_m, strength):
    """the scanned leather grain (box projected, object space) -> a Normal Map node output."""
    tc = g.obj()
    mp = g.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / scale_m, 1 / scale_m, 1 / scale_m)
    g.nt.links.new(tc, mp.inputs['Vector'])
    tx = g.new('ShaderNodeTexImage', projection='BOX', projection_blend=0.3)
    tx.image = bpy.data.images.load(os.path.join(TEX, 'Cabin_SeatLeather_N_0.30m.jpg'), check_existing=True)
    tx.image.colorspace_settings.name = 'Non-Color'
    g.nt.links.new(mp.outputs['Vector'], tx.inputs['Vector'])
    nm = g.new('ShaderNodeNormalMap')
    nm.inputs['Strength'].default_value = strength
    g.nt.links.new(tx.outputs['Color'], nm.inputs['Color'])
    return nm.outputs['Normal']


def vinyl(worn=1.0, sun=0.0, name='M_Bus_Vinyl_Detail'):
    """ox-blood vinyl, thirty years: grain + puckering wrinkles at the seams and edges (pointiness) + a slack sag
    crease field, polished where people sit / hold (object-space height bands), dust in the cavities (AO)."""
    m, nt, bs = _fresh('Vinyl', name)
    g = N(m)
    P = g.obj()
    geo = g.new('ShaderNodeNewGeometry')
    # edge / seam closeness: convex edges from the Bevel trick (density-independent), cavities from pointiness
    edge = g.edges(0.012)
    cav = g.ramp(geo.outputs['Pointiness'], 0.48, 0.42)
    ao = g.new('ShaderNodeAmbientOcclusion', samples=8, only_local=True)
    ao.inputs['Distance'].default_value = 0.03
    # wrinkles: stretched noise (long along the seam), stronger near edges; a broad low-frequency slack field
    wr = g.noise(P, 38.0, detail=3.0, rough=0.6, distort=0.6)
    slack = g.noise(P, 6.0, detail=2.0, rough=0.5)
    wr_h = g.math('MULTIPLY', wr.outputs['Fac'], g.math('ADD', g.math('MULTIPLY', edge, 0.8), 0.12))
    h = g.math('ADD', wr_h, g.math('MULTIPLY', slack.outputs['Fac'], 0.35))
    bump = g.new('ShaderNodeBump', invert=False)
    bump.inputs['Strength'].default_value = 1.0
    bump.inputs['Distance'].default_value = 0.004
    nt.links.new(h, bump.inputs['Height'])
    nt.links.new(_grain(g, 0.30, 0.35), bump.inputs['Normal'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    # polish (wear): convex edges + the front roll of the cushion + random hand patches
    hand = g.noise(P, 3.0, detail=2.0)
    wear = g.math('MAXIMUM', g.math('MULTIPLY', edge, 0.85),
                  g.math('MULTIPLY', g.ramp(hand.outputs['Fac'], 0.55, 0.72), 0.6))
    wear = g.math('MULTIPLY', wear, worn, clamp=True)
    base = g.mix(wear, (*lin('#5A2126'), 1), (*lin('#6A3434'), 1))
    # mottling: vinyl is never one flat colour (dye lots, body oil, light-fading patches)
    mot = g.noise(P, 9.0, detail=5.0, rough=0.6)
    base = g.mix(g.math('MULTIPLY', g.ramp(mot.outputs['Fac'], 0.35, 0.75), 0.18), base, (*lin('#4A1B20'), 1))
    # dust in the cavities / along the piping
    dust = g.math('MAXIMUM', g.math('MULTIPLY', cav, 0.7), g.math('MULTIPLY', g.math('SUBTRACT', 1.0, ao.outputs['AO']), 0.9))
    base = g.mix(g.math('MULTIPLY', dust, 0.55, clamp=True), base, (*lin('#5B524A'), 1))
    nt.links.new(base, bs.inputs['Base Color'])
    rough = g.math('SUBTRACT', 0.55, g.math('MULTIPLY', wear, 0.22))                  # 0.45 -> ~0.67 smoothness
    rough = g.math('ADD', rough, g.math('MULTIPLY', g.math('SUBTRACT', mot.outputs['Fac'], 0.5), 0.10))
    rough = g.math('ADD', rough, g.math('MULTIPLY', dust, 0.25), clamp=True)
    nt.links.new(rough, bs.inputs['Roughness'])
    bs.inputs['Specular IOR Level'].default_value = 0.5
    return m


def chrome(name='M_Bus_Chrome_Detail'):
    """chromed steel tube: pitting (tiny dark dots, rougher), hand smudges (cloudy, rougher), a little pitting rust."""
    m, nt, bs = _fresh('Chrome', name)
    g = N(m)
    P = g.obj()
    pit = g.new('ShaderNodeTexVoronoi', feature='F1')
    nt.links.new(P, pit.inputs['Vector'])
    pit.inputs['Scale'].default_value = 900.0
    pits = g.ramp(pit.outputs['Distance'], 0.10, 0.02)            # small round dots
    pitmask = g.ramp(g.noise(P, 25.0, detail=3).outputs['Fac'], 0.55, 0.70)
    pits = g.math('MULTIPLY', pits, pitmask)
    smudge = g.ramp(g.noise(P, 18.0, detail=6, rough=0.7, distort=1.5).outputs['Fac'], 0.45, 0.70)
    base = g.mix(g.math('MULTIPLY', pits, 0.9), (*lin('#CFD1D3'), 1), (*lin('#5A4A3C'), 1))
    nt.links.new(base, bs.inputs['Base Color'])
    rough = g.math('ADD', 0.12, g.math('MULTIPLY', smudge, 0.16))
    rough = g.math('ADD', rough, g.math('MULTIPLY', pits, 0.5), clamp=True)
    nt.links.new(rough, bs.inputs['Roughness'])
    bump = g.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.4
    bump.inputs['Distance'].default_value = 0.0003
    nt.links.new(g.math('SUBTRACT', 1.0, pits), bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    return m


def painted_steel(hexc='#3C3E3D', name='M_Bus_SeatFrame_Detail', primer='#7A6E5A', rust='#5E3B22'):
    """black-painted steel: orange-peel, chips on convex edges showing primer then rust, scuffs low down."""
    m, nt, bs = _fresh('SeatFrame', name)
    g = N(m)
    P = g.obj()
    edge = g.edges(0.003)
    chipn = g.noise(P, 60.0, detail=6, rough=0.7)
    chip = g.math('MULTIPLY', edge, g.ramp(chipn.outputs['Fac'], 0.56, 0.64))
    rustn = g.ramp(g.noise(P, 35.0, detail=4).outputs['Fac'], 0.5, 0.7)
    base = g.mix(chip, (*lin(hexc), 1), g.mix(rustn, (*lin(primer), 1), (*lin(rust), 1)))
    nt.links.new(base, bs.inputs['Base Color'])
    peel = g.noise(P, 300.0, detail=2)
    bump = g.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.12
    bump.inputs['Distance'].default_value = 0.0004
    nt.links.new(g.math('ADD', peel.outputs['Fac'], g.math('MULTIPLY', chip, -2.0)), bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    rough = g.math('ADD', 0.62, g.math('MULTIPLY', chip, 0.25), clamp=True)
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', edge, 0.15))
    nt.links.new(rough, bs.inputs['Roughness'])
    return m


def apply_details(objs):
    """swap the flat MAT_TABLE materials on these objects for the detailed ones (by base material name)."""
    table = {}
    for o in objs:
        if o.type != 'MESH':
            continue
        for i, ms in enumerate(o.data.materials):
            if ms is None:
                continue
            key = ms.name.replace('M_Bus_', '').split('.')[0]
            if key not in table:
                table[key] = {'Vinyl': vinyl, 'Chrome': chrome, 'SeatFrame': painted_steel}.get(key, lambda: None)()
            if table[key] is not None:
                o.data.materials[i] = table[key]
    return table
