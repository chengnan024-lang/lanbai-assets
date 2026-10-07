"""Preview A (v2): the stop at night in drizzle, the bible's FIRST FRAME from the spawn point (§6·1: the bus's rear and
right side at the left, its red tail lights in the wet road, a row of cold lit windows; the tube and the sign ahead,
slightly right - the brightest things in the world; the door's cold light on the shoulder; the headlight beams
dissolving into the fog ahead; the tube's long band on the wet asphalt pointing at you), with the RAIN KIT v2:
  * wet asphalt + puddles from Stop_WetMask, continuing with Road_WetMask outside its rect (node port of WetSurface);
  * puddle rings = the kit's procedural cells (LanbaiRippleCells, the bible's 3-5 / m^2 / s, footprint band-limited)
    + the lamp-arm and case drip rings (DripRipple LUT), baked into a normal map by cells_ref.py;
  * still water as the kit's dark mirror (_PuddleMirror 0.30, Schlick) with the tube's image held at the
    still-water target (_LampPeak), exactly the v2 PuddleOverlay / WetSurface rule (a ray-vs-tube test in nodes);
  * streaks lit only where lit (Lanbai/RainParticles: lamp E x forward-scatter phase x _Gain 0.0152 x _Tint
    #DCE7F3, 4-6 mm wide), splashes from the re-packed atlas.
World (lamp, pole, sign, bus, notice case, field, sky) = the Sign kit's preview stage (deliver2/Sign/Tools~/src).
usage: python3 rain_scene.py <outdir> W H SPP"""
import sys, os, math, json, functools
import numpy as np
import bpy, bmesh
from mathutils import Vector

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'src')); sys.path.insert(0, HERE)
import rainpaths as RP
LAN = RP.lanbai_root()
SIGN_SRC = os.path.join(LAN, 'deliver2', 'Sign', 'Tools~', 'src')
sys.path.insert(0, SIGN_SRC)
import stage as S
import cells_ref as CR

OUT = sys.argv[1]; W = int(sys.argv[2]); H = int(sys.argv[3]); SPP = int(sys.argv[4])
PV = os.environ.get('RAIN_PREVIEW') or os.path.abspath(os.path.join(HERE, '..', 'preview_cache' if os.path.basename(HERE) == 'preview' else 'preview'))
os.makedirs(OUT, exist_ok=True)
S.pbr_textured = functools.partial(S.pbr_textured, texdir=os.path.join(PV, 'signtex'))

K = 1.76                                   # Blender radiance -> Unity scene-linear (the Sign kit's enamel calibration)
I_TUBE = 15.0                              # stop tube in Unity light units (README §8: E 1.0 on the road 3.9 m below)
TUBE_P = Vector((2.44, -2.38, 3.90)); TUBE_AX = Vector((0.6, 0.8, 0.0)) * 0.6
HEADLIGHTS = [Vector((0.15, 0.80, 0.75)), Vector((0.15, 2.40, 0.75))]
I_HEAD = 90.0; HEAD_COL = (1.0, 0.56, 0.19)   # #FFC47A linear
TUBE_COL = (0.775, 0.879, 0.896)               # #E4F1F3 linear
TINT = (0.716, 0.799, 0.896)                   # _Tint #DCE7F3 linear
GAIN = 0.0152
CAM = Vector(tuple(float(v) for v in os.environ.get('CAM', '-11.8,-1.8,1.62').split(',')))
AIM = Vector(tuple(float(v) for v in os.environ.get('AIM', '2.81,1.58,1.96').split(',')))
LENS = float(os.environ.get('LENS', '24'))
T_RAIN = float(os.environ.get('TRAIN', '37.3'))
MIRROR_R0 = 0.30; LAMP_PEAK = 1.45
rng = np.random.default_rng(7)

sc = S.setup((W, H), SPP)
sc.render.threads = int(os.environ.get('THREADS', '2'))
# uniform sampling: adaptive sampling + OIDN turned the glossy bus paint into crumpled foil at high spp
sc.cycles.use_adaptive_sampling = bool(os.environ.get('ADAPTIVE'))
sc.cycles.transparent_max_bounces = 64
S.world(sky_zenith=tuple(v / K for v in (0.0017, 0.0027, 0.0055)),
        sky_horizon=tuple(v / K for v in (0.0066, 0.0113, 0.0233)),
        town_glow=tuple(v / K for v in (0.0197, 0.0145, 0.0179)))
S.ground()
S.grass_verge()
S.GLOSSY_TUBE_FRACTION = 330.0 / 1200.0     # glossy rays see the analytic lamp's physical radiance (~580 Unity)
L_GLOSSY_MAX = 1200.0 * S.GLOSSY_TUBE_FRACTION * max(TUBE_COL)
S.concrete_pole_and_lamp(1200.0)
S.wires()
for o in bpy.data.objects:                  # the game inflates thin wires to >= 1.5 px (LanbaiInflate): so do we
    if o.name.startswith('Pv_Wire') and o.type == 'CURVE':
        o.data.bevel_depth = 0.009
S.bus(interior_strength=float(os.environ.get('CABIN', '0.5')))   # 0.5: seat cushion E ~1 (bible §4.3 0.8)
for _mn in ('Pv_BusCream', 'Pv_BusIndigo'):          # wet old paint: soft, not a chrome foil (bible §4.9)
    _b = bpy.data.materials[_mn].node_tree.nodes['Principled BSDF']; _b.inputs['Roughness'].default_value = 0.32


