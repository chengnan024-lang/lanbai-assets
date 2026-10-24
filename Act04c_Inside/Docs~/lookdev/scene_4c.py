"""Act 4c (inside the tear) for the render harness (Engineering/render_harness/lbh_render.py --scene this file).

Materials are emission node trees that repeat Lanbai/InsideLip's arithmetic (Shaders/Lanbai_InsideLip.shader):
  sheet  = (cloth x weave + fibre x (lip glow + translucency band)) -> LanbaiApplyFog
  fringe = fibre x comb.r x (0.7 + 0.6 comb.b) x bundle gaps x gain -> x (1 - fog)       (additive)
  thread = dark core + lit rim, premultiplied -> LanbaiApplyFog
  dome   = LanbaiHorizon(V)  (the fog at infinity)
  dot    = core + halo, no fog (a sky object)
and the fog colour is LanbaiSky.cginc model B ("gradient", sky session v1), same arithmetic, with the act's parameter
group from inside_drive.fog_params(t). Geometry = Tools~/inside_geom.py (the same arrays the FBX is made from).
ctx['args']: lips=1,2,.. (subset), noloose=1, gain=<x>.
"""
import math
import os
import sys

import bpy
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
KIT = os.path.abspath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(KIT, 'Tools~'))
import inside_def as D  # noqa: E402
import inside_geom as GE  # noqa: E402
import inside_drive as DR  # noqa: E402

TEX = os.path.join(KIT, 'Textures')


