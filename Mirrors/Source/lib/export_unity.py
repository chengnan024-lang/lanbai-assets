"""The one FBX export setting set for Lanbai → Unity 2022.3 (Built-in RP).

Blender Z-up metres → Unity Y-up metres, rotation 0 / scale 1 on import.
"""
import bpy


def export_fbx(path, objects):
    """Export exactly `objects` (and nothing else) to `path`."""
    bpy.ops.object.select_all(action='DESELECT')
    for o in objects:
        o.select_set(True)
    bpy.context.view_layer.objects.active = objects[0]
    kw = dict(
        filepath=path,
        use_selection=True,
        object_types={'EMPTY', 'MESH'},
        apply_unit_scale=True,
        apply_scale_options='FBX_SCALE_ALL',
        axis_forward='-Z',
        axis_up='Y',
        bake_space_transform=True,
        use_mesh_modifiers=True,
        mesh_smooth_type='FACE',
        use_tspace=True,
        add_leaf_bones=False,
        bake_anim=False,
        path_mode='STRIP',
        embed_textures=False,
    )
    try:
        bpy.ops.export_scene.fbx(colors_type='LINEAR', **kw)
    except TypeError:
        bpy.ops.export_scene.fbx(**kw)
    return path