def bus_windows():
    """the lit side windows as REAL glass (a 5 mm slab, the kit's static beads on its outer face, tile 0.20 m), so the
    cabin - seats, rails, the cold tubes - is seen through the rain instead of a white panel."""
    bpy.data.objects['Pv_WindowGlow'].hide_render = True
    bn = bpy.data.images.load(RP.find('RainBeads_Vertical_Normal_1024.png'), check_existing=True)
    bn.colorspace_settings.name = 'Non-Color'
    def mat(name, ior, beads):
        m = bpy.data.materials.new(name); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
        o = nt.nodes.new('ShaderNodeOutputMaterial'); g = nt.nodes.new('ShaderNodeBsdfGlass')
        g.inputs['Color'].default_value = (*S.lin('#E9EFEA'), 1); g.inputs['IOR'].default_value = ior; g.inputs['Roughness'].default_value = 0.0
        if beads:
            tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
            mp.inputs['Scale'].default_value = (5.0, 5.0, 5.0); nt.links.new(tc.outputs['UV'], mp.inputs[0])
            t = nt.nodes.new('ShaderNodeTexImage'); t.image = bn; t.interpolation = 'Cubic'; nt.links.new(mp.outputs[0], t.inputs[0])
            nm = nt.nodes.new('ShaderNodeNormalMap'); nt.links.new(t.outputs['Color'], nm.inputs['Color'])
            nt.links.new(nm.outputs[0], g.inputs['Normal'])
        nt.links.new(g.outputs[0], o.inputs[0]); return m
    x0, x1 = S.BUS_FRONT_X - 8.0 + 0.1, S.DOOR_X0 - 0.12
    y0 = S.BUS_Y0; z0, z1 = 1.55, 2.35
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    v = {}
    for xi, xx in ((0, x0), (1, x1)):
        for zi, zz in ((0, z0), (1, z1)):
            for yi, yy in ((0, y0 - 0.002), (1, y0 + 0.003)):
                v[(xi, zi, yi)] = bm.verts.new((xx, yy, zz))
    outer = bm.faces.new([v[(0, 0, 0)], v[(1, 0, 0)], v[(1, 1, 0)], v[(0, 1, 0)]])
    inner = bm.faces.new([v[(0, 0, 1)], v[(0, 1, 1)], v[(1, 1, 1)], v[(1, 0, 1)]])
    for f in (outer, inner):
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x, lp.vert.co.z)
    bmesh.ops.recalc_face_normals(bm, faces=[outer, inner])
    outer.material_index = 0; inner.material_index = 1
    ob = S.mesh_obj('Rn_BusWindows', bm, mat('Rn_WinWater', 1.333, True))
    ob.data.materials.append(mat('Rn_WinGlass', 1.333, False))
    ob.visible_shadow = False


bus_windows()


def bus_rear():
    """round tail lamps in chrome bezels (bible §4.9: screen #B2252C, fill #CB1500 + a small glow) and a dark rear window
    that mirrors the night, instead of the stage's flat red squares and blank panel."""
    x0 = S.BUS_FRONT_X - 8.0
    for o in bpy.data.objects:
        if o.name.startswith('Pv_Tail'):
            o.hide_render = True
    chrome = S.pbr_simple('Rn_Chrome', S.lin('#CFD1D3'), 0.12, 1.0)
    lens = S.emission_mat('Rn_TailLens', S.lin('#CB1500'), 0.6)     # bible §4.9: fill #CB1500 -> screen #B2252C under S1
    rim = S.pbr_simple('Rn_TailRim', S.lin('#3A0A0A'), 0.25)
    for yc in (S.BUS_Y0 + 0.30, S.BUS_Y1 - 0.30):
        for (r, d, m, nm) in ((0.085, 0.020, chrome, 'Rn_TailBezel'), (0.070, 0.026, rim, 'Rn_TailRimRing'), (0.058, 0.030, lens, 'Rn_TailLens')):
            bm = bmesh.new()
            S.BS._add_cyl(bm, r, x0 - d, x0, seg=32, cx=yc, cy=0.98, axis='x')
            o = S.mesh_obj(nm, bm, m)
            for p in o.data.polygons: p.use_smooth = True
    # open the rear wall of the upper body and glaze it: the lit cabin shows through the rear window
    up = bpy.data.objects['Pv_BusUpper']
    bm = bmesh.new(); bm.from_mesh(up.data)
    kill = [f for f in bm.faces if f.calc_center_median().x < x0 + 0.045 and 1.30 < f.calc_center_median().z < 2.88]
    bmesh.ops.delete(bm, geom=kill, context='FACES')
    bm.to_mesh(up.data); bm.free()
    cream = bpy.data.materials['Pv_BusCream']
    bm = bmesh.new()
    y0, y1 = S.BUS_Y0, S.BUS_Y1
    S.bevel_box(bm, x0, x0 + 0.04, y0, y1, 1.32, 1.62)                       # below the window
    S.bevel_box(bm, x0, x0 + 0.04, y0, y1, 2.38, 2.86)                       # above
    S.bevel_box(bm, x0, x0 + 0.04, y0, y0 + 0.16, 1.62, 2.38)                # corners
    S.bevel_box(bm, x0, x0 + 0.04, y1 - 0.16, y1, 1.62, 2.38)
    S.mesh_obj('Rn_BusRearFrame', bm, cream)
    rub = S.pbr_simple('Rn_RearSeal', S.lin('#2B2B2B'), 0.3)
    bm = bmesh.new()
    for (a, b_, c, d) in ((y0 + 0.16, y1 - 0.16, 1.60, 1.63), (y0 + 0.16, y1 - 0.16, 2.37, 2.40), (y0 + 0.14, y0 + 0.17, 1.60, 2.40), (y1 - 0.17, y1 - 0.14, 1.60, 2.40)):
        S.bevel_box(bm, x0 - 0.012, x0 + 0.01, a, b_, c, d, r=0.004)
    S.mesh_obj('Rn_RearSealMesh', bm, rub)
    g = bpy.data.materials['Rn_WinWater']
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    f = bm.faces.new([bm.verts.new((x0 + 0.01, y1 - 0.16, 1.62)), bm.verts.new((x0 + 0.01, y0 + 0.16, 1.62)),
                      bm.verts.new((x0 + 0.01, y0 + 0.16, 2.38)), bm.verts.new((x0 + 0.01, y1 - 0.16, 2.38))])
    for lp in f.loops:
        lp[uv].uv = (-lp.vert.co.y, lp.vert.co.z)
    f.normal_update()
    if f.normal.x > 0: f.normal_flip()
    o = S.mesh_obj('Rn_RearGlass', bm, g); o.visible_shadow = False
    o.data.materials.append(bpy.data.materials['Rn_WinGlass'])       # the inner face is clean glass
    sol = o.modifiers.new('t', 'SOLIDIFY'); sol.thickness = 0.005; sol.material_offset = 1


bus_rear()
S.far_background()
for _o in bpy.data.objects:
    if _o.name.startswith(('Pv_Trees', 'Pv_NearTree', 'Pv_Hills')):
        _o.hide_render = True