# ------------------------------------------------------------------------------------------------ node helpers
class NT:
    def __init__(self, mat):
        mat.use_nodes = True
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')

    def n(self, kind, **kw):
        node = self.nt.nodes.new(kind)
        for k, v in kw.items():
            setattr(node, k, v)
        return node

    def link(self, a, b):
        self.nt.links.new(a, b)

    def math(self, op, a, b=None, clamp=False):
        m = self.n('ShaderNodeMath', operation=op, use_clamp=clamp)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (int, float)):
                m.inputs[i].default_value = float(v)
            else:
                self.link(v, m.inputs[i])
        return m.outputs[0]

    def vmath(self, op, a, b=None, s=None):
        m = self.n('ShaderNodeVectorMath', operation=op)
        for i, v in enumerate((a, b)):
            if v is None:
                continue
            if isinstance(v, (tuple, list)):
                m.inputs[i].default_value = v
            else:
                self.link(v, m.inputs[i])
        if s is not None:
            if isinstance(s, (int, float)):
                m.inputs[3].default_value = s
            else:
                self.link(s, m.inputs[3])
        return m.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else m.outputs['Vector']

    def sep(self, v):
        s = self.n('ShaderNodeSeparateXYZ')
        self.link(v, s.inputs[0])
        return s.outputs[0], s.outputs[1], s.outputs[2]

    def comb(self, x, y, z):
        c = self.n('ShaderNodeCombineXYZ')
        for i, v in enumerate((x, y, z)):
            if isinstance(v, (int, float)):
                c.inputs[i].default_value = float(v)
            else:
                self.link(v, c.inputs[i])
        return c.outputs[0]

    def rgb(self, c):
        return self.vmath('ADD', tuple(float(x) for x in c), (0.0, 0.0, 0.0))

    def smooth(self, e0, e1, x):
        """smoothstep(e0, e1, x) for scalar sockets / numbers (e0 > e1 allowed)."""
        t = self.math('DIVIDE', self.math('SUBTRACT', x, e0), float(e1) - float(e0) if isinstance(e0, (int, float)) and isinstance(e1, (int, float)) else self.math('SUBTRACT', e1, e0))
        t = self.math('MINIMUM', self.math('MAXIMUM', t, 0.0), 1.0)
        return self.math('MULTIPLY', self.math('MULTIPLY', t, t), self.math('SUBTRACT', 3.0, self.math('MULTIPLY', 2.0, t)))

    def mix(self, a, b, f):
        """lerp of two vectors by scalar f."""
        return self.vmath('ADD', a, self.vmath('SCALE', self.vmath('SUBTRACT', b, a), s=f))

    def attr(self, name, kind='GEOMETRY'):
        a = self.n('ShaderNodeAttribute', attribute_name=name)
        return a

    def uv(self, name):
        u = self.n('ShaderNodeUVMap', uv_map=name)
        return u.outputs[0]

    def img(self, path, vec, interp='Linear', ext='REPEAT'):
        t = self.n('ShaderNodeTexImage', interpolation=interp, extension=ext)
        im = bpy.data.images.load(path, check_existing=True)
        im.colorspace_settings.name = 'Non-Color'
        t.image = im
        self.link(vec, t.inputs[0])
        return t

    def emission(self, col, strength=1.0):
        e = self.n('ShaderNodeEmission')
        self.link(col, e.inputs['Color'])
        e.inputs['Strength'].default_value = strength
        return e.outputs[0]

    def transparent(self):
        return self.n('ShaderNodeBsdfTransparent').outputs[0]

    def add(self, a, b):
        m = self.n('ShaderNodeAddShader')
        self.link(a, m.inputs[0])
        self.link(b, m.inputs[1])
        return m.outputs[0]

    def mixs(self, a, b, f):
        m = self.n('ShaderNodeMixShader')
        if isinstance(f, (int, float)):
            m.inputs[0].default_value = f
        else:
            self.link(f, m.inputs[0])
        self.link(a, m.inputs[1])
        self.link(b, m.inputs[2])
        return m.outputs[0]

    def done(self, shader):
        self.link(shader, self.out.inputs['Surface'])

    # -------------------------------------------------------------------------------------------- the fog
    def view_dir_unity(self):
        """unit vector camera -> point, in UNITY axes (Blender (x, y, z) = Unity (x, z, y))."""
        g = self.n('ShaderNodeNewGeometry')
        bx, by, bz = self.sep(self.vmath('SCALE', g.outputs['Incoming'], s=-1.0))
        return bx, bz, by

    def horizon(self, fp):
        """LanbaiSky.cginc LanbaiHorizonGradient (model B) with this frame's parameter group (inside_drive.fog_params)."""
        vx, vy, vz = self.view_dir_unity()
        el = self.math('MULTIPLY', self.math('ARCSINE', self.math('MINIMUM', self.math('MAXIMUM', vy, -1.0), 1.0)), 180.0 / math.pi)
        # azimuth from the band direction (+Z in act 4c): acos of the normalised horizontal components
        hl = self.math('SQRT', self.math('ADD', self.math('MULTIPLY', vx, vx), self.math('ADD', self.math('MULTIPLY', vz, vz), 1e-10)))
        bd = np.asarray(fp['band_dir'], float)
        bh = bd[[0, 2]] / (np.linalg.norm(bd[[0, 2]]) + 1e-9)
        cosaz = self.math('DIVIDE', self.math('ADD', self.math('MULTIPLY', vx, float(bh[0])), self.math('MULTIPLY', vz, float(bh[1]))), hl)
        az = self.math('MULTIPLY', self.math('ARCCOSINE', self.math('MINIMUM', self.math('MAXIMUM', cosaz, -1.0), 1.0)), 180.0 / math.pi)
        hz = self.mix(self.rgb(fp['near']), self.rgb(fp['far']), self.smooth(0.0, max(fp['bw'], 1.0), az))
        sh, be = fp['shape'], fp['below']
        up = self.smooth(sh[0], max(sh[1], sh[0] + 0.1), el)
        if sh[2] > 0 and sh[2] != 1.0:
            up = self.math('POWER', up, sh[2])
        dn = self.smooth(be[1], min(be[0], be[1] - 0.1), el)
        if be[2] > 0 and be[2] != 1.0:
            dn = self.math('POWER', dn, be[2])
        c = self.mix(hz, self.rgb(fp['zenith']), up)
        return self.mix(c, self.rgb(fp['nadir']), dn)

    def fog_amount(self, density):
        cd = self.n('ShaderNodeCameraData')
        return self.math('SUBTRACT', 1.0, self.math('EXPONENT', self.math('MULTIPLY', cd.outputs['View Distance'], -float(density))))

    def apply_fog(self, col, fp):
        return self.mix(col, self.horizon(fp), self.fog_amount(fp['density']))


