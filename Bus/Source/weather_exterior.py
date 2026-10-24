# -*- coding: utf-8 -*-
"""车外观的做旧（圣经 §4.9）：在 Bus_Exterior_LOD0 的 uv1 图集上，先烘位置 / 法线 / 底色三张图，再用 numpy 按位置算做旧。
- 锈泡 #6B3A1E（轮拱、门槛、门边、保险杠附近；PAZ_04 / PAZ_07 的位置）
- 窗角流下的雨痕 #5B574E α ≤ 0.35（每扇窗的两个下角往下）
- 下 30 cm 的泥点 #5A4A3A α ≤ 0.6
- 门边掉漆露灰底漆 #8A8C88
- 车顶白漆氧化发粉（光滑度 0.28）
输出（Bus/Textures/）：
  Bus_Exterior_Albedo_2048.png（sRGB）
  Bus_Exterior_Mask_2048.png（线性：R 金属、G 光滑度、B 湿（立面水膜 1 / 车顶 0）、A AO）
    ~/bpy/bin/python Bus/Source/weather_exterior.py --blend /tmp/bus/bus_final.blend --res 2048
用 uv1（UVLightmap 层）：外观的 uv1 是唯一图集，uv0 仍是米制盒投影（给平铺细节）。
"""
import argparse
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import bus_spec as B  # noqa: E402
import build_bus as BB  # noqa: E402


def U(v):
    return np.stack([v[..., 0], v[..., 2], v[..., 1]], -1)


def ensure_uv1(ob):
    me = ob.data
    if 'UVLightmap' not in me.uv_layers:
        me.uv_layers.new(name='UVLightmap')
    src, dst = me.uv_layers['UVMap'].data, me.uv_layers['UVLightmap'].data
    for i in range(len(src)):
        dst[i].uv = src[i].uv
    me.uv_layers.active = me.uv_layers['UVLightmap']
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.mode_set(mode='EDIT')
    bpy.ops.mesh.select_all(action='SELECT')
    bpy.context.scene.tool_settings.use_uv_select_sync = True
    bpy.ops.uv.select_all(action='SELECT')
    try:
        bpy.ops.uv.pack_islands(rotate=True, rotate_method='ANY', scale=True, margin_method='FRACTION', margin=0.002, shape_method='CONCAVE')
    except TypeError:
        bpy.ops.uv.pack_islands(margin=0.002, rotate=True, scale=True)
    bpy.ops.object.mode_set(mode='OBJECT')
    me.uv_layers.active = me.uv_layers['UVMap']
    me.uv_layers['UVMap'].active_render = True


def bake_emit(ob, res, kind):
    """bake an emission of world position / normal / material base colour into a float image on uv1."""
    me = ob.data
    orig = [m for m in me.materials]
    tmp = []
    for m in orig:
        t = bpy.data.materials.new('tmp_' + kind)
        t.use_nodes = True
        nt = t.node_tree
        for n in list(nt.nodes):
            nt.nodes.remove(n)
        e = nt.nodes.new('ShaderNodeEmission')
        out = nt.nodes.new('ShaderNodeOutputMaterial')
        if kind == 'pos':
            g = nt.nodes.new('ShaderNodeNewGeometry')
            nt.links.new(g.outputs['Position'], e.inputs['Color'])
        elif kind == 'nrm':
            g = nt.nodes.new('ShaderNodeNewGeometry')
            nt.links.new(g.outputs['Normal'], e.inputs['Color'])
        else:
            bs = m.node_tree.nodes.get('Principled BSDF')
            c = bs.inputs['Base Color'].default_value
            e.inputs['Color'].default_value = (c[0], c[1], c[2], 1)
            if kind == 'rough':
                r = bs.inputs['Roughness'].default_value
                mt = bs.inputs['Metallic'].default_value
                e.inputs['Color'].default_value = (mt, 1 - r, 0, 1)
        e.inputs['Strength'].default_value = 1.0
        nt.links.new(e.outputs[0], out.inputs[0])
        img_node = nt.nodes.new('ShaderNodeTexImage')
        tmp.append((t, img_node))
    img = bpy.data.images.new('bake_' + kind, res, res, alpha=True, float_buffer=True)
    for i, (t, n) in enumerate(tmp):
        n.image = img
        t.node_tree.nodes.active = n
        me.materials[i] = t
    me.uv_layers.active = me.uv_layers['UVLightmap']
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 1
    sc.render.bake.margin = 6
    sc.render.bake.target = 'IMAGE_TEXTURES'
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True)
    bpy.context.view_layer.objects.active = ob
    bpy.ops.object.bake(type='EMIT')
    for i, m in enumerate(orig):
        me.materials[i] = m
    me.uv_layers.active = me.uv_layers['UVMap']
    return np.array(img.pixels[:], np.float32).reshape(res, res, 4)