def treeline(y0, x0, x1, hmin, hmax, seed, name):
    """a tree-line silhouette: overlapping rounded crowns on a low hedge, fine leafy edge, one flat strip"""
    r = np.random.default_rng(seed)
    n = int((x1 - x0) / 0.08)
    xs = np.linspace(x0, x1, n)
    def fbm(scales):
        out = np.zeros(n)
        for sc_, amp in scales:
            k = int((x1 - x0) / sc_) + 2
            kv = r.uniform(-1, 1, k)
            t = np.interp(xs, np.linspace(x0, x1, k), np.arange(k)); i = np.floor(t).astype(int); f = t - i; f = f * f * (3 - 2 * f)
            i1 = np.minimum(i + 1, k - 1)
            out += amp * (kv[i] * (1 - f) + kv[i1] * f)
        return out
    cluster = 0.5 + 0.5 * np.tanh(fbm(((60.0, 1.0), (25.0, 0.5))) * 1.6)
    h = hmin * 0.6 + hmin * 0.2 * fbm(((8.0, 1.0), (2.0, 0.3)))
    x = x0
    while x < x1:
        w = r.uniform(1.4, 4.0)
        cx = x + w * r.uniform(0.4, 1.0)
        c = cluster[min(n - 1, max(0, int((cx - x0) / (x1 - x0) * n)))]
        top = hmin * 0.7 + (hmax - hmin * 0.7) * (0.15 + 0.85 * c) * r.uniform(0.55, 1.0)
        tall = w * r.uniform(0.9, 1.9)
        for sub in range(int(r.integers(1, 4))):
            sw = w * r.uniform(0.45, 0.8); sx = cx + r.uniform(-0.5, 0.5) * w; st = top - r.uniform(0, 0.25) * tall
            m = np.abs(xs - sx) < sw
            dome = st - tall * 0.6 + tall * 0.6 * np.sqrt(np.clip(1 - ((xs[m] - sx) / sw) ** 2, 0, 1))
            h[m] = np.maximum(h[m], dome)
        x = cx + w * r.uniform(0.2, 0.6)
    h += 0.22 * fbm(((0.6, 1.0), (0.25, 0.7), (0.12, 0.4)))
    bm = bmesh.new()
    top = [bm.verts.new((xs[i], y0, h[i])) for i in range(n)]
    bot = [bm.verts.new((xs[i], y0, -2.0)) for i in range(n)]
    for i in range(n - 1):
        bm.faces.new([bot[i], bot[i + 1], top[i + 1], top[i]])
    S.mesh_obj(name, bm, S.pbr_simple('Pv_TreeLine', (0.010, 0.012, 0.010), 0.8))


def ridge(R, az0, az1, hmin, hmax, seed, name, col):
    r = np.random.default_rng(seed)
    n = 1400
    az = np.radians(np.linspace(az0, az1, n))
    prof = np.zeros(n)
    for k, amp in ((6, 1.0), (17, 0.5), (45, 0.22), (130, 0.10), (400, 0.04)):
        prof += amp * np.interp(np.linspace(0, 1, n), np.linspace(0, 1, k), r.uniform(-1, 1, k))
    prof = (prof - prof.min()) / (prof.max() - prof.min())
    h = hmin + (hmax - hmin) * prof ** 1.3
    bm = bmesh.new()
    top = [bm.verts.new((R * math.cos(a), -R * math.sin(a), h[i])) for i, a in enumerate(az)]
    bot = [bm.verts.new((R * math.cos(a), -R * math.sin(a), -5.0)) for a in az]
    for i in range(n - 1):
        bm.faces.new([bot[i], bot[i + 1], top[i + 1], top[i]])
    S.mesh_obj(name, bm, S.pbr_simple(name + '_M', col, 0.9))


ridge(760.0, -110, 110, 25.0, 95.0, 31, 'Rn_Hills', (0.006, 0.007, 0.009))
treeline(-95.0, -160, 200, 6.0, 13.0, 21, 'Rn_TreeLine')
treeline(-160.0, -260, 300, 8.0, 16.0, 22, 'Rn_TreeLine2')
treeline(60.0, -200, 260, 5.0, 11.0, 23, 'Rn_TreeLineFar')
S.town_lights()
S.place_sign_kit('ZH')
case = S.notice_case(light_on=False, glass_drops=0.8)
case['glass'].visible_shadow = False        # the lamp lights the sheet through the glass (it was a black slab)
S.beam_cones(float(os.environ.get('BEAMS', '0.10')))   # bible §6·1: the headlight beams dissolve into the fog ahead


def beams_low():
    """low beams light the rain and the spray near the road, not the sky: fade the fake cone with height (else its
    far end reads as a pale arch over the hills)."""
    m = bpy.data.materials['Pv_BeamMat']; nt = m.node_tree
    em = [n for n in nt.nodes if n.bl_idname == 'ShaderNodeEmission'][0]
    src = em.inputs[1].links[0].from_socket
    geo = nt.nodes.new('ShaderNodeNewGeometry'); sp = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(geo.outputs['Position'], sp.inputs[0])
    mr = nt.nodes.new('ShaderNodeMapRange'); mr.clamp = True
    mr.inputs[1].default_value = 2.4; mr.inputs[2].default_value = 0.3; mr.inputs[3].default_value = 0.0; mr.inputs[4].default_value = 1.0
    nt.links.new(sp.outputs['Z'], mr.inputs[0])
    pw = nt.nodes.new('ShaderNodeMath'); pw.operation = 'POWER'; pw.inputs[1].default_value = 1.5; nt.links.new(mr.outputs[0], pw.inputs[0])
    mu = nt.nodes.new('ShaderNodeMath'); mu.operation = 'MULTIPLY'; nt.links.new(src, mu.inputs[0]); nt.links.new(pw.outputs[0], mu.inputs[1])
    nt.links.new(mu.outputs[0], em.inputs[1])


beams_low()


# ---------------------------------------------------------------------------------------------- textures
def img(path, colorspace='Non-Color', packed=False):
    im = bpy.data.images.load(path, check_existing=True)
    im.colorspace_settings.name = colorspace
    if packed:
        im.alpha_mode = 'CHANNEL_PACKED'
    return im


# ---- puddle rings: the kit's procedural cells + the drip rings, baked into one normal map (stage x, y)
RX0, RX1, RY0, RY1 = -14.0, 10.0, -4.4, 6.6
RPX = float(os.environ.get('RPX', '0.004'))
DRIPS = [((2.83, -1.86), 0.62), ((6.88, -3.07), 1.45)]
PIX_ANG = (36.0 / LENS) / W