# ------------------------------------------------------------------------------------------------ materials
def mat_sheet(name, P, fp):
    m = bpy.data.materials.new(name)
    N = NT(m)
    geo = N.n('ShaderNodeNewGeometry')
    bx, by, bz = N.sep(geo.outputs['Position'])           # Blender world: x = Unity x, z = Unity y
    cr, sr = math.cos(math.radians(P['roll'])), math.sin(math.radians(P['roll']))
    lx = N.math('ADD', N.math('MULTIPLY', bx, cr), N.math('MULTIPLY', bz, sr))
    ly = N.math('ADD', N.math('MULTIPLY', bx, -sr), N.math('MULTIPLY', bz, cr))
    ws = P['weave_scale']
    w = N.img(os.path.join(TEX, 'Inside_Weave_1024.png'), N.comb(N.math('DIVIDE', lx, ws), N.math('DIVIDE', ly, ws), 0.0))
    w2 = N.img(os.path.join(TEX, 'Inside_Weave_1024.png'), N.comb(N.math('DIVIDE', N.math('ADD', N.math('MULTIPLY', lx, 3.1), 0.37), ws),
                                                                 N.math('DIVIDE', N.math('MULTIPLY', ly, 0.9), ws), 0.0))
    wr, wg, wb = N.sep(w.outputs['Color'])
    w2r, _, _ = N.sep(w2.outputs['Color'])
    streak = N.math('ADD', N.math('MULTIPLY', N.math('SUBTRACT', wr, 0.5), 1.6),
                    N.math('ADD', N.math('MULTIPLY', N.math('SUBTRACT', w2r, 0.5), 0.6), N.math('MULTIPLY', N.math('SUBTRACT', wg, 0.5), 0.35)))
    k = N.math('ADD', N.math('ADD', 1.0, N.math('MULTIPLY', streak, P['weave_amount'])), N.math('MULTIPLY', N.math('SUBTRACT', wb, 0.5), 0.25))
    k = N.math('MINIMUM', N.math('MAXIMUM', k, 0.0), 1.0)
    d_edge, u_edge, _ = N.sep(N.uv('UV1'))
    fo = P['folds']
    ft = N.img(os.path.join(TEX, 'Inside_Weave_1024.png'), N.comb(N.math('DIVIDE', u_edge, fo[0]), N.math('DIVIDE', d_edge, fo[1]), 0.0))
    fr_, _, _ = N.sep(ft.outputs['Color'])
    foldK = N.math('ADD', 1.0, N.math('MULTIPLY', N.math('MULTIPLY', N.math('SUBTRACT', fr_, 0.5), 2.0 * fo[2]),
                                      N.math('EXPONENT', N.math('DIVIDE', d_edge, -fo[3]))))
    cloth = N.vmath('SCALE', N.rgb(P['cloth']), s=N.math('MULTIPLY', k, foldK))
    comb = N.img(os.path.join(TEX, 'Inside_Fringe_2048x256.png'), N.comb(N.math('DIVIDE', u_edge, 64.0), 0.02, 0.0))
    cr_, _, _ = N.sep(comb.outputs['Color'])
    lip = N.math('MULTIPLY', N.math('MULTIPLY', P['lip_glow'], N.math('EXPONENT', N.math('DIVIDE', d_edge, -P['lip_w']))),
                 N.math('ADD', 0.55, N.math('MULTIPLY', cr_, 0.45)))
    bandmod = N.math('ADD', N.math('ADD', 0.5, N.math('MULTIPLY', N.math('SUBTRACT', wr, 0.5), 1.6)), N.math('MULTIPLY', N.math('SUBTRACT', wg, 0.5), 0.3))
    bandmod = N.math('MINIMUM', N.math('MAXIMUM', bandmod, 0.0), 1.0)
    # r11 (art review r10 B2): the thin weave near the tear lets the light through, mottled at ~0.03 H (not a rim glow)
    Hb = P['band'][1] / 0.04
    # r12 (art review r11 S5): domain-warped (no lattice)
    wu = N.math('ADD', N.math('MULTIPLY', u_edge, 2 * math.pi / (0.03 * Hb)),
                N.math('MULTIPLY', N.math('SINE', N.math('ADD', N.math('MULTIPLY', d_edge, 2 * math.pi / (0.037 * Hb)), 0.4)), 1.3))
    wd = N.math('ADD', N.math('MULTIPLY', d_edge, 2 * math.pi / (0.05 * Hb)),
                N.math('MULTIPLY', N.math('SINE', N.math('ADD', N.math('MULTIPLY', u_edge, 2 * math.pi / (0.043 * Hb)), 1.1)), 1.6))
    mott = N.math('ADD', 0.5, N.math('ADD', N.math('MULTIPLY', N.math('MULTIPLY', N.math('SINE', wu), N.math('SINE', wd)), 0.35),
                                     N.math('MULTIPLY', N.math('SINE', N.math('MULTIPLY', u_edge, 2 * math.pi / (0.071 * Hb))), 0.2)))
    band = N.math('MULTIPLY', N.math('MULTIPLY', P['band'][0], N.math('EXPONENT', N.math('DIVIDE', d_edge, -P['band'][1]))), N.math('MAXIMUM', mott, 0.0))
    gain = N.attr('Col')
    gr, _, _ = N.sep(gain.outputs['Color'])
    glow = N.math('MULTIPLY', N.math('ADD', lip, N.math('MULTIPLY', band, foldK)), gr)
    col = N.vmath('ADD', cloth, N.vmath('SCALE', N.rgb(P['fibre']), s=glow))
    col = N.mix(col, N.horizon(fp), N.math('MINIMUM', N.fog_amount(fp['density']), P['fog_cap_cloth']))
    # r09 (art review r08 B2): cloth-only cues AFTER the fog (a texture-based fold was averaged away by mips and fog):
    # tension folds radiating from the torn edge (procedural, +-amp) and, on ~15-20 % of the edge, the curled-back face:
    # a darker band just behind the glowing rim
    Hk = fo[0] / 0.08
    tau = 2.0 * math.pi
    # r13 (总导演 D-19: the r11 ridges read as rock strata): soft DRAPE pleats that hang with gravity (vertical in the
    # world, whatever the edge does), period ~0.035 H with a slow sway, +-12 %, fading 0.15 H from the torn edge
    phx = N.math('ADD', N.math('MULTIPLY', bx, tau / (0.025 * Hk)),
                 N.math('ADD', N.math('MULTIPLY', N.math('SINE', N.math('MULTIPLY', bz, tau / (0.2 * Hk))), 0.6),
                        N.math('MULTIPLY', N.math('SINE', N.math('MULTIPLY', bx, tau / (0.13 * Hk))), 0.8)))
    fold = N.math('ADD', N.math('MULTIPLY', N.math('SINE', phx), 0.6),
                  N.math('MULTIPLY', N.math('SINE', N.math('ADD', N.math('MULTIPLY', phx, 2.1), 1.0)), 0.4))
    env = N.math('EXPONENT', N.math('DIVIDE', d_edge, -0.15 * Hk))
    fk = N.math('ADD', 1.0, N.math('MULTIPLY', N.math('MULTIPLY', fold, 0.16), env))
    lw = P['lip_w']
    band_in = N.math('MULTIPLY', N.smooth(lw * 1.0, lw * 1.6, d_edge),
                     N.math('SUBTRACT', 1.0, N.smooth(lw + 0.005 * Hk, lw + 0.009 * Hk, d_edge)))
    cm = N.math('ADD', N.math('SINE', N.math('MULTIPLY', u_edge, tau / (0.05 * Hk))),
                N.math('MULTIPLY', N.math('SINE', N.math('MULTIPLY', u_edge, tau / (0.017 * Hk))), 0.8))
    curl = N.math('MULTIPLY', N.smooth(0.9, 1.3, cm), band_in)
    dk = N.math('SUBTRACT', 1.0, N.math('MULTIPLY', curl, 0.40))
    # r15: the rim brightens where a pleat turns toward the light and dims where it turns away (no constant bevel)
    rimk = N.math('ADD', 1.0, N.math('MULTIPLY', N.math('MULTIPLY', fold, 0.35),
                                      N.math('EXPONENT', N.math('DIVIDE', d_edge, -max(P['lip_w'] * 3.0, 0.5)))))
    col = N.vmath('SCALE', col, s=N.math('MULTIPLY', N.math('MULTIPLY', fk, dk), rimk))
    # r07: a hidden / fading lip blends into the fog at infinity (the dome's colour) by its visibility: no pop, no ghost
    # (r09: after the folds, so a hidden lip carries none)
    col = N.mix(N.horizon(fp), col, float(P.get('vis', 1.0)))
    N.done(N.emission(col))
    return m


