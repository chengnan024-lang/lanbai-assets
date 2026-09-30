"""蓝白 / Lanbai: photoreal volumetric cloud cards (Blender 5.0.1, Cycles, bpy module).

Pipeline (all procedural, no downloads):
  1. numpy builds a density field per cloud shape (hierarchical sphere SDF with
     cauliflower turrets, flat condensation base, billowy Worley displacement,
     wispy Perlin fringes) on a regular voxel grid.
  2. The grid is pushed into Blender as a real volume: a vertex-only mesh carries
     the voxels as a 'density' attribute, a Geometry Nodes 'Volume Cube' rebuilds
     the grid (Sample Index), Cycles renders it as NanoVDB.
  3. Principled Volume, albedo 1, anisotropy 0.55 (silver linings), 14 volume bounces.
  4. Each lighting preset = sun lamp + gradient sky world (dawn / dusk / moon).
  5. Render linear EXR (film transparent, premultiplied) -> numpy: consistent
     low-alpha cleanup, un-premultiply, push colour into transparent areas (no dark
     fringes), aerial haze + edge fades for the sea strips, tone map with the
     scene's view transform (Khronos PBR Neutral) via Image.save_render ->
     straight-alpha RGBA PNG; then contact sheets, clouds_meta.json, fringe checks.

Usage:
  python3 make_clouds.py                         # everything (cards + sea strips + sheets)
  python3 make_clouds.py --only Cumulus --preset dawn --test   # quick low-res look
  python3 make_clouds.py --only 1 2              # the two CloudSea strips only
  python3 make_clouds.py --sheets                # rebuild contact sheets + meta only
  python3 make_clouds.py --keep-exr              # also keep linear EXRs in ./exr
  python3 make_clouds.py --repost                # redo post-processing from ./exr (no render)
Options: --out DIR, --samples 40, --bounces 14, --scale 0.5 (resolution factor)
Needs: bpy 5.0.1 (pip module or Blender's own Python), numpy, scipy, Pillow.
"""
import os
import sys
import math
import time
import argparse
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)

import bpy  # noqa: E402
from mathutils import Vector  # noqa: E402

bpy.ops.wm.read_factory_settings(use_empty=True)

from scipy.ndimage import map_coordinates, gaussian_filter, median_filter  # noqa: E402
from scipy.spatial import cKDTree  # noqa: E402

DEFAULT_OUT = os.path.join(HERE, '..', 'deliver', 'Clouds')
EXR_DIR = os.path.join(HERE, 'exr')          # kept linear renders (--keep-exr), for --repost

# =============================================================================
# 1. Tileable noise textures (cached)
# =============================================================================
CACHE = os.path.join(HERE, 'cache')


def _grid01(n):
    c = (np.arange(n, dtype=np.float32) + 0.5) / n
    return np.stack(np.meshgrid(c, c, c, indexing='ij'), -1).reshape(-1, 3)


def _worley(n, cells, rng):
    """Tileable inverted Worley F1 (1 at feature points = billow centres)."""
    ii = np.stack(np.meshgrid(*[np.arange(cells)] * 3, indexing='ij'), -1).reshape(-1, 3)
    pts = (ii + rng.random(ii.shape)) / cells
    tree = cKDTree(pts, boxsize=1.0 + 1e-9)
    d, _ = tree.query(_grid01(n), k=1, workers=-1)
    return np.clip(1.0 - d * cells / 0.85, 0.0, 1.0).reshape(n, n, n).astype(np.float32)


def _perlin(n, period, rng):
    g = rng.standard_normal((period, period, period, 3)).astype(np.float32)
    g /= np.linalg.norm(g, axis=-1, keepdims=True)
    c = np.arange(n, dtype=np.float32) / n * period
    X, Y, Z = np.meshgrid(c, c, c, indexing='ij')
    xi, yi, zi = np.floor(X).astype(np.int32), np.floor(Y).astype(np.int32), np.floor(Z).astype(np.int32)
    xf, yf, zf = X - xi, Y - yi, Z - zi

    def fade(t):
        return t * t * t * (t * (t * 6 - 15) + 10)
    u, v, w = fade(xf), fade(yf), fade(zf)
    out = np.zeros_like(X)
    for dx in (0, 1):
        for dy in (0, 1):
            for dz in (0, 1):
                gg = g[(xi + dx) % period, (yi + dy) % period, (zi + dz) % period]
                dot = gg[..., 0] * (xf - dx) + gg[..., 1] * (yf - dy) + gg[..., 2] * (zf - dz)
                out += (u if dx else 1 - u) * (v if dy else 1 - v) * (w if dz else 1 - w) * dot
    return (out * 0.9 + 0.5).astype(np.float32)


def _fbm(fn, n, base, octaves, rng, gain=0.5):
    tot, amp, norm = 0, 1.0, 0
    for o in range(octaves):
        tot = tot + amp * fn(n, base * 2 ** o, rng)
        norm += amp
        amp *= gain
    return tot / norm


def _norm01(a):
    lo, hi = np.percentile(a, 0.5), np.percentile(a, 99.5)
    return np.clip((a - lo) / (hi - lo), 0, 1).astype(np.float32)


_TEX = None


def textures(n=128, seed=7):
    global _TEX
    if _TEX is not None:
        return _TEX
    os.makedirs(CACHE, exist_ok=True)
    path = os.path.join(CACHE, f'noise_{n}_{seed}.npz')
    if os.path.exists(path):
        z = np.load(path)
        _TEX = {k: z[k] for k in z.files}
        return _TEX
    rng = np.random.default_rng(seed)
    T = {}
    T['billow'] = _norm01(_fbm(_worley, n, 3, 3, rng, 0.55))
    T['billow_hi'] = _norm01(_fbm(_worley, n, 6, 3, rng, 0.55))
    T['perlin'] = _norm01(_fbm(_perlin, n, 4, 4, rng, 0.5))
    T['perlin_lo'] = _norm01(_fbm(_perlin, n, 2, 3, rng, 0.5))
    T['warp_x'] = _norm01(_fbm(_perlin, n, 2, 3, rng, 0.5))
    T['warp_y'] = _norm01(_fbm(_perlin, n, 2, 3, rng, 0.5))
    T['warp_z'] = _norm01(_fbm(_perlin, n, 2, 3, rng, 0.5))
    T['pw'] = _norm01(T['perlin'] * 0.5 + T['billow'] * 0.5)
    np.savez(path, **T)
    _TEX = T
    return T


def smp(name, P, freq, offset=(0.0, 0.0, 0.0)):
    """Sample a tileable texture at positions P (..., 3) with `freq` periods per unit."""
    tex = textures()[name]
    n = tex.shape[0]
    shp = P.shape[:-1]
    q = P.reshape(-1, 3)
    coords = [(q[:, i] * freq + offset[i]) * n - 0.5 for i in range(3)]
    return map_coordinates(tex, coords, order=1, mode='grid-wrap').reshape(shp).astype(np.float32)


def sstep(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0, 1)
    return t * t * (3 - 2 * t)


# =============================================================================
# 2. Density fields
# =============================================================================
class Grid:
    """Regular voxel grid; voxel i sits at bmin + i * vox (matches GN Volume Cube)."""

    def __init__(self, bmin, bmax, vox):
        self.vox = float(vox)
        self.bmin = np.array(bmin, np.float32)
        self.res = (np.round((np.array(bmax, np.float32) - self.bmin) / vox).astype(int) + 1)
        self.bmax = self.bmin + (self.res - 1) * self.vox
        self.xs = [self.bmin[i] + np.arange(self.res[i], dtype=np.float32) * self.vox for i in range(3)]

    def slab(self, k0, k1):
        X, Y, Z = np.meshgrid(self.xs[0], self.xs[1], self.xs[2][k0:k1], indexing='ij')
        return np.stack([X, Y, Z], -1)


def smin_into(dst, d, k):
    """Polynomial smooth union of d into dst (in place)."""
    h = np.clip(0.5 + 0.5 * (d - dst) / k, 0, 1)
    dst[...] = d * (1 - h) + dst * h - k * h * (1 - h)


def spheres_sdf(P, blobs, k):
    """Smooth union of ellipsoid blobs. blobs: list of (centre(3), radius, scale(3))."""
    sdf = np.full(P.shape[:-1], 1e3, np.float32)
    lo_z, hi_z = float(P[..., 2].min()), float(P[..., 2].max())
    x0, y0 = P[:, 0, 0, 0], P[0, :, 0, 1]
    for blob in blobs:
        c, r, s = blob[:3]
        hseg = blob[3] if len(blob) > 3 else 0.0   # vertical capsule segment below c
        ext = r * np.max(s) + 2 * k + 1
        if c[2] + ext < lo_z or c[2] - hseg - ext > hi_z:
            continue
        i0, i1 = np.searchsorted(x0, c[0] - ext), np.searchsorted(x0, c[0] + ext)
        j0, j1 = np.searchsorted(y0, c[1] - ext), np.searchsorted(y0, c[1] + ext)
        if i1 <= i0 or j1 <= j0:
            continue
        q = P[i0:i1, j0:j1] - c
        if hseg > 0:
            q = q.copy()
            q[..., 2] -= np.clip(q[..., 2], -hseg, 0.0)
        q = q / (np.array(s, np.float32) * r)
        d = (np.sqrt((q * q).sum(-1)) - 1.0) * (r * float(np.min(s)))
        sub = sdf[i0:i1, j0:j1]
        smin_into(sub, d, k)
    return sdf