def ripple_normal_png():
    from PIL import Image
    nx, ny = int((RX1 - RX0) / RPX), int((RY1 - RY0) / RPX)
    xs = RX0 + (np.arange(nx) + 0.5) * RPX
    out = np.zeros((ny, nx, 3), np.uint16)
    for j0 in range(0, ny, 200):
        ys = RY0 + (np.arange(j0, min(ny, j0 + 200)) + 0.5) * RPX
        Xb, Yb = np.meshgrid(xs, ys)
        Xu, Zu = -Yb, Xb                                         # Unity stop-local (X, Z)
        d = np.sqrt((Xb - CAM.x) ** 2 + (Yb - CAM.y) ** 2 + CAM.z ** 2)
        cosi = CAM.z / d
        bl = CR.ring_band(d * PIX_ANG / np.maximum(cosi, 0.2))
        sX, sZ = CR.cells(Xu, Zu, T_RAIN, 4.0, bl)
        for (dx_, dy_), age in DRIPS:
            a, b = CR.drip(Xu, Zu, -dy_, dx_, age, bl)
            sX += a; sZ += b
        sxb = sZ; syb = -sX                                      # dh/dx_b = dh/dZ_u, dh/dy_b = -dh/dX_u
        n = np.stack([-sxb, -syb, np.ones_like(sxb)], -1); n /= np.linalg.norm(n, axis=-1, keepdims=True)
        out[j0:j0 + n.shape[0]] = np.round((n * 0.5 + 0.5) * 65535).astype(np.uint16)
    p = os.path.join(OUT, 'ripple_cells_normal.exr')
    im = bpy.data.images.new('ripN', nx, ny, alpha=False, float_buffer=True)
    im.colorspace_settings.name = 'Non-Color'          # else Image.save() bakes the view transform into the EXR
    rgba = np.concatenate([out.astype(np.float32) / 65535.0, np.ones((ny, nx, 1), np.float32)], -1)
    im.pixels.foreach_set(rgba.ravel())                # Blender rows: bottom first = our row order (y up)
    im.filepath_raw = p; im.file_format = 'OPEN_EXR'; im.save()
    print('ripple map', nx, ny)
    return p


RIPPLE = ripple_normal_png()


