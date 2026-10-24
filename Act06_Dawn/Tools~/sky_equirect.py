# -*- coding: utf-8 -*-
"""天空会话的正式预设（Sky/SkyPresets 的 dawn），用它自己的 CPU 版 Lanbai/Sky（真的 LanbaiSky.cginc + LanbaiSkyLayers.cginc，
slangpy）渲成一张等距柱状图（Unity 世界方向，列 u = az/360 + 0.5，行 v = (90 − el)/180），给参考渲染当天、当世界光。
python sky_equirect.py dawn [W] -> $LB_WORK/sky_<preset>_<W>.hdr"""
import os
import sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
REPO = os.path.normpath(os.path.join(HERE, '..', '..'))
sys.path.insert(0, os.path.join(REPO, 'Sky', 'Tools~', 'render'))
sys.path.insert(0, os.path.join(REPO, 'Clouds_v2', 'Source'))
import lb_common as C  # noqa: E402

WORK = os.environ.get('LB_WORK', '/tmp/lb/clouds')


def render(name, W=1024):
    cwd = os.getcwd()
    os.chdir(os.path.join(REPO, 'Sky', 'Tools~', 'render'))
    try:
        import make_presets as MP
        import sky_cpu as S
    finally:
        os.chdir(cwd)
    p = MP.P[name]
    S.renderer().tex.clear()
    if p.get('hdri_file'):
        S.set_cube('_CubeA', S.load_hdr(p['hdri_file']))
    if p.get('glow'):
        S.set_tex('_GlowTex', S.load_glow(1))
    globs = dict(p['globals'])
    if p.get('fog_from_sky'):
        globs.update(MP.fog_group(p))
    H = W // 2
    d = C.equirect_dirs(H, W, 0.0).reshape(-1, 3).astype(np.float32)
    out = np.zeros((d.shape[0], 3), np.float32)
    n = 1 << 18
    for i in range(0, d.shape[0], n):
        out[i:i + n] = np.asarray(S.render(d[i:i + n], p['material'], globs)).reshape(-1, 3)
    img = out.reshape(H, W, 3)
    path = os.path.join(WORK, f'sky_{name}_{W}.hdr')
    os.makedirs(WORK, exist_ok=True)
    C.write_hdr(path, img)
    return path, img, p


if __name__ == '__main__':
    name = sys.argv[1] if len(sys.argv) > 1 else 'dawn'
    W = int(sys.argv[2]) if len(sys.argv) > 2 else 1024
    path, img, p = render(name, W)
    print(path, img.shape, float(img.max()), 'sunAz', p.get('sunAz'))
