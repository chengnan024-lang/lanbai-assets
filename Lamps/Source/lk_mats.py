# -*- coding: utf-8 -*-
"""Blender 材质：`Lanbai/LampKit`、`Lanbai/LampGlow` 两个 Unity shader 的节点移植（同一套数学，见 README §3），
以及参考图要用的路面、草、水田、车厢的简化材质。所有颜色按“取色器里的 sRGB”给，节点里转线性。"""
import math
import os

import bpy
import numpy as np


def hexlin(h):
    h = h.lstrip('#')
    s = np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)]) / 255.0
    return tuple(float(v) for v in np.where(s <= 0.04045, s / 12.92, ((s + 0.055) / 1.055) ** 2.4))


class NB:
    """Tiny node-builder."""

    def __init__(self, name):
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        self.m = m
        self.nt = m.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')

    def N(self, t):
        return self.nt.nodes.new(t)

    def L(self, a, b):
        self.nt.links.new(a, b)

    def _in(self, node, k, x):
        if x is None:
            return
        if isinstance(x, (int, float)):
            node.inputs[k].default_value = x
        elif isinstance(x, tuple):
            node.inputs[k].default_value = x
        else:
            self.L(x, node.inputs[k])

    def math(self, op, a, b=None, c=None):
        n = self.N('ShaderNodeMath'); n.operation = op
        self._in(n, 0, a); self._in(n, 1, b)
        if c is not None:
            self._in(n, 2, c)
        return n.outputs[0]

    def vmath(self, op, a, b=None, scale=None):
        n = self.N('ShaderNodeVectorMath'); n.operation = op
        self._in(n, 0, a); self._in(n, 1, b)
        if scale is not None:
            self._in(n, 'Scale', scale)
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']

    def mixf(self, f, a, b):
        n = self.N('ShaderNodeMix'); n.data_type = 'FLOAT'
        self._in(n, 'Factor', f); self._in(n, 'A', a); self._in(n, 'B', b)
        return n.outputs[0]

    def mixc(self, f, a, b, blend='MIX'):
        n = self.N('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = blend
        self._in(n, 0, f)
        for idx, x in ((6, a), (7, b)):
            if isinstance(x, tuple):
                n.inputs[idx].default_value = x if len(x) == 4 else (*x, 1.0)
            else:
                self.L(x, n.inputs[idx])
        return n.outputs[2]

    def tex(self, path, vec=None, cs='Non-Color', ext='REPEAT', interp='Linear'):
        t = self.N('ShaderNodeTexImage')
        im = bpy.data.images.load(path, check_existing=True)
        im.colorspace_settings.name = cs
        im.alpha_mode = 'CHANNEL_PACKED'
        t.image = im; t.extension = ext; t.interpolation = interp
        if vec is not None:
            self.L(vec, t.inputs[0])
        return t

    def sep(self, col):
        s = self.N('ShaderNodeSeparateColor'); self.L(col, s.inputs[0]); return s.outputs

    def comb(self, x, y, z=0.0):
        c = self.N('ShaderNodeCombineXYZ')
        self._in(c, 0, x); self._in(c, 1, y); self._in(c, 2, z)
        return c.outputs[0]

    def rgb(self, c):
        n = self.N('ShaderNodeRGB'); n.outputs[0].default_value = (*c, 1.0); return n.outputs[0]


# ---------------------------------------------------------------------------------------------- Lanbai/LampKit
KIT = {   # per material: texture set, wet darkening (Lagarde porosity), wet film smoothness (min, max by flow), wet normal x
    'M_Lamps_Concrete': dict(tex='T_Lamps_PoleRoad', wet_dark=0.55, wet_s=(0.35, 0.55)),
    'M_Lamps_ConcreteStop': dict(tex='T_Lamps_PoleStop', wet_dark=0.55, wet_s=(0.35, 0.55)),
    'M_Lamps_ConcreteLong': dict(tex='T_Lamps_PoleLong', wet_dark=0.55, wet_s=(0.35, 0.55)),
    'M_Lamps_Steel': dict(tex='T_Lamps_Steel', wet_dark=0.80, wet_s=(0.55, 0.75)),
    'M_Lamps_ArmSteel': dict(tex='T_Lamps_ArmSteel', wet_dark=0.80, wet_s=(0.55, 0.75)),
    'M_Lamps_Housing': dict(tex='T_Lamps_Housing', wet_dark=0.92, wet_s=(0.70, 0.85)),
    'M_Lamps_Porcelain': dict(tex='T_Lamps_Porcelain', wet_dark=1.0, wet_s=(0.90, 0.93)),
    'M_Lamps_Enamel': dict(tex='T_Lamps_Enamel', wet_dark=1.0, wet_s=(0.88, 0.92)),
    'M_Lamps_Photocell': dict(tex=None, col='#B9BAB4', s=0.4, wet_dark=1.0, wet_s=(0.8, 0.85)),
    'M_Lamps_Bakelite': dict(tex=None, col='#C8C2B0', s=0.5, wet_dark=1.0, wet_s=(0.5, 0.5)),
}


def lampkit(name, texdir, wet, cfg=None):
    """Port of Lanbai/LampKit (README §3):
        w      = wet * lerp(0.6, 1, flow)
        albedo = albedo * lerp(1, wet_dark, w)
        smooth = lerp(smooth_dry, lerp(wet_s.min, wet_s.max, flow), w)
        normal strength x lerp(1, 0.6, w)
    Metallic from the mask (all 0 in this kit), AO multiplies the albedo only in the reference render."""
    cfg = cfg or KIT[name]
    b = NB(name)
    bs = b.N('ShaderNodeBsdfPrincipled')
    bs.inputs['IOR'].default_value = 1.5
    if cfg.get('tex'):
        uv = b.N('ShaderNodeTexCoord').outputs['UV']
        A = b.tex(os.path.join(texdir, cfg['tex'] + '_Albedo.png'), uv, 'sRGB')
        Nn = b.tex(os.path.join(texdir, cfg['tex'] + '_Normal.png'), uv)
        Mk = b.tex(os.path.join(texdir, cfg['tex'] + '_Mask.png'), uv)
        r, g, bl = b.sep(Mk.outputs['Color'])
        flow = Mk.outputs['Alpha']
        w = b.math('MULTIPLY', wet, b.mixf(flow, 0.6, 1.0))
        alb = b.mixc(1.0, A.outputs['Color'], b.comb(b.mixf(w, 1.0, cfg['wet_dark']), b.mixf(w, 1.0, cfg['wet_dark']), b.mixf(w, 1.0, cfg['wet_dark'])), 'MULTIPLY')
        alb = b.mixc(1.0, alb, b.comb(bl, bl, bl), 'MULTIPLY')
        sm = b.mixf(w, g, b.mixf(flow, cfg['wet_s'][0], cfg['wet_s'][1]))
        nm = b.N('ShaderNodeNormalMap'); b.L(Nn.outputs['Color'], nm.inputs['Color'])
        b._in(nm, 'Strength', b.mixf(w, 1.0, 0.6))
        b.L(nm.outputs[0], bs.inputs['Normal'])
        b.L(alb, bs.inputs['Base Color'])
        b.L(r, bs.inputs['Metallic'])
        b.L(b.math('SUBTRACT', 1.0, sm), bs.inputs['Roughness'])
    else:
        c = hexlin(cfg['col'])
        k = 1.0 + (cfg['wet_dark'] - 1.0) * wet
        bs.inputs['Base Color'].default_value = (*(v * k for v in c), 1)
        bs.inputs['Roughness'].default_value = 1 - (cfg['s'] + (cfg['wet_s'][1] - cfg['s']) * wet)
    b.L(bs.outputs[0], b.out.inputs[0])
    return b.m


# ---------------------------------------------------------------------------------------------- Lanbai/LampGlow (refractor)
def lampglow(name, texdir, arc_a, arc_b, glow_fill, core_fill, wet, edge=0.45, core_sigma=0.035, dust_tint='#C9A878'):
    """Port of Lanbai/LampGlow: the drop refractor seen lit from the inside.
        d      = distance between the view ray through this surface point and the arc segment (object space)
        glow   = _Glow * (edge + (1 - edge) * exp(-(d / sigma)^2)) * prism(v)  +  _Core * exp(-(d / (0.35 sigma))^2)
        glow  *= lerp(1, dust_tint, dust)          (yellow-brown film, thicker toward the bottom)
        + a thin wet glass reflection: Fresnel(1.5) glossy, roughness 0.05 (only what the world gives it)
    arc_a, arc_b: the arc tube's end points in WORLD space (the reference scene is static per frame)."""
    b = NB(name)
    geo = b.N('ShaderNodeNewGeometry')
    P = geo.outputs['Position']
    I = geo.outputs['Incoming']                       # from the surface toward the camera
    A = tuple(arc_a); S = tuple(np.asarray(arc_b) - np.asarray(arc_a))
    SS = float(np.dot(S, S))
    # closest distance between the line P + t*I and the segment A + s*S
    L0 = b.vmath('SUBTRACT', A, P)
    IoS = b.vmath('DOT_PRODUCT', I, S)
    IoL = b.vmath('DOT_PRODUCT', I, L0)
    SoL = b.vmath('DOT_PRODUCT', S, L0)
    den = b.math('MAXIMUM', b.math('SUBTRACT', SS, b.math('MULTIPLY', IoS, IoS)), 1e-9)
    s = b.math('DIVIDE', b.math('SUBTRACT', b.math('MULTIPLY', IoL, IoS), SoL), den)
    s = b.math('MINIMUM', b.math('MAXIMUM', s, 0.0), 1.0)
    Q = b.vmath('ADD', L0, b.vmath('SCALE', S, None, s))          # A + sS - P
    perp = b.vmath('SUBTRACT', Q, b.vmath('SCALE', I, None, b.vmath('DOT_PRODUCT', Q, I)))
    d = b.vmath('LENGTH', perp)
    g1 = b.math('EXPONENT', b.math('MULTIPLY', -1.0, b.math('POWER', b.math('DIVIDE', d, core_sigma), 2.0)))
    g2 = b.math('EXPONENT', b.math('MULTIPLY', -1.0, b.math('POWER', b.math('DIVIDE', d, core_sigma * 0.35), 2.0)))
    # prism rings: brightness ripple along v (rim -> bottom), 22 rings
    uv = b.N('ShaderNodeTexCoord').outputs['UV']
    sx = b.N('ShaderNodeSeparateXYZ'); b.L(uv, sx.inputs[0])
    vv = sx.outputs[1]
    ring = b.math('ADD', 0.88, b.math('MULTIPLY', 0.12, b.math('SINE', b.math('MULTIPLY', vv, 2 * math.pi * 22))))
    base = b.math('MULTIPLY', b.math('ADD', edge, b.math('MULTIPLY', 1 - edge, g1)), ring)
    Dt = b.tex(os.path.join(texdir, 'T_Lamps_RefractorDirt.png'), uv)
    dr, dg, dbl = b.sep(Dt.outputs['Color'])
    tint = b.mixc(b.math('MULTIPLY', dr, 0.55), (1, 1, 1, 1), (*hexlin(dust_tint), 1))
    col = b.mixc(1.0, b.mixc(1.0, b.comb(b.math('MULTIPLY', base, glow_fill[0]), b.math('MULTIPLY', base, glow_fill[1]), b.math('MULTIPLY', base, glow_fill[2])),
                                b.comb(b.math('MULTIPLY', g2, core_fill[0]), b.math('MULTIPLY', g2, core_fill[1]), b.math('MULTIPLY', g2, core_fill[2])), 'ADD'),
                 tint, 'MULTIPLY')
    col = b.mixc(b.math('MULTIPLY', dbl, 0.8), col, (0.02, 0.012, 0.005, 1))      # insect specks
    em = b.N('ShaderNodeEmission'); b.L(col, em.inputs['Color']); em.inputs['Strength'].default_value = 1.0
    gl = b.N('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.06
    fr = b.N('ShaderNodeFresnel'); fr.inputs['IOR'].default_value = 1.5
    add = b.N('ShaderNodeAddShader')
    mixs = b.N('ShaderNodeMixShader'); b.L(fr.outputs[0], mixs.inputs[0])
    tr = b.N('ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (0, 0, 0, 1)
    b.L(tr.outputs[0], mixs.inputs[1]); b.L(gl.outputs[0], mixs.inputs[2])
    # opaque in Unity; here: black body + emission + the Fresnel glossy
    b.L(em.outputs[0], add.inputs[0]); b.L(mixs.outputs[0], add.inputs[1])
    b.L(add.outputs[0], b.out.inputs[0])
    return b.m


def emissive(name, col_lin, strength=1.0):
    b = NB(name)
    em = b.N('ShaderNodeEmission'); em.inputs['Color'].default_value = (*col_lin, 1); em.inputs['Strength'].default_value = strength
    b.L(em.outputs[0], b.out.inputs[0])
    return b.m


def tube_glow(name, fill_lin, end_dark='#8C9396', end_len=0.03, tube_len=1.2):
    """T8 tube: uniform emission with the two blackened ends (bible §5.4). UV v 0..1 along the tube."""
    b = NB(name)
    uv = b.N('ShaderNodeTexCoord').outputs['UV']
    sx = b.N('ShaderNodeSeparateXYZ'); b.L(uv, sx.inputs[0])
    v = sx.outputs[1]
    e = end_len / tube_len
    endk = b.math('MAXIMUM', b.math('LESS_THAN', v, e), b.math('GREATER_THAN', v, 1 - e))
    em = b.N('ShaderNodeEmission'); em.inputs['Color'].default_value = (*fill_lin, 1)
    b.L(b.math('SUBTRACT', 1.0, b.math('MULTIPLY', endk, 0.97)), em.inputs['Strength'])
    dif = b.N('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (*hexlin(end_dark), 1)
    add = b.N('ShaderNodeAddShader'); b.L(em.outputs[0], add.inputs[0]); b.L(dif.outputs[0], add.inputs[1])
    b.L(add.outputs[0], b.out.inputs[0])
    return b.m


def simple(name, col_hex, rough, metal=0.0, spec=0.5):
    b = NB(name)
    bs = b.N('ShaderNodeBsdfPrincipled')
    bs.inputs['Base Color'].default_value = (*hexlin(col_hex), 1)
    bs.inputs['Roughness'].default_value = rough
    bs.inputs['Metallic'].default_value = metal
    bs.inputs['Specular IOR Level'].default_value = spec
    b.L(bs.outputs[0], b.out.inputs[0])
    return b.m


def glass(name, refl=1.0, tint=(1, 1, 1)):
    """Thin pane: straight-through transparency + Fresnel glossy (a single refracting interface would bend the
    whole outside world)."""
    b = NB(name)
    tr = b.N('ShaderNodeBsdfTransparent'); tr.inputs[0].default_value = (*tint, 1)
    gl = b.N('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.02
    lw = b.N('ShaderNodeLayerWeight'); lw.inputs['Blend'].default_value = 0.08
    fr = b.math('MULTIPLY', lw.outputs['Fresnel'], refl)
    mx = b.N('ShaderNodeMixShader'); b.L(fr, mx.inputs[0]); b.L(tr.outputs[0], mx.inputs[1]); b.L(gl.outputs[0], mx.inputs[2])
    b.L(mx.outputs[0], b.out.inputs[0])
    return b.m


def depth_material():
    b = NB('LK_Depth')
    cd = b.N('ShaderNodeCameraData')
    em = b.N('ShaderNodeEmission'); em.inputs['Color'].default_value = (1, 1, 1, 1)
    b.L(cd.outputs['View Distance'], em.inputs['Strength'])
    b.L(em.outputs[0], b.out.inputs[0])
    return b.m


# ---------------------------------------------------------------------------------------------- road (Lanbai/WetSurface, simplified)
def wet_road(name, groundtex, road_mask_png, s_offset, wet=1.0, x_of_v=(6.6, 12.0), tile=2.0, puddle_r0=0.30):
    """Simplified port of Rain's Lanbai/WetSurface for the R_Road modules (Road_WetMask, README_Rain §2.2, §4):
    film: albedo x lerp(1, 0.5, wet), smoothness lerp(0.20, 0.74 + 0.10 G, wet), normal x0.6;
    puddles (R): albedo x0.25, smoothness 0.97, Fresnel weight R0 0.30 (the kit's art value);
    paint (A): worn white #E0E0DC-ish (linear 0.45 dry / 0.70 smooth wet). Road coordinate s = y + s_offset.
    wet = 0 (act 11): dry asphalt, smoothness 0.20, no puddle mirror (the puddles become faint dark stains)."""
    b = NB(name)
    geo = b.N('ShaderNodeNewGeometry')
    sx = b.N('ShaderNodeSeparateXYZ'); b.L(geo.outputs['Position'], sx.inputs[0])
    x, y = sx.outputs[0], sx.outputs[1]
    s = b.math('ADD', y, s_offset)
    uvA = b.comb(b.math('DIVIDE', x, tile), b.math('DIVIDE', s, tile))
    alb = b.tex(os.path.join(groundtex, 'Pv_Asphalt_Albedo.png'), uvA, 'sRGB')
    nrm = b.tex(os.path.join(groundtex, 'Pv_Asphalt_Normal.png'), uvA)
    uvM = b.comb(b.math('DIVIDE', b.math('ADD', s, 21.0), 60.0), b.math('DIVIDE', b.math('SUBTRACT', x_of_v[0], x), x_of_v[1]))
    M = b.tex(road_mask_png, uvM, ext='EXTEND')
    R, G, B = b.sep(M.outputs['Color'])
    A = M.outputs['Alpha']
    puddle = b.math('MULTIPLY', b.math('GREATER_THAN', R, 0.05), wet)
    film = b.N('ShaderNodeBsdfPrincipled'); film.inputs['IOR'].default_value = 1.5
    wk = b.mixf(wet, 1.0, 0.5)
    a1 = b.mixc(1.0, alb.outputs['Color'], b.comb(wk, wk, wk), 'MULTIPLY')
    paint = b.mixc(A, a1, (0.45, 0.45, 0.44, 1))
    b.L(paint, film.inputs['Base Color'])
    sm = b.mixf(wet, 0.20, b.math('ADD', 0.74, b.math('MULTIPLY', G, 0.10)))
    sm = b.mixf(A, sm, b.mixf(wet, 0.35, 0.70))
    b.L(b.math('SUBTRACT', 1.0, sm), film.inputs['Roughness'])
    nm = b.N('ShaderNodeNormalMap'); b.L(nrm.outputs['Color'], nm.inputs['Color'])
    b._in(nm, 'Strength', b.mixf(wet, 1.0, 0.6))
    b.L(nm.outputs[0], film.inputs['Normal'])
    # puddle: dark diffuse + mirror with Schlick R0 0.30
    cosv = b.math('MAXIMUM', b.vmath('DOT_PRODUCT', geo.outputs['Normal'], geo.outputs['Incoming']), 0.0)
    Rth = b.math('ADD', puddle_r0, b.math('MULTIPLY', 1 - puddle_r0, b.math('POWER', b.math('SUBTRACT', 1.0, cosv), 5.0)))
    gl = b.N('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = 0.035
    a2 = b.mixc(1.0, alb.outputs['Color'], (0.25, 0.25, 0.25, 1), 'MULTIPLY')
    dif = b.N('ShaderNodeBsdfDiffuse'); b.L(a2, dif.inputs['Color'])
    pm = b.N('ShaderNodeMixShader'); b.L(Rth, pm.inputs[0]); b.L(dif.outputs[0], pm.inputs[1]); b.L(gl.outputs[0], pm.inputs[2])
    fin = b.N('ShaderNodeMixShader'); b.L(puddle, fin.inputs[0]); b.L(film.outputs[0], fin.inputs[1]); b.L(pm.outputs[0], fin.inputs[2])
    b.L(fin.outputs[0], b.out.inputs[0])
    return b.m


def ground_noise(name, col_a, col_b, rough, scale=1.5, wet=1.0, bump=0.3):
    """Verge / grass / earth: two-colour noise, wet = smoother."""
    b = NB(name)
    tc = b.N('ShaderNodeTexCoord').outputs['Object']
    nz = b.N('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = scale; nz.inputs['Detail'].default_value = 8
    b.L(tc, nz.inputs['Vector'])
    col = b.mixc(nz.outputs['Fac'], (*hexlin(col_a), 1), (*hexlin(col_b), 1))
    bs = b.N('ShaderNodeBsdfPrincipled'); b.L(col, bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = rough
    bm = b.N('ShaderNodeBump'); bm.inputs['Strength'].default_value = bump
    nz2 = b.N('ShaderNodeTexNoise'); nz2.inputs['Scale'].default_value = scale * 30; b.L(tc, nz2.inputs['Vector'])
    b.L(nz2.outputs['Fac'], bm.inputs['Height']); b.L(bm.outputs[0], bs.inputs['Normal'])
    b.L(bs.outputs[0], b.out.inputs[0])
    return b.m


def paddy_water(name, rough=0.04, r0=0.02):
    """Paddy water (bible §6·1: Lanbai/Sea still-mirror mode, black albedo): Fresnel mirror only."""
    b = NB(name)
    gl = b.N('ShaderNodeBsdfGlossy'); gl.inputs['Roughness'].default_value = rough
    geo = b.N('ShaderNodeNewGeometry')
    cosv = b.math('MAXIMUM', b.vmath('DOT_PRODUCT', geo.outputs['Normal'], geo.outputs['Incoming']), 0.0)
    Rth = b.math('ADD', r0, b.math('MULTIPLY', 1 - r0, b.math('POWER', b.math('SUBTRACT', 1.0, cosv), 5.0)))
    dif = b.N('ShaderNodeBsdfDiffuse'); dif.inputs['Color'].default_value = (0.01, 0.012, 0.01, 1)
    mx = b.N('ShaderNodeMixShader'); b.L(Rth, mx.inputs[0]); b.L(dif.outputs[0], mx.inputs[1]); b.L(gl.outputs[0], mx.inputs[2])
    b.L(mx.outputs[0], b.out.inputs[0])
    return b.m