# ---------------------------------------------------------------------------------------------- Lanbai/WetSurface port
def wet_material(name, prefix, tile, s_dry, porosity, normal_dry=1.0):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    film = N('ShaderNodeBsdfPrincipled')
    geo = N('ShaderNodeNewGeometry')
    sep = N('ShaderNodeSeparateXYZ'); L(geo.outputs['Position'], sep.inputs[0])

    def math_(op, a, b=None):
        n = N('ShaderNodeMath'); n.operation = op
        for k, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (int, float)):
                n.inputs[k].default_value = x
            else:
                L(x, n.inputs[k])
        return n.outputs[0]

    def vmath(op, a, b=None, sc_=None):
        n = N('ShaderNodeVectorMath'); n.operation = op
        for k, x in enumerate((a, b)):
            if x is None:
                continue
            if isinstance(x, (tuple, list, Vector)):
                n.inputs[k].default_value = tuple(x)
            else:
                L(x, n.inputs[k])
        if sc_ is not None:
            if isinstance(sc_, (int, float)):
                n.inputs['Scale'].default_value = sc_
            else:
                L(sc_, n.inputs['Scale'])
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']

    def comb(x, y):
        c = N('ShaderNodeCombineXYZ'); L(x, c.inputs[0]); L(y, c.inputs[1]); return c.outputs[0]

    def tex(path, vec, cs='Non-Color', packed=False, interp='Linear', ext='REPEAT'):
        t = N('ShaderNodeTexImage'); t.image = img(path, cs, packed=packed); t.interpolation = interp; t.extension = ext
        L(vec, t.inputs[0]); return t

    def mixf(fac, a, b):
        n = N('ShaderNodeMix'); n.data_type = 'FLOAT'
        for sock, x in (('Factor', fac), ('A', a), ('B', b)):
            if isinstance(x, (int, float)):
                n.inputs[sock].default_value = x
            else:
                L(x, n.inputs[sock])
        return n.outputs[0]

    def mixc(fac, a, b, dtype='RGBA'):
        n = N('ShaderNodeMix'); n.data_type = dtype
        if isinstance(fac, (int, float)):
            n.inputs['Factor'].default_value = fac
        else:
            L(fac, n.inputs['Factor'])
        idx_a = {'RGBA': 6, 'VECTOR': 4}[dtype]; idx_b = idx_a + 1
        for s_, x in ((idx_a, a), (idx_b, b)):
            if isinstance(x, tuple):
                n.inputs[s_].default_value = x
            else:
                L(x, n.inputs[s_])
        return n.outputs[{'RGBA': 2, 'VECTOR': 1}[dtype]]

    x, y = sep.outputs[0], sep.outputs[1]
    uvA = comb(math_('DIVIDE', x, tile), math_('DIVIDE', y, tile))
    alb = tex(os.path.join(PV, 'Pv_%s_Albedo.png' % prefix), uvA, 'sRGB')
    nrm = tex(os.path.join(PV, 'Pv_%s_Normal.png' % prefix), uvA)
    hgt = tex(os.path.join(PV, 'Pv_%s_Height.png' % prefix), uvA)
    # masks: Stop_WetMask inside its rect, Road_WetMask (period 60 m from Z_u = -21) outside: README §4
    uvS = comb(math_('DIVIDE', math_('ADD', x, 22.0), 48.0), math_('DIVIDE', math_('ADD', y, 5.0), 12.0))
    uvR = comb(math_('DIVIDE', math_('ADD', x, 21.0), 60.0), math_('DIVIDE', math_('ADD', y, 5.0), 12.0))
    mS = tex(RP.find('Stop_WetMask_2048x512.png'), uvS, packed=True, ext='CLIP')
    mR = tex(RP.find('Road_WetMask_2048x512.png'), uvR, packed=True, ext='REPEAT')
    inside = math_('MULTIPLY', math_('GREATER_THAN', x, -22.0), math_('LESS_THAN', x, 26.0))
    col = mixc(inside, mR.outputs['Color'], mS.outputs['Color'])
    A = mixf(inside, mR.outputs['Alpha'], mS.outputs['Alpha'])
    sc_ = N('ShaderNodeSeparateColor'); L(col, sc_.inputs[0])
    R, G, B = sc_.outputs[0], sc_.outputs[1], sc_.outputs[2]
    wfilm = math_('SUBTRACT', 1.0, B)                                        # wet = 1 (scene 1)
    depthN = math_('MULTIPLY', R, R)
    shore = math_('ADD', depthN, math_('MULTIPLY', math_('SUBTRACT', hgt.outputs['Color'], 0.5), 0.06))
    mr = N('ShaderNodeMapRange'); mr.interpolation_type = 'SMOOTHSTEP'
    mr.inputs[1].default_value = 0.0; mr.inputs[2].default_value = 0.05; L(shore, mr.inputs[0])
    puddle = math_('MULTIPLY', math_('MULTIPLY', mr.outputs[0], math_('GREATER_THAN', R, 0.004)), wfilm)
    # ---- film (Principled, physical): albedo x porosity, smoothness 0.74-0.84 by G, normals x0.6
    mul = mixf(B, mixf(wfilm, 1.0, porosity), 0.8)
    a1 = N('ShaderNodeMix'); a1.data_type = 'RGBA'; a1.blend_type = 'MULTIPLY'; a1.inputs['Factor'].default_value = 1.0
    L(alb.outputs['Color'], a1.inputs[6]); L(mul, a1.inputs[7])
    paint = mixc(A, a1.outputs[2], (0.45, 0.45, 0.44, 1.0))
    L(paint, film.inputs['Base Color'])
    sm = mixf(wfilm, s_dry, math_('ADD', 0.74, math_('MULTIPLY', G, 0.10)))
    sm = mixf(B, sm, 0.45)
    sm = mixf(A, sm, mixf(wfilm, 0.35, 0.70))
    L(math_('SUBTRACT', 1.0, sm), film.inputs['Roughness'])
    film.inputs['IOR'].default_value = 1.5
    nmF = N('ShaderNodeNormalMap'); L(nrm.outputs['Color'], nmF.inputs['Color'])
    L(mixf(wfilm, normal_dry, normal_dry * 0.6), nmF.inputs['Strength'])
    L(nmF.outputs[0], film.inputs['Normal'])
    # ---- puddle: rings normal (cells + drips), dark bottom, the kit's still-water mirror
    uvP = comb(math_('DIVIDE', math_('SUBTRACT', x, RX0), RX1 - RX0), math_('DIVIDE', math_('SUBTRACT', y, RY0), RY1 - RY0))
    rip = tex(RIPPLE, uvP, ext='EXTEND')
    nmR = N('ShaderNodeNormalMap'); L(rip.outputs['Color'], nmR.inputs['Color'])
    Np = nmR.outputs[0]
    # R(theta) = R0 + (1 - R0) (1 - cos)^5 ; cos with the rippled normal
    cosv = vmath('DOT_PRODUCT', Np, geo.outputs['Incoming'])
    one_m = math_('SUBTRACT', 1.0, math_('MAXIMUM', cosv, 0.0))
    Rth = math_('ADD', MIRROR_R0, math_('MULTIPLY', 1.0 - MIRROR_R0, math_('POWER', one_m, 5.0)))
    # the tube's image: the reflected ray passes within the tube's radius -> weight so that its core = _LampPeak
    Rv = vmath('SUBTRACT', vmath('SCALE', Np, None, math_('MULTIPLY', cosv, 2.0)), geo.outputs['Incoming'])
    A0 = TUBE_P - TUBE_AX; SEG = TUBE_AX * 2.0
    L0 = vmath('SUBTRACT', tuple(A0), geo.outputs['Position'])
    RoS = vmath('DOT_PRODUCT', Rv, tuple(SEG))
    num = math_('SUBTRACT', math_('MULTIPLY', vmath('DOT_PRODUCT', Rv, L0), RoS), vmath('DOT_PRODUCT', L0, tuple(SEG)))
    den = math_('MAXIMUM', math_('SUBTRACT', SEG.dot(SEG), math_('MULTIPLY', RoS, RoS)), 1e-6)
    tt = math_('MINIMUM', math_('MAXIMUM', math_('DIVIDE', num, den), 0.0), 1.0)
    Lv = vmath('ADD', L0, vmath('SCALE', tuple(SEG), None, tt))
    perp = vmath('SUBTRACT', Lv, vmath('SCALE', Rv, None, vmath('DOT_PRODUCT', Lv, Rv)))
    dist = vmath('LENGTH', perp)
    hm = N('ShaderNodeMapRange'); hm.interpolation_type = 'SMOOTHSTEP'
    hm.inputs[1].default_value = 0.020; hm.inputs[2].default_value = 0.010; L(dist, hm.inputs[0])
    hit = math_('MULTIPLY', hm.outputs[0], math_('GREATER_THAN', vmath('DOT_PRODUCT', Lv, Rv), 0.0))
    w_hit = LAMP_PEAK / K / L_GLOSSY_MAX
    weight = mixf(hit, Rth, w_hit)
    gl = N('ShaderNodeBsdfGlossy'); gl.distribution = 'GGX'; gl.inputs['Roughness'].default_value = 0.03
    gl.inputs['Color'].default_value = (1, 1, 1, 1); L(Np, gl.inputs['Normal'])
    a2 = N('ShaderNodeMix'); a2.data_type = 'RGBA'; a2.blend_type = 'MULTIPLY'; a2.inputs['Factor'].default_value = 1.0
    L(alb.outputs['Color'], a2.inputs[6]); a2.inputs[7].default_value = (0.25, 0.25, 0.25, 1.0)
    dif = N('ShaderNodeBsdfDiffuse'); L(a2.outputs[2], dif.inputs['Color'])
    pm = N('ShaderNodeMixShader'); L(weight, pm.inputs[0]); L(dif.outputs[0], pm.inputs[1]); L(gl.outputs[0], pm.inputs[2])
    fin = N('ShaderNodeMixShader'); L(puddle, fin.inputs[0]); L(film.outputs[0], fin.inputs[1]); L(pm.outputs[0], fin.inputs[2])
    L(fin.outputs[0], out.inputs[0])
    return m


road = bpy.data.objects['Pv_Road']; road.data.materials.clear(); road.data.materials.append(wet_material('Rn_Road', 'Asphalt', 2.0, 0.20, 0.5))
sh = bpy.data.objects['Pv_Shoulder']; sh.data.materials.clear(); sh.data.materials.append(wet_material('Rn_Shoulder', 'Gravel', 2.0, 0.25, 0.55, 1.3))


