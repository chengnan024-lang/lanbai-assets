"""Build Tear_Kit.fbx + Tear_ShaftCard.fbx + Tear_Kit.blend + Tear_Layout.json (deliver/Tear).
usage: python3 build_kit.py"""
import os, sys, json, math, shutil
import numpy as np
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
LAN = os.path.dirname(os.path.dirname(HERE))
sys.path.insert(0, os.path.join(LAN, 'lib'))
import bpy
import tear_def as T
import kit_mesh as K
from bl import mesh_from_numpy
from export_unity import export_fbx

DEL = os.path.join(LAN, 'deliver', 'Tear')
for d in ('FBX', 'Source'):
    os.makedirs(os.path.join(DEL, d), exist_ok=True)

QUEUE = {'Tear_CloudGlow': 2988, 'Tear_SkyFolds': 2990, 'Tear_Halo': 2992, 'Tear_Lens': 2994, 'Tear_Rip': 2995,
         'Tear_Fibres': 2996, 'Tear_Shaft': 2998, 'Tear_Flap': 2450}
PART = {'Tear_Lens': 'Lens', 'Tear_Rip': 'Rip', 'Tear_Flap': 'Flap', 'Tear_Fibres': 'Fibre', 'Tear_Halo': 'Halo',
        'Tear_Shaft': 'Shaft', 'Tear_SkyFolds': 'Folds', 'Tear_CloudGlow': 'CloudGlow'}
TEXOF = {'Tear_Lens': 'Tear_Emission_2048x512.png', 'Tear_Rip': 'Tear_Rip_1024x128.png',
         'Tear_Flap': 'Tear_Flaps_1024.png', 'Tear_Fibres': 'Tear_Fibres_1024.png', 'Tear_Halo': 'Halo_512.png',
         'Tear_Shaft': 'Shaft_Gradient_256x1024.png', 'Tear_SkyFolds': 'Tear_SkyFolds_1024.png',
         'Tear_CloudGlow': 'Halo_512.png'}