_PERM = np.random.default_rng(1234).permutation(4096)
_VALS = np.random.default_rng(99).random(4096).astype(np.float32)


def vnoise(P, scale, seed=0):
    """3D value noise (hashed lattice, smoothstep-trilinear), 0..1."""
    Q = P * scale + seed * 17.13
    i = np.floor(Q).astype(np.int64)
    f = Q - i
    f = f * f * (3 - 2 * f)

    def h(dx, dy, dz):
        k = _PERM[(i[..., 0] + dx) % 4096]
        k = _PERM[(k + i[..., 1] + dy) % 4096]
        k = _PERM[(k + i[..., 2] + dz) % 4096]
        return _VALS[k]
    x0 = h(0, 0, 0) * (1 - f[..., 0]) + h(1, 0, 0) * f[..., 0]
    x1 = h(0, 1, 0) * (1 - f[..., 0]) + h(1, 1, 0) * f[..., 0]
    x2 = h(0, 0, 1) * (1 - f[..., 0]) + h(1, 0, 1) * f[..., 0]
    x3 = h(0, 1, 1) * (1 - f[..., 0]) + h(1, 1, 1) * f[..., 0]
    y0 = x0 * (1 - f[..., 1]) + x1 * f[..., 1]
    y1 = x2 * (1 - f[..., 1]) + x3 * f[..., 1]
    return y0 * (1 - f[..., 2]) + y1 * f[..., 2]


def fbm(P, scale, seed=0, octaves=4):
    out, amp, tot = 0.0, 1.0, 0.0
    for o in range(octaves):
        out = out + amp * vnoise(P, scale * 2 ** o, seed + o)
        tot += amp
        amp *= 0.5
    return out / tot