# ---------------------------------------------------------------------------------------------- rain (Lanbai/RainParticles)
def seg_closest(p, c, ax):
    a = c - ax; s = 2 * ax
    t = max(0.0, min(1.0, -(a - p).dot(s) / max(s.dot(s), 1e-9)))
    return a + s * t


def phase(c):
    f = max(0.0, min(1.0, 0.5 + 0.5 * c))
    return 0.30 + 2.6 * f ** 6 + 6.0 * f ** 40


def rain_light(p):
    """LanbaiRainLight (Unity units) for the tube + the two headlights; returns linear rgb."""
    to_eye = (CAM - p).normalized()
    q = seg_closest(p, TUBE_P, TUBE_AX)
    l = q - p; d2 = max(l.length_squared, 0.09)
    cone = 1.0 if (p - TUBE_P).normalized().z < -0.05 else 0.0                     # trough: lower hemisphere
    e = I_TUBE / d2 * cone * phase((-l.normalized()).dot(to_eye))
    col = [e * c for c in TUBE_COL]
    for h in HEADLIGHTS:
        l = h - p; d2 = max(l.length_squared, 0.09)
        c = (p - h).normalized().dot(Vector((0.985, 0.0, -0.17)))
        cone = max(0.0, min(1.0, (c - 0.874) / 0.16))
        e = I_HEAD / d2 * cone * phase((-l.normalized()).dot(to_eye))
        col = [col[k] + e * HEAD_COL[k] for k in range(3)]
    return col


def particle_material(name, atlas):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    N, L = nt.nodes.new, nt.links.new
    out = N('ShaderNodeOutputMaterial')
    uv = N('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    t = N('ShaderNodeTexImage'); t.image = img(atlas, packed=True); t.interpolation = 'Linear'; t.extension = 'CLIP'
    L(uv.outputs[0], t.inputs[0])
    at = N('ShaderNodeVertexColor'); at.layer_name = 'lit'
    sepc = N('ShaderNodeSeparateColor'); L(t.outputs['Color'], sepc.inputs[0])
    lum = N('ShaderNodeMath'); lum.operation = 'MULTIPLY'; L(sepc.outputs[0], lum.inputs[0]); L(t.outputs['Alpha'], lum.inputs[1])
    em = N('ShaderNodeEmission'); L(at.outputs['Color'], em.inputs['Color']); L(lum.outputs[0], em.inputs['Strength'])
    tr = N('ShaderNodeBsdfTransparent')
    add = N('ShaderNodeAddShader'); L(tr.outputs[0], add.inputs[0]); L(em.outputs[0], add.inputs[1])
    L(add.outputs[0], out.inputs[0])
    return m


def build_streaks(name, positions, ambient=0.0):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    cl = bm.loops.layers.float_color.new('lit')
    slant = math.radians(8.0)
    d = Vector((math.sin(slant), 0.0, -math.cos(slant)))
    amb = (0.323, 0.371, 0.402)
    n = 0
    for p in positions:
        c = rain_light(p)
        colv = [(c[k] * GAIN * TINT[k] + amb[k] * ambient) / K for k in range(3)]
        if max(colv) < 2e-4:
            continue
        L_ = rng.uniform(0.25, 0.40)
        width = rng.uniform(0.032, 0.048)                       # README §3: quad 32-48 mm -> visible line 4-6 mm
        side = d.cross(p - CAM).normalized() * (width / 2)
        p0 = p; p1 = p + d * L_
        vs = [bm.verts.new(p0 - side), bm.verts.new(p0 + side), bm.verts.new(p1 + side), bm.verts.new(p1 - side)]
        f = bm.faces.new(vs)
        cell = int(rng.integers(0, 8))
        for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):    # head (v = 1) at the lower end p1
            lp[uvl].uv = ((cell + uv[0]) / 8.0, uv[1])
            lp[cl] = (*colv, 1.0)
        n += 1
    me = bpy.data.meshes.new(name); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(name, me); bpy.context.scene.collection.objects.link(ob)
    me.materials.append(particle_material(name + '_M', RP.find('RainStreak_Atlas8x1_512.png')))
    ob.visible_shadow = False; ob.visible_diffuse = False
    print(name, n, 'streaks')
    return ob


def cyl_points(c, r, h, n, z0=0.02):
    pts = []
    for i in range(n):
        rr = r * math.sqrt(rng.random()); a = rng.uniform(0, 2 * math.pi)
        pts.append(Vector((c.x + rr * math.cos(a), c.y + rr * math.sin(a), rng.uniform(z0, h))))
    return pts


build_streaks('Pv_Rain_Cone', cyl_points(Vector((TUBE_P.x, TUBE_P.y, 0)), 5.0, 5.0, 1800))
beam_pts = []
for i in range(900):                                            # headlight beams: 22 m forward, 35 deg
    hsel = HEADLIGHTS[i % 2]
    t = rng.uniform(1.5, 22.0); a = rng.uniform(0, 2 * math.pi); rr = math.tan(math.radians(17.5)) * t * math.sqrt(rng.random())
    beam_pts.append(Vector((hsel.x + t, hsel.y + rr * math.cos(a), max(0.05, hsel.z - 0.17 * t + rr * math.sin(a)))))
build_streaks('Pv_Rain_Beams', beam_pts)
build_streaks('Pv_Rain_Ambient', [Vector((rng.uniform(-10, 14), rng.uniform(-6, 7), rng.uniform(0.05, 6))) for _ in range(560)], ambient=0.06)