def clear():
    for o in list(bpy.data.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for m in list(bpy.data.meshes):
        bpy.data.meshes.remove(m)


def make(p, parent):
    uvs = [('UVMap', p['UV0']), ('UV1', p['UV1']), ('UV2', p['UV2'])]
    cols = [('Col', p['COL'])] if p['COL'] is not None else []
    ob = mesh_from_numpy(p['name'], p['V'], p['F'], uvs=uvs, point_colors=cols, normals=p['N'])
    mat = bpy.data.materials.get(p['mat']) or bpy.data.materials.new(p['mat'])
    ob.data.materials.append(mat)
    ob.parent = parent
    return ob


def main():
    clear()
    root = bpy.data.objects.new('Tear_Root', None)
    bpy.context.scene.collection.objects.link(root)
    parts = K.all_parts()
    obs = [make(p, root) for p in parts]
    stats = {p['name']: dict(verts=int(len(p['V'])), tris=int(sum(len(f) - 2 for f in p['F'])), material=p['mat'])
             for p in parts}
    export_fbx(os.path.join(DEL, 'FBX', 'Tear_Kit.fbx'), [root] + obs)
    # single beam card for re-laying the beams between the tentacles
    sc = K.shaft_card()
    card_root = bpy.data.objects.new('Tear_ShaftCard_Root', None)
    bpy.context.scene.collection.objects.link(card_root)
    card = make(sc, card_root)
    export_fbx(os.path.join(DEL, 'FBX', 'Tear_ShaftCard.fbx'), [card])
    stats['Tear_ShaftCard'] = dict(verts=int(len(sc['V'])), tris=int(sum(len(f) - 2 for f in sc['F'])), material=sc['mat'])
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(DEL, 'Source', 'Tear_Kit.blend'))
    # sources
    for f in ('tear_def.py', 'kit_mesh.py', 'make_textures.py', 'build_kit.py', 'render_tear.py', 'bl.py', 's4.py',
              'verify_fbx.py', 'fse.py', 'metrics.py', 'tex_sheet.py', 'post.py', 'final_renders.sh'):
        shutil.copy(os.path.join(HERE, f), os.path.join(DEL, 'Source', f))

    # ------------------------------------------------------------------ layout json (Unity object space of Tear_Root)
    def u(v):     # Blender kit space -> Unity object space (FBX -Z forward / Y up, then Unity's x flip)
        v = np.asarray(v, float)
        return [round(float(-v[0]), 5), round(float(v[2]), 5), round(float(-v[1]), 5)]
    fills = json.load(open(os.path.join(os.path.dirname(HERE), 'tear_fills.json')))
    lay = {
        'about': 'Lanbai tear kit v2 (art bible 6.4, 8.1 #6). Unity object space of Tear_Root. The kit faces +Z '
                 '(put the bus on the +Z side, i.e. rotate the root so +Z points at the bus); +Y up; the pivot is the '
                 'lens axis at cloud-top height. Root scale 1 = tear height H 1000 m above the cloud top at FULL '
                 'opening. Uniform scale = H / 1000.',
        'frame_os': {'across_right': u(T.AC), 'axis_up': u(T.AX), 'toward_bus': u(-T.DEPTH),
                     'widest_point': u(T.P(T.T_W, float(T.path(np.array([T.T_W]))[0]))[()]),
                     'top_tip': u(T.P(T.T_TOP, float(T.path(np.array([T.T_TOP]))[0]))[()]),
                     'tear_light_origin_for_directional_light': u(T.P(380.0, 0.0, 60.0)[()])},
        'lens': dict(height_above_cloud_top=T.H, bottom_tip_below_cloud_top=-T.T_BOT, tilt_deg=4.0,
                     widest_at_fraction_of_height=0.40, left_share=0.45, right_share=0.55,
                     width_full_m=T.W_TOT, width_fraction_min=T.OPEN_MIN, width_fraction_max=T.OPEN_MAX,
                     emission_uv_rect_axis_m=dict(t=[T.T_MIN, T.T_MAX], a=[T.A_MIN, T.A_MAX])),
        'stages': {k: dict(D_m=v['D'], H_m=v['H'], root_scale=round(v['H'] / T.H, 4),
                           Udon_TearOpen=round(T.tear_open_param(v['open']), 3), width_fraction=v['open'],
                           Udon_RipProgress=v['rip'], bus_above_cloud_top_m=v['cam'],
                           top_elevation_deg=round(math.degrees(math.atan((v['H'] - v['cam']) / v['D'])), 1))
                   for k, v in T.STAGES.items()},
        'rips': {r['name']: dict(side='right' if r['side'] > 0 else 'left', branches_at_t_m=r['t0'],
                                 off_axis_deg=r['off'], length_root_scale_1_m=round(r['length'], 1),
                                 length_at_U7_m=round(r['length'] * 0.635, 1),
                                 width_max_root_scale_1_m=r['width'],
                                 RipProgress_window=list(r['window'])) for r in T.RIPS},
        'flaps': {f['name']: dict(side='right' if f['side'] > 0 else 'left', fold_span_t_m=[f['t0'], f['t1']],
                                  length_m=f['length'], band_in_Tear_Flaps_1024=K.FLAP_BAND[f['name']])
                  for f in T.FLAPS},
        'halo_cards': [dict(width_m=w, height_m=h, behind_lens_m=d, breath_phase_lag=ph, gain_uv2x=g)
                       for (w, h, d, ph, g) in K.HALO_CARDS],
        'shafts': [dict(start_os=u(T.P(s['t'], s['a'], -6.0)[()]), axis_os=u(K.shaft_axis(s)),
                        half_width_m=round(s['half_width'], 1), length_m=round(s['length'], 1),
                        yaw_deg=round(s['yaw'], 1), pitch_deg=round(s['pitch'], 1)) for s in K.shaft_layout()],
        'materials': {m: dict(part=PART[m], texture=TEXOF[m], render_queue=QUEUE[m]) for m in QUEUE},
        'meshes': stats,
        'fills_S4': {k: dict(screen=v['screen'], fill=v['fill_hex'], ev=v['fill_ev'], linear=v['linear'])
                     for k, v in fills.items()},
    }
    json.dump(lay, open(os.path.join(DEL, 'Tear_Layout.json'), 'w'), indent=1, ensure_ascii=False)
    print(json.dumps(stats, indent=1))


if __name__ == '__main__':
    main()