def mat_fringe(name, P, fp):
    m = bpy.data.materials.new(name)
    N = NT(m)
    t = N.img(os.path.join(TEX, 'Inside_Fringe_2048x256.png'), N.uv('UVMap'))
    r, _, b = N.sep(t.outputs['Color'])
    cg = N.attr('Col')
    gr, gg, _ = N.sep(cg.outputs['Color'])
    k = N.math('MULTIPLY', N.math('MULTIPLY', r, N.math('ADD', 0.7, N.math('MULTIPLY', b, 0.6))), N.math('MULTIPLY', gr, gg))
    k = N.math('MULTIPLY', k, P['fringe_gain'])
    k = N.math('MULTIPLY', k, N.math('SUBTRACT', 1.0, N.fog_amount(fp['density'])))
    col = N.vmath('SCALE', N.rgb(P['fibre']), s=k)
    N.done(N.add(N.emission(col), N.transparent()))
    return m


def mat_hang(name, P, fp):
    """r13 (总导演 D-19): a hanging thread is one solid strand (the fringe texture's strands are all short), tapering to
    the tip: fibre colour x the fringe gain x 1.6 x (1 - 0.6 v^2), additive, fogged. Unity: the FRINGE part with _Sway > 0."""
    m = bpy.data.materials.new(name)
    N = NT(m)
    _, v, _ = N.sep(N.uv('UVMap'))
    cg = N.attr('Col')
    gr, _, _ = N.sep(cg.outputs['Color'])
    cd = N.n('ShaderNodeCameraData')
    near = N.smooth(10.0, 20.0, cd.outputs['View Distance'])          # r14 (art review r13 B1): no bar across the window
    k = N.math('MULTIPLY', gr, near)
    k = N.math('MULTIPLY', k, P['fringe_gain'] * 1.6 * 0.35)
    k = N.math('MULTIPLY', k, N.math('SUBTRACT', 1.0, N.fog_amount(fp['density'])))
    N.done(N.add(N.emission(N.vmath('SCALE', N.rgb(P['fibre']), s=k)), N.transparent()))
    return m


