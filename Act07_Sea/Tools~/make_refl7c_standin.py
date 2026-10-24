"""The stand-in for Refl_S7c (README_Act07a §0 #12): what 7c's dark mirror reflects -- the water above and the palace
lamps -- baked from the SAME environment the reference frames use (Docs~/lookdev/scene_7a.lamps_env at 897.96: the
PalaceFrame lamps, gold #E0A860 under S7b x 14, 0.25 deg, the drowned city's specks; no fog in it: the sea shader's
_FogChroma does the distance), as a 6-face horizontal strip EXR the Sea kit's importer turns into a cube
(Sea/Editor/LanbaiSeaEditor.cs: 'Cube_' prefix, BC6H, specular convolution). The driver sets it as _Udon_ReflCube in 7c
until Control bakes the real one.

  ~/bpy/bin/python Act07_Sea/Tools~/make_refl7c_standin.py        -> Sea/Textures/Cube_Refl7c_Standin_512.exr
"""
import importlib.util
import os
import sys

import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def main():
    sys.path.insert(0, os.path.join(REPO, 'Sea', 'Tools~'))
    MA = load('make_sea_assets', os.path.join(REPO, 'Sea', 'Tools~', 'make_sea_assets.py'))
    SC = load('scene_7a', os.path.join(REPO, 'Act07_Sea', 'Docs~', 'lookdev', 'scene_7a.py'))
    env = SC.lamps_env(897.96, {})
    strip = MA.strip_from(lambda d: MA.S.clamp_max_channel(env.lookup(d), 16.0), 512).astype(np.float32)
    out = os.path.join(REPO, 'Sea', 'Textures', 'Cube_Refl7c_Standin_512.exr')
    MA.write_exr(strip, out)
    print('wrote', out, strip.shape, 'max', float(strip.max()))


if __name__ == '__main__':
    main()
