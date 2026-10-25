# -*- coding: utf-8 -*-
"""D-36 #3 材质：零件的“三十年的旧”，先在 Blender 里用程序节点调（快），对着照片调好以后烘成贴图给 Unity
（parts/texbake.py：法线、反照率、遮罩 R 金属 G 光滑 B 接缝开裂候选 A AO）。

每个函数把 build_bus 的底色材质（MAT_TABLE）换成一份带细节的拷贝，返回新材质。数值全按圣经 §4.2：
  乙烯  #5A2126 / 0.45；坐亮处 #6A3434 / 0.62–0.70；靠窗晒褪 #7A4A48 / 0.40；接缝开裂 #8A6A60 / 0.20；细皮纹 0.35
  铬    #CFD1D3 / 0.85，坑点处 0.7
  座椅框 #3C3E3D / 0.35，磨处 0.5；不生锈（车内、干、手够得到：D-40 #3）
  橡胶  #2B2B2B / 0.28，手摸的顶上 0.35
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


def vinyl(worn=1.0, sun=0.0, name='M_Bus_Vinyl_Detail', base_mat='Vinyl', cols=None):
    """ox-blood vinyl, thirty years (director r4 #2, D-40 #3: wear only from what touches it):
      - polish where people sit / slide / hold: the part's 'Zone' attribute R (seat.py writes it: the two sitting dents,
        the thighs over the front roll and the welt there, the hand grip on the back's top band) -> #6A3434, 0.62-0.70;
      - the window-side top sun-faded: 'Zone' G -> #7A4A48 / 0.40;
      - edges, seams and the welt elsewhere more matte, dust in the cavities and along the piping;
      - grain + puckering wrinkles at the seams + a broad slack field; mottling (dye lots, body oil)."""
    c = dict(base='#5A2126', polish='#6A3434', mottle='#4A1B20', faded='#7A4A48', dust='#5B524A')
    c.update(cols or {})
    m, nt, bs = _fresh(base_mat, name)
    g = N(m)
    P = g.obj()
    geo = g.new('ShaderNodeNewGeometry')
    zone = g.new('ShaderNodeAttribute', attribute_name='Zone', attribute_type='GEOMETRY')
    sep = g.new('ShaderNodeSeparateColor')
    nt.links.new(zone.outputs['Color'], sep.inputs['Color'])
    polish = g.math('MULTIPLY', sep.outputs['Red'], worn, clamp=True)
    faded = g.math('ADD', sep.outputs['Green'], sun, clamp=True)
    edge = g.edges(0.012)
    cav = g.ramp(geo.outputs['Pointiness'], 0.48, 0.42)
    ao = g.new('ShaderNodeAmbientOcclusion', samples=8, only_local=True)
    ao.inputs['Distance'].default_value = 0.03
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
    base = g.mix(polish, (*lin(c['base']), 1), (*lin(c['polish']), 1))
    mot = g.noise(P, 9.0, detail=5.0, rough=0.6)
    base = g.mix(g.math('MULTIPLY', g.ramp(mot.outputs['Fac'], 0.35, 0.75), 0.18), base, (*lin(c['mottle']), 1))
    base = g.mix(g.math('MULTIPLY', faded, 0.9), base, (*lin(c['faded']), 1))
    # dust: cavities / along the piping / the edges nobody rubs (not where it is polished)
    unrub = g.math('SUBTRACT', 1.0, polish)
    dust = g.math('MAXIMUM', g.math('MULTIPLY', cav, 0.7), g.math('MULTIPLY', g.math('SUBTRACT', 1.0, ao.outputs['AO']), 0.9))
    dust = g.math('MAXIMUM', dust, g.math('MULTIPLY', edge, 0.35))
    dust = g.math('MULTIPLY', dust, unrub)
    base = g.mix(g.math('MULTIPLY', dust, 0.55, clamp=True), base, (*lin(c['dust']), 1))
    # open seam cracks (bible §4.2 '接缝开裂（露出底布）#8A6A60 / 0.20, 2-5 per seat'): 'Zone' B says where this seat
    # has one; the split itself is a few short lines along the seam (stretched Voronoi edges) showing the knit backing.
    # 'crack_mask' is baked into the part mask's B channel (every candidate on the bake source); 'crack_show' is set to
    # 0 by texbake for the albedo / roughness bakes, because Unity draws the colour per seat (mask.b x vertex alpha).
    cz = g.ramp(sep.outputs['Blue'], 0.25, 0.65)
    # warp the cell network with noise so it is irregular craquelure, not honeycomb; two scales: fine crazing over
    # the whole patch, and in its core a couple of long open splits
    warp = g.noise(P, 18.0, detail=3, rough=0.6)
    wv = g.new('ShaderNodeVectorMath', operation='MULTIPLY_ADD')
    nt.links.new(warp.outputs['Color'], wv.inputs[0])
    wv.inputs[1].default_value = (0.012, 0.012, 0.012)
    nt.links.new(P, wv.inputs[2])
    cv = g.new('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
    nt.links.new(wv.outputs['Vector'], cv.inputs['Vector'])
    cv.inputs['Scale'].default_value = 110.0
    fine = g.ramp(cv.outputs['Distance'], 0.030, 0.006)
    gate = g.ramp(g.noise(P, 55.0, detail=4).outputs['Fac'], 0.50, 0.62)
    cv2 = g.new('ShaderNodeTexVoronoi', feature='DISTANCE_TO_EDGE')
    nt.links.new(wv.outputs['Vector'], cv2.inputs['Vector'])
    cv2.inputs['Scale'].default_value = 28.0
    split = g.math('MULTIPLY', g.ramp(cv2.outputs['Distance'], 0.030, 0.008), g.ramp(sep.outputs['Blue'], 0.6, 0.9))
    crack = g.math('MULTIPLY', g.math('MAXIMUM', g.math('MULTIPLY', fine, gate), split), cz)
    crack_mask = nt.nodes.new('ShaderNodeMath')
    crack_mask.name = crack_mask.label = 'crack_mask'
    crack_mask.operation = 'MINIMUM'
    nt.links.new(crack, crack_mask.inputs[0])
    crack_mask.inputs[1].default_value = 1.0
    show = nt.nodes.new('ShaderNodeValue')
    show.name = show.label = 'crack_show'
    show.outputs[0].default_value = 1.0
    crack_vis = g.math('MULTIPLY', crack_mask.outputs[0], show.outputs[0])
    base = g.mix(crack_vis, base, (*lin('#8A6A60'), 1))
    nt.links.new(base, bs.inputs['Base Color'])
    nt.links.new(g.math('ADD', h, g.math('MULTIPLY', crack_mask.outputs[0], -0.6)), bump.inputs['Height'])
    rough = g.math('SUBTRACT', 0.55, g.math('MULTIPLY', polish, 0.21))                # 0.45 -> 0.66 smoothness
    rough = g.math('ADD', rough, g.math('MULTIPLY', g.math('SUBTRACT', mot.outputs['Fac'], 0.5), 0.06))
    rough = g.math('ADD', rough, g.math('MULTIPLY', g.math('MULTIPLY', edge, unrub), 0.10))  # unrubbed edges / seams matte
    rough = g.math('ADD', rough, g.math('MULTIPLY', dust, 0.15))
    rough = g.math('ADD', g.math('MULTIPLY', rough, g.math('SUBTRACT', 1.0, faded)), g.math('MULTIPLY', faded, 0.60), clamp=True)
    rough = g.math('ADD', g.math('MULTIPLY', rough, g.math('SUBTRACT', 1.0, crack_vis)), g.math('MULTIPLY', crack_vis, 0.80))
    nt.links.new(rough, bs.inputs['Roughness'])
    bs.inputs['Specular IOR Level'].default_value = 0.5
    return m


def piping():
    """672M: the cream welt (米白嵌线) round cushion and back. Light vinyl shows dirt: grey-brown in the crevice under it,
    rubbed cleaner and a touch glossier where thighs and shoulders go (Zone R), never red."""
    return vinyl(name='M_Bus_Piping_Detail', base_mat='Piping',
                 cols=dict(base='#C8BC9E', polish='#D3C9AF', mottle='#A89A7A', faded='#D8D0BC', dust='#6A6252'))


def sleeve():
    """672M: the black leatherette sleeve on the seat-back top tube. Black vinyl wears glossier and a little greyer where
    the hands go (Zone R: the aisle end, the top); dust settles in the seam and the end gathers."""
    return vinyl(name='M_Bus_Sleeve_Detail', base_mat='Sleeve',
                 cols=dict(base='#2E2E2E', polish='#3A3938', mottle='#282828', faded='#4A4744', dust='#5A5650'))


def rubber(name='M_Bus_Seal_Detail'):
    """moulded black rubber (the seat bumper sleeves, gaskets): #2B2B2B, smoothness ~0.28 with a faint hand sheen on
    the top, a fine moulding stipple, grey dust in the cavities. Albedo stays >= 38 sRGB (director r4 #4)."""
    m, nt, bs = _fresh('Seal', name)
    g = N(m)
    P = g.obj()
    ao = g.new('ShaderNodeAmbientOcclusion', samples=8, only_local=True)
    ao.inputs['Distance'].default_value = 0.02
    dust = g.math('MULTIPLY', g.math('SUBTRACT', 1.0, ao.outputs['AO']), 0.8, clamp=True)
    mot = g.noise(P, 14.0, detail=4.0, rough=0.6)
    base = g.mix(g.math('MULTIPLY', g.ramp(mot.outputs['Fac'], 0.4, 0.7), 0.25), (*lin('#2B2B2B'), 1), (*lin('#303131'), 1))
    base = g.mix(g.math('MULTIPLY', dust, 0.5), base, (*lin('#55524C'), 1))
    nt.links.new(base, bs.inputs['Base Color'])
    geo = g.new('ShaderNodeNewGeometry')
    sep = g.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Normal'], sep.inputs['Vector'])
    top = g.ramp(sep.outputs['Z'], 0.4, 0.95)                         # Blender z = up: the hand rubs the top
    rough = g.math('SUBTRACT', 0.72, g.math('MULTIPLY', top, 0.07))
    rough = g.math('ADD', rough, g.math('MULTIPLY', g.math('SUBTRACT', mot.outputs['Fac'], 0.5), 0.06))
    rough = g.math('ADD', rough, g.math('MULTIPLY', dust, 0.12), clamp=True)
    nt.links.new(rough, bs.inputs['Roughness'])
    st = g.noise(P, 1400.0, detail=1.0)
    bump = g.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.08
    bump.inputs['Distance'].default_value = 0.0002
    nt.links.new(st.outputs['Fac'], bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    bs.inputs['Specular IOR Level'].default_value = 0.5
    return m


def chrome(name='M_Bus_Chrome_Detail'):
    """chromed steel tube: pitting (tiny dark dots of bare steel, rougher), hand smudges (cloudy, rougher)."""
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
    base = g.mix(g.math('MULTIPLY', pits, 0.9), (*lin('#CFD1D3'), 1), (*lin('#3E3F40'), 1))   # dark pitted steel, no rust (D-40 #3)
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


def painted_steel(hexc='#3C3E3D', name='M_Bus_SeatFrame_Detail', primer='#7A6E5A', bare='#4A4B4C'):
    """black-painted steel: orange-peel, chips on convex edges showing primer then dark bare steel. No rust: the seat
    frames are inside, dry and in reach of hands (D-40 #3: rust only where water stands - seams, underbody, arches)."""
    m, nt, bs = _fresh('SeatFrame', name)
    g = N(m)
    P = g.obj()
    edge = g.edges(0.003)
    chipn = g.noise(P, 60.0, detail=6, rough=0.7)
    chip = g.math('MULTIPLY', edge, g.ramp(chipn.outputs['Fac'], 0.56, 0.64))
    baren = g.ramp(g.noise(P, 35.0, detail=4).outputs['Fac'], 0.55, 0.7)
    base = g.mix(chip, (*lin(hexc), 1), g.mix(baren, (*lin(primer), 1), (*lin(bare), 1)))
    # rubbed patches ('Zone' R: the knees of the row behind on a seat's back board): the paint rubbed satin and a
    # little lighter, with fine scratches across
    zone = g.new('ShaderNodeAttribute', attribute_name='Zone', attribute_type='GEOMETRY')
    sepz = g.new('ShaderNodeSeparateColor')
    nt.links.new(zone.outputs['Color'], sepz.inputs['Color'])
    mp = g.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1.0, 1.0, 25.0)
    nt.links.new(P, mp.inputs['Vector'])
    scr = g.ramp(g.noise(mp.outputs['Vector'], 90.0, detail=3, rough=0.6).outputs['Fac'], 0.60, 0.70)
    rub = g.math('MULTIPLY', sepz.outputs['Red'], g.math('ADD', 0.7, g.math('MULTIPLY', scr, 0.6)), clamp=True)
    base = g.mix(g.math('MULTIPLY', rub, 0.8), base, (*lin('#545756'), 1))
    # worn through ('Zone' G: the hand on the aisle top bend of a seat tube, shoes on the legs): ragged islands of bare
    # steel, polished by the hands (metallic, smoother), a thin primer halo round them. Dry and handled: no rust (D-40 #3)
    thr = g.math('SUBTRACT', 1.0, sepz.outputs['Green'])
    wn = g.noise(P, 45.0, detail=6, rough=0.65).outputs['Fac']
    thru = g.ramp(g.math('SUBTRACT', wn, thr), -0.02, 0.06)
    halo = g.math('SUBTRACT', g.ramp(g.math('SUBTRACT', wn, thr), -0.10, -0.02), thru, clamp=True)
    halo = g.math('MULTIPLY', halo, g.ramp(sepz.outputs['Green'], 0.0, 0.05))
    base = g.mix(halo, base, (*lin(primer), 1))
    base = g.mix(thru, base, (*lin('#6A6A66'), 1))
    nt.links.new(base, bs.inputs['Base Color'])
    nt.links.new(g.math('MULTIPLY', thru, 0.85), bs.inputs['Metallic'])
    peel = g.noise(P, 300.0, detail=2)
    bump = g.new('ShaderNodeBump')
    bump.inputs['Strength'].default_value = 0.12
    bump.inputs['Distance'].default_value = 0.0004
    nt.links.new(g.math('ADD', peel.outputs['Fac'], g.math('MULTIPLY', chip, -2.0)), bump.inputs['Height'])
    nt.links.new(bump.outputs['Normal'], bs.inputs['Normal'])
    rough = g.math('ADD', 0.62, g.math('MULTIPLY', chip, 0.25), clamp=True)
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', edge, 0.15))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', rub, 0.20))
    rough = g.math('SUBTRACT', rough, g.math('MULTIPLY', thru, 0.30), clamp=True)
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
                table[key] = {'Vinyl': vinyl, 'Chrome': chrome, 'SeatFrame': painted_steel, 'Seal': rubber, 'Piping': piping, 'Sleeve': sleeve}.get(key, lambda: None)()
            if table[key] is not None:
                o.data.materials[i] = table[key]
    return table