def cauliflower(rng, parents, levels, n_range=(4, 8), ratio=(0.38, 0.58), up=0.9,
                zmin=0.0, embed=(0.15, 0.5), flat=1.0):
    """Recursively sprout smaller domes on the upper/outer surface of parent blobs."""
    out = []
    front = list(parents)
    for L in range(levels):
        new = []
        for blob in front:
            c, r, s = blob[:3]
            for _ in range(int(rng.integers(*n_range))):
                d = rng.standard_normal(3)
                d[2] = abs(d[2]) * up + (1 - up) * d[2] + 0.2
                d /= np.linalg.norm(d)
                rc = r * rng.uniform(*ratio)
                cc = np.array(c) + d * np.array(s) * (r - rc * rng.uniform(*embed))
                if cc[2] - rc * 0.55 * flat < zmin:
                    continue
                new.append((cc.astype(np.float32), rc, s))
        out += new
        front = new
    return out


def evaluate(grid, fn, chunk=24):
    """Evaluate density fn(P)->dens slab by slab (bounded memory)."""
    out = np.zeros(tuple(grid.res), np.float32)
    for k0 in range(0, grid.res[2], chunk):
        k1 = min(grid.res[2], k0 + chunk)
        out[:, :, k0:k1] = fn(grid.slab(k0, k1))
    return out


def warp(P, amp, freq):
    W = np.stack([smp('warp_x', P, freq), smp('warp_y', P, freq), smp('warp_z', P, freq)], -1) - 0.5
    return P + W * amp


def cumulus_field(blobs, K, base_z, top_z, edge, disp, fringe, warp_amp, warp_freq,
                  bill_f=1 / 30.0, bill_hi_f=1 / 12.0, fuzz_f=1 / 6.0, seed_off=(0, 0, 0),
                  base_soft=1.0, wisp_amt=0.12):
    """Returns a density function for cumulus-type clouds (0..1)."""
    off = np.array(seed_off, np.float32)

    def fn(P):
        Pw = warp(P + off, warp_amp, warp_freq) - off
        sdf = spheres_sdf(Pw, blobs, K)
        z = Pw[..., 2]
        h = np.clip((z - base_z) / (top_z - base_z), 0, 1)
        # flat condensation base, slightly ragged
        bz = base_z + (smp('perlin', P + off, 1 / 40.0) - 0.5) * 2.5 * base_soft
        sdf = np.maximum(sdf, bz - z)
        b = smp('billow', Pw + off, bill_f)
        b2 = smp('billow_hi', Pw + off, bill_hi_f)
        pf = smp('perlin', Pw + off, fuzz_f)
        up = sstep(0.0, 0.35, h)            # cauliflower grows with height
        dsp = (disp[0] * (0.55 - b) * (0.35 + 0.65 * up)
               + disp[1] * (0.55 - b2) * (0.25 + 0.75 * up)
               + disp[2] * (0.5 - pf))
        sd = sdf + dsp
        e = edge * (1.0 + 1.5 * (1 - up))   # crisper edges on top, softer near base
        dens = np.clip(0.5 - sd / (2 * e), 0, 1)
        dens = dens * dens * (3 - 2 * dens)
        if wisp_amt > 0:
            fr = np.clip((smp('perlin', (Pw + off) * np.array([1, 1, 2.2], np.float32), 1 / 9.0) - 0.47) * 3.0, 0, 1)
            fr_w = np.exp(-np.maximum(sd, 0) / fringe) * (sd > 0)
            dens = np.maximum(dens, fr * fr_w * wisp_amt)
        return dens
    return fn


# =============================================================================
# 3. Lighting presets (sun lamp + gradient sky world)
# =============================================================================
# Sun azimuth is measured from the camera's forward axis (+Y) toward +X:
# az 0 = sun straight behind the cloud (back-lit), 90 = from the right, 180 = behind camera.
PRESETS = {
    # verify pass: dawn sky fill x3 (0.75 -> 2.3), bluer zenith / anti-sun horizon / ground,
    # sun 30 -> 26: shadow sides were muddy mauve-brown (median body pixel ~ (70,51,63));
    # now cool blue-lavender and the whole cloud reads luminous.
    'dawn': dict(
        sun_el=7.0, sun_az=84.0, sun_col=(1.00, 0.64, 0.38), sun_E=26.0, sun_angle=0.55,
        zenith=(0.040, 0.120, 0.520), hz_sun=(1.00, 0.56, 0.34), hz_anti=(0.36, 0.30, 0.66),
        ground=(0.22, 0.22, 0.30), glow=(1.00, 0.60, 0.34), glow_k=9.0, glow_E=1.4,
        sky_E=2.3, exposure=-1.1, view='Khronos PBR Neutral', look='None',
        sheet_top=(66, 104, 168), sheet_bottom=(236, 176, 150)),
    'dusk': dict(
        sun_el=3.0, sun_az=72.0, sun_col=(1.00, 0.40, 0.26), sun_E=26.0, sun_angle=0.55,
        zenith=(0.060, 0.050, 0.300), hz_sun=(1.00, 0.40, 0.30), hz_anti=(0.34, 0.18, 0.52),
        ground=(0.16, 0.10, 0.20), glow=(1.00, 0.40, 0.28), glow_k=8.0, glow_E=1.6,
        sky_E=0.95, exposure=-1.1, view='Khronos PBR Neutral', look='None',
        sheet_top=(40, 36, 96), sheet_bottom=(212, 120, 124)),
    'moon': dict(
        sun_el=26.0, sun_az=55.0, sun_col=(0.60, 0.74, 1.00), sun_E=7.0, sun_angle=0.55,
        zenith=(0.006, 0.010, 0.032), hz_sun=(0.030, 0.042, 0.085), hz_anti=(0.016, 0.022, 0.050),
        ground=(0.030, 0.040, 0.075), glow=(0.40, 0.52, 0.85), glow_k=14.0, glow_E=0.5,
        sky_E=0.9, exposure=-0.85, view='Khronos PBR Neutral', look='None',
        sheet_top=(4, 7, 18), sheet_bottom=(20, 28, 52)),
}


def _set_enum(obj, prop, *cands):
    for c in cands:
        try:
            setattr(obj, prop, c)
            return c
        except (TypeError, ValueError):
            continue
    return None


def sun_dir(p):
    el, az = math.radians(p['sun_el']), math.radians(p['sun_az'])
    return Vector((math.cos(el) * math.sin(az), math.cos(el) * math.cos(az), math.sin(el)))