def build_splashes(n=26):
    bm = bmesh.new()
    uvl = bm.loops.layers.uv.new('UVMap')
    cl = bm.loops.layers.float_color.new('lit')
    size = 0.048 / 0.84                                         # the re-packed atlas: a cell spans 57 mm
    for i in range(n):
        r = 3.8 * math.sqrt(rng.random()); a = rng.uniform(0, 2 * math.pi)
        p = Vector((TUBE_P.x + r * math.cos(a), TUBE_P.y + 0.6 + r * math.sin(a), 0.0))
        if p.y > 6.4 or p.y < -4.0:
            continue
        c = rain_light(p + Vector((0, 0, 0.01)))
        colv = [ci * 0.03 / K for ci in c]
        fwd = (CAM - p); fwd.z = 0; fwd.normalize()
        right = Vector((0, 0, 1)).cross(fwd).normalized() * (size / 2)
        up = Vector((0, 0, 1)) * size
        base = p - up * 0.125
        vs = [bm.verts.new(base - right), bm.verts.new(base + right), bm.verts.new(base + right + up), bm.verts.new(base - right + up)]
        f = bm.faces.new(vs)
        fr = int(rng.integers(1, 12)); rr_, cc_ = divmod(fr, 4)
        for lp, uv in zip(f.loops, ((0, 0), (1, 0), (1, 1), (0, 1))):
            lp[uvl].uv = ((cc_ + uv[0]) / 4.0, (3 - rr_ + uv[1]) / 4.0)
            lp[cl] = (*colv, 1.0)
    me = bpy.data.meshes.new('Pv_Rain_Splash'); bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new('Pv_Rain_Splash', me); bpy.context.scene.collection.objects.link(ob)
    me.materials.append(particle_material('Pv_Rain_Splash_M', RP.find('RainSplash_Flip4x4_512.png')))
    ob.visible_shadow = False; ob.visible_diffuse = False


build_splashes()

# ---------------------------------------------------------------------------------------------- shots
SHOT = os.environ.get('SHOT', 'spawn')


def hero_pane():
    """the hero window (bible §4.6, §3.3): the last side pane before the door, x -2.26 .. -1.32, z 1.55 .. 2.35. Its outer
    face carries the normal map glass_normals.py composed with the kit's maths (beads, runners, the one drop) inside
    REGION, the plain tiled beads around it; a 5 mm slab of water-glass, so Cycles refracts the world through every drop
    and the inner face reflects the lit cabin."""
    GL = os.environ.get('GLDIR', os.path.join(PV, 'glassN'))
    meta = json.load(open(os.path.join(GL, 'glass_normal.json')))
    gx0, gx1, gz0, gz1 = meta['region']
    old = bpy.data.objects['Rn_BusWindows']
    bm = bmesh.new(); bm.from_mesh(old.data)
    for v in bm.verts:                                  # the general slab now ends at the last pillar
        if v.co.x > -2.30: v.co.x = -2.30
    bm.to_mesh(old.data); bm.free()
    bn = bpy.data.images.load(RP.find('RainBeads_Vertical_Normal_1024.png'), check_existing=True)
    bn.colorspace_settings.name = 'Non-Color'
    gn = bpy.data.images.load(os.path.join(GL, 'glass_normal.exr')); gn.colorspace_settings.name = 'Non-Color'
    m = bpy.data.materials.new('Rn_HeroWater'); m.use_nodes = True; nt = m.node_tree; nt.nodes.clear()
    N_, L_ = nt.nodes.new, nt.links.new
    o = N_('ShaderNodeOutputMaterial'); g = N_('ShaderNodeBsdfGlass')
    g.inputs['Color'].default_value = (*S.lin('#E9EFEA'), 1); g.inputs['IOR'].default_value = 1.333; g.inputs['Roughness'].default_value = 0.0
    geo = N_('ShaderNodeNewGeometry'); sp = N_('ShaderNodeSeparateXYZ'); L_(geo.outputs['Position'], sp.inputs[0])
    def mth(op, a, b):
        n = N_('ShaderNodeMath'); n.operation = op
        for k, x in enumerate((a, b)):
            if isinstance(x, (int, float)): n.inputs[k].default_value = x
            else: L_(x, n.inputs[k])
        return n.outputs[0]
    cu = N_('ShaderNodeCombineXYZ'); L_(mth('DIVIDE', mth('SUBTRACT', sp.outputs[0], gx0), gx1 - gx0), cu.inputs[0])
    L_(mth('DIVIDE', mth('SUBTRACT', sp.outputs[2], gz0), gz1 - gz0), cu.inputs[1])
    tg = N_('ShaderNodeTexImage'); tg.image = gn; tg.interpolation = 'Cubic'; tg.extension = 'EXTEND'; L_(cu.outputs[0], tg.inputs[0])
    ct = N_('ShaderNodeCombineXYZ'); L_(mth('DIVIDE', sp.outputs[0], 0.2), ct.inputs[0]); L_(mth('DIVIDE', sp.outputs[2], 0.2), ct.inputs[1])
    tb = N_('ShaderNodeTexImage'); tb.image = bn; tb.interpolation = 'Cubic'; L_(ct.outputs[0], tb.inputs[0])
    inside = mth('MULTIPLY', mth('MULTIPLY', mth('GREATER_THAN', sp.outputs[0], gx0), mth('LESS_THAN', sp.outputs[0], gx1)),
                 mth('MULTIPLY', mth('GREATER_THAN', sp.outputs[2], gz0), mth('LESS_THAN', sp.outputs[2], gz1)))
    mx = N_('ShaderNodeMix'); mx.data_type = 'RGBA'; L_(inside, mx.inputs['Factor']); L_(tb.outputs['Color'], mx.inputs[6]); L_(tg.outputs['Color'], mx.inputs[7])
    nm = N_('ShaderNodeNormalMap'); nm.uv_map = 'UVMap'; L_(mx.outputs[2], nm.inputs['Color'])
    gi = bpy.data.materials['Rn_WinGlass']
    if GLASS_MODE == 'mask':
        # the water coverage of the pane as seen by the camera (for the tilt composite): emission = how far the outer
        # face's normal leans off flat; the inner face only REFRACTS (no reflection), so the mask registers exactly with
        # the 'drops' render (the 5 mm slab shifts the view by ~3 mm at this incidence)
        sc_ = N_('ShaderNodeSeparateColor'); L_(mx.outputs[2], sc_.inputs[0])
        def sq(x):
            a = mth('SUBTRACT', x, 0.5); return mth('MULTIPLY', a, a)
        dev = mth('SQRT', mth('ADD', sq(sc_.outputs[0]), sq(sc_.outputs[1])), 0.0)
        mr_ = N_('ShaderNodeMapRange'); mr_.interpolation_type = 'SMOOTHSTEP'; L_(dev, mr_.inputs[0])
        mr_.inputs[1].default_value = 0.004; mr_.inputs[2].default_value = 0.02
        em_ = N_('ShaderNodeEmission'); em_.inputs[0].default_value = (1, 1, 1, 1); L_(mr_.outputs[0], em_.inputs[1])
        L_(em_.outputs[0], o.inputs[0])
        gi = bpy.data.materials.new('Rn_MaskInner'); gi.use_nodes = True; nti = gi.node_tree; nti.nodes.clear()
        oi = nti.nodes.new('ShaderNodeOutputMaterial'); rf = nti.nodes.new('ShaderNodeBsdfRefraction')
        rf.inputs['IOR'].default_value = 1.333; rf.inputs['Color'].default_value = (1, 1, 1, 1); rf.inputs['Roughness'].default_value = 0.0
        nti.links.new(rf.outputs[0], oi.inputs[0])
    elif GLASS_MODE == 'clear':
        L_(g.outputs[0], o.inputs[0])                    # flat water-glass: what the window shows with no drops
    else:
        L_(nm.outputs[0], g.inputs['Normal'])
        L_(g.outputs[0], o.inputs[0])
    y0 = S.BUS_Y0; xa, xb, za, zb = -2.26, -1.32, 1.55, 2.35
    bm = bmesh.new(); uv = bm.loops.layers.uv.new('UVMap')
    v = {}
    for xi, xx in ((0, xa), (1, xb)):
        for zi, zz in ((0, za), (1, zb)):
            for yi, yy in ((0, y0 - 0.002), (1, y0 + 0.003)):
                v[(xi, zi, yi)] = bm.verts.new((xx, yy, zz))
    outer = bm.faces.new([v[(0, 0, 0)], v[(1, 0, 0)], v[(1, 1, 0)], v[(0, 1, 0)]])     # faces -y (outside)
    inner = bm.faces.new([v[(0, 0, 1)], v[(0, 1, 1)], v[(1, 1, 1)], v[(1, 0, 1)]])
    for f in (outer, inner):
        for lp in f.loops:
            lp[uv].uv = (lp.vert.co.x, lp.vert.co.z)                                  # +u = +x, +v = +z: N = -y
    outer.normal_update(); inner.normal_update()
    if outer.normal.y > 0: outer.normal_flip()
    if inner.normal.y < 0: inner.normal_flip()
    outer.material_index = 0; inner.material_index = 1
    ob = S.mesh_obj('Rn_HeroPane', bm, m); ob.data.materials.append(gi); ob.visible_shadow = False
    return ob