def mat_thread(name, P, fp, core_lit=0.0):
    m = bpy.data.materials.new(name)
    N = NT(m)
    _, v, _ = N.sep(N.uv('UVMap'))
    x = N.math('ABSOLUTE', N.math('SUBTRACT', N.math('MULTIPLY', v, 2.0), 1.0))
    edge = N.math('POWER', x, 6.0)
    a = N.smooth(1.0, 0.82, x)
    cg = N.attr('Col')
    gr, _, _ = N.sep(cg.outputs['Color'])
    core = N.mix(N.rgb(np.asarray(P['cloth']) * 0.8), N.vmath('SCALE', N.rgb(P['fibre']), s=gr), float(core_lit))
    col = N.vmath('ADD', core, N.vmath('SCALE', N.rgb(P['fibre']), s=N.math('MULTIPLY', N.math('MULTIPLY', edge, P['thread_rim']), gr)))
    col = N.apply_fog(col, fp)
    N.done(N.mixs(N.transparent(), N.emission(col), a))
    return m


def mat_dome(fp):
    m = bpy.data.materials.new('Inside_Dome')
    N = NT(m)
    N.done(N.emission(N.horizon(fp)))
    return m


def mat_dot(core_lin, glow_k, core_frac, gain, halo_lin=(6.92, 5.95, 4.84)):
    m = bpy.data.materials.new('Inside_Dot')
    N = NT(m)
    u, v, _ = N.sep(N.uv('UVMap'))
    r = N.math('SQRT', N.math('ADD', N.math('MULTIPLY', N.math('MULTIPLY', u, 2.0), N.math('MULTIPLY', u, 2.0)),
                                  N.math('MULTIPLY', N.math('MULTIPLY', v, 2.0), N.math('MULTIPLY', v, 2.0))))
    core = N.math('SUBTRACT', 1.0, N.smooth(core_frac * 0.92, core_frac * 1.08, r))
    halo = N.math('MULTIPLY', N.math('MULTIPLY', N.math('EXPONENT', N.math('MULTIPLY', r, -4.5)), N.smooth(1.0, 0.6, r)), N.math('SUBTRACT', 1.0, core))   # r07: exp tail
    c = N.vmath('ADD', N.vmath('SCALE', N.rgb(core_lin), s=core), N.vmath('SCALE', N.rgb(halo_lin), s=N.math('MULTIPLY', halo, glow_k)))
    N.done(N.add(N.emission(N.vmath('SCALE', c, s=float(gain))), N.transparent()))
    return m


