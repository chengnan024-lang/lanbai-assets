"""Lanbai/Sky on the CPU: the real LanbaiSky.cginc + LanbaiSkyLayers.cginc through shader_cpu.Renderer."""
import os
import numpy as np
from shader_cpu import Renderer, cpu_stub, read, strip_includes, blur_equirect, camera_dirs, REPO

PRELUDE = None
_R = None
SLOTS = {'_CubeA': 0, '_CubeB': 2, '_GlowTex': 4, '_MoonTex': 5}


def renderer():
    global _R
    if _R is None:
        pre = cpu_stub() + strip_includes(read('Common/Shaders/LanbaiVR.cginc')) + strip_includes(read('Common/Shaders/LanbaiSky.cginc')) \
            + strip_includes(read('Sky/Shaders/LanbaiSkyLayers.cginc'))
        # samplerCUBE _Udon_FogCube (LanbaiSky) is a handle too: slot 6
        _R = Renderer(pre, ' OUTC[id] = LanbaiSkyColour(normalize(V[id]));', 'lanbai_sky')
    return _R


DEFAULTS = dict(_CubeA_HDR=(1, 1, 0, 0), _CubeB_HDR=(1, 1, 0, 0), _RotationA=0, _ExposureA=0, _ClampA=16, _ZenithTintA=(1, 1, 1, 1), _MidTintA=(1, 1, 1, 1), _HorizonTintA=(1, 1, 1, 1), _HorizonAntiTintA=(1, 1, 1, 1),
                _RotationB=0, _ExposureB=0, _ClampB=16, _ZenithTintB=(1, 1, 1, 1), _MidTintB=(1, 1, 1, 1), _HorizonTintB=(1, 1, 1, 1), _HorizonAntiTintB=(1, 1, 1, 1),
                _TintElevation=(2, 35, 75, 1), _Blend=0, _NadirColor=(0.16, 0.27, 0.39, 0), _BelowShape=(-35, 0.8, 0.6, 2),
                _ProcWeight=0, _Band1Color=(0.05, 0.095, 0.278, 1), _Band1Shape=(14, 8, 0, 60), _Band1Gain=0, _Band2Color=(1, 1, 1, 1), _Band2Shape=(12, 5, 180, 55), _Band2Gain=0,
                _OtherSky=0, _OtherGain=0.82, _OtherTint=(0.92, 0.95, 1.05, 1), _OtherSeam=1, _OtherFromB=0, _HorizonLift=0.8,
                _NightBlend=0, _NightColor=(0.0015, 0, 0, 1), _StarFloorAdd=(0.0025, 0.0048, 0.017, 1), _GalaxyGain=0,
                _NightMaskDir=(0, 0, 1, 0), _NightMaskShape=(40, 15, 12, 10),
                _SunDir=(0.7, 0.1, 0.7, 0), _SunColor=(5.86, 3.70, 1.98, 1), _SunShape=(0.45, 0.04, 0.55, 0), _SunGain=1,
                _SunGlow=(0, 1.2, 0, 0.15), _SunGlowColor=(1, 0.6, 0.3, 1),
                _MoonDir=(-0.206, 0.139, 0.969, 0), _MoonColor=(2.81, 2.97, 3.18, 1), _MoonRadius=0.6, _MoonGain=0,
                _MoonGlow=(1.6, 0.9, 0.06, 0.32), _MoonGlowColor=(0.275, 0.366, 0.578, 1), _Exposure=0, _Dither=0, _PurpleGuard=(0, 0.86, 1.25, 0))


def set_cube(slot_name, equirect):
    r = renderer()
    s = SLOTS[slot_name]
    r.set_texture(s, equirect)
    r.set_texture(s + 1, blur_equirect(equirect, max(1.0, equirect.shape[1] / 256.0)))   # ~ mip 3 of a 2048 face


def set_tex(slot_name, img):
    renderer().set_texture(SLOTS[slot_name], img)


def render(dirs, params=None, globs=None):
    u = dict(DEFAULTS)
    u.update(params or {})
    u.update(globs or {})
    for name, s in SLOTS.items():
        u[name] = {'id': s if s in renderer().tex else -1}
    u['_Udon_FogCube'] = {'id': -1}
    u.setdefault('unity_FogColor', (0.1, 0.1, 0.1, 1))
    u.setdefault('_WorldSpaceCameraPos', (0.55, 1.70, 2.05))
    u.setdefault('_ScreenParams', (480.0, 270.0, 1.0, 1.0))           # the preview tiles (LanbaiPixelAngle -> moon mip)
    u.setdefault('UNITY_MATRIX_P', [[1.0, 0, 0, 0], [0, 1.0 / 0.5625, 0, 0], [0, 0, 1, 0], [0, 0, 1, 0]])
    u.setdefault('_MoonTex_TexelSize', (1 / 1024.0, 1 / 1024.0, 1024.0, 1024.0))
    return renderer().run(dirs, u)


def load_hdr(path):
    from hdrio import read_hdr
    return read_hdr(path)