GLASS_MODE = os.environ.get('GLASS_MODE', 'drops')     # drops | clear | mask (the tilt composite, tilt_composite.py)
if SHOT == 'window':
    hero_pane()
    if GLASS_MODE == 'mask':
        for o_ in bpy.data.objects:
            if o_.type != 'CAMERA' and o_.name != 'Rn_HeroPane':
                o_.hide_render = True
        _wm = bpy.data.worlds.new('Rn_MaskWorld'); _wm.use_nodes = True
        _wm.node_tree.nodes['Background'].inputs[0].default_value = (0, 0, 0, 1); sc.world = _wm
        sc.cycles.use_denoising = False
    FOCUS = float(os.environ.get('FOCUS', '0.27'))
    cam = S.camera('Cam_Window', CAM, AIM, lens=LENS, sensor=36,
                   dof_dist=None if os.environ.get('NODOF') else FOCUS, fstop=float(os.environ.get('FSTOP', '3.2')))
    if not os.environ.get('NODOF'):
        cam.data.dof.aperture_blades = 0
    cam.data.clip_start = 0.01
else:
    cam = S.camera('Cam_Spawn', CAM, AIM, lens=LENS, sensor=36)
halo = S.lamp_halo(0.20, 1.6, cam)
# the halo card sits BEHIND the lamp (lit mist beyond it), scaled to the same angular size: the arm and the pole
# then read as clean dark silhouettes against the glow instead of being cut by a card through them
bpy.context.view_layer.update()
dvec = (S.LAMP_POS - CAM); dd = dvec.length; push = 2.2
halo.location = S.LAMP_POS + Vector((0, 0, -0.05)) + dvec.normalized() * push
halo.scale = ((dd + push) / dd,) * 3
# a lamp in drizzle glows with a soft core and a long faint tail, not a disc with an edge: steeper falloff on the card,
# plus one wide, very faint glow (the lit mist out to ~4 m)
for _n in bpy.data.materials['Pv_HaloMat'].node_tree.nodes:
    if _n.bl_idname == 'ShaderNodeMath' and _n.operation == 'POWER':
        _n.inputs[1].default_value = float(os.environ.get('HALO_POW', '3.2'))
halo2 = S.lamp_halo(float(os.environ.get('HALO_WIDE', '0.030')), 4.5, cam)
halo2.name = 'Pv_HaloWide'
for _n in halo2.data.materials[0].node_tree.nodes:
    if _n.bl_idname == 'ShaderNodeMath' and _n.operation == 'POWER':
        _n.inputs[1].default_value = 1.6
halo2.location = S.LAMP_POS + Vector((0, 0, -0.30)) + dvec.normalized() * (push + 1.0)
halo2.scale = ((dd + push + 1.0) / dd,) * 3

for _nm in os.environ.get('HIDE', '').split(','):
    for o_ in bpy.data.objects:
        if _nm and o_.name.startswith(_nm):
            o_.hide_render = True
# Unity's reflections (probes, the stencil mirror) never contain the rain particles: neither do ours
if not os.environ.get('GLOSSY_RAIN'):
    for o_ in bpy.data.objects:
        if o_.name.startswith('Pv_Rain'):
            o_.visible_glossy = False
if os.environ.get('BORDER'):                      # test crops: x0,y0,x1,y1 in 0..1 (y up)
    _b = [float(v) for v in os.environ['BORDER'].split(',')]
    sc.render.use_border = True; sc.render.use_crop_to_border = True
    sc.render.border_min_x, sc.render.border_min_y, sc.render.border_max_x, sc.render.border_max_y = _b
exr = os.path.join(OUT, 'stop.exr'); dexr = os.path.join(OUT, 'stop_depth.exr')
S.render_exr(exr, dexr)


def load(path):
    im = bpy.data.images.load(path)
    a = np.array(im.pixels[:], dtype=np.float32).reshape(im.size[1], im.size[0], 4)[::-1]
    return a


np.save(os.path.join(OUT, 'stop.npy'), load(exr)[..., :3])
np.save(os.path.join(OUT, 'stop_depth.npy'), load(dexr)[..., 0])
json.dump(dict(camera=list(CAM), aim=list(AIM), lens=LENS, K=K, t_rain=T_RAIN), open(os.path.join(OUT, 'stop_meta.json'), 'w'))
print('done')