def build_world(p):
    w = bpy.data.worlds.new('Sky_' + str(id(p)))
    bpy.context.scene.world = w
    nt = w.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputWorld')
    bg = N('ShaderNodeBackground')
    tc = N('ShaderNodeTexCoord')
    sd = sun_dir(p)
    sep = N('ShaderNodeSeparateXYZ'); L(tc.outputs['Generated'], sep.inputs[0])
    hsun = Vector((sd.x, sd.y, 0)).normalized()
    dot_h = N('ShaderNodeVectorMath'); dot_h.operation = 'DOT_PRODUCT'
    L(tc.outputs['Generated'], dot_h.inputs[0]); dot_h.inputs[1].default_value = tuple(hsun)
    dot_s = N('ShaderNodeVectorMath'); dot_s.operation = 'DOT_PRODUCT'
    L(tc.outputs['Generated'], dot_s.inputs[0]); dot_s.inputs[1].default_value = tuple(sd)

    def mr(v, a, b, c=0.0, d=1.0):
        n = N('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        n.inputs['From Min'].default_value = a; n.inputs['From Max'].default_value = b
        n.inputs['To Min'].default_value = c; n.inputs['To Max'].default_value = d
        L(v, n.inputs['Value'])
        return n.outputs['Result']

    def mix(f, a, b):
        n = N('ShaderNodeMix'); n.data_type = 'RGBA'; n.clamp_factor = True
        L(f, n.inputs['Factor'])
        for sock, v in (('A', a), ('B', b)):
            if isinstance(v, (tuple, list)):
                n.inputs[sock].default_value = (*v, 1.0)
            else:
                L(v, n.inputs[sock])
        return n.outputs['Result']
    horizon = mix(mr(dot_h.outputs['Value'], -0.9, 1.0), p['hz_anti'], p['hz_sun'])
    up = sep.outputs['Z']
    sky = mix(mr(up, 0.0, 0.55), horizon, p['zenith'])
    lower = mix(mr(up, 0.0, -0.35), horizon, p['ground'])
    col = mix(mr(up, -0.02, 0.02), lower, sky)
    # aureole around the sun: exp(k * (cos - 1))
    e1 = N('ShaderNodeMath'); e1.operation = 'SUBTRACT'; L(dot_s.outputs['Value'], e1.inputs[0]); e1.inputs[1].default_value = 1.0
    e2 = N('ShaderNodeMath'); e2.operation = 'MULTIPLY'; L(e1.outputs[0], e2.inputs[0]); e2.inputs[1].default_value = p['glow_k']
    e3 = N('ShaderNodeMath'); e3.operation = 'EXPONENT'; L(e2.outputs[0], e3.inputs[0])
    e4 = N('ShaderNodeMath'); e4.operation = 'MULTIPLY'; L(e3.outputs[0], e4.inputs[0]); e4.inputs[1].default_value = p['glow_E']
    gl = N('ShaderNodeVectorMath'); gl.operation = 'SCALE'; gl.inputs[0].default_value = tuple(p['glow'])
    L(e4.outputs[0], gl.inputs['Scale'])
    add = N('ShaderNodeVectorMath'); add.operation = 'ADD'; L(col, add.inputs[0]); L(gl.outputs[0], add.inputs[1])
    L(add.outputs[0], bg.inputs['Color'])
    bg.inputs['Strength'].default_value = p['sky_E']
    L(bg.outputs[0], out.inputs['Surface'])
    return w


def build_sun(p):
    ld = bpy.data.lights.new('Sun', 'SUN')
    ld.energy = p['sun_E']
    ld.color = tuple(p['sun_col'])
    ld.angle = math.radians(p['sun_angle'])
    ob = bpy.data.objects.new('Sun', ld)
    bpy.context.scene.collection.objects.link(ob)
    ob.rotation_euler = (-sun_dir(p)).to_track_quat('-Z', 'Y').to_euler()
    return ob


def sky_np(p, dirs):
    """numpy mirror of build_world(): scene-linear sky radiance for unit directions (..., 3)."""
    sd = np.array(sun_dir(p), np.float32)
    hs = np.array([sd[0], sd[1], 0.0], np.float32); hs /= np.linalg.norm(hs)
    d = dirs.astype(np.float32)
    up = d[..., 2:3]

    def c(k):
        return np.array(p[k], np.float32)
    horizon = c('hz_anti') + (c('hz_sun') - c('hz_anti')) * sstep(-0.9, 1.0, (d @ hs))[..., None]
    sky = horizon + (c('zenith') - horizon) * sstep(0.0, 0.55, up)
    lower = horizon + (c('ground') - horizon) * sstep(0.0, -0.35, up)
    col = lower + (sky - lower) * sstep(-0.02, 0.02, up)
    col = col + c('glow') * p['glow_E'] * np.exp(p['glow_k'] * ((d @ sd)[..., None] - 1.0))
    return col * p['sky_E']


# =============================================================================
# 4. Blender volume import, material, camera, render
# =============================================================================
def import_density(name, dens, grid, mat):
    nx, ny, nz = dens.shape
    me = bpy.data.meshes.new(name)
    me.vertices.add(nx * ny * nz)
    at = me.attributes.new('density', 'FLOAT', 'POINT')
    at.data.foreach_set('value', np.ascontiguousarray(dens.ravel(order='F')))
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ng = bpy.data.node_groups.new(name + '_ToVolume', 'GeometryNodeTree')
    ng.interface.new_socket('Geometry', in_out='INPUT', socket_type='NodeSocketGeometry')
    ng.interface.new_socket('Geometry', in_out='OUTPUT', socket_type='NodeSocketGeometry')
    N, L = ng.nodes.new, ng.links.new
    gi, go = N('NodeGroupInput'), N('NodeGroupOutput')
    pos = N('GeometryNodeInputPosition')
    sub = N('ShaderNodeVectorMath'); sub.operation = 'SUBTRACT'; sub.inputs[1].default_value = tuple(grid.bmin)
    L(pos.outputs[0], sub.inputs[0])
    div = N('ShaderNodeVectorMath'); div.operation = 'DIVIDE'; div.inputs[1].default_value = (grid.vox,) * 3
    L(sub.outputs[0], div.inputs[0])
    sep = N('ShaderNodeSeparateXYZ'); L(div.outputs[0], sep.inputs[0])
    ints = []
    for ax in 'XYZ':
        f2i = N('FunctionNodeFloatToInt'); f2i.rounding_mode = 'ROUND'
        L(sep.outputs[ax], f2i.inputs[0]); ints.append(f2i.outputs[0])
    m1 = N('FunctionNodeIntegerMath'); m1.operation = 'MULTIPLY_ADD'
    L(ints[2], m1.inputs[0]); m1.inputs[1].default_value = int(ny); L(ints[1], m1.inputs[2])
    m2 = N('FunctionNodeIntegerMath'); m2.operation = 'MULTIPLY_ADD'
    L(m1.outputs[0], m2.inputs[0]); m2.inputs[1].default_value = int(nx); L(ints[0], m2.inputs[2])
    na = N('GeometryNodeInputNamedAttribute'); na.data_type = 'FLOAT'; na.inputs['Name'].default_value = 'density'
    si = N('GeometryNodeSampleIndex'); si.data_type = 'FLOAT'; si.domain = 'POINT'
    L(gi.outputs[0], si.inputs['Geometry']); L(na.outputs['Attribute'], si.inputs['Value']); L(m2.outputs[0], si.inputs['Index'])
    vc = N('GeometryNodeVolumeCube')
    L(si.outputs[0], vc.inputs['Density'])
    vc.inputs['Min'].default_value = tuple(grid.bmin); vc.inputs['Max'].default_value = tuple(grid.bmax)
    vc.inputs['Resolution X'].default_value = int(nx)
    vc.inputs['Resolution Y'].default_value = int(ny)
    vc.inputs['Resolution Z'].default_value = int(nz)
    sm = N('GeometryNodeSetMaterial'); sm.inputs['Material'].default_value = mat
    L(vc.outputs[0], sm.inputs['Geometry']); L(sm.outputs[0], go.inputs[0])
    ob.modifiers.new('ToVolume', 'NODES').node_group = ng
    ob.data.materials.append(mat)
    return ob


def cloud_material(sigma, anisotropy=0.55, albedo=1.0):
    """Principled Volume, density = attribute * sigma (1/m in cloud units)."""
    mat = bpy.data.materials.new('CloudVolume')
    nt = mat.node_tree
    nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    attr = N('ShaderNodeAttribute'); attr.attribute_name = 'density'
    mul = N('ShaderNodeMath'); mul.operation = 'MULTIPLY'; mul.inputs[1].default_value = sigma
    L(attr.outputs['Fac'], mul.inputs[0])
    pv = N('ShaderNodeVolumePrincipled')
    pv.inputs['Color'].default_value = (albedo, albedo, albedo, 1)
    pv.inputs['Anisotropy'].default_value = anisotropy
    L(mul.outputs[0], pv.inputs['Density'])
    L(pv.outputs[0], out.inputs['Volume'])
    return mat


def occupied_points(dens, grid, thr=0.03, n=40000, seed=0):
    idx = np.argwhere(dens > thr)
    if len(idx) > n:
        idx = idx[np.random.default_rng(seed).choice(len(idx), n, replace=False)]
    return grid.bmin + idx.astype(np.float32) * grid.vox


def frame_camera(pts, res, yaw=0.0, pitch=0.0, lens=50.0, fill=0.84, center_bias=(0.0, 0.0)):
    """Perspective camera looking along +Y (rotated by yaw/pitch) that fits pts
    inside `fill` of the frame, centred."""
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('Cam')
    cd.lens = lens
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = 36.0
    cd.clip_start = 0.5
    cd.clip_end = 1e5
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    aspect = res[0] / res[1]
    tx = 18.0 / lens
    ty = tx / aspect
    yw, pt = math.radians(yaw), math.radians(pitch)
    fwd = np.array([math.sin(yw) * math.cos(pt), math.cos(yw) * math.cos(pt), math.sin(pt)])
    right = np.array([math.cos(yw), -math.sin(yw), 0.0])
    upv = np.cross(right, fwd)
    tgt = pts.mean(0)
    D = 1.0
    for _ in range(6):
        rel = pts - tgt
        x, y, z = rel @ right, rel @ upv, rel @ fwd
        lo, hi = 1.0, 1e5
        for _ in range(60):
            D = 0.5 * (lo + hi)
            depth = D + z
            ok = depth.min() > 1 and np.abs(x / depth).max() <= tx * fill and np.abs(y / depth).max() <= ty * fill
            if ok:
                hi = D
            else:
                lo = D
        D = hi
        depth = D + z
        u, v = x / depth, y / depth
        du = 0.5 * (u.max() + u.min()) + center_bias[0] * tx
        dv = 0.5 * (v.max() + v.min()) + center_bias[1] * ty
        tgt = tgt + right * du * D + upv * dv * D
    loc = tgt - fwd * D
    cam.location = Vector(loc)
    cam.rotation_euler = Vector(fwd).to_track_quat('-Z', 'Y').to_euler()
    return cam


def place_camera(loc, pitch, lens):
    sc = bpy.context.scene
    cd = bpy.data.cameras.new('Cam')
    cd.lens = lens
    cd.sensor_fit = 'HORIZONTAL'
    cd.sensor_width = 36.0
    cd.clip_start = 0.5
    cd.clip_end = 1e5
    cam = bpy.data.objects.new('Cam', cd)
    sc.collection.objects.link(cam)
    sc.camera = cam
    pt = math.radians(pitch)
    cam.location = Vector(loc)
    cam.rotation_euler = Vector((0.0, math.cos(pt), math.sin(pt))).to_track_quat('-Z', 'Y').to_euler()
    return cam


def camera_rays(cam, w, h):
    """World-space unit ray directions (h, w, 3) for a horizontal-fit perspective camera."""
    tx = 18.0 / cam.data.lens
    ty = tx * h / w
    u = ((np.arange(w) + 0.5) / w * 2 - 1) * tx
    v = (1 - (np.arange(h) + 0.5) / h * 2) * ty
    U, V = np.meshgrid(u, v)
    m = np.array(cam.matrix_world.to_3x3(), np.float32)
    local = np.stack([U, V, -np.ones_like(U)], -1).astype(np.float32)
    d = local @ m.T
    return d / np.linalg.norm(d, axis=-1, keepdims=True)


def setup_render(res, samples, p, vol_bounces=24):
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.device = 'CPU'
    sc.cycles.samples = samples
    sc.cycles.use_adaptive_sampling = True
    sc.cycles.adaptive_threshold = 0.02
    sc.cycles.use_denoising = True
    _set_enum(sc.cycles, 'denoiser', 'OPENIMAGEDENOISE')
    _set_enum(sc.cycles, 'denoising_input_passes', 'RGB_ALBEDO')
    _set_enum(sc.cycles, 'denoising_prefilter', 'ACCURATE')
    sc.cycles.max_bounces = vol_bounces + 8
    sc.cycles.volume_bounces = vol_bounces
    sc.cycles.diffuse_bounces = 2
    sc.cycles.glossy_bounces = 0
    sc.cycles.transmission_bounces = 0
    sc.cycles.transparent_max_bounces = 8
    sc.cycles.sample_clamp_indirect = 20.0
    sc.render.film_transparent = True
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = 'OPEN_EXR'
    sc.render.image_settings.color_mode = 'RGBA'
    sc.render.image_settings.color_depth = '32'
    _set_enum(sc.view_settings, 'view_transform', p.get('view', 'AgX'))
    _set_enum(sc.view_settings, 'look', p['look'], 'None')
    sc.view_settings.exposure = p['exposure']
    sc.view_settings.gamma = 1.0
    try:
        sc.display_settings.display_device = 'sRGB'
    except TypeError:
        pass
    return sc


# =============================================================================
# 5. Post: premultiplied linear EXR -> straight-alpha, fringe-free, AgX PNG
# =============================================================================
def load_float_image(path):
    img = bpy.data.images.load(path)
    w, h = img.size
    px = np.empty(w * h * 4, np.float32)
    img.pixels.foreach_get(px)
    bpy.data.images.remove(img)
    return px.reshape(h, w, 4)[::-1].copy()  # top row first


def _down(a):
    h, w = a.shape[:2]
    h2, w2 = h // 2 * 2, w // 2 * 2
    a = a[:h2, :w2]
    return a.reshape(h2 // 2, 2, w2 // 2, 2, *a.shape[2:]).mean((1, 3))


def _up(a, shape):
    from scipy.ndimage import zoom
    fy, fx = shape[0] / a.shape[0], shape[1] / a.shape[1]
    return zoom(a, (fy, fx, 1), order=1)[:shape[0], :shape[1]] if a.ndim == 3 else zoom(a, (fy, fx), order=1)


def push_pull_colour(prem, a, conf=0.03):
    """Straight colour everywhere: own colour where alpha is trustworthy, colour
    pulled in from the nearest cloud pixels elsewhere (so edges never go dark)."""
    levels = []
    P, A = prem, a
    while min(A.shape) > 8:
        levels.append((P, A))
        P, A = _down(P), _down(A)
    C = np.broadcast_to(P.reshape(-1, 3).sum(0) / max(A.sum(), 1e-8), P.shape).copy()
    for P, A in [(P, A)] + list(reversed(levels)):
        Cu = _up(C, P.shape) if C.shape != P.shape else C
        wgt = np.clip(A / conf, 0, 1)[..., None]
        C = P / np.maximum(A, 1e-6)[..., None] * wgt + Cu * (1 - wgt)
    return C


def tonemap(straight, tmp_path):
    """Apply the scene's view transform (AgX + look + exposure) to scene-linear RGB."""
    sc = bpy.context.scene
    h, w, _ = straight.shape
    img = bpy.data.images.new('tm', w, h, alpha=True, float_buffer=True)
    img.colorspace_settings.name = 'Linear Rec.709'
    px = np.concatenate([straight, np.ones((h, w, 1), np.float32)], -1)[::-1]
    img.pixels.foreach_set(np.ascontiguousarray(px, np.float32).ravel())
    s = sc.render.image_settings
    s.file_format = 'PNG'; s.color_mode = 'RGB'; s.color_depth = '16'
    img.save_render(tmp_path, scene=sc)
    bpy.data.images.remove(img)
    t = bpy.data.images.load(tmp_path)
    t.colorspace_settings.name = 'Non-Color'   # read back the display-encoded values as-is
    out = np.empty(w * h * 4, np.float32)
    t.pixels.foreach_get(out)
    bpy.data.images.remove(t)
    os.remove(tmp_path)
    return out.reshape(h, w, 4)[::-1, :, :3].copy()


def write_rgba(path, rgb, alpha, seed=0):
    """8-bit straight-alpha PNG with light triangular dither (no banding in soft gradients)."""
    from PIL import Image
    rng = np.random.default_rng(seed)
    d = (rng.random(rgb.shape[:2] + (1,)) - rng.random(rgb.shape[:2] + (1,))).astype(np.float32)
    c = np.clip(rgb * 255 + 0.5 + d * 0.5, 0, 255).astype(np.uint8)
    a = np.clip(alpha * 255 + 0.5 + d[..., 0] * 0.5, 0, 255).astype(np.uint8)
    a[alpha < 1.5 / 255] = 0
    Image.fromarray(np.dstack([c, a]), 'RGBA').save(path, optimize=True)


def _box(x, r):
    from scipy.ndimage import uniform_filter
    return uniform_filter(x, size=2 * r + 1, mode='reflect')


def guided_alpha(prem, a, r=4, eps=2e-4, a_guide=1.0):
    """Guided filter (He et al. 2010) of the alpha channel. Guide = the OIDN-denoised
    premultiplied colour (normalised to its 99th percentile) plus a lightly smoothed
    alpha, so silhouettes of near-black cloud bodies (moon backlight) stay crisp too."""
    solid = a > 0.5
    s = float(np.percentile(prem.max(-1)[solid], 99)) if solid.any() else 1.0
    ga = gaussian_filter(a, 0.8) * a_guide
    I = np.concatenate([prem / max(s, 1e-6), ga[..., None]], -1).astype(np.float64)
    n = I.shape[-1]
    p = a.astype(np.float64)
    mI = [_box(I[..., i], r) for i in range(n)]
    mp = _box(p, r)
    cIp = np.stack([_box(I[..., i] * p, r) - mI[i] * mp for i in range(n)], -1)
    S = np.empty(a.shape + (n, n))
    for i in range(n):
        for j in range(i, n):
            v = _box(I[..., i] * I[..., j], r) - mI[i] * mI[j]
            S[..., i, j] = v
            S[..., j, i] = v
    S += eps * np.eye(n)
    A = np.linalg.solve(S, cIp[..., None])[..., 0]
    B = mp - (A * np.stack(mI, -1)).sum(-1)
    q = sum(_box(A[..., i], r) * I[..., i] for i in range(n)) + _box(B, r)
    return np.clip(q, 0, 1).astype(np.float32)


ERODE = (1.4, 0.45, 5.0)   # strip-end break-up: taper gain, brightness weight, brightness blur (px)


def postprocess(exr_path, png_path, alpha_floor=0.004, haze=None, p=None, cam=None, side_taper=0.0,
                bottom_taper=0.0):
    raw = load_float_image(exr_path)
    prem, a = raw[..., :3], np.clip(raw[..., 3], 0, 1)
    h, w = a.shape
    if haze and cam is not None:
        # aerial perspective: blend toward the preset's sky radiance along each pixel's ray,
        # by the distance to the deck top plane (far cloud-sea melts into the horizon haze)
        d = camera_rays(cam, w, h)
        cz = float(cam.location.z)
        t = np.where(d[..., 2] < -1e-4, (haze['plane_z'] - cz) / np.minimum(d[..., 2], -1e-4), 1e9)
        f = (1 - np.exp(-np.maximum(t - haze['start'], 0) / haze['length'])) * haze['max']
        dh = d.copy(); dh[..., 2] = np.maximum(dh[..., 2], 0.0)
        dh /= np.linalg.norm(dh, axis=-1, keepdims=True)
        skyc = sky_np(p, dh)
        prem = prem * (1 - f[..., None]) + skyc * a[..., None] * f[..., None]
    if side_taper > 0 or bottom_taper > 0:
        # strip ends / bottom: the deck breaks up instead of a geometric vignette.
        # (verify pass: the plain smoothstep product read as a rounded-rectangle photo
        # pasted on the sky, very visibly on the bright moonlit strips.) Dark gaps between
        # clouds go transparent first, lit tops survive longest, so the fade follows the
        # clouds' own shapes. t = the old geometric taper, L = local brightness 0..1.
        x = (np.arange(w) + 0.5) / w
        y = (np.arange(h) + 0.5) / h
        tx = sstep(0.0, side_taper, x) * sstep(1.0, 1.0 - side_taper, x) if side_taper > 0 else np.ones(w)
        ty = sstep(1.0, 1.0 - bottom_taper, y) if bottom_taper > 0 else np.ones(h)
        t = ty[:, None] * tx[None, :]
        lum = np.maximum(prem, 0) @ np.array([0.2126, 0.7152, 0.0722], np.float32)
        Ls = gaussian_filter(lum, ERODE[2]) / np.maximum(gaussian_filter(a, ERODE[2]), 1e-4)
        # brightness relative to the neighbourhood (so the darker, back-lit sun-side end
        # is not eroded as a block): local tops -> 1, local gaps -> 0
        big = gaussian_filter(Ls * a, 40.0) / np.maximum(gaussian_filter(a, 40.0), 1e-4)
        L = np.clip(Ls / np.maximum(1.5 * big, 1e-6), 0, 1)
        tp = sstep(0.0, 1.0, t * ERODE[0] - ERODE[1] * (1.0 - L)).astype(np.float32)
        a = a * tp
        prem = prem * tp[..., None]
    prem = np.maximum(prem, 0)
    # thin fringes: the colour is OIDN-denoised but Cycles' alpha (a stochastic
    # transmittance estimate) is not, so semi-transparent areas (Wisp veils, flat
    # bases) showed grain / speckle. prem = C * a with C slowly varying, so alpha is
    # locally an affine function of the denoised colour: a colour-guided filter
    # regresses the noisy alpha on it. Crisp silhouettes survive (the guide has the
    # same edge), grain goes, colour and coverage stay consistent.
    # (verify pass: replaces the earlier median + blur of the low-alpha range, which
    # left visible grain inside the Wisp's half-transparent areas)
    a_g = guided_alpha(prem, median_filter(a, size=3), r=4, eps=2e-4)
    w = sstep(0.97, 0.995, np.minimum(a, a_g))      # keep the rendered alpha only in solid cores
    a = a * w + a_g * (1 - w)
    straight = push_pull_colour(prem, np.maximum(a, 1e-8), conf=0.03)
    # faint side-lit veils are physically dim (single scattering only) and read as
    # brown smoke on a night sky; lift them toward the colour of the nearby body
    # (never darken: silver-lining rims that are brighter than the body stay).
    nb = push_pull_colour(prem, np.maximum(a, 1e-8), conf=0.6)
    lift = (1 - sstep(0.12, 0.55, a))[..., None]
    straight = straight * (1 - lift) + np.maximum(straight, nb * 0.85) * lift
    a = np.clip((a - alpha_floor) / (1 - alpha_floor), 0, 1)
    disp = tonemap(straight, png_path + '.tmp.png')
    write_rgba(png_path, disp, a)
    return disp, a


# =============================================================================
# 6. Cloud shapes
# =============================================================================
def tower_blobs(rng, towers, base_z=0.0, levels=2, n_range=(4, 8), ratio=(0.38, 0.58)):
    """towers: (x, y, top_z, radius). Each tower is a column of blobs capped by a
    dome that sprouts cauliflower turrets."""
    blobs, domes = [], []
    for x, y, top, r in towers:
        z = base_z + r * 0.55
        while True:
            zc = min(z, top - r)
            jit = rng.normal(0, r * 0.07, 2)
            b = (np.array([x + jit[0], y + jit[1], zc], np.float32), r * rng.uniform(0.92, 1.04), (1.0, 1.0, 1.0))
            blobs.append(b)
            if zc >= top - r - 1e-3:
                domes.append(b)
                break
            if zc > base_z + r:
                domes.append((b[0], b[1] * 0.9, b[2]))
            z += r * 0.62
    # low flattened skirt joining the towers along the base
    xs = np.array([t[0] for t in towers]); rs = np.array([t[3] for t in towers])
    for x, y, top, r in towers:
        blobs.append((np.array([x, y, base_z + r * 0.35], np.float32), r * 1.05, (1.35, 1.15, 0.5)))
    blobs += cauliflower(rng, domes, levels, n_range=n_range, ratio=ratio, zmin=base_z + 1.0)
    return blobs


def mound_blobs(rng, masses, levels=3, n_range=(5, 9), ratio=(0.40, 0.60), up=0.75,
                embed=(0.3, 0.6), base_z=0.0, skirt=0.82):
    """masses: (x, y, z, R) main bodies; hierarchical rounded bulges grow on their
    upper surface (cauliflower), level by level."""
    parents = [(np.array(m[:3], np.float32), m[3], (1.0, 1.0, 1.0)) for m in masses]
    # vertical capsule skirts: straight sides down to the flat base (no round 'belly')
    low = [(c, r, s) for c, r, s in parents if float(c[2]) - base_z < 1.6 * r]   # bodies near the base
    skirts = [(c, r * skirt, s, max(0.0, float(c[2]) - base_z - r * 0.3)) for c, r, s in low]
    # one continuous lower body: flattened ellipsoids under the low masses, so the base
    # reads as a single flat-bottomed deck the turrets rise from
    slab = [(np.array([c[0], c[1], base_z + r * 0.25], np.float32), r * 0.95, (1.05, 1.0, 0.45))
            for c, r, s in low]
    return slab + skirts + parents + cauliflower(rng, parents, levels, n_range=n_range, ratio=ratio, up=up,
                                 embed=embed, zmin=base_z + 0.5)


def shape_cumulus(q):
    """Fair-weather cumulus (mediocris): flat base, one main dome, shoulders."""
    rng = np.random.default_rng(11)
    masses = [(-6, 0, 26, 20), (-26, 3, 16, 14), (15, -2, 20, 16), (32, 3, 12, 11), (-41, -1, 9, 9),
              (4, 12, 15, 13), (-14, -12, 13, 12), (22, 10, 10, 10)]
    blobs = mound_blobs(rng, masses, levels=3, n_range=(3, 6), ratio=(0.35, 0.55))
    grid = Grid((-68, -44, -4), (72, 44, 76), 0.40 / q)
    fn = cumulus_field(blobs, K=1.4, base_z=0.0, top_z=60.0, edge=0.5, disp=(4.0, 0.8, 0.4),
                       fringe=2.5, warp_amp=5.0, warp_freq=1 / 90.0)
    return grid, fn, dict(res=(1024, 1024), yaw=0.0, pitch=-3.0, lens=50.0, fill=0.84, sigma=2.2)


def shape_congestus(q):
    """Towering cumulus (congestus): a broad flat-based deck of shoulders, a stepped
    multi-turret main tower (widest mid-way, no neck), a lower secondary tower.
    (verify pass: the earlier version put a head wider than its neck on the tower and
    read as a sitting teddy bear.)"""
    rng = np.random.default_rng(23)
    masses = [(-30, 3, 14, 15), (27, -3, 15, 16), (46, 2, 9, 10), (-48, 0, 8, 8.5), (6, 16, 14, 14),
              (-10, -16, 13, 13), (0, 0, 20, 23), (-14, 8, 26, 17), (16, -6, 28, 18)]
    # main tower: leaning slightly right, broad, radius shrinks slowly; several masses per level
    ax, ay = 2.0, 0.0
    for z, r in [(36, 21), (48, 20), (60, 18.5), (71, 17), (81, 15.5)]:
        ax += rng.uniform(0.8, 2.2); ay += rng.uniform(-1.0, 1.0)
        for k in range(4):
            ang = rng.uniform(0, 2 * math.pi)
            off = r * rng.uniform(0.25, 0.55)
            masses.append((ax + off * math.cos(ang), ay + off * math.sin(ang) * 0.8, z + rng.uniform(-3, 3),
                           r * rng.uniform(0.72, 0.9)))
    # crown: domes of different heights INSIDE the tower's width (no head wider than the neck)
    masses += [(ax - 7, ay + 2, 88, 12.5), (ax + 6, ay - 3, 92, 13.5), (ax + 13, ay + 3, 84, 10.5),
               (ax - 13, ay - 2, 81, 10.0), (ax + 1, ay + 6, 86, 11.0)]
    # secondary tower on the left, lower (stepped skyline)
    bx, by = -28.0, 2.0
    for z, r in [(30, 15), (41, 13.5), (51, 12)]:
        bx += rng.uniform(-1.0, 0.6)
        for k in range(3):
            ang = rng.uniform(0, 2 * math.pi)
            off = r * rng.uniform(0.2, 0.5)
            masses.append((bx + off * math.cos(ang), by + off * math.sin(ang) * 0.8, z + rng.uniform(-3, 3),
                           r * rng.uniform(0.72, 0.92)))
    masses.append((bx + 2, by, 58, 10.5))
    # small turret on the right shoulder
    masses += [(38, 0, 30, 11), (40, 2, 39, 8.5)]
    blobs = mound_blobs(rng, masses, levels=3, n_range=(3, 6), ratio=(0.35, 0.55), up=0.7)
    grid = Grid((-66, -46, -6), (72, 46, 118), 0.46 / q)
    fn = cumulus_field(blobs, K=1.6, base_z=0.0, top_z=100.0, edge=0.55, disp=(4.5, 0.9, 0.4),
                       fringe=2.5, warp_amp=6.0, warp_freq=1 / 100.0, seed_off=(0.31, 0.17, 0.05))
    return grid, fn, dict(res=(1024, 1024), yaw=0.0, pitch=0.0, lens=50.0, fill=0.86, sigma=2.2)


def shape_puff(q):
    """Small young cumulus humilis: close-range card for drifting past the windows."""
    rng = np.random.default_rng(5)
    masses = [(0, 0, 8, 10), (-12, 2, 6, 8), (11, -1, 6.5, 8.5), (4, 8, 5, 7), (-5, -8, 5, 7), (20, 2, 4, 5.5),
              (-20, -1, 4, 5)]
    blobs = mound_blobs(rng, masses, levels=3, n_range=(3, 6), ratio=(0.35, 0.55))
    grid = Grid((-32, -22, -3), (32, 22, 30), 0.17 / q)
    fn = cumulus_field(blobs, K=0.8, base_z=0.0, top_z=20.0, edge=0.3, disp=(1.8, 0.45, 0.18),
                       fringe=1.2, warp_amp=2.5, warp_freq=1 / 40.0, bill_f=1 / 13.0, bill_hi_f=1 / 5.0,
                       fuzz_f=1 / 2.5, seed_off=(0.5, 0.2, 0.7), wisp_amt=0.16)
    return grid, fn, dict(res=(1024, 1024), yaw=0.0, pitch=-4.0, lens=50.0, fill=0.84, sigma=4.8)


def shape_bank(q):
    """A long bank of merged cumuli on one base, uneven heights, two dominant domes."""
    rng = np.random.default_rng(31)
    masses = [(-48, 0, 26, 21), (52, 3, 30, 23), (-5, -4, 18, 16)]
    x = -118.0
    while x < 118:
        env = math.cos(x / 125.0 * math.pi / 2) ** 0.8
        R = rng.uniform(9, 16) * (0.55 + 0.45 * env)
        z = R * rng.uniform(0.6, 1.1) + 10 * env * rng.uniform(0.2, 1.0)
        masses.append((x, rng.uniform(-10, 10), z, R))
        if rng.random() < 0.55:
            masses.append((x + rng.uniform(-6, 6), rng.uniform(-22, 22), R * 0.7, R * 0.8))
        x += R * rng.uniform(1.0, 1.4)
    blobs = mound_blobs(rng, masses, levels=3, n_range=(3, 6), ratio=(0.35, 0.55), skirt=0.95)
    grid = Grid((-140, -46, -4), (140, 46, 80), 0.55 / q)
    fn = cumulus_field(blobs, K=2.4, base_z=0.0, top_z=55.0, edge=0.55, disp=(4.5, 0.9, 0.4),
                       fringe=2.5, warp_amp=7.0, warp_freq=1 / 110.0, seed_off=(0.11, 0.61, 0.33))
    return grid, fn, dict(res=(2048, 1024), yaw=0.0, pitch=-3.0, lens=50.0, fill=0.9, sigma=2.0)


def layer_masses(rng, x0, x1, y0, y1, cell, rmin, rmax, zc, coverage_freq, coverage_thr, taper=None):
    """Jittered field of flattened masses for sheet clouds; a low-frequency 2D
    coverage noise opens gaps (cells) in the sheet."""
    out = []
    for gx in np.arange(x0, x1, cell):
        for gy in np.arange(y0, y1, cell):
            x, y = gx + rng.uniform(0, cell), gy + rng.uniform(0, cell)
            P = np.array([[[[x, y, 0.0]]]], np.float32)
            cov = float(smp('perlin_lo', P, coverage_freq)[0, 0, 0])
            t = taper(x, y) if taper else 1.0
            if cov * t < coverage_thr:
                continue
            k = np.clip((cov * t - coverage_thr) / 0.25, 0.25, 1.0)
            R = rng.uniform(rmin, rmax) * (0.6 + 0.4 * k)
            swell = float(smp('perlin_lo', P, coverage_freq * 1.7, (0.37, 0.61, 0.0))[0, 0, 0]) - 0.5
            out.append((x, y, zc + R * 0.25 * rng.uniform(0.5, 1.5) + swell * zc * 1.6, R))
    return out


def sheet_blobs(rng, masses, flat, levels=2):
    parents = [(np.array(m[:3], np.float32), m[3], (1.0, 1.0, flat)) for m in masses]
    return parents + cauliflower(rng, parents, levels, n_range=(3, 6), ratio=(0.35, 0.55), up=0.9,
                                 embed=(0.3, 0.6), zmin=0.5)


def shape_strato(q):
    """Stratocumulus patch: a lumpy sheet of flattened rolls with gaps, seen a little from above."""
    rng = np.random.default_rng(47)
    masses = layer_masses(rng, -125, 125, -70, 70, 12.0, 10, 16, 7.0, 1 / 110.0, 0.42,
                          taper=lambda x, y: max(0.0, 1 - (x / 132) ** 2 - (y / 78) ** 2) ** 0.35)
    blobs = sheet_blobs(rng, masses, 0.45, levels=1)
    grid = Grid((-140, -84, -3), (140, 84, 32), 0.55 / q)
    fn = cumulus_field(blobs, K=2.6, base_z=0.0, top_z=18.0, edge=0.9, disp=(3.0, 0.6, 0.3),
                       fringe=3.0, warp_amp=9.0, warp_freq=1 / 120.0, seed_off=(0.71, 0.13, 0.4),
                       wisp_amt=0.14)
    return grid, fn, dict(res=(2048, 1024), yaw=0.0, pitch=-14.0, lens=50.0, fill=0.9, sigma=1.3)


def wisp_field(blobs, K, soft, seed_off=(0, 0, 0), stretch=(0.5, 1.0, 1.2), gain=5.0):
    """Ragged fractus: soft envelope, noise-thresholded torn fragments with puffy bits."""
    off = np.array(seed_off, np.float32)
    st = np.array(stretch, np.float32)

    def fn(P):
        Pw = warp(P + off, 12.0, 1 / 60.0) - off
        env = np.clip(-spheres_sdf(Pw, blobs, K) / soft, 0, 1)
        Q = (Pw + off) * st
        nz = (0.42 * smp('pw', Q, 1 / 26.0) + 0.18 * smp('perlin', Q, 1 / 9.0)
              + 0.25 * smp('billow', Pw + off, 1 / 14.0) + 0.15 * smp('billow_hi', Pw + off, 1 / 5.0))
        thr = 0.98 - 0.62 * sstep(0.0, 1.0, env)
        dens = np.clip((nz - thr) * gain, 0, 1)
        return dens ** 1.3
    return fn


def shape_wisp(q):
    """Torn fractus fragment: translucent, fibrous, for close passes by the windows."""
    rng = np.random.default_rng(61)
    blobs = []
    x = -80.0
    while x < 80:
        env = math.cos(x / 88.0 * math.pi / 2) ** 0.7
        R = rng.uniform(11, 17) * (0.45 + 0.55 * env)
        blobs.append((np.array([x, rng.uniform(-8, 8), 14 + 0.05 * x + rng.uniform(-4, 4)], np.float32),
                      R, (2.0, 1.3, 0.95)))
        x += R * rng.uniform(0.9, 1.5)
    grid = Grid((-118, -40, -16), (118, 40, 44), 0.40 / q)
    fn = wisp_field(blobs, K=6.0, soft=7.0, seed_off=(0.2, 0.45, 0.8))
    return grid, fn, dict(res=(2048, 1024), yaw=0.0, pitch=-2.0, lens=50.0, fill=0.88, sigma=1.8, g=0.6)


def sea_field(inner, y_far, fade_far=40.0):
    """Thinning far edge (the horizon line of the deck)."""
    def fn(P):
        return inner(P) * sstep(y_far, y_far - fade_far, P[..., 1])
    return fn


def shape_sea(q, variant):
    """Cloud-sea horizon strip: the top of a vast deck receding to the horizon, seen from
    slightly above. Left/right ends fade out (post) so strips overlap around a ring."""
    rng = np.random.default_rng(71 + variant)
    xh, y0, y1 = 330.0, 0.0, 560.0
    trap = lambda x, y: 1.0 if abs(x) < 170 + 0.62 * (y - y0) else 0.0   # only what the camera sees
    if variant == 1:     # soft undulating stratocumulus deck, a few low domes
        masses = layer_masses(rng, -xh, xh, y0, y1, 17.0, 11, 20, 6.0, 1 / 260.0, 0.22, taper=trap)
        extra = [(rng.uniform(-150, 150) * (1 + y / 400), y, 12, rng.uniform(12, 18))
                 for y in rng.uniform(y0 + 70, y1 - 80, 6)]
    else:                # lumpier deck with cumulus heads rising out of it
        masses = layer_masses(rng, -xh, xh, y0, y1, 15.0, 10, 17, 6.0, 1 / 200.0, 0.28, taper=trap)
        # verify pass: heads only in the distance (y > 200; one used to sit close to the camera
        # as a big soft blob), a little taller, and the grid is taller too (they were clipped
        # flat by the old z = 44 grid top)
        extra = [(rng.uniform(-150, 150) * (1 + y / 400), y, 17, rng.uniform(15, 25))
                 for y in rng.uniform(210, y1 - 70, 11)]
    blobs = sheet_blobs(rng, masses, 0.5, levels=1) + mound_blobs(rng, extra, levels=2, n_range=(3, 6),
                                                                  ratio=(0.35, 0.55))
    # continuous deck underneath: the sea has no holes down to the ground
    for x in np.arange(-xh, xh, 30.0):
        for y in np.arange(y0, y1, 30.0):
            if trap(x, y + 15) or trap(x + 30, y + 15) or trap(x - 30, y + 15):
                blobs.append((np.array([x + 15, y + 15, 3.0], np.float32), 24.0, (1.0, 1.0, 0.28)))
    grid = Grid((-xh - 10, y0 - 5, -4), (xh + 10, y1 + 10, 44 if variant == 1 else 66),
                (1.0 if variant == 1 else 1.1) / q)
    inner = cumulus_field(blobs, K=2.5, base_z=0.0, top_z=24.0, edge=0.7, disp=(4.0, 1.0, 0.5),
                          fringe=3.0, warp_amp=10.0, warp_freq=1 / 150.0, seed_off=(0.3 * variant, 0.5, 0.2),
                          wisp_amt=0.10)
    fn = sea_field(inner, y1)
    return grid, fn, dict(res=(2048, 512), cam_loc=(0.0, -130.0, 58.0), pitch=-6.0, lens=30.0, sigma=1.4,
                          yaw=0.0, fill=0.9, prefix='CloudSea_', side_taper=0.14, bottom_taper=0.30,
                          haze=dict(plane_z=16.0, start=150.0, length=800.0, max=0.6))


SHAPES = {
    'Cumulus': shape_cumulus,
    'Congestus': shape_congestus,
    'Puff': shape_puff,
    'Bank': shape_bank,
    'Strato': shape_strato,
    'Wisp': shape_wisp,
    '1': lambda q: shape_sea(q, 1),
    '2': lambda q: shape_sea(q, 2),
}


# =============================================================================
# 7. Driver
# =============================================================================
def render_one(name, preset, out_dir, samples, scale, dens_cache, keep_exr=False, vol_bounces=24,
               p_over=None, spec_over=None, tag=None, q=None):
    bpy.ops.wm.read_factory_settings(use_empty=True)
    p = dict(PRESETS[preset])
    p.update(p_over or {})
    t0 = time.time()
    if name not in dens_cache:
        grid, fn, spec = SHAPES[name](q if q else (max(scale, 0.5) if scale < 1 else 1.0))
        dens = evaluate(grid, fn)
        dens_cache[name] = (grid, dens, spec)
        print(f'[{name}] density {tuple(grid.res)} = {dens.size / 1e6:.1f}M voxels, '
              f'{time.time() - t0:.1f}s, occupancy {(dens > 0.02).mean():.3f}')
    grid, dens, spec = dens_cache[name]
    spec = dict(spec)
    spec.update(spec_over or {})
    mat = cloud_material(spec['sigma'], spec.get('g', 0.55))
    import_density('Cloud_' + name, dens, grid, mat)
    res = (int(spec['res'][0] * scale), int(spec['res'][1] * scale))
    if 'cam_loc' in spec:
        cam = place_camera(spec['cam_loc'], spec['pitch'], spec['lens'])
    else:
        cam = frame_camera(occupied_points(dens, grid), res, spec['yaw'], spec['pitch'], spec['lens'],
                           spec['fill'], spec.get('center_bias', (0, 0)))
    build_world(p)
    build_sun(p)
    setup_render(res, samples, p, vol_bounces)
    prefix = spec.get('prefix', 'Cloud_')
    base = tag or f'{prefix}{name}_{preset}'
    exr_dir = EXR_DIR if keep_exr and out_dir == DEFAULT_OUT else out_dir
    os.makedirs(exr_dir, exist_ok=True)
    exr = os.path.join(exr_dir, f'_{base}.exr')
    bpy.context.scene.render.filepath = exr
    t1 = time.time()
    bpy.ops.render.render(write_still=True)
    t2 = time.time()
    png = os.path.join(out_dir, f'{base}.png')
    postprocess(exr, png, haze=spec.get('haze'), p=p, cam=cam, side_taper=spec.get('side_taper', 0.0),
                bottom_taper=spec.get('bottom_taper', 0.0))
    if not keep_exr:
        os.remove(exr)
    print(f'[{name}/{preset}] {res[0]}x{res[1]} render {t2 - t1:.1f}s, total {time.time() - t0:.1f}s -> {png}')
    return png


# =============================================================================
# 8. Contact sheets + fringe checks (Pillow)
# =============================================================================
SHEET_ORDER = [('Cloud_', ['Cumulus', 'Congestus', 'Puff']), ('Cloud_', ['Bank', 'Strato', 'Wisp']),
               ('CloudSea_', ['1']), ('CloudSea_', ['2'])]


def _srgb_to_lin(c):
    return np.where(c <= 0.04045, c / 12.92, ((c + 0.055) / 1.055) ** 2.4)


def _lin_to_srgb(c):
    c = np.clip(c, 0, 1)
    return np.where(c <= 0.0031308, c * 12.92, 1.055 * c ** (1 / 2.4) - 0.055)


def composite(bg_srgb, card_rgba):
    """Straight-alpha 'over' in linear light (what Unity does in a Linear-colour-space project)."""
    a = card_rgba[..., 3:4]
    out = _srgb_to_lin(card_rgba[..., :3]) * a + _srgb_to_lin(bg_srgb) * (1 - a)
    return _lin_to_srgb(out)


def sky_background(p, w, h, el_top=32.0, el_bot=-4.0):
    """The preset's own sky (same function that lit the clouds), tone mapped like the cards."""
    sc = bpy.context.scene
    _set_enum(sc.view_settings, 'view_transform', p.get('view', 'AgX'))
    _set_enum(sc.view_settings, 'look', p['look'], 'None')
    sc.view_settings.exposure = p['exposure']
    el = np.radians(np.linspace(el_top, el_bot, h))
    az = np.radians(np.linspace(-28, 28, w))
    E, A = np.meshgrid(el, az, indexing='ij')
    d = np.stack([np.cos(E) * np.sin(A), np.cos(E) * np.cos(A), np.sin(E)], -1).astype(np.float32)
    return tonemap(sky_np(p, d), os.path.join(CACHE, '_sky_tmp.png'))


def contact_sheets(out_dir):
    from PIL import Image, ImageDraw, ImageFont
    rdir = os.path.join(out_dir, 'Renders')
    os.makedirs(rdir, exist_ok=True)
    W, M = 2048, 16
    try:
        font = ImageFont.load_default(size=22)
    except TypeError:
        font = ImageFont.load_default()
    for pn, p in PRESETS.items():
        rows = []
        for prefix, names in SHEET_ORDER:
            files = [os.path.join(out_dir, f'{prefix}{n}_{pn}.png') for n in names]
            files = [f for f in files if os.path.exists(f)]
            if not files:
                continue
            ims = [Image.open(f).convert('RGBA') for f in files]
            tw = (W - M * (len(names) + 1)) // len(names)
            th = int(tw * ims[0].height / ims[0].width)
            rows.append((files, [im.resize((tw, th), Image.LANCZOS) for im in ims], tw, th))
        if not rows:
            continue
        H = M + sum(r[3] + M for r in rows) + 40
        bg = sky_background(p, W, H)
        canvas = bg.copy()
        y = M + 40
        boxes = []
        for files, ims, tw, th in rows:
            x = M
            for f, im in zip(files, ims):
                a = np.asarray(im).astype(np.float32) / 255
                canvas[y:y + th, x:x + tw] = composite(canvas[y:y + th, x:x + tw], a)
                boxes.append((x, y, os.path.basename(f)))
                x += tw + M
            y += th + M
        img = Image.fromarray((np.clip(canvas, 0, 1) * 255 + 0.5).astype(np.uint8))
        dr = ImageDraw.Draw(img)
        txt = (238, 238, 244) if pn == 'moon' else (250, 250, 255)
        dr.text((M, 10), f'Lanbai cloud cards - preset: {pn}  (composited in linear light over the preset sky)',
                fill=txt, font=font)
        for x, y0, name in boxes:
            dr.text((x + 6, y0 + 4), name, fill=txt, font=font)
        path = os.path.join(rdir, f'ContactSheet_{pn}.png')
        img.save(path, optimize=True)
        print('sheet', path)


def fringe_checks(out_dir, check_dir):
    """Every card over a bright sky and a near-black sky, plus a 3x edge crop of each."""
    from PIL import Image
    os.makedirs(check_dir, exist_ok=True)
    light, dark = np.array([0.80, 0.87, 0.96]), np.array([0.015, 0.02, 0.04])
    for pn in PRESETS:
        tiles = []
        for prefix, names in SHEET_ORDER:
            for n in names:
                f = os.path.join(out_dir, f'{prefix}{n}_{pn}.png')
                if not os.path.exists(f):
                    continue
                im = Image.open(f).convert('RGBA')
                a = np.asarray(im).astype(np.float32) / 255
                # crop around the strongest alpha edge (top of the silhouette), 3x nearest zoom
                al = a[..., 3]
                ys, xs = np.nonzero(al > 0.5)
                cy, cx = int(ys.min()), int(xs[np.argmin(ys)])
                h0, w0 = 96, 160
                y0 = int(np.clip(cy - h0 // 2, 0, al.shape[0] - h0)); x0 = int(np.clip(cx - w0 // 2, 0, al.shape[1] - w0))
                crop = a[y0:y0 + h0, x0:x0 + w0].repeat(3, 0).repeat(3, 1)
                small = np.asarray(im.resize((480, int(480 * im.height / im.width)), Image.LANCZOS)).astype(np.float32) / 255
                row = []
                for bgc in (light, dark):
                    s = composite(np.broadcast_to(bgc, small.shape[:2] + (3,)), small)
                    c = composite(np.broadcast_to(bgc, crop.shape[:2] + (3,)), crop)
                    hh = max(s.shape[0], c.shape[0])
                    pad = lambda z: np.pad(z, ((0, hh - z.shape[0]), (0, 0), (0, 0)), constant_values=0.5)
                    row += [pad(s), pad(c)]
                tiles.append(np.concatenate(row, 1))
        if tiles:
            wmax = max(t.shape[1] for t in tiles)
            tiles = [np.pad(t, ((0, 6), (0, wmax - t.shape[1]), (0, 0)), constant_values=0.5) for t in tiles]
            Image.fromarray((np.concatenate(tiles, 0) * 255).astype(np.uint8)).save(
                os.path.join(check_dir, f'FringeCheck_{pn}.png'))


def write_meta(out_dir):
    """clouds_meta.json: per card the opaque bbox and the flat-base line in Unity UV
    (v = 0 at the bottom), plus the baked light direction, for placing pivots / mirroring."""
    import json
    import glob
    from PIL import Image
    meta = {}
    for f in sorted(glob.glob(os.path.join(out_dir, 'Cloud*.png'))):
        a = np.asarray(Image.open(f).convert('RGBA'))[..., 3].astype(np.float32) / 255
        h, w = a.shape
        rows = np.nonzero((a > 0.5).mean(1) > 0.02)[0]
        cols = np.nonzero((a > 0.5).mean(0) > 0.0)[0]
        any_r = np.nonzero(a.max(1) > 0.01)[0]
        any_c = np.nonzero(a.max(0) > 0.01)[0]
        base = os.path.basename(f)[:-4]
        preset = base.rsplit('_', 1)[1]
        p = PRESETS[preset]
        meta[base] = dict(
            size=[w, h],
            bbox_uv=[round(any_c[0] / w, 4), round(1 - (any_r[-1] + 1) / h, 4),
                     round((any_c[-1] + 1) / w, 4), round(1 - any_r[0] / h, 4)],
            opaque_bbox_uv=[round(cols[0] / w, 4), round(1 - (rows[-1] + 1) / h, 4),
                            round((cols[-1] + 1) / w, 4), round(1 - rows[0] / h, 4)] if len(rows) else None,
            cloud_base_v=round(1 - (rows[-1] + 1) / h, 4) if len(rows) else None,
            light=dict(side='right', azimuth_deg=p['sun_az'], elevation_deg=p['sun_el'],
                       note='azimuth from the view direction toward screen-right; 0 = behind the cloud'),
        )
    with open(os.path.join(out_dir, 'clouds_meta.json'), 'w') as fh:
        json.dump(meta, fh, indent=1)


def repost(out_dir, exr_dir):
    """Redo only the post-processing (alpha / colour / tone map / haze) from kept EXRs."""
    import glob
    for exr in sorted(glob.glob(os.path.join(exr_dir, '_Cloud*.exr'))):
        base = os.path.basename(exr)[1:-4]
        prefix = 'CloudSea_' if base.startswith('CloudSea_') else 'Cloud_'
        name, preset = base[len(prefix):].rsplit('_', 1)
        if name not in SHAPES or preset not in PRESETS:
            continue
        bpy.ops.wm.read_factory_settings(use_empty=True)
        p = PRESETS[preset]
        _, _, spec = SHAPES[name](1.0)
        cam = place_camera(spec['cam_loc'], spec['pitch'], spec['lens']) if 'cam_loc' in spec else None
        setup_render(spec['res'], 1, p)
        postprocess(exr, os.path.join(out_dir, base + '.png'), haze=spec.get('haze'), p=p, cam=cam,
                    side_taper=spec.get('side_taper', 0.0), bottom_taper=spec.get('bottom_taper', 0.0))
        print('repost', base)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('--repost', action='store_true', help='only redo post-processing from kept EXRs')
    ap.add_argument('--exr-dir', default=EXR_DIR)
    ap.add_argument('--out', default=DEFAULT_OUT)
    ap.add_argument('--only', nargs='*', default=None)
    ap.add_argument('--preset', nargs='*', default=None)
    ap.add_argument('--samples', type=int, default=40)
    ap.add_argument('--scale', type=float, default=1.0)
    ap.add_argument('--bounces', type=int, default=14)
    ap.add_argument('--test', action='store_true')
    ap.add_argument('--keep-exr', action='store_true')
    ap.add_argument('--sheets', action='store_true')
    args = ap.parse_args(sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:])
    if args.test:
        args.scale = min(args.scale, 0.45)
        args.samples = min(args.samples, 32)
    os.makedirs(args.out, exist_ok=True)
    names = args.only or list(SHAPES)
    presets = args.preset or list(PRESETS)
    cache = {}
    if args.repost:
        repost(args.out, args.exr_dir)
    elif not args.sheets:
        for n in names:
            for pr in presets:
                render_one(n, pr, args.out, args.samples, args.scale, cache, args.keep_exr, args.bounces)
            cache.pop(n, None)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    contact_sheets(args.out)
    write_meta(args.out)
    fringe_checks(args.out, os.path.join(HERE, 'checks'))


if __name__ == '__main__':
    main()
