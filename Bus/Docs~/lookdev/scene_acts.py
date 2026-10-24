# -*- coding: utf-8 -*-
"""参考渲染：主座位在各幕里的车厢（圣经 §4.8 的表）。和 Lanbai/Cabin 同一套项：
  车厢 = 反照率 ×（_CabinTubeLM.rgb × 管灯 + _Udon_CabinAmbient × AO）+ 实时光（太阳 / 月）；漂白、侵蚀（同一个阈值公式、
  同一组系数、同一个噪声映射；噪声用 Blender 的 Noise 代替 shader 的哈希 FBM，统计上一样、图案不同）、侵蚀边 3 cm 发
  _Udon_CabinAmbient × 1.5。天只给相机看（不照车厢）：Unity 里天光也不进车厢（车厢只吃 _Udon_CabinAmbient）。
窗外是每幕的“天色占位”，不是那一幕的画面。
    --set act=1|2|4|4c|6|7a|8|9|11|12  [--set blend=...] [--set eye=x,y,z]
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.join(HERE, '..', '..', '..')
sys.path.insert(0, os.path.join(HERE, '..', '..', 'Source'))
sys.path.insert(0, HERE)
import build_bus  # noqa: E402
import bus_spec as B  # noqa: E402
import scene_final as SF  # noqa: E402

lin = build_bus.srgb2lin

# bible §4.8 table (tubes, bleach, fade, ambient colour x k) + a sky placeholder + an optional sun (unity dir TO the sun,
# E, colour). E for suns in Unity units (scene_harness: pi x E in Cycles).
ACTS = {
    '1': dict(t=-5, grade='S1', tubes=1.0, bleach=0, fade=0, amb=('#232A3A', 0.0), sky=('#0A0E18', 1.0), sun=None),
    '2': dict(t=30, grade='S2', tubes=1.0, bleach=0, fade=0, amb=('#232A3A', 0.0), sky=('#0C1018', 1.0), sun=None),
    '4': dict(t=150.3, grade='S4', tubes=0.31, bleach=0, fade=0, amb=('#232A3A', 0.3), sky=('#121630', 1.0), sun=None, tear=True),
    '4c': dict(t=200, grade='S4c', tubes=0.0, bleach=0, fade=0, amb=('#B5C3DB', 0.30), sky=('#B9C2D6', 1.0), sun=None),
    '6': dict(t=270, grade='S6', tubes=0.0, bleach=0.08, fade=0, amb=('#98A4B8', 0.5), sky=('#AEBBD0', 1.0),
              sun=((30, 6), 2.5, '#FFD9A8')),
    '7a': dict(t=500, grade='S7a', tubes=0.0, bleach=0.25, fade=0.25, amb=('#6186A7', 0.6), sky=('#2C5373', 1.0), sun=None),
    '8': dict(t=955, grade='S8', tubes=0.0, bleach=0.48, fade=0.6, amb=('#828BAA', 0.45), sky=('#C7A9B4', 1.0),
              sun=((-10, 8), 1.6, '#FFB38A')),
    '9': dict(t=1100, grade='S9a', tubes=0.0, bleach=0.7, fade=0.86, amb=('#232A3A', 0.3), sky=('#05070E', 1.0), sun=None),
    '11': dict(t=1200, grade='S11', tubes=1.0, bleach=0, fade=0, amb=('#232A3A', 0.0), sky=('#07080C', 1.0), sun=None),
    '12': dict(t=1265, grade='S12', tubes=1.0, bleach=0, fade=0, amb=('#3A4250', 0.25), sky=('#30384A', 1.0), sun=None),
}


def camera_only_world(rgb):
    w = bpy.context.scene.world
    nt = w.node_tree
    for n in list(nt.nodes):
        nt.nodes.remove(n)
    bg = nt.nodes.new('ShaderNodeBackground')
    bg.inputs[0].default_value = (*rgb, 1)
    lp = nt.nodes.new('ShaderNodeLightPath')
    black = nt.nodes.new('ShaderNodeBackground')
    black.inputs[0].default_value = (0, 0, 0, 1)
    mix = nt.nodes.new('ShaderNodeMixShader')
    out = nt.nodes.new('ShaderNodeOutputWorld')
    # seen by camera, glass and glossy rays; never lights the cabin diffusely (Unity: the cabin only takes _Udon_CabinAmbient)
    nt.links.new(lp.outputs['Is Diffuse Ray'], mix.inputs[0])
    nt.links.new(bg.outputs[0], mix.inputs[1])
    nt.links.new(black.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], out.inputs[0])


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


def erosion_field(nt, fade, resist=0.0):
    """s = noise_range(noise) - tau(pos) (s < 0 = removed); the Lanbai/Cabin default form (_ErodeForm 0)."""
    geo = nt.nodes.new('ShaderNodeNewGeometry')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ')
    nt.links.new(geo.outputs['Position'], sep.inputs[0])
    x, zu, yu = sep.outputs[0], sep.outputs[1], sep.outputs[2]          # blender (x, y, z) = unity (x, z, y)
    y0, y1, z0, z1 = B.FLOOR_Y, B.CEIL_Y, B.Z_REAR, B.Z_FRONT
    hN = _m(nt, 'MINIMUM', _m(nt, 'MAXIMUM', _m(nt, 'DIVIDE', _m(nt, 'SUBTRACT', yu, y0), y1 - y0), 0.0), 1.0)
    fN = _m(nt, 'MINIMUM', _m(nt, 'MAXIMUM', _m(nt, 'DIVIDE', _m(nt, 'SUBTRACT', zu, z0), z1 - z0), 0.0), 1.0)
    sx, sy, sz = B.SKY_C
    qx = _m(nt, 'MAXIMUM', _m(nt, 'SUBTRACT', _m(nt, 'ABSOLUTE', _m(nt, 'SUBTRACT', x, sx)), B.SKY_HALF), 0.0)
    qz = _m(nt, 'MAXIMUM', _m(nt, 'SUBTRACT', _m(nt, 'ABSOLUTE', _m(nt, 'SUBTRACT', zu, sz)), B.SKY_HALF), 0.0)
    dy = _m(nt, 'SUBTRACT', yu, sy)
    d = _m(nt, 'SQRT', _m(nt, 'ADD', _m(nt, 'ADD', _m(nt, 'MULTIPLY', qx, qx), _m(nt, 'MULTIPLY', qz, qz)), _m(nt, 'MULTIPLY', dy, dy)))
    e = _m(nt, 'EXPONENT', _m(nt, 'DIVIDE', d, -0.8))
    tau = _m(nt, 'SUBTRACT', fade, _m(nt, 'MULTIPLY', _m(nt, 'SUBTRACT', 1.0, hN), 0.45))
    tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', _m(nt, 'SUBTRACT', 1.0, fN), 0.25))
    tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', _m(nt, 'SUBTRACT', 1.0, e), 0.35))
    tau = _m(nt, 'SUBTRACT', tau, resist)
    # protections: the seat sphere (0.9 m round the hero seat) until 0.97; the floor patch until 0.65
    ex, ey, ez = B.EYE
    ds = _m(nt, 'SQRT', _m(nt, 'ADD', _m(nt, 'ADD', _m(nt, 'POWER', _m(nt, 'SUBTRACT', x, ex), 2.0),
                                              _m(nt, 'POWER', _m(nt, 'SUBTRACT', yu, ey - 0.45), 2.0)), _m(nt, 'POWER', _m(nt, 'SUBTRACT', zu, ez), 2.0)))
    if fade < 0.97:
        tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', _m(nt, 'LESS_THAN', ds, 0.9), 10.0))
    if fade < 0.65:
        low = _m(nt, 'LESS_THAN', yu, B.FLOOR_Y + 0.08)
        tau = _m(nt, 'SUBTRACT', tau, _m(nt, 'MULTIPLY', low, 10.0))
    nz = nt.nodes.new('ShaderNodeTexNoise')
    nz.inputs['Scale'].default_value = 1.0 / 0.55
    nz.inputs['Detail'].default_value = 3.0
    nt.links.new(geo.outputs['Position'], nz.inputs['Vector'])
    nu = _m(nt, 'MINIMUM', _m(nt, 'MAXIMUM', _m(nt, 'DIVIDE', _m(nt, 'SUBTRACT', nz.outputs['Fac'], 0.30), 0.40), 0.0), 1.0)
    nr = _m(nt, 'ADD', -0.20, _m(nt, 'MULTIPLY', nu, 0.45))
    return _m(nt, 'SUBTRACT', nr, tau)


# per-surface vertex-colour looks: the same values the Unity build writes (Bus/Editor/LanbaiBusBuild.cs)
#   wear (G): colour, amount; grime (R): colour (albedo x colour x 2), amount; fade (B <= 0.75) colour, amount
VC = {
    'Vinyl': dict(wear=('#6A3434', 1.0), fade=('#7A4A48', 1.0)),
    'SeatFrame': dict(wear=('#3C3E3D', 1.0)),
    'Floor': dict(wear=('#4A4B47', 1.0), grime=('#555550', 1.0, 'abs')),       # corner dust: lerp TO the colour
    'Int_Enamel': dict(wear=('#5B5A55', 1.0), grime=('#8C8370', 1.0)),
    'Int_Ceiling': dict(grime=('#CFC09A', 1.0)),
    'Dash': dict(wear=('#3E3F40', 1.0), grime=('#6A6355', 1.0)),
    'Alu': dict(grime=('#6B5A48', 1.0)),
    'Bakelite': dict(wear=('#2E2E2E', 1.0)),
    'RadioLeather': dict(wear=('#4A2E1F', 1.0)),
}


def _mixc(nt, fac, a, b):
    n = nt.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    for sock, v in ((0, fac), (6, a), (7, b)):
        if isinstance(v, (int, float)):
            n.inputs[sock].default_value = v
        elif isinstance(v, tuple):
            n.inputs[sock].default_value = (*v, 1)
        else:
            nt.links.new(v, n.inputs[sock])
    return n.outputs[2]


def _mulc(nt, a, b):
    n = nt.nodes.new('ShaderNodeMix')
    n.data_type = 'RGBA'
    n.blend_type = 'MULTIPLY'
    n.inputs[0].default_value = 1.0
    for sock, v in ((6, a), (7, b)):
        if isinstance(v, tuple):
            n.inputs[sock].default_value = (*v, 1)
        else:
            nt.links.new(v, n.inputs[sock])
    return n.outputs[2]


def act_material(m_src, lm_img, P, ambient, tubes):
    """the Lanbai/Cabin terms as an emission + the Principled lit by the sun only; vertex-colour wear / grime / fade,
    bleach, erosion clip and rim."""
    m = m_src.copy()
    nt = m.node_tree
    bs = nt.nodes.get('Principled BSDF')
    out = [n for n in nt.nodes if n.type == 'OUTPUT_MATERIAL'][0]
    c = tuple(list(bs.inputs['Base Color'].default_value)[:3])
    key = m_src.name.replace('M_Bus_', '').split('.')[0]
    look = VC.get(key, {})
    vc = nt.nodes.new('ShaderNodeVertexColor')
    vc.layer_name = 'Col'
    sep = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(vc.outputs['Color'], sep.inputs[0])
    alb = c
    if 'wear' in look:
        alb = _mixc(nt, _m(nt, 'MULTIPLY', sep.outputs[1], look['wear'][1]), alb, tuple(lin(look['wear'][0])))
    if 'grime' in look:
        if len(look['grime']) > 2:           # _GrimeAbsolute 1
            dirty = tuple(lin(look['grime'][0]))
        else:
            g = tuple(2.0 * v for v in lin(look['grime'][0]))
            dirty = _mulc(nt, alb if not isinstance(alb, tuple) else alb, g)
        alb = _mixc(nt, _m(nt, 'MULTIPLY', sep.outputs[0], look['grime'][1]), alb, dirty)
    if 'fade' in look:
        f = _m(nt, 'MINIMUM', _m(nt, 'DIVIDE', sep.outputs[2], 0.75), 1.0)
        alb = _mixc(nt, _m(nt, 'MULTIPLY', f, look['fade'][1]), alb, tuple(lin(look['fade'][0])))
    # bleach: albedo -> luminance x 0.9 tinted by the ambient colour
    bl = P['bleach']
    if bl > 0:
        bw = nt.nodes.new('ShaderNodeRGBToBW')
        if isinstance(alb, tuple):
            bw.inputs[0].default_value = (*alb, 1)
        else:
            nt.links.new(alb, bw.inputs[0])
        an = max(1e-4, max(ambient))
        tint = tuple(0.9 * v / an for v in ambient)
        lum_t = _mulc(nt, (1.0, 1.0, 1.0), tint)
        lum_c = nt.nodes.new('ShaderNodeCombineColor')
        for k in range(3):
            nt.links.new(bw.outputs[0], lum_c.inputs[k])
        target = _mulc(nt, lum_c.outputs[0], tint)
        alb = _mixc(nt, bl, alb, target)
        r = bs.inputs['Roughness'].default_value
        bs.inputs['Roughness'].default_value = r * (1 - bl) + 0.7 * bl
    if isinstance(alb, tuple):
        bs.inputs['Base Color'].default_value = (*alb, 1)
        alb_sock = None
    else:
        nt.links.new(alb, bs.inputs['Base Color'])
        alb_sock = alb
    t = nt.nodes.new('ShaderNodeTexImage')
    t.image = lm_img
    uv = nt.nodes.new('ShaderNodeUVMap')
    uv.uv_map = 'UVLightmap'
    nt.links.new(uv.outputs[0], t.inputs[0])
    sepl = nt.nodes.new('ShaderNodeSeparateColor')
    nt.links.new(t.outputs['Color'], sepl.inputs[0])
    # E = LM.rgb x tubes + ambient x AO ; emission = albedo x E
    comb = nt.nodes.new('ShaderNodeCombineColor')
    for k in range(3):
        ch = _m(nt, 'ADD', _m(nt, 'MULTIPLY', sepl.outputs[k], tubes), _m(nt, 'MULTIPLY', t.outputs['Alpha'], ambient[k]))
        nt.links.new(ch, comb.inputs[k])
    emc = _mulc(nt, comb.outputs[0], alb_sock if alb_sock is not None else alb)
    em = nt.nodes.new('ShaderNodeEmission')
    nt.links.new(emc, em.inputs['Color'])
    add = nt.nodes.new('ShaderNodeAddShader')
    nt.links.new(bs.outputs[0], add.inputs[0])
    nt.links.new(em.outputs[0], add.inputs[1])
    final = add.outputs[0]
    if P['fade'] > 0:
        s_ = erosion_field(nt, P['fade'], 0.30 if 'Steel' in m_src.name else 0.0)
        rim = nt.nodes.new('ShaderNodeEmission')
        rim.inputs['Color'].default_value = (*[1.5 * v for v in ambient], 1)
        isrim = _m(nt, 'LESS_THAN', s_, 0.02)
        mix_r = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(isrim, mix_r.inputs[0])
        nt.links.new(final, mix_r.inputs[1])
        nt.links.new(rim.outputs[0], mix_r.inputs[2])
        keep = _m(nt, 'GREATER_THAN', s_, 0.0)
        tr = nt.nodes.new('ShaderNodeBsdfTransparent')
        mix = nt.nodes.new('ShaderNodeMixShader')
        nt.links.new(keep, mix.inputs[0])
        nt.links.new(tr.outputs[0], mix.inputs[1])
        nt.links.new(mix_r.outputs[0], mix.inputs[2])
        final = mix.outputs[0]
    nt.links.new(final, out.inputs[0])
    return m


def pane_fade_at(o):
    """LanbaiCabinDriver.PaneThresholds: the fade at which a BusGlass pane is switched off (tau at its centre > median)."""
    from mathutils import Vector
    vs = [o.matrix_world @ v.co for v in o.data.vertices]
    c = sum(vs, Vector()) / max(len(vs), 1)
    x, y, z = c.x, c.z, c.y                                   # blender -> unity
    hN = min(max((y - 0.62) / 2.00, 0.0), 1.0)
    fN = min(max((z + 3.65) / 7.15, 0.0), 1.0)
    qx, qz = max(abs(x - 0.55) - 0.30, 0.0), max(abs(z - 2.80) - 0.30, 0.0)
    e = math.exp(-math.sqrt(qx * qx + qz * qz + (y - 2.62) ** 2) / 0.8)
    return 0.025 + 0.45 * (1 - hN) + 0.25 * (1 - fN) + 0.35 * (1 - e)


def erode_everything_else(objs, fade):
    """in Unity every Lanbai/Cabin and ThinCloth renderer clips on the same field, and the driver switches the glass
    panes off as the fade passes them: do the same for the objects build() did not already erode."""
    done = ('Cabin_Static', 'Bus_Exterior', 'Bus_Door')
    bpy.context.view_layer.update()                           # matrix_world of the appended objects (else identity)
    for n, o in objs.items():
        if o.type != 'MESH' or o.hide_render or n.startswith(done):
            continue
        if n.startswith('Glass_'):
            if fade >= pane_fade_at(o):
                o.hide_render = True
            continue
        resist = 0.30 if n.startswith('Cabin_Pole') else 0.0
        for i, m in enumerate(list(o.data.materials)):
            if m is None or not m.use_nodes:
                continue
            mm = m.copy()
            nt = mm.node_tree
            outn = [x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL'][0]
            if not outn.inputs[0].links:
                continue
            src = outn.inputs[0].links[0].from_socket
            keep = _m(nt, 'GREATER_THAN', erosion_field(nt, fade, resist), 0.0)
            tr = nt.nodes.new('ShaderNodeBsdfTransparent')
            mx = nt.nodes.new('ShaderNodeMixShader')
            nt.links.new(keep, mx.inputs[0])
            nt.links.new(tr.outputs[0], mx.inputs[1])
            nt.links.new(src, mx.inputs[2])
            nt.links.new(mx.outputs[0], outn.inputs[0])
            o.data.materials[i] = mm


def build(ctx):
    S = ctx['lbh_scene']
    a = ctx['args']
    P = ACTS[a.get('act', '2')]
    if 'eye' in a:
        ctx['cam']['eye'] = [float(v) for v in a['eye'].split(',')]
        ctx['eye'] = ctx['cam']['eye']
    objs = SF.load_blend(a.get('blend', '/tmp/bus/bus_final_ext.blend'))
    # eroded acts: a grazing ray crosses many cut-away (transparent) layers; Cycles' default 8 left black slivers
    bpy.context.scene.cycles.transparent_max_bounces = 128
    for n, o in objs.items():
        if n.endswith('_LOD1'):
            o.hide_render = True
    tex = os.path.join(ROOT, 'Bus', 'Textures')
    SF.exterior_material(objs['Bus_Exterior_LOD0'], tex, 2048)
    camera_only_world(lin(P['sky'][0]))
    # Unity culls back faces: the exterior skin is invisible from inside (so the cabin's erosion holes open to the sky)
    for n, o in objs.items():
        if o.type == 'MESH' and (n.startswith('Bus_Exterior') or n.startswith('Bus_Door')):
            for i, m in enumerate(list(o.data.materials)):
                mm = m.copy()
                nt = mm.node_tree
                outn = [x for x in nt.nodes if x.type == 'OUTPUT_MATERIAL'][0]
                src = outn.inputs[0].links[0].from_socket
                geo = nt.nodes.new('ShaderNodeNewGeometry')
                tr = nt.nodes.new('ShaderNodeBsdfTransparent')
                mx = nt.nodes.new('ShaderNodeMixShader')
                nt.links.new(geo.outputs['Backfacing'], mx.inputs[0])
                nt.links.new(src, mx.inputs[1])
                nt.links.new(tr.outputs[0], mx.inputs[2])
                res = mx.outputs[0]
                if P['fade'] > 0:          # the exterior is Lanbai/Cabin too: it erodes with the same field
                    keep = _m(nt, 'GREATER_THAN', erosion_field(nt, P['fade']), 0.0)
                    tr2 = nt.nodes.new('ShaderNodeBsdfTransparent')
                    mx2 = nt.nodes.new('ShaderNodeMixShader')
                    nt.links.new(keep, mx2.inputs[0])
                    nt.links.new(tr2.outputs[0], mx2.inputs[1])
                    nt.links.new(res, mx2.inputs[2])
                    res = mx2.outputs[0]
                nt.links.new(res, outn.inputs[0])
                o.data.materials[i] = mm
    amb = [P['amb'][1] * v for v in lin(P['amb'][0])]
    lm = bpy.data.images.load(os.path.join(tex, 'Cabin_TubeLM.exr'))
    lm.colorspace_settings.name = 'Non-Color'
    cs = objs['Cabin_Static']
    for i, m in enumerate(list(cs.data.materials)):
        cs.data.materials[i] = act_material(m, lm, P, amb, P['tubes'])
    if 'Cabin_Tubes' in objs:
        e = bpy.data.materials.new('TubeGlow')
        e.use_nodes = True
        nt = e.node_tree
        for nd in list(nt.nodes):
            nt.nodes.remove(nd)
        em = nt.nodes.new('ShaderNodeEmission')
        em.inputs[0].default_value = (*lin('#E7FEFF' if P['tubes'] > 0 else '#D8DBD6'), 1)
        em.inputs[1].default_value = 2.04 * P['tubes'] if P['tubes'] > 0 else max(0.02, amb[1])
        o_ = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(em.outputs[0], o_.inputs[0])
        objs['Cabin_Tubes'].data.materials.clear()
        objs['Cabin_Tubes'].data.materials.append(e)
    if P['fade'] > 0:
        erode_everything_else(objs, P['fade'])
    if P['sun']:
        (az, el), E, col = P['sun']
        S.unity_directional('Sun', E, col, B.dir_az_el(az, el))
    if P.get('tear'):
        import scene_d13 as D13
        D13.lens(S, P['t'], ctx['eye'])
        D13.disc(S, 'Moon', -12, 8, 1.2, D13.emis('MoonMat', lin('#E8EEF8'), 6.0))
    if a.get('exterior'):
        # act 1 from the spawn point (bible 6.1): one headlight spot for both lamps (3200 K, 35 deg, no shadow), the
        # tubes glowing through the windows; a cold stand-in for the stop lamp 14 m ahead of the spawn (not the stop kit)
        ld = bpy.data.lights.new('Headlights', 'SPOT')
        ld.energy, ld.spot_size, ld.color, ld.use_shadow = 900.0, math.radians(35), lin('#FFC47A'), False
        lo = bpy.data.objects.new('Headlights', ld)
        lo.location = S.U2B((B.XC, 0.70, B.Z_FRONT + 0.1))
        lo.rotation_euler = (math.radians(85), 0, 0)          # blender spot looks down -Z: tilt it to unity +Z (forward), 5 deg down
        bpy.context.scene.collection.objects.link(lo)
        lamp = bpy.data.lights.new('StopLamp', 'POINT')
        lamp.energy, lamp.color, lamp.shadow_soft_size = 300.0, lin('#E4F1F3'), 0.1
        lp_ = bpy.data.objects.new('StopLamp', lamp)
        lp_.location = S.U2B((3.6, 4.2, 4.0))
        bpy.context.scene.collection.objects.link(lp_)
        glow = S.mat_emission('StopLampGlow', lin('#EEF5F7'), 8.0)
        S.mesh_object('StopLampHead', [(3.45, 4.15, 4.0), (3.75, 4.15, 4.0), (3.75, 4.25, 4.0), (3.45, 4.25, 4.0)], [(0, 1, 2, 3)], glow)
    ground = S.mat_emission('Ground', [0.3 * v for v in lin(P['sky'][0])], 1.0)
    if a.get('exterior'):
        ground = bpy.data.materials.new('WetRoad')
        ground.use_nodes = True
        bsdf = ground.node_tree.nodes['Principled BSDF']
        bsdf.inputs['Base Color'].default_value = (*lin('#1E1F21'), 1)
        bsdf.inputs['Roughness'].default_value = 0.25
    if a.get('act') in ('1', '2', '11', '12', '6'):
        S.mesh_object('Ground', [(-200, 0, -300), (200, 0, -300), (200, 0, 300), (-200, 0, 300)], [(0, 1, 2, 3)], ground)
    return dict(what='act %s cabin reference' % a.get('act'), tubes=P['tubes'], bleach=P['bleach'], fade=P['fade'])
