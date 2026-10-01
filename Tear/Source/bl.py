"""small bpy helpers for the tear kit v2 (fast numpy -> mesh, node building)."""
import bpy
import numpy as np


def mesh_from_numpy(name, V, F, uvs=None, point_colors=None, normals=None, smooth=True):
    """V (n,3) float, F (m,k) int (all faces same arity), uvs: list of (layer_name, (n,2) per-vertex),
    point_colors: list of (name, (n,4)), normals: (n,3) custom normals (per vertex)."""
    V = np.asarray(V, np.float32)
    F = np.asarray(F, np.int32)
    me = bpy.data.meshes.new(name)
    nv, nf, k = len(V), len(F), F.shape[1]
    me.vertices.add(nv)
    me.vertices.foreach_set('co', V.ravel())
    me.loops.add(nf * k)
    me.loops.foreach_set('vertex_index', F.ravel())
    me.polygons.add(nf)
    me.polygons.foreach_set('loop_start', (np.arange(nf) * k).astype(np.int32))
    me.update(calc_edges=True)
    me.validate(clean_customdata=False)
    li = F.ravel()
    for lname, uv in (uvs or []):
        layer = me.uv_layers.new(name=lname)
        layer.data.foreach_set('uv', np.asarray(uv, np.float32)[li].ravel())
    for cname, col in (point_colors or []):
        at = me.color_attributes.new(name=cname, type='FLOAT_COLOR', domain='POINT')
        at.data.foreach_set('color', np.asarray(col, np.float32).ravel())
    if smooth:
        me.polygons.foreach_set('use_smooth', np.ones(nf, bool))
    if normals is not None:
        n = np.asarray(normals, np.float32)
        n = n / (np.linalg.norm(n, axis=1, keepdims=True) + 1e-12)
        try:
            me.normals_split_custom_set_from_vertices(n.tolist())
        except Exception as e:  # noqa
            print('custom normals failed:', e)
    me.update()
    ob = bpy.data.objects.new(name, me)
    bpy.context.scene.collection.objects.link(ob)
    return ob


class NB:
    """tiny node-tree builder."""

    def __init__(self, nt):
        self.nt = nt
        self.N = nt.nodes.new
        self.L = nt.links.new

    def _in(self, node, i, v):
        if v is None:
            return
        sock = node.inputs[i]
        if isinstance(v, (int, float)):
            sock.default_value = v
        elif isinstance(v, tuple):
            sock.default_value = v if len(v) == len(sock.default_value) else (*v, 1.0)[:len(sock.default_value)]
        else:
            self.L(v, sock)

    def math(self, op, a=None, b=None, c=None, clamp=False):
        n = self.N('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        self._in(n, 0, a); self._in(n, 1, b)
        if c is not None:
            self._in(n, 2, c)
        return n.outputs[0]

    def vmath(self, op, a=None, b=None, scale=None):
        n = self.N('ShaderNodeVectorMath'); n.operation = op
        self._in(n, 0, a); self._in(n, 1, b)
        if scale is not None:
            self._in(n, 3, scale)
        return n.outputs['Value'] if op in ('DOT_PRODUCT', 'LENGTH', 'DISTANCE') else n.outputs['Vector']

    def mix(self, fac, a, b):
        n = self.N('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MIX'
        self._in(n, 'Factor', fac)
        self._in(n, 6, a); self._in(n, 7, b)
        return n.outputs[2]

    def mixf(self, fac, a, b):
        n = self.N('ShaderNodeMix'); n.data_type = 'FLOAT'
        self._in(n, 0, fac); self._in(n, 2, a); self._in(n, 3, b)
        return n.outputs[0]

    def rgbmul(self, a, b):
        n = self.N('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'MULTIPLY'
        n.inputs['Factor'].default_value = 1.0
        self._in(n, 6, a); self._in(n, 7, b)
        return n.outputs[2]

    def rgbadd(self, a, b):
        n = self.N('ShaderNodeMix'); n.data_type = 'RGBA'; n.blend_type = 'ADD'
        n.inputs['Factor'].default_value = 1.0
        self._in(n, 6, a); self._in(n, 7, b)
        return n.outputs[2]

    def scale(self, col, s):
        """colour * scalar (socket or float)."""
        v = self.vmath('SCALE', col, None, s)
        return v

    def gray(self, s):
        n = self.N('ShaderNodeCombineColor')
        for i in range(3):
            self._in(n, i, s)
        return n.outputs[0]

    def rgb(self, c):
        n = self.N('ShaderNodeRGB'); n.outputs[0].default_value = (*c, 1.0)
        return n.outputs[0]

    def vec(self, v):
        n = self.N('ShaderNodeCombineXYZ')
        for i in range(3):
            n.inputs[i].default_value = float(v[i])
        return n.outputs[0]

    def sep(self, v):
        n = self.N('ShaderNodeSeparateXYZ'); self.L(v, n.inputs[0])
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def sepc(self, c):
        n = self.N('ShaderNodeSeparateColor'); self.L(c, n.inputs[0])
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def smooth(self, v, lo, hi, a=0.0, b=1.0):
        n = self.N('ShaderNodeMapRange'); n.interpolation_type = 'SMOOTHSTEP'; n.clamp = True
        n.inputs['From Min'].default_value = lo; n.inputs['From Max'].default_value = hi
        n.inputs['To Min'].default_value = a; n.inputs['To Max'].default_value = b
        self._in(n, 'Value', v)
        return n.outputs['Result']

    def attr(self, name, kind='GEOMETRY'):
        n = self.N('ShaderNodeAttribute'); n.attribute_name = name; n.attribute_type = kind
        return n

    def uv(self, name):
        n = self.N('ShaderNodeUVMap'); n.uv_map = name
        return n.outputs['UV']

    def tex(self, img, vec, interp='Linear', ext='CLIP'):
        n = self.N('ShaderNodeTexImage'); n.image = img; n.interpolation = interp; n.extension = ext
        self.L(vec, n.inputs['Vector'])
        return n

    def emission(self, col, strength=1.0):
        n = self.N('ShaderNodeEmission'); self._in(n, 'Color', col); n.inputs['Strength'].default_value = strength
        return n.outputs[0]

    def transparent(self):
        return self.N('ShaderNodeBsdfTransparent').outputs[0]

    def add(self, a, b):
        n = self.N('ShaderNodeAddShader'); self.L(a, n.inputs[0]); self.L(b, n.inputs[1])
        return n.outputs[0]

    def mixs(self, fac, a, b):
        n = self.N('ShaderNodeMixShader'); self._in(n, 0, fac); self.L(a, n.inputs[1]); self.L(b, n.inputs[2])
        return n.outputs[0]

    def out(self, shader):
        o = self.N('ShaderNodeOutputMaterial'); self.L(shader, o.inputs['Surface'])


def new_mat(name):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    m.node_tree.nodes.clear()
    try:
        m.blend_method = 'BLEND'
    except Exception:
        pass
    return m, NB(m.node_tree)


def load_img(path, colorspace='sRGB', alpha_mode='STRAIGHT'):
    im = bpy.data.images.load(path, check_existing=True)
    try:
        im.colorspace_settings.name = colorspace
    except TypeError:
        im.colorspace_settings.name = 'Non-Color'
    im.alpha_mode = alpha_mode
    return im