def weather(pos_b, nrm_b, base, rough):
    P = U(pos_b[..., :3])                       # unity coords
    N = U(nrm_b[..., :3])
    valid = pos_b[..., 3] > 0.5
    x, y, z = P[..., 0], P[..., 1], P[..., 2]
    alb = base[..., :3].copy()                  # linear
    metal, smooth = rough[..., 0].copy(), rough[..., 1].copy()
    lin = lambda h: np.array(BB.srgb2lin(h), np.float32)
    n1, n2, n3 = fbm(P, 2.0, 1) * 2 - 1, fbm(P, 7.0, 2) * 2 - 1, fbm(P, 23.0, 3) * 2 - 1
    dots = vnoise(P, 55.0, 7)
    side = np.abs(N[..., 1]) < 0.5
    # --- rust: arches, sills, door edges, lower front corners (PAZ_04 / 07)
    r_arch = np.zeros_like(x)
    for zc in B.AXLES:
        d = np.sqrt((y - B.WHEEL_R) ** 2 + (z - zc) ** 2)
        r_arch = np.maximum(r_arch, np.clip(1 - np.abs(d - B.ARCH_R - 0.03) / 0.07, 0, 1))
    sill = np.clip(1 - (y - B.Y_BOT) / 0.10, 0, 1) * side
    door_edge = (np.clip(1 - np.abs(z - B.DOOR[0]) / 0.05, 0, 1) + np.clip(1 - np.abs(z - B.DOOR[1]) / 0.05, 0, 1)) * (x > 0.9) * (y < 1.3)
    corner_lo = np.clip(1 - (y - B.Y_BOT) / 0.25, 0, 1) * np.clip((z - 3.2) / 0.3, 0, 1) * (z < B.Z_FRONT + 0.03)   # not the bumper bar
    blob = np.clip((fbm(P, 9.0, 11) - 0.45) * 4.0, 0, 1)
    rust = np.clip((0.9 * r_arch + 0.7 * sill + 0.6 * door_edge + 0.5 * corner_lo) * blob * 1.4, 0, 1)
    rust *= (alb.mean(-1) > 0.02)               # not on the black rubber
    rust *= ((z < B.Z_FRONT + 0.03) & (z > B.Z_REAR - 0.03)).astype(np.float32) * 0.85 + 0.15   # bumpers: a few spots only
    # --- rain streaks below every window's lower corners
    streak = np.zeros_like(x)
    corners = []
    for z0, z1 in B.WIN_R:
        corners += [(1, z0), (1, z1)]
    for z0, z1 in B.WIN_L:
        corners += [(-1, z0), (-1, z1)]
    for s, zc in corners:
        on = (np.sign(x - B.XC) == s) & side
        w = 0.025 + 0.02 * (0.5 + 0.5 * n2)
        below = np.clip((B.WIN_SILL - y) / 0.6, 0, 1) * (y < B.WIN_SILL)
        streak = np.maximum(streak, on * np.clip(1 - np.abs(z - zc) / w, 0, 1) * (1 - below) ** 0.5 * (y > B.Y_BOT + 0.05) * (y < B.WIN_SILL))
    # fine vertical streaks everywhere on the sides, very light
    runs = vnoise(np.stack([z * 1.0, y * 0.02, x * 1.0], -1), 45.0, 21)          # thin vertical runs (z-only variation)
    streak = np.maximum(streak, side * np.clip((runs - 0.78) * 4.0, 0, 1) * 0.6 * (y < B.WIN_SILL) * (y > B.Y_BOT + 0.1)
                        * np.clip((B.WIN_SILL - y) / 0.15, 0, 1))
    # --- mud: bottom 30 cm, speckled, heavier behind the wheels
    low = np.clip((B.Y_BOT + 0.30 - y) / 0.30, 0, 1)
    for zc in B.AXLES:              # thrown up behind each wheel
        low = np.maximum(low, np.clip(1 - np.abs(z - (zc - 0.75)) / 0.45, 0, 1) * np.clip((1.05 - y) / 0.5, 0, 1))
    speck = np.clip((dots - (0.80 - 0.25 * low)) * 8.0, 0, 1)
    mud = low * (0.18 + 0.82 * speck) * np.clip(0.6 + n2, 0, 1)
    # --- chips at the door edges and the front corners: grey primer
    chip = np.clip(door_edge * (vnoise(P, 30.0, 5) > 0.72) + corner_lo * (vnoise(P, 30.0, 6) > 0.8), 0, 1)
    # --- roof oxidation: chalky (lighter, flatter)
    roof = np.clip((N[..., 1] - 0.5) / 0.3, 0, 1) * (y > 2.2)
    a = alb
    a = a * (1 - 0.18 * roof[..., None]) + lin('#E8E4DA') * 0.18 * roof[..., None]
    a = a * (1 - (0.35 * streak)[..., None]) + lin('#5B574E') * (0.35 * streak)[..., None]
    a = a * (1 - (0.6 * mud)[..., None]) + lin('#5A4A3A') * (0.6 * mud)[..., None]
    a = a * (1 - chip[..., None]) + lin('#8A8C88') * chip[..., None]
    a = a * (1 - rust[..., None]) + (lin('#6B3A1E') * (0.8 + 0.4 * n2[..., None])) * rust[..., None]
    smooth = np.where(roof > 0.5, 0.28, smooth)
    smooth = smooth * (1 - 0.6 * mud) * (1 - 0.7 * rust) * (1 - 0.4 * chip)
    metal = metal * (1 - rust)
    wet = side.astype(np.float32) * (1 - rust) * (1 - 0.5 * mud)
    ao = np.ones_like(x)
    a[~valid] = 0
    return a, np.stack([metal, smooth, wet, ao], -1), dict(rust_frac=float(rust[valid].mean()), mud_frac=float(mud[valid].mean()),
                                                        streak_frac=float(streak[valid].mean()))


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--blend', default='/tmp/bus/bus_final.blend')
    ap.add_argument('--res', type=int, default=2048)
    ap.add_argument('--out', default=os.path.join(HERE, '..', 'Textures'))
    ap.add_argument('--save-blend', default='/tmp/bus/bus_final_ext.blend')
    a = ap.parse_args()
    bpy.ops.wm.open_mainfile(filepath=a.blend)
    ob = bpy.data.objects['Bus_Exterior_LOD0']
    ensure_uv1(ob)
    pos = bake_emit(ob, a.res, 'pos')
    nrm = bake_emit(ob, a.res, 'nrm')
    base = bake_emit(ob, a.res, 'base')
    rough = bake_emit(ob, a.res, 'rough')
    pos[..., 3] = (np.abs(pos[..., :3]).sum(-1) > 1e-6).astype(np.float32)
    alb, mask, info = weather(pos, nrm, base, rough)
    from PIL import Image
    srgb = np.where(alb <= 0.0031308, alb * 12.92, 1.055 * np.clip(alb, 0, None) ** (1 / 2.4) - 0.055)
    os.makedirs(a.out, exist_ok=True)
    Image.fromarray((np.clip(srgb[::-1], 0, 1) * 255 + 0.5).astype(np.uint8)).save(os.path.join(a.out, 'Bus_Exterior_Albedo_%d.png' % a.res))
    Image.fromarray((np.clip(mask[::-1], 0, 1) * 255 + 0.5).astype(np.uint8), 'RGBA').save(os.path.join(a.out, 'Bus_Exterior_Mask_%d.png' % a.res))
    bpy.ops.wm.save_as_mainfile(filepath=a.save_blend)
    print('[weather]', info)


if __name__ == '__main__':
    main()