def mat_loose(col_lin, fp):
    m = bpy.data.materials.new('Inside_Loose')
    N = NT(m)
    cg = N.attr('Col')
    gr, _, _ = N.sep(cg.outputs['Color'])
    k = N.math('MULTIPLY', gr, N.math('SUBTRACT', 1.0, N.fog_amount(fp['density'])))
    N.done(N.add(N.emission(N.vmath('SCALE', N.rgb(col_lin), s=k)), N.transparent()))
    return m


def loose_mesh(o, clk, eye, width=0.008, px=math.radians(90.0) / 960.0):
    """numpy port of the shader's loose-thread vertex stage (uv0 along / side, uv1 phase / speed, uv2 r0 / angle,
    uv3 z0 / length, col = axis, brightness); the ribbon is inflated to >= 1 px and its brightness x coverage."""
    uv0, uv1, uv2, uv3, col = (np.asarray(o[k], float) for k in ('uv0', 'uv1', 'uv2', 'uv3', 'col'))
    period = 40.0
    age = np.mod((clk + uv1[:, 0]) / period, 1.0)
    r = uv2[:, 0] * (1.0 - 0.25 * age)
    ln = uv3[:, 1]
    ang = uv2[:, 1] + 0.15 * np.sin(clk * 0.21 + uv1[:, 0])
    base = np.stack([np.cos(ang) * r, 1.6 + np.sin(ang) * r * 0.75, uv3[:, 0] + uv1[:, 1] * (age - 0.5) * period], -1)
    axis = col[:, :3] * 2.0 - 1.0
    axis /= np.linalg.norm(axis, axis=1, keepdims=True)
    along = axis * ((uv0[:, 0] - 0.5) * ln)[:, None]
    along[:, 1] += 0.25 * ln * np.sin(uv0[:, 0] * np.pi) * np.sin(clk * 0.4 + uv1[:, 0])
    wp = base + along
    side = np.cross(axis, wp - eye)
    side /= np.linalg.norm(side, axis=1, keepdims=True) + 1e-9
    dist = np.linalg.norm(wp - eye, axis=1)
    rmin = 0.5 * px * dist
    rdraw = np.maximum(width * 0.5, rmin)
    cov = (width * 0.5) / rdraw
    wp = wp + side * (uv0[:, 1] * rdraw)[:, None]
    life = (np.clip(age / 0.15, 0, 1) ** 2 * (3 - 2 * np.clip(age / 0.15, 0, 1))) * \
           (1.0 - (lambda x: x * x * (3 - 2 * x))(np.clip((age - 0.8) / 0.2, 0, 1))) * \
           (lambda x: x * x * (3 - 2 * x))(np.clip((r - 3.0) / 2.0, 0, 1))
    g = cov * life * col[:, 3]
    return dict(V=wp, F=o['F'], col=np.stack([g, np.ones_like(g), np.zeros_like(g), np.ones_like(g)], -1))


