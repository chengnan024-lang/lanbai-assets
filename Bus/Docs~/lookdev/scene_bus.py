# -*- coding: utf-8 -*-
"""标准台场景：真车（Bus/Source/build_bus.py，在进程里直接搭，玻璃是真的薄玻璃）+ 取景目标 / 夜的布光。
用 --bus none 跑（车由这里搭）。--set mode=targets|night ；--set door=open|closed
    ~/bpy/bin/python Engineering/render_harness/lbh_render.py --scene Bus/Docs~/lookdev/scene_bus.py --bus none \
        --cam hero --grade S2 --act 02 --t 30 --set mode=night --out /tmp/bus/r01_night
"""
import math
import os
import sys

import bpy

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', '..', 'Source'))
import build_bus  # noqa: E402
import bus_spec as B  # noqa: E402


def hexlin(h):
    return build_bus.srgb2lin(h)


def targets(S, eye):
    me = S.mat_emission('Target', (1.0, 0.55, 0.15), 6.0)
    for i, (name, az, el) in enumerate(B.TARGETS):
        az, el = B.TARGETS_MOVED.get(name, (az, el))
        if name == '收音机':
            continue
        d = B.dir_az_el(az, el)
        r, R = 60.0, 60.0 * math.tan(math.radians(0.9))
        c = [eye[k] + r * d[k] for k in range(3)]
        up = (0.0, 1.0, 0.0) if abs(d[1]) < 0.9 else (0.0, 0.0, 1.0)
        rx = (up[1] * d[2] - up[2] * d[1], up[2] * d[0] - up[0] * d[2], up[0] * d[1] - up[1] * d[0])
        n = math.sqrt(sum(x * x for x in rx))
        rx = [x / n for x in rx]
        ry = (d[1] * rx[2] - d[2] * rx[1], d[2] * rx[0] - d[0] * rx[2], d[0] * rx[1] - d[1] * rx[0])
        V = [c] + [[c[j] + R * (math.cos(2 * math.pi * k / 16) * rx[j] + math.sin(2 * math.pi * k / 16) * ry[j]) for j in range(3)] for k in range(16)]
        F = [(0, 1 + k, 1 + (k + 1) % 16) for k in range(16)]
        S.mesh_object('T_%02d' % i, V, F, me)


def tube_lights(S, scale=1.0, watts=7.0):
    """bible 4.3: each tube a 1.15 x 0.12 m area light (#E4F1F3) + the diffuser glowing #E7FEFF @ +1.03."""
    col = hexlin('#E4F1F3')
    em = hexlin('#E7FEFF')
    for ob in [o for o in bpy.data.objects if o.name.startswith('Tube')]:
        m = bpy.data.materials.new('TubeGlow_' + ob.name)
        m.use_nodes = True
        nt = m.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        e = nt.nodes.new('ShaderNodeEmission')
        e.inputs[0].default_value = (*em, 1)
        e.inputs[1].default_value = 2.04 * scale
        o = nt.nodes.new('ShaderNodeOutputMaterial')
        nt.links.new(e.outputs[0], o.inputs[0])
        ob.data.materials.clear()
        ob.data.materials.append(m)
        ob.visible_shadow = False
        # the area light just under the diffuser, facing down
        bb = [ob.matrix_world @ v.co for v in ob.data.vertices]
        cx = sum(v.x for v in bb) / len(bb)
        cy = sum(v.y for v in bb) / len(bb)
        cz = min(v.z for v in bb) - 0.005
        ld = bpy.data.lights.new('L_' + ob.name, 'AREA')
        ld.shape = 'RECTANGLE'
        ld.size = 0.12
        ld.size_y = 1.10
        ld.energy = watts * scale
        ld.color = col
        lo = bpy.data.objects.new('L_' + ob.name, ld)
        lo.location = (cx, cy, cz)
        bpy.context.scene.collection.objects.link(lo)


def build(ctx):
    S = ctx['lbh_scene']
    a = ctx['args']
    mode = a.get('mode', 'targets')
    build_bus.build(open_door=a.get('door', 'open') == 'open', reset=False)
    eye = ctx['eye']
    if mode == 'targets':
        S.unity_ambient_flat((0.03, 0.032, 0.036))
        targets(S, eye)
        tube_lights(S, scale=float(a.get('tubes', 0.25)))
    elif mode == 'night':
        # night road (act 2): dark blue-grey sky, wet asphalt, tubes at 1 (bible 4.8)
        S.unity_ambient_flat(tuple(0.25 * c for c in hexlin('#1B2230')))
        road = S.mat_emission('RoadDark', hexlin('#0B0C0E'), 1.0)
        S.mesh_object('Road', [(-60, 0, -200), (60, 0, -200), (60, 0, 200), (-60, 0, 200)], [(0, 1, 2, 3)], road)
        tube_lights(S, scale=float(a.get('tubes', 1.0)), watts=float(a.get('watts', 7.0)))
    return dict(what='bus %s' % mode)
