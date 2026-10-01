import sys, os, numpy as np
import bpy
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import addon_utils
addon_utils.enable('io_scene_fbx')
import io_scene_fbx.parse_fbx as pf
import kit_mesh as K, tear_def as T
path = '../../deliver/Tear/FBX/Tear_Kit.fbx'
root, ver = pf.parse(path)
print('FBX version', ver)
def find(elem, name):
    return [e for e in elem.elems if e.id == name]
objs = find(root, b'Objects')[0]
geoms = [e for e in objs.elems if e.id == b'Geometry']
src = {p['name']: p for p in K.all_parts()}
for g in geoms:
    nm = g.props[1].split(b'\x00')[0].decode()
    V = np.array([e for e in g.elems if e.id == b'Vertices'][0].props[0]).reshape(-1, 3)
    uvl = [e for e in g.elems if e.id == b'LayerElementUV']
    col = [e for e in g.elems if e.id == b'LayerElementColor']
    nrm = [e for e in g.elems if e.id == b'LayerElementNormal']
    s = src.get(nm)
    msg = ''
    if s is not None and len(s['V']) == len(V):
        m = np.stack([s['V'][:, 0], s['V'][:, 2], -s['V'][:, 1]], 1)
        msg = 'max|fbx - (x,z,-y)| = %.2e' % np.abs(V - m).max()
    print('%-15s verts %5d  uvLayers %d  colorLayers %d  normalLayers %d  %s' % (nm, len(V), len(uvl), len(col), len(nrm), msg))
# settings
gs = find(root, b'GlobalSettings')[0]
for p in find(gs, b'Properties70')[0].elems:
    if p.props[0] in (b'UpAxis', b'FrontAxis', b'CoordAxis', b'UnitScaleFactor', b'UpAxisSign', b'FrontAxisSign'):
        print(p.props[0].decode(), p.props[-1])
# Unity object space (x flip of FBX): across / axis vectors
AC_u = np.array([-T.AC[0], T.AC[2], -T.AC[1]]); AX_u = np.array([-T.AX[0], T.AX[2], -T.AX[1]])
print('Unity _TearAcrossOS', np.round(AC_u, 5), ' _TearAxisOS', np.round(AX_u, 5), ' front', [0, 0, 1])
# re-import to check UVs, colours, custom normals round trip
bpy.ops.wm.read_factory_settings(use_empty=True)
addon_utils.enable('io_scene_fbx')
bpy.ops.import_scene.fbx(filepath=path)
for o in bpy.data.objects:
    if o.type != 'MESH':
        print('empty', o.name, 'parent', o.parent)
        continue
    me = o.data
    uvn = [l.name for l in me.uv_layers]
    ca = [a.name for a in me.color_attributes]
    line = '%-15s parent=%s uv=%s col=%s' % (o.name, o.parent.name if o.parent else None, uvn, ca)
    if o.name in ('Tear_Shafts', 'Tear_Flap_L1', 'Tear_Rip_A', 'Tear_Lens'):
        n = np.zeros(len(me.loops) * 3); me.loops.foreach_get('normal', n); n = n.reshape(-1, 3)
        if len(uvn) > 1:
            uv1 = np.zeros(len(me.loops) * 2); me.uv_layers[1].data.foreach_get('uv', uv1)
            uv2 = np.zeros(len(me.loops) * 2); me.uv_layers[2].data.foreach_get('uv', uv2)
            line += ' uv1x[%.1f..%.1f] uv2[%.2f..%.2f]' % (uv1[0::2].min(), uv1[0::2].max(), uv2.min(), uv2.max())
        if o.name == 'Tear_Shafts' and src['Tear_Shafts'].get('N') is not None:
            s = src['Tear_Shafts']; ax = s['N'][0] / np.linalg.norm(s['N'][0])
            # imported mesh data are in Blender coords again (importer converts back)
            line += ' firstNormal %s src axis %s' % (np.round(n[0], 3), np.round(ax, 3))
    print(line)