# ------------------------------------------------------------------------------------------------ meshes
_SWAY_CLOCK = [None]


def mesh(S, name, o, offset_z, mat):
    V = np.asarray(o['V'], float).copy()
    if name.endswith('_Sheet') and 'col' in o and _SWAY_CLOCK[0] is not None:
        # r15: the tongues sway (Lanbai/InsideLip SHEET vertex stage): col.g = weight, col.b = phase
        c = np.asarray(o['col'], float)
        clk = _SWAY_CLOCK[0]
        V[:, 2] += DR.FLAP_SWAY_M * c[:, 1] * np.sin(clk * 2 * np.pi / DR.FLAP_PERIOD_S + c[:, 2] * 6.2832)
        V[:, 0] += 0.4 * DR.FLAP_SWAY_M * c[:, 1] * np.sin(clk * 2 * np.pi / (DR.FLAP_PERIOD_S * 1.33) + c[:, 2] * 6.2832 + 1.0)
    V[:, 2] += offset_z
    Vb = np.stack([V[:, 0], V[:, 2], V[:, 1]], -1)                       # Unity -> Blender (x, z, y)
    F = np.asarray(o['F'], np.int32)
    me = bpy.data.meshes.new(name)
    me.from_pydata(Vb.tolist(), [], F.tolist())
    me.update()
    li = F.ravel()
    for lname, key in (('UVMap', 'uv0'), ('UV1', 'uv1')):
        if key in o:
            lay = me.uv_layers.new(name=lname)
            lay.data.foreach_set('uv', np.asarray(o[key], np.float32)[li].ravel())
    if 'col' in o:
        at = me.color_attributes.new(name='Col', type='FLOAT_COLOR', domain='POINT')
        at.data.foreach_set('color', np.asarray(o['col'], np.float32).ravel())
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    ob.data.materials.append(mat)
    ob.visible_shadow = False
    return ob


_CACHE = os.path.join('/tmp', 'lanbai_inside_geom.npz')


def geometry():
    import pickle
    p = _CACHE + '.pkl'
    src = [os.path.join(KIT, 'Tools~', f) for f in ('inside_geom.py', 'inside_def.py', 'out/layout_solved.json')]
    if os.path.exists(p) and all(os.path.getmtime(p) > os.path.getmtime(s) for s in src):
        return pickle.load(open(p, 'rb'))
    rep, objs, meta = GE.build()
    pickle.dump((rep, objs, meta), open(p, 'wb'))
    return rep, objs, meta


