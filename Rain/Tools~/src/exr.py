import numpy as np


def read_exr(path):
    """read an RGBA EXR via bpy (Blender as a module)"""
    import bpy
    im = bpy.data.images.load(path, check_existing=False)
    w, h = im.size
    a = np.array(im.pixels[:], dtype=np.float32).reshape(h, w, 4)[::-1]
    bpy.data.images.remove(im)
    return a