def build(ctx):
    t = float(ctx['t'])
    a = ctx.get('args', {}) or {}
    sc = bpy.context.scene
    sc.cycles.transparent_max_bounces = 128
    sc.cycles.max_bounces = 0
    rep, objs, meta = geometry()
    _SWAY_CLOCK[0] = DR.clock(t)
    s = float(D.dist(t))
    st = DR.state(t)
    fp = st['fog']
    eye = np.asarray(ctx.get('eye', D.HERO_EYE), float)
    made = 0
    for L in rep['lips']:
        k = L['k']
        zk = L['s'] - s
        if k < 8 and zk < -400:            # far behind: fully fogged
            continue
        P = DR.lip_material(k, st)
        if k == 8:
            for p in rep['sleeve']['plies']:
                z = L['s'] + p['dz'] - s
                if z < -400:
                    continue
                Pp = dict(P, roll=p['roll'])
                if 1 <= p['i'] <= 3:            # r09 (art review r08 B3): the sleeve's inner cut faces a little lighter
                    Pp['cloth'] = tuple(np.asarray(P['cloth']) * DR.SLEEVE_INNER_CLOTH_K)
                mesh(None, 'Ply%d_Sheet' % p['i'], objs['Lip8_Ply%d_Sheet' % p['i']], z, mat_sheet('Ply%d' % p['i'], Pp, fp))
                if 'Lip8_Ply%d_Fringe' % p['i'] in objs:
                    mesh(None, 'Ply%d_Fringe' % p['i'], objs['Lip8_Ply%d_Fringe' % p['i']], z, mat_fringe('Ply%dF' % p['i'], Pp, fp))
                made += 1
            mesh(None, 'Lip8_Wall', objs['Lip8_Wall'], L['s'] - s, mat_thread('Wall', P, fp, core_lit=1.0))
            continue
        mesh(None, 'Lip%d_Sheet' % k, objs['Lip%d_Sheet' % k], zk, mat_sheet('Lip%d' % k, P, fp))
        mesh(None, 'Lip%d_Fringe' % k, objs['Lip%d_Fringe' % k], zk, mat_fringe('Lip%dF' % k, P, fp))
        if 'Lip%d_Hang' % k in objs:
            mesh(None, 'Lip%d_Hang' % k, objs['Lip%d_Hang' % k], zk, mat_hang('Lip%dH' % k, P, fp))   # r13: the hanging threads read
        if 'Lip%d_Threads' % k in objs:
            mesh(None, 'Lip%d_Threads' % k, objs['Lip%d_Threads' % k], zk, mat_thread('Lip%dT' % k, P, fp))
        made += 1
    # r08: the loose threads (bus-anchored; the same motion as Lanbai/InsideLip _PART_LOOSE), x 4 inside the sleeve
    if not a.get('noloose'):
        lo = loose_mesh(objs['Inside_Loose'], DR.clock(t), eye)
        if lo is not None:
            gain = DR.LOOSE_GAIN * DR.loose_gain(t)
            mesh(None, 'Inside_Loose', lo, 0.0, mat_loose(np.asarray(DR.fibre_fill(min(8, max(1, sum(1 for x in D.LIP_T if x <= t))))) * gain, fp))
    # the dome (bus-anchored, r 2.4 km) = the fog at infinity
    mesh(None, 'Inside_Dome', objs['Inside_Dome'], 0.0, mat_dome(fp))
    # the dot: a billboard toward the eye, 2.3 km out along the fixed bus direction
    core, glow, gain = D.dot_size(t)
    if gain > 0:
        dd = D.dot_dir()
        # r07: the halo is glare (Unity: ZTest Always); here the quad sits 40 m out with the same angular size, in front
        # of every sheet (the layout keeps the core clear of the cloth)
        c = eye + dd * 40.0
        gs, gk = DR.dot_flash(t)                            # D-20: grows inside the flash's rise
        glow = glow * gs
        gain = gain * gk
        half = 40.0 * math.tan(math.radians(glow) * 0.5)    # D-20: the glow angle is a DIAMETER (bible: <= 12 deg)
        f = dd / np.linalg.norm(dd)
        r = np.cross([0, 1, 0], f)
        r /= np.linalg.norm(r)
        u = np.cross(f, r)
        quad = dict(V=np.array([c + (-r - u) * half, c + (r - u) * half, c + (r + u) * half, c + (-r + u) * half]),
                    F=np.array([(0, 1, 2), (0, 2, 3)]), uv0=np.array([[-0.5, -0.5], [0.5, -0.5], [0.5, 0.5], [-0.5, 0.5]]))
        mesh(None, 'Inside_Dot', quad, 0.0, mat_dot(st['dot_core'], 0.32, core / glow, gain))
    return dict(what='第 4c 幕 t=%.2f s=%.1f lips=%d fog=%s' % (t, s, made, st['fog_zone_hex']))
